"""Sector detail service: sub-sector breakdown and top stocks for a given sector."""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict

from backend.schemas.sector import (
    SectorDetailResponse,
    SubSectorItem,
    TopStockItem,
)

logger = logging.getLogger(__name__)

# 섹터당 반환할 상위 종목 수
_TOP_STOCKS_LIMIT = 5


def _connect(db_path: str) -> sqlite3.Connection:
    """SQLite 연결 생성. 테스트에서 교체 가능."""
    return sqlite3.connect(db_path, check_same_thread=False)


def _classify_stage_simple(
    close: float | None,
    sma50: float | None,
    sma200: float | None,
) -> tuple[int | None, str | None]:
    """stock_meta 필드를 이용한 단순 스테이지 분류.

    weekly DB 없이 일간 DB 데이터만으로 스테이지를 근사 계산한다.
    주요 기준:
      - Stage 2: close > sma50 > sma200 (강한 상승)
      - Stage 2 Early: close > sma200 (sma50 조건 미충족)
      - Stage 4: close < sma50 and close < sma200 (하락)
      - Stage 3: 그 외 (천장권)
    """
    if close is None or sma50 is None or sma200 is None:
        return None, None

    if close < sma50 and close < sma200:
        return 4, "Stage 4"
    elif close > sma50 and close > sma200 and sma50 > sma200:
        return 2, "Stage 2"
    elif close > sma200:
        return 2, "Stage 2 Early"
    else:
        return 3, "Stage 3"


def get_sector_detail(daily_db_path: str, sector_name: str) -> SectorDetailResponse:
    """대분류 섹터의 소그룹 분석 및 상위 종목을 반환한다.

    stock_meta 테이블에서 sector_minor 그룹화, RS 점수, 가격 데이터를 읽어
    소그룹별 평균 RS, Stage 2 비율을 계산하고 상위 종목에 chg_1m, stage_detail을 추가한다.

    Args:
        daily_db_path: stock_meta 테이블이 있는 일간 SQLite DB 경로.
        sector_name: 조회할 대분류 섹터명 (산업명(대)).

    Returns:
        SectorDetailResponse with sub_sectors and top_stocks.
    """
    conn = _connect(daily_db_path)
    try:
        rows = conn.execute(
            """
            SELECT code, name, sector_minor, rs_12m, close, sma50, sma200, chg_1m
            FROM stock_meta
            WHERE sector_major = ?
              AND code IS NOT NULL
              AND name IS NOT NULL
            ORDER BY rs_12m DESC NULLS LAST
            """,
            (sector_name,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return SectorDetailResponse(
            sector_name=sector_name,
            sub_sectors=[],
            top_stocks=[],
        )

    # 소그룹별 종목 그룹화
    # 각 종목: dict with code, name, rs_12m, close, sma50, sma200, chg_1m
    sub_sector_stocks: dict[str, list[dict]] = defaultdict(list)
    for code, name, sector_minor, rs_12m, close, sma50, sma200, chg_1m in rows:
        key = sector_minor or "기타"
        sub_sector_stocks[key].append({
            "code": code,
            "name": name,
            "rs_12m": rs_12m or 0.0,
            "close": close,
            "sma50": sma50,
            "sma200": sma200,
            "chg_1m": chg_1m,
        })

    # 소그룹 아이템 생성 (rs_avg, stage2_pct 계산 포함)
    sub_sectors = []
    for sub_name, stocks in sorted(sub_sector_stocks.items()):
        count = len(stocks)

        # rs_avg: 소그룹 내 rs_12m 평균
        rs_avg = sum(s["rs_12m"] for s in stocks) / count if count > 0 else 0.0

        # stage2_pct: Stage 2 계열(stage=2) 종목 비율
        stage2_count = 0
        stage1_count = 0
        stage3_count = 0
        stage4_count = 0
        for s in stocks:
            stage, _ = _classify_stage_simple(s["close"], s["sma50"], s["sma200"])
            if stage == 2:
                stage2_count += 1
            elif stage == 1:
                stage1_count += 1
            elif stage == 3:
                stage3_count += 1
            elif stage == 4:
                stage4_count += 1

        stage2_pct = (stage2_count / count * 100.0) if count > 0 else 0.0

        sub_sectors.append(
            SubSectorItem(
                name=sub_name,
                stock_count=count,
                stage1_count=stage1_count,
                stage2_count=stage2_count,
                stage3_count=stage3_count,
                stage4_count=stage4_count,
                rs_avg=round(rs_avg, 2),
                stage2_pct=round(stage2_pct, 2),
            )
        )

    # 상위 종목: rs_12m DESC 정렬된 rows 상위 N개
    top_stocks = []
    for code, name, _sector_minor, rs_12m, close, sma50, sma200, chg_1m in rows[:_TOP_STOCKS_LIMIT]:
        stage, stage_detail = _classify_stage_simple(close, sma50, sma200)
        top_stocks.append(
            TopStockItem(
                code=code,
                name=name,
                rs_12m=round(rs_12m or 0.0, 2),
                stage=stage,
                chg_1m=chg_1m,
                stage_detail=stage_detail,
            )
        )

    return SectorDetailResponse(
        sector_name=sector_name,
        sub_sectors=sub_sectors,
        top_stocks=top_stocks,
    )
