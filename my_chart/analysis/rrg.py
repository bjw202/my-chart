# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M4 — RRG(Relative Rotation Graph).

수익률 연쇄 지수(plan.md §3.4) 기반 RS-Ratio. **롤링 정규화 없음**(O-A1 결정) — 과거
z-score 구현(:mod:`my_chart.analysis.sector_advanced` — SPEC-TOPDOWN-001A 소관, 본
모듈은 이를 대체하지 않는다)과 달리 RS-Ratio 는 ``100 × 섹터지수 / 벤치마크지수`` 를
그대로 쓴다. 강세장에서 전 섹터가 100 을 상회하는 것은 결함이 아니라 정상 동작이다
(AC-SAG-031, O-A1).

핵심 계약
---------
* **RRG-1**: 섹터지수 == 벤치마크지수인 픽스처에서 ``rs_ratio == 100 ± 0.01``.
* **RRG-2**: 워밍업 구간(``lookback_weeks``)은 ``trail[]`` 에 나타나지 않는다 — 상수
  패딩 없음.
* **RRG-3**: 지수는 **수익률 연쇄**(``I(t) = I(t−1) × (1 + r(t))``)로 산출한다.
  가중치는 **직전 시점**(``w_i(t−1)``) 기준이다 — 구성종목 변동을 수익률로 오인하지
  않기 위함이다(plan.md §3.4). 날짜별 ``Σ(close×cap)/Σcap`` 재계산 방식(레벨 재계산)은
  구성종목 변동 시점에 레벨 점프를 만든다 — 본 모듈은 그 경로를 쓰지 않는다.
* **RRG-4**: 시점별 시총은 ``주식수 × 그 시점 Close`` 다. 주식수는
  ``현재시총(daily 최신 stock_meta.market_cap) / 현재주가(daily 최신 Close)`` 로 **단일
  지점**에서 역산한다(:func:`implied_shares`) — 과거 시점에 현재 스냅샷 시총을 그대로
  적용하는 경로는 존재하지 않는다. 주식수가 실제로는 시점마다 변동(유상증자·감자 등)
  할 수 있다는 한계는 O-A3 결정에 따라 ``warnings[]`` 로 상설 고지한다
  (:data:`WARNING_CONSTANT_SHARE_COUNT`) — 감추지 않고 명시한다.
"""
from __future__ import annotations

from dataclasses import dataclass

from my_chart.analysis.aggregate_types import WEIGHT_CAP
from my_chart.analysis.weighting import capped_weights

#: O-A3 — 상수 주식수 가정의 한계를 매 응답에 상설 고지한다(plan.md M4 GREEN 목록).
WARNING_CONSTANT_SHARE_COUNT = (
    "rrg_constant_share_count_assumption: 시점별 시총은 현재주가 기준 역산 주식수를 "
    "과거 종가에 곱해 산출한다(RRG-4). 유상증자·감자 등에 의한 주식수 변동은 반영되지 "
    "않는다(O-A3 결정 — 경고로 고지, 산출을 막지 않는다)."
)


@dataclass(frozen=True)
class RRGPoint:
    """RRG 궤적의 한 점(워밍업 구간 이후만 존재)."""

    date: str
    rs_ratio: float
    rs_momentum: float


@dataclass(frozen=True)
class RRGSeries:
    """단일 섹터의 RRG 궤적."""

    trail: tuple[RRGPoint, ...]
    trail_start_date: str | None


@dataclass(frozen=True)
class RRGExcluded:
    """RS-Ratio 산출 불가 섹터(AC-SAG-035) — ``rs_ratio == 100`` 대체 없이 사유와 함께 기록."""

    name: str
    reason: str


@dataclass(frozen=True)
class RRGResult:
    trail_by_sector: dict[str, RRGSeries]
    excluded: tuple[RRGExcluded, ...]
    warnings: tuple[str, ...]
    benchmark_name: str


# @MX:NOTE: [AUTO] 가중치 지연(w_i(t−1)) 은 plan.md §3.4 가 명시한 설계 결정이다 —
#   구성종목 변동을 수익률로 오인하는 현상을 막기 위함이며, 우연한 구현 세부사항이
#   아니다(AC-SAG-033 대조 단언이 이 결정 자체를 검증한다).
def chain_index(
    dates: list[str],
    weights_by_date: dict[str, dict[str, float]],
    close_by_date: dict[str, dict[str, float]],
) -> dict[str, float]:
    """수익률 연쇄 지수(규칙 RRG-3).

    ``r(t) = Σ(w_i(t−1) × ret_i(t)) / Σ w_i(t−1)``, ``I(t) = I(t−1) × (1 + r(t))``,
    ``I(t0) = 100``. ``ret_i(t) = close_i(t) / close_i(t−1) − 1`` 은 이 함수 내부에서
    직전 날짜 종가와의 비율로 유도한다 — 별도 수익률 인자를 받지 않는다.

    가중치는 **직전 시점 기준**(``w_i(t−1)``)으로 고정한다 — 매 반복에서 분자·분모
    산출에 쓰는 가중치는 "그 반복이 시작될 때의 이전 시점 가중치"이며, 현재 시점(``t``)
    의 가중치로 미리 바뀌지 않는다.

    분모는 이번 구간에 종가가 양쪽(``t−1``, ``t``) 모두 존재하는 종목의 직전 가중치
    합으로 **재정규화**한다(:func:`my_chart.analysis.weighting.weighted_mean` 과 동일
    관용) — 구성종목이 도중에 빠지거나 늘어도 남은 종목의 수익률이 동일하면 ``r(t)``
    가 흔들리지 않는다(AC-SAG-033 — 레벨 점프 방지).

    Args:
        dates: 오름차순 날짜 목록. ``dates[0]`` 이 기준 시점(``I(t0) = 100``).
        weights_by_date: 날짜별 ``{종목: 비중}``.
        close_by_date: 날짜별 ``{종목: 종가}``.

    Returns:
        ``{날짜: 지수값}``. ``dates`` 가 비었으면 빈 dict.
    """
    if not dates:
        return {}
    index: dict[str, float] = {dates[0]: 100.0}
    level = 100.0
    prev_weights = weights_by_date.get(dates[0], {})
    prev_close = close_by_date.get(dates[0], {})
    for t in dates[1:]:
        cur_close = close_by_date.get(t, {})
        num = 0.0
        den = 0.0
        for name, w in prev_weights.items():
            c0 = prev_close.get(name)
            c1 = cur_close.get(name)
            if c0 is None or c1 is None or c0 == 0 or w <= 0:
                continue
            ret = c1 / c0 - 1.0
            num += w * ret
            den += w
        r_t = (num / den) if den > 0 else 0.0
        level = level * (1.0 + r_t)
        index[t] = level
        # 다음 반복을 위해 "직전 시점" 을 지금 시점(t)으로 전진시킨다 — 가중치 지연
        # 계약(w_i(t−1))이 여기서 성립한다: 다음 반복(t+1)은 이번에 갱신된 prev_weights
        # (== 시점 t 의 가중치)를 "직전 시점" 으로 사용한다.
        prev_weights = weights_by_date.get(t, prev_weights)
        prev_close = cur_close
    return index


def implied_shares(
    market_caps: dict[str, float], current_prices: dict[str, float]
) -> dict[str, float]:
    """RRG-4 — 주식수 = 현재시총 / 현재주가(단일 지점 역산).

    ``market_caps`` / ``current_prices`` 는 모두 daily DB 의 **최신 스냅샷** 값이어야
    한다(호출자 책임). 이 함수 자체는 시점 개념을 갖지 않는다 — 항상 "현재" 값만
    받는다.
    """
    out: dict[str, float] = {}
    for name, cap in market_caps.items():
        price = current_prices.get(name)
        if price is None or price <= 0 or cap is None or cap <= 0:
            continue
        out[name] = cap / price
    return out


def historical_market_caps(
    shares: dict[str, float], close_by_date: dict[str, dict[str, float]]
) -> dict[str, dict[str, float]]:
    """RRG-4 역산 — 시점별 시총 = 주식수 × 그 시점 Close.

    ``shares`` (:func:`implied_shares` 출력) 는 전 구간에서 **상수**로 취급된다 —
    이 함수는 현재 시총을 과거에 그대로 옮기지 않는다: 각 날짜의 값은 항상
    ``shares[name] × close_by_date[date][name]`` 이며, 현재 시총(``market_caps``)
    자체는 이 함수의 인자로 전달되지 않는다(정적 스캔 대상 — AC-SAG-034).
    """
    out: dict[str, dict[str, float]] = {}
    for date, closes in close_by_date.items():
        row: dict[str, float] = {}
        for name, close in closes.items():
            sh = shares.get(name)
            if sh is None or close is None:
                continue
            row[name] = sh * close
        out[date] = row
    return out


def _rs_ratio_trail(
    dates: list[str],
    sector_index: dict[str, float],
    benchmark_index: dict[str, float],
    lookback_weeks: int,
) -> RRGSeries:
    """규칙 RRG-1/RRG-2 — RS-Ratio 궤적 + 워밍업 구간 미발행.

    ``rs_ratio(t) = 100 × 섹터지수(t) / 벤치마크지수(t)``. 모멘텀은 직전 유효 지점
    대비 단순 차분(``rs_momentum(t) = rs_ratio(t) − rs_ratio(t_prev)``)이다 — 롤링
    z-score 정규화나 상수 패딩을 쓰지 않는다(O-A1).

    워밍업: 처음 ``lookback_weeks`` 개 날짜는 ``trail[]`` 에서 제외한다. 모멘텀 산출을
    위한 직전 지점은 워밍업 구간 마지막 값을 그대로 쓴다 — 그 지점 자체는 ``trail[]``
    에 실리지 않는다("모멘텀 차분 1점 추가 제외", AC-SAG-032).
    """
    rs_by_date: dict[str, float] = {}
    for d in dates:
        si = sector_index.get(d)
        bi = benchmark_index.get(d)
        if si is None or bi is None or bi == 0:
            continue
        rs_by_date[d] = 100.0 * si / bi

    ordered = [d for d in dates if d in rs_by_date]
    if len(ordered) <= lookback_weeks:
        return RRGSeries((), None)

    points: list[RRGPoint] = []
    for i in range(lookback_weeks, len(ordered)):
        d = ordered[i]
        prev_d = ordered[i - 1]
        cur = rs_by_date[d]
        momentum = cur - rs_by_date[prev_d]
        points.append(RRGPoint(date=d, rs_ratio=cur, rs_momentum=momentum))

    return RRGSeries(tuple(points), points[0].date if points else None)


def compute_rrg(
    dates: list[str],
    sector_close_by_date: dict[str, dict[str, dict[str, float]]],
    benchmark_close_by_date: dict[str, dict[str, float]],
    market_caps: dict[str, float],
    current_prices: dict[str, float],
    cap: float = WEIGHT_CAP,
    lookback_weeks: int = 12,
    benchmark_name: str = "ALL_CAPPED",
) -> RRGResult:
    """섹터별 RRG(RS-Ratio/모멘텀) 산출 — M6 라우터 배선 이전의 함수 수준 진입점.

    Args:
        dates: 오름차순 날짜 목록(주봉 격자 history, 미완성 최신 바 제외).
        sector_close_by_date: ``{섹터명: {날짜: {종목: 종가}}}``.
        benchmark_close_by_date: ``{날짜: {종목: 종가}}`` — 섹터 그룹핑 없는 전체
            유니버스(규칙 BM-1 과 동일 관용 — 벤치마크는 섹터 집계의 특수 케이스).
        market_caps: 현재(daily 최신) 시가총액 — RRG-4 역산 입력.
        current_prices: 현재(daily 최신) 종가 — RRG-4 역산 입력(단일 지점).
        lookback_weeks: 워밍업 길이(RRG-2).

    Returns:
        :class:`RRGResult`. ``warnings`` 는 항상 :data:`WARNING_CONSTANT_SHARE_COUNT`
        를 포함한다(O-A3 — 상수 주식수 가정은 항상 성립하므로 조건부 경고가 아니다).
    """
    shares = implied_shares(market_caps, current_prices)

    bench_hist_caps = historical_market_caps(shares, benchmark_close_by_date)
    bench_weights_by_date = {
        d: capped_weights(bench_hist_caps.get(d, {}), cap=cap) for d in dates
    }
    benchmark_index = chain_index(dates, bench_weights_by_date, benchmark_close_by_date)

    trail_by_sector: dict[str, RRGSeries] = {}
    excluded: list[RRGExcluded] = []
    # 워밍업 이후 궤적 산출에 실제로 필요한 구간(모멘텀 기준점 1개 포함).
    relevant_dates = dates[max(0, lookback_weeks - 1):]
    for sector_name, close_by_date in sector_close_by_date.items():
        has_any_data = any(close_by_date.get(d) for d in relevant_dates)
        if not has_any_data:
            # 산출 대상 구간에 종가가 전혀 없다 — RS-Ratio 자체를 산출할 수 없다
            # (rs_ratio == 100 대체를 만들지 않고 즉시 결측 처리한다, AC-SAG-035).
            excluded.append(RRGExcluded(sector_name, "no_data_in_trail_window"))
            continue
        sec_hist_caps = historical_market_caps(shares, close_by_date)
        sec_weights_by_date = {
            d: capped_weights(sec_hist_caps.get(d, {}), cap=cap) for d in dates
        }
        sector_index = chain_index(dates, sec_weights_by_date, close_by_date)
        series = _rs_ratio_trail(dates, sector_index, benchmark_index, lookback_weeks)
        if not series.trail:
            excluded.append(
                RRGExcluded(sector_name, "insufficient_overlap_with_benchmark_or_warmup")
            )
            continue
        trail_by_sector[sector_name] = series

    return RRGResult(
        trail_by_sector=trail_by_sector,
        excluded=tuple(excluded),
        warnings=(WARNING_CONSTANT_SHARE_COUNT,),
        benchmark_name=benchmark_name,
    )
