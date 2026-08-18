# coding: utf-8
"""SPEC-SECTOR-METRIC-UNIFY-001 M3 — SectorBubbleItem 4필드 nullable 스키마 관찰자.

스키마만 float → float | None 로 확장했다(값 불변). AC-SMU-028 관찰자:
- model_fields 의 4개 필드 어노테이션이 스칼라-or-None (`float | None` /
  `Optional[float]` 양형 모두 허용)이고 MetricValueModel/dict-모델이 아니다.
- 현재 실응답(프로즌 픽스처 1조합)은 4개 필드가 전부 딕트 아닌 스칼라(float)다.

M4 이후 null 유입이 시작되면 두 번째 단언은 "스칼라-or-None" 으로 완화된다
(이 파일은 M3 시점의 관찰을 고정한다).
"""
from __future__ import annotations

import types
from pathlib import Path
from typing import Any, Iterator, Union, get_args, get_origin
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from backend.schemas.envelope import MetricValueModel
from backend.schemas.sector_advanced import SectorBubbleItem

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "frozen" / "aggregation-2026-08-11"

NULLABLE_FIELDS = ("period_return", "excess_return", "rs_avg", "trading_value")

UNION_ORIGINS = (Union, types.UnionType)


# ---------------------------------------------------------------------------
# 1) AC-SMU-028 관찰자 — 스키마 어노테이션 형태
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field", NULLABLE_FIELDS)
def test_field_annotation_is_scalar_or_none(field: str) -> None:
    """4개 필드는 {float, None} 유니온이어야 한다 — MetricValueModel/dict 불가."""
    ann = SectorBubbleItem.model_fields[field].annotation
    origin = get_origin(ann)
    assert origin in UNION_ORIGINS, (
        f"{field}: 어노테이션이 유니온이 아니다 — {ann!r} "
        f"(MetricValueModel/dict-모델 탑재는 AC-SMU-028 위반)"
    )
    args = set(get_args(ann))
    assert args == {float, type(None)}, (
        f"{field}: 유니온 인수가 {{float, None}} 이 아니다: {args}"
    )
    # 벨트 서스펜더: None 제거 시 잔여 타입이 float 이어야 한다 (dict/모델 혼입 불가).
    non_none = args - {type(None)}
    assert all(t is float for t in non_none), f"{field}: float 외 타입 혼입: {non_none}"


def test_no_dict_model_among_nullable_fields() -> None:
    """4개 필드 전체에서 MetricValueModel(또는 그 어떤 BaseModel) 탑재 부재 단언."""
    for field in NULLABLE_FIELDS:
        ann = SectorBubbleItem.model_fields[field].annotation
        candidates = [a for a in get_args(ann) or (ann,)]
        for candidate in candidates:
            assert not (isinstance(candidate, type) and issubclass(candidate, BaseModel)), (
                f"{field}: BaseModel 서브클래스({candidate.__name__}) 탑재 — "
                f"MetricValueModel 포함 AC-SMU-028 위반"
            )
            assert candidate is not MetricValueModel, f"{field}: MetricValueModel 직접 탑재"
            assert candidate is not dict, f"{field}: dict 탑재"


# ---------------------------------------------------------------------------
# 2) 값 불변 관찰 — 실응답 4필드는 오늘 스칼라(float)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    """집계 프로즌 픽스처에 고정된 TestClient (test_bubble_characterization.py 관용)."""
    from fastapi.testclient import TestClient

    from backend.main import app

    with (
        patch("backend.routers.sectors.WEEKLY_DB_PATH", str(FIXTURE_DIR / "weekly.db")),
        patch("backend.routers.sectors.DAILY_DB_PATH", str(FIXTURE_DIR / "daily.db")),
        patch("backend.routers.stage.WEEKLY_DB_PATH", str(FIXTURE_DIR / "weekly.db")),
        patch("my_chart.registry.SECTORMAP_PATH", str(FIXTURE_DIR / "registry.xlsx")),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    ):
        yield TestClient(app)


def test_live_response_fields_are_scalars(client: Any) -> None:
    """1조합(1w/all) 실응답 — 4개 필드가 딕트 아닌 스칼라(float)임을 관찰 고정."""
    resp = client.get("/api/sectors/bubble", params={"period": "1w", "market": "all"})
    assert resp.status_code == 200, resp.text[:300]
    sectors = resp.json()["sectors"]
    assert sectors, "sectors 비어있음 — 픽스처 경로 이상"
    for sector in sectors:
        for field in NULLABLE_FIELDS:
            value = sector[field]
            assert not isinstance(value, (dict, list)), (
                f"{sector['name']}.{field}: 스칼라여야 한다(딕트 관찰): {value!r}"
            )
            assert isinstance(value, float), (
                f"{sector['name']}.{field}: float 관찰값과 다르다: {value!r}"
            )
