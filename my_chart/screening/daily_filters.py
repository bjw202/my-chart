"""Daily database filtering functions."""

from __future__ import annotations

import sqlite3

import pandas as pd

from my_chart.config import DEFAULT_DB_DAILY, REFERENCE_STOCK
from my_chart.registry import _code, _sector


def daily_filtering(
    *query: str, db_name: str = DEFAULT_DB_DAILY
) -> pd.DataFrame:
    """Filter daily stock data using sequential query conditions.

    Parameters
    ----------
    *query : str
        DataFrame query strings applied sequentially.
    db_name : str
        Database filename (without .db extension).

    Returns
    -------
    pd.DataFrame
        Filtered stock data with TradingView tickers and sector info.
    """
    conn = sqlite3.connect(f"{db_name}.db")

    df = pd.read_sql_query(
        f"SELECT * FROM stock_prices WHERE Name = '{REFERENCE_STOCK}'", conn
    )
    today = df["Date"].values[-1]

    df = pd.read_sql_query(
        f"SELECT * FROM stock_prices WHERE Date = '{today}'", conn
    )

    filtered_df = df.copy()
    for q in query:
        filtered_df = filtered_df.query(q).copy()

    conn.close()

    filtered_df["Ticker_TradingView"] = filtered_df["Name"].map(
        lambda x: "KRX:" + _code(x) + ","
    )
    filtered_df["Ticker"] = filtered_df["Name"].map(lambda x: _code(x))
    filtered_df["Sector"] = filtered_df["Name"].map(lambda x: _sector(x)[1])
    filtered_df.sort_values(by="Sector", ascending=False, inplace=True)

    filtered_df.to_excel("Filterd_Stock.xlsx")
    return filtered_df


def filter_etc(db_name: str = DEFAULT_DB_DAILY) -> pd.DataFrame:
    """Close > 50SMA, 20EMA > 50SMA, DailyRange < 2.5%, near 10/20 EMA, 50SMA > 200SMA."""
    q1 = "Close > SMA50 and EMA20 > SMA50"
    q2 = "Range < 2.5"
    q3 = "-2<= FromEMA10 <= 2 or 2 <= FromEMA20 <= 2"
    q4 = "SMA50 > SMA200"
    return daily_filtering(q1, q2, q3, q4)


def filter_1(db_name: str = DEFAULT_DB_DAILY) -> pd.DataFrame:
    """Price above 50SMA, 50SMA > 200SMA, ADR > 5, high volume, tight range, near 52w high."""
    q1 = "Close > SMA50 and SMA50 > SMA200"
    q2 = "Close > SMA200 and EMA10 > SMA200"
    q3 = "ADR20 > 5"
    q4 = "Volume20MA > 100000"
    q5 = "Range < ADR20 *0.5"
    q6 = "Close > High52W * 0.75"
    return daily_filtering(q1, q2, q3, q4, q5, q6)


def filter_2(db_name: str = DEFAULT_DB_DAILY) -> pd.DataFrame:
    """All MAs aligned: Close > EMA20 > SMA50 > SMA200, near 52w high."""
    q1 = "Close > EMA20 & EMA20 > SMA50 and SMA50 > SMA200"
    q2 = "Close > High52W * 0.75"
    return daily_filtering(q1, q2)


def daily_filtering_2(db_name: str = DEFAULT_DB_DAILY) -> None:
    """10EMA > 20EMA > 50SMA, DailyRange < 2%, Inside Day pattern."""
    conn = sqlite3.connect(f"{db_name}.db")

    df = pd.read_sql_query(
        f"SELECT * FROM stock_prices WHERE Name = '{REFERENCE_STOCK}'", conn
    )
    today = df["Date"].values[-1]
    yesterday = df["Date"].values[-2]

    df = pd.read_sql_query(
        f"SELECT * FROM stock_prices WHERE Date = '{yesterday}'", conn
    )
    df1 = df.query("Close > SMA50 and EMA10 > EMA20 and EMA20 > SMA50")
    df2 = df1.query("DailyRange < 2")

    df = pd.read_sql_query(
        f"SELECT * FROM stock_prices WHERE Date = '{today}'", conn
    )

    comp = []
    for _, row_stock in df2.iterrows():
        name, h, l = row_stock["Name"], row_stock["High"], row_stock["Low"]
        _df = df.query(f'Name == "{name}"')
        if _df["High"].values[0] <= h and _df["Low"].values[0] >= l:
            comp.append(name)

    conn.close()

    df_out = pd.DataFrame()
    df_out["Name"] = comp
    df_out["TICKER"] = df_out["Name"].map(lambda x: "KRX:" + _code(x) + ",")
    df_out.to_excel("DailyFiltering_inside_day.xlsx")


def daily_filtering_3(db_name: str = DEFAULT_DB_DAILY) -> None:
    """52-week high within 10%."""
    conn = sqlite3.connect(f"{db_name}.db")

    df = pd.read_sql_query(
        f"SELECT * FROM stock_prices WHERE Name = '{REFERENCE_STOCK}'", conn
    )
    today = df["Date"].values[-1]

    df = pd.read_sql_query(
        f"SELECT * FROM stock_prices WHERE Date = '{today}'", conn
    )
    df_out = df.query("Close >= High52W * 0.9")
    conn.close()

    df_out["TICKER"] = df_out["Name"].map(lambda x: "KRX:" + _code(x) + ",")
    df_out.to_excel("DailyFiltering_52high.xlsx")
