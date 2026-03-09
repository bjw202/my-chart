"""
FnGuide HTTP 크롤링 계층

FnGuide 각 페이지에서 데이터를 수집하여 DataFrame으로 반환한다.
"""

from __future__ import annotations

import json
import time
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
from lxml import html

from .parser import (
    convert_string_to_number,
    remove_E,
    remove_space,
    table_parsing,
    to_num,
)

# FnGuide URL 템플릿
_SNAP_URL = (
    "http://comp.fnguide.com/SVO2/asp/SVD_Main.asp"
    "?pGB=1&cID=&MenuYn=Y&ReportGB=&NewMenuID=101&stkGb=701&gicode=A{code}"
)
_FS_URL = (
    "http://comp.fnguide.com/SVO2/asp/SVD_Finance.asp"
    "?pGB=1&cID=&MenuYn=Y&ReportGB=&NewMenuID=103&stkGb=701&gicode=A{code}"
)
_CONS_D_URL = "http://comp.fnguide.com/SVO2/json/data/01_06/01_A{code}_A_D.json"
_CONS_B_URL = "http://comp.fnguide.com/SVO2/json/data/01_06/01_A{code}_A_B.json"
# 기본 크롤링 대기 시간 (초)
_CRAWL_DELAY = 0.1


def read_snapshot(
    code: str,
    account_type: str = "IFRS(연결)",
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """FnGuide 스냅샷 페이지를 크롤링한다.

    Args:
        code: 종목 코드 (6자리 숫자 문자열)
        account_type: 'IFRS(연결)' 또는 'IFRS(별도)'

    Returns:
        (report, df_snap, df_snap_ann)
        - report: 종가, 시가총액, 발행주식수 등 주요 지표 dict
        - df_snap: 분기 스냅샷 DataFrame
        - df_snap_ann: 연간 예상 포함 스냅샷 DataFrame
    """
    snap_url = _SNAP_URL.format(code=code)
    snap_page = requests.get(snap_url)
    snap_tables = pd.read_html(StringIO(snap_page.text))

    # tbody.text 파싱: 이름/값 교대 구조
    soup = BeautifulSoup(snap_page.text, "html.parser")
    tbody = soup.tbody
    if tbody is None:
        raise ValueError(f"FnGuide 스냅샷 페이지에서 tbody를 찾을 수 없습니다: {code}")
    temp = tbody.text.split("\n")

    cnt = 0
    name: list[str] = []
    value: list[str] = []
    for txt in temp:
        if txt != "":
            if cnt % 2 == 0:
                name.append(txt)
            else:
                value.append(txt)
            cnt += 1

    # 이름-값 쌍을 dict로 변환하여 위치 의존성 제거
    nv_lookup: dict[str, str] = {}
    for n, v in zip(name, value):
        nv_lookup[n] = v

    report: dict = {}

    # 이름 기반 탐색 (위치 의존성 제거)
    def _find_value(keyword: str) -> str:
        """이름에 keyword를 포함하는 첫 번째 값을 반환한다."""
        for n, v in zip(name, value):
            if keyword in n:
                return v
        return ""

    high_low = _find_value("52주")
    if "/" in high_low:
        high, low = high_low.split("/")
        report["52주.최고가"] = to_num(high)
        report["52주.최저가"] = to_num(low)

    report["거래대금(억원)"] = to_num(_find_value("거래대금"))
    report["시가총액(상장예정포함,억원)"] = to_num(_find_value("시가총액(상장예정포함"))
    report["베타(1년)"] = to_num(_find_value("베타"))
    report["시가총액(보통주,억원)"] = to_num(_find_value("시가총액(보통주)"))
    report["액면가"] = to_num(_find_value("액면가"))

    shares_str = _find_value("발행주식수")
    if "/" in shares_str:
        botong, usun = shares_str.split("/")
        report["발행주식수(보통주)"] = to_num(botong)
        report["발행주식수(우선주)"] = to_num(usun)
    else:
        report["발행주식수(보통주)"] = to_num(shares_str)
        report["발행주식수(우선주)"] = 0

    udong_str = _find_value("유동주식수")
    if "/" in udong_str:
        udong, udong_ratio = udong_str.split("/")
        report["유통주식수"] = to_num(udong)
        report["유통주식비율"] = to_num(udong_ratio)
    else:
        report["유통주식수"] = to_num(udong_str)
        report["유통주식비율"] = 0

    # 사업 요약 (bizSummaryContent)
    ul = soup.find(id="bizSummaryContent")
    summary = "\n"
    if ul is not None:
        for element in ul.find_all("li"):
            summary += element.text.replace("\xa0", " ") + "   "
    report["Summary"] = summary

    # 자기주식 (tables[4] 기준)
    tables = soup.find_all("table")
    treasury_table = tables[4] if len(tables) > 4 else None
    td: list[list[str]] = []
    if treasury_table is not None:
        for row in treasury_table.find_all("tr"):
            cols = row.find_all("td")
            td.append([x.text.strip() for x in cols])
    report["자기주식"] = to_num(td[5][1]) if len(td) > 5 else 0

    # PER/PBR 등 valuation 지표 (lxml XPath)
    tree = html.fromstring(snap_page.content)
    report["PER"] = snap_tables[8].iloc[4, 1]
    report["12M PER"] = tree.xpath('//*[@id="corp_group2"]/dl[2]/dd/text()')[0]
    report["업종 PER"] = tree.xpath('//*[@id="corp_group2"]/dl[3]/dd/text()')[0]
    report["PBR"] = tree.xpath('//*[@id="corp_group2"]/dl[4]/dd/text()')[0]
    report["배당수익률"] = tree.xpath('//*[@id="corp_group2"]/dl[5]/dd/text()')[0]

    # 연결/별도에 따라 스냅샷 테이블 인덱스 다름
    if account_type == "IFRS(연결)":
        df_snap = _extract_snap_table(snap_tables[10])
        df_snap_ann = _extract_snap_table(snap_tables[11])
    else:
        df_snap = _extract_snap_table(snap_tables[13])
        df_snap_ann = _extract_snap_table(snap_tables[14])

    return report, df_snap, df_snap_ann


def _extract_snap_table(df_temp: pd.DataFrame) -> pd.DataFrame:
    """멀티레벨 컬럼을 가진 스냅샷 테이블을 정리한다."""
    col_name1, col_name2 = df_temp.columns[0]
    new_index = df_temp[col_name1][col_name2]
    df_temp = df_temp.set_index(new_index)
    return df_temp.drop((col_name1, col_name2), axis=1)  # type: ignore[arg-type]


def read_fs(
    code: str,
) -> tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    """FnGuide 재무제표 페이지를 크롤링한다.

    테이블 순서: 0=연간손익, 1=분기손익, 2=연간재무, 3=분기재무, 4=연간현금, 5=분기현금

    Returns:
        (account_type, df_fs_ann, df_fs_quar, df_yoy_base_ann)
        - df_yoy_base_ann: 마지막 기간이 불완전 연도(전년동기 비교 필요)일 때
          '전년동기' 절대값 컬럼 데이터. 불필요 시 None.
    """
    fs_url = _FS_URL.format(code=code)
    fs_page = requests.get(fs_url)

    bs = BeautifulSoup(fs_page.text, "lxml")
    tables = bs.find_all("table")

    account_type, df_bs_ann = table_parsing(tables[0])
    _, df_bs_quar = table_parsing(tables[1])
    _, df_income_ann = table_parsing(tables[2])
    _, df_income_quar = table_parsing(tables[3])
    _, df_cash_ann = table_parsing(tables[4])
    _, df_cash_quar = table_parsing(tables[5])

    df_fs_ann = pd.concat([df_bs_ann, df_income_ann, df_cash_ann], sort=False)
    df_fs_quar = pd.concat([df_bs_quar, df_income_quar, df_cash_quar], sort=False)

    # 마지막 2개 컬럼 처리: 예상치 컬럼 또는 전년동기 컬럼 여부를 판별한다.
    # FnGuide는 불완전 연도(예: 2025/09) 마지막 컬럼 뒤에
    # '전년동기' 절대값 컬럼과 '전년동기(%)' 컬럼을 삽입한다.
    df_yoy_base_ann: pd.DataFrame | None = None
    cols_ann = list(df_fs_ann.columns)
    if len(cols_ann) >= 2:
        # 마지막 2개 컬럼명이 '전년동기'를 포함하는지 확인
        last_col = str(cols_ann[-1])
        second_last_col = str(cols_ann[-2])
        if "전년동기" in last_col or "전년동기" in second_last_col:
            # 절대값 컬럼(% 표기 없는 컬럼)을 전년동기 기준으로 보존
            # 통상 second_last_col이 절대값, last_col이 (%) 컬럼
            abs_col = second_last_col if "전년동기" in second_last_col else last_col
            df_yoy_base_ann = pd.DataFrame(df_fs_ann[[abs_col]])

    df_fs_ann = df_fs_ann.iloc[:, :-2]
    df_fs_quar = df_fs_quar.iloc[:, :-2]

    return account_type, df_fs_ann, df_fs_quar, df_yoy_base_ann


def read_consensus(
    code: str,
    account_type: str = "IFRS(연결)",
) -> pd.DataFrame:
    """FnGuide 컨센서스 JSON 데이터를 크롤링한다.

    Args:
        code: 종목 코드
        account_type: 'IFRS(연결)' 또는 'IFRS(별도)'

    Returns:
        계정명을 인덱스로 하는 연간 컨센서스 DataFrame
    """
    if account_type == "IFRS(연결)":
        json_url = _CONS_D_URL.format(code=code)
    else:
        json_url = _CONS_B_URL.format(code=code)

    json_page = requests.get(json_url)
    # FnGuide JSON은 UTF-8 BOM 인코딩
    decoded_data = json_page.text.encode().decode("utf-8-sig")
    data = json.loads(decoded_data)

    df_temp = pd.DataFrame(data["comp"])
    df_temp.columns = df_temp.iloc[0].values  # type: ignore[assignment]
    df_temp = df_temp.iloc[1:].reset_index(drop=True)
    df_temp.set_index(df_temp["항목"], inplace=True)

    # 메타 컬럼 제거 (존재 여부 확인 후)
    cols_to_drop = [c for c in ["항목", "0", "N"] if c in df_temp.columns]
    df_cons = df_temp.drop(cols_to_drop, axis=1)

    df_cons = convert_string_to_number(df_cons, fillna=float("nan"))
    df_cons.index = remove_space(df_cons.index)
    df_cons.columns = remove_E(df_cons.columns)

    return df_cons


def get_fnguide(
    code: str,
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict,
    str,
    pd.DataFrame | None,
]:
    """FnGuide 전체 데이터를 수집하는 통합 함수.

    read_fs → read_snapshot → read_consensus 순서로 호출하며,
    각 요청 사이 0.1초 대기한다.

    Args:
        code: 종목 코드 (6자리)

    Returns:
        (df_fs_ann, df_fs_quar, df_snap, df_snap_ann, df_cons, report,
         account_type, df_yoy_base_ann)
        - df_yoy_base_ann: 전년동기 절대값 데이터 (불완전 연도가 없으면 None)
    """
    time.sleep(_CRAWL_DELAY)
    account_type, df_fs_ann, df_fs_quar, df_yoy_base_ann = read_fs(code)

    time.sleep(_CRAWL_DELAY)
    report, df_snap, df_snap_ann = read_snapshot(code, account_type)

    time.sleep(_CRAWL_DELAY)
    df_cons = read_consensus(code, account_type)

    return df_fs_ann, df_fs_quar, df_snap, df_snap_ann, df_cons, report, account_type, df_yoy_base_ann
