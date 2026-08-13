# coding: utf-8
"""Sector ranking service: wraps sector_metrics for API response."""

from __future__ import annotations

import logging

from my_chart.analysis.aggregate_types import (
    WEIGHT_CAP,
    SectorAggregate,
    missing,
    present,
)
from my_chart.analysis.sector_metrics import SectorRank, compute_sector_ranking
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


def _as_aggregate(r: SectorRank) -> SectorAggregate:
    """M1.1 전환 매핑 — 구 `SectorRank` 를 신 `data[]` 형태로 옮긴다.

    **M1.1 은 형태만 고정한다**(plan.md §2 M1.1: "GREEN: 스키마 정의 + 빈 값으로 채워
    반환, 값 로직은 M2 이후"). 따라서 지표 값은 구 등가중 산출물을 그대로 싣고,
    커버리지·가중 산출물(``valid_count`` / ``coverage`` / ``effective_n`` /
    ``capped_members``)은 **아직 산출되지 않았으므로 결측**으로 남긴다 — 여기에 0 이나
    1.0 을 채우면 §9.1 이 금지한 치환이 되고, 화면에서 "커버리지 100%"로 읽힌다.

    M2 가 이 함수를 실제 시총가중 집계(`compute_sector_aggregates`)로 교체한다.
    """
    return SectorAggregate(
        name=r.name,
        member_count=r.stock_count,
        valid_count=None,
        coverage_ratio=missing(),
        cap_coverage_ratio=missing(),
        weight_cap=WEIGHT_CAP,
        effective_n=missing(),
        returns={
            "1w": present(r.sector_return_1w),
            "1m": present(r.sector_return_1m),
            "3m": present(r.sector_return_3m),
        },
        excess_returns={
            "1w": present(r.sector_excess_return_1w),
            "1m": present(r.sector_excess_return_1m),
            "3m": present(r.sector_excess_return_3m),
        },
        rs_avg=present(r.sector_rs_avg),
        rs_top_pct=present(r.sector_rs_top_pct),
        nh_pct=present(r.sector_nh_pct),
        stage2_pct=present(r.sector_stage2_pct),
        composite_score=present(r.composite_score),
        rank=r.rank,
        rank_change=r.rank_change,
    )


def get_sector_ranking(
    weekly_db_path: str,
    daily_db_path: str | None = None,
    as_of: str | None = None,
) -> SectorRankingResponse:
    """Compute sector rankings and return API response.

    Args:
        weekly_db_path: Full path to weekly SQLite database file.
        daily_db_path: 일봉 DB 경로(``stock_meta.market_cap`` — 시총가중 집계 입력).
            M2 부터 소비한다. ``None`` 이면 시총이 결측으로 취급된다.
        as_of: 기준일(ISO ``YYYY-MM-DD``). ``None`` 이면 구현 기본값. 게이팅 테스트는
            §8.4 규약 8 에 따라 **명시 인자**로 고정한다.

    Returns:
        SectorRankingResponse with sectors ordered by rank.
    """
    date = _get_latest_date(weekly_db_path, as_of)
    if not date:
        logger.warning("No date found in weekly DB: %s", weekly_db_path)
        return SectorRankingResponse(date="", sectors=[], **envelope_fields())

    rankings = compute_sector_ranking(weekly_db_path, date)

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
            weight_cap=WEIGHT_CAP,
            data=[_as_aggregate(r) for r in rankings],
        ),
    )
