"""적재 supersede 테스트 (AC-SGR-012 / AC-SGR-013, REQ-SGR-010).

REQ-SGR-010: weekly 적재가 ISO 주 W (종목 N) 에 대한 바를 기록할 때, 같은
``(Name, ISO 주 W)`` 에서 **이번 실행이 기록한 바보다 이른 날짜**의 행을 삭제한다.
이후 동일 ``(Name, ISO 주)`` 당 행이 최대 1개만 만들어진다(going-forward).
과거(이번 실행이 기록하지 않은) ISO 주의 행은 **절대 삭제하지 않는다**.

본 테스트는 SYNTHETIC in-memory/temp DB 만 사용한다(M4 [HARD] — 라이브
``Output/stock_data_weekly.db`` 에 supersede 를 실행하지 않는다).

AC-SGR-012 — 주중 재적재 supersede:
  같은 ISO 주 화요일 바로 재적재 → (Name, ISO 주) 행이 1개(화요일)만 남는다.
  과거 ISO 주(W-1 이전)의 다중 날짜 행은 보존된다.
  삭제 행 수가 INFO 로그({iso_week, deleted_rows})에 기록된다.
AC-SGR-013 — supersede 안전장치:
  supersede=False/--no-supersede → 기존 행이 삭제되지 않고 다중 날짜 행이 남는다.
  이 경로에서도 AC-SGR-001(조회 시점 격자)은 통과 — 적재 보호와 조회 정규화 독립.
"""

import inspect
import logging
import sqlite3
from datetime import date

from my_chart.analysis.weekly_grid import compute_weekly_grid
from my_chart.db.weekly import (
    _STOCK_PRICES_COLS,
    _batch_insert,
    _ensure_stock_prices_table,
    _supersede_same_iso_week_rows,
    generate_price_db,
)

# --- fixture dates (ISO weeks verified) ----------------------------------
# 2026-W02: Mon/Tue/Wed/Fri
MON_W = "2026-01-05"
TUE_W = "2026-01-06"
WED_W = "2026-01-07"
FRI_W = "2026-01-09"
# 2025-W50 (4주 과거): Mon/Fri — 이번 실행이 기록하지 않는 과거 주
PAST_MON = "2025-12-08"
PAST_FRI = "2025-12-12"


def _iso(date_str: str) -> tuple[int, int]:
    return date.fromisoformat(date_str).isocalendar()[:2]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    _ensure_stock_prices_table(conn)
    return conn


def _row(name: str, date_str: str) -> tuple:
    """``_STOCK_PRICES_COLS`` 순서의 행 튜플(Name/Date 만 설정, 나머지 NULL).
    supersede 는 (Name, Date) 만 읽으므로 수치 컬럼은 NULL 이어도 무방하다."""
    row = [None] * len(_STOCK_PRICES_COLS)
    row[0] = name
    row[1] = date_str
    return tuple(row)


def _dates_for(conn: sqlite3.Connection, name: str) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT Date FROM stock_prices WHERE Name = ? ORDER BY Date", (name,))]


def _count_for(conn: sqlite3.Connection, name: str) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM stock_prices WHERE Name = ?", (name,)).fetchone()[0]


# === AC-SGR-012 — 주중 재적재 supersede ==================================


def test_supersede_removes_earlier_same_iso_week_row_ac012():
    """같은 ISO 주: 과거 실행이 남긴 월요일 바 + 이번 실행이 기록한 화요일 바.
    supersede 후 (Name, ISO 주) 행이 1개(화요일)만 남는다."""
    assert _iso(MON_W) == _iso(TUE_W)  # 전제: 같은 ISO 주(W02)
    conn = _conn()
    _batch_insert(conn, [_row("AAA", MON_W)])  # 과거 실행이 남긴 월요일 바
    _batch_insert(conn, [_row("AAA", TUE_W)])  # 이번 실행이 기록한 화요일 바

    deleted = _supersede_same_iso_week_rows(conn, [("AAA", TUE_W)])

    assert deleted == 1
    assert _dates_for(conn, "AAA") == [TUE_W]  # 월요일 제거·화요일 잔존 → 1행


def test_supersede_preserves_past_iso_week_rows_ac012():
    """과거 ISO 주(W-4)의 다중 날짜 행은 이번 실행이 기록한 주에 한정해
    삭제하므로 그대로 존재한다(과거 이력 보존)."""
    assert _iso(PAST_MON) == _iso(PAST_FRI)   # 전제: 과거 주도 2개 날짜
    assert _iso(PAST_MON) != _iso(TUE_W)      # 전제: 이번 실행 주와 상이
    conn = _conn()
    # 과거 주(2025-W50): 2개 날짜 — 이번 실행은 기록하지 않음
    _batch_insert(conn, [_row("AAA", PAST_MON), _row("AAA", PAST_FRI)])
    # 이번 실행 주(2026-W02): 과거 실행 월요일 + 이번 실행 화요일
    _batch_insert(conn, [_row("AAA", MON_W)])
    _batch_insert(conn, [_row("AAA", TUE_W)])

    deleted = _supersede_same_iso_week_rows(conn, [("AAA", TUE_W)])

    assert deleted == 1  # W02 월요일 1건만 삭제
    # 과거 주 2일은 보존, W02 는 화요일만 잔존
    assert _dates_for(conn, "AAA") == [PAST_MON, PAST_FRI, TUE_W]


def test_supersede_logs_deleted_rows_at_info_ac012(caplog):
    """삭제 행 수가 INFO 로그에 {iso_week, deleted_rows} 형태로 기록된다."""
    conn = _conn()
    _batch_insert(conn, [_row("AAA", MON_W)])
    _batch_insert(conn, [_row("AAA", TUE_W)])

    with caplog.at_level(logging.INFO, logger="my_chart.db.weekly"):
        deleted = _supersede_same_iso_week_rows(conn, [("AAA", TUE_W)])

    assert deleted == 1
    msgs = " ".join(r.getMessage() for r in caplog.records if r.levelno >= logging.INFO)
    iy, iw = _iso(TUE_W)
    assert f"W{iw:02d}" in msgs, msgs            # iso_week 식별자
    assert f"deleted_rows=1" in msgs, msgs        # 삭제 행 수


def test_supersede_keeps_max_among_three_same_week_dates_ac012():
    """한 ISO 주에 3개 날짜(월·수 사전 + 금 이번 실행)가 있을 때 이번 실행
    기준 바(금)보다 이른 날짜(월·수)만 삭제되고 금이 잔존한다."""
    assert _iso(MON_W) == _iso(WED_W) == _iso(FRI_W)
    conn = _conn()
    _batch_insert(conn, [_row("AAA", MON_W), _row("AAA", WED_W)])
    _batch_insert(conn, [_row("AAA", FRI_W)])

    deleted = _supersede_same_iso_week_rows(conn, [("AAA", FRI_W)])

    assert deleted == 2
    assert _dates_for(conn, "AAA") == [FRI_W]


# === AC-SGR-013 — supersede 안전장치 ====================================


def test_supersede_flag_contrast_enabled_vs_disabled_ac013():
    """동일 픽스처에서 enabled 경로는 이전 same-week 행을 삭제하고, disabled
    경로(supersede=False → 함수 미호출)는 다중 날짜 행을 그대로 둔다(대조)."""

    def fresh_fixture() -> sqlite3.Connection:
        c = _conn()
        _batch_insert(c, [_row("AAA", MON_W)])
        _batch_insert(c, [_row("AAA", TUE_W)])
        return c

    # enabled: supersede 호출
    on = fresh_fixture()
    deleted_on = _supersede_same_iso_week_rows(on, [("AAA", TUE_W)])
    # disabled: supersede 미호출(= --no-supersede 경로)
    off = fresh_fixture()
    cnt_off = _count_for(off, "AAA")

    assert deleted_on == 1
    assert _count_for(on, "AAA") == 1        # enabled: 화요일 1행
    assert cnt_off == 2                      # disabled: 월·화 2행(중복 허용)


def test_supersede_disabled_grid_still_normalizes_ac013(tmp_path):
    """supersede=False 로 다중 날짜 행이 남아도 조회 시점 격자(compute_weekly_grid)
    는 ISO 주당 1일로 정규화한다 — 적재 보호와 조회 정규화가 독립(AC-SGR-001)."""
    db = tmp_path / "sup_disabled.db"
    conn = sqlite3.connect(str(db))
    _ensure_stock_prices_table(conn)
    # 원시 테이블에 중복(과거 주 2일 + 이번 주 2일)을 그대로 둔다(supersede 안 함)
    _batch_insert(conn, [_row("AAA", PAST_MON), _row("AAA", PAST_FRI),
                         _row("AAA", MON_W), _row("AAA", TUE_W)])
    conn.commit()
    conn.close()

    # supersede=False 경로 → 삭제 없음 → 원시 4행 보존
    raw = sqlite3.connect(str(db)).execute(
        "SELECT COUNT(*) FROM stock_prices").fetchone()[0]
    assert raw == 4

    grid = compute_weekly_grid(str(db), as_of="2026-06-01")
    # CG-1 불변식: 격자는 ISO 주당 최대 1일(AC-SGR-001 조회 정규화)
    by_week: dict[tuple[int, int], list[str]] = {}
    for d in grid.dates:
        by_week.setdefault(_iso(d), []).append(d)
    assert all(len(v) == 1 for v in by_week.values()), by_week
    # W02 대표 = MAX(TUE_W); 중복 월요일(MON_W)은 격자에서 나타나지 않는다
    assert TUE_W in grid.dates
    assert MON_W not in grid.dates


# --- no-op guards (Beyonce rule: pin the defensive branches) -------------


def test_supersede_empty_written_is_noop():
    conn = _conn()
    _batch_insert(conn, [_row("AAA", MON_W)])
    assert _supersede_same_iso_week_rows(conn, []) == 0
    assert _count_for(conn, "AAA") == 1


def test_supersede_no_earlier_same_week_date_is_noop():
    """이번 실행이 기록한 바가 그 주의 가장 이른 날짜면 삭제 대상이 없다."""
    conn = _conn()
    _batch_insert(conn, [_row("AAA", MON_W)])  # 월요일 = 그 주 최소
    assert _supersede_same_iso_week_rows(conn, [("AAA", MON_W)]) == 0
    assert _count_for(conn, "AAA") == 1


# --- defensive: unparseable date strings are skipped, never crash ---------


def test_supersede_skips_unparseable_written_date():
    """written_name_dates 의 파싱 불가 날짜는 무시된다(정상 same-week 행은
    여전히 supersede). _iso_year_week except 경로 + max_written None 건너뜀."""
    conn = _conn()
    _batch_insert(conn, [_row("AAA", MON_W), _row("AAA", TUE_W)])
    deleted = _supersede_same_iso_week_rows(
        conn, [("AAA", "not-a-date"), ("AAA", TUE_W)])
    assert deleted == 1  # 화요일이 월요일을 supersede; 파싱불가 엔트리는 무시
    assert _dates_for(conn, "AAA") == [TUE_W]


def test_supersede_all_unparseable_written_is_noop():
    """모든 written 날짜가 파싱 불가면 max_written 이 비어 no-op(삭제 0)."""
    conn = _conn()
    _batch_insert(conn, [_row("AAA", MON_W)])
    assert _supersede_same_iso_week_rows(
        conn, [("AAA", "bad1"), ("AAA", "bad2")]) == 0
    assert _count_for(conn, "AAA") == 1


def test_supersede_skips_unparseable_db_date():
    """DB 의 파싱 불가 날짜(legacy 데이터)는 ISO 주 그룹핑에서 건너뛴다.
    해당 행은 어떤 ISO 주에도 속하지 않으므로 삭제되지 않는다."""
    conn = _conn()
    _batch_insert(conn, [_row("AAA", MON_W), _row("AAA", TUE_W)])
    conn.execute(
        "INSERT OR REPLACE INTO stock_prices (Name, Date) VALUES (?, ?)",
        ("AAA", "garbage"),
    )
    conn.commit()
    deleted = _supersede_same_iso_week_rows(conn, [("AAA", TUE_W)])
    assert deleted == 1  # 월요일 제거
    dates = _dates_for(conn, "AAA")
    assert TUE_W in dates and "garbage" in dates  # garbage-date 행은 보존


# --- param wiring --------------------------------------------------------


def test_generate_price_db_has_supersede_param_default_true():
    """generate_price_db 가 supersede 플래그(기본 True)를 노출한다."""
    sig = inspect.signature(generate_price_db)
    assert "supersede" in sig.parameters
    assert sig.parameters["supersede"].default is True


def test_start_update_threads_supersede_param_default_true():
    """엔드포인트 진입점(start_update)도 supersede 플래그를 전달한다(최소 배선).
    --no-supersede 는 이 매개변수로 런타임 무력화된다."""
    from backend.services.db_service import start_update
    sig = inspect.signature(start_update)
    assert "supersede" in sig.parameters
    assert sig.parameters["supersede"].default is True
