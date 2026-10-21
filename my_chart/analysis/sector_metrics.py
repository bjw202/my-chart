"""Sector strength metrics and ranking engine.

Computes sector-level aggregated metrics from weekly DB and sector registry.
Ranks sectors by composite score.

Per SPEC-TOPDOWN-001A R7-R8.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import statistics
from dataclasses import dataclass, field
from typing import Any

from my_chart.analysis.aggregate_types import (
    WEIGHT_CAP,
    BenchmarkInfo,
    Coverage,
    ExcludedSector,
    MetricValue,
    SectorAggregate,
    ValidCounts,
    insufficient,
    missing,
    present,
)
from my_chart.analysis.stage_classifier import classify_stage, _compute_slope
from my_chart.analysis.universe import ETC_SECTOR, compute_universe
from my_chart.analysis.weekly_grid import anchor, compute_weekly_grid
from my_chart.analysis.weighting import (
    capped_weights_detail,
    effective_n,
    weighted_mean,
)
from my_chart.config import SECTORMAP_PATH
from my_chart.registry import get_sector_registry, load_sector_registry_with_diagnostics

logger = logging.getLogger(__name__)

# Index names excluded from sector metrics
_INDEX_NAMES = frozenset({"KOSPI", "KOSDAQ"})

# 52-week high/low proximity thresholds
_NH_THRESHOLD = 0.02  # within 2% of high_52w

#: AC-SAG-024 — 52주 신고가 판정 창(일). 저장된 `MAX52`(Close 기반)를 쓰지 않고
#: weekly `stock_prices.High` 를 이 창으로 직접 재계산한다(REQ-SAG-022, 규약 Y).
HIGH_52W_WINDOW_DAYS = 364

# RS top threshold per SPEC R7
_RS_TOP_THRESHOLD = 80.0

# --- SPEC-SECTOR-AGGREGATION-001 M2 집계 규칙 상수 -------------------------------
#: AG-5 — 섹터 최소 구성종목 수. 미달 섹터는 ``data[]`` 에서 빠지고 ``excluded[]`` 로 간다.
MIN_SECTOR_MEMBERS = 5
#: AG-4 — 시총가중 산출에 필요한 최소 유효 시총 종목 수. 미달이면 시총가중 필드가 null.
MIN_CAP_VALID_MEMBERS = 5
#: AG-7 — 최상위 ``coverage_ratio`` 가 이 값 **미만**이면 값을 null 로 만든다(경계 포함 유지).
COVERAGE_NULL_THRESHOLD = 0.50
#: AG-7 — 이 값 **미만**이면 ``low_confidence: true``(경계 0.80 정확히는 플래그 없음).
COVERAGE_LOW_CONFIDENCE_THRESHOLD = 0.80

# @MX:NOTE: [AUTO] 기간 라벨 → `anchor(t, N)` 의 라벨 일수(REQ-SAG-043 · O-A4/O-A8).
#   기간 수익률의 원천은 저장된 `CHG_*` 컬럼이 **아니라** `Close(t) / Close(anchor(t, N)) − 1`
#   이다. 저장된 `CHG_1M` 은 고정 바 오프셋(집계 픽스처 실측: `2026-08-11` 대비
#   `2026-07-16` = 4바 전)으로 산출돼 `anchor(t, 28)`(= `2026-07-10`)과 **다른 바**를 가리킨다
#   — spec.md §1.2 가 고정 바 오프셋 관용구를 `anchor(t, 28)` 로 교체하라고 적은 결함과
#   같은 계열이며, `as_of` 가 미완성 주 바일 때 창이 라벨보다 길어지는 O-A8 과도 어긋난다.
#   섹터·벤치마크가 **같은 `anchor(t, N)` 호출**을 공유하는 것이 BM-6 보존의 유일 조건이다.
_PERIOD_LABEL_DAYS = {"1w": 7, "1m": 28, "3m": 91}
#: 기간 라벨 목록(응답 키 순서 고정).
_PERIODS = tuple(_PERIOD_LABEL_DAYS)


def _load_weekly_snapshot(
    conn: sqlite3.Connection, date: str
) -> dict[str, dict[str, Any]]:
    """Load weekly stock data for a given date, keyed by stock name."""
    rows = conn.execute(
        """SELECT sp.Name, sp.Close, sp.SMA10, sp.SMA40,
                  sp.SMA40_Trend_4M, sp.CHG_1W, sp.CHG_1M, sp.CHG_3M,
                  sp.Volume, sp.VolumeSMA10, sp.MAX52,
                  rs.RS_12M_Rating
           FROM stock_prices sp
           LEFT JOIN relative_strength rs
             ON sp.Name = rs.Name AND sp.Date = rs.Date
           WHERE sp.Date = ?""",
        (date,),
    ).fetchall()

    result: dict[str, dict[str, Any]] = {}
    for r in rows:
        name = r[0]
        sma40 = float(r[3] or 0.0)
        sma40_4w_ago = float(r[4] or 0.0)
        result[name] = {
            "Close": r[1],
            "SMA10": r[2],
            "SMA40": sma40,
            "SMA40_slope": _compute_slope(sma40, sma40_4w_ago),
            "CHG_1W": r[5],
            "CHG_1M": r[6],
            "CHG_3M": r[7],
            "Volume": r[8],
            "VolumeSMA10": r[9],
            "MAX52": r[10],
            "RS_12M_Rating": r[11],
        }
    return result


# --- SPEC-SECTOR-AGGREGATION-001 M3 순위·정규화 상수 (규칙 AG-8/AG-9/RK-1) --------
#: composite_score 가중치(§2.9). ``norm(excess_1w)×0.30 + norm(excess_1m)×0.40 + norm(excess_3m)×0.30``.
_COMPOSITE_WEIGHTS = {"1w": 0.30, "1m": 0.40, "3m": 0.30}

#: 시장별 벤치마크 이름(규칙 BM-1).
_MARKET_BENCHMARK_NAMES = {"all": "ALL_CAPPED", "kospi": "KOSPI_CAPPED", "kosdaq": "KOSDAQ_CAPPED"}

#: AC-SAG-015 — 지수 행 정합성 경고 허용오차(%p). 단일 위치 정의 — O-A5 재측정 후
#: 여기 한 곳만 바꾸면 된다.
BENCHMARK_RECONCILIATION_TOLERANCE_PP = {"1w": 0.5, "1m": 3.0, "3m": 7.0}


def norm(values: list[float]) -> list[float]:
    """순위 백분위 정규화(규칙 AG-8, plan.md §3.3).

    min-max 대신 **순위** 기반이라 극단값이 스케일을 지배하지 않는다(``[1,2,3,1000]``
    이 ``[0,0.1,0.2,100]`` 대신 ``[0,33.33,66.67,100]`` 이 된다). 동점은 평균 순위로
    묶인다(scipy ``rankdata(method="average")`` 와 동치 — 여기서는 순수 파이썬으로
    재구현해 새 의존성을 추가하지 않는다).

    Args:
        values: 정규화할 값들(순서 보존).

    Returns:
        같은 길이의 0~100 스케일 리스트. ``N == 0`` → 빈 리스트. ``N == 1`` → ``[50.0]``.
    """
    n = len(values)
    if n == 0:
        return []
    if n == 1:
        return [50.0]
    order = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1          # 1-indexed 평균 순위(동점 묶음)
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return [(r - 1) / (n - 1) * 100 for r in ranks]


@dataclass(frozen=True)
class _Member:
    """집계 입력 1종목. 결측은 ``None`` 이며 **어떤 대체값도 부여하지 않는다**(§9.1)."""

    name: str
    market_cap: float | None
    returns: dict[str, float | None]      # % 스케일
    rs: float | None
    nh: bool | None                       # 52주 신고가 판정(판정 불가면 None)
    stage2: bool | None                   # Stage 2 여부(분류 불가면 None)
    # M6-gap G16 — 기간별 거래대금(원, daily VolumeWon 원천). 결측은 None.
    trading_value: dict[str, float | None] = field(default_factory=dict)

    @property
    def cap_valid(self) -> bool:
        """규칙 AG-3 — 시총이 NULL 이거나 ``<= 0`` 이면 시총가중에서 제외한다."""
        return self.market_cap is not None and self.market_cap > 0


@dataclass
class SectorAggregationResult:
    """`compute_sector_aggregates` 산출물 — 봉투의 ``data`` / ``excluded`` / ``warnings``."""

    aggregates: list[SectorAggregate]
    excluded: list[ExcludedSector]
    warnings: list[str]
    # --- M3 신설 필드 (규칙 BM-1 ~ BM-6, AG-8/AG-9, REQ-SAG-043) -----------------
    benchmark: BenchmarkInfo | None = None
    return_window_days: dict[str, int | None] = field(
        default_factory=lambda: {"1w": None, "1m": None, "3m": None})
    as_of_is_partial_week: bool | None = None
    baseline_date: str | None = None          # rank_change 기준일(anchor(t,28), AC-SAG-023)


def _load_market_caps(daily_db_path: str | None) -> dict[str, float]:
    """일봉 ``stock_meta`` 에서 시가총액을 읽는다(단일 원천 — 규칙 UN-2).

    경로가 없거나 파일이 없으면 **빈 dict** 를 돌려준다. 이때 전 종목이 AG-3 결측으로
    취급돼 시총가중이 불가능해지고 등가중 폴백이 걸린다 — 라이브 DB 를 암묵적으로 열지
    않기 위한 의도적 동작이다(``sqlite3.connect`` 는 없는 파일을 새로 만든다).
    """
    if not daily_db_path or not os.path.exists(daily_db_path):
        logger.warning("시총 원천(daily stock_meta) 없음 — 시총가중 불가: %s", daily_db_path)
        return {}
    conn = sqlite3.connect(daily_db_path)
    try:
        rows = conn.execute("SELECT name, market_cap FROM stock_meta").fetchall()
    except sqlite3.Error as exc:            # 테이블 부재 등
        logger.warning("stock_meta 조회 실패 — 시총가중 불가: %s", exc)
        return {}
    finally:
        conn.close()
    caps: dict[str, float] = {}
    for name, cap in rows:
        if cap is None:
            continue
        val = float(cap)
        if val > 0:                          # AG-3: NULL / <= 0 은 대체값 없이 제외
            caps[str(name)] = val
    return caps


# @MX:NOTE: [AUTO] AC-SAG-029/REQ-SAG-026 · O-A4 — trading_value 는 daily
#   `stock_prices.VolumeWon` 을 원천으로 하며, 집계 창은 수익률과 **동일한**
#   `anchor(t, N)` 호출에서 나온 `[anchor_date, t]` 다(기간 토글 연동). 종가×거래량
#   재계산을 금지한다 — 집계 경로(이 모듈)에서 그 표현은 어디에도 없다.
def compute_trading_value_by_period(
    daily_db_path: str | None,
    anchor_dates: dict[str, str | None],
    t: str,
) -> dict[str, dict[str, float | None]]:
    """``{기간: {종목: Σ VolumeWon over (anchor_date, t]}}`` — anchor 부재 시 그 기간은 빈 dict.

    반환은 `_anchor_returns` 와 동형(같은 ``_PERIODS`` 라벨 키)이라 동일한 anchor 창을
    공유함이 타입 수준에서 보인다(수익률·거래대금이 서로 다른 창을 쓰는 사고를 방지).
    """
    if not daily_db_path or not os.path.exists(daily_db_path):
        return {label: {} for label in _PERIODS}
    conn = sqlite3.connect(daily_db_path)
    try:
        per_period: dict[str, dict[str, float | None]] = {}
        for label in _PERIODS:
            a = anchor_dates.get(label)
            if a is None:
                per_period[label] = {}
                continue
            rows = conn.execute(
                "SELECT Name, SUM(VolumeWon) FROM stock_prices "
                "WHERE Date > ? AND Date <= ? GROUP BY Name",
                (a, t),
            ).fetchall()
            per_period[label] = {
                name: float(total) for name, total in rows if total is not None}
    finally:
        conn.close()
    return per_period


# @MX:NOTE: [AUTO] 앵커 기준 기간 수익률 — `Close(t) / Close(anchor(t, N)) − 1`.
#   앵커 바가 없거나(이력 부족, E7) 어느 한쪽 Close 가 결측·0 이면 **0 으로 접지 않고**
#   `None` 을 돌려준다(§9.1 상태 1). `anchor()` 는 정의상 완성 바(history_grid)만
#   반환하므로 앵커 쪽에 미완성 주 바가 섞이지 않는다(O-A8).
def _anchor_returns(
    conn: sqlite3.Connection, grid: Any, t: str
) -> tuple[dict[str, dict[str, float | None]], dict[str, str | None]]:
    """``({종목: {기간: 수익률%}}, {기간: 앵커 날짜})`` 를 돌려준다."""
    latest = dict(conn.execute(
        "SELECT Name, Close FROM stock_prices WHERE Date = ?", (t,)).fetchall())
    anchor_dates: dict[str, str | None] = {}
    per_period: dict[str, dict[str, float | None]] = {}
    for label, days in _PERIOD_LABEL_DAYS.items():
        bar = anchor(grid, t, days)
        anchor_dates[label] = bar.date if bar is not None else None
        if bar is None:
            per_period[label] = {}
            continue
        base = dict(conn.execute(
            "SELECT Name, Close FROM stock_prices WHERE Date = ?", (bar.date,)).fetchall())
        vals: dict[str, float | None] = {}
        for name, close in latest.items():
            b = base.get(name)
            if close is None or b is None or float(b) == 0:
                continue                       # 결측 — 대체값 없이 빠진다
            vals[name] = (float(close) / float(b) - 1.0) * 100
        per_period[label] = vals

    by_name: dict[str, dict[str, float | None]] = {
        name: {label: per_period[label].get(name) for label in _PERIODS}
        for name in latest
    }
    return by_name, anchor_dates


# @MX:NOTE: [AUTO] AC-SAG-024 — 규약 Y: MAX52 가 NULL(52주 이력 부족)인 종목은
#   신고가 판정의 분자·분모에서 모두 제외한다. NULL → 0.0 치환은 `Close >= 0` 을 항상
#   참으로 만들어 결측 처리 차이를 실질 판정 차이로 오계상한다(실측 차이 20건).
def _high52_map(
    conn: sqlite3.Connection, t: str, window_days: int = HIGH_52W_WINDOW_DAYS
) -> dict[str, float]:
    """``MAX(High)`` over ``(t − window_days, t]`` — weekly ``stock_prices`` 단일 원천.

    저장된 ``MAX52``(Close 기반, ``my_chart/price.py:148``)를 판정에 쓰지 않는다
    (REQ-SAG-022). 창 내 ``High`` 행이 하나도 없는 종목은 결과 dict 에서 빠진다
    (52주 최고가 산출 불가 — 분모에서 제외, AC-SAG-024 3번째 절).
    """
    from datetime import date as _date, timedelta as _timedelta

    win_start = (_date.fromisoformat(t) - _timedelta(days=window_days)).isoformat()
    try:
        rows = conn.execute(
            "SELECT Name, MAX(High) FROM stock_prices WHERE Date > ? AND Date <= ? "
            "GROUP BY Name",
            (win_start, t),
        ).fetchall()
    except sqlite3.OperationalError:
        # `High` 컬럼이 없는 최소 스키마 픽스처(단위 테스트 등) — 신고가 판정을
        # 전부 산출 불가(분모 제외)로 접는다. 라이브/집계 픽스처는 항상 보유.
        return {}
    return {name: float(high) for name, high in rows if high is not None}


def _build_member(
    name: str,
    row: dict[str, Any],
    caps: dict[str, float],
    high52_map: dict[str, float],
    returns: dict[str, float | None] | None = None,
    trading_value: dict[str, float | None] | None = None,
) -> _Member:
    close = row.get("Close")
    max52 = high52_map.get(name)
    nh: bool | None = None
    if close is not None and max52 is not None and float(max52) > 0:
        nh = float(close) >= float(max52) * (1 - _NH_THRESHOLD)

    stage2: bool | None = None
    if row.get("SMA10") is not None and row.get("SMA40") is not None:
        stage2 = classify_stage({**row, "Name": name}).stage == 2

    rs = row.get("RS_12M_Rating")
    return _Member(
        name=name,
        market_cap=caps.get(name),
        returns=dict(returns) if returns else {label: None for label in _PERIODS},
        rs=None if rs is None else float(rs),
        nh=nh,
        stage2=stage2,
        trading_value=(
            dict(trading_value) if trading_value else {label: None for label in _PERIODS}),
    )


def _ratio(valid: int, total: int) -> float | None:
    return None if total <= 0 else valid / total


def _equal_mean(values: list[float]) -> float | None:
    """결측을 **제외한** 등가중 평균. 유효 값이 없으면 ``None`` (0 반환 금지 — §9.1)."""
    return sum(values) / len(values) if values else None


def _metric(value: float | None) -> MetricValue:
    return missing() if value is None else present(value)


def _aggregate_members(
    sector_name: str,
    members: list[_Member],
    cap: float = WEIGHT_CAP,
) -> tuple[SectorAggregate, dict[str, float | None]]:
    """단일 섹터 집계 — ``(SectorAggregate, 등가중 폴백 수익률)``.

    규칙 적용:
      * **AG-3** 시총 NULL/``<=0`` 종목은 시총가중 분자·분모에서 제외하되 등가중 지표
        (``rs_avg`` / ``nh_pct`` / ``stage2_pct`` / ``member_count``)에는 포함한다.
      * **AG-4** 유효 시총 종목 < :data:`MIN_CAP_VALID_MEMBERS` → 시총가중 필드가
        ``null`` + ``reason:"insufficient"``, ``cap_weighted_available=False``.
      * **AG-7** 최상위 ``coverage_ratio`` 가 :data:`COVERAGE_NULL_THRESHOLD` **미만**이면
        시총가중 필드를 ``null``, :data:`COVERAGE_LOW_CONFIDENCE_THRESHOLD` 미만이면
        ``low_confidence=True``. 경계값(0.50 / 0.80 정확히)은 값을 유지한다.
    """
    n = len(members)
    cap_valid = [m for m in members if m.cap_valid]
    cap_valid_caps = {m.name: float(m.market_cap) for m in cap_valid}  # type: ignore[arg-type]

    # --- 지표별 유효 수 / 커버리지 (O-A6) -----------------------------------
    rs_values = [m.rs for m in members if m.rs is not None]
    nh_values = [m.nh for m in members if m.nh is not None]
    stage_values = [m.stage2 for m in members if m.stage2 is not None]
    chg_valid_by_period = {
        label: [m for m in members if m.returns[label] is not None]
        for label in _PERIODS
    }
    chg_valid_min = min(len(v) for v in chg_valid_by_period.values())

    coverage = Coverage(
        rs=_ratio(len(rs_values), n),
        nh=_ratio(len(nh_values), n),
        stage=_ratio(len(stage_values), n),
        chg=_ratio(chg_valid_min, n),
        # @MX:NOTE: [AUTO] trading_value 의 원천은 daily VolumeWon 이며 배선은 M5 소관이다.
        #   산출 대상이 아닌 지표를 0 으로 접으면 AG-7 최소값이 0 이 되어 전 섹터가 null
        #   이 되므로, None(미산출)으로 두고 Coverage.ratio 의 최소값에서 제외한다.
        trading_value=None,
    )
    valid_counts = ValidCounts(
        rs=len(rs_values), nh=len(nh_values), stage=len(stage_values),
        chg=chg_valid_min, trading_value=None,
    )
    coverage_ratio = coverage.ratio

    # --- 시총 커버리지 (AC-SAG-005) ------------------------------------------
    # 정의: 시총가중에 실제로 반영된 시총합 / 유효 시총합. 지표가 결측인 종목은 분자에서
    # 빠지므로 "이 숫자가 섹터 시총의 몇 %를 대표하는가"를 나타낸다. 기간별 최소값을 쓴다
    # (coverage_ratio 가 최소값인 것과 동일 관용).
    total_cap = sum(cap_valid_caps.values())
    cap_coverage: float | None = None
    if total_cap > 0:
        cap_coverage = min(
            sum(cap_valid_caps[m.name] for m in chg_valid_by_period[label] if m.cap_valid)
            / total_cap
            for label in _PERIODS
        )

    # --- 상한 재배분 가중치 (AG-1/AG-2) --------------------------------------
    weight_res = capped_weights_detail(cap_valid_caps, cap=cap)
    sector_effective_n = effective_n(weight_res.weights)

    ag4_ok = len(cap_valid) >= MIN_CAP_VALID_MEMBERS
    ag7_ok = coverage_ratio is not None and coverage_ratio >= COVERAGE_NULL_THRESHOLD
    cap_weighted_available = bool(ag4_ok and ag7_ok and weight_res.weights)
    low_confidence = bool(
        cap_weighted_available
        and coverage_ratio is not None
        and coverage_ratio < COVERAGE_LOW_CONFIDENCE_THRESHOLD
    )

    # --- 기간별 수익률 -------------------------------------------------------
    returns: dict[str, MetricValue] = {}
    equal_fallback: dict[str, float | None] = {}
    for label in _PERIODS:
        valid_members = chg_valid_by_period[label]
        equal_fallback[label] = _equal_mean(
            [m.returns[label] for m in valid_members])  # type: ignore[misc]

        if not valid_members:
            returns[label] = missing()          # 원천 값 없음(§9.1 상태 1)
            continue
        if not cap_weighted_available:
            returns[label] = insufficient()     # 산출 조건 미달(§9.1 상태 3)
            continue
        # 결측 종목을 제외한 뒤 **가중치를 재정규화**한다(AC-SAG-004).
        subset = {m.name: cap_valid_caps[m.name] for m in valid_members if m.cap_valid}
        sub_weights = capped_weights_detail(subset, cap=cap).weights
        value = weighted_mean(
            {m.name: m.returns[label] for m in valid_members}, sub_weights)  # type: ignore[misc]
        returns[label] = missing() if value is None else present(value)

    # --- M6-gap G16 — 기간별 거래대금 합계(단순 합산, 가중치 없음 — AC-SAG-029) -----
    trading_value: dict[str, MetricValue] = {}
    for label in _PERIODS:
        valid_tv = [m.trading_value.get(label) for m in members
                    if m.trading_value.get(label) is not None]
        trading_value[label] = present(sum(valid_tv)) if valid_tv else missing()

    rs_avg = _equal_mean(rs_values)                       # 결측 제외(§2.3)
    # REQ-RSR-013: 중앙값도 결측 제외 — 유효 값이 없으면 None(0 반환 금지)
    rs_med = statistics.median(rs_values) if rs_values else None
    rs_top = (sum(1 for r in rs_values if r >= _RS_TOP_THRESHOLD) / len(rs_values) * 100
              if rs_values else None)
    nh_pct = sum(1 for v in nh_values if v) / len(nh_values) * 100 if nh_values else None
    stage2_pct = (sum(1 for v in stage_values if v) / len(stage_values) * 100
                  if stage_values else None)

    aggregate = SectorAggregate(
        name=sector_name,
        member_count=n,
        valid_count=chg_valid_min,
        coverage_ratio=_metric(coverage_ratio),
        cap_coverage_ratio=_metric(cap_coverage),
        coverage=coverage,
        valid_counts=valid_counts,
        weight_cap=cap,
        effective_n=(_metric(sector_effective_n) if cap_weighted_available
                     else insufficient()),
        capped_members=weight_res.capped_members,
        cap_weighted_available=cap_weighted_available,
        low_confidence=low_confidence,
        returns=returns,
        trading_value=trading_value,
        # 초과수익률·composite·rank 는 벤치마크가 붙는 M3 소관이다. 지수 행 기준
        # 초과수익률을 여기에 실으면 규칙 BM-1(지수 행 사용 금지)을 어기게 된다.
        excess_returns={label: missing() for label in _PERIODS},
        rs_avg=_metric(rs_avg),
        rs_med=_metric(rs_med),
        rs_top_pct=_metric(rs_top),
        nh_pct=_metric(nh_pct),
        stage2_pct=_metric(stage2_pct),
        composite_score=missing(),
    )
    return aggregate, equal_fallback


# @MX:NOTE: [AUTO] 벤치마크 = 섹터 그룹핑 없는 전체 유니버스 집계(규칙 BM-1,
#   plan.md §3.2). `_aggregate_members` 를 섹터 집계와 **같은 함수**로 호출해
#   EX-1(방법론 일치)·BM-2 를 테스트가 아니라 타입 수준에서 보장한다(D1/D2) —
#   별도 벤치마크 구현을 두면 유니버스·상한·결측 처리가 조용히 갈릴 수 있다.
def _compute_benchmark(
    all_members: list[_Member],
    cap: float,
    market_key: str,
    anchor_dates: dict[str, str | None],
) -> BenchmarkInfo:
    """규칙 BM-1 ~ BM-6 벤치마크 산출.

    ``anchor_dates`` 는 섹터 집계와 **같은 `_anchor_returns` 호출**(같은 `t`)에서 나온
    값을 그대로 받는다 — 벤치마크가 앵커를 독립적으로 다시 구하지 않는 것이 BM-6
    보존의 유일 조건이다(plan.md 기술 노트).
    """
    name = _MARKET_BENCHMARK_NAMES.get(market_key, f"{market_key.upper()}_CAPPED")
    if not all_members:
        # 규칙 BM-4/BM-5 — 구성종목 0 이면 벤치마크 산출이 불가능하다.
        return BenchmarkInfo(
            name=name, status="unavailable", returns={},
            anchor_date=anchor_dates.get("1w"), universe_size=0,
            weight_cap=cap, error="벤치마크 유니버스가 비어 있다(구성종목 0) — 산출 불가")
    aggregate, _fallback = _aggregate_members("__benchmark__", all_members, cap=cap)
    return BenchmarkInfo(
        name=name, status="ok", returns=dict(aggregate.returns),
        anchor_date=anchor_dates.get("1w"), universe_size=len(all_members),
        weight_cap=cap, error=None)


def _excess_returns(
    sector_returns: dict[str, MetricValue], benchmark_returns: dict[str, MetricValue]
) -> dict[str, MetricValue]:
    """규칙 EX-2 — 섹터 초과수익률 = 섹터 수익률 − 벤치마크 수익률(기간별).

    두 값 모두 non-null 일 때만 산출한다(§9.1 상태 1 — 결측을 0 으로 접지 않는다).
    """
    out: dict[str, MetricValue] = {}
    for label in _PERIODS:
        s = sector_returns.get(label)
        b = benchmark_returns.get(label)
        if s is None or b is None or s.value is None or b.value is None:
            out[label] = missing()
        else:
            out[label] = present(s.value - b.value)
    return out


def _benchmark_reconciliation_warnings(
    conn: sqlite3.Connection,
    date: str,
    market_key: str,
    uncapped_returns: dict[str, MetricValue],
) -> list[str]:
    """규칙 BM-3 — 지수 행(``Name='KOSPI'``/``'KOSDAQ'``) 대비 정합성 경고(AC-SAG-015).

    ``market=all`` 은 단일 지수 행이 없으므로 대상에서 제외한다. 임계 초과 시에만
    경고를 싣는다(§8.4 규약 3 — 부분집합 유니버스가 전체 지수를 재현하지 못하는 것은
    결함이 아니라 산술이므로 항상 기록하지 않는다).
    """
    index_name = {"kospi": "KOSPI", "kosdaq": "KOSDAQ"}.get(market_key)
    if index_name is None:
        return []
    row = conn.execute(
        "SELECT CHG_1W, CHG_1M, CHG_3M FROM stock_prices WHERE Name = ? AND Date = ?",
        (index_name, date),
    ).fetchone()
    if not row:
        return []
    index_pct = {"1w": row[0], "1m": row[1], "3m": row[2]}
    out: list[str] = []
    for label in _PERIODS:
        idx_val = index_pct.get(label)
        bench = uncapped_returns.get(label)
        if idx_val is None or bench is None or bench.value is None:
            continue
        diff_pp = bench.value - float(idx_val) * 100
        threshold = BENCHMARK_RECONCILIATION_TOLERANCE_PP[label]
        if abs(diff_pp) > threshold:
            out.append(
                f"benchmark_reconciliation_warning: period={label} market={market_key} "
                f"diff_pp={diff_pp:.6f}")
    return out


def _rank_sectors(
    aggregates: list[SectorAggregate], period: str | None = None,
) -> list[ExcludedSector]:
    """규칙 AG-9(composite_score) · RK-1(결정적 tie-break) · RK-2(반올림 미포함).

    ``aggregates`` 를 in-place 로 갱신한다. **이 함수 내부에 ``round(`` 호출이 없다**
    (AC-SAG-020 정적 스캔 — 반올림은 직렬화 직전 1회만 수행한다, `backend/schemas/envelope.py`).

    Args:
        period: ``None`` 이면 종전과 동일하게 3기간 가중 composite 로 순위를 매긴다.
            ``"1w"``/``"1m"``/``"3m"`` 중 하나면 **그 기간의 초과수익률 단독**으로
            순위를 매긴다(AC-SAG-021 — M6-gap G22). ``composite_score`` 필드는
            어느 경우든 항상 3기간 가중 composite 값을 유지한다(AC-SAG-022).

    Returns:
        composite 산출이 불가능해 순위 대상에서 제외된 섹터 목록(``excluded[]`` 후보,
        규칙 AG-9 — "excess_3m 이 null 인 섹터는 부분 점수 산출 금지").
    """
    candidates = [
        a for a in aggregates
        if a.excess_returns
        and all(a.excess_returns.get(p) is not None and a.excess_returns[p].value is not None
                for p in _PERIODS)
    ]
    newly_excluded: list[ExcludedSector] = []
    for a in aggregates:
        if a in candidates:
            continue
        a.composite_score = missing()
        a.rank = None
        if a.excess_returns:
            newly_excluded.append(ExcludedSector(a.name, "excess_return_missing", a.member_count))

    if not candidates:
        return newly_excluded

    norm_by_period = {
        p: norm([a.excess_returns[p].value for a in candidates]) for p in _PERIODS
    }
    raw_scores = [
        sum(_COMPOSITE_WEIGHTS[p] * norm_by_period[p][i] for p in _PERIODS)
        for i in range(len(candidates))
    ]
    for i, a in enumerate(candidates):
        a.composite_score = present(raw_scores[i])

    # M6-gap G22 — `period` 지정 시 그 기간의 (원시, 정규화 전) 초과수익률 단독을
    # 순위 기준으로 쓴다(AC-SAG-021 "rank는 해당 (period, market)의 초과수익률
    # 기준"). 미지정이면 종전과 동일하게 composite 로 순위를 매긴다.
    if period in _PERIODS:
        rank_key = [candidates[i].excess_returns[period].value for i in range(len(candidates))]
    else:
        rank_key = raw_scores

    # RK-1 — 결정적 tie-break: 순위 기준 내림차순, 동점은 섹터명 사전순.
    order = sorted(range(len(candidates)), key=lambda i: (-rank_key[i], candidates[i].name))
    for rank_i, idx in enumerate(order, start=1):
        candidates[idx].rank = rank_i
    return newly_excluded


def compute_return_window_days(
    anchor_dates: dict[str, str | None], t: str
) -> dict[str, int | None]:
    """REQ-SAG-043 — 실제 창 일수 ``(t − anchor_date).days``. 라벨 상수(7/28/91)가 아니다."""
    from datetime import date as _date

    t_d = _date.fromisoformat(t)
    out: dict[str, int | None] = {}
    for label in _PERIODS:
        a = anchor_dates.get(label)
        out[label] = (t_d - _date.fromisoformat(a)).days if a else None
    return out


def _market_matches(market: str | None, market_key: str) -> bool:
    if market_key in ("", "all"):
        return True
    return str(market or "").strip().upper() == market_key.upper()


def _load_registry_mapping(
    registry_path: str | None = None,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """registry → ``(섹터별 종목 목록, 종목별 시장)`` (규칙 UN-1 — 섹터 소속 단일 원천).

    ``registry_path`` 를 주면 그 파일을 직접 dedup 로드한다. ``None`` 이면 모듈 수준에
    캐시되는 :func:`get_sector_registry` 를 쓴다 — 캐시는 경로 인자를 받지 않으므로
    픽스처 고정이 필요한 호출자는 **반드시 경로를 명시**한다.
    """
    if registry_path:
        df_sector, _dups = load_sector_registry_with_diagnostics(registry_path)
    else:
        df_sector = get_sector_registry()
    sector_to_stocks: dict[str, list[str]] = {}
    market_of: dict[str, str] = {}
    for _, row in df_sector.iterrows():
        name = str(row["Name"])
        sector = str(row.get("산업명(대)") or ETC_SECTOR)
        sector_to_stocks.setdefault(sector, []).append(name)
        if "Market" in row:
            market_of[name] = str(row.get("Market") or "")
    return sector_to_stocks, market_of


def _valid_universe(
    weekly_db_path: str,
    daily_db_path: str | None,
    registry_path: str | None,
    as_of: str | None,
) -> set[str] | None:
    """유효 유니버스(규칙 UN-3) — ① SPEC-SECTOR-GRID-001 의 산출물을 **소비만** 한다.

    일봉 DB 경로가 없으면 ``None``(=제한 없음)을 돌려준다. 라이브 DB 를 암묵적으로
    열지 않기 위한 의도적 동작이며, 그 경우 registry ∩ 주봉 스냅샷이 구성원이 된다.
    """
    if not daily_db_path or not os.path.exists(daily_db_path):
        return None
    try:
        snap = compute_universe(
            weekly_db_path, daily_db_path,
            registry_path or str(SECTORMAP_PATH), as_of=as_of)
    except Exception as exc:                    # 원천 부재 등 — 제한 없이 진행
        logger.warning("유효 유니버스 산출 실패 — 유니버스 제한 없이 집계한다: %s", exc)
        return None
    return set(snap.valid_names)


@dataclass(frozen=True)
class _SharedInputs:
    """여러 기준일을 연달아 집계할 때 **날짜와 무관한** 입력을 한 번만 계산해 넘기는 묶음.

    ``compute_sector_history`` 와, 같은 기준일을 두 번(기간 순위·composite 순위) 집계하는
    표 엔드포인트(``period`` 지정 시)가 쓴다 — :func:`build_shared_inputs` 참조.
    두 필드가 기준일 ``d`` 마다 새로 계산한 값과 같은 결과를 내는 근거:

    * ``universe`` — :func:`compute_universe` 는 격자의 ``latest.date``(as_of 와 무관하게
      DB 최신 정규 바)와 일봉 최신 거래일만 쓴다. ``as_of`` 는 ``is_partial_week`` 판정에만
      들어가고 유니버스는 그 값을 읽지 않으므로, 어느 ``as_of`` 로 계산해도 같다.
    * ``grid`` — ``as_of`` 가 다른 두 격자는 최신 바 ``L`` 이 ``history`` 에 들어가는지만
      다르다. 히스토리 날짜 ``d`` 는 항상 ``d <= L`` 이고 앵커는 ``d − N``(N ∈ 7/28/91)
      이하 바를 고르므로 ``L`` 이 앵커로 뽑힐 수 없다 — ``anchor()`` 결과가 같다.
      (결과의 ``as_of_is_partial_week`` 필드만 달라질 수 있는데 히스토리는 읽지 않는다.)
    * ``registry_mapping`` — :func:`_load_registry_mapping` 의 (섹터별 종목, 종목별 시장)은
      registry 만의 함수라 기준일과 무관하다. 히스토리 호출은 ``registry_path=None``
      (모듈 캐시)만 쓰므로 같은 값을 매 날짜 다시 순회할 이유가 없다.
    """

    grid: Any
    universe: set[str] | None
    registry_mapping: tuple[dict[str, list[str]], dict[str, str]]


def build_shared_inputs(
    weekly_db_path: str, daily_db_path: str | None, as_of: str,
) -> _SharedInputs:
    """기준일 ``as_of`` 로 :func:`_compute_sector_aggregates_core` 가 스스로 계산할 것과
    **같은** 날짜 무관 입력을 미리 만든다(registry 는 모듈 캐시 — ``registry_path=None``).

    같은 기준일을 ``period`` 만 바꿔 두 번 집계할 때(표 엔드포인트의 ``data[]`` 기간 순위 +
    ``sectors[]`` composite 순위) 유효 유니버스(registry xlsx 재독)를 한 번만 계산하려는 용도다.
    """
    return _SharedInputs(
        grid=compute_weekly_grid(weekly_db_path, as_of),
        universe=_valid_universe(weekly_db_path, daily_db_path, None, as_of),
        registry_mapping=_load_registry_mapping(None))


def _compute_sector_aggregates_core(
    weekly_db_path: str,
    date: str,
    daily_db_path: str | None,
    registry_path: str | None,
    market: str,
    cap: float,
    as_of: str | None,
    apply_min_members: bool,
    period: str | None = None,
    shared: _SharedInputs | None = None,
    equal_weight_fallback: bool = False,
) -> SectorAggregationResult:
    """`compute_sector_aggregates` 의 rank_change 를 제외한 나머지 전체(벤치마크 ~ 순위).

    별도 함수로 분리한 이유는 rank_change 산출이 ``anchor(t, 28)`` 기준일에서 **같은
    집계를 재귀 없이 1회 더** 호출해야 하기 때문이다(M3) — 공개 함수가 이 core 를
    두 번(현재·기준일) 호출한다.

    ``shared`` 가 주어지면 격자·유효 유니버스·registry 매핑을 다시 계산하지 않고 그 값을 쓴다
    (:class:`_SharedInputs` — 히스토리 전용, 기본 ``None`` 이면 종전과 동일).
    """
    grid = shared.grid if shared is not None else compute_weekly_grid(weekly_db_path, as_of or date)
    conn = sqlite3.connect(weekly_db_path, check_same_thread=False)
    try:
        snapshot = _load_weekly_snapshot(conn, date)
        returns_by_name, anchor_dates = _anchor_returns(conn, grid, date)
        high52_map = _high52_map(conn, date)
        caps = _load_market_caps(daily_db_path)
        sector_to_stocks, market_of = (
            shared.registry_mapping if shared is not None
            else _load_registry_mapping(registry_path))
        universe = (
            shared.universe if shared is not None
            else _valid_universe(weekly_db_path, daily_db_path, registry_path, as_of or date))
        # M6-gap G16 — 섹터 집계 거래대금(기간별 합산, O-A4 창 공유). anchor_dates 는
        # 위 `_anchor_returns` 와 같은 호출에서 나온 값이므로 수익률과 창을 공유한다.
        trading_value_by_period = compute_trading_value_by_period(
            daily_db_path, anchor_dates, date)

        warnings: list[str] = []
        if not caps:
            warnings.append(
                "시총 원천(daily stock_meta)을 읽지 못해 시총가중 집계가 불가능하다 — "
                "AG-4 에 따라 시총가중 필드가 null 로 보고된다")

        market_key = (market or "all").lower()
        aggregates: list[SectorAggregate] = []
        equal_by_name: dict[str, dict[str, float | None]] = {}   # 등가중 대체 수익률(히스토리 전용)
        excluded: list[ExcludedSector] = []
        all_members: list[_Member] = []          # 규칙 BM-1 — 섹터 그룹핑 없는 벤치마크 유니버스
        for sector_name, stock_names in sector_to_stocks.items():
            members = [
                _build_member(
                    name, snapshot[name], caps, high52_map, returns_by_name.get(name),
                    trading_value={
                        label: trading_value_by_period[label].get(name) for label in _PERIODS},
                )
                for name in stock_names
                if name in snapshot
                and name not in _INDEX_NAMES
                and (universe is None or name in universe)
                and _market_matches(market_of.get(name), market_key)
            ]
            all_members.extend(members)
            if not members:
                excluded.append(ExcludedSector(sector_name, "no_members", 0))
                continue
            if apply_min_members and len(members) < MIN_SECTOR_MEMBERS:
                # 규칙 AG-5 — 구성종목 부족 섹터는 순위 대상에서 제외한다.
                excluded.append(
                    ExcludedSector(sector_name, "insufficient_members", len(members)))
                continue
            aggregate, equal_fallback = _aggregate_members(sector_name, members, cap=cap)
            aggregates.append(aggregate)
            equal_by_name[sector_name] = equal_fallback

        # --- 규칙 BM-1 ~ BM-6 벤치마크(EX-1/EX-2 구조 보장 — 같은 `_aggregate_members`) --
        benchmark = _compute_benchmark(all_members, cap, market_key, anchor_dates)
        for a in aggregates:
            if equal_weight_fallback and not a.cap_weighted_available:
                # 히스토리(Bump) 전용 — AG-4/AG-7 로 시총가중이 null 이 된 섹터는 등가중
                # 수익률로 대체한다(3기간 모두 있을 때만). 표 경로는 이 인자를 넘기지 않는다.
                eq = equal_by_name[a.name]
                if all(eq[label] is not None for label in _PERIODS):
                    a.returns = {
                        label: present(eq[label]) for label in _PERIODS}  # type: ignore[arg-type]
            a.excess_returns = _excess_returns(a.returns, benchmark.returns)
        if benchmark.status == "ok":
            uncapped = _compute_benchmark(all_members, 1.0, market_key, anchor_dates).returns
            warnings.extend(
                _benchmark_reconciliation_warnings(conn, date, market_key, uncapped))
        else:
            # 규칙 BM-4/BM-5 — 벤치마크 부재 시 전 섹터 초과수익률·순위를 null 로 만든다.
            for a in aggregates:
                a.excess_returns = {label: missing() for label in _PERIODS}

        # --- 규칙 AG-8/AG-9/RK-1/RK-2 순위·정규화 -------------------------------
        # M6-gap G22 — `period` 가 주어지면 그 기간의 초과수익률 단독으로 순위를
        # 매긴다(AC-SAG-021). `composite_score` 는 항상 3기간 가중합으로 계산되며
        # `period` 와 무관하다(AC-SAG-022 — composite_score 는 rank 와 함께 존재).
        excluded.extend(_rank_sectors(aggregates, period=period))

        # --- AC-SAG-013 부호 분산 정합성(합성 픽스처용, 비게이팅 보조) -----------
        w1_excess = [a.excess_returns["1w"].value for a in aggregates
                     if a.excess_returns.get("1w") is not None
                     and a.excess_returns["1w"].value is not None]
        if w1_excess and (all(v > 0 for v in w1_excess) or all(v < 0 for v in w1_excess)):
            warnings.append("benchmark_reconciliation_warning: 1w excess distribution degenerate")

        return_window_days = compute_return_window_days(anchor_dates, date)
        partial = grid.latest.is_partial_week if grid.latest is not None else None
    finally:
        conn.close()

    return SectorAggregationResult(
        aggregates=aggregates, excluded=excluded, warnings=warnings,
        benchmark=benchmark, return_window_days=return_window_days,
        as_of_is_partial_week=partial)


def compute_sector_aggregates(
    weekly_db_path: str,
    date: str,
    daily_db_path: str | None = None,
    registry_path: str | None = None,
    market: str = "all",
    cap: float = WEIGHT_CAP,
    as_of: str | None = None,
    apply_min_members: bool = True,
    compute_rank_change: bool = True,
    period: str | None = None,
    shared: _SharedInputs | None = None,
    equal_weight_fallback: bool = False,
) -> SectorAggregationResult:
    """섹터별 시총가중 집계(규칙 AG-1 ~ AG-9, BM-1 ~ BM-6) — 응답 ``data[]`` 의 단일 산출 경로.

    Args:
        weekly_db_path: 주봉 DB 경로.
        date: 기준일(정규 격자 대표 바).
        daily_db_path: 일봉 DB 경로(``stock_meta.market_cap`` 단일 원천).
        registry_path: registry xlsx 경로. ``None`` 이면 모듈 캐시를 쓴다.
        market: ``all`` / ``kospi`` / ``kosdaq``. 필터는 **집계 시점**에 적용되므로
            ``member_count`` 자체가 달라진다.
        cap: 종목 비중 상한(AG-1).
        as_of: 진행 중인 주 판정 기준일. 게이팅 호출은 **반드시 명시**한다
            (acceptance.md §8.4 규약 8 — 기본값 ``date.today()`` 의존 금지).
        apply_min_members: ``True`` 면 AG-5(최소 구성종목 5) 미달 섹터를 ``data[]`` 에서
            빼고 ``excluded[]`` 에 등록한다.
        compute_rank_change: ``True`` 면 ``anchor(t, 28)`` 기준일 대비 ``rank_change`` 를
            산출한다(AC-SAG-023). 기준일 재귀 호출은 이 인자를 ``False`` 로 넘겨
            **1단만** 내려간다(무한 재귀 방지).
        period: ``None`` 이면 composite 순위(종전 동작). ``"1w"``/``"1m"``/``"3m"`` 면
            그 기간의 초과수익률 단독으로 순위를 매긴다(AC-SAG-021 — M6-gap G22).
            기준일 재귀 호출에도 **같은 period** 를 넘겨 ``rank_change`` 가 동일
            기준(같은 period)의 순위 이동을 비교하도록 한다.
        shared: 날짜 무관 입력(격자·유효 유니버스·registry 매핑) 사전 계산값 —
            ``compute_sector_history`` 전용(:class:`_SharedInputs`). ``None``(기본)이면
            종전과 동일하게 매번 계산한다.
            rank_change 기준일 집계에는 넘기지 않는다.
        equal_weight_fallback: ``True`` 면 시총가중이 AG-4/AG-7 로 null 인 섹터의 수익률을
            등가중 수익률로 대체해 순위에 넣는다 — ``compute_sector_history``(Bump) 전용.
            ``False``(기본)이면 종전과 동일하다(표·알림 경로는 넘기지 않는다).
    """
    result = _compute_sector_aggregates_core(
        weekly_db_path, date, daily_db_path, registry_path, market, cap, as_of,
        apply_min_members, period=period, shared=shared,
        equal_weight_fallback=equal_weight_fallback)

    if compute_rank_change:
        grid = compute_weekly_grid(weekly_db_path, as_of or date)
        baseline_bar = anchor(grid, as_of or date, 28)
        if baseline_bar is not None:
            baseline = _compute_sector_aggregates_core(
                weekly_db_path, baseline_bar.date, daily_db_path, registry_path, market, cap,
                baseline_bar.date, apply_min_members, period=period,
                equal_weight_fallback=equal_weight_fallback)
            prev_rank = {a.name: a.rank for a in baseline.aggregates}
            for a in result.aggregates:
                p = prev_rank.get(a.name)
                a.rank_change = (p - a.rank) if (p is not None and a.rank is not None) else None
            result.baseline_date = baseline_bar.date

    return result


def compute_sector_history(
    db_path: str,
    weeks: int = 12,
    daily_db_path: str | None = None,
    market: str = "all",
    period: str | None = None,
    as_of: str | None = None,
) -> tuple[list[str], list[list[SectorAggregate]]]:
    """최근 N주 섹터 랭킹 히스토리를 계산한다(끝난 주만 — 잠정점 없음).

    :func:`compute_sector_history_with_provisional` 의 앞 두 값이다. 인자·반환 계약은 같다.
    """
    dates, rankings, _provisional = compute_sector_history_with_provisional(
        db_path, weeks=weeks, daily_db_path=daily_db_path, market=market,
        period=period, as_of=as_of)
    return dates, rankings


def compute_sector_history_with_provisional(
    db_path: str,
    weeks: int = 12,
    daily_db_path: str | None = None,
    market: str = "all",
    period: str | None = None,
    as_of: str | None = None,
) -> tuple[list[str], list[list[SectorAggregate]],
           tuple[str, list[SectorAggregate]] | None]:
    """최근 N주 섹터 랭킹 히스토리 + 진행 중인 주의 잠정 순위를 계산한다.

    날짜는 정규 주간 격자(SPEC-SECTOR-GRID-001 REQ-SGR-001 ``compute_weekly_grid``)의
    ``history`` 에서 파생한다 — CG-1(ISO 주당 1바)·CG-3(부분 데이터 행 수 배제) 가 이미
    적용됐으므로 자체 행수-중앙값×0.5 부분데이터 가드는 폐기한다(AC-SGR-006-B B-2).
    ``(dates, rankings)`` 반환 계약과 last-N-weeks 의미는 유지한다(WIP 보존).

    Args:
        db_path: weekly SQLite DB 경로.
        weeks: 조회 주수.
        daily_db_path: 일봉 DB 경로 — M6 신설. ``compute_sector_aggregates`` 에 그대로
            넘긴다(시총가중 원천).
        market: ``all`` / ``kospi`` / ``kosdaq`` — M6 신설(AC-SAG-039).
        period: ``None`` 이면 composite 순위(종전 동작). ``"1w"``/``"1m"``/``"3m"`` 면 표의
            같은 기간 탭과 같은 기준(그 기간 초과수익률 단독, AC-SAG-021)으로 순위를 매긴다.
        as_of: 진행 중인 주 판정 기준일(``compute_weekly_grid`` 와 같다). ``None`` 이면 오늘 —
            표 엔드포인트의 라이브 기본값과 같다. 테스트는 명시 인자로 고정한다(§8.4 규약 8).

    Returns:
        (dates, rankings, provisional) 튜플. provisional 은 최신 격자 바가 부분 주일 때
        ``(그 날짜, 순위 리스트)``, 아니면 ``None`` (아래 @MX:NOTE).
        dates·rankings: dates는 정규 격자 history 의 최근 weeks 개(오름차순),
        rankings는 각 날짜에서 **순위가 매겨진** 섹터의 :class:`SectorAggregate` 리스트
        (rank 오름차순). AG-5 는 적용하지 않고 AG-4/AG-7 섹터는 등가중으로 대체한다
        (AC-SUX-019, 아래 @MX:NOTE). 그래도 순위가 없는 섹터(``rank is None``)는 그 날짜에서 빠진다.
        둘은 같은 길이·같은 순서.
    """
    grid = compute_weekly_grid(db_path, as_of)
    all_history = [bar.date for bar in grid.history]
    history_dates = all_history[-weeks:] if weeks > 0 else all_history

    if not history_dates:
        return [], [], None

    # @MX:NOTE: [AUTO] Bump 순위 원천 = 섹터 표와 같은 `compute_sector_aggregates(period=...)`.
    #   화면은 표의 기간 탭(1W/1M/3M)을 그대로 넘겨 표와 같은 기간 단독 순위를 그린다(2026-10-21
    #   사용자 결정 — 355주 실측에서 종합점수 대비 예측력 차이 없이 순위 흔들림만 커서). period=None 은 composite.
    #   종전에는 레거시 순위 함수(min-max 정규화, 제거됨)를 탔고, 3M 초과수익률
    #   극단값 섹터가 Bump 에서만 1위로 뛰는 불일치가 있었다(라이브 2026-10-16 비철금속: Bump 1위,
    #   표 5위). 이제 각 날짜 d 의 순위는 같은 period 로 매긴 표 순위와, composite 는 표의 순위
    #   백분위(AG-8) 값과 같다.
    #   `as_of=d` 로 고정해 오늘 날짜에 기대지 않는다(acceptance.md §8.4 규약 8).
    #   격자·유효 유니버스·registry 매핑은 날짜와 무관하므로 한 번만 계산해 넘긴다
    #   (_SharedInputs 근거 참조) — 유니버스 산출이 registry xlsx 를 매번 다시 읽어
    #   날짜당 ~0.5초가 들었다.
    # @MX:NOTE: [AUTO] AG-5 예외(AC-SUX-019) — Bump 는 AG-5 를 적용하지 않는다: 표 excluded[]
    #   섹터도 선이 있어야 한다. `apply_min_members=False` + `equal_weight_fallback=True` 로,
    #   AG-4/AG-7 로 시총가중 수익률이 null 인 섹터(구성종목 < 5 섹터뿐 아니라 유효 시총 < 5 거나
    #   커버리지 < 0.50 인 ≥ 5 종목 섹터도)는 등가중 수익률 − 벤치마크를 초과수익률로 써서
    #   전 섹터를 같은 기준(period 단독 또는 composite)으로 순위 매긴다. 대체 섹터가 없는 날짜(라이브
    #   market=all)의 순위는 같은 period 의 표 순위와 정확히 같고, 대체 섹터가 있으면 Bump 의 순위
    #   분모가 표보다 크다(사용자 결정 — 공통 섹터의 상대 순서는 같다). 3기간 수익률이 하나라도 없는 섹터(3M 앵커 없음 등)는 여전히 빠진다.
    shared = _SharedInputs(
        grid=grid,
        universe=_valid_universe(db_path, daily_db_path, None, history_dates[-1]),
        registry_mapping=_load_registry_mapping(None))
    def _ranked_at(date: str) -> list[SectorAggregate]:
        result = compute_sector_aggregates(
            db_path, date, daily_db_path, market=market, as_of=date,
            compute_rank_change=False, period=period, shared=shared,
            apply_min_members=False, equal_weight_fallback=True)
        ranked = [a for a in result.aggregates if a.rank is not None]
        ranked.sort(key=lambda a: a.rank)
        return ranked

    rankings = [_ranked_at(date) for date in history_dates]

    # @MX:NOTE: [AUTO] 잠정점(2026-10-22 사용자 결정) — 표(/sectors/ranking)는 격자 `latest`
    #   (진행 중인 주 바 포함, `_get_latest_valid_date`)로 순위를 매기지만 `history` 는 끝난 주만
    #   담아 Bump 마지막 점이 표보다 한 주 늦었다. 최신 바가 부분 주면 그 날짜를 같은 호출로 한 번 더
    #   집계해 잠정 순위로 돌려준다. `as_of=latest.date` 여도 같은 ISO 주의 일요일 이전이라 부분 주
    #   판정은 그대로이고, 수익률 앵커는 `history`(최신 바 제외)에서만 고르므로 표와 같은 창을 쓴다.
    #   dates/rankings 에는 넣지 않는다 — 끝난 주 last-N 계약(AC-SAG-040 len(dates)==weeks)을 지킨다.
    latest = grid.latest
    provisional = (
        (latest.date, _ranked_at(latest.date))
        if latest is not None and latest.is_partial_week and latest.date > history_dates[-1]
        else None)
    return history_dates, rankings, provisional
