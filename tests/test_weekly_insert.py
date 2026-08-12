"""Round-trip tests for weekly.py column-name INSERT (AC-SGR-009/010/011).

Lesson #8: positional `INSERT ... VALUES (?, ?, ...)` corrupts silently when a
legacy `ALTER TABLE ... ADD COLUMN` appended a column at the physical table end,
making the live physical column order diverge from the insert tuple order.
This caused a 1.3M-row corruption incident in daily.py (SPEC-SMA5-FILTER-001
v1.0.4) — since fixed at daily.py:267-276 with the column-name form. M3 of
SPEC-SECTOR-GRID-001 applies the identical fix to weekly.py.

Each numeric column is loaded with a distinct sentinel (its own index) so a
column->value shift is unambiguously detectable on read-back.

AC-SGR-009 — fresh-DDL round-trip: column-name insert writes+reads identical
              values on a fresh-DDL DB (both stock_prices and relative_strength).
AC-SGR-010 — legacy-ALTER round-trip [HARD, Lesson #8 gate]: column-name insert
              keeps every column's value under a legacy-Alter-shifted physical
              order, AND the same fixture executed with a positional insert
              demonstrably shifts (falsifiability — the test must catch the real
              defect, not be vacuously true).
AC-SGR-011 — positional INSERT 재도입 금지 (static scan): no positional INSERT
              literal remains in my_chart/db/.
"""

import re
import sqlite3
from pathlib import Path

import pytest

from my_chart.db.weekly import (
    _RELATIVE_STRENGTH_COLS,
    _STOCK_PRICES_COLS,
    _batch_insert,
    _batch_insert_rs,
)

_DB_DIR = Path(__file__).resolve().parent.parent / "my_chart" / "db"
# AC-SGR-011 정적 스캔 패턴 — positional `INSERT ... VALUES (` 리터럴 탐지.
_POSITIONAL_INSERT_RE = re.compile(r"INSERT\s+OR\s+REPLACE\s+INTO\s+\w+\s+VALUES\s*\(")


# --- sentinel fixtures ---------------------------------------------------

def _sentinel(col: str, idx: int):
    """Distinct, identifiable value for a column at position `idx`."""
    if col == "Name":
        return "TESTNAME"
    if col == "Date":
        return "2026-01-01"
    return float(idx)


def _row_from(cols):
    """One row tuple in `cols` order, each numeric column holding its index."""
    return tuple(_sentinel(c, i) for i, c in enumerate(cols))


def _expected_from(cols):
    """Map each column name -> its expected sentinel value after round-trip."""
    return {c: _sentinel(c, i) for i, c in enumerate(cols)}


def _read_back(conn, table, cols):
    names = ", ".join(cols)
    cur = conn.execute(
        f"SELECT {names} FROM {table} WHERE Name = ? AND Date = ?",
        ("TESTNAME", "2026-01-01"),
    )
    row = cur.fetchone()
    assert row is not None, f"no row round-tripped in {table}"
    return dict(zip(cols, row))


def _create_fresh(conn, table, cols):
    """Fresh-DDL: physical order == `cols` (Name/Date TEXT, rest REAL, PK)."""
    defs = []
    for c in cols:
        if c == "Name":
            defs.append("Name TEXT NOT NULL")
        elif c == "Date":
            defs.append("Date TEXT NOT NULL")
        else:
            defs.append(f"{c} REAL")
    defs.append("PRIMARY KEY (Name, Date)")
    conn.execute(f"CREATE TABLE {table} ({', '.join(defs)})")
    conn.commit()


def _create_legacy_alter(conn, table, cols, drop_col):
    """Legacy-Alter fixture: `drop_col` (a middle column) was added late via an
    idempotent `ALTER TABLE ... ADD COLUMN`, so it sits at the PHYSICAL end.
    Physical order = (cols minus drop_col) + [drop_col] != cols."""
    assert drop_col not in ("Name", "Date"), "drop a data column, not a key"
    assert drop_col in cols, f"{drop_col} not in {table} cols"
    old_cols = [c for c in cols if c != drop_col]
    defs = []
    for c in old_cols:
        if c == "Name":
            defs.append("Name TEXT NOT NULL")
        elif c == "Date":
            defs.append("Date TEXT NOT NULL")
        else:
            defs.append(f"{c} REAL")
    defs.append("PRIMARY KEY (Name, Date)")
    conn.execute(f"CREATE TABLE {table} ({', '.join(defs)})")
    # late migration appends the missing column at the physical END
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {drop_col} REAL")
    conn.commit()


def _positional_insert(conn, table, cols, rows):
    """The OLD positional form — included to prove the fixture catches the defect."""
    placeholders = ", ".join(["?"] * len(cols))
    conn.executemany(
        f"INSERT OR REPLACE INTO {table} VALUES ({placeholders})",
        rows,
    )
    conn.commit()


# === AC-SGR-009 — fresh-DDL round-trip ===================================

def test_stock_prices_fresh_ddl_round_trip_ac009():
    cols = list(_STOCK_PRICES_COLS)
    conn = sqlite3.connect(":memory:")
    _create_fresh(conn, "stock_prices", cols)
    _batch_insert(conn, [_row_from(cols)])
    got = _read_back(conn, "stock_prices", cols)
    expected = _expected_from(cols)
    for c in cols:
        assert got[c] == expected[c], f"fresh-DDL round-trip shifted {c}"


def test_relative_strength_fresh_ddl_round_trip_ac009():
    cols = list(_RELATIVE_STRENGTH_COLS)
    conn = sqlite3.connect(":memory:")
    _create_fresh(conn, "relative_strength", cols)
    _batch_insert_rs(conn, [_row_from(cols)])
    conn.commit()
    got = _read_back(conn, "relative_strength", cols)
    expected = _expected_from(cols)
    for c in cols:
        assert got[c] == expected[c], f"fresh-DDL round-trip shifted {c}"


# --- empty-input no-op guards (Beyonce rule: pin the defensive branch) ---

def test_batch_insert_empty_rows_is_noop():
    cols = list(_STOCK_PRICES_COLS)
    conn = sqlite3.connect(":memory:")
    _create_fresh(conn, "stock_prices", cols)
    _batch_insert(conn, [])
    assert conn.execute("SELECT COUNT(*) FROM stock_prices").fetchone()[0] == 0


def test_batch_insert_rs_empty_rows_is_noop():
    cols = list(_RELATIVE_STRENGTH_COLS)
    conn = sqlite3.connect(":memory:")
    _create_fresh(conn, "relative_strength", cols)
    _batch_insert_rs(conn, [])
    assert conn.execute("SELECT COUNT(*) FROM relative_strength").fetchone()[0] == 0


# === AC-SGR-010 — legacy-ALTER round-trip [HARD, Lesson #8 gate] =========

@pytest.mark.parametrize("drop_col", ["SMA10", "RS_1M"])
def test_stock_prices_legacy_alter_column_name_safe_ac010(drop_col):
    """AC-SGR-010: column-name INSERT keeps every column correct even when a
    legacy ALTER appended `drop_col` at the physical end (order divergence)."""
    cols = list(_STOCK_PRICES_COLS)
    conn = sqlite3.connect(":memory:")
    _create_legacy_alter(conn, "stock_prices", cols, drop_col)
    _batch_insert(conn, [_row_from(cols)])
    got = _read_back(conn, "stock_prices", cols)
    expected = _expected_from(cols)
    for c in cols:
        assert got[c] == expected[c], (
            f"column-name INSERT shifted {c}: got {got[c]!r}, want {expected[c]!r}"
        )


def test_relative_strength_legacy_alter_column_name_safe_ac010():
    cols = list(_RELATIVE_STRENGTH_COLS)
    drop_col = "RS_3M_Rating"
    conn = sqlite3.connect(":memory:")
    _create_legacy_alter(conn, "relative_strength", cols, drop_col)
    _batch_insert_rs(conn, [_row_from(cols)])
    conn.commit()
    got = _read_back(conn, "relative_strength", cols)
    expected = _expected_from(cols)
    for c in cols:
        assert got[c] == expected[c], (
            f"column-name INSERT shifted {c}: got {got[c]!r}, want {expected[c]!r}"
        )


# --- AC-SGR-010 falsifiability: positional INSERT MUST shift on same fixture

@pytest.mark.parametrize("drop_col", ["SMA10", "RS_1M"])
def test_stock_prices_legacy_alter_positional_shifts_ac010(drop_col):
    """Falsifiability: the same legacy-ALTER fixture, run through the OLD
    positional insert, demonstrably shifts values. This proves the safe-path
    test above is not vacuous — the fixture genuinely exercises the defect."""
    cols = list(_STOCK_PRICES_COLS)
    conn = sqlite3.connect(":memory:")
    _create_legacy_alter(conn, "stock_prices", cols, drop_col)
    _positional_insert(conn, "stock_prices", cols, [_row_from(cols)])
    got = _read_back(conn, "stock_prices", cols)
    expected = _expected_from(cols)
    shifted = [c for c in cols if got[c] != expected[c]]
    assert shifted, (
        "positional insert produced NO shift on the legacy-ALTER fixture — "
        "the round-trip test would be vacuous (falsifiability broken)"
    )


def test_relative_strength_legacy_alter_positional_shifts_ac010():
    cols = list(_RELATIVE_STRENGTH_COLS)
    drop_col = "RS_3M_Rating"
    conn = sqlite3.connect(":memory:")
    _create_legacy_alter(conn, "relative_strength", cols, drop_col)
    _positional_insert(conn, "relative_strength", cols, [_row_from(cols)])
    got = _read_back(conn, "relative_strength", cols)
    expected = _expected_from(cols)
    shifted = [c for c in cols if got[c] != expected[c]]
    assert shifted, (
        "positional insert produced NO shift on the legacy-ALTER fixture — "
        "the round-trip test would be vacuous (falsifiability broken)"
    )


# === AC-SGR-011 — positional INSERT 재도입 금지 (static scan) =============

def test_no_positional_insert_literal_in_db_dir_ac011():
    """AC-SGR-011: no positional `INSERT ... VALUES (?, ...)` / `VALUES ({...})`
    literal remains in my_chart/db/. A regression here re-opens Lesson #8."""
    positional_pat = _POSITIONAL_INSERT_RE
    offenders = []
    for src in _DB_DIR.glob("*.py"):
        for lineno, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
            if positional_pat.search(line):
                offenders.append(f"{src.name}:{lineno}: {line.strip()}")
    assert not offenders, "positional INSERT reintroduced:\n" + "\n".join(offenders)


def test_weekly_column_name_insert_literals_present_ac011():
    """AC-SGR-011 And: weekly.py carries the column-name INSERT literals for
    both tables (the replacement form)."""
    text = (_DB_DIR / "weekly.py").read_text(encoding="utf-8")
    assert "INSERT OR REPLACE INTO stock_prices (" in text
    assert "INSERT OR REPLACE INTO relative_strength (" in text
