"""Claude CLI 헤드리스 스트리머: stream-json 파서 + 서브프로세스 관리.

SPEC-AI-REPORT-002 Phase A (FR-004, FR-005, FR-007, ER-004, ER-005)

역할:
- stream-json 포맷 라인 파싱 → 타입화된 이벤트 객체 변환
- asyncio.create_subprocess_exec으로 'claude -p' 실행
- 타임아웃/CancelledError 시 서브프로세스 정리 보장
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncGenerator

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 스트림 이벤트 타입
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TextDelta:
    """마크다운 텍스트 청크 — type=assistant 이벤트에서 추출."""

    text: str


@dataclass(frozen=True)
class DoneSignal:
    """스트림 완료 신호 — type=result 이벤트에서 생성."""


@dataclass(frozen=True)
class ErrorSignal:
    """에러 신호 — type=system+subtype=error 또는 타임아웃/프로세스 오류."""

    message: str


# Union 타입 별칭
StreamEvent = TextDelta | DoneSignal | ErrorSignal

# subprocess 정리 타임아웃 (terminate → kill 대기)
_PROC_GRACE_PERIOD_SEC = 15.0


# ─────────────────────────────────────────────────────────────────────────────
# stream-json 파서
# ─────────────────────────────────────────────────────────────────────────────


# @MX:ANCHOR: [AUTO] parse_stream_json_line — fan_in >= 2 (오케스트레이터 + 테스트).
# @MX:REASON: Invariant: unknown type / JSONDecodeError → None, 절대 예외를 raise하지 않음.
# 이 계약이 깨지면 스트림 전체가 중단됨.
def parse_stream_json_line(line: str) -> StreamEvent | None:
    """stream-json 한 라인을 파싱하여 StreamEvent 또는 None 반환.

    Args:
        line: Claude CLI stdout의 JSON 라인 (개행 문자 포함 가능).

    Returns:
        TextDelta: type=assistant + content[].type=text 이벤트
        DoneSignal: type=result 이벤트
        ErrorSignal: type=system + subtype=error 이벤트
        None: 알 수 없는 type 또는 JSONDecodeError

    Note:
        JSONDecodeError는 WARNING으로 로그하고 None 반환 — 예외 전파 금지.
        알 수 없는 type은 조용히 무시 (방어적 파싱, 미래 호환성 보장).
    """
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        logger.warning("stream-json 라인 파싱 실패 (JSONDecodeError): %r", line[:200])
        return None

    event_type = data.get("type")

    if event_type == "assistant":
        # content 배열에서 첫 번째 text 청크 추출
        message = data.get("message", {})
        content_list = message.get("content", [])
        for item in content_list:
            if item.get("type") == "text":
                return TextDelta(text=item.get("text", ""))
        return None

    if event_type == "result":
        return DoneSignal()

    if event_type == "system" and data.get("subtype") == "error":
        return ErrorSignal(message=data.get("message", "알 수 없는 오류"))

    # 알 수 없는 type → 조용히 무시 (방어적 파싱)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Claude CLI 서브프로세스 실행기
# ─────────────────────────────────────────────────────────────────────────────


async def _terminate_proc(proc: asyncio.subprocess.Process) -> None:
    """서브프로세스를 terminate → (대기) → kill 순서로 안전하게 종료."""
    if proc.returncode is not None:
        return  # 이미 종료됨

    try:
        proc.terminate()
    except ProcessLookupError:
        return  # 이미 종료됨

    try:
        await asyncio.wait_for(proc.wait(), timeout=_PROC_GRACE_PERIOD_SEC)
    except asyncio.TimeoutError:
        # grace period 내 종료 안 됨 → 강제 kill
        try:
            proc.kill()
        except ProcessLookupError:
            pass  # 이미 종료됨
        try:
            await proc.wait()
        except Exception:
            pass


# @MX:ANCHOR: [AUTO] stream_claude_synthesis — fan_in >= 2 (오케스트레이터 + 테스트).
# @MX:REASON: finally 블록 invariant: CancelledError/TimeoutError 발생 시에도 반드시 subprocess를 terminate→kill.
#             이 블록이 없으면 'claude' 프로세스가 서버 재시작 전까지 좀비로 남을 수 있음.
# @MX:WARN: [AUTO] asyncio.create_subprocess_exec — subprocess 좀비 위험.
# @MX:REASON: finally terminate/kill 이중 보장 필수. TimeoutError/CancelledError 시 leak 방지.
async def stream_claude_synthesis(
    cwd: Path,
    prompt: str,
    system_prompt: str,
    model: str | None = None,
    timeout: float = 180.0,
    _cmd_override: list[str] | None = None,
    _proc_spy: list[asyncio.subprocess.Process] | None = None,
) -> AsyncGenerator[StreamEvent, None]:
    """Claude CLI를 서브프로세스로 실행하여 stream-json 이벤트를 yield.

    Args:
        cwd: Claude CLI가 실행될 작업 디렉토리 (스테이징 디렉토리).
        prompt: 사용자 프롬프트 (-p 인자).
        system_prompt: 시스템 프롬프트 (--append-system-prompt 인자).
        model: "opus"이면 --model claude-opus-4-6 추가. None이면 기본 Sonnet.
        timeout: 전체 합성 타임아웃 (초). 기본값 180초.
        _cmd_override: 테스트용 명령어 오버라이드 (실제 claude 바이너리 대체).
        _proc_spy: 테스트용 프로세스 레퍼런스 수집 리스트.

    Yields:
        TextDelta, DoneSignal, ErrorSignal 중 하나.

    Note:
        CancelledError는 re-raise (삼키지 않음).
        TimeoutError는 ErrorSignal로 변환 후 프로세스 정리.
    """
    if _cmd_override is not None:
        argv = _cmd_override
    else:
        argv = [
            "claude",
            "-p", prompt,
            "--cwd", str(cwd),
            "--append-system-prompt", system_prompt,
            "--allowedTools", "Read,Grep,Glob",
            "--output-format", "stream-json",
            "--verbose",
        ]
        if model == "opus":
            argv += ["--model", "claude-opus-4-6"]

    proc: asyncio.subprocess.Process | None = None

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd) if _cmd_override else None,
        )

        if _proc_spy is not None:
            _proc_spy.append(proc)

        assert proc.stdout is not None

        async def _read_lines() -> AsyncGenerator[StreamEvent, None]:
            """stdout 라인 스트리밍 및 이벤트 파싱."""
            async for raw_line in proc.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                if not line:
                    continue
                event = parse_stream_json_line(line)
                if event is not None:
                    yield event

        try:
            async with asyncio.timeout(timeout):
                async for event in _read_lines():
                    yield event
        except asyncio.TimeoutError:
            error_msg = (
                f"합성 시간 초과 ({int(timeout)}초). "
                "다시 시도하거나 빠른 분석을 사용해 주세요."
            )
            logger.error("Claude CLI 타임아웃: %s초 초과", timeout)
            yield ErrorSignal(message=error_msg)

    except asyncio.CancelledError:
        logger.info("Claude CLI 스트리밍 취소됨 (CancelledError)")
        raise  # CancelledError는 삼키지 않음
    finally:
        if proc is not None:
            await _terminate_proc(proc)
