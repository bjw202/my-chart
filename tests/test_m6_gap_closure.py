# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M6 Gap Closure — G16/G20/G21/G22/G23/G25.

M6 완료 후 progress.md §E.2 M6 Gap 목록에 남은 6건을 닫는 회귀 테스트.
각 테스트는 수정 전 상태(dead code / echo 전용 / weekly 근사 / period 미반영 /
필드 누락 / 최상위 필드 부재)를 재현했을 때 RED 가 되도록 작성됐다 — 즉 이
테스트들이 수정 전에는 실패했음을 보장한다(§D "각 gap을 닫는 regression test").
"""
from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Iterator

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = FIXTURE_DIR / "weekly.db"
DAILY_DB = FIXTURE_DIR / "daily.db"
REGISTRY = FIXTURE_DIR / "registry.xlsx"

AS_OF = "2026-08-11"


@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    from unittest.mock import patch

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
# G16 — compute_trading_value_by_period dead code + SectorAggregate.trading_value
# ---------------------------------------------------------------------------

def test_g16_compute_trading_value_by_period_has_call_site() -> None:
    """수정 전 실측: 정의 1건 / 호출 0건(`grep -rn compute_trading_value_by_period
    my_chart/ backend/` → `sector_metrics.py:288`의 `def` 1건만). 수정 후에는
    최소 1개의 실제 호출부(정의 라인 제외)가 존재해야 한다.
    """
    out = subprocess.run(
        ["grep", "-rn", "--include=*.py", "compute_trading_value_by_period",
         "my_chart/", "backend/"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    ).stdout
    call_sites = [
        line for line in out.splitlines()
        if "def compute_trading_value_by_period" not in line
    ]
    assert call_sites, f"호출부가 없다 — 여전히 dead code(G16 미해소): {out!r}"


def test_g16_data_trading_value_field_present_and_populated(client: Any) -> None:
    resp = client.get("/api/sectors/ranking").json()
    assert resp["data"], "data[] 가 비어 있다"
    for item in resp["data"]:
        assert "trading_value" in item, "SectorAggregate.trading_value 필드 누락(G16)"
        assert set(item["trading_value"]) == {"1w", "1m", "3m"}
    populated = [
        item["trading_value"]["1m"]["value"] for item in resp["data"]
        if item["trading_value"]["1m"]["value"] is not None
    ]
    assert populated, "전 섹터 trading_value 가 결측 — daily VolumeWon 배선이 안 됐다(G16)"
    assert any(v > 0 for v in populated)


# ---------------------------------------------------------------------------
# G20 — RRG / 종목 버블 market 파라미터 실배선(echo 탈피)
# ---------------------------------------------------------------------------

def test_g20_rrg_market_filter_recomputes_rs_ratio(client: Any) -> None:
    """수정 전에는 market=kospi 응답의 `rs_ratio` 가 market=all 과 **바이트 동일**
    했다(echo 전용, 실 데이터 재계산 없음). 수정 후에는 공통 섹터의 rs_ratio 가
    최소 1개 이상 달라야 한다.
    """
    all_resp = client.get("/api/sectors/rrg").json()
    kospi_resp = client.get("/api/sectors/rrg?market=kospi").json()
    all_map = {s["name"]: s["rs_ratio"] for s in all_resp["sectors"]}
    kospi_map = {s["name"]: s["rs_ratio"] for s in kospi_resp["sectors"]}
    common = set(all_map) & set(kospi_map)
    assert common, "market=all/kospi 공통 섹터가 없다 — 비교 불가"
    diverged = [n for n in common if abs(all_map[n] - kospi_map[n]) > 1e-9]
    assert diverged, (
        "market=kospi 의 rs_ratio 가 market=all 과 전부 동일 — "
        "echo 전용으로 회귀했다(G20 재발)")


def test_g20_stock_bubble_market_filter_reduces_universe(
    client: Any, sector_name: str,
) -> None:
    """수정 전에는 `/sectors/{name}/bubble` 의 `stocks[]` 가 market 무관하게 항상
    동일했다(종목 단위 시장 필터 미적용). 수정 후에는 market=kospi 가 market=all
    보다 종목 수가 적어야 한다(혼합 시장 섹터 전제).
    """
    all_resp = client.get(f"/api/sectors/{sector_name}/bubble").json()
    kospi_resp = client.get(f"/api/sectors/{sector_name}/bubble?market=kospi").json()
    assert len(kospi_resp["stocks"]) < len(all_resp["stocks"]), (
        f"market=kospi 종목 수({len(kospi_resp['stocks'])})가 market=all"
        f"({len(all_resp['stocks'])}) 과 같거나 많다 — market 필터가 종목 유니버스에"
        " 배선되지 않았다(G20 재발)")


# ---------------------------------------------------------------------------
# G21 — stage/overview trading_value 정규 원천(daily VolumeWon) 전환
# ---------------------------------------------------------------------------

def test_g21_stage_overview_trading_value_matches_canonical_source(client: Any) -> None:
    """수정 전에는 `trading_value` 가 weekly `Close×Volume` 근사였다. 수정 후에는
    M5 가 확정한 정규 원천(`compute_trading_value_by_period`, daily VolumeWon,
    1W 창)의 값과 정확히 일치해야 한다.
    """
    from my_chart.analysis.sector_metrics import compute_trading_value_by_period
    from my_chart.analysis.weekly_grid import anchor, compute_weekly_grid

    resp = client.get("/api/stage/overview").json()
    assert resp["all_stocks"], "all_stocks 가 비어 있다"

    grid = compute_weekly_grid(str(WEEKLY_DB), AS_OF)
    anchor_bar = anchor(grid, AS_OF, 7)
    assert anchor_bar is not None
    canonical = compute_trading_value_by_period(
        str(DAILY_DB), {"1w": anchor_bar.date}, AS_OF)["1w"]

    checked = 0
    for stock in resp["all_stocks"]:
        expected = canonical.get(stock["name"])
        if expected is None:
            continue
        assert stock["trading_value"] == pytest.approx(expected), (
            f"{stock['name']}: trading_value={stock['trading_value']} != "
            f"canonical(daily VolumeWon)={expected} — weekly 근사로 되돌아갔다(G21 재발)")
        checked += 1
    assert checked > 0, "canonical 원천과 대조 가능한 종목이 하나도 없다"


# ---------------------------------------------------------------------------
# G22 — /sectors/ranking?period=... 가 data[].rank 재배정에 실제로 영향을 준다
# ---------------------------------------------------------------------------

def test_g22_period_changes_data_rank(client: Any) -> None:
    """AC-SAG-021 — 수정 전에는 `period` 를 수신·검증만 하고 `compute_sector_
    ranking` 은 고정 composite 만 산출해 `data[].rank` 가 `period` 와 무관하게
    동일했다. 수정 후에는 period=1w 와 period=3m 의 rank 배정이 달라야 한다.
    """
    r1w = client.get("/api/sectors/ranking?period=1w").json()
    r3m = client.get("/api/sectors/ranking?period=3m").json()
    ranks_1w = {d["name"]: d["rank"] for d in r1w["data"]}
    ranks_3m = {d["name"]: d["rank"] for d in r3m["data"]}
    assert ranks_1w != ranks_3m, (
        "period=1w 와 period=3m 의 data[].rank 배정이 동일하다 — "
        "period 파라미터가 rank 재배정에 반영되지 않는다(G22 재발, AC-SAG-021 위반)")


def test_g22_composite_score_still_present_alongside_rank(client: Any) -> None:
    """AC-SAG-022 — period 기준 순위로 바뀌어도 composite_score 는 여전히
    rank 와 함께 존재해야 한다(회귀 방지)."""
    resp = client.get("/api/sectors/ranking?period=3m").json()
    for item in resp["data"]:
        if item["rank"] is not None:
            assert item["composite_score"]["value"] is not None


# ---------------------------------------------------------------------------
# G23 — StockBubbleItem 필드 확장(AC-SAG-041)
# ---------------------------------------------------------------------------

def test_g23_stock_bubble_item_has_ac_sag_041_fields(
    client: Any, sector_name: str,
) -> None:
    """수정 전에는 `StockBubbleItem` 이 `weight_in_sector`/`chg_1w`/`chg_3m`/
    `near_52w_high` 를 갖지 않았다(`price_change` 단일 필드만 존재).
    """
    resp = client.get(f"/api/sectors/{sector_name}/bubble").json()
    assert resp["stocks"], "stocks[] 가 비어 있다"
    required = ("weight_in_sector", "chg_1w", "chg_3m", "near_52w_high")
    for f in required:
        assert f in resp["stocks"][0], f"StockBubbleItem 필드 누락(G23): {f}"


def test_g23_weight_in_sector_sums_close_to_one(client: Any, sector_name: str) -> None:
    """`weight_in_sector` 가 섹터 내 정규 가중치라면 합이 1.0 근방이어야 한다
    (시총 결측 종목 제외 여지가 있으므로 상한만 확인 — 엄격 등식은 AC-SAG-041
    함수 수준 테스트가 전담한다)."""
    resp = client.get(f"/api/sectors/{sector_name}/bubble").json()
    weights = [s["weight_in_sector"] for s in resp["stocks"] if s["weight_in_sector"] is not None]
    assert weights, "weight_in_sector 가 전부 결측이다"
    assert sum(weights) <= 1.0 + 1e-6


# ---------------------------------------------------------------------------
# G25 — baseline_date / trading_value_window_days 최상위 노출(AC-SAG-023/046)
# ---------------------------------------------------------------------------

def test_g25_baseline_date_exposed_at_top_level(client: Any) -> None:
    """수정 전에는 `rank_change` 산출에 내부적으로 쓰이는 `baseline_date` 가
    응답 최상위에 노출되지 않았다."""
    resp = client.get("/api/sectors/ranking").json()
    assert resp.get("baseline_date") is not None, "baseline_date 최상위 노출 누락(G25)"
    days = (date.fromisoformat(resp["as_of_date"])
            - date.fromisoformat(resp["baseline_date"])).days
    assert days >= 28


def test_g25_trading_value_window_days_matches_return_window_days_per_period(
    client: Any,
) -> None:
    """AC-SAG-046 — `trading_value_window_days == return_window_days[period]`
    를 세 기간 각각에서 확인한다(O-A4 — 같은 anchor 창 공유)."""
    for period in ("1w", "1m", "3m"):
        resp = client.get(f"/api/sectors/ranking?period={period}").json()
        assert "trading_value_window_days" in resp, (
            "trading_value_window_days 최상위 노출 누락(G25)")
        assert resp["trading_value_window_days"] == resp["return_window_days"], (
            f"period={period}: trading_value_window_days"
            f"={resp['trading_value_window_days']} != return_window_days"
            f"={resp['return_window_days']}")
