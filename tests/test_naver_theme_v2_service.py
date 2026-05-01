"""naver_theme_v2.service 단위 테스트 — AC-1, AC-2, AC-5, AC-6, AC-11, AC-12, AC-13 service-level.

V1 컬럼 세트 정의는 SPEC acceptance.md §AC-5 기준.
"""
from __future__ import annotations

import inspect
import json
import os
import pathlib
import sys
import unittest.mock as mock

import pandas as pd
import pytest

for _mod in ("pykrx", "pykrx.stock"):
    if _mod not in sys.modules:
        import types
        sys.modules[_mod] = types.ModuleType(_mod)

from backend.services.naver_theme_v2 import collect_and_analyze_v2, ThemeAnalysisResult

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "naver_theme_v2"

# V1 컬럼 기준 세트 (AC-5, AC-12)
V1_THEMES_COLUMNS = {
    "theme_id", "theme_name", "change_rate", "score", "rank",
    "rising_count", "unchanged_count", "falling_count",
}
V1_STOCKS_COLUMNS = {
    "theme_id", "theme_name", "code", "name",
    "market_cap", "change_rate", "inclusion_reason",
}

FRONTEND_THEMES_REQUIRED = {"theme_id", "theme_name", "change_rate", "score", "rank"}
FRONTEND_STOCKS_REQUIRED = {
    "theme_id", "theme_name", "code", "name",
    "market_cap", "change_rate", "inclusion_reason",
}


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _mock_list_response(page: int, page_size: int) -> mock.MagicMock:
    """페이지 1에만 데이터, 이후 빈 sectors 반환."""
    resp = mock.MagicMock()
    resp.status_code = 200
    resp.headers = {"Content-Type": "application/json; charset=utf-8"}
    if page == 1:
        resp.json.return_value = _load("list_synthetic.json")
    else:
        resp.json.return_value = {
            "isSuccess": True,
            "detailCode": "ok",
            "message": "OK",
            "result": {"totalRisingCount": 0, "totalUnChangedCount": 0, "totalFallingCount": 0, "sectors": []},
        }
    return resp


def _mock_detail_response(theme_id: int) -> mock.MagicMock:
    resp = mock.MagicMock()
    resp.status_code = 200
    resp.headers = {"Content-Type": "application/json; charset=utf-8"}
    resp.json.return_value = _load("detail_synthetic.json")
    return resp


def _make_service_mock():
    """crawler.fetch_theme_list, crawler.fetch_theme_detail을 fixture로 대체하는 mock context."""
    def side_effect_get(url, params=None, headers=None, timeout=None):
        params = params or {}
        if "sectors/all" in url:
            page = params.get("page", 1)
            return _mock_list_response(page, params.get("pageSize", 50))
        elif "sector/item/list" in url:
            theme_id = int(params.get("sectorCode", 178))
            return _mock_detail_response(theme_id)
        resp = mock.MagicMock()
        resp.status_code = 404
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"isSuccess": False, "result": None}
        return resp

    return mock.patch(
        "backend.services.naver_theme_v2.crawler.requests.Session.get",
        side_effect=side_effect_get,
    )


# ---------------------------------------------------------------------------
# AC-1: 시그니처 검증
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_collect_and_analyze_v2_signature():
    """AC-1: 함수 시그니처 — top_n_themes=20, leaders_per_theme=3, skip_details=False."""
    assert callable(collect_and_analyze_v2)

    sig = inspect.signature(collect_and_analyze_v2)
    params = sig.parameters

    assert "top_n_themes" in params
    assert "leaders_per_theme" in params
    assert "skip_details" in params

    assert params["top_n_themes"].default == 20
    assert params["leaders_per_theme"].default == 3
    assert params["skip_details"].default is False


# ---------------------------------------------------------------------------
# AC-2: ThemeAnalysisResult 인스턴스 반환 + data_source
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_collect_and_analyze_v2_returns_result():
    """AC-2: fixture mock 기반. ThemeAnalysisResult 인스턴스, metadata data_source 확인."""
    with _make_service_mock():
        result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)

    assert isinstance(result, ThemeAnalysisResult)
    assert isinstance(result.themes_df, pd.DataFrame)
    assert isinstance(result.stocks_df, pd.DataFrame)
    assert isinstance(result.strong_themes_df, pd.DataFrame)
    assert isinstance(result.leaders_df, pd.DataFrame)
    assert isinstance(result.multi_theme_stocks_df, pd.DataFrame)
    assert isinstance(result.metadata, dict)

    assert result.metadata.get("data_source") == "naver_mobile_v2"


# ---------------------------------------------------------------------------
# AC-5: V1 컬럼 100% 보존
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_v1_columns_preserved():
    """AC-5: V2 themes_df, stocks_df가 V1 컬럼을 superset으로 가짐."""
    with _make_service_mock():
        result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)

    if not result.themes_df.empty:
        missing_themes = V1_THEMES_COLUMNS - set(result.themes_df.columns)
        assert missing_themes == set(), f"V1 themes 컬럼 누락: {missing_themes}"

    if not result.stocks_df.empty:
        missing_stocks = V1_STOCKS_COLUMNS - set(result.stocks_df.columns)
        assert missing_stocks == set(), f"V1 stocks 컬럼 누락: {missing_stocks}"

    # V2 신규 컬럼 추가 확인
    if not result.themes_df.empty:
        assert "theme_description" in result.themes_df.columns
    if not result.stocks_df.empty:
        assert "stock_description" in result.stocks_df.columns


# ---------------------------------------------------------------------------
# AC-6: errors dict 리스트 shape
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_errors_dict_shape():
    """AC-6: detail fetch를 강제 실패시켜 errors[] 구조 검증."""
    VALID_STAGES = {
        "list_fetch", "detail_fetch", "schema_validation",
        "content_type", "json_decode", "endpoint_drift",
    }

    call_count = {"n": 0}

    def side_effect_get(url, params=None, headers=None, timeout=None):
        params = params or {}
        if "sectors/all" in url:
            page = params.get("page", 1)
            return _mock_list_response(page, 50)
        elif "sector/item/list" in url:
            call_count["n"] += 1
            # 항상 5xx 반환 → service가 errors[]에 기록
            resp = mock.MagicMock()
            resp.status_code = 503
            resp.headers = {"Content-Type": "application/json"}
            resp.json.return_value = _load("error_5xx_response.json")
            return resp
        resp = mock.MagicMock()
        resp.status_code = 404
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = {"isSuccess": False, "result": None}
        return resp

    with mock.patch(
        "backend.services.naver_theme_v2.crawler.requests.Session.get",
        side_effect=side_effect_get,
    ):
        result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)

    errors = result.metadata.get("errors", [])
    assert isinstance(errors, list)

    for err in errors:
        assert isinstance(err, dict)
        assert "theme_id" in err
        assert "stage" in err
        assert "reason" in err
        assert err["stage"] in VALID_STAGES
        assert isinstance(err["reason"], str)


# ---------------------------------------------------------------------------
# AC-11: DB mtime 무변경
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_db_mtime_unchanged():
    """AC-11: collect_and_analyze_v2 호출 후 DB mtime 변경 없음 (REQ-NT2-C-004)."""
    db_path = pathlib.Path("Output/stock_data_daily.db")
    mtime_before = db_path.stat().st_mtime if db_path.exists() else 0.0

    with _make_service_mock():
        collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)

    mtime_after = db_path.stat().st_mtime if db_path.exists() else 0.0
    assert mtime_after == mtime_before, (
        f"DB가 수정됨. before={mtime_before}, after={mtime_after}"
    )


# ---------------------------------------------------------------------------
# AC-12: frontend 컬럼 호환성 + dtype
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_frontend_columns_compatibility():
    """AC-12: frontend 의존 컬럼 존재 + theme_id int, market_cap int dtype."""
    with _make_service_mock():
        result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)

    assert FRONTEND_THEMES_REQUIRED.issubset(set(result.themes_df.columns))
    assert FRONTEND_STOCKS_REQUIRED.issubset(set(result.stocks_df.columns))

    if not result.themes_df.empty:
        assert pd.api.types.is_integer_dtype(result.themes_df["theme_id"])

    if not result.stocks_df.empty:
        assert pd.api.types.is_integer_dtype(result.stocks_df["market_cap"])


# ---------------------------------------------------------------------------
# AC-13 service level: 5xx 2회 실패 → errors 기록, 예외 X
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_5xx_retry_then_partial_failure():
    """AC-13 service: 2회 모두 5xx 실패 → errors[]에 detail_fetch 기록, 예외 없음."""
    def always_5xx_detail(url, params=None, headers=None, timeout=None):
        params = params or {}
        if "sectors/all" in url:
            page = params.get("page", 1)
            return _mock_list_response(page, 50)
        resp = mock.MagicMock()
        resp.status_code = 503
        resp.headers = {"Content-Type": "application/json"}
        resp.json.return_value = _load("error_5xx_response.json")
        return resp

    with mock.patch(
        "backend.services.naver_theme_v2.crawler.requests.Session.get",
        side_effect=always_5xx_detail,
    ):
        result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)

    errors = result.metadata.get("errors", [])
    detail_errors = [e for e in errors if e["stage"] == "detail_fetch"]
    assert len(detail_errors) >= 1, "detail_fetch 실패가 errors[]에 기록되어야 함"


# ---------------------------------------------------------------------------
# 라이브 통합 테스트 (T5에서 실행, 여기서는 작성만)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_collect_and_analyze_v2_live():
    """라이브 mobile API 호출. T5에서 실행 (CI에서는 skip, 로컬에서만)."""
    result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)
    assert isinstance(result, ThemeAnalysisResult)
    assert len(result.themes_df) >= 1
    assert result.themes_df["theme_description"].notna().sum() >= 1
    assert result.stocks_df["stock_description"].notna().sum() >= 1
