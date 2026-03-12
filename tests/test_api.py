"""FastAPI TestClient integration tests for the KR Stock Screener API."""

from __future__ import annotations

import sqlite3
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Minimal test app (bypasses lifespan/registry loading)
# ---------------------------------------------------------------------------


def _make_test_app() -> FastAPI:
    """Create a FastAPI app with all routers but no lifespan registry init."""

    @asynccontextmanager
    async def _noop_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    test_app = FastAPI(lifespan=_noop_lifespan)
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from backend.routers.chart import router as chart_router
    from backend.routers.db import router as db_router
    from backend.routers.screen import router as screen_router
    from backend.routers.sectors import router as sectors_router

    test_app.include_router(chart_router, prefix="/api")
    test_app.include_router(db_router, prefix="/api")
    test_app.include_router(screen_router, prefix="/api")
    test_app.include_router(sectors_router, prefix="/api")

    return test_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    app = _make_test_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def stock_meta_db(tmp_path):
    """Write a minimal daily DB with stock_meta + stock_prices to a temp file."""
    db_path = str(tmp_path / "stock_data_daily.db")
    conn = sqlite3.connect(db_path)

    conn.execute(
        """CREATE TABLE stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT, market TEXT, market_cap INTEGER,
            sector_major TEXT, sector_minor TEXT, product TEXT,
            close REAL, change_1d REAL,
            ema10 REAL, ema20 REAL, sma50 REAL, sma100 REAL, sma200 REAL,
            high52w REAL, chg_1w REAL, chg_1m REAL, chg_3m REAL,
            rs_12m REAL, sma10_w REAL, sma20_w REAL, sma40_w REAL,
            last_updated TEXT
        )"""
    )
    conn.execute(
        """CREATE TABLE stock_prices (
            Name TEXT NOT NULL, Date TEXT NOT NULL,
            Open REAL, High REAL, Low REAL, Close REAL,
            Change REAL, High52W REAL,
            Volume REAL, Volume20MA REAL, VolumeWon REAL,
            EMA10 REAL, EMA20 REAL, SMA21 REAL, SMA50 REAL, EMA65 REAL, SMA100 REAL, SMA200 REAL,
            DailyRange REAL, HLC REAL,
            FromEMA10 REAL, FromEMA20 REAL, FromSMA50 REAL, FromSMA200 REAL,
            Range REAL, ADR20 REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )

    conn.execute(
        """INSERT INTO stock_meta
           (code,name,market,market_cap,sector_major,close,change_1d,ema10,ema20,
            sma50,sma100,sma200,rs_12m,last_updated)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        ("005930", "삼성전자", "KOSPI", 3000000, "전기전자",
         70000.0, 1.5, 69000.0, 68000.0, 65000.0, 63000.0, 60000.0, 85.0,
         "2026-02-28T00:00:00"),
    )

    for i in range(5):
        date = f"2026-02-{20 + i:02d}"
        conn.execute(
            """INSERT INTO stock_prices
               (Name,Date,Open,High,Low,Close,Volume,EMA10,EMA20,SMA50,SMA100,SMA200)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("삼성전자", date, 69500.0, 70500.0, 69000.0, 70000.0 + i * 100,
             1_000_000, 69000.0, 68000.0, 65000.0, 63000.0, 60000.0),
        )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def patch_db(stock_meta_db, monkeypatch):
    """Patch all router-level DAILY_DB_PATH and WEEKLY_DB_PATH constants."""
    monkeypatch.setattr("backend.routers.screen.DAILY_DB_PATH", stock_meta_db)
    monkeypatch.setattr("backend.routers.chart.DAILY_DB_PATH", stock_meta_db)
    monkeypatch.setattr("backend.routers.sectors.DAILY_DB_PATH", stock_meta_db)
    monkeypatch.setattr("backend.routers.db.DAILY_DB_PATH", stock_meta_db)
    monkeypatch.setattr("backend.routers.db.WEEKLY_DB_PATH", stock_meta_db)
    return stock_meta_db


# ---------------------------------------------------------------------------
# /api/screen tests
# ---------------------------------------------------------------------------


class TestScreenEndpoint:
    def test_empty_filter_returns_200(self, client, patch_db):
        resp = client.post("/api/screen", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "sectors" in data

    def test_filter_returns_matching_stocks(self, client, patch_db):
        resp = client.post("/api/screen", json={"rs_min": 80.0})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        codes = [s["code"] for sg in data["sectors"] for s in sg["stocks"]]
        assert "005930" in codes

    def test_no_matches_returns_empty(self, client, patch_db):
        resp = client.post("/api/screen", json={"market_cap_min": 999_999_999})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_invalid_indicator_rejected_by_pydantic(self, client, patch_db):
        """Pydantic validates indicator names; invalid names return 422."""
        payload = {
            "patterns": [
                {"indicator_a": "INVALID_COL", "operator": "gt",
                 "indicator_b": "Close", "multiplier": 1.0}
            ]
        }
        resp = client.post("/api/screen", json=payload)
        assert resp.status_code == 422

    def test_valid_pattern_condition(self, client, patch_db):
        payload = {
            "patterns": [
                {"indicator_a": "Close", "operator": "gte",
                 "indicator_b": "SMA50", "multiplier": 1.0}
            ]
        }
        resp = client.post("/api/screen", json=payload)
        assert resp.status_code == 200

    def test_too_many_patterns_rejected(self, client, patch_db):
        """More than 3 patterns should return 422."""
        payload = {
            "patterns": [
                {"indicator_a": "Close", "operator": "gt", "indicator_b": "SMA50", "multiplier": 1.0}
            ] * 4
        }
        resp = client.post("/api/screen", json=payload)
        assert resp.status_code == 422

    def test_market_filter_kospi(self, client, patch_db):
        resp = client.post("/api/screen", json={"markets": ["KOSPI"]})
        assert resp.status_code == 200
        data = resp.json()
        for sg in data["sectors"]:
            for s in sg["stocks"]:
                assert s["market"] == "KOSPI"

    def test_screen_response_structure(self, client, patch_db):
        resp = client.post("/api/screen", json={})
        data = resp.json()
        assert isinstance(data["sectors"], list)
        if data["sectors"]:
            sector = data["sectors"][0]
            assert "sector_name" in sector
            assert "stock_count" in sector
            assert "stocks" in sector


# ---------------------------------------------------------------------------
# /api/chart/{code} tests
# ---------------------------------------------------------------------------


class TestChartEndpoint:
    def test_valid_code_returns_200(self, client, patch_db):
        resp = client.get("/api/chart/005930")
        assert resp.status_code == 200
        data = resp.json()
        assert "candles" in data
        assert "volume" in data
        assert "ma" in data

    def test_candles_structure(self, client, patch_db):
        resp = client.get("/api/chart/005930")
        candle = resp.json()["candles"][0]
        assert "time" in candle
        assert "open" in candle
        assert "high" in candle
        assert "low" in candle
        assert "close" in candle

    def test_ma_overlays_structure(self, client, patch_db):
        resp = client.get("/api/chart/005930")
        ma = resp.json()["ma"]
        for key in ("ema10", "ema20", "sma50", "sma100", "sma200"):
            assert key in ma

    def test_unknown_code_returns_404(self, client, patch_db):
        resp = client.get("/api/chart/999999")
        assert resp.status_code == 404

    def test_404_detail_includes_error_key(self, client, patch_db):
        resp = client.get("/api/chart/999999")
        body = resp.json()
        # detail may be nested dict or string
        detail = body.get("detail", body)
        if isinstance(detail, dict):
            assert "error" in detail
        else:
            assert "error" in str(detail)


# ---------------------------------------------------------------------------
# /api/sectors tests
# ---------------------------------------------------------------------------


class TestSectorsEndpoint:
    def test_returns_200(self, client, patch_db):
        resp = client.get("/api/sectors")
        assert resp.status_code == 200

    def test_response_is_list(self, client, patch_db):
        data = client.get("/api/sectors").json()
        assert isinstance(data, list)

    def test_sector_items_have_required_fields(self, client, patch_db):
        data = client.get("/api/sectors").json()
        assert len(data) >= 1
        sector = data[0]
        assert "sector_name" in sector
        assert "count" in sector
        assert sector["count"] >= 1

    def test_empty_db_returns_empty_list(self, client, tmp_path, monkeypatch):
        """When stock_meta doesn't exist, /api/sectors returns empty list."""
        db_path = str(tmp_path / "empty.db")
        sqlite3.connect(db_path).close()
        monkeypatch.setattr("backend.routers.sectors.DAILY_DB_PATH", db_path)
        resp = client.get("/api/sectors")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# /api/db/last-updated tests
# ---------------------------------------------------------------------------


class TestDbLastUpdatedEndpoint:
    def test_returns_200(self, client, patch_db):
        resp = client.get("/api/db/last-updated")
        assert resp.status_code == 200

    def test_response_structure(self, client, patch_db):
        data = client.get("/api/db/last-updated").json()
        assert "last_updated" in data
        assert "daily_db_size" in data
        assert "weekly_db_size" in data

    def test_db_sizes_positive(self, client, patch_db):
        data = client.get("/api/db/last-updated").json()
        assert data["daily_db_size"] > 0

    def test_last_updated_with_corrupt_db_returns_200(self, client, tmp_path, monkeypatch):
        """When DAILY_DB_PATH points to a file without stock_meta, returns 200 with null last_updated."""
        bad_db = str(tmp_path / "bad.db")
        import sqlite3
        conn = sqlite3.connect(bad_db)
        conn.close()  # empty DB, no stock_meta table
        monkeypatch.setattr("backend.routers.db.DAILY_DB_PATH", bad_db)
        monkeypatch.setattr("backend.routers.db.WEEKLY_DB_PATH", bad_db)
        resp = client.get("/api/db/last-updated")
        assert resp.status_code == 200
        data = resp.json()
        assert data["last_updated"] is None


# ---------------------------------------------------------------------------
# /api/db/update tests
# ---------------------------------------------------------------------------


class TestDbUpdateEndpoint:
    def test_returns_202_when_not_running(self, client, monkeypatch):
        monkeypatch.setattr("backend.routers.db.DAILY_DB_PATH", ":memory:")
        monkeypatch.setattr("backend.routers.db.WEEKLY_DB_PATH", ":memory:")
        monkeypatch.setattr("backend.routers.db.start_update", lambda *a: True)
        resp = client.post("/api/db/update")
        assert resp.status_code == 202
        assert resp.json()["status"] == "started"

    def test_returns_409_when_running(self, client, monkeypatch):
        monkeypatch.setattr("backend.routers.db.DAILY_DB_PATH", ":memory:")
        monkeypatch.setattr("backend.routers.db.WEEKLY_DB_PATH", ":memory:")
        monkeypatch.setattr("backend.routers.db.start_update", lambda *a: False)
        resp = client.post("/api/db/update")
        assert resp.status_code == 409
        data = resp.json()
        assert data["detail"]["error"] == "update_in_progress"
