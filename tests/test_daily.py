"""Characterization tests for my_chart/db/daily.py.

Captures CURRENT behavior:
- _DAILY_COLS tuple length and column names
- _fetch_daily_stock() return type and empty-data behavior
- Exception handling returns (name, []) tuple
"""

from __future__ import annotations

import pandas as pd
import pytest


class TestDailyCols:
    """Characterizes _DAILY_COLS constant."""

    def test_daily_cols_is_tuple(self):
        from my_chart.db.daily import _DAILY_COLS

        assert isinstance(_DAILY_COLS, tuple)

    def test_daily_cols_has_32_elements(self):
        # SMA5/FromSMA5 컬럼 추가 (SPEC-SMA5-FILTER-001): 30 → 32
        from my_chart.db.daily import _DAILY_COLS

        assert len(_DAILY_COLS) == 32

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

        expected_indicators = ("SMA5", "EMA10", "EMA20", "SMA21", "SMA50", "EMA65", "SMA100", "SMA200")
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


class TestSMA5Indicator:
    """SPEC-SMA5-FILTER-001: SMA5 / FromSMA5 계산·영속화 정합성 (AC-1/AC-2/AC-8)."""

    @staticmethod
    def _col_index(name: str) -> int:
        """_DAILY_COLS에서 컬럼명의 위치 인덱스를 동적으로 조회 (위치 하드코딩 방지)."""
        from my_chart.db.daily import _DAILY_COLS

        return _DAILY_COLS.index(name)

    @staticmethod
    def _build_rows(close_values: list[float], monkeypatch) -> list[tuple]:
        from my_chart.db.daily import _fetch_daily_stock

        n = len(close_values)
        dates = pd.date_range("2024-01-02", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "Open": close_values,
                "High": [c + 5.0 for c in close_values],
                "Low": [c - 5.0 for c in close_values],
                "Close": close_values,
                "Volume": [1_000_000.0] * n,
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
        return rows

    def test_sma5_equals_close_5period_rolling_mean(self, monkeypatch):
        """AC-1: Close=[100,102,104,106,108] → 5번째 행 SMA5 == 104.0."""
        rows = self._build_rows([100.0, 102.0, 104.0, 106.0, 108.0], monkeypatch)
        sma5_idx = self._col_index("SMA5")
        # 5번째 행(index 4)의 SMA5 == (100+102+104+106+108)/5 == 104.0
        assert rows[4][sma5_idx] == pytest.approx(104.0, rel=1e-9)

    def test_from_sma5_matches_deviation_formula(self, monkeypatch):
        """AC-2: Close=108, SMA5=104.0 → FromSMA5(%) == (108-104)/104*100."""
        rows = self._build_rows([100.0, 102.0, 104.0, 106.0, 108.0], monkeypatch)
        from_idx = self._col_index("FromSMA5")
        expected = (108.0 - 104.0) / 104.0 * 100
        assert rows[4][from_idx] == pytest.approx(expected, rel=1e-9)

    def test_fewer_than_5_days_yields_null_without_raising(self, monkeypatch):
        """AC-8/REQ-SMA5-006: 4거래일 입력 → 모든 행 SMA5/FromSMA5 None (NULL), 예외 없음."""
        rows = self._build_rows([100.0, 102.0, 104.0, 106.0], monkeypatch)
        assert len(rows) == 4
        sma5_idx = self._col_index("SMA5")
        from_idx = self._col_index("FromSMA5")
        for row in rows:
            assert row[sma5_idx] is None
            assert row[from_idx] is None


class TestColumnAlignmentRoundTrip:
    """AC-9 [HARD]: 컬럼명↔값 정렬 round-trip 게이트.

    길이 검사(len(row)==32)만으로는 SMA5/FromSMA5가 swap된 위치에 들어가도 통과한다(둘 다 REAL).
    INSERT→SELECT 왕복으로 각 컬럼이 자기 값을 보유하는지 단언해 무음 위치 swap 오염을 검출한다.
    """

    @staticmethod
    def _build_distinct_rows(monkeypatch) -> list[tuple]:
        """SMA5≠FromSMA5≠SMA21≠SMA50≠FromSMA50이 되도록 distinct·단조증가 Close 시퀀스 생성."""
        from my_chart.db.daily import _fetch_daily_stock

        n = 60  # SMA50 비-NaN 보장
        # distinct하게 증가하는 Close: 5/21/50일선과 각 이격도가 서로 다른 수치가 되도록 비선형 증가
        close_values = [100.0 + i * 1.7 + (i % 3) * 0.3 for i in range(n)]
        dates = pd.date_range("2024-01-02", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "Open": close_values,
                "High": [c + 2.0 for c in close_values],
                "Low": [c - 2.0 for c in close_values],
                "Close": close_values,
                "Volume": [1_000_000.0] * n,
            },
            index=dates,
        )
        df.index.name = "Date"
        monkeypatch.setattr(
            "my_chart.db.daily.price_naver",
            lambda *args, **kwargs: df,
        )
        monkeypatch.setattr("my_chart.db.daily.time.sleep", lambda _: None)
        _, rows = _fetch_daily_stock("정렬검증주식", "20240101")
        return rows

    def test_each_column_holds_its_own_value_after_roundtrip(self, monkeypatch):
        """distinct 값으로 INSERT→SELECT 왕복 후 SMA5/FromSMA5/SMA21/SMA50/FromSMA50가
        각자의 기대값을 보유한다 (위치 swap이 없음을 증명)."""
        import sqlite3

        from my_chart.db.daily import _DAILY_COLS, _ensure_daily_table

        rows = self._build_distinct_rows(monkeypatch)
        # 실제 daily insert 경로(_DAILY_COLS placeholder + CREATE TABLE)를 그대로 사용
        conn = sqlite3.connect(":memory:")
        _ensure_daily_table(conn)
        placeholders = ", ".join(["?"] * len(_DAILY_COLS))
        conn.executemany(
            f"INSERT OR REPLACE INTO stock_prices VALUES ({placeholders})", rows
        )
        conn.commit()

        # 메모리 상의 기대값 (튜플 인덱스로 추출)
        idx = {c: _DAILY_COLS.index(c) for c in
               ("Name", "Date", "Close", "SMA5", "FromSMA5", "SMA21", "SMA50", "FromSMA50")}
        last = rows[-1]
        expected = {c: last[idx[c]] for c in
                    ("SMA5", "FromSMA5", "SMA21", "SMA50", "FromSMA50")}

        # 다섯 값이 서로 distinct한지(테스트 설계 자체 검증)
        vals = list(expected.values())
        assert len(set(round(v, 6) for v in vals)) == 5, f"기대값이 distinct하지 않음: {expected}"

        # read-back: 각 컬럼이 자기 값을 보유하는지 (swap 없음)
        db_row = conn.execute(
            "SELECT SMA5, FromSMA5, SMA21, SMA50, FromSMA50 FROM stock_prices "
            "WHERE Name = ? AND Date = ?",
            (last[idx["Name"]], last[idx["Date"]]),
        ).fetchone()
        conn.close()

        assert db_row[0] == pytest.approx(expected["SMA5"], rel=1e-9), "SMA5 컬럼 오염"
        assert db_row[1] == pytest.approx(expected["FromSMA5"], rel=1e-9), "FromSMA5 컬럼 오염"
        assert db_row[2] == pytest.approx(expected["SMA21"], rel=1e-9), "SMA21 컬럼 오염"
        assert db_row[3] == pytest.approx(expected["SMA50"], rel=1e-9), "SMA50 컬럼 오염"
        assert db_row[4] == pytest.approx(expected["FromSMA50"], rel=1e-9), "FromSMA50 컬럼 오염"

    def test_legacy_db_with_altered_columns_inserts_to_correct_columns(self, monkeypatch):
        """SPEC-SMA5-FILTER-001 v1.0.4 follow-up: 레거시 DB 컬럼 시프트 회귀 방지 게이트.

        근본 문제 (2026-05-26 라이브 검증 회귀):
        - daily.py가 _DAILY_COLS 중간(idx 13)에 SMA5를 삽입했지만 ALTER ADD COLUMN은
          기존 30-col stock_prices의 끝에 SMA5/FromSMA5를 append → 라이브 컬럼 순서가
          _DAILY_COLS와 어긋남.
        - positional INSERT (`VALUES (?, ?, ...)`)를 쓰면 placeholder idx 13의 값(SMA5)이
          라이브 idx 13(SMA21)에 들어가는 등 idx 13~31 전체가 한 칸씩 시프트되어
          무음 데이터 오염이 발생한다.

        본 테스트는 정확히 그 시나리오(legacy 30-col DDL + ALTER end-append)를 재현하고,
        column-name 기반 INSERT가 라이브 컬럼 순서와 무관하게 올바른 컬럼에 값을 쓰는지
        검증한다. AC-9의 fresh-DDL 한정 사각지대를 메운다.
        """
        import sqlite3

        from my_chart.db.daily import _DAILY_COLS

        # pre-SMA5 30-col 스키마 — 2026-05-25 이전 운영 DB와 동일 순서
        LEGACY_DDL = """
        CREATE TABLE stock_prices (
            Name TEXT NOT NULL,
            Date TEXT NOT NULL,
            Open REAL, High REAL, Low REAL, Close REAL, Change REAL, High52W REAL,
            Volume REAL, Volume20MA REAL, VolumeWon REAL,
            EMA10 REAL, EMA20 REAL,
            SMA21 REAL, SMA50 REAL, EMA65 REAL, SMA100 REAL, SMA200 REAL,
            DailyRange REAL, HLC REAL,
            FromEMA10 REAL, FromEMA20 REAL, FromSMA50 REAL, FromSMA200 REAL,
            Range REAL, ADR20 REAL, RS_Line REAL,
            SMA150 REAL, LOW_52W REAL, SMA200_20D_AGO REAL,
            PRIMARY KEY (Name, Date)
        )
        """
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute(LEGACY_DDL)

            # 멱등 ALTER 시뮬레이션 (daily.py L81-87 패턴) — SMA5/FromSMA5만 누락 상태
            conn.execute("ALTER TABLE stock_prices ADD COLUMN SMA5 REAL")
            conn.execute("ALTER TABLE stock_prices ADD COLUMN FromSMA5 REAL")

            # 라이브 시나리오 전제: 컬럼이 끝에 append됐는지 확인
            live_cols = [r[1] for r in conn.execute("PRAGMA table_info(stock_prices)").fetchall()]
            assert live_cols[30] == "SMA5", f"테스트 전제: SMA5는 idx 30에 위치 (실제: {live_cols[30]})"
            assert live_cols[31] == "FromSMA5", f"테스트 전제: FromSMA5는 idx 31에 위치 (실제: {live_cols[31]})"
            assert live_cols[13] == "SMA21", "테스트 전제: 라이브 idx 13은 SMA21 (코드는 SMA5라고 가정)"
            assert live_cols[26] == "RS_Line", "테스트 전제: 라이브 idx 26은 RS_Line"

            # distinct 값을 가진 row 생성 (AC-9 동일 헬퍼)
            rows = self._build_distinct_rows(monkeypatch)
            last = rows[-1]

            # daily.py와 동일한 column-name INSERT 사용 (fix 후 코드 경로)
            column_list = ", ".join(_DAILY_COLS)
            placeholders = ", ".join(["?"] * len(_DAILY_COLS))
            insert_sql = (
                f"INSERT OR REPLACE INTO stock_prices ({column_list}) "
                f"VALUES ({placeholders})"
            )
            conn.executemany(insert_sql, rows)
            conn.commit()

            # 검증: 각 컬럼이 자기 값을 보유 (시프트 0)
            idx = {c: _DAILY_COLS.index(c) for c in
                   ("Name", "Date", "SMA5", "FromSMA5", "SMA21", "SMA50",
                    "FromSMA50", "Range", "RS_Line")}
            expected = {c: last[idx[c]] for c in
                        ("SMA5", "FromSMA5", "SMA21", "SMA50", "FromSMA50", "Range", "RS_Line")}

            db_row = conn.execute(
                "SELECT SMA5, FromSMA5, SMA21, SMA50, FromSMA50, Range, RS_Line "
                "FROM stock_prices WHERE Name = ? AND Date = ?",
                (last[idx["Name"]], last[idx["Date"]]),
            ).fetchone()

            assert db_row[0] == pytest.approx(expected["SMA5"], rel=1e-9), (
                f"레거시 DB에서 SMA5 시프트 오염 — 기대 {expected['SMA5']}, 실제 {db_row[0]}"
            )
            assert db_row[1] == pytest.approx(expected["FromSMA5"], rel=1e-9), (
                f"레거시 DB에서 FromSMA5 시프트 오염 — 기대 {expected['FromSMA5']}, 실제 {db_row[1]}"
            )
            assert db_row[2] == pytest.approx(expected["SMA21"], rel=1e-9), "SMA21 시프트"
            assert db_row[3] == pytest.approx(expected["SMA50"], rel=1e-9), "SMA50 시프트"
            assert db_row[4] == pytest.approx(expected["FromSMA50"], rel=1e-9), "FromSMA50 시프트"
            assert db_row[5] == pytest.approx(expected["Range"], rel=1e-9), (
                f"Range 시프트 — 라이브 회귀(자주색 RS선 wild 패턴)의 직접 원인"
            )
            assert db_row[6] == pytest.approx(expected["RS_Line"], rel=1e-9), (
                f"RS_Line 시프트 — 사용자 차트의 RS 자주색 선이 Range 값으로 보이게 한 정확한 메커니즘"
            )
        finally:
            conn.close()
