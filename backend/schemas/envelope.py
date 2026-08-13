# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M1.1 — 응답 공통 봉투 Pydantic 스키마.

`my_chart.analysis.aggregate_types` 의 dataclass 를 직렬화 계층으로 옮긴 거울이다.
전 섹터·스테이지 응답 모델이 :class:`EnvelopeMixin` 을 상속해 AC-SAG-036 의 공통
10키를 획득한다.

하위 호환 (plan.md §1 D4)
-------------------------
봉투 필드는 전부 **추가 전용 optional**이며 기본값을 갖는다. 기존 응답 키(``date`` /
``sectors`` / ``distribution`` …)는 그대로 남으므로 기존 프론트엔드는 무변경으로
동작한다. 새 canonical 목록은 ``data`` 이며, 기존 목록 키와 당분간 공존한다.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from my_chart.analysis.aggregate_types import (
    COVERAGE_BUCKETS,
    WEIGHT_CAP,
    BenchmarkInfo,
    Coverage,
    ExcludedSector,
    MetricValue,
    SectorAggregate,
    ValidCounts,
)
from my_chart.analysis.weekly_grid import GRID_VERSION


class MetricValueModel(BaseModel):
    """결측 3상태 표현(§9.1 · AC-SAG-038) — ``{value, reason}`` 객체 형태."""

    value: float | None = None
    reason: str | None = None


class CoverageModel(BaseModel):
    """지표별 커버리지 비율(O-A6)."""

    rs: float | None = None
    nh: float | None = None
    stage: float | None = None
    chg: float | None = None
    trading_value: float | None = None


class ValidCountsModel(BaseModel):
    """지표별 유효 종목 수 — :class:`CoverageModel` 과 동형(O-A6)."""

    rs: int | None = None
    nh: int | None = None
    stage: int | None = None
    chg: int | None = None
    trading_value: int | None = None


class CappedMemberModel(BaseModel):
    """상한에 걸린 구성종목(규칙 AG-2 노출)."""

    name: str
    raw_weight: float
    capped_weight: float


class SectorAggregateModel(BaseModel):
    """응답 ``data[]`` 항목 — 섹터 집계 결과."""

    name: str

    # AG-6 커버리지 4필드 (AC-SAG-008 — 누락 0건)
    member_count: int = 0
    valid_count: int | None = None
    coverage_ratio: MetricValueModel = Field(default_factory=MetricValueModel)
    cap_coverage_ratio: MetricValueModel = Field(default_factory=MetricValueModel)

    # O-A6 지표별 입도
    coverage: CoverageModel = Field(default_factory=CoverageModel)
    valid_counts: ValidCountsModel = Field(default_factory=ValidCountsModel)

    # AG-1 / AG-2 가중 산출물
    weight_cap: float | None = None
    effective_n: MetricValueModel = Field(default_factory=MetricValueModel)
    capped_members: list[CappedMemberModel] = Field(default_factory=list)
    cap_weighted_available: bool = False
    low_confidence: bool = False

    # 지표
    returns: dict[str, MetricValueModel] = Field(default_factory=dict)
    excess_returns: dict[str, MetricValueModel] = Field(default_factory=dict)
    rs_avg: MetricValueModel = Field(default_factory=MetricValueModel)
    rs_top_pct: MetricValueModel = Field(default_factory=MetricValueModel)
    nh_pct: MetricValueModel = Field(default_factory=MetricValueModel)
    stage2_pct: MetricValueModel = Field(default_factory=MetricValueModel)

    # 순위 (M3 소관)
    composite_score: MetricValueModel = Field(default_factory=MetricValueModel)
    rank: int | None = None
    rank_change: int | None = None


class BenchmarkInfoModel(BaseModel):
    """벤치마크 정보(규칙 BM-1 ~ BM-6). 값 로직은 M3 소관."""

    name: str | None = None
    status: str = "unavailable"
    returns: dict[str, MetricValueModel] = Field(default_factory=dict)
    anchor_date: str | None = None
    universe_size: int | None = None
    weight_cap: float | None = None
    error: str | None = None


class ExcludedSectorModel(BaseModel):
    """제외 섹터와 사유(AG-4 / AG-5)."""

    sector: str
    reason: str
    count: int


def _default_return_window_days() -> dict[str, int | None]:
    """``return_window_days`` 기본값 — 키 3개는 항상 존재한다(AC-SAG-036).

    실측 값 채움은 앵커가 붙는 M3 소관이다(AC-SAG-046).
    """
    return {"1w": None, "1m": None, "3m": None}


class EnvelopeMixin(BaseModel):
    """AC-SAG-036 공통 10키. 전 섹터·스테이지 응답 모델이 상속한다."""

    as_of_date: str | None = None
    as_of_is_partial_week: bool | None = None
    return_window_days: dict[str, int | None] = Field(
        default_factory=_default_return_window_days)
    market_filter: str = "all"
    weight_cap: float = WEIGHT_CAP
    grid_version: str = GRID_VERSION
    benchmark: BenchmarkInfoModel | None = None
    data: list[SectorAggregateModel] = Field(default_factory=list)
    excluded: list[ExcludedSectorModel] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# dataclass → Pydantic 변환 (AC-SAG-043 2단계)
# ---------------------------------------------------------------------------

def metric_model(m: MetricValue) -> MetricValueModel:
    return MetricValueModel(value=m.value, reason=m.reason)


def _metric_map(d: dict[str, MetricValue]) -> dict[str, MetricValueModel]:
    return {k: metric_model(v) for k, v in d.items()}


def coverage_model(c: Coverage) -> CoverageModel:
    return CoverageModel(**{b: getattr(c, b) for b in COVERAGE_BUCKETS})


def valid_counts_model(v: ValidCounts) -> ValidCountsModel:
    return ValidCountsModel(**{b: getattr(v, b) for b in COVERAGE_BUCKETS})


def aggregate_model(a: SectorAggregate) -> SectorAggregateModel:
    """`SectorAggregate` dataclass → 직렬화 모델."""
    return SectorAggregateModel(
        name=a.name,
        member_count=a.member_count,
        valid_count=a.valid_count,
        coverage_ratio=metric_model(a.coverage_ratio),
        cap_coverage_ratio=metric_model(a.cap_coverage_ratio),
        coverage=coverage_model(a.coverage),
        valid_counts=valid_counts_model(a.valid_counts),
        weight_cap=a.weight_cap,
        effective_n=metric_model(a.effective_n),
        capped_members=[
            CappedMemberModel(name=c.name, raw_weight=c.raw_weight,
                              capped_weight=c.capped_weight)
            for c in a.capped_members
        ],
        cap_weighted_available=a.cap_weighted_available,
        low_confidence=a.low_confidence,
        returns=_metric_map(a.returns),
        excess_returns=_metric_map(a.excess_returns),
        rs_avg=metric_model(a.rs_avg),
        rs_top_pct=metric_model(a.rs_top_pct),
        nh_pct=metric_model(a.nh_pct),
        stage2_pct=metric_model(a.stage2_pct),
        composite_score=metric_model(a.composite_score),
        rank=a.rank,
        rank_change=a.rank_change,
    )


def benchmark_model(b: BenchmarkInfo | None) -> BenchmarkInfoModel | None:
    if b is None:
        return None
    return BenchmarkInfoModel(
        name=b.name,
        status=b.status,
        returns=_metric_map(b.returns),
        anchor_date=b.anchor_date,
        universe_size=b.universe_size,
        weight_cap=b.weight_cap,
        error=b.error,
    )


def excluded_models(items: list[ExcludedSector]) -> list[ExcludedSectorModel]:
    return [ExcludedSectorModel(sector=e.sector, reason=e.reason, count=e.count)
            for e in items]


def envelope_fields(
    *,
    as_of_date: str | None = None,
    as_of_is_partial_week: bool | None = None,
    return_window_days: dict[str, int | None] | None = None,
    market_filter: str = "all",
    weight_cap: float = WEIGHT_CAP,
    benchmark: BenchmarkInfo | None = None,
    data: list[SectorAggregate] | None = None,
    excluded: list[ExcludedSector] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """봉투 10키를 응답 모델 생성자 kwargs 로 만든다."""
    return {
        "as_of_date": as_of_date,
        "as_of_is_partial_week": as_of_is_partial_week,
        "return_window_days": return_window_days or _default_return_window_days(),
        "market_filter": market_filter,
        "weight_cap": weight_cap,
        "grid_version": GRID_VERSION,
        "benchmark": benchmark_model(benchmark),
        "data": [aggregate_model(a) for a in (data or [])],
        "excluded": excluded_models(excluded or []),
        "warnings": list(warnings or []),
    }
