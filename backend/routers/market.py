"""Router: GET /api/market/overview — 시장 개요 및 트리맵 엔드포인트.

SPEC-TOPDOWN-002A: 트리맵 엔드포인트 추가.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from backend.deps import WEEKLY_DB_PATH
from backend.schemas.market import MarketOverviewResponse
from backend.schemas.sector_advanced import TreemapResponse
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


@router.get("/market/treemap", response_model=TreemapResponse)
async def market_treemap(
    period: str = Query(default="1w", pattern="^(1w|1m|3m)$"),
) -> TreemapResponse:
    """시가총액 기준 트리맵 데이터를 반환한다.

    루트 → 섹터 → 종목 계층 구조.
    크기: 시가총액, 색상: 기간 수익률.
    Returns 503 if weekly DB is not available.
    """
    from backend.services.sector_advanced_service import get_treemap_data

    try:
        return get_treemap_data(WEEKLY_DB_PATH, period=period)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "weekly_db_not_ready", "detail": str(exc)},
        ) from exc
