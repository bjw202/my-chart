"""Characterization + integration tests for backend/services/chart_service.py."""

from __future__ import annotations

import sqlite3

import pytest

from backend.services.chart_service import get_chart_data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_chart_db(stocks: list[dict], price_rows: list[tuple]) -> sqlite3.Connection:
    """Create in-memory DB with stock_meta and stock_prices tables."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)

    conn.execute(
        """CREATE TABLE stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT,
            market TEXT,
            market_cap INTEGER,
            sector_major TEXT,
            sector_minor TEXT,
            product TEXT,
            close REAL, change_1d REAL,
            ema10 REAL, ema20 REAL, sma50 REAL, sma100 REAL, sma200 REAL,
            high52w REAL, chg_1w REAL, chg_1m REAL, chg_3m REAL,
            rs_12m REAL, ma50_w REAL, ma150_w REAL, ma200_w REAL,
            last_updated TEXT
        )"""
    )
    for s in stocks:
        conn.execute(
            "INSERT INTO stock_meta (code, name) VALUES (?, ?)",
            (s["code"], s["name"]),
        )

    conn.execute(
        """CREATE TABLE stock_prices (
            Name TEXT NOT NULL,
            Date TEXT NOT NULL,
            Open REAL, High REAL, Low REAL, Close REAL,
            Change REAL, High52W REAL,
            Volume REAL, Volume20MA REAL, VolumeWon REAL,
            EMA10 REAL, EMA20 REAL, SMA21 REAL, SMA50 REAL, EMA65 REAL, SMA100 REAL, SMA200 REAL,
            DailyRange REAL, HLC REAL,
            FromEMA10 REAL, FromEMA20 REAL, FromSMA50 REAL, FromSMA200 REAL,
            Range REAL, ADR20 REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    conn.executemany(
        """INSERT INTO stock_prices
           (Name, Date, Open, High, Low, Close, Volume,
            EMA10, EMA20, SMA50, SMA100, SMA200)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        price_rows,
    )
    conn.commit()
    return conn


# 252 rows of fake daily OHLCV for 삼성전자
def _make_price_rows(name: str, n: int = 252) -> list[tuple]:
    import datetime as _dt
    rows = []
    base = _dt.date(2024, 1, 2)
    for i in range(n):
        date = (base + _dt.timedelta(days=i)).isoformat()
        close = 70000.0 + i * 10
        sma100 = close * 0.97 if i >= 100 else None  # NULL for first 100 bars
        sma200 = close * 0.93 if i >= 200 else None  # NULL for first 200 bars
        rows.append((
            name, date,
            close * 0.99, close * 1.01, close * 0.98, close,  # OHLC
            1_000_000.0,                                        # Volume
            close * 0.99, close * 0.98,                         # EMA10, EMA20
            close * 0.97,                                        # SMA50
            sma100,                                              # SMA100 (nullable)
            sma200,                                              # SMA200 (nullable)
        ))
    return rows


class TestGetChartData:
    def setup_method(self):
        price_rows = _make_price_rows("삼성전자")
        self.conn = _make_chart_db(
            [{"code": "005930", "name": "삼성전자"}],
            price_rows,
        )
        import backend.services.chart_service as svc
        self._orig_get_conn = svc.get_db_conn
        svc.get_db_conn = lambda _path: self.conn

    def teardown_method(self):
        import backend.services.chart_service as svc
        svc.get_db_conn = self._orig_get_conn
        self.conn.close()

    def test_returns_252_candles(self):
        result = get_chart_data("005930", ":memory:")
        assert len(result.candles) == 252

    def test_candles_in_chronological_order(self):
        result = get_chart_data("005930", ":memory:")
        dates = [c.time for c in result.candles]
        assert dates == sorted(dates)

    def test_candle_fields_present(self):
        result = get_chart_data("005930", ":memory:")
        bar = result.candles[0]
        assert bar.time  # non-empty string
        assert bar.open > 0
        assert bar.high >= bar.low
        assert bar.close > 0

    def test_volume_series_length_matches_candles(self):
        result = get_chart_data("005930", ":memory:")
        assert len(result.volume) == 252

    def test_ma_overlays_present(self):
        result = get_chart_data("005930", ":memory:")
        assert len(result.ma.ema10) == 252
        assert len(result.ma.ema20) == 252
        assert len(result.ma.sma50) == 252

    def test_sma100_null_handling(self):
        """First 100 SMA100 values are NULL; they must be excluded from the series."""
        result = get_chart_data("005930", ":memory:")
        # Only entries where SMA100 is not None → last 152 bars
        assert len(result.ma.sma100) == 152

    def test_sma200_null_handling(self):
        """First 200 SMA200 values are NULL; only last 52 bars have values."""
        result = get_chart_data("005930", ":memory:")
        assert len(result.ma.sma200) == 52

    def test_ma_points_have_time_and_value(self):
        result = get_chart_data("005930", ":memory:")
        pt = result.ma.ema10[0]
        assert pt.time  # non-empty
        assert pt.value > 0

    def test_stock_not_found_raises_lookup_error(self):
        with pytest.raises(LookupError) as exc_info:
            get_chart_data("999999", ":memory:")
        assert "stock_not_found" in str(exc_info.value)

    def test_no_price_data_raises_lookup_error(self):
        """Code in stock_meta but no matching price rows → LookupError."""
        self.conn.execute("INSERT INTO stock_meta (code, name) VALUES (?,?)", ("000001", "비상장A"))
        self.conn.commit()
        with pytest.raises(LookupError) as exc_info:
            get_chart_data("000001", ":memory:")
        assert "no_data" in str(exc_info.value)

    def test_stock_meta_missing_raises_lookup_error(self):
        """If stock_meta table doesn't exist, should raise LookupError."""
        conn_no_meta = sqlite3.connect(":memory:", check_same_thread=False)
        import backend.services.chart_service as svc
        svc.get_db_conn = lambda _path: conn_no_meta
        try:
            with pytest.raises(LookupError):
                get_chart_data("005930", ":memory:")
        finally:
            conn_no_meta.close()
            svc.get_db_conn = self._orig_get_conn
