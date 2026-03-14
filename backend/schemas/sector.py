"""Pydantic schemas for sector ranking API endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class SectorReturns(BaseModel):
    """Sector returns by period."""

    w1: float
    m1: float
    m3: float


class SectorExcessReturns(BaseModel):
    """Sector excess returns vs KOSPI by period."""

    w1: float
    m1: float
    m3: float


class SectorRankItem(BaseModel):
    """Single sector ranking entry."""

    name: str
    stock_count: int
    returns: SectorReturns
    excess_returns: SectorExcessReturns
    rs_avg: float
    rs_top_pct: float
    nh_pct: float
    stage2_pct: float
    composite_score: float
    rank: int
    rank_change: int


class SectorRankingResponse(BaseModel):
    """Response for GET /api/sectors/ranking."""

    date: str
    sectors: list[SectorRankItem]
