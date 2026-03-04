"""Bulk company charting and PPTX generation."""

from __future__ import annotations

import datetime
import logging
import os
import sqlite3

import matplotlib.pyplot as plt
import mplfinance as mpf
import numpy as np
import pandas as pd
from pptx.util import Cm

from my_chart.charting.styles import get_korean_market_style
from my_chart.config import (
    DEFAULT_DB_WEEKLY,
    FONT_NAME,
    PPTX_HEIGHT,
    PPTX_WIDTH,
    REFERENCE_STOCK,
)
from my_chart.export.pptx_builder import (
    add_grid_slide,
    add_image_slide,
    create_widescreen_pptx,
    save_and_cleanup,
)
from my_chart.indicators import add_moving_averages
from my_chart.krx_session import get_market_cap_safe
from my_chart.price import fix_zero_ohlc, price_naver
from my_chart.registry import (
    _code,
    _name,
    _sector,
    add_sector_info,
    get_stock_registry,
)

logger = logging.getLogger(__name__)


def _generate_ndarray(x: float) -> np.ndarray:
    """Generate tick array from 0 to x in steps of 5."""
    if x >= 0:
        arr = np.arange(0, x + 0.00001, 5)
        if arr[-1] < x:
            arr = np.append(arr, x)
    else:
        arr = np.array([])
    return arr


def plot_all_companies(
    start: str = "2022-11-01",
    freq: str = "day",
    market_cap: float | None = None,
    MA50_Filter: bool = False,
) -> None:
    """Plot all companies (filtered by market cap) and export to 4-up PPTX."""
    df_stock = get_stock_registry()
    companies = df_stock["Name"].values

    a = price_naver(REFERENCE_STOCK, start="20230101")
    day = a.index[-1].strftime("%Y%m%d")
    mc = get_market_cap_safe(day)

    시가총액 = []
    if market_cap is not None:
        mc_filter = mc.query(f"시가총액>{market_cap * 100000000}")
        companies = []
        for ticker in mc_filter.index:
            try:
                name = _name(ticker)
                if name != "NonName":
                    companies.append(name)
                    시가총액.append(mc_filter.loc[ticker]["시가총액"])
            except (KeyError, IndexError):
                pass

    df = pd.DataFrame(companies, columns=["Name"])
    df.set_index("Name", inplace=True)
    df["시가총액"] = 시가총액 if 시가총액 else [0] * len(companies)
    df = add_sector_info(df)

    df.loc[df["산업명(대)"] == "None", "산업명(대)"] = "후_미분류"
    df.sort_values(
        by=["산업명(대)", "산업명(중)", "시가총액"],
        ascending=[True, True, False],
        inplace=True,
    )
    companies = df.index.values

    시가총액 = []
    for name in companies:
        try:
            ticker = _code(name)
            시가총액.append(int(mc.loc[ticker, "시가총액"] / 1_0000_0000))
        except (KeyError, IndexError):
            시가총액.append(0)

    s = get_korean_market_style()
    pic_files = []
    ticker_codes = []

    kospi = price_naver("KOSPI", start, freq=freq)

    from tqdm import tqdm

    for i, comp_name in enumerate(tqdm(companies, desc="Processing")):
        try:
            plt.ioff()
            plt.close()

            p = price_naver(comp_name, "2020-01-01", freq=freq)
            p = fix_zero_ohlc(p)
            p = add_moving_averages(p, freq)

            p["HLC"] = (p["High"] + p["Low"] + p["Close"]) / 3
            p["Volume"] = p["Volume"] * p["HLC"] / 1_0000_0000
            p = p.loc[start:]
            p["RS_Line"] = p["Close"] / kospi["Close"]

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

            if freq == "day":
                ma_cols = ["MA10", "MA20", "MA50", "MA200"]
            else:
                ma_cols = ["MA20", "MA50", "MA200"]

            plots = [
                mpf.make_addplot(p[ma_cols], panel=0, secondary_y=False),
                mpf.make_addplot(
                    kospi["Close"], color="limegreen", panel=2, ylabel="KOSPI"
                ),
                mpf.make_addplot(
                    p["RS_Line"],
                    color="orange",
                    panel=2,
                    secondary_y=True,
                    ylabel="RS Line",
                ),
            ]

            fig, ax = mpf.plot(
                p,
                type="candle",
                volume=True,
                style=s,
                figsize=(21, 9),
                alines=dict(alines=seq_of_points, colors=["b", "r"], alpha=0.3),
                addplot=plots,
                returnfig=True,
                panel_ratios=(6, 1, 2),
                scale_width_adjustment=dict(candle=1.5),
            )
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

            jo, uk = 시가총액[i] // 10000, 시가총액[i] % 10000
            sichong = f"{uk} 억" if jo == 0 else f"{jo}조 {uk}억"
            fig.suptitle(
                comp_name + f"\n({sichong})", fontsize=21, fontfamily=FONT_NAME
            )
            _, sector_txt = _sector(comp_name)
            fig.text(
                0.5, 0.9, sector_txt,
                ha="center", va="center", fontsize=12, fontfamily=FONT_NAME,
            )

            filename = f"./.cache/price{i + 1}"
            ticker_codes.append(_code(comp_name))
            plt.savefig(filename, bbox_inches="tight", pad_inches=0.2)
            plt.close("all")
            pic_files.append(filename + ".png")
        except Exception as e:
            logger.debug("Skipping %s: %s", comp_name, e)

    plt.ion()

    # Build 4-up PPTX
    prs = create_widescreen_pptx()
    num_comp = len(pic_files)
    num_ppt = (num_comp + 3) // 4

    for i in range(num_ppt):
        files = pic_files[i * 4: i * 4 + 4]
        links = [
            {
                "TradingView": f"https://kr.tradingview.com/chart/?symbol=KRX:{ticker_codes[i * 4 + j]}",
                "Naver News": f"https://finance.naver.com/item/news.naver?code={ticker_codes[i * 4 + j]}",
            }
            for j in range(len(files))
        ]
        add_grid_slide(prs, files, links)

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(
        os.getcwd(), f"price_{now_str}_시총{market_cap}_{freq}.pptx"
    )
    save_and_cleanup(prs, output_path, pic_files)


def plot_all_companies_rs_history(
    start: str = "2022-01-01",
    market_cap: float | None = None,
    db_name: str = DEFAULT_DB_WEEKLY,
) -> None:
    """Plot RS history for all companies and export to PPTX."""
    df_stock = get_stock_registry()
    companies = df_stock["Name"].values

    a = price_naver(REFERENCE_STOCK, start="20230101")
    day = a.index[-1].strftime("%Y%m%d")
    mc = get_market_cap_safe(day)

    시가총액 = []
    if market_cap is not None:
        mc_filter = mc.query(f"시가총액>{market_cap * 100000000}")
        companies = []
        for ticker in mc_filter.index:
            try:
                name = _name(ticker)
                if name != "NonName":
                    companies.append(name)
                    시가총액.append(mc_filter.loc[ticker]["시가총액"])
            except (KeyError, IndexError):
                pass

    df = pd.DataFrame(companies, columns=["Name"])
    df.set_index("Name", inplace=True)
    df["시가총액"] = 시가총액 if 시가총액 else [0] * len(companies)
    df = add_sector_info(df)

    df.loc[df["산업명(대)"] == "None", "산업명(대)"] = "후_미분류"
    df.sort_values(
        by=["산업명(대)", "산업명(중)", "시가총액"],
        ascending=[True, True, False],
        inplace=True,
    )
    companies = df.index.values

    시가총액 = []
    for name in companies:
        try:
            ticker = _code(name)
            시가총액.append(int(mc.loc[ticker, "시가총액"] / 1_0000_0000))
        except (KeyError, IndexError):
            시가총액.append(0)

    # Get date range from reference stock
    with sqlite3.connect(f"{db_name}.db") as conn:
        df_ref = pd.read_sql_query(
            "SELECT Date, Open, High, Low, Close, Volume, RS_Line "
            "FROM stock_prices WHERE Name = ? AND Date >= ?",
            conn,
            params=[REFERENCE_STOCK, start],
        )
        df_ref.set_index("Date", inplace=True)
        df_ref.index = pd.to_datetime(df_ref.index, format="%Y-%m-%d")

        start_str = datetime.datetime.strftime(df_ref.index[0], "%Y%m%d")
        end_str = datetime.datetime.strftime(df_ref.index[-1], "%Y%m%d")
        BM = price_naver("KOSPI", start_str, end=end_str, freq="week")

        s = get_korean_market_style()
        pic_files = []
        ticker_codes = []

        for i, comp_name in enumerate(companies):
            try:
                plt.ioff()
                plt.close()

                df_comp = pd.read_sql_query(
                    "SELECT Date, Open, High, Low, Close, Volume "
                    "FROM stock_prices WHERE Name = ? AND Date >= ?",
                    conn,
                    params=[comp_name, start],
                )
                df_comp.set_index("Date", inplace=True)
                df_comp.index = pd.to_datetime(df_comp.index, format="%Y-%m-%d")

                df_comp_rs = pd.read_sql_query(
                    "SELECT * FROM relative_strength "
                    "WHERE Name = ? AND Date >= ?",
                    conn,
                    params=[comp_name, start],
                )
                df_comp_rs.set_index("Date", inplace=True)
                df_comp_rs.index = pd.to_datetime(df_comp_rs.index, format="%Y-%m-%d")

                df_comp = pd.concat(
                    [df_comp, df_comp_rs[["RS_12M_Rating", "RS_6M_Rating"]]], axis=1
                )

                df_comp = fix_zero_ohlc(df_comp)

                last_days = df_comp[-25:]
                max_close_date = last_days["Close"].idxmax().strftime("%Y-%m-%d")
                min_close_date = last_days["Close"].idxmin().strftime("%Y-%m-%d")
                max_close_price = df_comp["Close"][max_close_date]
                min_close_price = df_comp["Close"][min_close_date]

                _today = df_comp.index[-1].strftime("%Y-%m-%d")
                _price = df_comp["Close"][_today]

                seq_of_points = [
                    [(max_close_date, max_close_price), (_today, _price)],
                    [(min_close_date, min_close_price), (_today, _price)],
                ]

                up = 100 * (_price - min_close_price) / min_close_price
                down = 100 * (_price - max_close_price) / max_close_price

                plots = [
                    mpf.make_addplot(
                        df_comp["RS_12M_Rating"],
                        color="limegreen",
                        width=1,
                        panel=2,
                        secondary_y=False,
                        ylabel="RS_Rating",
                        ylim=(0, 100),
                    ),
                    mpf.make_addplot(
                        df_comp["RS_6M_Rating"],
                        color="blueviolet",
                        width=1,
                        panel=2,
                        secondary_y=True,
                    ),
                ]

                fig, ax = mpf.plot(
                    df_comp,
                    title=comp_name,
                    type="candle",
                    volume=True,
                    mav=(4, 10, 40),
                    style=s,
                    figsize=(16, 9),
                    alines=dict(alines=seq_of_points, colors=["b", "r"], alpha=0.3),
                    addplot=plots,
                    returnfig=True,
                    panel_ratios=(6, 1, 2),
                    scale_width_adjustment=dict(candle=1.3),
                )

                jo, uk = 시가총액[i] // 10000, 시가총액[i] % 10000
                sichong = f"{uk} 억" if jo == 0 else f"{jo}조 {uk}억"
                fig.suptitle(
                    comp_name + f"\n({sichong}원)", fontsize=21, fontfamily=FONT_NAME
                )

                filename = f"./.cache/rs{i + 1}"
                ticker_codes.append(_code(comp_name))
                plt.savefig(filename, bbox_inches="tight", pad_inches=0.2)
                plt.close("all")
                pic_files.append(filename + ".png")

                print(f"\r{i + 1}/{len(companies)}", end="")
            except Exception as e:
                logger.debug("Skipping %s: %s", comp_name, e)

    plt.ion()

    prs = create_widescreen_pptx()
    for idx, f in enumerate(pic_files):
        links = {
            "TradingView": f"https://kr.tradingview.com/chart/?symbol=KRX:{ticker_codes[idx]}",
            "Naver News": f"https://finance.naver.com/item/news.naver?code={ticker_codes[idx]}",
        }
        add_image_slide(prs, f, links=links)

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.getcwd(), f"rs_history_{now_str}.pptx")
    save_and_cleanup(prs, output_path, pic_files)


def plot_companies(
    tickers: list[str],
    fname: str,
    freq: str = "day",
    start: str = "2023-01-01",
) -> None:
    """Plot charts for a list of ticker codes and export to PPTX."""
    companies = [_name(x) for x in tickers]

    today = datetime.date.today()
    today_str = f"{today.year}-{today.month:02}-{today.day:02}"

    market_cap_data = get_market_cap_safe(today_str)

    count_try = 0
    while (
        not market_cap_data.empty
        and market_cap_data["시가총액"].iloc[0] == 0
        and count_try < 5
    ):
        today = today - datetime.timedelta(days=1)
        today_str = today.strftime("%Y-%m-%d")
        market_cap_data = get_market_cap_safe(today_str)
        count_try += 1

    df = pd.DataFrame(index=companies)
    df = add_sector_info(df)
    df.sort_values(by="산업명(대)", ascending=True, inplace=True)
    companies = df.index.values

    s = get_korean_market_style()
    pic_files = []
    ticker_codes = []

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

        last_days = p[-80:] if freq == "day" else p[-16:]
        max_close_date = last_days["Close"].idxmax().strftime("%Y-%m-%d")
        min_close_date = last_days["Close"].idxmin().strftime("%Y-%m-%d")

        _today_str = p.index[-1].strftime("%Y-%m-%d")
        _price = p["Close"][_today_str]
        max_close_price = p["Close"][max_close_date]
        min_close_price = p["Close"][min_close_date]

        seq_of_points = [
            [(max_close_date, max_close_price), (_today_str, _price)],
            [(min_close_date, min_close_price), (_today_str, _price)],
        ]

        up = 100 * (_price - min_close_price) / min_close_price
        down = 100 * (_price - max_close_price) / max_close_price

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
            type="candle",
            volume=True,
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
        ymax_pct = (_ymax - last_close) / last_close * 100
        ymin_pct = (_ymin - last_close) / last_close * 100

        a_arr = _generate_ndarray(ymax_pct)
        b_arr = -_generate_ndarray(abs(ymin_pct))[1:]
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
        ticker_codes.append(_code(comp_name))

        print(f"\r{i + 1}/{len(companies)}", end="")

    plt.ion()

    prs = create_widescreen_pptx()
    for idx, file in enumerate(pic_files):
        links = {
            "TradingView": f"https://kr.tradingview.com/chart/?symbol=KRX:{ticker_codes[idx]}",
            "Naver News": f"https://finance.naver.com/item/news.naver?code={ticker_codes[idx]}",
        }
        add_image_slide(prs, file, links=links)

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.getcwd(), f"{fname}_{now_str}.pptx")
    save_and_cleanup(prs, output_path, pic_files)

    # Export TradingView format
    df.reset_index(inplace=True)
    tv_tickers = []
    sector_prev = ""
    for _, row in df.iterrows():
        sector = row["산업명(대)"] + " > " + row["산업명(중)"]
        if sector != sector_prev:
            tv_tickers.append("### " + sector + ",")
            sector_prev = sector
        tv_tickers.append("KRX:" + _code(row["index"]) + ",")

    ticker_df = pd.DataFrame(tv_tickers)
    ticker_df.to_excel(f"{fname}_{now_str}.xlsx")


def excel_companies(tickers: list[str], fname: str) -> None:
    """Export company list to TradingView-format Excel."""
    companies = [_name(x) for x in tickers]

    df = pd.DataFrame(index=companies)
    df = add_sector_info(df)
    df.sort_values(by="산업명(대)", ascending=True, inplace=True)
    df["Code"] = df.index.map(lambda x: _code(x))

    df.reset_index(inplace=True)
    tv_tickers = []
    sector_prev = ""
    for _, row in df.iterrows():
        sector = row["산업명(대)"] + " > " + row["산업명(중)"]
        if sector != sector_prev:
            tv_tickers.append("### " + sector + ",")
            sector_prev = sector
        tv_tickers.append("KRX:" + _code(row["index"]) + ",")

    ticker_df = pd.DataFrame(tv_tickers)
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ticker_df.to_excel(f"{fname}_{now_str}.xlsx")
