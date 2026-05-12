"""SPEC-AI-REPORT-001 v1.1.4 회귀 테스트.

테스트 대상:
- _sanitize_name(): 파일 경로 조작 방지 보안 (CRITICAL)
- get_report_content(): path traversal 차단
- save_report(): 동일 날짜 시퀀스 처리
- load_prompt(): 프롬프트 로드 + 종목명 치환
- check_rate_limit(): 일일 쿼터 + 분당 버스트
"""

from __future__ import annotations

import importlib
import os
import sys
import time
import types
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def service_module(monkeypatch, tmp_path):
    """깨끗한 상태의 ai_report_service 모듈 직접 로드.

    backend.services.__init__.py가 다른 서비스들을 연쇄 import하므로,
    importlib.util.spec_from_file_location으로 격리 로드하여 my_chart 전체 로드 회피.

    - my_chart.registry 스텁 (실제 DB 의존 회피)
    - _REPORTS_BASE를 tmp_path로 패치
    - 모듈 레벨 상태(_active_analyses, rate limiter) 초기화
    """
    import importlib.util

    # registry 스텁 (ai_report_service가 from my_chart.registry import _name)
    sys.modules["my_chart.registry"] = types.SimpleNamespace(
        _name=lambda code: "테스트종목" if code == "000000" else "NonName"
    )

    # 서비스 파일 직접 로드
    svc_path = Path(__file__).parent.parent / "services" / "ai_report_service.py"
    spec = importlib.util.spec_from_file_location("_test_ai_report_service", svc_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 보관 경로를 임시 디렉토리로
    monkeypatch.setattr(mod, "_REPORTS_BASE", tmp_path)
    # 모듈 레벨 상태 초기화
    mod._active_analyses.clear()
    mod._daily_call_count = 0
    mod._daily_reset_date = ""
    mod._recent_call_timestamps.clear()
    # 테스트용 완화된 제한 설정
    monkeypatch.setattr(mod, "AI_REPORT_DAILY_QUOTA", 5)
    monkeypatch.setattr(mod, "AI_REPORT_BURST_LIMIT", 2)
    monkeypatch.setattr(mod, "AI_REPORT_BURST_WINDOW_SEC", 2)

    yield mod


# ─────────────────────────────────────────────────────────────────────────────
# _sanitize_name 보안 테스트 (CRITICAL)
# ─────────────────────────────────────────────────────────────────────────────


class TestSanitizeName:
    """경로 조작 공격 방지 검증."""

    def test_normal_korean_name(self, service_module):
        assert service_module._sanitize_name("삼성전자") == "삼성전자"

    def test_normal_mixed_name(self, service_module):
        assert service_module._sanitize_name("LG에너지솔루션") == "LG에너지솔루션"

    def test_forbidden_path_chars_removed(self, service_module):
        """/, \\, :, *, ?, ", <, >, | 제거."""
        assert service_module._sanitize_name('evil/path\\:name*?"<>|') == "evilpathname"

    def test_parent_directory_traversal_blocked(self, service_module):
        """`..` 시퀀스는 `_`로 치환되어 경로 이탈 불가."""
        result = service_module._sanitize_name("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_leading_dot_stripped(self, service_module):
        """선행 점은 제거됨 (숨김 파일 방지)."""
        assert service_module._sanitize_name(".hidden") == "hidden"

    def test_multiple_dots_collapsed(self, service_module):
        """연속된 점은 단일 언더스코어로."""
        result = service_module._sanitize_name("a...b")
        assert ".." not in result

    def test_windows_reserved_name_prefixed(self, service_module):
        """Windows 예약명은 `_` 접두사 부여."""
        for reserved in ("CON", "NUL", "COM1", "LPT9", "aux"):
            result = service_module._sanitize_name(reserved)
            assert result.startswith("_"), f"{reserved} should be prefixed"

    def test_control_chars_removed(self, service_module):
        """제어 문자(\\x00-\\x1f) 제거."""
        assert service_module._sanitize_name("name\x00\x01\x1ftest") == "nametest"

    def test_null_byte_removed(self, service_module):
        """널 바이트 제거 (poisoning 방지)."""
        assert "\x00" not in service_module._sanitize_name("a\x00b")

    def test_empty_string_fallback(self, service_module):
        """빈 문자열은 `report`로 폴백."""
        assert service_module._sanitize_name("") == "report"
        assert service_module._sanitize_name("...") == "report"
        assert service_module._sanitize_name("   ") == "report"

    def test_length_limit(self, service_module):
        """100자 초과 시 자름."""
        long_name = "가" * 200
        result = service_module._sanitize_name(long_name)
        assert len(result) <= 100

    def test_nfkc_normalization(self, service_module):
        """NFKC 정규화로 전각/반각 통일."""
        # 전각 영문 A → 반각 A
        result = service_module._sanitize_name("Ａ")
        assert result == "A"


# ─────────────────────────────────────────────────────────────────────────────
# get_report_content: path traversal 방지
# ─────────────────────────────────────────────────────────────────────────────


class TestGetReportContent:
    def test_rejects_invalid_filename_format(self, service_module):
        """YYYY-MM-DD(_N).md 형식 아닌 것 거부."""
        assert service_module.get_report_content("테스트", "../../etc/passwd") is None
        assert service_module.get_report_content("테스트", "arbitrary.md") is None
        assert service_module.get_report_content("테스트", "2026-04-12.txt") is None

    def test_accepts_valid_filename_but_not_exists(self, service_module):
        """형식은 맞으나 파일 없으면 None."""
        assert service_module.get_report_content("테스트", "2026-04-12.md") is None

    def test_accepts_sequence_filename(self, service_module, tmp_path):
        """시퀀스 포함 파일명 허용."""
        (tmp_path / "테스트").mkdir()
        content_file = tmp_path / "테스트" / "2026-04-12_3.md"
        content_file.write_text("테스트 내용", encoding="utf-8")

        result = service_module.get_report_content("테스트", "2026-04-12_3.md")
        assert result == "테스트 내용"

    def test_path_traversal_in_stock_name_blocked(self, service_module):
        """stock_name에 경로 조작 시도해도 sanitize 후 안전."""
        # stock_name에 ".." 포함 시 sanitize로 제거되므로 파일이 있을 수 없음
        assert service_module.get_report_content("../../etc", "2026-04-12.md") is None


# ─────────────────────────────────────────────────────────────────────────────
# save_report: 동일 날짜 시퀀스
# ─────────────────────────────────────────────────────────────────────────────


class TestSaveReport:
    def test_saves_basic_report(self, service_module, tmp_path):
        filename = service_module.save_report("테스트", "# 내용")
        assert filename.endswith(".md")
        saved = tmp_path / "테스트" / filename
        assert saved.exists()
        assert saved.read_text(encoding="utf-8") == "# 내용"

    def test_same_day_sequence_increment(self, service_module, tmp_path):
        """같은 날 중복 호출 시 _2, _3 시퀀스."""
        f1 = service_module.save_report("종목", "첫번째")
        f2 = service_module.save_report("종목", "두번째")
        f3 = service_module.save_report("종목", "세번째")

        assert "_2" in f2 or f2 != f1
        assert "_3" in f3 or f3 != f2
        # 모든 파일이 존재해야 함
        assert (tmp_path / "종목" / f1).exists()
        assert (tmp_path / "종목" / f2).exists()
        assert (tmp_path / "종목" / f3).exists()


# ─────────────────────────────────────────────────────────────────────────────
# load_prompt: 프롬프트 치환
# ─────────────────────────────────────────────────────────────────────────────


# SPEC-AI-REPORT-003: TestLoadPrompt 제거됨 — load_prompt / _load_prompt_template /
# _PROMPT_TEMPLATE_PATH / SYSTEM_PROMPT / SEARCH_DOMAIN_FILTER 가 전부 삭제됨.
# Codex 프롬프트 로더 테스트는 test_codex_cli_runner.py::test_load_codex_prompt_* 참고.


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiting (CRITICAL 보안)
# ─────────────────────────────────────────────────────────────────────────────


class TestRateLimit:
    def test_allows_within_burst_limit(self, service_module):
        """분당 한도(2회) 내에서는 통과."""
        service_module.check_rate_limit()
        service_module.check_rate_limit()

    def test_blocks_burst_exceeded(self, service_module):
        """분당 한도 초과 시 RateLimitError."""
        service_module.check_rate_limit()
        service_module.check_rate_limit()
        with pytest.raises(service_module.RateLimitError) as exc_info:
            service_module.check_rate_limit()
        assert "분당" in str(exc_info.value) or "한도" in str(exc_info.value)

    def test_burst_window_resets(self, service_module):
        """버스트 윈도우 경과 후 재허용."""
        service_module.check_rate_limit()
        service_module.check_rate_limit()
        # 윈도우(2초) 경과
        time.sleep(2.1)
        # 재호출 가능해야 함
        service_module.check_rate_limit()

    def test_blocks_daily_quota(self, service_module):
        """일일 쿼터(5회) 초과 시 RateLimitError."""
        # 윈도우 충분히 기다리며 5회 호출
        for _ in range(5):
            service_module.check_rate_limit()
            time.sleep(2.1)  # 버스트 윈도우 회피

        with pytest.raises(service_module.RateLimitError) as exc_info:
            service_module.check_rate_limit()
        assert "일일" in str(exc_info.value) or "쿼터" in str(exc_info.value)


# ─────────────────────────────────────────────────────────────────────────────
# get_stock_name
# ─────────────────────────────────────────────────────────────────────────────


class TestGetStockName:
    def test_valid_code_returns_name(self, service_module):
        assert service_module.get_stock_name("000000") == "테스트종목"

    def test_invalid_code_returns_none(self, service_module):
        assert service_module.get_stock_name("999999") is None


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-003 Step 4 — stream_codex_fast
# ─────────────────────────────────────────────────────────────────────────────


def _load_codex_runner_into_sys_modules():
    """codex_cli_runner 를 실 모듈로 로드해 sys.modules 에 등록.

    주의: 다른 테스트 파일이 stub 을 sys.modules 에 심어둔 상태면 cached 반환 시
    run_codex_research/CodexResult 가 누락되므로, 실 모듈이 아닌 경우 강제 재로드한다.
    """
    import importlib.util
    codex_path = Path(__file__).parent.parent / "services" / "codex_cli_runner.py"
    module_name = "backend.services.codex_cli_runner"
    existing = sys.modules.get(module_name)
    if existing is not None and hasattr(existing, "run_codex_research"):
        return existing
    spec = importlib.util.spec_from_file_location(module_name, codex_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def codex_mod():
    return _load_codex_runner_into_sys_modules()


def _make_codex_result(
    codex_mod, *, success, error_type=None, error_message=None, char_count=0, output_path=None
):
    return codex_mod.CodexResult(
        success=success,
        output_path=output_path,
        char_count=char_count,
        error_type=error_type,
        error_message=error_message,
        duration_ms=50,
    )


class TestStreamCodexFast:
    """Codex Fast Mode SSE 스트림 계약 (SPEC-AI-REPORT-003 FR-001/FR-004)."""

    @pytest.mark.asyncio
    async def test_yields_chunks_and_done_on_success(self, service_module, codex_mod, monkeypatch):
        """성공 시 시작 phase → markdown 청크 여러 개 → done 이벤트 순서로 yield."""
        async def fake_run(**kwargs):
            markdown = "# 헤더\n" + "가나다라마" * 100  # 500자 내외
            kwargs["output_path"].write_text(markdown, encoding="utf-8")
            return _make_codex_result(
                codex_mod, success=True, char_count=len(markdown), output_path=kwargs["output_path"]
            )

        monkeypatch.setattr(codex_mod, "run_codex_research", fake_run)

        events = []
        async for evt in service_module.stream_codex_fast("Samsung SDI", "006400"):
            events.append(evt)

        phase_events = [e for e in events if e.get("event") == "phase"]
        data_events = [e for e in events if "data" in e and not e.get("event")]
        done_events = [e for e in events if e.get("event") == "done"]

        assert len(phase_events) >= 1, "시작 phase 이벤트 없음"
        assert any(
            "codex_fast_start" in (e.get("data") or "") for e in phase_events
        ), "codex_fast_start phase 이벤트 미검출"
        assert len(data_events) >= 1, "markdown 청크 이벤트 없음"
        assert len(done_events) == 1, "done 이벤트 정확히 1개 필요"

        total = "".join(e["data"] for e in data_events)
        assert "# 헤더" in total

    @pytest.mark.asyncio
    async def test_emits_error_on_codex_failure(self, service_module, codex_mod, monkeypatch):
        """Codex 실패 시 error 이벤트 yield, data 이벤트 없음."""
        async def fake_run(**kwargs):
            return _make_codex_result(
                codex_mod,
                success=False,
                error_type="timeout",
                error_message="Codex 타임아웃 (600초)",
                output_path=kwargs["output_path"],
            )

        monkeypatch.setattr(codex_mod, "run_codex_research", fake_run)

        events = []
        async for evt in service_module.stream_codex_fast("Samsung SDI", "006400"):
            events.append(evt)

        error_events = [e for e in events if e.get("event") == "error"]
        data_events = [e for e in events if "data" in e and not e.get("event")]

        assert len(error_events) == 1, "error 이벤트 정확히 1개 필요"
        assert "timeout" in error_events[0]["data"]
        assert len(data_events) == 0, "실패 시 markdown 청크 없어야 함"

    @pytest.mark.asyncio
    async def test_heartbeat_emitted_during_long_run(self, service_module, codex_mod, monkeypatch):
        """Codex subprocess 가 heartbeat 주기보다 오래 걸리면 progress phase 이벤트 yield."""
        monkeypatch.setattr(service_module, "_CODEX_FAST_HEARTBEAT_SEC", 0.1)

        async def fake_run(**kwargs):
            import asyncio
            await asyncio.sleep(0.35)  # heartbeat 2~3회 emit 기대
            kwargs["output_path"].write_text("# 완료", encoding="utf-8")
            return _make_codex_result(
                codex_mod, success=True, char_count=5, output_path=kwargs["output_path"]
            )

        monkeypatch.setattr(codex_mod, "run_codex_research", fake_run)

        events = []
        async for evt in service_module.stream_codex_fast("Samsung SDI", "006400"):
            events.append(evt)

        progress_phases = [
            e for e in events
            if e.get("event") == "phase" and "codex_fast_progress" in (e.get("data") or "")
        ]
        assert len(progress_phases) >= 1, "heartbeat progress phase 이벤트 미검출"

    @pytest.mark.asyncio
    async def test_save_report_called_on_success(self, service_module, codex_mod, monkeypatch):
        """성공 시 save_report 가 markdown 전체 내용과 함께 호출됨."""
        save_calls = []

        def fake_save(stock_name, content):
            save_calls.append((stock_name, content))
            return "2026-04-23.md"

        async def fake_run(**kwargs):
            markdown = "# 최종 리포트\n본문"
            kwargs["output_path"].write_text(markdown, encoding="utf-8")
            return _make_codex_result(
                codex_mod, success=True, char_count=len(markdown), output_path=kwargs["output_path"]
            )

        monkeypatch.setattr(codex_mod, "run_codex_research", fake_run)
        monkeypatch.setattr(service_module, "save_report", fake_save)

        async for _ in service_module.stream_codex_fast("Samsung SDI", "006400"):
            pass

        assert len(save_calls) == 1
        assert save_calls[0][0] == "Samsung SDI"
        assert "# 최종 리포트" in save_calls[0][1]

    @pytest.mark.asyncio
    async def test_prompt_error_yields_error_event_no_subprocess(
        self, service_module, codex_mod, monkeypatch
    ):
        """load_codex_prompt 가 실패하면 subprocess 호출 없이 즉시 error 이벤트."""
        run_call_count = 0

        async def fake_run(**kwargs):
            nonlocal run_call_count
            run_call_count += 1
            return _make_codex_result(
                codex_mod, success=True, output_path=kwargs["output_path"]
            )

        def fake_load_prompt(**kwargs):
            raise FileNotFoundError("템플릿 없음")

        monkeypatch.setattr(codex_mod, "run_codex_research", fake_run)
        monkeypatch.setattr(codex_mod, "load_codex_prompt", fake_load_prompt)

        events = []
        async for evt in service_module.stream_codex_fast("Samsung SDI", "006400"):
            events.append(evt)

        error_events = [e for e in events if e.get("event") == "error"]
        assert len(error_events) == 1
        assert "프롬프트 로드 실패" in error_events[0]["data"]
        assert run_call_count == 0, "프롬프트 실패 시 codex 호출되어서는 안 됨"
