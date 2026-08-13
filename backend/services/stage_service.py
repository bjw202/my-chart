"""Stage classification service: compute stage distribution and screening."""

from __future__ import annotations

import logging
import sqlite3

from my_chart.analysis.aggregate_types import WEIGHT_CAP
from my_chart.analysis.sector_metrics import compute_trading_value_by_period
from my_chart.analysis.stage_classifier import (
    _load_stocks_for_classification,
    classify_stage_or_none,
    screen_stage2_entry,
)
from my_chart.analysis.universe import ETC_SECTOR
from my_chart.analysis.weekly_grid import _get_latest_valid_date, anchor, compute_weekly_grid
from my_chart.analysis.weighting import capped_weights_detail
from my_chart.registry import get_sector_registry
from backend.schemas.stage import (
    SectorStageBreakdown,
    StageStock,
    StageDistribution,
    StageOverviewResponse,
)

logger = logging.getLogger(__name__)

# AC-SAG-041 근접 신고가 판정 — sector_metrics._NH_THRESHOLD 와 동일 관용(2% 이내).
_NEAR_52W_THRESHOLD = 0.02


def _get_latest_date(db_path: str) -> str | None:
    """정규 주간 격자 기반 최신 기준일 (SPEC-SECTOR-GRID-001 REQ-SGR-005 공유 헬퍼 경유)."""
    return _get_latest_valid_date(db_path)


def _market_matches(market: str | None, market_key: str) -> bool:
    if market_key in ("", "all"):
        return True
    return str(market or "").strip().upper() == market_key.upper()


def _pct(decimal_value: float | None) -> float | None:
    """decimal → % 변환(chg_1m 과 동일 관용). None 은 결측으로 보존."""
    return round(decimal_value * 100, 2) if decimal_value is not None else None


def _load_extended_weekly_fields(
    weekly_db_path: str, date: str, daily_db_path: str | None = None,
) -> dict[str, dict]:
    """CHG_1W / CHG_3M / MAX52 / trading_value 보조 필드 — AC-SAG-041 3열 확장.

    `_load_stocks_for_classification`(stage_classifier.py) 는 이 SPEC 범위 밖의
    다른 호출자와 공유하므로 건드리지 않고, 이 서비스에서 필요한 보조 컬럼만
    별도 쿼리로 읽는다(scope discipline).

    M6-gap G21 — ``trading_value`` 는 M5 가 확정한 정규 원천(daily
    ``VolumeWon``, ``compute_trading_value_by_period``, 1W 창)으로 계산한다.
    ``daily_db_path`` 가 없으면(호출자가 넘기지 않음) 결측(``None``)으로
    보존한다 — weekly ``Close×Volume`` 근사로 조용히 대체하지 않는다.
    """
    conn = sqlite3.connect(weekly_db_path, check_same_thread=False)
    try:
        rows = conn.execute(
            """SELECT Name, CHG_1W, CHG_3M, Close, MAX52
               FROM stock_prices WHERE Date = ?""",
            (date,),
        ).fetchall()
    finally:
        conn.close()

    tv_by_name: dict[str, float] = {}
    if daily_db_path:
        grid = compute_weekly_grid(weekly_db_path, date)
        anchor_bar = anchor(grid, date, 7)
        anchor_date = anchor_bar.date if anchor_bar is not None else None
        tv_by_period = compute_trading_value_by_period(
            daily_db_path, {"1w": anchor_date}, date)
        tv_by_name = tv_by_period.get("1w", {})

    out: dict[str, dict] = {}
    for name, chg_1w, chg_3m, close, max52 in rows:
        near_52w_high = None
        if close is not None and max52 is not None and float(max52) > 0:
            near_52w_high = float(close) >= float(max52) * (1 - _NEAR_52W_THRESHOLD)
        out[name] = {
            "chg_1w": chg_1w, "chg_3m": chg_3m,
            "trading_value": tv_by_name.get(name),
            "near_52w_high": near_52w_high,
        }
    return out


def _weight_in_sector_map(
    daily_db_path: str, sector_map: dict[str, str], names: set[str],
) -> dict[str, float]:
    """섹터별 시총 상한 재배분 가중치(AC-SAG-041, INV-CAP-1) — 종목별 flat map.

    `weighting.capped_weights_detail` 을 섹터별로 호출해 재사용한다(같은 산식을
    두 번 구현하지 않는다 — INV-CAP-1 재발 방지).
    """
    conn = sqlite3.connect(daily_db_path, check_same_thread=False)
    try:
        rows = conn.execute(
            "SELECT name, market_cap FROM stock_meta WHERE market_cap IS NOT NULL"
        ).fetchall()
    finally:
        conn.close()
    caps_by_sector: dict[str, dict[str, float]] = {}
    for name, cap in rows:
        if name not in names or cap is None or float(cap) <= 0:
            continue
        sector = sector_map.get(name)
        if sector is None:
            continue
        caps_by_sector.setdefault(sector, {})[name] = float(cap)

    out: dict[str, float] = {}
    for _sector, caps in caps_by_sector.items():
        weights = capped_weights_detail(caps, cap=WEIGHT_CAP).weights
        out.update(weights)
    return out


def get_stage_overview(
    weekly_db_path: str, daily_db_path: str | None = None, market: str = "all",
) -> StageOverviewResponse:
    """Compute stage distribution and entry candidates.

    Args:
        weekly_db_path: Full path to weekly SQLite database file.
        daily_db_path: 일봉 DB 경로(``stock_meta.market_cap``) — M6 신설.
            ``weight_in_sector``(AC-SAG-041) 산출에 쓰인다. ``None`` 이면 그
            필드는 전 종목 ``None``으로 채워진다.
        market: ``all`` / ``kospi`` / ``kosdaq`` — M6 신설(AC-SAG-039).

    Returns:
        StageOverviewResponse with distribution, by_sector, and candidates.
    """
    market_key = (market or "all").lower()
    date = _get_latest_date(weekly_db_path)
    if not date:
        logger.warning("No date found in weekly DB: %s", weekly_db_path)
        return StageOverviewResponse(
            distribution=StageDistribution(
                stage1=0, stage2=0, stage3=0, stage4=0, unclassified_count=0, total=0),
            by_sector=[],
            stage2_candidates=[],
            market_filter=market_key or "all",
        )

    # Build sector map from registry
    df_sector = get_sector_registry()
    sector_map: dict[str, str] = {}
    registry_market_of: dict[str, str] = {}
    for _, row in df_sector.iterrows():
        name = str(row["Name"])
        sector_map[name] = str(row.get("산업명(대)") or ETC_SECTOR)
        registry_market_of[name] = str(row.get("Market") or "")

    # AC-SAG-025/026/027 — REQ-SAG-023: SMA40/SMA10 결측 종목은 stage=None(분류 불가)
    # 으로 분류 카운트 분모에서 제외하고, distribution/by_sector 는 그 개수를
    # unclassified_count 로 별도 노출한다(0/Stage1 흡수 금지, §8.6 불변식).
    conn = sqlite3.connect(weekly_db_path, check_same_thread=False)
    try:
        raw_stocks = _load_stocks_for_classification(conn, date)
    finally:
        conn.close()

    # M6 — market 파라미터(AC-SAG-039). 집계 시점 필터이므로 distribution 자체가
    # 달라진다.
    if market_key not in ("", "all"):
        raw_stocks = [
            s for s in raw_stocks
            if _market_matches(registry_market_of.get(s["Name"]), market_key)
        ]

    extended = _load_extended_weekly_fields(weekly_db_path, date, daily_db_path)
    weight_map: dict[str, float] = {}
    if daily_db_path:
        names = {s["Name"] for s in raw_stocks}
        weight_map = _weight_in_sector_map(daily_db_path, sector_map, names)

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
    if market_key not in ("", "all"):
        candidates_raw = [
            c for c in candidates_raw
            if _market_matches(registry_market_of.get(c["name"]), market_key)
        ]

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
            chg_1w=_pct(extended.get(c["name"], {}).get("chg_1w")),
            chg_3m=_pct(extended.get(c["name"], {}).get("chg_3m")),
            volume_ratio=round(c["volume_ratio"], 2),
            close=round(c["close"], 2),
            sma50=round(c["sma50"], 2),
            sma200=round(c["sma200"], 2),
            weight_in_sector=weight_map.get(c["name"]),
            trading_value=extended.get(c["name"], {}).get("trading_value"),
            near_52w_high=extended.get(c["name"], {}).get("near_52w_high"),
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
        ext = extended.get(sname, {})

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
            chg_1w=_pct(ext.get("chg_1w")),
            chg_3m=_pct(ext.get("chg_3m")),
            volume_ratio=round(vol_ratio, 2),
            close=round(close, 2),
            sma50=round(sma50_val, 2),
            sma200=round(sma200_val, 2),
            weight_in_sector=weight_map.get(sname),
            trading_value=ext.get("trading_value"),
            near_52w_high=ext.get("near_52w_high"),
        ))

    return StageOverviewResponse(
        distribution=distribution,
        by_sector=by_sector,
        stage2_candidates=candidates,
        all_stocks=all_stocks_list,
        market_filter=market_key or "all",
    )
