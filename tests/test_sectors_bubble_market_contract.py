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
    """시장 파티션 등식 — AG-5 시장별 멤버십 적용 후의 의미론 (M4, AC-SMU-015).

    M4(`/api/sectors/bubble` → compute_sector_aggregates 투영) 이전에는 세 시장
    응답의 섹터 집합이 동일해 "kospi + kosdaq == all" 엄격 등식이 성립했다. M4는
    버블에 봉투(/api/sectors/ranking)와 동일한 AG-5 최소 멤버 기준을 **시장별
    멤버십 기준**으로 적용한다 — 단일 시장 유니버스에서 미달인 섹터(이 픽스처에서
    kospi 의 디스플레이·스마트폰·패션, kosdaq 의 패션)는 그 시장 응답에서 제외된다.
    등식의 전제("모든 섹터가 세 응답에 공통 존재")는 M4 로 제거되었으므로 계약을
    AG-5 의미론으로 재기술한다 (완화가 아니다):
      (a) 양 시장 응답에 모두 존재하는 섹터 — 기존 엄격 등식 그대로
      (b) 한쪽에만 존재하는 섹터(AG-5 경계) — 존재 쪽 값이 all 보다 엄격히 작다
          (진부분집합 증명)
      (c) (a) 집합이 비지 않는다 (공허한 통과 방지)
    """
    all_tv = _trading_value(client, "all")
    kospi_tv = _trading_value(client, "kospi")
    kosdaq_tv = _trading_value(client, "kosdaq")

    assert all_tv, "all 응답이 비어 있다 — 등식을 검사할 대상이 없다"

    both = set(kospi_tv) & set(kosdaq_tv)  # (c)
    assert both, "양쪽 모두에 존재하는 섹터가 0개 — 파티션 등식 검사 대상 없음"

    for name in both:  # (a)
        part = kospi_tv[name] + kosdaq_tv[name]
        assert part == pytest.approx(all_tv[name], rel=1e-9), (
            f"{name}: kospi({kospi_tv[name]}) + kosdaq({kosdaq_tv[name]}) "
            f"!= all({all_tv[name]})"
        )

    for name, total in all_tv.items():  # (b)
        if name in both:
            continue
        for side_name, side in (("kospi", kospi_tv), ("kosdaq", kosdaq_tv)):
            if name in side:
                assert side[name] < total, (
                    f"{name}: {side_name}에만 존재(AG-5 경계)한데 값({side[name]})이 "
                    f"all({total}) 이상 — 진부분집합 위반"
                )


def test_bubble_market_omitted_still_means_whole_universe(client: Any) -> None:
    """market 을 아예 넘기지 않은 경우와 all 의 모집단이 같다(기존 동작 보존)."""
    assert _sector_names(client, None) == _sector_names(client, "all")
