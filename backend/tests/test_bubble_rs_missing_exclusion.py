# coding: utf-8
"""SPEC-SECTOR-METRIC-UNIFY-001 M1 — RED: RS 결측 처리 계약(분모 8 / None) 합성 DB 단언.

M4 가 버블 rs_avg 의 결측 의미론을 "0 대체 → 가용 평균/None" 로 바꾸면 GREEN 이
되는 미래 계약 테스트. 현재 구현은 RS 결측 종목을 0 으로 대체해 **전체 구성종목수를
분모**로 쓰므로(M0 특성화 동일 기준 관측) RED 다.

대조군 설계 — 세 섹터는 "RS 행 존재" 축만 다르고 나머지(주 수·가격 공식·거래대금
공식·시장 구성)는 동일하다:
- 정상섹터   6종목, RS 전원 있음(평균 70.0)      → control: 현재도 GREEN
- 부분결측  10종목, 8종목만 RS 있음(평균 65.0)   → AC-SMU-007: 분모 8
- 전체결측   6종목, RS 전원 없음                  → AC-SMU-006/022: rs_avg None + 미탈락

수치 설계(0-대체와 가용-평균이 우연히 같아지는 항진명제 방어):
- 부분결측 가용 8개 합 520 → 분모 8 평균 65.0 / 0-대체 분모 10 평균 52.0 (엄격히 다름)
- 정상섹터 6개 합 420 → 평균 70.0 (어떤 분모든 동일 — control 이므로 문제없음)

M4 fixture 적응 — 신경로(``compute_sector_aggregates``)의 두 가지 입력 계약:
1. ``_load_weekly_snapshot`` 이 ``stock_prices.VolumeSMA10`` 컬럼을 참조한다(구경로
   ``compute_sector_bubble`` 은 Close·Volume·CHG·RS 만 읽었다).
2. 섹터 소속 원천이 주간 DB ``stock_meta``(구경로)에서 **registry**(UN-1 단일 원천,
   ``_load_registry_mapping``)로 바뀐다 — 합성 섹터명을 실 SECTORMAP 에 넣을 수
   없으므로 ``my_chart.analysis.sector_metrics.get_sector_registry`` 를 합성
   DataFrame 으로 패치한다.
"""
from __future__ import annotations

import sqlite3
import tempfile

import pytest

# 관용: backend/tests/test_sector_advanced.py:19-147 (_create_test_db) 와 동일한
# 테이블 스키마·12주 날짜 격자·KOSPI 지수 행 구조.
_BASE_DATES = [
    "2024-01-05", "2024-01-12", "2024-01-19", "2024-01-26",
    "2024-02-02", "2024-02-09", "2024-02-16", "2024-02-23",
    "2024-03-01", "2024-03-08", "2024-03-15", "2024-03-22",
]

# (섹터명, [종목명], {종목명: RS 값 — 없으면 RS 행 자체를 넣지 않는다})
_SECTOR_PLAN: list[tuple[str, list[str], dict[str, float]]] = [
    ("정상섹터",
     [f"정상{i}" for i in range(1, 7)],
     {f"정상{i}": v for i, v in
      zip(range(1, 7), (60.0, 64.0, 66.0, 72.0, 76.0, 82.0))}),  # 합 420 → 평균 70.0
    ("부분결측",
     [f"부분{i}" for i in range(1, 11)],
     {f"부분{i}": v for i, v in
      zip(range(1, 9), (50.0, 55.0, 60.0, 62.0, 65.0, 70.0, 76.0, 82.0))}),  # 합 520 → 분모 8 평균 65.0
    ("전체결측",
     [f"결측{i}" for i in range(1, 7)],
     {}),  # RS 행 전무 → rs_avg 는 None (AC-SMU-006), 탈락 금지 (AC-SMU-022)
]

_CONTROL_AVG = 70.0        # 정상섹터 — control (현재·M4 후 동일)
_PARTIAL_AVG_8 = 65.0      # 부분결측 — 가용 8개 평균 (AC-SMU-007 목표값)
_PARTIAL_AVG_SUB = 52.0    # 부분결측 — 0-대체 분모 10 평균 (현재값, 목표와 엄격히 다름)
TOL = 1e-9


def _create_synthetic_db() -> str:
    """RS 결측 시나리오 3종을 담은 합성 weekly DB 생성 (test_sector_advanced.py 관용)."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)

    conn.executescript("""
        CREATE TABLE stock_prices (
            Name TEXT, Date TEXT, Close REAL, Volume REAL,
            SMA10 REAL, SMA40 REAL, SMA40_Trend_4M REAL,
            CHG_1W REAL, CHG_1M REAL, CHG_3M REAL, MAX52 REAL,
            VolumeSMA10 REAL
        );
        CREATE TABLE relative_strength (
            Name TEXT, Date TEXT, RS_12M_Rating REAL
        );
    """)

    price_rows: list[tuple] = []
    rs_rows: list[tuple] = []

    # KOSPI 지수 행 (관용 — 초과수익률 벤치마크 입력)
    for i, date in enumerate(_BASE_DATES):
        close = 2500.0 + i * 10.0
        price_rows.append(("KOSPI", date, close, 5_000_000.0,
                           close * 0.98, close * 0.95, close * 0.93,
                           0.005 + i * 0.001, 0.015, 0.04, close * 1.05,
                           4_500_000.0))

    # 섹터별 종목 — 세 섹터 모두 동일한 가격 공식(축은 RS 존재뿐)
    for sector, names, rs_values in _SECTOR_PLAN:
        for j, name in enumerate(names):
            base_close = 50_000.0 + j * 10_000.0
            factor = 0.01 + j * 0.001
            for i, date in enumerate(_BASE_DATES):
                close = base_close * (1 + factor * i)
                chg_1w = factor * (1 + i * 0.1)
                price_rows.append((
                    name, date, close, 1_000_000.0 + i * 50_000,
                    close * 0.99, close * 0.97, close * 0.95,
                    chg_1w, chg_1w * 4, chg_1w * 12, close * 1.1,
                    900_000.0,
                ))
            # RS 축 — rs_values 에 없는 종목은 relative_strength 행을 아예 넣지 않는다.
            if name in rs_values:
                for date in _BASE_DATES:
                    rs_rows.append((name, date, rs_values[name]))

    conn.executemany("INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", price_rows)
    conn.executemany("INSERT INTO relative_strength VALUES (?,?,?)", rs_rows)
    conn.commit()
    conn.close()
    return tmp.name


def _synthetic_registry_df():
    """합성 섹터 매핑 DataFrame — UN-1 registry 계약(Name/산업명(대)/Market 컬럼)."""
    import pandas as pd

    rows = [
        {"Name": name, "산업명(대)": sector, "Market": "KOSPI"}
        for sector, names, _rs in _SECTOR_PLAN
        for name in names
    ]
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def bubble_response():
    """합성 DB 위에서의 현재 /api/sectors/bubble 서비스 출력 (period=1w, market=all)."""
    from unittest.mock import patch

    from backend.services.sector_advanced_service import get_sector_bubble

    db_path = _create_synthetic_db()
    # UN-1 — 신경로의 섹터 소속 원천은 registry 다(주간 stock_meta 아님).
    with patch("my_chart.analysis.sector_metrics.get_sector_registry",
               return_value=_synthetic_registry_df()):
        return get_sector_bubble(db_path, period="1w", market="all")


def _find_sector(bubble_response, name: str):
    for item in bubble_response.sectors:
        if item.name == name:
            return item
    return None


# ---------------------------------------------------------------------------
# Control — 정상섹터: RS 전원 존재 (현재 GREEN, M4 후에도 GREEN)
# ---------------------------------------------------------------------------

def test_control_full_rs_sector(bubble_response) -> None:
    """대조군 — RS 전원 존재 섹터의 rs_avg 는 평균 70.0 (결측 의미론과 무관하게 동일)."""
    item = _find_sector(bubble_response, "정상섹터")
    assert item is not None, "정상섹터(control) 가 응답에 없다"
    assert item.rs_avg == pytest.approx(_CONTROL_AVG, abs=TOL), (
        f"control rs_avg={item.rs_avg!r} != {_CONTROL_AVG}"
    )


# ---------------------------------------------------------------------------
# AC-SMU-007 — 부분 결측: 분모는 가용 8, 0-대체 값과 엄격히 다르다 (현재 RED)
# ---------------------------------------------------------------------------

def test_partial_missing_rs_avg_denominator_8(bubble_response) -> None:
    """10종목 중 2종목 RS 결측 → rs_avg 는 가용 8개의 평균(65.0)이어야 한다.

    0-대체 분모 10 값(52.0)과 엄격히 구분되는지도 함께 단언한다 — 분모만 바뀐
    변형이므로, 현재 구현이 52.0 을 반환하면 두 단언 모두 실패한다(RED).
    """
    item = _find_sector(bubble_response, "부분결측")
    assert item is not None, "부분결측 섹터가 응답에 없다"
    assert item.rs_avg == pytest.approx(_PARTIAL_AVG_8, abs=TOL), (
        f"부분결측 rs_avg={item.rs_avg!r}: 가용 8개 평균 {_PARTIAL_AVG_8} 이 아니다 "
        f"(AC-SMU-007 — 결측을 분모에서 제외해야 한다)"
    )
    assert abs(item.rs_avg - _PARTIAL_AVG_SUB) > TOL, (
        f"부분결측 rs_avg={item.rs_avg!r} 가 0-대체 분모 10 값 {_PARTIAL_AVG_SUB} "
        f"과 같다 — 결측이 0 으로 대체되고 있다 (AC-SMU-007 위반)"
    )


# ---------------------------------------------------------------------------
# AC-SMU-006/022 — 전체 결측: rs_avg 는 None (0.0 아님), 섹터는 탈락 금지 (현재 RED)
# ---------------------------------------------------------------------------

def test_all_missing_rs_avg_none_and_not_dropped(bubble_response) -> None:
    """RS 전원 결측 섹터 → rs_avg 는 None 이어야 하고(AC-SMU-006, 0.0 아님),
    섹터 자체는 응답에서 탈락하지 않는다(AC-SMU-022 관찰자).

    현재 구현은 0-대체로 rs_avg=0.0 을 반환하므로 RED 다.
    """
    item = _find_sector(bubble_response, "전체결측")
    assert item is not None, (
        "전체결측 섹터가 응답에서 탈락했다 (AC-SMU-022 위반 — 결측은 미포함이 아니라 null 이다)"
    )
    assert item.rs_avg is None, (
        f"전체결측 rs_avg={item.rs_avg!r}: None 이어야 한다 (AC-SMU-006 — "
        f"0.0 은 '전원 결측' 이 아니라 'RS 0' 을 의미하므로 정보를 왜곡한다)"
    )
