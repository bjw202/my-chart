"""Chart service: fetch OHLCV + MA data from the daily DB for TradingView."""

from __future__ import annotations

import logging
import sqlite3

from backend.deps import get_db_conn
from backend.schemas.chart import CandleBar, ChartResponse, MAOverlays, MAPoint, VolumeBar

logger = logging.getLogger(__name__)


def get_chart_data(code: str, daily_db_path: str) -> ChartResponse:
    """Return TradingView-formatted chart data for the given stock code.

    Raises:
        LookupError: if the code is not found in stock_meta or has no price data.
    """
    conn = get_db_conn(daily_db_path)
    try:
        # Resolve company name from stock_meta (code is the 6-digit ticker)
        meta_row = conn.execute(
            "SELECT name FROM stock_meta WHERE code = ?", (code,)
        ).fetchone()
    except sqlite3.OperationalError:
        # stock_meta table doesn't exist yet (before first DB update)
        raise LookupError(f"stock_not_found:{code}")

    if not meta_row:
        raise LookupError(f"stock_not_found:{code}")

    name: str = meta_row[0]

    try:
        rows = conn.execute(
            """SELECT Date, Open, High, Low, Close, Volume,
                      EMA10, EMA20, SMA50, SMA100, SMA200
               FROM stock_prices
               WHERE Name = ?
               ORDER BY Date DESC
               LIMIT 504""",  # 2 years for stable SMA200, frontend shows recent 10 months
            (name,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise LookupError(f"no_data:{code}")

    # Rows are newest-first; reverse to chronological order for TradingView
    rows = list(reversed(rows))

    candles: list[CandleBar] = []
    volume: list[VolumeBar] = []
    ema10_series: list[MAPoint] = []
    ema20_series: list[MAPoint] = []
    sma50_series: list[MAPoint] = []
    sma100_series: list[MAPoint] = []
    sma200_series: list[MAPoint] = []

    for row in rows:
        date, o, h, lo, c, v, e10, e20, s50, s100, s200 = row
        candles.append(CandleBar(time=date, open=o, high=h, low=lo, close=c))
        volume.append(VolumeBar(time=date, value=v if v is not None else 0.0))

        if e10 is not None:
            ema10_series.append(MAPoint(time=date, value=e10))
        if e20 is not None:
            ema20_series.append(MAPoint(time=date, value=e20))
        if s50 is not None:
            sma50_series.append(MAPoint(time=date, value=s50))
        if s100 is not None:
            sma100_series.append(MAPoint(time=date, value=s100))
        if s200 is not None:
            sma200_series.append(MAPoint(time=date, value=s200))

    return ChartResponse(
        candles=candles,
        volume=volume,
        ma=MAOverlays(
            ema10=ema10_series,
            ema20=ema20_series,
            sma50=sma50_series,
            sma100=sma100_series,
            sma200=sma200_series,
        ),
    )
