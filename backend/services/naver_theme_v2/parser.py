"""JSON dict → 정규화된 list/dict. 필드명 access only (§13-1 교훈)."""

from typing import Optional


def parse_theme_list(response_json: dict) -> list[dict]:
    """list endpoint 응답을 V1 형식의 dict 리스트로 변환.

    필드명 access only — positional indexing 금지 (§13-1).
    """
    if not response_json.get("isSuccess"):
        return []

    sectors = response_json.get("result", {}).get("sectors", [])
    parsed = []
    for sec in sectors:
        # sectorCode는 string-of-int — int 정규화 (V1 theme_id: int 호환)
        theme_id = int(sec["sectorCode"])
        parsed.append(
            {
                "theme_id": theme_id,
                "theme_name": sec["sectorName"],
                # V1 analyzer는 change_pct 컬럼 사용 — 모바일 changeRate와 매핑
                "change_pct": float(sec["changeRate"]),
                # V1 analyzer breadth_ratio: up_count / (up + flat + down)
                "up_count": int(sec["risingCount"]),
                "flat_count": int(sec["unChangedCount"]),
                "down_count": int(sec["fallingCount"]),
                # NOTE: list 응답의 sectorDescription은 항상 null (research.md §2.1)
                "theme_description": None,
                # V1 호환 alias — change_rate도 노출 (REQ-NT2-008)
                "change_rate": float(sec["changeRate"]),
                # V1 analyzer는 change_pct_3d가 필요하나 모바일 API 미제공 → 0.0 기본값
                "change_pct_3d": 0.0,
            }
        )
    return parsed


def parse_theme_detail(response_json: dict, theme_id: int) -> Optional[dict]:
    """Detail endpoint 응답을 V1 stocks_df row dict 리스트로 변환."""
    if not response_json.get("isSuccess"):
        return None

    result = response_json.get("result", {})
    # nullable — research.md §2.2
    theme_description: Optional[str] = result.get("sectorDescription")
    theme_name: str = result.get("sectorName", "")

    items_parsed = []
    for item in result.get("items", []):
        # fluctuationsRatio는 string-of-float (research.md §2.2)
        raw_ratio = item.get("fluctuationsRatio")
        change_pct = float(raw_ratio) if raw_ratio is not None else 0.0

        # marketValue는 원 단위 (research.md §2.3) — nullable
        raw_mv = item.get("marketValue")
        market_cap: Optional[int] = int(raw_mv) if raw_mv is not None else None

        items_parsed.append(
            {
                "theme_id": theme_id,
                "theme_name": theme_name,
                # V1 analyzer 컬럼명: stock_code, stock_name (build_leaders, build_multi_theme_stocks 참조)
                "stock_code": item["itemCode"],
                "stock_name": item["name"],
                # V1 analyzer 컬럼명: change_pct
                "change_pct": change_pct,
                # V1 호환 alias
                "change_rate": change_pct,
                "code": item["itemCode"],
                "name": item["name"],
                "market_cap": market_cap,
                # V1 컬럼 호환 (build_leaders volume, trade_value)
                "volume": int(item["accumulatedTradingVolume"]) if item.get("accumulatedTradingVolume") is not None else 0,
                "trade_value": int(item["accumulatedTradingValue"]) if item.get("accumulatedTradingValue") is not None else 0,
                # V1 inclusion_reason 자리에 V2 description 매핑 (REQ-NT2-005)
                "inclusion_reason": item.get("description"),
                # V2 신규 컬럼 (REQ-NT2-005)
                "stock_description": item.get("description"),
            }
        )

    return {
        "theme_id": theme_id,
        "theme_description": theme_description,
        "items": items_parsed,
    }
