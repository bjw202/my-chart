import pytest
import pandas as pd
from backend.services.naver_theme.parser import (
    to_num,
    normalize_money,
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
def test_to_num_invalid():
    """to_num() returns 0 for invalid input."""
    assert to_num("invalid") == 0
    assert to_num("") == 0
    assert to_num("NaN") == 0


@pytest.mark.unit
def test_normalize_money_won():
    """normalize_money() handles Korean currency units."""
    assert normalize_money("1000억") == 100_000_000_000
    assert normalize_money("1조") == 1_000_000_000_000
    assert normalize_money("100만") == 1_000_000


@pytest.mark.unit
def test_normalize_money_numeric():
    """normalize_money() handles plain numbers."""
    assert normalize_money("1000") == 1000
    assert normalize_money("1000.5") == 1000.5


@pytest.mark.unit
def test_parse_theme_list_empty_html():
    """parse_theme_list() returns empty DataFrame for invalid HTML."""
    html = "<html><body></body></html>"
    df = parse_theme_list(html)
    assert isinstance(df, pd.DataFrame)
    # Should handle empty gracefully


@pytest.mark.unit
def test_parse_theme_detail_empty_html():
    """parse_theme_detail() returns empty list for invalid HTML."""
    from backend.services.naver_theme.parser import parse_theme_detail
    html = "<html><body></body></html>"
    result = parse_theme_detail(html, 1)
    assert isinstance(result, list)
    assert len(result) == 0
