"""SPEC-RS-LINE-001: RS Line 관련 테스트.

테스트 범주:
- RS_Line 계산 공식 검증 (주가 종가 / KOSPI 종가)
- KOSPI 데이터 누락 시 None 반환
- API 응답에 rs_line 필드 포함 확인
- 구버전 DB (RS_Line 컬럼 없음) 하위 호환성
"""

from __future__ import annotations

import sqlite3

import pandas as pd
import pytest

from backend.services.chart_service import get_chart_data


# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------


def _make_db_with_rs_line(
    stock_name: str = "삼성전자",
    code: str = "005930",
    n: int = 5,
    rs_values: list[float | None] | None = None,
) -> sqlite3.Connection:
    """RS_Line 컬럼이 있는 인메모리 DB 생성."""
    import datetime as _dt

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(
        """CREATE TABLE stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO stock_meta (code, name) VALUES (?, ?)",
        (code, stock_name),
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
            RS_Line REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    base = _dt.date(2024, 1, 2)
    rows = []
    for i in range(n):
        date = (base + _dt.timedelta(days=i)).isoformat()
        close = 70000.0 + i * 100
        rs = rs_values[i] if rs_values is not None else (close / 2500.0)
        rows.append((stock_name, date, close * 0.99, close * 1.01, close * 0.98, close,
                      1000000.0, close * 0.99, close * 0.98, close * 0.97, None, None, rs))
    conn.executemany(
        """INSERT INTO stock_prices
           (Name, Date, Open, High, Low, Close,
            EMA10, EMA20, SMA50, SMA100, SMA200, RS_Line)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(r[0], r[1], r[3], r[3], r[2], r[3], r[7], r[8], r[9], r[10], r[11], r[12])
         for r in rows],
    )
    conn.commit()
    return conn


def _make_db_without_rs_line(
    stock_name: str = "삼성전자",
    code: str = "005930",
    n: int = 5,
) -> sqlite3.Connection:
    """RS_Line 컬럼이 없는 구버전 인메모리 DB 생성."""
    import datetime as _dt

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(
        """CREATE TABLE stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT
        )"""
    )
    conn.execute(
        "INSERT INTO stock_meta (code, name) VALUES (?, ?)",
        (code, stock_name),
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
    base = _dt.date(2024, 1, 2)
    rows = []
    for i in range(n):
        date = (base + _dt.timedelta(days=i)).isoformat()
        close = 70000.0 + i * 100
        rows.append((stock_name, date, close * 0.99, close * 1.01, close * 0.98, close,
                      close * 0.99, close * 0.98, close * 0.97, None, None))
    conn.executemany(
        """INSERT INTO stock_prices
           (Name, Date, Open, High, Low, Close,
            EMA10, EMA20, SMA50, SMA100, SMA200)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [(r[0], r[1], r[3], r[3], r[2], r[3], r[6], r[7], r[8], r[9], r[10])
         for r in rows],
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# TASK-001/002: RS_Line 계산 공식 검증
# ---------------------------------------------------------------------------


class TestRsLineCalculation:
    """_fetch_daily_stock() 내 RS_Line 계산 검증."""

    def _make_stock_df(self, closes: list[float]) -> pd.DataFrame:
        """최소 OHLCV DataFrame 생성 (price_naver 반환 형식)."""
        dates = pd.date_range("2024-01-02", periods=len(closes), freq="B")
        return pd.DataFrame(
            {
                "Open": closes,
                "High": [c * 1.01 for c in closes],
                "Low": [c * 0.99 for c in closes],
                "Close": closes,
                "Volume": [1_000_000.0] * len(closes),
            },
            index=dates,
        )

    def _make_kospi_series(self, closes: list[float]) -> pd.Series:
        """KOSPI 종가 Series 생성."""
        dates = pd.date_range("2024-01-02", periods=len(closes), freq="B")
        return pd.Series(closes, index=dates, name="Close")

    def test_rs_line_formula_close_divided_by_kospi(self, monkeypatch):
        """RS_Line = 주가 종가 / KOSPI 종가 공식 검증."""
        from my_chart.db.daily import _fetch_daily_stock

        stock_closes = [70000.0, 71000.0, 72000.0]
        kospi_closes = [2500.0, 2510.0, 2520.0]

        stock_df = self._make_stock_df(stock_closes)
        kospi_series = self._make_kospi_series(kospi_closes)

        monkeypatch.setattr("my_chart.db.daily.price_naver", lambda *a, **kw: stock_df)
        monkeypatch.setattr("my_chart.db.daily.time.sleep", lambda _: None)

        _, rows = _fetch_daily_stock("테스트", "20240101", kospi_close=kospi_series)

        assert len(rows) == 3
        # RS_Line은 마지막 컬럼(-1)
        for i, row in enumerate(rows):
            expected = stock_closes[i] / kospi_closes[i]
            assert row[-1] is not None
            assert abs(row[-1] - expected) < 1e-6, (
                f"행 {i}: RS_Line={row[-1]}, 기대값={expected}"
            )

    def test_rs_line_none_when_kospi_none(self, monkeypatch):
        """kospi_close=None 이면 RS_Line은 NULL(None)이어야 한다."""
        from my_chart.db.daily import _fetch_daily_stock

        stock_df = self._make_stock_df([70000.0, 71000.0])
        monkeypatch.setattr("my_chart.db.daily.price_naver", lambda *a, **kw: stock_df)
        monkeypatch.setattr("my_chart.db.daily.time.sleep", lambda _: None)

        _, rows = _fetch_daily_stock("테스트", "20240101", kospi_close=None)

        assert len(rows) == 2
        for row in rows:
            assert row[-1] is None, f"RS_Line이 None이어야 하나 {row[-1]} 반환됨"

    def test_rs_line_none_on_missing_kospi_date(self, monkeypatch):
        """주가 날짜에 해당하는 KOSPI 데이터가 없으면 RS_Line은 None이어야 한다."""
        from my_chart.db.daily import _fetch_daily_stock

        # 주가: 2024-01-02 ~ 2024-01-04
        stock_df = self._make_stock_df([70000.0, 71000.0, 72000.0])
        # KOSPI: 2024-01-08 ~ (주가 날짜와 겹치지 않음)
        kospi_dates = pd.date_range("2024-01-08", periods=3, freq="B")
        kospi_series = pd.Series([2500.0, 2510.0, 2520.0], index=kospi_dates, name="Close")

        monkeypatch.setattr("my_chart.db.daily.price_naver", lambda *a, **kw: stock_df)
        monkeypatch.setattr("my_chart.db.daily.time.sleep", lambda _: None)

        _, rows = _fetch_daily_stock("테스트", "20240101", kospi_close=kospi_series)

        # KOSPI 날짜 불일치 → reindex → NaN → None
        for row in rows:
            assert row[-1] is None, f"날짜 불일치 시 RS_Line은 None이어야 하나 {row[-1]} 반환됨"

    def test_rs_line_in_daily_cols(self):
        """_DAILY_COLS에 'RS_Line'이 포함되어야 한다."""
        from my_chart.db.daily import _DAILY_COLS

        assert "RS_Line" in _DAILY_COLS

    def test_rs_line_is_last_in_daily_cols(self):
        """RS_Line은 _DAILY_COLS의 마지막 컬럼이어야 한다."""
        from my_chart.db.daily import _DAILY_COLS

        assert _DAILY_COLS[-1] == "RS_Line"


# ---------------------------------------------------------------------------
# TASK-003/004: API 응답에 rs_line 필드 포함
# ---------------------------------------------------------------------------


class TestChartApiRsLine:
    """get_chart_data() RS_Line 관련 테스트."""

    def setup_method(self):
        import backend.services.chart_service as svc
        self._orig_get_conn = svc.get_db_conn

    def teardown_method(self):
        import backend.services.chart_service as svc
        svc.get_db_conn = self._orig_get_conn

    def test_rs_line_field_in_response(self):
        """응답에 rs_line 필드가 있어야 한다."""
        import backend.services.chart_service as svc
        conn = _make_db_with_rs_line(n=5)
        svc.get_db_conn = lambda _path: conn
        try:
            result = get_chart_data("005930", ":memory:")
            assert hasattr(result, "rs_line")
        finally:
            conn.close()

    def test_rs_line_values_populated_when_data_exists(self):
        """RS_Line 값이 있으면 rs_line 시리즈에 포함되어야 한다."""
        import backend.services.chart_service as svc
        rs_vals = [28.0, 28.1, 28.2, 28.3, 28.4]
        conn = _make_db_with_rs_line(n=5, rs_values=rs_vals)
        svc.get_db_conn = lambda _path: conn
        try:
            result = get_chart_data("005930", ":memory:")
            assert len(result.rs_line) == 5
            for pt in result.rs_line:
                assert pt.value > 0
        finally:
            conn.close()

    def test_rs_line_excludes_null_values(self):
        """DB에 NULL인 RS_Line 값은 rs_line 시리즈에서 제외되어야 한다."""
        import backend.services.chart_service as svc
        # 첫 2개 None, 나머지 3개 값 있음
        rs_vals = [None, None, 28.0, 28.1, 28.2]
        conn = _make_db_with_rs_line(n=5, rs_values=rs_vals)
        svc.get_db_conn = lambda _path: conn
        try:
            result = get_chart_data("005930", ":memory:")
            assert len(result.rs_line) == 3
        finally:
            conn.close()

    def test_rs_line_empty_list_by_default(self):
        """rs_line 필드의 기본값은 빈 리스트이어야 한다."""
        from backend.schemas.chart import ChartResponse, MAOverlays

        response = ChartResponse(
            timeframe="daily",
            candles=[],
            volume=[],
            ma=MAOverlays(),
        )
        assert response.rs_line == []


# ---------------------------------------------------------------------------
# TASK-004: 구버전 DB (RS_Line 컬럼 없음) 하위 호환성
# ---------------------------------------------------------------------------


class TestChartApiBackwardCompat:
    """RS_Line 컬럼이 없는 구버전 DB에서도 오류 없이 동작해야 한다."""

    def setup_method(self):
        import backend.services.chart_service as svc
        self._orig_get_conn = svc.get_db_conn

    def teardown_method(self):
        import backend.services.chart_service as svc
        svc.get_db_conn = self._orig_get_conn

    def test_old_db_returns_empty_rs_line(self):
        """RS_Line 컬럼 없는 구버전 DB에서 rs_line=[] 반환되어야 한다."""
        import backend.services.chart_service as svc
        conn = _make_db_without_rs_line(n=5)
        svc.get_db_conn = lambda _path: conn
        try:
            result = get_chart_data("005930", ":memory:")
            assert result.rs_line == []
        finally:
            conn.close()

    def test_old_db_candles_still_work(self):
        """RS_Line 컬럼 없는 구버전 DB에서 기존 캔들 데이터는 정상 반환되어야 한다."""
        import backend.services.chart_service as svc
        conn = _make_db_without_rs_line(n=5)
        svc.get_db_conn = lambda _path: conn
        try:
            result = get_chart_data("005930", ":memory:")
            assert len(result.candles) == 5
            assert result.timeframe == "daily"
        finally:
            conn.close()

    def test_old_db_no_exception_raised(self):
        """RS_Line 컬럼 없는 구버전 DB에서 예외가 발생하지 않아야 한다."""
        import backend.services.chart_service as svc
        conn = _make_db_without_rs_line(n=5)
        svc.get_db_conn = lambda _path: conn
        try:
            # 예외 없이 완료되어야 함
            result = get_chart_data("005930", ":memory:")
            assert result is not None
        finally:
            conn.close()
