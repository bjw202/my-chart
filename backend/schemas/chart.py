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
    """Moving average overlays for the chart (all series in TradingView line format).

    Daily timeframe: ema10, ema20, sma50, sma100, sma200 are populated.
    Weekly timeframe: sma10, sma20, sma40 are populated.
    """

    ema10: list[MAPoint] = []
    ema20: list[MAPoint] = []
    sma50: list[MAPoint] = []
    sma100: list[MAPoint] = []
    sma200: list[MAPoint] = []
    sma10: list[MAPoint] = []
    sma20: list[MAPoint] = []
    sma40: list[MAPoint] = []


class ChartResponse(BaseModel):
    """Response payload for GET /api/chart/{code}."""

    timeframe: str = "daily"
    candles: list[CandleBar]
    volume: list[VolumeBar]
    ma: MAOverlays
