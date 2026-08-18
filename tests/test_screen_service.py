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


# stock_meta.market_cap은 프로덕션에서 원 단위로 저장된다(meta_service: 상장주식수 × 종가).
# 요청(ScreenRequest.market_cap_min)만 억원 단위이므로 픽스처도 원 단위로 맞춘다.
_EOK = 100_000_000  # 1억원

_SAMPLE_STOCKS = [
    {"code": "005930", "name": "삼성전자", "market": "KOSPI", "market_cap": 3_000_000 * _EOK,
     "sector_major": "전기전자", "close": 70000.0, "rs_12m": 85.0, "sma50": 65000.0},
    {"code": "000660", "name": "SK하이닉스", "market": "KOSPI", "market_cap": 1_500_000 * _EOK,
     "sector_major": "전기전자", "close": 130000.0, "rs_12m": 72.0, "sma50": 120000.0},
    {"code": "005490", "name": "POSCO홀딩스", "market": "KOSPI", "market_cap": 500_000 * _EOK,
     "sector_major": "철강금속", "close": 200000.0, "rs_12m": 60.0, "sma50": 190000.0},
    {"code": "035420", "name": "NAVER", "market": "KOSPI", "market_cap": 800_000 * _EOK,
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
        # 요청은 억원 단위, DB는 원 단위 → 1억 배 변환된 값이 바인딩되어야 한다
        req = ScreenRequest(market_cap_min=1000000)
        where, params = _build_where(req)
        assert "market_cap >= ?" in where
        assert 1000000 * 100_000_000 in params

    def test_chg_1d_filter(self):
        req = ScreenRequest(chg_1d_min=2.0)
        where, params = _build_where(req)
        assert "change_1d >= ?" in where
        assert 2.0 in params

    def test_chg_1w_filter(self):
        # DB stores chg_1w as decimal (0.015 = 1.5%), UI sends percentage (1.5)
        req = ScreenRequest(chg_1w_min=1.5)
        where, params = _build_where(req)
        assert "chg_1w >= ?" in where
        assert 0.015 in params

    def test_chg_1m_filter(self):
        # DB stores chg_1m as decimal (0.05 = 5%), UI sends percentage (5.0)
        req = ScreenRequest(chg_1m_min=5.0)
        where, params = _build_where(req)
        assert "chg_1m >= ?" in where
        assert 0.05 in params

    def test_chg_3m_filter(self):
        # DB stores chg_3m as decimal (0.10 = 10%), UI sends percentage (10.0)
        req = ScreenRequest(chg_3m_min=10.0)
        where, params = _build_where(req)
        assert "chg_3m >= ?" in where
        assert 0.10 in params

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
        """patterns는 5개까지 허용하고 6개부터 거부한다 (max_length=5).

        SPEC-MINERVINI-001이 Minervini 템플릿을 위해 상한을 3 → 5로 올렸다.
        경계를 양쪽으로 단언해 상한값 자체를 고정한다.
        """
        def _patterns(n: int) -> list[PatternCondition]:
            return [
                PatternCondition(
                    indicator_a="Close", operator="gt", indicator_b="SMA50", multiplier=1.0
                )
            ] * n

        # 경계 이하: 5개는 통과
        req = ScreenRequest(patterns=_patterns(5))
        assert len(req.patterns) == 5

        # 경계 초과: 6개는 거부
        with pytest.raises(ValidationError):
            ScreenRequest(patterns=_patterns(6))


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


# ---------------------------------------------------------------------------
# SPEC-SMA5-FILTER-001: SMA5 indicator screening (AC-5 / AC-6)
# ---------------------------------------------------------------------------


def _make_stock_meta_db_with_sma5(stocks: list[dict]) -> sqlite3.Connection:
    """In-memory stock_meta with an sma5 column (mirrors production DDL extension)."""
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
            rs_12m REAL,
            sma5 REAL,
            last_updated TEXT
        )"""
    )
    for s in stocks:
        conn.execute(
            """INSERT INTO stock_meta
               (code,name,market,market_cap,sector_major,close,change_1d,
                ema10,ema20,sma50,sma100,sma200,rs_12m,sma5,last_updated)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                s["code"], s["name"], s["market"], s.get("market_cap"),
                s.get("sector_major", "전기전자"),
                s.get("close", 100000.0), s.get("change_1d", 1.5),
                s.get("ema10", 95000.0), s.get("ema20", 90000.0),
                s.get("sma50", 85000.0), s.get("sma100", 80000.0),
                s.get("sma200", 75000.0), s.get("rs_12m", 80.0),
                s.get("sma5", 98000.0),
                "2026-02-28T00:00:00",
            ),
        )
    conn.commit()
    return conn


class TestSMA5Pattern:
    """AC-5: Close > SMA5 패턴이 정확한 WHERE 절을 생성하고 매칭 종목을 반환한다."""

    def test_sma5_pattern_builds_expected_where(self):
        """AC-5: 단일 패턴은 항상 외곽 괄호로 감싸여 정확히 '(close > sma5 * ?)' 생성."""
        pattern = PatternCondition(
            indicator_a="Close", operator="gt", indicator_b="SMA5", multiplier=1.0
        )
        req = ScreenRequest(patterns=[pattern])
        where, params = _build_where(req)
        assert where == "(close > sma5 * ?)"
        assert params == [1.0]

    def test_sma5_pattern_returns_matching_stock(self):
        """AC-5: close > sma5 를 만족하는 종목 A(close=110, sma5=100)가 결과에 포함된다."""
        stocks = [
            {"code": "000001", "name": "종목A", "market": "KOSPI",
             "market_cap": 100000, "close": 110.0, "sma5": 100.0},
            {"code": "000002", "name": "종목B", "market": "KOSPI",
             "market_cap": 100000, "close": 90.0, "sma5": 100.0},
        ]
        conn = _make_stock_meta_db_with_sma5(stocks)
        import backend.services.screen_service as svc
        orig = svc.get_db_conn
        svc.get_db_conn = lambda _path: conn
        try:
            pattern = PatternCondition(
                indicator_a="Close", operator="gt", indicator_b="SMA5", multiplier=1.0
            )
            req = ScreenRequest(patterns=[pattern])
            result = screen_stocks(req, ":memory:")
        finally:
            svc.get_db_conn = orig
            conn.close()

        codes = [s.code for sg in result.sectors for s in sg.stocks]
        assert "000001" in codes  # close(110) > sma5(100) → True
        assert "000002" not in codes  # close(90) > sma5(100) → False

    def test_sma5_in_indicator_column_map(self):
        """AC-6: SMA5가 _INDICATOR_COLUMN에 'sma5'로 매핑된다."""
        assert _INDICATOR_COLUMN["SMA5"] == "sma5"
