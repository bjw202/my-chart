"""naver_theme_v2.parser 단위 테스트 — AC-3, AC-4.

JSON fixture 기반. 네트워크 호출 없음.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

for _mod in ("pykrx", "pykrx.stock"):
    if _mod not in sys.modules:
        import types
        sys.modules[_mod] = types.ModuleType(_mod)

from backend.services.naver_theme_v2.parser import parse_theme_list, parse_theme_detail

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "naver_theme_v2"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# parse_theme_list
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_theme_list_basic():
    """list_synthetic.json → list[dict] 반환. theme_id int, theme_name str, sectorDescription 없음."""
    data = _load("list_synthetic.json")
    result = parse_theme_list(data)

    assert isinstance(result, list)
    assert len(result) == 5

    first = result[0]
    assert isinstance(first["theme_id"], int)
    assert first["theme_id"] == 178
    assert isinstance(first["theme_name"], str)
    assert first["theme_name"] == "전선"

    # list 응답의 sectorDescription은 항상 null (research.md §2.1)
    for theme in result:
        assert "theme_description" in theme
        assert theme["theme_description"] is None


@pytest.mark.unit
def test_parse_theme_list_change_rates():
    """changeRate 값이 float으로 정규화되어 있는지 검증."""
    data = _load("list_synthetic.json")
    result = parse_theme_list(data)

    change_rates = {t["theme_id"]: t["change_rate"] for t in result}
    assert change_rates[178] == pytest.approx(9.2)
    assert change_rates[200] == pytest.approx(7.5)
    assert change_rates[503] == pytest.approx(-2.5)
    assert change_rates[402] == pytest.approx(0.0)


@pytest.mark.unit
def test_parse_theme_list_isSuccess_false():
    """isSuccess=false → 빈 list 반환."""
    data = _load("error_5xx_response.json")
    result = parse_theme_list(data)
    assert result == []


# ---------------------------------------------------------------------------
# parse_theme_detail — with description
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_parse_theme_detail_with_description():
    """detail_synthetic.json → theme_description non-null, items[0].stock_description non-null."""
    data = _load("detail_synthetic.json")
    result = parse_theme_detail(data, theme_id=178)

    assert result is not None
    assert result["theme_description"] is not None
    assert isinstance(result["theme_description"], str)
    assert "전선" in result["theme_description"]

    items = result["items"]
    assert len(items) == 3
    # 첫 번째 종목은 description이 있음
    assert items[0]["stock_description"] is not None
    assert isinstance(items[0]["stock_description"], str)


@pytest.mark.unit
def test_parse_theme_detail_null_stock_description():
    """items[].description=null 종목이 있을 때 stock_description=None으로 처리 (AC-4)."""
    data = _load("detail_synthetic.json")
    result = parse_theme_detail(data, theme_id=178)

    assert result is not None
    items = result["items"]

    # 두 번째 종목(테스트종목B)는 description=null
    null_desc_items = [it for it in items if it["stock_description"] is None]
    assert len(null_desc_items) >= 1, "description=null 종목이 1개 이상 있어야 함"


@pytest.mark.unit
def test_parse_theme_detail_null_description():
    """sectorDescription=null 케이스: theme_description=None 처리 (AC-3)."""
    # list 응답의 sectorDescription은 null이지만, detail 응답에서도 null인 경우 대비
    data = _load("detail_synthetic.json")
    # result를 복사하여 sectorDescription을 null로 수정
    import copy
    modified = copy.deepcopy(data)
    modified["result"]["sectorDescription"] = None

    result = parse_theme_detail(modified, theme_id=178)
    assert result is not None
    assert result["theme_description"] is None


@pytest.mark.unit
def test_parse_theme_detail_isSuccess_false():
    """isSuccess=false → None 반환."""
    data = _load("error_5xx_response.json")
    result = parse_theme_detail(data, theme_id=178)
    assert result is None


@pytest.mark.unit
def test_parse_theme_detail_items_fields():
    """파싱된 items에 필수 컬럼이 존재하는지 검증."""
    data = _load("detail_synthetic.json")
    result = parse_theme_detail(data, theme_id=178)

    assert result is not None
    for item in result["items"]:
        assert "theme_id" in item
        assert "code" in item
        assert "name" in item
        assert "market_cap" in item
        assert "change_rate" in item
        assert "inclusion_reason" in item
        assert "stock_description" in item
        assert item["theme_id"] == 178
