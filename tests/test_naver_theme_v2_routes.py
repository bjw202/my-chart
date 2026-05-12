"""naver_theme_v2 routes 단위 테스트 — AC-9, AC-10, AC-14.

FastAPI TestClient + inspect.getsource 기반. 네트워크 없음.
"""
from __future__ import annotations

import inspect
import re
import sys

import pytest

for _mod in ("pykrx", "pykrx.stock"):
    if _mod not in sys.modules:
        import types
        sys.modules[_mod] = types.ModuleType(_mod)


# ---------------------------------------------------------------------------
# AC-9: V2 라우터 등록 확인
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_v2_routes_registered():
    """AC-9: /api/themes/v2/snapshot GET, /api/themes/v2/quick GET 존재 확인."""
    from backend.main import app

    routes = [(r.path, r.methods) for r in app.routes if hasattr(r, "path")]

    assert any(
        path == "/api/themes/v2/snapshot" and "GET" in (methods or set())
        for path, methods in routes
    ), f"V2 snapshot 라우트 없음. 등록된 routes={[r[0] for r in routes]}"

    assert any(
        path == "/api/themes/v2/quick" and "GET" in (methods or set())
        for path, methods in routes
    ), f"V2 quick 라우트 없음. 등록된 routes={[r[0] for r in routes]}"


# ---------------------------------------------------------------------------
# AC-10: V1 라우터 무수정
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_v1_routes_unchanged():
    """AC-10: /api/themes/snapshot, /api/themes/quick — V1 endpoint 그대로 존재."""
    from backend.main import app

    routes = [
        (r.path, list(r.methods or set()), r.endpoint.__name__)
        for r in app.routes
        if hasattr(r, "path")
    ]

    v1_snapshot = [r for r in routes if r[0] == "/api/themes/snapshot"]
    v1_quick = [r for r in routes if r[0] == "/api/themes/quick"]

    assert len(v1_snapshot) == 1, f"/api/themes/snapshot 라우트 없음. routes={[r[0] for r in routes]}"
    assert len(v1_quick) == 1, f"/api/themes/quick 라우트 없음. routes={[r[0] for r in routes]}"

    assert "GET" in v1_snapshot[0][1]
    assert "GET" in v1_quick[0][1]

    # V1 endpoint 함수명 확인 (V1 ship 시점 기준)
    assert v1_snapshot[0][2] == "themes_snapshot", (
        f"V1 endpoint 함수명이 변경됨: {v1_snapshot[0][2]}"
    )
    assert v1_quick[0][2] == "themes_quick", (
        f"V1 endpoint 함수명이 변경됨: {v1_quick[0][2]}"
    )


# ---------------------------------------------------------------------------
# AC-14: endpoint URL이 config 상수로부터 사용됨
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_endpoint_url_from_config_only():
    """AC-14: config.py에 4개 상수 정의 확인 + crawler/service에 inline URL 없음."""
    from backend.services.naver_theme_v2 import config, crawler, service

    # 4개 상수 존재 + 값 확인
    assert hasattr(config, "NAVER_MOBILE_BASE_URL")
    assert hasattr(config, "NAVER_MOBILE_FRONT_API_PREFIX")
    assert hasattr(config, "LIST_ENDPOINT_PATH")
    assert hasattr(config, "DETAIL_ENDPOINT_PATH")

    assert config.NAVER_MOBILE_BASE_URL == "https://m.stock.naver.com"
    assert config.NAVER_MOBILE_FRONT_API_PREFIX == "/front-api"
    assert config.LIST_ENDPOINT_PATH == "/stock/sectors/all"
    assert config.DETAIL_ENDPOINT_PATH == "/domestic/sector/item/list"

    # crawler.py에 inline URL hardcoded 없음
    crawler_source = inspect.getsource(crawler)
    forbidden_in_crawler = re.findall(
        r'"https?://(?:m\.stock|api\.stock|finance)\.naver\.com[^\"]*"',
        crawler_source,
    )
    assert forbidden_in_crawler == [], (
        f"crawler.py에 inline URL 발견: {forbidden_in_crawler}"
    )

    # service.py에 inline URL hardcoded 없음
    service_source = inspect.getsource(service)
    forbidden_in_service = re.findall(
        r'"https?://(?:m\.stock|api\.stock|finance)\.naver\.com[^\"]*"',
        service_source,
    )
    assert forbidden_in_service == [], (
        f"service.py에 inline URL 발견: {forbidden_in_service}"
    )


@pytest.mark.unit
def test_no_inline_url_in_crawler_service():
    """AC-14 강화: crawler, service 소스 내 naver.com URL literal 0건."""
    from backend.services.naver_theme_v2 import crawler, service

    pattern = re.compile(
        r'"https?://[a-z.]*naver\.com[^\"]*"'
    )

    crawler_matches = pattern.findall(inspect.getsource(crawler))
    service_matches = pattern.findall(inspect.getsource(service))

    assert crawler_matches == [], f"crawler.py inline URL: {crawler_matches}"
    assert service_matches == [], f"service.py inline URL: {service_matches}"
