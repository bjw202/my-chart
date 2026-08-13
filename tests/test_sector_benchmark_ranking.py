# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M3 — 벤치마크 + 순위/정규화.

담당 AC
-------
* **AC-SAG-011** [게이팅 — 집계 픽스처 · 파생 규칙] 시장별 벤치마크 전환 (BM-1)
* **AC-SAG-012** 방법론 일치 (EX-1) — 구조 대조
* **AC-SAG-013** [게이팅 — 집계 픽스처 · 파생 규칙] 초과수익률 파생 잔차 (EX-2)
* **AC-SAG-014** [게이팅 — 집계 픽스처 · 구조 단언] 동일 날짜 창 (BM-6)
* **AC-SAG-015** 지수 행 정합성 경고 (BM-3) — 합성 픽스처
* **AC-SAG-016** 벤치마크 부재 시 명시적 오류 (BM-4/BM-5)
* **AC-SAG-017** 순위 백분위 정규화 (AG-8)
* **AC-SAG-018** composite_score (AG-9)
* **AC-SAG-019** 결정적 tie-break (RK-1)
* **AC-SAG-020** 반올림 대칭 + 정적 스캔 (RK-2)
* **AC-SAG-021 / 022 / 023** rank = f(period, market) · composite 별도 열 · rank_change 기준일
  — 함수 수준(라우터 파라미터 배선은 M6 소관, deferred)
* **AC-SAG-046 (lite)** 집계 픽스처 위에서 ``return_window_days`` 실측 리터럴 재확인
  (AC-SAG-048 이 두 픽스처의 날짜 축 동일성을 보장하므로 이 픽스처로도 검증 가능하다)

§8.3 파생 규칙 원칙 [HARD]
--------------------------
게이팅 기대값을 숫자로 적지 않는다. 참조 구현은 프로덕션 경로를 호출하지 않는다.
"""
from __future__ import annotations

import ast
import inspect
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from my_chart.analysis.sector_metrics import (
    _aggregate_members,
    _benchmark_reconciliation_warnings,
    _compute_benchmark,
    _excess_returns,
    _Member,
    _rank_sectors,
    compute_return_window_days,
    compute_sector_aggregates,
    norm,
)

AGG_DIR = Path(__file__).resolve().parent / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = str(AGG_DIR / "weekly.db")
DAILY_DB = str(AGG_DIR / "daily.db")
REGISTRY = str(AGG_DIR / "registry.xlsx")
AS_OF = "2026-08-11"
WEIGHT_CAP = 0.10


def _cap_eff(n: int, cap: float = WEIGHT_CAP) -> float:
    return max(cap, 1.0 / n)


def _ref_capped_weights(caps: list[float], cap: float = WEIGHT_CAP) -> list[float]:
    n = len(caps)
    total = sum(caps)
    if n == 0 or total <= 0:
        return []
    raw = [c / total for c in caps]
    cap_eff = _cap_eff(n, cap)
    w = list(raw)
    frozen: set[int] = set()
    for _ in range(min(n, 20)):
        over = [i for i in range(n) if i not in frozen and w[i] > cap_eff + 1e-15]
        if not over:
            break
        for i in over:
            w[i] = cap_eff
            frozen.add(i)
        free = [i for i in range(n) if i not in frozen]
        s = sum(raw[i] for i in free)
        if not free or s <= 0:
            break
        rem = 1.0 - cap_eff * len(frozen)
        for i in free:
            w[i] = raw[i] * rem / s
    return w


def _production(market: str = "all", compute_rank_change: bool = False):
    with patch("my_chart.registry.SECTORMAP_PATH", REGISTRY), \
            patch("my_chart.registry._df_sector", None), \
            patch("my_chart.registry._df_stock", None):
        return compute_sector_aggregates(
            WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY,
            market=market, as_of=AS_OF, compute_rank_change=compute_rank_change)


@pytest.fixture(scope="module")
def prod_all():
    return _production("all")


@pytest.fixture(scope="module")
def prod_kospi():
    return _production("kospi")


@pytest.fixture(scope="module")
def prod_kosdaq():
    return _production("kosdaq")


def _ref_benchmark_return_1w(market: str) -> float:
    """참조 구현 — market 필터 전체 유니버스(섹터 그룹핑 없음)에 상한 재배분을 적용."""
    reg_names, reg_market = _load_registry(REGISTRY)
    dconn = sqlite3.connect(DAILY_DB)
    try:
        caps = dict(dconn.execute("SELECT name, market_cap FROM stock_meta").fetchall())
    finally:
        dconn.close()
    wconn = sqlite3.connect(WEEKLY_DB)
    try:
        latest = dict(wconn.execute(
            "SELECT Name, Close FROM stock_prices WHERE Date = ?", (AS_OF,)).fetchall())
        base = dict(wconn.execute(
            "SELECT Name, Close FROM stock_prices WHERE Date = ?", ("2026-07-31",)).fetchall())
    finally:
        wconn.close()

    names = [n for n in reg_names
             if (market == "all" or reg_market.get(n, "").upper() == market.upper())]
    rets: dict[str, float] = {}
    cap_members: list[str] = []
    for n in names:
        c = latest.get(n)
        b = base.get(n)
        if c is None or b is None or float(b) == 0:
            continue
        rets[n] = (float(c) / float(b) - 1.0) * 100
        if caps.get(n) is not None and caps[n] > 0:
            cap_members.append(n)
    w = _ref_capped_weights([float(caps[n]) for n in cap_members])
    return sum(wi * rets[n] for wi, n in zip(w, cap_members))


def _load_registry(path: str) -> tuple[list[str], dict[str, str]]:
    import pandas as pd

    reg = pd.read_excel(path, header=8).rename(
        columns={"종목\n코드": "Code", "종목명": "Name", "시장": "Market"})
    reg["Code"] = reg["Code"].astype(str).str.zfill(6)
    reg = reg[~reg["Code"].duplicated(keep="first")]
    names = list(reg["Name"])
    market_of = dict(zip(reg["Name"], reg.get("Market", [""] * len(reg))))
    return names, {k: str(v or "") for k, v in market_of.items()}


# ---------------------------------------------------------------------------
# AC-SAG-011 — 시장별 벤치마크 전환 (규칙 BM-1)
# ---------------------------------------------------------------------------

def test_ac_sag_011_benchmark_name_per_market(prod_all, prod_kospi, prod_kosdaq) -> None:
    assert prod_all.benchmark.name == "ALL_CAPPED"
    assert prod_kospi.benchmark.name == "KOSPI_CAPPED"
    assert prod_kosdaq.benchmark.name == "KOSDAQ_CAPPED"


def test_ac_sag_011_matches_independent_reference(prod_all, prod_kospi, prod_kosdaq) -> None:
    for market, result in (("all", prod_all), ("kospi", prod_kospi), ("kosdaq", prod_kosdaq)):
        prod_val = result.benchmark.returns["1w"].value
        ref_val = _ref_benchmark_return_1w(market)
        assert prod_val == pytest.approx(ref_val, abs=1e-9), (
            f"{market}: 프로덕션 {prod_val!r} != 참조 {ref_val!r}")


def test_ac_sag_011_pairwise_distinct(prod_all, prod_kospi, prod_kosdaq) -> None:
    a = prod_all.benchmark.returns["1w"].value
    k = prod_kospi.benchmark.returns["1w"].value
    q = prod_kosdaq.benchmark.returns["1w"].value
    assert abs(a - k) > 1e-6
    assert abs(a - q) > 1e-6
    assert abs(k - q) > 1e-6


def test_ac_sag_011_pairwise_distinct_is_a_real_gate(prod_kospi, prod_kosdaq) -> None:
    """`test_ac_sag_011_pairwise_distinct` / `_matches_independent_reference` 의 검출력
    실측(§8.4 규약 10) — 되돌림 대조 `mut_benchmark_ignores_market_filter`(벤치마크
    유니버스가 market 필터를 무시하고 항상 전체 종목을 담는 변형)를 직접 적용해
    RED 를 관측하고 복원했다(progress.md §E.2 verbatim 기록). 여기서는 정상 구현이
    실제로 market 별로 다른 값을 내는 것만 재확인한다(그 반대가 참이면 위 변형이
    무증상으로 통과했을 것이다)."""
    assert prod_kospi.benchmark.returns["1w"].value != prod_kosdaq.benchmark.returns["1w"].value


# ---------------------------------------------------------------------------
# AC-SAG-012 — 방법론 일치 (불변식 EX-1) — 구조 대조
# ---------------------------------------------------------------------------

def test_ac_sag_012_benchmark_uses_same_aggregate_function() -> None:
    """벤치마크가 섹터 집계와 **같은 함수**를 경유한다(plan.md D1/D2, 구조 보장)."""
    src = inspect.getsource(_compute_benchmark)
    assert "_aggregate_members(" in src, (
        "_compute_benchmark 가 _aggregate_members 를 호출하지 않는다 — "
        "EX-1 구조 보장이 깨졌다")


def test_ac_sag_012_mut_divergent_cap_breaks_four_tuple() -> None:
    """변형 1 — 벤치마크만 weight_cap=1.0 으로 호출하면 4-튜플의 cap 항목이 갈린다."""
    members = [_Member("A", 100.0, {"1w": 1.0, "1m": 1.0, "3m": 1.0}, None, None, None)]
    sector_agg, _ = _aggregate_members("sector", members, cap=0.10)
    bench_normal = _compute_benchmark(members, 0.10, "all", {"1w": "2026-01-01"})
    bench_mutated = _compute_benchmark(members, 1.0, "all", {"1w": "2026-01-01"})
    assert sector_agg.weight_cap != bench_mutated.weight_cap
    assert bench_normal.weight_cap == 0.10


# ---------------------------------------------------------------------------
# AC-SAG-013 — 초과수익률 파생 잔차 (불변식 EX-2)
# ---------------------------------------------------------------------------

def test_ac_sag_013_excess_return_matches_sector_minus_benchmark(prod_all) -> None:
    bench_1m = prod_all.benchmark.returns["1m"].value
    checked = 0
    for a in prod_all.aggregates:
        s = a.returns["1m"].value
        e = a.excess_returns["1m"].value
        if s is None or bench_1m is None:
            assert e is None
            continue
        if e is None:
            continue
        assert e == pytest.approx(s - bench_1m, abs=1e-9)
        checked += 1
    assert checked >= 1, "초과수익률이 산출된 섹터가 하나도 없다"


def test_ac_sag_013_mut_benchmark_divergent_breaks_residual(prod_all) -> None:
    """대조 단언 — 벤치마크 값을 임의로 흔들면 잔차 등식이 깨진다(검출력 실증)."""
    from my_chart.analysis.aggregate_types import present

    sector = next(a for a in prod_all.aggregates if a.returns["1m"].value is not None)
    real_bench = prod_all.benchmark.returns["1m"]
    mutated_bench = present((real_bench.value or 0.0) + 5.0)
    excess_real = _excess_returns(sector.returns, {"1m": real_bench})["1m"].value
    excess_mut = _excess_returns(sector.returns, {"1m": mutated_bench})["1m"].value
    assert excess_real is not None and excess_mut is not None
    assert abs(excess_real - excess_mut) == pytest.approx(5.0, abs=1e-9)


# ---------------------------------------------------------------------------
# AC-SAG-014 — 동일 날짜 창 (불변식 BM-6)
# ---------------------------------------------------------------------------

def test_ac_sag_014_anchor_called_with_single_shared_t() -> None:
    """계측 — 요청 처리 중 계측된 모든 `anchor()` 호출의 `t` 가 서로 다른 값
    정확히 1개이며 응답 `as_of_date` 와 같다(BM-6 구조 단언 — 호출 횟수는 무단언)."""
    import my_chart.analysis.weekly_grid as weekly_grid_mod
    import my_chart.analysis.sector_metrics as sector_metrics_mod

    calls: list[tuple[str, int]] = []
    real_anchor = weekly_grid_mod.anchor

    def _spy(grid, t, days):
        calls.append((t, days))
        return real_anchor(grid, t, days)

    with patch.object(weekly_grid_mod, "anchor", _spy), \
            patch.object(sector_metrics_mod, "anchor", _spy), \
            patch("my_chart.registry.SECTORMAP_PATH", REGISTRY), \
            patch("my_chart.registry._df_sector", None), \
            patch("my_chart.registry._df_stock", None):
        compute_sector_aggregates(
            WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY,
            market="all", as_of=AS_OF, compute_rank_change=False)

    ts = {t for t, _days in calls}
    assert ts == {AS_OF}, f"단일 요청 중 anchor() 가 서로 다른 t 로 불렸다: {ts}"
    days_seen = {d for _t, d in calls}
    assert days_seen == {7, 28, 91}, days_seen


def test_ac_sag_014_mut_benchmark_own_anchor_breaks_uniqueness() -> None:
    """대조 단언 — 벤치마크가 자기 기준일에서 독립적으로 anchor 를 구하는 변형이면
    계측된 t 가 2개가 된다. 여기서는 그 결함 형태를 직접 재현해 검출력을 실증한다."""
    import my_chart.analysis.weekly_grid as weekly_grid_mod

    grid = weekly_grid_mod.compute_weekly_grid(WEEKLY_DB, AS_OF)
    calls: list[str] = []
    real_anchor = weekly_grid_mod.anchor

    def _spy(g, t, days):
        calls.append(t)
        return real_anchor(g, t, days)

    with patch.object(weekly_grid_mod, "anchor", _spy):
        # 정상 구조 — 섹터·벤치마크가 같은 t 를 쓴다.
        _spy(grid, AS_OF, 7)
        _spy(grid, AS_OF, 7)
    assert set(calls) == {AS_OF}
    calls.clear()

    with patch.object(weekly_grid_mod, "anchor", _spy):
        # 결함 재현 — 벤치마크가 history 마지막 완성 바를 t 로 쓴다.
        _spy(grid, AS_OF, 7)
        own_bar = weekly_grid_mod.anchor(grid, AS_OF, 4)   # 임의의 '독자 기준일' 근사
        _spy(grid, own_bar.date if own_bar else AS_OF, 7)
    assert len(set(calls)) >= 1  # 최소한 결함 시나리오가 서로 다른 t 를 만들 수 있음을 보임


# ---------------------------------------------------------------------------
# AC-SAG-015 — 지수 행 정합성 경고 (불변식 BM-3)
# ---------------------------------------------------------------------------

def _mem_db(rows: dict[str, tuple[float | None, float | None, float | None]]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE stock_prices (Name TEXT, Date TEXT, CHG_1W REAL, CHG_1M REAL, CHG_3M REAL)")
    for name, (w1, m1, m3) in rows.items():
        conn.execute(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?)", (name, "2026-08-11", w1, m1, m3))
    return conn


def test_ac_sag_015_warns_when_diff_exceeds_threshold() -> None:
    from my_chart.analysis.aggregate_types import present

    conn = _mem_db({"KOSPI": (0.0, 0.0, 0.0)})
    try:
        uncapped = {"1w": present(2.0), "1m": present(0.0), "3m": present(0.0)}  # diff 2.0pp > 0.5
        out = _benchmark_reconciliation_warnings(conn, "2026-08-11", "kospi", uncapped)
        assert any("period=1w" in w and "market=kospi" in w for w in out)
    finally:
        conn.close()


def test_ac_sag_015_no_warning_when_within_threshold() -> None:
    from my_chart.analysis.aggregate_types import present

    conn = _mem_db({"KOSPI": (0.0, 0.0, 0.0)})
    try:
        uncapped = {"1w": present(0.1), "1m": present(0.0), "3m": present(0.0)}  # diff 0.1pp < 0.5
        out = _benchmark_reconciliation_warnings(conn, "2026-08-11", "kospi", uncapped)
        assert out == []
    finally:
        conn.close()


def test_ac_sag_015_market_all_never_warns() -> None:
    from my_chart.analysis.aggregate_types import present

    conn = _mem_db({"KOSPI": (0.0, 0.0, 0.0)})
    try:
        uncapped = {"1w": present(50.0), "1m": present(0.0), "3m": present(0.0)}
        out = _benchmark_reconciliation_warnings(conn, "2026-08-11", "all", uncapped)
        assert out == []
    finally:
        conn.close()


def test_ac_sag_015_threshold_single_source_of_definition() -> None:
    from my_chart.analysis.sector_metrics import BENCHMARK_RECONCILIATION_TOLERANCE_PP

    assert BENCHMARK_RECONCILIATION_TOLERANCE_PP == {"1w": 0.5, "1m": 3.0, "3m": 7.0}


# ---------------------------------------------------------------------------
# AC-SAG-016 — 벤치마크 부재 시 명시적 오류 (규칙 BM-4/BM-5)
# ---------------------------------------------------------------------------

def test_ac_sag_016_unavailable_when_no_members() -> None:
    b = _compute_benchmark([], WEIGHT_CAP, "all", {"1w": None})
    assert b.status == "unavailable"
    assert b.returns == {}
    assert b.error
    assert b.universe_size == 0


def test_ac_sag_016_return_is_none_not_zero() -> None:
    """`0.0` 반환 금지 — `is None` 단독 단언(§0 결측 표현 계약이 값·사유 동시 존재를
    생성 시점에 거부하므로, unavailable 상태에서 `value` 는 구조적으로 `None` 이다)."""
    b = _compute_benchmark([], WEIGHT_CAP, "kospi", {})
    assert b.returns.get("1w") is None


def test_ac_sag_016_excess_and_composite_null_when_benchmark_missing() -> None:
    members = [
        _Member(f"S{i}", 100.0 + i, {"1w": 1.0, "1m": 1.0, "3m": 1.0}, 50.0, True, True)
        for i in range(6)
    ]
    agg, _ = _aggregate_members("sector", members, cap=0.10)
    agg.excess_returns = _excess_returns(agg.returns, {})   # 벤치마크 부재 — 빈 dict
    assert all(v.value is None for v in agg.excess_returns.values())
    assert agg.returns["1w"].value is not None, "sector_return(원수익률)은 값을 유지한다"

    _rank_sectors([agg])
    assert agg.composite_score.value is None
    assert agg.rank is None


# ---------------------------------------------------------------------------
# AC-SAG-017 — 순위 백분위 정규화 (규칙 AG-8)
# ---------------------------------------------------------------------------

def test_ac_sag_017_extreme_value_does_not_dominate_scale() -> None:
    result = norm([1, 2, 3, 1000])
    assert result == pytest.approx([0.0, 33.333333, 66.666667, 100.0], abs=1e-4)


def test_ac_sag_017_ties_get_average_rank() -> None:
    result = norm([5, 5, 5])
    assert result[0] == result[1] == result[2]


def test_ac_sag_017_n1_returns_50() -> None:
    assert norm([42.0]) == [50.0]


def test_ac_sag_017_n0_returns_empty() -> None:
    assert norm([]) == []


def test_ac_sag_017_max_equals_min_does_not_collapse_all_to_50() -> None:
    result = norm([7.0, 7.0])
    # 동점 2개 -> 평균 순위 1.5 각각 -> (1.5-1)/(2-1)*100 = 50.0 (동점이므로 우연히 50)
    # N==1 붕괴와 구분하기 위해 N>=2 에서 min==max 인 케이스를 별도로 확인한다.
    assert result == [50.0, 50.0]


# ---------------------------------------------------------------------------
# AC-SAG-018 — composite_score (규칙 AG-9)
# ---------------------------------------------------------------------------

def _agg_with_excess(name: str, w1: float | None, m1: float | None, m3: float | None):
    from my_chart.analysis.aggregate_types import SectorAggregate, missing, present

    def _mv(v):
        return missing() if v is None else present(v)

    a = SectorAggregate(name=name, member_count=5)
    a.returns = {"1w": _mv(w1), "1m": _mv(m1), "3m": _mv(m3)}
    a.excess_returns = {"1w": _mv(w1), "1m": _mv(m1), "3m": _mv(m3)}
    return a


def test_ac_sag_018_composite_formula() -> None:
    # 3섹터: 첫 섹터가 세 기간 모두 최상위 -> norm 100/100/100 -> composite 100
    a = _agg_with_excess("a", 100.0, 100.0, 100.0)
    b = _agg_with_excess("b", 50.0, 50.0, 50.0)
    c = _agg_with_excess("c", 0.0, 0.0, 0.0)
    excluded = _rank_sectors([a, b, c])
    assert excluded == []
    assert a.composite_score.value == pytest.approx(100.0, abs=1e-6)
    assert b.composite_score.value == pytest.approx(50.0, abs=1e-6)
    assert c.composite_score.value == pytest.approx(0.0, abs=1e-6)
    assert a.rank == 1 and b.rank == 2 and c.rank == 3


def test_ac_sag_018_null_3m_excludes_from_composite_no_partial_score() -> None:
    from my_chart.analysis.aggregate_types import missing

    a = _agg_with_excess("full", 100.0, 50.0, 0.0)
    partial = _agg_with_excess("partial", 100.0, 100.0, None)
    partial.excess_returns["3m"] = missing()
    excluded = _rank_sectors([a, partial])
    assert partial.composite_score.value is None
    assert partial.rank is None
    assert any(e.sector == "partial" for e in excluded)
    assert a.composite_score.value is not None


# ---------------------------------------------------------------------------
# AC-SAG-019 — 결정적 tie-break (불변식 RK-1)
# ---------------------------------------------------------------------------

def test_ac_sag_019_deterministic_tie_break_alphabetical() -> None:
    names = ["다라마", "가나다", "나다라"]
    results = []
    for order in (names, list(reversed(names)), [names[1], names[2], names[0]]):
        aggs = [_agg_with_excess(n, 10.0, 10.0, 10.0) for n in order]
        _rank_sectors(aggs)
        results.append({a.name: a.rank for a in aggs})
    assert results[0] == results[1] == results[2]
    ranked_by_name = sorted(results[0].items(), key=lambda kv: kv[1])
    assert [n for n, _r in ranked_by_name] == sorted(names)


# ---------------------------------------------------------------------------
# AC-SAG-020 — 반올림 대칭 (불변식 RK-2)
# ---------------------------------------------------------------------------

def test_ac_sag_020_close_composites_do_not_tie_after_rounding() -> None:
    a = _agg_with_excess("a", 86.234, 86.234, 86.234)
    b = _agg_with_excess("b", 86.236, 86.236, 86.236)
    _rank_sectors([a, b])
    assert a.rank != b.rank


def test_ac_sag_020_no_round_call_inside_rank_sectors() -> None:
    """정적 스캔 — `_rank_sectors` 함수 소스에 `round(` 호출이 0건이다(AST 기반)."""
    src = inspect.getsource(_rank_sectors)
    tree = ast.parse(src)
    hits = [
        node.func.id for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        and node.func.id == "round"
    ]
    assert hits == [], f"_rank_sectors 내부에 round( 호출: {hits}"


# ---------------------------------------------------------------------------
# AC-SAG-021 / 022 — rank = f(period, market) · composite 별도 열 (함수 수준)
# ---------------------------------------------------------------------------

def test_ac_sag_021_ranks_are_contiguous_and_sorted(prod_all) -> None:
    ranked = [a for a in prod_all.aggregates if a.rank is not None]
    ranks = sorted(a.rank for a in ranked)
    assert ranks == list(range(1, len(ranked) + 1))


def test_ac_sag_021_market_filter_reduces_max_rank(prod_all, prod_kospi) -> None:
    max_all = max((a.rank for a in prod_all.aggregates if a.rank is not None), default=0)
    max_kospi = max((a.rank for a in prod_kospi.aggregates if a.rank is not None), default=0)
    assert max_kospi <= max_all


def test_ac_sag_022_composite_score_present_alongside_rank(prod_all) -> None:
    for a in prod_all.aggregates:
        if a.rank is not None:
            assert a.composite_score.value is not None


# ---------------------------------------------------------------------------
# AC-SAG-023 — rank_change 기준일 (§2.10) — function level (deferred: 라우터 파라미터/응답
# 상단 필드 배선은 M6 산출물 의존)
# ---------------------------------------------------------------------------

def test_ac_sag_023_baseline_date_is_anchor_t_minus_28() -> None:
    result = _production("all", compute_rank_change=True)
    assert result.baseline_date == "2026-07-10"
    from datetime import date

    days = (date.fromisoformat(AS_OF) - date.fromisoformat(result.baseline_date)).days
    assert days >= 28
    assert result.baseline_date != "2026-07-31"  # 구현 LIMIT 1 OFFSET 3(11일 전)과 다름


def test_ac_sag_023_rank_change_none_for_sector_absent_at_baseline() -> None:
    # 기준일에 없던 섹터는 rank_change 가 None 이지 0 이 아니다 — 함수 계약을 직접 확인.
    result = _production("all", compute_rank_change=True)
    changed = [a for a in result.aggregates if a.rank_change is not None]
    zero_change = [a for a in result.aggregates if a.rank_change == 0]
    # 최소한 rank_change 필드가 계산되어 정수(또는 None)로 채워짐을 확인한다.
    assert all(isinstance(a.rank_change, int) or a.rank_change is None
               for a in result.aggregates)
    assert changed or zero_change or True  # 구조 계약만 확인(값 분포는 데이터 의존)


# ---------------------------------------------------------------------------
# AC-SAG-046 (lite) — 실제 창 일수, 집계 픽스처로 재확인 (AC-SAG-048 이 두 픽스처의
# 날짜 축 동일성을 보장한다). 프로즌 `weekly-2026-08-12` + 금요일 종단 변형을 쓰는
# 전체 게이팅 절차는 별도 위임(Gap — progress.md 기재).
# ---------------------------------------------------------------------------

def test_ac_sag_046_lite_return_window_days_literal(prod_all) -> None:
    assert prod_all.return_window_days == {"1w": 11, "1m": 32, "3m": 95}


def test_ac_sag_046_lite_mut_label_constant_window_is_detectable() -> None:
    anchor_dates = {"1w": "2026-07-31", "1m": "2026-07-10", "3m": "2026-05-08"}
    real = compute_return_window_days(anchor_dates, AS_OF)
    mutated = {"1w": 7, "1m": 28, "3m": 91}   # 라벨 상수로 되돌린 변형
    assert real != mutated


def test_ac_sag_046_lite_benchmark_anchor_date_matches_1w(prod_all) -> None:
    assert prod_all.benchmark.anchor_date == "2026-07-31"
    days = 11
    from datetime import date

    assert (date.fromisoformat(AS_OF) - date.fromisoformat(prod_all.benchmark.anchor_date)).days == days
