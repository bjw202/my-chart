"""Pydantic schemas for /api/db endpoints (DB update, status, metadata)."""

from __future__ import annotations

from pydantic import BaseModel


class UpdateProgress(BaseModel):
    """SSE event payload for GET /api/db/status progress stream."""

    phase: str
    progress: float  # 0.0 - 100.0
    current_stock: str | None = None
    total: int
    eta_seconds: float | None = None


class LastUpdated(BaseModel):
    """Response payload for GET /api/db/last-updated."""

    last_updated: str | None = None  # ISO timestamp of last DB update
    latest_data_date: str | None = None  # Latest date in stock_prices (YYYY-MM-DD)
    daily_db_size: int  # bytes
    weekly_db_size: int  # bytes


class UpdateResult(BaseModel):
    """Final result summary emitted when DB update completes."""

    status: str  # "completed" | "error"
    success_count: int
    skipped_count: int
    error_count: int
    skipped_codes: list[str]
