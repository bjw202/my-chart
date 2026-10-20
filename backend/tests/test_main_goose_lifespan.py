"""SPEC-AI-REPORT-004 M2 — 서버 lifespan이 goose 하네스 설치를 1회 호출하는지 확인.

무거운 초기화(KRX 세션·레지스트리)는 가짜로 바꾸고,
`goose_harness.install_at_startup` 호출 여부와 실패 시에도 서버가 뜨는지만 본다.
실제 ~/.goose-harness는 건드리지 않는다(설치 함수 자체를 대체).

격리: 다른 테스트 모듈이 `my_chart`·`backend*`를 sys.modules 스텁으로 바꿔 둘 수 있으므로,
이 테스트는 `my_chart*`·`backend*` 항목을 잠시 비우고 실제 모듈로 `backend.main`을 불러온 뒤
sys.modules를 원래대로 되돌린다.
"""

from __future__ import annotations

import importlib
import sys

import pytest


# 모듈 범위: 실제 my_chart(numpy C 확장 포함)를 한 프로세스에서 두 번 불러오면 ImportError가 나므로
# 이 파일의 테스트들이 한 번 불러온 모듈을 함께 쓴다(M4에서 두 번째 테스트 추가).
@pytest.fixture(scope="module")
def real_main():
    saved = {name: mod for name, mod in sys.modules.items() if _ours(name)}
    for name in saved:
        del sys.modules[name]
    try:
        main_module = importlib.import_module("backend.main")
        goose_harness = importlib.import_module("backend.services.goose_harness")
        yield main_module, goose_harness
    finally:
        # `my_chart*`·`backend*`만 되돌린다. sys.modules 전체를 되돌리면 여기서 처음 불러온 numpy 같은
        # C 확장이 빠지고, 다음 파일(test_goose_runner)이 다시 불러올 때 ImportError가 난다.
        for name in [n for n in sys.modules if _ours(n)]:
            del sys.modules[name]
        sys.modules.update(saved)


def _ours(name: str) -> bool:
    return name in ("my_chart", "backend") or name.startswith(("my_chart.", "backend."))


@pytest.fixture()
def light_lifespan(real_main, monkeypatch):
    main_module, goose_harness = real_main
    monkeypatch.setattr(main_module, "initialize", lambda: None)
    monkeypatch.setattr(main_module, "get_stock_registry", lambda: None)
    monkeypatch.setattr(main_module, "get_sector_registry", lambda: None)
    calls: list[dict] = []

    def fake_install(**kwargs):
        calls.append(kwargs)
        return goose_harness.HarnessStatus(False, "simulated source mismatch", None)

    monkeypatch.setattr(goose_harness, "install_at_startup", fake_install)
    return main_module, calls


async def test_lifespan_installs_goose_harness_once_and_survives_failure(light_lifespan):
    main_module, calls = light_lifespan

    async with main_module.lifespan(main_module.app):
        pass

    assert len(calls) == 1


async def test_lifespan_shutdown_cancels_running_goose_job(light_lifespan, monkeypatch):
    """design §4.6: lifespan 종료 단계에서 goose 작업 서비스의 shutdown()을 1회 호출한다(AC-011 (4))."""
    main_module, _ = light_lifespan
    goose_job_service = importlib.import_module("backend.services.goose_job_service")
    shutdowns: list[int] = []

    class FakeService:
        async def shutdown(self):
            shutdowns.append(1)

    monkeypatch.setattr(goose_job_service, "get_service", lambda: FakeService())

    async with main_module.lifespan(main_module.app):
        assert shutdowns == []

    assert shutdowns == [1]
