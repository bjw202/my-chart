"""Pydantic schemas for the /api/chart endpoint (TradingView Lightweight Charts format)."""

from __future__ import annotations

from pydantic import BaseModel


class CandleBar(BaseModel):
    """A single OHLC candlestick data point."""

    time: str  # "YYYY-MM-DD"
    open: float
    high: float
    low: float
    close: float


class VolumeBar(BaseModel):
    """A single volume bar data point."""

    time: str  # "YYYY-MM-DD"
    value: float


class MAPoint(BaseModel):
    """A single moving average data point."""

    time: str  # "YYYY-MM-DD"
    value: float


class MAOverlays(BaseModel):
    """Moving average overlays for the chart (all series in TradingView line format)."""

    ema10: list[MAPoint]
    ema20: list[MAPoint]
    sma50: list[MAPoint]
    sma100: list[MAPoint]
    sma200: list[MAPoint]


class ChartResponse(BaseModel):
    """Response payload for GET /api/chart/{code}.

    Returns the latest 252 trading days of OHLCV data plus MA overlays.
    """

    candles: list[CandleBar]
    volume: list[VolumeBar]
    ma: MAOverlays
