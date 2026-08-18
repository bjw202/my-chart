"""Tests for backend/services/meta_service.py — stock_meta rebuild logic."""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from backend.services.meta_service import _business_days_since, _rebuild


# ---------------------------------------------------------------------------
# Helpers to build test SQLite DB files
# ---------------------------------------------------------------------------


def _create_weekly_db(path: str, stocks: list[dict], date: str = "2026-02-28") -> None:
    """Populate a weekly DB file with stock_prices and relative_strength rows."""
    conn = sqlite3.connect(path)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_prices (
            Name TEXT NOT NULL, Date TEXT NOT NULL,
            Open REAL, High REAL, Low REAL, Close REAL,
            Volume REAL, VolumeSMA10 REAL,
            CHG_1W REAL, CHG_1M REAL, CHG_2M REAL, CHG_3M REAL,
            CHG_6M REAL, CHG_9M REAL, CHG_12M REAL,
            SMA10 REAL, SMA20 REAL, SMA40 REAL,
            SMA40_Trend_1M REAL, SMA40_Trend_2M REAL,
            SMA40_Trend_3M REAL, SMA40_Trend_4M REAL,
            MAX10 REAL, MAX52 REAL, min52 REAL, Close_52min REAL,
            RS_1M REAL, RS_2M REAL, RS_3M REAL,
            RS_6M REAL, RS_9M REAL, RS_12M REAL, RS_Line REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS relative_strength (
            Name TEXT NOT NULL, Date TEXT NOT NULL,
            RS_12M_Rating REAL, RS_6M_Rating REAL,
            RS_3M_Rating REAL, RS_1M_Rating REAL,
            PRIMARY KEY (Name, Date)
        )"""
    )
    for s in stocks:
        conn.execute(
            """INSERT INTO stock_prices
               (Name, Date, CHG_1W, CHG_1M, CHG_3M, SMA10, SMA20, SMA40)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                s["name"], date,
                s.get("chg_1w", 2.0), s.get("chg_1m", 5.0), s.get("chg_3m", 10.0),
                s.get("sma10", 68000.0), s.get("sma20", 65000.0), s.get("sma40", 62000.0),
            ),
        )
        conn.execute(
            "INSERT INTO relative_strength (Name, Date, RS_12M_Rating) VALUES (?,?,?)",
            (s["name"], date, s.get("rs_12m", 75.0)),
        )
    conn.commit()
    conn.close()


def _mock_sector_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Code": ["005930", "000660"],
        "Name": ["삼성전자", "SK하이닉스"],
        "Market": ["KOSPI", "KOSPI"],
        "산업명(대)": ["전기전자", "전기전자"],
        "산업명(중)": ["반도체", "반도체"],
        "주요제품": ["메모리", "D램"],
    })


def _stub_basic_data(monkeypatch, shares: dict[str, int] | None) -> list[str]:
    """Input/basic_data.xlsx 의존을 끊고 테스트가 상장주식수를 직접 공급한다.

    shares=None 이면 파일이 없는 상황(소스 unavailable)을 재현한다.
    반환값은 read_excel 호출 기록으로, 목이 실제로 먹혔는지 확인하는 데 쓴다.
    """
    calls: list[str] = []
    orig_exists = Path.exists

    def _fake_exists(self: Path) -> bool:
        if self.name == "basic_data.xlsx":
            return shares is not None
        return orig_exists(self)

    def _fake_read_excel(path, *args, **kwargs):
        calls.append(str(path))
        assert shares is not None, "소스 부재 시나리오에서는 read_excel이 호출되면 안 된다"
        return pd.DataFrame({
            "단축코드": list(shares.keys()),
            "상장주식수": list(shares.values()),
        })

    monkeypatch.setattr(Path, "exists", _fake_exists)
    monkeypatch.setattr(pd, "read_excel", _fake_read_excel)
    return calls


# ---------------------------------------------------------------------------
# _business_days_since tests
# ---------------------------------------------------------------------------


class TestBusinessDaysSince:
    def test_today_is_zero(self):
        assert _business_days_since(datetime.date.today()) == 0

    def test_future_is_zero(self):
        future = datetime.date.today() + datetime.timedelta(days=5)
        assert _business_days_since(future) == 0

    def test_one_week_ago(self):
        week_ago = datetime.date.today() - datetime.timedelta(days=7)
        result = _business_days_since(week_ago)
        assert 4 <= result <= 5

    def test_two_days_ago_is_small(self):
        two_days_ago = datetime.date.today() - datetime.timedelta(days=2)
        assert _business_days_since(two_days_ago) <= 2


# ---------------------------------------------------------------------------
# _rebuild integration tests
# ---------------------------------------------------------------------------


class TestRebuild:
    """Tests for the _rebuild() function using in-memory daily conn + weekly file."""

    _DEFAULT_DAILY_STOCKS = [
        {"name": "삼성전자", "close": 70000.0, "sma100": 68000.0, "sma200": 65000.0},
        {"name": "SK하이닉스", "close": 130000.0, "sma100": None, "sma200": None},
    ]
    _DEFAULT_WEEKLY_STOCKS = [
        {"name": "삼성전자", "rs_12m": 85.0},
        {"name": "SK하이닉스", "rs_12m": 72.0},
    ]

    def _make_conn(self, daily_stocks, _weekly_path: str, monkeypatch) -> sqlite3.Connection:
        """Set up in-memory daily conn and patch dependencies."""
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.execute(
            """CREATE TABLE stock_prices (
                Name TEXT NOT NULL, Date TEXT NOT NULL,
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
        for s in daily_stocks:
            conn.execute(
                """INSERT INTO stock_prices
                   (Name, Date, Close, Change, EMA10, EMA20, SMA50, SMA100, SMA200, High52W)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    s["name"], "2026-02-28",
                    s.get("close", 70000.0), s.get("change", 1.5),
                    s.get("ema10", 69000.0), s.get("ema20", 68000.0),
                    s.get("sma50", 65000.0), s.get("sma100"), s.get("sma200"),
                    s.get("high52w", 75000.0),
                ),
            )
        conn.commit()

        import backend.services.meta_service as svc
        monkeypatch.setattr(svc, "get_sector_registry", lambda: _mock_sector_df())
        monkeypatch.setattr(svc, "REFERENCE_STOCK", "삼성전자")

        # Patch pykrx to avoid network calls
        import types
        fake_pykrx = types.ModuleType("pykrx_mock")
        mc_data = pd.DataFrame(
            {"시가총액": [300_000_000_000_000, 100_000_000_000_000]},
            index=pd.Index(["005930", "000660"]),
        )
        setattr(fake_pykrx, "get_market_cap", lambda *_: mc_data)
        monkeypatch.setattr(svc, "pykrx_stock", fake_pykrx, raising=False)

        return conn

    def test_basic_rebuild_inserts_both_stocks(self, monkeypatch, tmp_path):
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = self._make_conn(self._DEFAULT_DAILY_STOCKS, weekly_path, monkeypatch)
        _rebuild(conn, weekly_path)

        rows = conn.execute("SELECT code FROM stock_meta").fetchall()
        codes = [r[0] for r in rows]
        assert "005930" in codes
        assert "000660" in codes

    def test_missing_daily_stock_excluded(self, monkeypatch, tmp_path):
        """A stock in sectormap but without daily data must not appear in stock_meta."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        # Only 삼성전자 in daily DB
        conn = self._make_conn(
            [{"name": "삼성전자", "close": 70000.0, "sma100": 68000.0, "sma200": 65000.0}],
            weekly_path,
            monkeypatch,
        )
        _rebuild(conn, weekly_path)

        codes = [r[0] for r in conn.execute("SELECT code FROM stock_meta").fetchall()]
        assert "005930" in codes
        assert "000660" not in codes

    def test_null_sma100_stored_correctly(self, monkeypatch, tmp_path):
        """Stocks with insufficient history should store NULL sma100/sma200."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = self._make_conn(
            [{"name": "삼성전자", "close": 5000.0, "sma100": None, "sma200": None}],
            weekly_path,
            monkeypatch,
        )
        _rebuild(conn, weekly_path)

        row = conn.execute(
            "SELECT sma100, sma200 FROM stock_meta WHERE code = '005930'"
        ).fetchone()
        assert row is not None
        assert row[0] is None
        assert row[1] is None

    def test_null_weekly_data_stored_as_null(self, monkeypatch, tmp_path):
        """Stock with no weekly data row gets NULL for chg_1w, rs_12m, etc."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, [])  # empty weekly DB

        conn = self._make_conn(
            [{"name": "삼성전자", "close": 70000.0, "sma100": 68000.0, "sma200": 65000.0}],
            weekly_path,
            monkeypatch,
        )
        _rebuild(conn, weekly_path)

        row = conn.execute(
            "SELECT chg_1w, rs_12m FROM stock_meta WHERE code = '005930'"
        ).fetchone()
        assert row is not None
        # Both fields should be NULL since no weekly data exists
        assert row[0] is None
        assert row[1] is None

    def test_rs_data_populated_from_weekly(self, monkeypatch, tmp_path):
        """RS_12M_Rating from weekly DB should appear in stock_meta."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, [{"name": "삼성전자", "rs_12m": 92.5}])

        conn = self._make_conn(
            [{"name": "삼성전자", "close": 70000.0, "sma100": 68000.0, "sma200": 65000.0}],
            weekly_path,
            monkeypatch,
        )
        _rebuild(conn, weekly_path)

        row = conn.execute("SELECT rs_12m FROM stock_meta WHERE code = '005930'").fetchone()
        assert row is not None
        assert abs(row[0] - 92.5) < 0.001

    def test_empty_daily_db_does_nothing(self, monkeypatch, tmp_path):
        """If no daily data exists for reference stock, stock_meta stays empty."""
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = self._make_conn([], weekly_path, monkeypatch)
        # No stock_prices rows at all → latest_daily_date is None → early return
        _rebuild(conn, weekly_path)

        # stock_meta table should exist but be empty
        try:
            rows = conn.execute("SELECT count(*) FROM stock_meta").fetchone()
            assert rows[0] == 0
        except sqlite3.OperationalError:
            pass  # table might not exist if _rebuild returned early before CREATE TABLE

    def test_market_cap_computed_from_basic_data(self, monkeypatch, tmp_path):
        """market_cap = basic_data.xlsx의 상장주식수 × 종가 (원 단위 저장).

        구 테스트명은 test_market_cap_stored_from_pykrx 였다. 프로덕션이 pykrx를
        더 이상 쓰지 않고 Input/basic_data.xlsx에서 시가총액을 계산하도록 바뀌었다
        (meta_service.py: 상장주식수 × 종가, 원 단위).
        """
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = self._make_conn(self._DEFAULT_DAILY_STOCKS, weekly_path, monkeypatch)

        # 레포의 실제 xlsx를 읽지 않고 테스트가 상장주식수를 공급한다
        shares = {"005930": 5_969_782_550, "000660": 728_002_365}
        calls = _stub_basic_data(monkeypatch, shares)

        _rebuild(conn, weekly_path)

        assert calls, "read_excel 목이 실제로 호출되어야 한다(레포 xlsx를 읽으면 안 됨)"

        row = conn.execute(
            "SELECT market_cap FROM stock_meta WHERE code = '005930'"
        ).fetchone()
        assert row is not None
        # 삼성전자 종가 70000.0 × 상장주식수 = 시가총액(원)
        close_price = 70000.0
        assert row[0] == int(close_price * shares["005930"])

    def test_sma5_column_exists_and_value_copied(self, monkeypatch, tmp_path):
        """SPEC-SMA5-FILTER-001 AC-4/REQ-SMA5-003: rebuild 후 stock_meta에 sma5가 존재하고
        최신 일봉 날짜의 stock_prices.SMA5가 stock_meta.sma5로 복사된다.

        이 테스트는 SMA5 + Minervini 컬럼을 포함한 daily DDL을 직접 정의해
        meta_service의 신규 SELECT 분기(has_minervini_price_cols=True)를 탄다.
        """
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.execute(
            """CREATE TABLE stock_prices (
                Name TEXT NOT NULL, Date TEXT NOT NULL,
                Open REAL, High REAL, Low REAL, Close REAL,
                Change REAL, High52W REAL,
                Volume REAL, Volume20MA REAL, VolumeWon REAL,
                EMA10 REAL, EMA20 REAL, SMA5 REAL, SMA21 REAL, SMA50 REAL, EMA65 REAL,
                SMA100 REAL, SMA200 REAL,
                DailyRange REAL, HLC REAL,
                FromEMA10 REAL, FromEMA20 REAL, FromSMA5 REAL, FromSMA50 REAL, FromSMA200 REAL,
                Range REAL, ADR20 REAL,
                RS_Line REAL,
                SMA150 REAL, LOW_52W REAL, SMA200_20D_AGO REAL,
                PRIMARY KEY (Name, Date)
            )"""
        )
        # 두 날짜를 넣어 "최신 일자" 복사를 검증한다 (오래된 날짜의 SMA5는 복사되면 안 됨).
        conn.execute(
            """INSERT INTO stock_prices
               (Name, Date, Close, Change, EMA10, EMA20, SMA5, SMA50, SMA100, SMA200,
                High52W, SMA150, LOW_52W, SMA200_20D_AGO)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("삼성전자", "2026-02-27", 69000.0, 1.0, 68500.0, 68000.0, 67000.0,
             65000.0, 64000.0, 63000.0, 75000.0, 62000.0, 50000.0, 62500.0),
        )
        conn.execute(
            """INSERT INTO stock_prices
               (Name, Date, Close, Change, EMA10, EMA20, SMA5, SMA50, SMA100, SMA200,
                High52W, SMA150, LOW_52W, SMA200_20D_AGO)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("삼성전자", "2026-02-28", 70000.0, 1.5, 69000.0, 68000.0, 71234.5,
             65000.0, 64000.0, 63000.0, 75000.0, 62000.0, 50000.0, 62500.0),
        )
        conn.commit()

        import backend.services.meta_service as svc
        monkeypatch.setattr(svc, "get_sector_registry", lambda: _mock_sector_df())
        monkeypatch.setattr(svc, "REFERENCE_STOCK", "삼성전자")

        _rebuild(conn, weekly_path)

        # 컬럼 존재 검증 (REQ-SMA5-003)
        meta_cols = {r[1] for r in conn.execute("PRAGMA table_info(stock_meta)").fetchall()}
        assert "sma5" in meta_cols

        # 최신 일자(2026-02-28)의 SMA5(71234.5)가 복사되었는지 검증 (AC-4)
        row = conn.execute(
            "SELECT sma5 FROM stock_meta WHERE code = '005930'"
        ).fetchone()
        assert row is not None
        assert row[0] == pytest.approx(71234.5, rel=1e-9)
        conn.close()

    def test_sma5_meta_roundtrip_matches_stock_prices(self, monkeypatch, tmp_path):
        """SPEC-SMA5-FILTER-001 AC-9 (meta 정렬 검사): rebuild 후 stock_meta.sma5가
        최신 일자 stock_prices.SMA5와 동일 값임을 read-back으로 단언한다 (SELECT/INSERT 정합성 증명).
        """
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.execute(
            """CREATE TABLE stock_prices (
                Name TEXT NOT NULL, Date TEXT NOT NULL,
                Open REAL, High REAL, Low REAL, Close REAL,
                Change REAL, High52W REAL,
                Volume REAL, Volume20MA REAL, VolumeWon REAL,
                EMA10 REAL, EMA20 REAL, SMA5 REAL, SMA21 REAL, SMA50 REAL, EMA65 REAL,
                SMA100 REAL, SMA200 REAL,
                DailyRange REAL, HLC REAL,
                FromEMA10 REAL, FromEMA20 REAL, FromSMA5 REAL, FromSMA50 REAL, FromSMA200 REAL,
                Range REAL, ADR20 REAL,
                RS_Line REAL,
                SMA150 REAL, LOW_52W REAL, SMA200_20D_AGO REAL,
                PRIMARY KEY (Name, Date)
            )"""
        )
        distinct_sma5 = 54321.98765
        conn.execute(
            """INSERT INTO stock_prices
               (Name, Date, Close, Change, EMA10, EMA20, SMA5, SMA50, SMA100, SMA200,
                High52W, SMA150, LOW_52W, SMA200_20D_AGO)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("삼성전자", "2026-02-28", 70000.0, 1.5, 69000.0, 68000.0, distinct_sma5,
             65000.0, 64000.0, 63000.0, 75000.0, 62000.0, 50000.0, 62500.0),
        )
        conn.commit()

        import backend.services.meta_service as svc
        monkeypatch.setattr(svc, "get_sector_registry", lambda: _mock_sector_df())
        monkeypatch.setattr(svc, "REFERENCE_STOCK", "삼성전자")

        _rebuild(conn, weekly_path)

        latest = conn.execute(
            "SELECT MAX(Date) FROM stock_prices WHERE Name = '삼성전자'"
        ).fetchone()[0]
        sp_sma5 = conn.execute(
            "SELECT SMA5 FROM stock_prices WHERE Name = '삼성전자' AND Date = ?",
            (latest,),
        ).fetchone()[0]
        meta_sma5 = conn.execute(
            "SELECT sma5 FROM stock_meta WHERE code = '005930'"
        ).fetchone()[0]
        conn.close()

        assert sp_sma5 == pytest.approx(distinct_sma5, rel=1e-12)
        assert meta_sma5 == pytest.approx(sp_sma5, rel=1e-12), "stock_meta.sma5 ≠ stock_prices.SMA5"

    def test_legacy_stock_meta_without_sma5_gets_column_added_on_rebuild(self, tmp_path):
        """SPEC-SMA5-FILTER-001 follow-up: 레거시 stock_meta(sma5 컬럼 없음)에 대해
        멱등 ALTER가 sma5 컬럼을 자동 추가해야 한다.

        User scenario (2026-05-26 라이브 검증): 기존 DB를 삭제하지 않고
        /api/db/update만 실행한 경우 — daily.py의 ALTER 루프는 stock_prices에
        SMA5/FromSMA5를 추가하지만, stock_meta의 _STOCK_META_DDL은
        CREATE TABLE IF NOT EXISTS라 기존 26-col 스키마가 잔존 → SMA5 패턴 평가 시
        'no such column: sma5' → 0건 반환. 멱등 ALTER로 self-healing 되어야 한다
        (daily.py SMA5 ALTER 패턴과 대칭).
        """
        from backend.services.meta_service import _ensure_meta_minervini_columns

        db_path = tmp_path / "legacy.db"
        # pre-SMA5 stock_meta DDL — 2026-05-25 이전 운영 DB 스키마와 동일 (26 컬럼)
        legacy_ddl = """
        CREATE TABLE stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT,
            market TEXT,
            market_cap INTEGER,
            sector_major TEXT,
            sector_minor TEXT,
            product TEXT,
            close REAL,
            change_1d REAL,
            ema10 REAL,
            ema20 REAL,
            sma50 REAL,
            sma100 REAL,
            sma200 REAL,
            high52w REAL,
            chg_1w REAL,
            chg_1m REAL,
            chg_3m REAL,
            rs_12m REAL,
            sma10_w REAL,
            sma20_w REAL,
            sma40_w REAL,
            last_updated TEXT,
            sma150 REAL,
            low52w REAL,
            sma200_20d_ago REAL
        )
        """
        conn = sqlite3.connect(str(db_path))
        try:
            conn.execute(legacy_ddl)
            legacy_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(stock_meta)").fetchall()
            }
            assert "sma5" not in legacy_cols, "테스트 전제: pre-SMA5 스키마는 sma5가 없어야 함"

            # When: 멱등 ALTER 호출
            _ensure_meta_minervini_columns(conn)

            # Then: sma5 컬럼이 자동 추가됨
            migrated_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(stock_meta)").fetchall()
            }
            assert "sma5" in migrated_cols, (
                "_ensure_meta_minervini_columns가 sma5를 ALTER로 추가해야 함 — "
                "이 단언이 실패하면 사용자 시나리오('SMA5 > EMA20'가 0건 반환)가 재현됨"
            )
            # 멱등성 확인: 재호출해도 오류 없이 통과 (이미 추가된 컬럼은 무시)
            _ensure_meta_minervini_columns(conn)
        finally:
            conn.close()

    def test_market_cap_is_null_when_basic_data_unavailable(self, monkeypatch, tmp_path):
        """회귀: basic_data.xlsx를 읽을 수 없으면 crash 없이 market_cap = NULL.

        구 테스트명은 test_market_cap_is_null_when_pykrx_fails_and_no_dday_column
        이었다. 프로덕션에서 pykrx 폴백 경로가 사라지고 시가총액 소스가
        Input/basic_data.xlsx 하나로 바뀌었으므로, NULL 조건도 '그 소스의 부재'다.
        """
        weekly_path = str(tmp_path / "weekly.db")
        _create_weekly_db(weekly_path, self._DEFAULT_WEEKLY_STOCKS)

        conn = self._make_conn(self._DEFAULT_DAILY_STOCKS, weekly_path, monkeypatch)

        # basic_data.xlsx 부재 재현 (shares=None)
        calls = _stub_basic_data(monkeypatch, None)

        _rebuild(conn, weekly_path)

        assert not calls, "소스가 없으면 read_excel에 진입하지 않아야 한다"

        # 소스가 없어도 종목 자체는 삽입되고, market_cap만 NULL이어야 한다
        row = conn.execute(
            "SELECT code, market_cap FROM stock_meta WHERE code = '005930'"
        ).fetchone()
        assert row is not None, "시가총액 소스가 없어도 종목은 삽입되어야 한다"
        assert row[1] is None, (
            "basic_data.xlsx가 없으면 market_cap은 NULL이어야 한다"
        )
