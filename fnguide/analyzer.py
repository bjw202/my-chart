"""
종목 재무상태 종합 분석

analyze_comp: FnGuide 데이터를 수집하고 재무상태를 분석하여 CompResult를 반환한다.
차트·시각화 코드를 포함하지 않으며, 순수 계산만 담당한다.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field

from .analysis import fs_analysis
from .crawler import get_fnguide


@dataclass
class RateHistory:
    """이익률/ROE의 3년 추이와 예상값"""

    year_minus_2: float  # -2년
    year_minus_1: float  # -1년
    recent: float        # 최근 (기준년도)
    expected: float      # 예상


@dataclass
class ProfitTrend:
    """매출/영업이익/순이익 추이 (연간 + Trailing 12M)"""

    periods: list[str]                    # 기간 라벨 ['2021/12', '2022/12', ...]
    revenue: list[float] = field(default_factory=list)            # 매출액 (억원)
    operating_profit: list[float] = field(default_factory=list)   # 영업이익 (억원)
    net_income: list[float] = field(default_factory=list)         # 당기순이익 (억원)
    operating_margin: list[float] = field(default_factory=list)   # 영업이익률 (%)


@dataclass
class CompResult:
    """종목 재무상태 분석 결과.

    재무구조, 이익률, 수익성 지표에 집중한다.
    """

    # ── 기본 정보
    code: str
    market_cap: int           # 시가총액 (억원)
    shares: int               # 발행주식수 (보통주 + 우선주 - 자기주식)

    # ── 수익성 지표
    trailing_eps: float       # Trailing 12M EPS (원)
    book_value_per_share: int # 주당 순자산 (원, BPS)

    # ── 매출/영업이익/순이익 추이
    profit_trend: ProfitTrend

    # ── 이익률 추이 (3년 + 예상)
    operating_asset_return: RateHistory   # 영업자산이익률
    non_operating_return: RateHistory     # 비영업자산이익률
    borrowing_rate: RateHistory           # 차입이자율
    roe: RateHistory                      # 지배주주ROE

    # ── 자본 구성 (최근 기준년도, 억원)
    shareholders_equity: int   # 주주몫
    minority_interest: int     # 비지배주주지분
    operating_liabilities: int # 영업부채
    external_debt: int         # 외부차입

    # ── 자산 구성 (최근 기준년도, 억원)
    operating_assets: int      # 영업자산
    non_operating_assets: int  # 비영업자산

    # ── 이익 구성 (예상, 억원)
    operating_profit: int      # 영업이익
    non_operating_profit: int  # 비영업이익
    interest_expense: int      # 이자비용
    tax_expense: int           # 법인세비용
    controlling_profit: int    # 지배주주순이익
    minority_profit: int       # 비지배주주순이익

    # ── 순현금 포지션
    net_cash: float            # 순현금 = 여유자금 - 단기/장기 차입부채 (억원)
    net_cash_ratio: float      # 순현금 / 시가총액 (%)

    # ── FnGuide 제공 밸류에이션 지표
    per_fnguide: str
    per_12m: str
    industry_per: str
    pbr: str
    dividend_yield: str

    # ── 사업 요약
    summary: str

    def __str__(self) -> str:
        """분석 결과 텍스트 요약"""
        # 매출/영업이익/순이익 추이
        trend = self.profit_trend
        trend_lines = ["── 매출/이익 추이 (억원) ─────────────────"]
        header = "  {:>10s}" + " {:>10s}" * len(trend.periods)
        trend_lines.append(header.format("", *trend.periods))
        trend_lines.append(header.format("매출액", *[f"{v:,.0f}" for v in trend.revenue]))
        trend_lines.append(header.format("영업이익", *[f"{v:,.0f}" for v in trend.operating_profit]))
        trend_lines.append(header.format("순이익", *[f"{v:,.0f}" for v in trend.net_income]))
        trend_lines.append(header.format("영업이익률", *[f"{v:.1f}%" for v in trend.operating_margin]))

        lines = [
            f"[{self.code}] 시가총액: {self.market_cap:,}억원",
            f"Trailing EPS: {self.trailing_eps:,.0f}원  BPS: {self.book_value_per_share:,}원",
            "",
            *trend_lines,
            "",
            "── 이익률 추이 (예상) ────────────────────",
            f"  영업자산이익률: {self.operating_asset_return.expected:.1%}  "
            f"| 비영업자산이익률: {self.non_operating_return.expected:.1%}",
            f"  차입이자율:      {self.borrowing_rate.expected:.1%}  "
            f"| 지배주주ROE:     {self.roe.expected:.1%}",
            "",
            "── 자본 구성 (억원) ──────────────────────",
            f"  주주몫: {self.shareholders_equity:,}  "
            f"비지배: {self.minority_interest:,}  "
            f"영업부채: {self.operating_liabilities:,}  "
            f"외부차입: {self.external_debt:,}",
            "",
            "── 자산 구성 (억원) ──────────────────────",
            f"  영업자산: {self.operating_assets:,}  "
            f"비영업자산: {self.non_operating_assets:,}",
            "",
            "── 예상 이익 구성 (억원) ─────────────────",
            f"  영업이익: {self.operating_profit:,}  "
            f"비영업이익: {self.non_operating_profit:,}  "
            f"이자비용: {self.interest_expense:,}  "
            f"법인세: {self.tax_expense:,}",
            f"  지배주주순이익: {self.controlling_profit:,}",
            "",
            "── 순현금 ────────────────────────────────",
            f"  순현금: {self.net_cash:,.0f}억원  비율: {self.net_cash_ratio:.1f}%",
            "",
            "── FnGuide 지표 ──────────────────────────",
            f"  PER: {self.per_fnguide}  12M PER: {self.per_12m}  "
            f"업종PER: {self.industry_per}  PBR: {self.pbr}  "
            f"배당수익률: {self.dividend_yield}",
        ]
        return "\n".join(lines)


def analyze_comp(code: str) -> CompResult:
    """FnGuide 데이터를 수집하고 재무상태를 종합 분석한다.

    재무구조·이익률·수익성 지표 분석에 집중한다.

    Args:
        code: 종목 코드 (6자리, 예: '005930')

    Returns:
        CompResult: 재무상태 분석 결과
    """
    # ── 데이터 수집
    df_fs_ann, df_fs_quar, _, _, _, report, account_type = get_fnguide(code)
    df_anal, df_invest = fs_analysis(df_fs_ann, df_fs_quar)

    col = df_fs_ann.columns  # ['YYYY/MM', 'YYYY/MM', 'YYYY/MM', 'YYYY/MM']

    # ── 기본 수치
    market_cap: int = int(report["시가총액(상장예정포함,억원)"])
    shares: int = (
        int(report["발행주식수(보통주)"])
        + int(report["발행주식수(우선주)"])
        - int(report["자기주식"])
    )

    # ── Trailing 12M EPS / BPS
    if account_type == "IFRS(연결)":
        trailing_net_income = float(df_fs_quar.loc["지배주주순이익"].sum())
        try:
            latest_equity = float(
                df_fs_quar.loc["지배기업주주지분계산에 참여한 계정 펼치기"].iloc[-1]
            )
        except KeyError:
            latest_equity = float(df_fs_quar.loc["지배기업주주지분"].iloc[-1])
    else:
        trailing_net_income = float(df_fs_quar.loc["당기순이익"].sum())
        latest_equity = float(df_fs_quar.loc["자본"].iloc[-1])

    trailing_eps: float = trailing_net_income * 1_0000_0000 / shares
    bps: int = int(latest_equity / shares * 1_0000_0000)

    # ── 매출/영업이익/순이익 추이
    periods = [str(c) for c in col]
    revenue = [float(df_fs_ann.loc["매출액", c]) for c in col]
    op_profit = [float(df_fs_ann.loc["영업이익", c]) for c in col]
    net_income = [float(df_fs_ann.loc["당기순이익", c]) for c in col]
    op_margin = [
        (op / rev * 100) if rev != 0 else 0.0
        for op, rev in zip(op_profit, revenue)
    ]
    profit_trend = ProfitTrend(
        periods=periods,
        revenue=revenue,
        operating_profit=op_profit,
        net_income=net_income,
        operating_margin=op_margin,
    )

    # ── 이익률 추이 (col[1]=−2y, col[2]=−1y, col[3]=recent, 예상)
    def _rate_history(metric: str) -> RateHistory:
        return RateHistory(
            year_minus_2=float(df_anal.loc[metric, col[1]]),
            year_minus_1=float(df_anal.loc[metric, col[2]]),
            recent=float(df_anal.loc[metric, col[3]]),
            expected=float(df_anal.loc[metric, "예상"]),
        )

    # ── 자본/자산/이익 구성 (col[3] = 최근 기준년도)
    def _int_anal(row: str, col_key: str = col[3]) -> int:
        return int(df_anal.loc[row, col_key])

    # ── 순현금 = 여유자금 − 단기/장기 차입부채
    net_cash: float = float(df_invest.loc["여유자금", col[3]]) - (
        float(df_fs_ann.loc["단기사채", col[3]])
        + float(df_fs_ann.loc["단기차입금", col[3]])
        + float(df_fs_ann.loc["유동금융부채", col[3]])
        + float(df_fs_ann.loc["사채", col[3]])
        + float(df_fs_ann.loc["장기차입금", col[3]])
    )
    net_cash_ratio: float = (net_cash / market_cap * 100) if market_cap != 0 else 0.0

    # ── 사업 요약 (52자 단위 텍스트 래핑)
    summary_raw: str = report.get("Summary", "")
    summary: str = textwrap.fill(summary_raw.strip(), width=52)

    return CompResult(
        code=code,
        market_cap=market_cap,
        shares=shares,
        trailing_eps=trailing_eps,
        book_value_per_share=bps,
        profit_trend=profit_trend,
        operating_asset_return=_rate_history("영업자산이익률"),
        non_operating_return=_rate_history("비영업자산이익률"),
        borrowing_rate=_rate_history("차입이자율"),
        roe=_rate_history("지배주주ROE"),
        shareholders_equity=_int_anal("주주몫"),
        minority_interest=_int_anal("비지배주주지분"),
        operating_liabilities=_int_anal("영업부채"),
        external_debt=_int_anal("외부차입"),
        operating_assets=_int_anal("영업자산"),
        non_operating_assets=_int_anal("비영업자산"),
        operating_profit=_int_anal("영업이익", "예상"),
        non_operating_profit=_int_anal("비영업이익", "예상"),
        interest_expense=_int_anal("이자비용", "예상"),
        tax_expense=_int_anal("법인세비용", "예상"),
        controlling_profit=_int_anal("지배주주순이익", "예상"),
        minority_profit=_int_anal("비지배주주순이익", "예상"),
        net_cash=net_cash,
        net_cash_ratio=net_cash_ratio,
        per_fnguide=str(report.get("PER", "")),
        per_12m=str(report.get("12M PER", "")),
        industry_per=str(report.get("업종 PER", "")),
        pbr=str(report.get("PBR", "")),
        dividend_yield=str(report.get("배당수익률", "")),
        summary=summary,
    )
