# coding: utf-8
"""RED: `/api/sectors/bubble` 의 `market` 파라미터 계약이 형제 엔드포인트와 다르다.

`/sectors/bubble` 만 `pattern="^(KOSPI|KOSDAQ)$"` (대문자 전용, default=None)을 쓰고,
나머지 6개(`/sectors/ranking`, `/sectors/rrg`, `/sectors/history`, `/sectors/{name}/detail`,
`/sectors/{name}/bubble`, `/stage/overview`)는 `^(all|kospi|kosdaq)$` (소문자, default="all")
를 쓴다. 프론트엔드는 M2 에서 소문자로 표준화했으므로(`AnalysisParamsContext.tsx`
`type Market = 'all' | 'kospi' | 'kosdaq'`), 버블 탭에서 KOSPI/KOSDAQ 을 고르면 422 가 나고
차트가 렌더되지 않는다.

200 만으로는 부족하다 — 패턴만 고치고 값이 필터로 이어지지 않으면 전 섹터를 그대로
돌려주면서 200 이 되는 거짓 GREEN 이 된다. 그래서 `kospi`/`kosdaq` 가 `all` 대비 실제로
모집단을 좁히는지, 그리고 두 시장의 합집합이 `all` 을 넘지 않는지까지 확인한다.
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

# 형제 엔드포인트가 공유하는 market 계약
SIBLING_MARKET_VALUES = ("all", "kospi", "kosdaq")


@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    """집계 프로즌 픽스처에 고정된 TestClient (test_response_contract.py 와 동일 관용)."""
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


def _bubble(client: Any, market: str | None = None) -> Any:
    params: dict[str, str] = {"period": "1m"}
    if market is not None:
        params["market"] = market
    return client.get("/api/sectors/bubble", params=params)


def _sector_names(client: Any, market: str | None) -> set[str]:
    resp = _bubble(client, market)
    assert resp.status_code == 200, f"market={market!r} → {resp.status_code}"
    return {s["name"] for s in resp.json()["sectors"]}


def _trading_value(client: Any, market: str | None) -> dict[str, float]:
    """섹터별 거래대금 — 시장 필터가 유니버스에 실제로 걸렸는지 재는 척도."""
    resp = _bubble(client, market)
    assert resp.status_code == 200, f"market={market!r} → {resp.status_code}"
    return {s["name"]: s["trading_value"] for s in resp.json()["sectors"]}


@pytest.mark.parametrize("market", SIBLING_MARKET_VALUES)
def test_bubble_accepts_sibling_market_values(client: Any, market: str) -> None:
    """형제 엔드포인트와 같은 소문자 3값을 그대로 받는다."""
    resp = _bubble(client, market)
    assert resp.status_code == 200, (
        f"market={market!r} 가 거부됐다 ({resp.status_code}): {resp.text[:200]}"
    )


def test_bubble_market_matches_sibling_endpoint_contract(client: Any) -> None:
    """같은 market 값 집합을 형제 엔드포인트(/sectors/rrg)와 동일하게 수용한다."""
    for market in SIBLING_MARKET_VALUES:
        bubble = _bubble(client, market).status_code
        rrg = client.get("/api/sectors/rrg", params={"market": market}).status_code
        assert bubble == rrg, (
            f"market={market!r}: /sectors/bubble → {bubble}, /sectors/rrg → {rrg} (계약 불일치)"
        )


def test_bubble_market_filter_actually_narrows_universe(client: Any) -> None:
    """200 을 돌려주기만 하는 게 아니라 모집단을 실제로 좁힌다(거짓 GREEN 방지).

    섹터명 집합은 판별력이 없다 — 이 픽스처에서는 18개 섹터 모두 양 시장에 종목이
    있어 all/kospi/kosdaq 의 섹터명 집합이 동일하다. 그래서 집계값(거래대금)으로 잰다.
    """
    all_tv = _trading_value(client, "all")
    kospi_tv = _trading_value(client, "kospi")

    assert all_tv, "all 응답이 비어 있다 — 픽스처가 잘못됐다"
    assert kospi_tv, "kospi 응답이 비어 있다 — 필터가 전부 걸러냈다"
    assert set(kospi_tv) <= set(all_tv)

    # KOSPI 로 좁히면 KOSDAQ 종목이 빠지므로 섹터 거래대금은 반드시 줄어든다.
    narrowed = [n for n, v in kospi_tv.items() if v < all_tv[n]]
    assert narrowed, (
        "어떤 섹터도 거래대금이 줄지 않았다 — market 값이 유니버스 필터로 이어지지 않는다"
    )
    assert all(kospi_tv[n] <= all_tv[n] for n in kospi_tv), (
        "일부 섹터에서 kospi 거래대금이 all 을 넘는다 — 필터가 잘못 걸렸다"
    )


def test_bubble_market_partition_is_exact(client: Any) -> None:
    """kospi + kosdaq == all (섹터별 거래대금) — 필터가 메아리가 아니라 실제 분할이다.

    거래대금은 구성 종목 합이므로, 시장 필터가 유니버스에 정확히 걸렸다면 두 시장의
    합이 전체와 일치해야 한다. 값이 무시되거나 잘못 걸리면 이 등식이 즉시 깨진다.
    """
    all_tv = _trading_value(client, "all")
    kospi_tv = _trading_value(client, "kospi")
    kosdaq_tv = _trading_value(client, "kosdaq")

    # 공허한 통과 방지 — all 이 비면 아래 루프가 0회 돌고 무조건 통과한다.
    assert all_tv, "all 응답이 비어 있다 — 등식을 검사할 대상이 없다"

    for name, total in all_tv.items():
        part = kospi_tv.get(name, 0.0) + kosdaq_tv.get(name, 0.0)
        assert part == pytest.approx(total, rel=1e-9), (
            f"{name}: kospi({kospi_tv.get(name)}) + kosdaq({kosdaq_tv.get(name)}) "
            f"!= all({total})"
        )


def test_bubble_market_omitted_still_means_whole_universe(client: Any) -> None:
    """market 을 아예 넘기지 않은 경우와 all 의 모집단이 같다(기존 동작 보존)."""
    assert _sector_names(client, None) == _sector_names(client, "all")
