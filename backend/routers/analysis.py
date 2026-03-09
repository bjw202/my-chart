"""Router: GET /api/analysis/{code} — S-RIM financial dashboard."""

from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

from backend.schemas.analysis import (
    ActivityRatiosSchema,
    AnalysisResponse,
    BalanceSheetSchema,
    BusinessPerformanceSchema,
    FiveQuestionSchema,
    FiveQuestionsSchema,
    HealthIndicatorSchema,
    HealthIndicatorsSchema,
    ProfitWaterfallSchema,
    ProfitWaterfallStepSchema,
    RateDecompositionSchema,
    TrendSignalSchema,
    TrendSignalsSchema,
)
from backend.services.analysis_service import get_dashboard
from fnguide.dashboard import DashboardResult

router = APIRouter()

_CODE_PATTERN = re.compile(r"^\d{6}$")


def _to_response(result: DashboardResult) -> AnalysisResponse:
    """Convert DashboardResult dataclass to Pydantic AnalysisResponse.

    Handles optional (None) sections for financial companies.
    """
    bp = result.business_performance
    hi = result.health_indicators
    bs = result.balance_sheet
    rd = result.rate_decomposition
    pw = result.profit_waterfall
    ts = result.trend_signals
    fq = result.five_questions

    return AnalysisResponse(
        code=result.code,
        company_name=result.company_name,
        summary=result.summary,
        business_performance=BusinessPerformanceSchema(
            periods=bp.periods,
            revenue=bp.revenue,
            operating_profit=bp.operating_profit,
            net_income=bp.net_income,
            controlling_profit=bp.controlling_profit,
            operating_cf=bp.operating_cf,
            gpm=bp.gpm,
            opm=bp.opm,
            npm=bp.npm,
            yoy_revenue=bp.yoy_revenue,
            yoy_op=bp.yoy_op,
            yoy_ni=bp.yoy_ni,
            profit_quality=bp.profit_quality,
        ) if bp else None,
        health_indicators=HealthIndicatorsSchema(
            indicators=[
                HealthIndicatorSchema(
                    name=ind.name,
                    value=ind.value,
                    threshold=ind.threshold,
                    status=ind.status,
                )
                for ind in hi.indicators
            ]
        ) if hi else None,
        balance_sheet=BalanceSheetSchema(
            periods=bs.periods,
            financing=bs.financing,
            assets=bs.assets,
        ) if bs else None,
        rate_decomposition=RateDecompositionSchema(
            periods=rd.periods,
            operating_asset_return=rd.operating_asset_return,
            non_operating_return=rd.non_operating_return,
            borrowing_rate=rd.borrowing_rate,
            roe=rd.roe,
            weighted_avg_roe=rd.weighted_avg_roe,
            ke=rd.ke,
            spread=rd.spread,
        ) if rd else None,
        profit_waterfall=ProfitWaterfallSchema(
            steps=[
                ProfitWaterfallStepSchema(name=s.name, value=s.value)
                for s in pw.steps
            ]
        ) if pw else None,
        trend_signals=TrendSignalsSchema(
            signals=[
                TrendSignalSchema(
                    name=s.name,
                    direction=s.direction,
                    description=s.description,
                )
                for s in ts.signals
            ]
        ) if ts else None,
        five_questions=FiveQuestionsSchema(
            questions=[
                FiveQuestionSchema(
                    question=q.question,
                    status=q.status,
                    detail=q.detail,
                )
                for q in fq.questions
            ],
            verdict=fq.verdict,
        ) if fq else None,
        activity_ratios=ActivityRatiosSchema(
            receivable_turnover=ar.receivable_turnover,
            receivable_days=ar.receivable_days,
            inventory_turnover=ar.inventory_turnover,
            inventory_days=ar.inventory_days,
            payable_turnover=ar.payable_turnover,
            payable_days=ar.payable_days,
            ccc=ar.ccc,
            asset_turnover=ar.asset_turnover,
            periods=ar.periods,
        ) if (ar := result.activity_ratios) else None,
    )


@router.get("/analysis/{code}", response_model=AnalysisResponse)
async def analysis(code: str) -> AnalysisResponse:
    """Return S-RIM financial dashboard for a KRX stock.

    - **code**: 6-digit KRX ticker code (e.g., "005930")

    Returns 404 if the stock data cannot be found.
    Returns 422 if the code format is invalid.
    Returns 503 if FnGuide crawling fails.
    """
    if not _CODE_PATTERN.match(code):
        raise HTTPException(
            status_code=422,
            detail={"error": "invalid_code", "detail": "Stock code must be 6 digits."},
        )

    try:
        result = get_dashboard(code)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "detail": str(exc)},
        ) from exc
    except (ConnectionError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "crawling_failed", "detail": str(exc)},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "internal_error", "detail": str(exc)},
        ) from exc

    return _to_response(result)
