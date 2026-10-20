"""재현 테스트: Sector history 날짜 정합성 (부분 데이터 날짜 제외).

버그: BumpChart 마지막 날에 일부 섹터가 누락되어 표시됨.
원인: weekly DB의 부분 데이터 날짜(1~4종목)가 compute_sector_history에 포함되어
      섹터별 history 길이가 불균일해지고, 프론트엔드 인덱스 매핑이 깨짐.

검증 (수정 후 기대동작):
1. 부분 데이터 날짜(종목 수 < 임계값)는 compute_sector_history 결과에서 제외된다.
2. 반환된 모든 날짜는 충분한 종목 수(>= 임계값)를 가져야 한다.
3. 정제된 날짜가 rankings와 함께 반환되어 서비스 계층이 날짜를 재조회하지 않아도 된다.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from my_chart.analysis.sector_metrics import compute_sector_history


# ---------------------------------------------------------------------------
# 테스트 DB 스키마 (test_sector_metrics.py와 동일)
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


def _make_sector_row(
    name: str,
    date: str,
    close: float = 100.0,
    chg_1w: float = 0.02,
    chg_1m: float = 0.05,
    chg_3m: float = 0.10,
    max52: float = 110.0,
    rs: float = 70.0,
) -> tuple:
    """32-element weekly row 생성 (test_sector_metrics.py 패턴)."""
    return (
        name, date,
        close * 0.99, close * 1.01, close * 0.98, close,
        1_000_000.0, 800_000.0,
        chg_1w, chg_1m, 0.08, chg_3m, 0.20, 0.25, 0.30,
        90.0, 92.0, 85.0,
        84.0, 83.0, 82.0, 81.0,
        close * 1.05, max52, 70.0, close - 70.0,
        50.0, 55.0, 60.0, 65.0, 70.0, rs, 1.1,
    )


# Bump 순위는 섹터 표와 같은 `compute_sector_aggregates` 경로를 탄다(AG-5 최소 구성종목 5,
# 시총가중 원천 = daily stock_meta, 3M 앵커 = t−91일 격자 바). 따라서 픽스처는 섹터당
# 5종목·시총·3M 이력을 갖춰야 정상 날짜가 순위 대상이 된다.
_SECTOR_MEMBERS: dict[str, list[tuple[str, float]]] = {
    # 섹터 → [(종목, 주간 종가 성장률)] — 섹터 간 수익률을 달리해 순위가 갈리게 한다.
    "전기전자": [("삼성전자", 0.012), ("SK하이닉스", 0.011), ("LG전자", 0.010),
              ("삼성전기", 0.009), ("LG디스플레이", 0.008)],
    "철강금속": [("POSCO홀딩스", 0.001), ("현대제철", 0.000), ("고려아연", -0.001),
              ("동국제강", -0.002), ("세아베스틸지주", -0.003)],
}
# 정상(전체) 날짜: 2023-09-22 ~ 2024-01-12 금요일 17개 — 마지막 3개 날짜 모두 3M 앵커 보유.
_FULL_DATES: list[str] = [
    (date(2023, 9, 22) + timedelta(weeks=i)).isoformat() for i in range(17)
]


def _insert_full_date(conn: sqlite3.Connection, date_str: str) -> None:
    """정상 날짜: 2섹터 × 5종목 + KOSPI."""
    week_i = _FULL_DATES.index(date_str)
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_sector_row("KOSPI", date_str, close=2500.0, chg_1w=0.01, chg_1m=0.03, chg_3m=0.08),
    )
    for members in _SECTOR_MEMBERS.values():
        for name, growth in members:
            close = 100.0 * (1 + growth) ** week_i
            conn.execute(
                "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                _make_sector_row(name, date_str, close=close),
            )
            conn.execute(
                "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
                (name, date_str, 70.0),
            )


def _insert_partial_date(conn: sqlite3.Connection, date: str) -> None:
    """부분 데이터 날짜: 종목 1개만 (실제 운영 DB의 1~4종목 잔재 재현)."""
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        _make_sector_row("삼성전자", date, chg_1w=0.02),
    )
    conn.execute(
        "INSERT OR REPLACE INTO relative_strength VALUES (?, ?, ?)",
        ("삼성전자", date, 80.0),
    )


@pytest.fixture
def history_db(tmp_path: Path, monkeypatch) -> str:
    """정상 날짜 17개(… 2024-01-05, 2024-01-12) + 부분 데이터 날짜 1개를 가진 weekly DB.

    Dates:
      2023-09-22 ~ 2024-01-12 금요일 (정상, 11행) — 3M 앵커 이력
      2024-01-10 (부분, 1행)  ← 버그 유발
    같은 디렉터리에 시총 원천 daily DB(``_daily_db``)도 만든다.
    """
    db_path = str(tmp_path / "test_history.db")
    conn = sqlite3.connect(db_path)
    conn.execute(_WEEKLY_DDL)
    conn.execute(_RS_DDL)

    for d in _FULL_DATES:
        _insert_full_date(conn, d)
    _insert_partial_date(conn, "2024-01-10")  # 부분 데이터

    conn.commit()
    conn.close()

    all_names = [n for members in _SECTOR_MEMBERS.values() for n, _g in members]
    dconn = sqlite3.connect(_daily_db(db_path))
    dconn.execute("CREATE TABLE stock_meta (name TEXT PRIMARY KEY, market_cap REAL)")
    dconn.execute("CREATE TABLE stock_prices (Name TEXT, Date TEXT, VolumeWon REAL)")
    dconn.executemany("INSERT INTO stock_meta VALUES (?, ?)",
                      [(n, 1.0e12) for n in all_names])
    dconn.commit()
    dconn.close()

    registry = pd.DataFrame([
        {"Code": f"{i:06d}", "Name": n, "Market": "KOSPI", "산업명(대)": sector,
         "산업명(중)": sector, "주요제품": "-"}
        for i, (sector, n) in enumerate(
            (s, n) for s, members in _SECTOR_MEMBERS.items() for n, _g in members)
    ])
    monkeypatch.setattr("my_chart.registry._load_sectormap", lambda *a, **k: registry.copy())
    monkeypatch.setattr("my_chart.registry._df_sector", None)
    # 유효 유니버스(UN-3)는 라이브 registry xlsx 를 읽는다 — 이 테스트의 관심사(날짜 정합성)가
    # 아니므로 제한 없음(None)으로 고정한다.
    monkeypatch.setattr(
        "my_chart.analysis.sector_metrics._valid_universe", lambda *a, **k: None)
    return db_path


def _daily_db(weekly_db: str) -> str:
    """history_db 픽스처가 같은 디렉터리에 만드는 daily DB 경로."""
    return str(Path(weekly_db).with_name("test_history_daily.db"))


# ---------------------------------------------------------------------------
# 재현 테스트: 부분 데이터 날짜 제외
# ---------------------------------------------------------------------------


def test_compute_sector_history_excludes_partial_dates(history_db: str) -> None:
    """부분 데이터 날짜(소수 종목)는 결과에서 제외되어야 한다.

    RED (현재): 3개 날짜 모두 반환 → 부분 데이터(2024-01-10) 포함
    GREEN (수정 후): 정상 날짜 2개만 반환 (2024-01-05, 2024-01-12)
    """
    result = compute_sector_history(history_db, weeks=3, daily_db_path=_daily_db(history_db))

    # 수정 후 시그니처: (dates, rankings) 튜플 반환
    # 현재 시그니처: list[list[SectorRank]] 반환
    if isinstance(result, tuple):
        dates, rankings = result
    else:
        # 현재(RED) 동작: 날짜 정보 없이 rankings만 반환
        dates = ["UNKNOWN"] * len(result)
        rankings = result

    # 부분 데이터 날짜(2024-01-10)는 결과에 없어야 한다
    assert "2024-01-10" not in dates, (
        f"부분 데이터 날짜가 제외되지 않음: {dates}. "
        "1종목만 있는 날짜는 섹터 history 길이를 불균일하게 만듦."
    )
    # 정상 날짜는 모두 포함되어야 한다
    assert "2024-01-05" in dates
    assert "2024-01-12" in dates


def test_compute_sector_history_all_dates_have_sufficient_stocks(history_db: str) -> None:
    """반환된 모든 날짜는 충분한 종목 수(>= 임계값)를 가져야 한다.

    임계값 미만 날짜가 섞이면 섹터별 history 길이가 달라져
    프론트엔드 인덱스 매핑이 깨지고 마지막 날 섹터가 누락됨.
    """
    result = compute_sector_history(history_db, weeks=3, daily_db_path=_daily_db(history_db))

    if isinstance(result, tuple):
        dates, rankings = result
    else:
        dates = ["UNKNOWN"] * len(result)
        rankings = result

    # 각 날짜(week)의 랭킹은 여러 섹터를 포함해야 함 (부분 데이터면 1섹터만)
    # 정상 날짜는 2개 섹터(전기전자, 철강금속) 이상 반환
    for i, week_rankings in enumerate(rankings):
        sector_count = len(week_rankings)
        assert sector_count >= 2, (
            f"날짜 {dates[i] if dates[i] != 'UNKNOWN' else f'#{i}'}의 섹터 수가 부족: {sector_count}. "
            "부분 데이터 날짜가 필터링되지 않았을 가능성."
        )


def test_compute_sector_history_returns_dates_for_ssot(history_db: str) -> None:
    """compute_sector_history는 정제된 날짜를 함께 반환해야 한다 (SSOT).

    서비스 계층(get_sector_history)이 날짜를 별도 재조회하면
    compute_sector_history의 정제 로직과 불일치가 발생할 수 있음.
    날짜를 함께 반환하면 단일 진실 공급원이 됨.
    """
    result = compute_sector_history(history_db, weeks=3, daily_db_path=_daily_db(history_db))

    assert isinstance(result, tuple), (
        "compute_sector_history는 (dates, rankings) 튜플을 반환해야 함. "
        "서비스 계층이 날짜를 재조회하면 정제 불일치 발생."
    )
    dates, rankings = result
    assert len(dates) == len(rankings), "날짜와 랭킹 리스트 길이 불일치"
    assert all(isinstance(d, str) for d in dates)
