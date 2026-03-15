"""Sector strength metrics and ranking engine.

Computes sector-level aggregated metrics from weekly DB and sector registry.
Ranks sectors by composite score.

Per SPEC-TOPDOWN-001A R7-R8.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from my_chart.analysis.stage_classifier import classify_stage, _compute_slope
from my_chart.registry import get_sector_registry

# Index names excluded from sector metrics
_INDEX_NAMES = frozenset({"KOSPI", "KOSDAQ"})

# 52-week high/low proximity thresholds
_NH_THRESHOLD = 0.02  # within 2% of MAX52

# Composite score weights per SPEC R8
_COMPOSITE_W_1W = 0.3
_COMPOSITE_W_1M = 0.4
_COMPOSITE_W_3M = 0.3

# RS top threshold per SPEC R7
_RS_TOP_THRESHOLD = 80.0

# Weeks to look back for rank_change comparison
_RANK_CHANGE_WEEKS = 4


@dataclass
class SectorRank:
    """Sector ranking result with all SPEC-required fields."""

    name: str                      # 산업명(대)
    stock_count: int
    sector_return_1w: float        # market-cap weighted avg 1W return (%)
    sector_return_1m: float        # market-cap weighted avg 1M return (%)
    sector_return_3m: float        # market-cap weighted avg 3M return (%)
    sector_excess_return_1w: float # sector - KOSPI 1W return
    sector_excess_return_1m: float # sector - KOSPI 1M return
    sector_excess_return_3m: float # sector - KOSPI 3M return
    sector_rs_avg: float           # avg RS_12M_Rating
    sector_rs_top_pct: float       # % stocks with RS >= 80
    sector_nh_pct: float           # % stocks at 52-week high
    sector_stage2_pct: float       # % stocks classified Stage 2
    composite_score: float         # 0-100 ranking score
    rank: int = 0
    rank_change: int = 0           # positive = improved, negative = declined


def _load_weekly_snapshot(
    conn: sqlite3.Connection, date: str
) -> dict[str, dict[str, Any]]:
    """Load weekly stock data for a given date, keyed by stock name."""
    rows = conn.execute(
        """SELECT sp.Name, sp.Close, sp.SMA10, sp.SMA40,
                  sp.SMA40_Trend_4M, sp.CHG_1W, sp.CHG_1M, sp.CHG_3M,
                  sp.Volume, sp.VolumeSMA10, sp.MAX52,
                  rs.RS_12M_Rating
           FROM stock_prices sp
           LEFT JOIN relative_strength rs
             ON sp.Name = rs.Name AND sp.Date = rs.Date
           WHERE sp.Date = ?""",
        (date,),
    ).fetchall()

    result: dict[str, dict[str, Any]] = {}
    for r in rows:
        name = r[0]
        sma40 = float(r[3] or 0.0)
        sma40_4w_ago = float(r[4] or 0.0)
        result[name] = {
            "Close": r[1],
            "SMA10": r[2],
            "SMA40": sma40,
            "SMA40_slope": _compute_slope(sma40, sma40_4w_ago),
            "CHG_1W": r[5],
            "CHG_1M": r[6],
            "CHG_3M": r[7],
            "Volume": r[8],
            "VolumeSMA10": r[9],
            "MAX52": r[10],
            "RS_12M_Rating": r[11],
        }
    return result


def _load_kospi_returns(conn: sqlite3.Connection, date: str) -> dict[str, float]:
    """Load KOSPI index returns for the given date."""
    row = conn.execute(
        "SELECT CHG_1W, CHG_1M, CHG_3M FROM stock_prices WHERE Name = 'KOSPI' AND Date = ?",
        (date,),
    ).fetchone()
    if not row:
        return {"chg_1w": 0.0, "chg_1m": 0.0, "chg_3m": 0.0}
    return {
        "chg_1w": float(row[0] or 0.0) * 100,  # convert to %
        "chg_1m": float(row[1] or 0.0) * 100,
        "chg_3m": float(row[2] or 0.0) * 100,
    }


def _normalize_list(values: list[float]) -> list[float]:
    """Min-max normalize a list of values to 0-100 range."""
    if not values:
        return []
    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        return [50.0] * len(values)
    return [(v - min_v) / (max_v - min_v) * 100 for v in values]


def _compute_sector_metrics(
    sector_name: str,
    stock_names: list[str],
    snapshot: dict[str, dict[str, Any]],
    kospi_returns: dict[str, float],
) -> SectorRank | None:
    """Compute all metrics for a single sector.

    Returns None if no valid stocks found in sector.
    """
    # Filter to stocks present in snapshot
    sector_stocks = [
        snapshot[name] for name in stock_names
        if name in snapshot and name not in _INDEX_NAMES
    ]

    if not sector_stocks:
        return None

    n = len(sector_stocks)

    # Simple average (equal-weight) returns - % scale
    # @MX:NOTE: [AUTO] CHG values in weekly DB are decimal (0.02 = 2%), convert to %
    returns_1w = []
    returns_1m = []
    returns_3m = []
    rs_values = []
    nh_count = 0
    stage2_count = 0

    for s in sector_stocks:
        chg_1w = float(s.get("CHG_1W") or 0.0) * 100  # decimal → %
        chg_1m = float(s.get("CHG_1M") or 0.0) * 100
        chg_3m = float(s.get("CHG_3M") or 0.0) * 100
        rs = float(s.get("RS_12M_Rating") or 0.0)
        close = float(s.get("Close") or 0.0)
        max52 = float(s.get("MAX52") or 0.0)

        returns_1w.append(chg_1w)
        returns_1m.append(chg_1m)
        returns_3m.append(chg_3m)
        rs_values.append(rs)

        # 52-week high: Close within 2% of MAX52
        if max52 > 0 and close >= max52 * (1 - _NH_THRESHOLD):
            nh_count += 1

        # Stage classification
        stage_row = {**s, "Name": "tmp", "RS_12M_Rating": rs}
        stage_result = classify_stage(stage_row)
        if stage_result.stage == 2:
            stage2_count += 1

    avg_1w = sum(returns_1w) / n
    avg_1m = sum(returns_1m) / n
    avg_3m = sum(returns_3m) / n
    rs_avg = sum(rs_values) / n if rs_values else 0.0

    # RS top % (stocks with RS >= 80)
    rs_top_count = sum(1 for r in rs_values if r >= _RS_TOP_THRESHOLD)
    rs_top_pct = rs_top_count / n * 100

    # 52W high % and Stage 2 %
    nh_pct = nh_count / n * 100
    stage2_pct = stage2_count / n * 100

    # Excess returns vs KOSPI
    excess_1w = avg_1w - kospi_returns["chg_1w"]
    excess_1m = avg_1m - kospi_returns["chg_1m"]
    excess_3m = avg_3m - kospi_returns["chg_3m"]

    return SectorRank(
        name=sector_name,
        stock_count=n,
        sector_return_1w=round(avg_1w, 4),
        sector_return_1m=round(avg_1m, 4),
        sector_return_3m=round(avg_3m, 4),
        sector_excess_return_1w=round(excess_1w, 4),
        sector_excess_return_1m=round(excess_1m, 4),
        sector_excess_return_3m=round(excess_3m, 4),
        sector_rs_avg=round(rs_avg, 2),
        sector_rs_top_pct=round(rs_top_pct, 2),
        sector_nh_pct=round(nh_pct, 2),
        sector_stage2_pct=round(stage2_pct, 2),
        composite_score=0.0,  # computed after normalization
    )


def compute_sector_ranking(db_path: str, date: str) -> list[SectorRank]:
    """Compute sector ranking for all sectors on a given date.

    Per SPEC R7-R8:
    - R7: sector_return, excess_return, rs_avg, rs_top_pct, nh_pct, stage2_pct
    - R8: composite = 0.3 * excess_1w_norm + 0.4 * excess_1m_norm + 0.3 * excess_3m_norm

    Also computes rank_change by comparing to 4-week-ago ranking.

    Args:
        db_path: Path to weekly SQLite database file.
        date: Date string in YYYY-MM-DD format.

    Returns:
        List of SectorRank ordered by composite_score descending (rank 1 = best).
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        snapshot = _load_weekly_snapshot(conn, date)
        kospi_returns = _load_kospi_returns(conn, date)

        # Get previous date for rank_change (4 weeks ago)
        prev_date_row = conn.execute(
            """SELECT DISTINCT Date FROM stock_prices
               WHERE Date < ? AND Name NOT IN ('KOSPI', 'KOSDAQ')
               ORDER BY Date DESC
               LIMIT 1 OFFSET ?""",
            (date, _RANK_CHANGE_WEEKS - 1),
        ).fetchone()
        prev_date = prev_date_row[0] if prev_date_row else None
        prev_snapshot = _load_weekly_snapshot(conn, prev_date) if prev_date else {}
        prev_kospi = _load_kospi_returns(conn, prev_date) if prev_date else {
            "chg_1w": 0.0, "chg_1m": 0.0, "chg_3m": 0.0
        }
    finally:
        conn.close()

    # Load sector registry to map stock names to sectors
    df_sector = get_sector_registry()
    sector_to_stocks: dict[str, list[str]] = {}
    for _, row in df_sector.iterrows():
        name = str(row["Name"])
        sector = str(row.get("산업명(대)") or "Unknown")
        if sector not in sector_to_stocks:
            sector_to_stocks[sector] = []
        sector_to_stocks[sector].append(name)

    # Compute current metrics for each sector
    current_results: list[SectorRank] = []
    for sector_name, stock_names in sector_to_stocks.items():
        metrics = _compute_sector_metrics(sector_name, stock_names, snapshot, kospi_returns)
        if metrics:
            current_results.append(metrics)

    if not current_results:
        return []

    # Compute composite scores via normalization
    excess_1w_values = [r.sector_excess_return_1w for r in current_results]
    excess_1m_values = [r.sector_excess_return_1m for r in current_results]
    excess_3m_values = [r.sector_excess_return_3m for r in current_results]

    norm_1w = _normalize_list(excess_1w_values)
    norm_1m = _normalize_list(excess_1m_values)
    norm_3m = _normalize_list(excess_3m_values)

    for i, r in enumerate(current_results):
        r.composite_score = round(
            _COMPOSITE_W_1W * norm_1w[i]
            + _COMPOSITE_W_1M * norm_1m[i]
            + _COMPOSITE_W_3M * norm_3m[i],
            2,
        )

    # Sort by composite score descending and assign ranks
    current_results.sort(key=lambda r: r.composite_score, reverse=True)
    current_rank_by_sector: dict[str, int] = {}
    for rank_i, r in enumerate(current_results, start=1):
        r.rank = rank_i
        current_rank_by_sector[r.name] = rank_i

    # Compute rank_change if previous data available
    if prev_snapshot:
        prev_results: list[SectorRank] = []
        for sector_name, stock_names in sector_to_stocks.items():
            metrics = _compute_sector_metrics(sector_name, stock_names, prev_snapshot, prev_kospi)
            if metrics:
                prev_results.append(metrics)

        if prev_results:
            prev_excess_1w = [r.sector_excess_return_1w for r in prev_results]
            prev_excess_1m = [r.sector_excess_return_1m for r in prev_results]
            prev_excess_3m = [r.sector_excess_return_3m for r in prev_results]
            pn1w = _normalize_list(prev_excess_1w)
            pn1m = _normalize_list(prev_excess_1m)
            pn3m = _normalize_list(prev_excess_3m)
            for i, r in enumerate(prev_results):
                r.composite_score = (
                    _COMPOSITE_W_1W * pn1w[i]
                    + _COMPOSITE_W_1M * pn1m[i]
                    + _COMPOSITE_W_3M * pn3m[i]
                )
            prev_results.sort(key=lambda r: r.composite_score, reverse=True)
            prev_rank_by_sector = {r.name: rank_i for rank_i, r in enumerate(prev_results, start=1)}

            for r in current_results:
                prev_rank = prev_rank_by_sector.get(r.name, r.rank)
                r.rank_change = prev_rank - r.rank  # positive = improved rank

    return current_results


def compute_sector_history(
    db_path: str,
    weeks: int = 12,
) -> list[list[SectorRank]]:
    """Compute sector ranking for each of the last N weeks.

    Args:
        db_path: Path to weekly SQLite database file.
        weeks: Number of weeks of history.

    Returns:
        List of sector ranking lists, ordered chronologically.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        date_rows = conn.execute(
            """SELECT DISTINCT Date FROM stock_prices
               WHERE Name NOT IN ('KOSPI', 'KOSDAQ')
               ORDER BY Date DESC
               LIMIT ?""",
            (weeks,),
        ).fetchall()
    finally:
        conn.close()

    if not date_rows:
        return []

    dates = sorted(r[0] for r in date_rows)
    return [compute_sector_ranking(db_path, date) for date in dates]
