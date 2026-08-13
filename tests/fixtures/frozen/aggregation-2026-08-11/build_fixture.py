#!/usr/bin/env python3
# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M1.0-a — 집계 프로즌 픽스처 빌드.

acceptance.md §8.2 F1~F13 의 **구조 요건**을 충족하는 집계 픽스처를 라이브 DB 에서
결정론적으로 재구성한다. 값(어느 섹터가 몇 %인지)은 규정하지 않으며, 요건 충족
실측값만 `MANIFEST.md` 에 기록한다(F11).

**v0.5.0 재빌드** — 이전 빌드(`adb1f25`)는 F1~F11 을 전부 충족하고 AC-SAG-048 도 PASS
였으나, AG-5 통과 18섹터 중 유효 시총 `n > 10` 이 게임 하나뿐이라 INV-CAP-1 축퇴
(`cap_eff = max(0.10, 1/n)`, `n <= 10` 이면 시총가중 == 등가중)에 걸려 AC-SAG-002 를
**완전한 무게이팅**으로 만들었다. 본 재빌드는 다음 셋을 추가로 이행한다.

* **F13-1 상위집합 [HARD]** — `f13-1-superset-baseline.tsv`(adb1f25 145종목)를 전량
  포함한다. 신규 시총순 선정 단독으로는 F5-a(7→0) · F5-b(10섹터→3) · F6(패션 소멸) ·
  F7(15→2)이 동시에 깨진다 — 이 네 요건이 요구하는 종목이 전부 시총 하위권이기 때문.
* **F13-2 대형 섹터 폭** — 유효 시총 `n >= 15` 섹터 `>= 14`. F12-a(관측 가능성 하한
  `n >= 11`)와 F12-b/c(효과 요건)의 여유를 확보한다.
* **F7 규약 Y** — `MAX52` 가 NULL 인 종목을 신·구 양쪽 판정의 분자·분모에서 제외한다.
  이전 판의 `(max52 or 0.0)`(규약 X)은 `Close >= 0` 을 항상 참으로 만들어 결측 처리
  차이를 실질 판정 차이로 오계상했다(35 vs 15, 차이 20 = NULL `MAX52` 종목 수).

빌드 명령:
    python tests/fixtures/frozen/aggregation-2026-08-11/build_fixture.py

핵심 설계
---------
* **F1 상위집합**: 날짜 축 픽스처(`weekly-2026-08-12/`)의 41 종목 · 385 날짜 주봉 행을
  **verbatim 복사**한 위에 횡단면 보강 종목을 얹는다. 날짜 축은 원본 41 종목이 보존하므로
  보강 종목은 최근 창(2025-07-01~)에만 행을 가져도 격자(346바)가 재현된다.
* **as_of 고정**: `2026-08-11`. 라이브 주봉의 ISO 33주 대표 바는 이미 `2026-08-12` 로
  갱신됐으므로(드리프트 진행 중), 보강 종목의 33주 바는 `2026-08-11` 로 **재라벨**한다.
  라이브의 `Date <= 2026-08-11` 날짜 집합은 날짜 축 픽스처 385 날짜의 부분집합임을
  실측 확인했으므로 신규 날짜가 유입되지 않는다.
* **지수 행 포함**: 날짜 축 픽스처와 달리 `KOSPI`/`KOSDAQ` 지수 행을 포함한다.
  `sector_metrics._load_kospi_returns` 가 이 행을 읽으므로, 없으면 M1.0-b 골든 baseline 의
  초과수익률이 전부 원수익률로 degenerate 한다. `weekly_grid` 는 지수 행을 날짜 카운트에서
  제외하므로 격자에는 영향이 없다.
* **주입이 아니라 선별**: F5(NULL 시총) / F7(신고가 판정 분기) / F8(SMA NULL) 케이스는
  라이브에 자연 존재하는 종목을 골라 담는다. 값을 손으로 만들지 않는다.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = Path(__file__).resolve().parent

SRC_WEEKLY = PROJECT_ROOT / "Output" / "stock_data_weekly.db"
SRC_DAILY = PROJECT_ROOT / "Output" / "stock_data_daily.db"
SRC_REGISTRY = PROJECT_ROOT / "Input" / "sectormap-original.xlsx"
DATE_AXIS_DIR = PROJECT_ROOT / "tests" / "fixtures" / "frozen" / "weekly-2026-08-12"

AS_OF = "2026-08-11"
WEEKLY_HISTORY_FROM = "2025-07-01"   # 364일 창(2025-08-12) + 여유 6주
DAILY_FROM = "2026-05-08"            # F10 3M 창 시작 = 3M 앵커 바
DAILY_TO = AS_OF
INDEX_NAMES = ("KOSPI", "KOSDAQ")
NH_THRESHOLD = 0.02                  # sector_metrics._NH_THRESHOLD 와 동일 규약
HIGH_WINDOW_DAYS = 364               # 52주 = 364일

SUPERSET_BASELINE = OUT_DIR / "f13-1-superset-baseline.tsv"
SUPERSET_BUILD_ID = "adb1f25"        # F13-1 기준 빌드 식별자
WEIGHT_CAP = 0.10                    # spec.md D3 — 상한. cap_eff = max(WEIGHT_CAP, 1/n)
F12_DELTA_THRESHOLD = 0.005          # F12-b — 0.5%p
F12_LARGE_N = 15                     # F13-2 — 대형 섹터 유효 시총 종목 수 하한
LIVE_SYNTHETIC_SOURCE_BAR = "2026-08-12"   # F13-6 — 재라벨 원본 라이브 바

# 섹터별 목표 구성수 (KOSPI, KOSDAQ). **F13-1 상위집합 시드**(adb1f25 145종목)를 먼저
# 채우고 부족분만 보강한다.
# F3 / F13-4: `market=kospi` 유효 종목 수가 **정확히 4**인 섹터가 정확히 2개
#     (디스플레이·스마트폰), **정확히 5**인 섹터가 >= 1개(PCB). 나머지 섹터의 KOSPI
#     목표는 4를 피한다.
# F13-2: 위 3개 소형 섹터 + 패션(F6) 을 제외한 **14개 섹터**를 유효 시총 종목 `n >= 15`
#     로 채운다. 시총 결측 강제 포함분(FORCED_CAP_MISSING_PER_SECTOR)은 유효 시총에
#     들어가지 않으므로 그만큼 목표를 올린다.
SECTOR_PLAN: dict[str, tuple[int, int]] = {
    "게임": (0, 0),          # 상위집합 시드 전량(KOSPI 6 / KOSDAQ 26, 유효 시총 32)
    # F3 3개 섹터는 **KOSPI 구성수를 고정**(F3 · F13-4 집합 동등)하되 KOSDAQ 으로만
    # 넓혀 유효 시총 `n >= 11` 축퇴 경계를 넘긴다. `n <= 10` 이면 시총가중이 등가중과
    # 비트 단위로 동일해져(INV-CAP-1 명제 2) F12-c 순위 이동 집합에 **값이 동일한
    # 섹터가 이웃 교차만으로 끼어드는** 상태가 되며, 이는 AC-SAG-048 축퇴 방지 절이
    # 참조 구현 결함으로 규정하는 형태다. KOSPI 4 / 4 / 5 는 그대로다.
    "디스플레이": (4, 14),    # F3 · F13-4 — KOSPI 정확히 4 고정
    "스마트폰": (4, 14),      # F3 · F13-4 — KOSPI 정확히 4 고정
    "PCB": (5, 13),          # F3 · F13-4 — KOSPI 정확히 5 고정
    "패션": (1, 4),          # F6 · F13-4 — 5 구성종목 중 시총 결측 2 → 유효 시총 3
    "반도체": (9, 9),
    "인터넷": (9, 11),       # 시총 결측 강제 2건 → 유효 시총 18
    "내수": (9, 9),
    "음식료": (9, 9),
    "Auto": (9, 9),
    "조선": (9, 9),
    "방산": (8, 10),         # 라이브 풀 KOSPI 8 / KOSDAQ 10 — 풀 상한
    "화장품": (9, 9),
    "유통": (9, 9),
    "비철금속": (8, 9),      # 라이브 풀 KOSPI 17 / KOSDAQ 17
    "철강": (9, 9),
    "통신": (8, 10),         # 라이브 풀 KOSPI 9
    "헬스케어": (9, 11),     # 시총 결측 강제 3건 → 유효 시총 17
}

# F5-a/F6 을 위해 반드시 포함하는 시총 결측 종목 수(섹터별 상한).
FORCED_CAP_MISSING_PER_SECTOR = {"패션": 2, "인터넷": 2, "헬스케어": 3}


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------

def _iso_week(d: str) -> tuple[int, int]:
    return date.fromisoformat(d).isocalendar()[:2]


AS_OF_WEEK = _iso_week(AS_OF)


def _table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f"PRAGMA table_info([{table}])")]


def _create_table_like(dst: sqlite3.Connection, src: sqlite3.Connection, table: str) -> None:
    ddl = src.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    if ddl is None or ddl[0] is None:
        raise RuntimeError(f"원본 DB 에 {table} 테이블이 없다")
    dst.execute(ddl[0])


def _git_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=True,
    ).stdout.strip()


def _mtime(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


# ---------------------------------------------------------------------------
# 1. 원본 로드
# ---------------------------------------------------------------------------

def load_date_axis() -> tuple[list[str], list[tuple], list[str], list[str]]:
    """날짜 축 픽스처의 주봉 컬럼·행·종목·날짜."""
    conn = sqlite3.connect(DATE_AXIS_DIR / "weekly.db")
    try:
        cols = _table_columns(conn, "stock_prices")
        rows = conn.execute(f"SELECT {', '.join(cols)} FROM stock_prices").fetchall()
        names = sorted({r[0] for r in rows})
        dates = sorted({r[1] for r in rows})
    finally:
        conn.close()
    return cols, rows, names, dates


def load_registry() -> pd.DataFrame:
    df = pd.read_excel(SRC_REGISTRY, header=8)
    df = df.rename(columns={"종목\n코드": "Code", "종목명": "Name", "시장": "Market"})
    df = df[["Code", "Name", "Market", "산업명(대)", "산업명(중)", "주요제품"]].copy()
    df["Code"] = df["Code"].astype(str).str.zfill(6)
    for col in ("산업명(대)", "산업명(중)"):
        df[col] = (
            df[col].fillna("기타").astype(str).str.strip()
            .replace({"": "기타", "-": "기타", "nan": "기타", "NaN": "기타", "None": "기타"})
        )
    df = df[~df["Code"].duplicated(keep="first")].reset_index(drop=True)
    return df


def load_superset_baseline() -> dict[str, str]:
    """F13-1 기준 종목 목록(`adb1f25` 빌드분 145종목) — `{종목명: 섹터}`.

    지수 행(`-`)을 포함해 그대로 반환한다. 이 집합의 **전량 포함**이 F13-1 이며,
    F5-a / F5-b / F6 / F7 의 **유일한 충족 경로**다(신규 시총순 선정 단독으로는
    각각 0 / 3섹터 / 소멸 / 2 로 전부 미달 — acceptance.md §8.2.1).
    """
    out: dict[str, str] = {}
    for line in SUPERSET_BASELINE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, _, sector = line.partition("\t")
        out[name] = sector
    return out


def build_candidates(reg: pd.DataFrame) -> pd.DataFrame:
    """라이브에서 후보 풀 + F5/F7/F8 플래그 산출."""
    dconn = sqlite3.connect(SRC_DAILY)
    try:
        meta = pd.read_sql("SELECT code, name, market_cap, close FROM stock_meta", dconn)
        dmax = dict(dconn.execute(
            "SELECT Name, MAX(Date) FROM stock_prices GROUP BY Name").fetchall())
        dmin_recent = {
            n: c for n, c in dconn.execute(
                "SELECT Name, COUNT(*) FROM stock_prices "
                "WHERE Date BETWEEN ? AND ? AND VolumeWon IS NOT NULL GROUP BY Name",
                (DAILY_FROM, DAILY_TO),
            ).fetchall()
        }
    finally:
        dconn.close()

    wconn = sqlite3.connect(SRC_WEEKLY)
    try:
        live_latest = wconn.execute(
            "SELECT MAX(Date) FROM stock_prices WHERE Date >= ?", ("2026-08-10",)
        ).fetchone()[0]
        snap = pd.read_sql(
            "SELECT Name, Close, SMA10, SMA40, MAX52 FROM stock_prices WHERE Date = ?",
            wconn, params=(live_latest,),
        )
        win_start = (date.fromisoformat(live_latest)
                     - timedelta(days=HIGH_WINDOW_DAYS)).isoformat()
        highs = pd.read_sql(
            "SELECT Name, MAX(High) AS max_high FROM stock_prices "
            "WHERE Date > ? AND Date <= ? GROUP BY Name",
            wconn, params=(win_start, live_latest),
        )
        rs_names = {r[0] for r in wconn.execute(
            "SELECT Name FROM relative_strength WHERE Date = ?", (live_latest,))}
    finally:
        wconn.close()

    df = reg.merge(meta, left_on="Code", right_on="code", how="inner")
    df = df.merge(snap, on="Name", how="inner")
    df = df.merge(highs, on="Name", how="left")

    df["daily_max"] = df["Name"].map(dmax)
    df["daily_rows_3m"] = df["Name"].map(dmin_recent).fillna(0).astype(int)
    latest_daily = max(dmax.values())
    df = df[df["daily_max"].notna()]
    df = df[df["daily_max"].map(
        lambda d: (date.fromisoformat(latest_daily) - date.fromisoformat(d)).days <= 14)]
    df = df[df["daily_rows_3m"] > 0]

    df["cap_missing"] = df["market_cap"].isna() | (df["market_cap"].fillna(1.0) <= 0)
    df["rs_missing"] = ~df["Name"].isin(rs_names)
    df["sma_null"] = df["SMA40"].isna() | df["SMA10"].isna()
    # F7 **규약 Y** (acceptance.md §8.2 F7 · AC-SAG-024 v0.5.0) — `MAX52` 가 NULL 인
    # 종목은 신·구 양쪽 판정의 **분자·분모에서 모두 제외**한다. 이전 판의
    # `(max52 or 0.0)` / `.fillna(0.0)`(규약 X)은 `Close >= 0` 을 항상 참으로 만들어
    # **결측 처리 차이를 실질 판정 차이로 오계상**했다(실측 35 vs 15, 차이 20 = NULL 수).
    judgeable = df["MAX52"].notna() & df["max_high"].notna()
    verdict_stored = df["Close"] >= df["MAX52"] * (1 - NH_THRESHOLD)
    verdict_high = df["Close"] >= df["max_high"] * (1 - NH_THRESHOLD)
    df["nh_divergent"] = judgeable & (verdict_stored != verdict_high)
    df["market_cap_sort"] = df["market_cap"].fillna(0.0)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. 종목 선별
# ---------------------------------------------------------------------------

def select_names(cand: pd.DataFrame, seed_names: list[str], reg: pd.DataFrame) -> list[str]:
    """섹터 계획에 따라 결정론적으로 종목을 선별한다.

    **F13-1 [HARD]**: `seed_names`(= `f13-1-superset-baseline.tsv` 의 145종목)는
    후보 풀 통과 여부와 무관하게 **전량 무조건 포함**한다. 이 시드가 F5-a / F5-b /
    F6 / F7 의 유일한 충족 경로이며, 시총순 신규 선정은 이 종목들을 구조적으로
    배제한다(전부 시총 하위권).
    """
    name_to_sector = dict(zip(reg["Name"], reg["산업명(대)"]))
    name_to_market = dict(zip(reg["Name"], reg["Market"]))

    selected: set[str] = set(seed_names)                    # F13-1 — 무조건 전량 포함
    seed_valid = [n for n in seed_names if n in set(cand["Name"])]

    for sector, (kospi_target, kosdaq_target) in SECTOR_PLAN.items():
        for market, target in (("KOSPI", kospi_target), ("KOSDAQ", kosdaq_target)):
            seeded = [n for n in seed_names
                      if name_to_sector.get(n) == sector and name_to_market.get(n) == market]
            need = target - len(seeded)
            if need <= 0:
                continue
            pool = cand[(cand["산업명(대)"] == sector) & (cand["Market"] == market)
                        & (~cand["Name"].isin(selected))]
            pool = pool.sort_values(["market_cap_sort", "Code"], ascending=[False, True])

            picks: list[str] = []
            # (a) F5/F6 — 시총 결측 강제 포함
            forced = FORCED_CAP_MISSING_PER_SECTOR.get(sector, 0)
            if forced:
                cm = pool[pool["cap_missing"]].sort_values("Code")["Name"].tolist()
                picks.extend(cm[:min(forced, need)])
            # (b) F7/F8/F5b — 플래그 종목 최대 2개
            flagged = pool[(pool["nh_divergent"] | pool["sma_null"] | pool["rs_missing"])
                           & (~pool["cap_missing"])]["Name"].tolist()
            for n in flagged:
                if len(picks) >= need or len([p for p in picks if p in flagged]) >= 2:
                    break
                if n not in picks:
                    picks.append(n)
            # (c) 나머지 — 시총 상위(섹터 리더) 우선
            for n in pool["Name"].tolist():
                if len(picks) >= need:
                    break
                if n not in picks:
                    picks.append(n)
            selected.update(picks[:need])

    return sorted(selected)


# ---------------------------------------------------------------------------
# 3. DB / registry 생성
# ---------------------------------------------------------------------------

def build_weekly(axis_cols: list[str], axis_rows: list[tuple],
                 new_names: list[str], out_path: Path) -> None:
    if out_path.exists():
        out_path.unlink()
    src = sqlite3.connect(SRC_WEEKLY)
    dst = sqlite3.connect(out_path)
    try:
        _create_table_like(dst, src, "stock_prices")
        _create_table_like(dst, src, "relative_strength")

        ph = ", ".join(["?"] * len(axis_cols))
        dst.executemany(
            f"INSERT OR REPLACE INTO stock_prices ({', '.join(axis_cols)}) VALUES ({ph})",
            axis_rows,
        )
        existing = {(r[0], r[1]) for r in axis_rows}

        fetch_names = list(new_names) + list(INDEX_NAMES)
        cols = axis_cols
        for name in fetch_names:
            rows = src.execute(
                f"SELECT {', '.join(cols)} FROM stock_prices "
                "WHERE Name = ? AND Date >= ? ORDER BY Date",
                (name, WEEKLY_HISTORY_FROM),
            ).fetchall()
            keep: list[tuple] = []
            week33 = [r for r in rows if _iso_week(r[1]) == AS_OF_WEEK]
            for r in rows:
                if _iso_week(r[1]) == AS_OF_WEEK:
                    continue
                if r[1] > AS_OF:
                    continue
                keep.append(r)
            if week33:
                latest = max(week33, key=lambda r: r[1])
                keep.append((latest[0], AS_OF) + tuple(latest[2:]))
            keep = [r for r in keep if (r[0], r[1]) not in existing]
            if keep:
                dst.executemany(
                    f"INSERT OR REPLACE INTO stock_prices ({', '.join(cols)}) VALUES ({ph})",
                    keep,
                )

        rs_cols = _table_columns(src, "relative_strength")
        rs_ph = ", ".join(["?"] * len(rs_cols))
        all_names = sorted({r[0] for r in axis_rows} | set(new_names))
        for name in all_names:
            rows = src.execute(
                f"SELECT {', '.join(rs_cols)} FROM relative_strength "
                "WHERE Name = ? AND Date >= ? ORDER BY Date",
                (name, WEEKLY_HISTORY_FROM),
            ).fetchall()
            keep = []
            week33 = [r for r in rows if _iso_week(r[1]) == AS_OF_WEEK]
            for r in rows:
                if _iso_week(r[1]) == AS_OF_WEEK or r[1] > AS_OF:
                    continue
                keep.append(r)
            if week33:
                latest = max(week33, key=lambda r: r[1])
                keep.append((latest[0], AS_OF) + tuple(latest[2:]))
            if keep:
                dst.executemany(
                    f"INSERT OR REPLACE INTO relative_strength "
                    f"({', '.join(rs_cols)}) VALUES ({rs_ph})",
                    keep,
                )
        dst.commit()
        dst.execute("VACUUM")
    finally:
        src.close()
        dst.close()


def build_daily(all_names: list[str], out_path: Path) -> None:
    if out_path.exists():
        out_path.unlink()
    src = sqlite3.connect(SRC_DAILY)
    dst = sqlite3.connect(out_path)
    try:
        _create_table_like(dst, src, "stock_meta")
        _create_table_like(dst, src, "stock_prices")

        meta_cols = _table_columns(src, "stock_meta")
        mph = ", ".join(["?"] * len(meta_cols))
        price_cols = _table_columns(src, "stock_prices")
        pph = ", ".join(["?"] * len(price_cols))

        for name in all_names:
            mrows = src.execute(
                f"SELECT {', '.join(meta_cols)} FROM stock_meta WHERE name = ?", (name,)
            ).fetchall()
            if mrows:
                dst.executemany(
                    f"INSERT OR REPLACE INTO stock_meta ({', '.join(meta_cols)}) "
                    f"VALUES ({mph})", mrows,
                )
            prows = src.execute(
                f"SELECT {', '.join(price_cols)} FROM stock_prices "
                "WHERE Name = ? AND Date BETWEEN ? AND ? ORDER BY Date",
                (name, DAILY_FROM, DAILY_TO),
            ).fetchall()
            if prows:
                dst.executemany(
                    f"INSERT OR REPLACE INTO stock_prices ({', '.join(price_cols)}) "
                    f"VALUES ({pph})", prows,
                )
        dst.commit()
        dst.execute("VACUUM")
    finally:
        src.close()
        dst.close()


def build_registry(reg: pd.DataFrame, names: list[str], out_path: Path) -> pd.DataFrame:
    sel = reg[reg["Name"].isin(names)].copy()
    sel = sel.sort_values("Code").reset_index(drop=True)
    # UN-4 dedup 진단 보존 — 날짜 축 픽스처와 동일하게 중복 행 1건을 유지한다.
    dup_src = sel[sel["Name"] == "아이톡시"]
    if not dup_src.empty:
        sel = pd.concat([sel, dup_src], ignore_index=True)
    out = sel.rename(columns={"Code": "종목\n코드", "Name": "종목명", "Market": "시장"})
    out = out[["종목\n코드", "종목명", "시장", "산업명(대)", "산업명(중)", "주요제품"]]
    out["종목\n코드"] = out["종목\n코드"].astype(str)

    notes = pd.DataFrame({0: [f"# note row {i}" for i in range(8)]})
    with pd.ExcelWriter(out_path, engine="openpyxl") as xw:
        notes.to_excel(xw, index=False, header=False, startrow=0)
        out.to_excel(xw, index=False, header=True, startrow=8)
    return out


# ---------------------------------------------------------------------------
# 4. 실측 (F1~F10)
# ---------------------------------------------------------------------------

def capped_weights(caps: list[float], cap: float = WEIGHT_CAP) -> list[float]:
    """상한 재배분 시총가중 (INV-CAP-1 · AC-SAG-049 동결형).

    `cap_eff = max(cap, 1/n)` — `n <= 1/cap` 이면 `cap_eff = 1/n` 이므로 해가
    **균등 하나뿐**이다(축퇴). 상한에 걸린 종목은 **동결**해 재배분 집합에서 빼며,
    이것이 §3.1 v0.4.1 verbatim 형태(비동결 → 진동 → 상한 초과 종료)와의 차이다.
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


def f12_reference(wpath: str, members: dict[str, list[str]], caps: dict[str, float],
                  anchor_1m: str) -> dict:
    """F12-b / F12-c 참조 산출 (acceptance.md §8.3 제외·null 처리 계약 · R-C8 범위).

    범위: `market=all`, **AG-5 통과 섹터 한정**, **AG-4 미달(유효 시총 < 5) 섹터는
    양쪽 집합에서 제외**, `period=1m`.
    * AG-3 — `market_cap` NULL/`<=0` 종목은 **시총가중 분자·분모에서 제외**하되
      **등가중 분모에는 포함**한다.
    * AG-7 — 1M 수익률 산출 가능 종목 비율이 `< 0.50` 인 섹터는 null 로 취급한다.
    """
    conn = sqlite3.connect(wpath)
    try:
        latest = {r[0]: r[1] for r in conn.execute(
            "SELECT Name, Close FROM stock_prices WHERE Date = ?", (AS_OF,))}
        base = {r[0]: r[1] for r in conn.execute(
            "SELECT Name, Close FROM stock_prices WHERE Date = ?", (anchor_1m,))}
    finally:
        conn.close()

    def ret_1m(n: str):
        a, b = latest.get(n), base.get(n)
        if a is None or b is None or b == 0:
            return None
        return a / b - 1.0

    cap_vals: dict[str, float] = {}
    eq_vals: dict[str, float] = {}
    n_cap_of: dict[str, int] = {}
    for sector, ms in members.items():
        if len(ms) < 5:                                   # AG-5
            continue
        rets = {n: ret_1m(n) for n in ms}
        avail = [n for n in ms if rets[n] is not None]
        if len(avail) / len(ms) < 0.50:                   # AG-7
            continue
        cap_members = [n for n in avail if caps.get(n) is not None and caps[n] > 0]
        n_cap_of[sector] = len(cap_members)
        if len(cap_members) < 5:                          # AG-4 — 양쪽 집합에서 제외
            continue
        w = capped_weights([caps[n] for n in cap_members])
        cap_vals[sector] = sum(wi * rets[n] for wi, n in zip(w, cap_members))
        eq_vals[sector] = sum(rets[n] for n in avail) / len(avail)

    def ranks(vals: dict[str, float]) -> dict[str, int]:
        order = sorted(vals, key=lambda s: (-vals[s], s))
        return {s: i + 1 for i, s in enumerate(order)}

    r_cap, r_eq = ranks(cap_vals), ranks(eq_vals)
    delta = {s: cap_vals[s] - eq_vals[s] for s in cap_vals}
    f12b = sorted(s for s, d in delta.items() if abs(d) >= F12_DELTA_THRESHOLD)
    f12c = sorted(s for s in cap_vals if r_cap[s] != r_eq[s])
    return {
        "anchor_1m": anchor_1m,
        "eligible": sorted(cap_vals),
        "cap_vals": cap_vals, "eq_vals": eq_vals, "delta": delta,
        "n_cap_of": n_cap_of,
        "f12b_sectors": f12b, "f12c_sectors": f12c,
        "rank_cap": r_cap, "rank_eq": r_eq,
    }


def measure(out_dir: Path) -> dict:
    """빌드 산출물에서 F1~F13 실측값을 산출한다(build 측 산출 — AC-SAG-048 은 독립 재산출)."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from my_chart.analysis.universe import compute_universe
    from my_chart.analysis.weekly_grid import compute_weekly_grid

    wpath, dpath = str(out_dir / "weekly.db"), str(out_dir / "daily.db")
    rpath = str(out_dir / "registry.xlsx")

    grid = compute_weekly_grid(wpath, as_of=AS_OF)
    snap = compute_universe(wpath, dpath, rpath, as_of=AS_OF)
    valid = set(snap.valid_names)

    reg = pd.read_excel(rpath, header=8)
    reg = reg.rename(columns={"종목\n코드": "Code", "종목명": "Name", "시장": "Market"})
    reg["Code"] = reg["Code"].astype(str).str.zfill(6)
    reg = reg[~reg["Code"].duplicated(keep="first")]
    sector_of = dict(zip(reg["Name"], reg["산업명(대)"]))
    market_of = dict(zip(reg["Name"], reg["Market"]))

    dconn = sqlite3.connect(dpath)
    caps = dict(dconn.execute("SELECT name, market_cap FROM stock_meta").fetchall())
    closes = dict(dconn.execute("SELECT name, close FROM stock_meta").fetchall())
    daily_vw = {
        n: c for n, c in dconn.execute(
            "SELECT Name, COUNT(*) FROM stock_prices "
            "WHERE Date BETWEEN ? AND ? AND VolumeWon IS NOT NULL GROUP BY Name",
            (DAILY_FROM, DAILY_TO)).fetchall()
    }
    dconn.close()

    members: dict[str, list[str]] = defaultdict(list)
    for n in valid:
        members[sector_of[n]].append(n)

    def cap_valid(n: str) -> bool:
        c = caps.get(n)
        return c is not None and c > 0

    ag5 = {s: ms for s, ms in members.items() if len(ms) >= 5}

    kospi_counts = {
        s: len([n for n in ms if market_of[n] == "KOSPI"]) for s, ms in members.items()
    }
    f3_four = sorted(s for s, c in kospi_counts.items() if c == 4)
    f3_five = sorted(s for s, c in kospi_counts.items() if c == 5)

    # [v0.5.0] F4 / F8 은 **폐지**됐다(acceptance.md §8.2 — 소비 AC 부재). F4 의 조건은
    # F12-a 가 `n >= 11` 제약과 함께 더 강한 형태로 포함한다.
    f5_cap = sorted(n for n in valid if not cap_valid(n))
    wconn = sqlite3.connect(wpath)
    rs_at_latest = {r[0] for r in wconn.execute(
        "SELECT Name FROM relative_strength WHERE Date = ?", (AS_OF,))}
    f5_rs_sectors = sorted({s for s, ms in members.items()
                            if any(n not in rs_at_latest for n in ms)})

    f6 = sorted(s for s, ms in ag5.items() if len([n for n in ms if cap_valid(n)]) == 3)

    win_start = (date.fromisoformat(AS_OF) - timedelta(days=HIGH_WINDOW_DAYS)).isoformat()
    snap_rows = wconn.execute(
        "SELECT Name, Close, SMA10, SMA40, MAX52 FROM stock_prices WHERE Date = ?", (AS_OF,)
    ).fetchall()
    highs = dict(wconn.execute(
        "SELECT Name, MAX(High) FROM stock_prices WHERE Date > ? AND Date <= ? GROUP BY Name",
        (win_start, AS_OF)).fetchall())
    total_rows = wconn.execute("SELECT COUNT(*) FROM stock_prices").fetchone()[0]
    n_dates = wconn.execute("SELECT COUNT(DISTINCT Date) FROM stock_prices").fetchone()[0]
    n_names = wconn.execute("SELECT COUNT(DISTINCT Name) FROM stock_prices").fetchone()[0]
    wconn.close()

    # F7 — **규약 Y**: `MAX52` NULL 종목은 신·구 양쪽 분자·분모에서 제외한다.
    # 규약 X(NULL → 0.0 치환)의 값도 함께 산출해 두 규약이 실제로 갈림을 기록한다.
    f7, f7_null_max52, f7_convention_x = [], [], []
    for name, close, sma10, sma40, max52 in snap_rows:
        if name in INDEX_NAMES or name not in valid:
            continue
        max_high = highs.get(name)
        vs_x = (close or 0.0) >= (max52 or 0.0) * (1 - NH_THRESHOLD)
        vh_x = (close or 0.0) >= (max_high or 0.0) * (1 - NH_THRESHOLD)
        if vs_x != vh_x:
            f7_convention_x.append(name)
        if max52 is None:
            f7_null_max52.append(name)
            continue                                   # 규약 Y — 분모에서 제외
        if max_high is None or close is None:
            continue
        if (close >= max52 * (1 - NH_THRESHOLD)) != (close >= max_high * (1 - NH_THRESHOLD)):
            f7.append(name)

    f10_meta_ok = sorted(
        n for n in valid
        if cap_valid(n) and (caps.get(n) is None or closes.get(n) is None)
    )
    f10_daily_missing = sorted(n for n in valid if daily_vw.get(n, 0) == 0)

    # --- F12 / F13 ---------------------------------------------------------
    from my_chart.analysis.weekly_grid import anchor as _anchor
    anchor_1m = _anchor(grid, grid.latest.date, 28).date
    f12 = f12_reference(wpath, dict(members), caps, anchor_1m)

    f12a = sorted(
        s for s, ms in ag5.items()
        if sum(1 for n in ms if cap_valid(n)) >= 11
        and (lambda vs: bool(vs) and max(vs) / sum(vs) > WEIGHT_CAP)(
            [caps[n] for n in ms if cap_valid(n)])
    )
    n_cap_by_sector = {s: sum(1 for n in ms if cap_valid(n)) for s, ms in members.items()}
    f13_2 = sorted(s for s, c in n_cap_by_sector.items() if c >= F12_LARGE_N)

    superset = load_superset_baseline()
    wconn2 = sqlite3.connect(wpath)
    try:
        agg_names = {r[0] for r in wconn2.execute("SELECT DISTINCT Name FROM stock_prices")}
        has_asof = wconn2.execute(
            "SELECT COUNT(*) FROM stock_prices WHERE Date = ?", (AS_OF,)).fetchone()[0]
        has_live_bar = wconn2.execute(
            "SELECT COUNT(*) FROM stock_prices WHERE Date = ?",
            (LIVE_SYNTHETIC_SOURCE_BAR,)).fetchone()[0]
    finally:
        wconn2.close()
    f13_1_missing = sorted(set(superset) - agg_names)
    f13_1_sector_drift = sorted(
        n for n, s in superset.items()
        if s != "-" and n in sector_of and sector_of[n] != s
    )

    kospi_members = {s: [n for n in ms if market_of[n] == "KOSPI"] for s, ms in members.items()}
    kosdaq_members = {s: [n for n in ms if market_of[n] == "KOSDAQ"] for s, ms in members.items()}

    return {
        "names": n_names, "dates": n_dates, "rows": total_rows,
        "f12a_sectors": f12a,
        "f12b_sectors": f12["f12b_sectors"],
        "f12c_sectors": f12["f12c_sectors"],
        "f12_eligible": f12["eligible"],
        "f12_anchor_1m": anchor_1m,
        "f12_delta": {s: round(d, 6) for s, d in sorted(f12["delta"].items())},
        "f13_1_superset_of": SUPERSET_BUILD_ID,
        "f13_1_baseline_count": len(superset),
        "f13_1_missing": f13_1_missing,
        "f13_1_sector_drift": f13_1_sector_drift,
        "f13_2_large_sectors": f13_2,
        "f13_4_fashion_members": len(members.get("패션", [])),
        "f13_4_fashion_cap_valid": n_cap_by_sector.get("패션", 0),
        "f13_5_kospi_ag5_sectors": sorted(s for s, ms in kospi_members.items() if len(ms) >= 5),
        "f13_5_kosdaq_ag5_sectors": sorted(s for s, ms in kosdaq_members.items() if len(ms) >= 5),
        "f13_5_kospi_universe": sum(len(ms) for ms in kospi_members.values()),
        "f13_5_kosdaq_universe": sum(len(ms) for ms in kosdaq_members.values()),
        "f13_6_as_of_rows": has_asof,
        "f13_6_live_source_bar_rows": has_live_bar,
        "n_cap_by_sector": dict(sorted(n_cap_by_sector.items())),
        "f7_null_max52": sorted(f7_null_max52),
        "f7_convention_x": sorted(f7_convention_x),
        "grid_bars": len(grid.dates),
        "grid_history": len(grid.history),
        "grid_latest": grid.latest.date if grid.latest else None,
        "grid_partial": grid.latest.is_partial_week if grid.latest else None,
        "grid_exclusions": len(grid.exclusions),
        "valid_universe": len(valid),
        "f2_ag5_sectors": sorted(ag5),
        "f3_kospi_exactly4": f3_four,
        "f3_kospi_exactly5": f3_five,
        "f5_cap_missing": f5_cap,
        "f5_rs_missing_sectors": f5_rs_sectors,
        "f6_cap_valid_exactly3": f6,
        "f7_nh_divergent": sorted(f7),
        "f10_meta_missing": f10_meta_ok,
        "f10_daily_missing": f10_daily_missing,
        "f9_anchor_3m_present": "2026-05-08" in set(grid.dates),
        "sector_member_counts": {s: len(ms) for s, ms in sorted(members.items())},
        "sector_kospi_counts": dict(sorted(kospi_counts.items())),
    }


# ---------------------------------------------------------------------------
# 5. MANIFEST
# ---------------------------------------------------------------------------

MANIFEST_TEMPLATE = """# Frozen Fixture Manifest — `aggregation-2026-08-11`

> SPEC-SECTOR-AGGREGATION-001 §8.1 **집계 픽스처**. acceptance.md §8.2 F1~F13 구조 요건을
> 호스팅하며, 게이팅 AC(002 / 007 / 011 / 012 / 013 / 014 / 024 / 030 / 045 R1·R3·R4·R5-a·R6)와
> M1.0-b 골든 baseline 캡처가 이 스냅샷 위에서 실행된다. 날짜 축 픽스처
> (`weekly-2026-08-12/`)는 ① SPEC-SECTOR-GRID-001 소관이며 본 SPEC 은 읽기 전용이다.
>
> **v0.5.0 재빌드분** — F12(효과 요건) 신설 + F13(재빌드 구성 계약) 신설 + F4/F8 폐지 +
> F7 규약 Y(NULL `MAX52` 제외) 적용. 이전 빌드(`{superset_of}`)는 전 섹터 `n <= 10` 축퇴로
> AC-SAG-002 를 무게이팅으로 만들었다(acceptance.md §8.2 F12 블록 · §8.2.1).

## 캡처 메타데이터 · F2~F13 실측 충족값 [기계 판독 블록 — F11]

> **이 블록이 F11 의 단일 원천이다.** AC-SAG-048 은 이 YAML 을 파싱해 **픽스처에서 독립
> 재산출한 실측값과 정확히 일치**하는지 검사한다(F3 / F6 / F12-b / F12-c 는 섹터명 집합까지).
> AC-SAG-007 / AC-SAG-045 R6 은 섹터명을, AC-SAG-002 는 `f12b_*` / `f12c_*` 집합을 AC 본문이
> 아니라 이 블록에서 읽는다. 손으로 값을 적어 넣고 픽스처를 다른 상태로 두면 게이트가 RED 다.

```yaml
as_of: "{as_of}"
captured_at: "{captured_at}"
git_sha: "{git_sha}"
source_weekly_db: "Output/stock_data_weekly.db"
source_weekly_db_mtime: "{weekly_mtime}"
source_daily_db: "Output/stock_data_daily.db"
source_daily_db_mtime: "{daily_mtime}"
source_registry: "Input/sectormap-original.xlsx"
source_registry_mtime: "{registry_mtime}"
build_command: "python tests/fixtures/frozen/aggregation-2026-08-11/build_fixture.py"

synthetic_bar:
  source_live_bar_date: "{synthetic_source_bar}"
  relabeled_to_date: "{as_of}"
  transformation: "날짜 라벨만 교체한다 — Close/High/Low/Open/거래량 등 값 컬럼은 라이브 원본 그대로이며 어떤 값도 재계산·보정하지 않는다 (acceptance.md §8.1.1)"
  reproduce_command: "python tests/fixtures/frozen/aggregation-2026-08-11/build_fixture.py"

f2_ag5_sector_count: {f2_count}
f2_ag5_sectors: [{f2_yaml}]
f3_kospi_exactly4_sector_count: {f3_four_count}
f3_kospi_exactly4_sectors: [{f3_four_yaml}]
f3_kospi_exactly5_sector_count: {f3_five_count}
f3_kospi_exactly5_sectors: [{f3_five_yaml}]
f5_cap_missing_stock_count: {f5_cap_count}
f5_rs_missing_sector_count: {f5_rs_count}
f6_cap_valid_exactly3_sector_count: {f6_count}
f6_cap_valid_exactly3_sectors: [{f6_yaml}]
f7_convention: "Y"
f7_nh_verdict_divergent_stock_count: {f7_count}
f7_max52_null_stock_count: {f7_null_count}
f7_convention_x_divergent_stock_count: {f7_x_count}
f9_complete_bar_count: {grid_history}
f9_anchor_3m_present: {f9_anchor_3m_present}
f10_meta_missing_stock_count: {f10_meta_missing_count}
f10_daily_volume_missing_stock_count: {f10_daily_missing_count}
f12a_n_ge_11_top_gt_10pct_sector_count: {f12a_count}
f12a_sectors: [{f12a_yaml}]
f12b_delta_ge_50bp_sector_count: {f12b_count}
f12b_delta_ge_50bp_sectors_1m: [{f12b_yaml}]
f12c_rank_shifted_sector_count: {f12c_count}
f12c_rank_shifted_sectors_1m: [{f12c_yaml}]
f12_eligible_sector_count: {f12_eligible_count}
f12_anchor_1m: "{f12_anchor_1m}"
f13_1_superset_of: "{superset_of}"
f13_1_baseline_stock_count: {f13_1_baseline_count}
f13_1_baseline_list: "f13-1-superset-baseline.tsv"
f13_1_missing_stock_count: {f13_1_missing_count}
f13_2_n_ge_15_sector_count: {f13_2_count}
f13_2_n_ge_15_sectors: [{f13_2_yaml}]
f13_4_fashion_member_count: {f13_4_fashion_members}
f13_4_fashion_cap_valid_count: {f13_4_fashion_cap_valid}
f13_5_kospi_universe_size: {f13_5_kospi_universe}
f13_5_kosdaq_universe_size: {f13_5_kosdaq_universe}
f13_5_kospi_ag5_sector_count: {f13_5_kospi_ag5_count}
f13_5_kosdaq_ag5_sector_count: {f13_5_kosdaq_ag5_count}
f13_6_as_of_row_count: {f13_6_as_of_rows}
f13_6_live_source_bar_row_count: {f13_6_live_source_bar_rows}
```

## 산출물

| 파일 | 내용 |
| --- | --- |
| `weekly.db` | `stock_prices` {rows}행 / {dates} 날짜 / {names} 이름(지수 2 포함) + `relative_strength` |
| `daily.db` | `stock_meta`(시총·현재가) + `stock_prices` `[{daily_from}, {daily_to}]` (`VolumeWon`) |
| `registry.xlsx` | `pd.read_excel(header=8)` 구조. UN-4 dedup 진단용 중복 행 1건 포함 |
| `f13-1-superset-baseline.tsv` | F13-1 기준 종목 목록(`{superset_of}` 빌드분 {f13_1_baseline_count}종목 + 섹터 배정) |
| `MANIFEST.md` | 본 문서 — F2~F13 실측 충족값(F11) |

## 합성 바 (§8.1.1 · F13-6)

라이브 주봉 DB 에는 `{as_of}` 행이 **존재하지 않는다.** 최신 라이브 바는
`{synthetic_source_bar}`(수)이며, 빌더가 그 행의 **날짜 라벨만** `{as_of}`(화)로 교체한다.
값 컬럼은 라이브 원본 그대로다. AC-SAG-046 의 창 일수 리터럴 `{{11, 32, 95}}` 은 **라벨**
기준으로 계산되므로 이 재라벨링이 그 리터럴의 전제다 — 빠뜨리면 `as_of` 가
`{synthetic_source_bar}` 가 되어 `{{12, 33, 96}}` 으로 전부 RED 가 된다.

| 항목 | 값 |
| --- | --- |
| `{as_of}` 행 수 | **{f13_6_as_of_rows}** (> 0 이어야 한다) |
| `{synthetic_source_bar}` 행 수 | **{f13_6_live_source_bar_rows}** (0 이어야 한다 — 재라벨링의 구조적 증거) |

## 날짜 축 정합 (F1 / F9)

| 지표 | 실측값 |
| --- | --- |
| 고유 날짜 수 | **{dates}** |
| 정규 격자 바 수 | **{grid_bars}** |
| `history_grid` 바 수 | **{grid_history}** |
| CG-3 배제 대표 바 | **{grid_exclusions}건** |
| `as_of={as_of}` → latest | **{grid_latest}**, `is_partial_week={grid_partial}` |
| 3M 앵커 바 `2026-05-08` | {f9_anchor_3m_present} |
| 유효 유니버스 크기 | **{valid_universe}** |

## F2~F13 실측 충족값 [F11 — AC-SAG-048 이 이 값과의 정확한 일치를 요구한다]

| 요건 | 임계 | 실측값 | 여유 |
| --- | --- | --- | --- |
| **F2** | AG-5 통과 섹터 >= 12 | **{f2_count}** | {f2_margin} |
| **F3-a** | `market=kospi` 유효 종목 **정확히 4**인 섹터 == 2 | **{f3_four_count}** | — |
| **F3-b** | `market=kospi` 유효 종목 **정확히 5**인 섹터 >= 1 | **{f3_five_count}** | {f3_five_margin} |
| **F5-a** | `market_cap` NULL 또는 <= 0 종목 >= 5 | **{f5_cap_count}** | {f5_cap_margin} |
| **F5-b** | RS 행 없는 종목을 가진 섹터 >= 3 | **{f5_rs_count}** | {f5_rs_margin} |
| **F6** | 유효 시총 종목 **정확히 3**인 섹터 >= 1 | **{f6_count}** | {f6_margin} |
| **F7** (규약 Y) | 신고가 판정이 갈리는 종목 >= 5 | **{f7_count}** | {f7_margin} |
| **F9** | 완성 바 >= 53 · 3M 앵커 바 존재 | **{grid_history}** / {f9_anchor_3m_present} | {f9_margin} |
| **F10** | meta 결측 0 · daily VolumeWon 결측 0 | **{f10_meta_missing_count}** / **{f10_daily_missing_count}** | — |
| **F12-a** | `n >= 11` 이고 최상위 원비중 > 0.10 인 섹터 >= 12 | **{f12a_count}** | {f12a_margin} |
| **F12-b** | 1M 시총가중 − 등가중 차 >= 0.5%p 섹터 >= 3 | **{f12b_count}** | {f12b_margin} |
| **F12-c** | 1M 시총가중 순위 != 등가중 순위 섹터 >= 5 | **{f12c_count}** | {f12c_margin} |
| **F13-1** | 상위집합 누락 종목 == 0 | **{f13_1_missing_count}** | — |
| **F13-2** | 유효 시총 `n >= 15` 섹터 >= 14 | **{f13_2_count}** | {f13_2_margin} |
| **F13-3** | F12-b >= 9 **이고** F12-c >= 9 (빌드 목표) | **{f12b_count}** / **{f12c_count}** | {f13_3_margin} |
| **F13-4** | 패션 구성 5 / 유효 시총 3 | **{f13_4_fashion_members}** / **{f13_4_fashion_cap_valid}** | — |
| **F13-5** | 양 시장 비공백 + 각 AG-5 섹터 >= 1 | **{f13_5_kospi_ag5_count}** / **{f13_5_kosdaq_ag5_count}** | — |
| **F13-6** | `{as_of}` 행 > 0 이고 `{synthetic_source_bar}` 행 == 0 | **{f13_6_as_of_rows}** / **{f13_6_live_source_bar_rows}** | — |

### F7 규약 Y vs 규약 X [AC-SAG-024 v0.5.0 · N2]

| 계수 규약 | divergent 종목 수 |
| --- | --- |
| **규약 Y** (NULL `MAX52` 를 분자·분모에서 제외 — **확정 규약**) | **{f7_count}** |
| 규약 X (NULL `MAX52` → `0.0` 치환, 폐기) | {f7_x_count} |
| NULL `MAX52` 종목 수 | {f7_null_count} |

두 값의 차이는 정확히 NULL `MAX52` 종목 수다 — 규약 X 는 `Close >= 0` 을 항상 참으로 만들어
**결측 처리 차이를 실질 판정 차이로 오계상**한다.

### F3 해당 섹터명 집합 [AC-SAG-007 / 045 R6 이 본 절에서 섹터명을 읽는다]

- `market=kospi` 유효 종목 **정확히 4**: `{f3_four_set}`
- `market=kospi` 유효 종목 **정확히 5**: `{f3_five_set}`

### F6 해당 섹터명 집합

- 유효 시총 종목 **정확히 3**: `{f6_set}`

### F2 해당 섹터명 집합 (AG-5 통과)

`{f2_set}`

### F12-b / F12-c 해당 섹터명 집합 [AC-SAG-002 가 본 절에서 집합을 읽는다]

- **F12-b** (1M `|시총가중 − 등가중| >= 0.5%p`): `{f12b_set}`
- **F12-c** (1M 시총가중 순위 != 등가중 순위): `{f12c_set}`
- F12 대조 대상 섹터(AG-5 통과 ∧ 유효 시총 >= 5): `{f12_eligible_set}`
- 1M 앵커 바: `{f12_anchor_1m}`

### F12-a / F13-2 해당 섹터명 집합

- **F12-a** (`n >= 11` ∧ 최상위 원비중 > 0.10): `{f12a_set}`
- **F13-2** (유효 시총 `n >= 15`): `{f13_2_set}`

### 섹터별 유효 시총 종목 수 (`n`) — INV-CAP-1 축퇴 경계 판정용

`{n_cap_table}`

## 갱신 규약

스냅샷 갱신은 명시적 행위다(acceptance.md §8.4 규약 4) — 커밋 메시지에 사유와 새 실측값을
남기고, 위 표의 실측값을 갱신한다. 조용한 재생성을 금지한다. AC-SAG-048 이 본 문서의 실측
기록과 픽스처 재산출값의 일치를 기계적으로 검사하므로, 픽스처만 바꾸고 본 문서를 방치하면
게이트가 RED 가 된다.
"""


def write_manifest(m: dict, out_path: Path) -> None:
    def yl(v):
        return ", ".join(f'"{s}"' for s in v)

    body = MANIFEST_TEMPLATE.format(
        as_of=AS_OF,
        captured_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        git_sha=_git_sha(),
        weekly_mtime=_mtime(SRC_WEEKLY),
        daily_mtime=_mtime(SRC_DAILY),
        registry_mtime=_mtime(SRC_REGISTRY),
        daily_from=DAILY_FROM, daily_to=DAILY_TO,
        synthetic_source_bar=LIVE_SYNTHETIC_SOURCE_BAR,
        rows=m["rows"], dates=m["dates"], names=m["names"],
        grid_bars=m["grid_bars"], grid_history=m["grid_history"],
        grid_exclusions=m["grid_exclusions"], grid_latest=m["grid_latest"],
        grid_partial=m["grid_partial"], valid_universe=m["valid_universe"],
        f9_anchor_3m_present=m["f9_anchor_3m_present"],
        f2_count=len(m["f2_ag5_sectors"]),
        f3_four_count=len(m["f3_kospi_exactly4"]),
        f3_five_count=len(m["f3_kospi_exactly5"]),
        f5_cap_count=len(m["f5_cap_missing"]),
        f5_rs_count=len(m["f5_rs_missing_sectors"]),
        f6_count=len(m["f6_cap_valid_exactly3"]),
        f7_count=len(m["f7_nh_divergent"]),
        f7_null_count=len(m["f7_null_max52"]),
        f7_x_count=len(m["f7_convention_x"]),
        f10_meta_missing_count=len(m["f10_meta_missing"]),
        f10_daily_missing_count=len(m["f10_daily_missing"]),
        f12a_count=len(m["f12a_sectors"]),
        f12b_count=len(m["f12b_sectors"]),
        f12c_count=len(m["f12c_sectors"]),
        f12_eligible_count=len(m["f12_eligible"]),
        f12_anchor_1m=m["f12_anchor_1m"],
        superset_of=m["f13_1_superset_of"],
        f13_1_baseline_count=m["f13_1_baseline_count"],
        f13_1_missing_count=len(m["f13_1_missing"]),
        f13_2_count=len(m["f13_2_large_sectors"]),
        f13_4_fashion_members=m["f13_4_fashion_members"],
        f13_4_fashion_cap_valid=m["f13_4_fashion_cap_valid"],
        f13_5_kospi_universe=m["f13_5_kospi_universe"],
        f13_5_kosdaq_universe=m["f13_5_kosdaq_universe"],
        f13_5_kospi_ag5_count=len(m["f13_5_kospi_ag5_sectors"]),
        f13_5_kosdaq_ag5_count=len(m["f13_5_kosdaq_ag5_sectors"]),
        f13_6_as_of_rows=m["f13_6_as_of_rows"],
        f13_6_live_source_bar_rows=m["f13_6_live_source_bar_rows"],
        f2_margin=f"{len(m['f2_ag5_sectors']) / 12:.2f}x",
        f3_five_margin=f"{len(m['f3_kospi_exactly5'])}/1",
        f5_cap_margin=f"{len(m['f5_cap_missing']) / 5:.2f}x",
        f5_rs_margin=f"{len(m['f5_rs_missing_sectors']) / 3:.2f}x",
        f6_margin=f"{len(m['f6_cap_valid_exactly3'])}/1",
        f7_margin=f"{len(m['f7_nh_divergent']) / 5:.2f}x",
        f9_margin=f"{m['grid_history'] / 53:.2f}x",
        f12a_margin=f"{len(m['f12a_sectors']) / 12:.2f}x",
        f12b_margin=f"{len(m['f12b_sectors']) / 3:.2f}x",
        f12c_margin=f"{len(m['f12c_sectors']) / 5:.2f}x",
        f13_2_margin=f"{len(m['f13_2_large_sectors']) / 14:.2f}x",
        f13_3_margin=f"{min(len(m['f12b_sectors']), len(m['f12c_sectors'])) / 9:.2f}x",
        f3_four_set=", ".join(m["f3_kospi_exactly4"]),
        f3_five_set=", ".join(m["f3_kospi_exactly5"]),
        f6_set=", ".join(m["f6_cap_valid_exactly3"]),
        f2_set=", ".join(m["f2_ag5_sectors"]),
        f12a_set=", ".join(m["f12a_sectors"]),
        f12b_set=", ".join(m["f12b_sectors"]),
        f12c_set=", ".join(m["f12c_sectors"]),
        f12_eligible_set=", ".join(m["f12_eligible"]),
        f13_2_set=", ".join(m["f13_2_large_sectors"]),
        n_cap_table=", ".join(f"{s}={c}" for s, c in m["n_cap_by_sector"].items()),
        f2_yaml=yl(m["f2_ag5_sectors"]),
        f3_four_yaml=yl(m["f3_kospi_exactly4"]),
        f3_five_yaml=yl(m["f3_kospi_exactly5"]),
        f6_yaml=yl(m["f6_cap_valid_exactly3"]),
        f12a_yaml=yl(m["f12a_sectors"]),
        f12b_yaml=yl(m["f12b_sectors"]),
        f12c_yaml=yl(m["f12c_sectors"]),
        f13_2_yaml=yl(m["f13_2_large_sectors"]),
    )
    out_path.write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="선별/실측만 출력하고 쓰지 않는다")
    ap.add_argument("--out", default=str(OUT_DIR))
    args = ap.parse_args()

    for p in (SRC_WEEKLY, SRC_DAILY, SRC_REGISTRY, DATE_AXIS_DIR):
        if not Path(p).exists():
            raise SystemExit(f"원본 없음: {p}")

    axis_cols, axis_rows, axis_names, axis_dates = load_date_axis()
    print(f"[axis] names={len(axis_names)} dates={len(axis_dates)} rows={len(axis_rows)}")

    reg = load_registry()
    cand = build_candidates(reg)
    print(f"[cand] pool={len(cand)} cap_missing={int(cand['cap_missing'].sum())} "
          f"nh_div={int(cand['nh_divergent'].sum())} sma_null={int(cand['sma_null'].sum())} "
          f"rs_missing={int(cand['rs_missing'].sum())}")

    superset = load_superset_baseline()
    seed_names = sorted(set(superset) | set(axis_names))
    print(f"[superset] F13-1 기준 {SUPERSET_BUILD_ID}: {len(superset)}종목 "
          f"(날짜 축 합집합 시드 {len(seed_names)})")

    selected = select_names(cand, seed_names, reg)
    missing_superset = sorted(set(superset) - set(selected))
    if missing_superset:
        raise SystemExit(f"F13-1 위반 — 상위집합 종목 누락: {missing_superset}")
    new_names = [n for n in selected if n not in set(axis_names)]
    all_names = sorted(set(selected) | set(axis_names))
    print(f"[select] selected={len(selected)} new={len(new_names)} all={len(all_names)}")

    if args.dry_run:
        return 0

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    build_weekly(axis_cols, axis_rows, new_names, out_dir / "weekly.db")
    build_daily(all_names, out_dir / "daily.db")
    build_registry(reg, all_names, out_dir / "registry.xlsx")

    m = measure(out_dir)
    for k, v in m.items():
        if isinstance(v, list) and len(v) > 12:
            print(f"  {k}: {len(v)} -> {v[:12]} ...")
        else:
            print(f"  {k}: {v}")
    write_manifest(m, out_dir / "MANIFEST.md")
    print(f"[done] {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
