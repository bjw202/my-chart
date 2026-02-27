"""Router: DB update endpoints — trigger, SSE status stream, metadata."""

from __future__ import annotations

import asyncio
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from backend.deps import DAILY_DB_PATH, WEEKLY_DB_PATH
from backend.schemas.db import LastUpdated, UpdateProgress
from backend.services.db_service import start_update
from backend.services.progress_store import get_progress

router = APIRouter()


@router.post("/db/update", status_code=202)
async def trigger_db_update() -> JSONResponse:
    """Start a full DB update (daily + weekly + stock_meta rebuild).

    Returns 202 {"status": "started"} if the update was launched.
    Returns 409 {"error": "update_in_progress"} if one is already running.
    """
    started = start_update(DAILY_DB_PATH, WEEKLY_DB_PATH)
    if not started:
        raise HTTPException(
            status_code=409,
            detail={"error": "update_in_progress"},
        )
    return JSONResponse(status_code=202, content={"status": "started"})


@router.get("/db/status")
async def db_status() -> EventSourceResponse:
    """Stream DB update progress as SSE events every 500ms.

    Each event contains UpdateProgress JSON. Stream ends when update completes or errors.
    """

    async def _generate():
        while True:
            state = get_progress()
            payload = UpdateProgress(
                phase=state.get("phase", ""),
                progress=float(state.get("progress", 0.0)),
                current_stock=state.get("current_stock") or None,
                total=int(state.get("total", 0)),
                eta_seconds=state.get("eta_seconds"),
            )
            yield {"data": payload.model_dump_json()}

            if state.get("done") or state.get("error"):
                break

            await asyncio.sleep(0.5)

    return EventSourceResponse(_generate())


@router.get("/db/last-updated", response_model=LastUpdated)
async def last_updated() -> LastUpdated:
    """Return the timestamp of the last successful DB update and current DB file sizes."""
    from backend.services.progress_store import get_progress as _gp

    # Derive last_updated from stock_meta if available
    last_ts: str | None = None
    try:
        import sqlite3

        with sqlite3.connect(DAILY_DB_PATH, check_same_thread=False) as conn:
            row = conn.execute("SELECT MAX(last_updated) FROM stock_meta").fetchone()
            last_ts = row[0] if row else None
    except Exception:
        pass

    daily_size = os.path.getsize(DAILY_DB_PATH) if os.path.exists(DAILY_DB_PATH) else 0
    weekly_size = os.path.getsize(WEEKLY_DB_PATH) if os.path.exists(WEEKLY_DB_PATH) else 0

    return LastUpdated(
        last_updated=last_ts,
        daily_db_size=daily_size,
        weekly_db_size=weekly_size,
    )
