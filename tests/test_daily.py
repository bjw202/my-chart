"""Characterization tests for my_chart/db/daily.py.

Captures CURRENT behavior:
- _DAILY_COLS tuple length and column names
- _fetch_daily_stock() return type and empty-data behavior
- Exception handling returns (name, []) tuple
"""

from __future__ import annotations

import pandas as pd


class TestDailyCols:
    """Characterizes _DAILY_COLS constant."""

    def test_daily_cols_is_tuple(self):
        from my_chart.db.daily import _DAILY_COLS

        assert isinstance(_DAILY_COLS, tuple)

    def test_daily_cols_has_27_elements(self):
        # RS_Line 컬럼 추가: SMA100(REQ-011) + RS_Line(SPEC-RS-LINE-001)
        from my_chart.db.daily import _DAILY_COLS

        assert len(_DAILY_COLS) == 27

    def test_daily_cols_first_is_name(self):
        from my_chart.db.daily import _DAILY_COLS

        assert _DAILY_COLS[0] == "Name"

    def test_daily_cols_second_is_date(self):
        from my_chart.db.daily import _DAILY_COLS

        assert _DAILY_COLS[1] == "Date"

    def test_daily_cols_contains_ohlcv(self):
        from my_chart.db.daily import _DAILY_COLS

        for col in ("Open", "High", "Low", "Close", "Volume"):
            assert col in _DAILY_COLS, f"Expected '{col}' in _DAILY_COLS"

    def test_daily_cols_contains_technical_indicators(self):
        from my_chart.db.daily import _DAILY_COLS

        expected_indicators = ("EMA10", "EMA20", "SMA21", "SMA50", "EMA65", "SMA100", "SMA200")
        for ind in expected_indicators:
            assert ind in _DAILY_COLS, f"Expected '{ind}' in _DAILY_COLS"

    def test_daily_cols_unique(self):
        from my_chart.db.daily import _DAILY_COLS

        assert len(_DAILY_COLS) == len(set(_DAILY_COLS))


class TestFetchDailyStock:
    """Characterizes _fetch_daily_stock() return contract."""

    def test_returns_tuple(self, monkeypatch):
        from my_chart.db.daily import _fetch_daily_stock

        monkeypatch.setattr(
            "my_chart.db.daily.price_naver",
            lambda *args, **kwargs: pd.DataFrame(),
        )
        result = _fetch_daily_stock("테스트주식", "20240101")
        assert isinstance(result, tuple)

    def test_returns_two_element_tuple(self, monkeypatch):
        from my_chart.db.daily import _fetch_daily_stock

        monkeypatch.setattr(
            "my_chart.db.daily.price_naver",
            lambda *args, **kwargs: pd.DataFrame(),
        )
        result = _fetch_daily_stock("테스트주식", "20240101")
        assert len(result) == 2

    def test_first_element_is_company_name(self, monkeypatch):
        from my_chart.db.daily import _fetch_daily_stock

        monkeypatch.setattr(
            "my_chart.db.daily.price_naver",
            lambda *args, **kwargs: pd.DataFrame(),
        )
        company, _ = _fetch_daily_stock("삼성전자", "20240101")
        assert company == "삼성전자"

    def test_empty_dataframe_yields_empty_rows(self, monkeypatch):
        """When price_naver returns empty DataFrame, rows list is empty."""
        from my_chart.db.daily import _fetch_daily_stock

        monkeypatch.setattr(
            "my_chart.db.daily.price_naver",
            lambda *args, **kwargs: pd.DataFrame(),
        )
        _, rows = _fetch_daily_stock("테스트주식", "20240101")
        assert rows == []

    def test_none_result_from_price_naver_yields_empty_rows(self, monkeypatch):
        """When price_naver returns None, rows list is empty."""
        from my_chart.db.daily import _fetch_daily_stock

        monkeypatch.setattr(
            "my_chart.db.daily.price_naver",
            lambda *args, **kwargs: None,
        )
        company, rows = _fetch_daily_stock("테스트주식", "20240101")
        assert company == "테스트주식"
        assert rows == []

    def test_exception_from_price_naver_yields_empty_rows(self, monkeypatch):
        """When price_naver raises any exception, returns (name, []) without re-raising."""
        from my_chart.db.daily import _fetch_daily_stock

        def raise_error(*args, **kwargs):
            raise RuntimeError("Simulated API failure")

        monkeypatch.setattr("my_chart.db.daily.price_naver", raise_error)
        company, rows = _fetch_daily_stock("에러주식", "20240101")
        assert company == "에러주식"
        assert rows == []

    def test_rows_are_tuples_on_valid_data(self, monkeypatch):
        """Each row in the returned list is a tuple (for executemany compatibility)."""
        from my_chart.db.daily import _fetch_daily_stock

        # Build minimal OHLCV DataFrame matching price_naver output
        dates = pd.date_range("2024-01-02", periods=5, freq="B")
        df = pd.DataFrame(
            {
                "Open": [100.0] * 5,
                "High": [105.0] * 5,
                "Low": [98.0] * 5,
                "Close": [102.0] * 5,
                "Volume": [1_000_000.0] * 5,
            },
            index=dates,
        )
        df.index.name = "Date"

        monkeypatch.setattr(
            "my_chart.db.daily.price_naver",
            lambda *args, **kwargs: df,
        )
        # Also patch time.sleep to avoid actual delays
        monkeypatch.setattr("my_chart.db.daily.time.sleep", lambda _: None)

        _, rows = _fetch_daily_stock("테스트주식", "20240101")
        assert len(rows) == 5
        for row in rows:
            assert isinstance(row, tuple)

    def test_row_tuple_length_matches_daily_cols(self, monkeypatch):
        """Each row tuple has exactly len(_DAILY_COLS) elements."""
        from my_chart.db.daily import _DAILY_COLS, _fetch_daily_stock

        dates = pd.date_range("2024-01-02", periods=3, freq="B")
        df = pd.DataFrame(
            {
                "Open": [100.0] * 3,
                "High": [105.0] * 3,
                "Low": [98.0] * 3,
                "Close": [102.0] * 3,
                "Volume": [1_000_000.0] * 3,
            },
            index=dates,
        )
        df.index.name = "Date"

        monkeypatch.setattr(
            "my_chart.db.daily.price_naver",
            lambda *args, **kwargs: df,
        )
        monkeypatch.setattr("my_chart.db.daily.time.sleep", lambda _: None)

        _, rows = _fetch_daily_stock("테스트주식", "20240101")
        for row in rows:
            assert len(row) == len(_DAILY_COLS)

    def test_row_first_element_is_company_name(self, monkeypatch):
        """First element of each row tuple is the company name string."""
        from my_chart.db.daily import _fetch_daily_stock

        dates = pd.date_range("2024-01-02", periods=2, freq="B")
        df = pd.DataFrame(
            {
                "Open": [100.0] * 2,
                "High": [105.0] * 2,
                "Low": [98.0] * 2,
                "Close": [102.0] * 2,
                "Volume": [1_000_000.0] * 2,
            },
            index=dates,
        )
        df.index.name = "Date"

        monkeypatch.setattr(
            "my_chart.db.daily.price_naver",
            lambda *args, **kwargs: df,
        )
        monkeypatch.setattr("my_chart.db.daily.time.sleep", lambda _: None)

        _, rows = _fetch_daily_stock("삼성전자", "20240101")
        for row in rows:
            assert row[0] == "삼성전자"
