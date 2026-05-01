import re
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import pytz

from backend.services.naver_theme.config import MOMENTUM_WEIGHT_1D, MOMENTUM_WEIGHT_3D


def to_num(x: str) -> int | float:
    """콤마 포맷 문자열을 int 또는 float으로 변환.

    @param x: 입력 문자열
    @return: 변환된 숫자 (변환 불가시 0)
    """
    num = str(x).replace(",", "")
    try:
        if "." in num:
            return float(num)
        return int(num)
    except ValueError:
        return 0


def normalize_money(s: str) -> int | float:
    """한글 화폐 단위를 정규화.

    "1000억" → 100,000,000,000
    "1조" → 1,000,000,000,000
    "100만" → 100,000,000
    """
    s = str(s).strip()

    # 조 단위
    if "조" in s:
        base = to_num(s.replace("조", ""))
        return int(base * 1_000_000_000_000)

    # 억 단위
    if "억" in s:
        base = to_num(s.replace("억", ""))
        return int(base * 100_000_000)

    # 만 단위
    if "만" in s:
        base = to_num(s.replace("만", ""))
        return int(base * 10_000)

    # 일반 숫자
    return to_num(s)


def parse_theme_list(html: str) -> pd.DataFrame:
    """테마 목록 페이지 파싱.

    @param html: HTML 문자열
    @return: 테마 DataFrame (theme_id, theme_name, change_pct, change_pct_3d, ...)
    """
    soup = BeautifulSoup(html, "html.parser")

    themes = []
    collected_at = datetime.now(pytz.timezone("Asia/Seoul")).isoformat()

    # 테마 테이블 찾기
    # 일반적으로 <tr> 태그로 시작하는 행 구조
    rows = soup.find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        try:
            # 첫 번째 td에 테마 링크와 ID 포함
            link = cols[0].find("a")
            if not link:
                continue

            href = link.get("href", "")
            # ?no=178 에서 178 추출
            match = re.search(r"no=(\d+)", href)
            if not match:
                continue

            theme_id = int(match.group(1))
            theme_name = link.text.strip()

            # 등락률 컬럼들 (정렬 순서는 페이지마다 다를 수 있음, 일반적으로)
            change_pct = to_num(cols[1].text.strip())
            change_pct_3d = to_num(cols[2].text.strip())
            up_count = to_num(cols[3].text.strip())
            flat_count = to_num(cols[4].text.strip())
            down_count = to_num(cols[5].text.strip()) if len(cols) > 5 else 0

            themes.append({
                "theme_id": theme_id,
                "theme_name": theme_name,
                "change_pct": change_pct,
                "change_pct_3d": change_pct_3d,
                "up_count": int(up_count),
                "flat_count": int(flat_count),
                "down_count": int(down_count),
                "top_stocks_preview": "",
                "collected_at": collected_at,
            })
        except (IndexError, AttributeError, ValueError):
            continue

    return pd.DataFrame(themes)


def parse_theme_detail(html: str, theme_id: int) -> list[dict]:
    """테마 상세 페이지 파싱 (종목 추출).

    @param html: HTML 문자열
    @param theme_id: 테마 ID
    @return: 종목 정보 리스트
    """
    soup = BeautifulSoup(html, "html.parser")

    stocks = []
    collected_at = datetime.now(pytz.timezone("Asia/Seoul")).isoformat()

    # 테마 상세 페이지의 종목 테이블
    rows = soup.find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        try:
            # 종목 코드와 이름
            link = cols[0].find("a")
            if not link:
                continue

            stock_code_text = link.text.strip()
            # "000001" 또는 "삼성전자(000001)" 형식
            code_match = re.search(r"(\d{6})", stock_code_text)
            if not code_match:
                continue

            stock_code = code_match.group(1)
            stock_name = cols[0].text.strip()

            # 등락률, 거래량 등
            change_pct = to_num(cols[1].text.strip()) if len(cols) > 1 else 0
            volume = to_num(cols[2].text.strip()) if len(cols) > 2 else 0

            stocks.append({
                "stock_code": stock_code,
                "stock_name": stock_name,
                "change_pct": change_pct,
                "volume": int(volume),
                "theme_id": theme_id,
                "collected_at": collected_at,
            })
        except (IndexError, AttributeError, ValueError):
            continue

    return stocks
