"""Specification tests for my_chart/analysis/stage_classifier.py.

Tests are written first (RED phase) to define expected behavior per SPEC R5, R6.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures: in-memory weekly DB for stage classification
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


def _make_full_weekly_row(
    name: str,
    date: str,
    close: float = 100.0,
    sma10: float = 95.0,
    sma40: float = 90.0,
    chg_1w: float = 0.02,
    chg_1m: float = 0.05,
    volume: float = 1_000_000.0,
    volume_sma10: float = 800_000.0,
    sma40_trend_4m: float = 88.0,  # 4-week-ago SMA40 for slope calc
) -> tuple:
    """Build a 32-element weekly row tuple."""
    return (
        name, date,
        close * 0.99, close * 1.01, close * 0.98, close,
        volume, volume_sma10,
        chg_1w, chg_1m, 0.08, 0.12, 0.20, 0.25, 0.30,
        sma10, 92.0, sma40,
        sma40_trend_4m, sma40 * 0.98, sma40 * 0.97, sma40 * 0.96,  # SMA40_Trend 1M..4M
        close * 1.05, close * 1.2, close * 0.7, close - close * 0.7,
        50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 1.1,
    )


# ---------------------------------------------------------------------------
# Unit tests: classify_stage() with dict input
# ---------------------------------------------------------------------------


class TestClassifyStageUnit:
    """Unit tests for classify_stage() - R5 Stage Classification Engine."""

    def _make_stock_row(
        self,
        close: float = 100.0,
        sma10: float = 90.0,   # proxy for SMA50
        sma40: float = 85.0,   # proxy for SMA200
        sma40_4w_ago: float = 83.0,
        rs_12m: float = 75.0,
        chg_1m: float = 0.05,
        volume: float = 1_000_000.0,
        volume_sma10: float = 800_000.0,
    ) -> dict:
        """Build a stock row dict for classify_stage."""
        sma40_slope = (sma40 - sma40_4w_ago) / sma40_4w_ago if sma40_4w_ago else 0.0
        return {
            "Name": "TestStock",
            "Date": "2024-01-05",
            "Close": close,
            "SMA10": sma10,
            "SMA40": sma40,
            "SMA40_slope": sma40_slope,
            "RS_12M_Rating": rs_12m,
            "CHG_1M": chg_1m,
            "Volume": volume,
            "VolumeSMA10": volume_sma10,
        }

    def test_stage2_strong_when_above_both_smas_high_rs(self) -> None:
        """AC5: classify_stage() correctly classifies Stage 2 Strong.

        Stage 2 Strong: Close > SMA50_proxy AND Close > SMA200_proxy
                       AND SMA50 > SMA200 AND SMA200_slope > 0.5%
                       AND RS_12M_Rating > 60.
        """
        from my_chart.analysis.stage_classifier import classify_stage

        row = self._make_stock_row(
            close=100.0,
            sma10=90.0,    # Close > SMA10 ✓
            sma40=85.0,    # Close > SMA40 ✓, SMA10 > SMA40 ✓
            sma40_4w_ago=84.0,  # slope = (85-84)/84 ≈ 1.19% > 0.5% ✓
            rs_12m=75.0,   # RS > 60 ✓
        )
        result = classify_stage(row)
        assert result.stage == 2
        assert result.detail == "Stage 2 Strong"

    def test_stage2_weak_when_above_both_smas_low_rs(self) -> None:
        """classify_stage() returns Stage 2 Weak when RS <= 60."""
        from my_chart.analysis.stage_classifier import classify_stage

        row = self._make_stock_row(
            close=100.0,
            sma10=90.0,
            sma40=85.0,
            sma40_4w_ago=84.0,
            rs_12m=50.0,   # RS <= 60 → Weak
        )
        result = classify_stage(row)
        assert result.stage == 2
        assert result.detail == "Stage 2 Weak"

    def test_stage4_when_below_both_smas_declining(self) -> None:
        """AC6: classify_stage() correctly classifies Stage 4.

        Stage 4 (Decline): Close < SMA50_proxy AND Close < SMA200_proxy
                           AND SMA200_slope < -1%.
        """
        from my_chart.analysis.stage_classifier import classify_stage

        row = self._make_stock_row(
            close=80.0,
            sma10=95.0,    # Close < SMA10 ✓
            sma40=100.0,   # Close < SMA40 ✓
            sma40_4w_ago=102.0,  # slope = (100-102)/102 ≈ -1.96% < -1% ✓
            rs_12m=20.0,
        )
        result = classify_stage(row)
        assert result.stage == 4

    def test_stage1_when_flat_sma200_price_near_sma200(self) -> None:
        """classify_stage() returns Stage 1 for base/accumulation phase.

        Stage 1 (Base): abs(SMA200_slope) < 0.5% AND Close within SMA200 ±5%.
        """
        from my_chart.analysis.stage_classifier import classify_stage

        # SMA40 very flat, Close near SMA40
        row = self._make_stock_row(
            close=100.0,
            sma10=100.0,   # Close at SMA10 (not clearly above)
            sma40=99.0,    # Close near SMA40 (within 2%)
            sma40_4w_ago=98.8,  # slope ≈ 0.2% → flat
            rs_12m=40.0,
        )
        result = classify_stage(row)
        assert result.stage == 1

    def test_stage3_when_flattening_sma200_declining_sma50(self) -> None:
        """classify_stage() returns Stage 3 for topping pattern.

        Stage 3 (Top): Close near SMA200 (±3%) AND SMA200_slope flattening
                       AND SMA50_slope < 0.
        """
        from my_chart.analysis.stage_classifier import classify_stage

        # Close near SMA40 but SMA10 declining (SMA10 < SMA40)
        row = self._make_stock_row(
            close=100.0,
            sma10=98.0,    # SMA10 < SMA40 (declining 50-day proxy)
            sma40=100.5,   # Close near SMA40 (within 3%)
            sma40_4w_ago=100.0,  # slope = 0.5% (flattening)
            rs_12m=35.0,
        )
        result = classify_stage(row)
        assert result.stage == 3

    def test_stage4_has_priority_over_stage2(self) -> None:
        """Stage 4 conditions take priority over Stage 2 in classification."""
        from my_chart.analysis.stage_classifier import classify_stage

        # Contradictory signals → Stage 4 should win (lowest priority wins in SPEC)
        row = self._make_stock_row(
            close=80.0,
            sma10=95.0,    # Close < SMA10
            sma40=100.0,   # Close < SMA40
            sma40_4w_ago=102.0,  # slope < -1% → Stage 4
            rs_12m=80.0,   # High RS (would suggest stage 2 if conditions met)
        )
        result = classify_stage(row)
        assert result.stage == 4

    def test_result_has_required_fields(self) -> None:
        """StageResult has all required fields."""
        from my_chart.analysis.stage_classifier import classify_stage

        row = self._make_stock_row()
        result = classify_stage(row)
        assert hasattr(result, "stage")
        assert hasattr(result, "detail")
        assert result.stage in {1, 2, 3, 4}


# ---------------------------------------------------------------------------
# Integration tests: classify_all() with weekly DB
# ---------------------------------------------------------------------------


@pytest.fixture
def stage_weekly_db(tmp_path: Path) -> str:
    """Weekly DB with stocks in known stages for integration testing."""
    db_path = str(tmp_path / "test_stage_weekly.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_WEEKLY_DDL)
    conn.execute(_RS_DDL)

    test_date = "2024-01-05"

    # Stage 2 Strong stock
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_full_weekly_row(
            "Stage2Stock", test_date,
            close=100.0, sma10=90.0, sma40=85.0, sma40_trend_4m=84.0,
            chg_1m=0.05, volume=2_000_000.0, volume_sma10=800_000.0,
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
        ("Stage2Stock", test_date, 75.0),
    )

    # Stage 4 stock
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_full_weekly_row(
            "Stage4Stock", test_date,
            close=80.0, sma10=95.0, sma40=100.0, sma40_trend_4m=102.0,
            chg_1m=-0.05,
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
        ("Stage4Stock", test_date, 20.0),
    )

    # KOSPI index (should be excluded)
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_full_weekly_row("KOSPI", test_date, close=2500.0, sma10=2400.0, sma40=2300.0),
    )

    conn.commit()
    conn.close()
    return db_path


class TestClassifyAll:
    """Tests for classify_all() function."""

    def test_returns_list_of_stage_results(self, stage_weekly_db: str) -> None:
        """classify_all() returns a list of StageResult objects."""
        from my_chart.analysis.stage_classifier import StageResult, classify_all

        results = classify_all(stage_weekly_db, "2024-01-05")
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, StageResult) for r in results)

    def test_excludes_index_stocks(self, stage_weekly_db: str) -> None:
        """classify_all() excludes KOSPI/KOSDAQ index stocks."""
        from my_chart.analysis.stage_classifier import classify_all

        results = classify_all(stage_weekly_db, "2024-01-05")
        names = [r.name for r in results]
        assert "KOSPI" not in names
        assert "KOSDAQ" not in names

    def test_correct_stage_for_stage2_stock(self, stage_weekly_db: str) -> None:
        """classify_all() correctly classifies Stage 2 stock in DB."""
        from my_chart.analysis.stage_classifier import classify_all

        results = classify_all(stage_weekly_db, "2024-01-05")
        stage2_results = [r for r in results if r.name == "Stage2Stock"]
        assert len(stage2_results) == 1
        assert stage2_results[0].stage == 2

    def test_correct_stage_for_stage4_stock(self, stage_weekly_db: str) -> None:
        """classify_all() correctly classifies Stage 4 stock in DB."""
        from my_chart.analysis.stage_classifier import classify_all

        results = classify_all(stage_weekly_db, "2024-01-05")
        stage4_results = [r for r in results if r.name == "Stage4Stock"]
        assert len(stage4_results) == 1
        assert stage4_results[0].stage == 4


# ---------------------------------------------------------------------------
# Integration tests: screen_stage2_entry() (AC7)
# ---------------------------------------------------------------------------


@pytest.fixture
def entry_screen_db(tmp_path: Path) -> str:
    """Weekly DB with stocks that do/don't meet Stage 2 entry criteria."""
    db_path = str(tmp_path / "test_entry_screen.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_WEEKLY_DDL)
    conn.execute(_RS_DDL)

    test_date = "2024-01-05"

    # Stock A: Meets ALL 6 criteria → should be included
    # 1. Stage 2 ✓ (Close > SMA10 > SMA40, slope > 0.5%)
    # 2. Close > SMA10 ✓
    # 3. SMA10 > SMA40 (Golden Cross) ✓
    # 4. Volume > VolumeSMA10 * 1.5 ✓
    # 5. RS_12M_Rating >= 70 ✓
    # 6. CHG_1M > 0 ✓
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_full_weekly_row(
            "GoodStock", test_date,
            close=100.0, sma10=90.0, sma40=85.0, sma40_trend_4m=84.0,
            chg_1m=0.06,
            volume=1_500_000.0,    # Volume > VolumeSMA10 * 1.5
            volume_sma10=800_000.0,
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
        ("GoodStock", test_date, 75.0),  # RS >= 70 ✓
    )

    # Stock B: Low RS → should be excluded (criteria 5 fails)
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_full_weekly_row(
            "LowRSStock", test_date,
            close=100.0, sma10=90.0, sma40=85.0, sma40_trend_4m=84.0,
            chg_1m=0.06,
            volume=1_500_000.0,
            volume_sma10=800_000.0,
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
        ("LowRSStock", test_date, 60.0),  # RS < 70 → excluded
    )

    # Stock C: Negative 1M return → should be excluded (criteria 6 fails)
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_full_weekly_row(
            "NegReturnStock", test_date,
            close=100.0, sma10=90.0, sma40=85.0, sma40_trend_4m=84.0,
            chg_1m=-0.02,  # Negative 1M return → excluded
            volume=1_500_000.0,
            volume_sma10=800_000.0,
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
        ("NegReturnStock", test_date, 75.0),
    )

    # Stock D: Low volume → should be excluded (criteria 4 fails)
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_full_weekly_row(
            "LowVolStock", test_date,
            close=100.0, sma10=90.0, sma40=85.0, sma40_trend_4m=84.0,
            chg_1m=0.06,
            volume=900_000.0,   # Volume < VolumeSMA10 * 1.5
            volume_sma10=800_000.0,
        ),
    )
    conn.execute(
        "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
        ("LowVolStock", test_date, 75.0),
    )

    conn.commit()
    conn.close()
    return db_path


class TestScreenStage2Entry:
    """Tests for screen_stage2_entry() - R6 Stage 2 Entry Screening (AC7)."""

    def test_returns_only_stocks_meeting_all_6_conditions(self, entry_screen_db: str) -> None:
        """AC7: screen_stage2_entry() filters only stocks meeting all 6 entry conditions."""
        from my_chart.analysis.stage_classifier import screen_stage2_entry

        results = screen_stage2_entry(entry_screen_db, "2024-01-05")
        names = [r["name"] for r in results]

        assert "GoodStock" in names
        assert "LowRSStock" not in names      # fails RS criterion
        assert "NegReturnStock" not in names  # fails CHG_1M criterion
        assert "LowVolStock" not in names     # fails Volume criterion

    def test_returns_list_of_dicts(self, entry_screen_db: str) -> None:
        """screen_stage2_entry() returns list of dicts with stock info."""
        from my_chart.analysis.stage_classifier import screen_stage2_entry

        results = screen_stage2_entry(entry_screen_db, "2024-01-05")
        assert isinstance(results, list)
        if results:
            assert isinstance(results[0], dict)
            assert "name" in results[0]
            assert "stage" in results[0]

    def test_returns_required_fields_per_spec(self, entry_screen_db: str) -> None:
        """Each result dict contains fields needed for API response."""
        from my_chart.analysis.stage_classifier import screen_stage2_entry

        results = screen_stage2_entry(entry_screen_db, "2024-01-05")
        if results:
            r = results[0]
            assert "name" in r
            assert "stage" in r
            assert "rs_12m" in r
            assert "chg_1m" in r
            assert "volume_ratio" in r
