"""SPEC-RS-REBALANCE-001 AC-RSR-014 (도구 측) — `stock_rs_eval.py --production --db <경로>`.

프로덕션 모드는 점수를 `relative_strength.RS_12M_Rating`에서만 읽고(원시 수익률로
산식을 다시 계산하지 않음), 유니버스 규칙은 기존 그대로 쓴다(REQ-RSR-020).

픽스처 설계: 210종목 × 64주. `RS_12M_Rating`은 종목마다 날짜와 무관한 고정값이라
상위 10% 집합이 매주 같다 → 프로덕션 모드의 4주 지속률은 정확히 100.0이어야 한다.
원시 수익률(`RS_1M`~`RS_12M`)은 매주 무작위라, 점수를 원시 컬럼에서 다시 계산하는
구현은 지속률이 100에 못 미친다(대조). 기대값 100.0은 픽스처 구조에서 손으로 정한
상수이며 스크립트에서 끌어오지 않는다.
"""

from __future__ import annotations

import sqlite3
import subprocess
from datetime import date, timedelta
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "rs_eval" / "stock_rs_eval.py"
_PYTHON = "/Users/byunjungwon/Dev/my_chart/.venv/bin/python"

_N_STOCKS = 210  # 날짜당 200종목 이상 규칙(:74)을 넘기는 수
_N_WEEKS = 64  # dates[52:-4] = 8개 날짜 → 지속률 표본 4개


def _make_eval_db(tmp_path: Path) -> Path:
    rng = np.random.default_rng(20261020)
    first = date(2025, 1, 3)  # 금요일 — 주마다 ISO 주차가 하나씩
    dates = [(first + timedelta(weeks=w)).isoformat() for w in range(_N_WEEKS)]
    names = [f"T{i:03d}" for i in range(_N_STOCKS)]

    prices, ratings = [], []
    for d in dates:
        raw = rng.uniform(-0.5, 1.5, size=(_N_STOCKS, 5))
        for i, name in enumerate(names):
            # Close·Volume 고정 → 주간거래대금 1e10 ≥ 5e9 (tv20 규칙 :99 통과)
            prices.append((name, d, 10_000.0, 1_000_000.0, *map(float, raw[i])))
            ratings.append((name, d, float(i)))  # 날짜 무관 고정 등급

    db = tmp_path / "eval_weekly.db"
    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "CREATE TABLE stock_prices (Name TEXT, Date TEXT, Close REAL, Volume REAL, "
            "RS_1M REAL, RS_3M REAL, RS_6M REAL, RS_9M REAL, RS_12M REAL)"
        )
        conn.executemany("INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?)", prices)
        conn.execute(
            "CREATE TABLE relative_strength (Name TEXT, Date TEXT, RS_12M_Rating REAL, "
            "RS_6M_Rating REAL, RS_3M_Rating REAL, RS_1M_Rating REAL, "
            "PRIMARY KEY (Name, Date))"
        )
        conn.executemany(
            "INSERT INTO relative_strength (Name, Date, RS_12M_Rating) VALUES (?,?,?)",
            ratings,
        )
        conn.commit()
    finally:
        conn.close()
    return db


def _run(*args: str) -> str:
    proc = subprocess.run(
        [_PYTHON, "-I", str(_SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout


def _persistence(stdout: str, label: str) -> float:
    """출력 표에서 `label` 행의 마지막 열(상위10_지속률)을 읽는다."""
    for line in stdout.splitlines():
        if line.split() and line.split()[0] == label:
            return float(line.split()[-1])
    raise AssertionError(f"row {label!r} not found in output:\n{stdout}")


def test_ac_rsr_014_production_mode_reads_rs_12m_rating_only(tmp_path):
    db = _make_eval_db(tmp_path)

    out = _run("--production", "--db", str(db), "4")

    assert "상위10_지속률" in out
    # 고정 등급 → 상위 10% 집합이 매주 같다 → 지속률 100.0
    assert _persistence(out, "프로덕션(RS_12M_Rating)") == 100.0
    # 프로덕션 모드는 원시 컬럼 기반 후보 산식을 돌리지 않는다
    assert "IBD식(최근분기 40%)" not in out


def test_ac_rsr_014_db_flag_without_production_keeps_raw_formula_mode(tmp_path):
    db = _make_eval_db(tmp_path)

    out = _run("--db", str(db), "4")

    # 기존 모드: 원시 컬럼에서 후보 산식을 다시 계산한다(프로덕션 행 없음).
    assert "프로덕션(RS_12M_Rating)" not in out
    # 원시 수익률이 매주 무작위라 원시 IBD식의 지속률은 100에 한참 못 미친다 —
    # 프로덕션 모드의 100.0이 원시 재계산으로는 나올 수 없음을 같은 픽스처로 보인다.
    assert _persistence(out, "IBD식(최근분기") < 50.0
