"""
FnGuide S-RIM Financial Analysis Dashboard

analyze_dashboard: Compute structured dashboard sections from FnGuide data.
Returns DashboardResult containing 7 analysis sections.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from .analysis import fs_analysis
from .crawler import get_fnguide


# @MX:ANCHOR: [AUTO] Public API boundary for dashboard computation
# @MX:REASON: Primary entry point called by backend service layer (fan_in >= 3 expected)


@dataclass
class BusinessPerformance:
    """Section 1: Revenue, profit, cash flow and margin trends (4 years).

    All monetary values in 억원 (100 million KRW).
    Margin values as decimal fractions (e.g. 0.25 for 25%).
    YoY and profit_quality may be None for the oldest period.
    """

    periods: list[str]                           # e.g. ['2021/12', '2022/12', '2023/12', 'TTM']
    revenue: list[float]                         # 매출액 (4 years)
    operating_profit: list[float]                # 영업이익 (4 years)
    net_income: list[float]                      # 당기순이익 (4 years)
    controlling_profit: list[float]              # 지배주주순이익 (4 years)
    operating_cf: list[float]                    # 영업활동현금흐름 (4 years, 0 if unavailable)
    gpm: list[float]                             # 매출총이익률 (4 years, 0 if unavailable)
    opm: list[float]                             # 영업이익률 (4 years)
    npm: list[float]                             # 지배주주순이익률 (4 years)
    yoy_revenue: list[float | None]              # 매출액 YoY (None for oldest period)
    yoy_op: list[float | None]                   # 영업이익 YoY (None for oldest period)
    yoy_ni: list[float | None]                   # 당기순이익 YoY (None for oldest period)
    profit_quality: list[float | None]           # 영업CF / 영업이익 (None if 영업이익==0)


@dataclass
class HealthIndicator:
    """A single financial health metric with threshold classification."""

    name: str
    value: float | None
    threshold: str
    status: Literal["ok", "warn", "danger"]


@dataclass
class HealthIndicators:
    """Section 2: 7 financial health indicators."""

    indicators: list[HealthIndicator]


@dataclass
class BalanceSheet:
    """Section 3: B/S reclassification time series (4 years).

    financing keys: 신용조달, 외부차입, 주주몫, 비지배주주지분
    assets keys: 설비투자, 운전자산, 금융투자, 여유자금
    All values in 억원.
    """

    periods: list[str]
    financing: dict[str, list[float]]
    assets: dict[str, list[float]]


@dataclass
class RateDecomposition:
    """Section 4: 3-rate decomposition (3 years + expected).

    All rates as decimal fractions.
    ke and spread may be None when Beta is unavailable.
    """

    periods: list[str]                           # e.g. ['-2y', '-1y', 'recent', 'expected']
    operating_asset_return: list[float]          # 영업자산이익률
    non_operating_return: list[float]            # 비영업자산이익률
    borrowing_rate: list[float]                  # 차입이자율
    roe: list[float]                             # 지배주주ROE
    weighted_avg_roe: float                      # 가중평균 ROE
    ke: float | None                             # Cost of equity = Rf + Beta * MRP
    spread: float | None                         # ROE(expected) - Ke


@dataclass
class ProfitWaterfallStep:
    """A single step in the profit waterfall."""

    name: str
    value: float


@dataclass
class ProfitWaterfall:
    """Section 5: 8-step profit waterfall from expected estimates.

    Steps: operating_asset_profit, non_operating_profit, interest_expense,
           pretax_income, tax_expense, net_income, minority_profit, controlling_profit
    """

    steps: list[ProfitWaterfallStep]


@dataclass
class TrendSignal:
    """A single trend signal derived from linear regression slope."""

    name: str
    direction: Literal["up", "flat", "down"]
    description: str


@dataclass
class TrendSignals:
    """Section 6: Linear trend signals for 6 financial metrics."""

    signals: list[TrendSignal]


@dataclass
class FiveQuestion:
    """A single question from the 5-question investment screening."""

    question: str
    status: Literal["ok", "warn", "danger"]
    detail: str


@dataclass
class FiveQuestions:
    """Section 7: 5-question investment quality screening.

    verdict: 양호 (ok>=4), 보통 (ok==3), 주의 (ok<=2)
    """

    questions: list[FiveQuestion]
    verdict: Literal["양호", "보통", "주의"]


@dataclass
class ActivityRatios:
    """Section 8: Activity ratios and cash conversion cycle (4 years).

    Turnover values as float (회), days as int.
    First year is None for all metrics (requires prior year for averaging).
    """

    receivable_turnover: list[float | None]
    receivable_days: list[int | None]
    inventory_turnover: list[float | None]
    inventory_days: list[int | None]
    payable_turnover: list[float | None]
    payable_days: list[int | None]
    ccc: list[int | None]
    asset_turnover: list[float | None]
    periods: list[str]


@dataclass
class DashboardResult:
    """Complete S-RIM financial dashboard result for a single stock.

    Sections 2-8 are optional: None when data is unavailable
    (e.g. financial companies with incompatible B/S structure).
    """

    code: str
    company_name: str
    business_performance: BusinessPerformance | None = None
    health_indicators: HealthIndicators | None = None
    balance_sheet: BalanceSheet | None = None
    rate_decomposition: RateDecomposition | None = None
    profit_waterfall: ProfitWaterfall | None = None
    trend_signals: TrendSignals | None = None
    five_questions: FiveQuestions | None = None
    activity_ratios: ActivityRatios | None = None


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────


def _safe_loc(df: pd.DataFrame, row: str) -> pd.Series | None:
    """Return df.loc[row] or None if row is missing."""
    try:
        return df.loc[row]
    except KeyError:
        return None


def _yoy(current: float, previous: float) -> float | None:
    """Compute YoY growth rate. Returns None if previous is 0."""
    if previous == 0:
        return None
    return (current - previous) / abs(previous)


def _calc_slope(values: list[float]) -> float:
    """Compute linear regression slope via least-squares formula."""
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _indicator_status(
    value: float,
    thresholds: tuple[float, float],
    direction: Literal["lower_is_better", "higher_is_better"],
) -> Literal["ok", "warn", "danger"]:
    """Classify a metric into ok/warn/danger based on thresholds.

    Args:
        value: The metric value (ratio, e.g. 0.3 for 30%).
        thresholds: (warn_boundary, danger_boundary) as fractions.
        direction: 'lower_is_better' or 'higher_is_better'.

    Returns:
        'ok', 'warn', or 'danger'.
    """
    low, high = thresholds
    if direction == "lower_is_better":
        if value < low:
            return "ok"
        elif value < high:
            return "warn"
        else:
            return "danger"
    else:
        if value > high:
            return "ok"
        elif value > low:
            return "warn"
        else:
            return "danger"


# ─────────────────────────────────────────────────────────────
# Section calculators
# ─────────────────────────────────────────────────────────────


def _calc_business_performance(
    df_fs_ann: pd.DataFrame,
) -> BusinessPerformance:
    """Compute Section 1: BusinessPerformance from annual financial statements."""
    col = list(df_fs_ann.columns)

    revenue = [float(df_fs_ann.loc["매출액", c]) for c in col]
    op_profit = [float(df_fs_ann.loc["영업이익", c]) for c in col]
    net_income = [float(df_fs_ann.loc["당기순이익", c]) for c in col]

    # Controlling profit (지배주주순이익) — fallback to net income for IFRS(별도)
    ctrl_series = _safe_loc(df_fs_ann, "지배주주순이익")
    if ctrl_series is not None:
        controlling_profit = [float(ctrl_series[c]) for c in col]
    else:
        controlling_profit = net_income[:]

    # Operating cash flow — optional row
    ocf_series = _safe_loc(df_fs_ann, "영업활동으로인한현금흐름")
    if ocf_series is not None:
        operating_cf = [float(ocf_series[c]) for c in col]
    else:
        operating_cf = [0.0] * len(col)

    # Gross profit margin — optional row
    gp_series = _safe_loc(df_fs_ann, "매출총이익")
    if gp_series is not None and all(revenue[i] != 0 for i in range(len(col))):
        gpm = [float(gp_series[c]) / rev if rev != 0 else 0.0
               for c, rev in zip(col, revenue)]
    else:
        gpm = [0.0] * len(col)

    opm = [op / rev if rev != 0 else 0.0 for op, rev in zip(op_profit, revenue)]
    npm = [cp / rev if rev != 0 else 0.0 for cp, rev in zip(controlling_profit, revenue)]

    # YoY calculations
    yoy_revenue: list[float | None] = [None]
    yoy_op: list[float | None] = [None]
    yoy_ni: list[float | None] = [None]
    for i in range(1, len(col)):
        yoy_revenue.append(_yoy(revenue[i], revenue[i - 1]))
        yoy_op.append(_yoy(op_profit[i], op_profit[i - 1]))
        yoy_ni.append(_yoy(net_income[i], net_income[i - 1]))

    # Profit quality = 영업CF / 영업이익
    profit_quality: list[float | None] = []
    for i in range(len(col)):
        if op_profit[i] == 0:
            profit_quality.append(None)
        else:
            profit_quality.append(operating_cf[i] / op_profit[i])

    return BusinessPerformance(
        periods=[str(c) for c in col],
        revenue=revenue,
        operating_profit=op_profit,
        net_income=net_income,
        controlling_profit=controlling_profit,
        operating_cf=operating_cf,
        gpm=gpm,
        opm=opm,
        npm=npm,
        yoy_revenue=yoy_revenue,
        yoy_op=yoy_op,
        yoy_ni=yoy_ni,
        profit_quality=profit_quality,
    )


def _calc_health_indicators(
    df_anal: pd.DataFrame,
    df_invest: pd.DataFrame,
    df_fs_ann: pd.DataFrame,
    col_recent: str,
) -> HealthIndicators:
    """Compute Section 2: 7 HealthIndicators from the most recent period."""

    def _get(df: pd.DataFrame, row: str, col: str) -> float:
        try:
            return float(df.loc[row, col])
        except (KeyError, TypeError):
            return 0.0

    external_debt = _get(df_anal, "외부차입", col_recent)
    shareholders_equity = _get(df_anal, "주주몫", col_recent)
    op_liabilities = _get(df_anal, "영업부채", col_recent)
    total_assets = _get(df_fs_ann, "자산", col_recent)
    slack = _get(df_invest, "여유자금", col_recent)
    op_assets = _get(df_anal, "영업자산", col_recent)
    op_profit = _get(df_anal, "영업이익", col_recent)
    interest_expense = _get(df_anal, "이자비용", col_recent)
    net_income = float(df_anal.loc["지배주주순이익", col_recent]) if "지배주주순이익" in df_anal.index else 0.0
    minority_profit = float(df_anal.loc["비지배주주순이익", col_recent]) if "비지배주주순이익" in df_anal.index else 0.0

    indicators: list[HealthIndicator] = []

    # 1. 외부차입/자기자본 (ok <20%, warn 20-50%, danger >50%)
    ratio1 = external_debt / shareholders_equity if shareholders_equity != 0 else 0.0
    indicators.append(HealthIndicator(
        name="외부차입/자기자본",
        value=ratio1,
        threshold="ok:<20% warn:20-50% danger:>50%",
        status=_indicator_status(ratio1, (0.20, 0.50), "lower_is_better"),
    ))

    # 2. 부채비율 (ok <100%, warn 100-200%, danger >200%)
    total_debt = external_debt + op_liabilities
    ratio2 = total_debt / shareholders_equity if shareholders_equity != 0 else 0.0
    indicators.append(HealthIndicator(
        name="부채비율",
        value=ratio2,
        threshold="ok:<100% warn:100-200% danger:>200%",
        status=_indicator_status(ratio2, (1.00, 2.00), "lower_is_better"),
    ))

    # 3. 차입금의존도 (ok <5%, warn 5-20%, danger >20%)
    ratio3 = external_debt / total_assets if total_assets != 0 else 0.0
    indicators.append(HealthIndicator(
        name="차입금의존도",
        value=ratio3,
        threshold="ok:<5% warn:5-20% danger:>20%",
        status=_indicator_status(ratio3, (0.05, 0.20), "lower_is_better"),
    ))

    # 4. 순차입금의존도 (ok <0, warn 0-10%, danger >10%)
    net_debt = external_debt - slack
    ratio4 = net_debt / total_assets if total_assets != 0 else 0.0
    indicators.append(HealthIndicator(
        name="순차입금의존도",
        value=ratio4,
        threshold="ok:<0 warn:0-10% danger:>10%",
        status=_indicator_status(ratio4, (0.0, 0.10), "lower_is_better"),
    ))

    # 5. 이자보상배율 (ok >10x, warn 3-10x, danger <3x; interest==0 → ok)
    if interest_expense == 0:
        icr_value = None
        icr_status: Literal["ok", "warn", "danger"] = "ok"
        icr_threshold = "ok:interest=0"
    else:
        icr = op_profit / interest_expense
        icr_value = icr
        icr_status = _indicator_status(icr, (3.0, 10.0), "higher_is_better")
        icr_threshold = "ok:>10x warn:3-10x danger:<3x"
    indicators.append(HealthIndicator(
        name="이자보상배율",
        value=icr_value,
        threshold=icr_threshold,
        status=icr_status,
    ))

    # 6. 영업자산비율 (ok >70%, warn 50-70%, danger <50%)
    ratio6 = op_assets / total_assets if total_assets != 0 else 0.0
    indicators.append(HealthIndicator(
        name="영업자산비율",
        value=ratio6,
        threshold="ok:>70% warn:50-70% danger:<50%",
        status=_indicator_status(ratio6, (0.50, 0.70), "higher_is_better"),
    ))

    # 7. 비지배귀속비율 (ok <5%, warn 5-20%, danger >20%)
    total_profit = net_income + minority_profit
    ratio7 = minority_profit / total_profit if total_profit != 0 else 0.0
    ratio7 = max(0.0, ratio7)  # prevent negative from signed minority profit
    indicators.append(HealthIndicator(
        name="비지배귀속비율",
        value=ratio7,
        threshold="ok:<5% warn:5-20% danger:>20%",
        status=_indicator_status(ratio7, (0.05, 0.20), "lower_is_better"),
    ))

    return HealthIndicators(indicators=indicators)


def _calc_balance_sheet(
    df_financing: pd.DataFrame,
    df_invest: pd.DataFrame,
    col: list[str],
) -> BalanceSheet:
    """Compute Section 3: B/S reclassification time series."""

    def _series(df: pd.DataFrame, row: str) -> list[float]:
        try:
            return [float(df.loc[row, c]) for c in col]
        except KeyError:
            return [0.0] * len(col)

    # 주주몫 = 유보이익 + 주주투자
    yobo = _series(df_financing, "유보이익")
    juju_invest = _series(df_financing, "주주투자")
    shareholders_equity = [y + j for y, j in zip(yobo, juju_invest)]

    financing = {
        "신용조달": _series(df_financing, "신용조달"),
        "외부차입": _series(df_financing, "외부차입"),
        "주주몫": shareholders_equity,
        "비지배주주지분": _series(df_financing, "비지배주주지분"),
    }

    assets = {
        "설비투자": _series(df_invest, "설비투자"),
        "운전자산": _series(df_invest, "운전자산"),
        "금융투자": _series(df_invest, "금융투자"),
        "여유자금": _series(df_invest, "여유자금"),
    }

    return BalanceSheet(
        periods=[str(c) for c in col],
        financing=financing,
        assets=assets,
    )


def _calc_rate_decomposition(
    df_anal: pd.DataFrame,
    report: dict,
) -> RateDecomposition:
    """Compute Section 4: 3-rate decomposition with CAPM-based Ke."""
    col = df_anal.columns
    # col[1], col[2], col[3] = -2y, -1y, recent; '예상' = expected
    yearly_cols = [c for c in col if "/" in str(c)]
    # Use last 3 yearly columns
    y_cols = yearly_cols[-3:] if len(yearly_cols) >= 3 else yearly_cols
    periods = [str(c) for c in y_cols] + ["예상"]

    def _rate(metric: str, col_key: str) -> float:
        try:
            return float(df_anal.loc[metric, col_key])
        except (KeyError, TypeError):
            return 0.0

    operating_asset_return = [_rate("영업자산이익률", c) for c in y_cols] + [_rate("영업자산이익률", "예상")]
    non_operating_return = [_rate("비영업자산이익률", c) for c in y_cols] + [_rate("비영업자산이익률", "예상")]
    borrowing_rate = [_rate("차입이자율", c) for c in y_cols] + [_rate("차입이자율", "예상")]
    roe = [_rate("지배주주ROE", c) for c in y_cols] + [_rate("지배주주ROE", "예상")]

    weighted_avg_roe = _rate("지배주주ROE", "가중평균")

    # CAPM: Ke = Rf + Beta * MRP (Rf=3.5%, MRP=6%)
    rf = 0.035
    mrp = 0.06
    beta: float | None = None
    for key in ("베타", "베타(1년)"):
        raw = report.get(key)
        if raw is not None:
            try:
                beta = float(raw)
                break
            except (ValueError, TypeError):
                pass

    if beta is not None:
        ke: float | None = rf + beta * mrp
        roe_expected = roe[-1] if roe else 0.0
        spread: float | None = roe_expected - ke
    else:
        ke = None
        spread = None

    return RateDecomposition(
        periods=periods,
        operating_asset_return=operating_asset_return,
        non_operating_return=non_operating_return,
        borrowing_rate=borrowing_rate,
        roe=roe,
        weighted_avg_roe=weighted_avg_roe,
        ke=ke,
        spread=spread,
    )


def _calc_profit_waterfall(df_anal: pd.DataFrame) -> ProfitWaterfall:
    """Compute Section 5: 8-step profit waterfall from expected estimates."""

    def _est(metric: str) -> float:
        try:
            return float(df_anal.loc[metric, "예상"])
        except (KeyError, TypeError):
            return 0.0

    op_profit = _est("영업이익")
    non_op_profit = _est("비영업이익")
    interest_exp = _est("이자비용")
    pretax = op_profit + non_op_profit - interest_exp
    tax = _est("법인세비용")
    net_income = _est("당기순이익")
    minority = _est("비지배주주순이익")
    controlling = _est("지배주주순이익")

    steps = [
        ProfitWaterfallStep(name="영업이익", value=op_profit),
        ProfitWaterfallStep(name="비영업이익", value=non_op_profit),
        ProfitWaterfallStep(name="이자비용", value=interest_exp),
        ProfitWaterfallStep(name="세전이익", value=pretax),
        ProfitWaterfallStep(name="법인세비용", value=tax),
        ProfitWaterfallStep(name="당기순이익", value=net_income),
        ProfitWaterfallStep(name="비지배주주순이익", value=minority),
        ProfitWaterfallStep(name="지배주주순이익", value=controlling),
    ]

    return ProfitWaterfall(steps=steps)


def _calc_trend_signals(
    df_anal: pd.DataFrame,
    df_fs_ann: pd.DataFrame,
) -> TrendSignals:
    """Compute Section 6: Linear trend signals from 3-year data."""
    yearly_cols = [c for c in df_fs_ann.columns if "/" in str(c)]
    recent_cols = yearly_cols[-3:] if len(yearly_cols) >= 3 else yearly_cols

    def _slope_for_df_fs(row: str) -> float:
        try:
            vals = [float(df_fs_ann.loc[row, c]) for c in recent_cols]
            return _calc_slope(vals)
        except (KeyError, TypeError):
            return 0.0

    def _slope_for_df_anal(row: str) -> float:
        try:
            vals = [float(df_anal.loc[row, c]) for c in recent_cols]
            return _calc_slope(vals)
        except (KeyError, TypeError):
            return 0.0

    # Threshold: use relative threshold based on typical value magnitude
    # For revenue (in 억), meaningful slope > 0 means growing
    # For ratios, use absolute 0.001 (0.1%) as threshold
    def _direction(slope: float, threshold: float = 0.0) -> Literal["up", "flat", "down"]:
        if slope > threshold:
            return "up"
        elif slope < -threshold:
            return "down"
        return "flat"

    # 1. 매출액 trend
    rev_slope = _slope_for_df_fs("매출액")
    rev_dir = _direction(rev_slope)

    # 2. 영업이익률 trend
    opm_vals = []
    for c in recent_cols:
        try:
            rev = float(df_fs_ann.loc["매출액", c])
            op = float(df_fs_ann.loc["영업이익", c])
            opm_vals.append(op / rev if rev != 0 else 0.0)
        except (KeyError, TypeError):
            opm_vals.append(0.0)
    opm_slope = _calc_slope(opm_vals)
    opm_dir = _direction(opm_slope)

    # 3. ROE trend
    roe_slope = _slope_for_df_anal("지배주주ROE")
    roe_dir = _direction(roe_slope)

    # 4. 외부차입 trend
    debt_slope = _slope_for_df_anal("외부차입")
    debt_dir = _direction(debt_slope)
    # For debt: increasing is bad — invert label for meaning
    if debt_dir == "up":
        debt_signal_dir: Literal["up", "flat", "down"] = "up"
    elif debt_dir == "down":
        debt_signal_dir = "down"
    else:
        debt_signal_dir = "flat"

    # 5. 영업자산비율 trend
    oa_ratio_vals = []
    try:
        asset_row = df_fs_ann.loc["자산"]
        oa_row = df_anal.loc["영업자산"]
        for c in recent_cols:
            assets = float(asset_row[c])
            oa = float(oa_row[c])
            oa_ratio_vals.append(oa / assets if assets != 0 else 0.0)
    except (KeyError, TypeError):
        oa_ratio_vals = [0.0] * len(recent_cols)
    oar_slope = _calc_slope(oa_ratio_vals)
    oar_dir = _direction(oar_slope)

    # 6. 이자보상배율 trend
    icr_vals = []
    try:
        for c in recent_cols:
            op = float(df_anal.loc["영업이익", c])
            ie = float(df_anal.loc["이자비용", c])
            icr_vals.append(op / ie if ie != 0 else 0.0)
    except (KeyError, TypeError):
        icr_vals = [0.0] * len(recent_cols)
    icr_slope = _calc_slope(icr_vals)
    icr_dir = _direction(icr_slope)

    signals = [
        TrendSignal(name="매출액", direction=rev_dir,
                    description=f"3년 추세 기울기: {rev_slope:+.1f}억원/년"),
        TrendSignal(name="영업이익률", direction=opm_dir,
                    description=f"3년 추세 기울기: {opm_slope:+.4f}/년"),
        TrendSignal(name="ROE", direction=roe_dir,
                    description=f"3년 추세 기울기: {roe_slope:+.4f}/년"),
        TrendSignal(name="외부차입", direction=debt_signal_dir,
                    description=f"3년 추세 기울기: {debt_slope:+.1f}억원/년"),
        TrendSignal(name="영업자산비율", direction=oar_dir,
                    description=f"3년 추세 기울기: {oar_slope:+.4f}/년"),
        TrendSignal(name="이자보상배율", direction=icr_dir,
                    description=f"3년 추세 기울기: {icr_slope:+.4f}/년"),
    ]

    return TrendSignals(signals=signals)


def _calc_five_questions(
    df_anal: pd.DataFrame,
    df_fs_ann: pd.DataFrame,
    col_recent: str,
) -> FiveQuestions:
    """Compute Section 7: 5-question investment quality screening.

    REQ-8 from SPEC-DASHBOARD-001.
    """

    def _get_anal(row: str) -> float:
        try:
            return float(df_anal.loc[row, col_recent])
        except (KeyError, TypeError):
            return 0.0

    questions: list[FiveQuestion] = []

    # Q1: 영업자산이익률 > 차입이자율 (수익성 > 조달비용)
    oa_return = float(df_anal.loc["영업자산이익률", col_recent]) if "영업자산이익률" in df_anal.index else 0.0
    borrow_rate = float(df_anal.loc["차입이자율", col_recent]) if "차입이자율" in df_anal.index else 0.0
    spread_q1 = oa_return - borrow_rate
    q1_ok = oa_return > borrow_rate
    questions.append(FiveQuestion(
        question="영업자산이익률 > 차입이자율?",
        status="ok" if q1_ok else "danger",
        detail=f"영업자산이익률 {oa_return:.1%} vs 차입이자율 {borrow_rate:.1%} (스프레드: {spread_q1:+.1%})",
    ))

    # Q2: ROE > Ke (ROE 가 자본비용을 상회하는가)
    # Use 가중평균 ROE vs a simple benchmark of 8% when Ke unavailable
    # For Q2 we use recent ROE
    roe_recent = float(df_anal.loc["지배주주ROE", col_recent]) if "지배주주ROE" in df_anal.index else 0.0
    # @MX:NOTE: [AUTO] Using 8% as minimum ROE threshold when CAPM Ke unavailable
    ke_benchmark = 0.08
    q2_ok = roe_recent > ke_benchmark
    questions.append(FiveQuestion(
        question="ROE > 최소요구수익률(8%)?",
        status="ok" if q2_ok else ("warn" if roe_recent > 0 else "danger"),
        detail=f"지배주주ROE {roe_recent:.1%} vs 기준 {ke_benchmark:.1%}",
    ))

    # Q3: 외부차입/자기자본 < 50% (재무 안정성)
    external_debt = _get_anal("외부차입")
    se = _get_anal("주주몫")
    debt_ratio = external_debt / se if se != 0 else 0.0
    questions.append(FiveQuestion(
        question="외부차입/자기자본 < 50%?",
        status="ok" if debt_ratio < 0.20 else ("warn" if debt_ratio < 0.50 else "danger"),
        detail=f"외부차입/자기자본 = {debt_ratio:.1%}",
    ))

    # Q4: 영업CF > 영업이익 (이익 현금화 품질)
    op_profit = _get_anal("영업이익")
    ocf_series = _safe_loc(df_fs_ann, "영업활동으로인한현금흐름")
    if ocf_series is not None:
        ocf = float(ocf_series[col_recent])
    else:
        ocf = 0.0
    q4_ok = ocf > op_profit and op_profit > 0
    pq = (ocf / op_profit) if op_profit != 0 else 0.0
    questions.append(FiveQuestion(
        question="영업CF > 영업이익? (이익 품질)",
        status="ok" if q4_ok else ("warn" if pq > 0.5 else "danger"),
        detail=f"영업CF {ocf:,.0f}억 vs 영업이익 {op_profit:,.0f}억 (비율: {pq:.1%})",
    ))

    # Q5: 지배주주ROE 3년 평균 > 8% (지속 수익성)
    yearly_cols = [c for c in df_fs_ann.columns if "/" in str(c)]
    recent_3 = yearly_cols[-3:] if len(yearly_cols) >= 3 else yearly_cols
    roe_vals = []
    for c in recent_3:
        try:
            roe_vals.append(float(df_anal.loc["지배주주ROE", c]))
        except (KeyError, TypeError):
            pass
    avg_roe = sum(roe_vals) / len(roe_vals) if roe_vals else 0.0
    q5_ok = avg_roe > 0.08
    questions.append(FiveQuestion(
        question="3년 평균 ROE > 8%? (지속 수익성)",
        status="ok" if q5_ok else ("warn" if avg_roe > 0 else "danger"),
        detail=f"3년 평균 지배주주ROE = {avg_roe:.1%}",
    ))

    ok_count = sum(1 for q in questions if q.status == "ok")
    if ok_count >= 4:
        verdict: Literal["양호", "보통", "주의"] = "양호"
    elif ok_count == 3:
        verdict = "보통"
    else:
        verdict = "주의"

    return FiveQuestions(questions=questions, verdict=verdict)


def _calc_activity_ratios(df_fs_ann: pd.DataFrame) -> ActivityRatios:
    """Compute Section 8: Activity ratios and cash conversion cycle."""
    col = list(df_fs_ann.columns)
    n = len(col)

    receivable = _safe_loc(df_fs_ann, "매출채권및기타유동채권")
    inventory = _safe_loc(df_fs_ann, "재고자산")
    payable = _safe_loc(df_fs_ann, "매입채무및기타유동채무")
    cogs_row = _safe_loc(df_fs_ann, "매출원가")
    revenue_row = _safe_loc(df_fs_ann, "매출액")
    asset_row = _safe_loc(df_fs_ann, "자산")

    rec_turnover: list[float | None] = []
    rec_days: list[int | None] = []
    inv_turnover: list[float | None] = []
    inv_days: list[int | None] = []
    pay_turnover: list[float | None] = []
    pay_days: list[int | None] = []
    ast_turnover: list[float | None] = []
    ccc_list: list[int | None] = []

    for i in range(n):
        c = col[i]

        # Receivable turnover
        rt = None
        rd = None
        if i > 0 and receivable is not None and revenue_row is not None:
            avg = (float(receivable[col[i - 1]]) + float(receivable[c])) / 2
            rev = float(revenue_row[c])
            if avg > 0:
                rt = round(rev / avg, 2)
                rd = round(365 / rt)
        rec_turnover.append(rt)
        rec_days.append(rd)

        # Inventory turnover
        it = None
        id_ = None
        if i > 0 and inventory is not None and cogs_row is not None:
            avg = (float(inventory[col[i - 1]]) + float(inventory[c])) / 2
            cogs = float(cogs_row[c])
            if avg > 0 and cogs > 0:
                it = round(cogs / avg, 2)
                id_ = round(365 / it)
        inv_turnover.append(it)
        inv_days.append(id_)

        # Payable turnover
        pt = None
        pd_ = None
        if i > 0 and payable is not None and cogs_row is not None:
            avg = (float(payable[col[i - 1]]) + float(payable[c])) / 2
            cogs = float(cogs_row[c])
            if avg > 0 and cogs > 0:
                pt = round(cogs / avg, 2)
                pd_ = round(365 / pt)
        pay_turnover.append(pt)
        pay_days.append(pd_)

        # Asset turnover
        at = None
        if i > 0 and asset_row is not None and revenue_row is not None:
            avg = (float(asset_row[col[i - 1]]) + float(asset_row[c])) / 2
            rev = float(revenue_row[c])
            if avg > 0:
                at = round(rev / avg, 2)
        ast_turnover.append(at)

        # CCC
        if rd is not None and id_ is not None and pd_ is not None:
            ccc_list.append(rd + id_ - pd_)
        else:
            ccc_list.append(None)

    return ActivityRatios(
        receivable_turnover=rec_turnover,
        receivable_days=rec_days,
        inventory_turnover=inv_turnover,
        inventory_days=inv_days,
        payable_turnover=pay_turnover,
        payable_days=pay_days,
        ccc=ccc_list,
        asset_turnover=ast_turnover,
        periods=[str(c) for c in col],
    )


# ─────────────────────────────────────────────────────────────
# Main API
# ─────────────────────────────────────────────────────────────


def analyze_dashboard(code: str) -> DashboardResult:
    """Compute complete S-RIM financial dashboard for a stock.

    # @MX:ANCHOR: [AUTO] Primary dashboard computation function
    # @MX:REASON: Called by backend API service layer (fan_in >= 3 expected)
    # @MX:SPEC: SPEC-DASHBOARD-001, SPEC-DASHBOARD-002

    Args:
        code: 6-digit KRX stock code (e.g., '005930').

    Returns:
        DashboardResult with 8 analysis sections.

    Raises:
        ValueError: if code is not 6 digits.
        ConnectionError: if FnGuide crawling fails.
    """
    if not code.isdigit() or len(code) != 6:
        raise ValueError(f"Invalid stock code: {code!r}. Must be 6 digits.")

    # Data acquisition
    df_fs_ann, df_fs_quar, _, _, _, report, _ = get_fnguide(code)  # type: ignore[misc]

    col = list(df_fs_ann.columns)
    col_recent = col[-1]  # Most recent year (e.g., '2023/12')

    # Company name from report
    company_name = str(report.get("종목명", code))

    # Financial companies (banks, insurance) may lack standard rows like '매출액'.
    # Wrap each section in try/except to return partial results.
    business_performance: BusinessPerformance | None = None
    health_indicators: HealthIndicators | None = None
    balance_sheet: BalanceSheet | None = None
    rate_decomposition: RateDecomposition | None = None
    profit_waterfall: ProfitWaterfall | None = None
    trend_signals: TrendSignals | None = None
    five_questions: FiveQuestions | None = None
    activity_ratios: ActivityRatios | None = None

    # Section 1
    try:
        business_performance = _calc_business_performance(df_fs_ann)
    except Exception:
        pass

    # Sections 2-7 depend on fs_analysis which may fail for financial companies
    try:
        df_anal, df_invest, df_financing = fs_analysis(df_fs_ann, df_fs_quar)

        # Section 2
        health_indicators = _calc_health_indicators(df_anal, df_invest, df_fs_ann, col_recent)

        # Section 3
        balance_sheet = _calc_balance_sheet(df_financing, df_invest, col)

        # Section 4
        rate_decomposition = _calc_rate_decomposition(df_anal, report)

        # Section 5
        profit_waterfall = _calc_profit_waterfall(df_anal)

        # Section 6
        trend_signals = _calc_trend_signals(df_anal, df_fs_ann)

        # Section 7
        five_questions = _calc_five_questions(df_anal, df_fs_ann, col_recent)
    except Exception:
        pass

    # Section 8 (depends only on df_fs_ann, independent of fs_analysis)
    try:
        activity_ratios = _calc_activity_ratios(df_fs_ann)
    except Exception:
        pass

    return DashboardResult(
        code=code,
        company_name=company_name,
        business_performance=business_performance,
        health_indicators=health_indicators,
        balance_sheet=balance_sheet,
        rate_decomposition=rate_decomposition,
        profit_waterfall=profit_waterfall,
        trend_signals=trend_signals,
        five_questions=five_questions,
        activity_ratios=activity_ratios,
    )
