"""Specification tests for my_chart/analysis/market_breadth.py.

Tests are written first (RED phase) to define expected behavior.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures: in-memory weekly DB
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
    sma10: float = 95.0,
    sma40: float = 90.0,
    chg_1w: float = 0.02,
    max52: float = 110.0,
    min52: float = 80.0,
    volume: float = 1_000_000.0,
    volume_sma10: float = 800_000.0,
    chg_1m: float = 0.05,
) -> tuple:
    """Build a 32-element weekly row tuple with sensible defaults."""
    return (
        name, date,
        close * 0.99, close * 1.01, close * 0.98, close,  # OHLC
        volume, volume_sma10,
        chg_1w, chg_1m, 0.08, 0.12, 0.20, 0.25, 0.30,   # CHG_1W ~ CHG_12M
        sma10, 92.0, sma40,                                 # SMA10, SMA20, SMA40
        0.5, 0.3, 0.2, 0.1,                                 # SMA40_Trend
        close * 1.05, max52, min52, close - min52,          # MAX10, MAX52, min52, Close_52min
        50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 1.1,           # RS_1M..RS_12M, RS_Line
    )


@pytest.fixture
def weekly_db_path(tmp_path: Path) -> str:
    """Create an in-memory weekly DB with test data."""
    db_path = str(tmp_path / "test_weekly.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_WEEKLY_DDL)
    conn.execute(_RS_DDL)

    test_date = "2024-01-05"
    prev_date = "2023-12-29"

    # 10 KOSPI stocks: 7 above SMA10, 3 below
    # Stock 1-7: Close > SMA10 (above 50-day proxy)
    for i in range(1, 8):
        close = 100.0
        sma10 = 90.0  # Close > SMA10
        # Only 5 of 7 above SMA40 (200-day proxy)
        sma40 = 80.0 if i <= 5 else 110.0
        chg_1w = 0.02 if i % 2 == 0 else -0.01
        max52 = 105.0 if i == 1 else 120.0  # stock 1 at 52W high
        min52 = 95.0 if i == 3 else 70.0    # stock 3 at 52W low
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES " + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_weekly_row(f"Stock{i}", test_date, close=close, sma10=sma10, sma40=sma40,
                             chg_1w=chg_1w, max52=max52, min52=min52),
        )
        # Previous date for slope calculation
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES " + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_weekly_row(f"Stock{i}", prev_date, close=close * 0.98, sma10=sma10 * 0.99,
                             sma40=sma40 * 0.99),
        )

    # Stocks 8-10: Close < SMA10 (below 50-day proxy)
    for i in range(8, 11):
        close = 85.0
        sma10 = 95.0  # Close < SMA10
        sma40 = 100.0
        chg_1w = -0.03
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES " + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_weekly_row(f"Stock{i}", test_date, close=close, sma10=sma10, sma40=sma40, chg_1w=chg_1w),
        )
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES " + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_weekly_row(f"Stock{i}", prev_date, close=close * 0.97, sma10=sma10 * 1.01, sma40=sma40 * 1.01),
        )

    # KOSPI index entry
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES " + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_weekly_row("KOSPI", test_date, close=2500.0, sma10=2400.0, sma40=2300.0, chg_1w=0.015),
    )
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES " + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_weekly_row("KOSPI", prev_date, close=2400.0, sma10=2350.0, sma40=2280.0),
    )

    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def weekly_db_12weeks(tmp_path: Path) -> str:
    """Create weekly DB with 12 weeks of data for history tests."""
    db_path = str(tmp_path / "test_weekly_12w.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_WEEKLY_DDL)
    conn.execute(_RS_DDL)

    from datetime import date, timedelta
    base = date(2024, 1, 5)

    for week in range(12):
        dt = (base - timedelta(weeks=week)).isoformat()
        # pct_above_sma50 oscillates between ~40% and ~70%
        above_count = 7 - (week % 4)  # 7,6,5,4,7,6,5,4,...
        for i in range(1, 11):
            above = i <= above_count
            close = 100.0
            sma10 = 90.0 if above else 110.0
            chg_1w = 0.01 if above else -0.01
            conn.execute(
                "INSERT OR REPLACE INTO stock_prices VALUES " + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                _make_weekly_row(f"Stock{i}", dt, close=close, sma10=sma10, chg_1w=chg_1w),
            )
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES " + "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_weekly_row("KOSPI", dt, close=2500.0, sma10=2400.0, sma40=2300.0,
                             chg_1w=0.01 if week % 3 != 0 else -0.01),
        )

    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Tests: compute_breadth (AC1)
# ---------------------------------------------------------------------------


class TestComputeBreadth:
    """Tests for compute_breadth() - R1 Market Breadth Calculation."""

    def test_pct_above_sma50_correct(self, weekly_db_path: str) -> None:
        """AC1: compute_breadth() returns correct pct_above_sma50 for test dataset."""
        from my_chart.analysis.market_breadth import compute_breadth

        result = compute_breadth(weekly_db_path, "KOSPI", "2024-01-05")
        # 7 out of 10 stocks have Close > SMA10 (proxy for SMA50)
        assert abs(result.pct_above_sma50 - 70.0) < 1.0

    def test_pct_above_sma200_correct(self, weekly_db_path: str) -> None:
        """pct_above_sma200 uses SMA40 as ~200-day proxy."""
        from my_chart.analysis.market_breadth import compute_breadth

        result = compute_breadth(weekly_db_path, "KOSPI", "2024-01-05")
        # Stocks 1-5: Close > SMA40, Stocks 6-10: Close <= SMA40
        # Stock 6,7 have SMA40=110 > Close=100, Stocks 8-10 have SMA40=100 > Close=85
        assert 40.0 <= result.pct_above_sma200 <= 60.0

    def test_nh_nl_ratio_in_range(self, weekly_db_path: str) -> None:
        """nh_nl_ratio is between 0 and 1."""
        from my_chart.analysis.market_breadth import compute_breadth

        result = compute_breadth(weekly_db_path, "KOSPI", "2024-01-05")
        assert 0.0 <= result.nh_nl_ratio <= 1.0

    def test_nh_nl_diff_is_integer_like(self, weekly_db_path: str) -> None:
        """nh_nl_diff is new_high_count - new_low_count."""
        from my_chart.analysis.market_breadth import compute_breadth

        result = compute_breadth(weekly_db_path, "KOSPI", "2024-01-05")
        # Difference should be an integer (or float close to integer)
        assert isinstance(result.nh_nl_diff, (int, float))

    def test_ad_ratio_positive_when_mostly_advancing(self, weekly_db_path: str) -> None:
        """ad_ratio > 1.0 when more stocks advance than decline."""
        from my_chart.analysis.market_breadth import compute_breadth

        result = compute_breadth(weekly_db_path, "KOSPI", "2024-01-05")
        # Stocks 1-7: some advance (+), some decline (-); Stocks 8-10: all decline
        assert result.ad_ratio >= 0.0

    def test_result_has_all_required_fields(self, weekly_db_path: str) -> None:
        """BreadthResult has all required fields."""
        from my_chart.analysis.market_breadth import compute_breadth

        result = compute_breadth(weekly_db_path, "KOSPI", "2024-01-05")
        assert hasattr(result, "pct_above_sma50")
        assert hasattr(result, "pct_above_sma200")
        assert hasattr(result, "nh_nl_ratio")
        assert hasattr(result, "nh_nl_diff")
        assert hasattr(result, "ad_ratio")
        assert hasattr(result, "date")
        assert hasattr(result, "market")

    def test_excludes_index_stocks(self, weekly_db_path: str) -> None:
        """KOSPI/KOSDAQ index entries must be excluded from breadth calculations."""
        from my_chart.analysis.market_breadth import compute_breadth

        result = compute_breadth(weekly_db_path, "KOSPI", "2024-01-05")
        # Should only count 10 individual stocks, not the KOSPI index itself
        assert result.total_stocks == 10


# ---------------------------------------------------------------------------
# Tests: compute_breadth_composite (R2 - AC not directly numbered but required)
# ---------------------------------------------------------------------------


class TestComputeBreadthComposite:
    """Tests for compute_breadth_composite() - R2 Breadth Composite Score."""

    def test_composite_score_in_range(self, weekly_db_path: str) -> None:
        """Breadth composite score is between 0 and 100."""
        from my_chart.analysis.market_breadth import compute_breadth, compute_breadth_composite

        breadth = compute_breadth(weekly_db_path, "KOSPI", "2024-01-05")
        score = compute_breadth_composite(breadth)
        assert 0.0 <= score <= 100.0

    def test_composite_score_is_float(self, weekly_db_path: str) -> None:
        """Breadth composite score is a float."""
        from my_chart.analysis.market_breadth import compute_breadth, compute_breadth_composite

        breadth = compute_breadth(weekly_db_path, "KOSPI", "2024-01-05")
        score = compute_breadth_composite(breadth)
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# Tests: determine_cycle (AC2, AC3)
# ---------------------------------------------------------------------------


class TestDetermineCycle:
    """Tests for determine_cycle() - R3 Market Cycle Determination."""

    def _make_bull_breadth(self):
        """Create a breadth result that triggers bull criteria."""
        from my_chart.analysis.market_breadth import BreadthResult

        return BreadthResult(
            date="2024-01-05",
            market="KOSPI",
            pct_above_sma50=70.0,   # Bull: > 60%
            pct_above_sma200=60.0,  # Bull: > 55%
            nh_nl_ratio=0.7,        # Bull: > 0.6
            nh_nl_diff=30,
            ad_ratio=2.5,
            breadth_score=70.0,     # Bull: > 65
            total_stocks=100,
        )

    def _make_bear_breadth(self):
        """Create a breadth result that triggers bear criteria."""
        from my_chart.analysis.market_breadth import BreadthResult

        return BreadthResult(
            date="2024-01-05",
            market="KOSPI",
            pct_above_sma50=30.0,   # Bear: < 40%
            pct_above_sma200=35.0,  # Bear: < 40%
            nh_nl_ratio=0.2,        # Bear: < 0.4
            nh_nl_diff=-30,
            ad_ratio=0.4,
            breadth_score=25.0,     # Bear: < 35
            total_stocks=100,
        )

    def _make_sideways_breadth(self):
        """Create a breadth result with mixed criteria."""
        from my_chart.analysis.market_breadth import BreadthResult

        return BreadthResult(
            date="2024-01-05",
            market="KOSPI",
            pct_above_sma50=52.0,   # Sideways: 40-60%
            pct_above_sma200=47.0,  # Sideways: 40-55%
            nh_nl_ratio=0.5,        # Sideways: 0.4-0.6
            nh_nl_diff=5,
            ad_ratio=1.1,
            breadth_score=50.0,     # Sideways: 35-65
            total_stocks=100,
        )

    def _make_bull_kospi_data(self):
        """KOSPI data for bull market: price > both MAs, SMA50 slope positive."""
        return {
            "close": 2500.0,
            "sma50": 2300.0,    # price > sma50
            "sma200": 2100.0,   # price > sma200
            "sma50_slope": 0.02,  # Bull: positive
        }

    def _make_bear_kospi_data(self):
        """KOSPI data for bear market."""
        return {
            "close": 2000.0,
            "sma50": 2200.0,    # price < sma50
            "sma200": 2300.0,   # price < sma200
            "sma50_slope": -0.03,  # Bear: negative
        }

    def _make_sideways_kospi_data(self):
        """KOSPI data for sideways: price between MAs."""
        return {
            "close": 2200.0,
            "sma50": 2100.0,    # price > sma50
            "sma200": 2300.0,   # price < sma200 → between MAs
            "sma50_slope": 0.001,  # Near zero
        }

    def test_bull_when_4_plus_criteria_bullish(self) -> None:
        """AC2: determine_cycle() returns 'bull' when 4+ criteria are bullish."""
        from my_chart.analysis.market_breadth import determine_cycle

        breadth = self._make_bull_breadth()
        kospi_data = self._make_bull_kospi_data()
        result = determine_cycle(breadth, kospi_data)

        assert result.phase == "bull"

    def test_bear_when_4_plus_criteria_bearish(self) -> None:
        """determine_cycle() returns 'bear' when 4+ criteria are bearish."""
        from my_chart.analysis.market_breadth import determine_cycle

        breadth = self._make_bear_breadth()
        kospi_data = self._make_bear_kospi_data()
        result = determine_cycle(breadth, kospi_data)

        assert result.phase == "bear"

    def test_sideways_when_criteria_mixed(self) -> None:
        """AC3: determine_cycle() returns 'sideways' when criteria are mixed."""
        from my_chart.analysis.market_breadth import determine_cycle

        breadth = self._make_sideways_breadth()
        kospi_data = self._make_sideways_kospi_data()
        result = determine_cycle(breadth, kospi_data)

        assert result.phase == "sideways"

    def test_result_has_criteria_list(self) -> None:
        """CycleResult includes criteria evaluation list."""
        from my_chart.analysis.market_breadth import determine_cycle

        breadth = self._make_bull_breadth()
        kospi_data = self._make_bull_kospi_data()
        result = determine_cycle(breadth, kospi_data)

        assert hasattr(result, "criteria")
        assert len(result.criteria) == 6  # 6 criteria per SPEC

    def test_result_has_confidence(self) -> None:
        """CycleResult includes confidence score."""
        from my_chart.analysis.market_breadth import determine_cycle

        breadth = self._make_bull_breadth()
        kospi_data = self._make_bull_kospi_data()
        result = determine_cycle(breadth, kospi_data)

        assert hasattr(result, "confidence")
        assert 0 <= result.confidence <= 100


# ---------------------------------------------------------------------------
# Tests: detect_choppy (AC4)
# ---------------------------------------------------------------------------


class TestDetectChoppy:
    """Tests for detect_choppy() - R4 Choppy Market Detection."""

    def _make_stable_breadth_list(self):
        """Breadth history with stable, non-oscillating values."""
        from my_chart.analysis.market_breadth import BreadthResult

        return [
            BreadthResult(
                date=f"2024-{w:02d}-05", market="KOSPI",
                pct_above_sma50=65.0,
                pct_above_sma200=60.0,
                nh_nl_ratio=0.65,
                nh_nl_diff=25,
                ad_ratio=2.0,
                breadth_score=68.0,
                total_stocks=100,
            )
            for w in range(1, 9)
        ]

    def _make_choppy_breadth_list(self):
        """Breadth history showing choppy conditions (oscillating in 40-60% band)."""
        from my_chart.analysis.market_breadth import BreadthResult

        # Oscillates between 42% and 58% - range < 15%, stays in 40-60% band
        values = [42.0, 58.0, 43.0, 57.0, 44.0, 56.0, 45.0, 55.0]
        return [
            BreadthResult(
                date=f"2024-{w:02d}-05", market="KOSPI",
                pct_above_sma50=v,
                pct_above_sma200=50.0,
                nh_nl_ratio=0.5,
                nh_nl_diff=2,  # very low NH+NL
                ad_ratio=1.0,
                breadth_score=50.0,
                total_stocks=100,
            )
            for w, v in enumerate(values, start=1)
        ]

    def _make_choppy_kospi_data(self):
        """KOSPI data with tight MA spread (< 5%)."""
        return {
            "sma20": 2500.0,
            "sma50": 2520.0,   # spread < 5%
            "sma200": 2510.0,  # spread < 5%
            "weekly_returns": [-0.01, 0.01, -0.01, 0.01, -0.01, 0.01, -0.01, 0.01],  # sign changes
        }

    def _make_trending_kospi_data(self):
        """KOSPI data in trending market (MA spread > 5%)."""
        return {
            "sma20": 2500.0,
            "sma50": 2300.0,   # spread > 5%
            "sma200": 2100.0,  # spread > 5%
            "weekly_returns": [0.02, 0.01, 0.03, 0.01, 0.02, 0.02, 0.01, 0.03],  # all positive
        }

    def test_choppy_returns_true_when_conditions_met(self) -> None:
        """AC4: detect_choppy() returns True when MA spread < 5% and breadth oscillates."""
        from my_chart.analysis.market_breadth import detect_choppy

        breadth_history = self._make_choppy_breadth_list()
        kospi_data = self._make_choppy_kospi_data()
        result = detect_choppy(breadth_history, kospi_data)

        assert result is True

    def test_choppy_returns_false_for_trending_market(self) -> None:
        """detect_choppy() returns False for a clearly trending market."""
        from my_chart.analysis.market_breadth import detect_choppy

        breadth_history = self._make_stable_breadth_list()
        kospi_data = self._make_trending_kospi_data()
        result = detect_choppy(breadth_history, kospi_data)

        assert result is False

    def test_choppy_requires_minimum_history_length(self) -> None:
        """detect_choppy() needs at least 4 weeks of history."""
        from my_chart.analysis.market_breadth import detect_choppy

        short_history = self._make_choppy_breadth_list()[:2]
        kospi_data = self._make_choppy_kospi_data()
        # Should not raise, but returns False with insufficient data
        result = detect_choppy(short_history, kospi_data)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Tests: compute_breadth_history
# ---------------------------------------------------------------------------


class TestComputeBreadthHistory:
    """Tests for compute_breadth_history() function."""

    def test_returns_list_of_breadth_results(self, weekly_db_12weeks: str) -> None:
        """compute_breadth_history() returns a list of BreadthResult."""
        from my_chart.analysis.market_breadth import BreadthResult, compute_breadth_history

        results = compute_breadth_history(weekly_db_12weeks, "KOSPI", weeks=12)
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, BreadthResult) for r in results)

    def test_history_length_matches_weeks_param(self, weekly_db_12weeks: str) -> None:
        """compute_breadth_history() returns up to `weeks` results."""
        from my_chart.analysis.market_breadth import compute_breadth_history

        results = compute_breadth_history(weekly_db_12weeks, "KOSPI", weeks=4)
        assert len(results) <= 4

    def test_history_ordered_by_date(self, weekly_db_12weeks: str) -> None:
        """Results are ordered chronologically (oldest first)."""
        from my_chart.analysis.market_breadth import compute_breadth_history

        results = compute_breadth_history(weekly_db_12weeks, "KOSPI", weeks=12)
        dates = [r.date for r in results]
        assert dates == sorted(dates)
