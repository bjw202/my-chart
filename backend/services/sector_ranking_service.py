# coding: utf-8
"""Sector ranking service: wraps sector_metrics for API response."""

from __future__ import annotations

import logging

from my_chart.analysis.aggregate_types import WEIGHT_CAP, MetricValue, SectorAggregate
from my_chart.analysis.sector_metrics import build_shared_inputs, compute_sector_aggregates
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


def _pct_or_zero(m: MetricValue) -> float:
    """비율형 지표 — 스키마가 non-null(float)이라 결측이면 레거시와 같이 0.0 으로 둔다."""
    return round(m.value, 2) if m.value is not None else 0.0


def _rank_item(a: SectorAggregate) -> SectorRankItem:
    """순위가 매겨진 집계 1건 → 하위 호환 ``SectorRankItem``(반올림은 직렬화 시점 1회).

    ``rank`` 가 있는 섹터는 ``_rank_sectors`` 가 3기간 초과수익률 전부 non-null 일 때만
    순위를 주므로 ``returns``/``excess_returns`` 값이 반드시 있다(초과 = 섹터 − 벤치마크).
    """
    def _r(d: dict[str, MetricValue], p: str) -> float:
        return round(d[p].value, 4)

    return SectorRankItem(
        name=a.name,
        stock_count=a.member_count,
        returns=SectorReturns(
            w1=_r(a.returns, "1w"), m1=_r(a.returns, "1m"), m3=_r(a.returns, "3m")),
        excess_returns=SectorExcessReturns(
            w1=_r(a.excess_returns, "1w"), m1=_r(a.excess_returns, "1m"),
            m3=_r(a.excess_returns, "3m")),
        rs_avg=_pct_or_zero(a.rs_avg),
        rs_med=round(a.rs_med.value, 2) if a.rs_med.value is not None else None,
        rs_top_pct=_pct_or_zero(a.rs_top_pct),
        nh_pct=_pct_or_zero(a.nh_pct),
        stage2_pct=_pct_or_zero(a.stage2_pct),
        composite_score=round(a.composite_score.value, 2),
        rank=a.rank,
        # 스키마 int — 기준일에 순위가 없던 섹터(None)는 레거시와 같이 0 으로 둔다.
        # 신규 진입 구분이 필요한 소비자는 data[].rank_change(null 허용)를 읽는다.
        rank_change=a.rank_change if a.rank_change is not None else 0,
    )


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
            동일하게 composite 기준이다. 하위 호환 표면 ``sectors[]`` 는 이 인자의
            영향을 받지 않는다(항상 composite 순위) — AC-SAG-036 이 그 표면은 3기간
            전부를 항상 반환하도록 요구한다.

    Returns:
        SectorRankingResponse with sectors ordered by rank.
    """
    date = _get_latest_date(weekly_db_path, as_of)
    if not date:
        logger.warning("No date found in weekly DB: %s", weekly_db_path)
        return SectorRankingResponse(
            date="", sectors=[], **envelope_fields(market_filter=market))

    # @MX:NOTE: [AUTO] sectors[] 원천 = data[] 와 같은 `compute_sector_aggregates(period=None)`
    #   (ALL_CAPPED 벤치마크 초과수익률 + 순위 백분위 composite, AG-8). 종전에는 레거시 순위
    #   함수(min-max 정규화 · KOSPI 지수 행 초과수익률, 제거됨)를 타서, 프론트 섹터 표 한 행에
    #   data[] 순위와 레거시 초과수익률이 섞였다(라이브 1M 방송미디어 +23.84 vs +15.53).
    #   순위 제외 섹터(rank None — AG-5 · 초과수익률 결측)는 sectors[] 에서도 빠진다(Bump·알림과 동일).
    #   period 지정 시 data[] 는 기간 순위, sectors[] 는 composite 순위 — 같은 기준일을 두 번
    #   집계하므로 날짜 무관 입력(유효 유니버스 등)은 한 번만 만들어 공유한다.
    if period is None:
        agg = compute_sector_aggregates(
            weekly_db_path, date, daily_db_path=daily_db_path, market=market, as_of=as_of)
        composite = agg
    else:
        shared = build_shared_inputs(weekly_db_path, daily_db_path, as_of or date)
        agg = compute_sector_aggregates(
            weekly_db_path, date, daily_db_path=daily_db_path, market=market, as_of=as_of,
            period=period, shared=shared)
        composite = compute_sector_aggregates(
            weekly_db_path, date, daily_db_path=daily_db_path, market=market, as_of=as_of,
            period=None, shared=shared)

    # 기존 응답 키(하위 호환, plan.md §1 D4) — 프론트엔드가 읽던 형태 그대로 유지한다.
    ranked = sorted((a for a in composite.aggregates if a.rank is not None),
                    key=lambda a: a.rank)
    sector_items = [_rank_item(a) for a in ranked]

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
