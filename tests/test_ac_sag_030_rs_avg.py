# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M5 — AC-SAG-030: RS 평균 등가중 + 결측 제외.

`rs_avg = Σ RSᵢ / n_valid`(등가중). RS 행이 없는 종목은 분자·분모 모두에서
제외한다(REQ-SAG-027, §2.3). 기존 `_equal_mean()` 구현이 이미 결측을 제외하므로
GREEN — 본 커밋은 그 사실을 게이팅 테스트로 실증하는 회귀 방지 커밋이다.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from my_chart.analysis.sector_metrics import (
    _Member,
    _aggregate_members,
    compute_sector_aggregates,
)

AGG_DIR = Path(__file__).resolve().parent / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = str(AGG_DIR / "weekly.db")
DAILY_DB = str(AGG_DIR / "daily.db")
REGISTRY = str(AGG_DIR / "registry.xlsx")
AS_OF = "2026-08-11"
MIN_MEMBERS = 5


def test_ac_sag_030_given_then_rs_avg_excludes_missing_from_denominator() -> None:
    """10종목 중 2종목 RS 행 없음 → rs_avg == Σ(8종목 RS)/8, 0.0 치환 후 /10 과 다르다."""
    rs_values = [80.0, 70.0, 60.0, 90.0, 50.0, 40.0, 65.0, 75.0]  # 8종목 유효
    members = [
        _Member(name=f"s{i}", market_cap=1.0, returns={"1w": 1.0, "1m": 1.0, "3m": 1.0},
                rs=rs, nh=None, stage2=None)
        for i, rs in enumerate(rs_values)
    ] + [
        _Member(name="missing1", market_cap=1.0, returns={"1w": 1.0, "1m": 1.0, "3m": 1.0},
                rs=None, nh=None, stage2=None),
        _Member(name="missing2", market_cap=1.0, returns={"1w": 1.0, "1m": 1.0, "3m": 1.0},
                rs=None, nh=None, stage2=None),
    ]
    agg, _ = _aggregate_members("합성", members)

    expected = sum(rs_values) / len(rs_values)
    assert agg.rs_avg.value == pytest.approx(expected)

    zero_fill_10 = sum(rs_values) / 10  # 결측을 0.0 으로 채우고 10 으로 나눈 값
    assert agg.rs_avg.value != pytest.approx(zero_fill_10)
    assert agg.coverage.rs == pytest.approx(0.8)
    assert agg.valid_counts.rs == 8


def test_ac_sag_030_not_market_cap_weighted() -> None:
    """대형주 RS 를 크게 바꿔도 rs_avg 변화가 1/n 비례 — 시총가중이 아님을 확인."""
    base = [
        _Member(name="big", market_cap=1_000_000.0,
                returns={"1w": 1.0, "1m": 1.0, "3m": 1.0}, rs=50.0, nh=None, stage2=None),
        _Member(name="small1", market_cap=1.0,
                returns={"1w": 1.0, "1m": 1.0, "3m": 1.0}, rs=50.0, nh=None, stage2=None),
        _Member(name="small2", market_cap=1.0,
                returns={"1w": 1.0, "1m": 1.0, "3m": 1.0}, rs=50.0, nh=None, stage2=None),
        _Member(name="small3", market_cap=1.0,
                returns={"1w": 1.0, "1m": 1.0, "3m": 1.0}, rs=50.0, nh=None, stage2=None),
        _Member(name="small4", market_cap=1.0,
                returns={"1w": 1.0, "1m": 1.0, "3m": 1.0}, rs=50.0, nh=None, stage2=None),
    ]
    agg_base, _ = _aggregate_members("합성", base)

    bumped = [
        m if m.name != "big" else _Member(
            name="big", market_cap=m.market_cap, returns=m.returns, rs=100.0,
            nh=None, stage2=None)
        for m in base
    ]
    agg_bumped, _ = _aggregate_members("합성", bumped)

    delta = agg_bumped.rs_avg.value - agg_base.rs_avg.value
    expected_delta = (100.0 - 50.0) / len(base)  # 1/n 비례(등가중)
    assert delta == pytest.approx(expected_delta), (
        f"delta={delta} — 시총가중이면 대형주 변화가 지배적이라 1/n 비례를 벗어난다")


@pytest.fixture(scope="module")
def fixture_ag5() -> dict:
    """집계 픽스처의 AG-5(구성종목 >= 5) 통과 섹터 → 구성종목명 목록."""
    reg = pd.read_excel(REGISTRY, header=8).rename(
        columns={"종목\n코드": "Code", "종목명": "Name", "시장": "Market"})
    reg["Code"] = reg["Code"].astype(str).str.zfill(6)
    reg = reg[~reg["Code"].duplicated(keep="first")]
    sector_of = dict(zip(reg["Name"], reg["산업명(대)"]))

    conn = sqlite3.connect(WEEKLY_DB)
    try:
        latest_names = {r[0] for r in conn.execute(
            "SELECT Name FROM stock_prices WHERE Date = ?", (AS_OF,))}
    finally:
        conn.close()
    dconn = sqlite3.connect(DAILY_DB)
    try:
        meta_names = {r[0] for r in dconn.execute("SELECT name FROM stock_meta")}
    finally:
        dconn.close()

    valid = {n for n in sector_of if n in meta_names and n in latest_names}
    members: dict[str, list[str]] = defaultdict(list)
    for n in sorted(valid):
        members[str(sector_of[n])].append(n)
    return {"ag5": {s: ms for s, ms in members.items() if len(ms) >= MIN_MEMBERS}}


def test_ac_sag_030_gating_production_rs_avg_matches_reference(fixture_ag5) -> None:
    """게이팅 — 집계 픽스처에서 프로덕션 rs_avg == 참조 구현(등가중, 결측 제외) `1e-9` 이내."""
    with patch("my_chart.registry.SECTORMAP_PATH", REGISTRY), \
            patch("my_chart.registry._df_sector", None), \
            patch("my_chart.registry._df_stock", None):
        result = compute_sector_aggregates(
            WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY,
            market="all", as_of=AS_OF)

    conn = sqlite3.connect(WEEKLY_DB)
    try:
        rs_at_latest = dict(conn.execute(
            "SELECT Name, RS_12M_Rating FROM relative_strength WHERE Date = ?",
            (AS_OF,)).fetchall())
    finally:
        conn.close()

    checked = 0
    for sector, names in fixture_ag5["ag5"].items():
        rs_ok = [rs_at_latest[n] for n in names if n in rs_at_latest]
        if not rs_ok:
            continue
        ref = sum(rs_ok) / len(rs_ok)
        prod = next((a.rs_avg.value for a in result.aggregates if a.name == sector), None)
        assert prod is not None, f"{sector}: 프로덕션 rs_avg 가 결측이다"
        assert prod == pytest.approx(ref, abs=1e-9), (
            f"{sector}: 프로덕션 {prod} != 참조 {ref}")
        checked += 1
    assert checked > 0, "AG-5 통과 섹터 중 RS 유효 종목을 가진 섹터가 하나도 없다"


def test_ac_sag_030_mut_rs_zero_fill_reference_diverges(fixture_ag5) -> None:
    """되돌림 대조(구조적) — `or 0.0` + member_count 분모 참조값과 프로덕션이 실제로 다르다."""
    with patch("my_chart.registry.SECTORMAP_PATH", REGISTRY), \
            patch("my_chart.registry._df_sector", None), \
            patch("my_chart.registry._df_stock", None):
        result = compute_sector_aggregates(
            WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY,
            market="all", as_of=AS_OF)

    conn = sqlite3.connect(WEEKLY_DB)
    try:
        rs_at_latest = dict(conn.execute(
            "SELECT Name, RS_12M_Rating FROM relative_strength WHERE Date = ?",
            (AS_OF,)).fetchall())
    finally:
        conn.close()

    diverging = 0
    for sector, names in fixture_ag5["ag5"].items():
        rs_ok = [rs_at_latest[n] for n in names if n in rs_at_latest]
        if not rs_ok or len(rs_ok) == len(names):
            continue  # 결측 종목이 없는 섹터는 두 방식이 같은 값을 낸다
        eq_correct = sum(rs_ok) / len(rs_ok)
        zero_fill = sum(rs_ok) / len(names)
        prod = next((a.rs_avg.value for a in result.aggregates if a.name == sector), None)
        if prod is None:
            continue
        if abs(prod - eq_correct) < 1e-6 and abs(prod - zero_fill) > 1e-6:
            diverging += 1

    assert diverging >= 1, (
        "결측 제외 방식(프로덕션)과 0.0 치환+member_count 분모 방식이 최소 1개 섹터에서 "
        "실제로 갈려야 한다 — 그렇지 않으면 mut_rs_zero_fill 대조가 무게이팅이다")
