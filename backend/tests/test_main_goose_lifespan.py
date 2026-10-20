"""SPEC-AI-REPORT-004 M2 — 서버 lifespan이 goose 하네스 설치를 1회 호출하는지 확인.

무거운 초기화(KRX 세션·레지스트리·Deep 프롬프트·스테이징 정리)는 가짜로 바꾸고,
`goose_harness.install_at_startup` 호출 여부와 실패 시에도 서버가 뜨는지만 본다.
실제 ~/.goose-harness는 건드리지 않는다(설치 함수 자체를 대체).

격리: 다른 테스트 모듈(test_ai_report_router_deep_mode)이 import 시점에 `my_chart`를
sys.modules 스텁으로 바꿔 두므로, 이 테스트는 `my_chart*`·`backend*` 항목을 잠시 비우고
실제 모듈로 `backend.main`을 불러온 뒤 sys.modules를 원래대로 되돌린다.
"""

from __future__ import annotations

import importlib
import sys

import pytest


@pytest.fixture()
def real_main():
    saved = dict(sys.modules)
    for name in list(sys.modules):
        if name in ("my_chart", "backend") or name.startswith(("my_chart.", "backend.")):
            del sys.modules[name]
    try:
        main_module = importlib.import_module("backend.main")
        goose_harness = importlib.import_module("backend.services.goose_harness")
        yield main_module, goose_harness
    finally:
        sys.modules.clear()
        sys.modules.update(saved)


@pytest.fixture()
def light_lifespan(real_main, monkeypatch):
    main_module, goose_harness = real_main
    monkeypatch.setattr(main_module, "initialize", lambda: None)
    monkeypatch.setattr(main_module, "get_stock_registry", lambda: None)
    monkeypatch.setattr(main_module, "get_sector_registry", lambda: None)
    monkeypatch.setattr(main_module, "_load_synthesis_prompt", lambda: "prompt")
    monkeypatch.setattr(main_module, "_cleanup_stale_staging_dirs", lambda max_age_days: 0)
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
