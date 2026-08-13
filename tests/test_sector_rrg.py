# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M4 — RRG(Relative Rotation Graph).

담당 AC
-------
* **AC-SAG-031** RS-Ratio 100 = 벤치마크 (RRG-1)
* **AC-SAG-032** 워밍업 미발행 (RRG-2)
* **AC-SAG-033** 지수 = 수익률 연쇄 (RRG-3) — 대조: 날짜별 재계산 방식은 점프 발생
* **AC-SAG-034** look-ahead 시총 금지 (RRG-4)
* **AC-SAG-035** RRG 결측 처리
* **AC-SAG-045 R7** RRG 사분면 편중 회귀 방지 (실행 가능 형태 2종)

되돌림/대조 원칙(§8.3): 참조·대조 계산은 프로덕션 함수를 재구현해 독립적으로 비교한다.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from my_chart.analysis.rrg import (
    WARNING_CONSTANT_SHARE_COUNT,
    chain_index,
    compute_rrg,
    historical_market_caps,
    implied_shares,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _weekly_series(dates: list[str], start: float, rate: float) -> dict[str, float]:
    """``start`` 에서 매 주 ``rate`` 만큼 성장하는 종가 시계열."""
    out: dict[str, float] = {}
    v = start
    for i, d in enumerate(dates):
        out[d] = start * (1.0 + rate) ** i
    return out


# ---------------------------------------------------------------------------
# AC-SAG-031 — RS-Ratio 100 = 벤치마크 (RRG-1)
# ---------------------------------------------------------------------------

def test_ac_sag_031_identical_sector_and_benchmark_rs_ratio_100():
    dates = [f"d{i}" for i in range(6)]
    a = _weekly_series(dates, 100.0, 0.02)
    b = _weekly_series(dates, 50.0, -0.01)
    close_by_date = {d: {"A": a[d], "B": b[d]} for d in dates}

    caps = {"A": 100.0, "B": 100.0}
    prices = {"A": a[dates[-1]], "B": b[dates[-1]]}

    result = compute_rrg(
        dates=dates,
        sector_close_by_date={"SEC": close_by_date},
        benchmark_close_by_date=close_by_date,   # 섹터 == 벤치마크 (동일 유니버스)
        market_caps=caps,
        current_prices=prices,
        lookback_weeks=2,
    )

    assert result.excluded == ()
    series = result.trail_by_sector["SEC"]
    assert series.trail, "워밍업 이후 궤적이 존재해야 한다"
    for point in series.trail:
        assert abs(point.rs_ratio - 100.0) <= 0.01, point
    assert result.benchmark_name


def _build_fixture_all_leading():
    """fixture_all_leading — 전 섹터가 벤치마크를 상회하는 합성 픽스처."""
    dates = [f"d{i}" for i in range(6)]
    bench_close = {d: c for d, c in zip(dates, _weekly_series(dates, 100.0, 0.005).values())}
    benchmark_close_by_date = {d: {"BENCH": bench_close[d]} for d in dates}

    sector_close_by_date = {}
    for name, rate in [("SEC_A", 0.02), ("SEC_B", 0.03), ("SEC_C", 0.015)]:
        s = _weekly_series(dates, 100.0, rate)
        sector_close_by_date[name] = {d: {name: s[d]} for d in dates}

    caps = {"SEC_A": 1.0, "SEC_B": 1.0, "SEC_C": 1.0, "BENCH": 1.0}
    prices = {
        "SEC_A": sector_close_by_date["SEC_A"][dates[-1]]["SEC_A"],
        "SEC_B": sector_close_by_date["SEC_B"][dates[-1]]["SEC_B"],
        "SEC_C": sector_close_by_date["SEC_C"][dates[-1]]["SEC_C"],
        "BENCH": bench_close[dates[-1]],
    }

    result = compute_rrg(
        dates=dates,
        sector_close_by_date=sector_close_by_date,
        benchmark_close_by_date=benchmark_close_by_date,
        market_caps=caps,
        current_prices=prices,
        lookback_weeks=2,
    )
    return result


def test_ac_sag_031_all_sectors_above_100_when_all_leading():
    """전 섹터가 벤치마크를 상회하는 픽스처 — 전 섹터 rs_ratio > 100 (fixture_all_leading)."""
    result = _build_fixture_all_leading()

    assert result.excluded == ()
    for name, series in result.trail_by_sector.items():
        assert series.trail, name
        assert all(p.rs_ratio > 100.0 for p in series.trail), (name, series.trail)


# ---------------------------------------------------------------------------
# AC-SAG-032 — 워밍업 미발행 (RRG-2)
# ---------------------------------------------------------------------------

def test_ac_sag_032_warmup_non_emission():
    lookback_weeks = 12
    n_dates = 30
    dates = [f"d{i:02d}" for i in range(n_dates)]
    sector = _weekly_series(dates, 100.0, 0.015)
    bench = _weekly_series(dates, 100.0, 0.006)
    sector_close_by_date = {d: {"S": sector[d]} for d in dates}
    benchmark_close_by_date = {d: {"B": bench[d]} for d in dates}

    result = compute_rrg(
        dates=dates,
        sector_close_by_date={"SEC": sector_close_by_date},
        benchmark_close_by_date=benchmark_close_by_date,
        market_caps={"S": 100.0, "B": 100.0},
        current_prices={"S": sector[dates[-1]], "B": bench[dates[-1]]},
        lookback_weeks=lookback_weeks,
    )

    series = result.trail_by_sector["SEC"]
    expected_len = n_dates - lookback_weeks
    assert abs(len(series.trail) - expected_len) <= 1, len(series.trail)
    assert series.trail_start_date is not None
    assert series.trail_start_date > dates[0]

    # 상수 패딩(rs_ratio == 100.0)이 없어야 한다 — 실제 값은 100 에 정확히 닿지 않는다
    # (두 지수의 성장률이 다르므로).
    assert all(abs(p.rs_ratio - 100.0) > 1e-6 for p in series.trail)

    first_momenta = [p.rs_momentum for p in series.trail[:4]]
    assert len(set(round(m, 8) for m in first_momenta)) > 1, first_momenta


# ---------------------------------------------------------------------------
# AC-SAG-033 — 지수 = 수익률 연쇄 (RRG-3) — 대조: 날짜별 재계산은 점프
# ---------------------------------------------------------------------------

def test_ac_sag_033_index_chain_no_jump_on_membership_change():
    """구성종목이 도중에 늘어도(각 종목 +1%/주) 인접 지수 비율이 전 구간 1.01."""
    dates = ["d0", "d1", "d2", "d3", "d4"]
    a = {d: 100.0 * 1.01 ** i for i, d in enumerate(dates)}
    b = dict(a)  # B == A (동일 성장률)
    # C 는 d3 부터 등장, 등장 시점부터 동일하게 +1%/주.
    c = {"d3": 100.0, "d4": 101.0}

    close_by_date = {
        "d0": {"A": a["d0"], "B": b["d0"]},
        "d1": {"A": a["d1"], "B": b["d1"]},
        "d2": {"A": a["d2"], "B": b["d2"]},
        "d3": {"A": a["d3"], "B": b["d3"], "C": c["d3"]},
        "d4": {"A": a["d4"], "B": b["d4"], "C": c["d4"]},
    }
    caps = {"A": a["d4"], "B": b["d4"], "C": c["d4"]}
    prices = dict(caps)  # shares == 1 (테스트 단순화 — cap/price == 1)

    result = compute_rrg(
        dates=dates,
        sector_close_by_date={"SEC": close_by_date},
        benchmark_close_by_date=close_by_date,
        market_caps=caps,
        current_prices=prices,
        lookback_weeks=0,
    )
    series = result.trail_by_sector["SEC"]
    # 벤치마크 == 섹터이므로 rs_ratio 는 100 근방 — 여기서는 지수 자체(체인)의 무점프를
    # 검증하는 것이 목적이므로 chain_index 를 직접 호출해 인접 비율을 확인한다.
    weights_by_date = {
        "d0": {"A": 0.5, "B": 0.5},
        "d1": {"A": 0.5, "B": 0.5},
        "d2": {"A": 0.5, "B": 0.5},
        "d3": {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3},
        "d4": {"A": 1 / 3, "B": 1 / 3, "C": 1 / 3},
    }
    idx = chain_index(dates, weights_by_date, close_by_date)
    ratios = [idx[dates[i]] / idx[dates[i - 1]] for i in range(1, len(dates))]
    for r in ratios:
        assert abs(r - 1.01) <= 0.001, ratios

    # --- 대조(필수) — 날짜별 Σ(close×cap)/Σcap 재계산 방식은 점프가 발생함을 단언 ---
    def _naive_level(t: str) -> float:
        w = weights_by_date[t]           # **현재 시점**(t) 가중치를 그대로 씀 — 결함
        closes = close_by_date[t]
        num = sum(w[name] * closes[name] for name in w)
        den = sum(w.values())
        return num / den

    naive_ratios = [
        _naive_level(dates[i]) / _naive_level(dates[i - 1]) for i in range(1, len(dates))
    ]
    # d2→d3 구간(구성종목 변동 시점)에서 naive 방식은 1.01 에서 크게 벗어난다.
    jump_idx = dates.index("d3") - 1
    assert abs(naive_ratios[jump_idx] - 1.01) > 0.005, naive_ratios
    # 반대로 체인 방식은 같은 구간에서 여전히 1.01 근방이다.
    assert abs(ratios[jump_idx] - 1.01) <= 0.001


def test_weight_lag_uses_prev_period_weights_not_current():
    """되돌림 대조 — 가중치를 w(t) 로 잘못 쓰면 결과가 달라짐을 확인(가중치 지연 계약)."""
    dates = ["d0", "d1", "d2"]
    weights_by_date = {
        "d0": {"A": 0.5, "B": 0.5},
        "d1": {"A": 0.9, "B": 0.1},
        "d2": {"A": 0.9, "B": 0.1},
    }
    close_by_date = {
        "d0": {"A": 100.0, "B": 100.0},
        "d1": {"A": 110.0, "B": 90.0},   # A +10%, B -10%
        "d2": {"A": 121.0, "B": 81.0},
    }
    idx = chain_index(dates, weights_by_date, close_by_date)
    # w(t-1) = w(d0) = {0.5, 0.5} → r(d1) = 0.5*0.10 + 0.5*(-0.10) = 0 → index(d1) == 100
    assert abs(idx["d1"] - 100.0) < 1e-9, idx

    # 되돌림: w(t) 를 그대로 쓰는(지연 없는) 변형 — r(d1) = 0.9*0.10 + 0.1*(-0.10) = 0.08
    def _naive_chain_wrong_current_weight(dates, weights_by_date, close_by_date):
        out = {dates[0]: 100.0}
        level = 100.0
        prev_close = close_by_date[dates[0]]
        for t in dates[1:]:
            w = weights_by_date[t]        # 결함: 직전이 아니라 **현재** 가중치
            cur = close_by_date[t]
            num = sum(w[n] * (cur[n] / prev_close[n] - 1.0) for n in w if n in prev_close)
            den = sum(w.values())
            level *= 1.0 + (num / den if den else 0.0)
            out[t] = level
            prev_close = cur
        return out

    wrong = _naive_chain_wrong_current_weight(dates, weights_by_date, close_by_date)
    assert abs(wrong["d1"] - 108.0) < 1e-9, wrong
    assert abs(idx["d1"] - wrong["d1"]) > 5.0, (idx, wrong)


# ---------------------------------------------------------------------------
# AC-SAG-034 — look-ahead 시총 금지 (RRG-4)
# ---------------------------------------------------------------------------

def test_ac_sag_034_historical_market_cap_uses_implied_shares_not_current_snapshot():
    current_price = 100.0
    current_cap = 1000.0
    shares = implied_shares({"X": current_cap}, {"X": current_price})
    assert shares["X"] == 10.0  # 1000 / 100

    close_by_date = {"past": {"X": 50.0}, "now": {"X": 100.0}}
    hist = historical_market_caps(shares, close_by_date)

    assert hist["past"]["X"] == 500.0    # 10 × 50, 현재 시총(1000) 과 다르다
    assert hist["now"]["X"] == 1000.0
    assert hist["past"]["X"] != current_cap


def test_ac_sag_034_static_scan_no_current_snapshot_leak_into_history():
    """현재 스냅샷 시총(market_caps 식별자)을 과거에 그대로 적용하는 경로가 없음을
    AST 기준으로 확인한다(docstring 산문 언급은 대상이 아니다 — 실제 코드 참조만 스캔)."""
    import ast

    src = (REPO_ROOT / "my_chart" / "analysis" / "rrg.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    func = next(
        n for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "historical_market_caps"
    )
    names = {
        node.id
        for node in ast.walk(func)
        if isinstance(node, ast.Name)
    }
    assert "market_caps" not in names, (
        "historical_market_caps 내부 코드에서 현재 시총(market_caps) 식별자를 직접 "
        "참조하면 안 된다 — shares 를 경유해야 한다"
    )


# ---------------------------------------------------------------------------
# AC-SAG-035 — RRG 결측 처리
# ---------------------------------------------------------------------------

def test_ac_sag_035_missing_sector_excluded_no_rs_ratio_100_substitute():
    dates = [f"d{i:02d}" for i in range(15)]
    bench = _weekly_series(dates, 100.0, 0.01)
    benchmark_close_by_date = {d: {"B": bench[d]} for d in dates}

    # SEC_OK: 전 구간 종가 존재.
    ok = _weekly_series(dates, 100.0, 0.02)
    # SEC_MISSING: 구성종목 전무(전 구간 종가 없음) — RS-Ratio 산출 자체가 불가능하다.
    lookback_weeks = 12

    sector_close_by_date = {
        "SEC_OK": {d: {"S": ok[d]} for d in dates},
        "SEC_MISSING": {d: {} for d in dates},
    }

    result = compute_rrg(
        dates=dates,
        sector_close_by_date=sector_close_by_date,
        benchmark_close_by_date=benchmark_close_by_date,
        market_caps={"S": 100.0, "B": 100.0},
        current_prices={"S": ok[dates[-1]], "B": bench[dates[-1]]},
        lookback_weeks=lookback_weeks,
    )

    assert "SEC_OK" in result.trail_by_sector
    assert "SEC_MISSING" not in result.trail_by_sector
    excluded_names = {e.name for e in result.excluded}
    assert "SEC_MISSING" in excluded_names
    for e in result.excluded:
        assert e.reason  # 사유가 항상 동반된다

    # rs_ratio == 100 대체가 발생하지 않는다 — 결측 섹터는 trail 이 아예 없다(빈 튜플).
    assert result.trail_by_sector.get("SEC_MISSING") is None


# ---------------------------------------------------------------------------
# AC-SAG-045 R7 — 사분면 편중 회귀 방지 (실행 가능 형태 2종)
# ---------------------------------------------------------------------------

def test_ac_sag_045_r7a_all_leading_no_bias_warning():
    """전 섹터가 Leading 사분면에 몰려도 응답이 정상이며 편중 경고가 없다."""
    result = _build_fixture_all_leading()
    assert all("quadrant" not in w.lower() and "편중" not in w for w in result.warnings)
    assert WARNING_CONSTANT_SHARE_COUNT in result.warnings


def test_ac_sag_045_r7a_cross_sectional_zscore_variant_diverges():
    """대조 — 횡단면 z-score 방식으로 되돌리면 약 절반이 100 미만이 된다."""
    dates = [f"d{i}" for i in range(6)]
    bench_close = _weekly_series(dates, 100.0, 0.005)
    benchmark_close_by_date = {d: {"BENCH": bench_close[d]} for d in dates}
    sector_close_by_date = {}
    rates = {"SEC_A": 0.02, "SEC_B": 0.03, "SEC_C": 0.015, "SEC_D": 0.05}
    for name, rate in rates.items():
        s = _weekly_series(dates, 100.0, rate)
        sector_close_by_date[name] = {d: {name: s[d]} for d in dates}

    caps = {name: 1.0 for name in rates}
    caps["BENCH"] = 1.0
    prices = {name: sector_close_by_date[name][dates[-1]][name] for name in rates}
    prices["BENCH"] = bench_close[dates[-1]]

    result = compute_rrg(
        dates=dates,
        sector_close_by_date=sector_close_by_date,
        benchmark_close_by_date=benchmark_close_by_date,
        market_caps=caps,
        current_prices=prices,
        lookback_weeks=2,
    )
    # 최신 시점의 rs_ratio 를 모은다 — 전부 100 초과(RS-Ratio 방식).
    last_values = [series.trail[-1].rs_ratio for series in result.trail_by_sector.values()]
    assert all(v > 100.0 for v in last_values), last_values

    # 횡단면 z-score 되돌림 — 평균을 100 으로 맞추므로 정의상 절반가량은 100 미만이 된다.
    mean = sum(last_values) / len(last_values)
    std = (sum((v - mean) ** 2 for v in last_values) / len(last_values)) ** 0.5
    z_transformed = [((v - mean) / std) * 7.0 + 100.0 if std > 0 else 100.0 for v in last_values]
    assert any(v < 100.0 for v in z_transformed), z_transformed


def test_ac_sag_045_r7b_no_quadrant_balance_assertion_in_test_suite():
    """정적 스캔 — 사분면 균등 분포를 요구하는 단언이 테스트 스위트에 없다."""
    # 이 파일 자신은 스캔 패턴 문자열을 리터럴로 포함하므로(자기 참조 오탐) 제외한다.
    proc = subprocess.run(
        [
            "grep", "-rnE", "--include=*.py", "--exclude=test_sector_rrg.py",
            r"quadrant.*(balanc|even|distribut)|len\(leading\).*<",
            str(REPO_ROOT / "tests"),
        ],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1, proc.stdout  # grep exit 1 == 매치 없음
    assert proc.stdout.strip() == ""
