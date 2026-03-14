"""Router: GET /api/sectors — list unique sectors from stock_meta.
Also provides GET /api/sectors/ranking for sector strength ranking.
"""

from __future__ import annotations

import sqlite3

from pydantic import BaseModel

from fastapi import APIRouter, HTTPException

from backend.deps import DAILY_DB_PATH, WEEKLY_DB_PATH
from backend.services.sector_service import get_sectors
from backend.schemas.sector import SectorRankingResponse

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
    return [SectorInfo(sector_name=r["sector_name"], count=r["count"]) for r in raw]


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
