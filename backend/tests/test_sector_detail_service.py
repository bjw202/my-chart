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
    """SubSectorItem.stage2_pct 값이 Stage 2 종목 비율(%)로 계산되어야 한다.

    Stage 2 기준 (단순 헤리스틱):
      - close > sma50 > sma200
      - 또는 close > sma200 (Stage 2 Early)
    """
    db_path = _create_test_db(_IT_ROWS)
    result = get_sector_detail(db_path, "IT")

    # 소프트웨어: A001만 Stage 2 → 1/2 = 50%
    sw = next(s for s in result.sub_sectors if s.name == "소프트웨어")
    assert abs(sw.stage2_pct - 50.0) < 0.01, f"소프트웨어 stage2_pct={sw.stage2_pct}, 기대값=50.0"

    # 하드웨어: A003 Stage 2 → 1/1 = 100%
    hw = next(s for s in result.sub_sectors if s.name == "하드웨어")
    assert abs(hw.stage2_pct - 100.0) < 0.01, f"하드웨어 stage2_pct={hw.stage2_pct}, 기대값=100.0"


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
    """TopStockItem.stage 및 stage_detail 이 단순 헤리스틱으로 분류되어야 한다.

    Stage 2: close > sma50 > sma200  → stage=2, stage_detail="Stage 2"
    Stage 4: close < sma50 and close < sma200 → stage=4, stage_detail="Stage 4"
    """
    db_path = _create_test_db(_IT_ROWS)
    result = get_sector_detail(db_path, "IT")

    # A003: close=200 > sma50=180 > sma200=150 → Stage 2
    a003 = next(s for s in result.top_stocks if s.code == "A003")
    assert a003.stage == 2
    assert a003.stage_detail is not None and "Stage 2" in a003.stage_detail

    # A001: close=120 > sma50=100 > sma200=80 → Stage 2
    a001 = next(s for s in result.top_stocks if s.code == "A001")
    assert a001.stage == 2

    # A002: close=50 < sma50=80, close=50 < sma200=90 → Stage 4
    a002 = next(s for s in result.top_stocks if s.code == "A002")
    assert a002.stage == 4
    assert a002.stage_detail is not None and "Stage 4" in a002.stage_detail


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
