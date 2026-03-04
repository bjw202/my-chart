"""High-performing stock screening functions."""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd
from pykrx import stock

from my_chart.config import REFERENCE_STOCK
from my_chart.krx_session import get_market_cap_safe
from my_chart.price import price_naver


def get_high_stocks(
    days: int = 30,
    top_percentage: float = 2,
    market_cap: float | None = None,
    dollar_vol: float | None = None,
) -> list[str]:
    """Get top-performing stocks over a given period.

    Parameters
    ----------
    days : int
        Lookback period in calendar days.
    top_percentage : float
        Top percentile cutoff (e.g. 2 = top 2%).
    market_cap : float or None
        Minimum market cap filter in 억원.
    dollar_vol : float or None
        Minimum dollar volume filter in 억원.

    Returns
    -------
    list[str]
        List of ticker codes.
    """
    p = price_naver(REFERENCE_STOCK, "20250101")
    end = p.index[-1].strftime("%Y%m%d")

    prev_day = p.index[-1] - datetime.timedelta(days=days)
    start = f"{prev_day.year}{prev_day.month:02}{prev_day.day:02}"

    df_kospi = stock.get_market_price_change(start, end, market="KOSPI")
    df_kosdaq = stock.get_market_price_change(start, end, market="KOSDAQ")

    df = pd.concat([df_kospi, df_kosdaq], axis=0)
    df = df.reset_index()
    df = df.set_index("종목명")
    df["rank"] = df["등락률"].rank(pct=True) * 100

    df_query = df.query(f"rank >= {100 - top_percentage}")
    _tickers = df_query["티커"].values

    tickers = []

    if market_cap is not None:
        mc = get_market_cap_safe(end)
        for t in _tickers:
            m = mc.loc[t]["시가총액"] / 1_0000_0000
            v = mc.loc[t]["거래대금"] / 1_0000_0000
            if m >= market_cap:
                if dollar_vol is not None:
                    if v >= dollar_vol:
                        tickers.append(t)
                else:
                    tickers.append(t)
    else:
        tickers = list(_tickers)

    return tickers


def 투자과열예상종목() -> np.ndarray:
    """Detect overheated stocks based on KRX criteria.

    Criteria:
    - Ultra-short surge: Close up >= 100% vs 3 days ago
    - Short surge: Close up >= 60% vs 5 days ago
    - Mid-term surge: Close up >= 100% vs 15 days ago
    """
    p = price_naver(REFERENCE_STOCK, "2024-01-01")
    date = p.index.strftime("%Y-%m-%d")

    results = []
    for days, threshold in [(3, 95), (5, 55), (15, 95)]:
        end = date[-1]
        start = date[-1 - days]

        df_kospi = stock.get_market_price_change(start, end, market="KOSPI")
        df_kosdaq = stock.get_market_price_change(start, end, market="KOSDAQ")

        df = pd.concat([df_kospi, df_kosdaq], axis=0).reset_index()
        df_query = df.query(f"등락률 >= {threshold}")
        results.append(df_query["티커"].values)

    return np.concatenate(results)
