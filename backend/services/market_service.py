"""Market overview service: aggregates breadth, cycle, and index data."""

from __future__ import annotations

import sqlite3
import logging

from my_chart.analysis.market_breadth import (
    BreadthResult,
    compute_breadth,
    compute_breadth_composite,
    compute_breadth_history,
    detect_choppy,
    determine_cycle,
)
from backend.schemas.market import (
    BreadthData,
    BreadthHistoryItem,
    CriterionItem,
    CycleData,
    IndexData,
    MarketBreadth,
    MarketOverviewResponse,
)

logger = logging.getLogger(__name__)

# Index names tracked by name
_INDEX_NAMES = frozenset({"KOSPI", "KOSDAQ"})


def _get_latest_date(db_path: str) -> str | None:
    """Get the latest date in the weekly DB (excluding index stocks)."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        row = conn.execute(
            "SELECT MAX(Date) FROM stock_prices WHERE Name NOT IN ('KOSPI', 'KOSDAQ')"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _load_index_data(db_path: str, index_name: str, date: str) -> IndexData:
    """Load index (KOSPI/KOSDAQ) price and MA data from weekly DB."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        row = conn.execute(
            """SELECT Close, SMA10, SMA40, SMA40_Trend_4M, CHG_1W
               FROM stock_prices
               WHERE Name = ? AND Date = ?""",
            (index_name, date),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return IndexData()

    close = float(row[0] or 0.0)
    sma50 = float(row[1] or 0.0)   # SMA10 ≈ 50-day proxy
    sma200 = float(row[2] or 0.0)  # SMA40 ≈ 200-day proxy
    sma40_prev = float(row[3] or 0.0)
    chg_1w = float(row[4] or 0.0)

    # Slope: (current - 4w_ago) / 4w_ago
    sma50_slope = (sma50 - sma40_prev) / sma40_prev if sma40_prev > 0 else 0.0
    sma200_slope = (sma200 - sma40_prev) / sma40_prev if sma40_prev > 0 else 0.0

    return IndexData(
        close=close,
        chg_1w=chg_1w * 100,  # decimal → %
        sma50=sma50,
        sma200=sma200,
        sma50_slope=round(sma50_slope, 4),
        sma200_slope=round(sma200_slope, 4),
    )


def _breadth_to_schema(breadth: BreadthResult) -> BreadthData:
    """Convert BreadthResult to Pydantic schema."""
    return BreadthData(
        pct_above_sma50=round(breadth.pct_above_sma50, 2),
        pct_above_sma200=round(breadth.pct_above_sma200, 2),
        nh_nl_ratio=round(breadth.nh_nl_ratio, 4),
        nh_nl_diff=breadth.nh_nl_diff,
        ad_ratio=round(breadth.ad_ratio, 4),
        breadth_score=round(breadth.breadth_score, 2),
    )


def _breadth_to_history_item(breadth: BreadthResult) -> BreadthHistoryItem:
    """Convert BreadthResult to history schema item."""
    return BreadthHistoryItem(
        date=breadth.date,
        pct_above_sma50=round(breadth.pct_above_sma50, 2),
        pct_above_sma200=round(breadth.pct_above_sma200, 2),
        nh_nl_ratio=round(breadth.nh_nl_ratio, 4),
        nh_nl_diff=breadth.nh_nl_diff,
        ad_ratio=round(breadth.ad_ratio, 4),
        breadth_score=round(breadth.breadth_score, 2),
    )


def get_market_overview(weekly_db_path: str) -> MarketOverviewResponse:
    """Compute and return full market overview response.

    Args:
        weekly_db_path: Full path to weekly SQLite database file.

    Returns:
        MarketOverviewResponse with all breadth, cycle, and index data.
    """
    date = _get_latest_date(weekly_db_path)
    if not date:
        logger.warning("No date found in weekly DB: %s", weekly_db_path)
        date = "2024-01-01"

    # Load index data
    kospi_index = _load_index_data(weekly_db_path, "KOSPI", date)

    # Compute breadth for KOSPI
    kospi_breadth = compute_breadth(weekly_db_path, "KOSPI", date)
    kospi_breadth.breadth_score = compute_breadth_composite(kospi_breadth)

    # Build KOSPI data dict for cycle determination
    kospi_data = {
        "close": kospi_index.close or 0.0,
        "sma50": kospi_index.sma50 or 0.0,
        "sma200": kospi_index.sma200 or 0.0,
        "sma50_slope": kospi_index.sma50_slope or 0.0,
    }

    # Determine cycle
    cycle_result = determine_cycle(kospi_breadth, kospi_data)

    # Compute breadth history (12 weeks)
    history = compute_breadth_history(weekly_db_path, "KOSPI", weeks=12)
    for h in history:
        h.breadth_score = compute_breadth_composite(h)

    # Detect choppy using history
    kospi_history_data = {
        "sma20": kospi_index.sma50 or 0.0,  # approximate sma20 with sma50
        "sma50": kospi_index.sma50 or 0.0,
        "sma200": kospi_index.sma200 or 0.0,
        "weekly_returns": [h.ad_ratio - 1.0 for h in history[-8:]],  # proxy for weekly returns
    }
    choppy = detect_choppy(history, kospi_history_data) if len(history) >= 4 else False
    cycle_result.choppy = choppy

    # Build criteria list for response
    criteria_items = [
        CriterionItem(
            name=c.name,
            value=round(c.value, 4),
            direction=c.direction,
        )
        for c in cycle_result.criteria
    ]

    # 섹터 전환 감지 (non-critical — 실패 시 None 반환)
    try:
        from my_chart.analysis.sector_advanced import detect_sector_transitions
        from backend.schemas.market import SectorAlertItem, SectorAlertsData

        alerts = detect_sector_transitions(weekly_db_path)
        sector_alerts: SectorAlertsData | None = SectorAlertsData(
            emerging_leaders=[
                SectorAlertItem(name=a.name, signals=a.signals)
                for a in alerts.emerging_leaders
            ],
            weakening_sectors=[
                SectorAlertItem(name=a.name, signals=a.signals)
                for a in alerts.weakening_sectors
            ],
        )
    except Exception:
        logger.warning("섹터 전환 감지 실패", exc_info=True)
        sector_alerts = None

    return MarketOverviewResponse(
        kospi=kospi_index,
        breadth=MarketBreadth(
            kospi=_breadth_to_schema(kospi_breadth),
        ),
        cycle=CycleData(
            phase=cycle_result.phase,
            choppy=cycle_result.choppy,
            criteria=criteria_items,
            confidence=cycle_result.confidence,
        ),
        breadth_history=[_breadth_to_history_item(h) for h in history],
        sector_alerts=sector_alerts,
    )
