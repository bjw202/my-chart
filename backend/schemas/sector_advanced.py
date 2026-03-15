"""SPEC-TOPDOWN-002A API 응답용 Pydantic 스키마.

고급 섹터 분석 엔드포인트 (버블, RRG, 히스토리, 트리맵)에 사용된다.
"""

from __future__ import annotations

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# 섹터 버블 스키마
# ---------------------------------------------------------------------------

class SectorBubbleItem(BaseModel):
    """섹터 버블 차트 단일 항목."""

    name: str
    excess_return: float    # KOSPI 대비 초과수익률 (%)
    rs_avg: float           # 섹터 평균 RS
    trading_value: float    # 거래대금 합계
    period_return: float    # 기간 수익률 (%)


class SectorBubbleResponse(BaseModel):
    """GET /api/sectors/bubble 응답."""

    date: str
    period: str
    market: str | None
    sectors: list[SectorBubbleItem]


# ---------------------------------------------------------------------------
# 종목 버블 스키마
# ---------------------------------------------------------------------------

class StockBubbleItem(BaseModel):
    """종목 버블 차트 단일 항목."""

    name: str
    price_change: float      # 기간 가격 변화율 (%)
    rs_12m: float            # 12개월 RS
    trading_value: float     # 거래대금
    stage: int | None        # 스테이지 (1~4)
    stage_detail: str | None # 스테이지 상세
    market_cap: float        # 시가총액
    volume_ratio: float      # 거래량 비율


class StockBubbleResponse(BaseModel):
    """GET /api/sectors/{sector_name}/bubble 응답."""

    date: str
    sector_name: str
    period: str
    stocks: list[StockBubbleItem]


# ---------------------------------------------------------------------------
# RRG 스키마
# ---------------------------------------------------------------------------

class RRGTrailPoint(BaseModel):
    """RRG 궤적의 단일 시점."""

    date: str
    rs_ratio: float
    rs_momentum: float


class RRGSectorItem(BaseModel):
    """RRG 차트 단일 섹터 항목."""

    name: str
    rs_ratio: float          # 현재 RS-Ratio (100 기준)
    rs_momentum: float       # 현재 RS-Momentum (100 기준)
    quadrant: str            # leading/weakening/lagging/improving
    trail: list[RRGTrailPoint]


class KospiPoint(BaseModel):
    """KOSPI 종가 시계열 포인트."""

    date: str
    close: float


class RRGResponse(BaseModel):
    """GET /api/sectors/rrg 응답."""

    date: str
    sectors: list[RRGSectorItem]
    kospi: list[KospiPoint] = []


# ---------------------------------------------------------------------------
# 섹터 히스토리 스키마
# ---------------------------------------------------------------------------

class SectorHistoryWeek(BaseModel):
    """단일 주의 섹터 랭킹 스냅샷."""

    date: str
    rank: int
    composite_score: float
    sector_return_1w: float
    sector_excess_return_1w: float
    rs_avg: float


class SectorHistoryItem(BaseModel):
    """섹터의 N주 히스토리."""

    name: str
    history: list[SectorHistoryWeek]


class SectorHistoryResponse(BaseModel):
    """GET /api/sectors/history 응답."""

    weeks: int
    sectors: list[SectorHistoryItem]


# ---------------------------------------------------------------------------
# 트리맵 스키마
# ---------------------------------------------------------------------------

class TreemapStockNode(BaseModel):
    """트리맵 종목 리프 노드."""

    name: str
    market_cap: float
    price_change: float
    rs_12m: float
    stage: int | None


class TreemapSectorNode(BaseModel):
    """트리맵 섹터 중간 노드."""

    name: str
    market_cap: float
    price_change: float
    stocks: list[TreemapStockNode]


class TreemapResponse(BaseModel):
    """GET /api/market/treemap 응답."""

    date: str
    period: str
    total_market_cap: float
    sectors: list[TreemapSectorNode]
