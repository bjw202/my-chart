# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 M1.1 — 응답 계약 + 결측 3상태 표현.

수용 기준: **AC-SAG-036**(응답 공통 스키마 10키) · **AC-SAG-038**(결측 3상태 구분) ·
**AC-SAG-043**(신규 필드 전 구간 전파 4단계) · **AC-SAG-008**(커버리지 필드 동반).

D6 결측 표현 형태 결정 (plan.md §1 D6 — M1.1 소관)
---------------------------------------------------
**`{value, reason}` 객체 형태**를 채택한다(형제 `*_reason` 필드 형태 기각). 근거는
`E2 결정 기록`(progress.md §E.2)에 남긴다. 요약:

1. AC-SAG-038 본문이 세 상태를 `{value: null, reason: "missing"}` / `{value: 0.0}` /
   `{value: null, reason: "insufficient"}` 로 **직접 명시**한다 — 형제 필드 형태는
   `{"x": null, "x_reason": "missing"}` 로 직렬화되어 AC 본문과 형태가 갈린다.
2. 형제 필드는 지표당 키가 2개로 늘고 **등록을 한쪽만 빠뜨릴 수 있다** — Lesson #4
   (파생 구조가 원본 갱신을 자동 반영하지 않아 누락된 선례)의 실패 형태 그대로다.
   객체 형태는 값과 사유가 **구조적으로 분리 불가능**하다.
3. 따라서 결측 자리에 `0` / `0.0` / `50.0` 을 넣으려면 `MetricValue(value=0.0)` 를
   **의도적으로 써야** 하며, 누락으로는 발생할 수 없다(§9.1 치환 금지의 구조적 보장).

`as_of` 명시 고정 — §8.4 규약 8
--------------------------------
집계 프로즌 픽스처(`aggregation-2026-08-11`) 위에서 실행하며 `as_of=None`(구현 기본값
→ `date.today()`) 의존을 금지한다. 현행 엔드포인트는 무파라미터이므로 기준일은 픽스처
최신 정규 바로 고정되며, 응답 `as_of_date == "2026-08-11"` 단언으로 실측 확인한다.
"""
from __future__ import annotations

import json
from dataclasses import fields as dataclass_fields
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import patch

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "frozen" / "aggregation-2026-08-11"
WEEKLY_DB = FIXTURE_DIR / "weekly.db"
DAILY_DB = FIXTURE_DIR / "daily.db"
REGISTRY = FIXTURE_DIR / "registry.xlsx"

AS_OF = "2026-08-11"

# AC-SAG-036 — 전 엔드포인트 공통 10키
ENVELOPE_KEYS = (
    "as_of_date",
    "as_of_is_partial_week",
    "return_window_days",
    "market_filter",
    "weight_cap",
    "grid_version",
    "benchmark",
    "data",
    "excluded",
    "warnings",
)
RETURN_WINDOW_LABELS = {"1w", "1m", "3m"}

# AC-SAG-008 — data[] 항목의 커버리지 4필드
COVERAGE_FIELDS = ("member_count", "valid_count", "coverage_ratio", "cap_coverage_ratio")

# AC-SAG-043 — 본 SPEC이 추가한 필드 목록(상수 정의 → 4단계 루프 단언)
NEW_AGGREGATE_FIELDS = (
    "member_count",
    "valid_count",
    "coverage",
    "valid_counts",
    "coverage_ratio",
    "cap_coverage_ratio",
    "effective_n",
    "weight_cap",
    "capped_members",
    "cap_weighted_available",
    "low_confidence",
)


# ---------------------------------------------------------------------------
# 픽스처 고정 클라이언트
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> Iterator[Any]:
    """집계 프로즌 픽스처에 고정된 TestClient.

    `get_sector_registry()` 는 경로 인자가 없고 라이브 `Input/sectormap-original.xlsx`
    를 lazy-load 하므로(`my_chart/registry.py:122`) 모듈 상수와 lazy 캐시를 함께 눌러
    픽스처 사본을 읽게 한다.
    """
    from fastapi.testclient import TestClient

    from backend.main import app

    with (
        patch("backend.routers.sectors.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("backend.routers.sectors.DAILY_DB_PATH", str(DAILY_DB)),
        patch("backend.routers.stage.WEEKLY_DB_PATH", str(WEEKLY_DB)),
        patch("my_chart.registry.SECTORMAP_PATH", str(REGISTRY)),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    ):
        yield TestClient(app)


@pytest.fixture(scope="module")
def sector_name(client: Any) -> str:
    """픽스처에 실재하는 섹터명 하나 — 경로 파라미터 엔드포인트용."""
    resp = client.get("/api/sectors/ranking")
    assert resp.status_code == 200, resp.text[:400]
    body = resp.json()
    assert body["data"], "ranking data[] 가 비어 있다 — 경로 파라미터 케이스를 만들 수 없다"
    return str(body["data"][0]["name"])


@pytest.fixture(scope="module")
def endpoints(sector_name: str) -> tuple[str, ...]:
    """AC-SAG-036 이 열거한 7개 엔드포인트."""
    return (
        "/api/sectors/ranking",
        "/api/sectors/bubble",
        "/api/sectors/rrg",
        "/api/sectors/history",
        "/api/stage/overview",
        f"/api/sectors/{sector_name}/detail",
        f"/api/sectors/{sector_name}/bubble",
    )


@pytest.fixture(scope="module")
def ranking_body(client: Any) -> dict:
    resp = client.get("/api/sectors/ranking")
    assert resp.status_code == 200, resp.text[:400]
    return resp.json()


# ---------------------------------------------------------------------------
# AC-SAG-036 — 응답 공통 스키마
# ---------------------------------------------------------------------------

def test_ac_sag_036_all_endpoints_carry_envelope_keys(
    client: Any, endpoints: tuple[str, ...]
) -> None:
    """AC-SAG-036 — 7개 엔드포인트 응답이 공통 10키를 모두 갖는다(엔드포인트별 루프)."""
    for path in endpoints:
        resp = client.get(path)
        assert resp.status_code == 200, f"{path} → {resp.status_code}: {resp.text[:300]}"
        body = resp.json()
        missing = [k for k in ENVELOPE_KEYS if k not in body]
        assert not missing, f"AC-SAG-036 위반 — {path} 응답에 공통 키 누락: {missing}"


def test_ac_sag_036_excluded_key_always_present_even_when_empty(
    client: Any, endpoints: tuple[str, ...]
) -> None:
    """AC-SAG-036 — `excluded` 는 빈 배열일 수 있으나 **키 자체는 항상 존재**한다."""
    for path in endpoints:
        body = client.get(path).json()
        assert "excluded" in body, f"{path}: excluded 키 부재"
        assert isinstance(body["excluded"], list), f"{path}: excluded 가 배열이 아니다"


def test_ac_sag_036_return_window_days_shape(
    client: Any, endpoints: tuple[str, ...]
) -> None:
    """AC-SAG-036 — `return_window_days` 는 `period` 와 무관하게 항상 3키를 갖는다.

    **값 단언은 AC-SAG-046(M3) 소관**이므로 여기서는 키 존재·모양만 단언한다
    (plan.md M1.1: "키 존재·모양은 M1.1 소관, 값의 실측 일치는 앵커가 붙는 M3 소관").
    """
    for path in endpoints:
        rwd = client.get(path).json()["return_window_days"]
        assert isinstance(rwd, dict), f"{path}: return_window_days 가 객체가 아니다"
        assert set(rwd) == RETURN_WINDOW_LABELS, (
            f"{path}: return_window_days 키 {sorted(rwd)} != {sorted(RETURN_WINDOW_LABELS)}")


def test_ac_sag_036_as_of_pinned_to_fixture_bar(ranking_body: dict) -> None:
    """§8.4 규약 8 — 기준일이 픽스처 최신 정규 바(2026-08-11)로 고정됐다."""
    assert ranking_body["as_of_date"] == AS_OF, (
        f"as_of_date {ranking_body['as_of_date']!r} != {AS_OF!r} — "
        "픽스처 고정이 풀렸거나 as_of=None(date.today()) 에 의존하고 있다")


# ---------------------------------------------------------------------------
# AC-SAG-038 — 결측 3상태 구분
# ---------------------------------------------------------------------------

def test_ac_sag_038_three_states_are_distinguishable() -> None:
    """AC-SAG-038 — (a) 원천 값 없음 / (b) 실제 0 / (c) 산출 조건 미달 이 구분된다."""
    from my_chart.analysis.aggregate_types import (
        REASON_INSUFFICIENT,
        REASON_MISSING,
        insufficient,
        missing,
        present,
    )

    a, b, c = missing(), present(0.0), insufficient()

    assert (a.value, a.reason) == (None, REASON_MISSING)
    assert (b.value, b.reason) == (0.0, None)
    assert (c.value, c.reason) == (None, REASON_INSUFFICIENT)

    # 세 상태가 서로 다른 직렬화 형태를 갖는다 — 하나라도 겹치면 구분 불가.
    forms = {json.dumps(x.to_dict(), sort_keys=True) for x in (a, b, c)}
    assert len(forms) == 3, f"AC-SAG-038 위반 — 3상태가 구분되지 않는다: {forms}"


def test_ac_sag_038_zero_substitution_is_structurally_impossible() -> None:
    """§9.1 — 결측에 0 / 0.0 / 50.0 을 치환하면 `reason` 과 동시에 성립할 수 없다."""
    from my_chart.analysis.aggregate_types import MetricValue

    for banned in (0, 0.0, 50.0):
        with pytest.raises(ValueError):
            MetricValue(value=banned, reason="missing")


def _metric_slots(node: Any, path: str = "$") -> Iterator[tuple[str, dict]]:
    """응답 JSON 전체를 훑어 `{value, reason}` 형태 노드를 모두 수확한다."""
    if isinstance(node, dict):
        if set(node) >= {"value", "reason"} and len(node) == 2:
            yield path, node
        for k, v in node.items():
            yield from _metric_slots(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _metric_slots(v, f"{path}[{i}]")


def test_ac_sag_038_no_zero_in_missing_slot_across_full_response(
    client: Any, endpoints: tuple[str, ...]
) -> None:
    """AC-SAG-038 — 응답 JSON **전체 스캔**: 결측 자리에 0/0.0/50.0 이 나타나지 않는다."""
    banned = (0, 0.0, 50.0)
    scanned = 0
    for path in endpoints:
        body = client.get(path).json()
        for where, slot in _metric_slots(body, path):
            scanned += 1
            if slot["reason"] is not None:
                assert slot["value"] is None, (
                    f"AC-SAG-038 위반 — 결측({slot['reason']}) 자리에 값 {slot['value']!r}: {where}")
                assert slot["value"] not in banned, f"치환 흔적: {where}"
    assert scanned > 0, "스캔된 결측 표현 슬롯이 0개다 — 스캔 자체가 무효(무게이팅)"


# ---------------------------------------------------------------------------
# AC-SAG-043 — 신규 필드 전 구간 전파 (4단계)
# ---------------------------------------------------------------------------

def test_ac_sag_043_stage1_dataclass(ranking_body: dict) -> None:
    """1단계 — 집계 dataclass `SectorAggregate` 가 신규 필드를 갖는다."""
    from my_chart.analysis.aggregate_types import SectorAggregate

    names = {f.name for f in dataclass_fields(SectorAggregate)}
    missing_fields = [f for f in NEW_AGGREGATE_FIELDS if f not in names]
    assert not missing_fields, f"1단계(dataclass) 누락: {missing_fields}"


def test_ac_sag_043_stage2_service_conversion() -> None:
    """2단계 — 서비스 변환 결과 인스턴스가 신규 필드를 갖는다."""
    from backend.services.sector_ranking_service import get_sector_ranking

    with (
        patch("my_chart.registry.SECTORMAP_PATH", str(REGISTRY)),
        patch("my_chart.registry._df_sector", None),
        patch("my_chart.registry._df_stock", None),
    ):
        resp = get_sector_ranking(str(WEEKLY_DB), daily_db_path=str(DAILY_DB), as_of=AS_OF)

    assert resp.data, "서비스 변환 결과 data[] 가 비어 있다"
    item = resp.data[0]
    missing_fields = [f for f in NEW_AGGREGATE_FIELDS if not hasattr(item, f)]
    assert not missing_fields, f"2단계(서비스 변환) 누락: {missing_fields}"


def test_ac_sag_043_stage3_pydantic_model_fields() -> None:
    """3단계 — Pydantic `model_fields` 에 신규 필드가 등록돼 있다."""
    from backend.schemas.envelope import SectorAggregateModel

    names = set(SectorAggregateModel.model_fields)
    missing_fields = [f for f in NEW_AGGREGATE_FIELDS if f not in names]
    assert not missing_fields, f"3단계(model_fields) 누락: {missing_fields}"


def test_ac_sag_043_stage4_json_response(ranking_body: dict) -> None:
    """4단계 — 실제 JSON 응답 `data[]` 항목이 신규 필드를 갖는다."""
    assert ranking_body["data"], "4단계: data[] 가 비어 있다(단언이 공허해진다)"
    for i, item in enumerate(ranking_body["data"]):
        missing_fields = [f for f in NEW_AGGREGATE_FIELDS if f not in item]
        assert not missing_fields, f"4단계(JSON) data[{i}] 누락: {missing_fields}"


# ---------------------------------------------------------------------------
# AC-SAG-008 — 커버리지 필드 동반 (불변식 AG-6)
# ---------------------------------------------------------------------------

def test_ac_sag_008_coverage_fields_on_every_data_item(ranking_body: dict) -> None:
    """AC-SAG-008 — `data[]` 의 **모든** 항목이 커버리지 4필드를 갖는다(누락 0건)."""
    assert ranking_body["data"], "data[] 가 비어 있어 AG-6 단언이 공허하다"
    for i, item in enumerate(ranking_body["data"]):
        missing_fields = [f for f in COVERAGE_FIELDS if f not in item]
        assert not missing_fields, f"AG-6 위반 — data[{i}] 커버리지 필드 누락: {missing_fields}"


def test_ac_sag_008_coverage_is_per_metric_with_top_level_minimum(ranking_body: dict) -> None:
    """O-A6 — `coverage: {rs, nh, stage, chg, trading_value}` + 최상위 최소값,
    `valid_counts` 동형."""
    assert ranking_body["data"], "data[] 가 비어 있다"
    buckets = {"rs", "nh", "stage", "chg", "trading_value"}
    for i, item in enumerate(ranking_body["data"]):
        assert set(item["coverage"]) == buckets, (
            f"data[{i}].coverage 키 {sorted(item['coverage'])} != {sorted(buckets)}")
        assert set(item["valid_counts"]) == buckets, (
            f"data[{i}].valid_counts 키가 coverage 와 동형이 아니다: "
            f"{sorted(item['valid_counts'])}")


# ---------------------------------------------------------------------------
# 하위 호환 (plan.md §1 D4) — 추가 전용 optional 필드
# ---------------------------------------------------------------------------

def test_backward_compatible_legacy_keys_preserved(client: Any, sector_name: str) -> None:
    """D4 — 기존 프론트엔드가 읽던 키가 그대로 남아 있다(추가 전용 확장)."""
    expected = {
        "/api/sectors/ranking": ("date", "sectors"),
        "/api/sectors/bubble": ("date", "period", "market", "sectors"),
        "/api/sectors/rrg": ("date", "sectors", "kospi"),
        "/api/sectors/history": ("weeks", "sectors"),
        "/api/stage/overview": ("distribution", "by_sector", "stage2_candidates", "all_stocks"),
        f"/api/sectors/{sector_name}/detail": ("sector_name", "sub_sectors", "top_stocks"),
        f"/api/sectors/{sector_name}/bubble": ("date", "sector_name", "period", "stocks"),
    }
    for path, keys in expected.items():
        body = client.get(path).json()
        gone = [k for k in keys if k not in body]
        assert not gone, f"하위 호환 위반 — {path} 기존 키 소실: {gone}"
