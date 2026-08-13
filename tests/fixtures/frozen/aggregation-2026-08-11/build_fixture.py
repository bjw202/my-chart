#!/usr/bin/env python3
# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M1.0-a — 집계 프로즌 픽스처 빌드.

acceptance.md §8.2 F1~F11 의 **구조 요건**을 충족하는 집계 픽스처를 라이브 DB 에서
결정론적으로 재구성한다. 값(어느 섹터가 몇 %인지)은 규정하지 않으며, 요건 충족
실측값만 `MANIFEST.md` 에 기록한다(F11).

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

# 섹터별 목표 구성수 (KOSPI, KOSDAQ). 원본 41 종목 시드를 먼저 채우고 부족분만 보강한다.
# F3: `market=kospi` 유효 종목 수가 **정확히 4**인 섹터가 정확히 2개(디스플레이·스마트폰),
#     **정확히 5**인 섹터가 >= 1개(PCB). 나머지 섹터의 KOSPI 목표는 4를 피한다.
SECTOR_PLAN: dict[str, tuple[int, int]] = {
    "게임": (0, 0),          # 원본 시드 전량(보강 없음)
    "디스플레이": (4, 2),     # F3 — KOSPI 정확히 4
    "스마트폰": (4, 2),       # F3 — KOSPI 정확히 4
    "PCB": (5, 1),           # F3 — KOSPI 정확히 5
    "반도체": (3, 3),
    "인터넷": (3, 3),
    "내수": (3, 3),
    "음식료": (3, 3),
    "Auto": (3, 3),
    "조선": (3, 3),
    "방산": (3, 3),
    "화장품": (3, 3),
    "유통": (3, 3),
    "비철금속": (3, 3),
    "철강": (3, 3),
    "통신": (3, 3),
    "패션": (1, 4),          # F6 — 5 구성종목 중 시총 결측 2 → 유효 시총 3
    "헬스케어": (3, 5),
}

# F5/F6 을 위해 반드시 포함하는 시총 결측 종목 수(섹터별 상한).
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
    verdict_stored = df["Close"] >= df["MAX52"].fillna(0.0) * (1 - NH_THRESHOLD)
    verdict_high = df["Close"] >= df["max_high"].fillna(0.0) * (1 - NH_THRESHOLD)
    df["nh_divergent"] = verdict_stored != verdict_high
    df["market_cap_sort"] = df["market_cap"].fillna(0.0)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 2. 종목 선별
# ---------------------------------------------------------------------------

def select_names(cand: pd.DataFrame, seed_names: list[str], reg: pd.DataFrame) -> list[str]:
    """섹터 계획에 따라 결정론적으로 종목을 선별한다."""
    name_to_sector = dict(zip(reg["Name"], reg["산업명(대)"]))
    name_to_market = dict(zip(reg["Name"], reg["Market"]))

    seed_valid = [n for n in seed_names if n in set(cand["Name"])]
    selected: set[str] = set(seed_valid)

    for sector, (kospi_target, kosdaq_target) in SECTOR_PLAN.items():
        for market, target in (("KOSPI", kospi_target), ("KOSDAQ", kosdaq_target)):
            seeded = [n for n in seed_valid
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

def measure(out_dir: Path) -> dict:
    """빌드 산출물에서 F1~F10 실측값을 산출한다(build 측 산출 — AC-SAG-048 은 독립 재산출)."""
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

    f4 = []
    for s, ms in ag5.items():
        vs = [caps[n] for n in ms if cap_valid(n)]
        if vs and max(vs) / sum(vs) > 0.10:
            f4.append(s)

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

    f7, f8 = [], []
    for name, close, sma10, sma40, max52 in snap_rows:
        if name in INDEX_NAMES or name not in valid:
            continue
        vs = (close or 0.0) >= (max52 or 0.0) * (1 - NH_THRESHOLD)
        vh = (close or 0.0) >= (highs.get(name) or 0.0) * (1 - NH_THRESHOLD)
        if vs != vh:
            f7.append(name)
        if sma40 is None or sma10 is None:
            f8.append(name)

    f10_meta_ok = sorted(
        n for n in valid
        if cap_valid(n) and (caps.get(n) is None or closes.get(n) is None)
    )
    f10_daily_missing = sorted(n for n in valid if daily_vw.get(n, 0) == 0)

    return {
        "names": n_names, "dates": n_dates, "rows": total_rows,
        "grid_bars": len(grid.dates),
        "grid_history": len(grid.history),
        "grid_latest": grid.latest.date if grid.latest else None,
        "grid_partial": grid.latest.is_partial_week if grid.latest else None,
        "grid_exclusions": len(grid.exclusions),
        "valid_universe": len(valid),
        "f2_ag5_sectors": sorted(ag5),
        "f3_kospi_exactly4": f3_four,
        "f3_kospi_exactly5": f3_five,
        "f4_top_weight_gt10": sorted(f4),
        "f5_cap_missing": f5_cap,
        "f5_rs_missing_sectors": f5_rs_sectors,
        "f6_cap_valid_exactly3": f6,
        "f7_nh_divergent": sorted(f7),
        "f8_sma_null": sorted(f8),
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

> SPEC-SECTOR-AGGREGATION-001 §8.1 **집계 픽스처**. acceptance.md §8.2 F1~F11 구조 요건을
> 호스팅하며, 게이팅 AC(002 / 007 / 011 / 013 / 014 / 024 / 030 / 045 R1·R3·R4·R5·R6)와
> M1.0-b 골든 baseline 캡처가 이 스냅샷 위에서 실행된다. 날짜 축 픽스처
> (`weekly-2026-08-12/`)는 ① SPEC-SECTOR-GRID-001 소관이며 본 SPEC 은 읽기 전용이다.

## 캡처 메타데이터 · F2~F8 실측 충족값 [기계 판독 블록 — F11]

> **이 블록이 F11 의 단일 원천이다.** AC-SAG-048 은 이 YAML 을 파싱해 **픽스처에서 독립
> 재산출한 실측값과 정확히 일치**하는지 검사한다(F3/F6 은 섹터명 집합까지). AC-SAG-007 /
> AC-SAG-045 R6 은 섹터명을 AC 본문이 아니라 이 블록에서 읽는다. 손으로 값을 적어 넣고
> 픽스처를 다른 상태로 두면 게이트가 RED 가 된다.

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

f2_ag5_sector_count: {f2_count}
f3_kospi_exactly4_sector_count: {f3_four_count}
f3_kospi_exactly4_sectors: [{f3_four_yaml}]
f3_kospi_exactly5_sector_count: {f3_five_count}
f3_kospi_exactly5_sectors: [{f3_five_yaml}]
f4_top_weight_gt_10pct_sector_count: {f4_count}
f5_cap_missing_stock_count: {f5_cap_count}
f5_rs_missing_sector_count: {f5_rs_count}
f6_cap_valid_exactly3_sector_count: {f6_count}
f6_cap_valid_exactly3_sectors: [{f6_yaml}]
f7_nh_verdict_divergent_stock_count: {f7_count}
f8_sma_null_stock_count: {f8_count}
```

## 산출물

| 파일 | 내용 |
| --- | --- |
| `weekly.db` | `stock_prices` {rows}행 / {dates} 날짜 / {names} 이름(지수 2 포함) + `relative_strength` |
| `daily.db` | `stock_meta`(시총·현재가) + `stock_prices` `[{daily_from}, {daily_to}]` (`VolumeWon`) |
| `registry.xlsx` | `pd.read_excel(header=8)` 구조. UN-4 dedup 진단용 중복 행 1건 포함 |
| `MANIFEST.md` | 본 문서 — F2~F8 실측 충족값(F11) |

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

## F2~F8 실측 충족값 [F11 — AC-SAG-048 이 이 값과의 정확한 일치를 요구한다]

| 요건 | 임계 | 실측값 |
| --- | --- | --- |
| **F2** | AG-5 통과 섹터 >= 12 | **{f2_count}** |
| **F3-a** | `market=kospi` 유효 종목 **정확히 4**인 섹터 == 2 | **{f3_four_count}** |
| **F3-b** | `market=kospi` 유효 종목 **정확히 5**인 섹터 >= 1 | **{f3_five_count}** |
| **F4** | 최상위 원비중 > 0.10 섹터 >= 3 | **{f4_count}** |
| **F5-a** | `market_cap` NULL 또는 <= 0 종목 >= 5 | **{f5_cap_count}** |
| **F5-b** | RS 행 없는 종목을 가진 섹터 >= 3 | **{f5_rs_count}** |
| **F6** | 유효 시총 종목 **정확히 3**인 섹터 >= 1 | **{f6_count}** |
| **F7** | 저장 `MAX52` vs `MAX(High) over 364d` 판정이 갈리는 종목 >= 5 | **{f7_count}** |
| **F8** | `SMA40` 또는 `SMA10`이 NULL인 종목 >= 3 | **{f8_count}** |

### F3 해당 섹터명 집합 [AC-SAG-007 / 045 R6 이 본 절에서 섹터명을 읽는다]

- `market=kospi` 유효 종목 **정확히 4**: `{f3_four_set}`
- `market=kospi` 유효 종목 **정확히 5**: `{f3_five_set}`

### F6 해당 섹터명 집합

- 유효 시총 종목 **정확히 3**: `{f6_set}`

### F2 해당 섹터명 집합 (AG-5 통과)

`{f2_set}`

## 갱신 규약

스냅샷 갱신은 명시적 행위다(acceptance.md §8.4 규약 4) — 커밋 메시지에 사유와 새 실측값을
남기고, 위 표의 실측값을 갱신한다. 조용한 재생성을 금지한다. AC-SAG-048 이 본 문서의 실측
기록과 픽스처 재산출값의 일치를 기계적으로 검사하므로, 픽스처만 바꾸고 본 문서를 방치하면
게이트가 RED 가 된다.
"""


def write_manifest(m: dict, out_path: Path) -> None:
    body = MANIFEST_TEMPLATE.format(
        as_of=AS_OF,
        captured_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        git_sha=_git_sha(),
        weekly_mtime=_mtime(SRC_WEEKLY),
        daily_mtime=_mtime(SRC_DAILY),
        registry_mtime=_mtime(SRC_REGISTRY),
        daily_from=DAILY_FROM, daily_to=DAILY_TO,
        rows=m["rows"], dates=m["dates"], names=m["names"],
        grid_bars=m["grid_bars"], grid_history=m["grid_history"],
        grid_exclusions=m["grid_exclusions"], grid_latest=m["grid_latest"],
        grid_partial=m["grid_partial"], valid_universe=m["valid_universe"],
        f9_anchor_3m_present=m["f9_anchor_3m_present"],
        f2_count=len(m["f2_ag5_sectors"]),
        f3_four_count=len(m["f3_kospi_exactly4"]),
        f3_five_count=len(m["f3_kospi_exactly5"]),
        f4_count=len(m["f4_top_weight_gt10"]),
        f5_cap_count=len(m["f5_cap_missing"]),
        f5_rs_count=len(m["f5_rs_missing_sectors"]),
        f6_count=len(m["f6_cap_valid_exactly3"]),
        f7_count=len(m["f7_nh_divergent"]),
        f8_count=len(m["f8_sma_null"]),
        f3_four_set=", ".join(m["f3_kospi_exactly4"]),
        f3_five_set=", ".join(m["f3_kospi_exactly5"]),
        f6_set=", ".join(m["f6_cap_valid_exactly3"]),
        f2_set=", ".join(m["f2_ag5_sectors"]),
        f3_four_yaml=", ".join(f'"{s}"' for s in m["f3_kospi_exactly4"]),
        f3_five_yaml=", ".join(f'"{s}"' for s in m["f3_kospi_exactly5"]),
        f6_yaml=", ".join(f'"{s}"' for s in m["f6_cap_valid_exactly3"]),
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

    selected = select_names(cand, axis_names, reg)
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
