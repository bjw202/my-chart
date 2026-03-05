"""Pydantic v2 schemas for GET /api/analysis/{code} endpoint.

Mirrors DashboardResult and its 7 section dataclasses from fnguide.dashboard.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BusinessPerformanceSchema(BaseModel):
    """Section 1: Revenue, profit, cash flow and margin trends (4 years)."""

    periods: list[str]
    revenue: list[float]
    operating_profit: list[float]
    net_income: list[float]
    controlling_profit: list[float]
    operating_cf: list[float]
    gpm: list[float]
    opm: list[float]
    npm: list[float]
    yoy_revenue: list[float | None]
    yoy_op: list[float | None]
    yoy_ni: list[float | None]
    profit_quality: list[float | None]


class HealthIndicatorSchema(BaseModel):
    """A single financial health metric with threshold classification."""

    name: str
    value: float | None
    threshold: str
    status: Literal["ok", "warn", "danger"]


class HealthIndicatorsSchema(BaseModel):
    """Section 2: 7 financial health indicators."""

    indicators: list[HealthIndicatorSchema]


class BalanceSheetSchema(BaseModel):
    """Section 3: B/S reclassification time series (4 years)."""

    periods: list[str]
    financing: dict[str, list[float]]
    assets: dict[str, list[float]]


class RateDecompositionSchema(BaseModel):
    """Section 4: 3-rate decomposition (3 years + expected)."""

    periods: list[str]
    operating_asset_return: list[float]
    non_operating_return: list[float]
    borrowing_rate: list[float]
    roe: list[float]
    weighted_avg_roe: float
    ke: float | None
    spread: float | None


class ProfitWaterfallStepSchema(BaseModel):
    """A single step in the profit waterfall."""

    name: str
    value: float


class ProfitWaterfallSchema(BaseModel):
    """Section 5: 8-step profit waterfall from expected estimates."""

    steps: list[ProfitWaterfallStepSchema]


class TrendSignalSchema(BaseModel):
    """A single trend signal derived from linear regression slope."""

    name: str
    direction: Literal["up", "flat", "down"]
    description: str


class TrendSignalsSchema(BaseModel):
    """Section 6: Linear trend signals for 6 financial metrics."""

    signals: list[TrendSignalSchema]


class FiveQuestionSchema(BaseModel):
    """A single question from the 5-question investment screening."""

    question: str
    status: Literal["ok", "warn", "danger"]
    detail: str


class FiveQuestionsSchema(BaseModel):
    """Section 7: 5-question investment quality screening."""

    questions: list[FiveQuestionSchema]
    verdict: Literal["양호", "보통", "주의"]


class AnalysisResponse(BaseModel):
    """Response payload for GET /api/analysis/{code}."""

    code: str
    company_name: str
    business_performance: BusinessPerformanceSchema
    health_indicators: HealthIndicatorsSchema
    balance_sheet: BalanceSheetSchema
    rate_decomposition: RateDecompositionSchema
    profit_waterfall: ProfitWaterfallSchema
    trend_signals: TrendSignalsSchema
    five_questions: FiveQuestionsSchema
