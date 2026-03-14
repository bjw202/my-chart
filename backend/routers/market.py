"""Router: GET /api/market/overview — market breadth and cycle analysis."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.deps import WEEKLY_DB_PATH
from backend.schemas.market import MarketOverviewResponse
from backend.services.market_service import get_market_overview

router = APIRouter()


@router.get("/market/overview", response_model=MarketOverviewResponse)
async def market_overview() -> MarketOverviewResponse:
    """Return full market overview including breadth, cycle phase, and 12-week history.

    Returns 503 if weekly DB is not available.
    """
    try:
        return get_market_overview(WEEKLY_DB_PATH)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "weekly_db_not_ready", "detail": str(exc)},
        ) from exc
