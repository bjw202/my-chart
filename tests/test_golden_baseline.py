# coding: utf-8
"""SPEC-SECTOR-AGGREGATION-001 — AC-SAG-047 (M1 종료 게이트).

골든 baseline `tests/fixtures/golden/pre-sector-ux/` 의 **캡처 완결성**을 기계적으로
검사한다. 이 테스트의 PASS 가 **M1 완료 조건**이며, RED 인 상태에서 M2 착수를 금지한다
(acceptance.md §8.5 — M2 가 구 집계 구현을 교체하는 순간 캡처 창이 영구히 닫힌다).

설계 원칙
---------
* **구조 게이트** — 되돌릴 구현 로직이 없다. 대신 **음성 검증**이 요구된다: 세 파일 중
  하나를 임시 이동한 상태에서 이 테스트가 RED 가 됨을 M1 종료 시 1회 실증하고 기록한다.
* **실측 직렬화 키만 단언한다 (v0.4.1 D12)** — v0.4.0 은 `sector_excess_return_1w/1m/3m`
  와 `total_count` 를 요구했으나 **둘 다 응답에 존재하지 않는다.** 전자는 내부 dataclass
  `my_chart.analysis.sector_metrics.SectorRank` 의 필드명이고(응답 모델은
  `backend/schemas/sector.py` 의 `excess_returns: {w1,m1,m3}`), 후자의 실제 키는
  `distribution.total` 이다. 그 결함의 **재도입 방지**로 캡처 JSON 전체에서
  `sector_excess_return` 문자열이 0건임을 정적으로 단언한다.
* **기준일 고정** — MANIFEST 의 `as_of` 가 `2026-08-11` 이어야 한다(§8 규약 7). 다른
  값이면 baseline 이 다른 기준일에서 떠졌다는 뜻이므로 AC-SAG-045 R1/R4/R5 비교가 무효다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# 경로 · 상수 (acceptance.md AC-SAG-047 본문 리터럴)
# ---------------------------------------------------------------------------

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "golden" / "pre-sector-ux"

RANKING_JSON = "ranking-current.json"
STAGE_JSON = "stage-overview.json"
MANIFEST_MD = "MANIFEST.md"
REQUIRED_FILES = (RANKING_JSON, STAGE_JSON, MANIFEST_MD)

AS_OF = "2026-08-11"
MIN_SECTORS = 10                     # R4 / R5-a 가 유의미하려면 baseline 이 담아야 할 최소 섹터 수

MANIFEST_REQUIRED_KEYS = ("as_of", "captured_at", "git_sha", "fixture", "capture_command")
MANIFEST_FORBIDDEN_PLACEHOLDERS = {"", "TBD", "tbd", "unknown", "UNKNOWN", "None", "none"}

PERIOD_KEYS = ("w1", "m1", "m3")
SECTOR_REQUIRED_KEYS = ("name", "rank", "rs_avg", "composite_score", "returns", "excess_returns")
DISTRIBUTION_KEYS = ("stage1", "stage2", "stage3", "stage4", "total")
BY_SECTOR_KEYS = ("sector", "stage1", "stage2", "stage3", "stage4")

# v0.4.0 결함의 재도입 방지 — 이 문자열들은 직렬화 응답에 존재하지 않는다.
FORBIDDEN_SUBSTRINGS = ("sector_excess_return", "total_count")


# ---------------------------------------------------------------------------
# 로딩 헬퍼
# ---------------------------------------------------------------------------

def _read(name: str) -> str:
    path = GOLDEN_DIR / name
    assert path.is_file(), (
        f"골든 baseline 누락: {path} — M1.0-b 캡처가 수행되지 않았다. "
        f"`python tests/fixtures/golden/pre-sector-ux/capture_baseline.py` 로 캡처한다."
    )
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def ranking() -> dict:
    raw = _read(RANKING_JSON)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - 파싱 실패 경로
        pytest.fail(f"{RANKING_JSON} 파싱 불가: {exc}")


@pytest.fixture(scope="module")
def stage() -> dict:
    raw = _read(STAGE_JSON)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - 파싱 실패 경로
        pytest.fail(f"{STAGE_JSON} 파싱 불가: {exc}")


@pytest.fixture(scope="module")
def manifest() -> dict:
    text = _read(MANIFEST_MD)
    blocks = re.findall(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    assert blocks, f"{MANIFEST_MD} 에 기계 판독 ```yaml 블록이 없다"
    return yaml.safe_load(blocks[0])


# ---------------------------------------------------------------------------
# 1. 산출물 존재
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", REQUIRED_FILES)
def test_baseline_file_exists(filename: str) -> None:
    """3개 산출물이 모두 존재하고 비어 있지 않다."""
    path = GOLDEN_DIR / filename
    assert path.is_file(), f"골든 baseline 파일 누락: {path}"
    assert path.stat().st_size > 0, f"골든 baseline 파일이 비어 있다: {path}"


# ---------------------------------------------------------------------------
# 2. MANIFEST 필수 키
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", MANIFEST_REQUIRED_KEYS)
def test_manifest_key_present_and_non_placeholder(manifest: dict, key: str) -> None:
    """필수 키가 존재하고 값이 빈 문자열·TBD·unknown 이 아니다."""
    assert key in manifest, f"MANIFEST 필수 키 누락: {key}"
    value = manifest[key]
    assert value is not None, f"MANIFEST `{key}` 값이 None"
    assert str(value).strip() not in MANIFEST_FORBIDDEN_PLACEHOLDERS, (
        f"MANIFEST `{key}` 가 플레이스홀더다: {value!r}"
    )


def test_manifest_as_of_is_fixed_reference_date(manifest: dict) -> None:
    """`as_of` 가 사용자 결정으로 고정된 2026-08-11 이다 (§8 규약 7)."""
    assert str(manifest["as_of"]) == AS_OF, (
        f"baseline 기준일 불일치: {manifest['as_of']!r} != {AS_OF!r} — "
        "다른 기준일에서 떠진 baseline 은 R1/R4/R5 비교를 무효화한다."
    )


def test_manifest_fixture_points_at_aggregation_snapshot(manifest: dict) -> None:
    """집계 프로즌 픽스처 식별자를 담는다 — 라이브 DB 캡처 금지의 기록."""
    assert "aggregation-2026-08-11" in str(manifest["fixture"]), (
        f"픽스처 식별자가 집계 스냅샷이 아니다: {manifest['fixture']!r}"
    )


# ---------------------------------------------------------------------------
# 3. ranking-current.json 구조
# ---------------------------------------------------------------------------

def test_ranking_top_level_container(ranking: dict) -> None:
    """최상위에 `date` 와 `sectors` 배열을 담는다 (v0.4.1 D12 실측 키)."""
    assert "date" in ranking, "ranking 최상위에 `date` 없음"
    assert isinstance(ranking.get("sectors"), list), "ranking 최상위 `sectors` 배열 없음"


def test_ranking_date_matches_as_of(ranking: dict) -> None:
    """응답 기준일이 고정 기준일과 일치한다."""
    assert ranking["date"] == AS_OF, f"ranking.date={ranking['date']!r} != {AS_OF!r}"


def test_ranking_sector_count_sufficient(ranking: dict) -> None:
    """R4(상승>하락) · R5-a(등간격) 가 유의미하려면 섹터가 충분해야 한다."""
    count = len(ranking["sectors"])
    assert count >= MIN_SECTORS, f"sectors 엔트리 수 {count} < {MIN_SECTORS}"


@pytest.mark.parametrize("key", SECTOR_REQUIRED_KEYS)
def test_ranking_every_sector_has_key(ranking: dict, key: str) -> None:
    """R1(`rank`) · R4/R5(`rs_avg`·`composite_score`) 가 읽는 키가 **모든** 엔트리에 있다."""
    missing = [i for i, s in enumerate(ranking["sectors"]) if key not in s]
    assert not missing, f"`{key}` 누락 엔트리 인덱스: {missing}"


@pytest.mark.parametrize("container", ["returns", "excess_returns"])
@pytest.mark.parametrize("period", PERIOD_KEYS)
def test_ranking_three_period_values_present(ranking: dict, container: str, period: str) -> None:
    """세 기간이 `sectors[i].{returns,excess_returns}.{w1,m1,m3}` 형태로 모든 엔트리에 있다."""
    missing = [
        i for i, s in enumerate(ranking["sectors"])
        if not isinstance(s.get(container), dict) or period not in s[container]
    ]
    assert not missing, f"`{container}.{period}` 누락 엔트리 인덱스: {missing}"


# ---------------------------------------------------------------------------
# 4. stage-overview.json 구조
# ---------------------------------------------------------------------------

def test_stage_top_level_container(stage: dict) -> None:
    assert isinstance(stage.get("distribution"), dict), "stage 최상위 `distribution` 없음"
    assert isinstance(stage.get("by_sector"), list), "stage 최상위 `by_sector` 배열 없음"


@pytest.mark.parametrize("key", DISTRIBUTION_KEYS)
def test_stage_distribution_key(stage: dict, key: str) -> None:
    """`distribution` 5개 키 — 실제 키는 `total` 이다 (`total_count` 아님, D12)."""
    assert key in stage["distribution"], f"distribution 키 누락: {key}"


@pytest.mark.parametrize("key", BY_SECTOR_KEYS)
def test_stage_by_sector_entry_key(stage: dict, key: str) -> None:
    assert stage["by_sector"], "by_sector 배열이 비어 있다"
    missing = [i for i, e in enumerate(stage["by_sector"]) if key not in e]
    assert not missing, f"by_sector `{key}` 누락 엔트리 인덱스: {missing}"


# ---------------------------------------------------------------------------
# 5. D12 결함 재도입 방지 (정적 문자열 단언)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", [RANKING_JSON, STAGE_JSON])
@pytest.mark.parametrize("forbidden", FORBIDDEN_SUBSTRINGS)
def test_no_dataclass_field_names_leaked(filename: str, forbidden: str) -> None:
    """`sector_excess_return` · `total_count` 는 직렬화 응답에 존재하지 않는다.

    존재하면 응답 모델을 우회해 dataclass 를 직접 덤프했다는 뜻이며, AC-SAG-047 이
    v0.4.0 에서 잘못된 키를 요구했던 결함이 되돌아온 것이다.
    """
    raw = _read(filename)
    assert raw.count(forbidden) == 0, (
        f"{filename} 에 `{forbidden}` 이 {raw.count(forbidden)}건 존재한다 — "
        "직렬화 응답이 아니라 내부 dataclass 를 캡처했을 가능성이 높다."
    )
