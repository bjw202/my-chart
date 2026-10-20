"""SPEC-RS-REBALANCE-001 M1 — 낡은 행 제거와 순위 분모 정리.

AC-RSR-001 짝 없는 행 제거 / AC-RSR-002 지수·거래량 0 제외, 유동성 비적용 /
AC-RSR-003 우선주·스팩 판별 / AC-RSR-004 `1+R <= 0` 가드 /
AC-RSR-017 짝이 있는 낡은 행 제거 / AC-RSR-018 결측 수익률 행.

모든 테스트는 `tmp_path` 임시 DB만 쓴다. 기대값은 픽스처에 심은 행 수 또는
테스트 안에서 손으로 정한 순위 상수이며, 프로덕션 함수에서 끌어오지 않는다.
"""

from __future__ import annotations

import pytest

from my_chart.db import weekly
from tests.rsr_fixtures import make_weekly_db, price_row, query_one, read_rs, registry

_ORPHAN_SQL = (
    "SELECT COUNT(*) FROM relative_strength rs "
    "LEFT JOIN stock_prices sp USING(Name, Date) WHERE sp.Name IS NULL"
)


def _use(monkeypatch, reference: str, *entries: tuple[str, str]) -> None:
    """기준 종목과 테스트 등록부를 주입한다(acceptance.md 픽스처 공통 주의, R14)."""
    monkeypatch.setattr(weekly, "REFERENCE_STOCK", reference)
    monkeypatch.setattr(weekly, "get_stock_registry", lambda: registry(*entries))


def _rs_row(name: str, date: str, v: float = 50.0) -> tuple:
    return (name, date, v, v, v, v)


def _ratings(db_name: str, date: str) -> dict[str, float]:
    df = read_rs(db_name)
    df = df[df["Date"] == date]
    return dict(zip(df["Name"], df["RS_1M_Rating"]))


# ---------------------------------------------------------------------------
# AC-RSR-001 — 짝 없는 행 제거 (REQ-RSR-001)
# ---------------------------------------------------------------------------

_D1, _D2, _DX, _DP = "2026-01-02", "2026-01-09", "2025-12-26", "2026-01-07"
_S = ["S1", "S2", "S3", "S4", "S5"]


@pytest.fixture
def ac001_db(tmp_path, monkeypatch):
    _use(monkeypatch, "S1", *[(f"0000{i}0", n) for i, n in enumerate(_S, 1)])
    prices = [
        price_row(n, d, RS_1M=0.1 * i) for d in (_D1, _D2) for i, n in enumerate(_S, 1)
    ]
    prices.append(price_row("S2", _DP))  # (c) 기준 종목이 없는 날짜
    stale = [_rs_row(n, d) for d in (_D1, _D2) for n in _S]
    stale += [_rs_row(n, _DX) for n in ("S1", "S2", "S3")]  # (a) 3행
    stale += [_rs_row("OLD", _D1)]  # (b) 1행
    stale += [_rs_row(n, _DP) for n in ("S3", "S4")]  # (c) 2행
    db = make_weekly_db(tmp_path, prices, stale)
    assert query_one(db, _ORPHAN_SQL) == 6  # 픽스처 전제: 짝 없는 행 6개
    return db


def test_ac_rsr_001_unpaired_rows_removed(ac001_db):
    weekly.generate_rs_db(db_name=ac001_db)

    assert query_one(ac001_db, _ORPHAN_SQL) == 0


def test_ac_rsr_001_contrast_both_steps_disabled_leaves_6(ac001_db, monkeypatch):
    """대조: (i)·(ii)를 모두 끄면 짝 없는 행 6개가 남는다."""
    monkeypatch.setattr(weekly, "_delete_unprocessed_dates", lambda conn: None)
    monkeypatch.setattr(weekly, "_delete_stale_rows_for_date", lambda conn, d, keep: None)

    weekly.generate_rs_db(db_name=ac001_db)

    assert query_one(ac001_db, _ORPHAN_SQL) == 6


def test_ac_rsr_001_contrast_step_i_disabled_leaves_5(ac001_db, monkeypatch):
    """대조: (i)만 끄면 (b)는 (ii)가 지우고 (a)·(c)의 5개가 남는다."""
    monkeypatch.setattr(weekly, "_delete_unprocessed_dates", lambda conn: None)

    weekly.generate_rs_db(db_name=ac001_db)

    assert query_one(ac001_db, _ORPHAN_SQL) == 5


def test_ac_rsr_001_date_with_no_rows_after_filter_is_cleared(tmp_path, monkeypatch):
    """필터 후 행이 0개인 날짜는 그 날짜의 행을 모두 삭제한다(REQ-RSR-001)."""
    _use(monkeypatch, "S1", ("000010", "S1"), ("000020", "S2"))
    prices = [price_row("S1", _D1), price_row("S2", _D1, RS_1M=0.2)]
    prices += [price_row("S1", _D2, Volume=0.0), price_row("S2", _D2, Volume=0.0)]
    db = make_weekly_db(tmp_path, prices, [_rs_row("S1", _D2), _rs_row("S2", _D2)])

    weekly.generate_rs_db(db_name=db)

    assert query_one(db, "SELECT COUNT(*) FROM relative_strength WHERE Date = ?", (_D2,)) == 0
    assert query_one(db, "SELECT COUNT(*) FROM relative_strength WHERE Date = ?", (_D1,)) == 2


def test_missing_reference_stock_leaves_table_untouched(tmp_path, monkeypatch):
    """기준 종목 행이 없으면 (i)이 테이블 전체를 지우지 않도록 아무것도 바꾸지 않는다."""
    _use(monkeypatch, "ABSENT", ("000010", "S1"))
    db = make_weekly_db(tmp_path, [price_row("S1", _D1)], [_rs_row("S1", _D1), _rs_row("S1", _DX)])

    weekly.generate_rs_db(db_name=db)

    assert query_one(db, "SELECT COUNT(*) FROM relative_strength") == 2


# ---------------------------------------------------------------------------
# AC-RSR-002 — 지수·거래량 0 분모 제외, 유동성 비적용 (REQ-RSR-002, 004, 008)
# ---------------------------------------------------------------------------


def test_ac_rsr_002_index_and_zero_volume_excluded_before_ranking(tmp_path, monkeypatch):
    _use(
        monkeypatch, "S1",
        ("000010", "S1"), ("000020", "S2"), ("000030", "S3"), ("000040", "S4"),
        ("000050", "Z"), ("000060", "L"),
    )
    prices = [
        price_row("S1", _D1, RS_1M=0.10),
        price_row("S2", _D1, RS_1M=0.20),
        price_row("S3", _D1, RS_1M=0.30),
        price_row("S4", _D1, RS_1M=0.40),
        price_row("KOSPI", _D1, RS_1M=0.25),
        price_row("KOSDAQ", _D1, RS_1M=0.35),
        price_row("Z", _D1, RS_1M=0.90, Volume=0.0),  # 일반 종목 중간값보다 큰 RS_1M
        # 거래대금 = 100원 × 10주 = 1,000원 — 50억 원에 크게 못 미침
        price_row("L", _D1, RS_1M=0.05, Close=100.0, Volume=10.0, VolumeSMA10=10.0),
    ]
    db = make_weekly_db(tmp_path, prices)

    weekly.generate_rs_db(db_name=db)

    ratings = _ratings(db, _D1)
    # (a) 지수·거래량 0 행 미기록
    assert not {"KOSPI", "KOSDAQ", "Z"} & set(ratings)
    # (b) 유동성 필터 비적용 — L은 기록된다
    assert "L" in ratings
    # (c) 다섯 종목만의 분모: RS_1M 오름차순 L < S1 < S2 < S3 < S4 → 20/40/60/80/100
    assert ratings == {"L": 20.0, "S1": 40.0, "S2": 60.0, "S3": 80.0, "S4": 100.0}


# ---------------------------------------------------------------------------
# AC-RSR-003 — 우선주·스팩 판별 규칙 (REQ-RSR-003, B-1)
# ---------------------------------------------------------------------------


def test_ac_rsr_003_preferred_and_spac_excluded_common_kept(tmp_path, monkeypatch):
    _use(
        monkeypatch, "성우",
        ("000100", "성우"), ("000200", "에코글로우"), ("000300", "이오플로우"),
        ("000015", "가나다우"),  # 코드 끝자리 5 → 우선주
        ("000400", "가나다스팩1호"),  # 끝자리 0 → 이름의 '스팩'으로만 잡힌다
    )
    names = ["성우", "에코글로우", "이오플로우", "가나다우", "가나다스팩1호"]
    prices = [price_row(n, _D1, RS_1M=0.1 * i) for i, n in enumerate(names, 1)]
    db = make_weekly_db(tmp_path, prices)

    weekly.generate_rs_db(db_name=db)

    assert set(_ratings(db, _D1)) == {"성우", "에코글로우", "이오플로우"}


def test_ac_rsr_003_name_absent_from_registry_is_not_preferred(tmp_path, monkeypatch):
    """등록부에 코드가 없는 이름은 우선주로 판정하지 않는다."""
    _use(monkeypatch, "S1", ("000010", "S1"))
    prices = [price_row("S1", _D1), price_row("미등록우", _D1, RS_1M=0.2)]
    db = make_weekly_db(tmp_path, prices)

    weekly.generate_rs_db(db_name=db)

    assert set(_ratings(db, _D1)) == {"S1", "미등록우"}


# ---------------------------------------------------------------------------
# AC-RSR-004 — `1+R <= 0` 행 가드 (REQ-RSR-007)
# ---------------------------------------------------------------------------


def test_ac_rsr_004_non_positive_one_plus_return_row_excluded(tmp_path, monkeypatch):
    _use(
        monkeypatch, "S1",
        ("000010", "S1"), ("000020", "S2"), ("000030", "S3"), ("000040", "S4"),
        ("000050", "V"),
    )
    prices = [price_row(f"S{i}", _D1, RS_1M=0.1 * i) for i in range(1, 5)]
    prices.append(price_row("V", _D1, RS_1M=0.9, RS_6M=-1.0))
    db = make_weekly_db(tmp_path, prices)

    weekly.generate_rs_db(db_name=db)

    assert _ratings(db, _D1) == {"S1": 25.0, "S2": 50.0, "S3": 75.0, "S4": 100.0}


# ---------------------------------------------------------------------------
# AC-RSR-017 — 짝이 있는 낡은 행 제거 (REQ-RSR-001, 004)
# ---------------------------------------------------------------------------

_DN = "2026-01-05"
_STALE_SQL = (
    "SELECT COUNT(*) FROM relative_strength WHERE (Name='KOSPI' AND Date=?) "
    "OR (Name='Z' AND Date=?) OR Date=?"
)


@pytest.fixture
def ac017_db(tmp_path, monkeypatch):
    _use(
        monkeypatch, "S1",
        ("000010", "S1"), ("000020", "S2"), ("000030", "S3"), ("000040", "S4"),
        ("000050", "Z"),
    )
    prices = [price_row(f"S{i}", d, RS_1M=0.1 * i) for d in (_D1, _D2) for i in range(1, 5)]
    prices += [
        price_row("KOSPI", _D1),
        price_row("Z", _D1, RS_1M=0.5),
        price_row("Z", _D2, RS_1M=0.5, Volume=0.0),
        price_row("S2", _DN),
    ]
    stale = [
        _rs_row("KOSPI", _D1),  # (a) 짝 있는 지수 행
        _rs_row("Z", _D2),  # (b) 거래량 0으로 바뀐 종목
        _rs_row("S2", _DN),  # (c) 비기준 날짜의 짝 있는 행
    ]
    db = make_weekly_db(tmp_path, prices, stale)
    assert query_one(db, _ORPHAN_SQL) == 0  # 픽스처 전제: 세 행 모두 짝이 있다
    return db


def test_ac_rsr_017_paired_stale_rows_removed(ac017_db):
    weekly.generate_rs_db(db_name=ac017_db)

    assert query_one(ac017_db, _STALE_SQL, (_D1, _D2, _DN)) == 0
    df = read_rs(ac017_db)
    written = set(zip(df["Name"], df["Date"]))
    expected = {(f"S{i}", d) for d in (_D1, _D2) for i in range(1, 5)} | {("Z", _D1)}
    assert written == expected


def test_ac_rsr_017_contrast_pair_based_delete_leaves_3(ac017_db, monkeypatch):
    """대조: (i)·(ii) 자리에 짝 기준 삭제를 넣으면 세 행이 모두 살아남는다."""

    def pair_based_delete(conn):
        conn.execute(
            "DELETE FROM relative_strength WHERE NOT EXISTS (SELECT 1 FROM stock_prices sp "
            "WHERE sp.Name = relative_strength.Name AND sp.Date = relative_strength.Date)"
        )

    monkeypatch.setattr(weekly, "_delete_unprocessed_dates", pair_based_delete)
    monkeypatch.setattr(weekly, "_delete_stale_rows_for_date", lambda conn, d, keep: None)

    weekly.generate_rs_db(db_name=ac017_db)

    assert query_one(ac017_db, _STALE_SQL, (_D1, _D2, _DN)) == 3


# ---------------------------------------------------------------------------
# AC-RSR-018 — 결측 수익률 행 (REQ-RSR-023, 현행 dropna 유지)
# ---------------------------------------------------------------------------


def test_ac_rsr_018_rows_with_any_null_column_get_no_rating(tmp_path, monkeypatch):
    _use(
        monkeypatch, "S1",
        ("000010", "S1"), ("000020", "S2"), ("000030", "S3"), ("000040", "S4"),
        ("000050", "Y"), ("000060", "W"),
    )
    prices = [price_row(f"S{i}", _D1, RS_1M=0.1 * i) for i in range(1, 5)]
    prices.append(price_row("Y", _D1, RS_1M=0.9, RS_12M=None))  # 신규 상장
    prices.append(price_row("W", _D1, RS_1M=0.8, SMA40_Trend_4M=None))  # 명인제약 형태
    db = make_weekly_db(tmp_path, prices)

    weekly.generate_rs_db(db_name=db)

    assert _ratings(db, _D1) == {"S1": 25.0, "S2": 50.0, "S3": 75.0, "S4": 100.0}
