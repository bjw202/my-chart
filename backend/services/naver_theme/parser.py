import math
import re

from bs4 import BeautifulSoup

# REQ-NT-003: theme_id는 href의 ?no=(\d+) 에서 추출 (A-7)
_THEME_NO_RE = re.compile(r"no=(\d+)")
# REQ-NT-006: stock_code는 href의 ?code=(\d{6}) 에서 추출
_STOCK_CODE_RE = re.compile(r"code=(\d{6})")

# REQ-NT-003, REQ-NT-NF-005: 한글 단위 변환 (조/억/천만/백만/만)
_KOREAN_UNIT: dict[str, float] = {
    "조": 1_000_000_000_000,
    "억": 100_000_000,
    "천만": 10_000_000,
    "백만": 1_000_000,
    "만": 10_000,
}
_KOREAN_NUMBER_RE = re.compile(r"([\d,]+(?:\.\d+)?)\s*(조|억|천만|백만|만)?")


def to_num(x: str) -> float:
    # 콤마/공백/퍼센트 제거 후 float; 변환 불가 또는 센티널('-','N/A','') → NaN
    s = (x or "").replace(",", "").strip().replace("%", "")
    if s in ("", "-", "N/A"):
        return math.nan
    try:
        return float(s)
    except ValueError:
        return math.nan


def _parse_korean_number(text: str) -> float:
    # '1,289조 1,044억', '524억', '1.2조' 등을 원 단위 float으로 누적 합산
    if not text:
        return math.nan
    total = 0.0
    matched = False
    for raw, unit in _KOREAN_NUMBER_RE.findall(text):
        if not raw:
            continue
        val = float(raw.replace(",", ""))
        total += val * _KOREAN_UNIT.get(unit, 1)
        matched = True
    return total if matched else math.nan


def parse_theme_list(html: str) -> dict:
    # REQ-NT-002, REQ-NT-003: 테마 목록 파싱 및 last_page 탐지
    # Returns {'themes': [...], 'last_page': int}
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table.type_1 tr")
    themes: list[dict] = []

    for row in rows:
        anchor = row.select_one("td.col_type1 a")
        if not anchor:
            continue
        href = anchor.get("href", "")
        m = _THEME_NO_RE.search(href)
        if not m:
            continue
        theme_id = int(m.group(1))
        cells = row.find_all("td")
        if len(cells) < 7:
            continue
        themes.append({
            "theme_id": theme_id,
            "theme_name": anchor.get_text(strip=True),
            "change_pct": to_num(cells[1].get_text()),
            "change_pct_3d": to_num(cells[2].get_text()),
            "up_count": to_num(cells[3].get_text()),
            "flat_count": to_num(cells[4].get_text()),
            "down_count": to_num(cells[5].get_text()),
            "top_stocks_preview": cells[6].get_text(" ", strip=True) if len(cells) > 6 else "",
        })

    # REQ-NT-003: 페이지네이션 블록에서 최대 페이지 번호 추출
    last_page = 1
    for a in soup.select("table.Nnavi a, td.pgRR a"):
        txt = a.get_text(strip=True)
        if txt.isdigit():
            last_page = max(last_page, int(txt))

    return {"themes": themes, "last_page": last_page}


def parse_theme_detail(html: str, theme_id: int, theme_name: str) -> list[dict]:
    # REQ-NT-006, REQ-NT-008: 테마 상세 종목 파싱
    # 컬럼 매핑 (A-6):
    #   td[0] 종목명 (a.tltle), code는 href에서 추출
    #   td[1] 편입사유 (REQ-NT-008)
    #   td[2] 현재가
    #   td[3] 전일비
    #   td[4] 등락률
    #   td[7] 거래량
    #   td[8] 거래대금 (_parse_korean_number)
    # PER/ROE = NaN 고정 (A-5)
    soup = BeautifulSoup(html, "lxml")
    stocks: list[dict] = []

    for row in soup.select("table.type_5 tr"):
        anchor = row.select_one("td a.tltle, td a[href*='code=']")
        if not anchor:
            continue
        href = anchor.get("href", "")
        m = _STOCK_CODE_RE.search(href)
        if not m:
            continue
        cells = row.find_all("td")
        if len(cells) < 9:
            continue
        volume_text = cells[7].get_text(strip=True)
        trade_text = cells[8].get_text(strip=True)
        stocks.append({
            "theme_id": theme_id,
            "theme_name": theme_name,
            "stock_code": m.group(1),
            "stock_name": anchor.get_text(strip=True),
            "inclusion_reason": cells[1].get_text(" ", strip=True),
            "price": to_num(cells[2].get_text()),
            "change": to_num(cells[3].get_text()),
            "change_pct": to_num(cells[4].get_text()),
            "volume": int(_parse_korean_number(volume_text)) if volume_text else 0,
            "trade_value": int(_parse_korean_number(trade_text)) if trade_text else 0,
            "per": math.nan,
            "roe": math.nan,
        })

    return stocks
