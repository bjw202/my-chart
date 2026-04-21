"""SPEC-MINERVINI-001: Mark Minervini Trend Template 스크리너 테스트.

TDD RED 단계: 구현 전에 먼저 작성한 테스트.
그룹 A: rolling 계산 단위 테스트
그룹 B: meta_service 멱등 ALTER 테스트
그룹 C: screen_service WHERE + 점수 테스트
그룹 D: 회귀 테스트
그룹 E: Defense path (레거시 DB 누락 컬럼) 테스트
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

# ---------------------------------------------------------------------------
# 공통 픽스처 헬퍼
# ---------------------------------------------------------------------------


def _create_legacy_meta_db(tmp_path: Path) -> str:
    """신규 컬럼 없는 레거시 stock_meta DB 생성 (Group E 테스트용)."""
    db_path = str(tmp_path / "legacy.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
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
            last_updated TEXT
        );
    """)
    # 레거시 DB에 샘플 데이터 추가 (sma150, low52w, sma200_20d_ago 컬럼 없음)
    conn.execute("""
        INSERT INTO stock_meta VALUES (
            '005930', '삼성전자', 'KOSPI', 5000000000000,
            '전기전자', 'IT', NULL,
            70000, 0.5, 68000, 67000, 65000, 60000, 55000,
            80000, 0.02, 0.05, 0.10, 75.0,
            64000, 66000, 68000, '2026-04-01'
        )
    """)
    conn.commit()
    conn.close()
    return db_path


def _create_full_meta_db(tmp_path: Path) -> str:
    """신규 컬럼 포함한 완전한 stock_meta DB 생성 (Group C/D 테스트용).

    S1~S8: T1~T8 조건을 각각 하나씩 실패
    S9: 8조건 모두 통과
    S10: 8조건 모두 실패
    """
    db_path = str(tmp_path / "full.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
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
        );
    """)

    # 기본 통과 값 (S9 기준)
    # 8조건:
    # T1: close > sma150 AND close > sma200       -> close=100, sma150=80, sma200=70
    # T2: sma150 > sma200                          -> sma150=80 > sma200=70
    # T3: sma200 > sma200_20d_ago                  -> sma200=70 > sma200_20d_ago=60
    # T4: sma50 > sma150 AND sma50 > sma200        -> sma50=90, sma150=80, sma200=70
    # T5: close > sma50                            -> close=100 > sma50=90
    # T6: close >= low52w * 1.25                   -> low52w=50, 50*1.25=62.5, close=100 >= 62.5 OK
    # T7: close >= high52w*0.75 AND close<=high52w -> high52w=110, 110*0.75=82.5, close=100 in [82.5,110]
    # T8: rs_12m >= 70                             -> rs_12m=75

    base = {
        "market": "KOSPI",
        "market_cap": 1000000000000,
        "sector_major": "전기전자",
        "sector_minor": "IT",
        "product": None,
        "change_1d": 0.5,
        "ema10": 98.0,
        "ema20": 97.0,
        "sma50": 90.0,
        "sma100": 85.0,
        "sma200": 70.0,
        "high52w": 110.0,
        "chg_1w": 0.02,
        "chg_1m": 0.05,
        "chg_3m": 0.10,
        "rs_12m": 75.0,
        "sma10_w": None,
        "sma20_w": None,
        "sma40_w": None,
        "last_updated": "2026-04-21",
        "sma150": 80.0,
        "low52w": 50.0,
        "sma200_20d_ago": 60.0,
        # close=100: T1(100>80,100>70), T2(80>70), T3(70>60), T4(90>80,90>70),
        #            T5(100>90), T6(100>=62.5), T7(100>=82.5,100<=110), T8(75>=70)
        "close": 100.0,
    }

    def make_row(code: str, name: str, overrides: dict) -> tuple:
        d = {**base, **overrides}
        return (
            code, name, d["market"], d["market_cap"],
            d["sector_major"], d["sector_minor"], d["product"],
            d["close"], d["change_1d"],
            d["ema10"], d["ema20"], d["sma50"], d["sma100"], d["sma200"],
            d["high52w"], d["chg_1w"], d["chg_1m"], d["chg_3m"], d["rs_12m"],
            d["sma10_w"], d["sma20_w"], d["sma40_w"], d["last_updated"],
            d["sma150"], d["low52w"], d["sma200_20d_ago"],
        )

    rows = [
        # S1: T1 실패 — close <= sma150 (close=75, sma150=80, sma200=70 → close NOT > sma150)
        make_row("S01001", "S1_T1실패", {"close": 75.0}),
        # S2: T2 실패 — sma150 <= sma200 (sma150=65, sma200=70)
        make_row("S02001", "S2_T2실패", {"sma150": 65.0}),
        # S3: T3 실패 — sma200 <= sma200_20d_ago (sma200=70, sma200_20d_ago=75)
        make_row("S03001", "S3_T3실패", {"sma200_20d_ago": 75.0}),
        # S4: T4 실패 — sma50 <= sma150 (sma50=75, sma150=80)
        make_row("S04001", "S4_T4실패", {"sma50": 75.0}),
        # S5: T5 실패 — close <= sma50 (close=85, sma50=90)
        make_row("S05001", "S5_T5실패", {"close": 85.0, "sma150": 80.0}),
        # S6: T6 실패 — close < low52w * 1.25 (close=100, low52w=85 → 85*1.25=106.25 > 100)
        make_row("S06001", "S6_T6실패", {"low52w": 85.0}),
        # S7: T7 실패 — close > high52w (close=120, high52w=110)
        make_row("S07001", "S7_T7실패", {"close": 120.0, "high52w": 110.0}),
        # S8: T8 실패 — rs_12m < 70 (rs_12m=65)
        make_row("S08001", "S8_T8실패", {"rs_12m": 65.0}),
        # S9: 8조건 모두 통과
        make_row("S09001", "S9_전체통과", {}),
        # S10: 8조건 모두 실패
        make_row("S10001", "S10_전체실패", {
            "close": 50.0, "sma150": 80.0, "sma200": 70.0, "sma50": 40.0,
            "low52w": 90.0, "high52w": 45.0, "rs_12m": 20.0, "sma200_20d_ago": 75.0,
        }),
    ]

    conn.executemany(
        """INSERT INTO stock_meta VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# Group A: rolling 계산 단위 테스트
# ---------------------------------------------------------------------------


class TestGroupA_RollingCalculation:
    """Group A: rolling 계산 단위 테스트 (my_chart/db/daily.py의 _compute_minervini_indicators)."""

    def test_sma150_rolling_correctness(self):
        """AC-1: 150일 선형 Close 입력 → SMA150[149] == 174.5, SMA150[0..148] 모두 NaN."""
        from my_chart.db.daily import _compute_minervini_indicators

        # Close = [100, 101, ..., 249] (150개 값)
        close_values = list(range(100, 250))  # 100 ~ 249 (150개)
        df = pd.DataFrame({
            "Close": close_values,
            "High": close_values,
            "Low": close_values,
            "SMA200": [float("nan")] * 150,
        })
        result = _compute_minervini_indicators(df)

        # 149번째 인덱스(0-based)가 첫 유효값: mean(100..249) = (100+249)/2 = 174.5
        assert result["SMA150"].iloc[149] == pytest.approx(174.5)
        # 0..148 은 모두 NaN
        assert result["SMA150"].iloc[:149].isna().all()

    def test_sma150_insufficient_history_null(self):
        """100일 데이터 → 모든 SMA150 값이 NaN."""
        from my_chart.db.daily import _compute_minervini_indicators

        close_values = list(range(100, 200))  # 100개
        df = pd.DataFrame({
            "Close": close_values,
            "High": close_values,
            "Low": close_values,
            "SMA200": [float("nan")] * 100,
        })
        result = _compute_minervini_indicators(df)
        assert result["SMA150"].isna().all()

    def test_52w_rolling_high_low_correctness(self):
        """AC-2: 300일 High/Low → rolling 250 max/min 검증."""
        from my_chart.db.daily import _compute_minervini_indicators

        n = 300
        # High: 단순 증가 (0, 1, ..., 299)
        # Low: 단순 감소 (299, 298, ..., 0) — 반전
        high_values = list(range(n))
        low_values = list(range(n - 1, -1, -1))
        df = pd.DataFrame({
            "Close": high_values,
            "High": high_values,
            "Low": low_values,
            "SMA200": [float("nan")] * n,
        })
        result = _compute_minervini_indicators(df)

        # HIGH_52W[249] = max(High[0..249]) = 249
        assert result["HIGH_52W"].iloc[249] == pytest.approx(249.0)
        # LOW_52W[299] = min(Low[50..299]) = Low[299] = 0
        assert result["LOW_52W"].iloc[299] == pytest.approx(0.0)
        # 첫 249개는 NaN (min_periods=250)
        assert result["HIGH_52W"].iloc[:249].isna().all()
        assert result["LOW_52W"].iloc[:249].isna().all()

    def test_52w_ipo_under_250days_null(self):
        """150일 데이터 → HIGH_52W, LOW_52W 전부 NaN."""
        from my_chart.db.daily import _compute_minervini_indicators

        n = 150
        df = pd.DataFrame({
            "Close": list(range(n)),
            "High": list(range(n)),
            "Low": list(range(n)),
            "SMA200": [float("nan")] * n,
        })
        result = _compute_minervini_indicators(df)
        assert result["HIGH_52W"].isna().all()
        assert result["LOW_52W"].isna().all()

    def test_sma200_20d_ago_shift(self):
        """AC-3: SMA200 배열을 shift(20)과 동일하게 생성 — SMA200_20D_AGO[t] == SMA200[t-20]."""
        from my_chart.db.daily import _compute_minervini_indicators

        n = 50
        sma200_values = [float(i) for i in range(n)]
        df = pd.DataFrame({
            "Close": [100.0] * n,
            "High": [100.0] * n,
            "Low": [100.0] * n,
            "SMA200": sma200_values,
        })
        result = _compute_minervini_indicators(df)

        # SMA200_20D_AGO[t] == SMA200[t-20]
        for t in range(20, n):
            assert result["SMA200_20D_AGO"].iloc[t] == pytest.approx(sma200_values[t - 20])

    def test_sma200_20d_ago_null_for_short_history(self):
        """215일 데이터, SMA200 = None → SMA200_20D_AGO 전부 NaN.

        SMA200 자체가 모두 NaN이면 shift해도 NaN이 됨.
        """
        from my_chart.db.daily import _compute_minervini_indicators

        n = 215
        df = pd.DataFrame({
            "Close": [100.0] * n,
            "High": [100.0] * n,
            "Low": [100.0] * n,
            "SMA200": [float("nan")] * n,  # SMA200 미계산 상태
        })
        result = _compute_minervini_indicators(df)
        assert result["SMA200_20D_AGO"].isna().all()


# ---------------------------------------------------------------------------
# Group B: meta_service 멱등 ALTER 테스트
# ---------------------------------------------------------------------------


class TestGroupB_MetaServiceAlter:
    """Group B: meta_service 멱등 ALTER 및 스냅샷 복사 테스트."""

    def _create_minimal_prices_db(self, tmp_path: Path, stock_name: str = "TEST001") -> str:
        """최소한의 stock_prices 테이블을 포함한 DB 생성 (신규 컬럼 포함)."""
        db_path = str(tmp_path / "test_daily.db")
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE stock_prices (
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
                SMA150 REAL,
                LOW_52W REAL,
                SMA200_20D_AGO REAL,
                PRIMARY KEY (Name, Date)
            );
            CREATE TABLE relative_strength (
                Name TEXT,
                Date TEXT,
                RS_12M_Rating REAL
            );
        """)
        # 2개 날짜의 데이터 삽입 (최신 날짜의 신규 컬럼 값 확인용)
        conn.executemany(
            """INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (stock_name, "2026-04-20",
                 10000, 10200, 9800, 10100,  # Open/High/Low/Close
                 0.01, 11000,  # Change, High52W
                 500000, 480000, 5050,  # Volume/Volume20MA/VolumeWon
                 10050, 10030, 10000, 9800, 9900, 9500, 9200,  # EMAs/SMAs
                 2.0, 10033.3,  # DailyRange, HLC
                 0.5, 0.7, 3.1, 9.8,  # From...
                 2.0, 1.9,  # Range, ADR20
                 None,  # RS_Line
                 7800.0,  # SMA150
                 6000.0,  # LOW_52W
                 9000.0),  # SMA200_20D_AGO
                (stock_name, "2026-04-21",
                 10100, 10300, 9900, 10200,
                 0.01, 11200,
                 510000, 490000, 5151,
                 10150, 10130, 10100, 9900, 10000, 9600, 9300,
                 2.0, 10133.3,
                 0.5, 0.7, 3.1, 9.8,
                 2.0, 1.9,
                 None,
                 7900.0,  # SMA150 (최신)
                 6100.0,  # LOW_52W (최신)
                 9100.0),  # SMA200_20D_AGO (최신)
            ]
        )
        conn.commit()

        # RS 데이터
        conn.execute(
            "INSERT INTO relative_strength VALUES (?,?,?)",
            (stock_name, "2026-04-21", 72.5)
        )
        conn.commit()
        conn.close()
        return db_path

    def _create_legacy_prices_db(self, tmp_path: Path, stock_name: str = "TEST001") -> str:
        """신규 컬럼 없는 레거시 stock_prices DB."""
        db_path = str(tmp_path / "legacy_daily.db")
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE stock_prices (
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
            );
            CREATE TABLE relative_strength (
                Name TEXT,
                Date TEXT,
                RS_12M_Rating REAL
            );
        """)
        conn.execute(
            """INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (stock_name, "2026-04-21",
             10000, 10200, 9800, 10100,
             0.01, 11000,
             500000, 480000, 5050,
             10050, 10030, 10000, 9800, 9900, 9500, 9200,
             2.0, 10033.3,
             0.5, 0.7, 3.1, 9.8,
             2.0, 1.9,
             None)
        )
        conn.execute(
            "INSERT INTO relative_strength VALUES (?,?,?)",
            (stock_name, "2026-04-21", 68.0)
        )
        conn.commit()
        conn.close()
        return db_path

    def _create_weekly_db(self, tmp_path: Path, stock_name: str = "TEST001") -> str:
        """최소한의 weekly DB 생성."""
        db_path = str(tmp_path / "test_weekly.db")
        conn = sqlite3.connect(db_path)
        conn.executescript("""
            CREATE TABLE stock_prices (
                Name TEXT NOT NULL,
                Date TEXT NOT NULL,
                CHG_1W REAL, CHG_1M REAL, CHG_3M REAL,
                SMA10 REAL, SMA20 REAL, SMA40 REAL,
                PRIMARY KEY (Name, Date)
            );
            CREATE TABLE relative_strength (
                Name TEXT,
                Date TEXT,
                RS_12M_Rating REAL,
                PRIMARY KEY (Name, Date)
            );
        """)
        conn.execute(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?)",
            (stock_name, "2026-04-21", 0.02, 0.05, 0.10, 9800.0, 9700.0, 9500.0)
        )
        conn.execute(
            "INSERT INTO relative_strength VALUES (?,?,?)",
            (stock_name, "2026-04-21", 72.5)
        )
        conn.commit()
        conn.close()
        return db_path

    def test_meta_alter_adds_missing_columns(self, tmp_path: pytest.TempPathFactory):
        """레거시 stock_prices + stock_meta (신규 컬럼 없음) → rebuild 후 sma150/low52w/sma200_20d_ago 존재."""
        from unittest.mock import patch

        from my_chart.config import REFERENCE_STOCK

        daily_db = self._create_legacy_prices_db(tmp_path, stock_name=REFERENCE_STOCK)
        weekly_db = self._create_weekly_db(tmp_path, stock_name=REFERENCE_STOCK)

        with patch("backend.services.meta_service.get_sector_registry") as mock_sector:
            import pandas as pd
            mock_sector.return_value = pd.DataFrame([{
                "Name": REFERENCE_STOCK,
                "Code": "000001",
                "Market": "KOSPI",
                "산업명(대)": "전기전자",
                "산업명(중)": "IT",
                "주요제품": "반도체",
            }])
            from backend.services.meta_service import rebuild_stock_meta
            rebuild_stock_meta(daily_db, weekly_db)

        conn = sqlite3.connect(daily_db)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(stock_meta)").fetchall()}
        conn.close()

        assert "sma150" in cols
        assert "low52w" in cols
        assert "sma200_20d_ago" in cols

    def test_meta_alter_idempotent(self, tmp_path: pytest.TempPathFactory):
        """rebuild_stock_meta 두 번 호출 → 컬럼 중복 없음."""
        from unittest.mock import patch

        from my_chart.config import REFERENCE_STOCK

        daily_db = self._create_legacy_prices_db(tmp_path, stock_name=REFERENCE_STOCK)
        weekly_db = self._create_weekly_db(tmp_path, stock_name=REFERENCE_STOCK)

        with patch("backend.services.meta_service.get_sector_registry") as mock_sector:
            import pandas as pd
            mock_sector.return_value = pd.DataFrame([{
                "Name": REFERENCE_STOCK,
                "Code": "000001",
                "Market": "KOSPI",
                "산업명(대)": "전기전자",
                "산업명(중)": "IT",
                "주요제품": "반도체",
            }])
            from backend.services.meta_service import rebuild_stock_meta
            # 두 번 연속 호출
            rebuild_stock_meta(daily_db, weekly_db)
            rebuild_stock_meta(daily_db, weekly_db)

        conn = sqlite3.connect(daily_db)
        all_cols = [row[1] for row in conn.execute("PRAGMA table_info(stock_meta)").fetchall()]
        conn.close()

        # 각 컬럼이 정확히 1회만 존재해야 함
        assert all_cols.count("sma150") == 1
        assert all_cols.count("low52w") == 1
        assert all_cols.count("sma200_20d_ago") == 1

    def test_meta_latest_value_copied(self, tmp_path: pytest.TempPathFactory):
        """최신 일봉 행의 SMA150/LOW_52W/SMA200_20D_AGO 값이 stock_meta로 복사됨."""
        from unittest.mock import patch

        from my_chart.config import REFERENCE_STOCK

        daily_db = self._create_minimal_prices_db(tmp_path, stock_name=REFERENCE_STOCK)
        weekly_db = self._create_weekly_db(tmp_path, stock_name=REFERENCE_STOCK)

        with patch("backend.services.meta_service.get_sector_registry") as mock_sector:
            import pandas as pd
            mock_sector.return_value = pd.DataFrame([{
                "Name": REFERENCE_STOCK,
                "Code": "000001",
                "Market": "KOSPI",
                "산업명(대)": "전기전자",
                "산업명(중)": "IT",
                "주요제품": "반도체",
            }])
            from backend.services.meta_service import rebuild_stock_meta
            rebuild_stock_meta(daily_db, weekly_db)

        conn = sqlite3.connect(daily_db)
        row = conn.execute(
            "SELECT sma150, low52w, sma200_20d_ago FROM stock_meta WHERE code = '000001'"
        ).fetchone()
        conn.close()

        # 최신 날짜(2026-04-21)의 값이 복사되어야 함
        assert row is not None
        assert row[0] == pytest.approx(7900.0)  # sma150
        assert row[1] == pytest.approx(6100.0)  # low52w
        assert row[2] == pytest.approx(9100.0)  # sma200_20d_ago


# ---------------------------------------------------------------------------
# Group C: screen_service WHERE + 점수 테스트
# ---------------------------------------------------------------------------


class TestGroupC_ScreenService:
    """Group C: screen_service WHERE + 점수 (strict gate) 테스트."""

    def test_minervini_where_all_conditions_met(self, tmp_path: pytest.TempPathFactory):
        """S9 (8조건 모두 통과) → 결과에 포함, trend_template_score == 8."""
        from backend.schemas.screen import ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_full_meta_db(tmp_path)
        req = ScreenRequest(minervini_trend_template=True)
        resp = screen_stocks(req, db_path)

        codes = [item.code for sg in resp.sectors for item in sg.stocks]
        assert "S09001" in codes, f"S9가 결과에 없음. 결과: {codes}"

        s9_item = next(item for sg in resp.sectors for item in sg.stocks if item.code == "S09001")
        assert s9_item.trend_template_score == 8

    @pytest.mark.parametrize("failing_code,failing_name", [
        ("S01001", "S1_T1실패"),
        ("S02001", "S2_T2실패"),
        ("S03001", "S3_T3실패"),
        ("S04001", "S4_T4실패"),
        ("S05001", "S5_T5실패"),
        ("S06001", "S6_T6실패"),
        ("S07001", "S7_T7실패"),
        ("S08001", "S8_T8실패"),
    ])
    def test_minervini_where_each_boundary_case(
        self, tmp_path: pytest.TempPathFactory, failing_code: str, failing_name: str
    ):
        """S1~S8 각각 조건 하나씩 실패 → 결과에서 제외 (strict gate)."""
        from backend.schemas.screen import ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_full_meta_db(tmp_path)
        req = ScreenRequest(minervini_trend_template=True)
        resp = screen_stocks(req, db_path)

        codes = [item.code for sg in resp.sectors for item in sg.stocks]
        assert failing_code not in codes, f"{failing_name}({failing_code})이 결과에 포함됨"

    def test_trend_template_score_is_8_for_all_returned_rows(self, tmp_path: pytest.TempPathFactory):
        """strict gate: 응답의 모든 StockItem에서 trend_template_score == 8."""
        from backend.schemas.screen import ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_full_meta_db(tmp_path)
        req = ScreenRequest(minervini_trend_template=True)
        resp = screen_stocks(req, db_path)

        all_items = [item for sg in resp.sectors for item in sg.stocks]
        assert len(all_items) > 0, "결과가 비어 있음 (S9가 통과해야 함)"
        for item in all_items:
            assert item.trend_template_score == 8, f"{item.code}의 score={item.trend_template_score}"

    def test_trend_template_score_none_when_flag_off(self, tmp_path: pytest.TempPathFactory):
        """minervini_trend_template=False/None → trend_template_score == None."""
        from backend.schemas.screen import ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_full_meta_db(tmp_path)

        for flag in [False, None]:
            req = ScreenRequest(minervini_trend_template=flag)
            resp = screen_stocks(req, db_path)
            for sg in resp.sectors:
                for item in sg.stocks:
                    assert item.trend_template_score is None, (
                        f"flag={flag}일 때 {item.code}의 score={item.trend_template_score}"
                    )

    def test_minervini_with_existing_filters_combined(self, tmp_path: pytest.TempPathFactory):
        """market_cap_min + minervini=True AND 결합 동작."""
        from backend.schemas.screen import ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_full_meta_db(tmp_path)
        # 시가총액 5000억 이상 AND minervini=True
        # S9의 market_cap = 1000000000000 (1조) → 통과 (5000억 = 500000000000)
        req = ScreenRequest(
            market_cap_min=5000,  # 5000 억원
            minervini_trend_template=True,
        )
        resp = screen_stocks(req, db_path)
        codes = [item.code for sg in resp.sectors for item in sg.stocks]
        assert "S09001" in codes


# ---------------------------------------------------------------------------
# Group D: 회귀 테스트
# ---------------------------------------------------------------------------


class TestGroupD_Regression:
    """Group D: 기존 필터 불변성 회귀 테스트."""

    def test_existing_chg_filters_unchanged(self, tmp_path: pytest.TempPathFactory):
        """chg_1w/1m/3m 필터 — minervini 플래그 없이 동일한 결과 반환."""
        from backend.schemas.screen import ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_full_meta_db(tmp_path)

        # chg_1w_min 필터 (1주 수익률 >= 3% = 0.03)
        req = ScreenRequest(chg_1w_min=1.0)  # 1% 이상 (1주 수익률 > 1%)
        resp = screen_stocks(req, db_path)

        # 결과가 반환되어야 하며 minervini 필드는 None이어야 함
        all_items = [item for sg in resp.sectors for item in sg.stocks]
        for item in all_items:
            assert item.trend_template_score is None

    def test_existing_patterns_unchanged(self, tmp_path: pytest.TempPathFactory):
        """patterns[0..3개] — minervini 플래그 없이 기존과 동일 동작."""
        from backend.schemas.screen import PatternCondition, ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_full_meta_db(tmp_path)

        # Close > SMA50 패턴 (S9는 close=100 > sma50=90)
        req = ScreenRequest(
            patterns=[PatternCondition(
                indicator_a="Close",
                operator="gt",
                indicator_b="SMA50",
                multiplier=1.0,
            )]
        )
        resp = screen_stocks(req, db_path)
        codes = [item.code for sg in resp.sectors for item in sg.stocks]
        # S9는 Close(100) > SMA50(90) 이므로 포함되어야 함
        assert "S09001" in codes
        # 모든 결과의 trend_template_score는 None
        for sg in resp.sectors:
            for item in sg.stocks:
                assert item.trend_template_score is None

    def test_patterns_max_length_5_accepts_4_or_5(self):
        """Pydantic이 4개, 5개 PatternCondition을 허용 (기존 3개도 허용)."""
        from backend.schemas.screen import PatternCondition, ScreenRequest

        cond = PatternCondition(
            indicator_a="Close", operator="gt", indicator_b="SMA50", multiplier=1.0
        )

        # 4개 허용
        req4 = ScreenRequest(patterns=[cond] * 4)
        assert len(req4.patterns) == 4

        # 5개 허용
        req5 = ScreenRequest(patterns=[cond] * 5)
        assert len(req5.patterns) == 5

    def test_patterns_max_length_5_rejects_6(self):
        """Pydantic이 6개 PatternCondition을 거부 (ValidationError)."""
        from backend.schemas.screen import PatternCondition, ScreenRequest

        cond = PatternCondition(
            indicator_a="Close", operator="gt", indicator_b="SMA50", multiplier=1.0
        )

        with pytest.raises(ValidationError):
            ScreenRequest(patterns=[cond] * 6)


# ---------------------------------------------------------------------------
# Group E: Defense path 테스트
# ---------------------------------------------------------------------------


class TestGroupE_DefensePath:
    """Group E: 레거시 DB 누락 컬럼 방어 경로 테스트."""

    def test_defense_missing_columns_returns_200_empty(self, tmp_path: pytest.TempPathFactory):
        """레거시 stock_meta (신규 컬럼 없음) + minervini=True → ScreenResponse(total=0, sectors=[])."""
        from backend.schemas.screen import ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_legacy_meta_db(tmp_path)
        req = ScreenRequest(minervini_trend_template=True)
        resp = screen_stocks(req, db_path)

        assert resp.total == 0
        assert resp.sectors == []

    def test_defense_warn_log_emitted_once(
        self, tmp_path: pytest.TempPathFactory, caplog: pytest.LogCaptureFixture
    ):
        """동일 요청에서 caplog으로 WARN 1회 확인 (로그 문구: '[minervini] required columns missing')."""
        from backend.schemas.screen import ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_legacy_meta_db(tmp_path)
        req = ScreenRequest(minervini_trend_template=True)

        with caplog.at_level(logging.WARNING, logger="backend.services.screen_service"):
            screen_stocks(req, db_path)

        warn_msgs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warn_msgs) >= 1
        assert any("[minervini] required columns missing" in r.message for r in warn_msgs)

    def test_defense_other_filters_still_work(self, tmp_path: pytest.TempPathFactory):
        """레거시 DB + minervini=False + market_cap_min → 정상 결과 (기존 필터에 영향 없음)."""
        from backend.schemas.screen import ScreenRequest
        from backend.services.screen_service import screen_stocks

        db_path = _create_legacy_meta_db(tmp_path)
        # minervini=False, 시가총액 1000억 이상
        req = ScreenRequest(
            minervini_trend_template=False,
            market_cap_min=1000,  # 1000억원
        )
        resp = screen_stocks(req, db_path)

        # 레거시 DB에 삼성전자 데이터가 있음 (시가총액 5조 > 1000억)
        codes = [item.code for sg in resp.sectors for item in sg.stocks]
        assert "005930" in codes
