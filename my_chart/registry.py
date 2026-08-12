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
def _load_raw_sectormap(path: str | None = None) -> pd.DataFrame:
    """sectormap xlsx 원시 로드(rename/select/zfill/정규화). dedup 전 단계.

    파일 구조 (sectormap-original.xlsx):
    - row 0~7: 데이터 설명 주석 (header가 아님)
    - row 8: 실제 header 행 ('종목\\n코드', '종목명', '시장', '산업명(대)', ...)
    - row 9+: 데이터
    """
    df = pd.read_excel(path or str(SECTORMAP_PATH), header=8)
    df = df.rename(columns={
        "종목\n코드": "Code",
        "종목명": "Name",
        "시장": "Market",
    })
    df = df[["Code", "Name", "Market", "산업명(대)", "산업명(중)", "주요제품"]].copy()
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    for col in ["산업명(대)", "산업명(중)"]:
        if col in df.columns:
            df[col] = _normalize_sector_column(df[col])
    return df


def _dedup_by_code(df: pd.DataFrame) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """Code 기준 중복 제거 — 첫 행 유지, 나머지 drop + WARNING (UN-4 / REQ-SGR-013).

    Returns:
        (deduped_df, [(code, name), ...]) — drop 된 행들의 (Code, 종목명) 목록.
        조용한 무시 금지: drop 마다 WARNING 로그에 Code+종목명을 남긴다.
    """
    dup_mask = df["Code"].duplicated(keep="first")
    dups = [(str(r["Code"]), str(r["Name"])) for _, r in df[dup_mask].iterrows()]
    for code, name in dups:
        logger.warning(
            "registry 중복 Code 감지 — 첫 행 유지, 이 행 drop: Code=%s 종목명=%s",
            code, name,
        )
    return (df[~dup_mask].copy() if dups else df), dups


def _load_sectormap(path: str | None = None) -> pd.DataFrame:
    """sectormap 로드 → dedup 된 영문 컬럼 6개 DataFrame 반환.

    기존 호출부(get_stock_registry/get_sector_registry)와의 호환을 위해 DataFrame 만
    반환한다. dedup 된 행의 (Code, 종목명) 목록이 필요하면 load_sector_registry_with_diagnostics.
    """
    df, _ = _dedup_by_code(_load_raw_sectormap(path))
    return df


def load_sector_registry(path: str | None = None) -> pd.DataFrame:
    """지정 경로(또는 기본 SECTORMAP_PATH) 섹터 registry 로드 + Code-dedup + WARNING.

    universe.py 및 테스트가 경로를 지정해 로드하기 위해 사용한다.
    get_sector_registry() 와 달리 global 캐시를 쓰지 않고 매 호출 시 로드한다.
    """
    return _load_sectormap(path)


def load_sector_registry_with_diagnostics(
    path: str | None = None,
) -> tuple[pd.DataFrame, list[tuple[str, str]]]:
    """섹터 registry 로드 + dedup. (deduped_df, [(code, name), ...]) 반환.

    universe.py 가 UniverseSnapshot.diagnostics 에 drop 된 중복 행을 기록할 때 사용.
    """
    return _dedup_by_code(_load_raw_sectormap(path))


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
