import pandas as pd

from backend.services.naver_theme.config import (
    LEADER_SCORE_WEIGHTS,
    MOMENTUM_WEIGHT_1D,
    MOMENTUM_WEIGHT_3D,
)


def _zscore(s: pd.Series) -> pd.Series:
    # ddof=0 (모집단 표준편차); std==0 또는 NaN이면 0 반환
    std = s.std(ddof=0)
    if std == 0 or pd.isna(std):
        return pd.Series([0.0] * len(s), index=s.index)
    return (s - s.mean()) / std


def build_strong_themes(themes_df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    # REQ-NT-005: momentum_score / breadth_ratio 계산 후 change_pct 내림차순 상위 top_n
    df = themes_df.copy()
    df["momentum_score"] = (
        df["change_pct"] * MOMENTUM_WEIGHT_1D + df["change_pct_3d"] * MOMENTUM_WEIGHT_3D
    )
    denom = df["up_count"] + df["flat_count"] + df["down_count"]
    df["breadth_ratio"] = (df["up_count"] / denom).fillna(0)
    return df.sort_values("change_pct", ascending=False).head(top_n).reset_index(drop=True)


def build_leaders(stocks_df: pd.DataFrame, leaders_per_theme: int) -> pd.DataFrame:
    # REQ-NT-009: 테마별 z-score 기반 leader_score 계산
    # market_cap NaN → fillna(0) 후 z-score; std==0 → z=0
    out: list[pd.DataFrame] = []
    for _, group in stocks_df.groupby("theme_id"):
        g = group.copy()
        for col in ("change_pct", "volume", "market_cap", "trade_value"):
            series = g[col].astype(float).fillna(0)
            g[f"z_{col}"] = _zscore(series)
        g["leader_score"] = sum(
            g[f"z_{c}"] * w for c, w in LEADER_SCORE_WEIGHTS.items()
        )
        top = g.nlargest(leaders_per_theme, "leader_score").reset_index(drop=True)
        top["rank"] = top.index + 1
        out.append(
            top[
                [
                    "theme_id",
                    "theme_name",
                    "rank",
                    "stock_code",
                    "stock_name",
                    "leader_score",
                    "change_pct",
                    "volume",
                    "market_cap",
                    "trade_value",
                ]
            ]
        )
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def build_multi_theme_stocks(stocks_df: pd.DataFrame) -> pd.DataFrame:
    # REQ-NT-010: theme_count >= 2인 종목만 포함; theme_names = sorted(set)
    if stocks_df.empty:
        return pd.DataFrame()
    grouped = (
        stocks_df.groupby("stock_code")
        .agg(
            stock_name=("stock_name", "first"),
            theme_names=("theme_name", lambda x: sorted(set(x))),
            theme_count=("theme_name", "nunique"),
            avg_change_pct=("change_pct", "mean"),
        )
        .reset_index()
    )
    return (
        grouped[grouped["theme_count"] >= 2]
        .sort_values("theme_count", ascending=False)
        .reset_index(drop=True)
    )
