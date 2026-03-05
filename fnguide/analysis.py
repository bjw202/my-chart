"""
FnGuide 재무 분석

fs_analysis: 재무제표 → 자금조달/자산/손익 분석
"""

from __future__ import annotations

import pandas as pd


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

    # 이익률 예상값 = 1순위 (추세 또는 가중평균)
    df_anal.loc["영업자산이익률", "예상"] = df_anal.loc["영업자산이익률", "1순위"]
    df_anal.loc["비영업자산이익률", "예상"] = df_anal.loc["비영업자산이익률", "1순위"]
    df_anal.loc["차입이자율", "예상"] = df_anal.loc["차입이자율", "1순위"]

    df_anal.loc["영업이익", "예상"] = 영업이익_est
    df_anal.loc["비영업이익", "예상"] = 비영업이익_est
    df_anal.loc["이자비용", "예상"] = 이자비용_est
    df_anal.loc["법인세비용", "예상"] = 법인세비용_est
    df_anal.loc["당기순이익", "예상"] = 당기순이익_est
    df_anal.loc["지배주주순이익", "예상"] = 지배주주순이익_est
    df_anal.loc["비지배주주순이익", "예상"] = 비지배주주순이익_est
    df_anal.loc["지배주주ROE", "예상"] = 지배주주ROE_est

    return df_anal, df_invest
