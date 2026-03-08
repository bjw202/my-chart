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
        try:
            rows = conn.execute(
                """SELECT Date, Open, High, Low, Close, VolumeWon,
                          EMA10, EMA20, SMA50, SMA100, SMA200, RS_Line
                   FROM stock_prices
                   WHERE Name = ?
                   ORDER BY Date DESC
                   LIMIT 504""",  # 2 years for stable SMA200, frontend shows recent 10 months
                (name,),
            ).fetchall()
            has_rs_line = True
        except sqlite3.OperationalError:
            # RS_Line 컬럼이 없는 구버전 DB
            rows = conn.execute(
                """SELECT Date, Open, High, Low, Close, VolumeWon,
                          EMA10, EMA20, SMA50, SMA100, SMA200
                   FROM stock_prices
                   WHERE Name = ?
                   ORDER BY Date DESC
                   LIMIT 504""",
                (name,),
            ).fetchall()
            has_rs_line = False
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
    rs_line_series: list[MAPoint] = []

    for row in rows:
        if has_rs_line:
            date, o, h, lo, c, vw, e10, e20, s50, s100, s200, rs = row
        else:
            date, o, h, lo, c, vw, e10, e20, s50, s100, s200 = row
            rs = None
        candles.append(CandleBar(time=date, open=o, high=h, low=lo, close=c))
        # VolumeWon is already in 억원 (HLC * Volume / 1_0000_0000)
        trading_value = round(vw, 1) if vw else 0.0
        volume.append(VolumeBar(time=date, value=trading_value))

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
        if rs is not None:
            rs_line_series.append(MAPoint(time=date, value=rs))

    return ChartResponse(
        timeframe="daily",
        candles=candles,
        volume=volume,
        ma=MAOverlays(
            ema10=ema10_series,
            ema20=ema20_series,
            sma50=sma50_series,
            sma100=sma100_series,
            sma200=sma200_series,
        ),
        rs_line=rs_line_series,
    )


def get_weekly_chart_data(code: str, daily_db_path: str, weekly_db_path: str) -> ChartResponse:
    """Return TradingView-formatted weekly chart data for the given stock code.

    Raises:
        LookupError: if the code is not found in stock_meta or has no weekly price data.
    """
    # Resolve company name from daily DB's stock_meta
    daily_conn = get_db_conn(daily_db_path)
    try:
        meta_row = daily_conn.execute(
            "SELECT name FROM stock_meta WHERE code = ?", (code,)
        ).fetchone()
    except sqlite3.OperationalError:
        raise LookupError(f"stock_not_found:{code}")
    finally:
        daily_conn.close()

    if not meta_row:
        raise LookupError(f"stock_not_found:{code}")

    name: str = meta_row[0]

    weekly_conn = get_db_conn(weekly_db_path)
    try:
        try:
            rows = weekly_conn.execute(
                """SELECT Date, Open, High, Low, Close, Volume, VolumeSMA10,
                          SMA10, SMA20, SMA40, RS_Line
                   FROM stock_prices
                   WHERE Name = ?
                   ORDER BY Date DESC
                   LIMIT 200""",  # ~4 years of weekly data
                (name,),
            ).fetchall()
            has_rs_line_w = True
        except sqlite3.OperationalError:
            # RS_Line 컬럼이 없는 구버전 주간 DB
            rows = weekly_conn.execute(
                """SELECT Date, Open, High, Low, Close, Volume, VolumeSMA10,
                          SMA10, SMA20, SMA40
                   FROM stock_prices
                   WHERE Name = ?
                   ORDER BY Date DESC
                   LIMIT 200""",
                (name,),
            ).fetchall()
            has_rs_line_w = False
    finally:
        weekly_conn.close()

    if not rows:
        raise LookupError(f"no_data:{code}")

    rows = list(reversed(rows))

    candles: list[CandleBar] = []
    volume: list[VolumeBar] = []
    sma10_series: list[MAPoint] = []
    sma20_series: list[MAPoint] = []
    sma40_series: list[MAPoint] = []
    rs_line_w_series: list[MAPoint] = []

    for row in rows:
        if has_rs_line_w:
            date, o, h, lo, c, vol, _, s10, s20, s40, rs_w = row
        else:
            date, o, h, lo, c, vol, _, s10, s20, s40 = row
            rs_w = None
        candles.append(CandleBar(time=date, open=o, high=h, low=lo, close=c))
        # Weekly volume is raw share count (not VolumeWon)
        volume.append(VolumeBar(time=date, value=float(vol) if vol else 0.0))

        if s10 is not None:
            sma10_series.append(MAPoint(time=date, value=s10))
        if s20 is not None:
            sma20_series.append(MAPoint(time=date, value=s20))
        if s40 is not None:
            sma40_series.append(MAPoint(time=date, value=s40))
        if rs_w is not None:
            rs_line_w_series.append(MAPoint(time=date, value=rs_w))

    return ChartResponse(
        timeframe="weekly",
        candles=candles,
        volume=volume,
        ma=MAOverlays(
            sma10=sma10_series,
            sma20=sma20_series,
            sma40=sma40_series,
        ),
        rs_line=rs_line_w_series,
    )
