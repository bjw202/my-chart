"""Sector strength metrics and ranking engine.

Computes sector-level aggregated metrics from weekly DB and sector registry.
Ranks sectors by composite score.

Per SPEC-TOPDOWN-001A R7-R8.
"""

from __future__ import annotations

import logging
import os
import sqlite3
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

# Composite score weights per SPEC R8
_COMPOSITE_W_1W = 0.3
_COMPOSITE_W_1M = 0.4
_COMPOSITE_W_3M = 0.3

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


@dataclass
class SectorRank:
    """Sector ranking result with all SPEC-required fields.

    하위 호환 표면이다(plan.md §1 D4). SPEC-SECTOR-AGGREGATION-001 의 결측 3상태·커버리지
    계약은 :class:`~my_chart.analysis.aggregate_types.SectorAggregate` (응답 ``data[]``)가
    소유하며, 이 dataclass 의 float 필드는 **null 을 표현할 수 없다** — 따라서 시총가중
    산출이 불가능한 경우(AG-4/AG-7) 등가중 값으로 되돌아간다(아래 각 필드 주석).
    """

    name: str                      # 산업명(대)
    stock_count: int
    # @MX:NOTE: [AUTO] 아래 세 필드는 M2 부터 **상한 재배분 시총가중**(AG-1) 값이다.
    #   M2 이전 주석은 "market-cap weighted" 라고 적혀 있었으나 실제 구현은 `sum/n`
    #   등가중이었다(구 :173-175). 주석만 시총가중이고 코드는 등가중인 상태가 오래
    #   유지됐고, 그 괴리가 본 SPEC 의 출발점이다(plan.md §2 M2 "거짓 주석 정정").
    #   현재 계약: 유효 시총 종목 >= 5 이고 커버리지 >= 0.50 이면 시총가중,
    #   그렇지 않으면 **등가중으로 폴백**한다(이 표면은 null 을 실을 수 없다).
    #   null 이 필요한 소비자는 응답 `data[]` 의 SectorAggregate.returns 를 읽어야 한다.
    sector_return_1w: float        # 상한재배분 시총가중, anchor(t,7) 기준 (%) — 폴백 등가중
    sector_return_1m: float        # 상한재배분 시총가중, anchor(t,28) 기준 (%) — 폴백 등가중
    sector_return_3m: float        # 상한재배분 시총가중, anchor(t,91) 기준 (%) — 폴백 등가중
    sector_excess_return_1w: float # sector - KOSPI 1W return
    sector_excess_return_1m: float # sector - KOSPI 1M return
    sector_excess_return_3m: float # sector - KOSPI 3M return
    sector_rs_avg: float           # avg RS_12M_Rating
    sector_rs_top_pct: float       # % stocks with RS >= 80
    sector_nh_pct: float           # % stocks at 52-week high
    sector_stage2_pct: float       # % stocks classified Stage 2
    composite_score: float         # 0-100 ranking score
    rank: int = 0
    rank_change: int = 0           # positive = improved, negative = declined


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


def _load_kospi_returns(conn: sqlite3.Connection, date: str) -> dict[str, float]:
    """Load KOSPI index returns for the given date."""
    row = conn.execute(
        "SELECT CHG_1W, CHG_1M, CHG_3M FROM stock_prices WHERE Name = 'KOSPI' AND Date = ?",
        (date,),
    ).fetchone()
    if not row:
        return {"chg_1w": 0.0, "chg_1m": 0.0, "chg_3m": 0.0}
    return {
        "chg_1w": float(row[0] or 0.0) * 100,  # convert to %
        "chg_1m": float(row[1] or 0.0) * 100,
        "chg_3m": float(row[2] or 0.0) * 100,
    }


def _normalize_list(values: list[float]) -> list[float]:
    """Min-max normalize a list of values to 0-100 range."""
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [50.0] * len(values)
    return [(v - min_v) / (max_v - min_v) * 100 for v in values]


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

    rs_avg = _equal_mean(rs_values)                       # 결측 제외(§2.3)
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
        # 초과수익률·composite·rank 는 벤치마크가 붙는 M3 소관이다. 지수 행 기준
        # 초과수익률을 여기에 실으면 규칙 BM-1(지수 행 사용 금지)을 어기게 된다.
        excess_returns={label: missing() for label in _PERIODS},
        rs_avg=_metric(rs_avg),
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


def _rank_sectors(aggregates: list[SectorAggregate]) -> list[ExcludedSector]:
    """규칙 AG-9(composite_score) · RK-1(결정적 tie-break) · RK-2(반올림 미포함).

    ``aggregates`` 를 in-place 로 갱신한다. **이 함수 내부에 ``round(`` 호출이 없다**
    (AC-SAG-020 정적 스캔 — 반올림은 직렬화 직전 1회만 수행한다, `backend/schemas/envelope.py`).

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
    # RK-1 — 결정적 tie-break: composite 내림차순, 동점은 섹터명 사전순.
    order = sorted(range(len(candidates)), key=lambda i: (-raw_scores[i], candidates[i].name))
    for rank_i, idx in enumerate(order, start=1):
        a = candidates[idx]
        a.composite_score = present(raw_scores[idx])
        a.rank = rank_i
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


def _compute_sector_aggregates_core(
    weekly_db_path: str,
    date: str,
    daily_db_path: str | None,
    registry_path: str | None,
    market: str,
    cap: float,
    as_of: str | None,
    apply_min_members: bool,
) -> SectorAggregationResult:
    """`compute_sector_aggregates` 의 rank_change 를 제외한 나머지 전체(벤치마크 ~ 순위).

    별도 함수로 분리한 이유는 rank_change 산출이 ``anchor(t, 28)`` 기준일에서 **같은
    집계를 재귀 없이 1회 더** 호출해야 하기 때문이다(M3) — 공개 함수가 이 core 를
    두 번(현재·기준일) 호출한다.
    """
    grid = compute_weekly_grid(weekly_db_path, as_of or date)
    conn = sqlite3.connect(weekly_db_path, check_same_thread=False)
    try:
        snapshot = _load_weekly_snapshot(conn, date)
        returns_by_name, anchor_dates = _anchor_returns(conn, grid, date)
        high52_map = _high52_map(conn, date)
        caps = _load_market_caps(daily_db_path)
        sector_to_stocks, market_of = _load_registry_mapping(registry_path)
        universe = _valid_universe(weekly_db_path, daily_db_path, registry_path, as_of or date)

        warnings: list[str] = []
        if not caps:
            warnings.append(
                "시총 원천(daily stock_meta)을 읽지 못해 시총가중 집계가 불가능하다 — "
                "AG-4 에 따라 시총가중 필드가 null 로 보고된다")

        market_key = (market or "all").lower()
        aggregates: list[SectorAggregate] = []
        excluded: list[ExcludedSector] = []
        all_members: list[_Member] = []          # 규칙 BM-1 — 섹터 그룹핑 없는 벤치마크 유니버스
        for sector_name, stock_names in sector_to_stocks.items():
            members = [
                _build_member(name, snapshot[name], caps, high52_map, returns_by_name.get(name))
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
            aggregate, _fallback = _aggregate_members(sector_name, members, cap=cap)
            aggregates.append(aggregate)

        # --- 규칙 BM-1 ~ BM-6 벤치마크(EX-1/EX-2 구조 보장 — 같은 `_aggregate_members`) --
        benchmark = _compute_benchmark(all_members, cap, market_key, anchor_dates)
        for a in aggregates:
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
        excluded.extend(_rank_sectors(aggregates))

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
    """
    result = _compute_sector_aggregates_core(
        weekly_db_path, date, daily_db_path, registry_path, market, cap, as_of,
        apply_min_members)

    if compute_rank_change:
        grid = compute_weekly_grid(weekly_db_path, as_of or date)
        baseline_bar = anchor(grid, as_of or date, 28)
        if baseline_bar is not None:
            baseline = _compute_sector_aggregates_core(
                weekly_db_path, baseline_bar.date, daily_db_path, registry_path, market, cap,
                baseline_bar.date, apply_min_members)
            prev_rank = {a.name: a.rank for a in baseline.aggregates}
            for a in result.aggregates:
                p = prev_rank.get(a.name)
                a.rank_change = (p - a.rank) if (p is not None and a.rank is not None) else None
            result.baseline_date = baseline_bar.date

    return result


def _compute_sector_metrics(
    sector_name: str,
    stock_names: list[str],
    snapshot: dict[str, dict[str, Any]],
    kospi_returns: dict[str, float],
    caps: dict[str, float] | None = None,
    returns_by_name: dict[str, dict[str, float | None]] | None = None,
    high52_map: dict[str, float] | None = None,
) -> SectorRank | None:
    """하위 호환 표면용 단일 섹터 지표(:class:`SectorRank`).

    M2 부터 수익률은 :func:`_aggregate_members` 의 **상한 재배분 시총가중** 값이며,
    AG-4/AG-7 로 시총가중이 불가능한 경우에만 등가중으로 폴백한다(이 표면의 float
    필드는 null 을 실을 수 없다). AG-5 제외는 여기에 적용하지 않는다 — 기존 응답의
    섹터 구성을 보존하기 위함이며 규칙 AG-5 는 ``data[]`` 가 소유한다.

    Returns None if no valid stocks found in sector.
    """
    rets = returns_by_name or {}
    h52 = high52_map or {}
    members = [
        _build_member(name, snapshot[name], caps or {}, h52, rets.get(name))
        for name in stock_names
        if name in snapshot and name not in _INDEX_NAMES
    ]
    if not members:
        return None

    aggregate, equal_fallback = _aggregate_members(sector_name, members)

    def _value(metric: MetricValue, fallback: float | None) -> float:
        if metric.value is not None:
            return float(metric.value)
        return float(fallback) if fallback is not None else 0.0

    avg_1w = _value(aggregate.returns["1w"], equal_fallback["1w"])
    avg_1m = _value(aggregate.returns["1m"], equal_fallback["1m"])
    avg_3m = _value(aggregate.returns["3m"], equal_fallback["3m"])

    return SectorRank(
        name=sector_name,
        stock_count=aggregate.member_count,
        sector_return_1w=round(avg_1w, 4),
        sector_return_1m=round(avg_1m, 4),
        sector_return_3m=round(avg_3m, 4),
        sector_excess_return_1w=round(avg_1w - kospi_returns["chg_1w"], 4),
        sector_excess_return_1m=round(avg_1m - kospi_returns["chg_1m"], 4),
        sector_excess_return_3m=round(avg_3m - kospi_returns["chg_3m"], 4),
        sector_rs_avg=round(aggregate.rs_avg.value or 0.0, 2),
        sector_rs_top_pct=round(aggregate.rs_top_pct.value or 0.0, 2),
        sector_nh_pct=round(aggregate.nh_pct.value or 0.0, 2),
        sector_stage2_pct=round(aggregate.stage2_pct.value or 0.0, 2),
        composite_score=0.0,  # computed after normalization
    )


def compute_sector_ranking(
    db_path: str, date: str, daily_db_path: str | None = None,
    market: str = "all",
) -> list[SectorRank]:
    """Compute sector ranking for all sectors on a given date.

    Per SPEC R7-R8:
    - R7: sector_return, excess_return, rs_avg, rs_top_pct, nh_pct, stage2_pct
    - R8: composite = 0.3 * excess_1w_norm + 0.4 * excess_1m_norm + 0.3 * excess_3m_norm

    Also computes rank_change by comparing to 4-week-ago ranking.

    Args:
        db_path: Path to weekly SQLite database file.
        date: Date string in YYYY-MM-DD format.
        daily_db_path: 일봉 DB 경로(``stock_meta.market_cap``). ``None`` 이면 시총이
            전부 결측으로 취급돼 등가중 폴백이 걸린다(라이브 DB 를 암묵 개방하지 않는다).
        market: ``all`` / ``kospi`` / ``kosdaq`` — M6 신설(AC-SAG-039). 종목별 소속
            시장(registry ``Market`` 컬럼)으로 구성종목을 필터링한다.

    Returns:
        List of SectorRank ordered by composite_score descending (rank 1 = best).
    """
    grid = compute_weekly_grid(db_path)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        snapshot = _load_weekly_snapshot(conn, date)
        kospi_returns = _load_kospi_returns(conn, date)
        # M2 — 기간 수익률은 `anchor(t, N)` 기준이며 저장된 CHG_* 컬럼이 아니다.
        returns_now, _anchors = _anchor_returns(conn, grid, date)
        # M5 — AC-SAG-024 규약 Y: 신고가 판정은 weekly High 364일 창 재계산
        high52_map = _high52_map(conn, date)

        # rank_change 기준일: anchor(t, 28) — t−28일 이하 최근 정규 격자 바
        # (SPEC-SECTOR-GRID-001 AC-SGR-006-B / AC-SGR-020 R2). 1M = 28d(REQ-SGR-006).
        # 기존 raw 날짜 오프셋 기준 → 정규 격자 기준으로 의미 변경.
        prev_bar = anchor(grid, date, 28)
        prev_date = prev_bar.date if prev_bar is not None else None
        prev_snapshot = _load_weekly_snapshot(conn, prev_date) if prev_date else {}
        returns_prev = (
            _anchor_returns(conn, grid, prev_date)[0] if prev_date else {})
        prev_kospi = _load_kospi_returns(conn, prev_date) if prev_date else {
            "chg_1w": 0.0, "chg_1m": 0.0, "chg_3m": 0.0
        }
    finally:
        conn.close()

    # Load sector registry to map stock names to sectors
    sector_to_stocks, market_of = _load_registry_mapping()
    caps = _load_market_caps(daily_db_path)
    market_key = (market or "all").lower()

    def _filter_by_market(names: list[str]) -> list[str]:
        if market_key in ("", "all"):
            return names
        return [n for n in names if _market_matches(market_of.get(n), market_key)]

    # Compute current metrics for each sector
    current_results: list[SectorRank] = []
    for sector_name, stock_names in sector_to_stocks.items():
        metrics = _compute_sector_metrics(
            sector_name, _filter_by_market(stock_names), snapshot, kospi_returns, caps,
            returns_now, high52_map)
        if metrics:
            current_results.append(metrics)

    if not current_results:
        return []

    # Compute composite scores via normalization
    excess_1w_values = [r.sector_excess_return_1w for r in current_results]
    excess_1m_values = [r.sector_excess_return_1m for r in current_results]
    excess_3m_values = [r.sector_excess_return_3m for r in current_results]

    norm_1w = _normalize_list(excess_1w_values)
    norm_1m = _normalize_list(excess_1m_values)
    norm_3m = _normalize_list(excess_3m_values)

    for i, r in enumerate(current_results):
        r.composite_score = round(
            _COMPOSITE_W_1W * norm_1w[i]
            + _COMPOSITE_W_1M * norm_1m[i]
            + _COMPOSITE_W_3M * norm_3m[i],
            2,
        )

    # Sort by composite score descending and assign ranks
    current_results.sort(key=lambda r: r.composite_score, reverse=True)
    current_rank_by_sector: dict[str, int] = {}
    for rank_i, r in enumerate(current_results, start=1):
        r.rank = rank_i
        current_rank_by_sector[r.name] = rank_i

    # Compute rank_change if previous data available
    if prev_snapshot:
        prev_results: list[SectorRank] = []
        for sector_name, stock_names in sector_to_stocks.items():
            metrics = _compute_sector_metrics(
                sector_name, _filter_by_market(stock_names), prev_snapshot, prev_kospi, caps,
                returns_prev)
            if metrics:
                prev_results.append(metrics)

        if prev_results:
            prev_excess_1w = [r.sector_excess_return_1w for r in prev_results]
            prev_excess_1m = [r.sector_excess_return_1m for r in prev_results]
            prev_excess_3m = [r.sector_excess_return_3m for r in prev_results]
            pn1w = _normalize_list(prev_excess_1w)
            pn1m = _normalize_list(prev_excess_1m)
            pn3m = _normalize_list(prev_excess_3m)
            for i, r in enumerate(prev_results):
                r.composite_score = (
                    _COMPOSITE_W_1W * pn1w[i]
                    + _COMPOSITE_W_1M * pn1m[i]
                    + _COMPOSITE_W_3M * pn3m[i]
                )
            prev_results.sort(key=lambda r: r.composite_score, reverse=True)
            prev_rank_by_sector = {r.name: rank_i for rank_i, r in enumerate(prev_results, start=1)}

            for r in current_results:
                prev_rank = prev_rank_by_sector.get(r.name, r.rank)
                r.rank_change = prev_rank - r.rank  # positive = improved rank

    return current_results


def compute_sector_history(
    db_path: str,
    weeks: int = 12,
    daily_db_path: str | None = None,
    market: str = "all",
) -> tuple[list[str], list[list[SectorRank]]]:
    """최근 N주 섹터 랭킹 히스토리를 계산한다.

    날짜는 정규 주간 격자(SPEC-SECTOR-GRID-001 REQ-SGR-001 ``compute_weekly_grid``)의
    ``history`` 에서 파생한다 — CG-1(ISO 주당 1바)·CG-3(부분 데이터 행 수 배제) 가 이미
    적용됐으므로 자체 행수-중앙값×0.5 부분데이터 가드는 폐기한다(AC-SGR-006-B B-2).
    ``(dates, rankings)`` 반환 계약과 last-N-weeks 의미는 유지한다(WIP 보존).

    Args:
        db_path: weekly SQLite DB 경로.
        weeks: 조회 주수.
        daily_db_path: 일봉 DB 경로 — M6 신설. ``compute_sector_ranking`` 에 그대로
            넘긴다(시총가중 원천).
        market: ``all`` / ``kospi`` / ``kosdaq`` — M6 신설(AC-SAG-039).

    Returns:
        (dates, rankings) 튜플. dates는 정규 격자 history 의 최근 weeks 개(오름차순),
        rankings는 각 날짜의 섹터 랭킹 리스트. 둘은 같은 길이·같은 순서.
    """
    grid = compute_weekly_grid(db_path)
    all_history = [bar.date for bar in grid.history]
    history_dates = all_history[-weeks:] if weeks > 0 else all_history

    if not history_dates:
        return [], []

    rankings = [
        compute_sector_ranking(db_path, date, daily_db_path, market)
        for date in history_dates
    ]
    return history_dates, rankings
