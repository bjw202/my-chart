"""Router: GET /api/stage/overview — stage classification distribution and candidates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.deps import WEEKLY_DB_PATH
from backend.schemas.stage import StageOverviewResponse
from backend.services.stage_service import get_stage_overview

router = APIRouter()


@router.get("/stage/overview", response_model=StageOverviewResponse)
async def stage_overview() -> StageOverviewResponse:
    """Return stage distribution, per-sector breakdown, and Stage 2 entry candidates.

    Returns 503 if weekly DB is not available.
    """
    try:
        return get_stage_overview(WEEKLY_DB_PATH)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "weekly_db_not_ready", "detail": str(exc)},
        ) from exc
