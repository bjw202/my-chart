import time
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
import pytz
import pandas as pd
import re

from backend.services.naver_theme.config import (
    DEFAULT_TOP_N_THEMES,
    DEFAULT_LEADERS_PER_THEME,
)
from backend.services.naver_theme.crawler import (
    fetch_theme_list_page,
    fetch_theme_detail_page,
)
from backend.services.naver_theme.parser import (
    parse_theme_list,
    parse_theme_detail,
)
from backend.services.naver_theme.analyzer import (
    build_strong_themes,
    build_leaders,
    build_multi_theme_stocks,
)


@dataclass
class ThemeAnalysisResult:
    """테마 분석 결과."""
    themes_df: pd.DataFrame
    stocks_df: pd.DataFrame
    strong_themes_df: pd.DataFrame
    leaders_df: pd.DataFrame
    multi_theme_stocks_df: pd.DataFrame
    metadata: dict = field(default_factory=dict)


def _fetch_all_theme_pages(top_n: int | None = None) -> pd.DataFrame:
    """모든 테마 목록 페이지 크롤링 및 파싱.

    @param top_n: 최대 조회할 테마 수 (기본값: 무제한)
    @return: 테마 DataFrame
    """
    all_themes = []
    page = 1

    while True:
        try:
            html = fetch_theme_list_page(page)
            themes_df = parse_theme_list(html)

            if len(themes_df) == 0:
                break

            all_themes.append(themes_df)

            if top_n and len(pd.concat(all_themes)) >= top_n:
                break

            page += 1
        except Exception:
            break

    if not all_themes:
        return pd.DataFrame()

    result = pd.concat(all_themes, ignore_index=True)

    if top_n:
        result = result.head(top_n)

    return result


def _fetch_all_theme_details(theme_ids: list[int]) -> pd.DataFrame:
    """테마별 종목 상세 정보 크롤링 및 파싱.

    @param theme_ids: 테마 ID 리스트
    @return: 종목 DataFrame
    """
    all_stocks = []

    for theme_id in theme_ids:
        try:
            html = fetch_theme_detail_page(theme_id)
            stocks_list = parse_theme_detail(html, theme_id)
            if stocks_list:
                all_stocks.extend(stocks_list)
        except Exception:
            continue

    if not all_stocks:
        return pd.DataFrame()

    return pd.DataFrame(all_stocks)


def _enrich_with_market_cap(stocks_df: pd.DataFrame, db_path: str) -> pd.DataFrame:
    """시가총액 및 거래대금 정보로 종목 DataFrame 보강.

    @param stocks_df: 종목 DataFrame
    @param db_path: SQLite 데이터베이스 경로
    @return: 보강된 DataFrame
    """
    if stocks_df.empty:
        return stocks_df

    result = stocks_df.copy()

    try:
        conn = sqlite3.connect(db_path)
        codes = result["stock_code"].unique().tolist()

        # 시가총액, 거래대금 조회
        if codes:
            placeholders = ",".join("?" * len(codes))
            query = f"SELECT code, market_cap FROM stock_meta WHERE code IN ({placeholders})"
            market_cap_df = pd.read_sql(query, conn, params=codes)

            # 병합
            if not market_cap_df.empty:
                market_cap_df.columns = ["stock_code", "market_cap"]
                result = result.merge(market_cap_df, on="stock_code", how="left")
            else:
                result["market_cap"] = None

        conn.close()
    except Exception:
        result["market_cap"] = None

    # trade_value는 volume 추정으로 계산 (정확한 값은 추가 크롤링 필요)
    if "volume" in result.columns and result["volume"].notna().any():
        result["trade_value"] = result["volume"] * 1000  # 임시 추정값
    else:
        result["trade_value"] = None

    return result


def collect_and_analyze(
    top_n_themes: int | None = None,
    leaders_per_theme: int | None = None,
    skip_details: bool = False,
    db_path: str = "/Users/byunjungwon/Dev/my-project-01/my_chart/Output/stock_data_daily.db",
) -> ThemeAnalysisResult:
    """테마 분석 메인 진입점.

    @param top_n_themes: 조회할 테마 수 (기본값: 20)
    @param leaders_per_theme: 테마당 리더 스톡 수 (기본값: 3)
    @param skip_details: True시 상세 크롤링 스킵 (기본값: False)
    @param db_path: SQLite 데이터베이스 경로
    @return: ThemeAnalysisResult
    """
    if top_n_themes is None:
        top_n_themes = DEFAULT_TOP_N_THEMES
    if leaders_per_theme is None:
        leaders_per_theme = DEFAULT_LEADERS_PER_THEME

    start_time = time.time()
    errors = []

    try:
        # 1. 테마 목록 수집
        themes_df = _fetch_all_theme_pages(top_n_themes)

        if themes_df.empty:
            raise ValueError("테마 목록을 수집할 수 없습니다")

        # 2. 종목 정보 수집
        if skip_details:
            stocks_df = pd.DataFrame()
        else:
            theme_ids = themes_df["theme_id"].tolist()
            stocks_df = _fetch_all_theme_details(theme_ids)

            # 3. 시가총액 및 거래대금 보강
            stocks_df = _enrich_with_market_cap(stocks_df, db_path)

        # 4. 강세 테마 추출
        strong_themes_df = build_strong_themes(themes_df)

        # 5. 리더 스톡 추출
        leaders_df = pd.DataFrame()
        if not stocks_df.empty:
            leaders_df = build_leaders(stocks_df, leaders_per_theme)

        # 6. 멀티 테마 종목 추출
        multi_theme_stocks_df = pd.DataFrame()
        if not stocks_df.empty:
            multi_theme_stocks_df = build_multi_theme_stocks(stocks_df)

    except Exception as e:
        errors.append(str(e))
        themes_df = pd.DataFrame()
        stocks_df = pd.DataFrame()
        strong_themes_df = pd.DataFrame()
        leaders_df = pd.DataFrame()
        multi_theme_stocks_df = pd.DataFrame()

    elapsed_sec = time.time() - start_time

    # Metadata 구성
    metadata = {
        "collected_at": datetime.now(pytz.timezone("Asia/Seoul")).isoformat(),
        "theme_count": len(themes_df),
        "stock_count": len(stocks_df),
        "elapsed_sec": round(elapsed_sec, 2),
        "errors": errors,
    }

    return ThemeAnalysisResult(
        themes_df=themes_df,
        stocks_df=stocks_df,
        strong_themes_df=strong_themes_df,
        leaders_df=leaders_df,
        multi_theme_stocks_df=multi_theme_stocks_df,
        metadata=metadata,
    )
