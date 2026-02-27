"""Market analysis functions."""

from __future__ import annotations

import datetime
import os

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker
import pandas as pd
from matplotlib.gridspec import GridSpec
from pykrx import stock

from my_chart.config import FONT_NAME, REFERENCE_STOCK
from my_chart.export.pptx_builder import (
    add_image_slide,
    create_widescreen_pptx,
    save_and_cleanup,
)
from my_chart.price import price_naver
from my_chart.registry import _code, get_sector_registry


def market_cap_analysis(start: str = "20231001") -> dict:
    """Analyze market cap trends by industry sector, output to PPTX."""
    a = price_naver(REFERENCE_STOCK, start=start, freq="week")
    weekdate = a.index.strftime("%Y-%m-%d").values

    market_cap = {}
    for day in weekdate:
        mc = stock.get_market_cap(day)
        market_cap[day] = mc[["시가총액", "거래대금"]]

    df_sector = get_sector_registry()
    industry = df_sector["산업명(대)"].unique()

    matplotlib.rc("font", family=FONT_NAME)
    matplotlib.rcParams["axes.unicode_minus"] = False

    pic_files = []
    for j, ind in enumerate(industry):
        plt.ioff()
        plt.close()

        tickers = df_sector[df_sector["산업명(대)"] == ind]["Code"].values

        _data = []
        for day in weekdate:
            _df = market_cap[day]
            existing_tickers = [t for t in tickers if t in _df.index]
            mc_sum = _df.loc[existing_tickers, "시가총액"].sum() / 1_0000_0000_0000
            tv_sum = _df.loc[existing_tickers, "거래대금"].sum() / 1_0000_0000_0000
            _data.append([mc_sum, tv_sum])

        df = pd.DataFrame(_data, columns=["시가총액", "거래대금"])
        df.index = weekdate

        fig = plt.figure(figsize=(20, 9))
        fig.suptitle(ind, fontsize=20, fontfamily=FONT_NAME)
        gs = GridSpec(2, 1, height_ratios=[2, 1])

        ax0 = fig.add_subplot(gs[0])
        ax0.plot(df.index, df["시가총액"], label="시가총액(조)")
        ax0.grid()
        ax0.legend()
        ax0.yaxis.tick_right()

        ax1 = fig.add_subplot(gs[1], sharex=ax0)
        ax1.bar(df.index, df["거래대금"], label="거래대금(조)", color="orange")
        ax1.legend()
        ax1.grid()
        ax1.yaxis.tick_right()

        plt.setp(ax0.get_xticklabels(), visible=False)
        plt.xticks(rotation=45)
        plt.tight_layout()

        filename = f"./.cache/industry{j + 1}"
        pic_files.append(filename + ".png")
        plt.savefig(filename, bbox_inches="tight", pad_inches=0.2)
        plt.close("all")

    plt.ion()

    prs = create_widescreen_pptx()
    for f in pic_files:
        add_image_slide(prs, f)

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.getcwd(), f"섹터분석_{now_str}.pptx")
    save_and_cleanup(prs, output_path, pic_files)

    return market_cap


def market_cap_analysis_detail(start: str = "20240601") -> dict:
    """Detailed daily market cap analysis by sector."""
    a = price_naver(REFERENCE_STOCK, start=start, freq="day")
    daydate = a.index.strftime("%Y-%m-%d").values

    market_cap = {}
    for day in daydate:
        mc = stock.get_market_cap(day)
        market_cap[day] = mc[["시가총액", "거래대금"]]

    df_sector = get_sector_registry()
    industry = df_sector["산업명(대)"].unique()

    matplotlib.rc("font", family=FONT_NAME)
    matplotlib.rcParams["axes.unicode_minus"] = False

    pic_files = []
    for j, ind in enumerate(industry):
        plt.ioff()
        plt.close()

        tickers = df_sector[df_sector["산업명(대)"] == ind]["Code"].values

        _data = []
        for day in daydate:
            _df = market_cap[day]
            existing_tickers = [t for t in tickers if t in _df.index]
            mc_sum = _df.loc[existing_tickers, "시가총액"].sum() / 1_0000_0000_0000
            tv_sum = _df.loc[existing_tickers, "거래대금"].sum() / 1_0000_0000_0000
            _data.append([mc_sum, tv_sum])

        df = pd.DataFrame(_data, columns=["시가총액", "거래대금"])
        df.index = daydate

        fig = plt.figure(figsize=(20, 9))
        fig.suptitle(ind, fontsize=20, fontfamily=FONT_NAME)
        gs = GridSpec(2, 1, height_ratios=[2, 1])

        ax0 = fig.add_subplot(gs[0])
        ax0.plot(df.index, df["시가총액"], label="시가총액(조)")
        ax0.grid()
        ax0.legend()
        ax0.yaxis.tick_right()

        ax1 = fig.add_subplot(gs[1], sharex=ax0)
        ax1.bar(df.index, df["거래대금"], label="거래대금(조)", color="orange")
        ax1.legend()
        ax1.grid()
        ax1.yaxis.tick_right()

        plt.setp(ax0.get_xticklabels(), visible=False)
        plt.xticks(rotation=45)
        plt.tight_layout()

        filename = f"./.cache/industry_d{j + 1}"
        pic_files.append(filename + ".png")
        plt.savefig(filename, bbox_inches="tight", pad_inches=0.2)
        plt.close("all")

    plt.ion()

    prs = create_widescreen_pptx()
    for f in pic_files:
        add_image_slide(prs, f)

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(os.getcwd(), f"섹터분석_일봉_{now_str}.pptx")
    save_and_cleanup(prs, output_path, pic_files)

    return market_cap


def 수급분석(
    comp_list: str | list[str], start: str = "20200401", freq: str = "d"
) -> None:
    """Analyze institutional/foreign trading flow for given stocks."""
    if isinstance(comp_list, str):
        comp_list = [comp_list]

    today = datetime.date.today()
    end = f"{today.year}{today.month:02}{today.day:02}"

    for c in comp_list:
        df = stock.get_market_trading_value_by_date(
            start, end, _code(c), detail=True, freq=freq
        )
        df = df / 1_0000_0000
        df_cumsum = df.cumsum()
        df_cumsum["기관계"] = (
            df_cumsum["연기금"]
            + df_cumsum["사모"]
            + df_cumsum["보험"]
            + df_cumsum["투신"]
        )
        df = df[["개인", "외국인", "연기금", "사모", "보험", "투신", "기타법인"]]

        p = stock.get_market_cap_by_date(start, end, _code(c), freq=freq)
        p["시가총액"] = p["시가총액"] / 1_0000_0000
        p["거래대금"] = p["거래대금"] / 1_0000_0000
        p["거래대금/시총(%)"] = p["거래대금"] / p["시가총액"] * 100

        freq_labels = {"w": "주간", "m": "월간", "y": "연간"}
        sub = freq_labels.get(freq, "일간")

        fig, ax = plt.subplots(4, 1, sharex=True, figsize=(16, 17))
        fig.suptitle(c + f"\n({sub},억원)", fontsize=24)

        p["시가총액"].plot(ax=ax[0], fontsize=14)
        df.plot(ax=ax[1], fontsize=14)
        p["거래대금"].plot(ax=ax[2], fontsize=14)
        ax_twin = ax[2].twinx()
        p["거래대금/시총(%)"].plot(
            ax=ax_twin, color="gray", linestyle="--", fontsize=14
        )
        df_cumsum[["개인", "외국인", "기관계"]].plot(ax=ax[3], fontsize=14)

        for i in range(4):
            ax[i].get_yaxis().set_major_formatter(
                matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ","))
            )
            ax[i].grid()
            ax[i].legend(loc=3)
        ax_twin.legend(loc=1)
        fig.tight_layout(pad=4.0)
