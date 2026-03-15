"""Pydantic schemas for market overview API endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class IndexData(BaseModel):
    """KOSPI or KOSDAQ index data."""

    close: float | None = None
    chg_1w: float | None = None
    sma50: float | None = None
    sma200: float | None = None
    sma50_slope: float | None = None
    sma200_slope: float | None = None


class BreadthData(BaseModel):
    """Market breadth indicators for a single market."""

    pct_above_sma50: float
    pct_above_sma200: float
    nh_nl_ratio: float
    nh_nl_diff: int
    ad_ratio: float
    breadth_score: float


class MarketBreadth(BaseModel):
    """Breadth data split by market."""

    kospi: BreadthData
    kosdaq: BreadthData | None = None


class CriterionItem(BaseModel):
    """Single market cycle criterion evaluation."""

    name: str
    value: float
    direction: str  # "bull", "sideways", "bear"


class CycleData(BaseModel):
    """Market cycle phase determination result."""

    phase: str          # "bull", "sideways", "bear"
    choppy: bool
    criteria: list[CriterionItem]
    confidence: int


class BreadthHistoryItem(BaseModel):
    """Single week breadth snapshot for history chart."""

    date: str
    pct_above_sma50: float
    pct_above_sma200: float
    nh_nl_ratio: float
    nh_nl_diff: int
    ad_ratio: float
    breadth_score: float


class SectorAlertItem(BaseModel):
    """섹터 전환 알림 항목."""

    name: str
    signals: list[str]


class SectorAlertsData(BaseModel):
    """섹터 전환 알림 데이터."""

    emerging_leaders: list[SectorAlertItem]
    weakening_sectors: list[SectorAlertItem]


class MarketOverviewResponse(BaseModel):
    """Response for GET /api/market/overview."""

    kospi: IndexData
    kosdaq: IndexData | None = None
    breadth: MarketBreadth
    cycle: CycleData
    breadth_history: list[BreadthHistoryItem]
    sector_alerts: SectorAlertsData | None = None
