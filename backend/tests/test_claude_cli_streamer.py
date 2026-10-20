"""SPEC-AI-REPORT-002 Phase A — Claude CLI 스트리머 단위 테스트.

테스트 대상:
- parse_stream_json_line(): stream-json 라인 파서
- _terminate_proc(): 서브프로세스 terminate → kill 종료

AC-007: stream-json 파싱
SPEC-AI-REPORT-004 M7: 옛 Deep 합성 실행기(stream_claude_synthesis) 삭제와 함께
그 실행기를 대상으로 한 시험(타임아웃·좀비 정리·argv 조립·출력 파싱 통합)도 삭제했다.

격리 방식: importlib.util.spec_from_file_location으로 직접 로드하여
backend/services/__init__.py cascade import 회피 (ai_report_service.py 테스트 동일 패턴).
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest


# ─────────────────────────────────────────────────────────────────────────────
# 픽스처: claude_cli_streamer 모듈 격리 로드
# ─────────────────────────────────────────────────────────────────────────────

_STREAMER_PATH = Path(__file__).parent.parent / "services" / "claude_cli_streamer.py"


@pytest.fixture(scope="module")
def streamer():
    """claude_cli_streamer 모듈을 직접 로드하여 cascade import 없이 격리 테스트."""
    spec = importlib.util.spec_from_file_location("_test_claude_cli_streamer", _STREAMER_PATH)
    assert spec and spec.loader, f"모듈 스펙 로드 실패: {_STREAMER_PATH}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_test_claude_cli_streamer"] = mod
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
# parse_stream_json_line 테스트
# ─────────────────────────────────────────────────────────────────────────────


def test_parse_assistant_event(streamer):
    """type=assistant + content[].type=text → TextDelta 반환 (AC-007)."""
    line = json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "# 삼성전자"}]
            },
        }
    )
    result = streamer.parse_stream_json_line(line)
    assert isinstance(result, streamer.TextDelta)
    assert result.text == "# 삼성전자"


def test_parse_result_event(streamer):
    """type=result,subtype=success → DoneSignal 반환 (AC-007)."""
    line = json.dumps({"type": "result", "subtype": "success", "cost_usd": 0.01})
    result = streamer.parse_stream_json_line(line)
    assert isinstance(result, streamer.DoneSignal)


def test_parse_error_event(streamer):
    """type=system,subtype=error → ErrorSignal(message) 반환 (AC-007)."""
    line = json.dumps(
        {"type": "system", "subtype": "error", "message": "rate limit exceeded"}
    )
    result = streamer.parse_stream_json_line(line)
    assert isinstance(result, streamer.ErrorSignal)
    assert result.message == "rate limit exceeded"


def test_ignore_unknown_type(streamer):
    """알 수 없는 type → None 반환, 예외 없음 (AC-007)."""
    line = json.dumps({"type": "unknown_future_type", "data": {}})
    result = streamer.parse_stream_json_line(line)
    assert result is None


def test_malformed_json_skipped(streamer):
    """JSONDecodeError → None 반환, 예외를 바깥으로 전파하지 않음 (AC-007)."""
    line = "{not valid json"
    result = streamer.parse_stream_json_line(line)
    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# 추가 커버리지 테스트: 엣지 케이스
# ─────────────────────────────────────────────────────────────────────────────


def test_parse_assistant_no_text_content(streamer):
    """type=assistant이지만 text 타입 content가 없는 경우 → None 반환."""
    line = json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [{"type": "tool_use", "id": "abc"}]
            },
        }
    )
    result = streamer.parse_stream_json_line(line)
    assert result is None


def test_parse_assistant_empty_content(streamer):
    """type=assistant이지만 content 배열이 빈 경우 → None 반환."""
    line = json.dumps({"type": "assistant", "message": {"content": []}})
    result = streamer.parse_stream_json_line(line)
    assert result is None


def test_parse_system_non_error_subtype(streamer):
    """type=system이지만 subtype이 error가 아닌 경우 → None 반환."""
    line = json.dumps({"type": "system", "subtype": "init", "message": "started"})
    result = streamer.parse_stream_json_line(line)
    assert result is None


def test_parse_error_event_default_message(streamer):
    """type=system,subtype=error에 message 필드가 없는 경우 기본 메시지 반환."""
    line = json.dumps({"type": "system", "subtype": "error"})
    result = streamer.parse_stream_json_line(line)
    assert isinstance(result, streamer.ErrorSignal)
    assert result.message == "알 수 없는 오류"


@pytest.mark.asyncio
async def test_terminate_proc_already_terminated(streamer):
    """이미 종료된 프로세스를 _terminate_proc에 넘겨도 예외 없이 처리."""
    proc = await asyncio.create_subprocess_exec(
        "true",  # 즉시 종료
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await proc.wait()  # 완전히 종료 대기
    assert proc.returncode is not None

    # 이미 종료된 proc → returncode is not None → 즉시 반환
    await streamer._terminate_proc(proc)  # 예외 없어야 함


@pytest.mark.asyncio
async def test_terminate_proc_process_lookup_error_on_terminate(streamer):
    """proc.terminate()가 ProcessLookupError를 raise하면 조용히 반환 (경쟁 조건 방어)."""
    from unittest.mock import AsyncMock, MagicMock

    mock_proc = MagicMock()
    mock_proc.returncode = None  # 종료되지 않은 것처럼 보임
    mock_proc.terminate = MagicMock(side_effect=ProcessLookupError("already gone"))
    mock_proc.wait = AsyncMock(return_value=0)

    # ProcessLookupError 발생 시 예외 없이 반환해야 함
    await streamer._terminate_proc(mock_proc)
    mock_proc.terminate.assert_called_once()
    mock_proc.wait.assert_not_called()  # terminate 실패 시 wait 호출 안 함


@pytest.mark.asyncio
async def test_terminate_proc_kill_on_grace_timeout(streamer):
    """_terminate_proc에서 grace period 내 종료 실패 시 kill 호출 (121-130 라인 커버).

    모듈의 _PROC_GRACE_PERIOD_SEC를 임시로 0.1초로 변경하여
    asyncio.wait_for TimeoutError → kill 경로를 빠르게 검증.
    """
    call_log: list[str] = []
    killed = False

    # grace period 동안은 느리게, kill 이후 wait는 즉시 반환하는 mock proc
    class SlowThenFastProc:
        returncode = None

        def terminate(self) -> None:
            call_log.append("terminate")

        def kill(self) -> None:
            nonlocal killed
            killed = True
            call_log.append("kill")

        async def wait(self) -> int:
            call_log.append("wait")
            if not killed:
                await asyncio.sleep(999)  # grace period보다 오래 (kill 전)
            return 0  # kill 후 즉시 반환

    # 모듈의 _PROC_GRACE_PERIOD_SEC를 직접 패치 (모듈 레벨 변수)
    original = streamer._PROC_GRACE_PERIOD_SEC
    try:
        streamer._PROC_GRACE_PERIOD_SEC = 0.1
        proc = SlowThenFastProc()
        await streamer._terminate_proc(proc)
    finally:
        streamer._PROC_GRACE_PERIOD_SEC = original

    assert "terminate" in call_log
    assert "kill" in call_log
