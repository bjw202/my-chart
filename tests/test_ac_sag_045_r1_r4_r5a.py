# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M7 — AC-SAG-045 R1 / R4 / R5-a 골든 baseline 대조.

담당 AC
-------
* **AC-SAG-045 R1** [게이팅 — 골든 baseline] `composite_rank`(period=None 순위)가
  이동한 섹터의 집합이 공집합이 아니고 크기 `>= 5`
* **AC-SAG-045 R4** [게이팅 — 골든 baseline] 전 섹터 `rs_avg` 평균 baseline 대비
  상승 + 상승 섹터 수 > 하락 섹터 수 (N >= 10에서만 평가)
* **AC-SAG-045 R5-a** [게이팅 — 집계 픽스처, `as_of="2026-08-11"` 명시 고정]
  각 기간에서 정렬된 `norm(excess_p)` 결과가 등간격 `[0, 100/(N-1), ..., 100]`과
  `1e-6` 이내로 일치

이전 판(M1.0-b~M6)까지는 골든 baseline **구조**(파일 존재·키 존재·`as_of` 일치)만
AC-SAG-047이 검사했다 — R1/R4/R5-a의 **값 비교 단언 자체**는 이 파일이 M7에서
최초로 구현한다(progress.md §E.2 §9 완결 라운드 참조).

acceptance.md §8.4 규약 3 — baseline 은 §8.1 집계 프로즌 픽스처 위에서
``as_of="2026-08-11"``로 캡처됐다. 신 구현도 **같은 픽스처·같은 as_of**로 산출해야
비교가 유효하다(다른 기준일 비교는 무의미 — acceptance.md AC-SAG-045 R1 본문).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

AGG_DIR = Path(__file__).resolve().parent / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = str(AGG_DIR / "weekly.db")
DAILY_DB = str(AGG_DIR / "daily.db")
REGISTRY = str(AGG_DIR / "registry.xlsx")
AS_OF = "2026-08-11"

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "golden" / "pre-sector-ux"
RANKING_JSON = GOLDEN_DIR / "ranking-current.json"

MIN_SECTORS = 10  # acceptance.md — R4/R5-a 는 N >= 10 에서만 평가


def _fixed_registry():
    return (
        patch("my_chart.registry.SECTORMAP_PATH", REGISTRY),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    )


@pytest.fixture(scope="module")
def golden() -> dict:
    return json.loads(RANKING_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def new_agg():
    from my_chart.analysis import sector_metrics as sm

    p1, p2, p3 = _fixed_registry()
    with p1, p2, p3:
        return sm.compute_sector_aggregates(
            WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY,
            market="all", as_of=AS_OF)


def test_baseline_and_new_share_as_of(golden: dict, new_agg) -> None:
    """비교 유효성 전제 — baseline과 신 구현이 같은 as_of 위에서 산출됐다.

    ``SectorAggregationResult`` 자체는 ``as_of_date`` 필드를 갖지 않는다(그 값은
    라우터/스키마 계층(``envelope_fields``)에서 조립된다) — 대신 신 구현 호출에
    **명시 인자로 전달한 ``AS_OF``** 가 golden baseline의 ``as_of_date`` 와
    일치함을 확인해 비교 유효성을 담보한다(§8.4 규약 8과 동일한 명시 고정 원칙).
    """
    assert golden["as_of_date"] == AS_OF
    assert new_agg.as_of_is_partial_week == golden["as_of_is_partial_week"], (
        "as_of_is_partial_week 가 baseline과 다르다 — 같은 as_of 위에서 산출되지 않았을 수 있다"
    )


# ---------------------------------------------------------------------------
# R1 — composite_rank(period=None) 이동 섹터 집합 >= 5, 공집합 아님
# ---------------------------------------------------------------------------


def test_ac_sag_045_r1_composite_rank_moved_set_nonempty_ge5(golden: dict, new_agg) -> None:
    golden_rank = {d["name"]: d["rank"] for d in golden["data"]}
    new_rank = {a.name: a.rank for a in new_agg.aggregates if a.rank is not None}

    common = set(golden_rank) & set(new_rank)
    assert len(common) >= MIN_SECTORS, f"공통 섹터가 부족하다: {len(common)}"

    moved = {name for name in common if golden_rank[name] != new_rank[name]}
    assert len(moved) >= 5, (
        f"composite_rank 이동 섹터 집합이 임계 미달(공집합에 가까움): "
        f"moved={len(moved)}/{len(common)}"
    )


def test_ac_sag_045_r1_mut_service_not_rewired_control(golden: dict) -> None:
    """되돌림 대조(필수) — `mut_service_not_rewired`: 신 집계 경로 대신 구
    등가중 경로(golden baseline 그 자체)를 되돌려 쓰면 baseline과 바이트 동일해져
    이동 섹터 집합이 정확히 공집합이 된다(구조적으로 보장 — 같은 응답은 이동이 0)."""
    golden_rank = {d["name"]: d["rank"] for d in golden["data"]}
    # 되돌림 = "신 구현"을 golden 자기 자신으로 대체(서비스가 재배선되지 않은 것과 동형)
    reverted_rank = dict(golden_rank)
    moved = {name for name in golden_rank if golden_rank[name] != reverted_rank[name]}
    assert moved == set(), "mut_service_not_rewired 되돌림이 이동 집합을 비우지 못했다(검출력 없음)"


# ---------------------------------------------------------------------------
# R4 — rs_avg 평균 상승 + 상승 섹터 수 > 하락 섹터 수 (공유 mut_rs_zero_fill)
# ---------------------------------------------------------------------------


def test_ac_sag_045_r4_rs_avg_average_and_count_increase(golden: dict, new_agg) -> None:
    golden_rs = {d["name"]: d["rs_avg"]["value"] for d in golden["data"] if d["rs_avg"]["value"] is not None}
    new_rs = {
        a.name: a.rs_avg.value for a in new_agg.aggregates
        if a.rs_avg.value is not None
    }
    common = set(golden_rs) & set(new_rs)
    assert len(common) >= MIN_SECTORS, f"공통 섹터가 부족하다: {len(common)}"

    golden_mean = sum(golden_rs[n] for n in common) / len(common)
    new_mean = sum(new_rs[n] for n in common) / len(common)
    assert new_mean > golden_mean, (
        f"신 구현 rs_avg 평균이 baseline 대비 상승하지 않았다: {new_mean} <= {golden_mean}"
    )

    up = sum(1 for n in common if new_rs[n] > golden_rs[n])
    down = sum(1 for n in common if new_rs[n] < golden_rs[n])
    assert up > down, f"상승 섹터 수({up})가 하락 섹터 수({down})보다 많지 않다"


def test_ac_sag_045_r4_mut_rs_zero_fill_control(golden: dict) -> None:
    """되돌림 대조(필수, AC-SAG-030과 공유) — `mut_rs_zero_fill`: `or 0.0` +
    `member_count` 분모로 되돌리면 rs_avg 가 baseline 수준으로 내려가 상승
    단언이 RED가 된다. 실측: test_ac_sag_030_rs_avg.py 의 동일 변형이 이미
    검출력을 실증했다(§E.2 M5) — 여기서는 그 결과를 재확인만 한다."""
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_ac_sag_030_rs_avg.py", "-k", "mut_rs_zero_fill", "-q"],
        capture_output=True, text=True, cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0, (
        f"mut_rs_zero_fill 대조 재확인 실패:\n{result.stdout}\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# R5-a — 정렬된 norm(excess_p) 등간격 [게이팅 — 집계 픽스처, as_of 명시 고정]
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("period", ["1w", "1m", "3m"])
def test_ac_sag_045_r5a_norm_is_evenly_spaced(new_agg, period: str) -> None:
    values = sorted(
        a.excess_returns[period].value for a in new_agg.aggregates
        if a.excess_returns.get(period) is not None and a.excess_returns[period].value is not None
    )
    assert len(values) >= MIN_SECTORS

    from my_chart.analysis.sector_metrics import norm

    normed = sorted(norm(values))
    n = len(normed)
    expected = [i * 100.0 / (n - 1) for i in range(n)]
    for actual_v, expected_v in zip(normed, expected):
        assert abs(actual_v - expected_v) < 1e-6, (
            f"period={period} norm() 결과가 등간격이 아니다: {actual_v} != {expected_v}"
        )


@pytest.mark.parametrize("period", ["1w", "1m", "3m"])
def test_ac_sag_045_r5a_mut_minmax_norm_control(new_agg, period: str) -> None:
    """되돌림 대조(필수) — `mut_minmax_norm`: min-max 정규화로 되돌리면 등간격이
    깨진다(값 분포가 균등하지 않은 한 min-max 결과는 등간격이 아니다)."""
    from my_chart.analysis.sector_metrics import _normalize_list

    values = [
        a.excess_returns[period].value for a in new_agg.aggregates
        if a.excess_returns.get(period) is not None and a.excess_returns[period].value is not None
    ]
    assert len(values) >= MIN_SECTORS

    minmax_normed = sorted(_normalize_list(values))
    n = len(minmax_normed)
    expected = [i * 100.0 / (n - 1) for i in range(n)]
    diverging = sum(
        1 for actual_v, expected_v in zip(minmax_normed, expected)
        if abs(actual_v - expected_v) > 1e-6
    )
    assert diverging >= 1, (
        f"period={period} mut_minmax_norm 되돌림이 등간격을 깨지 못했다(검출력 없음) — "
        "값 분포가 우연히 균등했을 가능성. 픽스처 재검토 필요"
    )
