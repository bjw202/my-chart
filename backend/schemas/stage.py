"""Pydantic schemas for stage classification API endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class StageDistribution(BaseModel):
    """Stage distribution counts."""

    stage1: int
    stage2: int
    stage3: int
    stage4: int
    total: int


class SectorStageBreakdown(BaseModel):
    """Per-sector stage breakdown."""

    sector: str
    stage1: int
    stage2: int
    stage3: int
    stage4: int


class StageStock(BaseModel):
    """Stock with stage classification info."""

    code: str = ""
    name: str
    market: str = ""
    sector_major: str = ""
    sector_minor: str = ""
    stage: int
    stage_detail: str
    rs_12m: float
    chg_1m: float
    volume_ratio: float
    close: float
    sma50: float
    sma200: float


# Keep backward-compatible alias
Stage2Candidate = StageStock


class StageOverviewResponse(BaseModel):
    """Response for GET /api/stage/overview."""

    distribution: StageDistribution
    by_sector: list[SectorStageBreakdown]
    stage2_candidates: list[StageStock]
    all_stocks: list[StageStock] = []
