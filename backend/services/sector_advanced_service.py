"""SPEC-TOPDOWN-002A 고급 섹터 분석 서비스 레이어.

sector_advanced.py 계산 함수를 API 응답 형식으로 변환한다.
"""

from __future__ import annotations

import logging
import sqlite3

from my_chart.analysis.sector_advanced import (
    compute_rrg_data,
    compute_sector_bubble,
    compute_stock_bubble,
    compute_treemap_data,
)
from my_chart.analysis.weekly_grid import _get_latest_valid_date
from backend.schemas.sector_advanced import (
    RRGResponse,
    RRGSectorItem,
    RRGTrailPoint,
    SectorBubbleItem,
    SectorBubbleResponse,
    SectorHistoryItem,
    SectorHistoryResponse,
    SectorHistoryWeek,
    StockBubbleItem,
    StockBubbleResponse,
    TreemapResponse,
    TreemapSectorNode,
    TreemapStockNode,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 섹터 버블 서비스
# ---------------------------------------------------------------------------

def get_sector_bubble(
    weekly_db_path: str,
    period: str = "1w",
    market: str | None = None,
) -> SectorBubbleResponse:
    """섹터 버블 차트 API 응답을 반환한다.

    Args:
        weekly_db_path: weekly SQLite DB 경로
        period: 수익률 기간 ("1w", "1m", "3m")
        market: 시장 필터 (None=전체, "KOSPI", "KOSDAQ")

    Returns:
        SectorBubbleResponse
    """
    date = _get_latest_valid_date(weekly_db_path) or ""
    bubbles = compute_sector_bubble(weekly_db_path, period=period, market=market)

    items = [
        SectorBubbleItem(
            name=b.name,
            excess_return=b.excess_return,
            rs_avg=b.rs_avg,
            trading_value=b.trading_value,
            period_return=b.period_return,
        )
        for b in bubbles
    ]

    return SectorBubbleResponse(
        date=date,
        period=period,
        market=market,
        sectors=items,
    )


# ---------------------------------------------------------------------------
# 종목 버블 서비스
# ---------------------------------------------------------------------------

def get_stock_bubble(
    weekly_db_path: str,
    sector_name: str,
    period: str = "1w",
) -> StockBubbleResponse:
    """섹터 내 종목 버블 차트 API 응답을 반환한다.

    Args:
        weekly_db_path: weekly SQLite DB 경로
        sector_name: 조회할 섹터명
        period: 수익률 기간 ("1w", "1m", "3m")

    Returns:
        StockBubbleResponse
    """
    date = _get_latest_valid_date(weekly_db_path) or ""
    stocks = compute_stock_bubble(weekly_db_path, sector_name=sector_name, period=period)

    items = [
        StockBubbleItem(
            name=s.name,
            price_change=s.price_change,
            rs_12m=s.rs_12m,
            trading_value=s.trading_value,
            stage=s.stage,
            stage_detail=s.stage_detail,
            market_cap=s.market_cap,
            volume_ratio=s.volume_ratio,
            sector_minor=s.sector_minor,  # SPEC-SECTOR-MINOR-COLOR-001
            product=s.product,            # SPEC-STOCK-TOOLTIP-PRODUCT-001
        )
        for s in stocks
    ]

    return StockBubbleResponse(
        date=date,
        sector_name=sector_name,
        period=period,
        stocks=items,
    )


# ---------------------------------------------------------------------------
# RRG 서비스
# ---------------------------------------------------------------------------

def get_rrg_data(weekly_db_path: str) -> RRGResponse:
    """RRG(Relative Rotation Graph) API 응답을 반환한다.

    Args:
        weekly_db_path: weekly SQLite DB 경로

    Returns:
        RRGResponse
    """
    date = _get_latest_valid_date(weekly_db_path) or ""
    sectors = compute_rrg_data(weekly_db_path)

    items = [
        RRGSectorItem(
            name=s.name,
            rs_ratio=s.rs_ratio,
            rs_momentum=s.rs_momentum,
            quadrant=s.quadrant,
            trail=[
                RRGTrailPoint(
                    date=t["date"],
                    rs_ratio=t["rs_ratio"],
                    rs_momentum=t["rs_momentum"],
                )
                for t in s.trail
            ],
        )
        for s in sectors
    ]

    # KOSPI 종가 시계열 (트레일 기간과 동일)
    from backend.schemas.sector_advanced import KospiPoint
    kospi_points: list[KospiPoint] = []
    try:
        conn = sqlite3.connect(weekly_db_path, check_same_thread=False)
        rows = conn.execute(
            """SELECT Date, Close FROM stock_prices
               WHERE Name = 'KOSPI'
               ORDER BY Date ASC"""
        ).fetchall()
        conn.close()
        kospi_points = [KospiPoint(date=r[0], close=float(r[1] or 0)) for r in rows if r[1]]
    except Exception:
        pass

    return RRGResponse(date=date, sectors=items, kospi=kospi_points)


# ---------------------------------------------------------------------------
# 섹터 히스토리 서비스
# ---------------------------------------------------------------------------

def get_sector_history(weekly_db_path: str, weeks: int = 12) -> SectorHistoryResponse:
    """N주 섹터 랭킹 히스토리 API 응답을 반환한다.

    compute_sector_history()가 부분 데이터 날짜를 제외한 정제된
    (dates, rankings)를 반환하면, 이를 섹터별 시계열로 재구성한다.
    날짜를 별도 재조회하지 않고 compute_sector_history가 반환한 dates를
    그대로 사용하여 단일 진실 공급원(SSOT)을 보장한다.

    Args:
        weekly_db_path: weekly SQLite DB 경로
        weeks: 조회 주수 (기본 12주)

    Returns:
        SectorHistoryResponse
    """
    from my_chart.analysis.sector_metrics import compute_sector_history

    # SSOT: 부분 데이터 날짜가 제외된 (dates, rankings) 튜플
    dates, history_by_week = compute_sector_history(weekly_db_path, weeks=weeks)

    if not history_by_week:
        return SectorHistoryResponse(weeks=weeks, sectors=[])

    # 섹터별 히스토리 데이터 수집
    sector_history: dict[str, list[SectorHistoryWeek]] = {}

    # dates와 history_by_week는 같은 길이·같은 순서 (SSOT 보장)
    for date, week_rankings in zip(dates, history_by_week):
        if not week_rankings:
            continue
        for rank_item in week_rankings:
            name = rank_item.name
            if name not in sector_history:
                sector_history[name] = []
            sector_history[name].append(SectorHistoryWeek(
                date=date,
                rank=rank_item.rank,
                composite_score=rank_item.composite_score,
                sector_return_1w=rank_item.sector_return_1w,
                sector_excess_return_1w=rank_item.sector_excess_return_1w,
                rs_avg=rank_item.sector_rs_avg,
            ))

    sector_items = [
        SectorHistoryItem(name=name, history=history)
        for name, history in sector_history.items()
        if history
    ]

    return SectorHistoryResponse(weeks=weeks, sectors=sector_items)


# ---------------------------------------------------------------------------
# 트리맵 서비스
# ---------------------------------------------------------------------------

def get_treemap_data(weekly_db_path: str, period: str = "1w") -> TreemapResponse:
    """트리맵 API 응답을 반환한다.

    Args:
        weekly_db_path: weekly SQLite DB 경로
        period: 수익률 기간 ("1w", "1m", "3m")

    Returns:
        TreemapResponse
    """
    date = _get_latest_valid_date(weekly_db_path) or ""
    root = compute_treemap_data(weekly_db_path, period=period)

    sector_nodes: list[TreemapSectorNode] = []
    for sector_child in root.children:
        stock_nodes = [
            TreemapStockNode(
                name=s.name,
                market_cap=s.market_cap,
                price_change=s.price_change,
                rs_12m=s.rs_12m,
                stage=s.stage,
            )
            for s in sector_child.children
        ]
        sector_nodes.append(TreemapSectorNode(
            name=sector_child.name,
            market_cap=sector_child.market_cap,
            price_change=sector_child.price_change,
            stocks=stock_nodes,
        ))

    return TreemapResponse(
        date=date,
        period=period,
        total_market_cap=root.market_cap,
        sectors=sector_nodes,
    )
