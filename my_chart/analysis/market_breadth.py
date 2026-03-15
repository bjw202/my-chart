"""Market breadth calculation engine.

Computes breadth indicators (pct_above_sma50, nh_nl_ratio, etc.) from weekly DB.
Determines market cycle phase (Bull/Sideways/Bear) based on 6 criteria.
Detects choppy market conditions.

Per SPEC-TOPDOWN-001A R1-R4.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

# Index names excluded from breadth calculations
_INDEX_NAMES = frozenset({"KOSPI", "KOSDAQ"})

# Proximity threshold for 52-week high/low detection (within 2%)
_NH_THRESHOLD = 0.02
_NL_THRESHOLD = 0.02

# Stage criteria thresholds per SPEC R3
_BULL_PCT_SMA50 = 60.0
_BEAR_PCT_SMA50 = 40.0
_BULL_PCT_SMA200 = 55.0
_BEAR_PCT_SMA200 = 40.0
_BULL_NH_NL_RATIO = 0.6
_BEAR_NH_NL_RATIO = 0.4
_BULL_BREADTH_SCORE = 65.0
_BEAR_BREADTH_SCORE = 35.0

# Choppy detection thresholds per SPEC R4
_CHOPPY_MA_SPREAD_MAX = 0.05    # < 5% spread between SMA20/50/200
_CHOPPY_BREADTH_RANGE_MAX = 15.0  # breadth oscillation range < 15%p
_CHOPPY_SIGN_CHANGES_MIN = 5    # >= 5 sign changes in 8 weeks
_CHOPPY_NH_NL_PCT_MAX = 0.05    # NH + NL total < 5% of universe
_CHOPPY_MIN_CONDITIONS = 3      # at least 3 conditions met

# Breadth composite weights per SPEC R2
_COMPOSITE_WEIGHTS = (0.25, 0.25, 0.25, 0.25)


@dataclass
class BreadthResult:
    """Market breadth indicators for a single date and market."""

    date: str
    market: str
    pct_above_sma50: float       # % stocks with Close > SMA10 (proxy)
    pct_above_sma200: float      # % stocks with Close > SMA40 (proxy)
    nh_nl_ratio: float           # new highs / (new highs + new lows)
    nh_nl_diff: int              # new highs - new lows
    ad_ratio: float              # advancing / declining count
    breadth_score: float = 0.0  # composite 0-100
    total_stocks: int = 0       # number of individual stocks counted


@dataclass
class CriteriaDatum:
    """Single criterion evaluation result."""

    name: str
    value: float
    direction: str  # "bull", "sideways", "bear"


@dataclass
class CycleResult:
    """Market cycle phase determination result."""

    phase: str                              # "bull", "sideways", "bear"
    choppy: bool = False
    criteria: list[CriteriaDatum] = field(default_factory=list)
    confidence: int = 0                    # 0-100


def _query_stocks_at_date(
    conn: sqlite3.Connection, date: str
) -> list[dict[str, Any]]:
    """Load all individual stock rows for a given date, excluding indices."""
    rows = conn.execute(
        """SELECT Name, Close, SMA10, SMA40, CHG_1W, MAX52, min52, Volume, VolumeSMA10
           FROM stock_prices
           WHERE Date = ?
           ORDER BY Name""",
        (date,),
    ).fetchall()

    result = []
    for r in rows:
        name = r[0]
        if name in _INDEX_NAMES:
            continue
        result.append({
            "Name": name,
            "Close": r[1],
            "SMA10": r[2],
            "SMA40": r[3],
            "CHG_1W": r[4],
            "MAX52": r[5],
            "min52": r[6],
            "Volume": r[7],
            "VolumeSMA10": r[8],
        })
    return result


def _query_index_at_date(
    conn: sqlite3.Connection, index_name: str, date: str
) -> dict[str, Any] | None:
    """Load a single index row (KOSPI or KOSDAQ) for a date."""
    row = conn.execute(
        """SELECT Close, SMA10, SMA40, CHG_1W
           FROM stock_prices
           WHERE Name = ? AND Date = ?""",
        (index_name, date),
    ).fetchone()
    if not row:
        return None
    return {
        "Close": row[0],
        "SMA10": row[1],
        "SMA40": row[2],
        "CHG_1W": row[3],
    }


def _safe_ratio(numerator: float, denominator: float, default: float = 0.5) -> float:
    """Compute ratio safely, returning default when denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def compute_breadth(db_path: str, market: str, date: str) -> BreadthResult:
    """Compute market breadth indicators for a given market and date.

    Uses weekly DB:
    - SMA10 as ~50-day SMA proxy
    - SMA40 as ~200-day SMA proxy
    - MAX52 / min52 for 52-week high/low detection

    Args:
        db_path: Path to weekly SQLite database file.
        market: "KOSPI" or "KOSDAQ".
        date: Date string in YYYY-MM-DD format.

    Returns:
        BreadthResult with all computed indicators.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        stocks = _query_stocks_at_date(conn, date)
    finally:
        conn.close()

    if not stocks:
        return BreadthResult(
            date=date, market=market,
            pct_above_sma50=0.0, pct_above_sma200=0.0,
            nh_nl_ratio=0.5, nh_nl_diff=0, ad_ratio=1.0,
            total_stocks=0,
        )

    n = len(stocks)
    above_sma50 = 0
    above_sma200 = 0
    new_highs = 0
    new_lows = 0
    advancing = 0
    declining = 0

    for s in stocks:
        close = s["Close"] or 0.0
        sma10 = s["SMA10"] or 0.0
        sma40 = s["SMA40"] or 0.0
        max52 = s["MAX52"] or 0.0
        min52 = s["min52"] or 0.0
        chg_1w = s["CHG_1W"]

        if sma10 > 0 and close > sma10:
            above_sma50 += 1
        if sma40 > 0 and close > sma40:
            above_sma200 += 1

        # 52-week high: Close >= MAX52 * (1 - threshold)
        if max52 > 0 and close >= max52 * (1 - _NH_THRESHOLD):
            new_highs += 1
        # 52-week low: Close <= min52 * (1 + threshold)
        if min52 > 0 and close <= min52 * (1 + _NL_THRESHOLD):
            new_lows += 1

        if chg_1w is not None:
            if chg_1w > 0:
                advancing += 1
            elif chg_1w < 0:
                declining += 1

    pct_above_sma50 = (above_sma50 / n * 100) if n > 0 else 0.0
    pct_above_sma200 = (above_sma200 / n * 100) if n > 0 else 0.0
    nh_nl_ratio = _safe_ratio(new_highs, new_highs + new_lows)
    nh_nl_diff = new_highs - new_lows
    ad_ratio = _safe_ratio(float(advancing), float(max(declining, 1)))

    return BreadthResult(
        date=date,
        market=market,
        pct_above_sma50=pct_above_sma50,
        pct_above_sma200=pct_above_sma200,
        nh_nl_ratio=nh_nl_ratio,
        nh_nl_diff=nh_nl_diff,
        ad_ratio=ad_ratio,
        total_stocks=n,
    )


def compute_breadth_composite(breadth: BreadthResult) -> float:
    """Compute breadth composite score (0-100) per SPEC R2.

    Formula: 0.25 * pct_above_sma50_norm + 0.25 * pct_above_sma200_norm
             + 0.25 * nh_nl_ratio_norm + 0.25 * ad_ratio_norm

    Each indicator normalized to 0-100 scale.
    """
    # pct values are already 0-100
    pct_sma50_norm = min(max(breadth.pct_above_sma50, 0.0), 100.0)
    pct_sma200_norm = min(max(breadth.pct_above_sma200, 0.0), 100.0)

    # nh_nl_ratio is 0-1, normalize to 0-100
    nh_nl_norm = min(max(breadth.nh_nl_ratio * 100, 0.0), 100.0)

    # ad_ratio: 0 = all declining, 2 = equal adv/decl, > 2 = mostly advancing
    # Normalize: ratio of 2 → 100, ratio of 0 → 0
    ad_norm = min(max(breadth.ad_ratio / 2.0 * 100, 0.0), 100.0)

    score = (
        _COMPOSITE_WEIGHTS[0] * pct_sma50_norm
        + _COMPOSITE_WEIGHTS[1] * pct_sma200_norm
        + _COMPOSITE_WEIGHTS[2] * nh_nl_norm
        + _COMPOSITE_WEIGHTS[3] * ad_norm
    )
    return float(min(max(score, 0.0), 100.0))


def _eval_criterion(
    name: str,
    value: float,
    bull_threshold: float,
    bear_threshold: float,
    higher_is_bull: bool = True,
) -> CriteriaDatum:
    """Evaluate a single criterion and return its directional assessment."""
    if higher_is_bull:
        if value > bull_threshold:
            direction = "bull"
        elif value < bear_threshold:
            direction = "bear"
        else:
            direction = "sideways"
    else:
        # Lower value is bull (e.g., SMA50 slope where negative is bear)
        if value > bull_threshold:
            direction = "sideways"
        elif value < bear_threshold:
            direction = "bear"
        else:
            direction = "sideways"

    return CriteriaDatum(name=name, value=value, direction=direction)


def determine_cycle(
    breadth: BreadthResult,
    kospi_data: dict[str, Any],
) -> CycleResult:
    """Determine market cycle phase based on 6 criteria per SPEC R3.

    Criteria:
    1. KOSPI vs SMA50/200
    2. SMA50 slope (4-week)
    3. % above SMA50
    4. % above SMA200
    5. NH-NL ratio
    6. Breadth Score

    When 4+ criteria point same direction → confirm that phase.
    Otherwise → "sideways".

    Args:
        breadth: Computed BreadthResult for the date.
        kospi_data: Dict with keys: close, sma50, sma200, sma50_slope.

    Returns:
        CycleResult with phase, criteria list, and confidence score.
    """
    close = kospi_data.get("close", 0.0)
    sma50 = kospi_data.get("sma50", 0.0)
    sma200 = kospi_data.get("sma200", 0.0)
    sma50_slope = kospi_data.get("sma50_slope", 0.0)

    # Criterion 1: KOSPI price vs SMA50/200
    if sma50 > 0 and sma200 > 0:
        if close > sma50 and close > sma200:
            c1_direction = "bull"
        elif close < sma50 and close < sma200:
            c1_direction = "bear"
        else:
            c1_direction = "sideways"
    else:
        c1_direction = "sideways"
    c1 = CriteriaDatum(name="KOSPI vs SMA50/200", value=close, direction=c1_direction)

    # Criterion 2: SMA50 slope (4-week)
    # @MX:NOTE: [AUTO] Slope near zero means abs(slope) < 0.005 (0.5%)
    if sma50_slope > 0.005:
        c2_direction = "bull"
    elif sma50_slope < -0.005:
        c2_direction = "bear"
    else:
        c2_direction = "sideways"
    c2 = CriteriaDatum(name="SMA50 slope", value=sma50_slope, direction=c2_direction)

    # Criterion 3: % above SMA50
    if breadth.pct_above_sma50 > _BULL_PCT_SMA50:
        c3_direction = "bull"
    elif breadth.pct_above_sma50 < _BEAR_PCT_SMA50:
        c3_direction = "bear"
    else:
        c3_direction = "sideways"
    c3 = CriteriaDatum(name="% above SMA50", value=breadth.pct_above_sma50, direction=c3_direction)

    # Criterion 4: % above SMA200
    if breadth.pct_above_sma200 > _BULL_PCT_SMA200:
        c4_direction = "bull"
    elif breadth.pct_above_sma200 < _BEAR_PCT_SMA200:
        c4_direction = "bear"
    else:
        c4_direction = "sideways"
    c4 = CriteriaDatum(name="% above SMA200", value=breadth.pct_above_sma200, direction=c4_direction)

    # Criterion 5: NH-NL ratio
    if breadth.nh_nl_ratio > _BULL_NH_NL_RATIO:
        c5_direction = "bull"
    elif breadth.nh_nl_ratio < _BEAR_NH_NL_RATIO:
        c5_direction = "bear"
    else:
        c5_direction = "sideways"
    c5 = CriteriaDatum(name="NH-NL ratio", value=breadth.nh_nl_ratio, direction=c5_direction)

    # Criterion 6: Breadth Score
    breadth_score = compute_breadth_composite(breadth)
    if breadth_score > _BULL_BREADTH_SCORE:
        c6_direction = "bull"
    elif breadth_score < _BEAR_BREADTH_SCORE:
        c6_direction = "bear"
    else:
        c6_direction = "sideways"
    c6 = CriteriaDatum(name="Breadth score", value=breadth_score, direction=c6_direction)

    criteria = [c1, c2, c3, c4, c5, c6]

    bull_count = sum(1 for c in criteria if c.direction == "bull")
    bear_count = sum(1 for c in criteria if c.direction == "bear")

    if bull_count >= 4:
        phase = "bull"
        confidence = int(bull_count / 6 * 100)
    elif bear_count >= 4:
        phase = "bear"
        confidence = int(bear_count / 6 * 100)
    else:
        phase = "sideways"
        confidence = 50  # uncertain

    return CycleResult(
        phase=phase,
        criteria=criteria,
        confidence=confidence,
    )


def detect_choppy(
    breadth_history: list[BreadthResult],
    kospi_data: dict[str, Any],
) -> bool:
    """Detect choppy market conditions per SPEC R4.

    Checks 4 conditions, returns True when 3+ are met:
    1. MA spread < 5% (convergence of SMA20/50/200)
    2. Breadth oscillation (pct_above_sma50 range < 15%p in 40-60% band over 4 weeks)
    3. Weekly return sign changes >= 5 out of 8 weeks
    4. NH + NL total < 5% of universe

    Args:
        breadth_history: List of BreadthResult ordered by date (oldest first).
        kospi_data: Dict with keys: sma20, sma50, sma200, weekly_returns (list).

    Returns:
        True if market is choppy, False otherwise.
    """
    if len(breadth_history) < 4:
        return False

    conditions_met = 0

    # Condition 1: MA spread < 5%
    sma20 = kospi_data.get("sma20", 0.0)
    sma50 = kospi_data.get("sma50", 0.0)
    sma200 = kospi_data.get("sma200", 0.0)

    if sma200 > 0 and sma50 > 0 and sma20 > 0:
        spread_20_50 = abs(sma20 - sma50) / sma50
        spread_50_200 = abs(sma50 - sma200) / sma200
        if spread_20_50 < _CHOPPY_MA_SPREAD_MAX and spread_50_200 < _CHOPPY_MA_SPREAD_MAX:
            conditions_met += 1

    # Condition 2: Breadth oscillation in 40-60% band with range < 15%
    recent_4w = breadth_history[-4:]
    pct_values = [r.pct_above_sma50 for r in recent_4w]
    in_band = all(40.0 <= v <= 60.0 for v in pct_values)
    pct_range = max(pct_values) - min(pct_values)
    if in_band and pct_range < _CHOPPY_BREADTH_RANGE_MAX:
        conditions_met += 1

    # Condition 3: Weekly return sign changes >= 5 out of 8 weeks
    weekly_returns: list[float] = kospi_data.get("weekly_returns", [])
    if len(weekly_returns) >= 4:
        sign_changes = 0
        for i in range(1, len(weekly_returns)):
            if weekly_returns[i] * weekly_returns[i - 1] < 0:
                sign_changes += 1
        if sign_changes >= _CHOPPY_SIGN_CHANGES_MIN:
            conditions_met += 1

    # Condition 4: NH + NL total < 5% of universe
    if breadth_history:
        latest = breadth_history[-1]
        total = latest.total_stocks
        nh_nl_total_pct = (
            abs(latest.nh_nl_diff) / max(total, 1)
            if total > 0 else 0.0
        )
        # Use nh_nl_ratio as proxy: if ratio near 0.5 and total is low
        if latest.nh_nl_ratio > 0.3 and latest.nh_nl_ratio < 0.7:
            # Low NH+NL activity: nh_nl_diff is small relative to universe
            if total > 0 and abs(latest.nh_nl_diff) < total * _CHOPPY_NH_NL_PCT_MAX:
                conditions_met += 1

    return conditions_met >= _CHOPPY_MIN_CONDITIONS


def compute_breadth_history(
    db_path: str,
    market: str,
    weeks: int = 12,
) -> list[BreadthResult]:
    """Compute breadth indicators for the last N weeks.

    Args:
        db_path: Path to weekly SQLite database file.
        market: "KOSPI" or "KOSDAQ".
        weeks: Number of weeks to look back (default 12).

    Returns:
        List of BreadthResult ordered by date ascending (oldest first).
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        # Get the last N distinct dates
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

    dates = sorted(r[0] for r in date_rows)  # ascending order

    results = []
    for date in dates:
        breadth = compute_breadth(db_path, market, date)
        breadth.breadth_score = compute_breadth_composite(breadth)
        results.append(breadth)

    return results
