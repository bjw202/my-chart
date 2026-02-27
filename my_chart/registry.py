"""Stock and sector registry with lazy loading.

Primary data source: sectormap.xlsx (2,500+ stocks with Code, Name, Market, sector info).
pykrx is used only for market cap queries where needed.
"""

from __future__ import annotations

import logging

import pandas as pd

from my_chart.config import REFERENCE_STOCK, SECTORMAP_PATH

logger = logging.getLogger(__name__)

# Lazy-loaded singletons
_df_stock: pd.DataFrame | None = None
_df_sector: pd.DataFrame | None = None


def get_stock_registry() -> pd.DataFrame:
    """Lazily load stock registry from sectormap.xlsx.

    Returns DataFrame with columns: Code, Name, Market.
    Code is zero-padded to 6 digits.
    """
    global _df_stock
    if _df_stock is None:
        df = pd.read_excel(str(SECTORMAP_PATH))
        df["Code"] = df["Code"].astype(str).str.zfill(6)
        _df_stock = df[["Code", "Name", "Market"]].copy()
        logger.info("Stock registry loaded: %d stocks", len(_df_stock))
    return _df_stock


def get_sector_registry() -> pd.DataFrame:
    """Lazily load full sector registry from sectormap.xlsx."""
    global _df_sector
    if _df_sector is None:
        _df_sector = pd.read_excel(str(SECTORMAP_PATH))
        _df_sector["Code"] = _df_sector["Code"].astype(str).str.zfill(6)
        _df_sector.sort_values(by="산업명(대)", ascending=True, inplace=True)
    return _df_sector


def _code(x: str) -> str:
    """Get stock code from name."""
    df = get_stock_registry()
    try:
        filtered = df.query("Name == @x")
        if not filtered.empty:
            return filtered["Code"].values[0]
        return "NoCode"
    except Exception:
        return "NoCode"


def _name(x: str) -> str:
    """Get stock name from code."""
    df = get_stock_registry()
    try:
        filtered = df.query("Code == @x")
        if not filtered.empty:
            return filtered["Name"].values[0]
        return "NonName"
    except Exception:
        return "NonName"


def _market(x: str) -> str:
    """Get market (KOSPI/KOSDAQ) from stock name."""
    df = get_stock_registry()
    try:
        filtered = df.query("Name == @x")
        if not filtered.empty:
            return filtered["Market"].values[0]
        return "NonMarket"
    except Exception:
        return "NonMarket"


def _sector(x: str) -> tuple[dict, str]:
    """Get sector info for a stock name."""
    df = get_sector_registry()
    try:
        c = _code(x)
        sector = df[df["Code"] == c]
        data_dict = sector.to_dict(orient="records")[0]
        summary_txt = f"{data_dict['산업명(대)']}> {data_dict['산업명(중)']}> {data_dict['주요제품']}"
        return data_dict, summary_txt
    except Exception:
        sector_dict = {
            "Code": "None",
            "Name": "None",
            "Market": "None",
            "산업명(대)": "None",
            "산업명(중)": "None",
            "주요제품": "None",
        }
        return sector_dict, "NoData"


def add_sector_info(df: pd.DataFrame) -> pd.DataFrame:
    """Add sector columns to a DataFrame indexed by company name."""
    산업명대 = []
    산업명중 = []
    주요제품 = []

    for comp in df.index:
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
    return df


def get_companies_by_market_cap(market_cap: float) -> pd.DataFrame:
    """Get companies filtered by market cap (in 억원).

    Note: This function still requires pykrx for market cap data.
    """
    from pykrx import stock

    from my_chart.price import price_naver

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

    result = pd.DataFrame(companies, columns=["Name"])
    result.set_index("Name", inplace=True)
    result["시가총액"] = market_caps
    return result
