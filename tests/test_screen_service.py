"""Characterization + integration tests for backend/services/screen_service.py."""

from __future__ import annotations

import sqlite3

import pytest
from pydantic import ValidationError

from backend.schemas.screen import PatternCondition, ScreenRequest
from backend.services.screen_service import _INDICATOR_COLUMN, _build_where, screen_stocks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
     "sector_major": "전기전자", "close": 70000.0, "rs_12m": 85.0, "sma50": 65000.0},
    {"code": "000660", "name": "SK하이닉스", "market": "KOSPI", "market_cap": 1500000,
     "sector_major": "전기전자", "close": 130000.0, "rs_12m": 72.0, "sma50": 120000.0},
    {"code": "005490", "name": "POSCO홀딩스", "market": "KOSPI", "market_cap": 500000,
     "sector_major": "철강금속", "close": 200000.0, "rs_12m": 60.0, "sma50": 190000.0},
    {"code": "035420", "name": "NAVER", "market": "KOSPI", "market_cap": 800000,
     "sector_major": "서비스업", "close": 150000.0, "rs_12m": 55.0, "sma50": 145000.0},
]


# ---------------------------------------------------------------------------
# _build_where tests
# ---------------------------------------------------------------------------


class TestBuildWhere:
    def test_empty_request_returns_tautology(self):
        req = ScreenRequest()
        where, params = _build_where(req)
        assert where == "1=1"
        assert params == []

    def test_market_cap_filter(self):
        req = ScreenRequest(market_cap_min=1000000)
        where, params = _build_where(req)
        assert "market_cap >= ?" in where
        assert 1000000 in params

    def test_chg_1d_filter(self):
        req = ScreenRequest(chg_1d_min=2.0)
        where, params = _build_where(req)
        assert "change_1d >= ?" in where
        assert 2.0 in params

    def test_chg_1w_filter(self):
        req = ScreenRequest(chg_1w_min=1.5)
        where, params = _build_where(req)
        assert "chg_1w >= ?" in where
        assert 1.5 in params

    def test_chg_1m_filter(self):
        req = ScreenRequest(chg_1m_min=5.0)
        where, params = _build_where(req)
        assert "chg_1m >= ?" in where
        assert 5.0 in params

    def test_chg_3m_filter(self):
        req = ScreenRequest(chg_3m_min=10.0)
        where, params = _build_where(req)
        assert "chg_3m >= ?" in where
        assert 10.0 in params

    def test_rs_filter(self):
        req = ScreenRequest(rs_min=70.0)
        where, params = _build_where(req)
        assert "rs_12m >= ?" in where
        assert 70.0 in params

    def test_markets_filter_single(self):
        req = ScreenRequest(markets=["KOSPI"])
        where, params = _build_where(req)
        assert "market IN (?)" in where
        assert "KOSPI" in params

    def test_markets_filter_both(self):
        req = ScreenRequest(markets=["KOSPI", "KOSDAQ"])
        where, params = _build_where(req)
        assert "market IN (?,?)" in where
        assert "KOSPI" in params and "KOSDAQ" in params

    def test_sectors_filter(self):
        req = ScreenRequest(sectors=["전기전자", "철강금속"])
        where, params = _build_where(req)
        assert "sector_major IN (?,?)" in where
        assert "전기전자" in params

    def test_pattern_condition_and(self):
        pattern = PatternCondition(
            indicator_a="Close", operator="gte", indicator_b="SMA50", multiplier=1.0
        )
        req = ScreenRequest(patterns=[pattern], pattern_logic="AND")
        where, params = _build_where(req)
        assert "close >= sma50 * ?" in where
        assert 1.0 in params

    def test_pattern_condition_with_multiplier(self):
        pattern = PatternCondition(
            indicator_a="Close", operator="gte", indicator_b="SMA200", multiplier=0.95
        )
        req = ScreenRequest(patterns=[pattern])
        where, params = _build_where(req)
        assert "close >= sma200 * ?" in where
        assert 0.95 in params

    def test_multiple_patterns_and_logic(self):
        patterns = [
            PatternCondition(indicator_a="Close", operator="gte", indicator_b="SMA50", multiplier=1.0),
            PatternCondition(indicator_a="EMA10", operator="gt", indicator_b="EMA20", multiplier=1.0),
        ]
        req = ScreenRequest(patterns=patterns, pattern_logic="AND")
        where, params = _build_where(req)
        assert " AND " in where
        assert len([p for p in params if isinstance(p, float)]) == 2

    def test_multiple_patterns_or_logic(self):
        patterns = [
            PatternCondition(indicator_a="Close", operator="gte", indicator_b="SMA50", multiplier=1.0),
            PatternCondition(indicator_a="Close", operator="gte", indicator_b="SMA100", multiplier=1.0),
        ]
        req = ScreenRequest(patterns=patterns, pattern_logic="OR")
        where, params = _build_where(req)
        # Pattern clause should have OR inside parentheses
        assert " OR " in where

    def test_combined_filters(self):
        pattern = PatternCondition(
            indicator_a="Close", operator="gte", indicator_b="SMA50", multiplier=1.0
        )
        req = ScreenRequest(
            market_cap_min=500000,
            rs_min=70.0,
            markets=["KOSPI"],
            patterns=[pattern],
        )
        where, params = _build_where(req)
        assert "market_cap >= ?" in where
        assert "rs_12m >= ?" in where
        assert "market IN (?)" in where
        assert "close >= sma50 * ?" in where

    def test_max_patterns_enforced(self):
        """Pydantic model should reject more than 3 patterns."""
        patterns = [
            PatternCondition(indicator_a="Close", operator="gt", indicator_b="SMA50", multiplier=1.0)
        ] * 4
        with pytest.raises(ValidationError):
            ScreenRequest(patterns=patterns)


# ---------------------------------------------------------------------------
# SQL injection prevention
# ---------------------------------------------------------------------------


class TestSQLInjectionPrevention:
    def test_invalid_indicator_name_rejected_by_pydantic(self):
        """Any indicator name not in the Literal whitelist must be rejected."""
        with pytest.raises(ValidationError):
            PatternCondition(
                indicator_a="Name; DROP TABLE stock_meta",
                operator="gt",
                indicator_b="Close",
                multiplier=1.0,
            )

    def test_operator_injection_rejected(self):
        """Invalid operator strings must be rejected by Pydantic."""
        with pytest.raises(ValidationError):
            PatternCondition(
                indicator_a="Close",
                operator="> 1 OR 1=1 --",
                indicator_b="SMA50",
                multiplier=1.0,
            )

    def test_indicator_column_map_covers_all_whitelist_values(self):
        """Every Literal value in the whitelist must have a safe column mapping."""
        from typing import get_args
        from backend.schemas.screen import IndicatorName
        for name in get_args(IndicatorName):
            assert name in _INDICATOR_COLUMN, f"Missing mapping for {name}"

    def test_column_names_are_lowercase_identifiers(self):
        """Mapped column names must be simple lowercase identifiers (no SQL characters)."""
        import re
        for col in _INDICATOR_COLUMN.values():
            assert re.match(r"^[a-z][a-z0-9_]*$", col), f"Unsafe column name: {col}"


# ---------------------------------------------------------------------------
# screen_stocks integration tests (in-memory DB)
# ---------------------------------------------------------------------------


class TestScreenStocks:
    def setup_method(self):
        self.conn = _make_stock_meta_db(_SAMPLE_STOCKS)
        # Patch get_db_conn to return our in-memory connection
        import backend.services.screen_service as svc
        self._orig_get_conn = svc.get_db_conn
        svc.get_db_conn = lambda _path: self.conn

    def teardown_method(self):
        import backend.services.screen_service as svc
        svc.get_db_conn = self._orig_get_conn
        self.conn.close()

    def test_empty_filter_returns_all_stocks(self):
        req = ScreenRequest()
        result = screen_stocks(req, ":memory:")
        assert result.total == 4

    def test_market_cap_filter_reduces_results(self):
        req = ScreenRequest(market_cap_min=1000000)
        result = screen_stocks(req, ":memory:")
        assert result.total == 2
        codes = [s.code for sg in result.sectors for s in sg.stocks]
        assert "005930" in codes
        assert "000660" in codes
        assert "005490" not in codes

    def test_rs_filter(self):
        req = ScreenRequest(rs_min=80.0)
        result = screen_stocks(req, ":memory:")
        assert result.total == 1
        assert result.sectors[0].stocks[0].code == "005930"

    def test_market_filter_kospi_only(self):
        req = ScreenRequest(markets=["KOSPI"])
        result = screen_stocks(req, ":memory:")
        assert result.total == 4  # all are KOSPI in our test data
        for sg in result.sectors:
            for s in sg.stocks:
                assert s.market == "KOSPI"

    def test_sector_filter(self):
        req = ScreenRequest(sectors=["전기전자"])
        result = screen_stocks(req, ":memory:")
        assert result.total == 2
        for sg in result.sectors:
            assert sg.sector_name == "전기전자"

    def test_results_grouped_by_sector(self):
        req = ScreenRequest()
        result = screen_stocks(req, ":memory:")
        sector_names = [sg.sector_name for sg in result.sectors]
        assert len(set(sector_names)) == len(sector_names), "Duplicate sector groups"

    def test_no_matches_returns_empty_response(self):
        req = ScreenRequest(market_cap_min=99_999_999)
        result = screen_stocks(req, ":memory:")
        assert result.total == 0
        assert result.sectors == []

    def test_pattern_condition_close_above_sma50(self):
        # 삼성전자: close=70000, sma50=65000 → Close >= SMA50 * 1.0 → True
        # SK하이닉스: close=130000, sma50=120000 → True
        # POSCO: close=200000, sma50=190000 → True
        # NAVER: close=150000, sma50=145000 → True
        # All stocks should match
        pattern = PatternCondition(indicator_a="Close", operator="gte", indicator_b="SMA50", multiplier=1.0)
        req = ScreenRequest(patterns=[pattern])
        result = screen_stocks(req, ":memory:")
        assert result.total == 4

    def test_null_market_cap_excluded_by_filter(self):
        """Stocks with NULL market_cap are excluded by market_cap_min filter (SQL NULL semantics)."""
        # Add a stock with NULL market_cap
        self.conn.execute(
            """INSERT INTO stock_meta (code,name,market,market_cap,sector_major,close,change_1d,
               ema10,ema20,sma50,sma100,sma200,rs_12m,last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("999999", "신규상장A", "KOSDAQ", None, "기타", 5000.0, 0.5,
             4900.0, 4800.0, 4700.0, 4600.0, 4500.0, 50.0, "2026-02-28T00:00:00"),
        )
        self.conn.commit()

        req = ScreenRequest(market_cap_min=1)  # any positive threshold
        result = screen_stocks(req, ":memory:")
        codes = [s.code for sg in result.sectors for s in sg.stocks]
        assert "999999" not in codes  # NULL market_cap excluded by WHERE NULL >= 1 → False
