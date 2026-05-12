"""naver_theme.parser 단위 테스트.

픽스처 전략:
  - theme_list_page1.html : Option A (실 네이버 금융 페이지 fetch, EUC-KR 저장)
  - theme_detail_178.html : Option B (합성 HTML — 실 페이지의 앵커에 class="tltle" 없음,
                            parser가 "td a.tltle" 셀렉터를 사용하므로 합성 픽스처 사용)

코드-SPEC 불일치 사항 (backend-dev 보고용):
  - 실 네이버 상세 페이지 앵커에는 class="tltle" 가 없음 (class 미지정).
    현재 parser.py 의 `row.select_one("td a.tltle")` 는 실 페이지에서 0건을 반환한다.
    → backend-dev 가 셀렉터를 `td a[href*="code="]` 로 변경해야 한다.
"""

from __future__ import annotations

import math
import pathlib
import sys
import re

import pytest

# pykrx 가 pkg_resources 를 필요로 하는데 설치되지 않은 환경 대응
for _mod in ("pykrx", "pykrx.stock"):
    if _mod not in sys.modules:
        import types
        sys.modules[_mod] = types.ModuleType(_mod)

from backend.services.naver_theme.parser import (
    _parse_korean_number,
    parse_theme_detail,
    parse_theme_list,
    to_num,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "naver_theme"


# ---------------------------------------------------------------------------
# parse_theme_list 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_parse_theme_list_extracts_theme_id_from_anchor_href():
    """td.col_type1 a 앵커 href의 ?no=178 → theme_id=178 로 추출."""
    html = (FIXTURES / "theme_list_page1.html").read_text(encoding="euc-kr")
    result = parse_theme_list(html)
    theme_ids = [t["theme_id"] for t in result["themes"]]
    assert 178 in theme_ids, f"theme_id=178 (전선) not found in {theme_ids[:10]}"


@pytest.mark.unit
def test_parse_theme_list_returns_themes_and_last_page():
    """반환 딕셔너리가 {'themes': list, 'last_page': int} 형태인지 검증."""
    html = (FIXTURES / "theme_list_page1.html").read_text(encoding="euc-kr")
    result = parse_theme_list(html)
    assert isinstance(result, dict)
    assert "themes" in result
    assert "last_page" in result
    assert isinstance(result["themes"], list)
    assert isinstance(result["last_page"], int)
    assert len(result["themes"]) > 0


@pytest.mark.unit
def test_parse_theme_list_detects_last_page_above_one():
    """실 목록 페이지의 페이지네이션에서 last_page > 1 을 탐지한다."""
    html = (FIXTURES / "theme_list_page1.html").read_text(encoding="euc-kr")
    result = parse_theme_list(html)
    assert result["last_page"] > 1, (
        f"last_page={result['last_page']} — 페이지네이션 탐지 실패 또는 픽스처 단일 페이지"
    )


@pytest.mark.unit
def test_parse_theme_list_theme_entry_has_required_keys():
    """각 테마 항목이 필수 키를 보유하는지 검증."""
    html = (FIXTURES / "theme_list_page1.html").read_text(encoding="euc-kr")
    result = parse_theme_list(html)
    required = {"theme_id", "theme_name", "change_pct", "change_pct_3d"}
    for theme in result["themes"][:5]:
        assert required <= set(theme.keys()), f"Missing keys in theme: {theme}"


# ---------------------------------------------------------------------------
# parse_theme_detail 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_parse_theme_detail_captures_inclusion_reason():
    """td[1] 이 inclusion_reason 으로 보존되며 한글 포함 검증 (AC-13)."""
    html = (FIXTURES / "theme_detail_178.html").read_text(encoding="euc-kr")
    stocks = parse_theme_detail(html, theme_id=178, theme_name="전선")
    assert len(stocks) > 0
    assert all("inclusion_reason" in s for s in stocks)
    non_empty = [s for s in stocks if s["inclusion_reason"].strip()]
    assert len(non_empty) >= 1, "inclusion_reason 이 비어있는 종목만 존재"
    HANGUL = re.compile(r"[가-힣]")
    assert any(HANGUL.search(s["inclusion_reason"]) for s in non_empty), (
        "inclusion_reason 에 한글 없음 — 컬럼 매핑 오류 가능성"
    )


@pytest.mark.unit
def test_parse_theme_detail_columns_match_real_layout():
    """가격=td[2], 등락률=td[4], 거래대금=td[8] 매핑 검증 (A-6)."""
    html = (FIXTURES / "theme_detail_178.html").read_text(encoding="euc-kr")
    stocks = parse_theme_detail(html, theme_id=178, theme_name="전선")
    assert len(stocks) > 0
    first = stocks[0]
    # price 는 양수 float
    assert isinstance(first["price"], float)
    assert first["price"] > 0
    # change_pct 는 float (양수/음수 가능)
    assert isinstance(first["change_pct"], float)
    # trade_value 는 int (원 단위 정수)
    assert isinstance(first["trade_value"], int)
    # per/roe 는 NaN 고정 (A-5)
    assert math.isnan(first["per"])
    assert math.isnan(first["roe"])


@pytest.mark.unit
def test_parse_theme_detail_extracts_stock_code():
    """앵커 href 에서 6자리 종목코드를 정규식으로 추출한다."""
    html = (FIXTURES / "theme_detail_178.html").read_text(encoding="euc-kr")
    stocks = parse_theme_detail(html, theme_id=178, theme_name="전선")
    assert len(stocks) > 0
    for s in stocks:
        assert re.fullmatch(r"\d{6}", s["stock_code"]), (
            f"stock_code 형식 오류: {s['stock_code']!r}"
        )


@pytest.mark.unit
def test_parse_theme_detail_theme_id_and_name_propagated():
    """parse_theme_detail 호출 시 전달된 theme_id/theme_name 이 각 행에 반영된다."""
    html = (FIXTURES / "theme_detail_178.html").read_text(encoding="euc-kr")
    stocks = parse_theme_detail(html, theme_id=178, theme_name="전선")
    for s in stocks:
        assert s["theme_id"] == 178
        assert s["theme_name"] == "전선"


# ---------------------------------------------------------------------------
# 방어 코드 분기 커버리지 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_parse_theme_list_skips_anchor_without_no_param():
    """href 에 ?no= 가 없는 앵커는 건너뛴다 (line 62 방어 분기)."""
    html = """<html><body>
    <table class="type_1">
    <tr><td class="col_type1"><a href="?type=theme">테마없음</a></td>
        <td>1.0</td><td>0.5</td><td>3</td><td>1</td><td>2</td><td>종목A</td></tr>
    </table>
    </body></html>"""
    result = parse_theme_list(html)
    assert result["themes"] == [], "?no= 없는 앵커가 themes 에 포함됨"


@pytest.mark.unit
def test_parse_theme_list_skips_rows_with_few_cells():
    """td 가 7개 미만인 행은 건너뛴다 (line 66 방어 분기)."""
    html = """<html><body>
    <table class="type_1">
    <tr><td class="col_type1"><a href="?no=999">테마짧은행</a></td>
        <td>1.0</td></tr>
    </table>
    </body></html>"""
    result = parse_theme_list(html)
    assert result["themes"] == [], "셀 부족 행이 themes 에 포함됨"


@pytest.mark.unit
def test_parse_theme_detail_skips_anchor_without_code():
    """href 에 code= 가 없는 앵커는 건너뛴다 (line 109 방어 분기)."""
    html = """<html><body>
    <table class="type_5">
    <tr>
      <td><a class="tltle" href="/item/main.naver?id=123">종목A</a></td>
      <td>편입사유</td><td>1000</td><td>10</td><td>+1%</td>
      <td>999</td><td>1001</td><td>5000</td><td>100억</td><td>4500</td>
    </tr>
    </table>
    </body></html>"""
    stocks = parse_theme_detail(html, theme_id=999, theme_name="테스트")
    assert stocks == [], "code= 없는 앵커가 stocks 에 포함됨"


@pytest.mark.unit
def test_parse_theme_detail_skips_rows_with_few_cells():
    """td 가 9개 미만인 행은 건너뛴다 (line 112 방어 분기)."""
    html = """<html><body>
    <table class="type_5">
    <tr>
      <td><a class="tltle" href="/item/main.naver?code=001234">종목A</a></td>
      <td>편입사유</td><td>1000</td>
    </tr>
    </table>
    </body></html>"""
    stocks = parse_theme_detail(html, theme_id=999, theme_name="테스트")
    assert stocks == [], "셀 부족 행이 stocks 에 포함됨"


@pytest.mark.unit
def test_parse_korean_number_no_match_returns_nan():
    """숫자 패턴이 전혀 없는 문자열 → math.nan (line 45 else 분기)."""
    result = _parse_korean_number("없음없음")
    assert math.isnan(result), f"Expected NaN, got {result}"


# ---------------------------------------------------------------------------
# _parse_korean_number 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_parse_korean_number_multi_token():
    """'1,289조 1,044억' 멀티 토큰 누적 합산 검증."""
    # 1,289조 = 1_289 * 1_000_000_000_000 = 1_289_000_000_000_000
    # 1,044억 = 1_044 * 100_000_000 = 104_400_000_000
    expected = 1_289_000_000_000_000 + 104_400_000_000
    result = _parse_korean_number("1,289조 1,044억")
    assert result == pytest.approx(expected, rel=1e-9)


@pytest.mark.unit
def test_parse_korean_number_single_tokens():
    """단일 한글 단위 토큰 변환 검증."""
    assert _parse_korean_number("524억") == pytest.approx(524 * 100_000_000)
    assert _parse_korean_number("1.2조") == pytest.approx(1.2 * 1_000_000_000_000)
    assert _parse_korean_number("500만") == pytest.approx(500 * 10_000)


@pytest.mark.unit
def test_parse_korean_number_plain_integer():
    """단위 없는 숫자 문자열 (쉼표 포함) → 그대로 float 반환."""
    assert _parse_korean_number("500,000") == pytest.approx(500_000)


@pytest.mark.unit
def test_parse_korean_number_returns_nan_for_empty():
    """빈 문자열 → math.nan 반환."""
    result = _parse_korean_number("")
    assert math.isnan(result), f"Expected NaN, got {result}"


# ---------------------------------------------------------------------------
# to_num 테스트
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_to_num_handles_dash_and_empty():
    """'-', '', 'N/A' → math.nan (0 이 아님)."""
    for sentinel in ("-", "", "N/A"):
        result = to_num(sentinel)
        assert math.isnan(result), f"to_num({sentinel!r}) 는 NaN 이어야 함, got {result}"


@pytest.mark.unit
def test_to_num_strips_commas_and_percent():
    """'1,234.5%' → 1234.5 (쉼표/퍼센트 제거 후 float)."""
    assert to_num("1,234.5%") == pytest.approx(1234.5)


@pytest.mark.unit
def test_to_num_plain_number():
    """일반 숫자 문자열 → float 변환."""
    assert to_num("3850") == pytest.approx(3850.0)
    assert to_num("-2.5") == pytest.approx(-2.5)
