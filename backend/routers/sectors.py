"""Router: GET /api/sectors — list unique sectors from stock_meta."""

from __future__ import annotations

from pydantic import BaseModel

from fastapi import APIRouter

from backend.deps import DAILY_DB_PATH
from backend.services.sector_service import get_sectors

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
