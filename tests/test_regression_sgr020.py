# coding: utf-8
"""SPEC-SECTOR-GRID-001 AC-SGR-020 (REQ-SGR-018) — 회귀 방지 게이트.

아래 R1~R5 는 전부 **올바른 결과**다. 본 SPEC(M1~M5)이 고친 격자·유니버스 규칙이
만들어낸 의도된 변화이며, 향후 리뷰어가 "되돌리는" 것을 막기 위해 기대값으로 고정한다.

각 R 은 테스트 함수의 docstring 에 "이것은 의도된 변화다"를 명시하고, 릴리스 노트
문구를 함께 기재한다(acceptance.md §AC-SGR-020 마지막 문단). 단 docstring 은 **보조
설명일 뿐 검사 수단이 아니다** — R1~R5 전부가 실행 가능한 ``assert`` 를 갖는다(R5).

게이팅 단언은 전부 §3 프로즌 픽스처(``tests/fixtures/frozen/weekly-2026-08-12/``) 위에서
수행한다. 라이브 DB 실행은 비게이팅 스모크다(acceptance.md §3 규약 1).
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

FROZEN = Path(__file__).resolve().parent / "fixtures" / "frozen" / "weekly-2026-08-12"


# ---------------------------------------------------------------------------
# 픽스처 빌더 — R3 Code-vs-Name 분기 (acceptance.md AC-SGR-020 R3(b) 합성 픽스처)
# ---------------------------------------------------------------------------

def _write_registry_xlsx(path: Path, rows: list[dict]) -> None:
    """registry.xlsx 를 header=8 구조로 기록(rows 0~7 빈, row 8 = 헤더)."""
    df = pd.DataFrame(
        rows,
        columns=["종목\n코드", "종목명", "시장", "산업명(대)", "산업명(중)", "주요제품"],
    )
    with pd.ExcelWriter(str(path), engine="openpyxl") as w:
        df.to_excel(w, sheet_name="Sheet1", startrow=8, index=False)


def _make_weekly_db(path: Path, names: list[str], dates: list[str]) -> None:
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


def _dedup_branch_fixture(tmp: Path) -> Path:
    """R3(b): 같은 Code(X00001)·다른 Name(가나전자/가나전자우) 2행 registry.

    Code 기준 dedup → 1행 유지(게임 base+1). Name 기준 dedup → 2행 유지(base+2).
    라이브 052770 은 완전 중복이라 두 규칙이 같은 32를 내 반증 불가 → 이 합성 픽스처로만
    UN-4 "Code 기준" 규칙을 검증한다(acceptance.md AC-SGR-020 R3(b)).
    """
    T = date(2026, 8, 11)
    reg = tmp / "reg_branch.xlsx"
    wk = tmp / "weekly_branch.db"
    _write_registry_xlsx(reg, [
        {"종목\n코드": "X00001", "종목명": "가나전자", "시장": "KOSPI",
         "산업명(대)": "게임", "산업명(중)": "g", "주요제품": "x"},
        {"종목\n코드": "X00001", "종목명": "가나전자우", "시장": "KOSPI",
         "산업명(대)": "게임", "산업명(중)": "g", "주요제품": "x"},
    ])
    _make_weekly_db(wk, ["가나전자"], [(T - timedelta(days=7 * k)).isoformat() for k in range(2)])
    return reg


# ---------------------------------------------------------------------------
# R1 — history(weeks=12) span 이 36일 → 84±7일로 늘어난다
# ---------------------------------------------------------------------------

def test_r1_history_12_span_84_days():
    """R1: 이것은 의도된 변화다. history(weeks=12) span 이 36일(구 LIMIT 36행)에서
    84±7일(정규 격자 12바)로 늘어난다.

    릴리스 노트: "히스토리 구간이 12주 = 84일로 늘어납니다(기존 36일)."
    """
    from my_chart.analysis.weekly_grid import compute_weekly_grid, history

    grid = compute_weekly_grid(str(FROZEN / "weekly.db"), as_of="2026-08-12")
    sl = history(grid, 12)
    assert len(sl.bars) == 12, f"R1: history(12) 바 수 = {len(sl.bars)} (기대 12)"
    span_days = (
        date.fromisoformat(sl.bars[-1].date) - date.fromisoformat(sl.bars[0].date)
    ).days
    # span_days 는 36(구현 전)이 아니라 84±7 이다
    assert 77 <= span_days <= 91, f"R1: 12주 span = {span_days}일 (기대 77~91, 구 36)"


# ---------------------------------------------------------------------------
# R2 — rank_change 기준일이 t−28d 이하 가장 가까운 격자 바로 이동 (양쪽 경계 필수)
# ---------------------------------------------------------------------------

def test_r2_anchor_28_both_bounds():
    """R2: 이것은 의도된 변화다. rank_change 기준일이 구 LIMIT 1 OFFSET 3 의
    2026-07-31(11일 전)에서 ``t−28d`` 이하의 가장 가까운 격자 바로 이동한다.

    상한 ``<= 35`` 가 없으면 ``anchor(t, 364)`` 를 ``anchor(t, 28)`` 자리에 잘못 배선해도
    통과한다(둘 다 ``>= 28``). 양쪽 경계 ``28 <= delta <= 35`` 가 "이하의 가장 가까운 바"를
    실제로 강제한다(정규 격자 간격 6~10일 → t−28d 직전 바는 최대 t−35d 근방).

    릴리스 노트: "rank_change(순위 변동) 비교 기준일이 4주 전 정규 바로 고정됩니다."
    """
    from my_chart.analysis.weekly_grid import compute_weekly_grid, anchor

    grid = compute_weekly_grid(str(FROZEN / "weekly.db"), as_of="2026-08-12")
    t = "2026-08-07"
    t_d = date.fromisoformat(t)
    a28 = anchor(grid, t, 28)
    assert a28 is not None, "R2: anchor(t,28) 반환바 존재"
    delta = (t_d - date.fromisoformat(a28.date)).days
    # 양쪽 경계 필수 — 하한(>=28)만으로는 anchor(t,364) 도 통과한다
    assert 28 <= delta <= 35, f"R2: anchor(t,28) delta = {delta}일 (기대 28~35, 양측)"

    # 대조: anchor(t,91) / anchor(t,364) 의 delta 는 [28,35] 밖 → 상한이 이들을 구별
    a91 = anchor(grid, t, 91)
    a364 = anchor(grid, t, 364)
    assert a91 is not None and a364 is not None
    delta91 = (t_d - date.fromisoformat(a91.date)).days
    delta364 = (t_d - date.fromisoformat(a364.date)).days
    assert delta91 > 35, f"R2 대조: anchor(t,91) delta={delta91} > 35 (R2 범위 밖)"
    assert delta364 > 35, f"R2 대조: anchor(t,364) delta={delta364} > 35 (오배선 감지)"


# ---------------------------------------------------------------------------
# R3 — 게임 섹터 구성종목 33 → 32 (dedup). (a) 라이브값 고정 + (b) Code/Name 분기
# ---------------------------------------------------------------------------

def test_r3_game_member_count_32_frozen():
    """R3(a): 이것은 의도된 변화다. 게임 섹터 구성종목이 33행(중복 052770 포함)에서
    Code 기준 dedup 후 **32**로 줄어든다.

    우변은 리터럴 32(같은 함수에서 나온 값이 아님) — 좌우변이 같은 방식으로 산출되면
    항상 참인 항진명제가 되는 것을 막는다(acceptance.md AC-SGR-020 R3(a)).

    릴리스 노트: "게임 섹터 종목 수가 중복(아이톡시 052770) 제거로 33 → 32로 정정됩니다."
    """
    from my_chart.registry import load_sector_registry

    df = load_sector_registry(str(FROZEN / "registry.xlsx"))
    game = df[df["산업명(대)"] == "게임"]
    game_member_count = len(game)
    assert game_member_count == 32, f"R3(a): 게임 섹터 종목 수 = {game_member_count} (기대 32)"


def test_r3_dedup_key_is_code_not_name(tmp_path):
    """R3(b): 이것은 의도된 변화다. UN-4 dedup 키는 Code(같은 Code → 1행)다.

    합성 픽스처(같은 Code·다른 Name 2행)에서만 검증 가능 — 라이브 052770 은 완전 중복이라
    Code-dedup == Name-dedup == 32 로 반증 불가(acceptance.md AC-SGR-020 R3(b)).

    Code 기준 → 1행 유지(가나전자). Name 기준이면 2행(가나전자+가나전자우).
    """
    from my_chart.registry import load_sector_registry

    reg = _dedup_branch_fixture(tmp_path)
    df = load_sector_registry(reg)
    codes_x = df[df["Code"] == "X00001"]
    assert len(codes_x) == 1, f"R3(b): Code 기준 dedup → X00001 은 1행 (실제 {len(codes_x)})"
    # 대조: Name 기준 dedup 이었으면 2행 이었을 것(가나전자 ≠ 가나전자우)
    raw = pd.read_excel(reg, header=8).rename(columns={"종목\n코드": "Code", "종목명": "Name"})
    raw["Code"] = raw["Code"].astype(str).str.zfill(6)
    assert len(raw[raw["Code"] == "X00001"]) == 2, "R3(b) 대조: 원본엔 X00001 이 2행(Name 상이)"


# ---------------------------------------------------------------------------
# R4 — 정규 격자 바 수(346) < 원시 고유 날짜 수(385)
# ---------------------------------------------------------------------------

def test_r4_grid_fewer_than_raw_dates():
    """R4: 이것은 의도된 변화다. 정규 격자 바 수(346)가 원시 고유 날짜 수(385)보다 적다.
    다중 날짜 주가 1바로 정규화(CG-1)되기 때문이다.

    릴리스 노트: "히스토리 x축 포인트 수가 다중 날짜 주 정규화로 약간 줄어들 수 있습니다
    (중복 바 제거, 차트가 더 균일해짐)."
    """
    from my_chart.analysis.weekly_grid import compute_weekly_grid

    grid = compute_weekly_grid(str(FROZEN / "weekly.db"), as_of="2026-08-12")
    conn = sqlite3.connect(str(FROZEN / "weekly.db"))
    raw_distinct = conn.execute(
        "SELECT COUNT(DISTINCT Date) FROM stock_prices"
    ).fetchone()[0]
    conn.close()
    assert len(grid.dates) == 346, f"R4: 격자 바 = {len(grid.dates)} (프로즌 기대 346)"
    assert raw_distinct == 385, f"R4: 원시 날짜 = {raw_distinct} (프로즌 기대 385)"
    assert len(grid.dates) < raw_distinct, (
        f"R4: 격자({len(grid.dates)}) < 원시({raw_distinct}) — 다중 날짜 주 정규화"
    )


# ---------------------------------------------------------------------------
# R5 — history_grid(345) < grid(346) < 원시 고유 날짜(385) 프로즌 리터럴 3중 고정
# ---------------------------------------------------------------------------

# 프로즌 스냅샷(weekly-2026-08-12) 실측 리터럴. 우변이 좌변과 같은 함수에서 나오지 않게
# 리터럴로 못 박는다 — acceptance.md AC-SGR-020 R5(v0.3.0 재기술).
_FROZEN_HISTORY_GRID = 345   # CG-2 가 진행 중인 주(W33)를 제외한 히스토리 뷰
_FROZEN_GRID = 346           # CG-1 적용, 진행 중인 주 포함한 전체 격자
_FROZEN_RAW_DISTINCT = 385   # 원시 고유 날짜(격자 규칙 미적용)


def test_r5_history_grid_frozen_literals_and_strict_ordering():
    """R5: 이것은 의도된 변화다. 히스토리 뷰가 진행 중인 주까지 제외해 격자보다 한 바
    더 적다 — ``345 < 346 < 385`` 의 엄격한 3중 부등.

    **v0.3.0 재기술 — 이전 판은 수학적 항진명제였다.** 이전 판은
    ``len(history_grid) <= len(raw_row_dates)`` 였다. 격자 바는 원시 날짜에서 **선별**
    되므로 이 부등식은 **어떤 구현에서도 참이다** — 격자 규칙을 한 줄도 구현하지 않고
    원시 날짜를 그대로 돌려줘도 ``385 <= 385`` 로 통과했다.

    재기술 R5 가 잡는 순진한 구현(전부 이전 판을 통과하던 것들):

    ======================================== ============ ============
    순진한 동작                                 이전 판 R5    재기술 R5
    ======================================== ============ ============
    원시 날짜를 그대로 히스토리로 반환 (385)        통과          실패
    CG-1 만 적용, CG-2(진행 중인 주 제외) 누락 (346)  통과          실패
    진행 중인 주를 두 번 제외 (344)                통과          실패
    ======================================== ============ ============

    릴리스 노트: "RRG 궤적·Bump x축이 정규 격자 기준으로 재정렬되어 포인트 수가 약간
    줄어들 수 있으며, 궤적이 더 짧고 일관되게 표시됩니다."
    """
    from my_chart.analysis.weekly_grid import compute_weekly_grid

    grid = compute_weekly_grid(str(FROZEN / "weekly.db"), as_of="2026-08-12")
    conn = sqlite3.connect(str(FROZEN / "weekly.db"))
    raw_distinct_dates = conn.execute(
        "SELECT COUNT(DISTINCT Date) FROM stock_prices"
    ).fetchone()[0]
    conn.close()

    history_grid = grid.history
    # 3중 리터럴 고정 — 우변은 전부 리터럴(같은 함수 산출값이 아님)
    assert len(history_grid) == _FROZEN_HISTORY_GRID, (
        f"R5: history_grid = {len(history_grid)} (프로즌 기대 {_FROZEN_HISTORY_GRID})"
    )
    assert len(grid.dates) == _FROZEN_GRID, (
        f"R5: grid = {len(grid.dates)} (프로즌 기대 {_FROZEN_GRID})"
    )
    assert raw_distinct_dates == _FROZEN_RAW_DISTINCT, (
        f"R5: 원시 고유 날짜 = {raw_distinct_dates} (프로즌 기대 {_FROZEN_RAW_DISTINCT})"
    )

    # R4 와 같은 프로즌 스냅샷에서 엄격한 3중 부등 — 어느 한 값이 다른 값과 같아지는
    # 순간 규칙 하나가 죽은 것이다(acceptance.md AC-SGR-020 R5 마지막 And).
    assert len(history_grid) < len(grid.dates) < raw_distinct_dates, (
        f"R5: 엄격 3중 부등 실패 — history_grid({len(history_grid)}) < "
        f"grid({len(grid.dates)}) < raw({raw_distinct_dates})"
    )

    # 대조 단언: history_grid 대신 grid(진행 중인 주 포함)를 반환하도록 되돌리면
    # 345 != 346 이므로 위 첫 단언이 실패한다 — CG-2 제외가 실제로 일어남을 값으로 증명.
    assert len(grid.dates) != _FROZEN_HISTORY_GRID, (
        "R5 대조: grid 를 history_grid 자리에 되돌리면 R5 가 실패해야 한다 "
        f"(grid={len(grid.dates)} == {_FROZEN_HISTORY_GRID} 이면 CG-2 제외가 무의미)"
    )
