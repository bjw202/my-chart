"""SPEC-RS-REBALANCE-001 AC-RSR-006 기준 — 변경 전 `generate_rs_db()` 특성화(골든값).

M1 착수 직전의 프로덕션 코드로 research.md R10 픽스처(필터에 걸리는 행 없음)를
처리해 `RS_6M/3M/1M_Rating`을 캡처한 값이다. 이후 마일스톤(M1 분모 필터, M2 IBD식
재가중)은 이 세 등급을 바꾸면 안 된다(REQ-RSR-006). 골든값의 출처는 변경 전
프로덕션 출력이고, 비교 대상은 변경 후 프로덕션 출력이다.
"""

from __future__ import annotations

import sqlite3

import pytest

from my_chart.db import weekly
from tests.rsr_fixtures import make_weekly_db, price_row, read_rs, registry

_DATE = "2026-01-02"

# research.md R10 입력 (원시 수익률, 소수 비율).
_R10 = {
    "A": dict(RS_1M=-0.10, RS_3M=1.00, RS_6M=1.00, RS_9M=1.00, RS_12M=1.000),
    "B": dict(RS_1M=0.00, RS_3M=0.00, RS_6M=0.50, RS_9M=1.25, RS_12M=2.375),
    "C": dict(RS_1M=0.50, RS_3M=0.10, RS_6M=0.10, RS_9M=0.10, RS_12M=0.100),
    "D": dict(RS_1M=0.05, RS_3M=0.20, RS_6M=0.30, RS_9M=0.40, RS_12M=0.500),
}

# 변경 전 코드(HEAD 0b1dfc3)에서 캡처한 (RS_6M, RS_3M, RS_1M) 골든값 — research.md R10과 일치.
_GOLDEN = {
    "A": (100.0, 50.0, 25.0),
    "B": (25.0, 25.0, 50.0),
    "C": (50.0, 87.5, 100.0),
    "D": (75.0, 87.5, 75.0),
}


@pytest.fixture
def r10_db(tmp_path, monkeypatch):
    monkeypatch.setattr(weekly, "REFERENCE_STOCK", "A")
    monkeypatch.setattr(
        weekly,
        "get_stock_registry",
        lambda: registry(("000010", "A"), ("000020", "B"), ("000030", "C"), ("000040", "D")),
    )
    rows = [price_row(name, _DATE, **vals) for name, vals in _R10.items()]
    return make_weekly_db(tmp_path, rows)


def test_characterize_generate_rs_db_r10_6m_3m_1m_golden(r10_db):
    weekly.generate_rs_db(db_name=r10_db)

    df = read_rs(r10_db).set_index("Name")
    assert sorted(df.index) == ["A", "B", "C", "D"]
    for name, (rs6, rs3, rs1) in _GOLDEN.items():
        assert df.loc[name, "RS_6M_Rating"] == rs6, name
        assert df.loc[name, "RS_3M_Rating"] == rs3, name
        assert df.loc[name, "RS_1M_Rating"] == rs1, name


def test_characterize_relative_strength_schema_unchanged(r10_db):
    weekly.generate_rs_db(db_name=r10_db)

    conn = sqlite3.connect(f"{r10_db}.db")
    try:
        info = conn.execute("PRAGMA table_info(relative_strength)").fetchall()
    finally:
        conn.close()
    assert [c[1] for c in info] == [
        "Name", "Date", "RS_12M_Rating", "RS_6M_Rating", "RS_3M_Rating", "RS_1M_Rating",
    ]
    # 기본 키 (Name, Date)
    assert [c[1] for c in sorted(info, key=lambda c: c[5]) if c[5] > 0] == ["Name", "Date"]
