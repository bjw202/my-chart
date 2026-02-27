"""Shared database query patterns."""

from __future__ import annotations

import datetime
import sqlite3

import pandas as pd

from my_chart.config import DEFAULT_DB_WEEKLY, REFERENCE_STOCK


def get_nearest_date(date: str, db_name: str = DEFAULT_DB_WEEKLY) -> str:
    """Find the nearest date in the DB to the given date string (YYYY-MM-DD)."""
    with sqlite3.connect(f"{db_name}.db") as conn:
        df = pd.read_sql_query(
            "SELECT * FROM stock_prices WHERE Name = ?", conn, params=[REFERENCE_STOCK]
        )

    date_strings = df["Date"].values
    dates = [datetime.datetime.strptime(ds, "%Y-%m-%d") for ds in date_strings]
    input_date = datetime.datetime.strptime(date, "%Y-%m-%d")
    nearest_date = min(dates, key=lambda d: abs(d - input_date))
    return nearest_date.strftime("%Y-%m-%d")


def load_price_with_rs(
    date: str, db_name: str = DEFAULT_DB_WEEKLY
) -> pd.DataFrame:
    """Load stock_prices joined with relative_strength for a given date."""
    with sqlite3.connect(f"{db_name}.db") as conn:
        df = pd.read_sql_query(
            "SELECT * FROM stock_prices WHERE Date = ?", conn, params=[date]
        )
        df.set_index("Name", inplace=True)

        df_rs = pd.read_sql_query(
            "SELECT * FROM relative_strength WHERE Date = ?", conn, params=[date]
        )
    df_rs.set_index("Name", inplace=True)
    if "Date" in df_rs.columns:
        df_rs.drop(columns=["Date"], inplace=True)

    df = pd.concat([df, df_rs], axis=1)

    return df


def get_query(
    date: str,
    query: str = "Close >= MAX52 * 0.95 & RS_12M_Rating > 80",
    db_name: str = DEFAULT_DB_WEEKLY,
) -> pd.DataFrame:
    """Query the weekly DB with custom filters."""
    import numpy as np

    from my_chart.registry import _sector

    date = get_nearest_date(date, db_name)
    df = load_price_with_rs(date, db_name)
    df.dropna(inplace=True)
    df = df.query(query)

    companies = df.index.values
    산업명대, 산업명중, 주요제품 = [], [], []
    for comp in companies:
        sector_dict, summary = _sector(comp)
        if summary == "NoData":
            산업명대.append("NoData")
            산업명중.append("NoData")
            주요제품.append("NoData")
        else:
            산업명대.append(sector_dict["산업명(대)"])
            산업명중.append(sector_dict["산업명(중)"])
            주요제품.append(sector_dict["주요제품"])

    df["산업명(대)"] = 산업명대
    df["산업명(중)"] = 산업명중
    df["주요제품"] = 주요제품

    col = df.columns
    new_col = np.concatenate([col[-3:], col[1:-6], col[-5:-3]])
    df = df[new_col]

    return df


def get_db_data(
    date: str,
    fname: str,
    query: str = "Close >= MAX52 * 0.95 & RS_12M_Rating > 80",
    db_name: str = DEFAULT_DB_WEEKLY,
) -> pd.DataFrame:
    """Query DB data, plot charts, and create PPTX."""
    import os
    import sqlite3

    import matplotlib.pyplot as plt
    import mplfinance as mpf
    from pykrx import stock

    from my_chart.charting.styles import get_korean_market_style
    from my_chart.config import FONT_NAME
    from my_chart.export.pptx_builder import (
        add_image_slide,
        create_widescreen_pptx,
        save_and_cleanup,
    )
    from my_chart.price import fix_zero_ohlc, price_naver
    from my_chart.registry import _code, _sector, add_sector_info

    date = get_nearest_date(date, db_name)
    market_cap = stock.get_market_cap(date)

    df = load_price_with_rs(date, db_name)
    df.dropna(inplace=True)
    df = df.query(query)

    df = add_sector_info(df)

    with sqlite3.connect(f"{db_name}.db") as conn:
        companies = df.index
        s = get_korean_market_style()

        pic_files = []
        for i, comp_name in enumerate(companies):
            if comp_name in ("KOSPI", "KOSDAQ"):
                continue

            plt.ioff()
            plt.close()

            p = price_naver(comp_name, "20180101")
            p = fix_zero_ohlc(p)

            p["MA20"] = p["Close"].rolling(20).mean()
            p["MA50"] = p["Close"].rolling(50).mean()
            p["MA200"] = p["Close"].rolling(200).mean()

            idx_num = p.index.get_loc(pd.to_datetime(date))
            p = p.iloc[idx_num - 250 : idx_num + 100]

            arrow = pd.Series(index=p.index, dtype="float64")
            arrow[date] = p.loc[date]["Close"] * 0.9

            plots = [
                mpf.make_addplot(p[["MA20", "MA50", "MA200"]], panel=0, secondary_y=False),
                mpf.make_addplot(
                    arrow, panel=0, type="scatter", markersize=100, marker="^", color="g"
                ),
            ]

            fig, ax = mpf.plot(
                p,
                type="candle",
                volume=True,
                style=s,
                figsize=(16, 9),
                addplot=plots,
                returnfig=True,
                panel_ratios=(5, 1),
                scale_width_adjustment=dict(candle=1.5),
            )

            시가총액 = market_cap.loc[_code(comp_name), "시가총액"] / 1_0000_0000
            jo, uk = int(시가총액 // 10000), int(시가총액 % 10000)
            sichong = f"{uk} 억" if jo == 0 else f"{jo}조 {uk}억"
            fig.suptitle(
                comp_name + f"\n({sichong}원)", fontsize=24, fontfamily=FONT_NAME
            )

            filename = f"./.cache/price{i + 1}"
            plt.savefig(filename, bbox_inches="tight", pad_inches=0.2)
            plt.close("all")
            pic_files.append(filename + ".png")

    plt.ion()

    prs = create_widescreen_pptx()
    for f in pic_files:
        add_image_slide(prs, f)

    import datetime as dt

    now_str = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.getcwd(), f"{fname}_{now_str}.pptx")
    save_and_cleanup(prs, output_path, pic_files)

    return df
