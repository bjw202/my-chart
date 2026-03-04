"""Router: GET /api/chart/{code} — daily/weekly OHLCV + MA data for TradingView."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Query

from backend.deps import DAILY_DB_PATH, WEEKLY_DB_PATH
from backend.schemas.chart import ChartResponse
from backend.services.chart_service import get_chart_data, get_weekly_chart_data

router = APIRouter()

_VALID_TIMEFRAMES = {"daily", "weekly"}


@router.get("/chart/{code}", response_model=ChartResponse)
async def chart(
    code: str,
    timeframe: str = Query(default="daily", description="Timeframe: 'daily' or 'weekly'"),
) -> ChartResponse:
    """Return OHLCV + MA overlays for a stock.

    - **code**: 6-digit KRX ticker code (e.g., "005930")
    - **timeframe**: 'daily' (default, 2 years) or 'weekly' (4 years)

    Returns 404 if the code is not found or has no price data.
    Returns 400 if timeframe is invalid.
    """
    if timeframe not in _VALID_TIMEFRAMES:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_timeframe", "valid": sorted(_VALID_TIMEFRAMES)},
        )
    try:
        if timeframe == "weekly":
            return get_weekly_chart_data(code, DAILY_DB_PATH, WEEKLY_DB_PATH)
        return get_chart_data(code, DAILY_DB_PATH)
    except sqlite3.OperationalError:
        raise HTTPException(
            status_code=503,
            detail={"error": "weekly_db_schema_outdated", "detail": "주간 DB 스키마가 구버전입니다. DB 업데이트를 실행하세요."},
        )
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
