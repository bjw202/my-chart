"""Claude CLI stream-json 라인 파서 + 서브프로세스 종료 함수.

SPEC-AI-REPORT-002 Phase A (FR-004, FR-005, ER-004)에서 만든 모듈을
SPEC-AI-REPORT-004 M7에서 축소했다: 옛 Deep 합성 실행기(`stream_claude_synthesis`)는
Deep 파이프라인과 함께 삭제하고, 라인 파서와 종료 함수만 남긴다(plan.md §3 축소 대상).

역할:
- stream-json 포맷 라인 파싱 → 타입화된 이벤트 객체 변환
- 서브프로세스 terminate → kill 순서 종료
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass

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


# @MX:NOTE: [AUTO] parse_stream_json_line — 계약: unknown type / JSONDecodeError → None, 예외를 raise하지 않음.
# SPEC-AI-REPORT-004 M7에서 호출자(stream_claude_synthesis)가 삭제되어 fan_in이 테스트 1곳으로 줄어 ANCHOR → NOTE 강등.
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
# 서브프로세스 종료
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
