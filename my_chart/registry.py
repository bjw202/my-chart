"""Stock and sector registry with lazy loading.

Primary data source: sectormap-original.xlsx (2,500+ stocks with sector and financial info).
Header is at row 8 (header=8 skips notes/주석 rows 0~7).
한글/개행 컬럼명 '종목\n코드', '종목명', '시장' → 'Code', 'Name', 'Market'로 rename.
사용하는 6개 컬럼만 select하여 메모리 사용 최소화 (전체 53 컬럼 중).
pykrx는 시가총액 query 시에만 별도 호출 (이 모듈 scope 밖).
"""

from __future__ import annotations

import logging

import pandas as pd

from my_chart.config import REFERENCE_STOCK, SECTORMAP_PATH

logger = logging.getLogger(__name__)

# @MX:WARN: [AUTO] Global mutable state - lazy-loaded singletons shared across all callers
# @MX:REASON: Not thread-safe for concurrent initialization; DataFrame references could be mutated by callers
_df_stock: pd.DataFrame | None = None
_df_sector: pd.DataFrame | None = None


def _normalize_sector_column(series: pd.Series) -> pd.Series:
    """섹터 컬럼에서 빈 값, nan, '-' 등을 '기타'로 정규화."""
    return (
        series
        .fillna("기타")
        .astype(str)
        .str.strip()
        .replace({"": "기타", "-": "기타", "nan": "기타", "NaN": "기타", "None": "기타"})
    )


# @MX:ANCHOR: [AUTO] sectormap loader — fan_in 8+ (registry/meta_service/sector_advanced/screen_service/stage_service)
# @MX:REASON: 한 곳에서 sectormap-original.xlsx를 로드하여 단일 source 원칙 유지.
#   header=8 + 컬럼 rename은 본 함수에서만 처리되어야 downstream 코드 변경 0.
def _load_sectormap() -> pd.DataFrame:
    """sectormap-original.xlsx 로드 → 영문 컬럼 6개 DataFrame 반환.

    파일 구조 (sectormap-original.xlsx):
    - row 0~7: 데이터 설명 주석 (header가 아님)
    - row 8: 실제 header 행 ('종목\\n코드', '종목명', '시장', '산업명(대)', '산업명(중)', '주요제품', + 47개 재무/주가 컬럼)
    - row 9+: 데이터 (2556 종목)

    동작:
    1. header=8로 실제 헤더 행 지정
    2. 한글/개행 컬럼명 → 영문 (downstream 코드 변경 0 보장)
    3. 사용 6 컬럼만 select (메모리 88% 절약, 47개 추가 컬럼 drop)
    4. Code zfill(6) — 9, A0 같은 짧은/특수 코드도 6자리 정규화
    5. 섹터 컬럼 정규화 (_normalize_sector_column)
    """
    # header=8: 앞 8개 row는 데이터 설명 주석 — 실제 컬럼명은 row 8
    df = pd.read_excel(str(SECTORMAP_PATH), header=8)
    # 한글/개행 컬럼명 → 영문 (downstream 호환)
    df = df.rename(columns={
        "종목\n코드": "Code",
        "종목명": "Name",
        "시장": "Market",
    })
    # 사용하는 6개 컬럼만 select (전체 53 컬럼 중) — 메모리 절약 + downstream 동일
    df = df[["Code", "Name", "Market", "산업명(대)", "산업명(중)", "주요제품"]].copy()
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    # 섹터 컬럼 정규화: 빈 값, nan, '-' 등을 '기타'로 처리
    for col in ["산업명(대)", "산업명(중)"]:
        if col in df.columns:
            df[col] = _normalize_sector_column(df[col])
    return df


def get_stock_registry() -> pd.DataFrame:
    """Lazily load stock registry from sectormap-original.xlsx.

    Returns DataFrame with columns: Code, Name, Market.
    Code is zero-padded to 6 digits.
    """
    global _df_stock
    if _df_stock is None:
        df = _load_sectormap()
        _df_stock = df[["Code", "Name", "Market"]].copy()
        logger.info("Stock registry loaded: %d stocks", len(_df_stock))
    return _df_stock


def get_sector_registry() -> pd.DataFrame:
    """Lazily load full sector registry from sectormap-original.xlsx."""
    global _df_sector
    if _df_sector is None:
        _df_sector = _load_sectormap()
        _df_sector.sort_values(by="산업명(대)", ascending=True, inplace=True)
    return _df_sector


# @MX:ANCHOR: [AUTO] Stock name to code lookup - fan_in=9, used by price, charting, db, screening, export
# @MX:REASON: Core mapping function; returns sentinel "NoCode" on failure instead of raising
def _code(x: str) -> str:
    """Get stock code from name."""
    df = get_stock_registry()
    try:
        filtered = df.query("Name == @x")
        if not filtered.empty:
            return filtered["Code"].values[0]
        return "NoCode"
    except (KeyError, IndexError):
        return "NoCode"


def _name(x: str) -> str:
    """Get stock name from code."""
    df = get_stock_registry()
    try:
        filtered = df.query("Code == @x")
        if not filtered.empty:
            return filtered["Name"].values[0]
        return "NonName"
    except (KeyError, IndexError):
        return "NonName"


def _market(x: str) -> str:
    """Get market (KOSPI/KOSDAQ) from stock name."""
    df = get_stock_registry()
    try:
        filtered = df.query("Name == @x")
        if not filtered.empty:
            return filtered["Market"].values[0]
        return "NonMarket"
    except (KeyError, IndexError):
        return "NonMarket"


# @MX:ANCHOR: [AUTO] Stock sector lookup - fan_in=5, used by queries, momentum, bulk charting, tradingview
# @MX:REASON: Returns (dict, str) tuple; callers must check summary string "NoData" not the dict
def _sector(x: str) -> tuple[dict, str]:
    """Get sector info for a stock name."""
    df = get_sector_registry()
    try:
        c = _code(x)
        sector = df[df["Code"] == c]
        data_dict = sector.to_dict(orient="records")[0]
        summary_txt = f"{data_dict['산업명(대)']}> {data_dict['산업명(중)']}> {data_dict['주요제품']}"
        return data_dict, summary_txt
    except (KeyError, IndexError):
        sector_dict = {
            "Code": "None",
            "Name": "None",
            "Market": "None",
            "산업명(대)": "None",
            "산업명(중)": "None",
            "주요제품": "None",
        }
        return sector_dict, "NoData"


# @MX:ANCHOR: [AUTO] DataFrame sector enrichment - fan_in=4, used by queries, momentum, bulk, tradingview
# @MX:REASON: Mutates input DataFrame in-place (adds 3 columns); callers expect Name-indexed DataFrame
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

    Note: get_market_cap_safe()를 통해 pykrx 인증 세션을 사용하며,
    실패 시 sectormap 폴백을 적용한다.
    """
    from my_chart.krx_session import get_market_cap_safe
    from my_chart.price import price_naver

    a = price_naver(REFERENCE_STOCK, start="20240101")
    day = a.index[-1].strftime("%Y%m%d")
    mc = get_market_cap_safe(day)

    mc_filter = mc.query(f"시가총액>{market_cap * 100000000}")
    companies = []
    market_caps = []
    for ticker in mc_filter.index:
        try:
            name = _name(ticker)
            if name != "NonName":
                companies.append(name)
                market_caps.append(mc_filter.loc[ticker]["시가총액"])
        except (KeyError, IndexError):
            logger.debug("Skipping ticker %s", ticker)

    result = pd.DataFrame(companies, columns=["Name"])
    result.set_index("Name", inplace=True)
    result["시가총액"] = market_caps
    return result
