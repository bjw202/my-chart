"""naver_theme_v2.crawler 단위 테스트 — AC-7, AC-8, AC-13.

requests.Session.get을 mock하여 네트워크 없이 동작 검증.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import unittest.mock as mock

import pytest

for _mod in ("pykrx", "pykrx.stock"):
    if _mod not in sys.modules:
        import types
        sys.modules[_mod] = types.ModuleType(_mod)

from backend.services.naver_theme_v2 import crawler
from backend.services.naver_theme_v2 import config

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "naver_theme_v2"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _ok_list_response() -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.status_code = 200
    resp.headers = {"Content-Type": "application/json; charset=utf-8"}
    resp.json.return_value = _load("list_synthetic.json")
    return resp


def _ok_detail_response() -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.status_code = 200
    resp.headers = {"Content-Type": "application/json; charset=utf-8"}
    resp.json.return_value = _load("detail_synthetic.json")
    return resp


def _err_5xx_response(status: int = 503) -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.status_code = status
    resp.headers = {"Content-Type": "application/json; charset=utf-8"}
    resp.json.return_value = _load("error_5xx_response.json")
    return resp


# ---------------------------------------------------------------------------
# AC-7: 모바일 UA + Referer + Accept 헤더 검증
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_crawler_headers_anonymous():
    """AC-7: Cookie/Authorization 없음. User-Agent에 iPhone+Mobile 포함. Referer, Accept 검증."""
    with mock.patch(
        "backend.services.naver_theme_v2.crawler.requests.Session.get",
        return_value=_ok_list_response(),
    ) as mocked_get:
        crawler.fetch_theme_list(page=1, page_size=50)

    call_args = mocked_get.call_args
    sent_headers = call_args.kwargs.get("headers", {})

    assert "User-Agent" in sent_headers
    assert "iPhone" in sent_headers["User-Agent"]
    assert "Mobile" in sent_headers["User-Agent"]

    assert "Referer" in sent_headers
    assert sent_headers["Referer"] == "https://m.stock.naver.com/domestic/home/theme/daily"

    assert "Accept" in sent_headers
    assert "application/json" in sent_headers["Accept"]

    # Cookie/Authorization 절대 없음 (REQ-NT2-C-001)
    assert "Cookie" not in sent_headers
    assert "Authorization" not in sent_headers


# ---------------------------------------------------------------------------
# AC-8: sleep ≥ 0.7s between consecutive requests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_crawler_sleep_policy():
    """AC-8: 연속 호출 사이 sleep ≥ 0.7s 검증."""
    call_times: list[float] = []

    def fake_get(*args, **kwargs):
        call_times.append(time.monotonic())
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = _load("list_synthetic.json")
        return resp

    with mock.patch(
        "backend.services.naver_theme_v2.crawler.requests.Session.get",
        side_effect=fake_get,
    ):
        crawler.fetch_theme_list(page=1, page_size=50)
        crawler.fetch_theme_list(page=2, page_size=50)

    assert len(call_times) == 2
    gap = call_times[1] - call_times[0]
    assert gap >= config.REQUEST_SLEEP_SECONDS, (
        f"Sleep between requests must be >= {config.REQUEST_SLEEP_SECONDS}s, got {gap:.3f}s"
    )


# ---------------------------------------------------------------------------
# AC-13: 5xx retry 동작
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_crawler_5xx_retry_then_success():
    """AC-13 Case A: 첫 호출 503 → 두 번째 호출 200 → call_count==2, 결과 반환."""
    call_count = {"n": 0}

    def fake_get(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return _err_5xx_response(503)
        return _ok_detail_response()

    with mock.patch(
        "backend.services.naver_theme_v2.crawler.requests.Session.get",
        side_effect=fake_get,
    ):
        result = crawler.fetch_theme_detail(theme_id=178)

    assert call_count["n"] == 2
    assert result is not None
    assert result.get("isSuccess") is True


@pytest.mark.unit
def test_crawler_5xx_persistent_raise():
    """AC-13 Case B: 2회 모두 503 → exception raise (service.py가 catch)."""
    def always_5xx(*args, **kwargs):
        return _err_5xx_response(503)

    with mock.patch(
        "backend.services.naver_theme_v2.crawler.requests.Session.get",
        side_effect=always_5xx,
    ):
        with pytest.raises(Exception):
            crawler.fetch_theme_detail(theme_id=178)


# ---------------------------------------------------------------------------
# Content-Type 검증
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_crawler_content_type_validation():
    """Content-Type이 application/json이 아니면 ValueError 발생."""
    def html_response(*args, **kwargs):
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        resp.json.return_value = {}
        return resp

    with mock.patch(
        "backend.services.naver_theme_v2.crawler.requests.Session.get",
        side_effect=html_response,
    ):
        with pytest.raises(ValueError):
            crawler.fetch_theme_list(page=1, page_size=50)
