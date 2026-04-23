"""SPEC-AI-REPORT-003 Step 1: Codex CLI subprocess 어댑터.

Codex CLI (`codex exec ...`) 를 asyncio 서브프로세스로 호출해 Fast/Deep 모드의
심층 리서치 markdown 을 `--output-last-message` 경로에 생성한다. Perplexity API
전면 대체(SPEC-AI-REPORT-003) 의 하위 어댑터 레이어로, 이 모듈 위에 Step 3
(Deep Mode) / Step 4 (Fast Mode) 가 쌓인다.

subprocess 관리 계약 (기존 `claude_cli_streamer` 패턴 복제):
- terminate → wait(_PROC_GRACE_PERIOD_SEC) → kill 2단계 정리
- stderr 백그라운드 drain (마지막 50 라인 보관) → 실패 시 진단
- `asyncio.timeout()` 로 감싸 타임아웃 시 좀비 방지
- `CancelledError` 는 re-raise (삼키지 않음) + finally 에서 정리 보장

에러 분류 (ER-001 ~ ER-004, plan.md):
- `binary_missing`: argv[0] 이 PATH 에 없음 (FileNotFoundError). 재시도 금지 사유.
- `auth`: stderr 에 "not logged in" 등 인증 실패 마커 포함. 재시도 금지 사유.
- `timeout`: `asyncio.TimeoutError`. 1회 재시도 허용 (상위 레이어 판단).
- `empty_output`: exit 0 이지만 output 파일 미생성 또는 0바이트. 1회 재시도 허용.
- `exit_error`: 기타 비정상 종료 (returncode != 0).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# 프롬프트 템플릿 경로 및 플레이스홀더
# ─────────────────────────────────────────────────────────────────────────────

# backend/services/codex_cli_runner.py → backend/prompts/codex_prompt.md
_PROMPT_TEMPLATE_PATH: Path = Path(__file__).resolve().parent.parent / "prompts" / "codex_prompt.md"

# 치환 필요한 플레이스홀더 (fail-fast 검증 대상)
_REQUIRED_PLACEHOLDERS: tuple[str, ...] = ("〈종목명〉", "〈종목코드〉")

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

# terminate 후 kill 까지 대기 시간 (claude_cli_streamer 와 동일)
_PROC_GRACE_PERIOD_SEC = 15.0

# stderr 보관 tail 라인 수 — 실패 시 사용자/로그에 넘길 진단 메시지 한도
_STDERR_TAIL_LINES = 50

# asyncio.StreamReader 버퍼 한도 — Codex json 이벤트가 대용량일 가능성 대비 (claude 와 동일)
_STREAM_BUFFER_LIMIT = 4 * 1024 * 1024

# stderr 에 포함되면 'auth' 로 분류할 소문자 마커 (ER-002)
_AUTH_FAIL_MARKERS: tuple[str, ...] = (
    "not logged in",
    "authentication failed",
    "login required",
    "please run `codex login`",
)


# ─────────────────────────────────────────────────────────────────────────────
# 결과 타입
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CodexResult:
    """Codex CLI 단일 호출 결과.

    Attributes:
        success: `output_path` 에 유효한 markdown 이 기록되었는지.
        output_path: 요청된 출력 파일 경로 (실패 시에도 요청 경로 그대로 보관).
        char_count: 기록된 파일 크기(바이트 기준). 실패 시 0.
        error_type: 실패 유형. 성공 시 None.
            - "binary_missing" | "auth" | "timeout" | "empty_output" | "exit_error"
        error_message: 실패 시 진단 메시지 (stderr tail 또는 예외 메시지). 성공 시 None.
        duration_ms: 호출 총 소요 시간 (밀리초).
    """

    success: bool
    output_path: Path | None
    char_count: int
    error_type: str | None
    error_message: str | None
    duration_ms: int


# ─────────────────────────────────────────────────────────────────────────────
# 내부 유틸
# ─────────────────────────────────────────────────────────────────────────────


def _build_argv(
    *,
    output_path: Path,
    prompt: str,
    working_dir: Path,
) -> list[str]:
    """실제 Codex CLI 호출 argv 구성 (plan.md §Step 1 사양)."""
    return [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "-C",
        str(working_dir),
        "--output-last-message",
        str(output_path),
        "--color",
        "never",
        "--json",
        prompt,
    ]


async def _terminate_proc(proc: asyncio.subprocess.Process) -> None:
    """서브프로세스를 terminate → (대기) → kill 순서로 안전하게 종료.

    이미 종료됐거나 ProcessLookupError 발생 시 조용히 통과.
    Grace period 내에 종료 못하면 강제 kill 후 reap.
    """
    if proc.returncode is not None:
        return

    try:
        proc.terminate()
    except ProcessLookupError:
        return

    try:
        await asyncio.wait_for(proc.wait(), timeout=_PROC_GRACE_PERIOD_SEC)
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except ProcessLookupError:
            pass
        with contextlib.suppress(Exception):
            await proc.wait()


def _is_auth_failure(stderr_lines: list[str]) -> bool:
    """stderr tail 에 auth 실패 마커가 포함돼 있는지 검사 (ER-002)."""
    for line in stderr_lines:
        lower = line.lower()
        for marker in _AUTH_FAIL_MARKERS:
            if marker in lower:
                return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# 공개 API — 프롬프트 로더 (Step 2)
# ─────────────────────────────────────────────────────────────────────────────


def load_codex_prompt(*, code: str, stock_name: str) -> str:
    """`codex_prompt.md` 템플릿을 로드하고 플레이스홀더를 치환한다.

    Args:
        code: 종목 코드 (예: "006400").
        stock_name: 종목명 (예: "Samsung SDI").

    Returns:
        치환된 프롬프트 문자열. Fast Mode 와 Deep Mode 모두에서 동일 템플릿 사용.

    Raises:
        FileNotFoundError: 템플릿 파일이 존재하지 않음.
        ValueError: 템플릿에 필수 플레이스홀더가 없거나, 치환 후에도 잔존하는 경우
            (fail-fast — Codex 호출 전에 즉시 실패해 운영 리포트 품질 보호).
    """
    if not _PROMPT_TEMPLATE_PATH.exists():
        raise FileNotFoundError(
            f"Codex 프롬프트 템플릿 미존재: {_PROMPT_TEMPLATE_PATH}"
        )

    raw = _PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")

    # 1) 템플릿이 기대하는 플레이스홀더를 모두 포함하는지 선검증
    missing = [p for p in _REQUIRED_PLACEHOLDERS if p not in raw]
    if missing:
        raise ValueError(
            f"Codex 프롬프트 템플릿에 필수 플레이스홀더 누락: {missing} "
            f"({_PROMPT_TEMPLATE_PATH})"
        )

    # 2) 치환
    rendered = raw.replace("〈종목명〉", stock_name).replace("〈종목코드〉", code)

    # 3) 치환 후에도 플레이스홀더가 잔존하면 실패 (사용자 입력이 플레이스홀더와
    #    정확히 일치하는 방어적 경로 — 실전에서는 발생하지 않아야 정상)
    for placeholder in _REQUIRED_PLACEHOLDERS:
        if placeholder in rendered:
            raise ValueError(
                f"플레이스홀더 치환 실패: '{placeholder}' 가 여전히 남아있습니다. "
                f"입력값이 플레이스홀더 문자열과 동일한지 확인하세요."
            )

    return rendered


# ─────────────────────────────────────────────────────────────────────────────
# 공개 API — Codex CLI 호출
# ─────────────────────────────────────────────────────────────────────────────


# @MX:ANCHOR: [AUTO] run_codex_research — 계약 경계 (Fast Mode + Deep Mode + 단위 테스트 호출).
# @MX:REASON: finally invariant — CancelledError/TimeoutError 발생해도 subprocess 정리 보장.
#             이 불변식이 깨지면 codex 프로세스가 서버 재시작 전까지 좀비로 남는다.
# @MX:WARN: [AUTO] asyncio.create_subprocess_exec + --output-last-message 로컬 파일 쓰기.
# @MX:REASON: terminate→kill 2단계 cleanup 과 stderr tail buffer 없으면 blind failure 발생.
async def run_codex_research(
    *,
    code: str,
    stock_name: str,
    output_path: Path,
    prompt: str | None = None,
    timeout: float = 600.0,
    working_dir: Path | None = None,
    _cmd_override: list[str] | None = None,
) -> CodexResult:
    """Codex CLI 를 호출해 심층 리서치 markdown 을 `output_path` 에 기록한다.

    Args:
        code: 종목 코드 (예: "006400"). Codex 호출 자체에는 직접 전달되지 않고
            로그/진단 용도로 사용된다. 실제 전달은 `prompt` 안에 포함시킨다.
        stock_name: 종목명 (예: "Samsung SDI"). `code` 와 동일 용도.
        output_path: `--output-last-message` 대상 경로. 호출 전에 상위 디렉토리가
            존재해야 한다 (Step 3 `prepare_staging_directory` 가 보장).
        prompt: Codex 에 전달할 합성 프롬프트. `_cmd_override` 를 쓰지 않는
            실제 호출에서는 필수.
        timeout: 전체 호출 타임아웃 (초). 기본 600초 (NFR-001).
        working_dir: `codex -C` 옵션 경로. None 이면 `output_path.parent` 사용.
        _cmd_override: 테스트 전용 — argv 전체 치환. 지정 시 argv 자동 구성 대신
            이 리스트를 그대로 subprocess 에 투입하고, prompt/working_dir 은 무시한다.

    Returns:
        `CodexResult` — 성공/실패 + 에러 분류 + 진단 메시지.

    Raises:
        asyncio.CancelledError: 상위 Task 가 cancel 된 경우 re-raise. 이 예외 경로에서도
            finally 블록의 `_terminate_proc` 가 subprocess 정리를 보장한다.
        ValueError: `_cmd_override` 없이 `prompt` 도 누락된 경우.
    """
    start = time.monotonic()

    if _cmd_override is not None:
        argv = list(_cmd_override)
    else:
        if prompt is None:
            raise ValueError(
                "prompt 는 필수입니다 (테스트에서는 _cmd_override 를 사용하세요)"
            )
        cwd = working_dir if working_dir is not None else output_path.parent
        argv = _build_argv(
            output_path=output_path,
            prompt=prompt,
            working_dir=cwd,
        )

    stderr_tail: deque[str] = deque(maxlen=_STDERR_TAIL_LINES)
    proc: asyncio.subprocess.Process | None = None
    stderr_task: asyncio.Task[None] | None = None
    stdout_task: asyncio.Task[None] | None = None

    async def _drain_stderr(stream: asyncio.StreamReader) -> None:
        """stderr 라인을 tail buffer 와 logger 에 동시에 흘린다."""
        try:
            async for raw in stream:
                line = raw.decode("utf-8", errors="replace").rstrip()
                if line:
                    stderr_tail.append(line)
                    logger.warning("[codex stderr] %s", line[:500])
        except Exception:  # noqa: BLE001
            # drain 실패는 본 흐름을 막지 않는다
            pass

    async def _drain_stdout(stream: asyncio.StreamReader) -> None:
        """stdout 은 버퍼 블로킹 방지용으로 단순 소진 (내용은 사용하지 않음)."""
        try:
            while True:
                chunk = await stream.read(8192)
                if not chunk:
                    break
        except Exception:  # noqa: BLE001
            pass

    try:
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=_STREAM_BUFFER_LIMIT,
            )
        except FileNotFoundError as exc:
            # ER-001 — argv[0] 이 PATH 에 없음. 재시도 금지 (결정론적 실패).
            logger.error(
                "Codex 바이너리 미설치 (code=%s, argv[0]=%s): %s",
                code, argv[0] if argv else "<empty>", exc,
            )
            return CodexResult(
                success=False,
                output_path=output_path,
                char_count=0,
                error_type="binary_missing",
                error_message=f"Codex 바이너리를 찾을 수 없습니다: {exc}",
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        assert proc.stdout is not None
        assert proc.stderr is not None

        stderr_task = asyncio.create_task(_drain_stderr(proc.stderr))
        stdout_task = asyncio.create_task(_drain_stdout(proc.stdout))

        try:
            async with asyncio.timeout(timeout):
                await proc.wait()
        except asyncio.TimeoutError:
            # ER-003 — 타임아웃. terminate→kill 2단계 정리 후 timeout 결과 반환.
            logger.error(
                "Codex 타임아웃 (code=%s, stock=%s, %.1f초 초과)",
                code, stock_name, timeout,
            )
            await _terminate_proc(proc)
            return CodexResult(
                success=False,
                output_path=output_path,
                char_count=0,
                error_type="timeout",
                error_message=f"Codex 타임아웃 ({int(timeout)}초)",
                duration_ms=int((time.monotonic() - start) * 1000),
            )

        # proc.wait() 정상 종료 — drain 태스크 정리 후 결과 판정.
        for task in (stderr_task, stdout_task):
            if task is not None and not task.done():
                with contextlib.suppress(asyncio.CancelledError):
                    await asyncio.wait_for(task, timeout=1.0)

        duration_ms = int((time.monotonic() - start) * 1000)
        returncode = proc.returncode

        if returncode != 0:
            stderr_lines = list(stderr_tail)
            error_type = "auth" if _is_auth_failure(stderr_lines) else "exit_error"
            error_msg = (
                "\n".join(stderr_lines)
                if stderr_lines
                else f"Codex 비정상 종료 (exit={returncode})"
            )
            logger.error(
                "Codex 실패 (code=%s, type=%s, exit=%s): %s",
                code, error_type, returncode, error_msg[:500],
            )
            return CodexResult(
                success=False,
                output_path=output_path,
                char_count=0,
                error_type=error_type,
                error_message=error_msg,
                duration_ms=duration_ms,
            )

        # exit 0 — output 파일 검증 (ER-004)
        if not output_path.exists():
            return CodexResult(
                success=False,
                output_path=output_path,
                char_count=0,
                error_type="empty_output",
                error_message="Codex 가 output 파일을 생성하지 않았습니다",
                duration_ms=duration_ms,
            )

        char_count = output_path.stat().st_size
        if char_count == 0:
            return CodexResult(
                success=False,
                output_path=output_path,
                char_count=0,
                error_type="empty_output",
                error_message="Codex output 파일이 비어 있습니다",
                duration_ms=duration_ms,
            )

        return CodexResult(
            success=True,
            output_path=output_path,
            char_count=char_count,
            error_type=None,
            error_message=None,
            duration_ms=duration_ms,
        )

    except asyncio.CancelledError:
        # 상위 Task 취소 — finally 에서 정리 후 예외 재전파.
        logger.info(
            "Codex 호출 취소됨 (code=%s, stock=%s, CancelledError)",
            code, stock_name,
        )
        raise
    finally:
        if proc is not None:
            await _terminate_proc(proc)
        for task in (stderr_task, stdout_task):
            if task is not None and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
