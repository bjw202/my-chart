"""SPEC-AI-REPORT-002 Phase B: 5-소스 병렬 수집 + /tmp 스테이징 테스트.

대상 모듈: backend/services/deep_research_collector.py
TDD 방법론: RED-GREEN-REFACTOR

테스트 범위:
- 소스별 수집 함수 (Perplexity, Brave, Tavily, Naver, YouTube)
- 실패 유형 분류 (timeout, http_error, missing_key)
- 최소 소스 게이트 (2/5 성공 필요)
- 스테이징 디렉토리 생성 및 파일 구조
- 파서 어댑터 (merge_results.py 포팅)
- 중복 제거
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import re
import sys
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx


# ─────────────────────────────────────────────────────────────────────────────
# 모듈 격리 로드 헬퍼
# ─────────────────────────────────────────────────────────────────────────────


def _load_collector_module():
    """deep_research_collector 모듈을 격리 방식으로 로드.

    backend/__init__.py → chart_service → my_chart 연쇄 import 회피.
    my_chart.registry 스텁 불필요 (collector는 my_chart 미사용).

    frozen=True dataclass를 위해 sys.modules에 먼저 등록.
    """
    svc_path = Path(__file__).parent.parent / "services" / "deep_research_collector.py"
    module_name = "backend.services.deep_research_collector"
    spec = importlib.util.spec_from_file_location(module_name, svc_path)
    assert spec and spec.loader, f"모듈 로드 실패: {svc_path}"
    mod = importlib.util.module_from_spec(spec)
    # frozen=True dataclass가 sys.modules[__module__].__dict__를 참조하므로 사전 등록
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# 모듈 전역 로드 (한 번만)
_MOD = _load_collector_module()

collect_all_sources = _MOD.collect_all_sources
create_staging_directory = _MOD.create_staging_directory
SourceResult = _MOD.SourceResult
CollectionResult = _MOD.CollectionResult
_normalize_brave = _MOD._normalize_brave
_normalize_tavily = _MOD._normalize_tavily
_normalize_naver = _MOD._normalize_naver
_normalize_youtube = _MOD._normalize_youtube
_deduplicate_by_url = _MOD._deduplicate_by_url
_strip_think_blocks = _MOD._strip_think_blocks


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_env_all_keys(monkeypatch):
    """모든 API 키 환경변수 설정."""
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test-key")
    monkeypatch.setenv("BRAVE_API_KEY", "brave-test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test-key")
    monkeypatch.setenv("NAVER_CLIENT_ID", "naver-test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "naver-test-secret")
    monkeypatch.setenv("YOUTUBE_API_KEY", "yt-test-key")


@pytest.fixture()
def brave_response_json():
    """Brave 검색 응답 픽스처."""
    return {
        "web": {
            "results": [
                {
                    "title": "삼성전자 실적 분석",
                    "url": "https://example.com/samsung",
                    "description": "삼성전자 3분기 실적이 예상치를 상회했습니다.",
                },
                {
                    "title": "Samsung Electronics Q3 Results",
                    "url": "https://example.com/samsung-en",
                    "description": "Samsung beat Q3 expectations.",
                },
            ]
        }
    }


@pytest.fixture()
def tavily_response_json():
    """Tavily 검색 응답 픽스처."""
    return {
        "results": [
            {
                "title": "Samsung stock analysis",
                "url": "https://example.com/tavily-samsung",
                "content": "Deep analysis of Samsung Electronics.",
                "score": 0.95,
            }
        ],
        "answer": "Samsung Electronics shows strong fundamentals.",
    }


@pytest.fixture()
def perplexity_response_json():
    """Perplexity 응답 픽스처 (think 블록 포함)."""
    return {
        "choices": [
            {
                "message": {
                    "content": (
                        "<think>내부 추론: 삼성전자의 최근 실적을 분석해야 한다.</think>"
                        "삼성전자(005930)는 현재 반도체 사이클 회복 국면에 있습니다."
                    )
                }
            }
        ],
        "citations": ["https://citation1.com", "https://citation2.com"],
    }


@pytest.fixture()
def naver_response_json():
    """Naver 검색 응답 픽스처 (HTML 태그 포함)."""
    return {
        "items": [
            {
                "title": "<b>삼성전자</b> 주가 분석",
                "link": "https://naver.example.com/samsung",
                "description": "<b>삼성전자</b> 주가가 강세를 보이고 있습니다.",
            }
        ]
    }


@pytest.fixture()
def youtube_response_json():
    """YouTube 검색 응답 픽스처."""
    return {
        "items": [
            {
                "id": {"videoId": "abc123"},
                "snippet": {
                    "title": "삼성전자 주가 전망",
                    "description": "삼성전자의 향후 주가 전망을 분석합니다.",
                    "channelTitle": "주식분석TV",
                    "publishedAt": "2026-04-01T00:00:00Z",
                    "thumbnails": {
                        "medium": {"url": "https://img.youtube.com/vi/abc123/mqdefault.jpg"}
                    },
                },
            }
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1: 소스별 수집 함수 단위 테스트
# ─────────────────────────────────────────────────────────────────────────────


# SPEC-AI-REPORT-003: test_collect_perplexity_nonstreaming 제거됨 (Perplexity 완전 대체).
# Codex 어댑터 테스트는 test_codex_cli_runner.py 및 SECTION 3b (test_collect_codex_*) 참고.


@pytest.mark.asyncio
async def test_collect_brave(mock_env_all_keys, brave_response_json):
    """Brave Search GET 요청 + 정규화 결과 검증."""
    with respx.mock:
        route = respx.get(
            url__startswith="https://api.search.brave.com/res/v1/web/search"
        ).respond(json=brave_response_json, status_code=200)
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_brave("005930", "삼성전자", client=client)

    assert isinstance(result, SourceResult)
    assert result.success is True
    assert result.name == "brave"
    assert isinstance(result.data, list)
    assert len(result.data) >= 1
    # X-Subscription-Token 헤더 검증
    request = route.calls.last.request
    assert request.headers.get("x-subscription-token") == "brave-test-key"
    # count=20 파라미터 확인
    assert "count=20" in str(request.url)


@pytest.mark.asyncio
async def test_collect_tavily(mock_env_all_keys, tavily_response_json):
    """Tavily POST 요청 + advanced depth + include_answer 검증."""
    with respx.mock:
        route = respx.post("https://api.tavily.com/search").respond(
            json=tavily_response_json, status_code=200
        )
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_tavily("005930", "삼성전자", client=client)

    assert isinstance(result, SourceResult)
    assert result.success is True
    assert result.name == "tavily"
    request = route.calls.last.request
    body = json.loads(request.content)
    assert body.get("search_depth") == "advanced"
    assert body.get("max_results") == 20
    # include_answer는 "advanced" 문자열 또는 True
    assert body.get("include_answer") in ("advanced", True, "true")


@pytest.mark.asyncio
async def test_collect_naver(mock_env_all_keys, naver_response_json):
    """Naver 웹 검색 GET + 한국어 쿼리 + 헤더 검증."""
    with respx.mock:
        respx.get(
            url__startswith="https://openapi.naver.com/v1/search/"
        ).respond(json=naver_response_json, status_code=200)
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_naver("005930", "삼성전자", client=client)

    assert isinstance(result, SourceResult)
    assert result.success is True
    assert result.name == "naver"
    # 결과는 리스트 (webkr 결과) 또는 dict 포함 리스트
    assert result.data is not None


@pytest.mark.asyncio
async def test_collect_youtube(mock_env_all_keys, youtube_response_json):
    """YouTube Data API v3 GET + snippet + type=video 검증."""
    with respx.mock:
        route = respx.get(
            url__startswith="https://www.googleapis.com/youtube/v3/search"
        ).respond(json=youtube_response_json, status_code=200)
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_youtube("005930", "삼성전자", client=client)

    assert isinstance(result, SourceResult)
    assert result.success is True
    assert result.name == "youtube"
    request = route.calls.last.request
    url_str = str(request.url)
    assert "part=snippet" in url_str
    assert "type=video" in url_str
    assert "maxResults=10" in url_str


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2: 실패 처리 테스트
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_source_timeout_counted_as_failure(mock_env_all_keys):
    """httpx.TimeoutException → SourceResult.success=False, error_type='timeout'."""
    with respx.mock:
        respx.get(url__startswith="https://api.search.brave.com").mock(
            side_effect=httpx.TimeoutException("timed out")
        )
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_brave("005930", "삼성전자", client=client)

    assert isinstance(result, SourceResult)
    assert result.success is False
    assert result.error_type == "timeout"
    assert result.name == "brave"


@pytest.mark.asyncio
async def test_source_http_error_counted_as_failure(mock_env_all_keys):
    """HTTP 500 응답 → SourceResult.success=False, error_type='http_error'."""
    with respx.mock:
        respx.get(
            url__startswith="https://api.search.brave.com"
        ).respond(status_code=500, json={"error": "internal server error"})
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_brave("005930", "삼성전자", client=client)

    assert isinstance(result, SourceResult)
    assert result.success is False
    assert result.error_type == "http_error"


@pytest.mark.asyncio
async def test_missing_api_key_counted_as_failure(monkeypatch):
    """BRAVE_API_KEY 미설정 → 해당 소스 실패, error_type='missing_key', 예외 없음."""
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    # 다른 키는 설정
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "tavily-test-key")
    monkeypatch.setenv("NAVER_CLIENT_ID", "naver-test-id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "naver-test-secret")
    monkeypatch.setenv("YOUTUBE_API_KEY", "yt-test-key")

    with respx.mock:
        # BRAVE 키 없으므로 HTTP 요청이 발생하지 않아야 함
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_brave("005930", "삼성전자", client=client)

    assert isinstance(result, SourceResult)
    assert result.success is False
    assert result.error_type == "missing_key"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3: 게이트 & 오케스트레이션 테스트
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_minimum_2_sources_gate_passes(monkeypatch, mock_env_all_keys):
    """2/5 소스 성공 시 gate_passed=True (SPEC-AI-REPORT-003: codex 슬롯)."""
    async def mock_codex(code, name, client=None, staging_sources_dir=None):
        return SourceResult(
            name="codex",
            success=True,
            data={"markdown_path": "/tmp/fake/codex.md", "char_count": 100},
        )

    async def mock_brave(code, name, client=None):
        return SourceResult(name="brave", success=True, data=[{"title": "t", "url": "u", "snippet": "s"}])

    async def mock_tavily(code, name, client=None):
        return SourceResult(name="tavily", success=False, data=None, error_type="timeout")

    async def mock_naver(code, name, client=None):
        return SourceResult(name="naver", success=False, data=None, error_type="timeout")

    async def mock_youtube(code, name, client=None):
        return SourceResult(name="youtube", success=False, data=None, error_type="timeout")

    monkeypatch.setattr(_MOD, "_collect_codex", mock_codex)
    monkeypatch.setattr(_MOD, "_collect_brave", mock_brave)
    monkeypatch.setattr(_MOD, "_collect_tavily", mock_tavily)
    monkeypatch.setattr(_MOD, "_collect_naver", mock_naver)
    monkeypatch.setattr(_MOD, "_collect_youtube", mock_youtube)

    result = await collect_all_sources("005930", "삼성전자", staging_sources_dir=Path("/tmp/fake"))

    assert isinstance(result, CollectionResult)
    assert result.gate_passed is True
    assert result.sources["codex"].success is True
    assert result.sources["brave"].success is True
    assert result.sources["tavily"].success is False


@pytest.mark.asyncio
async def test_minimum_2_sources_gate_fails_at_one(monkeypatch, mock_env_all_keys):
    """1/5 소스 성공 시 gate_passed=False, ValueError는 발생하지 않음."""
    async def mock_codex(code, name, client=None, staging_sources_dir=None):
        return SourceResult(
            name="codex",
            success=True,
            data={"markdown_path": "/tmp/fake/codex.md", "char_count": 50},
        )

    async def mock_fail(source_name):
        async def inner(code, name, client=None):
            return SourceResult(name=source_name, success=False, data=None, error_type="timeout")
        return inner

    monkeypatch.setattr(_MOD, "_collect_codex", mock_codex)
    monkeypatch.setattr(_MOD, "_collect_brave", await mock_fail("brave"))
    monkeypatch.setattr(_MOD, "_collect_tavily", await mock_fail("tavily"))
    monkeypatch.setattr(_MOD, "_collect_naver", await mock_fail("naver"))
    monkeypatch.setattr(_MOD, "_collect_youtube", await mock_fail("youtube"))

    # ValueError가 발생하지 않아야 함 — gate check는 boolean만 반환
    result = await collect_all_sources("005930", "삼성전자", staging_sources_dir=Path("/tmp/fake"))

    assert isinstance(result, CollectionResult)
    assert result.gate_passed is False
    successful = sum(1 for s in result.sources.values() if s.success)
    assert successful == 1


@pytest.mark.asyncio
async def test_all_sources_succeed(monkeypatch, mock_env_all_keys):
    """5/5 소스 성공 시 gate_passed=True, 5개 소스 모두 존재."""
    async def mock_codex(code, name, client=None, staging_sources_dir=None):
        return SourceResult(
            name="codex",
            success=True,
            data={"markdown_path": "/tmp/fake/codex.md", "char_count": 1000},
        )

    async def mock_brave(code, name, client=None):
        return SourceResult(name="brave", success=True, data=[])

    async def mock_tavily(code, name, client=None):
        return SourceResult(name="tavily", success=True, data={"results": [], "answer": None})

    async def mock_naver(code, name, client=None):
        return SourceResult(name="naver", success=True, data=[])

    async def mock_youtube(code, name, client=None):
        return SourceResult(name="youtube", success=True, data=[])

    monkeypatch.setattr(_MOD, "_collect_codex", mock_codex)
    monkeypatch.setattr(_MOD, "_collect_brave", mock_brave)
    monkeypatch.setattr(_MOD, "_collect_tavily", mock_tavily)
    monkeypatch.setattr(_MOD, "_collect_naver", mock_naver)
    monkeypatch.setattr(_MOD, "_collect_youtube", mock_youtube)

    result = await collect_all_sources("005930", "삼성전자", staging_sources_dir=Path("/tmp/fake"))

    assert result.gate_passed is True
    assert len(result.sources) == 5
    assert all(s.success for s in result.sources.values())


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4: 스테이징 디렉토리 테스트
# ─────────────────────────────────────────────────────────────────────────────


def _make_collection_result(
    *,
    codex_success: bool = True,
    brave_success: bool = True,
    tavily_success: bool = True,
    naver_success: bool = True,
    youtube_success: bool = True,
) -> CollectionResult:
    """테스트용 CollectionResult 생성 헬퍼 (SPEC-AI-REPORT-003: codex 슬롯)."""
    sources = {
        "codex": SourceResult(
            name="codex",
            success=codex_success,
            data={"markdown_path": "/tmp/fake/codex.md", "char_count": 200}
            if codex_success
            else None,
            error_type=None if codex_success else "timeout",
        ),
        "brave": SourceResult(
            name="brave",
            success=brave_success,
            data=[{"title": "t", "url": "https://brave.com/1", "snippet": "s"}]
            if brave_success
            else None,
            error_type=None if brave_success else "timeout",
        ),
        "tavily": SourceResult(
            name="tavily",
            success=tavily_success,
            data={"results": [{"title": "t", "url": "u", "snippet": "s", "score": 0.9}], "answer": "A"}
            if tavily_success
            else None,
            error_type=None if tavily_success else "http_error",
        ),
        "naver": SourceResult(
            name="naver",
            success=naver_success,
            data=[{"title": "t", "url": "https://naver.com/1", "snippet": "s"}]
            if naver_success
            else None,
            error_type=None if naver_success else "missing_key",
        ),
        "youtube": SourceResult(
            name="youtube",
            success=youtube_success,
            data=[{"title": "t", "url": "https://youtu.be/1", "snippet": "s"}]
            if youtube_success
            else None,
            error_type=None if youtube_success else "timeout",
        ),
    }
    gate_passed = sum(1 for s in sources.values() if s.success) >= 2
    return CollectionResult(
        code="005930",
        stock_name="삼성전자",
        sources=sources,
        gate_passed=gate_passed,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )


def test_create_staging_dir_uuid8(tmp_path):
    """스테이징 디렉토리 이름에 8자리 UUID 포함, tmp_path 하위 생성."""
    result = _make_collection_result()
    staging_dir = create_staging_directory("005930", result, base_dir=tmp_path)

    assert staging_dir.exists()
    assert staging_dir.is_dir()
    # 이름 포맷: analysis_<code>_<ISO8601-UTC>_<uuid8>
    name = staging_dir.name
    assert name.startswith("analysis_005930_")
    # UUID 부분 추출 (마지막 '_' 이후)
    uuid_part = name.rsplit("_", 1)[-1]
    assert len(uuid_part) == 8
    assert re.match(r"^[0-9a-f]{8}$", uuid_part), f"UUID8이 아님: {uuid_part}"
    # sources/ 하위 디렉토리 존재
    assert (staging_dir / "sources").is_dir()


def test_staging_path_under_tmp_only(tmp_path):
    """base_dir 외부 경로로 생성 시 ValueError 발생."""
    result = _make_collection_result()
    # 경로 탈출 시도 — base_dir를 /tmp로 설정하고 code에 경로 탈출 문자 삽입
    # 또는 base_dir 자체가 /tmp 외부인 경우 테스트
    # 여기서는 base_dir를 /tmp로 설정 후, 잘못된 base_dir 전달 테스트
    import tempfile
    non_tmp_dir = tmp_path.parent.parent  # tmp_path의 부모의 부모 (매우 상위)
    # base_dir 파라미터가 /tmp 외부를 가리키는 경우 ValueError
    # 단, tmp_path 자체를 base_dir로 전달하면 정상 동작이므로,
    # base_dir를 /usr 등으로 설정하여 테스트
    unsafe_dir = Path("/usr/local/bin")
    if unsafe_dir.exists():
        with pytest.raises(ValueError, match="base_dir"):
            create_staging_directory("005930", result, base_dir=unsafe_dir)


def test_write_summary_md_table(tmp_path):
    """summary.md에 5개 소스 상태 테이블 포함 + 실패 소스 오류 이유 기록."""
    result = _make_collection_result(naver_success=False, youtube_success=False)
    staging_dir = create_staging_directory("005930", result, base_dir=tmp_path)

    summary_path = staging_dir / "summary.md"
    assert summary_path.exists()

    content = summary_path.read_text(encoding="utf-8")

    # 5개 소스 모두 테이블에 등록 (SPEC-AI-REPORT-003: perplexity → codex)
    for source in ("codex", "brave", "tavily", "naver", "youtube"):
        assert source in content.lower(), f"{source} 소스가 summary.md에 없음"

    # 성공 소스: ✅ 표시
    assert "✅" in content

    # 실패 소스: ❌ 표시
    assert "❌" in content

    # 종목 코드/이름 포함
    assert "005930" in content or "삼성전자" in content


# SPEC-AI-REPORT-003: test_write_perplexity_md_think_stripped 제거됨.
# Codex 는 마크다운을 --output-last-message 경로에 직접 기록하므로, finalize 단계에서
# codex.md 를 파이썬이 새로 쓰지 않는다 (덮어쓰기 방지). think 블록 처리 불필요.


def test_finalize_skips_codex_md_write(tmp_path):
    """SPEC-AI-REPORT-003 FR-006: finalize 는 codex.md 를 새로 작성하지 않는다.

    Codex subprocess 가 --output-last-message 경로에 직접 마크다운을 쓴 후에는
    finalize_staging_directory 가 해당 파일을 덮어쓰지 않아야 한다.
    """
    result = _make_collection_result()
    # Codex 성공 시 data 는 markdown_path 정보만 포함 (실제 파일은 subprocess 가 씀)
    staging_dir = create_staging_directory("005930", result, base_dir=tmp_path)

    # finalize 는 codex.md 를 새로 쓰지 않으므로 파일이 없어야 정상
    # (단위 테스트에서는 subprocess 를 호출하지 않으므로 애초에 파일 미존재)
    codex_md = staging_dir / "sources" / "codex.md"
    assert not codex_md.exists(), (
        "finalize_staging_directory 가 codex.md 를 새로 작성했음 — "
        "subprocess 경로와 충돌 위험"
    )


def test_failed_source_json_omitted(tmp_path):
    """실패 소스의 JSON 파일은 생성되지 않음; summary.md는 실패 기록."""
    result = _make_collection_result(naver_success=False)
    staging_dir = create_staging_directory("005930", result, base_dir=tmp_path)

    # naver.json 없음
    naver_json = staging_dir / "sources" / "naver.json"
    assert not naver_json.exists(), "실패한 naver.json이 생성되어서는 안 됨"

    # 성공 소스 파일은 존재
    assert (staging_dir / "sources" / "brave.json").exists()

    # summary.md에는 naver 실패 기록
    summary = (staging_dir / "summary.md").read_text(encoding="utf-8")
    assert "naver" in summary.lower()


def test_staging_dir_uuid_unique_concurrent(tmp_path):
    """동시 생성 호출 시 UUID가 충돌하지 않음."""
    result = _make_collection_result()
    dirs = [
        create_staging_directory("005930", result, base_dir=tmp_path)
        for _ in range(5)
    ]
    # 모두 고유해야 함
    dir_names = [d.name for d in dirs]
    assert len(set(dir_names)) == 5, f"UUID 충돌 발생: {dir_names}"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5: 파서 어댑터 단위 테스트
# ─────────────────────────────────────────────────────────────────────────────


def test_normalize_brave_fixture(brave_response_json):
    """Brave API 응답 → [{title, url, snippet}, ...] 정규화."""
    results = _normalize_brave(brave_response_json)

    assert isinstance(results, list)
    assert len(results) == 2
    first = results[0]
    assert "title" in first
    assert "url" in first
    assert "snippet" in first
    assert first["url"] == "https://example.com/samsung"


def test_normalize_naver_strips_html(naver_response_json):
    """Naver 응답 title/description의 HTML 태그 제거."""
    results = _normalize_naver(naver_response_json)

    assert isinstance(results, list)
    assert len(results) >= 1
    first = results[0]
    # HTML 태그 없어야 함
    assert "<b>" not in first["title"]
    assert "<b>" not in first["snippet"]
    assert "삼성전자" in first["title"]


def test_normalize_youtube_video_url(youtube_response_json):
    """YouTube videoId → https://www.youtube.com/watch?v=<id> 변환."""
    results = _normalize_youtube(youtube_response_json)

    assert isinstance(results, list)
    assert len(results) >= 1
    first = results[0]
    assert first["url"] == "https://www.youtube.com/watch?v=abc123"
    assert "title" in first
    assert "snippet" in first


def test_deduplicate_by_url():
    """URL 중복 제거 — 첫 번째 항목 보존."""
    items = [
        {"title": "A", "url": "https://example.com/1", "snippet": "first"},
        {"title": "B", "url": "https://example.com/2", "snippet": "second"},
        {"title": "C", "url": "https://example.com/1", "snippet": "duplicate"},  # 중복
    ]
    deduped = _deduplicate_by_url(items)

    assert len(deduped) == 2
    urls = [item["url"] for item in deduped]
    assert urls.count("https://example.com/1") == 1
    # 첫 번째 항목 보존 확인
    first_match = next(i for i in deduped if i["url"] == "https://example.com/1")
    assert first_match["title"] == "A"


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6: _strip_think_blocks 단위 테스트
# ─────────────────────────────────────────────────────────────────────────────


def test_strip_think_blocks_removes_content():
    """<think>...</think> DOTALL 패턴 제거."""
    text = "<think>내부\n추론</think>실제 내용"
    stripped = _strip_think_blocks(text)
    assert "<think>" not in stripped
    assert "내부" not in stripped
    assert "실제 내용" in stripped


def test_strip_think_blocks_noop_without_tags():
    """<think> 없는 텍스트는 변경 없음."""
    text = "일반 텍스트입니다."
    assert _strip_think_blocks(text) == text


def test_strip_think_blocks_multiple():
    """복수 <think> 블록 모두 제거."""
    text = "<think>1</think>중간<think>2</think>끝"
    stripped = _strip_think_blocks(text)
    assert "1" not in stripped
    assert "2" not in stripped
    assert "중간" in stripped
    assert "끝" in stripped


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7: 커버리지 보강 — 추가 실패 경로 및 엣지 케이스
# ─────────────────────────────────────────────────────────────────────────────


# SPEC-AI-REPORT-003: test_collect_perplexity_{timeout,http_error} 제거됨.
# Codex 어댑터의 타임아웃 / 비정상 종료 처리는 test_codex_cli_runner.py 및
# test_collect_codex_{timeout_retry_fails,binary_missing,retry_succeeds} 에서 커버.


# SPEC-AI-REPORT-003: test_collect_perplexity_missing_key 제거됨.
# Codex 는 ChatGPT 구독 기반이라 API 키 개념이 없음 (`codex login` 으로 인증).
# 바이너리/인증 실패 경로는 test_collect_codex_{binary_missing,auth_no_retry} 에서 커버.


@pytest.mark.asyncio
async def test_collect_tavily_timeout(mock_env_all_keys):
    """Tavily httpx.TimeoutException → error_type='timeout'."""
    with respx.mock:
        respx.post("https://api.tavily.com/search").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_tavily("005930", "삼성전자", client=client)
    assert result.success is False
    assert result.error_type == "timeout"


@pytest.mark.asyncio
async def test_collect_tavily_missing_key(monkeypatch):
    """TAVILY_API_KEY 미설정 → missing_key."""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    async with httpx.AsyncClient() as client:
        result = await _MOD._collect_tavily("005930", "삼성전자", client=client)
    assert result.success is False
    assert result.error_type == "missing_key"


@pytest.mark.asyncio
async def test_collect_naver_timeout(mock_env_all_keys):
    """Naver httpx.TimeoutException → error_type='timeout'."""
    with respx.mock:
        respx.get(url__startswith="https://openapi.naver.com").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_naver("005930", "삼성전자", client=client)
    assert result.success is False
    assert result.error_type == "timeout"


@pytest.mark.asyncio
async def test_collect_naver_missing_key(monkeypatch):
    """NAVER_CLIENT_ID 미설정 → missing_key."""
    monkeypatch.delenv("NAVER_CLIENT_ID", raising=False)
    async with httpx.AsyncClient() as client:
        result = await _MOD._collect_naver("005930", "삼성전자", client=client)
    assert result.success is False
    assert result.error_type == "missing_key"


@pytest.mark.asyncio
async def test_collect_youtube_timeout(mock_env_all_keys):
    """YouTube httpx.TimeoutException → error_type='timeout'."""
    with respx.mock:
        respx.get(url__startswith="https://www.googleapis.com/youtube/v3/search").mock(
            side_effect=httpx.TimeoutException("timeout")
        )
        async with httpx.AsyncClient() as client:
            result = await _MOD._collect_youtube("005930", "삼성전자", client=client)
    assert result.success is False
    assert result.error_type == "timeout"


@pytest.mark.asyncio
async def test_collect_youtube_missing_key(monkeypatch):
    """YOUTUBE_API_KEY 미설정 → missing_key."""
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    async with httpx.AsyncClient() as client:
        result = await _MOD._collect_youtube("005930", "삼성전자", client=client)
    assert result.success is False
    assert result.error_type == "missing_key"


def test_normalize_brave_empty_data():
    """Brave 응답 없음 → 빈 리스트."""
    assert _normalize_brave(None) == []
    assert _normalize_brave({}) == []


def test_normalize_tavily_none():
    """Tavily 응답 없음 → 기본 구조."""
    result = _normalize_tavily(None)
    assert result == {"results": [], "answer": None}


def test_normalize_naver_empty():
    """Naver 응답 없음 → 빈 리스트."""
    assert _normalize_naver(None) == []
    assert _normalize_naver({"items": []}) == []


# SPEC-AI-REPORT-003: test_normalize_perplexity_none / test_write_staging_with_citations 제거됨.
# _normalize_perplexity 함수 및 perplexity.md citations 블록 생성 기능은 삭제됨.


@pytest.mark.asyncio
async def test_collect_all_sources_no_client(monkeypatch):
    """client=None 경우 내부 httpx.AsyncClient 생성 경로 검증 (SPEC-AI-REPORT-003: codex 슬롯)."""
    async def mock_codex(code, name, client=None, staging_sources_dir=None):
        return SourceResult(
            name="codex",
            success=True,
            data={"markdown_path": "/tmp/fake/codex.md", "char_count": 100},
        )

    async def mock_fail(src_name):
        async def inner(code, name, client=None):
            return SourceResult(name=src_name, success=False, data=None, error_type="missing_key")
        return inner

    monkeypatch.setattr(_MOD, "_collect_codex", mock_codex)
    monkeypatch.setattr(_MOD, "_collect_brave", await mock_fail("brave"))
    monkeypatch.setattr(_MOD, "_collect_tavily", await mock_fail("tavily"))
    monkeypatch.setattr(_MOD, "_collect_naver", await mock_fail("naver"))
    monkeypatch.setattr(_MOD, "_collect_youtube", await mock_fail("youtube"))

    # client=None — 내부에서 AsyncClient 생성. staging_sources_dir 은 codex 슬롯용.
    result = await collect_all_sources("005930", "삼성전자", staging_sources_dir=Path("/tmp/fake"))
    assert isinstance(result, CollectionResult)
    assert result.sources["codex"].success is True


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-003 Step 3b — _collect_codex 테스트
# ─────────────────────────────────────────────────────────────────────────────


def _load_codex_runner_module():
    """codex_cli_runner 실 모듈을 sys.modules 에 등록 (stub 이 있으면 강제 재로드).

    다른 테스트 파일이 부분 stub 을 sys.modules 에 심어둔 경우 run_codex_research /
    CodexResult 가 누락돼 monkeypatch 가 실패한다. 실 모듈이 아닌 경우 덮어쓴다.
    """
    codex_module_name = "backend.services.codex_cli_runner"
    existing = sys.modules.get(codex_module_name)
    if existing is not None and hasattr(existing, "run_codex_research"):
        return existing

    codex_path = Path(__file__).parent.parent / "services" / "codex_cli_runner.py"
    spec = importlib.util.spec_from_file_location(codex_module_name, codex_path)
    assert spec and spec.loader, f"codex_cli_runner 로드 실패: {codex_path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[codex_module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture()
def codex_runner_mod():
    """codex_cli_runner 모듈 인스턴스 픽스처."""
    return _load_codex_runner_module()


def _make_codex_result(
    runner_mod,
    *,
    success: bool,
    error_type: str | None = None,
    error_message: str | None = None,
    char_count: int = 0,
    output_path: Path | None = None,
):
    """CodexResult 인스턴스 생성 헬퍼 (격리 로드된 runner 모듈의 dataclass 사용)."""
    return runner_mod.CodexResult(
        success=success,
        output_path=output_path,
        char_count=char_count,
        error_type=error_type,
        error_message=error_message,
        duration_ms=100,
    )


@pytest.mark.asyncio
async def test_collect_codex_success(codex_runner_mod, monkeypatch, tmp_path):
    """run_codex_research 가 성공을 반환하면 SourceResult(success=True) + markdown_path."""
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()

    async def fake_run(**kwargs):
        # 실제 subprocess 대신 fake 가 output_path 에 파일 생성
        kwargs["output_path"].write_text("# Codex 결과\n내용 내용", encoding="utf-8")
        return _make_codex_result(
            codex_runner_mod,
            success=True,
            char_count=kwargs["output_path"].stat().st_size,
            output_path=kwargs["output_path"],
        )

    monkeypatch.setattr(codex_runner_mod, "run_codex_research", fake_run)

    result = await _MOD._collect_codex(
        "006400", "Samsung SDI", staging_sources_dir=sources_dir
    )

    assert result.name == "codex"
    assert result.success is True
    assert isinstance(result.data, dict)
    assert result.data["markdown_path"] == str(sources_dir / "codex.md")
    assert result.data["char_count"] > 0
    assert result.error_type is None
    assert (sources_dir / "codex.md").exists()


@pytest.mark.asyncio
async def test_collect_codex_timeout_retry_fails(codex_runner_mod, monkeypatch, tmp_path):
    """타임아웃이 두 번 연속 발생하면 SourceResult(success=False, error_type='timeout')."""
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()

    call_count = 0

    async def fake_run(**kwargs):
        nonlocal call_count
        call_count += 1
        return _make_codex_result(
            codex_runner_mod,
            success=False,
            error_type="timeout",
            error_message="Codex 타임아웃 (600초)",
            output_path=kwargs["output_path"],
        )

    monkeypatch.setattr(codex_runner_mod, "run_codex_research", fake_run)

    result = await _MOD._collect_codex(
        "006400", "Samsung SDI", staging_sources_dir=sources_dir
    )

    assert call_count == 2  # 초기 + 1회 재시도
    assert result.name == "codex"
    assert result.success is False
    assert result.error_type == "timeout"


@pytest.mark.asyncio
async def test_collect_codex_binary_missing(codex_runner_mod, monkeypatch, tmp_path):
    """binary_missing 은 결정론적 실패 — 재시도 없음 (ER-001)."""
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()

    call_count = 0

    async def fake_run(**kwargs):
        nonlocal call_count
        call_count += 1
        return _make_codex_result(
            codex_runner_mod,
            success=False,
            error_type="binary_missing",
            error_message="Codex 바이너리를 찾을 수 없습니다",
            output_path=kwargs["output_path"],
        )

    monkeypatch.setattr(codex_runner_mod, "run_codex_research", fake_run)

    result = await _MOD._collect_codex(
        "006400", "Samsung SDI", staging_sources_dir=sources_dir
    )

    assert call_count == 1  # 재시도 없음
    assert result.success is False
    assert result.error_type == "binary_missing"


@pytest.mark.asyncio
async def test_collect_codex_retry_succeeds(codex_runner_mod, monkeypatch, tmp_path):
    """첫 호출 timeout, 두 번째 호출 성공 → SourceResult(success=True)."""
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()

    call_count = 0

    async def fake_run(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _make_codex_result(
                codex_runner_mod,
                success=False,
                error_type="timeout",
                error_message="첫 호출 타임아웃",
                output_path=kwargs["output_path"],
            )
        kwargs["output_path"].write_text("# 재시도 성공", encoding="utf-8")
        return _make_codex_result(
            codex_runner_mod,
            success=True,
            char_count=kwargs["output_path"].stat().st_size,
            output_path=kwargs["output_path"],
        )

    monkeypatch.setattr(codex_runner_mod, "run_codex_research", fake_run)

    result = await _MOD._collect_codex(
        "006400", "Samsung SDI", staging_sources_dir=sources_dir
    )

    assert call_count == 2
    assert result.success is True
    assert result.data["markdown_path"] == str(sources_dir / "codex.md")
    assert (sources_dir / "codex.md").exists()


@pytest.mark.asyncio
async def test_collect_codex_auth_no_retry(codex_runner_mod, monkeypatch, tmp_path):
    """auth 실패는 결정론적 — 재시도 금지 (ER-002)."""
    sources_dir = tmp_path / "sources"
    sources_dir.mkdir()

    call_count = 0

    async def fake_run(**kwargs):
        nonlocal call_count
        call_count += 1
        return _make_codex_result(
            codex_runner_mod,
            success=False,
            error_type="auth",
            error_message="not logged in",
            output_path=kwargs["output_path"],
        )

    monkeypatch.setattr(codex_runner_mod, "run_codex_research", fake_run)

    result = await _MOD._collect_codex(
        "006400", "Samsung SDI", staging_sources_dir=sources_dir
    )

    assert call_count == 1  # 재시도 없음
    assert result.error_type == "auth"


@pytest.mark.asyncio
async def test_collect_codex_without_staging_dir_fails_fast(tmp_path):
    """staging_sources_dir 미전달 시 호출자 로직 오류로 즉시 실패."""
    result = await _MOD._collect_codex(
        "006400", "Samsung SDI", staging_sources_dir=None
    )

    assert result.success is False
    assert result.error_type == "missing_staging_dir"
