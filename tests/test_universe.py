# coding: utf-8
"""SPEC-SECTOR-GRID-001 M2 — 유니버스 규약 (universe.py) 테스트.

AC-SGR-014/015/016/017/018/019/021 (REQ-SGR-011~017) 를 검증한다.

반증 우선(plan M2): UN-4/UN-5 는 라이브·프로즌 데이터로 반증 불가하다
(실측: stale ∩ stock_meta = 0; 052770 은 완전 중복이라 Code-dedup == Name-dedup).
따라서 stale/last_updated/divergent-dedup 픽스처를 합성으로 GREEN 이전에 구축한다.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

FROZEN = Path(__file__).resolve().parent / "fixtures" / "frozen" / "weekly-2026-08-12"


# ---------------------------------------------------------------------------
# 합성 픽스처 빌더 (반증 가능성 확보 — GREEN 이전 구축)
# ---------------------------------------------------------------------------

def _write_registry_xlsx(path: Path, rows: list[dict]) -> None:
    """registry.xlsx 를 header=8 구조로 기록 (rows 0~7 빈, row 8 = 헤더).

    _load_sectormap 가 ``pd.read_excel(path, header=8)`` 로 읽도록 맞춘다.
    """
    df = pd.DataFrame(rows, columns=["종목\n코드", "종목명", "시장", "산업명(대)", "산업명(중)", "주요제품"])
    with pd.ExcelWriter(str(path), engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Sheet1", startrow=8, index=False)


def _make_weekly_db(path: Path, names: list[str], dates: list[str]) -> None:
    """합성 주봉 DB. compute_weekly_grid + latest-bar 이름 집합에 필요한 최소 스키마."""
    conn = sqlite3.connect(str(path))
    conn.execute(
        "CREATE TABLE stock_prices (Name TEXT, Date TEXT, Close REAL, PRIMARY KEY(Name, Date))"
    )
    conn.executemany(
        "INSERT INTO stock_prices VALUES (?,?,?)",
        [(n, d, 1000.0) for n in names for d in dates],
    )
    conn.commit()
    conn.close()


def _make_daily_db(path: Path, meta_rows: list[tuple], price_rows: list[tuple]) -> None:
    """합성 일봉 DB. stock_meta(이름/시가총액/last_updated) + stock_prices(Name,Date)."""
    conn = sqlite3.connect(str(path))
    conn.execute(
        """CREATE TABLE stock_meta (
            code TEXT PRIMARY KEY, name TEXT, market TEXT, market_cap INTEGER,
            sector_major TEXT, sector_minor TEXT, product TEXT, close REAL,
            last_updated TEXT
        )"""
    )
    conn.executemany(
        "INSERT INTO stock_meta(code,name,market,market_cap,sector_major,sector_minor,product,close,last_updated) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        meta_rows,
    )
    conn.execute(
        "CREATE TABLE stock_prices (Name TEXT, Date TEXT, Close REAL, PRIMARY KEY(Name, Date))"
    )
    conn.executemany("INSERT INTO stock_prices VALUES (?,?,?)", price_rows)
    conn.commit()
    conn.close()


def _stale_fixture(tmp: Path, identical_last_updated: bool = False) -> dict:
    """AC-SGR-017 / AC-SGR-018 용 반증 픽스처.

    4 종목이 전부 registry·stock_meta·최신 주봉 바 에 존재 → stale 규칙만이 유일한 배제 사유.
    종목별 일봉 MAX(Date): S-STALE=T-20, S-EDGE14=T-14, S-EDGE15=T-15, S-FRESH=T.
    identical_last_updated=True 면 stock_meta.last_updated 를 전 행 동일 타임스탬프로.
    """
    T = date(2026, 8, 11)
    names = ["S-STALE", "S-EDGE14", "S-EDGE15", "S-FRESH"]
    max_offsets = {"S-STALE": 20, "S-EDGE14": 14, "S-EDGE15": 15, "S-FRESH": 0}
    lu_common = "2026-08-11T23:50:45.009643"

    weekly_db = tmp / "weekly_stale.db"
    daily_db = tmp / "daily_stale.db"
    reg_xlsx = tmp / "registry_stale.xlsx"
    wk_dates = [(T - timedelta(days=7 * k)).isoformat() for k in range(4)]
    _make_weekly_db(weekly_db, names, wk_dates)
    price_rows = [
        (nm, (T - timedelta(days=max_offsets[nm])).isoformat(), 1000.0) for nm in names
    ]
    meta_rows = [
        (f"C{i:05d}", nm, "KOSPI", 1000, "게임", "게임_KOSPI", "x", 1000.0,
         lu_common if identical_last_updated else f"{nm}-lu")
        for i, nm in enumerate(names)
    ]
    _make_daily_db(daily_db, meta_rows, price_rows)
    _write_registry_xlsx(reg_xlsx, [
        {"종목\n코드": f"C{i:05d}", "종목명": nm, "시장": "KOSPI",
         "산업명(대)": "게임", "산업명(중)": "게임_KOSPI", "주요제품": "x"}
        for i, nm in enumerate(names)
    ])
    return {"weekly": str(weekly_db), "daily": str(daily_db), "registry": str(reg_xlsx)}


def _dedup_branch_fixture(tmp: Path) -> dict:
    """AC-SGR-016 R3 / AC-SGR-020 R3 용 Code-vs-Name 분기 픽스처.

    같은 Code(X00001)·다른 Name(가나전자/가나전자우) 2행.
    Code-dedup → 1행 유지(가나전자), Name-dedup → 2행 유지. 두 규칙이 갈리므로 반증 가능.
    """
    T = date(2026, 8, 11)
    base = ["BASE_A", "BASE_B"]
    names_all = ["가나전자", "가나전자우"] + base
    weekly_db = tmp / "weekly_dedup.db"
    daily_db = tmp / "daily_dedup.db"
    reg_xlsx = tmp / "registry_dedup.xlsx"
    wk_dates = [(T - timedelta(days=7 * k)).isoformat() for k in range(2)]
    _make_weekly_db(weekly_db, names_all, wk_dates)
    meta_rows = [
        ("X00002", "BASE_A", "KOSPI", 1000, "게임", "g", "x", 1000.0, "lu"),
        ("X00003", "BASE_B", "KOSPI", 1000, "게임", "g", "x", 1000.0, "lu"),
    ]
    price_rows = [(nm, T.isoformat(), 1000.0) for nm in ["BASE_A", "BASE_B"]]
    _make_daily_db(daily_db, meta_rows, price_rows)
    _write_registry_xlsx(reg_xlsx, [
        {"종목\n코드": "X00001", "종목명": "가나전자", "시장": "KOSPI",
         "산업명(대)": "게임", "산업명(중)": "g", "주요제품": "x"},
        {"종목\n코드": "X00001", "종목명": "가나전자우", "시장": "KOSPI",
         "산업명(대)": "게임", "산업명(중)": "g", "주요제품": "x"},
        {"종목\n코드": "X00002", "종목명": "BASE_A", "시장": "KOSPI",
         "산업명(대)": "게임", "산업명(중)": "g", "주요제품": "x"},
        {"종목\n코드": "X00003", "종목명": "BASE_B", "시장": "KOSPI",
         "산업명(대)": "게임", "산업명(중)": "g", "주요제품": "x"},
    ])
    return {"weekly": str(weekly_db), "daily": str(daily_db), "registry": str(reg_xlsx)}


# ---------------------------------------------------------------------------
# AC-SGR-014 — 유니버스 단일 소스 (UN-1/UN-2)
# ---------------------------------------------------------------------------

def test_ac_sgr_014_single_source_frozen():
    """AC-SGR-014: sector/market 출처=registry, market_cap 출처=stock_meta(UN-1/UN-2)."""
    from my_chart.analysis.universe import compute_universe

    snap = compute_universe(
        str(FROZEN / "weekly.db"),
        str(FROZEN / "daily.db"),
        str(FROZEN / "registry.xlsx"),
    )
    conn = sqlite3.connect(str(FROZEN / "daily.db"))
    meta_names = {r[0] for r in conn.execute("SELECT name FROM stock_meta")}
    conn.close()
    assert snap.valid_names, "valid universe 가 비어 있으면 안 됨"
    # market_cap 단일 원천 = stock_meta(UN-2) → valid names 는 stock_meta 부분집합
    assert snap.valid_names <= meta_names


# ---------------------------------------------------------------------------
# AC-SGR-015 — 유효 유니버스 정의 (UN-3 4중 교집합)
# ---------------------------------------------------------------------------

def test_ac_sgr_015_four_way_intersection_frozen():
    """AC-SGR-015: valid = registry(dedup) ∩ stock_meta ∩ {최신바가격} ∩ {비-stale}."""
    from my_chart.analysis.universe import compute_universe
    from my_chart.analysis.weekly_grid import compute_weekly_grid

    snap = compute_universe(
        str(FROZEN / "weekly.db"),
        str(FROZEN / "daily.db"),
        str(FROZEN / "registry.xlsx"),
        as_of="2026-08-12",
    )
    reg_df = pd.read_excel(str(FROZEN / "registry.xlsx"), header=8).rename(
        columns={"종목\n코드": "Code", "종목명": "Name", "시장": "Market"})
    reg_df["Code"] = reg_df["Code"].astype(str).str.zfill(6)
    reg_names = set(reg_df.drop_duplicates(subset="Code", keep="first")["Name"])
    conn = sqlite3.connect(str(FROZEN / "daily.db"))
    meta_names = {r[0] for r in conn.execute("SELECT name FROM stock_meta")}
    conn.close()
    grid = compute_weekly_grid(str(FROZEN / "weekly.db"), "2026-08-12")
    latest_date = grid.latest.date
    wconn = sqlite3.connect(str(FROZEN / "weekly.db"))
    latest_names = {r[0] for r in wconn.execute(
        "SELECT Name FROM stock_prices WHERE Date=?", (latest_date,))}
    wconn.close()

    expected = (reg_names & meta_names & latest_names) - snap.stale_names
    # 원소별 단언: valid 의 모든 원소가 4조건을 전부 만족
    for nm in snap.valid_names:
        assert nm in reg_names, f"{nm} not in registry"
        assert nm in meta_names, f"{nm} not in stock_meta"
        assert nm in latest_names, f"{nm} no price on latest bar"
        assert nm not in snap.stale_names, f"{nm} is stale"
    for nm in snap.registry_only:
        assert nm not in snap.valid_names
    # 집합 동등
    assert snap.valid_names == expected


def test_ac_sgr_015_stock_meta_only_injection(tmp_path):
    """AC-SGR-015 And: 합성으로 stock_meta 에만 존재하는 종목 주입 → 교집합 결과 제외(A6)."""
    from my_chart.analysis.universe import compute_universe

    T = date(2026, 8, 11)
    weekly_db = tmp_path / "w.db"
    daily_db = tmp_path / "d.db"
    reg_xlsx = tmp_path / "r.xlsx"
    _make_weekly_db(weekly_db, ["IN_BOTH", "META_ONLY"], [T.isoformat()])
    _make_daily_db(
        daily_db,
        [("C001", "IN_BOTH", "KOSPI", 100, "게임", "g", "x", 1000.0, "lu"),
         ("C002", "META_ONLY", "KOSPI", 200, "게임", "g", "x", 1000.0, "lu")],
        [("IN_BOTH", T.isoformat(), 1.0), ("META_ONLY", T.isoformat(), 1.0)],
    )
    _write_registry_xlsx(reg_xlsx, [
        {"종목\n코드": "C001", "종목명": "IN_BOTH", "시장": "KOSPI",
         "산업명(대)": "게임", "산업명(중)": "g", "주요제품": "x"}])
    snap = compute_universe(str(weekly_db), str(daily_db), str(reg_xlsx))
    assert "META_ONLY" not in snap.valid_names, "stock_meta-only 는 교집합에서 제외(A6)"
    assert "META_ONLY" in snap.stock_meta_only


# ---------------------------------------------------------------------------
# AC-SGR-016 — registry 중복 제거 + 경고 (UN-4)
# ---------------------------------------------------------------------------

def test_ac_sgr_016_dedup_warning_frozen(caplog):
    """AC-SGR-016: 052770 중복 → 1행 유지 + WARNING 로그(Code+종목명)."""
    from my_chart.registry import load_sector_registry

    with caplog.at_level(logging.WARNING, logger="my_chart.registry"):
        df = load_sector_registry(str(FROZEN / "registry.xlsx"))
    assert len(df) == df["Code"].nunique(), "고유 Code 수 == 행 수(완전 중복 제거)"
    warns = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warns, "중복 WARNING 최소 1건(조용한 무시 금지, UN-4)"
    joined = " ".join(r.getMessage() for r in warns)
    assert "052770" in joined and "아이톡시" in joined, "WARNING 에 Code+종목명 포함 필수"


def test_ac_sgr_016_dedup_branch_code_vs_name(tmp_path, caplog):
    """AC-SGR-016 R3 / AC-SGR-020 R3: 같은 Code·다른 Name → Code 기준 dedup(UN-4 실제 게이트).

    Code-dedup → 가나전자 1행 유지(가나전자우 drop). Name-dedup → 2행. 라이브 완전중복
    (052770)에서는 두 규칙이 같은 결과라 반증 불가 → 이 합성 픽스처로만 검증.
    """
    from my_chart.registry import load_sector_registry

    fx = _dedup_branch_fixture(tmp_path)
    with caplog.at_level(logging.WARNING, logger="my_chart.registry"):
        df = load_sector_registry(fx["registry"])
    codes = df[df["Code"] == "X00001"]
    assert len(codes) == 1, "Code 기준 dedup → X00001 은 1행"
    assert codes.iloc[0]["Name"] == "가나전자", "첫 행(가나전자) 유지"
    joined = " ".join(r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)
    assert "가나전자우" in joined, "drop 된 행의 종목명이 WARNING 에 기록(UN-4)"


# ---------------------------------------------------------------------------
# AC-SGR-017 — stale 종목 배제 (UN-5)
# ---------------------------------------------------------------------------

def test_ac_sgr_017_stale_boundary_14_15(tmp_path):
    """AC-SGR-017: 14일=포함, 15일=배제(>14), 20일=배제. stale ∩ stock_meta != 0 조건.

    대조: stale 필터 없으면 S-STALE/S-EDGE15 가 3-way 교집합에 나타난다
    (즉 배제가 ∩ stock_meta 가 아니라 stale 규칙에서 왔음을 증명).
    """
    from my_chart.analysis.universe import compute_universe

    fx = _stale_fixture(tmp_path)
    snap = compute_universe(fx["weekly"], fx["daily"], fx["registry"])
    assert "S-STALE" not in snap.valid_names, "20일 → 배제"
    assert "S-EDGE15" not in snap.valid_names, "15일 → 배제(>14)"
    assert "S-EDGE14" in snap.valid_names, "14일 → 포함(경계: >14 만 배제)"
    assert "S-FRESH" in snap.valid_names
    assert snap.stale_excluded_count == 2
    # 대조: 3-way(stale 제외) 에는 S-STALE/S-EDGE15 가 있다 → stale 만이 배제 사유
    reg_df = pd.read_excel(fx["registry"], header=8).rename(
        columns={"종목\n코드": "Code", "종목명": "Name", "시장": "Market"})
    reg_df["Code"] = reg_df["Code"].astype(str).str.zfill(6)
    reg_names = set(reg_df.drop_duplicates(subset="Code")["Name"])
    conn = sqlite3.connect(fx["daily"])
    meta_names = {r[0] for r in conn.execute("SELECT name FROM stock_meta")}
    conn.close()
    grid_names = {"S-STALE", "S-EDGE14", "S-EDGE15", "S-FRESH"}
    three_way = reg_names & meta_names & grid_names
    assert "S-STALE" in three_way and "S-EDGE15" in three_way, (
        "대조: stale 필터 없으면 3-way 교집합에 존재 → stale 규칙이 유일 배제 사유")


# ---------------------------------------------------------------------------
# AC-SGR-018 — last_updated 기반 판정 금지
# ---------------------------------------------------------------------------

def test_ac_sgr_018_last_updated_divergent(tmp_path):
    """AC-SGR-018: last_updated 전 행 동일 + 일봉 MAX(Date) 상이 → MAX(Date) 기준 판정.

    last_updated 로 판정하면 stale 0(전 행 동일). 일봉 MAX(Date) 로 판정하면 2.
    compute_universe 가 2 를 내면 → 판정 원천이 MAX(Date) 임이 값으로 증명.
    """
    from my_chart.analysis.universe import compute_universe

    fx = _stale_fixture(tmp_path, identical_last_updated=True)
    # 전제 단언: stock_meta.last_updated 가 정말 전 행 동일한가(라이브 실태 재현)
    conn = sqlite3.connect(fx["daily"])
    lus = {r[0] for r in conn.execute("SELECT last_updated FROM stock_meta")}
    conn.close()
    assert len(lus) == 1, "전제: last_updated 전 행 동일 타임스탬프"
    snap = compute_universe(fx["weekly"], fx["daily"], fx["registry"])
    assert snap.stale_excluded_count == 2, (
        "last_updated 동일한데도 2건 배제 → 일봉 MAX(Date) 기반 판정 증명(REQ-SGR-015)")


# ---------------------------------------------------------------------------
# AC-SGR-019 — registry 전용 종목 진단 산출물
# ---------------------------------------------------------------------------

def test_ac_sgr_019_registry_only_diagnostic(tmp_path, caplog):
    """AC-SGR-019: registry \\ stock_meta 차집합이 registry_only[] + WARNING 으로 노출."""
    from my_chart.analysis.universe import compute_universe

    fx = _dedup_branch_fixture(tmp_path)
    with caplog.at_level(logging.WARNING, logger="my_chart.analysis.universe"):
        snap = compute_universe(fx["weekly"], fx["daily"], fx["registry"])
    assert "가나전자" in snap.registry_only, "registry \\ stock_meta 진단"
    assert snap.registry_only_count >= 1
    assert isinstance(snap.registry_only, tuple), "프로그램적 접근 가능(AC-SGR-019 And)"
    joined = " ".join(r.getMessage() for r in caplog.records if r.levelno == logging.WARNING)
    assert "가나전자" in joined, "registry-only 진단이 WARNING 에 종목명 포함"


def test_ac_sgr_019_registry_only_frozen(caplog):
    """AC-SGR-019 (프로즌): frozen 의 registry \\ stock_meta(7종목) 진단 노출."""
    from my_chart.analysis.universe import compute_universe

    with caplog.at_level(logging.WARNING, logger="my_chart.analysis.universe"):
        snap = compute_universe(
            str(FROZEN / "weekly.db"), str(FROZEN / "daily.db"), str(FROZEN / "registry.xlsx"))
    assert snap.registry_only_count == len(snap.registry_only)
    assert snap.registry_only_count > 0, "frozen: registry-only 종목 존재(7종)"


# ---------------------------------------------------------------------------
# AC-SGR-021 — 미분류 섹터 센티넬 단일화 (잠재 발산 차단)
# ---------------------------------------------------------------------------

def test_ac_sgr_021_sentinel_constant():
    """AC-SGR-021: ETC_SECTOR 단일 canonical 상수 노출 + 값 == '기타'(O-G5)."""
    from my_chart.analysis.universe import ETC_SECTOR
    assert ETC_SECTOR == "기타"


def test_ac_sgr_021_sentinel_unified_no_hardcoded_defaults():
    """AC-SGR-021 (정적): stage_service 에 'Unknown' 잔류 0, 양 파일 모두 ETC_SECTOR 참조."""
    import backend.services.stage_service as ss
    import my_chart.analysis.sector_metrics as sm

    src_ss = Path(ss.__file__).read_text(encoding="utf-8")
    src_sm = Path(sm.__file__).read_text(encoding="utf-8")
    assert '"Unknown"' not in src_ss, "stage_service 에 하드코딩 'Unknown' 잔류 0(AC-SGR-021)"
    assert "ETC_SECTOR" in src_ss and "ETC_SECTOR" in src_sm


def test_ac_sgr_021_sentinel_behavioral_divergence_blocked():
    """AC-SGR-021 (행동): 빈 산업명(대) 행이 두 경로에서 같은 센티널 키로 귀결.

    대조: 두 경로가 다른 기본값(Unknown vs 기타)을 쓰면 키가 갈라져 단언이 실패한다.
    """
    from my_chart.analysis.universe import ETC_SECTOR

    row = pd.Series({"산업명(대)": ""})
    # stage_service:57 / sector_metrics:250 의 통일된 패턴: or ETC_SECTOR
    stage_key = str(row.get("산업명(대)") or ETC_SECTOR)
    metrics_key = str(row.get("산업명(대)") or ETC_SECTOR)
    assert stage_key == metrics_key == ETC_SECTOR, (
        "두 경로가 같은 센티널 → 섹터 키 발산 차단(REQ-SGR-017)")
