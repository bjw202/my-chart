# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M7 — AC-SAG-044 되돌림 검출 3케이스.

담당 AC
-------
* **AC-SAG-044** 의미 테스트로의 대체(테스트 1급 산출물) — ``tests/test_sector_metrics.py``
  의 필드-존재 확인 블록(구 ``hasattr`` 15건)을 값 단언으로 교체한 뒤, 그 대체가 실제
  검출력을 갖는지 아래 3가지 되돌림 변형으로 증명한다(acceptance.md §8.4 규약 9/10):

  (a) 시총가중 → 등가중 (시총 원천을 전 종목 동일값으로 바꾸면 섹터 수익률이 달라진다)
  (b) 순위 백분위 정규화 → min-max 정규화 (``norm`` → 테스트 내 min-max 되돌림)
  (c) 벤치마크 방법론 일치 → 벤치마크 수익률이 끊기면(0 고정) 초과수익률이 더 이상
      벤치마크를 따라가지 않는다(초과수익률의 ALL_CAPPED 벤치마크 민감도 실증)

  레거시 순위 함수(KOSPI 지수 행 기준·min-max, 제거됨)를 대상으로 하던 (a)(c) 는 응답
  ``sectors[]``/``data[]`` 의 단일 원천인 ``compute_sector_aggregates`` 대상으로 이관했다.

이 파일은 §8.3 파생 규칙 원칙과 무관하다 — 프로덕션 함수를 직접 호출·패치하는
**mutation 스타일 대조**이며, 참조 구현 대조가 아니다(AC-SAG-044는 순수 합성 열거
소속, §8.4 규약 5).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

AGG_DIR = Path(__file__).resolve().parent / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = str(AGG_DIR / "weekly.db")
DAILY_DB = str(AGG_DIR / "daily.db")
REGISTRY = str(AGG_DIR / "registry.xlsx")
AS_OF = "2026-08-11"


def _fixed_registry():
    """AGG_DIR registry.xlsx 를 모듈 캐시에 고정한다(§8.3 registry 고정 요건과 동형)."""
    return (
        patch("my_chart.registry.SECTORMAP_PATH", REGISTRY),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    )


def _aggregates(**patches):
    """집계 픽스처 고정 + (선택) ``sector_metrics`` 속성 패치 상태로 집계를 산출한다."""
    from my_chart.analysis import sector_metrics as sm

    p1, p2, p3 = _fixed_registry()
    with p1, p2, p3:
        ctx = [patch.object(sm, k, side_effect=v) for k, v in patches.items()]
        for c in ctx:
            c.start()
        try:
            return sm.compute_sector_aggregates(
                WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY, as_of=AS_OF,
                compute_rank_change=False)
        finally:
            for c in ctx:
                c.stop()


def _minmax(values: list[float]) -> list[float]:
    """되돌림 변형 — min-max 0~100 정규화(제거된 레거시 정규화와 동형, 테스트 전용)."""
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0] * len(values)
    return [(v - lo) / (hi - lo) * 100 for v in values]


# ---------------------------------------------------------------------------
# (a) 시총가중 → 등가중 되돌림
# ---------------------------------------------------------------------------


def test_ac_sag_044_mut_a_cap_weight_to_equal_weight_changes_values() -> None:
    """되돌림 (a): 시총 원천을 전 종목 동일값으로 바꾸면(= 등가중) 섹터 수익률이 시총가중
    버전과 달라진다 — 값 단언이 이 변형을 검출한다(구 ``hasattr`` 블록은 필드 존재만
    확인하므로 이 변형에서도 GREEN이었다)."""
    from my_chart.analysis import sector_metrics as sm

    real_caps = sm._load_market_caps

    def _equal_caps(path):  # noqa: ANN001
        return {name: 1.0 for name in real_caps(path)}

    def _ret_1m(result) -> dict[str, float]:
        return {a.name: a.returns["1m"].value for a in result.aggregates
                if a.returns.get("1m") is not None and a.returns["1m"].value is not None}

    cap_weighted = _ret_1m(_aggregates())
    equal_weighted = _ret_1m(_aggregates(_load_market_caps=_equal_caps))

    common = set(cap_weighted) & set(equal_weighted)
    assert len(common) >= 10, "두 산출 모두에 존재하는 섹터가 충분히 있어야 대조가 유의미하다"

    diverging = [
        name for name in common
        if abs(cap_weighted[name] - equal_weighted[name]) > 1e-9
    ]
    # 대조 단언 — 시총가중 폴백을 제거하면 섹터 다수가 값이 달라진다(F12-a 요건상
    # n>=11 섹터가 다수이므로 상한 재배분의 해가 등가중과 갈린다).
    assert len(diverging) >= 3, (
        f"시총가중→등가중 되돌림이 값을 바꾸지 못했다(검출력 없음): "
        f"diverging={len(diverging)}/{len(common)}"
    )


# ---------------------------------------------------------------------------
# (b) 순위 백분위 정규화 → min-max 정규화 되돌림
# ---------------------------------------------------------------------------


def test_ac_sag_044_mut_b_percentile_norm_to_minmax_changes_composite() -> None:
    """되돌림 (b): ``norm``(순위 백분위) 을 min-max 로 되돌리면
    ``composite_score`` 가 달라진다 — 극단값이 스케일을 지배하는 min-max 의 정의적
    성질이 순위 백분위와 다른 결과를 낸다.

    대상은 응답 ``sectors[]``/``data[]`` 의 단일 원천인 집계 코어
    (``compute_sector_aggregates`` → ``_rank_sectors``)다 — percentile 정규화
    (AC-SAG-017/045 R5-a)의 실제 프로덕션 경로다."""
    from my_chart.analysis import sector_metrics as sm

    p1, p2, p3 = _fixed_registry()
    with p1, p2, p3:
        baseline = sm.compute_sector_aggregates(
            WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY, as_of=AS_OF)
        with patch.object(sm, "norm", side_effect=_minmax):
            mutated = sm.compute_sector_aggregates(
                WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY, as_of=AS_OF)

    baseline_scores = {
        a.name: a.composite_score.value for a in baseline.aggregates
        if a.composite_score.value is not None
    }
    mutated_scores = {
        a.name: a.composite_score.value for a in mutated.aggregates
        if a.composite_score.value is not None
    }
    common = set(baseline_scores) & set(mutated_scores)
    assert len(common) >= 10

    diverging = [
        name for name in common
        if abs(baseline_scores[name] - mutated_scores[name]) > 1e-6
    ]
    assert len(diverging) >= 3, (
        f"순위백분위→min-max 되돌림이 composite_score 를 바꾸지 못했다(검출력 없음): "
        f"diverging={len(diverging)}/{len(common)}"
    )


# ---------------------------------------------------------------------------
# (c) 벤치마크 방법론 일치 되돌림 — 벤치마크 원천 단절 시 초과수익률 민감도
# ---------------------------------------------------------------------------


def test_ac_sag_044_mut_c_benchmark_disconnect_changes_excess_return() -> None:
    """되돌림 (c): 벤치마크 수익률을 0으로 고정하면(벤치마크 방법론이 끊긴 것과 동형 —
    초과수익률이 더 이상 실제 벤치마크를 반영하지 못한다) ``excess_returns["1w"]`` 가
    ``returns["1w"]`` 와 완전히 같아진다. 정상 경로에서는 ALL_CAPPED 1W 수익률이 0이
    아니므로 둘은 달라야 한다."""
    import dataclasses

    from my_chart.analysis import sector_metrics as sm
    from my_chart.analysis.aggregate_types import present

    real_benchmark = sm._compute_benchmark

    def _zero_benchmark(*args, **kwargs):  # noqa: ANN002, ANN003
        b = real_benchmark(*args, **kwargs)
        return dataclasses.replace(b, returns={p: present(0.0) for p in ("1w", "1m", "3m")})

    def _pairs(result) -> dict[str, tuple[float, float]]:
        return {
            a.name: (a.returns["1w"].value, a.excess_returns["1w"].value)
            for a in result.aggregates
            if a.returns.get("1w") is not None and a.returns["1w"].value is not None
            and a.excess_returns.get("1w") is not None
            and a.excess_returns["1w"].value is not None
        }

    baseline = _pairs(_aggregates())
    assert len(baseline) >= 1

    # 정상 경로 — 벤치마크가 살아 있으면 초과수익률 != 원수익률(ALL_CAPPED 1W != 0)
    normal_diff = [n for n, (r, e) in baseline.items() if abs(e - r) > 1e-9]
    assert len(normal_diff) >= 5, "정상 경로에서 벤치마크가 초과수익률에 반영되지 않는다"

    mutated = _pairs(_aggregates(_compute_benchmark=_zero_benchmark))
    # 벤치마크가 0으로 끊기면 초과수익률 == 원수익률이어야 한다(방법론 단절 증거)
    still_matches = sum(1 for n, (r, e) in mutated.items() if n in baseline and abs(e - r) < 1e-9)
    assert still_matches >= 5, (
        "벤치마크 원천을 끊었는데도 초과수익률이 원수익률과 갈리지 않는다 — "
        "벤치마크 방법론 대조가 검출력을 갖지 못한다"
    )
