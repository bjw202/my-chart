# coding: utf-8
"""Sector ranking service: wraps sector_metrics for API response."""

from __future__ import annotations

import logging

from my_chart.analysis.aggregate_types import WEIGHT_CAP
from my_chart.analysis.sector_metrics import (
    compute_sector_aggregates,
    compute_sector_ranking,
)
from my_chart.analysis.weekly_grid import _get_latest_valid_date, compute_weekly_grid
from backend.schemas.envelope import envelope_fields
from backend.schemas.sector import (
    SectorExcessReturns,
    SectorRankItem,
    SectorRankingResponse,
    SectorReturns,
)

logger = logging.getLogger(__name__)


def _get_latest_date(db_path: str, as_of: str | None = None) -> str | None:
    """정규 주간 격자 기반 최신 기준일 (SPEC-SECTOR-GRID-001 REQ-SGR-005 공유 헬퍼 경유)."""
    return _get_latest_valid_date(db_path, as_of)


def get_sector_ranking(
    weekly_db_path: str,
    daily_db_path: str | None = None,
    as_of: str | None = None,
    market: str = "all",
    period: str | None = None,
) -> SectorRankingResponse:
    """Compute sector rankings and return API response.

    Args:
        weekly_db_path: Full path to weekly SQLite database file.
        daily_db_path: 일봉 DB 경로(``stock_meta.market_cap`` — 시총가중 집계 입력).
            M2 부터 소비한다. ``None`` 이면 시총이 결측으로 취급된다.
        as_of: 기준일(ISO ``YYYY-MM-DD``). ``None`` 이면 구현 기본값. 게이팅 테스트는
            §8.4 규약 8 에 따라 **명시 인자**로 고정한다.
        market: ``all`` / ``kospi`` / ``kosdaq`` — M6 신설(AC-SAG-039). 집계 시점
            필터이므로 ``member_count`` 자체가 달라진다.
        period: ``1w``/``1m``/``3m`` — M6-gap G22(AC-SAG-021). ``data[]`` 의 ``rank``
            가 이 기간의 초과수익률 단독 기준으로 재배정된다. ``None`` 이면 종전과
            동일하게 composite 기준이다. 하위 호환 표면(``sectors[]``, legacy
            ``compute_sector_ranking``)은 이 인자의 영향을 받지 않는다 —
            AC-SAG-036 이 그 표면은 3기간 전부를 항상 반환하도록 요구한다.

    Returns:
        SectorRankingResponse with sectors ordered by rank.
    """
    date = _get_latest_date(weekly_db_path, as_of)
    if not date:
        logger.warning("No date found in weekly DB: %s", weekly_db_path)
        return SectorRankingResponse(
            date="", sectors=[], **envelope_fields(market_filter=market))

    rankings = compute_sector_ranking(weekly_db_path, date, daily_db_path, market)
    agg = compute_sector_aggregates(
        weekly_db_path, date, daily_db_path=daily_db_path, market=market, as_of=as_of,
        period=period)

    # 기존 응답 키(하위 호환, plan.md §1 D4) — 프론트엔드가 읽던 형태 그대로 유지한다.
    sector_items = [
        SectorRankItem(
            name=r.name,
            stock_count=r.stock_count,
            returns=SectorReturns(
                w1=round(r.sector_return_1w, 4),
                m1=round(r.sector_return_1m, 4),
                m3=round(r.sector_return_3m, 4),
            ),
            excess_returns=SectorExcessReturns(
                w1=round(r.sector_excess_return_1w, 4),
                m1=round(r.sector_excess_return_1m, 4),
                m3=round(r.sector_excess_return_3m, 4),
            ),
            rs_avg=r.sector_rs_avg,
            rs_top_pct=r.sector_rs_top_pct,
            nh_pct=r.sector_nh_pct,
            stage2_pct=r.sector_stage2_pct,
            composite_score=r.composite_score,
            rank=r.rank,
            rank_change=r.rank_change,
        )
        for r in rankings
    ]

    grid = compute_weekly_grid(weekly_db_path, as_of)
    partial = grid.latest.is_partial_week if grid.latest is not None else None

    return SectorRankingResponse(
        date=date,
        sectors=sector_items,
        **envelope_fields(
            as_of_date=date,
            as_of_is_partial_week=partial,
            return_window_days=agg.return_window_days,
            market_filter=market,
            weight_cap=WEIGHT_CAP,
            benchmark=agg.benchmark,
            data=agg.aggregates,
            excluded=agg.excluded,
            warnings=agg.warnings,
            baseline_date=agg.baseline_date,
        ),
    )
