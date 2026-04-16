"""SPEC-AI-REPORT-002 Phase C: 딥 리서치 서비스 단위 테스트.

TDD 방법론: RED-GREEN-REFACTOR

테스트 범위:
- 오케스트레이션 성공 / 부분 실패 / 전체 실패 경로
- 타임아웃 및 클라이언트 연결 끊김
- 리포트 저장 on DoneSignal / 저장 안 됨 on error
- Rate limit: 일일 쿼터 + 버스트 + Perplexity 격리
- 중복 분석 차단 (AlreadyRunningError)
- 활성 분석 세트 해제 보장 (success & exception)
- 합성 프롬프트 로더
- opus 모델 플래그 전달

AC 매핑:
- AC-004: 5개 소스 수집
- AC-006: rate limit 쿼터
- AC-007: 스트리밍 이벤트 형식
- AC-008: 중복 요청 거부 (ER-006)
- AC-009: 타임아웃 처리
- AC-010: 클라이언트 연결 끊김
- AC-011: 리포트 저장
- AC-013: 합성 프롬프트 파일
- AC-018: opus 모델 플래그
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 모듈 격리 로드 헬퍼
# ─────────────────────────────────────────────────────────────────────────────

_SVC_PATH = Path(__file__).parent.parent / "services" / "deep_research_service.py"
_COLLECTOR_PATH = Path(__file__).parent.parent / "services" / "deep_research_collector.py"
_STREAMER_PATH = Path(__file__).parent.parent / "services" / "claude_cli_streamer.py"
_AI_REPORT_PATH = Path(__file__).parent.parent / "services" / "ai_report_service.py"


def _load_module(path: Path, module_name: str):
    """모듈을 직접 로드. cascade import 회피."""
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec and spec.loader, f"모듈 로드 실패: {path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# 종속 모듈 먼저 로드 (deep_research_service가 이들을 import함)
# collector 모듈 로드
_collector_mod = _load_module(_COLLECTOR_PATH, "backend.services.deep_research_collector")

# streamer 모듈 로드
_streamer_mod = _load_module(_STREAMER_PATH, "backend.services.claude_cli_streamer")

# ai_report_service: my_chart.registry를 요구하므로 실 패키지 import를 우선 시도하고
# 실패 시에만 스텁 등록. 무조건 스텁하면 test_sector_advanced.py 등 다른 테스트가
# my_chart.registry에서 `get_sector_registry` 등 심볼을 찾지 못해 실패한다.
def _load_ai_report():
    """ai_report_service를 my_chart.registry와 함께 로드."""
    # 프로젝트 루트(my_chart/ 패키지 부모 디렉토리)를 sys.path에 추가
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        # 실 패키지 시도
        import my_chart.registry  # type: ignore[import-not-found]  # noqa: F401
    except Exception:
        # 실 패키지 로드 실패 시에만 스텁 등록 (ai_report_service가 _name을 요구)
        registry_stub = types.ModuleType("my_chart.registry")
        registry_stub._name = lambda code: "삼성전자"  # type: ignore[attr-defined]
        existing = sys.modules.get("my_chart")
        if existing is None or not hasattr(existing, "__path__"):
            my_chart_pkg_path = project_root / "my_chart"
            stub = types.ModuleType("my_chart")
            stub.__path__ = [str(my_chart_pkg_path)] if my_chart_pkg_path.is_dir() else []  # type: ignore[attr-defined]
            sys.modules["my_chart"] = stub
        sys.modules["my_chart.registry"] = registry_stub

    module_name = "backend.services.ai_report_service"
    spec = importlib.util.spec_from_file_location(module_name, _AI_REPORT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


_ai_report_mod = _load_ai_report()

# deep_research_service 로드
_svc_mod = _load_module(_SVC_PATH, "backend.services.deep_research_service")

# 편의 변수
AlreadyRunningError = _svc_mod.AlreadyRunningError
DeepRateLimitError = _svc_mod.DeepRateLimitError
CollectionFailedError = _svc_mod.CollectionFailedError
check_deep_rate_limit = _svc_mod.check_deep_rate_limit
_load_synthesis_prompt = _svc_mod._load_synthesis_prompt
stream_deep_analysis = _svc_mod.stream_deep_analysis
_cleanup_stale_staging_dirs = _svc_mod._cleanup_stale_staging_dirs

# Streamer 이벤트 타입
TextDelta = _streamer_mod.TextDelta
DoneSignal = _streamer_mod.DoneSignal
ErrorSignal = _streamer_mod.ErrorSignal

# Collector 타입
CollectionResult = _collector_mod.CollectionResult
SourceResult = _collector_mod.SourceResult


# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼: CollectionResult 팩토리
# ─────────────────────────────────────────────────────────────────────────────

def _make_source(name: str, success: bool) -> SourceResult:
    return SourceResult(
        name=name,
        success=success,
        data={"content": f"{name} data"} if success else None,
        error_type=None if success else "http_error",
        error_message=None if success else "HTTP 500",
    )


def _make_collection_result(n_success: int, code: str = "005930", stock_name: str = "삼성전자") -> CollectionResult:
    """n_success개 소스가 성공한 CollectionResult 생성."""
    src_names = ["perplexity", "brave", "tavily", "naver", "youtube"]
    sources = {}
    for i, name in enumerate(src_names):
        sources[name] = _make_source(name, i < n_success)
    gate_passed = n_success >= 2
    now = datetime.now(timezone.utc)
    return CollectionResult(
        code=code,
        stock_name=stock_name,
        sources=sources,
        gate_passed=gate_passed,
        started_at=now,
        completed_at=now,
    )


async def _make_streamer_gen(*events):
    """StreamEvent 목록을 yield하는 비동기 제너레이터."""
    for event in events:
        yield event


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_module_state(monkeypatch):
    """각 테스트 전 모듈 레벨 가변 상태 초기화."""
    monkeypatch.setattr(_svc_mod, "_deep_daily_call_count", {})
    monkeypatch.setattr(_svc_mod, "_deep_recent_timestamps", [])
    monkeypatch.setattr(_svc_mod, "_active_deep_analyses", set())


@pytest.fixture()
def synthesis_prompt_file(tmp_path, monkeypatch):
    """합성 프롬프트 파일을 tmp_path에 생성하고 경로를 패치."""
    prompt_file = tmp_path / "stock_synthesis_prompt.md"
    prompt_file.write_text("# 합성 프롬프트\n\n테스트 내용입니다.", encoding="utf-8")
    monkeypatch.setattr(_svc_mod, "_SYNTHESIS_PROMPT_PATH", prompt_file)
    return prompt_file


# ─────────────────────────────────────────────────────────────────────────────
# 오케스트레이션 성공 경로
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrate_full_success_5_of_5(tmp_path, monkeypatch, synthesis_prompt_file):
    """AC-004, AC-007: 5/5 소스 성공 → SSE 이벤트 순서 확인 + save_report 호출."""
    collection_result = _make_collection_result(5)

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        d = tmp_path / f"staging_{code}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        yield TextDelta("# 리포트\n")
        yield TextDelta("본문\n")
        yield DoneSignal()

    mock_save = MagicMock(return_value="2026-04-16.md")

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)
    monkeypatch.setattr(_svc_mod, "save_report", mock_save)

    events = []
    async for event in stream_deep_analysis("005930", "삼성전자"):
        events.append(event)

    # 최소 data 이벤트 존재 확인
    data_events = [e for e in events if e.get("data") and not e.get("event")]
    assert any("# 리포트" in e["data"] for e in data_events), "리포트 헤더 이벤트 없음"
    assert any("본문" in e["data"] for e in data_events), "본문 이벤트 없음"

    # done 이벤트 확인
    done_events = [e for e in events if e.get("event") == "done"]
    assert len(done_events) == 1, "done 이벤트 정확히 1개 필요"

    # save_report 호출 확인
    mock_save.assert_called_once()
    args = mock_save.call_args
    assert "삼성전자" in args[0]


@pytest.mark.asyncio
async def test_orchestrate_partial_sources_3_of_5(tmp_path, monkeypatch, synthesis_prompt_file):
    """AC-004: 3/5 소스 성공 → gate 통과, 합성 진행, done 이벤트."""
    collection_result = _make_collection_result(3)

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        d = tmp_path / f"staging_{code}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        yield TextDelta("# 부분 리포트\n")
        yield DoneSignal()

    mock_save = MagicMock(return_value="2026-04-16.md")

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)
    monkeypatch.setattr(_svc_mod, "save_report", mock_save)

    events = []
    async for event in stream_deep_analysis("005930", "삼성전자"):
        events.append(event)

    done_events = [e for e in events if e.get("event") == "done"]
    assert len(done_events) == 1
    mock_save.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrate_below_minimum_1_of_5(monkeypatch, synthesis_prompt_file):
    """AC-004: 1/5 소스 성공 → gate 실패, error 이벤트, stream_claude_synthesis 미호출."""
    collection_result = _make_collection_result(1)

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    mock_streamer = MagicMock()

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)

    events = []
    async for event in stream_deep_analysis("005930", "삼성전자"):
        events.append(event)

    # error 이벤트 존재 확인
    error_events = [e for e in events if e.get("event") == "error"]
    assert error_events, "error 이벤트 없음"
    assert "1/5" in error_events[0]["data"], "에러 메시지에 1/5 없음"
    assert "수집 실패" in error_events[0]["data"], "에러 메시지에 '수집 실패' 없음"

    # streamer 미호출 확인
    mock_streamer.assert_not_called()


@pytest.mark.asyncio
async def test_orchestrate_all_sources_fail(monkeypatch, synthesis_prompt_file):
    """AC-004: 0/5 소스 성공 → error 이벤트 + 502 힌트 포함."""
    collection_result = _make_collection_result(0)

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    mock_streamer = MagicMock()

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)

    events = []
    async for event in stream_deep_analysis("005930", "삼성전자"):
        events.append(event)

    error_events = [e for e in events if e.get("event") == "error"]
    assert error_events, "error 이벤트 없음"
    # 0/5 문구 확인
    assert "0/5" in error_events[0]["data"]
    mock_streamer.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# 타임아웃 및 취소
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_orchestrate_cli_timeout(tmp_path, monkeypatch, synthesis_prompt_file):
    """AC-009: TimeoutError → error 이벤트 '합성 시간 초과' + 스테이징 정리."""
    collection_result = _make_collection_result(5)
    staging_dir = tmp_path / "staging_timeout"
    staging_dir.mkdir()

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        return staging_dir

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        raise asyncio.TimeoutError()
        yield  # 제너레이터로 만들기

    mock_save = MagicMock()

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)
    monkeypatch.setattr(_svc_mod, "save_report", mock_save)

    events = []
    async for event in stream_deep_analysis("005930", "삼성전자"):
        events.append(event)

    error_events = [e for e in events if e.get("event") == "error"]
    assert error_events, "error 이벤트 없음"
    assert "합성 시간 초과" in error_events[0]["data"] or "시간 초과" in error_events[0]["data"]

    # save_report 미호출
    mock_save.assert_not_called()

    # 스테이징 정리 확인 (finally 블록)
    assert not staging_dir.exists(), "스테이징 디렉토리가 정리되지 않음"


@pytest.mark.asyncio
async def test_orchestrate_client_disconnect_cancelled(tmp_path, monkeypatch, synthesis_prompt_file):
    """AC-010: CancelledError → 스테이징 정리 + CancelledError 재발생."""
    collection_result = _make_collection_result(5)
    staging_dir = tmp_path / "staging_cancel"
    staging_dir.mkdir()

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        return staging_dir

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        raise asyncio.CancelledError()
        yield  # 제너레이터로 만들기

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)

    with pytest.raises(asyncio.CancelledError):
        async for _ in stream_deep_analysis("005930", "삼성전자"):
            pass

    # 스테이징 정리 확인
    assert not staging_dir.exists(), "CancelledError 후 스테이징 디렉토리 정리 안 됨"


# ─────────────────────────────────────────────────────────────────────────────
# 리포트 저장
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_report_saved_on_done(tmp_path, monkeypatch, synthesis_prompt_file):
    """AC-011: DoneSignal 수신 시 save_report 정확히 1회 호출, 전체 마크다운 전달."""
    collection_result = _make_collection_result(5)

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        d = tmp_path / f"staging_{code}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        yield TextDelta("# 리포트\n")
        yield TextDelta("본문 내용입니다.\n")
        yield DoneSignal()

    save_calls = []

    def mock_save(stock_name, content):
        save_calls.append((stock_name, content))
        return "2026-04-16.md"

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)
    monkeypatch.setattr(_svc_mod, "save_report", mock_save)

    async for _ in stream_deep_analysis("005930", "삼성전자"):
        pass

    assert len(save_calls) == 1, f"save_report 호출 횟수: {len(save_calls)}"
    sname, content = save_calls[0]
    assert sname == "삼성전자"
    assert "# 리포트" in content
    assert "본문 내용입니다." in content


@pytest.mark.asyncio
async def test_report_not_saved_on_error(tmp_path, monkeypatch, synthesis_prompt_file):
    """AC-011: 소스 수집 실패 경로에서 save_report 미호출."""
    collection_result = _make_collection_result(0)  # gate 실패

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    mock_save = MagicMock()

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "save_report", mock_save)

    async for _ in stream_deep_analysis("005930", "삼성전자"):
        pass

    mock_save.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# Rate Limit
# ─────────────────────────────────────────────────────────────────────────────


def test_check_deep_rate_limit_under_daily_quota(monkeypatch):
    """AC-006: 일일 쿼터(15) 미만 → 모든 호출 통과."""
    monkeypatch.setenv("AI_REPORT_DEEP_DAILY_QUOTA", "15")
    monkeypatch.setenv("AI_REPORT_DEEP_BURST_LIMIT", "100")  # 버스트 제한 해제

    for i in range(15):
        check_deep_rate_limit()  # 예외 없어야 함


def test_check_deep_rate_limit_over_daily_quota(monkeypatch):
    """AC-006: 16번째 호출 → DeepRateLimitError."""
    monkeypatch.setenv("AI_REPORT_DEEP_DAILY_QUOTA", "15")
    monkeypatch.setenv("AI_REPORT_DEEP_BURST_LIMIT", "100")

    for _ in range(15):
        check_deep_rate_limit()

    with pytest.raises(DeepRateLimitError) as exc_info:
        check_deep_rate_limit()

    assert "쿼터" in str(exc_info.value) or "quota" in str(exc_info.value).lower()


def test_check_deep_rate_limit_burst(monkeypatch):
    """AC-006: 60초 내 2번 → 2번째 호출에서 버스트 에러 (limit=1)."""
    import time

    monkeypatch.setenv("AI_REPORT_DEEP_DAILY_QUOTA", "100")
    monkeypatch.setenv("AI_REPORT_DEEP_BURST_LIMIT", "1")

    # 첫 번째 호출 통과
    check_deep_rate_limit()

    # 두 번째 호출은 버스트 초과
    with pytest.raises(DeepRateLimitError) as exc_info:
        check_deep_rate_limit()

    assert "버스트" in str(exc_info.value) or "burst" in str(exc_info.value).lower() or "분당" in str(exc_info.value)


def test_check_deep_rate_limit_isolated_from_perplexity(monkeypatch):
    """AC-006: Deep rate limit 소진 후에도 Perplexity(ai_report_service) 카운터 미영향."""
    monkeypatch.setenv("AI_REPORT_DEEP_DAILY_QUOTA", "1")
    monkeypatch.setenv("AI_REPORT_DEEP_BURST_LIMIT", "100")

    # Deep quota 소진
    check_deep_rate_limit()
    with pytest.raises(DeepRateLimitError):
        check_deep_rate_limit()

    # Perplexity 카운터 확인: ai_report_service의 _daily_call_count는 0이어야 함
    assert _ai_report_mod._daily_call_count == 0, (
        "Deep rate limit 소진이 Perplexity 카운터에 영향을 미침"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 활성 분석 추적 (ER-006)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_deep_request_rejected(monkeypatch, synthesis_prompt_file):
    """AC-008: 같은 종목 코드로 중복 요청 → AlreadyRunningError 또는 error SSE."""
    # 먼저 수동으로 활성 세트에 추가
    _svc_mod._active_deep_analyses.add("005930")

    try:
        events = []
        async for event in stream_deep_analysis("005930", "삼성전자"):
            events.append(event)

        # SSE error 방식으로 처리하는 경우
        error_events = [e for e in events if e.get("event") == "error"]
        assert error_events, "중복 요청에 대한 error 이벤트 없음"
        assert "이미 진행" in error_events[0]["data"] or "already" in error_events[0]["data"].lower()
    except AlreadyRunningError:
        # 예외 방식으로 처리해도 OK
        pass


@pytest.mark.asyncio
async def test_active_analysis_released_on_success(tmp_path, monkeypatch, synthesis_prompt_file):
    """AC-008: 스트림 완료 후 _active_deep_analyses에서 코드 제거."""
    collection_result = _make_collection_result(5)

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        d = tmp_path / f"staging_{code}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        yield DoneSignal()

    mock_save = MagicMock(return_value="2026-04-16.md")

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)
    monkeypatch.setattr(_svc_mod, "save_report", mock_save)

    async for _ in stream_deep_analysis("005930", "삼성전자"):
        pass

    assert "005930" not in _svc_mod._active_deep_analyses, (
        "완료 후에도 _active_deep_analyses에 코드가 남아있음"
    )


@pytest.mark.asyncio
async def test_active_analysis_released_on_exception(tmp_path, monkeypatch, synthesis_prompt_file):
    """AC-008: 예외 발생 후에도 finally에서 _active_deep_analyses 해제."""
    collection_result = _make_collection_result(5)
    staging_dir = tmp_path / "staging_exc"
    staging_dir.mkdir()

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        return staging_dir

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        raise RuntimeError("테스트 예외")
        yield

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)

    try:
        async for _ in stream_deep_analysis("005930", "삼성전자"):
            pass
    except Exception:
        pass

    assert "005930" not in _svc_mod._active_deep_analyses, (
        "예외 후에도 _active_deep_analyses에 코드가 남아있음"
    )


# ─────────────────────────────────────────────────────────────────────────────
# 합성 프롬프트 로더
# ─────────────────────────────────────────────────────────────────────────────


def test_load_synthesis_prompt_success(synthesis_prompt_file):
    """AC-013: _load_synthesis_prompt()가 파일 내용을 반환."""
    content = _load_synthesis_prompt()
    assert "합성 프롬프트" in content
    assert len(content) > 0


def test_load_synthesis_prompt_fail_fast(tmp_path, monkeypatch):
    """AC-013: 파일 없으면 FileNotFoundError 또는 ValueError 발생."""
    non_existent = tmp_path / "no_such_prompt.md"
    monkeypatch.setattr(_svc_mod, "_SYNTHESIS_PROMPT_PATH", non_existent)

    with pytest.raises((FileNotFoundError, ValueError)):
        _load_synthesis_prompt()


# ─────────────────────────────────────────────────────────────────────────────
# Opus 모델 플래그
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_opus_model_flag_passed_when_env_set(tmp_path, monkeypatch, synthesis_prompt_file):
    """AC-018: AI_REPORT_DEEP_MODEL=opus → stream_claude_synthesis(model='opus') 호출."""
    monkeypatch.setenv("AI_REPORT_DEEP_MODEL", "opus")

    collection_result = _make_collection_result(5)

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        d = tmp_path / f"staging_{code}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    captured_model = []

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        captured_model.append(model)
        yield DoneSignal()

    mock_save = MagicMock(return_value="2026-04-16.md")

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)
    monkeypatch.setattr(_svc_mod, "save_report", mock_save)

    async for _ in stream_deep_analysis("005930", "삼성전자"):
        pass

    assert captured_model, "stream_claude_synthesis가 호출되지 않음"
    assert captured_model[0] == "opus", f"model 인자: {captured_model[0]}"


@pytest.mark.asyncio
async def test_default_model_when_env_not_set(tmp_path, monkeypatch, synthesis_prompt_file):
    """AI_REPORT_DEEP_MODEL 미설정 → model=None으로 stream_claude_synthesis 호출."""
    monkeypatch.delenv("AI_REPORT_DEEP_MODEL", raising=False)

    collection_result = _make_collection_result(5)

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        d = tmp_path / f"staging_{code}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    captured_model = []

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        captured_model.append(model)
        yield DoneSignal()

    mock_save = MagicMock(return_value="2026-04-16.md")

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)
    monkeypatch.setattr(_svc_mod, "save_report", mock_save)

    async for _ in stream_deep_analysis("005930", "삼성전자"):
        pass

    assert captured_model, "stream_claude_synthesis가 호출되지 않음"
    assert captured_model[0] is None, f"기본 model은 None이어야 함, 실제: {captured_model[0]}"


# ─────────────────────────────────────────────────────────────────────────────
# 커버리지 보완 테스트
# ─────────────────────────────────────────────────────────────────────────────


def test_load_synthesis_prompt_empty_file(tmp_path, monkeypatch):
    """빈 합성 프롬프트 파일 → ValueError 발생."""
    empty_file = tmp_path / "empty_prompt.md"
    empty_file.write_text("   \n  ", encoding="utf-8")  # 공백만 있는 파일
    monkeypatch.setattr(_svc_mod, "_SYNTHESIS_PROMPT_PATH", empty_file)

    with pytest.raises(ValueError, match="비어 있"):
        _load_synthesis_prompt()


@pytest.mark.asyncio
async def test_streamer_error_signal_propagated(tmp_path, monkeypatch, synthesis_prompt_file):
    """ErrorSignal 이벤트가 SSE error로 변환됨."""
    collection_result = _make_collection_result(5)

    async def mock_collect(code, stock_name, **kwargs):
        return collection_result

    def mock_staging(code, result, **kwargs):
        d = tmp_path / f"staging_{code}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    async def mock_streamer(cwd, prompt, system_prompt, model=None, **kwargs):
        yield ErrorSignal("Claude CLI 내부 오류")

    monkeypatch.setattr(_svc_mod, "collect_all_sources", mock_collect)
    monkeypatch.setattr(_svc_mod, "create_staging_directory", mock_staging)
    monkeypatch.setattr(_svc_mod, "stream_claude_synthesis", mock_streamer)

    events = []
    async for event in stream_deep_analysis("005930", "삼성전자"):
        events.append(event)

    error_events = [e for e in events if e.get("event") == "error"]
    assert error_events, "ErrorSignal이 SSE error로 변환되지 않음"
    assert "Claude CLI 내부 오류" in error_events[0]["data"]


def test_cleanup_stale_staging_dirs(tmp_path):
    """_cleanup_stale_staging_dirs: 오래된 디렉토리 삭제, 신규는 유지."""
    import os
    import time as time_mod

    # 오래된 디렉토리 (생성 후 mtime 조작)
    old_dir = tmp_path / "analysis_005930_20260101T000000Z_abcd1234"
    old_dir.mkdir()
    old_time = time_mod.time() - (8 * 86400)  # 8일 전
    os.utime(old_dir, (old_time, old_time))

    # 신규 디렉토리 (현재 시각)
    new_dir = tmp_path / "analysis_000660_20260416T120000Z_efgh5678"
    new_dir.mkdir()

    # 비-analysis 디렉토리 (패턴 불일치, 무시되어야 함)
    other_dir = tmp_path / "other_dir"
    other_dir.mkdir()

    deleted = _cleanup_stale_staging_dirs(base_dir=tmp_path, max_age_days=7)

    assert deleted == 1, f"삭제 수: {deleted}"
    assert not old_dir.exists(), "오래된 디렉토리가 삭제되지 않음"
    assert new_dir.exists(), "신규 디렉토리가 삭제되면 안 됨"
    assert other_dir.exists(), "비-analysis 디렉토리가 삭제되면 안 됨"
