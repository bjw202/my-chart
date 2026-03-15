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


class SubSectorItem(BaseModel):
    """A sub-sector breakdown item within a major sector."""

    name: str
    stock_count: int
    stage1_count: int = 0
    stage2_count: int = 0
    stage3_count: int = 0
    stage4_count: int = 0
    # 소그룹 내 rs_12m 평균
    rs_avg: float = 0.0
    # Stage 2 종목 비율 (%)
    stage2_pct: float = 0.0


class TopStockItem(BaseModel):
    """A top stock entry within a sector, ordered by RS."""

    code: str
    name: str
    rs_12m: float
    stage: int | None = None
    # 1개월 가격 변동률 (%)
    chg_1m: float | None = None
    # 상세 스테이지 설명 (예: "Stage 2", "Stage 4")
    stage_detail: str | None = None


class SectorDetailResponse(BaseModel):
    """Response for GET /api/sectors/{name}/detail."""

    sector_name: str
    sub_sectors: list[SubSectorItem]
    top_stocks: list[TopStockItem]
