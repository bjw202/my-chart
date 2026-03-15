"""RED: Tests for R3 - GET /api/sectors/{name}/detail endpoint and service."""

from __future__ import annotations

import sqlite3

import pytest

from backend.schemas.sector import SectorDetailResponse


# ---------------------------------------------------------------------------
# Tests: SectorDetailResponse schema
# ---------------------------------------------------------------------------


class TestSectorDetailResponseSchema:
    def test_schema_has_sub_sectors_field(self):
        response = SectorDetailResponse(
            sector_name="전기전자",
            sub_sectors=[],
            top_stocks=[],
        )
        assert response.sub_sectors == []

    def test_schema_has_top_stocks_field(self):
        response = SectorDetailResponse(
            sector_name="전기전자",
            sub_sectors=[],
            top_stocks=[],
        )
        assert response.top_stocks == []

    def test_sub_sector_item_has_required_fields(self):
        from backend.schemas.sector import SubSectorItem
        item = SubSectorItem(
            name="반도체",
            stock_count=10,
            stage1_count=2,
            stage2_count=5,
            stage3_count=2,
            stage4_count=1,
        )
        assert item.name == "반도체"
        assert item.stock_count == 10
        assert item.stage2_count == 5

    def test_top_stock_item_has_required_fields(self):
        from backend.schemas.sector import TopStockItem
        item = TopStockItem(
            code="005930",
            name="삼성전자",
            rs_12m=85.0,
            stage=2,
        )
        assert item.code == "005930"
        assert item.rs_12m == 85.0
        assert item.stage == 2


# ---------------------------------------------------------------------------
# Helpers: in-memory DB setup
# ---------------------------------------------------------------------------


def _make_stock_meta_db(stocks: list[dict]) -> sqlite3.Connection:
    """Create an in-memory SQLite DB with stock_meta rows for testing."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.execute(
        """CREATE TABLE stock_meta (
            code TEXT PRIMARY KEY,
            name TEXT,
            market TEXT,
            market_cap INTEGER,
            sector_major TEXT,
            sector_minor TEXT,
            product TEXT,
            close REAL,
            change_1d REAL,
            ema10 REAL,
            ema20 REAL,
            sma50 REAL,
            sma100 REAL,
            sma200 REAL,
            high52w REAL,
            chg_1w REAL,
            chg_1m REAL,
            chg_3m REAL,
            rs_12m REAL,
            sma10_w REAL,
            sma20_w REAL,
            sma40_w REAL,
            last_updated TEXT
        )"""
    )
    for s in stocks:
        conn.execute(
            """INSERT INTO stock_meta
               (code, name, market, market_cap, sector_major, sector_minor, rs_12m, last_updated)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                s["code"], s["name"], s.get("market", "KOSPI"),
                s.get("market_cap", 100000),
                s.get("sector_major", "전기전자"),
                s.get("sector_minor", "반도체"),
                s.get("rs_12m", 50.0),
                "2026-03-15",
            ),
        )
    conn.commit()
    return conn


_SAMPLE_STOCKS = [
    {"code": "005930", "name": "삼성전자", "sector_major": "전기전자", "sector_minor": "반도체", "rs_12m": 85.0},
    {"code": "000660", "name": "SK하이닉스", "sector_major": "전기전자", "sector_minor": "반도체", "rs_12m": 72.0},
    {"code": "009150", "name": "삼성전기", "sector_major": "전기전자", "sector_minor": "전자부품", "rs_12m": 60.0},
    {"code": "006400", "name": "삼성SDI", "sector_major": "전기전자", "sector_minor": "디스플레이", "rs_12m": 55.0},
    {"code": "005490", "name": "POSCO홀딩스", "sector_major": "철강금속", "sector_minor": "철강", "rs_12m": 60.0},
]


# ---------------------------------------------------------------------------
# Tests: get_sector_detail service
# ---------------------------------------------------------------------------


class TestGetSectorDetail:
    def setup_method(self):
        self.conn = _make_stock_meta_db(_SAMPLE_STOCKS)
        import backend.services.sector_detail_service as svc
        self._svc = svc
        self._orig_connect = svc._connect
        svc._connect = lambda _path: self.conn

    def teardown_method(self):
        self._svc._connect = self._orig_connect
        self.conn.close()

    def test_returns_sector_detail_response(self):
        from backend.services.sector_detail_service import get_sector_detail
        result = get_sector_detail(":memory:", "전기전자")
        assert result.sector_name == "전기전자"

    def test_sub_sectors_grouped_by_sector_minor(self):
        from backend.services.sector_detail_service import get_sector_detail
        result = get_sector_detail(":memory:", "전기전자")
        sub_names = {s.name for s in result.sub_sectors}
        assert "반도체" in sub_names
        assert "전자부품" in sub_names
        assert "디스플레이" in sub_names

    def test_sub_sector_stock_count_correct(self):
        from backend.services.sector_detail_service import get_sector_detail
        result = get_sector_detail(":memory:", "전기전자")
        semi = next(s for s in result.sub_sectors if s.name == "반도체")
        assert semi.stock_count == 2  # 삼성전자, SK하이닉스

    def test_top_stocks_limited_to_five(self):
        from backend.services.sector_detail_service import get_sector_detail
        result = get_sector_detail(":memory:", "전기전자")
        assert len(result.top_stocks) <= 5

    def test_top_stocks_sorted_by_rs_descending(self):
        from backend.services.sector_detail_service import get_sector_detail
        result = get_sector_detail(":memory:", "전기전자")
        rs_values = [s.rs_12m for s in result.top_stocks]
        assert rs_values == sorted(rs_values, reverse=True)

    def test_only_returns_stocks_from_given_sector(self):
        from backend.services.sector_detail_service import get_sector_detail
        result = get_sector_detail(":memory:", "전기전자")
        # POSCO (철강금속) should not appear
        for s in result.sub_sectors:
            assert s.name != "철강"
        for s in result.top_stocks:
            assert s.code != "005490"

    def test_empty_sector_returns_empty_lists(self):
        from backend.services.sector_detail_service import get_sector_detail
        result = get_sector_detail(":memory:", "존재하지않는섹터")
        assert result.sub_sectors == []
        assert result.top_stocks == []

    def test_top_stock_has_code_and_name(self):
        from backend.services.sector_detail_service import get_sector_detail
        result = get_sector_detail(":memory:", "전기전자")
        assert len(result.top_stocks) > 0
        top = result.top_stocks[0]
        assert top.code == "005930"  # highest RS
        assert top.name == "삼성전자"
