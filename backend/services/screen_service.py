"""Screen service: parameterized SQL filter against the stock_meta table."""

from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict

from backend.deps import get_db_conn
from backend.schemas.screen import (
    ScreenRequest,
    ScreenResponse,
    SectorGroup,
    StockItem,
)

logger = logging.getLogger(__name__)

# Maps Pydantic Literal indicator names to actual stock_meta column names.
# Column names are hardcoded here (not from user input) to prevent SQL injection.
# Open/High/Low map to close since stock_meta uses only close for daily price.
_INDICATOR_COLUMN: dict[str, str] = {
    "Close": "close",
    "Open": "close",
    "High": "close",
    "Low": "close",
    "EMA10": "ema10",
    "EMA20": "ema20",
    "SMA50": "sma50",
    "SMA100": "sma100",
    "SMA200": "sma200",
}

_OPERATOR_SQL: dict[str, str] = {
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}


def _build_where(req: ScreenRequest) -> tuple[str, list[object]]:
    """Build a parameterized SQL WHERE clause from ScreenRequest.

    Returns (where_sql, params) where params are bound positionally.
    Column names are ONLY sourced from _INDICATOR_COLUMN (server-side whitelist),
    never from user input directly.
    """
    conditions: list[str] = []
    params: list[object] = []

    if req.market_cap_min is not None:
        conditions.append("market_cap >= ?")
        params.append(req.market_cap_min)

    if req.chg_1d_min is not None:
        conditions.append("change_1d >= ?")
        params.append(req.chg_1d_min)

    # chg_1w/1m/3m are stored as decimals (0.30 = 30%) from pct_change(),
    # while the UI sends percentage values (30 = 30%), so divide by 100.
    if req.chg_1w_min is not None:
        conditions.append("chg_1w >= ?")
        params.append(req.chg_1w_min / 100)

    if req.chg_1m_min is not None:
        conditions.append("chg_1m >= ?")
        params.append(req.chg_1m_min / 100)

    if req.chg_3m_min is not None:
        conditions.append("chg_3m >= ?")
        params.append(req.chg_3m_min / 100)

    if req.rs_min is not None:
        conditions.append("rs_12m >= ?")
        params.append(req.rs_min)

    if req.markets:
        placeholders = ",".join("?" * len(req.markets))
        conditions.append(f"market IN ({placeholders})")
        params.extend(req.markets)

    if req.sectors:
        placeholders = ",".join("?" * len(req.sectors))
        conditions.append(f"sector_major IN ({placeholders})")
        params.extend(req.sectors)

    if req.codes:
        placeholders = ",".join("?" * len(req.codes))
        conditions.append(f"code IN ({placeholders})")
        params.extend(req.codes)

    # Pattern conditions: column names sourced exclusively from _INDICATOR_COLUMN
    pattern_clauses: list[str] = []
    for pat in req.patterns:
        col_a = _INDICATOR_COLUMN[pat.indicator_a]  # validated by Literal + dict lookup
        col_b = _INDICATOR_COLUMN[pat.indicator_b]
        op = _OPERATOR_SQL[pat.operator]             # validated by Literal + dict lookup
        pattern_clauses.append(f"{col_a} {op} {col_b} * ?")
        params.append(pat.multiplier)

    if pattern_clauses:
        joiner = " AND " if req.pattern_logic == "AND" else " OR "
        conditions.append(f"({joiner.join(pattern_clauses)})")

    where_sql = " AND ".join(conditions) if conditions else "1=1"
    return where_sql, params


def screen_stocks(req: ScreenRequest, daily_db_path: str) -> ScreenResponse:
    """Execute the screen filter against stock_meta and return sector-grouped results.

    Returns ScreenResponse with total=0 and empty sectors when nothing matches.
    Raises sqlite3.OperationalError (-> caught by router as 503) if stock_meta is missing.
    """
    where_sql, params = _build_where(req)
    query = f"""
        SELECT code, name, market, market_cap, sector_major, sector_minor, product,
               close, change_1d, rs_12m, ema10, ema20, sma50, sma100, sma200
        FROM stock_meta
        WHERE {where_sql}
        ORDER BY sector_major, sector_minor, market_cap DESC
    """

    conn = get_db_conn(daily_db_path)
    try:
        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    # Group by "sector_major > sector_minor"
    sector_map: dict[str, list[StockItem]] = defaultdict(list)
    for row in rows:
        code, name, market, market_cap, sector_major, sector_minor, product, close, chg1d, rs12m, e10, e20, s50, s100, s200 = row
        item = StockItem(
            code=code,
            name=name,
            market=market or "",
            market_cap=market_cap,
            sector_major=sector_major,
            sector_minor=sector_minor,
            product=product,
            close=close,
            change_1d=chg1d,
            rs_12m=rs12m,
            ema10=e10,
            ema20=e20,
            sma50=s50,
            sma100=s100,
            sma200=s200,
        )
        major = sector_major or "기타"
        minor = sector_minor or ""
        bucket = f"{major} > {minor}" if minor else major
        sector_map[bucket].append(item)

    sectors: list[SectorGroup] = [
        SectorGroup(sector_name=sector, stock_count=len(stocks), stocks=stocks)
        for sector, stocks in sorted(sector_map.items())
    ]

    return ScreenResponse(total=len(rows), sectors=sectors)
