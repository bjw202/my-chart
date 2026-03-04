"""Momentum screening: unified mmt_companies and mmt_filtering."""

from __future__ import annotations

import datetime
import os
import sqlite3
import time

import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd
from pykrx import stock

from my_chart.charting.styles import get_korean_market_style
from my_chart.config import (
    DEFAULT_DB_WEEKLY,
    FONT_NAME,
    MIN_CLOSE_PRICE,
    REFERENCE_STOCK,
)
from my_chart.db.queries import get_nearest_date, load_price_with_rs
from my_chart.export.pptx_builder import (
    add_image_slide,
    create_widescreen_pptx,
    save_and_cleanup,
)
from my_chart.indicators import add_moving_averages
from my_chart.price import fix_zero_ohlc, price_naver
from my_chart.registry import _code, _sector, add_sector_info


def _generate_ndarray(x: float) -> np.ndarray:
    """Generate tick array from 0 to x in steps of 5."""
    if x >= 0:
        arr = np.arange(0, x + 0.00001, 5)
        if arr[-1] < x:
            arr = np.append(arr, x)
    else:
        arr = np.array([])
    return arr


# @MX:NOTE: [AUTO] Momentum screening filters by RS period
# 0.75*MAX52 = within 25% of 52-week high; 1.3*min52 = at least 30% above 52-week low
# 12M: basic momentum; 6M: adds MA trend alignment; 3M: relaxed (no MA filter)
_QUERY_FILTERS: dict[str, list[str]] = {
    "12M": [
        f"Close > {MIN_CLOSE_PRICE} & VolumeSMA10 > 100000",
        "Close > SMA10",
        "Close >= 0.75*MAX52 & Close >= 1.3 * min52",
    ],
    "6M": [
        f"Close > {MIN_CLOSE_PRICE} & VolumeSMA10 > 100000",
        "Close > SMA10 & SMA10 > SMA40 & SMA20 > SMA40",
        "Close >= 0.75*MAX52 & Close >= 1.3 * min52",
    ],
    "3M": [
        f"Close > {MIN_CLOSE_PRICE} & VolumeSMA10 > 100000",
        "Close >= 0.75*MAX52 & Close >= 1.3 * min52",
    ],
}


def mmt_companies(
    date: str,
    rs_period: str = "12M",
    start: str = "2023-09-01",
    freq: str = "day",
    summary: bool = False,
    db_name: str = DEFAULT_DB_WEEKLY,
) -> pd.DataFrame:
    """Unified momentum screening for 12M, 6M, or 3M RS periods.

    Parameters
    ----------
    date : str
        Target date (YYYY-MM-DD).
    rs_period : str
        RS rating period: "12M", "6M", or "3M".
    start : str
        Chart start date.
    freq : str
        Price frequency: "day" or "week".
    summary : bool
        Include summary images in PPTX.
    db_name : str
        Weekly database name.

    Returns
    -------
    pd.DataFrame
        Filtered momentum DataFrame.
    """
    rs_col = f"RS_{rs_period}_Rating"

    date = get_nearest_date(date, db_name)
    market_cap_data = stock.get_market_cap(date)

    df = load_price_with_rs(date, db_name)
    df.dropna(inplace=True)

    filters = _QUERY_FILTERS.get(rs_period, _QUERY_FILTERS["12M"])
    for q in filters:
        df = df.query(q)

    df["MAX52_Ratio"] = df["Close"] / df["MAX52"] - 1
    df = df.query(f"{rs_col} > 80")

    df = add_sector_info(df)
    df.sort_values(by="산업명(대)", ascending=True, inplace=True)

    # Add hyperlinks and code columns
    code = [_code(name) for name in df.index]
    df["Naver"] = [
        f'=HYPERLINK("https://finance.naver.com/item/fchart.nhn?code={c}", "Naver")'
        for c in code
    ]
    df["TradingView"] = [
        f'=HYPERLINK("https://www.tradingview.com/chart/?symbol=KRX:{c}", "TradingView")'
        for c in code
    ]
    df["Code"] = ["KRX:" + _code(n) + "," for n in df.index]

    mmt = pd.DataFrame(df[[
        "산업명(대)",
        "산업명(중)",
        "주요제품",
        "Naver",
        "TradingView",
        "Close",
        "RS_12M_Rating",
        "MAX52_Ratio",
        "SMA10",
        "SMA20",
        "SMA40",
        "MAX52",
        "min52",
        "SMA40_Trend_1M",
        "SMA40_Trend_2M",
        "SMA40_Trend_3M",
        "SMA40_Trend_4M",
    ]])
    mmt.to_excel(f"mmt_{date}_{rs_period}.xlsx")

    # Plot charts
    _plot_mmt_charts(
        df, date, start, freq, summary, rs_period, market_cap_data, db_name
    )

    return mmt


def _plot_mmt_charts(
    df: pd.DataFrame,
    date: str,
    start: str,
    freq: str,
    summary: bool,
    rs_period: str,
    market_cap_data: pd.DataFrame,
    db_name: str,
) -> None:
    """Generate candlestick charts and PPTX for mmt_companies."""
    companies = df.index
    s = get_korean_market_style()

    pic_files = []
    ticker = []

    plt.ioff()

    kospi = price_naver("KOSPI", start, freq=freq)
    for i, comp_name in enumerate(companies):
        plt.close()

        p = price_naver(comp_name, "2020-01-01", freq=freq)
        p = fix_zero_ohlc(p)
        p = add_moving_averages(p, freq)

        p = p.loc[start:]
        bm = kospi.loc[p.index[0]:]
        p["RS_Line"] = p["Close"] / bm["Close"]
        p["HLC"] = (p["High"] + p["Low"] + p["Close"]) / 3
        p["Volume"] = p["Volume"] * p["HLC"] / 1_0000_0000

        # Recent trend lines
        last_days = p[-80:] if freq == "day" else p[-16:]
        max_close_date = last_days["Close"].idxmax().strftime("%Y-%m-%d")
        min_close_date = last_days["Close"].idxmin().strftime("%Y-%m-%d")

        max_close_price = p["Close"][max_close_date]
        min_close_price = p["Close"][min_close_date]

        _today = p.index[-1].strftime("%Y-%m-%d")
        _price = p["Close"][_today]

        seq_of_points = [
            [(max_close_date, max_close_price), (_today, _price)],
            [(min_close_date, min_close_price), (_today, _price)],
        ]

        up = 100 * (_price - min_close_price) / min_close_price
        down = 100 * (_price - max_close_price) / max_close_price

        kwargs = dict(type="candle", volume=True)

        if freq == "day":
            ma_cols = ["MA10", "MA20", "MA50", "MA200"]
        else:
            ma_cols = ["MA20", "MA50", "MA200"]

        plots = [
            mpf.make_addplot(p[ma_cols], panel=0, secondary_y=False),
            mpf.make_addplot(bm["Close"], color="limegreen", panel=2, ylabel="KOSPI"),
            mpf.make_addplot(
                p["RS_Line"], color="orange", panel=2, secondary_y=True, ylabel="RS Line"
            ),
        ]

        fig, ax = mpf.plot(
            p,
            **kwargs,
            style=s,
            figsize=(28, 12),
            alines=dict(alines=seq_of_points, colors=["b", "r"], alpha=0.3),
            addplot=plots,
            returnfig=True,
            panel_ratios=(6, 1, 2),
            scale_width_adjustment=dict(candle=1.5),
        )

        ax[0].set_yscale("log")
        ax[1].yaxis.tick_right()
        ax[2].yaxis.tick_right()
        ax[3].yaxis.tick_right()

        txt = f"UP {up:.1f}%\nDOWN {down:.1f}%\n"
        _ymin, _ymax = ax[0].get_ylim()
        ax[0].text(len(p) - 10, _ymax, txt, fontsize=14)
        ax[0].grid(False)

        last_close = p["Close"].iloc[-1]
        ymax = (_ymax - last_close) / last_close * 100
        ymin = (_ymin - last_close) / last_close * 100

        a_arr = _generate_ndarray(ymax)
        b_arr = -_generate_ndarray(abs(ymin))[1:]
        b_arr.sort()
        new_ticks = np.concatenate((b_arr, a_arr)).astype("int")

        ax2 = ax[0].twinx()
        ax2.set_yticks(new_ticks)
        ax2.grid(True)

        try:
            시가총액 = market_cap_data.loc[_code(comp_name), "시가총액"] / 1_0000_0000
            jo, uk = int(시가총액 // 10000), int(시가총액 % 10000)
            sichong = f"{uk} 억" if jo == 0 else f"{jo}조 {uk}억"
        except (KeyError, IndexError):
            sichong = "N/A"

        fig.suptitle(
            comp_name + f"\n({sichong}원)\n", fontsize=21, fontfamily=FONT_NAME
        )

        _, sector_txt = _sector(comp_name)
        fig.text(
            0.5, 0.9, sector_txt,
            ha="center", va="center", fontsize=12, fontfamily=FONT_NAME,
        )

        filename = f"./.cache/price{i + 1}"
        plt.savefig(filename, bbox_inches="tight", pad_inches=0.2)
        plt.close("all")
        pic_files.append(filename + ".png")
        ticker.append(_code(comp_name))

        print(f"\r{comp_name} {i + 1}/{len(companies)}", end="")

    plt.ion()

    # Build PPTX
    prs = create_widescreen_pptx()
    for idx, file in enumerate(pic_files):
        links = {
            "TradingView": f"https://kr.tradingview.com/chart/?symbol=KRX:{ticker[idx]}",
            "Naver News": f"https://finance.naver.com/item/news.naver?code={ticker[idx]}",
        }
        add_image_slide(prs, file, links=links)

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.getcwd(), f"mmt_{rs_period}_{now_str}.pptx")
    save_and_cleanup(prs, output_path, pic_files)


def mmt_filtering(
    db_name: str = DEFAULT_DB_WEEKLY, rs_rating: float = 90
) -> pd.DataFrame:
    """Track momentum stock list changes over time."""
    with sqlite3.connect(f"{db_name}.db") as conn:
        df = pd.read_sql_query(
            "SELECT * FROM stock_prices WHERE Name = ?", conn, params=[REFERENCE_STOCK]
        )
        dates = df["Date"].values

    date_list = []
    comp_list = []
    link_list = []

    for date in dates:
        df = load_price_with_rs(date, db_name)

        is_all_none = df["RS_12M_Rating"].isna().all()
        if bool(is_all_none):
            continue

        df = df.query(f"Close > {MIN_CLOSE_PRICE} & VolumeSMA10 > 100000")
        df = df.query("Close > SMA10 & SMA10 > SMA40")
        df = df.query("Close >= 0.75*MAX52 & Close >= 1.3 * min52")
        df = df.query(f"RS_12M_Rating > {rs_rating}")

        df.sort_values(by="RS_12M_Rating", ascending=False, inplace=True)

        date_list.append(date)
        df.reset_index(inplace=True)
        comp_list.append(df["Name"].values)
        df.loc[:, "Link"] = df["Name"]
        link_list.append(df["Link"].values)

    data = {}
    for i, d in enumerate(date_list):
        data[d] = link_list[i]
    mmt = pd.DataFrame.from_dict(data, orient="index").T

    # New & Out tracking
    data_new = {}
    data_out = {}

    for i, d in enumerate(date_list):
        if i > 0:
            comp_new = [c for c in link_list[i] if c not in link_list[i - 1]]
            comp_out = [c for c in link_list[i - 1] if c not in comp_list[i]]
            data_new[d] = comp_new
            data_out[d] = comp_out

    mmt_new = pd.DataFrame.from_dict(data_new, orient="index").T
    mmt_out = pd.DataFrame.from_dict(data_out, orient="index").T

    with pd.ExcelWriter(
        f"_mmt_history_{date_list[-1]}.xlsx", engine="xlsxwriter"
    ) as writer:
        mmt.to_excel(writer, sheet_name="MMT", index=False)
        mmt_new.to_excel(writer, sheet_name="NEW", index=False)
        mmt_out.to_excel(writer, sheet_name="OUT", index=False)

    return mmt
