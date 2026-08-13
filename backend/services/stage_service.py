"""Stage classification service: compute stage distribution and screening."""

from __future__ import annotations

import logging
import sqlite3

from my_chart.analysis.stage_classifier import (
    _load_stocks_for_classification,
    classify_stage_or_none,
    screen_stage2_entry,
)
from my_chart.analysis.universe import ETC_SECTOR
from my_chart.analysis.weekly_grid import _get_latest_valid_date
from my_chart.registry import get_sector_registry
from backend.schemas.stage import (
    SectorStageBreakdown,
    StageStock,
    StageDistribution,
    StageOverviewResponse,
)

logger = logging.getLogger(__name__)


def _get_latest_date(db_path: str) -> str | None:
    """정규 주간 격자 기반 최신 기준일 (SPEC-SECTOR-GRID-001 REQ-SGR-005 공유 헬퍼 경유)."""
    return _get_latest_valid_date(db_path)


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
            distribution=StageDistribution(
                stage1=0, stage2=0, stage3=0, stage4=0, unclassified_count=0, total=0),
            by_sector=[],
            stage2_candidates=[],
        )

    # Build sector map from registry
    df_sector = get_sector_registry()
    sector_map: dict[str, str] = {}
    for _, row in df_sector.iterrows():
        sector_map[str(row["Name"])] = str(row.get("산업명(대)") or ETC_SECTOR)

    # AC-SAG-025/026/027 — REQ-SAG-023: SMA40/SMA10 결측 종목은 stage=None(분류 불가)
    # 으로 분류 카운트 분모에서 제외하고, distribution/by_sector 는 그 개수를
    # unclassified_count 로 별도 노출한다(0/Stage1 흡수 금지, §8.6 불변식).
    conn = sqlite3.connect(weekly_db_path, check_same_thread=False)
    try:
        raw_stocks = _load_stocks_for_classification(conn, date)
    finally:
        conn.close()

    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    unclassified = 0
    sector_stages: dict[str, dict[int, int]] = {}
    sector_unclassified: dict[str, int] = {}

    for stock in raw_stocks:
        sector = sector_map.get(stock["Name"], ETC_SECTOR)
        stage, _detail = classify_stage_or_none(stock)
        if stage is None:
            unclassified += 1
            sector_unclassified[sector] = sector_unclassified.get(sector, 0) + 1
            continue
        counts[stage] = counts.get(stage, 0) + 1
        if sector not in sector_stages:
            sector_stages[sector] = {1: 0, 2: 0, 3: 0, 4: 0}
        sector_stages[sector][stage] = sector_stages[sector].get(stage, 0) + 1

    total = sum(counts.values()) + unclassified
    distribution = StageDistribution(
        stage1=counts[1],
        stage2=counts[2],
        stage3=counts[3],
        stage4=counts[4],
        unclassified_count=unclassified,
        total=total,
    )

    # By sector breakdown
    all_sectors = sorted(set(sector_stages) | set(sector_unclassified))
    by_sector = []
    for sector in all_sectors:
        stages = sector_stages.get(sector, {})
        s_unclassified = sector_unclassified.get(sector, 0)
        s_total = sum(stages.values()) + s_unclassified
        by_sector.append(SectorStageBreakdown(
            sector=sector,
            stage1=stages.get(1, 0),
            stage2=stages.get(2, 0),
            stage3=stages.get(3, 0),
            stage4=stages.get(4, 0),
            unclassified_count=s_unclassified,
            total=s_total,
        ))

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

    # Build all_stocks enriched with RS/price data. `raw_stocks` was already
    # loaded above for the distribution/by_sector pass — re-use it (avoids a
    # second identical query). AC-SAG-026 — 분류 불가(SMA40/SMA10 NULL) 종목은
    # StageStock.stage 가 non-optional int 이므로 목록에서 제외한다(0 치환 대신
    # 완전 배제 — REQ-SAG-023).
    all_stocks_list: list[StageStock] = []
    for stock in raw_stocks:
        stage_val, detail_val = classify_stage_or_none(stock)
        if stage_val is None:
            continue
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
            stage=stage_val,
            stage_detail=detail_val,
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
