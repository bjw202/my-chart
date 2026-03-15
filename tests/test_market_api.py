"""Specification tests for new Market/Stage/Sector API endpoints.

Tests are written first (RED phase) to define expected behavior per SPEC AC10-AC12.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Fixtures: test DB + FastAPI test client
# ---------------------------------------------------------------------------

_WEEKLY_DDL = """
CREATE TABLE IF NOT EXISTS stock_prices (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    Open REAL, High REAL, Low REAL, Close REAL,
    Volume REAL, VolumeSMA10 REAL,
    CHG_1W REAL, CHG_1M REAL, CHG_2M REAL, CHG_3M REAL,
    CHG_6M REAL, CHG_9M REAL, CHG_12M REAL,
    SMA10 REAL, SMA20 REAL, SMA40 REAL,
    SMA40_Trend_1M REAL, SMA40_Trend_2M REAL,
    SMA40_Trend_3M REAL, SMA40_Trend_4M REAL,
    MAX10 REAL, MAX52 REAL, min52 REAL, Close_52min REAL,
    RS_1M REAL, RS_2M REAL, RS_3M REAL,
    RS_6M REAL, RS_9M REAL, RS_12M REAL, RS_Line REAL,
    PRIMARY KEY (Name, Date)
)
"""

_RS_DDL = """
CREATE TABLE IF NOT EXISTS relative_strength (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    RS_12M_Rating REAL,
    PRIMARY KEY (Name, Date)
)
"""


def _make_weekly_row(
    name: str,
    date: str,
    close: float = 100.0,
    sma10: float = 90.0,
    sma40: float = 85.0,
    chg_1w: float = 0.02,
    chg_1m: float = 0.05,
    chg_3m: float = 0.10,
    volume: float = 1_000_000.0,
    volume_sma10: float = 800_000.0,
    sma40_trend_4m: float = 84.0,
    max52: float = 110.0,
    min52: float = 70.0,
) -> tuple:
    return (
        name, date,
        close * 0.99, close * 1.01, close * 0.98, close,
        volume, volume_sma10,
        chg_1w, chg_1m, 0.08, chg_3m, 0.20, 0.25, 0.30,
        sma10, 92.0, sma40,
        sma40_trend_4m, sma40 * 0.98, sma40 * 0.97, sma40 * 0.96,
        close * 1.05, max52, min52, close - min52,
        50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 1.1,
    )


@pytest.fixture
def api_weekly_db(tmp_path: Path, mock_sectormap) -> str:  # noqa: F811
    """Weekly DB with enough data for API endpoint tests."""
    db_path = str(tmp_path / "api_weekly.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_WEEKLY_DDL)
    conn.execute(_RS_DDL)

    test_date = "2024-01-05"
    prev_4w = "2023-12-08"

    # KOSPI index data (required for market overview)
    for dt, close, sma10, sma40 in [
        (test_date, 2500.0, 2400.0, 2300.0),
        (prev_4w, 2400.0, 2350.0, 2280.0),
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_weekly_row("KOSPI", dt, close=close, sma10=sma10, sma40=sma40, chg_1w=0.015),
        )

    # Individual stocks
    for i, (name, sector, rs, chg_1w, chg_1m, close) in enumerate([
        ("삼성전자", "전기전자", 85.0, 0.03, 0.08, 100.0),
        ("SK하이닉스", "전기전자", 72.0, 0.025, 0.07, 80.0),
        ("POSCO홀딩스", "철강금속", 45.0, -0.01, -0.02, 60.0),
    ]):
        for dt in [test_date, prev_4w]:
            conn.execute(
                "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                _make_weekly_row(
                    name, dt,
                    close=close, sma10=close * 0.9, sma40=close * 0.85,
                    chg_1w=chg_1w, chg_1m=chg_1m, chg_3m=0.10,
                    volume=2_000_000.0, volume_sma10=800_000.0,
                    sma40_trend_4m=close * 0.84,
                    max52=close * 1.1, min52=close * 0.7,
                ),
            )
            conn.execute(
                "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
                (name, dt, rs),
            )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def test_client(api_weekly_db: str) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with mocked DB paths pointing to test data."""
    from backend.main import app

    # Patch the DB path constants used by the new routers
    with patch("backend.routers.market.WEEKLY_DB_PATH", api_weekly_db), \
         patch("backend.routers.stage.WEEKLY_DB_PATH", api_weekly_db), \
         patch("backend.routers.sectors.WEEKLY_DB_PATH", api_weekly_db):
        with TestClient(app) as client:
            yield client


# ---------------------------------------------------------------------------
# Tests: GET /api/market/overview (AC10)
# ---------------------------------------------------------------------------


class TestMarketOverviewEndpoint:
    """Tests for GET /api/market/overview."""

    def test_endpoint_returns_200(self, test_client: TestClient) -> None:
        """AC10: GET /api/market/overview returns valid JSON response."""
        response = test_client.get("/api/market/overview")
        assert response.status_code == 200

    def test_response_has_kospi_section(self, test_client: TestClient) -> None:
        """Response contains KOSPI data section."""
        response = test_client.get("/api/market/overview")
        data = response.json()
        assert "kospi" in data
        kospi = data["kospi"]
        assert "close" in kospi
        assert "chg_1w" in kospi
        assert "sma50" in kospi
        assert "sma200" in kospi

    def test_response_has_breadth_section(self, test_client: TestClient) -> None:
        """Response contains breadth indicators section."""
        response = test_client.get("/api/market/overview")
        data = response.json()
        assert "breadth" in data
        assert "kospi" in data["breadth"]
        breadth = data["breadth"]["kospi"]
        assert "pct_above_sma50" in breadth
        assert "pct_above_sma200" in breadth
        assert "nh_nl_ratio" in breadth
        assert "breadth_score" in breadth

    def test_response_has_cycle_section(self, test_client: TestClient) -> None:
        """Response contains market cycle section."""
        response = test_client.get("/api/market/overview")
        data = response.json()
        assert "cycle" in data
        cycle = data["cycle"]
        assert "phase" in cycle
        assert cycle["phase"] in {"bull", "sideways", "bear"}
        assert "choppy" in cycle
        assert "confidence" in cycle

    def test_response_has_breadth_history(self, test_client: TestClient) -> None:
        """Response contains breadth_history list."""
        response = test_client.get("/api/market/overview")
        data = response.json()
        assert "breadth_history" in data
        assert isinstance(data["breadth_history"], list)

    def test_response_time_under_500ms(self, api_weekly_db: str) -> None:
        """AC11: API response time < 500ms for full market overview."""
        from backend.main import app

        with patch("backend.routers.market.WEEKLY_DB_PATH", api_weekly_db), \
             patch("backend.routers.stage.WEEKLY_DB_PATH", api_weekly_db), \
             patch("backend.routers.sectors.WEEKLY_DB_PATH", api_weekly_db):
            with TestClient(app) as client:
                start = time.time()
                response = client.get("/api/market/overview")
                elapsed = time.time() - start
                assert response.status_code == 200
                assert elapsed < 0.5, f"Response took {elapsed:.3f}s (> 500ms)"

    def test_pct_above_sma50_is_valid_percentage(self, test_client: TestClient) -> None:
        """pct_above_sma50 should be a valid percentage (0-100)."""
        response = test_client.get("/api/market/overview")
        data = response.json()
        val = data["breadth"]["kospi"]["pct_above_sma50"]
        assert 0.0 <= val <= 100.0


# ---------------------------------------------------------------------------
# Tests: GET /api/stage/overview (AC10)
# ---------------------------------------------------------------------------


class TestStageOverviewEndpoint:
    """Tests for GET /api/stage/overview."""

    def test_endpoint_returns_200(self, test_client: TestClient) -> None:
        """GET /api/stage/overview returns valid JSON response."""
        response = test_client.get("/api/stage/overview")
        assert response.status_code == 200

    def test_response_has_distribution(self, test_client: TestClient) -> None:
        """Response contains stage distribution."""
        response = test_client.get("/api/stage/overview")
        data = response.json()
        assert "distribution" in data
        dist = data["distribution"]
        assert "stage1" in dist
        assert "stage2" in dist
        assert "stage3" in dist
        assert "stage4" in dist
        assert "total" in dist

    def test_distribution_sums_correctly(self, test_client: TestClient) -> None:
        """Stage distribution counts sum to total."""
        response = test_client.get("/api/stage/overview")
        data = response.json()
        dist = data["distribution"]
        computed_total = dist["stage1"] + dist["stage2"] + dist["stage3"] + dist["stage4"]
        assert computed_total == dist["total"]

    def test_response_has_by_sector(self, test_client: TestClient) -> None:
        """Response contains by_sector breakdown."""
        response = test_client.get("/api/stage/overview")
        data = response.json()
        assert "by_sector" in data
        assert isinstance(data["by_sector"], list)

    def test_response_has_stage2_candidates(self, test_client: TestClient) -> None:
        """Response contains stage2_candidates list."""
        response = test_client.get("/api/stage/overview")
        data = response.json()
        assert "stage2_candidates" in data
        assert isinstance(data["stage2_candidates"], list)

    def test_stage2_candidates_have_required_fields(self, test_client: TestClient) -> None:
        """Each stage2_candidate has SPEC-required fields."""
        response = test_client.get("/api/stage/overview")
        data = response.json()
        candidates = data["stage2_candidates"]
        if candidates:
            c = candidates[0]
            assert "name" in c
            assert "stage" in c
            assert "rs_12m" in c


# ---------------------------------------------------------------------------
# Tests: GET /api/sectors/ranking (AC10)
# ---------------------------------------------------------------------------


class TestSectorRankingEndpoint:
    """Tests for GET /api/sectors/ranking."""

    def test_endpoint_returns_200(self, test_client: TestClient) -> None:
        """GET /api/sectors/ranking returns valid JSON response."""
        response = test_client.get("/api/sectors/ranking")
        assert response.status_code == 200

    def test_response_has_sectors_list(self, test_client: TestClient) -> None:
        """Response contains sectors list."""
        response = test_client.get("/api/sectors/ranking")
        data = response.json()
        assert "sectors" in data
        assert isinstance(data["sectors"], list)

    def test_response_has_date(self, test_client: TestClient) -> None:
        """Response contains date field."""
        response = test_client.get("/api/sectors/ranking")
        data = response.json()
        assert "date" in data

    def test_sector_items_have_required_fields(self, test_client: TestClient) -> None:
        """Each sector item has SPEC-required fields."""
        response = test_client.get("/api/sectors/ranking")
        data = response.json()
        sectors = data["sectors"]
        if sectors:
            s = sectors[0]
            assert "name" in s
            assert "rank" in s
            assert "composite_score" in s
            assert "returns" in s
            assert "w1" in s["returns"]
            assert "m1" in s["returns"]
            assert "m3" in s["returns"]
            assert "excess_returns" in s
            assert "rs_avg" in s
            assert "stage2_pct" in s

    def test_sectors_ordered_by_rank(self, test_client: TestClient) -> None:
        """Sectors are ordered by rank (ascending)."""
        response = test_client.get("/api/sectors/ranking")
        data = response.json()
        sectors = data["sectors"]
        if len(sectors) > 1:
            ranks = [s["rank"] for s in sectors]
            assert ranks == sorted(ranks)

    def test_sector_returns_are_percentages(self, test_client: TestClient) -> None:
        """Returns should be in percentage format (not decimals)."""
        response = test_client.get("/api/sectors/ranking")
        data = response.json()
        sectors = data["sectors"]
        if sectors:
            # Returns can be negative but should be reasonable percentage range
            w1 = sectors[0]["returns"]["w1"]
            assert -100.0 <= w1 <= 100.0
