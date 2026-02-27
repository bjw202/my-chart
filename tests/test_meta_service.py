"""Tests for backend/services/meta_service.py — stock_meta rebuild logic."""

from __future__ import annotations

import datetime
import sqlite3

import pandas as pd
import pytest

from backend.services.meta_service import _business_days_since, _rebuild


# ---------------------------------------------------------------------------
# Helpers to build test SQLite DB files
# ---------------------------------------------------------------------------


def _create_daily_db(path: str, stocks: list[dict], date: str = "2026-02-28") -> None:
    """Populate a daily DB file with stock_prices rows."""
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_prices (
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
    for s in stocks:
        conn.execute(
            """INSERT INTO stock_prices
               (Name, Date, Close, Change, EMA10, EMA20, SMA50, SMA100, SMA200, High52W)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                s["name"], date,
                s.get("close", 70000.0), s.get("change", 1.5),
                s.get("ema10", 69000.0), s.get("ema20", 68000.0),
                s.get("sma50", 65000.0), s.get("sma100"), s.get("sma200"),
                s.get("high52w", 75000.0),
            ),
        )
    conn.commit()
    conn.close()


def _create_weekly_db(path: str, stocks: list[dict], date: str = "2026-02-28") -> None:
    """Populate a weekly DB file with stock_prices and relative_strength rows."""
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_prices (
            Name TEXT NOT NULL, Date TEXT NOT NULL,
            Open REAL, High REAL, Low REAL, Close REAL,
            Volume REAL, Volume50MA REAL,
            CHG_1W REAL, CHG_1M REAL, CHG_2M REAL, CHG_3M REAL,
            CHG_6M REAL, CHG_9M REAL, CHG_12M REAL,
            MA50 REAL, MA150 REAL, MA200 REAL,
            MA200_Trend_1M REAL, MA200_Trend_2M REAL,
            MA200_Trend_3M REAL, MA200_Trend_4M REAL,
            MAX10 REAL, MAX52 REAL, min52 REAL, Close_52min REAL,
            RS_1M REAL, RS_2M REAL, RS_3M REAL,
            RS_6M REAL, RS_9M REAL, RS_12M REAL, RS_Line REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS relative_strength (
            Name TEXT NOT NULL, Date TEXT NOT NULL,
            RS_12M_Rating REAL, RS_6M_Rating REAL,
            RS_3M_Rating REAL, RS_1M_Rating REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    for s in stocks:
        conn.execute(
            """INSERT INTO stock_prices
               (Name, Date, CHG_1W, CHG_1M, CHG_3M, MA50, MA150, MA200)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                s["name"], date,
                s.get("chg_1w", 2.0), s.get("chg_1m", 5.0), s.get("chg_3m", 10.0),
                s.get("ma50", 68000.0), s.get("ma150", 65000.0), s.get("ma200", 62000.0),
            ),
        )
        conn.execute(
            "INSERT INTO relative_strength (Name, Date, RS_12M_Rating) VALUES (?,?,?)",
            (s["name"], date, s.get("rs_12m", 75.0)),
        )
    conn.commit()
    conn.close()


def _mock_sector_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Code": ["005930", "000660"],
        "Name": ["삼성전자", "SK하이닉스"],
        "Market": ["KOSPI", "KOSPI"],
        "산업명(대)": ["전기전자", "전기전자"],
        "산업명(중)": ["반도체", "반도체"],
        "주요제품": ["메모리", "D램"],
    })


# ---------------------------------------------------------------------------
# _business_days_since tests
# ---------------------------------------------------------------------------


class TestBusinessDaysSince:
    def test_today_is_zero(self):
        assert _business_days_since(datetime.date.today()) == 0

    def test_future_is_zero(self):
        future = datetime.date.today() + datetime.timedelta(days=5)
        assert _business_days_since(future) == 0

    def test_one_week_ago(self):
        week_ago = datetime.date.today() - datetime.timedelta(days=7)
        result = _business_days_since(week_ago)
        assert 4 <= result <= 5

    def test_two_days_ago_is_small(self):
        two_days_ago = datetime.date.today() - datetime.timedelta(days=2)
        assert _business_days_since(two_days_ago) <= 2


# ---------------------------------------------------------------------------
# _rebuild integration tests
# ---------------------------------------------------------------------------


class TestRebuild:
    """Tests for the _rebuild() function using in-memory daily conn + weekly file."""

    _DEFAULT_DAILY_STOCKS = [
        {"name": "삼성전자", "close": 70000.0, "sma100": 68000.0, "sma200": 65000.0},
        {"name": "SK하이닉스", "close": 130000.0, "sma100": None, "sma200": None},
    ]
    _DEFAULT_WEEKLY_STOCKS = [
        {"name": "삼성전자", "rs_12m": 85.0},
        {"name": "SK하이닉스", "rs_12m": 72.0},
    ]

    def _make_conn(self, daily_stocks, weekly_path: str, monkeypatch) -> sqlite3.Connection:
        """Set up in-memory daily conn and patch dependencies."""
        conn = sqlite3.connect(":memory:", check_same_thread=False)
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
        for s in daily_stocks:
            conn.execute(
                """INSERT INTO stock_prices
                   (Name, Date, Close, Change, EMA10, EMA20, SMA50, SMA100, SMA200, High52W)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    s["name"], "2026-02-28",
                    s.get("close", 70000.0), s.get("change", 1.5),
                    s.get("ema10", 69000.0), s.get("ema20", 68000.0),
                    s.get("sma50", 65000.0), s.get("sma100"), s.get("sma200"),
                    s.get("high52w", 75000.0),
                ),
            )
        conn.commit()

        import backend.services.meta_service as svc
        monkeypatch.setattr(svc, "get_sector_registry", lambda: _mock_sector_df())
        monkeypatch.setattr(svc, "REFERENCE_STOCK", "삼성전자")

        # Patch pykrx to avoid network calls
        import types
        fake_pykrx = types.ModuleType("pykrx_mock")
        mc_data = pd.DataFrame(
            {"시가총액": [300_000_000_000_000, 100_000_000_000_000]},
            index=pd.Index(["005930", "000660"]),
        )
        fake_pykrx.get_market_cap = lambda *a, **kw: mc_data
        monkeypatch.setattr(svc, "pykrx_stock", fake_pykrx, raising=False)

        return conn

    def test_basic_rebuild_inserts_both_stocks(self, monkeypatch, tmp_path):
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = self._make_conn(self._DEFAULT_DAILY_STOCKS, weekly_path, monkeypatch)
        _rebuild(conn, weekly_path)

        rows = conn.execute("SELECT code FROM stock_meta").fetchall()
        codes = [r[0] for r in rows]
        assert "005930" in codes
        assert "000660" in codes

    def test_missing_daily_stock_excluded(self, monkeypatch, tmp_path):
        """A stock in sectormap but without daily data must not appear in stock_meta."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        # Only 삼성전자 in daily DB
        conn = self._make_conn(
            [{"name": "삼성전자", "close": 70000.0, "sma100": 68000.0, "sma200": 65000.0}],
            weekly_path,
            monkeypatch,
        )
        _rebuild(conn, weekly_path)

        codes = [r[0] for r in conn.execute("SELECT code FROM stock_meta").fetchall()]
        assert "005930" in codes
        assert "000660" not in codes

    def test_null_sma100_stored_correctly(self, monkeypatch, tmp_path):
        """Stocks with insufficient history should store NULL sma100/sma200."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = self._make_conn(
            [{"name": "삼성전자", "close": 5000.0, "sma100": None, "sma200": None}],
            weekly_path,
            monkeypatch,
        )
        _rebuild(conn, weekly_path)

        row = conn.execute(
            "SELECT sma100, sma200 FROM stock_meta WHERE code = '005930'"
        ).fetchone()
        assert row is not None
        assert row[0] is None
        assert row[1] is None

    def test_null_weekly_data_stored_as_null(self, monkeypatch, tmp_path):
        """Stock with no weekly data row gets NULL for chg_1w, rs_12m, etc."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, [])  # empty weekly DB

        conn = self._make_conn(
            [{"name": "삼성전자", "close": 70000.0, "sma100": 68000.0, "sma200": 65000.0}],
            weekly_path,
            monkeypatch,
        )
        _rebuild(conn, weekly_path)

        row = conn.execute(
            "SELECT chg_1w, rs_12m FROM stock_meta WHERE code = '005930'"
        ).fetchone()
        assert row is not None
        # Both fields should be NULL since no weekly data exists
        assert row[0] is None
        assert row[1] is None

    def test_rs_data_populated_from_weekly(self, monkeypatch, tmp_path):
        """RS_12M_Rating from weekly DB should appear in stock_meta."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, [{"name": "삼성전자", "rs_12m": 92.5}])

        conn = self._make_conn(
            [{"name": "삼성전자", "close": 70000.0, "sma100": 68000.0, "sma200": 65000.0}],
            weekly_path,
            monkeypatch,
        )
        _rebuild(conn, weekly_path)

        row = conn.execute("SELECT rs_12m FROM stock_meta WHERE code = '005930'").fetchone()
        assert row is not None
        assert abs(row[0] - 92.5) < 0.001

    def test_empty_daily_db_does_nothing(self, monkeypatch, tmp_path):
        """If no daily data exists for reference stock, stock_meta stays empty."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = self._make_conn([], weekly_path, monkeypatch)
        # No stock_prices rows at all → latest_daily_date is None → early return
        _rebuild(conn, weekly_path)

        # stock_meta table should exist but be empty
        try:
            rows = conn.execute("SELECT count(*) FROM stock_meta").fetchone()
            assert rows[0] == 0
        except sqlite3.OperationalError:
            pass  # table might not exist if _rebuild returned early before CREATE TABLE
