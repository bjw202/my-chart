"""Sector ranking service: wraps sector_metrics for API response."""

from __future__ import annotations

import logging
import sqlite3

from my_chart.analysis.sector_metrics import compute_sector_ranking
from backend.schemas.sector import (
    SectorExcessReturns,
    SectorRankItem,
    SectorRankingResponse,
    SectorReturns,
)

logger = logging.getLogger(__name__)


def _get_latest_date(db_path: str) -> str | None:
    """Get the latest date in the weekly DB."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        row = conn.execute(
            "SELECT MAX(Date) FROM stock_prices WHERE Name NOT IN ('KOSPI', 'KOSDAQ')"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def get_sector_ranking(weekly_db_path: str) -> SectorRankingResponse:
    """Compute sector rankings and return API response.

    Args:
        weekly_db_path: Full path to weekly SQLite database file.

    Returns:
        SectorRankingResponse with sectors ordered by rank.
    """
    date = _get_latest_date(weekly_db_path)
    if not date:
        logger.warning("No date found in weekly DB: %s", weekly_db_path)
        return SectorRankingResponse(date="", sectors=[])

    rankings = compute_sector_ranking(weekly_db_path, date)

    sector_items = [
        SectorRankItem(
            name=r.name,
            stock_count=r.stock_count,
            returns=SectorReturns(
                w1=round(r.sector_return_1w, 4),
                m1=round(r.sector_return_1m, 4),
                m3=round(r.sector_return_3m, 4),
            ),
            excess_returns=SectorExcessReturns(
                w1=round(r.sector_excess_return_1w, 4),
                m1=round(r.sector_excess_return_1m, 4),
                m3=round(r.sector_excess_return_3m, 4),
            ),
            rs_avg=r.sector_rs_avg,
            rs_top_pct=r.sector_rs_top_pct,
            nh_pct=r.sector_nh_pct,
            stage2_pct=r.sector_stage2_pct,
            composite_score=r.composite_score,
            rank=r.rank,
            rank_change=r.rank_change,
        )
        for r in rankings
    ]

    return SectorRankingResponse(date=date, sectors=sector_items)
