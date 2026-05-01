import pytest
import pandas as pd
import numpy as np
from backend.services.naver_theme.analyzer import (
    build_strong_themes,
    build_leaders,
    build_multi_theme_stocks,
)


@pytest.mark.unit
def test_build_strong_themes_filters_by_momentum():
    """build_strong_themes() calculates momentum_score correctly."""
    themes_df = pd.DataFrame({
        "theme_id": [1, 2, 3],
        "theme_name": ["A", "B", "C"],
        "change_pct": [5.0, 2.0, -1.0],
        "change_pct_3d": [10.0, 3.0, 0.0],
    })

    result = build_strong_themes(themes_df)

    # momentum_score = change_pct * 0.6 + change_pct_3d * 0.4
    assert "momentum_score" in result.columns
    assert result[result["theme_id"] == 1]["momentum_score"].iloc[0] == pytest.approx(7.0)


@pytest.mark.unit
def test_build_leaders_calculates_z_score():
    """build_leaders() calculates leader_score with z-score weights."""
    stocks_df = pd.DataFrame({
        "stock_code": ["000001", "000002", "000003"],
        "stock_name": ["A", "B", "C"],
        "change_pct": [5.0, 2.0, -1.0],
        "volume": [1000000, 500000, 200000],
        "market_cap": [100000000000, 50000000000, 20000000000],
        "trade_value": [50000000000, 25000000000, 10000000000],
        "theme_id": [1, 1, 1],
    })

    leaders_df = build_leaders(stocks_df, 3)

    assert "leader_score" in leaders_df.columns
    assert len(leaders_df) <= 3
    assert leaders_df["leader_score"].dtype in [np.float64, np.float32]


@pytest.mark.unit
def test_build_multi_theme_stocks_filters_count():
    """build_multi_theme_stocks() filters stocks appearing in 2+ themes."""
    stocks_df = pd.DataFrame({
        "stock_code": ["001", "001", "002", "003", "001"],
        "stock_name": ["A", "A", "B", "C", "A"],
        "theme_id": [1, 2, 1, 2, 3],
        "theme_name": ["T1", "T2", "T1", "T2", "T3"],
    })

    result = build_multi_theme_stocks(stocks_df)

    assert "theme_count" in result.columns
    assert all(result["theme_count"] >= 2)
