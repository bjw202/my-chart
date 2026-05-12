import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from backend.deps import DAILY_DB_PATH
from backend.services.naver_theme.analyzer import (
    build_leaders,
    build_multi_theme_stocks,
    build_strong_themes,
)
from backend.services.naver_theme.config import (
    DEFAULT_LEADERS_PER_THEME,
    DEFAULT_TOP_N_THEMES,
)
from backend.services.naver_theme.crawler import (
    fetch_theme_detail_page,
    fetch_theme_list_page,
)
from backend.services.naver_theme.db_join import enrich_market_cap
from backend.services.naver_theme.parser import parse_theme_detail, parse_theme_list

# KST = UTC+9
_KST = timezone(timedelta(hours=9))
logger = logging.getLogger("naver_theme")


@dataclass
class ThemeAnalysisResult:
    """테마 분석 결과 (5종 DataFrame + metadata)."""

    themes_df: pd.DataFrame
    stocks_df: pd.DataFrame
    strong_themes_df: pd.DataFrame
    leaders_df: pd.DataFrame
    multi_theme_stocks_df: pd.DataFrame
    metadata: dict


def _now_kst() -> str:
    return datetime.now(_KST).isoformat(timespec="seconds")


def _collect_theme_list(errors: list[dict]) -> pd.DataFrame:
    # REQ-NT-002, REQ-NT-003: 첫 페이지 fetch → last_page 추출 → 후속 페이지 순회
    themes: list[dict] = []
    try:
        first_html = fetch_theme_list_page(1)
        first = parse_theme_list(first_html)
        themes.extend(first["themes"])
        last_page = max(1, int(first.get("last_page", 1)))
    except requests.RequestException as e:
        errors.append({"theme_id": None, "stage": "list", "reason": f"page=1 네트워크 오류: {e}"})
        return pd.DataFrame()
    except Exception as e:
        errors.append({"theme_id": None, "stage": "list", "reason": f"page=1 파싱 오류: {e}"})
        return pd.DataFrame()

    for page in range(2, last_page + 1):
        try:
            html = fetch_theme_list_page(page)
            themes.extend(parse_theme_list(html)["themes"])
        except requests.RequestException as e:
            errors.append({"theme_id": None, "stage": "list", "reason": f"page={page} 네트워크 오류: {e}"})
        except Exception as e:
            errors.append({"theme_id": None, "stage": "list", "reason": f"page={page} 파싱 오류: {e}"})

    df = pd.DataFrame(themes)
    if not df.empty:
        df["collected_at"] = _now_kst()
    return df


def _collect_theme_details(strong_df: pd.DataFrame, errors: list[dict]) -> pd.DataFrame:
    # REQ-NT-006, REQ-NT-NF-003: 테마별 상세 수집; 부분 실패 허용
    rows: list[dict] = []
    for _, theme in strong_df.iterrows():
        theme_id = int(theme["theme_id"])
        try:
            html = fetch_theme_detail_page(theme_id)
            rows.extend(parse_theme_detail(html, theme_id, str(theme["theme_name"])))
        except requests.RequestException as e:
            errors.append({"theme_id": theme_id, "stage": "detail", "reason": f"네트워크 오류: {e}"})
        except Exception as e:
            errors.append({"theme_id": theme_id, "stage": "detail", "reason": str(e)})

    df = pd.DataFrame(rows)
    if not df.empty:
        df["collected_at"] = _now_kst()
    return df


def collect_and_analyze(
    top_n_themes: int = DEFAULT_TOP_N_THEMES,
    leaders_per_theme: int = DEFAULT_LEADERS_PER_THEME,
    skip_details: bool = False,
    theme_filter: list[str] | None = None,
) -> ThemeAnalysisResult:
    # REQ-NT-001: 단일 진입점 — DAILY_DB_PATH는 내부에서만 사용 (공개 파라미터 아님)
    start = time.time()
    errors: list[dict] = []

    themes_df = _collect_theme_list(errors)

    # REQ-NT-001: theme_filter 파라미터 지원
    if theme_filter and not themes_df.empty:
        themes_df = themes_df[themes_df["theme_name"].isin(theme_filter)].reset_index(drop=True)

    strong_df = (
        build_strong_themes(themes_df, top_n_themes) if not themes_df.empty else pd.DataFrame()
    )

    if skip_details or strong_df.empty:
        stocks_df: pd.DataFrame = pd.DataFrame()
        leaders_df: pd.DataFrame = pd.DataFrame()
        multi_df: pd.DataFrame = pd.DataFrame()
    else:
        stocks_df = _collect_theme_details(strong_df, errors)
        if not stocks_df.empty:
            # REQ-NT-007: read-only DB JOIN으로 market_cap 보강
            stocks_df = enrich_market_cap(stocks_df, DAILY_DB_PATH)
            leaders_df = build_leaders(stocks_df, leaders_per_theme)
            multi_df = build_multi_theme_stocks(stocks_df)
        else:
            leaders_df = pd.DataFrame()
            multi_df = pd.DataFrame()

    elapsed = round(time.time() - start, 2)

    return ThemeAnalysisResult(
        themes_df=themes_df,
        stocks_df=stocks_df,
        strong_themes_df=strong_df,
        leaders_df=leaders_df,
        multi_theme_stocks_df=multi_df,
        metadata={
            "collected_at": _now_kst(),
            "theme_count": int(len(themes_df)),
            "stock_count": int(len(stocks_df) if not stocks_df.empty else 0),
            "elapsed_sec": elapsed,
            "errors": errors,
        },
    )
