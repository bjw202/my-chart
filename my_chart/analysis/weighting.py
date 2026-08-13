# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M2 — 시총 상한 재배분 가중치 (규칙 AG-1/AG-2).

**섹터 집계와 벤치마크 집계가 이 모듈의 같은 함수를 호출한다**(plan.md §1 D1/D2).
불변식 EX-1(방법론 일치)·BM-2 를 테스트가 아니라 **구조로 보장**하기 위함이다 —
같은 함수를 부르면 가중 방식이 어긋날 수 없다.

동결(freeze) 형태 — plan.md §3.1 v0.4.2 [HARD · 근거 기록]
----------------------------------------------------------
plan.md §3.1 의 **v0.4.1 verbatim** 형태는 상한에 걸린 종목을 `cap_eff` 로 고정하지만
다음 반복에서 그 종목이 `over` 조건에 걸리지 않아 `rest` 로 분류되어 **재배분을 다시
받는다**. 진동하다 20회 안전 상한에서 **상한을 초과한 채 종료**한다 — 실측(2026-08-13,
seed `20260813`, 4,000 케이스, `n ∈ [2,40]`) **3,183건(79.6%)** 이 상한 초과 상태로
종료했고 최악은 `n=6` 에서 `cap_eff=0.166667` 대비 `max(w)=0.211925`(**+27.2%**)였다.

본 구현은 상한에 걸린 종목을 **동결**해 이후 재배분 집합에서 영구 제외한다. `frozen`
이 매 반복 진부분집합으로 엄격히 증가하므로 반복은 **`<= min(n, 20)`회에 반드시
종료**하며(구조적 종료 계약 — AC-SAG-001 · AC-SAG-049 불변식 2), 종료 시점에
`max(w) <= cap_eff` 가 성립한다. **반복 상한 소진은 정상 종료 경로가 아니다**
(:attr:`WeightResult.exhausted` 가 그 사건을 노출한다).

*"5회 이하 수렴"* 은 v0.4.2 에서 **폐기된 거짓 임계**다 — 실측 최악 반복은 본 스윕
**6회**, 확장 스윕(60,000 케이스 · `n <= 60` · seed 7) **7회**다. 계약은 횟수 임계가
아니라 위 종료 증명이다.

두 형태는 **같은 고정점**을 갖는다 — verbatim 을 2,000회까지 돌린 결과와 최대 편차
`6.696e-12`, 닫힌 해와 `3.053e-16`. 즉 이 교체는 결과값이 아니라 **종료 성질만**
고친다. 기계 검증은 `tests/test_weighting.py` 의 AC-SAG-049 스윕이며, 오라클은
프로덕션을 import 하지 않고 §3.1 을 독립 재구현한다(acceptance.md §8.3).

축퇴 경계 (INV-CAP-1 명제 2)
---------------------------
`cap_eff = max(cap, 1/n)` 이므로 `cap=0.10` 에서 `n <= 10` 이면 `n × cap_eff = 1` 이
되어 `max(w) <= cap_eff ∧ Σw = 1` 의 해가 **균등 하나뿐**이다. 상한 재배분이 관측
가능한 하한은 `n >= 11` 이며, 상한 적용 후 가중치의 기대값은 `weight_cap` 리터럴이
아니라 항상 `cap_eff(n)` 이다.
"""
from __future__ import annotations

from dataclasses import dataclass

from my_chart.analysis.aggregate_types import WEIGHT_CAP, CappedMember

#: 재배분 반복 안전 상한(plan.md §3.1). 실제 상한은 `min(n, 20)` 이며 동결 집합이 매 회
#: 엄격히 증가하므로 도달하지 않는다(실측 최악 6회 / 확장 스윕 7회).
MAX_REDISTRIBUTION_ITERATIONS = 20

#: 상한 초과 판정 허용 오차(plan.md §3.1 verbatim 과 동일).
_EPS = 1e-12


@dataclass(frozen=True)
class WeightResult:
    """상한 재배분 결과.

    Attributes:
        weights: 종목별 가중치. ``Σw == 1`` (빈 입력이면 빈 dict).
        cap_eff: ``max(cap, 1/n)`` — 상한 적용 후 가중치의 기대값은 항상 이 값이며
            ``weight_cap`` 리터럴이 아니다(INV-CAP-1 명제 1).
        iterations: 실제 재배분 반복 횟수. 계약 상한은 ``min(n, 20)``.
        capped_members: 상한이 적용된 종목(원비중 + 적용 후 비중) — 규칙 AG-2.
        exhausted: 반복 상한을 **소진**하며 루프를 빠져나왔는가. 동결 형태에서는 항상
            ``False`` 여야 한다 — ``True`` 는 종료 계약 위반이며 AC-SAG-049 불변식 2가
            이 필드로 그 사건을 관측한다.
    """

    weights: dict[str, float]
    cap_eff: float
    iterations: int
    capped_members: tuple[CappedMember, ...]
    exhausted: bool = False


# @MX:ANCHOR: [AUTO] AG-1 상한 재배분 가중치 계약 — 섹터·벤치마크 공용 진입점.
#   fan_in = 3 (M2/M3 동일 실측: `capped_weights` 래퍼 + `sector_metrics._aggregate_members`
#   2곳). M3 는 벤치마크를 `_aggregate_members` **재사용**(`_compute_benchmark`)으로
#   구현했으므로 새 호출 지점이 생기지 않았다 — 호출 **빈도**는 늘지만 call-site 수는
#   그대로다(EX-1 구조 보장이 정확히 "새 지점을 만들지 않는 것"이다).
# @MX:REASON: EX-1(방법론 일치)·BM-2 를 "같은 함수 호출" 이라는 구조로 보장한다. 벤치마크가
#   별도 구현을 두면 유니버스·상한·결측 처리가 조용히 갈리고, 그 어긋남은 응답에 두 값이
#   모두 실려 겉보기 일치하는 형태로 **무증상 진행**한다(plan.md D1/D2, §3.2).
#   불변식: (1) 0 < Σw 정규화 후 Σw == 1, (2) max(w) <= cap_eff = max(cap, 1/n),
#   (3) 미동결 종목 간 비중 비율 보존(비례 배분), (4) 반복 <= min(n, 20) 이며 반복 상한
#   소진으로 종료하지 않는다(exhausted is False).
def capped_weights_detail(
    caps: dict[str, float], cap: float = WEIGHT_CAP
) -> WeightResult:
    """시총 상한 재배분 가중치를 산출한다(규칙 AG-1).

    Args:
        caps: ``{종목명: 시가총액}``. 시총이 NULL 이거나 `<= 0` 인 종목은 **호출 전에**
            제외한다(규칙 AG-3 — 이 함수는 대체값을 부여하지 않는다).
        cap: 종목 비중 상한. 기본값은 :data:`WEIGHT_CAP` (0.10, plan.md D3).

    Returns:
        :class:`WeightResult`. 입력이 비었거나 시총 합이 `<= 0` 이면 빈 가중치.

    Note:
        ``cap_eff = max(cap, 1/n)`` 이므로 ``n <= 1/cap`` 인 섹터에서는
        ``cap_eff = 1/n`` 이 되어 결과가 **등가중으로 강제**된다. 즉 `cap=0.10` 에서
        비례 배분이 관측 가능한 구간은 `n >= 11` 이다.
    """
    n = len(caps)
    if n == 0:
        return WeightResult({}, cap, 0, ())

    total = sum(caps.values())
    if total <= 0:
        return WeightResult({}, cap, 0, ())

    cap_eff = max(cap, 1.0 / n)
    raw = {k: v / total for k, v in caps.items()}
    w = dict(raw)

    frozen: set[str] = set()
    iterations = 0
    exhausted = True          # 아래 `break` 경로 중 하나를 타면 False 로 내려간다
    # 매 회 `frozen` 이 진부분집합으로 엄격히 증가하므로 `min(n, 20)` 회 안에 종료한다.
    for _ in range(min(n, MAX_REDISTRIBUTION_ITERATIONS)):
        over = {k for k, v in w.items() if k not in frozen and v > cap_eff + _EPS}
        if not over:
            exhausted = False
            break
        iterations += 1
        frozen |= over
        for k in over:
            w[k] = cap_eff

        rest = {k: w[k] for k in w if k not in frozen}
        if not rest:
            # 전 종목이 동결됐다 — n × cap_eff == 1 인 축퇴 구간이며 이미 균등이다.
            exhausted = False
            break
        rest_total = sum(rest.values())
        remaining = 1.0 - cap_eff * len(frozen)
        for k in rest:
            # 미동결 종목의 **현재 비중에 비례**해 잔여 예산을 배분한다(균등 배분 아님).
            # rest_total == 0 은 전 종목이 상한에 걸린 경우이며 이때 이미 등가중이다.
            w[k] = rest[k] / rest_total * remaining if rest_total > 0 else remaining / len(rest)

    capped = tuple(
        CappedMember(name=k, raw_weight=raw[k], capped_weight=w[k])
        for k in sorted(frozen)
        if raw[k] > cap_eff + _EPS
    )
    return WeightResult(w, cap_eff, iterations, capped, exhausted)


def capped_weights(caps: dict[str, float], cap: float = WEIGHT_CAP) -> dict[str, float]:
    """:func:`capped_weights_detail` 의 가중치만 반환하는 얇은 래퍼."""
    return capped_weights_detail(caps, cap).weights


def effective_n(weights: dict[str, float]) -> float | None:
    """유효 종목수 ``1 / Σwᵢ²`` (AC-SAG-010). 가중치가 없으면 ``None``."""
    denom = sum(v * v for v in weights.values())
    if denom <= 0:
        return None
    return 1.0 / denom


def weighted_mean(values: dict[str, float], weights: dict[str, float]) -> float | None:
    """``Σ(wᵢ × rᵢ) / Σwᵢ`` — 가중치가 있는 종목만으로 재정규화해 계산한다.

    결측 종목을 0 으로 치환하지 않는다(§9.1). 분모는 **값이 존재하는 종목의 가중치
    합** 이므로 결측 제외 후 자동으로 재정규화된다(AC-SAG-004).
    """
    num = 0.0
    den = 0.0
    for k, w in weights.items():
        v = values.get(k)
        if v is None:
            continue
        num += w * v
        den += w
    if den <= 0:
        return None
    return num / den
