"""Router: GET /api/sectors — 섹터 목록, 랭킹, 버블, RRG, 히스토리 엔드포인트.

SPEC-TOPDOWN-002A: 고급 섹터 분석 엔드포인트 추가.
"""

from __future__ import annotations


from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, Query

from backend.deps import DAILY_DB_PATH, WEEKLY_DB_PATH
from backend.services.sector_service import get_sectors
from backend.schemas.sector import SectorDetailResponse, SectorRankingResponse
from backend.schemas.sector_advanced import (
    SectorBubbleResponse,
    StockBubbleResponse,
    RRGResponse,
    SectorHistoryResponse,
)

router = APIRouter()


class SectorInfo(BaseModel):
    """A sector with its stock count from stock_meta."""

    sector_name: str
    count: int


@router.get("/sectors", response_model=list[SectorInfo])
async def sectors() -> list[SectorInfo]:
    """Return unique 산업명(대) values and stock counts from stock_meta.

    Returns an empty list if stock_meta has not been built yet.
    """
    raw = get_sectors(DAILY_DB_PATH)
    return [SectorInfo(sector_name=str(r["sector_name"]), count=int(r["count"])) for r in raw]


@router.get("/sectors/ranking", response_model=SectorRankingResponse)
async def sector_ranking() -> SectorRankingResponse:
    """Return sector strength ranking ordered by composite score.

    Uses weekly DB for breadth and return data.
    Returns 503 if weekly DB is not available.
    """
    from backend.services.sector_ranking_service import get_sector_ranking

    try:
        return get_sector_ranking(WEEKLY_DB_PATH)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "weekly_db_not_ready", "detail": str(exc)},
        ) from exc


@router.get("/sectors/bubble", response_model=SectorBubbleResponse)
async def sector_bubble(
    period: str = Query(default="1w", pattern="^(1w|1m|3m)$"),
    market: str | None = Query(default=None, pattern="^(KOSPI|KOSDAQ)$"),
) -> SectorBubbleResponse:
    """섹터 버블 차트 데이터를 반환한다.

    각 섹터의 초과수익률, RS 평균, 거래대금을 계산한다.
    Returns 503 if weekly DB is not available.
    """
    from backend.services.sector_advanced_service import get_sector_bubble

    try:
        return get_sector_bubble(WEEKLY_DB_PATH, period=period, market=market)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "weekly_db_not_ready", "detail": str(exc)},
        ) from exc


@router.get("/sectors/rrg", response_model=RRGResponse)
async def sector_rrg() -> RRGResponse:
    """RRG(Relative Rotation Graph) 데이터를 반환한다.

    각 섹터의 RS-Ratio와 RS-Momentum을 JdK 방식으로 정규화한다.
    Returns 503 if weekly DB is not available.
    """
    from backend.services.sector_advanced_service import get_rrg_data

    try:
        return get_rrg_data(WEEKLY_DB_PATH)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "weekly_db_not_ready", "detail": str(exc)},
        ) from exc


@router.get("/sectors/history", response_model=SectorHistoryResponse)
async def sector_history(
    weeks: int = Query(default=12, ge=1, le=52),
) -> SectorHistoryResponse:
    """섹터 랭킹 N주 히스토리를 반환한다.

    Returns 503 if weekly DB is not available.
    """
    from backend.services.sector_advanced_service import get_sector_history

    try:
        return get_sector_history(WEEKLY_DB_PATH, weeks=weeks)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "weekly_db_not_ready", "detail": str(exc)},
        ) from exc


# @MX:NOTE: [AUTO] 경로 파라미터 엔드포인트는 고정 경로 엔드포인트 다음에 선언해야 한다
# FastAPI가 "bubble", "rrg", "history"를 sector_name으로 잘못 라우팅하는 것을 방지
@router.get("/sectors/{sector_name}/detail", response_model=SectorDetailResponse)
async def sector_detail(sector_name: str) -> SectorDetailResponse:
    """Return sub-sector breakdown and top 5 stocks by RS for a major sector.

    Uses daily DB (stock_meta) for stock data.
    Returns empty lists if sector is not found.
    """
    from backend.services.sector_detail_service import get_sector_detail
    return get_sector_detail(DAILY_DB_PATH, sector_name)


# @MX:NOTE: [AUTO] /sectors/{sector_name}/bubble은 /sectors/bubble 다음에 선언
# 경로 충돌 방지를 위해 고정 경로가 먼저, 파라미터 경로가 나중에 위치
@router.get("/sectors/{sector_name}/bubble", response_model=StockBubbleResponse)
async def stock_bubble(
    sector_name: str,
    period: str = Query(default="1w", pattern="^(1w|1m|3m)$"),
) -> StockBubbleResponse:
    """특정 섹터 내 종목 버블 차트 데이터를 반환한다.

    Returns 503 if weekly DB is not available.
    """
    from backend.services.sector_advanced_service import get_stock_bubble

    try:
        return get_stock_bubble(WEEKLY_DB_PATH, sector_name=sector_name, period=period)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "weekly_db_not_ready", "detail": str(exc)},
        ) from exc
