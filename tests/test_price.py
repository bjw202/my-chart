"""Characterization tests for my_chart/price.py.

Captures CURRENT behavior:
- fix_zero_ohlc() replaces zero Open/High/Low with Close value
- price_naver() returns DataFrame with OHLCV columns and DatetimeIndex
- price_naver() raises ValueError for unknown stock name
- price_naver() handles "KOSPI"/"KOSDAQ" as special market codes
"""

from __future__ import annotations

import pandas as pd
import pytest


class TestFixZeroOhlc:
    """Characterizes fix_zero_ohlc() in-place mutation behavior."""

    def test_zero_open_replaced_with_close(self):
        from my_chart.price import fix_zero_ohlc

        df = pd.DataFrame(
            {"Open": [0.0, 100.0], "High": [105.0, 105.0], "Low": [90.0, 90.0], "Close": [95.0, 95.0]}
        )
        result = fix_zero_ohlc(df)
        assert result.loc[0, "Open"] == 95.0

    def test_nonzero_open_unchanged(self):
        from my_chart.price import fix_zero_ohlc

        df = pd.DataFrame(
            {"Open": [0.0, 100.0], "High": [105.0, 105.0], "Low": [90.0, 90.0], "Close": [95.0, 95.0]}
        )
        result = fix_zero_ohlc(df)
        assert result.loc[1, "Open"] == 100.0

    def test_zero_high_replaced_with_close(self):
        from my_chart.price import fix_zero_ohlc

        df = pd.DataFrame(
            {"Open": [100.0], "High": [0.0], "Low": [90.0], "Close": [95.0]}
        )
        result = fix_zero_ohlc(df)
        assert result.loc[0, "High"] == 95.0

    def test_zero_low_replaced_with_close(self):
        from my_chart.price import fix_zero_ohlc

        df = pd.DataFrame(
            {"Open": [100.0], "High": [105.0], "Low": [0.0], "Close": [95.0]}
        )
        result = fix_zero_ohlc(df)
        assert result.loc[0, "Low"] == 95.0

    def test_returns_same_dataframe_object(self):
        """fix_zero_ohlc mutates in-place and returns the same object."""
        from my_chart.price import fix_zero_ohlc

        df = pd.DataFrame(
            {"Open": [0.0], "High": [0.0], "Low": [0.0], "Close": [95.0]}
        )
        result = fix_zero_ohlc(df)
        assert result is df

    def test_all_zeros_replaced(self):
        from my_chart.price import fix_zero_ohlc

        df = pd.DataFrame(
            {"Open": [0.0], "High": [0.0], "Low": [0.0], "Close": [95.0]}
        )
        result = fix_zero_ohlc(df)
        assert result.loc[0, "Open"] == 95.0
        assert result.loc[0, "High"] == 95.0
        assert result.loc[0, "Low"] == 95.0

    def test_close_column_never_modified(self):
        from my_chart.price import fix_zero_ohlc

        df = pd.DataFrame(
            {"Open": [0.0], "High": [0.0], "Low": [0.0], "Close": [95.0]}
        )
        result = fix_zero_ohlc(df)
        assert result.loc[0, "Close"] == 95.0


class TestPriceNaverReturnContract:
    """Characterizes price_naver() return format with mocked HTTP."""

    def test_returns_dataframe(self, mock_naver_response):
        from my_chart.price import price_naver

        result = price_naver("KOSPI", "20240101")
        assert isinstance(result, pd.DataFrame)

    def test_has_open_column(self, mock_naver_response):
        from my_chart.price import price_naver

        result = price_naver("KOSPI", "20240101")
        assert "Open" in result.columns

    def test_has_high_column(self, mock_naver_response):
        from my_chart.price import price_naver

        result = price_naver("KOSPI", "20240101")
        assert "High" in result.columns

    def test_has_low_column(self, mock_naver_response):
        from my_chart.price import price_naver

        result = price_naver("KOSPI", "20240101")
        assert "Low" in result.columns

    def test_has_close_column(self, mock_naver_response):
        from my_chart.price import price_naver

        result = price_naver("KOSPI", "20240101")
        assert "Close" in result.columns

    def test_has_volume_column(self, mock_naver_response):
        from my_chart.price import price_naver

        result = price_naver("KOSPI", "20240101")
        assert "Volume" in result.columns

    def test_index_is_datetimeindex(self, mock_naver_response):
        from my_chart.price import price_naver

        result = price_naver("KOSPI", "20240101")
        assert isinstance(result.index, pd.DatetimeIndex)

    def test_index_name_is_date(self, mock_naver_response):
        from my_chart.price import price_naver

        result = price_naver("KOSPI", "20240101")
        assert result.index.name == "Date"

    def test_rows_filtered_by_start_date(self, mock_naver_response):
        """Rows before start date are excluded from the result."""
        from my_chart.price import price_naver

        result = price_naver("KOSPI", "20240103")
        # Mock data has 20240102 and 20240103; only 20240103 should remain
        assert len(result) == 1
        assert result.index[0] == pd.Timestamp("2024-01-03")


class TestPriceNaverErrorHandling:
    """Characterizes price_naver() error handling."""

    def test_raises_value_error_for_unknown_stock(self, mock_sectormap):
        """price_naver raises ValueError when _code returns 'NoCode'."""
        from my_chart.price import price_naver

        with pytest.raises(ValueError, match="Unknown stock name"):
            price_naver("존재하지않는주식XYZ999", "20240101")

    def test_kospi_does_not_raise(self, mock_naver_response):
        """'KOSPI' is a special market code that bypasses registry lookup."""
        from my_chart.price import price_naver

        # Should not raise even without mock_sectormap fixture
        result = price_naver("KOSPI", "20240101")
        assert isinstance(result, pd.DataFrame)

    def test_kosdaq_does_not_raise(self, mock_naver_response):
        """'KOSDAQ' is a special market code that bypasses registry lookup."""
        from my_chart.price import price_naver

        result = price_naver("KOSDAQ", "20240101")
        assert isinstance(result, pd.DataFrame)

    def test_empty_api_response_returns_empty_dataframe(self, monkeypatch):
        """When API returns zero rows, returns empty DataFrame."""
        from unittest.mock import MagicMock

        from my_chart.price import price_naver

        # Mock response with header row only (no data rows)
        csv_data = '"Date","Open","High","Low","Close","Volume"\n'.encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.content = csv_data
        mock_resp.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        monkeypatch.setattr("my_chart.price._get_session", lambda: mock_session)

        result = price_naver("KOSPI", "20240101")
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestPriceNaverUrlConstruction:
    """Characterizes that price_naver builds URL with correct parameters."""

    def test_url_contains_symbol(self, mock_naver_response):
        from my_chart.price import price_naver

        price_naver("KOSPI", "20240101")
        call_args = mock_naver_response.get.call_args
        assert "KOSPI" in call_args[0][0]

    def test_url_contains_start_time(self, mock_naver_response):
        from my_chart.price import price_naver

        price_naver("KOSPI", "20240101")
        call_args = mock_naver_response.get.call_args
        assert "20240101" in call_args[0][0]

    def test_uses_day_timeframe_by_default(self, mock_naver_response):
        from my_chart.price import price_naver

        price_naver("KOSPI", "20240101")
        call_args = mock_naver_response.get.call_args
        assert "timeframe=day" in call_args[0][0]

    def test_custom_freq_used_in_url(self, mock_naver_response):
        from my_chart.price import price_naver

        price_naver("KOSPI", "20240101", freq="week")
        call_args = mock_naver_response.get.call_args
        assert "timeframe=week" in call_args[0][0]
