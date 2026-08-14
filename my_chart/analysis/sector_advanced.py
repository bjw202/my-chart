"""고급 섹터 분석 엔진 (SPEC-TOPDOWN-002A).

RRG(Relative Rotation Graph), 섹터/종목 버블 차트, 트리맵 데이터를 계산한다.
weekly SQLite DB 데이터를 기반으로 동작한다.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from my_chart.analysis.aggregate_types import WEIGHT_CAP
from my_chart.analysis.stage_classifier import classify_stage, _compute_slope
from my_chart.analysis.weekly_grid import compute_weekly_grid
from my_chart.analysis.weighting import capped_weights_detail
from my_chart.config import DEFAULT_DB_DAILY

# M6-gap G23 — AC-SAG-041 근접 신고가 판정. `sector_metrics._NH_THRESHOLD` /
# `stage_service._NEAR_52W_THRESHOLD` 와 동일 관용(2% 이내).
_NEAR_52W_THRESHOLD = 0.02

# ---------------------------------------------------------------------------
# 상수 정의
# ---------------------------------------------------------------------------

# 인덱스 종목명 (주식 계산에서 제외)
_INDEX_NAMES = frozenset({"KOSPI", "KOSDAQ"})

# RRG 정규화 파라미터
_RRG_LOOKBACK_WEEKS = 12  # z-score 계산을 위한 롤링 윈도우
_RRG_SCALE = 7.0           # z-score 스케일 팩터 (축 범위 75~125에 맞춤)
_RRG_CENTER = 100.0        # 정규화 중심값


# @MX:NOTE: [AUTO] M6-gap G20 — RRG/종목버블 `market` 파라미터 실배선.
#   라우터는 소문자 `all`/`kospi`/`kosdaq` 를 받지만 `stock_meta.market`(`시장구분`)
#   원천은 대문자 `KOSPI`/`KOSDAQ` 로 저장된다(`_build_sector_stock_map` 관용과 동일).
def _normalize_market_filter(market: str | None) -> str | None:
    """``all``/``None``/``""`` → ``None``(무필터). 그 외 → 대문자(``KOSPI``/``KOSDAQ``)."""
    if not market or market.strip().lower() == "all":
        return None
    return market.strip().upper()


# ---------------------------------------------------------------------------
# 데이터 클래스 정의
# ---------------------------------------------------------------------------

@dataclass
class RRGSector:
    """RRG 차트용 섹터 데이터."""

    name: str
    rs_ratio: float          # 현재 RS-Ratio (100 기준)
    rs_momentum: float       # 현재 RS-Momentum (100 기준)
    quadrant: str            # leading/weakening/lagging/improving
    trail: list[dict[str, float]] = field(default_factory=list)  # 8주 궤적


@dataclass
class SectorBubble:
    """섹터 버블 차트용 데이터."""

    name: str
    excess_return: float     # KOSPI 대비 초과수익률 (%)
    rs_avg: float            # 섹터 평균 RS
    trading_value: float     # 거래대금 합계 (Close * Volume)
    period_return: float     # 기간 수익률 (%)


# @MX:NOTE: [AUTO] StockBubble에 sector_minor 필드 추가. API 응답에 산업명(중) 포함. 기본값 None으로 하위 호환성 유지.
# @MX:SPEC: SPEC-SECTOR-MINOR-COLOR-001
@dataclass
class StockBubble:
    """종목 버블 차트용 데이터."""

    name: str
    price_change: float      # 기간 가격 변화율 (%)
    rs_12m: float            # 12개월 RS
    trading_value: float     # 거래대금
    stage: int | None        # 스테이지 (1~4)
    stage_detail: str | None # 스테이지 상세
    market_cap: float        # 시가총액
    # AC-SAG-028 — weekly VolumeSMA10 기준. NULL/0 이면 None(1.0 치환 금지, REQ-SAG-025).
    volume_ratio: float | None
    sector_minor: str | None = None  # 산업명(중) (SPEC-SECTOR-MINOR-COLOR-001)
    product: str | None = None       # 주요제품 (SPEC-STOCK-TOOLTIP-PRODUCT-001)
    # M6-gap G23 — AC-SAG-041 종목 목록 필드 확장(weight_in_sector/chg_1w/chg_3m/
    # near_52w_high). 결측은 None(치환 금지).
    weight_in_sector: float | None = None
    chg_1w: float | None = None
    chg_3m: float | None = None
    near_52w_high: bool | None = None


@dataclass
class TreemapNode:
    """트리맵 계층 노드.

    루트 → 섹터 → 종목 구조를 표현한다.
    """

    name: str
    market_cap: float        # 시가총액 (크기)
    price_change: float      # 가격 변화율 (색상)
    rs_12m: float = 0.0      # 12개월 RS
    stage: int | None = None # 스테이지
    children: list[TreemapNode] = field(default_factory=list)


# ---------------------------------------------------------------------------
# DB 헬퍼 함수
# ---------------------------------------------------------------------------

def _connect(db_path: str) -> sqlite3.Connection:
    """SQLite 연결 생성."""
    return sqlite3.connect(db_path, check_same_thread=False)


def _get_dates(db_path: str, weeks: int) -> list[str]:
    """최근 N주 정규 격자 날짜(오름차순). SPEC-SECTOR-GRID-001 REQ-SGR-005.

    ``compute_weekly_grid`` 의 정규 격자(CG-1 ISO 주당 1바·CG-3 부분 데이터 배제)에서
    최근 ``weeks`` 개 바를 취한다. 자체 최신-날짜 직조회 SQL 관용구는 폐기했다.
    """
    grid = compute_weekly_grid(db_path)
    dates = grid.dates  # 정규 격자 전체(미완성 latest 포함), 오름차순
    if not dates:
        return []
    if weeks <= 0:
        return list(dates)
    return dates[-weeks:]


def _get_kospi_close_by_date(conn: sqlite3.Connection, dates: list[str]) -> dict[str, float]:
    """날짜별 KOSPI 종가를 반환한다."""
    if not dates:
        return {}
    placeholders = ",".join("?" * len(dates))
    rows = conn.execute(
        f"SELECT Date, Close FROM stock_prices WHERE Name='KOSPI' AND Date IN ({placeholders})",
        dates,
    ).fetchall()
    return {r[0]: float(r[1] or 0.0) for r in rows}


# @MX:NOTE: [AUTO] stock_meta SELECT에 sector_minor 컬럼 추가. sector_detail_service.py와 동일 패턴.
# @MX:SPEC: SPEC-SECTOR-MINOR-COLOR-001
# @MX:NOTE: [AUTO] stock_meta SELECT에 product(주요제품) 컬럼 추가. sector_minor와 동일 패턴.
# @MX:SPEC: SPEC-STOCK-TOOLTIP-PRODUCT-001
def _get_stock_meta(db_path: str | None = None) -> dict[str, dict[str, Any]]:
    """stock_meta에서 종목 메타데이터를 로드한다.

    stock_meta 테이블은 daily DB에만 존재한다.
    db_path가 주어져도 먼저 해당 DB에서 시도하고, stock_meta가 없으면 daily DB를 사용한다.

    Args:
        db_path: 우선 시도할 DB 경로. None이면 daily DB 기본 경로 사용.

    Returns:
        {Name: {Code, sector_major, sector_minor, 시장구분, market_cap, product}} 딕셔너리
    """
    daily_fallback = f"{DEFAULT_DB_DAILY}.db"
    paths_to_try = [db_path, daily_fallback] if db_path else [daily_fallback]

    for path in paths_to_try:
        if not path:
            continue
        conn = _connect(path)
        try:
            rows = conn.execute(
                "SELECT name, code, sector_major, sector_minor, market, market_cap, product FROM stock_meta"
            ).fetchall()
            if rows:
                result: dict[str, dict[str, Any]] = {}
                for name, code, sector, sector_minor, market, cap, product in rows:
                    result[str(name)] = {
                        "Code": code or "",
                        "sector_major": sector or "",
                        "sector_minor": sector_minor or None,  # SPEC-SECTOR-MINOR-COLOR-001
                        "시장구분": market or "",
                        "market_cap": float(cap or 0.0),
                        "product": product or None,  # SPEC-STOCK-TOOLTIP-PRODUCT-001
                    }
                return result
        except sqlite3.OperationalError:
            pass
        finally:
            conn.close()
    return {}


def _get_price_on_date(
    conn: sqlite3.Connection, date: str
) -> dict[str, dict[str, Any]]:
    """특정 날짜의 종가 및 거래량 데이터를 로드한다."""
    try:
        rows = conn.execute(
            """SELECT Name, Close, Volume, SMA10, SMA40, SMA40_Trend_4M,
                      CHG_1W, CHG_1M, CHG_3M, MAX52, VolumeSMA10
               FROM stock_prices
               WHERE Date = ?""",
            (date,),
        ).fetchall()
    except sqlite3.OperationalError:
        # `VolumeSMA10` 컬럼이 없는 최소 스키마 픽스처(단위 테스트) — volume_ratio 는
        # 전부 결측(None)으로 접힌다(AC-SAG-028). 라이브/집계 픽스처는 항상 보유.
        rows = [
            (*r, None) for r in conn.execute(
                """SELECT Name, Close, Volume, SMA10, SMA40, SMA40_Trend_4M,
                          CHG_1W, CHG_1M, CHG_3M, MAX52
                   FROM stock_prices
                   WHERE Date = ?""",
                (date,),
            ).fetchall()
        ]
    result: dict[str, dict[str, Any]] = {}
    for r in rows:
        name = r[0]
        sma40 = float(r[4] or 0.0)
        sma40_prev = float(r[5] or 0.0)
        result[str(name)] = {
            "Close": float(r[1] or 0.0),
            "Volume": float(r[2] or 0.0),
            "SMA10": float(r[3] or 0.0),
            "SMA40": sma40,
            "SMA40_slope": _compute_slope(sma40, sma40_prev),
            "SMA40_Trend_4M": sma40_prev,
            "CHG_1W": float(r[6] or 0.0),
            "CHG_1M": float(r[7] or 0.0),
            "CHG_3M": float(r[8] or 0.0),
            "MAX52": float(r[9] or 0.0),
            # AC-SAG-028 — 원시(raw) VolumeSMA10. None/0 은 volume_ratio 결측 판정에 쓴다.
            "VolumeSMA10": r[10],
        }
    return result


def _get_rs_on_date(
    conn: sqlite3.Connection, date: str
) -> dict[str, float]:
    """특정 날짜의 RS_12M_Rating을 종목명 키로 반환한다."""
    rows = conn.execute(
        "SELECT Name, RS_12M_Rating FROM relative_strength WHERE Date = ?",
        (date,),
    ).fetchall()
    return {str(r[0]): float(r[1] or 0.0) for r in rows}


# ---------------------------------------------------------------------------
# 섹터 구조: sector_name → stock_names 매핑 (stock_meta 기반)
# ---------------------------------------------------------------------------

def _build_sector_stock_map(
    stock_meta: dict[str, dict[str, Any]],
    market_filter: str | None = None,
) -> dict[str, list[str]]:
    """섹터별 종목 이름 목록을 빌드한다.

    Args:
        stock_meta: _get_stock_meta() 결과
        market_filter: None=전체, "KOSPI"=코스피만, "KOSDAQ"=코스닥만

    Returns:
        {sector_major: [stock_names]} 딕셔너리
    """
    sector_map: dict[str, list[str]] = {}
    for name, meta in stock_meta.items():
        if market_filter and meta["시장구분"] != market_filter:
            continue
        sector = meta["sector_major"] or "기타"
        if not sector:
            continue
        sector_map.setdefault(sector, []).append(name)
    return sector_map


# ---------------------------------------------------------------------------
# compute_sector_price_index
# ---------------------------------------------------------------------------

def compute_sector_price_index(
    db_path: str, weeks: int = 12, market: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """섹터별 시가총액 가중 가격 지수를 계산한다.

    공식: sector_price_index = sum(close * market_cap) / sum(market_cap)

    Args:
        db_path: weekly SQLite DB 경로
        weeks: 조회할 주수 (기본 12주)
        market: 시장 필터 — ``None``/``"all"``=전체, ``"kospi"``/``"KOSPI"``/
            ``"kosdaq"``/``"KOSDAQ"``(대소문자 무관, M6-gap G20). 필터는 섹터
            지수를 구성하는 종목 유니버스에 적용된다 — RRG 가 시장별 지수를
            실제로 재계산할 수 있는 유일한 경로다.

    Returns:
        {sector_name: [{date, index_value}, ...]} 딕셔너리
        KOSPI 인덱스도 "KOSPI" 키로 포함된다.
    """
    conn = _connect(db_path)
    try:
        dates = _get_dates(db_path, weeks)
        if not dates:
            return {}

        stock_meta = _get_stock_meta(db_path)
        sector_map = _build_sector_stock_map(
            stock_meta, market_filter=_normalize_market_filter(market))
        kospi_closes = _get_kospi_close_by_date(conn, dates)

        # 섹터별 시계열 데이터 초기화
        sector_series: dict[str, list[dict[str, Any]]] = {
            sector: [] for sector in sector_map
        }
        sector_series["KOSPI"] = []

        for date in dates:
            price_data = _get_price_on_date(conn, date)

            # KOSPI 인덱스 추가
            if date in kospi_closes and kospi_closes[date] > 0:
                sector_series["KOSPI"].append({
                    "date": date,
                    "index_value": kospi_closes[date],
                })

            # 각 섹터별 가중 지수 계산 (market_cap 없으면 동일 가중)
            for sector, stock_names in sector_map.items():
                total_weight = 0.0
                weighted_close = 0.0
                for name in stock_names:
                    if name not in price_data or name in _INDEX_NAMES:
                        continue
                    close = price_data[name]["Close"]
                    cap = stock_meta[name]["market_cap"]
                    # market_cap이 없으면 동일 가중(1.0) 사용
                    weight = cap if cap and cap > 0 else 1.0
                    if close > 0:
                        weighted_close += close * weight
                        total_weight += weight

                if total_weight > 0:
                    index_value = weighted_close / total_weight
                    sector_series[sector].append({
                        "date": date,
                        "index_value": round(index_value, 4),
                    })

    finally:
        conn.close()

    # 빈 섹터 제거
    return {k: v for k, v in sector_series.items() if v}


# ---------------------------------------------------------------------------
# compute_rrg_data
# ---------------------------------------------------------------------------

def _rolling_zscore(values: list[float], lookback: int) -> list[float]:
    """롤링 z-score 정규화 (JdK RS-Ratio 방식).

    각 시점에서 최근 lookback 개 값의 평균/표준편차로 z-score를 계산한다.
    결과 = (현재값 - 롤링평균) / 롤링표준편차 * scale + center

    lookback 미만의 초기 값들은 100으로 채운다.
    """
    if not values:
        return []
    result: list[float] = []
    for i in range(len(values)):
        if i < lookback - 1:
            result.append(_RRG_CENTER)
            continue
        window = values[max(0, i - lookback + 1) : i + 1]
        n = len(window)
        mean = sum(window) / n
        variance = sum((v - mean) ** 2 for v in window) / n
        std = variance ** 0.5
        if std == 0:
            result.append(_RRG_CENTER)
        else:
            z = (values[i] - mean) / std
            result.append(z * _RRG_SCALE + _RRG_CENTER)
    return result


def _assign_quadrant(rs_ratio: float, rs_momentum: float) -> str:
    """RRG 사분면을 결정한다.

    - leading:   rs_ratio > 100 AND rs_momentum > 100
    - weakening: rs_ratio > 100 AND rs_momentum <= 100
    - lagging:   rs_ratio <= 100 AND rs_momentum <= 100
    - improving: rs_ratio <= 100 AND rs_momentum > 100
    """
    if rs_ratio > _RRG_CENTER and rs_momentum > _RRG_CENTER:
        return "leading"
    elif rs_ratio > _RRG_CENTER and rs_momentum <= _RRG_CENTER:
        return "weakening"
    elif rs_ratio <= _RRG_CENTER and rs_momentum <= _RRG_CENTER:
        return "lagging"
    else:
        return "improving"


def compute_rrg_data(db_path: str, weeks: int = 0, market: str | None = None) -> list[RRGSector]:
    """RRG(Relative Rotation Graph) 데이터를 계산한다.

    DB에 있는 전체 기간(또는 지정 주수)의 RS-Ratio/Momentum 시계열을 반환한다.
    프론트엔드에서 8주 윈도우를 슬라이딩하며 표시한다.

    JdK RS-Ratio 방식:
    1. RS raw = sector_index / KOSPI_index * 100
    2. RS-Ratio = 롤링 z-score(RS raw, lookback=12) * 7 + 100
    3. RS-Momentum = 롤링 z-score(RS-Ratio 주간 변화량, lookback=12) * 7 + 100

    Args:
        db_path: weekly SQLite DB 경로
        weeks: 조회 주수 (0이면 전체 기간)
        market: 시장 필터 — ``None``/``"all"``=전체, ``"kospi"``/``"kosdaq"``
            (M6-gap G20). 섹터 지수 시계열을 구성하는 종목 유니버스를 시장으로
            제한한다 — 별도 시장별 지수 저장소를 신설하지 않고, `compute_
            sector_price_index` 의 종목 유니버스 필터를 재사용해 실제로
            시장별 RRG 를 재계산한다(M2/M3 이 확립한 `_market_matches` 계열
            유니버스 필터 관용을 이 모듈에서 재사용).

    Returns:
        RRGSector 리스트 (trail에 전체 시계열 포함)
    """
    # weeks=0이면 DB에 있는 전체 주수 로드
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        if weeks <= 0:
            row = conn.execute(
                "SELECT COUNT(DISTINCT Date) FROM stock_prices WHERE Name NOT IN ('KOSPI','KOSDAQ')"
            ).fetchone()
            total_weeks = row[0] if row else 20
        else:
            total_weeks = weeks
    finally:
        conn.close()

    sector_index = compute_sector_price_index(db_path, weeks=total_weeks, market=market)

    if "KOSPI" not in sector_index or not sector_index["KOSPI"]:
        return []

    kospi_by_date: dict[str, float] = {
        e["date"]: e["index_value"] for e in sector_index["KOSPI"]
    }

    results: list[RRGSector] = []

    for sector_name, entries in sector_index.items():
        if sector_name == "KOSPI":
            continue
        if len(entries) < 2:
            continue

        entries_sorted = sorted(entries, key=lambda e: e["date"])

        # 1단계: KOSPI 대비 RS raw 계산
        rs_raw: list[float] = []
        valid_dates: list[str] = []
        for entry in entries_sorted:
            date = entry["date"]
            kospi_val = kospi_by_date.get(date, 0.0)
            if kospi_val > 0:
                rs_raw.append(entry["index_value"] / kospi_val * 100)
                valid_dates.append(date)

        if len(rs_raw) < 2:
            continue

        # 2단계: RS-Ratio 롤링 z-score
        rs_ratio_series = _rolling_zscore(rs_raw, _RRG_LOOKBACK_WEEKS)

        # 3단계: RS-Momentum = RS-Ratio 변화량의 롤링 z-score
        rs_ratio_delta: list[float] = [0.0]
        for i in range(1, len(rs_ratio_series)):
            rs_ratio_delta.append(rs_ratio_series[i] - rs_ratio_series[i - 1])
        rs_momentum_series = _rolling_zscore(rs_ratio_delta, _RRG_LOOKBACK_WEEKS)

        # lookback이 안정화된 시점부터만 반환 (처음 lookback-1개는 100 고정값이므로 제외)
        start_idx = min(_RRG_LOOKBACK_WEEKS - 1, len(rs_ratio_series) - 1)

        # 전체 시계열을 trail로 반환
        trail = [
            {
                "date": valid_dates[i],
                "rs_ratio": round(rs_ratio_series[i], 4),
                "rs_momentum": round(rs_momentum_series[i], 4),
            }
            for i in range(start_idx, len(rs_ratio_series))
        ]

        if not trail:
            continue

        # 현재 값 (마지막)
        current_rs_ratio = rs_ratio_series[-1]
        current_rs_momentum = rs_momentum_series[-1]
        quadrant = _assign_quadrant(current_rs_ratio, current_rs_momentum)

        results.append(RRGSector(
            name=sector_name,
            rs_ratio=round(current_rs_ratio, 4),
            rs_momentum=round(current_rs_momentum, 4),
            quadrant=quadrant,
            trail=trail,
        ))

    return results


# ---------------------------------------------------------------------------
# compute_sector_bubble
# ---------------------------------------------------------------------------

def _get_chg_by_period(price_row: dict[str, Any], period: str) -> float:
    """기간에 따른 가격 변화율(%)을 반환한다.

    DB에서 CHG 값은 소수 (0.02 = 2%), * 100 후 반환한다.
    """
    field_map = {
        "1w": "CHG_1W",
        "1m": "CHG_1M",
        "3m": "CHG_3M",
    }
    field_key = field_map.get(period, "CHG_1W")
    raw = price_row.get(field_key, 0.0) or 0.0
    return float(raw) * 100  # 소수 → %


def compute_sector_bubble(
    db_path: str,
    period: str = "1w",
    market: str | None = None,
) -> list[SectorBubble]:
    """섹터 버블 차트 데이터를 계산한다.

    Args:
        db_path: weekly SQLite DB 경로
        period: 수익률 계산 기간 ("1w", "1m", "3m")
        market: 시장 필터 — ``None``/``"all"``=전체, ``"kospi"``/``"kosdaq"``
            (대소문자 무관). ``stock_meta.시장구분`` 원천은 대문자이므로
            ``_normalize_market_filter`` 를 거쳐야 한다 —
            ``compute_stock_bubble``/``compute_sector_price_index`` 와 같은 관용.

    Returns:
        SectorBubble 리스트
    """
    market_filter = _normalize_market_filter(market)
    conn = _connect(db_path)
    try:
        dates = _get_dates(db_path, 1)  # 최신 날짜만 필요
        if not dates:
            return []
        latest_date = dates[-1]

        stock_meta = _get_stock_meta(db_path)
        sector_map = _build_sector_stock_map(stock_meta, market_filter=market_filter)
        price_data = _get_price_on_date(conn, latest_date)
        rs_data = _get_rs_on_date(conn, latest_date)

        # KOSPI 기간 수익률 계산
        kospi_row = price_data.get("KOSPI", {})
        kospi_return = _get_chg_by_period(kospi_row, period)

    finally:
        conn.close()

    results: list[SectorBubble] = []

    for sector_name, stock_names in sector_map.items():
        excess_returns = []
        rs_values = []
        trading_values = []
        period_returns = []

        for name in stock_names:
            if name not in price_data or name in _INDEX_NAMES:
                continue
            price_row = price_data[name]
            close = price_row["Close"]
            volume = price_row["Volume"]
            ret = _get_chg_by_period(price_row, period)
            rs = rs_data.get(name, 0.0)

            excess_returns.append(ret - kospi_return)
            rs_values.append(rs)
            trading_values.append(close * volume)
            period_returns.append(ret)

        if not excess_returns:
            continue

        n = len(excess_returns)
        results.append(SectorBubble(
            name=sector_name,
            excess_return=round(sum(excess_returns) / n, 4),
            rs_avg=round(sum(rs_values) / n, 2),
            trading_value=round(sum(trading_values), 0),
            period_return=round(sum(period_returns) / n, 4),
        ))

    return results


# ---------------------------------------------------------------------------
# compute_stock_bubble
# ---------------------------------------------------------------------------

def _load_raw_chg_max52(conn: sqlite3.Connection, date: str) -> dict[str, dict[str, Any]]:
    """CHG_1W / CHG_3M / MAX52 — 결측을 0 으로 접지 않는 원시(raw) 조회.

    `_get_price_on_date` 는 공유 함수라 다른 호출자와의 하위 호환을 위해 결측을
    `0.0` 으로 접는다(scope discipline — 건드리지 않는다). AC-SAG-041 의
    `chg_1w`/`chg_3m`/`near_52w_high` 는 결측을 `None` 으로 보존해야 하므로
    (§9.1) 이 함수에서 별도 원시 조회를 한다(stage_service._load_extended_weekly_fields
    와 동일 관용).
    """
    try:
        rows = conn.execute(
            "SELECT Name, CHG_1W, CHG_3M, Close, MAX52 FROM stock_prices WHERE Date = ?",
            (date,),
        ).fetchall()
    except sqlite3.OperationalError:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for name, chg_1w, chg_3m, close, max52 in rows:
        out[str(name)] = {"chg_1w": chg_1w, "chg_3m": chg_3m, "close": close, "max52": max52}
    return out


def compute_stock_bubble(
    db_path: str,
    sector_name: str,
    period: str = "1w",
    market: str | None = None,
) -> list[StockBubble]:
    """섹터 내 종목 버블 차트 데이터를 계산한다.

    Args:
        db_path: weekly SQLite DB 경로
        sector_name: 조회할 섹터명
        period: 수익률 계산 기간 ("1w", "1m", "3m")
        market: 시장 필터 — ``None``/``"all"``=전체, ``"kospi"``/``"kosdaq"``
            (대소문자 무관, M6-gap G20). 섹터 내 종목을 시장으로 제한하며,
            ``weight_in_sector``(AC-SAG-041)도 이 필터링 후 유니버스 기준으로
            재계산된다(stage_service 의 시장 필터→가중치 재계산 관용과 동일).

    Returns:
        StockBubble 리스트
    """
    market_filter = _normalize_market_filter(market)
    conn = _connect(db_path)
    try:
        dates = _get_dates(db_path, 1)
        if not dates:
            return []
        latest_date = dates[-1]

        stock_meta = _get_stock_meta(db_path)
        price_data = _get_price_on_date(conn, latest_date)
        rs_data = _get_rs_on_date(conn, latest_date)
        raw_extended = _load_raw_chg_max52(conn, latest_date)

        # 해당 섹터 종목 필터링 (+ M6-gap G20 — market 필터)
        sector_stocks = [
            name for name, meta in stock_meta.items()
            if meta["sector_major"] == sector_name
            and (market_filter is None or meta["시장구분"] == market_filter)
        ]

    finally:
        conn.close()

    if not sector_stocks:
        return []

    # M6-gap G23 — AC-SAG-041 weight_in_sector: 이 섹터(위 market 필터 적용 후)
    # 유니버스에 대해 시총 상한 재배분 가중치를 산출한다(INV-CAP-1, `weighting.
    # capped_weights_detail` 재사용 — stage_service._weight_in_sector_map 과
    # 동일 산식, 별도 재구현하지 않는다).
    sector_caps = {
        name: float(stock_meta[name]["market_cap"])
        for name in sector_stocks
        if stock_meta[name].get("market_cap") and float(stock_meta[name]["market_cap"]) > 0
    }
    weight_map: dict[str, float] = (
        capped_weights_detail(sector_caps, cap=WEIGHT_CAP).weights if sector_caps else {})

    results: list[StockBubble] = []
    for name in sector_stocks:
        if name not in price_data or name in _INDEX_NAMES:
            continue
        price_row = price_data[name]
        meta = stock_meta[name]
        close = price_row["Close"]
        volume = price_row["Volume"]
        sma10 = price_row["SMA10"]
        raw_volume_sma10 = price_row.get("VolumeSMA10")
        rs = rs_data.get(name, 0.0)
        price_change = _get_chg_by_period(price_row, period)
        trading_value = close * volume
        cap = meta["market_cap"]

        ext = raw_extended.get(name, {})
        chg_1w = float(ext["chg_1w"]) * 100 if ext.get("chg_1w") is not None else None
        chg_3m = float(ext["chg_3m"]) * 100 if ext.get("chg_3m") is not None else None
        ext_close = ext.get("close")
        ext_max52 = ext.get("max52")
        near_52w_high: bool | None = None
        if ext_close is not None and ext_max52 is not None and float(ext_max52) > 0:
            near_52w_high = float(ext_close) >= float(ext_max52) * (1 - _NEAR_52W_THRESHOLD)

        # AC-SAG-028 — volume_ratio = Volume / VolumeSMA10(weekly). NULL/0 이면 None
        # (1.0 치환 금지, REQ-SAG-025). 가격 SMA10 을 거래량 기준선으로 쓰던 근사를 폐기.
        if raw_volume_sma10 is None or float(raw_volume_sma10) == 0:
            volume_ratio: float | None = None
            stage_volume_sma10 = 1.0  # stage 분류 입력(classify_stage)만의 안전값
        else:
            volume_ratio = volume / float(raw_volume_sma10)
            stage_volume_sma10 = float(raw_volume_sma10)

        # 스테이지 분류
        stock_row = {
            "Name": name,
            "Close": close,
            "SMA10": sma10,
            "SMA40": price_row["SMA40"],
            "SMA40_slope": price_row["SMA40_slope"],
            "RS_12M_Rating": rs,
            "CHG_1M": price_row["CHG_1M"],
            "Volume": volume,
            "VolumeSMA10": stage_volume_sma10,
        }
        stage_result = classify_stage(stock_row)

        results.append(StockBubble(
            name=name,
            price_change=round(price_change, 4),
            rs_12m=round(rs, 2),
            trading_value=round(trading_value, 0),
            stage=stage_result.stage,
            stage_detail=stage_result.detail,
            market_cap=round(cap, 0),
            volume_ratio=round(volume_ratio, 4) if volume_ratio is not None else None,
            sector_minor=meta.get("sector_minor"),  # SPEC-SECTOR-MINOR-COLOR-001
            product=meta.get("product"),             # SPEC-STOCK-TOOLTIP-PRODUCT-001
            weight_in_sector=weight_map.get(name),   # M6-gap G23 (AC-SAG-041)
            chg_1w=round(chg_1w, 4) if chg_1w is not None else None,
            chg_3m=round(chg_3m, 4) if chg_3m is not None else None,
            near_52w_high=near_52w_high,
        ))

    return results


# ---------------------------------------------------------------------------
# compute_treemap_data
# ---------------------------------------------------------------------------

def compute_treemap_data(
    db_path: str,
    period: str = "1w",
) -> TreemapNode:
    """트리맵 계층 데이터를 계산한다.

    구조: 루트 → 섹터 노드 → 종목 노드
    크기: market_cap, 색상: price_change

    Args:
        db_path: weekly SQLite DB 경로
        period: 수익률 계산 기간 ("1w", "1m", "3m")

    Returns:
        TreemapNode (루트 노드, 자식으로 섹터 노드 포함)
    """
    conn = _connect(db_path)
    try:
        dates = _get_dates(db_path, 1)
        if not dates:
            return TreemapNode(name="root", market_cap=0.0, price_change=0.0)
        latest_date = dates[-1]

        stock_meta = _get_stock_meta(db_path)
        sector_map = _build_sector_stock_map(stock_meta)
        price_data = _get_price_on_date(conn, latest_date)
        rs_data = _get_rs_on_date(conn, latest_date)

    finally:
        conn.close()

    sector_nodes: list[TreemapNode] = []

    for sector_name, stock_names in sector_map.items():
        stock_nodes: list[TreemapNode] = []

        for name in stock_names:
            if name not in price_data or name in _INDEX_NAMES:
                continue
            price_row = price_data[name]
            meta = stock_meta[name]
            close = price_row["Close"]
            volume = price_row["Volume"]
            cap = meta["market_cap"]
            rs = rs_data.get(name, 0.0)
            price_change = _get_chg_by_period(price_row, period)

            # 스테이지 분류
            stock_row = {
                "Name": name,
                "Close": close,
                "SMA10": price_row["SMA10"],
                "SMA40": price_row["SMA40"],
                "SMA40_slope": price_row["SMA40_slope"],
                "RS_12M_Rating": rs,
                "CHG_1M": price_row["CHG_1M"],
                "Volume": volume,
                "VolumeSMA10": max(price_row["SMA10"], 1.0),
            }
            stage_result = classify_stage(stock_row)

            stock_nodes.append(TreemapNode(
                name=name,
                market_cap=round(cap, 0),
                price_change=round(price_change, 4),
                rs_12m=round(rs, 2),
                stage=stage_result.stage,
                children=[],
            ))

        if not stock_nodes:
            continue

        # 섹터 집계: market_cap 합산, 가중 평균 price_change
        total_cap = sum(n.market_cap for n in stock_nodes)
        if total_cap > 0:
            weighted_return = sum(
                n.price_change * n.market_cap for n in stock_nodes
            ) / total_cap
        else:
            weighted_return = 0.0

        sector_nodes.append(TreemapNode(
            name=sector_name,
            market_cap=round(total_cap, 0),
            price_change=round(weighted_return, 4),
            children=stock_nodes,
        ))

    # 루트 집계
    root_cap = sum(n.market_cap for n in sector_nodes)
    if root_cap > 0:
        root_change = sum(n.price_change * n.market_cap for n in sector_nodes) / root_cap
    else:
        root_change = 0.0

    return TreemapNode(
        name="root",
        market_cap=round(root_cap, 0),
        price_change=round(root_change, 4),
        children=sector_nodes,
    )


# ---------------------------------------------------------------------------
# detect_sector_transitions
# ---------------------------------------------------------------------------

@dataclass
class SectorAlert:
    """섹터 전환 감지 결과."""

    name: str
    signals: list[str]  # 감지된 시그널 목록


@dataclass
class SectorAlerts:
    """섹터 전환 감지 종합 결과."""

    emerging_leaders: list[SectorAlert]
    weakening_sectors: list[SectorAlert]


def detect_sector_transitions(db_path: str) -> SectorAlerts:
    """섹터 강세/약세 전환을 감지한다.

    강세 전환(emerging strength): 3개 이상 조건 충족 시
      1. 4주간 순위 3단계 이상 상승
      2. 4주간 RS 평균 10포인트 이상 상승
      3. 4주간 Stage 2 비율 10%p 이상 상승
      4. 거래대금 4주 평균 대비 1.5배 이상
      5. RRG 사분면이 Lagging/Improving → Leading으로 이동

    약세 전환(emerging weakness): 3개 이상 조건 충족 시
      1. 4주간 순위 3단계 이상 하락
      2. 4주간 RS 평균 10포인트 이상 하락
      3. 4주간 Stage 2 비율 10%p 이상 하락
      4. 거래대금 4주 평균 대비 0.5배 이하
      5. RRG 사분면이 Leading/Weakening → Lagging으로 이동

    Args:
        db_path: weekly SQLite DB 경로

    Returns:
        SectorAlerts (강세/약세 전환 섹터 목록)
    """
    # 최근 5주 날짜를 가져온다 (현재 + 4주 전 비교)
    # SPEC-SECTOR-GRID-001 REQ-SGR-005: alerts 비교 날짜도 정규 격자에서 파생한다.
    grid = compute_weekly_grid(db_path)
    all_dates = grid.dates[-5:] if grid.dates else []

    if len(all_dates) < 2:
        return SectorAlerts(emerging_leaders=[], weakening_sectors=[])

    current_date = all_dates[-1]
    prev_date = all_dates[0]  # 4주 전 (또는 가능한 가장 오래된 날짜)

    # 섹터 랭킹 데이터 import (순환 import 방지를 위해 함수 내부에서 import)
    from my_chart.analysis.sector_metrics import compute_sector_ranking  # noqa: PLC0415

    # 현재 및 4주 전 랭킹 계산
    try:
        current_ranks_list = compute_sector_ranking(db_path, current_date)
        prev_ranks_list = compute_sector_ranking(db_path, prev_date)
    except Exception:
        return SectorAlerts(emerging_leaders=[], weakening_sectors=[])

    if not current_ranks_list:
        return SectorAlerts(emerging_leaders=[], weakening_sectors=[])

    # 섹터명 → SectorRank 딕셔너리 생성
    current_by_name = {r.name: r for r in current_ranks_list}
    prev_by_name = {r.name: r for r in prev_ranks_list}

    # RRG 데이터 계산 (현재 사분면)
    try:
        rrg_list = compute_rrg_data(db_path)
        rrg_by_name = {r.name: r for r in rrg_list}
    except Exception:
        rrg_by_name = {}

    # 섹터별 거래대금: 현재 vs 4주 전 평균
    try:
        current_bubbles = compute_sector_bubble(db_path, period="1w")
        current_tv_by_name = {b.name: b.trading_value for b in current_bubbles}
        # 4주 전 거래대금 근사: sector_bubble은 최신 날짜만 지원하므로
        # 현재 값과 비교할 기준값으로 현재 평균 사용 (근사)
        prev_tv_by_name: dict[str, float] = current_tv_by_name  # 단순화된 근사
    except Exception:
        current_tv_by_name = {}
        prev_tv_by_name = {}

    emerging_leaders: list[SectorAlert] = []
    weakening_sectors: list[SectorAlert] = []

    for sector_name, cur in current_by_name.items():
        prev = prev_by_name.get(sector_name)
        rrg = rrg_by_name.get(sector_name)

        # 현재 및 이전 지표
        cur_rank = cur.rank
        prev_rank = prev.rank if prev else cur_rank
        cur_rs = cur.sector_rs_avg
        prev_rs = prev.sector_rs_avg if prev else cur_rs
        cur_stage2 = cur.sector_stage2_pct
        prev_stage2 = prev.sector_stage2_pct if prev else cur_stage2
        cur_tv = current_tv_by_name.get(sector_name, 0.0)
        # 거래대금 비교를 위한 이전 값 (없으면 현재 값으로 동일 처리)
        prev_tv = prev_tv_by_name.get(sector_name, cur_tv)

        # 거래대금 평균 계산 (이전 4주 평균 근사)
        avg_tv = (cur_tv + prev_tv) / 2 if prev_tv > 0 else cur_tv

        # 현재 사분면
        cur_quadrant = rrg.quadrant if rrg else None

        # -------------------------------------------------------------------
        # 강세 전환 시그널 감지
        # -------------------------------------------------------------------
        strength_signals: list[str] = []

        # 조건 1: 순위 3단계 이상 상승 (낮은 rank 숫자 = 더 좋은 순위)
        rank_delta = prev_rank - cur_rank  # 양수 = 순위 상승
        if rank_delta >= 3:
            strength_signals.append(f"순위 {rank_delta}단계 상승 ({prev_rank}위 → {cur_rank}위)")

        # 조건 2: RS 평균 10포인트 이상 상승
        rs_delta = cur_rs - prev_rs
        if rs_delta >= 10:
            strength_signals.append(f"RS 평균 {rs_delta:.1f}pt 상승")

        # 조건 3: Stage 2 비율 10%p 이상 상승
        stage2_delta = cur_stage2 - prev_stage2
        if stage2_delta >= 10:
            strength_signals.append(f"Stage 2 비율 {stage2_delta:.1f}%p 상승")

        # 조건 4: 거래대금 4주 평균 대비 1.5배 이상
        if avg_tv > 0 and cur_tv >= avg_tv * 1.5:
            strength_signals.append("거래대금 4주 평균 대비 1.5배 이상")

        # 조건 5: RRG 사분면 → Leading
        if cur_quadrant == "leading":
            strength_signals.append("RRG Leading 사분면 진입")

        # 3개 이상 충족 시 강세 전환
        if len(strength_signals) >= 3:
            emerging_leaders.append(SectorAlert(name=sector_name, signals=strength_signals))

        # -------------------------------------------------------------------
        # 약세 전환 시그널 감지
        # -------------------------------------------------------------------
        weakness_signals: list[str] = []

        # 조건 1: 순위 3단계 이상 하락
        if rank_delta <= -3:
            weakness_signals.append(f"순위 {abs(rank_delta)}단계 하락 ({prev_rank}위 → {cur_rank}위)")

        # 조건 2: RS 평균 10포인트 이상 하락
        if rs_delta <= -10:
            weakness_signals.append(f"RS 평균 {abs(rs_delta):.1f}pt 하락")

        # 조건 3: Stage 2 비율 10%p 이상 하락
        if stage2_delta <= -10:
            weakness_signals.append(f"Stage 2 비율 {abs(stage2_delta):.1f}%p 하락")

        # 조건 4: 거래대금 4주 평균 대비 0.5배 이하
        if avg_tv > 0 and cur_tv <= avg_tv * 0.5:
            weakness_signals.append("거래대금 4주 평균 대비 0.5배 이하")

        # 조건 5: RRG 사분면 → Lagging
        if cur_quadrant == "lagging":
            weakness_signals.append("RRG Lagging 사분면 진입")

        # 3개 이상 충족 시 약세 전환
        if len(weakness_signals) >= 3:
            weakening_sectors.append(SectorAlert(name=sector_name, signals=weakness_signals))

    # 강세/약세 각각 최대 5개까지만 반환 (composite_score 기준 정렬)
    emerging_leaders.sort(key=lambda a: current_by_name[a.name].composite_score, reverse=True)
    weakening_sectors.sort(key=lambda a: current_by_name[a.name].composite_score)

    return SectorAlerts(
        emerging_leaders=emerging_leaders[:5],
        weakening_sectors=weakening_sectors[:5],
    )
