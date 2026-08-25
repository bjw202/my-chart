"""Characterization + integration tests for backend/services/chart_service.py."""

from __future__ import annotations

import sqlite3

import pytest

from backend.services.chart_service import get_chart_data, get_weekly_chart_data


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
            EMA10 REAL, EMA20 REAL, SMA21 REAL, SMA50 REAL, EMA65 REAL, SMA100 REAL, SMA150 REAL, SMA200 REAL,
            DailyRange REAL, HLC REAL,
            FromEMA10 REAL, FromEMA20 REAL, FromSMA50 REAL, FromSMA200 REAL,
            Range REAL, ADR20 REAL,
            RS_Line REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    conn.executemany(
        """INSERT INTO stock_prices
           (Name, Date, Open, High, Low, Close, Volume,
            EMA10, EMA20, SMA50, SMA100, SMA150, SMA200)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
        sma150 = close * 0.95 if i >= 150 else None  # NULL for first 150 bars
        sma200 = close * 0.93 if i >= 200 else None  # NULL for first 200 bars
        rows.append((
            name, date,
            close * 0.99, close * 1.01, close * 0.98, close,  # OHLC
            1_000_000.0,                                        # Volume
            close * 0.99, close * 0.98,                         # EMA10, EMA20
            close * 0.97,                                        # SMA50
            sma100,                                              # SMA100 (nullable)
            sma150,                                              # SMA150 (nullable)
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

    def test_sma150_null_handling(self):
        """First 150 SMA150 values are NULL; only last 102 bars have values."""
        result = get_chart_data("005930", ":memory:")
        assert len(result.ma.sma150) == 102
        # Values must match the fixture formula (close * 0.95)
        assert result.ma.sma150[0].value == pytest.approx(result.candles[150].close * 0.95)

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


# ---------------------------------------------------------------------------
# Weekly chart (get_weekly_chart_data) — sma30 contract coverage
# ---------------------------------------------------------------------------


def _make_weekly_db(with_rs_line: bool = True, n: int = 60) -> sqlite3.Connection:
    """In-memory weekly stock_prices with SMA10/20/30/40 (and RS_Line if asked)."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    rs_col = ", RS_Line REAL" if with_rs_line else ""
    conn.execute(
        f"""CREATE TABLE stock_prices (
            Name TEXT NOT NULL,
            Date TEXT NOT NULL,
            Open REAL, High REAL, Low REAL, Close REAL,
            Volume REAL, VolumeSMA10 REAL,
            SMA10 REAL, SMA20 REAL, SMA30 REAL, SMA40 REAL{rs_col},
            PRIMARY KEY (Name, Date)
        )"""
    )
    import datetime as _dt
    base = _dt.date(2025, 1, 6)  # Mondays
    rows = []
    for i in range(n):
        date = (base + _dt.timedelta(weeks=i)).isoformat()
        close = 70000.0 + i * 100
        s10 = close * 0.99 if i >= 10 else None
        s20 = close * 0.98 if i >= 20 else None
        s30 = close * 0.97 if i >= 30 else None
        s40 = close * 0.96 if i >= 40 else None
        row = (
            "삼성전자", date,
            close * 0.99, close * 1.01, close * 0.98, close,
            5_000_000.0, 5_000_000.0,
            s10, s20, s30, s40,
        )
        if with_rs_line:
            row = row + (1.0 + i * 0.001,)
        rows.append(row)
    cols = "Name, Date, Open, High, Low, Close, Volume, VolumeSMA10, SMA10, SMA20, SMA30, SMA40"
    if with_rs_line:
        cols += ", RS_Line"
    conn.executemany(
        f"INSERT INTO stock_prices ({cols}) VALUES ({', '.join(['?'] * (13 if with_rs_line else 12))})",
        rows,
    )
    conn.commit()
    return conn


def _make_meta_db() -> sqlite3.Connection:
    """In-memory daily DB holding only stock_meta (name resolution)."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute("CREATE TABLE stock_meta (code TEXT PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO stock_meta (code, name) VALUES ('005930', '삼성전자')")
    conn.commit()
    return conn


class TestGetWeeklyChartData:
    def _patch(self, weekly_conn):
        """Route get_db_conn: daily path → meta DB, weekly path → weekly DB."""
        import backend.services.chart_service as svc
        self._svc = svc
        self._orig = svc.get_db_conn
        self._meta_conn = _make_meta_db()
        self._weekly_conn = weekly_conn

        def _router(path: str):
            return self._weekly_conn if "weekly" in path else self._meta_conn

        svc.get_db_conn = _router

    def teardown_method(self):
        if hasattr(self, "_svc"):
            self._svc.get_db_conn = self._orig
            self._meta_conn.close()
            self._weekly_conn.close()

    def test_returns_60_weeks_chronological(self):
        self._patch(_make_weekly_db())
        result = get_weekly_chart_data("005930", "daily.db", "weekly.db")
        assert result.timeframe == "weekly"
        assert len(result.candles) == 60
        dates = [c.time for c in result.candles]
        assert dates == sorted(dates)

    def test_sma30_series_null_handling_and_values(self):
        """First 30 SMA30 values are NULL; last 30 bars carry close * 0.97."""
        self._patch(_make_weekly_db())
        result = get_weekly_chart_data("005930", "daily.db", "weekly.db")
        assert len(result.ma.sma30) == 30
        assert result.ma.sma30[0].value == pytest.approx(
            result.candles[30].close * 0.97
        )

    def test_all_weekly_ma_lengths(self):
        self._patch(_make_weekly_db())
        result = get_weekly_chart_data("005930", "daily.db", "weekly.db")
        assert len(result.ma.sma10) == 50  # NULL for first 10
        assert len(result.ma.sma20) == 40  # NULL for first 20
        assert len(result.ma.sma30) == 30  # NULL for first 30
        assert len(result.ma.sma40) == 20  # NULL for first 40
        assert len(result.rs_line) == 60   # always populated in this fixture

    def test_weekly_without_rs_line_still_serves_sma30(self):
        """구버전 주간 DB (RS_Line 컬럼 없음): sma30은 여전히 내려간다."""
        self._patch(_make_weekly_db(with_rs_line=False))
        result = get_weekly_chart_data("005930", "daily.db", "weekly.db")
        assert len(result.ma.sma30) == 30
        assert result.rs_line == []

    def test_unknown_code_raises_lookup_error(self):
        self._patch(_make_weekly_db())
        with pytest.raises(LookupError) as exc_info:
            get_weekly_chart_data("999999", "daily.db", "weekly.db")
        assert "stock_not_found" in str(exc_info.value)
