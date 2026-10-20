"""SPEC-RS-REBALANCE-001 AC-RSR-015 (도구 측) — `stage2_ratio_eval.py`.

`--mode conditional`: RS 외 진입 조건 다섯 개를 통과한 종목 중 `RS_12M_Rating >= t` 비중.
`--mode strong`: Stage 2 종목 중 `detail == "Stage 2 Strong"`(RS > t) 비중.
W = 기준 종목(`삼성전자`) 날짜 중 최근 N개. `--ref-db`가 있으면 두 사본에 모두 있는 날짜만.

기대값은 픽스처에 심은 행에서 손으로 센 상수이며 프로덕션 함수에서 끌어오지 않는다.
스크립트는 계획서 §G처럼 `-I`로 실행한다(스크립트가 저장소 루트를 직접 sys.path에 넣어야 함).
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

from tests.rsr_fixtures import make_weekly_db, price_row

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "rs_eval" / "stage2_ratio_eval.py"
_PYTHON = "/Users/byunjungwon/Dev/my_chart/.venv/bin/python"
_REF = "삼성전자"

# 기본 price_row: Close 105 > SMA10 100 > SMA40 97, SMA40_Trend_4M 1.0 → Stage 2 (엄격 분기).
# 거래량 1e6 / VolumeSMA10 9e5 = 1.11 < 1.5 → 진입 조건 4(거래량 배수) 탈락이 기본값이다.
_SURGE = {"Volume": 2_000_000.0}  # 2e6 / 9e5 = 2.22 ≥ 1.5
_EARLY = {"SMA10": 110.0}  # Close 105 < SMA10 110, > SMA40 97 → 기본 분기 "Stage 2 Early"
_DECLINE = {"Close": 90.0, "SMA40_Trend_4M": -0.02}  # Close < SMA10·SMA40, slope < -1% → Stage 4


def _run(db: str, mode: str, threshold: float, weeks: int, ref_db: str | None = None):
    cmd = [_PYTHON, "-I", str(_SCRIPT), "--db", db, "--weeks", str(weeks),
           "--mode", mode, "--threshold", str(threshold)]
    if ref_db:
        cmd += ["--ref-db", ref_db]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def _mean(out: str) -> float:
    m = re.search(r"^mean=([0-9.]+) n_dates=(\d+)$", out, re.M)
    assert m, out
    return float(m.group(1))


def _w(out: str) -> list[str]:
    m = re.search(r"^W=(\S+) \(n=\d+\)$", out, re.M)
    assert m, out
    return m.group(1).split(",")


def _dates(out: str) -> dict[str, tuple[int, int]]:
    return {d: (int(n), int(k)) for d, n, k in
            re.findall(r"^date=(\S+) denom=(\d+) num=(\d+) share=", out, re.M)}


def _conditional_db(tmp_path: Path) -> str:
    """두 날짜. 비RS 조건 통과 P1~P5(P5는 등급 행 없음), 탈락 D1~D3, 지수 1개."""
    rows, rs = [], []
    plan = {
        "2026-01-02": {"P1": 65.0, "P2": 75.0, "P3": 85.0, "P4": 95.0},
        "2026-01-09": {"P1": 55.0, "P2": 65.0, "P3": 75.0, "P4": 85.0},
    }
    for d, ratings in plan.items():
        rows.append(price_row(_REF, d))  # 거래량 기본값 → 조건 4 탈락(분모 밖)
        rs.append((_REF, d, 99.0, None, None, None))
        for name, r in ratings.items():
            rows.append(price_row(name, d, **_SURGE))
            rs.append((name, d, r, None, None, None))
        rows.append(price_row("P5", d, **_SURGE))  # 등급 행 없음 → RS 0 취급, 분모에는 들어감
        rows.append(price_row("D1", d))  # 조건 4 탈락
        rows.append(price_row("D2", d, CHG_1M=-0.01, **_SURGE))  # 조건 6 탈락
        rows.append(price_row("D3", d, **_EARLY, **_SURGE))  # Stage 2 Early이나 조건 2 탈락
        rows.append(price_row("KOSPI", d, **_SURGE))  # 지수 행 — 로더가 제외
        for name in ("D1", "D2", "D3", "KOSPI"):
            rs.append((name, d, 99.0, None, None, None))
    (tmp_path / "c").mkdir()
    return make_weekly_db(tmp_path / "c", rows, rs) + ".db"


def test_conditional_counts_only_five_non_rs_conditions_in_denominator(tmp_path):
    db = _conditional_db(tmp_path)
    res = _run(db, "conditional", 70, weeks=12)
    assert res.returncode == 0, res.stderr
    # 날짜별 분모 5(P1~P5). 70 통과: 1/2일 P2·P3·P4 = 3, 1/9일 P3·P4 = 2.
    assert _dates(res.stdout) == {"2026-01-02": (5, 3), "2026-01-09": (5, 2)}
    assert _mean(res.stdout) == 50.0  # (60 + 40) / 2


def test_conditional_threshold_argument_moves_the_rs_cut(tmp_path):
    db = _conditional_db(tmp_path)
    assert _mean(_run(db, "conditional", 60, weeks=12).stdout) == 70.0  # (80 + 60) / 2
    assert _mean(_run(db, "conditional", 80, weeks=12).stdout) == 30.0  # (40 + 20) / 2


def _strong_db(tmp_path: Path) -> str:
    """한 날짜. Stage 2 엄격 분기 S1~S4, Stage 2 Early E1, Stage 4 X1, 지수, 기준 종목(Stage 4)."""
    d = "2026-01-02"
    rows = [price_row(_REF, d, **_DECLINE)]
    rs = [(_REF, d, 99.0, None, None, None)]
    for name, r in {"S1": 50.0, "S2": 65.0, "S3": 75.0, "S4": 60.0}.items():
        rows.append(price_row(name, d))
        rs.append((name, d, r, None, None, None))
    rows += [price_row("E1", d, **_EARLY), price_row("X1", d, **_DECLINE), price_row("KOSDAQ", d)]
    rs += [(n, d, 99.0, None, None, None) for n in ("E1", "X1", "KOSDAQ")]
    (tmp_path / "s").mkdir()
    return make_weekly_db(tmp_path / "s", rows, rs) + ".db"


def test_strong_share_among_all_stage2_including_early(tmp_path):
    db = _strong_db(tmp_path)
    res = _run(db, "strong", 60, weeks=12)
    assert res.returncode == 0, res.stderr
    # 분모 = S1~S4 + E1 = 5. Strong은 RS > 60: S2·S3 = 2 (S4의 60은 경계 미포함).
    assert _dates(res.stdout) == {"2026-01-02": (5, 2)}
    assert _mean(res.stdout) == 40.0


def test_strong_threshold_argument_replaces_the_strong_constant(tmp_path):
    db = _strong_db(tmp_path)
    assert _mean(_run(db, "strong", 70, weeks=12).stdout) == 20.0  # S3 하나 / 5


def _ref_dates_db(tmp_path: Path, sub: str, dates: list[str]) -> str:
    rows, rs = [], []
    for d in dates:
        rows += [price_row(_REF, d), price_row("P1", d, **_SURGE)]
        rs += [(_REF, d, 99.0, None, None, None), ("P1", d, 75.0, None, None, None)]
    (tmp_path / sub).mkdir()
    return make_weekly_db(tmp_path / sub, rows, rs) + ".db"


def test_w_is_latest_n_reference_dates_present_in_both_copies(tmp_path):
    a = _ref_dates_db(tmp_path, "a", ["2026-01-02", "2026-01-09", "2026-01-16", "2026-01-23"])
    b = _ref_dates_db(tmp_path, "b", ["2026-01-02", "2026-01-09", "2026-01-16"])
    alone = _run(a, "conditional", 70, weeks=2)
    paired = _run(a, "conditional", 70, weeks=2, ref_db=b)
    assert _w(alone.stdout) == ["2026-01-16", "2026-01-23"]
    assert _w(paired.stdout) == ["2026-01-09", "2026-01-16"]
    assert sorted(_dates(paired.stdout)) == ["2026-01-09", "2026-01-16"]


def test_snapshot_is_opened_read_only(tmp_path):
    db = _conditional_db(tmp_path)
    before = hashlib.sha256(Path(db).read_bytes()).hexdigest()
    listing = sorted(p.name for p in Path(db).parent.iterdir())
    assert _run(db, "strong", 60, weeks=12).returncode == 0
    assert hashlib.sha256(Path(db).read_bytes()).hexdigest() == before
    assert sorted(p.name for p in Path(db).parent.iterdir()) == listing
