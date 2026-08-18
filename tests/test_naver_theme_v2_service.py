"""naver_theme_v2.service 단위 테스트 — AC-1, AC-2, AC-5, AC-6, AC-11, AC-12, AC-13 service-level.

V1 컬럼 세트 정의는 V1 코드 직접 inspection 결과 기준
(backend/services/naver_theme/parser.py + backend/services/naver_theme/analyzer.py).
SPEC acceptance.md v1.0.1 amendment: plan phase 추정 컬럼명(score/rank/rising_count 등)이
V1 실측(change_pct/up_count 등)과 불일치한 사실이 RUN phase에서 발견됨 → V1 실측으로 정정.
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

# V1 실측 컬럼 세트 (AC-5, AC-12) — V1 build_strong_themes 입력 + V1 parser.py 출력 기준
# V1 themes_df: theme_id, theme_name, change_pct, change_pct_3d, up_count, flat_count, down_count, top_stocks_preview
# V1 stocks_df: theme_id, theme_name, stock_code, stock_name, inclusion_reason, price, change, change_pct, volume, trade_value, per, roe (+ market_cap from enrich_market_cap)
V1_THEMES_COLUMNS = {
    "theme_id", "theme_name", "change_pct", "change_pct_3d",
    "up_count", "flat_count", "down_count",
}
V1_STOCKS_COLUMNS = {
    "theme_id", "theme_name", "stock_code", "stock_name",
    "inclusion_reason", "change_pct", "volume", "trade_value", "market_cap",
}

# Frontend 의존 컬럼 (research.md §3.3) — V1 실측 컬럼명 기준
# V2 parser.py는 V1 호환 alias(change_rate, code, name)도 추가 노출하지만 검증의 source-of-truth는 V1 실측
FRONTEND_THEMES_REQUIRED = {"theme_id", "theme_name", "change_pct"}
FRONTEND_STOCKS_REQUIRED = {
    "theme_id", "theme_name", "stock_code", "stock_name",
    "market_cap", "change_pct", "inclusion_reason",
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
# 매너 호출 sleep 무력화 (테스트 전용)
#
# 본 파일의 테스트는 HTTP 응답을 전부 목킹하지만, crawler._enforce_sleep_policy()
# 의 time.sleep(REQUEST_SLEEP_SECONDS=0.7) 와 5xx 재시도의
# time.sleep(RETRY_BACKOFF_SECONDS=1.0) 은 목킹 대상이 아니라 실제로 잔다.
# 목킹 요청 6회 × 0.7s ≈ 4.2s/테스트 × 13건 ≈ 60초가 순수 대기였다(2026-08-18 실측).
# 두 상수만 0 으로 monkeypatch 하여 대기를 없앤다 — 프로덕션 코드와 매너 호출
# 정책(REQ-NT2-NF-001)은 변경하지 않으며, monkeypatch 이므로 테스트 종료 시 복원된다.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _no_request_sleep(monkeypatch):
    from backend.services.naver_theme_v2 import config as _nt2_config

    monkeypatch.setattr(_nt2_config, "REQUEST_SLEEP_SECONDS", 0)
    monkeypatch.setattr(_nt2_config, "RETRY_BACKOFF_SECONDS", 0)


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
# SPEC-NAVER-THEME-003 AC-6 ~ AC-10: V1 metadata alias 4 필드 검증
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_metadata_v1_alias_fields_present():
    """AC-6 (SPEC-NT3): V2 metadata에 V1 alias 4 필드 모두 존재 + 기존 4 필드 보존.

    REQ-NT3-005: collected_at, theme_count, stock_count, elapsed_sec 추가.
    REQ-NT3-C-003: 기존 data_source, generated_at, total_themes_seen, errors 보존.
    alias 정합성: collected_at == generated_at, theme_count == total_themes_seen.
    """
    with _make_service_mock():
        result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)
    metadata = result.metadata

    # V1 alias 4 필드 존재
    assert "collected_at" in metadata
    assert "theme_count" in metadata
    assert "stock_count" in metadata
    assert "elapsed_sec" in metadata

    # 기존 V2 필드 보존 (REQ-NT3-C-003 additive only)
    assert metadata["data_source"] == "naver_mobile_v2"
    assert "generated_at" in metadata
    assert "total_themes_seen" in metadata
    assert "errors" in metadata

    # alias 정합성
    assert metadata["collected_at"] == metadata["generated_at"]
    assert metadata["theme_count"] == metadata["total_themes_seen"]


@pytest.mark.unit
def test_metadata_collected_at_iso8601():
    """AC-7 (SPEC-NT3): collected_at은 ISO-8601 parsable + timezone-aware.

    REQ-NT3-005: str 타입 + datetime.fromisoformat 파싱 가능 + tzinfo 존재.
    """
    from datetime import datetime

    with _make_service_mock():
        result = collect_and_analyze_v2(top_n_themes=5)
    collected_at = result.metadata["collected_at"]

    assert isinstance(collected_at, str)
    # Z 접미사를 +00:00으로 교체하여 fromisoformat 호환
    parsed = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


@pytest.mark.unit
def test_metadata_stock_count_matches_df():
    """AC-8 (SPEC-NT3): stock_count == len(result.stocks_df).

    REQ-NT3-005: stock_count는 stocks_df 행 수와 일치해야 함.
    """
    with _make_service_mock():
        result = collect_and_analyze_v2(top_n_themes=5)
    stock_count = result.metadata["stock_count"]
    actual_len = len(result.stocks_df)

    assert isinstance(stock_count, int)
    assert stock_count == actual_len, (
        f"stock_count={stock_count}, len(stocks_df)={actual_len}"
    )


@pytest.mark.unit
def test_metadata_elapsed_sec_positive():
    """AC-9 (SPEC-NT3): elapsed_sec은 float, >= 0.0, < 60.0.

    REQ-NT3-005: time.monotonic() 측정값 — fixture mock이므로 < 60초.
    """
    with _make_service_mock():
        result = collect_and_analyze_v2(top_n_themes=5)
    elapsed = result.metadata["elapsed_sec"]

    assert isinstance(elapsed, float)
    assert elapsed >= 0.0
    assert elapsed < 60.0


@pytest.mark.unit
def test_strong_themes_has_theme_description():
    """AC-21 (SPEC-NT3 v1.0.4): strong_themes_df의 theme_description이 themes_df와 동일하게 매핑.

    REQ-NT3-014: detail 호출 후 themes_df에 머지된 theme_description이 strong_themes_df에도 매핑되어야 함.
    v1.0.4 amendment 이전: strong_themes_df = build_strong_themes(themes_df, ...)이 detail 머지 전에 빌드되어
    description이 None으로 남는 버그. frontend가 strong_themes를 우선 사용하므로 사용자 화면에 description 미노출.

    fixture: detail_synthetic.json에 sectorDescription="각종 전선 및 전람(電纜)제조 관련 종목 (synthetic)" 채워짐.
    """
    with _make_service_mock():
        result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)

    # strong_themes_df 컬럼에 theme_description 존재
    assert "theme_description" in result.strong_themes_df.columns

    # themes_df → strong_themes_df 매핑 정합성
    desc_map = result.themes_df.set_index("theme_id")["theme_description"].to_dict()
    for _, row in result.strong_themes_df.iterrows():
        theme_id = row["theme_id"]
        expected = desc_map.get(theme_id)
        actual = row["theme_description"]
        assert actual == expected, (
            f"strong_themes theme_id={theme_id} description mismatch: "
            f"strong={actual!r} vs themes={expected!r}"
        )

    # fixture가 detail에 description을 포함하므로 strong_themes에도 truthy description 1개 이상
    truthy_count = sum(
        1 for desc in result.strong_themes_df["theme_description"] if desc
    )
    assert truthy_count >= 1, (
        "strong_themes_df에 theme_description이 채워진 row가 1개 이상 있어야 함 "
        "(detail fixture sectorDescription이 머지되어야 함)"
    )


@pytest.mark.unit
def test_empty_result_has_v1_alias():
    """AC-10 (SPEC-NT3): 5xx mock으로 _empty_result 경로 강제 — V1 alias 4 필드 zero values.

    REQ-NT3-006: _empty_result()에도 collected_at, theme_count=0, stock_count=0, elapsed_sec>=0.
    errors[]에 최소 1건 기록.
    """
    import requests

    def fake_5xx(*args, **kwargs):
        resp = mock.MagicMock()
        resp.status_code = 503
        resp.headers = {"Content-Type": "application/json"}
        raise requests.HTTPError("503 Service Unavailable")

    with mock.patch(
        "backend.services.naver_theme_v2.crawler.requests.Session.get",
        side_effect=fake_5xx,
    ):
        result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)

    metadata = result.metadata

    # 빈 결과 반환 — 예외 X (REQ-NT2-NF-003 계승)
    assert len(result.themes_df) == 0
    assert len(result.stocks_df) == 0

    # V1 alias 4 필드 모두 존재 (zero values)
    assert metadata["collected_at"]  # truthy ISO string
    assert metadata["theme_count"] == 0
    assert metadata["stock_count"] == 0
    assert metadata["elapsed_sec"] >= 0.0

    # errors 기록됨
    assert len(metadata["errors"]) >= 1


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
