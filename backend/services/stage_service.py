"""Stage classification service: compute stage distribution and screening."""

from __future__ import annotations

import logging
import sqlite3

from my_chart.analysis.stage_classifier import classify_all, classify_stage, screen_stage2_entry
from my_chart.registry import get_sector_registry
from backend.schemas.stage import (
    SectorStageBreakdown,
    StageStock,
    StageDistribution,
    StageOverviewResponse,
)

logger = logging.getLogger(__name__)


def _get_latest_date(db_path: str) -> str | None:
    """Get the latest date in the weekly DB."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        row = conn.execute(
            "SELECT MAX(Date) FROM stock_prices WHERE Name NOT IN ('KOSPI', 'KOSDAQ')"
        ).fetchone()
        return row[0] if row else None
    finally:
        conn.close()


def _get_sector_for_stock(name: str, sector_map: dict[str, str]) -> str:
    """Get sector for a stock name, defaulting to 'Unknown'."""
    return sector_map.get(name, "Unknown")


def get_stage_overview(weekly_db_path: str) -> StageOverviewResponse:
    """Compute stage distribution and entry candidates.

    Args:
        weekly_db_path: Full path to weekly SQLite database file.

    Returns:
        StageOverviewResponse with distribution, by_sector, and candidates.
    """
    date = _get_latest_date(weekly_db_path)
    if not date:
        logger.warning("No date found in weekly DB: %s", weekly_db_path)
        return StageOverviewResponse(
            distribution=StageDistribution(stage1=0, stage2=0, stage3=0, stage4=0, total=0),
            by_sector=[],
            stage2_candidates=[],
        )

    # Classify all stocks
    all_stages = classify_all(weekly_db_path, date)

    # Build sector map from registry
    df_sector = get_sector_registry()
    sector_map: dict[str, str] = {}
    for _, row in df_sector.iterrows():
        sector_map[str(row["Name"])] = str(row.get("산업명(대)") or "Unknown")

    # Stage distribution
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    sector_stages: dict[str, dict[int, int]] = {}

    for result in all_stages:
        stage = result.stage
        counts[stage] = counts.get(stage, 0) + 1

        sector = sector_map.get(result.name, "Unknown")
        if sector not in sector_stages:
            sector_stages[sector] = {1: 0, 2: 0, 3: 0, 4: 0}
        sector_stages[sector][stage] = sector_stages[sector].get(stage, 0) + 1

    total = sum(counts.values())
    distribution = StageDistribution(
        stage1=counts[1],
        stage2=counts[2],
        stage3=counts[3],
        stage4=counts[4],
        total=total,
    )

    # By sector breakdown
    by_sector = [
        SectorStageBreakdown(
            sector=sector,
            stage1=stages.get(1, 0),
            stage2=stages.get(2, 0),
            stage3=stages.get(3, 0),
            stage4=stages.get(4, 0),
        )
        for sector, stages in sorted(sector_stages.items())
    ]

    # Stage 2 entry candidates
    candidates_raw = screen_stage2_entry(weekly_db_path, date)

    # Load additional info (code, market, etc.) from sector registry
    code_map: dict[str, str] = {}
    market_map: dict[str, str] = {}
    sector_minor_map: dict[str, str] = {}
    for _, row in df_sector.iterrows():
        name = str(row["Name"])
        code_map[name] = str(row.get("Code", "")).zfill(6)
        market_map[name] = str(row.get("Market", ""))
        sector_minor_map[name] = str(row.get("산업명(중)", "") or "")

    candidates = [
        StageStock(
            code=code_map.get(c["name"], ""),
            name=c["name"],
            market=market_map.get(c["name"], ""),
            sector_major=sector_map.get(c["name"], ""),
            sector_minor=sector_minor_map.get(c["name"], ""),
            stage=c["stage"],
            stage_detail=c.get("stage_detail", "Stage 2"),
            rs_12m=round(c["rs_12m"], 2),
            chg_1m=round(c["chg_1m"] * 100, 2),  # decimal → %
            volume_ratio=round(c["volume_ratio"], 2),
            close=round(c["close"], 2),
            sma50=round(c["sma50"], 2),
            sma200=round(c["sma200"], 2),
        )
        for c in candidates_raw
    ]

    # Build all_stocks from classify_all results enriched with RS/price data
    # Re-use the internal loader via the same query pattern as screen_stage2_entry
    conn = sqlite3.connect(weekly_db_path, check_same_thread=False)
    try:
        # Use the same SQL that stage_classifier uses internally
        from my_chart.analysis.stage_classifier import _load_stocks_for_classification
        raw_stocks = _load_stocks_for_classification(conn, date)
    finally:
        conn.close()

    all_stocks_list: list[StageStock] = []
    for stock in raw_stocks:
        sr = classify_stage(stock)
        sname = stock["Name"]
        close = float(stock.get("Close", 0.0) or 0.0)
        sma50_val = float(stock.get("SMA10", 0.0) or 0.0)
        sma200_val = float(stock.get("SMA40", 0.0) or 0.0)
        rs = float(stock.get("RS_12M_Rating", 0.0) or 0.0)
        chg_1m_val = float(stock.get("CHG_1M", 0.0) or 0.0)
        vol = float(stock.get("Volume", 0.0) or 0.0)
        vol_sma = float(stock.get("VolumeSMA10", 0.0) or 0.0)
        vol_ratio = vol / max(vol_sma, 1.0)

        all_stocks_list.append(StageStock(
            code=code_map.get(sname, ""),
            name=sname,
            market=market_map.get(sname, ""),
            sector_major=sector_map.get(sname, ""),
            sector_minor=sector_minor_map.get(sname, ""),
            stage=sr.stage,
            stage_detail=sr.detail,
            rs_12m=round(rs, 2),
            chg_1m=round(chg_1m_val * 100, 2),
            volume_ratio=round(vol_ratio, 2),
            close=round(close, 2),
            sma50=round(sma50_val, 2),
            sma200=round(sma200_val, 2),
        ))

    return StageOverviewResponse(
        distribution=distribution,
        by_sector=by_sector,
        stage2_candidates=candidates,
        all_stocks=all_stocks_list,
    )
