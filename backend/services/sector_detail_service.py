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

# Maximum number of top stocks to return per sector
_TOP_STOCKS_LIMIT = 5


def _connect(db_path: str) -> sqlite3.Connection:
    """Open a SQLite connection. Replaceable in tests."""
    return sqlite3.connect(db_path, check_same_thread=False)


def get_sector_detail(daily_db_path: str, sector_name: str) -> SectorDetailResponse:
    """Compute sub-sector breakdown and top stocks for a major sector.

    Reads stock_meta from the daily DB to get sector_minor groupings,
    RS scores, and stock identifiers. Stage data is optional and will be
    null when not available.

    Args:
        daily_db_path: Path to the daily SQLite database containing stock_meta.
        sector_name: The 산업명(대) sector name to query.

    Returns:
        SectorDetailResponse with sub_sectors and top_stocks.
    """
    conn = _connect(daily_db_path)
    try:
        rows = conn.execute(
            """
            SELECT code, name, sector_minor, rs_12m
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

    # Group by sub-sector (sector_minor)
    sub_sector_stocks: dict[str, list[dict]] = defaultdict(list)
    for code, name, sector_minor, rs_12m in rows:
        key = sector_minor or "기타"
        sub_sector_stocks[key].append({"code": code, "name": name, "rs_12m": rs_12m or 0.0})

    sub_sectors = [
        SubSectorItem(
            name=sub_name,
            stock_count=len(stocks),
            # Stage counts are 0 for now (stage data not in daily DB)
            # @MX:TODO: Enrich stage counts from weekly DB classify_all results
            stage1_count=0,
            stage2_count=0,
            stage3_count=0,
            stage4_count=0,
        )
        for sub_name, stocks in sorted(sub_sector_stocks.items())
    ]

    # Top stocks: already sorted by rs_12m DESC, take first N
    top_stocks = [
        TopStockItem(
            code=code,
            name=name,
            rs_12m=round(rs_12m or 0.0, 2),
            stage=None,  # Stage enrichment requires weekly DB; frontend merges via stageMap
        )
        for code, name, _sector_minor, rs_12m in rows[:_TOP_STOCKS_LIMIT]
    ]

    return SectorDetailResponse(
        sector_name=sector_name,
        sub_sectors=sub_sectors,
        top_stocks=top_stocks,
    )
