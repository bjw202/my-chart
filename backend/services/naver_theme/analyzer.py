import pandas as pd
import numpy as np
from backend.services.naver_theme.config import (
    MOMENTUM_WEIGHT_1D,
    MOMENTUM_WEIGHT_3D,
    LEADER_SCORE_WEIGHTS,
)


def _zscore(series: pd.Series) -> pd.Series:
    """Z-score 계산 (NaN 처리).

    @param series: 입력 시리즈
    @return: Z-score 시리즈
    """
    mean = series.mean()
    std = series.std()

    if std == 0 or pd.isna(std):
        return pd.Series(0, index=series.index)

    zscore = (series - mean) / std
    return zscore.fillna(0)


def build_strong_themes(themes_df: pd.DataFrame) -> pd.DataFrame:
    """강세 테마 추출 및 모멘텀 스코어 계산.

    @param themes_df: 테마 DataFrame
    @return: momentum_score 컬럼 추가된 DataFrame
    """
    result = themes_df.copy()

    result["momentum_score"] = (
        result["change_pct"] * MOMENTUM_WEIGHT_1D +
        result["change_pct_3d"] * MOMENTUM_WEIGHT_3D
    )

    return result.sort_values("momentum_score", ascending=False)


def build_leaders(stocks_df: pd.DataFrame, top_n: int = 3) -> pd.DataFrame:
    """테마별 리더 스톡 선정 (Z-score 가중치 기반).

    @param stocks_df: 종목 DataFrame
    @param top_n: 테마당 선정할 리더 스톡 수
    @return: leader_score 컬럼 추가된 DataFrame
    """
    result = stocks_df.copy()

    # Z-score 계산
    result["zscore_change"] = _zscore(result["change_pct"])
    result["zscore_volume"] = _zscore(result["volume"])
    result["zscore_market_cap"] = _zscore(result["market_cap"])
    result["zscore_trade_value"] = _zscore(result["trade_value"])

    # 가중 스코어 계산
    result["leader_score"] = (
        result["zscore_change"] * LEADER_SCORE_WEIGHTS["change_pct"] +
        result["zscore_volume"] * LEADER_SCORE_WEIGHTS["volume"] +
        result["zscore_market_cap"] * LEADER_SCORE_WEIGHTS["market_cap"] +
        result["zscore_trade_value"] * LEADER_SCORE_WEIGHTS["trade_value"]
    )

    # 테마별 상위 top_n 선정
    leaders = result.sort_values(["theme_id", "leader_score"], ascending=[True, False])
    leaders = leaders.groupby("theme_id").head(top_n)

    # Z-score 컬럼 제거
    leaders = leaders.drop(columns=[
        "zscore_change", "zscore_volume", "zscore_market_cap", "zscore_trade_value"
    ])

    return leaders


def build_multi_theme_stocks(stocks_df: pd.DataFrame) -> pd.DataFrame:
    """멀티 테마 종목 추출 (theme_count >= 2).

    @param stocks_df: 종목 DataFrame
    @return: theme_count >= 2인 종목 DataFrame
    """
    # 종목별 테마 개수 계산
    theme_count = stocks_df.groupby("stock_code")["theme_id"].nunique().reset_index()
    theme_count.columns = ["stock_code", "theme_count"]

    result = stocks_df.merge(theme_count, on="stock_code", how="left")

    # theme_count >= 2인 종목만 선택
    result = result[result["theme_count"] >= 2]

    return result.drop_duplicates(subset=["stock_code"])
