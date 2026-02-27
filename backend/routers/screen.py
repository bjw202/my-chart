"""Router: POST /api/screen — parameterized stock screener."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException

from backend.deps import DAILY_DB_PATH
from backend.schemas.screen import ScreenRequest, ScreenResponse
from backend.services.screen_service import screen_stocks

router = APIRouter()


@router.post("/screen", response_model=ScreenResponse)
async def screen(req: ScreenRequest) -> ScreenResponse:
    """Execute parameterized filter against stock_meta and return sector-grouped results.

    All indicator column names are validated against a server-side whitelist;
    user input is never interpolated into SQL.

    Returns 200 with total=0 and empty sectors when no stocks match.
    Returns 503 if stock_meta is not available yet (run DB update first).
    """
    try:
        return screen_stocks(req, DAILY_DB_PATH)
    except sqlite3.OperationalError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "db_not_ready", "detail": str(exc)},
        )
