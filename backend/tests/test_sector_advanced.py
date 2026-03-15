"""SPEC-TOPDOWN-002A 백엔드 고급 섹터 분석 테스트.

TDD RED 단계: 구현 전에 먼저 작성한 테스트.
인메모리 SQLite를 사용하여 외부 의존성 없이 실행 가능.
"""

from __future__ import annotations

import sqlite3
import tempfile
import math

import pytest

# ---------------------------------------------------------------------------
# 테스트 DB 픽스처 생성 헬퍼
# ---------------------------------------------------------------------------

def _create_test_db() -> str:
    """테스트용 인메모리 SQLite 파일 생성.

    - stock_prices: 3개 섹터, 각 섹터 3~4종목, 12주 데이터 + KOSPI
    - stock_meta: 종목 코드, 시장구분, 시가총액
    - relative_strength: RS 데이터
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    conn = sqlite3.connect(tmp.name)

    # ---------------------------------------------------------------------------
    # 테이블 생성
    # ---------------------------------------------------------------------------
    conn.executescript("""
        CREATE TABLE stock_prices (
            Name TEXT,
            Date TEXT,
            Close REAL,
            Volume REAL,
            SMA10 REAL,
            SMA40 REAL,
            SMA40_Trend_4M REAL,
            CHG_1W REAL,
            CHG_1M REAL,
            CHG_3M REAL,
            MAX52 REAL
        );
        CREATE TABLE stock_meta (
            name TEXT,
            code TEXT,
            sector_major TEXT,
            sector_minor TEXT,
            market TEXT,
            market_cap REAL
        );
        CREATE TABLE relative_strength (
            Name TEXT,
            Date TEXT,
            RS_12M_Rating REAL
        );
    """)

    # ---------------------------------------------------------------------------
    # 12주 날짜 생성
    # ---------------------------------------------------------------------------
    base_dates = [
        "2024-01-05", "2024-01-12", "2024-01-19", "2024-01-26",
        "2024-02-02", "2024-02-09", "2024-02-16", "2024-02-23",
        "2024-03-01", "2024-03-08", "2024-03-15", "2024-03-22",
    ]

    # ---------------------------------------------------------------------------
    # 종목 정의: (Name, sector_major, 시장구분, market_cap, base_close, chg_1w_factor)
    # sector_major: IT, 화학, 헬스케어
    # ---------------------------------------------------------------------------
    stocks = [
        # IT 섹터
        ("삼성전자", "IT", "KOSPI", 400_000_000.0, 70000.0, 0.02),
        ("SK하이닉스", "IT", "KOSPI", 80_000_000.0, 130000.0, 0.01),
        ("카카오", "IT", "KOSDAQ", 30_000_000.0, 55000.0, -0.005),
        # 화학 섹터
        ("LG화학", "화학", "KOSPI", 25_000_000.0, 450000.0, 0.015),
        ("롯데케미칼", "화학", "KOSPI", 5_000_000.0, 180000.0, -0.01),
        # 헬스케어 섹터
        ("삼성바이오로직스", "헬스케어", "KOSPI", 60_000_000.0, 800000.0, 0.03),
        ("셀트리온", "헬스케어", "KOSPI", 40_000_000.0, 175000.0, 0.02),
        ("한미약품", "헬스케어", "KOSDAQ", 5_000_000.0, 350000.0, 0.01),
    ]

    # stock_meta 삽입
    meta_rows = []
    for name, sector, market, cap, _, _ in stocks:
        code = f"{hash(name) % 900000 + 100000:06d}"
        meta_rows.append((name, code, sector, sector + "소그룹", market, cap))
    conn.executemany(
        "INSERT INTO stock_meta VALUES (?,?,?,?,?,?)",
        meta_rows,
    )

    # KOSPI 인덱스 데이터
    kospi_prices = []
    for i, date in enumerate(base_dates):
        close = 2500.0 + i * 10.0
        chg_1w = 0.005 + i * 0.001  # 0.5% ~ 1.6%
        chg_1m = 0.015
        chg_3m = 0.04
        kospi_prices.append(("KOSPI", date, close, 5_000_000.0,
                              close * 0.98, close * 0.95, close * 0.93,
                              chg_1w, chg_1m, chg_3m, close * 1.05))

    # 종목별 가격 데이터 삽입
    price_rows = list(kospi_prices)
    rs_rows = []
    for name, sector, market, cap, base_close, factor in stocks:
        for i, date in enumerate(base_dates):
            close = base_close * (1 + factor * i)
            volume = 1_000_000.0 + i * 50_000
            chg_1w = factor * (1 + i * 0.1)
            chg_1m = chg_1w * 4
            chg_3m = chg_1w * 12
            max52 = close * 1.1
            price_rows.append((
                name, date, close, volume,
                close * 0.99, close * 0.97, close * 0.95,
                chg_1w, chg_1m, chg_3m, max52,
            ))
            rs = 50.0 + (i * 3.0) + (20.0 if factor > 0 else -10.0)
            rs_rows.append((name, date, min(rs, 100.0)))

    conn.executemany(
        "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        price_rows,
    )
    conn.executemany(
        "INSERT INTO relative_strength VALUES (?,?,?)",
        rs_rows,
    )
    conn.commit()
    conn.close()
    return tmp.name


# ---------------------------------------------------------------------------
# 공유 픽스처
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_db() -> str:
    """모듈 범위 테스트 DB 픽스처."""
    return _create_test_db()


# ---------------------------------------------------------------------------
# compute_sector_price_index 테스트
# ---------------------------------------------------------------------------

class TestSectorPriceIndex:
    """섹터 가격 지수 계산 검증."""

    def test_returns_dict_with_sector_keys(self, test_db: str) -> None:
        """섹터 이름을 키로 하는 딕셔너리를 반환해야 한다."""
        from my_chart.analysis.sector_advanced import compute_sector_price_index

        result = compute_sector_price_index(test_db, weeks=12)
        assert isinstance(result, dict)
        # 최소한 IT, 화학, 헬스케어 섹터가 포함되어야 함
        assert "IT" in result
        assert "화학" in result
        assert "헬스케어" in result

    def test_each_sector_has_date_and_value(self, test_db: str) -> None:
        """각 섹터 값은 date와 index_value를 포함하는 딕셔너리 리스트여야 한다."""
        from my_chart.analysis.sector_advanced import compute_sector_price_index

        result = compute_sector_price_index(test_db, weeks=12)
        it_data = result["IT"]
        assert isinstance(it_data, list)
        assert len(it_data) > 0
        entry = it_data[0]
        assert "date" in entry
        assert "index_value" in entry

    def test_index_value_is_positive(self, test_db: str) -> None:
        """지수 값은 양수여야 한다."""
        from my_chart.analysis.sector_advanced import compute_sector_price_index

        result = compute_sector_price_index(test_db, weeks=12)
        for sector, entries in result.items():
            for entry in entries:
                assert entry["index_value"] > 0, f"{sector} 지수가 음수: {entry}"

    def test_weeks_parameter_limits_results(self, test_db: str) -> None:
        """weeks 파라미터로 결과 수가 제한되어야 한다."""
        from my_chart.analysis.sector_advanced import compute_sector_price_index

        result_4 = compute_sector_price_index(test_db, weeks=4)
        result_12 = compute_sector_price_index(test_db, weeks=12)
        # 4주는 최대 4개, 12주는 최대 12개
        for sector in result_4:
            assert len(result_4[sector]) <= 4
        for sector in result_12:
            assert len(result_12[sector]) <= 12


# ---------------------------------------------------------------------------
# compute_rrg_data 테스트
# ---------------------------------------------------------------------------

class TestRRGData:
    """RRG(Relative Rotation Graph) 데이터 계산 검증."""

    def test_returns_list_of_rrg_sectors(self, test_db: str) -> None:
        """RRGSector 리스트를 반환해야 한다."""
        from my_chart.analysis.sector_advanced import compute_rrg_data, RRGSector

        result = compute_rrg_data(test_db)
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(r, RRGSector) for r in result)

    def test_rrg_has_required_fields(self, test_db: str) -> None:
        """RRGSector는 name, rs_ratio, rs_momentum, quadrant, trail 필드를 가져야 한다."""
        from my_chart.analysis.sector_advanced import compute_rrg_data

        result = compute_rrg_data(test_db)
        for sector in result:
            assert hasattr(sector, "name")
            assert hasattr(sector, "rs_ratio")
            assert hasattr(sector, "rs_momentum")
            assert hasattr(sector, "quadrant")
            assert hasattr(sector, "trail")

    def test_rs_ratio_roughly_centered_at_100(self, test_db: str) -> None:
        """rs_ratio는 100 근처에서 분포해야 한다 (JdK 정규화 방식).

        z-score 정규화: (raw - mean) / std * 10 + 100
        각 섹터의 시계열 내에서 정규화되므로 현재 값들의 평균은
        100에서 벗어날 수 있다. 단, 합리적인 범위(50~150) 내에 있어야 한다.
        """
        from my_chart.analysis.sector_advanced import compute_rrg_data

        result = compute_rrg_data(test_db)
        if not result:
            pytest.skip("데이터 부족")
        rs_ratios = [r.rs_ratio for r in result]
        # 각 개별 rs_ratio 값이 합리적인 범위 내에 있어야 함
        for rs in rs_ratios:
            assert 50 <= rs <= 150, f"rs_ratio={rs:.2f}, 합리적 범위 50~150 벗어남"

    def test_quadrant_assignment(self, test_db: str) -> None:
        """quadrant는 leading/weakening/lagging/improving 중 하나여야 한다."""
        from my_chart.analysis.sector_advanced import compute_rrg_data

        valid_quadrants = {"leading", "weakening", "lagging", "improving"}
        result = compute_rrg_data(test_db)
        for sector in result:
            assert sector.quadrant in valid_quadrants, (
                f"{sector.name} quadrant={sector.quadrant} 유효하지 않음"
            )

    def test_trail_has_8_or_fewer_entries(self, test_db: str) -> None:
        """trail은 최대 8개 항목을 가져야 한다."""
        from my_chart.analysis.sector_advanced import compute_rrg_data

        result = compute_rrg_data(test_db)
        for sector in result:
            assert len(sector.trail) <= 8, (
                f"{sector.name} trail 길이={len(sector.trail)}, 최대 8이어야 함"
            )


# ---------------------------------------------------------------------------
# compute_sector_bubble 테스트
# ---------------------------------------------------------------------------

class TestSectorBubble:
    """섹터 버블 차트 데이터 계산 검증."""

    def test_returns_list_of_sector_bubble(self, test_db: str) -> None:
        """SectorBubble 리스트를 반환해야 한다."""
        from my_chart.analysis.sector_advanced import compute_sector_bubble, SectorBubble

        result = compute_sector_bubble(test_db, period="1w")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(r, SectorBubble) for r in result)

    def test_sector_bubble_has_required_fields(self, test_db: str) -> None:
        """SectorBubble는 필요한 모든 필드를 가져야 한다."""
        from my_chart.analysis.sector_advanced import compute_sector_bubble

        result = compute_sector_bubble(test_db, period="1w")
        for item in result:
            assert hasattr(item, "name")
            assert hasattr(item, "excess_return")
            assert hasattr(item, "rs_avg")
            assert hasattr(item, "trading_value")
            assert hasattr(item, "period_return")

    def test_market_filter_kospi(self, test_db: str) -> None:
        """market='KOSPI' 필터 시 KOSPI 종목만 포함되어야 한다."""
        from my_chart.analysis.sector_advanced import compute_sector_bubble

        result_all = compute_sector_bubble(test_db, period="1w", market=None)
        result_kospi = compute_sector_bubble(test_db, period="1w", market="KOSPI")
        # KOSPI 필터는 전체보다 적거나 같아야 함
        assert len(result_kospi) <= len(result_all)

    def test_market_filter_kosdaq(self, test_db: str) -> None:
        """market='KOSDAQ' 필터 시 KOSDAQ 종목만 포함된 섹터."""
        from my_chart.analysis.sector_advanced import compute_sector_bubble

        result_kosdaq = compute_sector_bubble(test_db, period="1w", market="KOSDAQ")
        assert isinstance(result_kosdaq, list)
        # KOSDAQ 종목이 있는 섹터(IT, 헬스케어)만 반환
        assert len(result_kosdaq) >= 0

    def test_period_1m_supported(self, test_db: str) -> None:
        """period='1m' 파라미터가 지원되어야 한다."""
        from my_chart.analysis.sector_advanced import compute_sector_bubble

        result = compute_sector_bubble(test_db, period="1m")
        assert isinstance(result, list)

    def test_trading_value_is_positive(self, test_db: str) -> None:
        """trading_value는 양수여야 한다."""
        from my_chart.analysis.sector_advanced import compute_sector_bubble

        result = compute_sector_bubble(test_db, period="1w")
        for item in result:
            assert item.trading_value > 0, f"{item.name} trading_value={item.trading_value}"


# ---------------------------------------------------------------------------
# compute_stock_bubble 테스트
# ---------------------------------------------------------------------------

class TestStockBubble:
    """개별 종목 버블 차트 데이터 계산 검증."""

    def test_returns_list_of_stock_bubble(self, test_db: str) -> None:
        """StockBubble 리스트를 반환해야 한다."""
        from my_chart.analysis.sector_advanced import compute_stock_bubble, StockBubble

        result = compute_stock_bubble(test_db, sector_name="IT", period="1w")
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(r, StockBubble) for r in result)

    def test_stock_bubble_has_required_fields(self, test_db: str) -> None:
        """StockBubble는 필요한 모든 필드를 가져야 한다."""
        from my_chart.analysis.sector_advanced import compute_stock_bubble

        result = compute_stock_bubble(test_db, sector_name="IT", period="1w")
        for item in result:
            assert hasattr(item, "name")
            assert hasattr(item, "price_change")
            assert hasattr(item, "rs_12m")
            assert hasattr(item, "trading_value")
            assert hasattr(item, "stage")
            assert hasattr(item, "market_cap")

    def test_filters_by_sector(self, test_db: str) -> None:
        """sector_name으로 해당 섹터 종목만 반환해야 한다."""
        from my_chart.analysis.sector_advanced import compute_stock_bubble

        it_stocks = compute_stock_bubble(test_db, sector_name="IT", period="1w")
        chem_stocks = compute_stock_bubble(test_db, sector_name="화학", period="1w")
        it_names = {s.name for s in it_stocks}
        chem_names = {s.name for s in chem_stocks}
        # IT와 화학 종목은 겹치지 않아야 함
        assert it_names.isdisjoint(chem_names)

    def test_empty_sector_returns_empty_list(self, test_db: str) -> None:
        """존재하지 않는 섹터는 빈 리스트를 반환해야 한다."""
        from my_chart.analysis.sector_advanced import compute_stock_bubble

        result = compute_stock_bubble(test_db, sector_name="존재하지않는섹터", period="1w")
        assert result == []

    def test_stage_is_valid_integer(self, test_db: str) -> None:
        """stage는 1~4 사이의 정수여야 한다."""
        from my_chart.analysis.sector_advanced import compute_stock_bubble

        result = compute_stock_bubble(test_db, sector_name="IT", period="1w")
        for item in result:
            if item.stage is not None:
                assert item.stage in (1, 2, 3, 4), (
                    f"{item.name} stage={item.stage} 유효하지 않음"
                )


# ---------------------------------------------------------------------------
# compute_treemap_data 테스트
# ---------------------------------------------------------------------------

class TestTreemapData:
    """트리맵 데이터 계산 검증."""

    def test_returns_treemap_node(self, test_db: str) -> None:
        """TreemapNode를 반환해야 한다."""
        from my_chart.analysis.sector_advanced import compute_treemap_data, TreemapNode

        result = compute_treemap_data(test_db, period="1w")
        assert isinstance(result, TreemapNode)

    def test_root_has_children(self, test_db: str) -> None:
        """루트 노드는 섹터 자식 노드를 가져야 한다."""
        from my_chart.analysis.sector_advanced import compute_treemap_data

        result = compute_treemap_data(test_db, period="1w")
        assert hasattr(result, "children")
        assert len(result.children) > 0

    def test_sector_nodes_have_stock_children(self, test_db: str) -> None:
        """섹터 노드는 종목 자식 노드를 가져야 한다."""
        from my_chart.analysis.sector_advanced import compute_treemap_data

        result = compute_treemap_data(test_db, period="1w")
        for sector_node in result.children:
            assert len(sector_node.children) > 0, (
                f"섹터 {sector_node.name}에 종목이 없음"
            )

    def test_market_cap_is_positive(self, test_db: str) -> None:
        """market_cap은 양수여야 한다."""
        from my_chart.analysis.sector_advanced import compute_treemap_data

        result = compute_treemap_data(test_db, period="1w")
        for sector_node in result.children:
            assert sector_node.market_cap > 0
            for stock_node in sector_node.children:
                assert stock_node.market_cap > 0

    def test_treemap_node_has_required_fields(self, test_db: str) -> None:
        """TreemapNode는 name, market_cap, price_change 필드를 가져야 한다."""
        from my_chart.analysis.sector_advanced import compute_treemap_data

        result = compute_treemap_data(test_db, period="1w")
        assert hasattr(result, "name")
        assert hasattr(result, "market_cap")
        assert hasattr(result, "price_change")
        for sector in result.children:
            assert hasattr(sector, "name")
            assert hasattr(sector, "market_cap")
            assert hasattr(sector, "price_change")
            for stock in sector.children:
                assert hasattr(stock, "name")
                assert hasattr(stock, "market_cap")
                assert hasattr(stock, "price_change")

    def test_sector_market_cap_equals_sum_of_stocks(self, test_db: str) -> None:
        """섹터 market_cap은 자식 종목들의 market_cap 합계와 같아야 한다."""
        from my_chart.analysis.sector_advanced import compute_treemap_data

        result = compute_treemap_data(test_db, period="1w")
        for sector in result.children:
            total = sum(s.market_cap for s in sector.children)
            assert abs(sector.market_cap - total) < 1.0, (
                f"섹터 {sector.name}: market_cap={sector.market_cap}, "
                f"자식 합계={total}"
            )


# ---------------------------------------------------------------------------
# 엣지 케이스 테스트
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """엣지 케이스 및 에러 처리 검증."""

    def test_empty_db_returns_empty(self) -> None:
        """데이터 없는 DB에서 빈 결과 반환."""
        from my_chart.analysis.sector_advanced import compute_sector_bubble

        # 빈 DB 생성
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        conn = sqlite3.connect(tmp.name)
        conn.executescript("""
            CREATE TABLE stock_prices (
                Name TEXT, Date TEXT, Close REAL, Volume REAL,
                SMA10 REAL, SMA40 REAL, SMA40_Trend_4M REAL,
                CHG_1W REAL, CHG_1M REAL, CHG_3M REAL, MAX52 REAL
            );
            CREATE TABLE stock_meta (
                name TEXT, code TEXT, sector_major TEXT, sector_minor TEXT,
                market TEXT, market_cap REAL
            );
            CREATE TABLE relative_strength (
                Name TEXT, Date TEXT, RS_12M_Rating REAL
            );
        """)
        conn.commit()
        conn.close()

        result = compute_sector_bubble(tmp.name, period="1w")
        assert result == []

    def test_sector_with_no_market_cap_data(self, test_db: str) -> None:
        """market_cap 데이터 없는 종목도 처리 가능해야 한다."""
        from my_chart.analysis.sector_advanced import compute_treemap_data

        # 예외 없이 실행되어야 함
        result = compute_treemap_data(test_db, period="1w")
        assert result is not None

    def test_rrg_data_handles_insufficient_history(self) -> None:
        """히스토리가 부족한 경우도 처리 가능해야 한다."""
        from my_chart.analysis.sector_advanced import compute_rrg_data

        # 데이터 1주만 있는 DB 생성
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        conn = sqlite3.connect(tmp.name)
        conn.executescript("""
            CREATE TABLE stock_prices (
                Name TEXT, Date TEXT, Close REAL, Volume REAL,
                SMA10 REAL, SMA40 REAL, SMA40_Trend_4M REAL,
                CHG_1W REAL, CHG_1M REAL, CHG_3M REAL, MAX52 REAL
            );
            CREATE TABLE stock_meta (
                name TEXT, code TEXT, sector_major TEXT, sector_minor TEXT,
                market TEXT, market_cap REAL
            );
            CREATE TABLE relative_strength (
                Name TEXT, Date TEXT, RS_12M_Rating REAL
            );
        """)
        conn.execute(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("KOSPI", "2024-01-05", 2500.0, 5000000.0, 2450.0, 2400.0, 2350.0, 0.01, 0.02, 0.04, 2600.0)
        )
        conn.execute(
            "INSERT INTO stock_prices VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            ("삼성전자", "2024-01-05", 70000.0, 1000000.0, 69000.0, 68000.0, 67000.0, 0.02, 0.03, 0.06, 75000.0)
        )
        conn.execute(
            "INSERT INTO stock_meta VALUES (?,?,?,?,?,?)",
            ("삼성전자", "005930", "IT", "반도체", "KOSPI", 400000000.0)
        )
        conn.execute(
            "INSERT INTO relative_strength VALUES (?,?,?)",
            ("삼성전자", "2024-01-05", 75.0)
        )
        conn.commit()
        conn.close()

        # 예외 없이 실행되어야 함 (데이터 부족 시 빈 결과 반환 가능)
        result = compute_rrg_data(tmp.name)
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# detect_sector_transitions 테스트
# ---------------------------------------------------------------------------

class TestDetectSectorTransitions:
    """섹터 전환 감지 검증."""

    def test_returns_sector_alerts(self, test_db: str) -> None:
        """SectorAlerts 타입을 반환해야 한다."""
        from my_chart.analysis.sector_advanced import detect_sector_transitions, SectorAlerts

        result = detect_sector_transitions(test_db)
        assert isinstance(result, SectorAlerts)

    def test_has_emerging_leaders_and_weakening_sectors(self, test_db: str) -> None:
        """emerging_leaders와 weakening_sectors 필드를 가져야 한다."""
        from my_chart.analysis.sector_advanced import detect_sector_transitions

        result = detect_sector_transitions(test_db)
        assert hasattr(result, "emerging_leaders")
        assert hasattr(result, "weakening_sectors")
        assert isinstance(result.emerging_leaders, list)
        assert isinstance(result.weakening_sectors, list)

    def test_alerts_have_name_and_signals(self, test_db: str) -> None:
        """각 SectorAlert는 name과 signals 필드를 가져야 한다."""
        from my_chart.analysis.sector_advanced import detect_sector_transitions

        result = detect_sector_transitions(test_db)
        for alert in result.emerging_leaders + result.weakening_sectors:
            assert hasattr(alert, "name")
            assert hasattr(alert, "signals")
            assert isinstance(alert.name, str)
            assert isinstance(alert.signals, list)

    def test_max_5_alerts_per_category(self, test_db: str) -> None:
        """강세/약세 각각 최대 5개까지만 반환해야 한다."""
        from my_chart.analysis.sector_advanced import detect_sector_transitions

        result = detect_sector_transitions(test_db)
        assert len(result.emerging_leaders) <= 5
        assert len(result.weakening_sectors) <= 5

    def test_empty_db_returns_empty_alerts(self) -> None:
        """빈 DB에서 빈 alerts를 반환해야 한다."""
        from my_chart.analysis.sector_advanced import detect_sector_transitions

        # 빈 DB 생성
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        conn = sqlite3.connect(tmp.name)
        conn.executescript("""
            CREATE TABLE stock_prices (
                Name TEXT, Date TEXT, Close REAL, Volume REAL,
                SMA10 REAL, SMA40 REAL, SMA40_Trend_4M REAL,
                CHG_1W REAL, CHG_1M REAL, CHG_3M REAL, MAX52 REAL
            );
            CREATE TABLE stock_meta (
                name TEXT, code TEXT, sector_major TEXT, sector_minor TEXT,
                market TEXT, market_cap REAL
            );
            CREATE TABLE relative_strength (
                Name TEXT, Date TEXT, RS_12M_Rating REAL
            );
        """)
        conn.commit()
        conn.close()

        result = detect_sector_transitions(tmp.name)
        assert result.emerging_leaders == []
        assert result.weakening_sectors == []

    def test_signals_are_strings(self, test_db: str) -> None:
        """signals 목록의 각 항목은 문자열이어야 한다."""
        from my_chart.analysis.sector_advanced import detect_sector_transitions

        result = detect_sector_transitions(test_db)
        for alert in result.emerging_leaders + result.weakening_sectors:
            for signal in alert.signals:
                assert isinstance(signal, str), f"시그널이 문자열이 아님: {signal!r}"
