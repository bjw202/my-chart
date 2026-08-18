# coding: utf-8
"""SPEC-SECTOR-METRIC-UNIFY-001 M4 — E-6 빈 date 엣지: 가드가 빈 응답을 낸다.

``_get_latest_valid_date`` 가 빈 문자열을 반환하는 상황(weekly DB 미구축/빈 테이블)에서
``/api/sectors/bubble`` 는 503 이 아니라 **200 + ``sectors == []``** 를 반환해야 한다.

분기 A(status 관측량) — get_stock_bubble 관행과 같은 빈 date 가드가 라우터의
포괄 ``except``→503 경로에 빠지지 않음을 HTTP status 로 관측한다. 가드가 없으면
``date.fromisoformat('')`` ValueError 가 봉투 계산으로 흘러 503 이 된다.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = FIXTURE_DIR / "weekly.db"
DAILY_DB = FIXTURE_DIR / "daily.db"
REGISTRY = FIXTURE_DIR / "registry.xlsx"


def _make_client() -> Any:
    """집계 프로즌 픽스처에 고정된 TestClient + 빈 date 패치 (test_bubble_ranking_parity.py 관용)."""
    from fastapi.testclient import TestClient

    from backend.main import app

    # UN-1 — registry 모듈 캐시 초기화(픽스처 xlsx 로 고정).
    # 빈 date 가드가 통과 계산을 원천 차단하므로 계산 경로는 실행되지 않는다.
    with (
        patch("backend.routers.sectors.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("backend.routers.sectors.DAILY_DB_PATH", str(DAILY_DB)),
        patch("backend.routers.stage.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("my_chart.registry.SECTORMAP_PATH", str(REGISTRY)),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
        patch("backend.services.sector_advanced_service._get_latest_valid_date",
              return_value=""),
    ):
        yield TestClient(app)


def test_bubble_empty_date_returns_200_empty_sectors() -> None:
    """_get_latest_valid_date → "" 이면 200 + sectors=[] (+ date=""·as_of_date=None)."""
    client_gen = _make_client()
    client = next(client_gen)
    try:
        resp = client.get("/api/sectors/bubble",
                          params={"period": "1w", "market": "all"})
        assert resp.status_code == 200, (
            f"빈 date 가 503 으로 샌다 — 가드 미작동: {resp.status_code} {resp.text[:200]}"
        )
        body = resp.json()
        assert body["sectors"] == [], f"sectors 가 비어 있지 않다: {body['sectors'][:3]}..."
        assert body["date"] == "", f"date={body['date']!r} != ''"
        assert body["as_of_date"] is None, f"as_of_date={body['as_of_date']!r} != None"
    finally:
        client_gen.close()
