"""Pydantic schemas for stage classification API endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from backend.schemas.envelope import EnvelopeMixin


class StageDistribution(BaseModel):
    """Stage distribution counts."""

    stage1: int
    stage2: int
    stage3: int
    stage4: int
    # AC-SAG-027 — SMA40/SMA10 결측으로 분류 불가한 종목 수(REQ-SAG-024).
    unclassified_count: int = 0
    total: int


class SectorStageBreakdown(BaseModel):
    """Per-sector stage breakdown."""

    sector: str
    stage1: int
    stage2: int
    stage3: int
    stage4: int
    # AC-SAG-027 — distribution 과 동일한 불변식(§8.6)이 by_sector 항목에도 성립해야
    # 한다: stage1+stage2+stage3+stage4+unclassified_count == total.
    unclassified_count: int = 0
    total: int = 0


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
    # M6 신설 (spec.md §12.3, AC-SAG-041) — 종목 목록 3열 확장.
    chg_1w: float | None = None
    chg_3m: float | None = None
    # 섹터 내 시총 상한 재배분 가중치(INV-CAP-1) — daily DB 부재 시 None.
    weight_in_sector: float | None = None
    trading_value: float | None = None
    near_52w_high: bool | None = None


# Keep backward-compatible alias
Stage2Candidate = StageStock


class StageOverviewResponse(EnvelopeMixin):
    """Response for GET /api/stage/overview."""

    distribution: StageDistribution
    by_sector: list[SectorStageBreakdown]
    stage2_candidates: list[StageStock]
    all_stocks: list[StageStock] = []
