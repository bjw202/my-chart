"""naver_theme.parser 단위 테스트 (tests/services/naver_theme/ 버전)."""

from __future__ import annotations

import math
import sys
import types

import pytest

# pykrx 스텁
for _m in ("pykrx", "pykrx.stock"):
    if _m not in sys.modules:
        sys.modules[_m] = types.ModuleType(_m)

from backend.services.naver_theme.parser import (
    to_num,
    _parse_korean_number,
    parse_theme_list,
    parse_theme_detail,
)


@pytest.mark.unit
def test_to_num_integer():
    """to_num() converts integer strings."""
    assert to_num("1234") == 1234
    assert to_num("0") == 0


@pytest.mark.unit
def test_to_num_float():
    """to_num() converts float strings."""
    assert to_num("12.34") == 12.34
    assert to_num("0.5") == 0.5


@pytest.mark.unit
def test_to_num_with_commas():
    """to_num() removes commas before converting."""
    assert to_num("1,234,567") == 1234567
    assert to_num("1,234.56") == 1234.56


@pytest.mark.unit
def test_to_num_sentinel_returns_nan():
    """to_num() returns math.nan for '-', 'N/A', empty (REQ-NT-004)."""
    assert math.isnan(to_num("-"))
    assert math.isnan(to_num("N/A"))
    assert math.isnan(to_num(""))
    assert math.isnan(to_num("invalid"))


@pytest.mark.unit
def test_parse_korean_number_eok():
    """_parse_korean_number() handles 억 unit."""
    assert _parse_korean_number("1000억") == pytest.approx(100_000_000_000)


@pytest.mark.unit
def test_parse_korean_number_jo():
    """_parse_korean_number() handles 조 unit."""
    assert _parse_korean_number("1조") == pytest.approx(1_000_000_000_000)


@pytest.mark.unit
def test_parse_korean_number_man():
    """_parse_korean_number() handles 만 unit."""
    assert _parse_korean_number("100만") == pytest.approx(1_000_000)


@pytest.mark.unit
def test_parse_korean_number_plain_numeric():
    """_parse_korean_number() handles plain numbers."""
    assert _parse_korean_number("1000") == pytest.approx(1000)
    assert _parse_korean_number("1000.5") == pytest.approx(1000.5)


@pytest.mark.unit
def test_parse_theme_list_empty_html():
    """parse_theme_list() returns dict with empty themes list for invalid HTML."""
    html = "<html><body></body></html>"
    result = parse_theme_list(html)
    assert isinstance(result, dict)
    assert "themes" in result
    assert isinstance(result["themes"], list)


@pytest.mark.unit
def test_parse_theme_detail_empty_html():
    """parse_theme_detail() returns empty list for invalid HTML."""
    html = "<html><body></body></html>"
    result = parse_theme_detail(html, 1, "테스트테마")
    assert isinstance(result, list)
    assert len(result) == 0
