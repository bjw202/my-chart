"""
FnGuide HTML/JSON 파싱 유틸리티

HTML 테이블 파싱과 문자열-숫자 변환을 담당한다.
외부 네트워크 의존성 없음.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from bs4 import Tag


def table_parsing(table: Tag) -> tuple[str, pd.DataFrame]:
    """FnGuide HTML 테이블을 DataFrame으로 파싱한다.

    Args:
        table: BeautifulSoup의 <table> 태그 요소

    Returns:
        (account_type, df): 회계 유형 문자열과 수치 데이터 DataFrame
    """
    rows = table.find_all("tr")

    th: list[list[str]] = []
    for row in rows:
        cols = row.find_all("th")
        th.append([x.text.strip() for x in cols])

    td: list[list[str]] = []
    for row in rows:
        cols = row.find_all("td")
        td.append([x.text.strip() for x in cols])

    account_type: str = th[0][0]
    columns: list[str] = th[0][1:]
    numbers = np.array(td[1:][:], dtype=object)
    index: list[str] = [n[0] for n in th[1:]]

    df = pd.DataFrame(numbers, columns=columns, index=index)  # type: ignore[arg-type]
    df = convert_string_to_number(df)
    df.index.name = account_type
    return account_type, df


def convert_string_to_number(
    df: pd.DataFrame,
    fillna: float = 0,
) -> pd.DataFrame:
    """DataFrame의 문자열 셀을 수치로 변환한다 (컬럼 단위 벡터화).

    원본 O(n²) 셀 단위 루프 대신 컬럼 단위 pd.to_numeric을 사용하여 성능을 개선한다.

    Args:
        df: 변환할 DataFrame
        fillna: '-' 또는 빈 문자열 대체값 (기본 0, NaN 허용 시 np.nan 전달)

    Returns:
        수치형으로 변환된 DataFrame
    """
    keep_nan = isinstance(fillna, float) and math.isnan(fillna)
    df = df.replace(["-", ""], np.nan)  # 먼저 NaN으로 통일

    for col in df.columns:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            )
        if not keep_nan:
            df[col] = df[col].fillna(fillna)

    return df


def remove_E(columns: list[str] | pd.Index) -> list[str]:
    """컬럼명에서 '(E)' 접미사를 제거한다."""
    return [str(col).replace("(E)", "") for col in columns]


def remove_space(index: list[str] | pd.Index) -> list[str]:
    """인덱스 값에서 공백을 제거한다."""
    return [str(idx).replace(" ", "") for idx in index]


def to_num(x: str) -> int | float:
    """콤마 포맷 문자열을 int 또는 float으로 변환한다.

    Returns:
        정수 또는 실수. 변환 실패 시 0.
    """
    num = x.replace(",", "")
    try:
        if "." in num:
            return float(num)
        return int(num)
    except ValueError:
        return 0
