# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 — AC-SAG-048 (M1.0-a 종료 게이트).

집계 프로즌 픽스처 `tests/fixtures/frozen/aggregation-2026-08-11/` 가 acceptance.md
§8.2 **F1~F11 구조 요건**을 충족하는지 기계적으로 검사한다. 이 테스트의 PASS 가
**M1.0-a 완료 조건**이며, RED 인 상태에서 M1.0-b(골든 baseline 캡처) 착수를 금지한다
(acceptance.md §8.5 강제 순서).

설계 원칙
---------
* **요건당 1개 단언** — 실패한 요건명이 오류 메시지에 그대로 드러나야 한다.
* **독립 재산출** — `build_fixture.py` 를 import 하지 않는다. 픽스처 DB/xlsx 에서 원시
  컬럼을 직접 읽어 요건을 다시 계산하고, 그 값을 `MANIFEST.md` 의 기계 판독 블록에
  기록된 값과 대조한다. MANIFEST 에 손으로 값을 적어 넣고 픽스처는 다른 상태인 경우를
  이 대조가 잡는다(AC-SAG-007 / 045 R6 이 섹터명을 MANIFEST 에서 읽으므로, MANIFEST 가
  틀리면 그 두 AC 가 틀린 기대값 위에서 GREEN 이 된다).
* **`as_of` 명시 고정** — §8.4 규약 8. `as_of=None`(구현 기본값 → `date.today()`) 의존은
  금지다. W33 이 마감되는 2026-08-17 부터 `as_of_is_partial_week` 가 코드 변경 0줄에
  뒤집힌다.
"""
from __future__ import annotations

import re
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
import yaml

from my_chart.analysis.universe import compute_universe
from my_chart.analysis.weekly_grid import anchor, compute_weekly_grid

# ---------------------------------------------------------------------------
# 경로 · 상수 (임계값은 acceptance.md §8.2 F1~F11 본문 리터럴)
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "frozen"
AGG_DIR = FIXTURES / "aggregation-2026-08-11"
AXIS_DIR = FIXTURES / "weekly-2026-08-12"

AS_OF = "2026-08-11"                 # §8.4 규약 7 — 사용자 결정으로 고정
NH_THRESHOLD = 0.02                  # sector_metrics._NH_THRESHOLD 와 동일 규약
HIGH_WINDOW_DAYS = 364               # 52주
DAILY_WINDOW = ("2026-05-08", "2026-08-11")   # F10 3M 창
INDEX_NAMES = ("KOSPI", "KOSDAQ")

F2_MIN_AG5_SECTORS = 12             # F2 임계 — 음성 검증 시 999 로 임시 상향
F3_EXACT4_SECTOR_COUNT = 2           # F3 — 정확히 4인 섹터 수는 **정확히** 2
F3_MIN_EXACT5_SECTORS = 1
F4_MIN_TOP_WEIGHT_SECTORS = 3
F5_MIN_CAP_MISSING_STOCKS = 5
F5_MIN_RS_MISSING_SECTORS = 3
F6_MIN_CAP_VALID3_SECTORS = 1
F7_MIN_DIVERGENT_STOCKS = 5
F8_MIN_SMA_NULL_STOCKS = 3
F9_MIN_COMPLETE_BARS = 53
F9_ANCHOR_3M = "2026-05-08"

# AC-SAG-046 과 동일해야 하는 날짜 축 파생값(F1 상위집합 성질의 귀결)
EXPECTED_WINDOW_DAYS = {"1w": 11, "1m": 32, "3m": 95}
LABEL_DAYS = {"1w": 7, "1m": 28, "3m": 91}

MANIFEST_FORBIDDEN_PLACEHOLDERS = {"", "TBD", "tbd", "unknown", "UNKNOWN", "None"}
MANIFEST_REQUIRED_KEYS = (
    "as_of", "captured_at", "git_sha",
    "source_weekly_db_mtime", "source_daily_db_mtime", "source_registry_mtime",
    "build_command",
)


# ---------------------------------------------------------------------------
# 픽스처 로딩 · 독립 재산출
# ---------------------------------------------------------------------------

def _weekly_path() -> str:
    return str(AGG_DIR / "weekly.db")


def _daily_path() -> str:
    return str(AGG_DIR / "daily.db")


def _registry_path() -> str:
    return str(AGG_DIR / "registry.xlsx")


@pytest.fixture(scope="module")
def manifest() -> dict:
    """MANIFEST.md 의 기계 판독 YAML 블록(F11)."""
    text = (AGG_DIR / "MANIFEST.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    assert blocks, "F11: MANIFEST.md 에 기계 판독 ```yaml 블록이 없다"
    return yaml.safe_load(blocks[0])


@pytest.fixture(scope="module")
def measured() -> dict:
    """픽스처에서 F1~F10 을 **독립 재산출**한다(build_fixture.py 미import)."""
    grid = compute_weekly_grid(_weekly_path(), as_of=AS_OF)
    snap = compute_universe(_weekly_path(), _daily_path(), _registry_path(), as_of=AS_OF)
    valid = set(snap.valid_names)

    reg = pd.read_excel(_registry_path(), header=8)
    reg = reg.rename(columns={"종목\n코드": "Code", "종목명": "Name", "시장": "Market"})
    reg["Code"] = reg["Code"].astype(str).str.zfill(6)
    reg = reg[~reg["Code"].duplicated(keep="first")]
    sector_of = dict(zip(reg["Name"], reg["산업명(대)"]))
    market_of = dict(zip(reg["Name"], reg["Market"]))

    dconn = sqlite3.connect(_daily_path())
    try:
        caps = dict(dconn.execute("SELECT name, market_cap FROM stock_meta").fetchall())
        closes = dict(dconn.execute("SELECT name, close FROM stock_meta").fetchall())
        daily_vw = dict(dconn.execute(
            "SELECT Name, COUNT(*) FROM stock_prices "
            "WHERE Date BETWEEN ? AND ? AND VolumeWon IS NOT NULL GROUP BY Name",
            DAILY_WINDOW).fetchall())
    finally:
        dconn.close()

    win_start = (date.fromisoformat(AS_OF) - timedelta(days=HIGH_WINDOW_DAYS)).isoformat()
    wconn = sqlite3.connect(_weekly_path())
    try:
        agg_names = {r[0] for r in wconn.execute("SELECT DISTINCT Name FROM stock_prices")}
        agg_dates = {r[0] for r in wconn.execute("SELECT DISTINCT Date FROM stock_prices")}
        latest_rows = wconn.execute(
            "SELECT Name, Close, SMA10, SMA40, MAX52 FROM stock_prices WHERE Date = ?",
            (AS_OF,)).fetchall()
        max_high = dict(wconn.execute(
            "SELECT Name, MAX(High) FROM stock_prices WHERE Date > ? AND Date <= ? "
            "GROUP BY Name", (win_start, AS_OF)).fetchall())
        rs_at_latest = {r[0] for r in wconn.execute(
            "SELECT Name FROM relative_strength WHERE Date = ?", (AS_OF,))}
    finally:
        wconn.close()

    aconn = sqlite3.connect(str(AXIS_DIR / "weekly.db"))
    try:
        axis_names = {r[0] for r in aconn.execute("SELECT DISTINCT Name FROM stock_prices")}
        axis_dates = {r[0] for r in aconn.execute("SELECT DISTINCT Date FROM stock_prices")}
    finally:
        aconn.close()

    members: dict[str, list[str]] = defaultdict(list)
    for n in valid:
        members[sector_of[n]].append(n)

    def cap_ok(n: str) -> bool:
        c = caps.get(n)
        return c is not None and c > 0

    ag5 = {s: ms for s, ms in members.items() if len(ms) >= 5}
    kospi_counts = {s: sum(1 for n in ms if market_of[n] == "KOSPI")
                    for s, ms in members.items()}

    f4 = []
    for s, ms in ag5.items():
        vals = [caps[n] for n in ms if cap_ok(n)]
        if vals and max(vals) / sum(vals) > 0.10:
            f4.append(s)

    f7, f8 = [], []
    for name, close, sma10, sma40, max52 in latest_rows:
        if name in INDEX_NAMES or name not in valid:
            continue
        stored = (close or 0.0) >= (max52 or 0.0) * (1 - NH_THRESHOLD)
        recomputed = (close or 0.0) >= (max_high.get(name) or 0.0) * (1 - NH_THRESHOLD)
        if stored != recomputed:
            f7.append(name)
        if sma40 is None or sma10 is None:
            f8.append(name)

    windows = {}
    for label, days in LABEL_DAYS.items():
        bar = anchor(grid, grid.latest.date, days)
        windows[label] = (
            date.fromisoformat(grid.latest.date) - date.fromisoformat(bar.date)
        ).days if bar else None

    return {
        "grid": grid,
        "snapshot": snap,
        "valid": valid,
        "members": dict(members),
        "agg_names": agg_names,
        "agg_dates": agg_dates,
        "axis_names": axis_names,
        "axis_dates": axis_dates,
        "f2_sectors": sorted(ag5),
        "f3_exact4": sorted(s for s, c in kospi_counts.items() if c == 4),
        "f3_exact5": sorted(s for s, c in kospi_counts.items() if c == 5),
        "f4_sectors": sorted(f4),
        "f5_cap_missing": sorted(n for n in valid if not cap_ok(n)),
        "f5_rs_sectors": sorted({s for s, ms in members.items()
                                 if any(n not in rs_at_latest for n in ms)}),
        "f6_sectors": sorted(s for s, ms in ag5.items()
                             if sum(1 for n in ms if cap_ok(n)) == 3),
        "f7_stocks": sorted(f7),
        "f8_stocks": sorted(f8),
        "f10_meta_missing": sorted(
            n for n in valid if cap_ok(n) and (caps.get(n) is None or closes.get(n) is None)),
        "f10_daily_missing": sorted(n for n in valid if daily_vw.get(n, 0) == 0),
        "windows": windows,
        "cap_ok": cap_ok,
    }


# ---------------------------------------------------------------------------
# 산출물 존재
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", ["weekly.db", "daily.db", "registry.xlsx", "MANIFEST.md"])
def test_ac_sag_048_artifacts_exist(filename: str) -> None:
    """AC-SAG-048 — 집계 픽스처 4개 산출물이 모두 존재한다."""
    p = AGG_DIR / filename
    assert p.exists(), f"집계 픽스처 산출물 누락: {p}"
    assert p.stat().st_size > 0, f"집계 픽스처 산출물이 비어 있다: {p}"


# ---------------------------------------------------------------------------
# F1 ~ F10 — 요건당 1개 단언
# ---------------------------------------------------------------------------

def test_ac_sag_048_f1_superset_of_date_axis_fixture(measured: dict) -> None:
    """F1 — 날짜 축 픽스처의 종목 집합 ⊆ / 날짜 집합 ⊆ 집계 픽스처(상위집합)."""
    missing_names = measured["axis_names"] - measured["agg_names"]
    missing_dates = measured["axis_dates"] - measured["agg_dates"]
    assert not missing_names, f"F1 위반 — 집계 픽스처에 없는 날짜 축 종목: {sorted(missing_names)}"
    assert not missing_dates, f"F1 위반 — 집계 픽스처에 없는 날짜 축 날짜: {sorted(missing_dates)}"


def test_ac_sag_048_f2_ag5_sector_count(measured: dict) -> None:
    """F2 — AG-5(>= 5종목)를 통과하는 섹터 수 >= 12."""
    n = len(measured["f2_sectors"])
    assert n >= F2_MIN_AG5_SECTORS, (
        f"F2 위반 — AG-5 통과 섹터 {n}개 < {F2_MIN_AG5_SECTORS}: {measured['f2_sectors']}")


def test_ac_sag_048_f3_kospi_member_count_shape(measured: dict) -> None:
    """F3 — market=kospi 유효 종목 정확히 4인 섹터 == 2, 정확히 5인 섹터 >= 1."""
    four, five = measured["f3_exact4"], measured["f3_exact5"]
    assert len(four) == F3_EXACT4_SECTOR_COUNT, (
        f"F3 위반 — kospi 유효 종목 정확히 4인 섹터 {len(four)}개 "
        f"(요건 == {F3_EXACT4_SECTOR_COUNT}): {four}")
    assert len(five) >= F3_MIN_EXACT5_SECTORS, (
        f"F3 위반 — kospi 유효 종목 정확히 5인 섹터 {len(five)}개 "
        f"(요건 >= {F3_MIN_EXACT5_SECTORS}): {five}")


def test_ac_sag_048_f4_cap_binding_sectors(measured: dict) -> None:
    """F4 — 최상위 종목의 원비중 > 0.10 인 섹터 >= 3 (상한 재배분이 실제로 구속)."""
    n = len(measured["f4_sectors"])
    assert n >= F4_MIN_TOP_WEIGHT_SECTORS, (
        f"F4 위반 — 최상위 원비중 > 0.10 섹터 {n}개 < {F4_MIN_TOP_WEIGHT_SECTORS}")


def test_ac_sag_048_f5_missing_cap_and_rs(measured: dict) -> None:
    """F5 — market_cap NULL/<=0 종목 >= 5, RS 행 없는 종목을 가진 섹터 >= 3."""
    caps, rs = measured["f5_cap_missing"], measured["f5_rs_sectors"]
    assert len(caps) >= F5_MIN_CAP_MISSING_STOCKS, (
        f"F5 위반 — market_cap NULL/<=0 종목 {len(caps)}개 "
        f"< {F5_MIN_CAP_MISSING_STOCKS}: {caps}")
    assert len(rs) >= F5_MIN_RS_MISSING_SECTORS, (
        f"F5 위반 — RS 결측 종목 보유 섹터 {len(rs)}개 < {F5_MIN_RS_MISSING_SECTORS}: {rs}")


def test_ac_sag_048_f6_ag4_insufficient_sector(measured: dict) -> None:
    """F6 — 유효 시총 종목 수가 정확히 3(AG-4 미달)인 섹터 >= 1."""
    s = measured["f6_sectors"]
    assert len(s) >= F6_MIN_CAP_VALID3_SECTORS, (
        f"F6 위반 — 유효 시총 종목 정확히 3인 섹터 {len(s)}개 "
        f"< {F6_MIN_CAP_VALID3_SECTORS}")


def test_ac_sag_048_f7_nh_verdict_divergence(measured: dict) -> None:
    """F7 — 저장 MAX52 기준과 MAX(High) over 364d 기준의 신고가 판정이 갈리는 종목 >= 5."""
    s = measured["f7_stocks"]
    assert len(s) >= F7_MIN_DIVERGENT_STOCKS, (
        f"F7 위반 — 신고가 판정 분기 종목 {len(s)}개 < {F7_MIN_DIVERGENT_STOCKS}: {s}")


def test_ac_sag_048_f8_sma_null_stocks(measured: dict) -> None:
    """F8 — SMA40 또는 SMA10 이 NULL 인 종목 >= 3."""
    s = measured["f8_stocks"]
    assert len(s) >= F8_MIN_SMA_NULL_STOCKS, (
        f"F8 위반 — SMA 결측 종목 {len(s)}개 < {F8_MIN_SMA_NULL_STOCKS}: {s}")


def test_ac_sag_048_f9_grid_depth_and_anchor(measured: dict) -> None:
    """F9 — 주봉 격자 완성 바 >= 53 이고 3M 앵커 바 2026-05-08 이 존재한다."""
    grid = measured["grid"]
    assert len(grid.history) >= F9_MIN_COMPLETE_BARS, (
        f"F9 위반 — 완성 바 {len(grid.history)}개 < {F9_MIN_COMPLETE_BARS}")
    assert F9_ANCHOR_3M in set(grid.dates), (
        f"F9 위반 — 3M 앵커 바 {F9_ANCHOR_3M} 부재")


def test_ac_sag_048_f10_daily_meta_and_volume_window(measured: dict) -> None:
    """F10 — 전 종목(F5 예외 제외)이 daily stock_meta 에 market_cap·close 를 갖고,
    daily stock_prices 에 3M 창의 VolumeWon 행이 존재한다."""
    assert not measured["f10_meta_missing"], (
        f"F10 위반 — stock_meta 에 market_cap/close 결측: {measured['f10_meta_missing']}")
    assert not measured["f10_daily_missing"], (
        f"F10 위반 — daily VolumeWon 행 부재 {DAILY_WINDOW}: {measured['f10_daily_missing']}")


def test_ac_sag_048_f11_manifest_required_keys(manifest: dict) -> None:
    """F11 — MANIFEST 가 as_of/캡처 시각/git SHA/원본 DB mtime/빌드 명령을
    비어 있지 않은 값으로 담는다."""
    for key in MANIFEST_REQUIRED_KEYS:
        assert key in manifest, f"F11 위반 — MANIFEST 필수 키 누락: {key}"
        val = str(manifest[key]).strip()
        assert val not in MANIFEST_FORBIDDEN_PLACEHOLDERS, (
            f"F11 위반 — MANIFEST['{key}'] 가 플레이스홀더다: {val!r}")
    assert manifest["as_of"] == AS_OF, (
        f"F11 위반 — MANIFEST as_of {manifest['as_of']!r} != {AS_OF!r}")


# ---------------------------------------------------------------------------
# MANIFEST 실측 일치 — 이 절이 핵심 (AC-SAG-048 본문 "And (MANIFEST 실측 일치)")
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("manifest_key", "measured_key"),
    [
        ("f2_ag5_sector_count", "f2_sectors"),
        ("f3_kospi_exactly4_sector_count", "f3_exact4"),
        ("f3_kospi_exactly5_sector_count", "f3_exact5"),
        ("f4_top_weight_gt_10pct_sector_count", "f4_sectors"),
        ("f5_cap_missing_stock_count", "f5_cap_missing"),
        ("f5_rs_missing_sector_count", "f5_rs_sectors"),
        ("f6_cap_valid_exactly3_sector_count", "f6_sectors"),
        ("f7_nh_verdict_divergent_stock_count", "f7_stocks"),
        ("f8_sma_null_stock_count", "f8_stocks"),
    ],
)
def test_ac_sag_048_manifest_counts_match_measured(
    manifest: dict, measured: dict, manifest_key: str, measured_key: str
) -> None:
    """F2~F8 각 요건의 MANIFEST 기록값 == 픽스처 독립 재산출 실측값."""
    assert manifest_key in manifest, f"MANIFEST 키 누락: {manifest_key}"
    assert manifest[manifest_key] == len(measured[measured_key]), (
        f"MANIFEST 불일치 — {manifest_key}: 기록 {manifest[manifest_key]} "
        f"vs 실측 {len(measured[measured_key])} ({measured[measured_key]})")


@pytest.mark.parametrize(
    ("manifest_key", "measured_key"),
    [
        ("f3_kospi_exactly4_sectors", "f3_exact4"),
        ("f3_kospi_exactly5_sectors", "f3_exact5"),
        ("f6_cap_valid_exactly3_sectors", "f6_sectors"),
    ],
)
def test_ac_sag_048_manifest_sector_sets_match_measured(
    manifest: dict, measured: dict, manifest_key: str, measured_key: str
) -> None:
    """F3/F6 은 해당 섹터명 **집합**까지 동등해야 한다 — AC-SAG-007 / 045 R6 이
    섹터명을 MANIFEST 에서 읽으므로, 여기서 갈리면 그 두 AC 가 틀린 기대값 위에서
    GREEN 이 된다."""
    assert manifest_key in manifest, f"MANIFEST 키 누락: {manifest_key}"
    assert set(manifest[manifest_key]) == set(measured[measured_key]), (
        f"MANIFEST 섹터명 집합 불일치 — {manifest_key}: 기록 {sorted(manifest[manifest_key])} "
        f"vs 실측 {measured[measured_key]}")


# ---------------------------------------------------------------------------
# 날짜 축 정합 — AC-SAG-046 과 갈라지지 않음(F1 상위집합 성질의 귀결)
# ---------------------------------------------------------------------------

def test_ac_sag_048_date_axis_parity_with_ac046(measured: dict) -> None:
    """as_of='2026-08-11' 에서 latest/partial/창 일수가 AC-SAG-046 과 동일하다."""
    grid = measured["grid"]
    assert grid.latest is not None, "격자 latest 바 부재"
    assert grid.latest.date == AS_OF, f"latest {grid.latest.date} != {AS_OF}"
    assert grid.latest.is_partial_week is True, "as_of_is_partial_week 가 True 가 아니다"
    assert measured["windows"] == EXPECTED_WINDOW_DAYS, (
        f"창 일수 {measured['windows']} != {EXPECTED_WINDOW_DAYS}")
    assert measured["windows"] != LABEL_DAYS, "창 일수가 라벨 상수와 같다(오구현 신호)"


def test_ac_sag_048_grid_shape_preserved(measured: dict) -> None:
    """집계 픽스처의 날짜 축이 날짜 축 픽스처와 갈라지지 않는다(385 날짜 / 346 바)."""
    grid = measured["grid"]
    assert measured["agg_dates"] == measured["axis_dates"], (
        "집계 픽스처가 날짜 축 픽스처에 없는 날짜를 도입했다: "
        f"{sorted(measured['agg_dates'] - measured['axis_dates'])}")
    assert len(grid.dates) == 346, f"정규 격자 바 {len(grid.dates)} != 346"
    assert grid.exclusions == [], f"CG-3 배제 대표 바 발생: {grid.exclusions}"


# ---------------------------------------------------------------------------
# §8.4 규약 8 — 게이팅 테스트의 as_of 기본값 사용 금지 (정적 자기 스캔)
# ---------------------------------------------------------------------------

def test_gating_test_pins_as_of_explicitly() -> None:
    """이 게이팅 테스트 파일에 `as_of=None` 의존이 0건이고, 격자·유니버스 진입점
    호출에 `as_of=` 키워드가 누락된 호출이 0건이다(§8.4 규약 8)."""
    src = Path(__file__).read_text(encoding="utf-8")
    calls: list[tuple[str, str]] = []
    for m in re.finditer(r"\b(compute_weekly_grid|compute_universe)\(", src):
        depth, i = 1, m.end()
        while i < len(src) and depth:          # 중첩 괄호까지 포함해 인자 전체를 잘라낸다
            depth += (src[i] == "(") - (src[i] == ")")
            i += 1
        calls.append((m.group(1), src[m.end():i - 1]))
    assert calls, "격자·유니버스 진입점 호출을 찾지 못했다(스캔 자체가 무효)"
    for fname, args in calls:
        assert "as_of=" in args, f"{fname} 호출에 as_of= 키워드가 없다: {fname}({args})"
        assert "as_of=None" not in args.replace(" ", ""), (
            f"{fname} 호출이 as_of=None 에 의존한다: {fname}({args})")
