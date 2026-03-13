"""Characterization tests for my_chart/config.py.

These tests capture the CURRENT behavior of config constants. They should
remain stable as long as the config values are not intentionally changed.
"""

from __future__ import annotations

from pathlib import Path


def test_default_db_daily_is_string():
    from my_chart.config import DEFAULT_DB_DAILY

    assert isinstance(DEFAULT_DB_DAILY, str)


def test_default_db_daily_ends_with_expected_name():
    from my_chart.config import DEFAULT_DB_DAILY

    assert DEFAULT_DB_DAILY.endswith("stock_data_daily")


def test_default_db_weekly_is_string():
    from my_chart.config import DEFAULT_DB_WEEKLY

    assert isinstance(DEFAULT_DB_WEEKLY, str)


def test_default_db_weekly_ends_with_expected_name():
    from my_chart.config import DEFAULT_DB_WEEKLY

    assert DEFAULT_DB_WEEKLY.endswith("stock_data_weekly")


def test_sectormap_path_is_path_object():
    from my_chart.config import SECTORMAP_PATH

    assert isinstance(SECTORMAP_PATH, Path)


def test_sectormap_path_filename():
    from my_chart.config import SECTORMAP_PATH

    assert SECTORMAP_PATH.name == "sectormap.xlsx"


def test_sectormap_path_parent_is_input_dir():
    from my_chart.config import SECTORMAP_PATH

    assert SECTORMAP_PATH.parent.name == "Input"


def test_reference_stock_is_samsung():
    from my_chart.config import REFERENCE_STOCK

    assert REFERENCE_STOCK == "삼성전자"


def test_min_close_price_is_positive_int():
    from my_chart.config import MIN_CLOSE_PRICE

    assert isinstance(MIN_CLOSE_PRICE, int)
    assert MIN_CLOSE_PRICE > 0


def test_min_close_price_value():
    from my_chart.config import MIN_CLOSE_PRICE

    assert MIN_CLOSE_PRICE == 5000
