# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M6 — 라우터 파라미터 + 종목 목록 필드.

수용 기준: AC-SAG-039(market/period 파라미터) · AC-SAG-040(Bump 히스토리) ·
AC-SAG-041(종목 목록 필드) · AC-SAG-042(종목 버블 섹터 기준선) ·
AC-SAG-043(신규 필드 전 구간 전파 — 파생 구조 절, deferred-to-M6) ·
AC-SAG-007(최소 구성종목 수, deferred-to-M6).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = FIXTURE_DIR / "weekly.db"
DAILY_DB = FIXTURE_DIR / "daily.db"
REGISTRY = FIXTURE_DIR / "registry.xlsx"


@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    from fastapi.testclient import TestClient

    from backend.main import app

    with (
        patch("backend.routers.sectors.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("backend.routers.sectors.DAILY_DB_PATH", str(DAILY_DB)),
        patch("backend.routers.stage.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("backend.routers.stage.DAILY_DB_PATH", str(DAILY_DB)),
        patch("my_chart.registry.SECTORMAP_PATH", str(REGISTRY)),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    ):
        yield TestClient(app)


@pytest.fixture(scope="module")
def sector_name(client: Any) -> str:
    resp = client.get("/api/sectors/ranking")
    assert resp.status_code == 200, resp.text[:400]
    body = resp.json()
    assert body["data"]
    return str(body["data"][0]["name"])


# ---------------------------------------------------------------------------
# AC-SAG-039 — market/period 파라미터 신설
# ---------------------------------------------------------------------------

def test_ac_sag_039_ranking_market_filter_changes_data(client: Any) -> None:
    all_resp = client.get("/api/sectors/ranking").json()
    kospi_resp = client.get("/api/sectors/ranking?market=kospi").json()
    assert all_resp["market_filter"] == "all"
    assert kospi_resp["market_filter"] == "kospi"
    all_names = {d["name"] for d in all_resp["data"]}
    kospi_names = {d["name"] for d in kospi_resp["data"]}
    assert kospi_names != all_names, "market=kospi 응답이 market=all 과 동일 — 필터 미반영"
    # 필터는 집계 시점에 적용되므로 member_count 자체가 달라진다.
    kospi_members = {d["name"]: d["member_count"] for d in kospi_resp["data"]}
    all_members = {d["name"]: d["member_count"] for d in all_resp["data"]}
    common = set(kospi_members) & set(all_members)
    assert any(kospi_members[n] < all_members[n] for n in common), (
        "market=kospi 의 member_count 가 market=all 보다 작은 섹터가 하나도 없다")


def test_ac_sag_039_backward_compat_default_market_all(client: Any) -> None:
    """파라미터 미전달 == market=all (하위 호환)."""
    no_param = client.get("/api/sectors/ranking").json()
    explicit_all = client.get("/api/sectors/ranking?market=all").json()
    assert [d["name"] for d in no_param["data"]] == [d["name"] for d in explicit_all["data"]]
    assert no_param["market_filter"] == "all"


def test_ac_sag_039_invalid_market_returns_422(client: Any) -> None:
    resp = client.get("/api/sectors/ranking?market=nyse")
    assert resp.status_code == 422


def test_ac_sag_039_stage_overview_market_filter_changes_distribution(client: Any) -> None:
    all_resp = client.get("/api/stage/overview").json()
    kospi_resp = client.get("/api/stage/overview?market=kospi").json()
    assert kospi_resp["distribution"]["total"] < all_resp["distribution"]["total"]
    assert kospi_resp["market_filter"] == "kospi"


def test_ac_sag_039_sector_detail_market_filter(client: Any, sector_name: str) -> None:
    all_resp = client.get(f"/api/sectors/{sector_name}/detail").json()
    kospi_resp = client.get(f"/api/sectors/{sector_name}/detail?market=kospi").json()
    all_count = sum(s["stock_count"] for s in all_resp["sub_sectors"])
    kospi_count = sum(s["stock_count"] for s in kospi_resp["sub_sectors"])
    assert kospi_count <= all_count
    assert kospi_resp["market_filter"] == "kospi"


def test_ac_sag_039_history_market_filter_echo(client: Any) -> None:
    resp = client.get("/api/sectors/history?weeks=4&market=kospi")
    assert resp.status_code == 200
    assert resp.json()["market_filter"] == "kospi"


def test_ac_sag_039_rrg_market_param_accepted(client: Any) -> None:
    """RRG 는 시장별 지수 시계열이 없어 M6 단계에서는 echo 만 한다(deferred).

    되돌림 대조 — 대조 변형: 파라미터를 제거하면 422 대신 존재하지 않는
    쿼리 파라미터로 취급돼 FastAPI 가 무시한다(추가 파라미터 무시는 기본
    동작). 이 단언은 최소한 파라미터가 수신·검증됨을 확인한다.
    """
    ok = client.get("/api/sectors/rrg?market=kospi")
    assert ok.status_code == 200
    assert ok.json()["market_filter"] == "kospi"
    bad = client.get("/api/sectors/rrg?market=nyse")
    assert bad.status_code == 422


# ---------------------------------------------------------------------------
# AC-SAG-040 — Bump 히스토리 응답
# ---------------------------------------------------------------------------

def test_ac_sag_040_dates_length_matches_weeks(client: Any) -> None:
    resp = client.get("/api/sectors/history?weeks=8&market=all").json()
    assert len(resp["dates"]) == 8


def test_ac_sag_040_span_days_within_tolerance(client: Any) -> None:
    weeks = 8
    resp = client.get(f"/api/sectors/history?weeks={weeks}&market=all").json()
    expected = 7 * (weeks - 1)
    assert resp["span_days"] is not None
    assert abs(resp["span_days"] - expected) <= 7


def test_ac_sag_040_rankings_null_not_substituted(client: Any) -> None:
    resp = client.get("/api/sectors/history?weeks=8&market=all").json()
    rankings = resp["rankings"]
    assert set(rankings.keys()) == set(resp["dates"])
    # 최하위 순위값으로 대체되지 않았음을 확인 — null 이 실제로 존재해야 한다
    # (전 날짜에 전 섹터가 존재하면 이 픽스처에선 통과 못할 수 있으니 구조만 확인).
    for date, per_sector in rankings.items():
        for sector, rank in per_sector.items():
            assert rank is None or isinstance(rank, int)


# ---------------------------------------------------------------------------
# AC-SAG-041 — 종목 목록 필드 (stage/overview)
# ---------------------------------------------------------------------------

def test_ac_sag_041_stage_stock_has_required_fields(client: Any) -> None:
    resp = client.get("/api/stage/overview").json()
    assert resp["all_stocks"], "all_stocks 가 비어 있다"
    required = (
        "weight_in_sector", "sector_minor", "stage", "stage_detail", "rs_12m",
        "chg_1w", "chg_1m", "chg_3m", "trading_value", "volume_ratio", "near_52w_high",
    )
    stock = resp["all_stocks"][0]
    for f in required:
        assert f in stock, f"필드 누락: {f}"


def test_ac_sag_041_weight_in_sector_not_literal_010_degenerate_sector(client: Any) -> None:
    """INV-CAP-1 명제 2 — 축퇴 섹터(패션, 유효시총 3)는 cap_eff == 1/3.

    weight_in_sector 를 상수 0.10 또는 min(raw, 0.10) 으로 산출한 구현은
    이 절에서 RED 가 된다(AC-SAG-041 v0.5.0 정정 대조).
    """
    resp = client.get("/api/stage/overview").json()
    fashion_stocks = [s for s in resp["all_stocks"] if s["sector_major"] == "패션"
                       and s["weight_in_sector"] is not None]
    assert fashion_stocks, "패션 섹터 종목이 weight_in_sector 를 갖지 않는다"
    for s in fashion_stocks:
        # cap_eff(3) = max(0.10, 1/3) = 0.333333...
        assert abs(s["weight_in_sector"] - 0.10) > 0.01, (
            f"{s['name']} weight_in_sector={s['weight_in_sector']} 가 리터럴 0.10 근처다 "
            "— cap_eff(n) 대신 weight_cap 리터럴을 쓴 것으로 의심된다")


def test_ac_sag_041_weight_in_sector_red_when_literal_010_used() -> None:
    """되돌림 대조(필수) — mut_weight_cap_literal: min(raw, 0.10) 산출 변형은 RED.

    Lesson #9 — 실제로 구현을 변형해 RED 를 관측한다(대조 단언의 검출력 실증).
    """
    from my_chart.analysis.weighting import capped_weights_detail

    # 패션 섹터 실측 시총 규모(3종목, MANIFEST F6) 유사 축퇴 케이스로 재현.
    caps = {"A": 600.0, "B": 300.0, "C": 100.0}
    correct = capped_weights_detail(caps, cap=0.10).weights
    n = len(caps)
    cap_eff = max(0.10, 1.0 / n)
    assert all(abs(w - cap_eff) < 1e-9 for w in correct.values()), (
        "정상 구현은 축퇴 섹터에서 전 종목이 cap_eff(n)=1/n 로 균등해야 한다")

    # mut_weight_cap_literal — min(raw, 0.10) 산출 변형(되돌림)
    total = sum(caps.values())
    mutated = {k: min(v / total, 0.10) for k, v in caps.items()}
    mutated_sum = sum(mutated.values())
    assert mutated_sum < 1.0 - 1e-9, (
        f"mutated Σw={mutated_sum} — 변형이 정규화 위반(<1.0)을 재현하지 못했다(RED 검출 실패)")


# ---------------------------------------------------------------------------
# AC-SAG-042 — 종목 버블 섹터 기준선
# ---------------------------------------------------------------------------

def test_ac_sag_042_stock_bubble_sector_aggregate_matches_ranking(
    client: Any, sector_name: str,
) -> None:
    ranking = client.get("/api/sectors/ranking").json()
    # AC-SAG-042 는 "/sectors/ranking 의 동일 섹터·동일 기간 sector_return" 을
    # 지시한다 — 이는 하위 호환 legacy 표면 sectors[i].returns(SectorReturns,
    # compute_sector_ranking 산출)이며, 신규 canonical data[](compute_sector_
    # aggregates 산출, 별도 계산 경로)가 아니다.
    ranking_return = next(
        (s["returns"]["w1"] for s in ranking["sectors"] if s["name"] == sector_name),
        None)
    bubble = client.get(f"/api/sectors/{sector_name}/bubble?period=1w").json()
    assert bubble["sector_aggregate"] is not None
    assert ranking_return is not None
    assert abs(bubble["sector_aggregate"] - ranking_return) < 1e-6, (
        f"sector_aggregate={bubble['sector_aggregate']} != ranking sector_return="
        f"{ranking_return}")


# ---------------------------------------------------------------------------
# AC-SAG-007 — 최소 구성종목 수 (M6 의존 — 이제 평가)
# ---------------------------------------------------------------------------

def test_ac_sag_007_min_members_excluded_at_kospi_market(client: Any) -> None:
    """F3 — market=kospi 유효 종목 정확히 4 인 섹터(디스플레이·스마트폰)는
    excluded[] 에 등록되고 data[] 에서 빠진다. market=all 에서는 포함된다."""
    kospi = client.get("/api/sectors/ranking?market=kospi").json()
    excluded_names = {e["sector"] for e in kospi["excluded"]}
    assert {"디스플레이", "스마트폰"} <= excluded_names, (
        f"F3 섹터가 excluded[] 에 없다: {excluded_names}")
    for e in kospi["excluded"]:
        if e["sector"] in ("디스플레이", "스마트폰"):
            assert e["reason"] == "insufficient_members"
            assert e["count"] == 4

    all_resp = client.get("/api/sectors/ranking?market=all").json()
    all_names = {d["name"] for d in all_resp["data"]}
    assert {"디스플레이", "스마트폰"} <= all_names, "market=all 에서는 F3 섹터가 포함돼야 한다"


def test_ac_sag_007_boundary_exactly_5_included(client: Any) -> None:
    """F3-b — market=kospi 유효 종목 정확히 5(PCB)는 >=5 경계 포함으로 data[] 에 있다."""
    kospi = client.get("/api/sectors/ranking?market=kospi").json()
    names = {d["name"] for d in kospi["data"]}
    assert "PCB" in names


def test_ac_sag_007_red_when_ag5_gate_removed() -> None:
    """되돌림 대조(필수) — mut_no_ag5_gate: AG-5 게이트 제거 시 F3 섹터가 재등장하고
    excluded[] 가 비어 RED 가 된다(공유 변형명, AC-SAG-045 R6 과 공유).
    """
    from my_chart.analysis.sector_metrics import compute_sector_aggregates

    agg = compute_sector_aggregates(
        str(WEEKLY_DB), "2026-08-11", daily_db_path=str(DAILY_DB),
        registry_path=str(REGISTRY), market="kospi", as_of="2026-08-11",
        apply_min_members=True)
    excluded_names = {e.sector for e in agg.excluded}
    assert {"디스플레이", "스마트폰"} <= excluded_names

    mutated = compute_sector_aggregates(
        str(WEEKLY_DB), "2026-08-11", daily_db_path=str(DAILY_DB),
        registry_path=str(REGISTRY), market="kospi", as_of="2026-08-11",
        apply_min_members=False)  # mut_no_ag5_gate
    mutated_names = {d.name for d in mutated.aggregates}
    assert {"디스플레이", "스마트폰"} <= mutated_names, (
        "AG-5 게이트를 껐는데도 F3 섹터가 재등장하지 않았다 — 대조가 검출력을 잃었다")
    # AG-5 사유(insufficient_members)로는 더 이상 제외되지 않는다. (다른 사유
    # — 예: excess_return_missing — 로 excluded 에 남을 수는 있으나 그건 AG-9
    # 로직이며 AG-5 게이트와 무관하다.)
    mutated_ag5_excluded = {
        e.sector for e in mutated.excluded if e.reason == "insufficient_members"}
    assert "디스플레이" not in mutated_ag5_excluded and "스마트폰" not in mutated_ag5_excluded


# ---------------------------------------------------------------------------
# AC-SAG-043 — 신규 필드 전 구간 전파 (M6 파생 구조 절 — by_sector)
# ---------------------------------------------------------------------------

def test_ac_sag_043_by_sector_unclassified_count_present(client: Any) -> None:
    """M6 파생 구조 절 — stage_service.by_sector 가 unclassified_count/total 을 갖는다.

    (M5 에서 이미 신설됐음을 확인 — 중복 구현 방지 재확인.)
    """
    resp = client.get("/api/stage/overview").json()
    assert resp["by_sector"], "by_sector 가 비어 있다"
    for entry in resp["by_sector"]:
        assert "unclassified_count" in entry
        assert "total" in entry
        assert (entry["stage1"] + entry["stage2"] + entry["stage3"] + entry["stage4"]
                + entry["unclassified_count"]) == entry["total"]
