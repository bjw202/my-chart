# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M7 — AC-SAG-044 되돌림 검출 3케이스.

담당 AC
-------
* **AC-SAG-044** 의미 테스트로의 대체(테스트 1급 산출물) — ``tests/test_sector_metrics.py``
  의 필드-존재 확인 블록(구 ``hasattr`` 15건)을 값 단언으로 교체한 뒤, 그 대체가 실제
  검출력을 갖는지 아래 3가지 되돌림 변형으로 증명한다(acceptance.md §8.4 규약 9/10):

  (a) 시총가중 → 등가중 (시총 원천 부재 시 프로덕션의 AG-4 등가중 폴백 경로가 실제로
      다른 값을 낸다는 것을 확인)
  (b) 순위 백분위 정규화 → min-max 정규화 (``norm`` → ``_normalize_list`` 되돌림)
  (c) 벤치마크 방법론 일치 → 벤치마크 원천이 끊기면 초과수익률이 더 이상 벤치마크를
      따라가지 않는다(KOSPI 고정 legacy 표면에서 초과수익률의 벤치마크 민감도 실증)

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


def _rankings(daily_db_path: str | None):
    from my_chart.analysis.sector_metrics import compute_sector_ranking

    p1, p2, p3 = _fixed_registry()
    with p1, p2, p3:
        return compute_sector_ranking(WEEKLY_DB, AS_OF, daily_db_path=daily_db_path)


# ---------------------------------------------------------------------------
# (a) 시총가중 → 등가중 되돌림
# ---------------------------------------------------------------------------


def test_ac_sag_044_mut_a_cap_weight_to_equal_weight_changes_values() -> None:
    """되돌림 (a): daily_db_path 를 제거하면(시총 원천 부재) AG-4 등가중 폴백이
    걸려 ``sector_return_*`` 값이 시총가중 버전과 달라진다 — 값 단언이 이 변형을
    검출한다(구 ``hasattr`` 블록은 필드 존재만 확인하므로 이 변형에서도 GREEN이었다)."""
    cap_weighted = {r.name: r.sector_return_1m for r in _rankings(DAILY_DB)}
    equal_weighted = {r.name: r.sector_return_1m for r in _rankings(None)}

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
    """되돌림 (b): ``norm``(순위 백분위) 을 ``_normalize_list``(min-max) 로 되돌리면
    ``composite_score`` 가 달라진다 — 극단값이 스케일을 지배하는 min-max 의 정의적
    성질이 순위 백분위와 다른 결과를 낸다.

    [범위 정정] 이 되돌림은 ``tests/test_sector_metrics.py`` 가 다루는 legacy
    호환 표면(``compute_sector_ranking`` → ``SectorRank``)이 아니라 M3 신 집계 코어
    (``compute_sector_aggregates`` → ``_rank_sectors``)를 대상으로 한다 — 실측
    확인 결과 legacy 표면은 애초부터 ``_normalize_list``(min-max)를 무조건 쓰고
    있어(마이그레이션되지 않은 알려진 단순화) 그 표면에서는 되돌릴 대상이 없다
    (percentile→min-max 되돌림이 항등 변환이 되어 검출력 0). 신 집계 코어가
    percentile 정규화(AC-SAG-017/045 R5-a)의 실제 프로덕션 경로이므로 여기서
    되돌림 검출력을 증명하는 것이 정직한 대체다."""
    from my_chart.analysis import sector_metrics as sm

    p1, p2, p3 = _fixed_registry()
    with p1, p2, p3:
        baseline = sm.compute_sector_aggregates(
            WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY, as_of=AS_OF)
        with patch.object(sm, "norm", side_effect=sm._normalize_list):
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
    """되돌림 (c): ``_load_kospi_returns`` 를 0으로 고정하면(벤치마크 방법론이
    끊긴 것과 동형 — 초과수익률이 더 이상 실제 벤치마크를 반영하지 못한다)
    ``sector_excess_return_1w`` 가 ``sector_return_1w`` 와 완전히 같아진다.
    정상 경로에서는 KOSPI 수익률이 0이 아니므로 둘은 달라야 한다."""
    from my_chart.analysis import sector_metrics as sm

    baseline = _rankings(DAILY_DB)
    assert len(baseline) >= 1

    # 정상 경로 — 벤치마크가 살아 있으면 초과수익률 != 원수익률(KOSPI 1W != 0)
    normal_diff = [
        r for r in baseline
        if abs(r.sector_excess_return_1w - r.sector_return_1w) > 1e-9
    ]
    assert len(normal_diff) >= 5, "정상 경로에서 벤치마크가 초과수익률에 반영되지 않는다"

    def _zero_benchmark(conn, date):  # noqa: ANN001, ARG001
        return {"chg_1w": 0.0, "chg_1m": 0.0, "chg_3m": 0.0}

    with patch.object(sm, "_load_kospi_returns", side_effect=_zero_benchmark):
        mutated = _rankings(DAILY_DB)

    mutated_by_name = {r.name: r for r in mutated}
    still_matches = 0
    for r in baseline:
        m = mutated_by_name.get(r.name)
        if m is None:
            continue
        # 벤치마크가 0으로 끊기면 초과수익률 == 원수익률이어야 한다(방법론 단절 증거)
        if abs(m.sector_excess_return_1w - m.sector_return_1w) < 1e-9:
            still_matches += 1
    assert still_matches >= 5, (
        "벤치마크 원천을 끊었는데도 초과수익률이 원수익률과 갈리지 않는다 — "
        "벤치마크 방법론 대조가 검출력을 갖지 못한다"
    )
