"""SPEC-CHART-SEARCH-001 T1 RED — GET /api/stocks/master 엔드포인트 테스트.

커버리지:
- AC-DATA-001 (must-pass): 정상 200 + stocks + ETag + Cache-Control + name NULL 제외 + name ascending
- AC-DATA-002 (must-pass): 빈 stock_meta → 503 stock_meta_not_ready
- AC-DATA-003 (must-pass): stock_meta 테이블 부재 → 503 stock_meta_not_ready
- AC-DATA-004 (must-pass): SELECT-only invariant — mode=ro URI

격리 방식:
- 임시 SQLite DB (tmp_path)
- DAILY_DB_PATH를 monkeypatch로 교체
"""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """임시 SQLite DB 경로를 반환한다. 테이블은 각 테스트에서 생성."""
    return tmp_path / "test_daily.db"


@pytest.fixture()
def client_with_db(tmp_db: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """DAILY_DB_PATH가 tmp_db를 가리키는 TestClient.

    stocks.py는 DAILY_DB_PATH를 모듈 수준에서 import하므로,
    라우터 모듈 자체의 네임스페이스도 함께 패치해야 한다.
    """
    import backend.deps as deps_mod
    monkeypatch.setattr(deps_mod, "DAILY_DB_PATH", str(tmp_db))

    import backend.routers.stocks as stocks_router_mod
    monkeypatch.setattr(stocks_router_mod, "DAILY_DB_PATH", str(tmp_db))

    from backend.main import app
    return TestClient(app)


def _setup_db(db_path: Path) -> None:
    """정상 stock_meta 테이블 + 3개 row (name NULL 1개 포함)."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT,
            market TEXT,
            last_updated TEXT
        )"""
    )
    cur.executemany(
        "INSERT INTO stock_meta VALUES (?, ?, ?, ?)",
        [
            ("005930", "삼성전자", "KOSPI", "2026-05-10T18:00"),
            ("000660", "SK하이닉스", "KOSPI", "2026-05-10T18:00"),
            ("035720", None, "KOSPI", "2026-05-10T18:00"),
        ],
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# AC-DATA-001 — 정상 200 + 정렬 + ETag + Cache-Control
# ---------------------------------------------------------------------------

def test_stocks_master_200_with_etag_and_cache_control(
    tmp_db: Path, client_with_db: TestClient
) -> None:
    """정상 응답 200, stocks 2개, ETag, Cache-Control 검증."""
    _setup_db(tmp_db)

    resp = client_with_db.get("/api/stocks/master")
    assert resp.status_code == 200

    body = resp.json()
    assert "stocks" in body
    assert "generated_at" in body

    # name NULL row 제외 → 2개
    stocks = body["stocks"]
    assert len(stocks) == 2

    # ETag 헤더 존재
    assert "etag" in resp.headers or "ETag" in resp.headers

    # Cache-Control: max-age=300
    cc = resp.headers.get("cache-control") or resp.headers.get("Cache-Control", "")
    assert "max-age=300" in cc


def test_stocks_master_name_ascending_sort(
    tmp_db: Path, client_with_db: TestClient
) -> None:
    """stocks 배열이 name 오름차순 정렬됨 (SK하이닉스 < 삼성전자)."""
    _setup_db(tmp_db)

    resp = client_with_db.get("/api/stocks/master")
    assert resp.status_code == 200

    names = [s["name"] for s in resp.json()["stocks"]]
    # SQLite BINARY 정렬: 'S' < 'ㅅ' (ASCII 우선)
    assert names == sorted(names)


def test_stocks_master_etag_from_max_last_updated(
    tmp_db: Path, client_with_db: TestClient
) -> None:
    """ETag 값이 MAX(last_updated)을 포함."""
    _setup_db(tmp_db)

    resp = client_with_db.get("/api/stocks/master")
    etag = resp.headers.get("etag") or resp.headers.get("ETag", "")
    assert "2026-05-10T18:00" in etag


# ---------------------------------------------------------------------------
# AC-DATA-002 — 빈 stock_meta → 503
# ---------------------------------------------------------------------------

def test_stocks_master_empty_table_503(
    tmp_db: Path, client_with_db: TestClient
) -> None:
    """stock_meta 테이블이 존재하나 row 0건 → 503."""
    conn = sqlite3.connect(str(tmp_db))
    conn.execute(
        """CREATE TABLE stock_meta (
            code TEXT, name TEXT, market TEXT, last_updated TEXT
        )"""
    )
    conn.commit()
    conn.close()

    resp = client_with_db.get("/api/stocks/master")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "stock_meta_not_ready"


def test_stocks_master_all_null_names_503(
    tmp_db: Path, client_with_db: TestClient
) -> None:
    """name이 모두 NULL인 경우 → 503 (edge case)."""
    conn = sqlite3.connect(str(tmp_db))
    conn.execute(
        """CREATE TABLE stock_meta (
            code TEXT, name TEXT, market TEXT, last_updated TEXT
        )"""
    )
    conn.execute("INSERT INTO stock_meta VALUES ('035720', NULL, 'KOSPI', '2026-05-10T18:00')")
    conn.commit()
    conn.close()

    resp = client_with_db.get("/api/stocks/master")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# AC-DATA-003 — stock_meta 테이블 부재 → 503
# ---------------------------------------------------------------------------

def test_stocks_master_no_table_503(
    tmp_db: Path, client_with_db: TestClient
) -> None:
    """stock_meta 테이블 자체 없음 → 503, bare except 없이 처리."""
    # DB 파일은 생성하되 stock_meta 테이블은 없음
    conn = sqlite3.connect(str(tmp_db))
    conn.execute("CREATE TABLE other_table (id INTEGER)")
    conn.commit()
    conn.close()

    resp = client_with_db.get("/api/stocks/master")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "stock_meta_not_ready"


# ---------------------------------------------------------------------------
# AC-DATA-004 — SELECT-only invariant
# ---------------------------------------------------------------------------

def test_stocks_master_service_uses_mode_ro(tmp_db: Path) -> None:
    """stocks_master_service.py가 mode=ro URI를 사용하는지 정적 확인."""
    import inspect
    import backend.services.stocks_master_service as svc

    src = inspect.getsource(svc)
    assert "mode=ro" in src, "mode=ro URI가 서비스 코드에 없음"
    assert "uri=True" in src, "uri=True 파라미터가 서비스 코드에 없음"


def test_stocks_master_service_readonly_rejects_write(tmp_db: Path) -> None:
    """mode=ro 연결에서 INSERT 시도 → OperationalError (write 차단 검증)."""
    _setup_db(tmp_db)

    from backend.services.stocks_master_service import list_stock_master

    # 정상 read는 성공
    stocks, _max_upd = list_stock_master(str(tmp_db))
    assert len(stocks) == 2

    # mode=ro 연결로 INSERT 시도
    conn = sqlite3.connect(f"file:{tmp_db}?mode=ro", uri=True)
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("INSERT INTO stock_meta VALUES ('999999', 'Test', 'KOSPI', '2026-05-10')")
    conn.close()
