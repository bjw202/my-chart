"""Single-stock charting functions."""

from __future__ import annotations

import datetime
import sqlite3

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd

from my_chart.charting.styles import get_korean_market_style
from my_chart.config import DEFAULT_DB_WEEKLY, FONT_NAME
from my_chart.indicators import MACD, RSI, BolingerBand, ImpulseMACD
from my_chart.price import fix_zero_ohlc, price_naver


def plot_chart(
    comp_name: str,
    start: str = "20230101",
    freq: str = "day",
    mav: tuple[int, ...] = (20, 50, 150, 200),
) -> pd.DataFrame:
    """Plot a candlestick chart with RSI and Impulse MACD."""
    df = price_naver(comp_name, start, freq=freq)
    df = fix_zero_ohlc(df)

    impulse_macd = ImpulseMACD(df)
    rsi = RSI(df, 14)

    s = get_korean_market_style()

    plots = [
        mpf.make_addplot(
            rsi[["rsi", "UL", "DL"]], ylim=[0, 100], panel=2, ylabel="RSI(14)"
        ),
        mpf.make_addplot(
            impulse_macd["Impulse MACD"],
            color=impulse_macd["Color"].values,
            type="bar",
            panel=3,
            ylabel="Impulse MACD",
        ),
        mpf.make_addplot(
            impulse_macd["Impulse Signal"],
            color="maroon",
            panel=3,
            secondary_y=False,
        ),
        mpf.make_addplot(
            impulse_macd["Impulse Histo"],
            color="blue",
            panel=3,
            type="bar",
            secondary_y=False,
        ),
    ]

    fig, ax = mpf.plot(
        df,
        title=comp_name,
        type="candle",
        volume=True,
        mav=mav,
        style=s,
        figsize=(16, 11),
        addplot=plots,
        returnfig=True,
        panel_ratios=(3, 1, 2, 2),
        scale_width_adjustment=dict(candle=2.0),
    )
    ax[0].set_yscale("log")
    fig.suptitle(comp_name, fontsize=20, fontfamily=FONT_NAME)

    return df


def plot_mdd(
    comp_name: str, freq: str = "day", start: str = "20100101"
) -> None:
    """Plot Maximum Drawdown chart."""
    df = price_naver(comp_name, start, freq=freq)
    df = fix_zero_ohlc(df)

    df["MAX"] = df["Close"].cummax()
    df["MDD"] = (df["Close"] - df["MAX"]) / df["MAX"] * 100

    s = get_korean_market_style()
    plots = [mpf.make_addplot(df["MDD"], panel=2, ylabel="MDD")]

    fig, ax = mpf.plot(
        df,
        title=comp_name,
        type="candle",
        volume=True,
        style=s,
        figsize=(12, 10),
        addplot=plots,
        returnfig=True,
        panel_ratios=(2, 1, 1),
        figscale=1.0,
    )
    fig.suptitle(comp_name, fontsize=20, fontfamily=FONT_NAME)


def rs_history(
    comp_name: str,
    start: str = "2018-01-01",
    db_name: str = DEFAULT_DB_WEEKLY,
) -> pd.DataFrame:
    """Plot RS history chart with KOSPI benchmark."""
    with sqlite3.connect(f"{db_name}.db") as conn:
        df = pd.read_sql_query(
            "SELECT Date, Open, High, Low, Close, Volume, RS_Line "
            "FROM stock_prices WHERE Name = ? AND Date >= ?",
            conn,
            params=(comp_name, start),
        )
        df.set_index("Date", inplace=True)
        df.index = pd.to_datetime(df.index, format="%Y-%m-%d")

        df_rs = pd.read_sql_query(
            "SELECT * FROM relative_strength WHERE Name = ? AND Date >= ?",
            conn,
            params=(comp_name, start),
        )
        df_rs.set_index("Date", inplace=True)
        df_rs.index = pd.to_datetime(df_rs.index, format="%Y-%m-%d")

    df = pd.concat([df, df_rs], axis=1)

    start_str = datetime.datetime.strftime(df.index[0], "%Y%m%d")
    end_str = datetime.datetime.strftime(df.index[-1], "%Y%m%d")

    benchmark = "KOSPI"
    BM = price_naver(benchmark, start_str, end=end_str, freq="week")

    s = get_korean_market_style()

    plots = [
        mpf.make_addplot(
            df["RS_12M_Rating"],
            color="limegreen",
            width=1,
            panel=0,
            secondary_y=True,
            ylabel="RS_Rating",
            ylim=(0, 100),
        ),
        mpf.make_addplot(
            df["RS_6M_Rating"], color="cyan", width=1, panel=0, secondary_y=True
        ),
        mpf.make_addplot(BM["Close"], color="green", panel=2, ylabel=benchmark),
        mpf.make_addplot(
            df["RS_Line"], color="red", panel=2, secondary_y=True, ylabel="RS Line"
        ),
    ]

    fig, ax = mpf.plot(
        df,
        title=comp_name,
        type="candle",
        volume=True,
        mav=(10, 40),
        style=s,
        figsize=(16, 12),
        addplot=plots,
        returnfig=True,
        panel_ratios=(5, 1, 2),
        scale_width_adjustment=dict(candle=1.5),
    )
    fig.suptitle(comp_name, fontsize=20, fontfamily=FONT_NAME)

    return df_rs
