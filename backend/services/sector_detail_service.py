"""Sector detail service: sub-sector breakdown and top stocks for a given sector."""

from __future__ import annotations

import sqlite3
from collections import defaultdict

from backend.schemas.sector import (
    SectorDetailResponse,
    SubSectorItem,
    TopStockItem,
)
from my_chart.analysis.stage_classifier import (
    _load_stocks_for_classification,
    classify_stage_or_none,
)
from my_chart.analysis.weekly_grid import _get_latest_valid_date, compute_weekly_grid

# 섹터당 반환할 상위 종목 수
_TOP_STOCKS_LIMIT = 5


def _connect(db_path: str) -> sqlite3.Connection:
    """SQLite 연결 생성. 테스트에서 교체 가능."""
    return sqlite3.connect(db_path, check_same_thread=False)


# @MX:NOTE: [AUTO] REQ-SAG-023 — 폐기된 일봉 근사 분류기를 주봉 Weinstein
#   분류기(`stage_classifier.classify_stage`) 로 단일화한다(AC-SAG-025).
#   `SMA40`/`SMA10` 결측 종목은 `classify_stage_or_none()` 이 분류 불가로
#   판정해 (None, None) 을 돌려준다(AC-SAG-026).
def _load_weekly_classification(
    weekly_db_path: str,
) -> dict[str, tuple[int | None, str | None]]:
    """종목명 → ``(stage 번호, 상세 설명)`` — 최신 정규 주간 격자 바 기준(주봉 Weinstein)."""
    grid = compute_weekly_grid(weekly_db_path)
    if grid.latest is None:
        return {}
    conn = _connect(weekly_db_path)
    try:
        stocks = _load_stocks_for_classification(conn, grid.latest.date)
    finally:
        conn.close()
    return {s["Name"]: classify_stage_or_none(s) for s in stocks}


def get_sector_detail(
    daily_db_path: str, sector_name: str, weekly_db_path: str | None = None,
    market: str = "all",
) -> SectorDetailResponse:
    """대분류 섹터의 소그룹 분석 및 상위 종목을 반환한다.

    stock_meta 테이블에서 sector_minor 그룹화, RS 점수, 가격 데이터를 읽고,
    stage 는 weekly DB 의 주봉 Weinstein 분류기(REQ-SAG-023)로 조회해
    소그룹별 평균 RS, Stage 2 비율을 계산하고 상위 종목에 chg_1m, stage_detail을 추가한다.

    Args:
        daily_db_path: stock_meta 테이블이 있는 일간 SQLite DB 경로.
        sector_name: 조회할 대분류 섹터명 (산업명(대)).
        weekly_db_path: 주봉 Weinstein stage 분류에 쓰는 weekly SQLite DB 경로.
            ``None`` 이면 stage 조회 없이(전 종목 분류 불가로) 진행한다.
        market: ``all`` / ``kospi`` / ``kosdaq`` — M6 신설(AC-SAG-039).
            ``stock_meta.market`` 컬럼(대문자 ``KOSPI``/``KOSDAQ``)으로 필터한다.

    Returns:
        SectorDetailResponse with sub_sectors and top_stocks.
    """
    stage_map = _load_weekly_classification(weekly_db_path) if weekly_db_path else {}
    market_key = (market or "all").lower()
    # AC-SAG-037(SN-3) — 다른 6개 엔드포인트와 동일한 공유 헬퍼로 as_of_date 를 고정한다.
    as_of_date = _get_latest_valid_date(weekly_db_path) if weekly_db_path else None

    conn = _connect(daily_db_path)
    try:
        if market_key in ("", "all"):
            rows = conn.execute(
                """
                SELECT code, name, sector_minor, rs_12m, chg_1m
                FROM stock_meta
                WHERE sector_major = ?
                  AND code IS NOT NULL
                  AND name IS NOT NULL
                ORDER BY rs_12m DESC NULLS LAST
                """,
                (sector_name,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT code, name, sector_minor, rs_12m, chg_1m
                FROM stock_meta
                WHERE sector_major = ?
                  AND code IS NOT NULL
                  AND name IS NOT NULL
                  AND UPPER(market) = ?
                ORDER BY rs_12m DESC NULLS LAST
                """,
                (sector_name, market_key.upper()),
            ).fetchall()
    finally:
        conn.close()

    if not rows:
        return SectorDetailResponse(
            sector_name=sector_name,
            sub_sectors=[],
            top_stocks=[],
            market_filter=market_key or "all",
            as_of_date=as_of_date,
        )

    # 소그룹별 종목 그룹화
    # 각 종목: dict with code, name, rs_12m, chg_1m
    sub_sector_stocks: dict[str, list[dict]] = defaultdict(list)
    for code, name, sector_minor, rs_12m, chg_1m in rows:
        key = sector_minor or "기타"
        sub_sector_stocks[key].append({
            "code": code,
            "name": name,
            "rs_12m": rs_12m or 0.0,
            "chg_1m": chg_1m,
        })

    # 소그룹 아이템 생성 (rs_avg, stage2_pct 계산 포함)
    sub_sectors = []
    for sub_name, stocks in sorted(sub_sector_stocks.items()):
        count = len(stocks)

        # rs_avg: 소그룹 내 rs_12m 평균
        rs_avg = sum(s["rs_12m"] for s in stocks) / count if count > 0 else 0.0

        # stage2_pct: Stage 2 계열(stage=2) 종목 비율. 분류 불가(AC-SAG-026) 종목은
        # 분모에서 제외한다 — 0 치환 금지.
        stage2_count = 0
        stage1_count = 0
        stage3_count = 0
        stage4_count = 0
        classified_count = 0
        for s in stocks:
            stage, _ = stage_map.get(s["name"], (None, None))
            if stage is None:
                continue
            classified_count += 1
            if stage == 2:
                stage2_count += 1
            elif stage == 1:
                stage1_count += 1
            elif stage == 3:
                stage3_count += 1
            elif stage == 4:
                stage4_count += 1

        stage2_pct = (
            (stage2_count / classified_count * 100.0) if classified_count > 0 else 0.0
        )

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
    for code, name, _sector_minor, rs_12m, chg_1m in rows[:_TOP_STOCKS_LIMIT]:
        stage, stage_detail = stage_map.get(name, (None, None))
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
        market_filter=market_key or "all",
        as_of_date=as_of_date,
    )
