"""TradingView export utilities."""

from __future__ import annotations

import datetime

import pandas as pd
from pykrx import stock

from my_chart.config import REFERENCE_STOCK
from my_chart.price import price_naver
from my_chart.registry import _code, _name, _sector, add_sector_info


def tradingview(market_cap: float = 2000) -> None:
    """Export all stocks above market_cap (억원) to Excel with TradingView tickers."""
    today = datetime.date.today()
    today_str = f"{today.year}{today.month}{today.day}"

    a = price_naver(REFERENCE_STOCK, start="20230101")
    day = a.index[-1].strftime("%Y%m%d")
    mc = stock.get_market_cap(day)

    mc_filter = mc.query(f"시가총액>{market_cap * 100000000}")
    companies = []
    market_caps = []
    for ticker in mc_filter.index:
        try:
            name = _name(ticker)
            if name != "NonName":
                companies.append(name)
                market_caps.append(mc_filter.loc[ticker]["시가총액"])
        except Exception:
            pass

    df = pd.DataFrame(companies, columns=["Name"])
    df.set_index("Name", inplace=True)
    df["시가총액"] = market_caps
    df["Ticker"] = df.index.map(lambda x: "KRX:" + _code(x) + ",")
    df = add_sector_info(df)

    df.sort_values(
        by=["산업명(대)", "산업명(중)", "시가총액"],
        ascending=[True, True, False],
        inplace=True,
    )
    df.to_excel(f"전종목시총_{today_str}_{market_cap}억원.xlsx")


def company_list_tradingview(market_cap: float = 1500) -> None:
    """Export company list split by market cap thresholds."""
    a = price_naver(REFERENCE_STOCK, start="20230101")
    day = a.index[-1].strftime("%Y%m%d")
    mc = stock.get_market_cap(day)

    companies = []
    market_caps = []
    for ticker in mc.index:
        try:
            name = _name(ticker)
            if name != "NonName":
                companies.append(name)
                market_caps.append(mc.loc[ticker]["시가총액"])
        except Exception:
            pass

    df = pd.DataFrame(companies, columns=["Name"])
    df.set_index("Name", inplace=True)
    df["시가총액"] = market_caps
    df = add_sector_info(df)

    df.sort_values(
        by=["산업명(대)", "산업명(중)", "시가총액"],
        ascending=[True, True, False],
        inplace=True,
    )
    df["Code,"] = df.index.map(lambda x: _code(x) + ",")

    df_high = df.query(f"시가총액 >= {2000 * 1_0000_0000}")
    df_low = df.query(
        f"시가총액 > {market_cap * 1_0000_0000} & 시가총액 < {2000 * 1_0000_0000}"
    )
    df_high.to_excel("trading_view_code_2000.xlsx")
    df_low.to_excel("trading_view_code_1500-2000.xlsx")


def company_to_tradingview_text(market_cap: float = 2000) -> None:
    """Export TradingView-format ticker list grouped by sector."""
    a = price_naver(REFERENCE_STOCK, start="20240101")
    day = a.index[-1].strftime("%Y%m%d")
    mc = stock.get_market_cap(day)

    mc_filter = mc.query(f"시가총액>{market_cap * 100000000}")
    companies = []
    market_caps = []
    for ticker in mc_filter.index:
        try:
            name = _name(ticker)
            if name != "NonName":
                companies.append(name)
                market_caps.append(mc_filter.loc[ticker]["시가총액"])
        except Exception:
            pass

    df = pd.DataFrame(companies, columns=["Name"])
    df.set_index("Name", inplace=True)
    df["시가총액"] = market_caps
    df = add_sector_info(df)

    df.loc[df["산업명(대)"] == "None", "산업명(대)"] = "후_미분류"

    df.sort_values(
        by=["산업명(대)", "산업명(중)", "시가총액"],
        ascending=[True, True, False],
        inplace=True,
    )

    df.reset_index(inplace=True)
    tickers = []
    sector_prev = ""

    df.to_excel("sector_industry.xlsx")

    for _, row in df.iterrows():
        try:
            sector = row["산업명(대)"] + " > " + row["산업명(중)"]
            if sector != sector_prev:
                tickers.append("### " + sector + ",")
                sector_prev = sector
            tickers.append("KRX:" + _code(row["Name"]) + ",")
        except Exception:
            pass

    ticker_df = pd.DataFrame(tickers)
    ticker_df.to_excel("tickers.xlsx")


def ticker_to_tradingview(tickers: list[str]) -> None:
    """Convert ticker array to TradingView format Excel."""
    df = pd.DataFrame(tickers, columns=["Ticker"])
    df["TradingView"] = df["Ticker"].map(lambda x: "KRX:" + x + ",")
    df.to_excel("tickers.xlsx")


def sector_stocks(sector: str) -> list[str] | str:
    """Get stock codes for a sector and export to Excel."""
    from my_chart.charting.bulk import excel_companies
    from my_chart.registry import get_sector_registry

    df_s = get_sector_registry().copy()
    df_s.columns = ["Code", "Name", "Market", "Industry", "Sector", "Product"]

    try:
        filtered = df_s.query("Sector == @sector")
        if not filtered.empty:
            tickers = filtered["Code"].values
            excel_companies(tickers, sector)
            return filtered["Code"].values
        return "NoCode"
    except Exception:
        return "NoCode"
