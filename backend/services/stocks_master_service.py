"""주식 마스터 서비스: stock_meta 테이블에서 종목 목록 조회.

# @MX:ANCHOR: [AUTO] list_stock_master — public API for stock master data
# @MX:REASON: 모달 검색 진입점. mode=ro SQLite URI invariant. fan_in >= 2 예상 (router + tests).
"""

from __future__ import annotations

import sqlite3
from zoneinfo import ZoneInfo

_KST = ZoneInfo("Asia/Seoul")


def list_stock_master(daily_db_path: str) -> tuple[list[dict[str, str]], str | None]:
    """stock_meta에서 종목 목록과 최대 last_updated를 반환한다.

    Returns:
        (stocks, max_last_updated_iso) — stocks가 빈 리스트이면 라우터가 503 처리.
        max_last_updated_iso는 ETag 생성에 사용; 데이터 없으면 None.

    # @MX:NOTE: [AUTO] mode=ro URI로 SELECT-only 강제 (REQ-DATA-002, NFR-CONST-002)
    """
    conn = sqlite3.connect(f"file:{daily_db_path}?mode=ro", uri=True)
    try:
        cur = conn.cursor()

        # stock_meta 테이블 존재 여부 확인
        try:
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='stock_meta'"
            )
        except sqlite3.OperationalError:
            return [], None

        if cur.fetchone() is None:
            return [], None

        # 종목 목록 조회 (name IS NOT NULL + name ascending)
        try:
            cur.execute(
                "SELECT code, name, market FROM stock_meta"
                " WHERE name IS NOT NULL"
                " ORDER BY name"
            )
        except sqlite3.OperationalError:
            return [], None

        rows = cur.fetchall()
        if not rows:
            return [], None

        stocks = [{"code": r[0], "name": r[1], "market": r[2]} for r in rows]

        # ETag용 MAX(last_updated) 조회
        max_updated: str | None = None
        try:
            cur.execute("SELECT MAX(last_updated) FROM stock_meta")
            row = cur.fetchone()
            if row and row[0]:
                max_updated = row[0]
        except sqlite3.OperationalError:
            pass

        return stocks, max_updated

    finally:
        conn.close()
