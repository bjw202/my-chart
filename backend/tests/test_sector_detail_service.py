"""sector_detail_service 풍부화 기능 테스트.

TDD RED 단계: 스키마 및 서비스 변경 전에 먼저 작성.
인메모리 SQLite를 사용하여 외부 의존성 없이 실행 가능.
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from backend.services.sector_detail_service import get_sector_detail


# ---------------------------------------------------------------------------
# 주봉 DB 픽스처 (REQ-SAG-023/AC-SAG-025 — 주봉 Weinstein 분류기 단일화)
# ---------------------------------------------------------------------------

_WEEKLY_DDL = """
CREATE TABLE IF NOT EXISTS stock_prices (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
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
)
"""

_RS_DDL = """
CREATE TABLE IF NOT EXISTS relative_strength (
    Name TEXT NOT NULL,
    Date TEXT NOT NULL,
    RS_12M_Rating REAL,
    PRIMARY KEY (Name, Date)
)
"""

_WEEKLY_DATE = "2026-08-07"


def _make_weekly_row(
    name: str,
    close: float,
    sma10: float | None,
    sma40: float | None,
    sma40_trend_4m: float | None = None,
) -> tuple:
    """32-컬럼 주봉 row. `SMA40_Trend_4M` 이 slope 산출용 4주 전 SMA40 값이다."""
    return (
        name, _WEEKLY_DATE,
        close * 0.99, close * 1.01, close * 0.98, close,
        1_000_000.0, 800_000.0,
        0.02, 0.05, 0.08, 0.12, 0.20, 0.25, 0.30,
        sma10, 92.0, sma40,
        sma40_trend_4m, None, None, sma40_trend_4m,
        close * 1.05, close * 1.2, close * 0.7, close - close * 0.7,
        50.0, 55.0, 60.0, 65.0, 70.0, 75.0, 1.1,
    )


def _create_weekly_db(rows: list[tuple], rs_ratings: dict[str, float] | None = None) -> str:
    """주봉 DB(+ relative_strength) 임시 파일 생성. REQ-SAG-023 stage_map 소스."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute(_WEEKLY_DDL)
    conn.execute(_RS_DDL)
    conn.executemany(
        "INSERT INTO stock_prices VALUES (" + ",".join("?" * 33) + ")", rows)
    for name, rating in (rs_ratings or {}).items():
        conn.execute(
            "INSERT INTO relative_strength VALUES (?, ?, ?)",
            (name, _WEEKLY_DATE, rating))
    conn.commit()
    conn.close()
    return tmp.name


# ---------------------------------------------------------------------------
# 테스트용 DB 픽스처
# ---------------------------------------------------------------------------

def _create_test_db(rows: list[tuple]) -> str:
    """임시 SQLite 파일 생성. rows: (code, name, sector_major, sector_minor, rs_12m, close, sma50, sma200, chg_1m)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    conn.execute(
        """
        CREATE TABLE stock_meta (
            code TEXT,
            name TEXT,
            sector_major TEXT,
            sector_minor TEXT,
            rs_12m REAL,
            close REAL,
            sma50 REAL,
            sma200 REAL,
            chg_1m REAL
        )
        """
    )
    conn.executemany(
        "INSERT INTO stock_meta VALUES (?,?,?,?,?,?,?,?,?)",
        rows,
    )
    conn.commit()
    conn.close()
    return tmp.name


# ---------------------------------------------------------------------------
# 테스트 데이터: IT 섹터 3종목
# code, name, sector_major, sector_minor, rs_12m, close, sma50, sma200, chg_1m
# ---------------------------------------------------------------------------

_IT_ROWS = [
    # 소프트웨어 - Stage 2 (close > sma50 > sma200)
    ("A001", "알파", "IT", "소프트웨어", 80.0, 120.0, 100.0, 80.0, 5.0),
    # 소프트웨어 - Stage 4 (close < sma50 and close < sma200)
    ("A002", "베타", "IT", "소프트웨어", 60.0, 50.0, 80.0, 90.0, -3.0),
    # 하드웨어 - Stage 2 (close > sma50 > sma200)
    ("A003", "감마", "IT", "하드웨어", 90.0, 200.0, 180.0, 150.0, 10.0),
]


# ---------------------------------------------------------------------------
# test_sub_sector_rs_avg — 소그룹 평균 RS 계산 검증
# ---------------------------------------------------------------------------

def test_sub_sector_rs_avg() -> None:
    """SubSectorItem.rs_avg 값이 소그룹 내 rs_12m 평균으로 계산되어야 한다."""
    db_path = _create_test_db(_IT_ROWS)
    result = get_sector_detail(db_path, "IT")

    # 소프트웨어: (80 + 60) / 2 = 70.0
    sw = next(s for s in result.sub_sectors if s.name == "소프트웨어")
    assert abs(sw.rs_avg - 70.0) < 0.01, f"소프트웨어 rs_avg={sw.rs_avg}, 기대값=70.0"

    # 하드웨어: 90.0 / 1 = 90.0
    hw = next(s for s in result.sub_sectors if s.name == "하드웨어")
    assert abs(hw.rs_avg - 90.0) < 0.01, f"하드웨어 rs_avg={hw.rs_avg}, 기대값=90.0"


# ---------------------------------------------------------------------------
# test_sub_sector_stage2_pct — Stage 2 비율 계산 검증
# ---------------------------------------------------------------------------

def test_sub_sector_stage2_pct() -> None:
    """SubSectorItem.stage2_pct — 주봉 Weinstein 분류기(REQ-SAG-023) 기준.

    소프트웨어: 알파(Stage 2 Strong) + 베타(Stage 4) → 1/2 = 50%.
    하드웨어: 감마(Stage 2 Strong) → 1/1 = 100%.
    """
    db_path = _create_test_db(_IT_ROWS)
    weekly_db_path = _create_weekly_db([
        _make_weekly_row("알파", close=120.0, sma10=100.0, sma40=80.0, sma40_trend_4m=78.0),
        _make_weekly_row("베타", close=50.0, sma10=80.0, sma40=90.0, sma40_trend_4m=95.0),
        _make_weekly_row("감마", close=200.0, sma10=180.0, sma40=150.0, sma40_trend_4m=145.0),
    ], rs_ratings={"알파": 80.0, "베타": 60.0, "감마": 90.0})
    result = get_sector_detail(db_path, "IT", weekly_db_path=weekly_db_path)

    sw = next(s for s in result.sub_sectors if s.name == "소프트웨어")
    assert abs(sw.stage2_pct - 50.0) < 0.01, f"소프트웨어 stage2_pct={sw.stage2_pct}, 기대값=50.0"

    hw = next(s for s in result.sub_sectors if s.name == "하드웨어")
    assert abs(hw.stage2_pct - 100.0) < 0.01, f"하드웨어 stage2_pct={hw.stage2_pct}, 기대값=100.0"


def test_sub_sector_stage2_pct_excludes_unclassified_from_denominator() -> None:
    """AC-SAG-026 — SMA40/SMA10 결측 종목은 stage2_pct 분모에서 제외(0 치환 금지)."""
    db_path = _create_test_db(_IT_ROWS)
    weekly_db_path = _create_weekly_db([
        _make_weekly_row("알파", close=120.0, sma10=100.0, sma40=80.0, sma40_trend_4m=78.0),
        _make_weekly_row("베타", close=50.0, sma10=None, sma40=None),  # 분류 불가
        _make_weekly_row("감마", close=200.0, sma10=180.0, sma40=150.0, sma40_trend_4m=145.0),
    ], rs_ratings={"알파": 80.0, "베타": 60.0, "감마": 90.0})
    result = get_sector_detail(db_path, "IT", weekly_db_path=weekly_db_path)

    # 소프트웨어: 알파(Stage 2) + 베타(분류 불가, 분모 제외) → 1/1 = 100% (2 종목 중 분모 1)
    sw = next(s for s in result.sub_sectors if s.name == "소프트웨어")
    assert sw.stock_count == 2, "stock_count 는 여전히 전체 종목 수(분류 불가 포함)"
    assert abs(sw.stage2_pct - 100.0) < 0.01, (
        f"분류 불가 종목이 분모에 남았다: stage2_pct={sw.stage2_pct}, 기대값=100.0")


# ---------------------------------------------------------------------------
# test_top_stocks_chg_1m — chg_1m 필드 포함 검증
# ---------------------------------------------------------------------------

def test_top_stocks_chg_1m() -> None:
    """TopStockItem.chg_1m 값이 stock_meta.chg_1m 그대로 반환되어야 한다."""
    db_path = _create_test_db(_IT_ROWS)
    result = get_sector_detail(db_path, "IT")

    # top_stocks는 rs_12m DESC 정렬: A003(90), A001(80), A002(60)
    assert result.top_stocks[0].code == "A003"
    assert result.top_stocks[0].chg_1m == pytest.approx(10.0)

    assert result.top_stocks[1].code == "A001"
    assert result.top_stocks[1].chg_1m == pytest.approx(5.0)

    assert result.top_stocks[2].code == "A002"
    assert result.top_stocks[2].chg_1m == pytest.approx(-3.0)


# ---------------------------------------------------------------------------
# test_top_stocks_stage — stage 및 stage_detail 분류 검증
# ---------------------------------------------------------------------------

def test_top_stocks_stage() -> None:
    """TopStockItem.stage / stage_detail — 주봉 Weinstein 분류기(REQ-SAG-023) 기준."""
    db_path = _create_test_db(_IT_ROWS)
    weekly_db_path = _create_weekly_db([
        _make_weekly_row("알파", close=120.0, sma10=100.0, sma40=80.0, sma40_trend_4m=78.0),
        _make_weekly_row("베타", close=50.0, sma10=80.0, sma40=90.0, sma40_trend_4m=95.0),
        _make_weekly_row("감마", close=200.0, sma10=180.0, sma40=150.0, sma40_trend_4m=145.0),
    ], rs_ratings={"알파": 80.0, "베타": 60.0, "감마": 90.0})
    result = get_sector_detail(db_path, "IT", weekly_db_path=weekly_db_path)

    a003 = next(s for s in result.top_stocks if s.code == "A003")  # 감마
    assert a003.stage == 2
    assert a003.stage_detail is not None and "Stage 2" in a003.stage_detail

    a001 = next(s for s in result.top_stocks if s.code == "A001")  # 알파
    assert a001.stage == 2

    a002 = next(s for s in result.top_stocks if s.code == "A002")  # 베타
    assert a002.stage == 4
    assert a002.stage_detail is not None and "Stage 4" in a002.stage_detail


def test_top_stocks_stage_none_when_weekly_db_absent() -> None:
    """weekly_db_path 미제공 시 stage=None(분류 불가) — 일봉 근사 폐기(REQ-SAG-023)."""
    db_path = _create_test_db(_IT_ROWS)
    result = get_sector_detail(db_path, "IT")

    assert all(s.stage is None for s in result.top_stocks)


# ---------------------------------------------------------------------------
# test_empty_sector — 빈 섹터 처리 검증
# ---------------------------------------------------------------------------

def test_empty_sector() -> None:
    """존재하지 않는 섹터는 빈 리스트를 반환해야 한다."""
    db_path = _create_test_db(_IT_ROWS)
    result = get_sector_detail(db_path, "존재하지않는섹터")

    assert result.sector_name == "존재하지않는섹터"
    assert result.sub_sectors == []
    assert result.top_stocks == []


# ---------------------------------------------------------------------------
# test_null_price_fields — 가격 데이터 누락 시 stage=None 처리
# ---------------------------------------------------------------------------

def test_null_price_fields() -> None:
    """close/sma50/sma200 이 NULL 인 종목은 stage=None, chg_1m=None 이어야 한다."""
    rows = [
        ("B001", "델타", "헬스케어", "의약품", 70.0, None, None, None, None),
    ]
    db_path = _create_test_db(rows)
    result = get_sector_detail(db_path, "헬스케어")

    assert len(result.top_stocks) == 1
    stock = result.top_stocks[0]
    assert stock.stage is None
    assert stock.chg_1m is None


# ---------------------------------------------------------------------------
# AC-SAG-025 — fixture_stage_divergent: 두 분류기가 서로 다른 답을 내는 3케이스.
# GREEN(단일화 구현) 전에 이 픽스처가 실제로 구 분류기와 주봉 분류기를 **분기**
# 시킴을 실증했다(progress.md §E.2 M5 참조 — 되돌림 실증 절차).
# ---------------------------------------------------------------------------

def _old_daily_classify(close: float, sma50: float, sma200: float) -> int:
    """폐기된 `_classify_stage_simple` 의 재현(대조 전용, 프로덕션에서는 삭제됨)."""
    if close < sma50 and close < sma200:
        return 4
    elif close > sma50 and close > sma200 and sma50 > sma200:
        return 2
    elif close > sma200:
        return 2
    else:
        return 3


def test_fixture_stage_divergent_c1_uptrend_daily_vs_downtrend_weekly() -> None:
    """C1 — 일봉 상승 배열(→ 구 분류기 2) vs 주봉 SMA40 하락 추세 + RS 낮음(→ 1 또는 4)."""
    from my_chart.analysis.stage_classifier import classify_stage_or_none

    old = _old_daily_classify(close=110.0, sma50=100.0, sma200=90.0)
    assert old == 2, "C1 전제 위반 — 구 분류기가 2 를 내지 않는다"

    weekly_row = {
        "Name": "C1", "Close": 70.0, "SMA10": 100.0, "SMA40": 90.0,
        "SMA40_slope": -0.02,  # SMA40 하락 추세
        "RS_12M_Rating": 20.0,  # RS 낮음
        "CHG_1M": 0.0, "Volume": 100.0, "VolumeSMA10": 100.0,
    }
    new_stage, _ = classify_stage_or_none(weekly_row)
    assert new_stage in (1, 4), f"C1 — 주봉 기대 stage {{1,4}}, 실제 {new_stage}"
    assert new_stage != old, "C1 — 되돌림 대조: 두 분류기가 실제로 분기해야 한다"


def test_fixture_stage_divergent_c2_downtrend_daily_vs_uptrend_weekly() -> None:
    """C2 — 일봉 하락 배열(→ 구 분류기 4) vs 주봉 골든크로스 + RS 높음(→ 2)."""
    from my_chart.analysis.stage_classifier import classify_stage_or_none

    old = _old_daily_classify(close=80.0, sma50=90.0, sma200=100.0)
    assert old == 4, "C2 전제 위반 — 구 분류기가 4 를 내지 않는다"

    weekly_row = {
        "Name": "C2", "Close": 120.0, "SMA10": 100.0, "SMA40": 90.0,
        "SMA40_slope": 0.02,  # SMA40 상승 추세
        "RS_12M_Rating": 75.0,  # RS 높음
        "CHG_1M": 0.0, "Volume": 100.0, "VolumeSMA10": 100.0,
    }
    new_stage, _ = classify_stage_or_none(weekly_row)
    assert new_stage == 2, f"C2 — 주봉 기대 stage 2, 실제 {new_stage}"
    assert new_stage != old, "C2 — 되돌림 대조: 두 분류기가 실제로 분기해야 한다"


def test_fixture_stage_divergent_c3_sma40_null_insufficient() -> None:
    """C3 — 일봉 상승 배열(→ 구 분류기 2) vs 주봉 SMA40 NULL(→ None + 분류 불가)."""
    from my_chart.analysis.stage_classifier import classify_stage_or_none

    old = _old_daily_classify(close=110.0, sma50=100.0, sma200=90.0)
    assert old == 2, "C3 전제 위반 — 구 분류기가 2 를 내지 않는다"

    weekly_row = {
        "Name": "C3", "Close": 110.0, "SMA10": 100.0, "SMA40": None,
        "SMA40_slope": 0.0, "RS_12M_Rating": 50.0,
        "CHG_1M": 0.0, "Volume": 100.0, "VolumeSMA10": 100.0,
    }
    new_stage, new_detail = classify_stage_or_none(weekly_row)
    assert new_stage is None and new_detail is None, (
        f"C3 — 주봉 기대 (None, None), 실제 ({new_stage}, {new_detail})")
    assert new_stage != old, "C3 — 되돌림 대조: 두 분류기가 실제로 분기해야 한다"


def test_ac_sag_025_no_three_input_daily_stage_classifier_in_module() -> None:
    """행동 단언(이름 변경 내성) — close/sma50/sma200 3입력만으로 stage 를 산출하는
    호출 가능 객체가 모듈에 존재하지 않는다. rename 으로는 회피되지 않는다."""
    import inspect

    from backend.services import sector_detail_service as mod

    for attr_name in dir(mod):
        if attr_name.startswith("__"):
            continue
        attr = getattr(mod, attr_name)
        if not callable(attr) or not inspect.isfunction(attr):
            continue
        if inspect.getmodule(attr) is not mod:
            continue  # 재-export 된 외부 심볼(import) 은 대상이 아니다
        try:
            params = list(inspect.signature(attr).parameters)
        except (TypeError, ValueError):
            continue
        three_input_daily_shape = {"close", "sma50", "sma200"}
        assert set(params) != three_input_daily_shape, (
            f"모듈에 3입력 일봉 근사 stage 분류기가 남아있다(rename 회피): {attr_name}{params}")


def test_ac_sag_025_static_scan_no_daily_stage_classifier_source() -> None:
    """정적 스캔(보조) — `def .*stage` / `sma200` 패턴이 소스에 남아있지 않다."""
    import re
    from pathlib import Path

    src = Path("backend/services/sector_detail_service.py").read_text(encoding="utf-8")
    # 주석(@MX:NOTE 등)의 참조는 예외 — 실제 코드 라인만 스캔한다.
    code_lines = [
        line for line in src.splitlines()
        if not line.strip().startswith("#")
    ]
    matches = [
        line for line in code_lines
        if re.search(r"def .*stage|sma200", line)
    ]
    assert matches == [], f"일봉 근사 분류기 흔적이 소스에 남아있다: {matches}"
