"""Router: GET /api/chart/{code} — daily OHLCV + MA data for TradingView."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.deps import DAILY_DB_PATH
from backend.schemas.chart import ChartResponse
from backend.services.chart_service import get_chart_data

router = APIRouter()


@router.get("/chart/{code}", response_model=ChartResponse)
async def chart(code: str) -> ChartResponse:
    """Return the latest 252 trading days of OHLCV + MA overlays for a stock.

    - **code**: 6-digit KRX ticker code (e.g., "005930")

    Returns 404 if the code is not found in stock_meta or has no price data.
    """
    try:
        return get_chart_data(code, DAILY_DB_PATH)
    except LookupError as exc:
        key = str(exc).split(":")[0]
        if key == "stock_not_found":
            raise HTTPException(status_code=404, detail={"error": "stock_not_found"})
        raise HTTPException(
            status_code=404,
            detail={
                "error": "no_data",
                "detail": f"Stock {code} has no price data in DB. It may be delisted or newly listed.",
            },
        )
