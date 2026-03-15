"""Pydantic schemas for the /api/screen endpoint."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# Whitelist of allowed indicator column names.
# CRITICAL: This Literal type is the ONLY input accepted for SQL column references.
# It prevents SQL injection in PatternCondition-based WHERE clauses.
IndicatorName = Literal["Close", "Open", "High", "Low", "EMA10", "EMA20", "SMA50", "SMA100", "SMA200"]

MarketName = Literal["KOSPI", "KOSDAQ"]


class PatternCondition(BaseModel):
    """A single technical pattern condition: indicator_a [op] indicator_b * multiplier."""

    indicator_a: IndicatorName
    operator: Literal["gt", "gte", "lt", "lte"]
    indicator_b: IndicatorName
    multiplier: float = Field(default=1.0, gt=0.0, le=100.0)


class ScreenRequest(BaseModel):
    """Filter criteria for POST /api/screen."""

    market_cap_min: int | None = Field(default=None, ge=0, description="Minimum market cap in 억원")
    chg_1d_min: float | None = Field(default=None, description="Minimum 1-day return %")
    chg_1w_min: float | None = Field(default=None, description="Minimum 1-week return %")
    chg_1m_min: float | None = Field(default=None, description="Minimum 1-month return %")
    chg_3m_min: float | None = Field(default=None, description="Minimum 3-month return %")
    patterns: list[PatternCondition] = Field(default_factory=list, max_length=3)
    pattern_logic: Literal["AND", "OR"] = Field(default="AND")
    rs_min: float | None = Field(default=None, ge=0.0, le=100.0, description="Minimum RS_12M_Rating")
    markets: list[MarketName] = Field(default_factory=list, description="KOSPI and/or KOSDAQ")
    sectors: list[str] = Field(default_factory=list, description="산업명(대) values to include")
    codes: list[str] = Field(default_factory=list, description="Stock codes to filter by (from cross-tab navigation)")


class StockItem(BaseModel):
    """A single stock result row from stock_meta."""

    code: str
    name: str
    market: str
    market_cap: int | None = None
    sector_major: str | None = None
    sector_minor: str | None = None
    product: str | None = None
    close: float | None = None
    change_1d: float | None = None
    rs_12m: float | None = None
    ema10: float | None = None
    ema20: float | None = None
    sma50: float | None = None
    sma100: float | None = None
    sma200: float | None = None


class SectorGroup(BaseModel):
    """A group of stocks under the same 산업명(대) sector."""

    sector_name: str
    stock_count: int
    stocks: list[StockItem]


class ScreenResponse(BaseModel):
    """Response payload for POST /api/screen."""

    total: int
    sectors: list[SectorGroup]
