# coding: utf-8
"""SPEC-SECTOR-METRIC-UNIFY-001 M1 — RED: 버블 sectors[] ↔ 랭킹 봉투 data[] 파리티 계약.

M4 가 메트릭 원천을 봉투로 통일하면 GREEN 이 되는 **미래 계약** 테스트.
현재 구현(버블 독자 산식)에서는 RED 다 — M0 특성화(test_bubble_characterization.py,
commit 6aabf81)가 9조합 전부에서 교집합 전 섹터·전 필드쌍 불일치(N=18)를 관측했다.

AC-SMU-001 의 4개 필드쌍 — 오른쪽은 **항상 봉투 ``data[]``**, legacy ``sectors[]`` 아님:
  rs_avg          ↔ data[].rs_avg.value
  excess_return   ↔ data[].excess_returns[p].value
  trading_value   ↔ data[].trading_value[p].value
  period_return   ↔ data[].returns[p].value

동봉 가드(현재 PASS, M4 이후에도 유지되어야 함):
- AC-SMU-009/010 — 봉투 ``market_filter`` echo, ``benchmark`` non-null, ``data`` 비휘발.
- AC-SMU-003 — rs_avg 기간 불변(버블·봉투 양쪽) + 동반 단언(기간 의존 3필드는 실제로
  기간에 따라 달라진다 — 항진명제 방어).
- AC-SMU-004 — 봉투 쪽 초과수익률 항등식 returns[p] − benchmark.returns[p] == excess_returns[p].

⚠ M4 메모 — MIN_SECTOR_MEMBERS=5(AG-5) 때문에 봉투에만 있는 섹터(bubble-only)는
정당하게 존재할 수 있다(M0 관측: kospi → 디스플레이·스마트폰·패션, kosdaq → 패션).
따라서 본 파일은 집합 **완전 일치를 단언하지 않고** 조인 무결성만 단언하며,
bubble-only/missing 집합은 기록만 한다(AC-SMU-015 관찰자).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = FIXTURE_DIR / "weekly.db"
DAILY_DB = FIXTURE_DIR / "daily.db"
REGISTRY = FIXTURE_DIR / "registry.xlsx"

AS_OF = "2026-08-11"
PERIODS = ("1w", "1m", "3m")
MARKETS = ("all", "kospi", "kosdaq")
TOL = 1e-9


@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    """집계 프로즌 픽스처에 고정된 TestClient (M0 test_bubble_characterization.py 관용)."""
    from fastapi.testclient import TestClient

    from backend.main import app

    with (
        patch("backend.routers.sectors.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("backend.routers.sectors.DAILY_DB_PATH", str(DAILY_DB)),
        patch("backend.routers.stage.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("my_chart.registry.SECTORMAP_PATH", str(REGISTRY)),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    ):
        yield TestClient(app)


def _get_bubble(client: Any, period: str, market: str) -> dict[str, Any]:
    resp = client.get("/api/sectors/bubble", params={"period": period, "market": market})
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


def _get_ranking(client: Any, period: str, market: str) -> dict[str, Any]:
    resp = client.get("/api/sectors/ranking",
                      params={"as_of": AS_OF, "market": market, "period": period})
    assert resp.status_code == 200, resp.text[:300]
    return resp.json()


def _equal(a: float | None, b: float | None) -> bool:
    """None-None 은 일치, 한쪽만 None 이면 불일치, 양쪽 값이면 TOL 이내 일치."""
    if a is None or b is None:
        return a is b
    return abs(a - b) <= TOL


# ---------------------------------------------------------------------------
# 1) 봉투 계약 가드 — AC-SMU-009/010 (현재 PASS, M4 이후 유지)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("period", PERIODS)
def test_envelope_contract(client: Any, period: str, market: str) -> None:
    """봉투 기본 계약: market_filter echo(009), benchmark non-null·기간 키 구비, data 비휘발(010)."""
    ranking = _get_ranking(client, period, market)

    assert ranking["market_filter"] == market, (
        f"market_filter={ranking['market_filter']!r} != 요청 market={market!r}"
    )
    benchmark = ranking["benchmark"]
    assert benchmark is not None, "benchmark 가 null 이다 (AC-SMU-010 위반)"
    assert benchmark["returns"] is not None
    for p in PERIODS:
        assert p in benchmark["returns"], f"benchmark.returns 에 {p} 키가 없다"
    assert ranking["data"], "data[] 가 비어 있다 (AC-SMU-010 위반)"


# ---------------------------------------------------------------------------
# 2) AC-SMU-001 파리티 — 4개 필드쌍 전 섹터 일치 (M4에서 GREEN, 현재 RED)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("period", PERIODS)
def test_parity_four_field_pairs(client: Any, period: str, market: str) -> None:
    """조인된 모든 공통 섹터에서 4개 필드쌍이 1e-9 이내로 일치해야 한다 (AC-SMU-001).

    현재는 M0 관측대로 교집합 전 섹터·전 필드쌍이 불일치 → RED.
    불일치 집계는 M0 의 N=18 측정과 같은 구조(per_pair 카운트)로 출력한다.
    """
    bubble = _get_bubble(client, period, market)
    ranking = _get_ranking(client, period, market)

    bubble_sectors = bubble["sectors"]
    data = ranking["data"]
    # 조인 무결성: 이름 중복 없음 (dict 축약이 중복을 숨기지 않아야 한다).
    assert len(bubble_sectors) == len({s["name"] for s in bubble_sectors}), (
        f"{period}/{market}: sectors[] 에 이름 중복이 있다"
    )
    assert len(data) == len({d["name"] for d in data}), (
        f"{period}/{market}: data[] 에 이름 중복이 있다"
    )

    bmap = {s["name"]: s for s in bubble_sectors}
    dmap = {d["name"]: d for d in data}

    # 조인 무결성: 봉투에만 있는 섹터는 AG-5 로 정당 — 기록만 한다(M0 관측:
    # kospi → 디스플레이·스마트폰·패션, kosdaq → 패션, all → 없음).
    # 봉투(data[])에만 있고 버블에 없는 섹터는 관측된 적 없다 — 이것은 단언.
    bubble_only = frozenset(bmap) - frozenset(dmap)
    missing_in_bubble = frozenset(dmap) - frozenset(bmap)
    assert not missing_in_bubble, (
        f"{period}/{market}: 버블에 없는 봉투 섹터 발견: {sorted(missing_in_bubble)}"
    )

    per_pair = {"rs_avg": 0, "excess_return": 0, "trading_value": 0, "period_return": 0}
    mismatching: set[str] = set()
    detail: list[str] = []
    for name, b in bmap.items():
        d = dmap.get(name)
        if d is None:
            continue  # bubble-only: AG-5 영역 — 4쌍 비교 대상 아님(기록됨)
        pairs = {
            "rs_avg": (b["rs_avg"], d["rs_avg"]["value"]),
            "excess_return": (b["excess_return"], d["excess_returns"][period]["value"]),
            "trading_value": (b["trading_value"], d["trading_value"][period]["value"]),
            "period_return": (b["period_return"], d["returns"][period]["value"]),
        }
        for key, (bv, dv) in pairs.items():
            if not _equal(bv, dv):
                per_pair[key] += 1
                mismatching.add(name)
                if len(detail) < 5:  # 메시지 폭주 방지 — 대표 5건만
                    detail.append(f"{name}.{key}: bubble={bv!r} envelope={dv!r}")

    n_common = len(bmap) - len(bubble_only)
    assert not mismatching, (
        f"{period}/{market}: 4개 필드쌍 불일치 섹터 {len(mismatching)}/{n_common} "
        f"(공통) — per_pair={per_pair}, bubble_only={sorted(bubble_only)}\n"
        + "\n".join(detail)
    )


# ---------------------------------------------------------------------------
# 3) AC-SMU-003 — rs_avg 기간 불변 + 동반 단언(항진명제 방어)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market", MARKETS)
def test_rs_avg_period_invariance(client: Any, market: str) -> None:
    """같은 market 에서 기간 1w/1m/3m 의 rs_avg 는 섹터별로 동일해야 한다 (양쪽 표면).

    동반 단언(항진명제 방어): excess_return·period_return(양쪽) 과
    trading_value(봉투 쪽) 은 기간에 따라 실제로 달라진다 — "모든 기간이 우연히
    같은 응답" 이 아니라 기간 파라미터가 실배선됨을 증명한다.
    (버블 trading_value 는 현재 기간 불변 — M0 관측. 기간 의존화는 AC-SMU-001
    파리티가 담당하므로 여기서 중복 단언하지 않는다. 봉투 쪽 trading_value[p] 는
    기간 의존이므로 동반 단언에 포함한다.)
    """
    bubbles = {p: _get_bubble(client, p, market) for p in PERIODS}
    rankings = {p: _get_ranking(client, p, market) for p in PERIODS}

    bmaps = {p: {s["name"]: s for s in bubbles[p]["sectors"]} for p in PERIODS}
    dmaps = {p: {d["name"]: d for d in rankings[p]["data"]} for p in PERIODS}

    common_b = set(bmaps["1w"]) & set(bmaps["1m"]) & set(bmaps["3m"])
    common_d = set(dmaps["1w"]) & set(dmaps["1m"]) & set(dmaps["3m"])
    assert common_b, f"{market}: 버블 3기간 공통 섹터가 없다"
    assert common_d, f"{market}: 봉투 3기간 공통 섹터가 없다"

    # 기간 불변 — 버블 sectors[].rs_avg
    for name in sorted(common_b):
        base = bmaps["1w"][name]["rs_avg"]
        for p in ("1m", "3m"):
            assert _equal(base, bmaps[p][name]["rs_avg"]), (
                f"{market}/{name}: 버블 rs_avg 가 기간 의존이다 "
                f"(1w={base!r} vs {p}={bmaps[p][name]['rs_avg']!r})"
            )
    # 기간 불변 — 봉투 data[].rs_avg.value
    for name in sorted(common_d):
        base = dmaps["1w"][name]["rs_avg"]["value"]
        for p in ("1m", "3m"):
            assert _equal(base, dmaps[p][name]["rs_avg"]["value"]), (
                f"{market}/{name}: 봉투 rs_avg 가 기간 의존이다 "
                f"(1w={base!r} vs {p}={dmaps[p][name]['rs_avg']['value']!r})"
            )

    # 동반 단언 1 — 버블 쪽 기간 의존 필드(excess_return, period_return)는 실제로 변한다.
    moved_b = [
        name for name in common_b
        if not _equal(bmaps["1w"][name]["excess_return"], bmaps["1m"][name]["excess_return"])
        and not _equal(bmaps["1w"][name]["period_return"], bmaps["1m"][name]["period_return"])
    ]
    assert moved_b, f"{market}: 버블 excess/period_return 이 1w↔1m 전혀 변하지 않는다"

    # 동반 단언 2 — 봉투 쪽 기간 의존 필드 3종(excess/return/trading_value)은 실제로 변한다.
    # 주의: 각 응답은 3기간을 전부 싣는다(AC-SAG-036) — 고정 키가 아니라
    # "요청 기간 p 의 키" 를 비교해야 한다(고정 키 비교는 항진명제가 된다).
    envelope_period_fields = ("returns", "excess_returns", "trading_value")
    moved_d = [
        name for name in common_d
        if all(
            not _equal(dmaps["1w"][name][k]["1w"]["value"],
                       dmaps["1m"][name][k]["1m"]["value"])
            for k in envelope_period_fields
        )
    ]
    assert moved_d, f"{market}: 봉투 returns/excess/trading_value 가 1w↔1m 전혀 변하지 않는다"


# ---------------------------------------------------------------------------
# 4) AC-SMU-004 — 봉투 쪽 초과수익률 항등식 (현재 PASS, M4 통일 후에도 유지)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("market", MARKETS)
@pytest.mark.parametrize("period", PERIODS)
def test_excess_identity_envelope(client: Any, period: str, market: str) -> None:
    """data[].returns[p] − benchmark.returns[p] == data[].excess_returns[p] (봉투 쪽).

    값이 null(reason 기입)인 섹터는 양쪽 다 null 이어야 하고, 양쪽 다 값이 있으면
    항등식이 1e-9 이내로 성립해야 한다. M4 가 버블을 이 원천에 연결하므로
    항등식은 통일 후에도 그대로 유지되어야 한다.
    """
    ranking = _get_ranking(client, period, market)
    bm_value = ranking["benchmark"]["returns"][period]["value"]
    assert bm_value is not None, f"{period}/{market}: benchmark.returns.{period} 가 null"

    checked = 0
    for d in ranking["data"]:
        ret = d["returns"][period]["value"]
        exc = d["excess_returns"][period]["value"]
        if ret is None and exc is None:
            continue  # 정당한 결측(reason 기입) — M0 관측: all→패션·헬스케어 등
        assert not (ret is None or exc is None), (
            f"{period}/{market}/{d['name']}: returns·excess 한쪽만 null "
            f"(ret={ret!r}, exc={exc!r})"
        )
        assert abs((ret - bm_value) - exc) <= TOL, (
            f"{period}/{market}/{d['name']}: 항등식 위반 "
            f"{ret!r} - {bm_value!r} != {exc!r}"
        )
        checked += 1
    assert checked > 0, f"{period}/{market}: 항등식 검증 대상 섹터가 0개다"
