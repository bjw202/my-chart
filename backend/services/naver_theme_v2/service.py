"""단일 진입점 + V1 analyzer/db_join 재사용."""

import json
import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests
from pydantic import ValidationError

# V1 모듈 재사용 (import만, 파일 수정 X — REQ-NT2-C-002)
from backend.deps import DAILY_DB_PATH
from backend.services.naver_theme.service import ThemeAnalysisResult
from backend.services.naver_theme.analyzer import (
    build_strong_themes,
    build_leaders,
    build_multi_theme_stocks,
)
from backend.services.naver_theme.db_join import enrich_market_cap

from . import config, crawler, parser

# @MX:ANCHOR: V2 단일 진입점 (REQ-NT2-001) — frontend/route 진입점, fan_in≥3 예상
# @MX:REASON: V1 collect_and_analyze와 동일 시그니처 패턴, V2 mobile API 기반
# @MX:SPEC: SPEC-NAVER-THEME-002 REQ-NT2-001, SPEC-NAVER-THEME-003 REQ-NT3-005


def collect_and_analyze_v2(
    top_n_themes: int = 20,
    leaders_per_theme: int = 3,
    skip_details: bool = False,
) -> ThemeAnalysisResult:
    """V2 단일 진입점 (REQ-NT2-001).

    Args:
        top_n_themes: 강세 테마 상위 N개 (default 20, V1과 동일)
        leaders_per_theme: 테마별 주도주 N개
        skip_details: True면 list endpoint만 호출 (10초 이내 빠른 모드)

    Returns:
        ThemeAnalysisResult (V1 schema 동일, themes_df/stocks_df에 신규 컬럼 추가)
    """
    errors: list[dict] = []
    _start_time = time.monotonic()  # elapsed_sec 측정 시작 (REQ-NT3-005)

    # Phase A: list endpoint 페이지네이션
    all_themes: list[dict] = []
    for page in range(1, config.LIST_MAX_PAGES + 1):
        try:
            list_resp = crawler.fetch_theme_list(page=page, page_size=config.LIST_PAGE_SIZE)
            page_themes = parser.parse_theme_list(list_resp)
            if not page_themes:
                break
            all_themes.extend(page_themes)
            if len(page_themes) < config.LIST_PAGE_SIZE:
                break
        except (requests.RequestException, json.JSONDecodeError, KeyError, ValidationError, ValueError) as e:
            errors.append(
                {
                    "theme_id": None,
                    "stage": "list_fetch",
                    "reason": f"page={page}: {type(e).__name__}: {e}",
                }
            )
            break

    themes_df = pd.DataFrame(all_themes)
    if themes_df.empty:
        return _empty_result(errors, elapsed=time.monotonic() - _start_time)

    # Phase B: top-N 결정 (V1 analyzer 재사용)
    strong_themes_df = build_strong_themes(themes_df, top_n=top_n_themes)
    top_theme_ids = strong_themes_df["theme_id"].tolist()

    # Phase C: detail endpoint (skip_details=False일 때만)
    all_stocks: list[dict] = []
    if not skip_details:
        for theme_id in top_theme_ids:
            try:
                detail_resp = crawler.fetch_theme_detail(theme_id=theme_id)
                detail_parsed = parser.parse_theme_detail(detail_resp, theme_id=theme_id)
                if detail_parsed is None:
                    errors.append(
                        {
                            "theme_id": theme_id,
                            "stage": "endpoint_drift",
                            "reason": "isSuccess=false",
                        }
                    )
                    continue
                # theme_description을 themes_df에 머지
                themes_df.loc[
                    themes_df["theme_id"] == theme_id, "theme_description"
                ] = detail_parsed["theme_description"]
                all_stocks.extend(detail_parsed["items"])
            except (requests.RequestException, json.JSONDecodeError, KeyError, ValidationError, ValueError) as e:
                errors.append(
                    {
                        "theme_id": theme_id,
                        "stage": "detail_fetch",
                        "reason": f"{type(e).__name__}: {e}",
                    }
                )
                continue

    # REQ-NT3-014 (v1.0.4 amendment): strong_themes_df는 line 73에서 detail 머지 전 빌드되므로
    # theme_description이 None 상태. detail 머지 후 themes_df의 theme_description을 strong_themes_df에 매핑.
    if not skip_details and "theme_description" in themes_df.columns:
        desc_map = themes_df.set_index("theme_id")["theme_description"].to_dict()
        strong_themes_df["theme_description"] = strong_themes_df["theme_id"].map(desc_map)

    stocks_df = pd.DataFrame(all_stocks) if all_stocks else _empty_stocks_df()

    # Phase D: market_cap fallback (REQ-NT2-006) — marketValue 누락 종목 보강
    if not stocks_df.empty and "market_cap" in stocks_df.columns:
        missing_mask = stocks_df["market_cap"].isna()
        if missing_mask.any():
            # V1 enrich_market_cap은 DataFrame 단위 enrich (mode=ro URI — REQ-NT2-C-004)
            stocks_with_missing = stocks_df[missing_mask].copy()
            # stock_code 컬럼이 있어야 enrich_market_cap이 동작
            if "stock_code" in stocks_with_missing.columns:
                enriched = enrich_market_cap(stocks_with_missing, DAILY_DB_PATH)
                stocks_df.loc[missing_mask, "market_cap"] = enriched["market_cap"].values

    # Phase E: V1 analyzer 재사용
    if not stocks_df.empty:
        leaders_df = build_leaders(stocks_df, leaders_per_theme=leaders_per_theme)
        multi_theme_stocks_df = build_multi_theme_stocks(stocks_df)
    else:
        leaders_df = pd.DataFrame()
        multi_theme_stocks_df = pd.DataFrame()

    _generated_at = datetime.now(timezone.utc).isoformat()
    _elapsed = time.monotonic() - _start_time

    return ThemeAnalysisResult(
        themes_df=themes_df,
        stocks_df=stocks_df,
        strong_themes_df=strong_themes_df,
        leaders_df=leaders_df,
        multi_theme_stocks_df=multi_theme_stocks_df,
        metadata={
            # 기존 V2 필드 보존 (REQ-NT3-C-003 additive only)
            "data_source": config.DATA_SOURCE,
            "generated_at": _generated_at,
            "total_themes_seen": len(themes_df),
            "errors": errors,
            # V1 alias 4 필드 추가 (REQ-NT3-005, SPEC-NAVER-THEME-003)
            "collected_at": _generated_at,
            "theme_count": len(themes_df),
            "stock_count": len(stocks_df),
            "elapsed_sec": _elapsed,
        },
    )


def _empty_stocks_df() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "theme_id",
            "theme_name",
            "stock_code",
            "stock_name",
            "code",
            "name",
            "change_pct",
            "change_rate",
            "market_cap",
            "volume",
            "trade_value",
            "inclusion_reason",
            "stock_description",
        ]
    )


def _empty_result(errors: list[dict], elapsed: float = 0.0) -> ThemeAnalysisResult:
    """모든 list 호출이 실패한 경우 빈 결과 반환 (예외 X — REQ-NT2-NF-003).

    V1 alias 4 필드 zero values 보장 (REQ-NT3-006, SPEC-NAVER-THEME-003).
    """
    empty_themes = pd.DataFrame(
        columns=[
            "theme_id",
            "theme_name",
            "change_pct",
            "change_rate",
            "change_pct_3d",
            "up_count",
            "flat_count",
            "down_count",
            "theme_description",
        ]
    )
    empty_stocks = _empty_stocks_df()
    _generated_at = datetime.now(timezone.utc).isoformat()
    return ThemeAnalysisResult(
        themes_df=empty_themes,
        stocks_df=empty_stocks,
        strong_themes_df=empty_themes.copy(),
        leaders_df=empty_stocks.copy(),
        multi_theme_stocks_df=empty_stocks.copy(),
        metadata={
            # 기존 V2 필드 보존 (REQ-NT3-C-003 additive only)
            "data_source": config.DATA_SOURCE,
            "generated_at": _generated_at,
            "total_themes_seen": 0,
            "errors": errors,
            # V1 alias zero values (REQ-NT3-006, SPEC-NAVER-THEME-003)
            "collected_at": _generated_at,
            "theme_count": 0,
            "stock_count": 0,
            "elapsed_sec": elapsed,
        },
    )
