# -*- coding: utf-8 -*-
"""Stage 2 임계값 재보정 측정 (SPEC-RS-REBALANCE-001 REQ-RSR-018, AC-RSR-015).

--mode conditional : RS 외 진입 조건 다섯 개를 모두 통과한 종목 중
                     RS_12M_Rating >= threshold 인 비중 (진입 기준 _STAGE2_ENTRY_RS_MIN)
--mode strong      : Stage 2 종목 중 detail == "Stage 2 Strong" 인 비중
                     (강세 기준 _STAGE2_RS_STRONG, Strong 판정은 RS > threshold)

W = 기준 종목(REFERENCE_STOCK) 날짜 중 최근 --weeks 개. --ref-db 를 주면 두 사본에
모두 있는 날짜만 쓴다. 값은 날짜별 비중의 W 평균이다.

산식은 다시 만들지 않는다. stage_classifier 의 상수를 인자값으로 바꾼 뒤 프로덕션
함수(screen_stage2_entry, classify_all → _load_stocks_for_classification·classify_stage)를
그대로 호출한다. conditional 의 분모는 같은 screen_stage2_entry 를 RS 하한 -inf 로 불러
얻는다(조건 5만 무력화, 나머지 다섯 조건은 프로덕션 그대로).

사본은 읽기만 한다: stage_classifier 가 쓰는 sqlite3.connect 를 mode=ro&immutable=1 URI 로
여는 래퍼로 바꿔, -wal/-shm 사이드카도 만들지 않는다.
"""
import argparse
import sqlite3
import sys
from pathlib import Path

# -I 로 실행해도 이 저장소의 my_chart 를 잡도록 저장소 루트를 직접 넣는다.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from my_chart.analysis import stage_classifier as sc  # noqa: E402
from my_chart.config import REFERENCE_STOCK  # noqa: E402


def _ro_connect(path, *args, **kwargs):
    """읽기 전용·immutable 연결 (stage_classifier 내부 connect 대체용)."""
    return sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro&immutable=1",
                           *args, uri=True, **kwargs)


class _ReadOnlySqlite:
    connect = staticmethod(_ro_connect)


def _reference_dates(db: str) -> set[str]:
    conn = _ro_connect(db)
    try:
        rows = conn.execute("SELECT DISTINCT Date FROM stock_prices WHERE Name = ?",
                            (REFERENCE_STOCK,)).fetchall()
    finally:
        conn.close()
    return {r[0] for r in rows}


def _share_conditional(db: str, date: str, threshold: float) -> tuple[int, int]:
    sc._STAGE2_ENTRY_RS_MIN = float("-inf")
    denom = len(sc.screen_stage2_entry(db, date))
    sc._STAGE2_ENTRY_RS_MIN = threshold
    num = len(sc.screen_stage2_entry(db, date))
    return denom, num


def _share_strong(db: str, date: str, threshold: float) -> tuple[int, int]:
    sc._STAGE2_RS_STRONG = threshold
    stage2 = [r for r in sc.classify_all(db, date) if r.stage == 2]
    return len(stage2), sum(1 for r in stage2 if r.detail == "Stage 2 Strong")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", required=True, help="주간 DB 사본 경로 (읽기 전용으로 연다)")
    ap.add_argument("--weeks", type=int, default=12, help="W 크기 (기본 12)")
    ap.add_argument("--mode", required=True, choices=["conditional", "strong"])
    ap.add_argument("--threshold", type=float, required=True)
    ap.add_argument("--ref-db", default=None, help="W 를 두 사본 공통 날짜로 제한할 다른 사본")
    args = ap.parse_args(argv)

    sc.sqlite3 = _ReadOnlySqlite  # 프로덕션 함수가 사본을 읽기 전용으로 열게 한다

    dates = _reference_dates(args.db)
    if args.ref_db:
        dates &= _reference_dates(args.ref_db)
    window = sorted(dates)[-args.weeks:]

    measure = _share_conditional if args.mode == "conditional" else _share_strong
    print(f"db={args.db} mode={args.mode} threshold={args.threshold:g} weeks={args.weeks}"
          + (f" ref_db={args.ref_db}" if args.ref_db else ""))
    print(f"W={','.join(window)} (n={len(window)})")

    shares = []
    for d in window:
        denom, num = measure(args.db, d, args.threshold)
        share = 100.0 * num / denom if denom else float("nan")
        if denom:
            shares.append(share)
        print(f"date={d} denom={denom} num={num} share={share:.2f}")
    mean = sum(shares) / len(shares) if shares else float("nan")
    print(f"mean={mean:.2f} n_dates={len(shares)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
