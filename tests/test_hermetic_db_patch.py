# coding: utf-8
"""SPEC-TEST-HERMETIC-001 AC-003 — 허메틱 패치 픽스처의 전 모듈 커버 검증.

pkgutil 로 ``backend.routers`` 패키지를 순회해, 각 모듈이 보유한
``WEEKLY_DB_PATH``·``DAILY_DB_PATH`` 모듈 상수가 프로덕션 Output 경로가 아니라
conftest ``hermetic_db_paths`` 픽스처가 만든 tmp_path 산하 경로를 가리킴을
단언한다.

이 테스트가 잡아내는 오구현:
- ``backend.deps`` 만 패치한 수정 — 라우터 모듈 상수는 원본 Output 경로 잔존으로 FAIL
- market/stage/sectors 등 일부 모듈만 이름 나열해 패치한 수정 — 누락된 모듈이 FAIL
- 조건부 패치의 조건을 잃은 수정(Output 판별 제거) — 값이 tmp 가 아니면 FAIL

되돌림 RED: conftest 의 autouse 패치를 제거(되돌림)하면 본 테스트는 반드시
실패해야 한다(실패 출력은 evidence/m3-unexplained-diagnosis.md 에 기록).
"""
from __future__ import annotations

import importlib
import pkgutil

import backend.routers as _routers_pkg

# 수집 시점에 모든 라우터 모듈을 임포트해 sys.modules 에 등록한다.
# hermetic_db_paths autouse 픽스처는 테스트 함수 직전에 실행되므로, 모듈이 그
# 이전에 로드돼 있어야 패치 대상 순회에 포함된다(본 파일 단독 실행 대비).
for _mod_info in pkgutil.iter_modules(_routers_pkg.__path__):
    importlib.import_module(f"{_routers_pkg.__name__}.{_mod_info.name}")


def _router_modules() -> list[str]:
    """backend.routers 패키지의 모든 하위 모듈 이름을 pkgutil 순회로 수집한다."""
    import backend.routers as routers_pkg

    names = [routers_pkg.__name__]
    for mod_info in pkgutil.iter_modules(routers_pkg.__path__):
        names.append(f"{routers_pkg.__name__}.{mod_info.name}")
    return names


def test_hermetic_patch_covers_all_router_db_path_constants(tmp_path) -> None:
    """AC-003 — 모든 라우터 모듈의 DB 경로 상수가 tmp_path 산하를 가리킨다."""
    checked: list[str] = []
    for module_name in _router_modules():
        module = importlib.import_module(module_name)
        for attr in ("WEEKLY_DB_PATH", "DAILY_DB_PATH"):
            value = getattr(module, attr, None)
            if value is None:
                continue  # 해당 상수를 보유하지 않는 라우터는 대상 아님
            assert isinstance(value, str), (
                f"{module_name}.{attr} 이 문자열이 아니다: {value!r}"
            )
            assert value.startswith(str(tmp_path)), (
                f"{module_name}.{attr} = {value!r} 이 tmp_path 산하가 아니다 — "
                "허메틱 패치(hermetic_db_paths)가 이 모듈을 커버하지 못했다"
            )
            checked.append(f"{module_name}.{attr}")

    # 순회 대상이 실재했음을 보장한다 — 빈 순회는 검증 자체가 무의미해진다.
    assert len(checked) >= 10, (
        f"패치 커버 대상 상수가 비정상적으로 적다: {len(checked)}건 {checked}"
    )


def test_hermetic_patch_covers_config_derived_constants(tmp_path) -> None:
    """config 파생 상수(my_chart.config.DEFAULT_DB_*)도 tmp_path 산하를 가리킨다.

    ``_get_stock_meta`` 폴백(M1 미설명 4건의 원인)처럼 my_chart 계층에서 config
    상수를 직접 읽는 경로를 막는 축이다.
    """
    from my_chart import config

    for attr in ("DEFAULT_DB_DAILY", "DEFAULT_DB_WEEKLY"):
        value = getattr(config, attr)
        assert isinstance(value, str), f"config.{attr} 이 문자열이 아니다: {value!r}"
        assert value.startswith(str(tmp_path)), (
            f"config.{attr} = {value!r} 이 tmp_path 산하가 아니다 — "
            "허메틱 패치가 config 계층을 커버하지 못했다"
        )
