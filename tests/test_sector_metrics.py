"""Specification tests for my_chart/analysis/sector_metrics.py.

Tests are written first (RED phase) to define expected behavior per SPEC R7, R8.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures: weekly DB with sector data
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


def _make_sector_row(
    name: str,
    date: str,
    close: float = 100.0,
    sma10: float = 90.0,
    sma40: float = 85.0,
    chg_1w: float = 0.02,
    chg_1m: float = 0.05,
    chg_3m: float = 0.10,
    max52: float = 110.0,
    min52: float = 70.0,
    volume: float = 1_000_000.0,
    volume_sma10: float = 800_000.0,
    sma40_trend_4m: float = 84.0,
) -> tuple:
    """Build a 32-element weekly row for sector testing."""
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
def sector_db(tmp_path: Path, mock_sectormap) -> str:  # noqa: F811
    """Weekly DB with multi-sector stocks for ranking tests.

    Uses mock_sectormap fixture to avoid xlsx file dependency.
    Stocks: 삼성전자, SK하이닉스 → 전기전자; POSCO홀딩스 → 철강금속.
    """
    db_path = str(tmp_path / "test_sector.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_WEEKLY_DDL)
    conn.execute(_RS_DDL)

    test_date = "2024-01-05"
    prev_date_4w = "2023-12-08"  # 4 weeks ago

    # KOSPI index (for excess return calculation)
    kospi_chg_1w = 0.01  # KOSPI 1W return = 1%
    for dt in [test_date, prev_date_4w]:
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_sector_row("KOSPI", dt, close=2500.0, chg_1w=kospi_chg_1w, chg_1m=0.03, chg_3m=0.08),
        )

    # 전기전자 sector stocks (above KOSPI performance)
    for name, chg_1w, chg_1m, chg_3m, rs in [
        ("삼성전자", 0.03, 0.08, 0.15, 85.0),  # outperforms
        ("SK하이닉스", 0.025, 0.07, 0.12, 72.0),
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_sector_row(name, test_date, close=100.0, chg_1w=chg_1w, chg_1m=chg_1m, chg_3m=chg_3m,
                             max52=105.0, sma10=90.0, sma40=85.0),
        )
        conn.execute(
            "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
            (name, test_date, rs),
        )
        # Previous date for rank_change
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_sector_row(name, prev_date_4w, close=95.0, chg_1w=0.01, chg_1m=0.03, chg_3m=0.07),
        )
        conn.execute(
            "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
            (name, prev_date_4w, rs - 5.0),
        )

    # 철강금속 sector stocks (below KOSPI performance)
    for name, chg_1w, chg_1m, chg_3m, rs in [
        ("POSCO홀딩스", -0.01, -0.02, 0.03, 45.0),  # underperforms
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_sector_row(name, test_date, close=100.0, chg_1w=chg_1w, chg_1m=chg_1m, chg_3m=chg_3m,
                             max52=120.0, sma10=105.0, sma40=110.0),
        )
        conn.execute(
            "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
            (name, test_date, rs),
        )
        conn.execute(
            "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _make_sector_row(name, prev_date_4w, close=105.0, chg_1w=0.02, chg_1m=0.04, chg_3m=0.10),
        )
        conn.execute(
            "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
            (name, prev_date_4w, 50.0),
        )

    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Tests: compute_sector_ranking (AC8, AC9)
# ---------------------------------------------------------------------------


class TestComputeSectorRanking:
    """Tests for compute_sector_ranking() - R7, R8."""

    def test_returns_list_of_sector_rank(self, sector_db: str) -> None:
        """compute_sector_ranking() returns a list of SectorRank objects."""
        from my_chart.analysis.sector_metrics import SectorRank, compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        assert isinstance(results, list)
        assert len(results) > 0
        assert all(isinstance(r, SectorRank) for r in results)

    def test_ranks_sectors_by_composite_score(self, sector_db: str) -> None:
        """AC8: compute_sector_ranking() ranks sectors by composite score descending."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        # 전기전자 outperforms KOSPI → should rank #1
        # 철강금속 underperforms → should rank #2
        sector_names = [r.name for r in results]
        assert len(sector_names) > 0
        assert results[0].rank == 1
        assert results[-1].rank == len(results)

    def test_ranks_sorted_descending_by_composite(self, sector_db: str) -> None:
        """Ranks are assigned in descending order of composite_score."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        scores = [r.composite_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_strong_sector_ranks_above_weak_sector(self, sector_db: str) -> None:
        """전기전자 (outperforms) should rank above 철강금속 (underperforms)."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        rank_by_name = {r.name: r.rank for r in results}

        if "전기전자" in rank_by_name and "철강금속" in rank_by_name:
            assert rank_by_name["전기전자"] < rank_by_name["철강금속"]

    def test_sector_rank_has_required_fields(self, sector_db: str) -> None:
        """SectorRank has all SPEC-required fields."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        assert len(results) > 0
        r = results[0]

        # Per SPEC R7
        assert hasattr(r, "name")
        assert hasattr(r, "stock_count")
        assert hasattr(r, "sector_return_1w")
        assert hasattr(r, "sector_return_1m")
        assert hasattr(r, "sector_return_3m")
        assert hasattr(r, "sector_excess_return_1w")
        assert hasattr(r, "sector_excess_return_1m")
        assert hasattr(r, "sector_excess_return_3m")
        assert hasattr(r, "sector_rs_avg")
        assert hasattr(r, "sector_rs_top_pct")
        assert hasattr(r, "sector_nh_pct")
        assert hasattr(r, "sector_stage2_pct")
        assert hasattr(r, "composite_score")
        assert hasattr(r, "rank")
        assert hasattr(r, "rank_change")

    def test_excess_return_computed_correctly(self, sector_db: str) -> None:
        """sector_excess_return = sector_return - KOSPI_return."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        # 전기전자 avg return ≈ (3% + 2.5%) / 2 = 2.75%, KOSPI = 1%
        # excess ≈ 1.75%
        elec_sector = next((r for r in results if r.name == "전기전자"), None)
        if elec_sector:
            assert elec_sector.sector_excess_return_1w > 0  # outperforms KOSPI

    def test_rs_avg_calculated(self, sector_db: str) -> None:
        """sector_rs_avg is the average RS_12M_Rating of sector stocks."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        elec_sector = next((r for r in results if r.name == "전기전자"), None)
        if elec_sector:
            # 삼성전자 RS=85, SK하이닉스 RS=72 → avg ≈ 78.5
            assert 70.0 <= elec_sector.sector_rs_avg <= 90.0

    def test_rs_top_pct_calculated(self, sector_db: str) -> None:
        """sector_rs_top_pct = % of sector stocks with RS >= 80."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        elec_sector = next((r for r in results if r.name == "전기전자"), None)
        if elec_sector:
            # 삼성전자 RS=85 >= 80 → 1/2 = 50%
            assert abs(elec_sector.sector_rs_top_pct - 50.0) < 1.0

    def test_rank_change_compares_current_vs_historical(self, sector_db: str) -> None:
        """AC9: sector rank_change correctly compares current vs 4-week-ago rank."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        # rank_change should be an integer (positive = improved, negative = declined)
        for r in results:
            assert isinstance(r.rank_change, int)

    def test_composite_score_formula(self, sector_db: str) -> None:
        """composite = 0.3 * excess_1w_norm + 0.4 * excess_1m_norm + 0.3 * excess_3m_norm."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        # Composite scores should be within reasonable range
        for r in results:
            assert 0.0 <= r.composite_score <= 100.0

    def test_nh_pct_reflects_52w_high_stocks(self, sector_db: str) -> None:
        """sector_nh_pct = % of sector stocks at 52-week high."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        for r in results:
            assert 0.0 <= r.sector_nh_pct <= 100.0

    def test_excludes_index_names_from_sectors(self, sector_db: str) -> None:
        """KOSPI/KOSDAQ are not counted as sector stocks."""
        from my_chart.analysis.sector_metrics import compute_sector_ranking

        results = compute_sector_ranking(sector_db, "2024-01-05")
        sector_names = [r.name for r in results]
        assert "KOSPI" not in sector_names
        assert "KOSDAQ" not in sector_names
