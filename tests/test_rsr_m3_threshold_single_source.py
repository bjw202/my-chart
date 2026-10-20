"""SPEC-RS-REBALANCE-001 AC-RSR-013 (백엔드 측) — T8은 `_STAGE2_ENTRY_RS_MIN`을 따른다.

REQ-RSR-019 / spec.md §2.4 D13: Minervini T8(`screen_service._build_minervini_where()`)은
Stage 2 진입 RS 하한을 리터럴이 아니라 공유 상수 `stage_classifier._STAGE2_ENTRY_RS_MIN`
에서 읽는다. 단언은 프로덕션 WHERE 절을 실제 SQLite에 돌린 결과(한 변)와 픽스처에 심은
`rs_12m = 75`(다른 변)를 비교한다. 상수를 80으로 바꾸면 75는 탈락해야 한다 — T8이
리터럴 70으로 남아 있으면 여전히 통과하므로 RED.
"""

from __future__ import annotations

import sqlite3

from backend.services.screen_service import _build_minervini_where
from my_chart.analysis import stage_classifier

# T1~T7을 모두 통과하는 값(test_minervini_template.py S9와 같은 모양) + rs_12m 75.
_ROW = {
    "code": "T8", "close": 100.0, "sma150": 80.0, "sma200": 70.0, "sma200_20d_ago": 60.0,
    "sma50": 90.0, "low52w": 50.0, "high52w": 110.0, "rs_12m": 75.0,
}


def _passes_minervini() -> bool:
    conn = sqlite3.connect(":memory:")
    try:
        cols = ", ".join(f"{k} {'TEXT' if k == 'code' else 'REAL'}" for k in _ROW)
        conn.execute(f"CREATE TABLE stock_meta ({cols})")
        conn.execute(f"INSERT INTO stock_meta VALUES ({', '.join('?' * len(_ROW))})",
                     tuple(_ROW.values()))
        sql = f"SELECT code FROM stock_meta WHERE {_build_minervini_where()}"
        return [r[0] for r in conn.execute(sql)] == ["T8"]
    finally:
        conn.close()


def test_t8_admits_rs_75_under_current_entry_minimum():
    assert _passes_minervini()


def test_t8_follows_shared_stage2_entry_constant(monkeypatch):
    monkeypatch.setattr(stage_classifier, "_STAGE2_ENTRY_RS_MIN", 80.0)
    assert not _passes_minervini()
