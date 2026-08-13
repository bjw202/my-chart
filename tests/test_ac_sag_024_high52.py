# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M5 — AC-SAG-024: 52주 신고가 판정.

`MAX(High)` over 364d, 규약 Y(`MAX52` NULL 종목 분자·분모 제외). 저장된
`MAX52`(Close 기반)를 판정에 쓰지 않는다(REQ-SAG-022).
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

from my_chart.analysis.sector_metrics import (
    HIGH_52W_WINDOW_DAYS,
    _aggregate_members,
    _build_member,
)

AGG_DIR = Path(__file__).resolve().parent / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = str(AGG_DIR / "weekly.db")
DAILY_DB = str(AGG_DIR / "daily.db")
REGISTRY = str(AGG_DIR / "registry.xlsx")
AS_OF = "2026-08-11"
NH_THRESHOLD = 0.02
MIN_MEMBERS = 5


def test_ac_sag_024_given_then_close_98_high_100_stored_max52_92() -> None:
    """AC 본문 Given/Then — 종가 98, 52주 MAX(High) 100, 저장 MAX52(Close 기반) 92.

    `98 >= 100*0.98` → True (신 판정). `95 >= 100*0.98`→ False 인데 저장 MAX52
    기준(`95 >= 92*0.98`→True)은 True 로 갈린다 — 두 기준이 실제로 다른 판정을 낸다.
    """
    high52_map = {"S1": 100.0, "S2": 100.0}
    caps = {"S1": 1.0, "S2": 1.0}

    m1 = _build_member("S1", {"Close": 98.0, "SMA10": None, "SMA40": None,
                               "RS_12M_Rating": None}, caps, high52_map)
    assert m1.nh is True

    m2 = _build_member("S2", {"Close": 95.0, "SMA10": None, "SMA40": None,
                               "RS_12M_Rating": None}, caps, high52_map)
    assert m2.nh is False, "AC 본문 — Close=95 는 MAX(High)=100 기준 신고가가 아니다"

    # 대조: 저장 MAX52(Close 기반) = 92 기준이면 95 도 신고가 판정(True)이 되어 갈린다.
    old_verdict = 95.0 >= 92.0 * (1 - NH_THRESHOLD)
    assert old_verdict is True and m2.nh is False, (
        "규약 정정 전(저장 MAX52 기준)과 정정 후(MAX(High) 기준) 판정이 실제로 갈려야 한다")


def test_ac_sag_024_null_max52_excluded_from_both_numerator_and_denominator() -> None:
    """규약 Y — 52주 이력 부족(high52 없음)이면 신고가 판정에서 완전히 빠진다."""
    m = _build_member(
        "NoHistory", {"Close": 100.0, "SMA10": None, "SMA40": None, "RS_12M_Rating": None},
        {"NoHistory": 1.0}, high52_map={})
    assert m.nh is None, "52주 이력 부족 종목은 nh=None(분모 제외)이어야 한다 — 0.0 치환 금지"

    agg, _ = _aggregate_members("합성", [m])
    assert agg.nh_pct.value is None, "nh 판정 종목이 0개면 nh_pct 는 결측이어야 한다"
    assert agg.valid_counts.nh == 0


@pytest.fixture(scope="module")
def fixture_high52() -> dict:
    """픽스처 weekly `stock_prices` 에서 직접 재계산한 `[as_of-364d, as_of]` MAX(High)."""
    win_start = (date.fromisoformat(AS_OF) - timedelta(days=HIGH_52W_WINDOW_DAYS)).isoformat()
    conn = sqlite3.connect(WEEKLY_DB)
    try:
        max_high = dict(conn.execute(
            "SELECT Name, MAX(High) FROM stock_prices WHERE Date > ? AND Date <= ? "
            "GROUP BY Name", (win_start, AS_OF)).fetchall())
        latest = dict(conn.execute(
            "SELECT Name, Close FROM stock_prices WHERE Date = ?", (AS_OF,)).fetchall())
        stored_max52 = dict(conn.execute(
            "SELECT Name, MAX52 FROM stock_prices WHERE Date = ?", (AS_OF,)).fetchall())
    finally:
        conn.close()

    reg = pd.read_excel(REGISTRY, header=8).rename(
        columns={"종목\n코드": "Code", "종목명": "Name", "시장": "Market"})
    reg["Code"] = reg["Code"].astype(str).str.zfill(6)
    reg = reg[~reg["Code"].duplicated(keep="first")]
    sector_of = dict(zip(reg["Name"], reg["산업명(대)"]))

    dconn = sqlite3.connect(DAILY_DB)
    try:
        meta_names = {r[0] for r in dconn.execute("SELECT name FROM stock_meta")}
    finally:
        dconn.close()

    valid = {n for n in sector_of if n in meta_names and n in latest}
    members: dict[str, list[str]] = defaultdict(list)
    for n in sorted(valid):
        members[str(sector_of[n])].append(n)
    ag5 = {s: ms for s, ms in members.items() if len(ms) >= MIN_MEMBERS}

    nh_count = 0
    for sector, names in ag5.items():
        for n in names:
            mh = max_high.get(n)
            close = latest.get(n)
            if mh is None or close is None or mh <= 0:
                continue
            if close >= mh * (1 - NH_THRESHOLD):
                nh_count += 1
    return {
        "max_high": max_high, "latest": latest, "stored_max52": stored_max52,
        "ag5": ag5, "nh_count_ref": nh_count,
    }


def test_ac_sag_024_gating_production_nh_count_matches_reference(fixture_high52) -> None:
    """게이팅 — 집계 픽스처에서 프로덕션(전 섹터 합산) 신고가 종목 수 == 참조 구현."""
    from my_chart.analysis.sector_metrics import compute_sector_aggregates

    from unittest.mock import patch
    with patch("my_chart.registry.SECTORMAP_PATH", REGISTRY), \
            patch("my_chart.registry._df_sector", None), \
            patch("my_chart.registry._df_stock", None):
        result = compute_sector_aggregates(
            WEEKLY_DB, AS_OF, daily_db_path=DAILY_DB, registry_path=REGISTRY,
            market="all", as_of=AS_OF)

    prod_nh_count = 0
    for a in result.aggregates:
        if a.nh_pct.value is not None and a.valid_counts.nh:
            prod_nh_count += round(a.nh_pct.value / 100 * a.valid_counts.nh)

    assert prod_nh_count == fixture_high52["nh_count_ref"], (
        f"프로덕션 신고가 종목 수 {prod_nh_count} != 참조 {fixture_high52['nh_count_ref']}")


def test_ac_sag_024_diverges_from_stored_max52_reference_by_at_least_5(fixture_high52) -> None:
    """되돌림 대조(구조적) — 저장 MAX52(Close 기반) 참조와 MAX(High) 참조가 >= 5종목 갈린다.

    (F7 요건 — `test_aggregation_fixture.py::test_ac_sag_048_f7_*` 가 같은 사실을
    MANIFEST 대조로 이미 게이팅한다. 여기서는 AC-SAG-024 자신의 되돌림 절로 재확인한다.)
    """
    max_high, latest, stored = (
        fixture_high52["max_high"], fixture_high52["latest"], fixture_high52["stored_max52"])
    diverging = []
    for sector, names in fixture_high52["ag5"].items():
        for n in names:
            mh, close, sm = max_high.get(n), latest.get(n), stored.get(n)
            if close is None:
                continue
            new_v = mh is not None and mh > 0 and close >= mh * (1 - NH_THRESHOLD)
            old_v = sm is not None and sm > 0 and close >= sm * (1 - NH_THRESHOLD)
            if bool(new_v) != bool(old_v) and mh is not None and sm is not None:
                diverging.append(n)
    assert len(diverging) >= 5, (
        f"MAX(High) 기준과 저장 MAX52 기준의 divergent 종목이 {len(diverging)}개뿐 — "
        "mut_stored_max52 되돌림이 검출력을 가지려면 >= 5 필요")


def test_ac_sag_024_static_scan_high52_source_is_weekly_max_high() -> None:
    """정적 스캔 — `_high52_map` 이 실제로 weekly `MAX(High)` 재계산을 쓴다(회귀 방지)."""
    src = Path("my_chart/analysis/sector_metrics.py").read_text(encoding="utf-8")
    assert "MAX(High)" in src
    assert "def _high52_map(" in src
