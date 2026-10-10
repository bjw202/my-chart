# SPEC-FNGUIDE-WCOMP-001: GET /api/analysis/{code} 라우터 경유 오프라인 테스트
"""wcomp 리더를 라우터까지 실제로 통과시키는 테스트.

``get_dashboard`` → ``analyze_dashboard`` → ``get_fnguide`` → ``read_fs``·``read_snapshot``을
그대로 쓰고, 맨 아래 ``requests.Session.request``만 ``tests/fnguide/fixtures/wcomp/``의
실응답 축소본으로 바꾼다. 실제 HTTP는 보내지 않는다. 담당 AC: AC-WC-006 (d),
AC-WC-009 (a)(b), AC-WC-010 (라우터·get_fnguide 부분), AC-WC-014(라우터).
"""

from __future__ import annotations

import copy
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import pytest
import requests
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.services.analysis_service import _cache
from fnguide.crawler import get_fnguide

FIXTURE_DIR = Path(__file__).parent / "fnguide" / "fixtures" / "wcomp"
# 응답이 하나뿐인 코드의 재무제표 본문과 스냅샷 본문(fixtures README 참조)
SINGLE_BODY = {
    "005935": FIXTURE_DIR / "getFinIncome_005935_Y_C.json",
    "999999": FIXTURE_DIR / "getFinIncome_999999_Y_C.html",
}
SNAPSHOT_FILE = {
    "005935": "snapshot_005935_served_as_005930.html",
    "999999": "snapshot_999999_object_moved.html",
}
SECTIONS_1_TO_7 = (
    "business_performance",
    "health_indicators",
    "balance_sheet",
    "rate_decomposition",
    "profit_waterfall",
    "trend_signals",
    "five_questions",
)


def _resp(body: bytes, url: str, status: int = 200) -> requests.Response:
    r = requests.Response()
    r.status_code = status
    r._content = body
    r.encoding = "utf-8"
    r.url = url
    return r


@pytest.fixture
def site(monkeypatch):
    """fixture 응답을 돌려주는 가짜 사이트. override[(ep, code, freq, consol)]는
    dict를 고치는 함수, (status, bytes) 튜플, 또는 던질 예외다."""
    state = {"calls": [], "override": {}}

    def fake_request(self, method, url, **kwargs):
        state["calls"].append({"url": url, **kwargs})
        p = kwargs.get("params") or {}
        endpoint, code = url.rsplit("/", 1)[-1], p.get("cmp_cd")
        key = (endpoint, code, p.get("freq_typ"), p.get("consol_typ"))
        ov = state["override"].get(key)
        if isinstance(ov, BaseException):
            raise ov
        if isinstance(ov, tuple):
            return _resp(ov[1], url, ov[0])
        if endpoint == "Snapshot":
            name = SNAPSHOT_FILE.get(code, f"Snapshot_{code}.html")
            return _resp((FIXTURE_DIR / name).read_bytes(), url)
        if code in SINGLE_BODY:
            return _resp(SINGLE_BODY[code].read_bytes(), url)
        path = FIXTURE_DIR / "{}_{}_{}_{}.json".format(*key)
        assert path.exists(), f"fixture 없음: {path.name}"
        if ov is None:
            return _resp(path.read_bytes(), url)
        data = ov(copy.deepcopy(json.loads(path.read_text(encoding="utf-8"))))
        return _resp(json.dumps(data, ensure_ascii=False).encode("utf-8"), url)

    monkeypatch.setattr(requests.Session, "request", fake_request)
    _cache.clear()  # get_dashboard 5분 캐시가 테스트 사이에 새지 않게
    yield state
    _cache.clear()


@pytest.fixture(scope="module")
def client() -> TestClient:
    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    app = FastAPI(lifespan=_noop_lifespan)
    from backend.routers.analysis import router as analysis_router

    app.include_router(analysis_router, prefix="/api")
    return TestClient(app)


# ───────────────────── AC-WC-006 (d) ─────────────────────


def test_ac_wc_006_d_router_period_misalignment_is_503(site, client):
    def misalign(d):
        for h in d["dataset"]["header"]:
            if h["CD"] == "VAL2":
                h["YYMM"] = "2024/09"
        return d

    site["override"][("getFinBalance", "005930", "Y", "C")] = misalign
    assert client.get("/api/analysis/005930").status_code == 503


# ───────────────────── AC-WC-009 (a)(b) ─────────────────────


@pytest.mark.parametrize("code", ["999999", "005935"])
def test_ac_wc_009_router_error_page_and_empty_dataset_are_404(site, client, code):
    resp = client.get(f"/api/analysis/{code}")
    assert resp.status_code == 404
    assert code in resp.text


# ───────────────────── AC-WC-010 ─────────────────────


def test_ac_wc_010_get_fnguide_request_hygiene(site):
    get_fnguide("005930")
    assert site["calls"]
    for c in site["calls"]:
        assert 0 < c["timeout"] <= 10
        for header in ("User-Agent", "X-Requested-With", "Referer"):
            assert header in c["headers"]
        assert c["params"]["cmp_cd"] == "005930" and "005930" not in c["url"]
        assert c.get("allow_redirects", True) is not False


def test_ac_wc_010_router_transport_timeout_is_503(site, client):
    site["override"][("getFinIncome", "005930", "Y", "C")] = requests.exceptions.ConnectTimeout("t")
    assert client.get("/api/analysis/005930").status_code == 503


def test_ac_wc_010_router_http_500_is_503(site, client):
    body = (FIXTURE_DIR / "getFinBalance_005930_Y_C.json").read_bytes()
    site["override"][("getFinBalance", "005930", "Y", "C")] = (500, body)
    assert client.get("/api/analysis/005930").status_code == 503


# ───────────────────── AC-WC-014 (불변) ─────────────────────


@pytest.mark.parametrize("code", ["105560", "001750"])
def test_ac_wc_014_router_financial_layout_is_200_with_null_sections(site, client, code):
    resp = client.get(f"/api/analysis/{code}")
    assert resp.status_code == 200
    body = resp.json()
    assert all(body[s] is None for s in SECTIONS_1_TO_7)
    if code == "105560":
        assert body["company_name"] == "KB금융"
    else:
        assert body["company_name"] and body["company_name"] != code


# ───────────────────── 일반 레이아웃 끝까지 ─────────────────────


def test_general_layout_005930_router_returns_filled_sections(site, client):
    resp = client.get("/api/analysis/005930")
    assert resp.status_code == 200
    body = resp.json()
    assert body["company_name"] == "삼성전자"
    assert all(body[s] is not None for s in SECTIONS_1_TO_7)
