# coding: utf-8
"""SPEC-RS-REBALANCE-001 M4 — 종목 응답 `rs_1m` (AC-RSR-009, REQ-RSR-012·014).

양변 출처: HTTP 응답 값(`/api/stage/overview`, `/api/sectors/{name}/bubble`) vs 고정 픽스처
주간 DB에서 독립 SQL로 읽은 같은 주차 `RS_1M_Rating`.

고정 픽스처(`aggregation-2026-08-11`)는 운영 스키마 `relative_strength`(6컬럼)를 갖고,
최신 주차 2026-08-11에 RS 행 291개 중 `RS_1M_Rating == RS_12M_Rating`인 행이 1개,
RS 행이 없는 가격 행이 32개다 — 따라서 "rs_1m에 RS_12M_Rating 연결" 되돌림과
"결측을 0으로" 되돌림을 모두 구분할 수 있다. 픽스처는 읽기 전용으로만 연다.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = FIXTURE_DIR / "weekly.db"
DAILY_DB = FIXTURE_DIR / "daily.db"
REGISTRY = FIXTURE_DIR / "registry.xlsx"


def _ro(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)


def _rs_on(date: str) -> dict[str, tuple[float | None, float | None]]:
    """독립 SQL — Name → (RS_12M_Rating, RS_1M_Rating)."""
    conn = _ro(WEEKLY_DB)
    try:
        rows = conn.execute(
            "SELECT Name, RS_12M_Rating, RS_1M_Rating FROM relative_strength WHERE Date = ?",
            (date,),
        ).fetchall()
    finally:
        conn.close()
    return {r[0]: (r[1], r[2]) for r in rows}


@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    from fastapi.testclient import TestClient

    from backend.main import app

    with (
        patch("backend.routers.sectors.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("backend.routers.sectors.DAILY_DB_PATH", str(DAILY_DB)),
        patch("backend.routers.stage.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("backend.routers.stage.DAILY_DB_PATH", str(DAILY_DB)),
        # 종목 버블의 stock_meta 폴백이 라이브 일봉 DB를 열지 않도록 픽스처로 고정
        patch("my_chart.analysis.sector_advanced.DEFAULT_DB_DAILY", str(DAILY_DB.with_suffix(""))),
        patch("my_chart.registry.SECTORMAP_PATH", str(REGISTRY)),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    ):
        yield TestClient(app)


def _assert_rs_fields(items: list[dict], rs: dict, label: str) -> tuple[int, int]:
    """각 항목의 rs_1m이 같은 주차 RS_1M_Rating(없으면 null)과 같은지 단언.

    Returns: (rs_1m ≠ rs_12m인 RS 보유 항목 수, RS 행 없는 항목 수)
    """
    differing = 0
    missing = 0
    for it in items:
        assert "rs_1m" in it, f"{label}: {it['name']} 항목에 rs_1m 필드가 없다"
        if it["name"] not in rs:
            missing += 1
            assert it["rs_1m"] is None, f"{label}: RS 행 없는 {it['name']}의 rs_1m={it['rs_1m']!r}"
            continue
        rs12, rs1 = rs[it["name"]]
        assert it["rs_1m"] == pytest.approx(round(rs1, 2), abs=0.005), (
            f"{label}: {it['name']} rs_1m={it['rs_1m']!r} != RS_1M_Rating={rs1!r}")
        # rs_12m은 이름·의미 불변(REQ-RSR-014)
        assert it["rs_12m"] == pytest.approx(round(rs12 or 0.0, 2), abs=0.005)
        if abs(rs1 - (rs12 or 0.0)) > 0.01:
            differing += 1
    return differing, missing


def test_ac_rsr_009_stage_overview_rs_1m(client: Any) -> None:
    resp = client.get("/api/stage/overview")
    assert resp.status_code == 200, resp.text[:400]
    body = resp.json()
    rs = _rs_on(body["as_of_date"])
    assert rs, "전제: 픽스처 최신 주차에 RS 행이 있다"

    items = body["all_stocks"]
    differing, missing = _assert_rs_fields(items, rs, "/stage/overview all_stocks")
    # 대조력: 12M을 잘못 연결하면 잡히는 항목, 결측 null 경로가 실제로 실행된 항목이 있어야 한다
    assert differing >= 100, f"rs_1m≠rs_12m 항목이 {differing}개뿐 — 대조력 부족"
    assert missing >= 1, "RS 행 없는 종목이 all_stocks에 없다 — null 경로 미검증"

    cand = body["stage2_candidates"]
    assert cand, "전제: Stage 2 후보가 1개 이상"
    _assert_rs_fields(cand, rs, "/stage/overview stage2_candidates")


def test_ac_rsr_009_stock_bubble_rs_1m(client: Any) -> None:
    # RS 행 없는 종목이 들어 있는 섹터를 고른다(null 경로를 버블에서도 실행)
    conn = _ro(DAILY_DB)
    try:
        meta = conn.execute("SELECT name, sector_major FROM stock_meta").fetchall()
    finally:
        conn.close()
    ranking = client.get("/api/sectors/ranking").json()
    rs_latest = _rs_on(ranking["as_of_date"])
    sectors_with_missing = sorted({s for n, s in meta if n not in rs_latest and s})
    assert sectors_with_missing, "전제: RS 행 없는 종목을 가진 섹터가 있다"

    total_diff = 0
    total_missing = 0
    for sector in sectors_with_missing:
        resp = client.get(f"/api/sectors/{sector}/bubble")
        assert resp.status_code == 200, resp.text[:400]
        body = resp.json()
        rs = _rs_on(body["date"])
        d, m = _assert_rs_fields(body["stocks"], rs, f"/sectors/{sector}/bubble")
        total_diff += d
        total_missing += m
    assert total_diff >= 10, f"rs_1m≠rs_12m 버블 항목이 {total_diff}개뿐 — 대조력 부족"
    assert total_missing >= 1, "버블 응답에서 RS 행 없는 종목을 만나지 못했다 — null 경로 미검증"
