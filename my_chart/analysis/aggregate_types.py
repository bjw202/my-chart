# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M1.1 — 집계 응답 계약 dataclass + 결측 3상태 표현.

전 응답에 파급되는 **형태 결정**을 여기서 고정한다(plan.md §2 M1.1). 값 로직은 M2
이후가 채우며, 이 모듈은 형태만 소유한다.

D6 결측 표현 — `{value, reason}` 객체 형태 (M1.1 확정)
------------------------------------------------------
plan.md §1 D6 은 "값 필드 + 형제 ``*_reason`` 필드" 와 "``{value, reason}`` 객체" 두
안을 제시하고 M1.1 에서 확정하도록 위임했다. **객체 형태를 채택한다.**

* AC-SAG-038 본문이 세 상태를 ``{value: null, reason: "missing"}`` /``{value: 0.0}`` /
  ``{value: null, reason: "insufficient"}`` 로 직접 명시한다 — 형제 필드 형태는
  ``{"x": null, "x_reason": "missing"}`` 로 직렬화돼 AC 본문과 형태가 갈린다.
* 형제 필드는 지표당 키가 2개로 늘고 **한쪽만 등록에서 빠뜨릴 수 있다** — Lesson #4
  (파생 구조가 원본 갱신을 자동 반영하지 않아 누락된 선례)의 실패 형태다. AC-SAG-043
  의 4단계 전파 검사 대상도 두 배가 된다.
* 객체 형태에서는 값과 사유가 **한 노드에 묶여** 분리 불가능하다.

§9.1 3상태 보존
---------------
1. **원천 값 없음** → :func:`missing` → ``{value: null, reason: "missing"}``
2. **실제 0** → :func:`present` (``0.0``) → ``{value: 0.0, reason: null}``
3. **산출 조건 미달** → :func:`insufficient` → ``{value: null, reason: "insufficient"}``

:class:`MetricValue` 는 ``reason`` 이 붙은 채로 ``value`` 가 들어오는 조합을 **생성
시점에 거부**한다. 즉 결측 자리에 ``0`` / ``0.0`` / ``50.0`` 을 넣는 일이 *누락으로는*
발생할 수 없고, 반드시 ``present(0.0)`` 를 명시적으로 써야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# 결측 사유 상수
# ---------------------------------------------------------------------------

#: 원천 데이터에 값 자체가 없다(NULL / 행 부재).
REASON_MISSING = "missing"
#: 산출 조건 미달(AG-4 유효 시총 종목 부족 · AG-7 커버리지 하한 미달 등).
REASON_INSUFFICIENT = "insufficient"
#: 산출 자체가 불가능(벤치마크 부재 등, 규칙 BM-4/BM-5).
REASON_UNAVAILABLE = "unavailable"

VALID_REASONS = frozenset({REASON_MISSING, REASON_INSUFFICIENT, REASON_UNAVAILABLE})

#: O-A6 — 커버리지 지표별 버킷. `Coverage` 와 `ValidCounts` 가 **동형**이어야 한다.
COVERAGE_BUCKETS = ("rs", "nh", "stage", "chg", "trading_value")

#: 종목 비중 상한(규칙 AG-1/AG-2). plan.md §1 D3 — **단일 정의 위치**이며 설정
#: 파일화하지 않는다. `weighting.capped_weights` 와 응답 봉투가 이 값을 공유한다.
WEIGHT_CAP = 0.10


# @MX:NOTE: [AUTO] 결측 3상태 헬퍼 — §9.1. 결측 자리에 0 / 0.0 / 50.0 치환을 금지한다.
#   구 구현은 `float(s.get("CHG_1W") or 0.0)`(sector_metrics.py:150) 처럼 NULL 을 조용히
#   0 으로 접었고, `_normalize_list` 는 max == min 에서 전 섹터를 50.0 으로 붕괴시켰다
#   (:114-115). 두 값 모두 "실제 0" / "실제 중앙" 과 구분되지 않아 화면에서 결측이
#   유효값으로 읽혔다. 아래 생성자 검증이 그 조합을 타입 수준에서 차단한다.
@dataclass(frozen=True)
class MetricValue:
    """단일 지표의 값 + 결측 사유.

    Args:
        value: 산출된 값. 결측이면 ``None``.
        reason: 결측 사유(:data:`VALID_REASONS`). 값이 있으면 ``None``.

    Raises:
        ValueError: ``reason`` 이 붙은 채 ``value`` 가 들어온 경우(치환 흔적) 또는
            알 수 없는 ``reason`` 인 경우.
    """

    value: float | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.reason is not None:
            if self.reason not in VALID_REASONS:
                raise ValueError(f"알 수 없는 결측 사유: {self.reason!r}")
            if self.value is not None:
                raise ValueError(
                    f"결측({self.reason}) 자리에 값 {self.value!r} 이 함께 왔다 — "
                    "§9.1 치환 금지. 실제 값이면 present(v), 결측이면 값을 비워라.")

    @property
    def is_missing(self) -> bool:
        return self.value is None

    def to_dict(self) -> dict[str, Any]:
        return {"value": self.value, "reason": self.reason}


def present(value: float) -> MetricValue:
    """실제 산출된 값(``0.0`` 도 정상 값이다 — §9.1 상태 2)."""
    if value is None:  # pragma: no cover - 호출부 오용 방어
        raise ValueError("present() 에 None 을 넘길 수 없다 — missing() 을 써라")
    return MetricValue(value=float(value), reason=None)


def missing() -> MetricValue:
    """원천 값 없음(§9.1 상태 1)."""
    return MetricValue(value=None, reason=REASON_MISSING)


def insufficient() -> MetricValue:
    """산출 조건 미달(§9.1 상태 3 — AG-4 / AG-7)."""
    return MetricValue(value=None, reason=REASON_INSUFFICIENT)


def unavailable() -> MetricValue:
    """산출 불가(규칙 BM-4/BM-5 벤치마크 부재)."""
    return MetricValue(value=None, reason=REASON_UNAVAILABLE)


# ---------------------------------------------------------------------------
# 커버리지 (O-A6 — 지표별 + 최상위 최소값)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Coverage:
    """지표별 커버리지 비율. 산출 대상이 아닌 지표는 ``None`` 이다.

    ``trading_value`` 는 daily ``VolumeWon`` 을 원천으로 하며 그 배선은 M5 소관이다.
    M2 시점에는 산출 대상이 아니므로 ``None`` 이며 :meth:`ratio` 의 최소값 계산에서
    제외된다(존재하지 않는 지표를 0 으로 접으면 AG-7 이 전 섹터를 null 로 만든다).
    """

    rs: float | None = None
    nh: float | None = None
    stage: float | None = None
    chg: float | None = None
    trading_value: float | None = None

    @property
    def ratio(self) -> float | None:
        """최상위 ``coverage_ratio`` = 산출된 지표들의 **최소값**(O-A6).

        AG-7 임계는 이 값에 적용한다(plan.md M1.1).
        """
        vals = [v for v in self.to_dict().values() if v is not None]
        return min(vals) if vals else None

    def to_dict(self) -> dict[str, float | None]:
        return {b: getattr(self, b) for b in COVERAGE_BUCKETS}


@dataclass(frozen=True)
class ValidCounts:
    """지표별 유효 종목 수. :class:`Coverage` 와 **동형**(O-A6)."""

    rs: int | None = None
    nh: int | None = None
    stage: int | None = None
    chg: int | None = None
    trading_value: int | None = None

    def to_dict(self) -> dict[str, int | None]:
        return {b: getattr(self, b) for b in COVERAGE_BUCKETS}


# ---------------------------------------------------------------------------
# 집계 산출물
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CappedMember:
    """상한(AG-2)에 걸려 비중이 깎인 구성종목."""

    name: str
    raw_weight: float
    capped_weight: float


@dataclass
class SectorAggregate:
    """단일 섹터의 집계 결과 — 응답 ``data[]`` 항목의 원본 형태.

    커버리지 4필드(``member_count`` / ``valid_count`` / ``coverage_ratio`` /
    ``cap_coverage_ratio``)는 불변식 AG-6 에 의해 **모든 항목에 존재**해야 한다
    (AC-SAG-008).
    """

    name: str

    # AG-6 커버리지 4필드
    member_count: int = 0
    valid_count: int | None = None
    coverage_ratio: MetricValue = field(default_factory=missing)
    cap_coverage_ratio: MetricValue = field(default_factory=missing)

    # O-A6 지표별 입도
    coverage: Coverage = field(default_factory=Coverage)
    valid_counts: ValidCounts = field(default_factory=ValidCounts)

    # 가중 산출물 (AG-1 / AG-2)
    weight_cap: float | None = None
    effective_n: MetricValue = field(default_factory=missing)
    capped_members: tuple[CappedMember, ...] = ()
    cap_weighted_available: bool = False
    low_confidence: bool = False

    # 지표 — 전부 결측 3상태 표현
    returns: dict[str, MetricValue] = field(default_factory=dict)
    excess_returns: dict[str, MetricValue] = field(default_factory=dict)
    rs_avg: MetricValue = field(default_factory=missing)
    rs_top_pct: MetricValue = field(default_factory=missing)
    nh_pct: MetricValue = field(default_factory=missing)
    stage2_pct: MetricValue = field(default_factory=missing)

    # 순위 (M3 소관 — M2 는 형태만 유지한다)
    composite_score: MetricValue = field(default_factory=missing)
    rank: int | None = None
    rank_change: int | None = None


@dataclass
class BenchmarkInfo:
    """벤치마크 산출 결과(규칙 BM-1 ~ BM-6). 값 로직은 M3 소관."""

    name: str | None = None
    status: str = "unavailable"
    returns: dict[str, MetricValue] = field(default_factory=dict)
    anchor_date: str | None = None
    universe_size: int | None = None
    weight_cap: float | None = None
    error: str | None = None


@dataclass(frozen=True)
class ExcludedSector:
    """순위·집계 대상에서 제외된 섹터와 사유(AG-4 / AG-5)."""

    sector: str
    reason: str
    count: int


@dataclass
class ResponseEnvelope:
    """전 엔드포인트 공통 응답 봉투(AC-SAG-036 의 10키)."""

    as_of_date: str | None = None
    as_of_is_partial_week: bool | None = None
    return_window_days: dict[str, int | None] = field(
        default_factory=lambda: {"1w": None, "1m": None, "3m": None})
    market_filter: str = "all"
    weight_cap: float | None = None
    grid_version: str = "canonical-v1"
    benchmark: BenchmarkInfo | None = None
    data: list[SectorAggregate] = field(default_factory=list)
    excluded: list[ExcludedSector] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
