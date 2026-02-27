"""Characterization tests for my_chart/registry.py.

Captures CURRENT behavior of registry functions. External xlsx file loading
is mocked via the mock_sectormap fixture in conftest.py.
"""

from __future__ import annotations

import pandas as pd
import pytest


class TestGetStockRegistry:
    """Characterizes get_stock_registry() return contract."""

    def test_returns_dataframe(self, mock_sectormap):
        from my_chart.registry import get_stock_registry

        result = get_stock_registry()
        assert isinstance(result, pd.DataFrame)

    def test_has_code_column(self, mock_sectormap):
        from my_chart.registry import get_stock_registry

        result = get_stock_registry()
        assert "Code" in result.columns

    def test_has_name_column(self, mock_sectormap):
        from my_chart.registry import get_stock_registry

        result = get_stock_registry()
        assert "Name" in result.columns

    def test_has_market_column(self, mock_sectormap):
        from my_chart.registry import get_stock_registry

        result = get_stock_registry()
        assert "Market" in result.columns

    def test_has_exactly_three_columns(self, mock_sectormap):
        from my_chart.registry import get_stock_registry

        result = get_stock_registry()
        assert list(result.columns) == ["Code", "Name", "Market"]

    def test_code_is_string_type(self, mock_sectormap):
        from my_chart.registry import get_stock_registry

        result = get_stock_registry()
        # pandas 2.x may return StringDtype; either way it should be string-compatible
        assert pd.api.types.is_string_dtype(result["Code"])

    def test_code_is_zero_padded_6_digits(self, mock_sectormap):
        from my_chart.registry import get_stock_registry

        result = get_stock_registry()
        for code in result["Code"]:
            assert len(code) == 6, f"Code '{code}' is not 6 digits"
            assert code.isdigit(), f"Code '{code}' contains non-digit characters"

    def test_is_cached_on_second_call(self, mock_sectormap):
        """Verifies lazy-loading singleton caches the result."""
        from my_chart.registry import get_stock_registry

        first = get_stock_registry()
        second = get_stock_registry()
        assert first is second


class TestGetSectorRegistry:
    """Characterizes get_sector_registry() return contract."""

    def test_returns_dataframe(self, mock_sectormap):
        from my_chart.registry import get_sector_registry

        result = get_sector_registry()
        assert isinstance(result, pd.DataFrame)

    def test_has_sector_major_column(self, mock_sectormap):
        from my_chart.registry import get_sector_registry

        result = get_sector_registry()
        assert "산업명(대)" in result.columns

    def test_has_sector_minor_column(self, mock_sectormap):
        from my_chart.registry import get_sector_registry

        result = get_sector_registry()
        assert "산업명(중)" in result.columns

    def test_has_product_column(self, mock_sectormap):
        from my_chart.registry import get_sector_registry

        result = get_sector_registry()
        assert "주요제품" in result.columns

    def test_sorted_by_sector_major_ascending(self, mock_sectormap):
        from my_chart.registry import get_sector_registry

        result = get_sector_registry()
        sector_values = result["산업명(대)"].tolist()
        assert sector_values == sorted(sector_values)

    def test_is_cached_on_second_call(self, mock_sectormap):
        from my_chart.registry import get_sector_registry

        first = get_sector_registry()
        second = get_sector_registry()
        assert first is second


class TestCodeLookup:
    """Characterizes _code() sentinel behavior."""

    def test_returns_code_for_known_name(self, mock_sectormap):
        from my_chart.registry import _code

        result = _code("삼성전자")
        assert result == "005930"

    def test_returns_nocode_for_unknown_name(self, mock_sectormap):
        from my_chart.registry import _code

        result = _code("존재하지않는주식이름XYZ")
        assert result == "NoCode"

    def test_returns_nocode_for_empty_string(self, mock_sectormap):
        from my_chart.registry import _code

        result = _code("")
        assert result == "NoCode"


class TestNameLookup:
    """Characterizes _name() sentinel behavior."""

    def test_returns_name_for_known_code(self, mock_sectormap):
        from my_chart.registry import _name

        result = _name("005930")
        assert result == "삼성전자"

    def test_returns_nonname_for_unknown_code(self, mock_sectormap):
        from my_chart.registry import _name

        result = _name("999999")
        assert result == "NonName"

    def test_returns_nonname_for_empty_string(self, mock_sectormap):
        from my_chart.registry import _name

        result = _name("")
        assert result == "NonName"


class TestSectorLookup:
    """Characterizes _sector() return contract."""

    def test_returns_tuple_of_two(self, mock_sectormap):
        from my_chart.registry import _sector

        result = _sector("삼성전자")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_dict_and_string(self, mock_sectormap):
        from my_chart.registry import _sector

        data_dict, summary = _sector("삼성전자")
        assert isinstance(data_dict, dict)
        assert isinstance(summary, str)

    def test_summary_contains_sector_hierarchy(self, mock_sectormap):
        from my_chart.registry import _sector

        _, summary = _sector("삼성전자")
        assert "전기전자" in summary
        assert "반도체" in summary

    def test_unknown_stock_returns_nodata_sentinel(self, mock_sectormap):
        from my_chart.registry import _sector

        _, summary = _sector("존재하지않는주식XYZ")
        assert summary == "NoData"

    def test_unknown_stock_dict_has_none_values(self, mock_sectormap):
        from my_chart.registry import _sector

        data_dict, _ = _sector("존재하지않는주식XYZ")
        assert data_dict["Code"] == "None"
        assert data_dict["Name"] == "None"
        assert data_dict["Market"] == "None"
