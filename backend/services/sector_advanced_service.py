"""SPEC-TOPDOWN-002A 고급 섹터 분석 서비스 레이어.

sector_advanced.py 계산 함수를 API 응답 형식으로 변환한다.
"""

from __future__ import annotations

import logging
import sqlite3

from my_chart.analysis.sector_advanced import (
    compute_rrg_data,
    compute_stock_bubble,
    compute_treemap_data,
)
from my_chart.analysis.aggregate_types import WEIGHT_CAP
from my_chart.analysis.weekly_grid import _get_latest_valid_date
from backend.schemas.envelope import envelope_fields
from backend.schemas.sector_advanced import (
    RRGResponse,
    RRGSectorItem,
    RRGTrailPoint,
    SectorBubbleItem,
    SectorBubbleResponse,
    SectorHistoryItem,
    SectorHistoryResponse,
    SectorHistoryWeek,
    StockBubbleItem,
    StockBubbleResponse,
    TreemapResponse,
    TreemapSectorNode,
    TreemapStockNode,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 섹터 버블 서비스
# ---------------------------------------------------------------------------

def get_sector_bubble(
    weekly_db_path: str,
    period: str = "1w",
    market: str | None = "all",
    daily_db_path: str | None = None,
) -> SectorBubbleResponse:
    """섹터 버블 차트 API 응답을 반환한다.

    SPEC-SECTOR-METRIC-UNIFY-001 M4 — 메트릭 원천을 랭킹 봉투(/sectors/ranking
    ``data[]``)와 동일한 ``compute_sector_aggregates`` 로 통일한다(AC-SMU-001).
    4개 메트릭은 같은 원천에서 기간 키 ``period`` 를 변환 없이 써서 투영한다:

    - ``period_return`` ← ``a.returns[period].value``
    - ``excess_return`` ← ``a.excess_returns[period].value``
    - ``rs_avg`` ← ``a.rs_avg.value`` (기간 불변, INV-3)
    - ``trading_value`` ← ``a.trading_value[period].value``

    결측(``MetricValue.value is None``)은 치환 금지(§9.1)에 따라 None 그대로
    통과한다(DEC-3 — 결측 섹터 drop 없음). AG-5(최소 구성종목 5) 미달 섹터는
    봉투 ``data[]`` 와 같은 기준으로 ``excluded[]`` 에 등록되고 ``sectors[]``
    에서 빠진다(AC-SMU-015).

    M5 — 봉투 정상화(D4): 봉투 12키를 직접 나열하지 않고 랭킹 봉투와 같은
    ``envelope_fields`` 공유 헬퍼로 구성한다. ``market_filter`` 는 스키마
    기본값 "all" 이 아니라 **요청 market** 을 반영한다(유일하게 거짓말하던
    엔드포인트였다). 빈 date(guard)에서는 봉투 필드가 기본값으로 내려간다.

    Args:
        weekly_db_path: weekly SQLite DB 경로
        period: 수익률 기간 ("1w", "1m", "3m") — 라우터 쿼리값을 변환 없이
            기간 키로 쓴다.
        market: ``all``/``None``=전체, ``kospi``/``kosdaq`` (대소문자 무관).
            집계 시점 유니버스 필터에 실배선된다(``compute_sector_aggregates``
            관용 — ``member_count`` 자체가 달라진다).
        daily_db_path: 일봉 DB 경로(시총가중·거래대금 원천) — M2 배선.
            ``None`` 이면 시총 결측 취급(등가중 폴백).

    Returns:
        SectorBubbleResponse
    """
    date = _get_latest_valid_date(weekly_db_path) or ""
    aggregates = []
    excluded = []  # 가드 밖 초기화 [HARD] — M5가 envelope_fields(excluded=excluded) 배선
    result = None  # SectorAggregationResult — 빈 date 가드에서는 None 유지
    if date:
        # E-6 — 빈 date 가드(get_stock_bubble 관행). 가드가 없으면
        # date.fromisoformat('') ValueError 가 라우터 포괄 except 를 타고 503 이 된다.
        from my_chart.analysis.sector_metrics import compute_sector_aggregates
        result = compute_sector_aggregates(
            weekly_db_path, date,
            daily_db_path=daily_db_path,
            market=market,
            as_of=date,
            period=period,
            # 버블 투영은 rank_change 를 소비하지 않는다 — 기본 True 는
            # anchor(t,28) 기준일 집계를 1회 더 돌려 비용만 2배로 만든다.
            compute_rank_change=False,
        )
        aggregates = result.aggregates
        excluded = result.excluded  # E-6 branch-B 관측 원천 (M5 보존)
        if excluded:
            logger.debug("sector bubble AG-5 excluded: %s",
                         [(e.sector, e.count) for e in excluded])

    items = [
        SectorBubbleItem(
            name=a.name,
            excess_return=a.excess_returns[period].value,
            rs_avg=a.rs_avg.value,
            trading_value=a.trading_value[period].value,
            period_return=a.returns[period].value,
        )
        for a in aggregates
    ]

    # M5(D4) — 봉투 12키는 envelope_fields 공유 헬퍼로 구성한다(랭킹 봉투와 동일
    # 호출 형태). data[]/benchmark/return_window_days 는 여기서 원천 공유되며,
    # 빈 date 에서는 result=None 이므로 기본값(benchmark=None · data=[] ·
    # return_window_days 3키 전부 None)으로 폴백한다.
    return SectorBubbleResponse(
        date=date,
        period=period,
        market=market,
        sectors=items,
        **envelope_fields(
            as_of_date=date or None,
            as_of_is_partial_week=result.as_of_is_partial_week if result else None,
            return_window_days=result.return_window_days if result else None,
            market_filter=(market or "all").lower(),
            weight_cap=WEIGHT_CAP,
            benchmark=result.benchmark if result else None,
            data=aggregates,
            excluded=excluded,
            warnings=result.warnings if result else None,
            baseline_date=result.baseline_date if result else None,
        ),
    )


# ---------------------------------------------------------------------------
# 종목 버블 서비스
# ---------------------------------------------------------------------------

def get_stock_bubble(
    weekly_db_path: str,
    sector_name: str,
    period: str = "1w",
    market: str = "all",
    daily_db_path: str | None = None,
) -> StockBubbleResponse:
    """섹터 내 종목 버블 차트 API 응답을 반환한다.

    Args:
        weekly_db_path: weekly SQLite DB 경로
        sector_name: 조회할 섹터명
        period: 수익률 기간 ("1w", "1m", "3m")
        market: ``all`` / ``kospi`` / ``kosdaq`` — M6 신설(AC-SAG-039, §12.3).
            M6-gap G20 수정 — ``compute_stock_bubble`` 의 종목 유니버스 필터에
            실배선된다(더 이상 echo 전용이 아니다).
        daily_db_path: 일봉 DB 경로(시총가중 원천) — ``sector_aggregate``
            (AC-SAG-042) 산출에 쓰인다.

    Returns:
        StockBubbleResponse
    """
    date = _get_latest_valid_date(weekly_db_path) or ""
    # M6-gap G20 — market 을 실제로 종목 유니버스 필터에 배선한다(echo 미탈피).
    stocks = compute_stock_bubble(
        weekly_db_path, sector_name=sector_name, period=period, market=market)

    items = [
        StockBubbleItem(
            name=s.name,
            price_change=s.price_change,
            rs_12m=s.rs_12m,
            trading_value=s.trading_value,
            stage=s.stage,
            stage_detail=s.stage_detail,
            market_cap=s.market_cap,
            volume_ratio=s.volume_ratio,
            sector_minor=s.sector_minor,  # SPEC-SECTOR-MINOR-COLOR-001
            product=s.product,            # SPEC-STOCK-TOOLTIP-PRODUCT-001
            weight_in_sector=s.weight_in_sector,  # M6-gap G23 (AC-SAG-041)
            chg_1w=s.chg_1w,
            chg_3m=s.chg_3m,
            near_52w_high=s.near_52w_high,
        )
        for s in stocks
    ]

    # AC-SAG-042 — sector_aggregate 는 /sectors/ranking 의 동일 섹터·동일 기간
    # sector_return 과 일치해야 한다. compute_sector_ranking() 을 같은 인자로
    # 재호출해 단일 원천을 공유한다(별도 산식을 두지 않는다).
    sector_aggregate: float | None = None
    if date:
        from my_chart.analysis.sector_metrics import compute_sector_ranking
        period_attr = {"1w": "sector_return_1w", "1m": "sector_return_1m",
                       "3m": "sector_return_3m"}.get(period, "sector_return_1w")
        for r in compute_sector_ranking(weekly_db_path, date, daily_db_path, market):
            if r.name == sector_name:
                sector_aggregate = getattr(r, period_attr)
                break

    return StockBubbleResponse(
        date=date,
        sector_name=sector_name,
        period=period,
        stocks=items,
        sector_aggregate=sector_aggregate,
        market_filter=(market or "all").lower(),
        as_of_date=date or None,
    )


# ---------------------------------------------------------------------------
# RRG 서비스
# ---------------------------------------------------------------------------

def get_rrg_data(weekly_db_path: str, market: str = "all") -> RRGResponse:
    """RRG(Relative Rotation Graph) API 응답을 반환한다.

    Args:
        weekly_db_path: weekly SQLite DB 경로
        market: ``all`` / ``kospi`` / ``kosdaq`` — M6 신설(AC-SAG-039, §12.3).
            M6-gap G20 수정 — 별도 시장별 지수 저장소를 신설하지 않고,
            섹터 지수 시계열을 구성하는 종목 유니버스를 시장으로 제한해
            실제로 재계산한다(``compute_sector_price_index`` 의
            ``_build_sector_stock_map`` 필터 재사용).

    Returns:
        RRGResponse
    """
    date = _get_latest_valid_date(weekly_db_path) or ""
    sectors = compute_rrg_data(weekly_db_path, market=market)

    items = [
        RRGSectorItem(
            name=s.name,
            rs_ratio=s.rs_ratio,
            rs_momentum=s.rs_momentum,
            quadrant=s.quadrant,
            trail=[
                RRGTrailPoint(
                    date=t["date"],
                    rs_ratio=t["rs_ratio"],
                    rs_momentum=t["rs_momentum"],
                )
                for t in s.trail
            ],
        )
        for s in sectors
    ]

    # KOSPI 종가 시계열 (트레일 기간과 동일)
    from backend.schemas.sector_advanced import KospiPoint
    kospi_points: list[KospiPoint] = []
    try:
        conn = sqlite3.connect(weekly_db_path, check_same_thread=False)
        rows = conn.execute(
            """SELECT Date, Close FROM stock_prices
               WHERE Name = 'KOSPI'
               ORDER BY Date ASC"""
        ).fetchall()
        conn.close()
        kospi_points = [KospiPoint(date=r[0], close=float(r[1] or 0)) for r in rows if r[1]]
    except Exception:
        pass

    return RRGResponse(
        date=date, sectors=items, kospi=kospi_points,
        market_filter=(market or "all").lower(),
        as_of_date=date or None)


# ---------------------------------------------------------------------------
# 섹터 히스토리 서비스
# ---------------------------------------------------------------------------

def get_sector_history(
    weekly_db_path: str, weeks: int = 12,
    daily_db_path: str | None = None, market: str = "all",
) -> SectorHistoryResponse:
    """N주 섹터 랭킹 히스토리 API 응답을 반환한다.

    compute_sector_history()가 부분 데이터 날짜를 제외한 정제된
    (dates, rankings)를 반환하면, 이를 섹터별 시계열로 재구성한다.
    날짜를 별도 재조회하지 않고 compute_sector_history가 반환한 dates를
    그대로 사용하여 단일 진실 공급원(SSOT)을 보장한다.

    Args:
        weekly_db_path: weekly SQLite DB 경로
        weeks: 조회 주수 (기본 12주)
        daily_db_path: 일봉 DB 경로(시총가중 원천) — M6 신설.
        market: ``all`` / ``kospi`` / ``kosdaq`` — M6 신설(AC-SAG-039).

    Returns:
        SectorHistoryResponse — ``dates[]`` / ``span_days`` / ``rankings[date][sector]``
        (spec.md §12.3, AC-SAG-040)를 함께 실은 확장 스키마.
    """
    from my_chart.analysis.sector_metrics import compute_sector_history

    # AC-SAG-037(SN-3) — 공통 봉투 as_of_date 는 dates[-1](진행 중인 주 제외 가능성이
    # 있는 history SSOT)이 아니라, 다른 6개 엔드포인트와 동일한 공유 헬퍼를 직접
    # 호출해 정규 대표 바로 고정한다.
    as_of_date = _get_latest_valid_date(weekly_db_path)

    # SSOT: 부분 데이터 날짜가 제외된 (dates, rankings) 튜플
    dates, history_by_week = compute_sector_history(
        weekly_db_path, weeks=weeks, daily_db_path=daily_db_path, market=market)

    if not history_by_week:
        return SectorHistoryResponse(
            weeks=weeks, sectors=[], dates=[], span_days=None,
            rankings={}, market_filter=(market or "all").lower(),
            as_of_date=as_of_date)

    # 섹터별 히스토리 데이터 수집 (하위 호환 — ``sectors[]``)
    sector_history: dict[str, list[SectorHistoryWeek]] = {}
    # 전 구간에서 한 번이라도 등장한 섹터 전체 집합 — AC-SAG-040의
    # "rankings[date][sector] == null" 은 키 부재가 아니라 명시적 null 값을
    # 요구하므로, 그 날짜에 없던 섹터도 키를 만들고 값만 None 으로 둔다.
    all_sector_names: set[str] = {
        rank_item.name for week in history_by_week for rank_item in week
    }
    rankings: dict[str, dict[str, int | None]] = {}

    # dates와 history_by_week는 같은 길이·같은 순서 (SSOT 보장)
    for date, week_rankings in zip(dates, history_by_week):
        rankings[date] = {name: None for name in all_sector_names}
        for rank_item in week_rankings:
            name = rank_item.name
            rankings[date][name] = rank_item.rank
            if name not in sector_history:
                sector_history[name] = []
            sector_history[name].append(SectorHistoryWeek(
                date=date,
                rank=rank_item.rank,
                composite_score=rank_item.composite_score,
                sector_return_1w=rank_item.sector_return_1w,
                sector_excess_return_1w=rank_item.sector_excess_return_1w,
                rs_avg=rank_item.sector_rs_avg,
            ))

    sector_items = [
        SectorHistoryItem(name=name, history=history)
        for name, history in sector_history.items()
        if history
    ]

    span_days = None
    if len(dates) >= 2:
        from datetime import date as _date
        span_days = (
            _date.fromisoformat(dates[-1]) - _date.fromisoformat(dates[0])
        ).days

    return SectorHistoryResponse(
        weeks=weeks, sectors=sector_items, dates=dates, span_days=span_days,
        rankings=rankings, market_filter=(market or "all").lower(),
        as_of_date=as_of_date)


# ---------------------------------------------------------------------------
# 트리맵 서비스
# ---------------------------------------------------------------------------

def get_treemap_data(weekly_db_path: str, period: str = "1w") -> TreemapResponse:
    """트리맵 API 응답을 반환한다.

    Args:
        weekly_db_path: weekly SQLite DB 경로
        period: 수익률 기간 ("1w", "1m", "3m")

    Returns:
        TreemapResponse
    """
    date = _get_latest_valid_date(weekly_db_path) or ""
    root = compute_treemap_data(weekly_db_path, period=period)

    sector_nodes: list[TreemapSectorNode] = []
    for sector_child in root.children:
        stock_nodes = [
            TreemapStockNode(
                name=s.name,
                market_cap=s.market_cap,
                price_change=s.price_change,
                rs_12m=s.rs_12m,
                stage=s.stage,
            )
            for s in sector_child.children
        ]
        sector_nodes.append(TreemapSectorNode(
            name=sector_child.name,
            market_cap=sector_child.market_cap,
            price_change=sector_child.price_change,
            stocks=stock_nodes,
        ))

    return TreemapResponse(
        date=date,
        period=period,
        total_market_cap=root.market_cap,
        sectors=sector_nodes,
    )
