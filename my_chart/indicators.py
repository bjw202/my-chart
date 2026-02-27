"""Technical indicators: MACD, RSI, Bollinger Bands, Stochastic, Impulse MACD."""

from __future__ import annotations

import numpy as np
import pandas as pd


def MACD(
    df: pd.DataFrame,
    window_slow: int = 26,
    window_fast: int = 12,
    window_signal: int = 9,
) -> pd.DataFrame:
    """Calculate MACD indicator."""
    macd = pd.DataFrame()
    macd["ema_slow"] = df["Close"].ewm(span=window_slow).mean()
    macd["ema_fast"] = df["Close"].ewm(span=window_fast).mean()
    macd["macd"] = macd["ema_fast"] - macd["ema_slow"]
    macd["signal"] = macd["macd"].ewm(span=window_signal).mean()
    macd["diff"] = macd["macd"] - macd["signal"]
    macd["bar_positive"] = macd["diff"].map(lambda x: x if x > 0 else 0)
    macd["bar_negative"] = macd["diff"].map(lambda x: x if x < 0 else 0)
    return macd


def Stochastic(
    df: pd.DataFrame, window: int = 5, smooth_window: int = 3
) -> pd.DataFrame:
    """Calculate Stochastic oscillator."""
    stochastic = pd.DataFrame()
    stochastic["K"] = (df["Close"] - df["Low"].rolling(window).min()) / (
        df["High"].rolling(window).max() - df["Low"].rolling(window).min()
    )
    stochastic["%K"] = stochastic["K"].rolling(smooth_window).mean()
    stochastic["%D"] = stochastic["%K"].rolling(smooth_window).mean()
    stochastic["UL"] = 80
    stochastic["DL"] = 20
    return stochastic


def RSI(df: pd.DataFrame, periods: int = 14, ema: bool = True) -> pd.DataFrame:
    """Calculate RSI indicator."""
    close_delta = df["Close"].diff()
    up = close_delta.clip(lower=0)
    down = -close_delta.clip(upper=0)

    if ema:
        ma_up = up.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
        ma_down = down.ewm(com=periods - 1, adjust=True, min_periods=periods).mean()
    else:
        ma_up = up.rolling(window=periods, adjust=False).mean()
        ma_down = down.rolling(window=periods, adjust=False).mean()

    rsi = ma_up / ma_down
    rsi = 100 - (100 / (1 + rsi))

    rsi_df = pd.DataFrame()
    rsi_df["RSI"] = rsi
    rsi_df["UL"] = 70
    rsi_df["DL"] = 30
    return rsi_df


def BolingerBand(df: pd.DataFrame, n: int = 20, k: int = 2) -> pd.DataFrame:
    """Calculate Bollinger Bands."""
    bol = pd.DataFrame()
    bol["Bol_center"] = df["Close"].rolling(window=n).mean()
    bol["Bol_upper"] = bol["Bol_center"] + k * df["Close"].rolling(window=n).std()
    bol["Bol_lower"] = bol["Bol_center"] - k * df["Close"].rolling(window=n).std()
    return bol


def _calc_smma(series: pd.Series, length: int = 34) -> pd.Series:
    """Smooth Moving Average."""
    smma = series.rolling(length).mean()
    pd.set_option("mode.chained_assignment", None)
    for i in range(length, len(series.index)):
        smma.iloc[i] = (smma.iloc[i - 1] * (length - 1) + series.iloc[i]) / length
    return smma


def _calc_zlema(series: pd.Series, length: int = 34) -> pd.Series:
    """Zero lag exponential moving average."""
    ema1 = series.ewm(span=length).mean()
    ema2 = ema1.ewm(span=length).mean()
    d = ema1 - ema2
    return ema1 + d


def ImpulseMACD(
    df: pd.DataFrame, lengthMA: int = 34, lengthSignal: int = 9
) -> pd.DataFrame:
    """Calculate Impulse MACD indicator."""
    df = df.copy()
    df["HLC3"] = (df["High"] + df["Low"] + df["Close"]) / 3

    hi = _calc_smma(df["High"], lengthMA)
    lo = _calc_smma(df["Low"], lengthMA)
    mi = _calc_zlema(df["HLC3"], lengthMA)

    df["hi"] = hi
    df["lo"] = lo
    df["mi"] = mi

    df["Impulse MACD"] = np.nan
    df["Color"] = ""

    for i in range(len(df.index)):
        if mi.iloc[i] > hi.iloc[i]:
            df.iloc[i, df.columns.get_loc("Impulse MACD")] = mi.iloc[i] - hi.iloc[i]
        elif mi.iloc[i] < lo.iloc[i]:
            df.iloc[i, df.columns.get_loc("Impulse MACD")] = mi.iloc[i] - lo.iloc[i]
        else:
            df.iloc[i, df.columns.get_loc("Impulse MACD")] = 0

        if df["HLC3"].iloc[i] > mi.iloc[i]:
            df.iloc[i, df.columns.get_loc("Color")] = (
                "lime" if df["HLC3"].iloc[i] > hi.iloc[i] else "green"
            )
        else:
            df.iloc[i, df.columns.get_loc("Color")] = (
                "red" if df["HLC3"].iloc[i] < lo.iloc[i] else "orange"
            )

    df["Impulse Signal"] = df["Impulse MACD"].ewm(span=lengthSignal).mean()
    df["Impulse Histo"] = df["Impulse MACD"] - df["Impulse Signal"]
    return df


def add_moving_averages(
    df: pd.DataFrame, freq: str = "day"
) -> pd.DataFrame:
    """Add MA10/MA20/MA50/MA200 columns based on frequency."""
    adjust = 5 if freq == "week" else 1
    if freq == "day":
        df["MA10"] = df["Close"].ewm(span=10, adjust=False).mean()
        df["MA20"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["MA50"] = df["Close"].rolling(int(50 / adjust)).mean()
        df["MA200"] = df["Close"].rolling(int(200 / adjust)).mean()
    elif freq == "week":
        df["MA20"] = df["Close"].ewm(span=4, adjust=False).mean()
        df["MA50"] = df["Close"].rolling(10).mean()
        df["MA200"] = df["Close"].rolling(40).mean()
    return df
