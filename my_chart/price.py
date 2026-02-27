"""Price data fetching from Naver Finance API."""

from __future__ import annotations

import datetime
import logging
from io import BytesIO

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from my_chart.registry import _code

logger = logging.getLogger(__name__)

# Shared session with retry logic and connection pooling
_session: requests.Session | None = None


def _get_session() -> requests.Session:
    """Get or create a shared requests session with retry adapter."""
    global _session
    if _session is None:
        _session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        _session.mount("https://", adapter)
        _session.mount("http://", adapter)
    return _session


_NAVER_API_BASE = (
    "https://api.finance.naver.com/siseJson.naver"
)
_REQUEST_TIMEOUT = 15


def fix_zero_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Fix zero values in Open/High/Low by replacing with Close."""
    for col in ("Open", "High", "Low"):
        mask = df[col] == 0
        df.loc[mask, col] = df.loc[mask, "Close"]
    return df


def price_naver(
    comp_name: str, start: str, end: str | None = None, freq: str = "day"
) -> pd.DataFrame:
    """Fetch price data from Naver Finance API."""
    if end is None:
        today = datetime.date.today()
        end = f"{today.year}{today.month:02}{today.day:02}"

    if comp_name in ("KOSPI", "KOSDAQ"):
        code = comp_name
    else:
        code = _code(comp_name)
        if code == "NoCode":
            raise ValueError(f"Unknown stock name: {comp_name}")

    url = (
        f"{_NAVER_API_BASE}?"
        f"symbol={code}&requestType=1&startTime={start}&endTime={end}&timeframe={freq}"
    )

    session = _get_session()
    resp = session.get(url, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data_list = pd.read_csv(BytesIO(resp.content))

    if len(data_list) == 0:
        return pd.DataFrame()

    price = data_list.iloc[:, 0:6]
    price.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
    price = price.dropna()
    price["Date"] = price["Date"].str.extract(r"(\d+)")
    price["Date"] = pd.to_datetime(price["Date"])
    price.set_index("Date", inplace=True)

    return price.query(f"Date >= '{start}'")


def price_naver_rs(
    comp_name: str,
    benchmark: pd.DataFrame | None,
    start: str,
    end: str | None = None,
    freq: str = "week",
) -> pd.DataFrame:
    """Fetch price data with relative strength metrics."""
    if end is None:
        today = datetime.date.today()
        end = f"{today.year}{today.month:02}{today.day:02}"

    if comp_name in ("KOSPI", "KOSDAQ"):
        code = comp_name
    else:
        code = _code(comp_name)
        if code == "NoCode":
            logger.warning("Unknown stock: %s, returning empty DataFrame", comp_name)
            return pd.DataFrame()

    url = (
        f"{_NAVER_API_BASE}?"
        f"symbol={code}&requestType=1&startTime={start}&endTime={end}&timeframe={freq}"
    )

    session = _get_session()
    resp = session.get(url, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data_list = pd.read_csv(BytesIO(resp.content))

    if len(data_list) == 0:
        return pd.DataFrame()

    price = data_list.iloc[:, 0:6]
    price.columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
    price = price.dropna()
    price["Date"] = price["Date"].str.extract(r"(\d+)")
    price["Date"] = pd.to_datetime(price["Date"])
    price.set_index("Date", inplace=True)

    # Moving averages (weekly: 10w=~50d, 30w=~150d, 40w=~200d)
    price["Volume MA50"] = price["Volume"].rolling(window=10).mean()
    price["MA50"] = price["Close"].rolling(window=10).mean()
    price["MA150"] = price["Close"].rolling(window=30).mean()
    price["MA200"] = price["Close"].rolling(window=40).mean()

    # MA200 trend
    for months, label in [(1, "1M"), (2, "2M"), (3, "3M"), (4, "4M")]:
        price[f"MA200_Trend({label})"] = price["MA200"].pct_change(
            4 * months, fill_method=None
        )

    # 52-week metrics (fixed: MAX 10W uses window=10, not 52)
    price["MAX 10W"] = price["Close"].rolling(window=10).max()
    price["MAX 52W"] = price["Close"].rolling(window=52).max()
    price["min 52W"] = price["Close"].rolling(window=52).min()
    price["Close-min 52W"] = price["Close"] / price["min 52W"] - 1

    # Change metrics
    periods = {"1W": 1, "1M": 4, "2M": 8, "3M": 12, "6M": 26, "9M": 38, "12M": 52}
    for label, p in periods.items():
        price[f"CHG_{label}"] = price["Close"].pct_change(p, fill_method=None)

    if comp_name in ("KOSPI", "KOSDAQ"):
        benchmark = price.copy()

    # Relative strength
    for label, p in periods.items():
        if label != "1W":
            price[f"RS {label}"] = price["Close"].pct_change(p, fill_method=None)
    price["RS 1W"] = price["Close"].pct_change(1, fill_method=None)

    if benchmark is not None:
        price["RS_Line"] = price["Close"] / benchmark["Close"]

    return price
