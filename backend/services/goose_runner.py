"""SPEC-AI-REPORT-004 M3 — goose 실행기: `claude -p` 하위 프로세스 1회 실행.

설계: design.md §3(명령·프롬프트·환경 변수·종료·진행 단계), §4.1(종료 사유 표),
§5.2(리포트 선택 규칙 — 분류에 필요한 선택만 하고 복사는 M5 작업 서비스가 한다).

경계(design §8): 무결성 검사·쿼터·실행 중 작업 등록·`runs/{job_id}/` 생성은 작업 서비스
(M4)가 실행기 호출 전에 한다. 실행기는 프로세스를 띄우고, stream-json을 진행 단계로 바꿔
콜백으로 넘기고, 끝나면 종료 사유를 분류해 ``RunResult``로 돌려준다.

취소: 실행 중인 ``run_goose`` 태스크를 cancel하면 프로세스 그룹을 종료한 뒤
``asyncio.CancelledError``를 다시 던진다. 상태 ``cancelled``(취소 요청·서버 종료)는
작업 서비스가 정한다(§4.1 — ``cancelled``는 오류 종류가 아니다).
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import re
import signal
import time
from collections import deque
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.services.goose_harness import resolve_harness_dir

logger = logging.getLogger(__name__)

ENV_MODEL = "AI_REPORT_GOOSE_MODEL"
DEFAULT_MODEL = "sonnet"
ENV_TIMEOUT = "AI_REPORT_GOOSE_TIMEOUT"
# design §3.4: M1 P4 352.8초 × 2를 5분 단위로 올린 값(표본 1회)
DEFAULT_TIMEOUT_SEC = 900.0
DEFAULT_GRACE_SEC = 15.0
# design §3.3: 부모 환경에 있는 것만 넘긴다. 인증용 추가 변수는 없다.
ENV_ALLOWLIST = ("PATH", "HOME", "USER", "LANG", "LC_ALL", "TZ", "TMPDIR", "SHELL")
STDERR_TAIL_LINES = 50
LINE_LIMIT_BYTES = 4 * 1024 * 1024
# 리더 프로세스가 끝난 뒤 남은 출력을 기다리는 시간(초)
DRAIN_SEC = 2.0
_POLL_SEC = 0.1

_KST = timezone(timedelta(hours=9))
_CODE_PATTERN = re.compile(r"^\d{6}$")
_JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# stderr 인증 실패 문구(소문자 비교). AC-006은 `not logged in`.
_AUTH_MARKERS = ("not logged in", "please run /login", "invalid api key", "authentication_error")
_WORKFLOWS_MARK = ".claude/skills/goose/workflows/"


@dataclass(frozen=True)
class ProgressEvent:
    """진행 단계 이벤트(design §3.5). ``detail``은 ``fetch_start``의 설명 문구만 채운다."""

    stage: str
    detail: str | None = None


@dataclass
class RunResult:
    """실행 1회의 결과. ``status``는 ``done`` 또는 ``error``(취소는 예외로 전달)."""

    status: str
    error_kind: str | None
    exit_code: int | None
    delivery_status: str | None = None  # 선택된 리포트: "final" | "draft" | None
    report_dir: Path | None = None
    stderr_tail: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Invocation:
    argv: list[str]
    cwd: Path


# ─────────────────────────────────────────────────────────────────────────────
# 설정·명령 구성
# ─────────────────────────────────────────────────────────────────────────────


def resolve_model(environ: Mapping[str, str]) -> str:
    return environ.get(ENV_MODEL) or DEFAULT_MODEL


def resolve_timeout(environ: Mapping[str, str]) -> float:
    """`AI_REPORT_GOOSE_TIMEOUT`(초). 숫자가 아니거나 0 이하면 기본 900초."""
    raw = environ.get(ENV_TIMEOUT)
    if not raw:
        return DEFAULT_TIMEOUT_SEC
    try:
        value = float(raw)
    except ValueError:
        logger.warning("%s 값이 숫자가 아님(%r) — 기본값 사용", ENV_TIMEOUT, raw)
        return DEFAULT_TIMEOUT_SEC
    return value if value > 0 else DEFAULT_TIMEOUT_SEC


def build_prompt(stock_name: str, code: str, job_id: str, as_of: datetime | None = None) -> str:
    """design §3.2 프롬프트. 사용자 자유 입력은 없다 — 코드·작업 ID는 형식을 검사한다."""
    if not _CODE_PATTERN.fullmatch(code or ""):
        raise ValueError(f"종목 코드 형식 오류: {code!r}")
    if not _JOB_ID_PATTERN.fullmatch(job_id or ""):
        raise ValueError(f"작업 ID 형식 오류: {job_id!r}")
    stamp = (as_of or datetime.now(_KST)).isoformat(timespec="seconds")
    return (
        f"/goose {stock_name}({code}) 종목을 분석해줘.\n"
        f"기준일: {stamp}. 범위: 전체 기업 보고서(company_report).\n"
        f"작업 디렉터리: runs/{job_id}. 질문 없이 진행하고 가정은 runs/{job_id}/assumptions.md에 기록하세요."
    )


# @MX:ANCHOR: [AUTO] build_invocation — design §3.1 argv의 단일 정의(실행기·AC-002 테스트).
# @MX:REASON: 권한 우회 플래그 금지, --settings·--strict-mcp-config 누락 시 리포 밖에서
#             allow 무시·계정 커넥터 MCP 부착(M1 측정). argv를 바꾸면 SPEC design §3.1도 바꿔야 한다.
def build_invocation(
    prompt: str,
    *,
    environ: Mapping[str, str] | None = None,
    claude_bin: str = "claude",
) -> Invocation:
    """argv와 cwd(하네스 경로)를 구성한다(design §3.1)."""
    env = os.environ if environ is None else environ
    harness_dir = resolve_harness_dir(env)
    argv = [
        claude_bin,
        "-p", prompt,
        "--output-format", "stream-json",
        "--verbose",
        "--setting-sources", "project",
        "--settings", str(harness_dir / ".claude" / "settings.json"),
        "--strict-mcp-config",
        "--permission-mode", "dontAsk",
        "--no-session-persistence",
        "--model", resolve_model(env),
    ]
    return Invocation(argv=argv, cwd=harness_dir)


def build_env(parent: Mapping[str, str]) -> dict[str, str]:
    """허용 목록 방식 환경 변수(REQ-004). 목록에 없는 키는 모두 버린다."""
    return {key: parent[key] for key in ENV_ALLOWLIST if key in parent}


# ─────────────────────────────────────────────────────────────────────────────
# 리포트 선택·종료 사유 분류
# ─────────────────────────────────────────────────────────────────────────────


def _regular_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def select_report(job_dir: Path) -> tuple[str, Path] | None:
    """design §5.2 선택 규칙. 모델이 출력한 경로는 쓰지 않고 작업 디렉터리만 본다.

    M5 작업 서비스는 이 결과로 복사 원본을 정한다. 심볼릭 링크 리포트는 없는 것으로 본다.
    """
    final_dir = job_dir / "final"
    if _regular_file(final_dir / "report.html"):
        validation = final_dir / "render-validation.json"
        try:
            allowed = _regular_file(validation) and json.loads(validation.read_text()).get(
                "delivery_allowed"
            ) is True
        except (OSError, ValueError, AttributeError):
            allowed = False
        if allowed:
            return "final", final_dir
    draft_dir = job_dir / "draft"
    if _regular_file(draft_dir / "report.html"):
        return "draft", draft_dir
    return None


def is_auth_failure(stderr_lines: list[str]) -> bool:
    text = "\n".join(stderr_lines).lower()
    return any(marker in text for marker in _AUTH_MARKERS)


def classify_exit(
    *, timed_out: bool, exit_code: int | None, stderr_tail: list[str], report_selected: bool
) -> tuple[str, str | None]:
    """design §4.1 표(실행기가 관측하는 부분). 무결성·취소는 작업 서비스 몫이다."""
    if timed_out:
        return "error", "timeout"
    if exit_code == 0:
        return ("done", None) if report_selected else ("error", "empty_output")
    if is_auth_failure(stderr_tail):
        return "error", "auth"
    return "error", "exit_error"


# ─────────────────────────────────────────────────────────────────────────────
# stream-json → 진행 단계
# ─────────────────────────────────────────────────────────────────────────────


class StageMapper:
    """design §3.5 측정 표. 알 수 없는 타입·깨진 JSON은 무시하고 예외를 던지지 않는다."""

    def __init__(self, job_id: str) -> None:
        self._input_suffix = f"runs/{job_id}/input.json"

    def feed(self, line: str) -> list[ProgressEvent]:
        try:
            data = json.loads(line)
        except (ValueError, TypeError):
            if line.strip():
                logger.debug("stream-json 줄 무시(깨진 JSON): %r", line[:200])
            return []
        if not isinstance(data, dict):
            return []
        kind = data.get("type")
        if kind == "system":
            return self._system(data)
        if kind == "result":
            return [ProgressEvent("session_end")]
        if kind == "assistant":
            return self._assistant(data)
        return []

    def _system(self, data: dict) -> list[ProgressEvent]:
        subtype = data.get("subtype")
        if subtype == "init":
            return [ProgressEvent("goose_start")]
        if subtype == "task_notification":
            return [ProgressEvent("fetch_done")]
        if subtype == "permission_denied":
            logger.warning("goose 세션 permission_denied: %s", str(data)[:300])
        return []

    def _assistant(self, data: dict) -> list[ProgressEvent]:
        message = data.get("message")
        if not isinstance(message, dict):
            return []
        content = message.get("content")
        if not isinstance(content, list):
            return []
        is_sub = bool(data.get("parent_tool_use_id"))
        events: list[ProgressEvent] = []
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue
            inp = item.get("input")
            if not isinstance(inp, dict):
                continue
            stage = self._tool_stage(str(item.get("name")), inp, is_sub)
            if stage is not None:
                events.append(stage)
        return events

    def _tool_stage(self, name: str, inp: dict, is_sub: bool) -> ProgressEvent | None:
        if is_sub:
            # 서브에이전트는 WebFetch만 집계한다(원문 열람 횟수)
            return ProgressEvent("research_tick") if name == "WebFetch" else None
        if name == "Read" and _WORKFLOWS_MARK in str(inp.get("file_path", "")):
            return ProgressEvent("plan")
        if name == "WebSearch":
            return ProgressEvent("research_tick")
        if name == "Agent" and inp.get("subagent_type") == "web-fetch":
            return ProgressEvent("fetch_start", detail=str(inp.get("description") or ""))
        if name == "Write" and str(inp.get("file_path", "")).endswith(self._input_suffix):
            return ProgressEvent("compose")
        if name == "Bash":
            return _bash_stage(str(inp.get("command", "")))
        return None


def _bash_stage(command: str) -> ProgressEvent | None:
    if "audit_report.py" in command:
        return ProgressEvent("audit")
    if "render_report.py" in command and "--help" not in command:
        return ProgressEvent("render_final" if "--final" in command else "render_draft")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# 프로세스 그룹 종료
# ─────────────────────────────────────────────────────────────────────────────


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# @MX:WARN: [AUTO] 프로세스 그룹 전체에 신호를 보낸다(SIGTERM → 유예 → SIGKILL).
# @MX:REASON: claude는 서브에이전트·Bash 손자 프로세스를 띄운다. 직계 자식만 죽이면 손자가
#             남는다(AC-005). pgid는 start_new_session으로 만든 그룹이어야 하며 서버 자신의
#             그룹을 넘기면 서버가 죽는다 — run_goose 밖에서 호출할 때 주의.
async def terminate_group(pgid: int, grace_sec: float) -> None:
    """``os.killpg(pgid, SIGTERM)`` → 유예 → 남아 있으면 SIGKILL. 없는 그룹은 종료로 본다."""
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + max(grace_sec, 0.0)
    while time.monotonic() < deadline:
        if not _group_alive(pgid):
            return
        await asyncio.sleep(0.05)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return


# ─────────────────────────────────────────────────────────────────────────────
# 실행
# ─────────────────────────────────────────────────────────────────────────────

EventCallback = Callable[[ProgressEvent], Awaitable[None] | None]


async def _read_stdout(stream: asyncio.StreamReader, mapper: StageMapper, on_event: EventCallback) -> None:
    while True:
        try:
            raw = await stream.readline()
        except ValueError:
            # 4MB를 넘는 줄: 버퍼가 비워지므로 다음 줄부터 계속 읽는다
            logger.warning("stream-json 줄이 %d바이트를 넘어 버림", LINE_LIMIT_BYTES)
            continue
        if not raw:
            return
        for event in mapper.feed(raw.decode("utf-8", errors="replace")):
            outcome = on_event(event)
            if inspect.isawaitable(outcome):
                await outcome


async def _read_stderr(stream: asyncio.StreamReader, tail: deque[str]) -> None:
    while True:
        try:
            raw = await stream.readline()
        except ValueError:
            continue
        if not raw:
            return
        tail.append(raw.decode("utf-8", errors="replace").rstrip("\n"))


# @MX:ANCHOR: [AUTO] run_goose — M4 작업 서비스의 실행 진입점(시작·취소·서버 종료 경로가 모두 거친다).
# @MX:REASON: 어떤 경로로 끝나도(정상·시간 초과·취소) 프로세스 그룹을 남기지 않는 것이 불변 조건이다.
async def run_goose(
    *,
    job_id: str,
    stock_name: str,
    code: str,
    on_event: EventCallback,
    environ: Mapping[str, str] | None = None,
    claude_bin: str = "claude",
    timeout_sec: float | None = None,
    grace_sec: float = DEFAULT_GRACE_SEC,
    as_of: datetime | None = None,
) -> RunResult:
    """goose 세션 1회를 실행하고 종료 사유를 분류한다.

    ``environ``은 부모 환경(기본 os.environ) — 하네스 경로·모델·시간 상한을 읽고,
    허용 목록 변수만 하위 프로세스에 넘긴다. 취소되면 그룹 종료 후 CancelledError를 다시 던진다.
    """
    env = dict(os.environ if environ is None else environ)
    prompt = build_prompt(stock_name, code, job_id, as_of)
    inv = build_invocation(prompt, environ=env, claude_bin=claude_bin)
    limit = resolve_timeout(env) if timeout_sec is None else timeout_sec
    job_dir = inv.cwd / "runs" / job_id
    tail: deque[str] = deque(maxlen=STDERR_TAIL_LINES)

    try:
        proc = await asyncio.create_subprocess_exec(
            *inv.argv,
            cwd=str(inv.cwd),
            env=build_env(env),
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
            limit=LINE_LIMIT_BYTES,
        )
    except FileNotFoundError:
        logger.error("goose 실행 파일 없음: %s", claude_bin)
        return RunResult(status="error", error_kind="binary_missing", exit_code=None)

    pgid = proc.pid  # start_new_session → 새 세션·새 그룹의 리더
    mapper = StageMapper(job_id)
    timed_out = False

    async def _drive() -> None:
        assert proc.stdout is not None and proc.stderr is not None
        readers = asyncio.gather(
            _read_stdout(proc.stdout, mapper, on_event),
            _read_stderr(proc.stderr, tail),
        )
        try:
            # asyncio의 proc.wait()는 파이프가 모두 닫혀야 돌아온다. 손자가 파이프를 쥐고
            # 있으면 리더가 끝나도 기다리므로, returncode(리더 종료 즉시 설정)를 폴링한다.
            while proc.returncode is None and not readers.done():
                await asyncio.wait([readers], timeout=_POLL_SEC)
            if not readers.done():
                # 리더는 끝났는데 출력이 안 닫힘: 잠깐 더 읽은 뒤 그룹을 종료해 파이프를 닫는다
                # (리더 exit 0을 시간 초과로 오분류하지 않기 위해).
                try:
                    await asyncio.wait_for(asyncio.shield(readers), timeout=DRAIN_SEC)
                except asyncio.TimeoutError:
                    await terminate_group(pgid, grace_sec)
                    await readers
            await proc.wait()
        finally:
            if not readers.done():
                readers.cancel()
                await asyncio.gather(readers, return_exceptions=True)

    try:
        await asyncio.wait_for(_drive(), timeout=limit)
    except asyncio.TimeoutError:
        timed_out = True
        logger.warning("goose 작업 %s 시간 초과(%.1f초) — 프로세스 그룹 종료", job_id, limit)
    finally:
        # 정상 종료여도 손자 프로세스가 남을 수 있으므로 그룹을 항상 정리한다.
        # 취소(CancelledError) 중에도 정리가 끝날 때까지 기다린다.
        await asyncio.shield(_cleanup(proc, pgid, grace_sec))

    selected = select_report(job_dir)
    status, kind = classify_exit(
        timed_out=timed_out,
        exit_code=proc.returncode,
        stderr_tail=list(tail),
        report_selected=selected is not None,
    )
    return RunResult(
        status=status,
        error_kind=kind,
        exit_code=None if timed_out else proc.returncode,
        delivery_status=selected[0] if selected else None,
        report_dir=selected[1] if selected else None,
        stderr_tail=list(tail),
    )


async def _cleanup(proc: asyncio.subprocess.Process, pgid: int, grace_sec: float) -> None:
    if _group_alive(pgid):
        await terminate_group(pgid, grace_sec)
    if proc.returncode is None:
        try:
            await asyncio.wait_for(proc.wait(), timeout=max(grace_sec, 0.0) + 5.0)
        except asyncio.TimeoutError:
            logger.error("goose 프로세스 %d 회수 실패", proc.pid)
