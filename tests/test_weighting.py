# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M2 — 상한 재배분 가중치.

담당 AC: **AC-SAG-001**(가중 + 상한 재배분) · **AC-SAG-003 산출물 절**(capped_members) ·
**AC-SAG-010**(effective_n) · **AC-SAG-049**(무작위 스윕 종료·불변식 계약).

`§8.4 규약 5` 순수 합성 열거에 속하므로 프로즌 픽스처·라이브 DB 를 읽지 않는다.

§0 INV-CAP-1 준수
-----------------
상한 적용 후 가중치의 기대값은 **언제나 `cap_eff(n) = max(weight_cap, 1/n)`** 으로 적고
`weight_cap` 리터럴(`0.10`)로 적지 않는다. `n >= 11` 이어서 두 값이 일치하는 경우에도
`cap_eff` 를 경유한다 — 리터럴은 `n` 이 바뀌는 순간 거짓이 되는 형태이고, 그것이
D17 / D22 / N1 이 반복된 경로다. 기계적 집행은 `tests/test_inv_cap1_scan.py`.

독립 오라클 (§8.3 · Lesson #9)
------------------------------
AC-SAG-049 의 고정점 등가 절과 닫힌 해 대조 절은 **프로덕션 모듈을 import 하지 않는**
두 개의 독립 재구현(`_plan31_verbatim` / `_closed_form`)을 오라클로 쓴다. 단언의 양변이
같은 표현식에서 오면 무효이므로, 한 변은 프로덕션 다른 한 변은 독립 재구현이다.
"""
from __future__ import annotations

import random

import pytest

CAP = 0.10                       # spec.md D3 weight_cap — 이 파일에서 유일한 상한 리터럴


def _cap_eff(n: int, cap: float = CAP) -> float:
    """INV-CAP-1 — 유효 상한. 테스트 기대값은 **전부 이 함수를 경유**한다."""
    return max(cap, 1.0 / n)


def _caps(values: list[float]) -> dict[str, float]:
    return {f"s{i}": float(v) for i, v in enumerate(values)}


# ---------------------------------------------------------------------------
# 독립 오라클 — 프로덕션 미import
# ---------------------------------------------------------------------------

def _plan31_verbatim(caps: dict[str, float], cap: float = CAP,
                     iterations: int = 20) -> dict[str, float]:
    """plan.md §3.1 **v0.4.1 verbatim**(동결 없음) 재구현.

    상한에 걸린 종목이 다음 반복에서 `over` 조건에 걸리지 않아 `rest` 로 분류되고
    **재배분을 다시 받는다** — 진동하며, 20회에서 상한을 초과한 채 종료한다.
    `iterations` 를 크게 주면 같은 고정점으로 수렴한다.
    """
    n = len(caps)
    cap_eff = max(cap, 1.0 / n)
    total = sum(caps.values())
    w = {k: v / total for k, v in caps.items()}
    for _ in range(iterations):
        over = {k for k, v in w.items() if v > cap_eff + 1e-12}
        if not over:
            break
        excess = sum(w[k] - cap_eff for k in over)
        rest = {k: v for k, v in w.items() if k not in over}
        rest_total = sum(rest.values())
        for k in over:
            w[k] = cap_eff
        if rest_total > 0:
            for k in rest:
                w[k] += excess * (w[k] / rest_total)
    return w


def _closed_form(caps: dict[str, float], cap: float = CAP) -> dict[str, float]:
    """닫힌 해 — 상한 집합 `S` 를 확정한 뒤 잔여를 원비중 비례로 배분한다(반복 없음)."""
    n = len(caps)
    cap_eff = max(cap, 1.0 / n)
    total = sum(caps.values())
    raw = {k: v / total for k, v in caps.items()}
    over: set[str] = set()
    while True:
        remaining = 1.0 - cap_eff * len(over)
        denom = sum(raw[k] for k in raw if k not in over)
        if denom <= 0:
            break
        new = [k for k in raw
               if k not in over and raw[k] * remaining / denom > cap_eff + 1e-15]
        if not new:
            break
        over.update(new)
    remaining = 1.0 - cap_eff * len(over)
    denom = sum(raw[k] for k in raw if k not in over)
    return {k: (cap_eff if k in over else raw[k] * remaining / denom) for k in raw}


# ---------------------------------------------------------------------------
# AC-SAG-001 — 시총가중 + 상한 재배분 (규칙 AG-1)
# ---------------------------------------------------------------------------

def test_ac_sag_001_a_degenerate_n5_is_exactly_equal_weight() -> None:
    """(A · 축퇴) `[70,10,10,5,5]` — `cap_eff == max(0.10, 1/5) == 0.20`, 결과가 정확히 균등.

    `n × cap_eff == 1` 이므로 `max(w) <= cap_eff ∧ Σw = 1` 의 해가 **하나뿐**이다
    (§0 INV-CAP-1 명제 2). 부동소수 오차조차 0 이어야 한다.
    """
    from my_chart.analysis.weighting import capped_weights_detail

    res = capped_weights_detail(_caps([70, 10, 10, 5, 5]), cap=CAP)
    cap_eff = _cap_eff(5)

    assert cap_eff == pytest.approx(0.20), "cap_eff = max(0.10, 1/5)"
    assert res.cap_eff == pytest.approx(cap_eff, abs=1e-12)
    for k, v in res.weights.items():
        assert v == pytest.approx(0.2, abs=1e-12), f"{k}={v} — 균등해가 아니다"
    assert abs(sum(res.weights.values()) - 1.0) < 1e-9


def test_ac_sag_001_b_proportional_redistribution_observable_at_n15() -> None:
    """(B · 비례 배분) `[1000, 15, 10×13]` (n=15) — 최상위만 상한, 나머지는 **원비중 비례**.

    `cap_eff == max(0.10, 1/15) == 0.10`. 최상위 원비중 `1000/1145 == 0.873362…`.
    실측 리터럴(2026-08-13): `w[1] == 0.0931034483`, `w[2] == 0.0620689655`.
    """
    from my_chart.analysis.weighting import capped_weights_detail

    caps = _caps([1000, 15] + [10] * 13)
    res = capped_weights_detail(caps, cap=CAP)
    w = res.weights
    cap_eff = _cap_eff(15)

    assert res.cap_eff == pytest.approx(cap_eff, abs=1e-12)
    assert w["s0"] == pytest.approx(cap_eff, abs=1e-12), "최상위가 cap_eff 로 고정되지 않았다"
    assert w["s1"] / w["s2"] == pytest.approx(1.5, abs=1e-12), "원 시총비 15/10 이 깨졌다"
    assert w["s1"] == pytest.approx(0.0931034483, abs=1e-9)
    assert w["s2"] == pytest.approx(0.0620689655, abs=1e-9)
    # 균등 배분이었다면 미상한 14종목이 전부 0.90/14 == 0.0642857… 로 같아진다.
    assert w["s1"] != pytest.approx(0.90 / 14, abs=1e-9), "균등 배분으로 되돌아갔다"
    assert abs(sum(w.values()) - 1.0) < 1e-9
    assert max(w.values()) <= cap_eff + 1e-12


def test_ac_sag_001_termination_is_structural_not_a_count_threshold() -> None:
    """(종료 계약) 반복 `<= min(n, 20)` 이고 **반복 상한 소진으로 종료하지 않는다**.

    v0.4.1 의 *"5회 이하 수렴"* 은 폐기된 거짓 임계다(실측 최악 6~7회) — 되살리지 않는다.
    계약은 횟수가 아니라 "동결 집합이 매 회 엄격히 증가한다"는 구조다.
    """
    from my_chart.analysis.weighting import (
        MAX_REDISTRIBUTION_ITERATIONS,
        capped_weights_detail,
    )

    assert MAX_REDISTRIBUTION_ITERATIONS == 20, "안전 상한 20 (plan.md §3.1)"

    for values in ([70, 10, 10, 5, 5], [1000, 15] + [10] * 13, [600] + [40] * 11,
                   [3000] + [100] * 24, [55] + [5] * 20, [100] + [1] * 14):
        res = capped_weights_detail(_caps(values), cap=CAP)
        n = len(values)
        assert res.iterations <= min(n, MAX_REDISTRIBUTION_ITERATIONS), (
            f"n={n} 반복 {res.iterations} > min(n, 20)")
        assert res.exhausted is False, f"n={n} 반복 상한 소진으로 종료했다"
        assert max(res.weights.values()) <= res.cap_eff + 1e-12


def test_ac_sag_001_uniform_caps_need_no_redistribution() -> None:
    """(무구속) 15종목 동일 시총 — 결과가 등가중 `1/15` 이고 반복 횟수가 **0**."""
    from my_chart.analysis.weighting import capped_weights_detail

    res = capped_weights_detail(_caps([10] * 15), cap=CAP)
    assert res.iterations == 0, "상한이 구속하지 않는데 재배분이 일어났다"
    for v in res.weights.values():
        assert v == pytest.approx(1 / 15, abs=1e-12)
    assert res.capped_members == (), "상한 미구속인데 capped_members 가 생겼다"


# ---------------------------------------------------------------------------
# AC-SAG-003 (산출물 절) — 상한 적용 사실의 노출 (규칙 AG-2)
# ---------------------------------------------------------------------------

def test_ac_sag_003_capped_members_expose_raw_and_cap_eff_at_n12() -> None:
    """`[600, 40×11]` (n=12) — `capped_members` 가 정확히 1건, `capped_weight == cap_eff`."""
    from my_chart.analysis.weighting import capped_weights_detail

    res = capped_weights_detail(_caps([600] + [40] * 11), cap=CAP)
    cap_eff = _cap_eff(12)

    assert res.cap_eff == pytest.approx(cap_eff, abs=1e-12)
    assert len(res.capped_members) == 1, f"capped_members = {res.capped_members}"
    top = res.capped_members[0]
    assert top.raw_weight == pytest.approx(0.5769230769, abs=1e-9)   # 600/1040
    assert top.capped_weight == pytest.approx(cap_eff, abs=1e-9)
    # 상한에 걸리지 않은 11종목은 각각 40/440 × 0.90.
    rest = [v for k, v in res.weights.items() if k != top.name]
    assert len(rest) == 11
    for v in rest:
        assert v == pytest.approx(0.0818181818, abs=1e-9)
    assert res.iterations == 1
    assert abs(sum(res.weights.values()) - 1.0) < 1e-9


def test_ac_sag_003_degenerate_contrast_n6_capped_weight_is_not_the_cap_literal() -> None:
    """(축퇴 대조 — D17 재발 방지) 같은 비율의 6종목 `[600, 88×5]`.

    `cap_eff == 1/6 == 0.1666…` 이므로 상한 적용 후 가중치가 `weight_cap` 과 갈린다.
    상한 적용 후 가중치를 `weight_cap` 상수로 하드코딩한 구현은 여기서 **RED** 가 된다.
    """
    from my_chart.analysis.weighting import capped_weights_detail

    res = capped_weights_detail(_caps([600] + [88] * 5), cap=CAP)
    cap_eff = _cap_eff(6)

    assert res.cap_eff == pytest.approx(cap_eff, abs=1e-12)
    assert cap_eff != pytest.approx(CAP), "n=6 에서 cap_eff 가 weight_cap 과 같아졌다"
    for v in res.weights.values():
        assert v == pytest.approx(1 / 6, abs=1e-12), "축퇴 구간인데 균등이 아니다"
    for m in res.capped_members:
        assert m.capped_weight == pytest.approx(cap_eff, abs=1e-9)
        assert m.capped_weight != pytest.approx(CAP, abs=1e-3), (
            "capped_weight 가 weight_cap 리터럴로 고정돼 있다")


# ---------------------------------------------------------------------------
# AC-SAG-010 — 유효 종목수 effective_n (INV-CAP-1 명제 3)
# ---------------------------------------------------------------------------

def test_ac_sag_010_a_effective_n_at_n25_is_160_over_7() -> None:
    """(A) `[3000, 100×24]` (n=25) — 상한 후 `effective_n == 160/7 == 22.8571428571`.

    상한 없는 순수 시총가중은 `3.1558441558` 이므로 상한 재배분이 유효 종목수를
    **약 7.2배**로 끌어올린다. `effective_n <= n` 은 INV-CAP-1 명제 3의 항등적 귀결.
    """
    from my_chart.analysis.weighting import capped_weights, effective_n

    caps = _caps([3000] + [100] * 24)
    cap_eff = _cap_eff(25)

    capped_en = effective_n(capped_weights(caps, cap=CAP))
    # cap=1.0 은 "상한 없음" — 원비중 그대로다.
    uncapped_en = effective_n(capped_weights(caps, cap=1.0))

    assert cap_eff == pytest.approx(CAP), "n=25 에서는 cap_eff == weight_cap"
    assert capped_en == pytest.approx(160 / 7, abs=1e-9)
    assert capped_en == pytest.approx(22.8571428571, abs=1e-9)
    assert uncapped_en == pytest.approx(3.1558441558, abs=1e-9)
    assert capped_en <= 25, "effective_n 이 n 을 넘었다 — 산술적으로 불가능하다"
    assert capped_en / uncapped_en == pytest.approx(7.24, abs=0.01)


@pytest.mark.parametrize("values,n", [([70, 10, 10, 5, 5], 5), ([600] + [88] * 5, 6)])
def test_ac_sag_010_degenerate_effective_n_collapses_to_n(values: list, n: int) -> None:
    """(축퇴 대조 — D22 재발 방지) `n <= 10` 이면 `effective_n == n` 으로 **정확히** 붕괴한다."""
    from my_chart.analysis.weighting import capped_weights, effective_n

    en = effective_n(capped_weights(_caps(values), cap=CAP))
    assert en == pytest.approx(float(n), abs=1e-9), (
        f"n={n} 축퇴 구간의 effective_n 이 {en} — n 이외의 값을 가질 수 없다")


def test_ac_sag_010_mut_effective_n_uncapped_is_detectable() -> None:
    """되돌림 대조 `mut_effective_n_uncapped` 의 **검출력**을 실측한다(§8.4 규약 10).

    `effective_n` 을 상한 **적용 전** 원비중으로 산출하는 변형은 (A) 의 기대값을
    `22.8571428571 → 3.1558441558` 로 바꾼다. 편차가 허용오차(`1e-9`)의 약 `10^10` 배이므로
    검출은 확정적이다. 실제 되돌림 실증은 progress.md §E.2 에 verbatim 으로 기록한다.
    """
    from my_chart.analysis.weighting import capped_weights, effective_n

    caps = _caps([3000] + [100] * 24)
    correct = effective_n(capped_weights(caps, cap=CAP))
    mutated = effective_n(capped_weights(caps, cap=1.0))   # 변형이 산출할 값
    assert abs(correct - mutated) / 1e-9 > 1e9, "변형의 편차가 허용오차를 가로지르지 않는다"


def test_effective_n_is_inverse_herfindahl_and_none_on_empty() -> None:
    from my_chart.analysis.weighting import effective_n

    assert effective_n({"a": 0.5, "b": 0.25, "c": 0.25}) == pytest.approx(1 / 0.375)
    assert effective_n({}) is None


# ---------------------------------------------------------------------------
# AC-SAG-049 — 종료·불변식 계약 (시드 고정 무작위 스윕)
# ---------------------------------------------------------------------------

SWEEP_SEED = 20260813            # AC 본문 리터럴 — 재현성을 위해 테스트 상수로 고정
SWEEP_CASES = 4000
SWEEP_N_MIN, SWEEP_N_MAX = 2, 40


def _sweep_inputs() -> list[dict[str, float]]:
    """AC-SAG-049 Given — `random.seed(20260813)`, 4,000 케이스, `n ~ U{2..40}`,
    각 종목 시총 `10**uniform(0,4) * random()`."""
    rnd = random.Random(SWEEP_SEED)
    out = []
    for _ in range(SWEEP_CASES):
        n = rnd.randint(SWEEP_N_MIN, SWEEP_N_MAX)
        out.append({f"s{i}": 10 ** rnd.uniform(0, 4) * rnd.random() for i in range(n)})
    return out


@pytest.fixture(scope="module")
def sweep() -> list[dict[str, float]]:
    return _sweep_inputs()


def test_ac_sag_049_invariants_cap_termination_normalization(sweep) -> None:
    """불변식 1(상한) · 2(종료) · 3(정규화) — **전 4,000 케이스**에서 위반 0건."""
    from my_chart.analysis.weighting import (
        MAX_REDISTRIBUTION_ITERATIONS,
        capped_weights_detail,
    )

    cap_violations, exhausted, bound_violations, norm_violations = [], [], [], []
    worst_iterations = 0
    for caps in sweep:
        n = len(caps)
        res = capped_weights_detail(caps, cap=CAP)
        worst_iterations = max(worst_iterations, res.iterations)
        if max(res.weights.values()) > res.cap_eff + 1e-9:
            cap_violations.append((n, max(res.weights.values()), res.cap_eff))
        if res.exhausted:
            exhausted.append(n)
        if res.iterations > min(n, MAX_REDISTRIBUTION_ITERATIONS):
            bound_violations.append((n, res.iterations))
        if abs(sum(res.weights.values()) - 1.0) >= 1e-9:
            norm_violations.append((n, sum(res.weights.values())))

    assert cap_violations == [], f"불변식 1 위반 {len(cap_violations)}건: {cap_violations[:3]}"
    assert bound_violations == [], f"불변식 2 반복 상한 초과: {bound_violations[:3]}"
    assert exhausted == [], f"불변식 2 반복 상한 소진 종료 {len(exhausted)}건"
    assert norm_violations == [], f"불변식 3 위반: {norm_violations[:3]}"
    # 실측 최악 반복은 6회(본 스윕). *"5회 이하"* 는 폐기된 거짓 임계이므로 되살리지 않는다.
    assert worst_iterations <= min(SWEEP_N_MAX, MAX_REDISTRIBUTION_ITERATIONS)


def test_ac_sag_049_matches_plan31_fixed_point(sweep) -> None:
    """고정점 등가 — 동결형 == §3.1 verbatim 을 2,000회까지 돌린 값(실측 최대 편차 6.696e-12)."""
    from my_chart.analysis.weighting import capped_weights

    worst = 0.0
    for caps in sweep:
        prod = capped_weights(caps, cap=CAP)
        oracle = _plan31_verbatim(caps, cap=CAP, iterations=2000)
        worst = max(worst, max(abs(prod[k] - oracle[k]) for k in caps))
    assert worst < 1e-9, f"§3.1 고정점과 최대 편차 {worst:.3e}"


def test_ac_sag_049_matches_closed_form(sweep) -> None:
    """닫힌 해 대조 — 반복형·닫힌 해 두 경로가 독립적으로 같은 값을 낸다."""
    from my_chart.analysis.weighting import capped_weights

    worst = 0.0
    for caps in sweep:
        prod = capped_weights(caps, cap=CAP)
        oracle = _closed_form(caps, cap=CAP)
        worst = max(worst, max(abs(prod[k] - oracle[k]) for k in caps))
    assert worst < 1e-9, f"닫힌 해와 최대 편차 {worst:.3e}"


def test_ac_sag_049_mut_plan31_verbatim_is_detectable(sweep) -> None:
    """대조 단언 `mut_plan31_verbatim` 의 **검출력 실측**(§8.4 규약 10).

    §3.1 v0.4.1 verbatim(동결 없음)을 20회로 끊으면 불변식 1이 다수 케이스에서 깨진다 —
    실측 3,183 / 4,000. 즉 이 변형의 검출은 확률적이 아니라 **사실상 확정적**이다.
    실제 되돌림 실증(프로덕션을 verbatim 으로 되돌린 상태의 RED 출력)은
    progress.md §E.2 에 verbatim 으로 기록한다.
    """
    violations = 0
    for caps in sweep:
        w = _plan31_verbatim(caps, cap=CAP, iterations=20)
        if max(w.values()) > _cap_eff(len(caps)) + 1e-9:
            violations += 1
    assert violations >= 1, "변형이 불변식 1을 한 건도 깨지 않는다 — 대조가 무효다"
    assert violations == 3183, f"검출 케이스 수 실측 불일치: {violations} != 3183"


# ---------------------------------------------------------------------------
# 에지 케이스
# ---------------------------------------------------------------------------

def test_edge_e2_single_member_cap_not_binding() -> None:
    """E2 — `n == 1` 이면 `cap_eff = max(0.10, 1/1) = 1.0` 으로 상한 무구속."""
    from my_chart.analysis.weighting import capped_weights_detail

    res = capped_weights_detail(_caps([42.0]), cap=CAP)
    assert res.cap_eff == pytest.approx(_cap_eff(1))
    assert res.weights["s0"] == pytest.approx(1.0)
    assert res.capped_members == ()


def test_empty_and_nonpositive_caps_yield_no_weights() -> None:
    """시총 합이 `<= 0` 이거나 입력이 비면 가중치를 만들지 않는다(대체값 부여 금지)."""
    from my_chart.analysis.weighting import capped_weights

    assert capped_weights({}) == {}
    assert capped_weights({"a": 0.0, "b": 0.0}) == {}


def test_weighted_mean_excludes_missing_and_renormalizes() -> None:
    """`weighted_mean` 은 결측 종목을 0 으로 접지 않고 **분모에서 제외**한다(§9.1)."""
    from my_chart.analysis.weighting import weighted_mean

    weights = {"a": 0.5, "b": 0.3, "c": 0.2}
    got = weighted_mean({"a": 10.0, "b": 20.0, "c": None}, weights)
    assert got == pytest.approx((0.5 * 10 + 0.3 * 20) / 0.8)
    assert got != pytest.approx(0.5 * 10 + 0.3 * 20), "결측을 0 으로 접었다"
    assert weighted_mean({"a": None}, {"a": 1.0}) is None
