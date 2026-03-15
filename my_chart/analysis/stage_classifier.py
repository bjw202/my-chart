"""Stage classification engine for Weinstein stage analysis.

Classifies individual stocks into Stage 1 (Base), Stage 2 (Advance),
Stage 3 (Top), Stage 4 (Decline) based on weekly price data.

Per SPEC-TOPDOWN-001A R5-R6.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Any

# Index names excluded from classification
_INDEX_NAMES = frozenset({"KOSPI", "KOSDAQ"})

# Stage 2 entry criteria thresholds per SPEC R6
_STAGE2_ENTRY_RS_MIN = 70.0       # RS_12M_Rating >= 70
_STAGE2_ENTRY_VOLUME_RATIO = 1.5  # Volume > VolumeSMA10 * 1.5

# Stage classification thresholds per SPEC R5
_STAGE4_SLOPE_THRESHOLD = -0.01   # SMA200_slope < -1%
_STAGE2_SLOPE_THRESHOLD = 0.005   # SMA200_slope > 0.5%
_STAGE2_RS_STRONG = 60.0          # RS > 60 → Stage 2 Strong
_STAGE3_PROXIMITY = 0.07          # Close within SMA200 ±7%
_STAGE3_SLOPE_MAX = 0.02          # SMA200 slope 둔화 기준 (±2%)
_STAGE1_SLOPE_FLAT = 0.005        # abs(SMA200_slope) < 0.5%
_STAGE1_PROXIMITY = 0.05          # Close within SMA200 ±5%


@dataclass
class StageResult:
    """Stage classification result for a single stock."""

    name: str
    stage: int               # 1, 2, 3, or 4
    detail: str              # e.g., "Stage 2 Strong", "Stage 4"
    sma50_proxy: float = 0.0  # weekly SMA10
    sma200_proxy: float = 0.0  # weekly SMA40
    sma200_slope: float = 0.0
    rs_12m: float = 0.0
    chg_1m: float = 0.0
    volume_ratio: float = 0.0
    close: float = 0.0


def _compute_slope(current: float, prev: float) -> float:
    """Compute 4-week slope: (current - prev) / prev."""
    if prev == 0:
        return 0.0
    return (current - prev) / prev


def classify_stage(stock_row: dict[str, Any]) -> StageResult:
    """Classify a single stock into Weinstein Stage 1-4 per SPEC R5.

    Priority order (highest priority first):
    1. Stage 4 (Decline): Close < SMA50_proxy AND Close < SMA200_proxy AND slope < -1%
    2. Stage 2 (Advance): Close > SMA50_proxy AND Close > SMA200_proxy AND SMA50 > SMA200 AND slope > 0.5%
       - Stage 2 Strong: RS_12M_Rating > 60
       - Stage 2 Weak: RS_12M_Rating <= 60
    3. Stage 3 (Top): Close near SMA200 (±3%) AND SMA200 flattening AND SMA50 declining
    4. Stage 1 (Base): abs(SMA200_slope) < 0.5% AND Close within SMA200 ±5%
    5. Default: Close > SMA200 → Stage 2 Early; else → Stage 4 Late

    Args:
        stock_row: Dict with keys: Name, Close, SMA10, SMA40, SMA40_slope,
                   RS_12M_Rating, CHG_1M, Volume, VolumeSMA10.

    Returns:
        StageResult with stage number and detail description.
    """
    name = str(stock_row.get("Name", ""))
    close = float(stock_row.get("Close", 0.0) or 0.0)
    sma50_proxy = float(stock_row.get("SMA10", 0.0) or 0.0)   # weekly SMA10 ≈ 50-day
    sma200_proxy = float(stock_row.get("SMA40", 0.0) or 0.0)  # weekly SMA40 ≈ 200-day
    sma40_slope = float(stock_row.get("SMA40_slope", 0.0) or 0.0)
    rs_12m = float(stock_row.get("RS_12M_Rating", 0.0) or 0.0)
    chg_1m = float(stock_row.get("CHG_1M", 0.0) or 0.0)
    volume = float(stock_row.get("Volume", 0.0) or 0.0)
    volume_sma10 = float(stock_row.get("VolumeSMA10", 0.0) or 0.0)

    volume_ratio = volume / max(volume_sma10, 1.0)

    # --- Priority 1: Stage 4 (Decline) ---
    # Close < SMA50_proxy AND Close < SMA200_proxy AND SMA200_slope < -1%
    if (sma50_proxy > 0 and close < sma50_proxy
            and sma200_proxy > 0 and close < sma200_proxy
            and sma40_slope < _STAGE4_SLOPE_THRESHOLD):
        return StageResult(
            name=name, stage=4, detail="Stage 4",
            sma50_proxy=sma50_proxy, sma200_proxy=sma200_proxy,
            sma200_slope=sma40_slope, rs_12m=rs_12m,
            chg_1m=chg_1m, volume_ratio=volume_ratio, close=close,
        )

    # --- Priority 2: Stage 2 (Advance) ---
    # Close > SMA50_proxy AND Close > SMA200_proxy
    # AND SMA50 > SMA200 (Golden Cross) AND SMA200_slope > 0.5%
    if (sma50_proxy > 0 and close > sma50_proxy
            and sma200_proxy > 0 and close > sma200_proxy
            and sma50_proxy > sma200_proxy
            and sma40_slope > _STAGE2_SLOPE_THRESHOLD):
        if rs_12m > _STAGE2_RS_STRONG:
            detail = "Stage 2 Strong"
        else:
            detail = "Stage 2 Weak"
        return StageResult(
            name=name, stage=2, detail=detail,
            sma50_proxy=sma50_proxy, sma200_proxy=sma200_proxy,
            sma200_slope=sma40_slope, rs_12m=rs_12m,
            chg_1m=chg_1m, volume_ratio=volume_ratio, close=close,
        )

    # --- Priority 3: Stage 3 (Top) ---
    # Weinstein Stage 3: 상승 추세가 둔화되며 천장을 형성하는 구간
    # 조건: Close가 SMA200 근처 (±7%) AND SMA200 slope가 둔화 (±2%) AND
    #        SMA50 < SMA200 (골든크로스 해제, 하락 전환 시작)
    if sma200_proxy > 0:
        proximity_to_sma200 = abs(close - sma200_proxy) / sma200_proxy
        sma50_declining = sma50_proxy < sma200_proxy

        if (proximity_to_sma200 <= _STAGE3_PROXIMITY
                and abs(sma40_slope) <= _STAGE3_SLOPE_MAX
                and sma50_declining):
            return StageResult(
                name=name, stage=3, detail="Stage 3",
                sma50_proxy=sma50_proxy, sma200_proxy=sma200_proxy,
                sma200_slope=sma40_slope, rs_12m=rs_12m,
                chg_1m=chg_1m, volume_ratio=volume_ratio, close=close,
            )

    # --- Priority 4: Stage 1 (Base) ---
    # abs(SMA200_slope) < 0.5% AND Close within SMA200 ±5%
    if sma200_proxy > 0:
        proximity_to_sma200 = abs(close - sma200_proxy) / sma200_proxy
        if (abs(sma40_slope) < _STAGE1_SLOPE_FLAT
                and proximity_to_sma200 <= _STAGE1_PROXIMITY):
            return StageResult(
                name=name, stage=1, detail="Stage 1",
                sma50_proxy=sma50_proxy, sma200_proxy=sma200_proxy,
                sma200_slope=sma40_slope, rs_12m=rs_12m,
                chg_1m=chg_1m, volume_ratio=volume_ratio, close=close,
            )

    # --- Priority 5: Default ---
    if sma200_proxy > 0 and close > sma200_proxy:
        stage, detail = 2, "Stage 2 Early"
    else:
        stage, detail = 4, "Stage 4 Late"

    return StageResult(
        name=name, stage=stage, detail=detail,
        sma50_proxy=sma50_proxy, sma200_proxy=sma200_proxy,
        sma200_slope=sma40_slope, rs_12m=rs_12m,
        chg_1m=chg_1m, volume_ratio=volume_ratio, close=close,
    )


def _load_stocks_for_classification(
    conn: sqlite3.Connection,
    date: str,
) -> list[dict[str, Any]]:
    """Load weekly stock data with RS ratings for stage classification."""
    # Get base stock data
    rows = conn.execute(
        """SELECT sp.Name, sp.Close, sp.SMA10, sp.SMA40,
                  sp.SMA40_Trend_4M, sp.CHG_1M, sp.Volume, sp.VolumeSMA10,
                  rs.RS_12M_Rating
           FROM stock_prices sp
           LEFT JOIN relative_strength rs
             ON sp.Name = rs.Name AND sp.Date = rs.Date
           WHERE sp.Date = ?
           ORDER BY sp.Name""",
        (date,),
    ).fetchall()

    result = []
    for r in rows:
        name = r[0]
        if name in _INDEX_NAMES:
            continue
        # SMA40_Trend_4M은 SMA40의 4개월 추세 slope 값 (이미 비율로 계산됨)
        slope = float(r[4] or 0.0)

        result.append({
            "Name": name,
            "Close": r[1],
            "SMA10": r[2],
            "SMA40": r[3],
            "SMA40_slope": slope,
            "CHG_1M": r[5],
            "Volume": r[6],
            "VolumeSMA10": r[7],
            "RS_12M_Rating": r[8],
        })
    return result


def classify_all(db_path: str, date: str) -> list[StageResult]:
    """Classify all stocks in the weekly DB for a given date.

    Args:
        db_path: Path to weekly SQLite database file.
        date: Date string in YYYY-MM-DD format.

    Returns:
        List of StageResult, one per individual stock (indices excluded).
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        stocks = _load_stocks_for_classification(conn, date)
    finally:
        conn.close()

    return [classify_stage(s) for s in stocks]


def screen_stage2_entry(db_path: str, date: str) -> list[dict[str, Any]]:
    """Screen for Stage 2 entry candidates meeting all 6 conditions per SPEC R6.

    Conditions:
    1. Classified as Stage 2 (any sub-type)
    2. Close > SMA50_proxy (Close > SMA10)
    3. SMA50_proxy > SMA200_proxy (Golden Cross: SMA10 > SMA40)
    4. Volume > VolumeSMA10 * 1.5 (volume surge)
    5. RS_12M_Rating >= 70 (top 30%)
    6. CHG_1M > 0 (positive 1-month return)

    Args:
        db_path: Path to weekly SQLite database file.
        date: Date string in YYYY-MM-DD format.

    Returns:
        List of dicts with stock info for Stage 2 entry candidates.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        stocks = _load_stocks_for_classification(conn, date)
    finally:
        conn.close()

    results = []
    for stock in stocks:
        stage_result = classify_stage(stock)

        # Condition 1: Must be Stage 2
        if stage_result.stage != 2:
            continue

        close = float(stock.get("Close", 0.0) or 0.0)
        sma50_proxy = float(stock.get("SMA10", 0.0) or 0.0)
        sma200_proxy = float(stock.get("SMA40", 0.0) or 0.0)
        rs = float(stock.get("RS_12M_Rating", 0.0) or 0.0)
        chg_1m = float(stock.get("CHG_1M", 0.0) or 0.0)
        volume = float(stock.get("Volume", 0.0) or 0.0)
        volume_sma10 = float(stock.get("VolumeSMA10", 0.0) or 0.0)
        volume_ratio = volume / max(volume_sma10, 1.0)

        # Condition 2: Close > SMA50_proxy
        if sma50_proxy > 0 and close <= sma50_proxy:
            continue

        # Condition 3: Golden Cross (SMA50_proxy > SMA200_proxy)
        if sma200_proxy > 0 and sma50_proxy <= sma200_proxy:
            continue

        # Condition 4: Volume surge
        if volume_ratio < _STAGE2_ENTRY_VOLUME_RATIO:
            continue

        # Condition 5: RS >= 70
        if rs < _STAGE2_ENTRY_RS_MIN:
            continue

        # Condition 6: Positive 1-month return
        if chg_1m <= 0:
            continue

        results.append({
            "name": stock["Name"],
            "stage": stage_result.stage,
            "stage_detail": stage_result.detail,
            "rs_12m": rs,
            "chg_1m": chg_1m,
            "volume_ratio": volume_ratio,
            "close": close,
            "sma50": sma50_proxy,
            "sma200": sma200_proxy,
        })

    return results
