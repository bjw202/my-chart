# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 — AC-SAG-048 (M1.0-a 종료 게이트).

집계 프로즌 픽스처 `tests/fixtures/frozen/aggregation-2026-08-11/` 가 acceptance.md
§8.2 **F1~F13 구조 요건**을 충족하는지 기계적으로 검사한다. 이 테스트의 PASS 가
**M1.0-a 완료 조건**이며, RED 인 상태에서 M1.0-b(골든 baseline 캡처) 착수를 금지한다
(acceptance.md §8.5 강제 순서).

v0.5.0 변경
-----------
* **F4 / F8 폐지** — 소비 AC 가 하나도 없다(acceptance.md §8.2). F4 의 조건은 F12-a 가
  `n >= 11` 제약과 함께 더 강한 형태로 포함한다.
* **F12 신설** — "구조가 효과를 함의한다"는 전제를 폐기하고 **효과 자체**를 검사한다.
* **F13 신설** — 재빌드 구성 계약 6종(§8.2.1). 상위집합 보존(F13-1)이 F5-a / F5-b /
  F6 / F7 의 **유일한 충족 경로**다.
* **F7 규약 Y** — `MAX52` 가 NULL 인 종목을 신·구 양쪽 판정의 분자·분모에서 제외한다.

설계 원칙
---------
* **요건당 1개 단언** — 실패한 요건명이 오류 메시지에 그대로 드러나야 한다.
* **독립 재산출** — `build_fixture.py` 를 import 하지 않는다. 픽스처 DB/xlsx 에서 원시
  컬럼을 직접 읽어 요건을 다시 계산하고, 그 값을 `MANIFEST.md` 의 기계 판독 블록에
  기록된 값과 대조한다. MANIFEST 에 손으로 값을 적어 넣고 픽스처는 다른 상태인 경우를
  이 대조가 잡는다(AC-SAG-007 / 045 R6 이 섹터명을, AC-SAG-002 가 `f12b_*` / `f12c_*`
  집합을 MANIFEST 에서 읽으므로, MANIFEST 가 틀리면 그 AC 들이 틀린 기대값 위에서
  GREEN 이 된다).
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
# 경로 · 상수 (임계값은 acceptance.md §8.2 F1~F13 본문 리터럴)
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "frozen"
AGG_DIR = FIXTURES / "aggregation-2026-08-11"
AXIS_DIR = FIXTURES / "weekly-2026-08-12"
SUPERSET_BASELINE = AGG_DIR / "f13-1-superset-baseline.tsv"

AS_OF = "2026-08-11"                 # §8.4 규약 7 — 사용자 결정으로 고정
NH_THRESHOLD = 0.02                  # sector_metrics._NH_THRESHOLD 와 동일 규약
HIGH_WINDOW_DAYS = 364               # 52주
DAILY_WINDOW = ("2026-05-08", "2026-08-11")   # F10 3M 창
INDEX_NAMES = ("KOSPI", "KOSDAQ")
WEIGHT_CAP = 0.10                    # spec.md D3 — cap_eff = max(WEIGHT_CAP, 1/n)
CAP_DEGENERATE_N = 10                # INV-CAP-1 명제 2 — n <= 10 이면 시총가중 == 등가중
LIVE_SYNTHETIC_SOURCE_BAR = "2026-08-12"      # F13-6 — 재라벨 원본 라이브 바

F2_MIN_AG5_SECTORS = 12              # F2 임계 — 음성 검증 시 999 로 임시 상향
F3_EXACT4_SECTOR_COUNT = 2           # F3 — 정확히 4인 섹터 수는 **정확히** 2
F3_MIN_EXACT5_SECTORS = 1
F5A_MIN_CAP_MISSING_STOCKS = 5
F5B_MIN_RS_MISSING_SECTORS = 3
F6_MIN_CAP_VALID3_SECTORS = 1
F7_MIN_DIVERGENT_STOCKS = 5
F9_MIN_COMPLETE_BARS = 53
F9_ANCHOR_3M = "2026-05-08"
F12A_MIN_SECTORS = 12                # F12-a 임계 — 음성 검증 시 999 로 임시 상향
F12A_MIN_CAP_VALID_N = 11            # 상한 재배분 관측 가능성 하한 (INV-CAP-1 명제 2)
F12B_MIN_SECTORS = 3                 # 계약 임계
F12B_DELTA_THRESHOLD = 0.005         # 0.5%p
F12C_MIN_SECTORS = 5                 # 계약 임계
F13_2_MIN_LARGE_SECTORS = 14
F13_2_LARGE_N = 15
F13_3_MIN_F12B = 9                   # 빌드 목표 — 계약 임계(3)보다 높다
F13_3_MIN_F12C = 9                   # 빌드 목표 — 계약 임계(5)보다 높다
F13_4_FASHION_MEMBERS = 5
F13_4_FASHION_CAP_VALID = 3
F13_5_MIN_AG5_PER_MARKET = 1

# AC-SAG-046 과 동일해야 하는 날짜 축 파생값(F1 상위집합 성질의 귀결)
EXPECTED_WINDOW_DAYS = {"1w": 11, "1m": 32, "3m": 95}
LABEL_DAYS = {"1w": 7, "1m": 28, "3m": 91}

MANIFEST_FORBIDDEN_PLACEHOLDERS = {"", "TBD", "tbd", "unknown", "UNKNOWN", "None"}
MANIFEST_REQUIRED_KEYS = (
    "as_of", "captured_at", "git_sha",
    "source_weekly_db_mtime", "source_daily_db_mtime", "source_registry_mtime",
    "build_command",
)
MANIFEST_SYNTHETIC_BAR_KEYS = (
    "source_live_bar_date", "relabeled_to_date", "transformation", "reproduce_command",
)


# ---------------------------------------------------------------------------
# 참조 구현 — 프로덕션 경로를 호출하지 않는다 (§8.3 · Lesson #9)
# ---------------------------------------------------------------------------

def _capped_weights(caps: list[float], cap: float = WEIGHT_CAP) -> list[float]:
    """상한 재배분 시총가중 (INV-CAP-1 · AC-SAG-049 동결형).

    `cap_eff = max(cap, 1/n)`. `n <= 1/cap` 이면 `cap_eff = 1/n` 이므로 제약 집합의
    해가 **균등 하나뿐**이다(축퇴). 상한에 걸린 종목은 **동결**해 재배분 집합에서 뺀다.
    """
    n = len(caps)
    total = sum(caps)
    if n == 0 or total <= 0:
        return []
    raw = [c / total for c in caps]
    cap_eff = max(cap, 1.0 / n)
    w = list(raw)
    frozen: set[int] = set()
    for _ in range(min(n, 20) + 1):
        over = [i for i in range(n) if i not in frozen and w[i] > cap_eff + 1e-15]
        if not over:
            break
        for i in over:
            w[i] = cap_eff
            frozen.add(i)
        free = [i for i in range(n) if i not in frozen]
        s = sum(raw[i] for i in free)
        if not free or s <= 0:
            break
        rem = 1.0 - cap_eff * len(frozen)
        for i in free:
            w[i] = raw[i] * rem / s
    return w


def _f12_reference(wpath: str, members: dict[str, list[str]], caps: dict[str, float],
                   anchor_1m: str) -> dict:
    """F12-b / F12-c 참조 산출 — §8.3 제외·null 처리 계약 + R-C8 산출 범위.

    범위: `market=all`, **AG-5 통과 섹터 한정**, **AG-4 미달(유효 시총 < 5) 섹터는
    양쪽 집합에서 제외**, `period=1m`.

    * **AG-3** — `market_cap` NULL/`<=0` 종목은 시총가중 분자·분모에서 **제외**하되
      등가중 분모에는 **포함**한다(AC-SAG-005 와 동형).
    * **AG-7** — 1M 수익률 산출 가능 종목 비율이 `< 0.50` 인 섹터는 null 로 취급한다.
    """
    conn = sqlite3.connect(wpath)
    try:
        latest = dict(conn.execute(
            "SELECT Name, Close FROM stock_prices WHERE Date = ?", (AS_OF,)))
        base = dict(conn.execute(
            "SELECT Name, Close FROM stock_prices WHERE Date = ?", (anchor_1m,)))
    finally:
        conn.close()

    def ret_1m(n: str):
        a, b = latest.get(n), base.get(n)
        if a is None or b is None or b == 0:
            return None
        return a / b - 1.0

    cap_vals: dict[str, float] = {}
    eq_vals: dict[str, float] = {}
    for sector, ms in members.items():
        if len(ms) < 5:                                   # AG-5
            continue
        rets = {n: ret_1m(n) for n in ms}
        avail = [n for n in ms if rets[n] is not None]
        if not avail or len(avail) / len(ms) < 0.50:      # AG-7
            continue
        cap_members = [n for n in avail if caps.get(n) is not None and caps[n] > 0]
        if len(cap_members) < 5:                          # AG-4 — 양쪽 집합에서 제외
            continue
        w = _capped_weights([caps[n] for n in cap_members])
        cap_vals[sector] = sum(wi * rets[n] for wi, n in zip(w, cap_members))
        eq_vals[sector] = sum(rets[n] for n in avail) / len(avail)

    def ranks(vals: dict[str, float]) -> dict[str, int]:
        return {s: i + 1 for i, s in enumerate(sorted(vals, key=lambda x: (-vals[x], x)))}

    r_cap, r_eq = ranks(cap_vals), ranks(eq_vals)
    return {
        "eligible": sorted(cap_vals),
        "delta": {s: cap_vals[s] - eq_vals[s] for s in cap_vals},
        "f12b": sorted(s for s in cap_vals
                       if abs(cap_vals[s] - eq_vals[s]) >= F12B_DELTA_THRESHOLD),
        "f12c": sorted(s for s in cap_vals if r_cap[s] != r_eq[s]),
    }


def _load_superset_baseline() -> dict[str, str]:
    """F13-1 기준 종목 목록 — `{종목명: 섹터}` (지수 행 섹터는 `-`)."""
    out: dict[str, str] = {}
    for line in SUPERSET_BASELINE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, _, sector = line.partition("\t")
        out[name] = sector
    return out


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
    """픽스처에서 F1~F13 을 **독립 재산출**한다(build_fixture.py 미import)."""
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
            "SELECT Name, Close, MAX52 FROM stock_prices WHERE Date = ?", (AS_OF,)).fetchall()
        max_high = dict(wconn.execute(
            "SELECT Name, MAX(High) FROM stock_prices WHERE Date > ? AND Date <= ? "
            "GROUP BY Name", (win_start, AS_OF)).fetchall())
        rs_at_latest = {r[0] for r in wconn.execute(
            "SELECT Name FROM relative_strength WHERE Date = ?", (AS_OF,))}
        as_of_rows = wconn.execute(
            "SELECT COUNT(*) FROM stock_prices WHERE Date = ?", (AS_OF,)).fetchone()[0]
        live_bar_rows = wconn.execute(
            "SELECT COUNT(*) FROM stock_prices WHERE Date = ?",
            (LIVE_SYNTHETIC_SOURCE_BAR,)).fetchone()[0]
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
    n_cap = {s: sum(1 for n in ms if cap_ok(n)) for s, ms in members.items()}

    # --- F7 규약 Y (+ 폐기된 규약 X 대조) --------------------------------------
    f7_y, f7_null, f7_x = [], [], []
    for name, close, max52 in latest_rows:
        if name in INDEX_NAMES or name not in valid:
            continue
        mh = max_high.get(name)
        if ((close or 0.0) >= (max52 or 0.0) * (1 - NH_THRESHOLD)) != \
           ((close or 0.0) >= (mh or 0.0) * (1 - NH_THRESHOLD)):
            f7_x.append(name)                             # 규약 X (폐기)
        if max52 is None:
            f7_null.append(name)
            continue                                      # 규약 Y — 분자·분모에서 제외
        if mh is None or close is None:
            continue
        if (close >= max52 * (1 - NH_THRESHOLD)) != (close >= mh * (1 - NH_THRESHOLD)):
            f7_y.append(name)

    # --- F12 ------------------------------------------------------------------
    anchor_1m = anchor(grid, grid.latest.date, LABEL_DAYS["1m"]).date
    f12 = _f12_reference(_weekly_path(), dict(members), caps, anchor_1m)
    f12a = sorted(
        s for s, ms in ag5.items()
        if n_cap[s] >= F12A_MIN_CAP_VALID_N
        and (lambda vs: bool(vs) and max(vs) / sum(vs) > WEIGHT_CAP)(
            [caps[n] for n in ms if cap_ok(n)])
    )

    # --- F13 ------------------------------------------------------------------
    superset = _load_superset_baseline()

    windows = {}
    for label, days in LABEL_DAYS.items():
        bar = anchor(grid, grid.latest.date, days)
        windows[label] = (
            date.fromisoformat(grid.latest.date) - date.fromisoformat(bar.date)
        ).days if bar else None

    return {
        "grid": grid,
        "valid": valid,
        "members": dict(members),
        "n_cap": n_cap,
        "agg_names": agg_names,
        "agg_dates": agg_dates,
        "axis_names": axis_names,
        "axis_dates": axis_dates,
        "f2_sectors": sorted(ag5),
        "f3_exact4": sorted(s for s, c in kospi_counts.items() if c == 4),
        "f3_exact5": sorted(s for s, c in kospi_counts.items() if c == 5),
        "f5a_cap_missing": sorted(n for n in valid if not cap_ok(n)),
        "f5b_rs_sectors": sorted({s for s, ms in members.items()
                                  if any(n not in rs_at_latest for n in ms)}),
        "f6_sectors": sorted(s for s, ms in ag5.items() if n_cap[s] == 3),
        "f7_stocks": sorted(f7_y),
        "f7_null_max52": sorted(f7_null),
        "f7_convention_x": sorted(f7_x),
        "f10_meta_missing": sorted(
            n for n in valid if cap_ok(n) and (caps.get(n) is None or closes.get(n) is None)),
        "f10_daily_missing": sorted(n for n in valid if daily_vw.get(n, 0) == 0),
        "f12a_sectors": f12a,
        "f12b_sectors": f12["f12b"],
        "f12c_sectors": f12["f12c"],
        "f12_eligible": f12["eligible"],
        "f12_anchor_1m": anchor_1m,
        "f12_delta": f12["delta"],
        "f13_1_baseline": superset,
        "f13_1_missing": sorted(set(superset) - agg_names),
        "f13_1_sector_drift": sorted(
            n for n, s in superset.items()
            if s != "-" and n in sector_of and sector_of[n] != s),
        "f13_2_large_sectors": sorted(s for s, c in n_cap.items() if c >= F13_2_LARGE_N),
        "f13_5_kospi_ag5": sorted(
            s for s, ms in members.items()
            if sum(1 for n in ms if market_of[n] == "KOSPI") >= 5),
        "f13_5_kosdaq_ag5": sorted(
            s for s, ms in members.items()
            if sum(1 for n in ms if market_of[n] == "KOSDAQ") >= 5),
        "f13_5_kospi_universe": sum(1 for n in valid if market_of[n] == "KOSPI"),
        "f13_5_kosdaq_universe": sum(1 for n in valid if market_of[n] == "KOSDAQ"),
        "f13_6_as_of_rows": as_of_rows,
        "f13_6_live_source_bar_rows": live_bar_rows,
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# 산출물 존재
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "filename",
    ["weekly.db", "daily.db", "registry.xlsx", "MANIFEST.md",
     "f13-1-superset-baseline.tsv"],
)
def test_ac_sag_048_artifacts_exist(filename: str) -> None:
    """AC-SAG-048 — 집계 픽스처 산출물이 모두 존재한다."""
    p = AGG_DIR / filename
    assert p.exists(), f"집계 픽스처 산출물 누락: {p}"
    assert p.stat().st_size > 0, f"집계 픽스처 산출물이 비어 있다: {p}"


# ---------------------------------------------------------------------------
# F1 ~ F11 — 요건당 1개 단언 (F4 / F8 은 v0.5.0 에서 폐지)
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


def test_ac_sag_048_f5a_missing_market_cap_stocks(measured: dict) -> None:
    """F5-a — market_cap 이 NULL 또는 <= 0 인 종목 >= 5 (AG-3 분기 발화)."""
    s = measured["f5a_cap_missing"]
    assert len(s) >= F5A_MIN_CAP_MISSING_STOCKS, (
        f"F5-a 위반 — market_cap NULL/<=0 종목 {len(s)}개 "
        f"< {F5A_MIN_CAP_MISSING_STOCKS}: {s}")


def test_ac_sag_048_f5b_rs_missing_sectors(measured: dict) -> None:
    """F5-b — RS 행이 없는 종목을 가진 섹터 >= 3."""
    s = measured["f5b_rs_sectors"]
    assert len(s) >= F5B_MIN_RS_MISSING_SECTORS, (
        f"F5-b 위반 — RS 결측 종목 보유 섹터 {len(s)}개 "
        f"< {F5B_MIN_RS_MISSING_SECTORS}: {s}")


def test_ac_sag_048_f6_ag4_insufficient_sector(measured: dict) -> None:
    """F6 — 유효 시총 종목 수가 정확히 3(AG-4 미달)인 섹터 >= 1."""
    s = measured["f6_sectors"]
    assert len(s) >= F6_MIN_CAP_VALID3_SECTORS, (
        f"F6 위반 — 유효 시총 종목 정확히 3인 섹터 {len(s)}개 "
        f"< {F6_MIN_CAP_VALID3_SECTORS}")


def test_ac_sag_048_f7_nh_verdict_divergence_convention_y(measured: dict) -> None:
    """F7 (규약 Y) — 저장 MAX52 기준과 MAX(High) over 364d 기준의 신고가 판정이
    갈리는 종목 >= 5. **MAX52 가 NULL 인 종목은 양 기준의 분자·분모에서 제외**한다."""
    s = measured["f7_stocks"]
    assert len(s) >= F7_MIN_DIVERGENT_STOCKS, (
        f"F7 위반 — 신고가 판정 분기 종목 {len(s)}개 < {F7_MIN_DIVERGENT_STOCKS}: {s}")


def test_ac_sag_048_f7_convention_y_differs_from_x(measured: dict) -> None:
    """F7 — 규약 Y 와 폐기된 규약 X(NULL MAX52 → 0.0 치환)의 계수가 **다르다**.

    두 값이 같으면 NULL `MAX52` 종목이 0개라는 뜻이므로 규약 선택이 무증상이었음을
    뜻한다 — 그 경우 이 픽스처는 AC-SAG-024 의 규약 Y 절을 게이팅하지 못한다.
    차이는 정확히 NULL `MAX52` 종목 수여야 한다(규약 X 는 `Close >= 0` 을 항상 참으로
    만들어 결측 처리 차이를 실질 판정 차이로 오계상한다).
    """
    y, x, nulls = (measured["f7_stocks"], measured["f7_convention_x"],
                   measured["f7_null_max52"])
    assert len(nulls) > 0, "F7 위반 — NULL MAX52 종목이 0개면 규약 Y 선택이 무증상이다"
    assert len(x) != len(y), (
        f"F7 위반 — 규약 X({len(x)}) 와 규약 Y({len(y)}) 계수가 같다(규약 무증상)")
    assert len(x) - len(y) == len(nulls), (
        f"F7 위반 — 규약 차이 {len(x) - len(y)} != NULL MAX52 종목 수 {len(nulls)}")


def test_ac_sag_048_f9_grid_depth_and_anchor(measured: dict) -> None:
    """F9 — 주봉 격자 완성 바 >= 53 이고 3M 앵커 바 2026-05-08 이 존재한다."""
    grid = measured["grid"]
    assert len(grid.history) >= F9_MIN_COMPLETE_BARS, (
        f"F9 위반 — 완성 바 {len(grid.history)}개 < {F9_MIN_COMPLETE_BARS}")
    assert F9_ANCHOR_3M in set(grid.dates), (
        f"F9 위반 — 3M 앵커 바 {F9_ANCHOR_3M} 부재")


def test_ac_sag_048_f10_daily_meta_and_volume_window(measured: dict) -> None:
    """F10 — 전 종목(F5-a 예외 제외)이 daily stock_meta 에 market_cap·close 를 갖고,
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


def test_ac_sag_048_f11_manifest_synthetic_bar_block(manifest: dict) -> None:
    """F11 / F13-6 — MANIFEST `synthetic_bar` 가 §8.1.1 의 4항목을 비어 있지 않은
    값으로 담는다: 원본 라이브 바 날짜 / 재라벨 대상 날짜 / 값이 아니라 날짜 라벨만
    바꿨다는 진술 / 재현 명령."""
    assert "synthetic_bar" in manifest, "F11 위반 — MANIFEST 에 synthetic_bar 블록이 없다"
    sb = manifest["synthetic_bar"]
    assert isinstance(sb, dict), f"F11 위반 — synthetic_bar 가 매핑이 아니다: {sb!r}"
    for key in MANIFEST_SYNTHETIC_BAR_KEYS:
        assert key in sb, f"F11 위반 — synthetic_bar 필수 항목 누락: {key}"
        val = str(sb[key]).strip()
        assert val not in MANIFEST_FORBIDDEN_PLACEHOLDERS, (
            f"F11 위반 — synthetic_bar['{key}'] 가 플레이스홀더다: {val!r}")
    assert sb["source_live_bar_date"] == LIVE_SYNTHETIC_SOURCE_BAR, (
        f"F11 위반 — synthetic_bar 원본 바 {sb['source_live_bar_date']!r} "
        f"!= {LIVE_SYNTHETIC_SOURCE_BAR!r}")
    assert sb["relabeled_to_date"] == AS_OF, (
        f"F11 위반 — synthetic_bar 재라벨 대상 {sb['relabeled_to_date']!r} != {AS_OF!r}")


# ---------------------------------------------------------------------------
# F12 — 효과 요건 (v0.4.2 신설 · D16)
# ---------------------------------------------------------------------------

def test_ac_sag_048_f12a_observable_cap_redistribution_sectors(measured: dict) -> None:
    """F12-a — 유효 시총 종목 수 `n >= 11` **이고** 최상위 원비중 > 0.10 인 섹터 >= 12.

    `n <= 10` 에서는 `cap_eff = 1/n` 이라 `n × cap_eff = 1` 이 되어 상한 재배분의 해가
    균등 하나뿐이다 — 상한 재배분이 **관측 가능한 하한이 `n = 11`** 이다(INV-CAP-1 명제 2).
    """
    s = measured["f12a_sectors"]
    assert len(s) >= F12A_MIN_SECTORS, (
        f"F12-a 위반 — n >= {F12A_MIN_CAP_VALID_N} 이고 최상위 원비중 > {WEIGHT_CAP} 인 "
        f"섹터 {len(s)}개 < {F12A_MIN_SECTORS}: {s} "
        f"(섹터별 유효 시총 종목 수: {measured['n_cap']})")


def test_ac_sag_048_f12b_cap_vs_equal_weight_delta(measured: dict) -> None:
    """F12-b — 1M 시총가중 값과 등가중 값의 차가 >= 0.5%p 인 섹터 >= 3."""
    s = measured["f12b_sectors"]
    assert len(s) >= F12B_MIN_SECTORS, (
        f"F12-b 위반 — |시총가중 − 등가중| >= {F12B_DELTA_THRESHOLD} 섹터 {len(s)}개 "
        f"< {F12B_MIN_SECTORS}: {s} "
        f"(섹터별 차: { {k: round(v, 6) for k, v in measured['f12_delta'].items()} })")


def test_ac_sag_048_f12c_cap_vs_equal_weight_rank_shift(measured: dict) -> None:
    """F12-c — 1M 시총가중 순위와 등가중 순위가 다른 섹터 >= 5."""
    s = measured["f12c_sectors"]
    assert len(s) >= F12C_MIN_SECTORS, (
        f"F12-c 위반 — 시총가중 순위 != 등가중 순위 섹터 {len(s)}개 "
        f"< {F12C_MIN_SECTORS}: {s}")


def test_ac_sag_048_f12_no_degenerate_sector(measured: dict) -> None:
    """F12 축퇴 방지 절 (v0.4.2 D16) — F12-a 를 만족하는 섹터 중 `n <= 10` 인 섹터가
    0개다. 아울러 F12-b / F12-c 집합에도 `n <= 10` 섹터가 들어 있지 않다.

    `n <= 10` 섹터의 시총가중 값은 등가중과 **비트 단위로 동일**해지므로
    (INV-CAP-1 명제 2 · AC-SAG-001 A), 그런 섹터가 이 집합들에 들어 있다면 참조 구현의
    결함이다.
    """
    n_cap = measured["n_cap"]
    for key in ("f12a_sectors", "f12b_sectors", "f12c_sectors"):
        degenerate = sorted(s for s in measured[key] if n_cap[s] <= CAP_DEGENERATE_N)
        assert not degenerate, (
            f"F12 축퇴 방지 위반 — {key} 에 n <= {CAP_DEGENERATE_N} 섹터가 있다: "
            f"{ {s: n_cap[s] for s in degenerate} }")


# ---------------------------------------------------------------------------
# F13 — 재빌드 구성 계약 (v0.5.0 신설 · §8.2.1)
# ---------------------------------------------------------------------------

def test_ac_sag_048_f13_1_superset_preserved(measured: dict, manifest: dict) -> None:
    """F13-1 [HARD] — 재빌드 종목 집합이 기준 빌드의 종목 집합을 **전량 포함**하고,
    그 종목들의 섹터 배정이 보존된다.

    기준 종목 목록은 MANIFEST `f13_1_superset_of` 가 가리키는 빌드 식별자의 목록
    (`f13_1_baseline_list`)에서 읽는다. 이 상위집합이 F5-a / F5-b / F6 / F7 의 **유일한
    충족 경로**다 — 신규 시총순 선정 단독으로는 각각 0 / 3섹터 / 소멸 / 2 로 전부 미달한다.
    """
    assert manifest.get("f13_1_superset_of"), "F13-1 위반 — MANIFEST f13_1_superset_of 부재"
    assert manifest.get("f13_1_baseline_list") == SUPERSET_BASELINE.name, (
        f"F13-1 위반 — MANIFEST f13_1_baseline_list "
        f"{manifest.get('f13_1_baseline_list')!r} != {SUPERSET_BASELINE.name!r}")
    assert manifest["f13_1_baseline_stock_count"] == len(measured["f13_1_baseline"]), (
        f"F13-1 위반 — MANIFEST 기준 종목 수 {manifest['f13_1_baseline_stock_count']} "
        f"vs 목록 실측 {len(measured['f13_1_baseline'])}")
    assert not measured["f13_1_missing"], (
        f"F13-1 위반 — 상위집합 종목이 재빌드에 없다: {measured['f13_1_missing']}")
    assert not measured["f13_1_sector_drift"], (
        f"F13-1 위반 — 상위집합 종목의 섹터 배정이 바뀌었다: "
        f"{measured['f13_1_sector_drift']}")


def test_ac_sag_048_f13_2_large_sector_breadth(measured: dict) -> None:
    """F13-2 — 유효 시총 종목 수 `n >= 15` 인 섹터 >= 14 (F12-a 하한 11보다 강한 빌드 목표)."""
    s = measured["f13_2_large_sectors"]
    assert len(s) >= F13_2_MIN_LARGE_SECTORS, (
        f"F13-2 위반 — n >= {F13_2_LARGE_N} 섹터 {len(s)}개 "
        f"< {F13_2_MIN_LARGE_SECTORS}: {s} (섹터별 n: {measured['n_cap']})")


def test_ac_sag_048_f13_3_f12_headroom(measured: dict) -> None:
    """F13-3 [R-C1] — F12-b >= 9 **이고** F12-c >= 9.

    계약 임계(F12-b >= 3 / F12-c >= 5)보다 높은 **빌드 목표**다. 이 절이 RED 면 구성이
    임계에 붙어 있다는 뜻이므로 재구성한다 — 임계에 붙여 빌드하면 안 된다.
    """
    b, c = len(measured["f12b_sectors"]), len(measured["f12c_sectors"])
    assert b >= F13_3_MIN_F12B, (
        f"F13-3 위반 — F12-b {b}개 < 빌드 목표 {F13_3_MIN_F12B} "
        f"(계약 임계 {F12B_MIN_SECTORS}): {measured['f12b_sectors']}")
    assert c >= F13_3_MIN_F12C, (
        f"F13-3 위반 — F12-c {c}개 < 빌드 목표 {F13_3_MIN_F12C} "
        f"(계약 임계 {F12C_MIN_SECTORS}): {measured['f12c_sectors']}")


def test_ac_sag_048_f13_4_small_sectors_preserved(measured: dict) -> None:
    """F13-4 [R-C5] — `패션`은 구성종목 5 / 유효 시총 3 을 유지하고, F3 의 KOSPI
    정확히-4 섹터 2개와 정확히-5 섹터 1개가 그대로 유지된다(F3 검사와 집합 동등).

    이 섹터들에 대형 구성을 배정하면 F3 · F6 과 §8.3 의 AG-4/AG-5 분기가 함께 소멸하고
    AC-SAG-007 / 013 / 045 R6 이 동시에 무게이팅이 된다.
    """
    fashion = measured["members"].get("패션", [])
    assert len(fashion) == F13_4_FASHION_MEMBERS, (
        f"F13-4 위반 — 패션 구성종목 {len(fashion)} != {F13_4_FASHION_MEMBERS}: "
        f"{sorted(fashion)}")
    assert measured["n_cap"].get("패션") == F13_4_FASHION_CAP_VALID, (
        f"F13-4 위반 — 패션 유효 시총 종목 {measured['n_cap'].get('패션')} "
        f"!= {F13_4_FASHION_CAP_VALID}")
    assert set(measured["f6_sectors"]) == {"패션"}, (
        f"F13-4 위반 — AG-4 미달(유효 시총 정확히 3) 섹터 집합이 패션 단독이 아니다: "
        f"{measured['f6_sectors']}")
    assert len(measured["f3_exact4"]) == F3_EXACT4_SECTOR_COUNT, (
        f"F13-4 위반 — F3 KOSPI 정확히-4 섹터 {measured['f3_exact4']} "
        f"(요건 {F3_EXACT4_SECTOR_COUNT}개)")
    assert len(measured["f3_exact5"]) >= F3_MIN_EXACT5_SECTORS, (
        f"F13-4 위반 — F3 KOSPI 정확히-5 섹터 {measured['f3_exact5']}")


def test_ac_sag_048_f13_5_both_markets_non_empty(measured: dict) -> None:
    """F13-5 [R-C7] — market=kospi / market=kosdaq 유니버스가 각각 비어 있지 않고,
    각각 AG-5 통과 섹터를 >= 1개 갖는다.

    AC-SAG-011 의 "세 벤치마크 값이 쌍마다 다르다" 절이 이를 전제한다 — 한쪽이 비면
    `all == 그쪽`이 되어 즉시 붕괴한다.
    """
    assert measured["f13_5_kospi_universe"] > 0, "F13-5 위반 — kospi 유니버스가 비어 있다"
    assert measured["f13_5_kosdaq_universe"] > 0, "F13-5 위반 — kosdaq 유니버스가 비어 있다"
    assert len(measured["f13_5_kospi_ag5"]) >= F13_5_MIN_AG5_PER_MARKET, (
        f"F13-5 위반 — kospi AG-5 통과 섹터 {measured['f13_5_kospi_ag5']}")
    assert len(measured["f13_5_kosdaq_ag5"]) >= F13_5_MIN_AG5_PER_MARKET, (
        f"F13-5 위반 — kosdaq AG-5 통과 섹터 {measured['f13_5_kosdaq_ag5']}")


def test_ac_sag_048_f13_6_synthetic_bar_relabeled(measured: dict) -> None:
    """F13-6 [§8.1.1] — `stock_prices` 에 `2026-08-11` 행이 존재하고 `2026-08-12` 행이
    **존재하지 않는다**(재라벨링이 수행됐음의 구조적 증거).

    재라벨링을 빠뜨리면 `as_of` 가 `2026-08-12` 가 되어 AC-SAG-046 의 창 리터럴이
    `{11,32,95}` → `{12,33,96}` 으로 전부 RED 가 된다.
    """
    assert measured["f13_6_as_of_rows"] > 0, (
        f"F13-6 위반 — {AS_OF} 행이 없다")
    assert measured["f13_6_live_source_bar_rows"] == 0, (
        f"F13-6 위반 — 재라벨 원본 바 {LIVE_SYNTHETIC_SOURCE_BAR} 행이 "
        f"{measured['f13_6_live_source_bar_rows']}개 남아 있다(재라벨링 미수행)")


# ---------------------------------------------------------------------------
# MANIFEST 실측 일치 — 이 절이 핵심 (AC-SAG-048 본문 "And (MANIFEST 실측 일치)")
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("manifest_key", "measured_key"),
    [
        ("f2_ag5_sector_count", "f2_sectors"),
        ("f3_kospi_exactly4_sector_count", "f3_exact4"),
        ("f3_kospi_exactly5_sector_count", "f3_exact5"),
        ("f5_cap_missing_stock_count", "f5a_cap_missing"),
        ("f5_rs_missing_sector_count", "f5b_rs_sectors"),
        ("f6_cap_valid_exactly3_sector_count", "f6_sectors"),
        ("f7_nh_verdict_divergent_stock_count", "f7_stocks"),
        ("f7_max52_null_stock_count", "f7_null_max52"),
        ("f7_convention_x_divergent_stock_count", "f7_convention_x"),
        ("f10_meta_missing_stock_count", "f10_meta_missing"),
        ("f10_daily_volume_missing_stock_count", "f10_daily_missing"),
        ("f12a_n_ge_11_top_gt_10pct_sector_count", "f12a_sectors"),
        ("f12b_delta_ge_50bp_sector_count", "f12b_sectors"),
        ("f12c_rank_shifted_sector_count", "f12c_sectors"),
        ("f12_eligible_sector_count", "f12_eligible"),
        ("f13_1_missing_stock_count", "f13_1_missing"),
        ("f13_2_n_ge_15_sector_count", "f13_2_large_sectors"),
        ("f13_5_kospi_ag5_sector_count", "f13_5_kospi_ag5"),
        ("f13_5_kosdaq_ag5_sector_count", "f13_5_kosdaq_ag5"),
    ],
)
def test_ac_sag_048_manifest_counts_match_measured(
    manifest: dict, measured: dict, manifest_key: str, measured_key: str
) -> None:
    """F2~F13 각 요건의 MANIFEST 기록값 == 픽스처 독립 재산출 실측값."""
    assert manifest_key in manifest, f"MANIFEST 키 누락: {manifest_key}"
    assert manifest[manifest_key] == len(measured[measured_key]), (
        f"MANIFEST 불일치 — {manifest_key}: 기록 {manifest[manifest_key]} "
        f"vs 실측 {len(measured[measured_key])} ({measured[measured_key]})")


@pytest.mark.parametrize(
    ("manifest_key", "measured_key"),
    [
        ("f2_ag5_sectors", "f2_sectors"),
        ("f3_kospi_exactly4_sectors", "f3_exact4"),
        ("f3_kospi_exactly5_sectors", "f3_exact5"),
        ("f6_cap_valid_exactly3_sectors", "f6_sectors"),
        ("f12a_sectors", "f12a_sectors"),
        ("f12b_delta_ge_50bp_sectors_1m", "f12b_sectors"),
        ("f12c_rank_shifted_sectors_1m", "f12c_sectors"),
        ("f13_2_n_ge_15_sectors", "f13_2_large_sectors"),
    ],
)
def test_ac_sag_048_manifest_sector_sets_match_measured(
    manifest: dict, measured: dict, manifest_key: str, measured_key: str
) -> None:
    """F3 / F6 / F12-b / F12-c 등은 해당 섹터명 **집합**까지 동등해야 한다 —
    AC-SAG-007 / 045 R6 이 섹터명을, AC-SAG-002 가 `f12b_*` / `f12c_*` 집합을 MANIFEST
    에서 읽으므로, 여기서 갈리면 그 AC 들이 틀린 기대값 위에서 GREEN 이 된다."""
    assert manifest_key in manifest, f"MANIFEST 키 누락: {manifest_key}"
    assert set(manifest[manifest_key]) == set(measured[measured_key]), (
        f"MANIFEST 섹터명 집합 불일치 — {manifest_key}: 기록 {sorted(manifest[manifest_key])} "
        f"vs 실측 {measured[measured_key]}")


@pytest.mark.parametrize(
    ("manifest_key", "measured_key"),
    [
        ("f9_complete_bar_count", "grid_history_len"),
        ("f12_anchor_1m", "f12_anchor_1m"),
        ("f13_4_fashion_member_count", "fashion_members"),
        ("f13_4_fashion_cap_valid_count", "fashion_cap_valid"),
        ("f13_5_kospi_universe_size", "f13_5_kospi_universe"),
        ("f13_5_kosdaq_universe_size", "f13_5_kosdaq_universe"),
        ("f13_6_as_of_row_count", "f13_6_as_of_rows"),
        ("f13_6_live_source_bar_row_count", "f13_6_live_source_bar_rows"),
    ],
)
def test_ac_sag_048_manifest_scalars_match_measured(
    manifest: dict, measured: dict, manifest_key: str, measured_key: str
) -> None:
    """F9 / F12 앵커 / F13-4 / F13-5 / F13-6 스칼라 기록값 == 독립 재산출 실측값."""
    scalars = dict(measured)
    scalars["grid_history_len"] = len(measured["grid"].history)
    scalars["fashion_members"] = len(measured["members"].get("패션", []))
    scalars["fashion_cap_valid"] = measured["n_cap"].get("패션", 0)
    assert manifest_key in manifest, f"MANIFEST 키 누락: {manifest_key}"
    assert manifest[manifest_key] == scalars[measured_key], (
        f"MANIFEST 불일치 — {manifest_key}: 기록 {manifest[manifest_key]!r} "
        f"vs 실측 {scalars[measured_key]!r}")


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
