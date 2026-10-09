"""
FnGuide HTTP 크롤링 계층

FnGuide 각 페이지에서 데이터를 수집하여 DataFrame으로 반환한다.
"""

from __future__ import annotations

import json
import logging
import re
import time
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
from lxml import html

from . import account_alias as aa
from .parser import (
    convert_string_to_number,
    remove_E,
    remove_space,
    to_num,
)

logger = logging.getLogger(__name__)

# wcomp 재무제표 JSON API (SPEC-FNGUIDE-WCOMP-001 REQ-WC-001)
_WCOMP_BASE = "https://wcomp.fnguide.com/CompanyInfo/"
_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://wcomp.fnguide.com/",
}
_TIMEOUT = 10  # 초, 요청당 상한
_CODE_RE = re.compile(r"[0-9]{6}")
# 이어 붙이는 순서: 손익 → 대차 → 현금흐름 (REQ-WC-008)
_ENDPOINTS = ("getFinIncome", "getFinBalance", "getFinCashFlow")
_STATEMENT_ORDER = _ENDPOINTS
_RECENT_MARK = "(최근분기)"  # 연간 VAL4가 누적 YTD라는 사이트 표지 (spec D5)
_BALANCE_TOLERANCE = 0.1  # 억원 (spec D7)

# 옛 호스트 컨센서스 URL — read_consensus 전용으로 남김(호출되지 않음, spec §6)
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


def _fetch(endpoint: str, code: str, freq: str, consol: str) -> requests.Response:
    """재무제표 JSON 한 건을 요청한다.

    전송 실패와 2xx 밖 상태는 ConnectionError(라우터 503)로 바꾼다(REQ-WC-003).
    리디렉션은 requests 기본값대로 따라간다 — 없는 종목은 302 뒤 200 HTML 오류
    페이지가 오며, 이 본문이 ValueError(404)가 되어야 한다(M1 V-1).
    """
    try:
        resp = requests.get(
            _WCOMP_BASE + endpoint,
            params={"cmp_cd": code, "freq_typ": freq, "consol_typ": consol},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
    except requests.RequestException as e:
        raise ConnectionError(f"FnGuide 요청 실패 ({code}, {endpoint}): {e}") from e
    if not 200 <= resp.status_code < 300:
        raise ConnectionError(f"FnGuide 응답 상태 {resp.status_code} ({code}, {endpoint})")
    return resp


def _check_dataset(rows: list, periods: list, code: str, endpoint: str) -> None:
    """빈 data와 null 머리글 기간을 ValueError(404)로 판정한다(REQ-WC-002)."""
    if not rows:
        raise ValueError(f"FnGuide 재무제표 데이터 없음 ({code}, {endpoint})")
    if any(p is None for p in periods):
        raise ValueError(
            f"FnGuide 결산 기간 부족 — 보고된 기간이 4개 미만 ({code}, {endpoint})"
        )


def _parse(resp: requests.Response, code: str, endpoint: str) -> tuple[dict, list]:
    """응답 본문을 (머리글 dict, 행 목록)으로 바꾼다. 상태 코드·Content-Type은 믿지 않는다."""
    text = resp.content.decode("utf-8-sig", errors="replace").strip()
    if text.startswith("<"):
        raise ValueError(f"FnGuide 응답이 JSON이 아님(HTML 오류 페이지) ({code}, {endpoint})")
    try:
        dataset = json.loads(text)["dataset"]
        header = {h["CD"]: h.get("YYMM") for h in dataset.get("header") or []}
        rows = dataset.get("data") or []
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        raise ValueError(f"FnGuide 응답 형식 오류 ({code}, {endpoint}): {e}") from e
    _check_dataset(rows, [header.get(f"VAL{i}") for i in range(1, 5)], code, endpoint)
    return header, rows


def _norm(name: object) -> str:
    """행 이름에서 공백과 NBSP(\\xa0)를 지운다(REQ-WC-007)."""
    return str(name).replace(" ", "").replace("\xa0", "")


def _to_float(value: object) -> float:
    """JSON null과 숫자가 아닌 문자열은 0.0(REQ-WC-007)."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def _period(label: str) -> str:
    """머리글 기간에서 앞의 YYYY/MM만 남긴다(예: '2026/06 (최근분기)' → '2026/06')."""
    m = re.match(r"\s*(\d{4}/\d{2})", label)
    return m.group(1) if m else label.strip()


def _choose_consol(c_rows: list | None, b_rows: list | None) -> str:
    """연결/별도를 고른다(REQ-WC-004). 실패한 유형의 행은 None(값 없음)으로 받는다.

    두 유형의 연간 손익 LVL0 당기순이익 중 어느 쪽에든 값이 있는 가장 최근 열
    (VAL4 → VAL1)에서 C 값이 null이 아니면 C, 아니면 B.
    """

    def selection_row(rows: list | None) -> dict:
        for r in rows or []:
            if r.get("LVL") == 0 and _norm(r.get("NAME", "")) == aa.CONSOL_SELECTION_LABEL:
                return r
        return {}

    c, b = selection_row(c_rows), selection_row(b_rows)
    for i in range(4, 0, -1):
        key = f"VAL{i}"
        if c.get(key) is not None or b.get(key) is not None:
            return "C" if c.get(key) is not None else "B"
    return "B"


def _frame(header: dict, rows: list) -> pd.DataFrame:
    """재무제표 하나를 4열 DataFrame으로 만든다. VAL5·VAL6은 쓰지 않는다(REQ-WC-006)."""
    return pd.DataFrame(
        [[_to_float(r.get(f"VAL{i}")) for i in range(1, 5)] for r in rows],
        index=[_norm(r.get("NAME", "")) for r in rows],
        columns=[_period(header[f"VAL{i}"]) for i in range(1, 5)],
        dtype=float,
    )


def _check_alignment(frames: list[pd.DataFrame], code: str, freq: str) -> None:
    """같은 주기 세 재무제표의 정규화 기간이 다르면 RuntimeError(503, REQ-WC-005 (b))."""
    cols = [list(f.columns) for f in frames]
    if any(c != cols[0] for c in cols[1:]):
        raise RuntimeError(f"FnGuide 재무제표 기간 불일치 ({code}, {freq}): {cols}")


def _first_row(frame: pd.DataFrame, label: str) -> int | None:
    """label인 첫 행의 위치. 없으면 None — 부재를 예외가 아니라 경고로 다루는 단위."""
    hits = (frame.index == label).nonzero()[0]
    return int(hits[0]) if len(hits) else None


def _fold(frame: pd.DataFrame, rows: list, code: str, name: str) -> pd.DataFrame:
    """일반 레이아웃 대차대조표: 별칭 원천도 필수 계정도 아닌 LVL2 하위 행을 부모 소계의
    기타* 행에 더하고 그 행은 지운다(사용자 결정 Q-G, REQ-WC-011 (a)·(b))."""
    keep = set(aa.ALIASES) | set(aa.REQUIRED_LABELS)
    values = frame.to_numpy(copy=True)
    labels = list(frame.index)
    folded: set[int] = set()
    for pos, r in enumerate(rows):
        dest = aa.FOLD_PARENT_TO_OTHER.get(r.get("P_AC_CODE"))
        if dest is None or r.get("LVL") != 2 or labels[pos] in keep:
            continue
        dest_pos = _first_row(frame, dest)
        if dest_pos is None:
            logger.warning(
                "%s 접기 건너뜀: %s 표에 '%s' 행 없음 (하위 행 '%s')", code, name, dest, labels[pos]
            )
            continue
        values[dest_pos] += values[pos]
        folded.add(pos)
    kept = [i for i in range(len(labels)) if i not in folded]
    return pd.DataFrame(values[kept], index=[labels[i] for i in kept], columns=frame.columns)


def _ensure_multi_rows(frame: pd.DataFrame) -> pd.DataFrame:
    """이자비용·법인세비용이 두 행 이상이도록 현금흐름표 뒤에 0 행을 덧붙인다(spec D4 (b))."""
    # @MX:WARN: [AUTO] 분석 코드의 암묵 가정에 묶인 구조 보정 — 행 개수가 계산 결과를 바꾼다
    # @MX:REASON: analysis.py의 .loc["이자비용"].iloc[0]은 두 행 이상일 때만 "첫 행"을 뜻한다. 한 행이면 첫 열 값이 네 해에 복사되어 예외 없이 숫자가 틀린다(research.md §R4 P-2)
    for label in aa.MULTI_ROW_LABELS:
        count = int((frame.index == label).sum())
        if 0 < count < aa.MULTI_ROW_MIN:
            pad = pd.DataFrame(
                0.0, index=[label] * (aa.MULTI_ROW_MIN - count), columns=frame.columns
            )
            frame = pd.concat([frame, pad])
    return frame


def _supplement(frame: pd.DataFrame, code: str, name: str) -> pd.DataFrame:
    """명시 목록만 0 행 보충, 그 밖의 필수 계정 부재는 경고만 남긴다(REQ-WC-010)."""
    missing = [label for label in aa.ZERO_ROW_LABELS if label not in frame.index]
    if missing:
        frame = pd.concat([frame, pd.DataFrame(0.0, index=missing, columns=frame.columns)])
    for label in aa.REQUIRED_LABELS:
        if label not in frame.index:
            logger.warning("%s 필수 계정 없음: %s 표에 '%s' 행 없음", code, name, label)
    return frame


def _check_balance(frame: pd.DataFrame, code: str, name: str) -> None:
    """자산·부채 합계와 소비 계정 합의 차이가 0.1억원을 넘으면 열마다 경고(REQ-WC-011 (c))."""
    for total, labels in (
        (aa.ASSET_TOTAL_LABEL, aa.CONSUMED_ASSET_LABELS),
        (aa.LIABILITY_TOTAL_LABEL, aa.CONSUMED_LIABILITY_LABELS),
    ):
        pos = _first_row(frame, total)
        if pos is None:
            logger.warning("%s 정합성 검사 건너뜀: %s 표에 '%s' 행 없음", code, name, total)
            continue
        part = frame[frame.index.isin(labels)]
        part = part[~part.index.duplicated()]  # 표에 없는 계정은 0으로 합산된다
        diff = frame.iloc[pos] - part.sum()
        for col, d in diff.items():
            if abs(d) > _BALANCE_TOLERANCE:
                logger.warning(
                    "%s 정합성 불일치: %s 표 %s 열 %s 차이 %+.2f", code, name, col, total, d
                )


def _yoy_base(header: dict, rows: list, general: bool) -> pd.DataFrame | None:
    """연간 손익 VAL4에 (최근분기) 표지가 있으면 VAL5로 1열 DataFrame을 만든다(spec D5)."""
    if _RECENT_MARK not in (header.get("VAL4") or ""):
        return None
    df = pd.DataFrame(
        {header.get("VAL5") or "전년동기": [_to_float(r.get("VAL5")) for r in rows]},
        index=[_norm(r.get("NAME", "")) for r in rows],
    )
    return df.rename(index=aa.ALIASES) if general else df


# @MX:ANCHOR: [AUTO] 재무제표 리더 — 반환 순서와 DataFrame 성질이 분석 코드의 입력 계약이다
# @MX:REASON: get_fnguide·라이브 테스트가 (account_type, df_fs_ann, df_fs_quar, df_yoy_base_ann) 순서와 4열 YYYY/MM·옛 계정명·행 개수 불변식에 기대며, 바뀌면 fs_analysis·대시보드 섹션이 조용히 None이 된다
# @MX:SPEC: SPEC-FNGUIDE-WCOMP-001
def read_fs(
    code: str,
) -> tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    """FnGuide 신사이트(wcomp) 재무제표 JSON을 읽어 옛 계정명 DataFrame으로 반환한다.

    요청은 연간 손익 C·B(선택 판정) 2회 + 결정된 유형의 나머지 재무제표 5회다.

    Returns:
        (account_type, df_fs_ann, df_fs_quar, df_yoy_base_ann)
        - account_type: 'IFRS(연결)'(C) 또는 'IFRS(별도)'(B)
        - df_fs_ann / df_fs_quar: 4열(YYYY/MM), 손익 → 대차 → 현금흐름 순으로 이어 붙임
        - df_yoy_base_ann: 연간 최근 열이 누적 YTD일 때 전년동기 1열, 아니면 None

    Raises:
        ValueError: 코드 형식 오류, 비정상 본문(HTML·빈 data·기간 부족) — 라우터 404
        ConnectionError: 전송 실패·2xx 밖 상태 — 라우터 503
        RuntimeError: 세 재무제표의 기간 불일치 — 라우터 503
    """
    if not isinstance(code, str) or not _CODE_RE.fullmatch(code):
        raise ValueError(f"종목 코드 형식 오류(6자리 숫자): {code!r}")

    # 1) 선택 판정: 연간 손익 C·B. 결정되지 않은 유형의 실패는 "값 없음"으로 본다.
    selection: dict[str, tuple[dict, list]] = {}
    errors: dict[str, ValueError] = {}
    for consol in ("C", "B"):
        try:
            resp = _fetch("getFinIncome", code, "Y", consol)
            selection[consol] = _parse(resp, code, "getFinIncome")
        except ValueError as e:
            errors[consol] = e
    if not selection:
        raise errors["C"]
    consol = _choose_consol(
        selection["C"][1] if "C" in selection else None,
        selection["B"][1] if "B" in selection else None,
    )
    if consol not in selection:
        raise errors[consol]

    # 2) 결정된 유형으로 나머지 다섯 건. 응답마다 검사한 뒤에 기간을 맞춰 본다.
    parsed = {("getFinIncome", "Y"): selection[consol]}
    for endpoint in _ENDPOINTS:
        for freq in ("Y", "Q"):
            if (endpoint, freq) not in parsed:
                resp = _fetch(endpoint, code, freq, consol)
                parsed[(endpoint, freq)] = _parse(resp, code, endpoint)

    statements = {}
    for freq in ("Y", "Q"):
        statements[freq] = {ep: _frame(*parsed[(ep, freq)]) for ep in _ENDPOINTS}
        _check_alignment(list(statements[freq].values()), code, freq)
    last_ann = statements["Y"]["getFinIncome"].columns[3]
    last_quar = statements["Q"]["getFinIncome"].columns[3]
    if last_ann != last_quar:
        logger.warning(
            "%s 연간·분기 네 번째 기간 불일치: 연간 %s, 분기 %s", code, last_ann, last_quar
        )

    inc_header, inc_rows = parsed[("getFinIncome", "Y")]
    general = any(
        r.get("LVL") == 0 and _norm(r.get("NAME", "")) == aa.GENERAL_LAYOUT_MARKER
        for r in inc_rows
    )

    # 3) 행 구조: 개명 → (일반) 접기 → 이어 붙이기 → 다중 행 → (일반) 별칭·0 행·가드
    result = {}
    for freq, name in (("Y", "연간"), ("Q", "분기")):
        st = statements[freq]
        st["getFinCashFlow"] = st["getFinCashFlow"].rename(index=aa.CASHFLOW_RENAMES)
        if general:
            st["getFinBalance"] = _fold(
                st["getFinBalance"], parsed[("getFinBalance", freq)][1], code, name
            )
        df = _ensure_multi_rows(pd.concat([st[ep] for ep in _STATEMENT_ORDER]))
        if general:
            df = _supplement(df.rename(index=aa.ALIASES), code, name)
            _check_balance(df, code, name)
        result[freq] = df

    account_type = "IFRS(연결)" if consol == "C" else "IFRS(별도)"
    return account_type, result["Y"], result["Q"], _yoy_base(inc_header, inc_rows, general)


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
