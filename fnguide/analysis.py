"""
FnGuide 재무 분석 및 RIM 적정가 계산

fs_analysis: 재무제표 → 자금조달/자산/손익 분석
price_analysis: 컨센서스 + 분석치 기반 RIM 가격 산출
cal_rim: RIM 현재가치 계산 (전역변수 의존성 제거)
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import numpy_financial as npf  # type: ignore[import-untyped]
import pandas as pd

# BBB- 기본 요구수익률 (get_required_rate()로 갱신 가능)
DEFAULT_REQUIRED_RATE: float = 0.08


def calc_weight_coeff(date_columns: pd.Index) -> tuple[float, float, float, float]:
    """회계연도 간격에 따라 가중평균 계수를 계산한다.

    Args:
        date_columns: df_fs_ann.columns (예: ['2020/12', '2021/12', ...])

    Returns:
        (w1, w2, w3, denom) — 오래된 순서대로 가중치
    """
    curr_year = int(str(date_columns[3]).split("/")[0])
    curr_month = int(str(date_columns[3]).split("/")[1])
    last_year = int(str(date_columns[2]).split("/")[0])
    last_month = int(str(date_columns[2]).split("/")[1])

    gap_month = (curr_year - last_year) * 12 + curr_month - last_month

    w1, w2, w3, denom = 1.0, 2.0, 3.0, 6.0
    if gap_month == 3:
        w2, denom = 0.5, 4.5
    elif gap_month == 6:
        w2, denom = 1.0, 5.0
    elif gap_month == 9:
        w2, denom = 1.5, 5.5

    return w1, w2, w3, denom


def fs_analysis(
    df_fs_ann: pd.DataFrame,
    df_fs_quar: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """재무제표 기반 종합 재무 분석을 수행한다.

    분석 단계:
        1. 자금조달 분석 (신용조달, 외부차입, 주주몫)
        2. 자산투자 분석 (설비투자, 운전자산, 금융투자, 여유자금)
        3. 손익자료 (Trailing 12M 반영)
        4. 이익률 / ROE / 차입이자율 계산
        5. 예상 순이익 추정

    Args:
        df_fs_ann: FnGuide 연간 재무제표 DataFrame (read_fs 결과)
        df_fs_quar: FnGuide 분기 재무제표 DataFrame (read_fs 결과)

    Returns:
        (df_anal, df_invest)
    """
    # ─────────────────────────────────────────────────────────────
    # 1. 자금조달 분석
    # ─────────────────────────────────────────────────────────────
    df_financing = pd.DataFrame([], columns=df_fs_ann.columns)

    df_financing.loc["신용조달"] = (
        df_fs_ann.loc["매입채무및기타유동채무"]
        + df_fs_ann.loc["유동종업원급여충당부채"]
        + df_fs_ann.loc["기타단기충당부채"]
        + df_fs_ann.loc["당기법인세부채"]
        + df_fs_ann.loc["기타유동부채"]
        + df_fs_ann.loc["장기매입채무및기타비유동채무"]
        + df_fs_ann.loc["비유동종업원급여충당부채"]
        + df_fs_ann.loc["기타장기충당부채"]
        + df_fs_ann.loc["이연법인세부채"]
        + df_fs_ann.loc["장기당기법인세부채"]
        + df_fs_ann.loc["기타비유동부채"]
    )

    df_financing.loc["외부차입"] = (
        df_fs_ann.loc["단기사채"]
        + df_fs_ann.loc["단기차입금"]
        + df_fs_ann.loc["유동성장기부채"]
        + df_fs_ann.loc["유동금융부채"]
        + df_fs_ann.loc["사채"]
        + df_fs_ann.loc["장기차입금"]
        + df_fs_ann.loc["비유동금융부채"]
    )

    df_financing.loc["유보이익"] = (
        df_fs_ann.loc["기타포괄손익누계액"] + df_fs_ann.loc["이익잉여금(결손금)"]
    )

    df_financing.loc["주주투자"] = (
        df_fs_ann.loc["자본금"]
        + df_fs_ann.loc["신종자본증권"]
        + df_fs_ann.loc["자본잉여금"]
        + df_fs_ann.loc["기타자본"]
    )

    try:
        df_financing.loc["비지배주주지분"] = df_fs_ann.loc["비지배주주지분"]
    except KeyError:  # IFRS 별도 시 비지배주주지분 없음
        df_financing.loc["비지배주주지분"] = [0, 0, 0, 0]

    df_financing.loc["기타"] = (
        df_fs_ann.loc["매각예정으로분류된처분자산집단에포함된부채"]
        + df_fs_ann.loc["기타금융업부채"]
    )

    # ─────────────────────────────────────────────────────────────
    # 2. 자산투자 분석
    # ─────────────────────────────────────────────────────────────
    df_invest = pd.DataFrame([], columns=df_fs_ann.columns)

    df_invest.loc["설비투자"] = (
        df_fs_ann.loc["유형자산"]
        + df_fs_ann.loc["무형자산"]
        + df_fs_ann.loc["비유동생물자산"]
    )

    df_invest.loc["운전자산"] = (
        df_fs_ann.loc["재고자산"]
        + df_fs_ann.loc["유동생물자산"]
        + df_fs_ann.loc["매출채권및기타유동채권"]
        + df_fs_ann.loc["당기법인세자산"]
        + df_fs_ann.loc["기타유동자산"]
        + df_fs_ann.loc["장기매출채권및기타비유동채권"]
        + df_fs_ann.loc["이연법인세자산"]
        + df_fs_ann.loc["장기당기법인세자산"]
        + df_fs_ann.loc["기타비유동자산"]
    )

    df_invest.loc["금융투자"] = (
        df_fs_ann.loc["투자부동산"]
        + df_fs_ann.loc["장기금융자산"]
        + df_fs_ann.loc["관계기업등지분관련투자자산"]
    )

    df_invest.loc["여유자금"] = (
        df_fs_ann.loc["현금및현금성자산"] + df_fs_ann.loc["유동금융자산"]
    )

    df_invest.loc["기타"] = (
        df_fs_ann.loc["매각예정비유동자산및처분자산집단"]
        + df_fs_ann.loc["기타금융업자산"]
    )

    # ─────────────────────────────────────────────────────────────
    # 3. 손익자료 (마지막 컬럼 = Trailing 12M)
    # ─────────────────────────────────────────────────────────────
    df_profit = pd.DataFrame([], columns=df_fs_ann.columns)

    df_profit.loc["영업이익"] = df_fs_ann.loc["영업이익"]
    # 이자비용/법인세비용은 중복 계정이 있어 iloc[0]으로 첫 번째 행만 사용
    df_profit.loc["이자비용"] = df_fs_ann.loc["이자비용"].iloc[0]
    df_profit.loc["법인세비용"] = df_fs_ann.loc["법인세비용"].iloc[0]
    df_profit.loc["당기순이익"] = df_fs_ann.loc["당기순이익"]

    # Trailing 12M: 최근 4개 분기 합산
    last_col = df_profit.columns[-1]
    df_profit.loc["영업이익", last_col] = df_fs_quar.loc["영업이익"].sum()
    df_profit.loc["이자비용", last_col] = df_fs_quar.loc["이자비용"].iloc[0].sum()
    df_profit.loc["법인세비용", last_col] = df_fs_quar.loc["법인세비용"].iloc[0].sum()
    df_profit.loc["당기순이익", last_col] = df_fs_quar.loc["당기순이익"].sum()

    try:
        df_profit.loc["지배주주순이익"] = df_fs_ann.loc["지배주주순이익"]
        df_profit.loc["비지배주주순이익"] = df_fs_ann.loc["비지배주주순이익"]
        df_profit.loc["지배주주순이익", last_col] = df_fs_quar.loc["지배주주순이익"].sum()
        df_profit.loc["비지배주주순이익", last_col] = df_fs_quar.loc["비지배주주순이익"].sum()
    except KeyError:  # IFRS 별도 시 지배/비지배 구분 없음
        df_profit.loc["지배주주순이익"] = df_profit.loc["당기순이익"]
        df_profit.loc["비지배주주순이익"] = [0, 0, 0, 0]

    # ─────────────────────────────────────────────────────────────
    # 최종 분석 데이터 취합
    # ─────────────────────────────────────────────────────────────
    df_anal = pd.DataFrame([], columns=df_fs_ann.columns)
    col = df_anal.columns
    w1, w2, w3, denom = calc_weight_coeff(col)

    df_anal.loc["주주몫"] = df_financing.loc["유보이익"] + df_financing.loc["주주투자"]
    df_anal.loc["비지배주주지분"] = df_financing.loc["비지배주주지분"]
    df_anal.loc["외부차입"] = df_financing.loc["외부차입"]
    df_anal.loc["영업부채"] = df_financing.loc["신용조달"]
    df_anal.loc["영업자산"] = df_invest.loc["설비투자"] + df_invest.loc["운전자산"]
    df_anal.loc["설비투자"] = df_invest.loc["설비투자"]
    df_anal.loc["운전자산"] = df_invest.loc["운전자산"]
    df_anal.loc["비영업자산"] = df_invest.loc["금융투자"] + df_invest.loc["여유자금"]

    df_anal.loc["영업이익"] = df_profit.loc["영업이익"]
    df_anal.loc["비영업이익"] = (
        df_profit.loc["당기순이익"]
        - df_profit.loc["영업이익"]
        + df_profit.loc["이자비용"]
        + df_profit.loc["법인세비용"]
    )
    df_anal.loc["이자비용"] = df_profit.loc["이자비용"]
    df_anal.loc["법인세비용"] = df_profit.loc["법인세비용"]
    df_anal.loc["지배주주순이익"] = df_profit.loc["지배주주순이익"]
    df_anal.loc["비지배주주순이익"] = df_profit.loc["비지배주주순이익"]

    # ─────────────────────────────────────────────────────────────
    # 이익률 계산 (연도별)
    # ─────────────────────────────────────────────────────────────
    for i in range(1, 4):
        try:
            df_anal.loc["영업자산이익률", col[i]] = (
                2
                * df_anal.loc["영업이익", col[i]]
                / (df_anal.loc["영업자산", col[i - 1]] + df_anal.loc["영업자산", col[i]])
            )
            df_anal.loc["비영업자산이익률", col[i]] = (
                2
                * df_anal.loc["비영업이익", col[i]]
                / (
                    df_anal.loc["비영업자산", col[i - 1]]
                    + df_anal.loc["비영업자산", col[i]]
                )
            )

            차입합계 = (
                df_anal.loc["외부차입", col[i - 1]] + df_anal.loc["외부차입", col[i]]
            )
            df_anal.loc["차입이자율", col[i]] = (
                (2 * df_anal.loc["이자비용", col[i]] / 차입합계) if 차입합계 > 0 else 0.0
            )

            df_anal.loc["지배주주ROE", col[i]] = (
                2
                * df_anal.loc["지배주주순이익", col[i]]
                / (df_anal.loc["주주몫", col[i - 1]] + df_anal.loc["주주몫", col[i]])
            )
        except ZeroDivisionError:
            df_anal.loc["영업자산이익률", col[i]] = 0.0
            df_anal.loc["비영업자산이익률", col[i]] = 0.0
            df_anal.loc["차입이자율", col[i]] = 0.0
            df_anal.loc["지배주주ROE", col[i]] = 0.0

    # 가중평균
    for metric in ["영업자산이익률", "비영업자산이익률", "차입이자율", "지배주주ROE"]:
        df_anal.loc[metric, "가중평균"] = (
            w1 * df_anal.loc[metric, col[1]]
            + w2 * df_anal.loc[metric, col[2]]
            + w3 * df_anal.loc[metric, col[3]]
        ) / denom

    # 영업자산이익률 1순위: 추세가 있으면 최근값, 없으면 가중평균
    a, b, c = (
        df_anal.loc["영업자산이익률", col[1]],
        df_anal.loc["영업자산이익률", col[2]],
        df_anal.loc["영업자산이익률", col[3]],
    )
    if (b > a and c > b) or (a > b and b > c):
        df_anal.loc["영업자산이익률", "1순위"] = float(c)
    else:
        df_anal.loc["영업자산이익률", "1순위"] = df_anal.loc["영업자산이익률", "가중평균"]

    # 비영업자산이익률 1순위
    noa_returns = df_anal.loc["비영업자산이익률"][1:4]
    c1: float | None = float(noa_returns.min()) if noa_returns.min() > 0 else None
    c2: float | None = (
        float(df_anal.loc["비영업자산이익률", col[3]])
        if df_anal.loc["비영업자산이익률"][1:5].max() < 0
        else None
    )
    c3: float = (
        float(df_anal.loc["비영업자산이익률", col[3]])
        if df_anal.loc["비영업자산이익률"][1:5].std() < 0.01
        else 0.0
    )
    candidates = [v for v in [c1, c2] if v is not None]
    max_val = max(candidates) if candidates else 0.0
    df_anal.loc["비영업자산이익률", "1순위"] = max_val if max_val != 0 else c3

    # 차입이자율 1순위: 최근값
    df_anal.loc["차입이자율", "1순위"] = df_anal.loc["차입이자율", col[3]]

    # ─────────────────────────────────────────────────────────────
    # 예상 순이익 추정 (이익률 기반)
    # ─────────────────────────────────────────────────────────────
    영업이익_est = (
        df_anal.loc["영업자산", col[3]] * df_anal.loc["영업자산이익률", "1순위"]
    )
    비영업이익_est = (
        df_anal.loc["비영업자산", col[3]] * df_anal.loc["비영업자산이익률", "1순위"]
    )
    이자비용_est = df_anal.loc["외부차입", col[3]] * df_anal.loc["차입이자율", "1순위"]
    법인세비용_est = (영업이익_est + 비영업이익_est - 이자비용_est) * 0.22  # 법인세율 22%
    당기순이익_est = 영업이익_est + 비영업이익_est - 이자비용_est - 법인세비용_est

    try:
        지배비율 = df_anal.loc["지배주주순이익", col[3]] / (
            df_anal.loc["지배주주순이익", col[3]]
            + df_anal.loc["비지배주주순이익", col[3]]
        )
    except ZeroDivisionError:
        지배비율 = 0.0

    지배주주순이익_est = 당기순이익_est * 지배비율
    비지배주주순이익_est = 당기순이익_est * (1 - 지배비율)
    지배주주ROE_est = 지배주주순이익_est / df_anal.loc["주주몫", col[3]]

    df_anal.loc["영업이익", "예상"] = 영업이익_est
    df_anal.loc["비영업이익", "예상"] = 비영업이익_est
    df_anal.loc["이자비용", "예상"] = 이자비용_est
    df_anal.loc["법인세비용", "예상"] = 법인세비용_est
    df_anal.loc["당기순이익", "예상"] = 당기순이익_est
    df_anal.loc["지배주주순이익", "예상"] = 지배주주순이익_est
    df_anal.loc["비지배주주순이익", "예상"] = 비지배주주순이익_est
    df_anal.loc["지배주주ROE", "예상"] = 지배주주ROE_est

    return df_anal, df_invest


def cal_rim(
    지배주주지분0: float,
    ROE: float,
    감소계수: float,
    finaldata_date: str,
    report: dict,  # type: ignore[type-arg]
    required_rate: float = DEFAULT_REQUIRED_RATE,
    premium: float = 0.0,
) -> int:
    """RIM(잔여이익모형) 기반 주당 적정가를 계산한다.

    원본 버그 수정: 전역변수 `요구수익률` 의존성 제거 → required_rate 파라미터.

    Args:
        지배주주지분0: 기준 지배주주지분 (억원)
        ROE: 예상 자기자본이익률
        감소계수: 연간 ROE 감소율 (0=무한지속, 0.1=10%씩 감소)
        finaldata_date: 기준 연도 'YYYY/MM'
        report: read_snapshot 반환 dict (발행주식수, 자기주식 포함)
        required_rate: 요구수익률 (기본 0.08)
        premium: 프리미엄 조정 (%p 단위)

    Returns:
        주당 적정가 (원)
    """
    spread = ROE - (required_rate - premium / 100)
    years = np.linspace(0, 10, 11)
    roe_arr = np.array(
        [required_rate + spread * ((1 - 감소계수) ** n) for n in years]
    )

    지배주주순이익 = np.zeros(11)
    초과이익 = np.zeros(11)
    지배주주지분 = np.zeros(11)

    for i, _roe in enumerate(roe_arr):
        if i == 0:
            지배주주지분[i] = 지배주주지분0
        else:
            지배주주순이익[i] = 지배주주지분[i - 1] * _roe
            초과이익[i] = 지배주주순이익[i] - 지배주주지분[i - 1] * required_rate
            지배주주지분[i] = 지배주주지분[i - 1] + 지배주주순이익[i]

    pv_ri = npf.npv(required_rate, 초과이익)
    rim = 지배주주지분0 + pv_ri

    # 기준일로부터 오늘까지 현재가치 할인
    y, m = finaldata_date.split("/")
    final_date = datetime(int(y), int(m), 30)
    del_year = (final_date - datetime.today()).days / 365

    현재가치 = rim / ((1 + required_rate) ** del_year)
    주식수 = (
        report["발행주식수(보통주)"]
        + report["발행주식수(우선주)"]
        - report["자기주식"]
    )

    return int(현재가치 / 주식수 * 100_000_000)


def calculate_historical_rim(
    BPS: float,
    ROE: float,
    required_rate: float,
    감소계수: float,
    premium: float,
) -> float:
    """QuantKing 과거 데이터 기반 간략 RIM 계산.

    Args:
        BPS: 주당 순자산 (원)
        ROE: 자기자본이익률
        required_rate: 요구수익률
        감소계수: 연간 ROE 감소율
        premium: ROE 조정 승수 (프리미엄)

    Returns:
        RIM 적정가 (BPS와 동일 단위)
    """
    spread = ROE - required_rate
    years = np.linspace(0, 10, 11)
    weight = np.array([max(1 - 감소계수 * i, 0) for i in years])
    roe_arr = spread * weight + required_rate

    지배주주순이익 = np.zeros(11)
    초과이익 = np.zeros(11)
    지배주주지분 = np.zeros(11)

    for i, _roe in enumerate(roe_arr):
        if i == 0:
            지배주주지분[i] = BPS
        else:
            지배주주순이익[i] = 지배주주지분[i - 1] * _roe * (1 + premium)
            초과이익[i] = 지배주주순이익[i] - 지배주주지분[i - 1] * required_rate
            지배주주지분[i] = 지배주주지분[i - 1] + 지배주주순이익[i]

    pv_ri = npf.npv(required_rate, 초과이익)
    return BPS + pv_ri


def price_analysis(
    df_fs_ann: pd.DataFrame,  # noqa: ARG001
    df_fs_quar: pd.DataFrame,  # noqa: ARG001
    df_snap: pd.DataFrame,
    df_cons: pd.DataFrame,
    report: dict,  # type: ignore[type-arg]
    account_type: str,  # noqa: ARG001
    df_anal: pd.DataFrame,
    required_rate: float = DEFAULT_REQUIRED_RATE,
    premium: float = 0,
) -> tuple[list[int], pd.DataFrame, float, bool]:
    """컨센서스 + 분석치 기반 RIM 3단계 적정가를 산출한다.

    Args:
        df_fs_ann: 연간 재무제표 (read_fs 결과)
        df_fs_quar: 분기 재무제표 (read_fs 결과)
        df_snap: 분기 스냅샷 DataFrame (read_snapshot 결과)
        df_cons: 컨센서스 DataFrame (read_consensus 결과)
        report: read_snapshot 결과 dict
        account_type: 'IFRS(연결)' 또는 'IFRS(별도)'
        df_anal: fs_analysis 결과
        required_rate: 요구수익률
        premium: 프리미엄 (%)

    Returns:
        ([price_5y_decay, price_10y_decay, price_no_decay], df_rim, ROE, is_정배열)
    """
    df_rim = pd.DataFrame([], columns=df_cons.columns)

    try:
        df_rim.loc["지배주주지분순이익"] = df_cons.loc["지배주주순이익(억원)"]
        df_rim.loc["지배주주지분"] = df_cons.loc["지배주주지분(억원)"]
    except KeyError:
        df_rim.loc["지배주주지분순이익"] = df_cons.loc["당기순이익(억원)"]
        df_rim.loc["지배주주지분"] = df_cons.loc["자본총계(억원)"]

    # 최신 데이터가 있는 컬럼 탐색
    finaldata_date: str = str(df_rim.columns[2])  # 기본값
    finaldata_cnt: int = 2
    for cnt, col in enumerate(df_rim.columns):
        if not pd.isna(df_rim.loc["지배주주지분순이익", col]) and not pd.isna(
            df_rim.loc["지배주주지분", col]
        ):
            finaldata_date = str(col)
            finaldata_cnt = cnt

    # 지배주주지분(평균) 계산
    df_rim.loc["지배주주지분(평균)"] = [np.nan] * len(df_rim.columns)
    for cnt in range(3, len(df_rim.columns)):
        df_rim.loc["지배주주지분(평균)", df_rim.columns[cnt]] = 0.5 * (
            df_rim.loc["지배주주지분", df_rim.columns[cnt - 1]]
            + df_rim.loc["지배주주지분", df_rim.columns[cnt]]
        )

    df_rim.loc["ROE"] = (
        df_rim.loc["지배주주지분순이익"] / df_rim.loc["지배주주지분(평균)"]
    )
    # 과거 실제 ROE로 앞 3개 컬럼 덮어씀
    df_rim.loc["ROE"].iloc[:3] = df_snap["Annual"].loc["ROE"].iloc[:3]

    # 기준 지배주주지분 결정
    if finaldata_cnt == 2:
        지배주주지분0 = float(df_rim.loc["지배주주지분", df_rim.columns[finaldata_cnt]])
    elif finaldata_cnt == 3:
        지배주주지분0 = float(
            df_rim.loc["지배주주지분", df_rim.columns[finaldata_cnt - 1]]
            + df_rim.loc["지배주주지분순이익", df_rim.columns[finaldata_cnt]]
        )
    elif finaldata_cnt == 4:
        지배주주지분0 = float(
            df_rim.loc["지배주주지분", df_rim.columns[finaldata_cnt - 2]]
            + df_rim.loc["지배주주지분순이익", df_rim.columns[finaldata_cnt - 1]]
            + df_rim.loc["지배주주지분순이익", df_rim.columns[finaldata_cnt]]
        )
    else:  # cnt == 5 또는 그 외
        지배주주지분0 = float(df_rim.loc["지배주주지분", df_rim.columns[finaldata_cnt]])

    # ROE 선택: 컨센서스 최신값 우선, 없으면 분석치
    ROE_consen = np.nan
    for roe in df_rim.loc["ROE"].iloc[-3:]:
        if not pd.isna(roe):
            ROE_consen = float(roe)
    ROE_esti = float(df_anal.loc["지배주주ROE", "예상"])
    ROE = ROE_consen if not np.isnan(ROE_consen) else ROE_esti

    # RIM 3단계 계산
    price_no_decay = cal_rim(
        지배주주지분0, ROE, 0.0, finaldata_date, report, required_rate, premium
    )
    price_10y_decay = cal_rim(
        지배주주지분0, ROE, 0.1, finaldata_date, report, required_rate, premium
    )
    price_5y_decay = cal_rim(
        지배주주지분0, ROE, 0.2, finaldata_date, report, required_rate, premium
    )

    정배열 = price_no_decay > price_5y_decay

    return [price_5y_decay, price_10y_decay, price_no_decay], df_rim, ROE, 정배열
