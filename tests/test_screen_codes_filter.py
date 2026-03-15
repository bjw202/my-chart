"""RED: Tests for R1 - codes filter in ScreenRequest and _build_where."""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import ValidationError

from backend.schemas.screen import ScreenRequest
from backend.services.screen_service import _build_where, screen_stocks


def _make_stock_meta_db(stocks: list[dict]) -> sqlite3.Connection:
    """Create an in-memory SQLite DB with stock_meta rows for testing."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(
        """CREATE TABLE stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT,
            market TEXT,
            market_cap INTEGER,
            sector_major TEXT,
            sector_minor TEXT,
            product TEXT,
            close REAL,
            change_1d REAL,
            ema10 REAL,
            ema20 REAL,
            sma50 REAL,
            sma100 REAL,
            sma200 REAL,
            high52w REAL,
            chg_1w REAL,
            chg_1m REAL,
            chg_3m REAL,
            rs_12m REAL,
            ma50_w REAL,
            ma150_w REAL,
            ma200_w REAL,
            last_updated TEXT
        )"""
    )
    for s in stocks:
        conn.execute(
            """INSERT INTO stock_meta
               (code,name,market,market_cap,sector_major,close,change_1d,
                ema10,ema20,sma50,sma100,sma200,rs_12m,last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                s["code"], s["name"], s["market"], s.get("market_cap"),
                s.get("sector_major", "전기전자"),
                s.get("close", 100000.0), s.get("change_1d", 1.5),
                s.get("ema10", 95000.0), s.get("ema20", 90000.0),
                s.get("sma50", 85000.0), s.get("sma100", 80000.0),
                s.get("sma200", 75000.0), s.get("rs_12m", 80.0),
                "2026-02-28T00:00:00",
            ),
        )
    conn.commit()
    return conn


_SAMPLE_STOCKS = [
    {"code": "005930", "name": "삼성전자", "market": "KOSPI", "market_cap": 3000000,
     "sector_major": "전기전자", "close": 70000.0, "rs_12m": 85.0},
    {"code": "000660", "name": "SK하이닉스", "market": "KOSPI", "market_cap": 1500000,
     "sector_major": "전기전자", "close": 130000.0, "rs_12m": 72.0},
    {"code": "005490", "name": "POSCO홀딩스", "market": "KOSPI", "market_cap": 500000,
     "sector_major": "철강금속", "close": 200000.0, "rs_12m": 60.0},
]


class TestScreenRequestCodes:
    """ScreenRequest.codes field existence and validation."""

    def test_codes_field_defaults_to_empty_list(self):
        req = ScreenRequest()
        assert req.codes == []

    def test_codes_field_accepts_list_of_strings(self):
        req = ScreenRequest(codes=["005930", "000660"])
        assert req.codes == ["005930", "000660"]

    def test_codes_empty_list_is_valid(self):
        req = ScreenRequest(codes=[])
        assert req.codes == []


class TestBuildWhereCodes:
    """_build_where generates correct SQL for codes filter."""

    def test_no_codes_filter_produces_no_code_in_clause(self):
        req = ScreenRequest()
        where, params = _build_where(req)
        assert "code IN" not in where

    def test_single_code_filter(self):
        req = ScreenRequest(codes=["005930"])
        where, params = _build_where(req)
        assert "code IN (?)" in where
        assert "005930" in params

    def test_multiple_codes_filter(self):
        req = ScreenRequest(codes=["005930", "000660", "005490"])
        where, params = _build_where(req)
        assert "code IN (?,?,?)" in where
        assert "005930" in params
        assert "000660" in params
        assert "005490" in params

    def test_codes_combined_with_other_filters(self):
        req = ScreenRequest(codes=["005930"], rs_min=80.0)
        where, params = _build_where(req)
        assert "code IN (?)" in where
        assert "rs_12m >= ?" in where
        assert "005930" in params
        assert 80.0 in params


class TestScreenStocksCodes:
    """screen_stocks returns only matching codes when codes filter is applied."""

    def setup_method(self):
        self.conn = _make_stock_meta_db(_SAMPLE_STOCKS)
        import backend.services.screen_service as svc
        self._orig_get_conn = svc.get_db_conn
        svc.get_db_conn = lambda _path: self.conn

    def teardown_method(self):
        import backend.services.screen_service as svc
        svc.get_db_conn = self._orig_get_conn
        self.conn.close()

    def test_codes_filter_returns_only_specified_codes(self):
        req = ScreenRequest(codes=["005930", "005490"])
        result = screen_stocks(req, ":memory:")
        codes = [s.code for sg in result.sectors for s in sg.stocks]
        assert set(codes) == {"005930", "005490"}
        assert result.total == 2

    def test_codes_filter_returns_empty_when_no_match(self):
        req = ScreenRequest(codes=["999999"])
        result = screen_stocks(req, ":memory:")
        assert result.total == 0

    def test_empty_codes_returns_all_stocks(self):
        req = ScreenRequest(codes=[])
        result = screen_stocks(req, ":memory:")
        assert result.total == 3
