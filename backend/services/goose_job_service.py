"""SPEC-AI-REPORT-004 M4 — goose 작업 서비스: 시작 판정·상태 기계·이벤트 재생·취소·종료 정리.

설계: design.md §4.1(상태 기계), §4.2(메모리 구조), §4.3(시작 판정 4~8단계), §4.4(재생),
§4.5(실행 중 작업 조회), §4.6(서버 종료), §8(라우터는 1~3단계, start()는 4~8단계를 잠금 하나 안에서).

경계:
- 무결성 검사는 goose_harness.check_job_integrity(), 실행은 goose_runner.run_goose()에 맡긴다.
- 리포트 복사·job.json(M5)은 ``on_finish`` 훅으로 붙인다. 훅이 돌려준 dict는 종료 이벤트
  데이터에 합쳐진다(run, report_url, interrupted 등). M4 기본값은 훅 없음.
- 쿼터는 goose 전용(`AI_REPORT_GOOSE_DAILY_QUOTA`, 기본 5)이며 Fast·옛 Deep 카운터와 무관하다.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.services import goose_harness, goose_runner

logger = logging.getLogger(__name__)

ENV_DAILY_QUOTA = "AI_REPORT_GOOSE_DAILY_QUOTA"
DEFAULT_DAILY_QUOTA = 5
MAX_FINISHED_JOBS = 50
TERMINAL_STATES = ("done", "error", "cancelled")

_KST = timezone(timedelta(hours=9))

# 종료 이벤트 `error`의 사용자 안내 문구(design §4.4 — {error_kind, message})
_ERROR_MESSAGES = {
    "integrity": "goose 하네스 무결성 검사에 실패해 분석을 시작하지 않았습니다.",
    "binary_missing": "claude 실행 파일을 찾을 수 없습니다.",
    "auth": "claude 인증에 실패했습니다. 서버에서 로그인 상태를 확인하세요.",
    "timeout": "분석 시간이 상한을 넘어 중단했습니다.",
    "empty_output": "분석이 끝났지만 리포트가 만들어지지 않았습니다.",
    "exit_error": "분석 프로세스가 비정상 종료했습니다.",
}


# ─────────────────────────────────────────────────────────────────────────────
# goose 전용 일일 쿼터 (옛 Deep 레이트 리밋을 대체 — Fast·Deep 카운터와 공유하지 않음)
# ─────────────────────────────────────────────────────────────────────────────


class GooseRateLimiter:
    """KST 날짜별 goose 시작 횟수. 판정(exhausted)과 차감(consume)을 나눠 8단계에서만 차감한다."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(_KST))
        self._counts: dict[str, int] = {}

    @property
    def quota(self) -> int:
        raw = os.environ.get(ENV_DAILY_QUOTA)
        if not raw:
            return DEFAULT_DAILY_QUOTA
        try:
            value = int(raw)
        except ValueError:
            logger.warning("%s 값이 정수가 아님(%r) — 기본값 %d 사용", ENV_DAILY_QUOTA, raw, DEFAULT_DAILY_QUOTA)
            return DEFAULT_DAILY_QUOTA
        return max(value, 0)

    def _today(self) -> str:
        return self._clock().astimezone(_KST).strftime("%Y-%m-%d")

    def used(self) -> int:
        return self._counts.get(self._today(), 0)

    def exhausted(self) -> bool:
        return self.used() >= self.quota

    def consume(self) -> None:
        today = self._today()
        # 지난 날짜 키는 남길 이유가 없다
        self._counts = {today: self._counts.get(today, 0) + 1}


# ─────────────────────────────────────────────────────────────────────────────
# 작업·이벤트
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class JobEvent:
    seq: int
    type: str
    data: dict[str, Any]


@dataclass
class Job:
    job_id: str
    code: str
    stock_name: str
    status: str = "running"
    error_kind: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(_KST))
    finished_at: datetime | None = None
    cancel_reason: str | None = None
    result: dict[str, Any] = field(default_factory=dict)
    events: list[JobEvent] = field(default_factory=list)
    cond: asyncio.Condition = field(default_factory=asyncio.Condition)
    task: asyncio.Task | None = None

    @property
    def finished(self) -> bool:
        return self.status in TERMINAL_STATES


@dataclass(frozen=True)
class StartOutcome:
    """start() 판정 결과. kind: started | existing | busy | rate_limit | integrity.

    busy면 ``job``은 실행 중인 다른 종목 작업(라우터가 종목명을 안내에 쓴다), rate_limit면 None.
    """

    kind: str
    job: Job | None


Runner = Callable[..., Awaitable[goose_runner.RunResult]]
FinishHook = Callable[[Job, "goose_runner.RunResult | None"], Any]


def _default_runs_root() -> Path:
    return goose_harness.resolve_harness_dir() / "runs"


def _default_integrity() -> goose_harness.IntegrityResult:
    return goose_harness.check_job_integrity()


class GooseJobService:
    """서버 전체 goose 작업 관리(동시 실행 1개, D10). 단일 uvicorn 워커 전제."""

    def __init__(
        self,
        *,
        runner: Runner | None = None,
        integrity_check: Callable[[], goose_harness.IntegrityResult] | None = None,
        limiter: GooseRateLimiter | None = None,
        runs_root: Callable[[], Path] | None = None,
        on_finish: FinishHook | None = None,
        max_finished: int = MAX_FINISHED_JOBS,
    ) -> None:
        self._runner: Runner = runner or goose_runner.run_goose
        self._integrity = integrity_check or _default_integrity
        self.limiter = limiter or GooseRateLimiter()
        self._runs_root = runs_root or _default_runs_root
        self._on_finish = on_finish
        self._max_finished = max_finished
        self._jobs: dict[str, Job] = {}
        self._active_job_id: str | None = None
        # @MX:WARN: [AUTO] 판정-후-등록 전체를 묶는 단일 잠금(design §4.2·§8).
        # @MX:REASON: 무결성 검사가 스레드로 넘어가며 await가 생긴다. 잠금 밖에서 4~8단계를 판정하면
        #             동시 요청 두 개가 모두 통과해 서버 전체 동시 1개(D10)와 쿼터가 깨진다(B5 테스트).
        self._lock = asyncio.Lock()

    # ── 조회 ────────────────────────────────────────────────────────────────

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def active(self) -> dict[str, str] | None:
        """design §4.5: 실행 중 작업 또는 None. 무결성 실패 작업은 등록되지 않는다."""
        job = self._jobs.get(self._active_job_id) if self._active_job_id else None
        if job is None or job.finished:
            return None
        return {"job_id": job.job_id, "code": job.code, "stock_name": job.stock_name, "status": job.status}

    # ── 시작 ────────────────────────────────────────────────────────────────

    # @MX:ANCHOR: [AUTO] start — goose 작업 시작 판정 4~8단계의 단일 정의(REQ-AIR4-008, design §4.3).
    # @MX:REASON: 라우터(mode=deep)·테스트·M6 프론트 흐름이 이 순서에 의존한다. 같은 종목 → 다른 종목
    #             → 쿼터 → 무결성 → 등록 순서를 바꾸면 AC-007·008, AC-001 (2b)(3)(4)가 깨진다.
    #             무결성 실패는 실행·쿼터 차감·active 등록 없이 error/integrity 작업만 남긴다(닫힌 실패).
    async def start(self, code: str, stock_name: str) -> StartOutcome:
        async with self._lock:
            running = self._jobs.get(self._active_job_id) if self._active_job_id else None
            if running is not None and not running.finished:
                if running.code == code:  # 4. 같은 종목 실행 중 → 기존 작업
                    return StartOutcome("existing", running)
                return StartOutcome("busy", running)  # 5. 다른 종목 실행 중
            if self.limiter.exhausted():  # 6. 일일 쿼터 소진
                return StartOutcome("rate_limit", None)
            integrity = await asyncio.to_thread(self._integrity)  # 7. 무결성(파일 해시 — 스레드)
            job = Job(job_id=uuid.uuid4().hex, code=code, stock_name=stock_name)
            self._jobs[job.job_id] = job
            if not integrity.ok:
                logger.error("goose 작업 %s 무결성 실패 — 실행하지 않음: %s", job.job_id, integrity.reason)
                await self._finish(job, "error", "integrity", {})
                return StartOutcome("integrity", job)
            # 8. 작업 디렉터리 → active 등록 → 쿼터 차감 → 백그라운드 태스크
            (self._runs_root() / job.job_id).mkdir(parents=True, exist_ok=True)
            self._active_job_id = job.job_id
            self.limiter.consume()
            job.task = asyncio.create_task(self._run(job), name=f"goose-{job.job_id}")
            logger.info("goose 작업 시작 %s (%s %s), 쿼터 %d/%d",
                        job.job_id, code, stock_name, self.limiter.used(), self.limiter.quota)
            return StartOutcome("started", job)

    # ── 실행 ────────────────────────────────────────────────────────────────

    async def _run(self, job: Job) -> None:
        async def on_event(ev: goose_runner.ProgressEvent) -> None:
            await self._emit(job, "progress", {"stage": ev.stage, "detail": ev.detail})

        try:
            result = await self._runner(
                job_id=job.job_id, stock_name=job.stock_name, code=job.code, on_event=on_event
            )
        except asyncio.CancelledError:
            # 실행기는 그룹을 정리한 뒤 CancelledError를 다시 던진다(M3). 취소는 오류 종류가 아니다.
            reason = job.cancel_reason or "cancel"
            logger.info("goose 작업 %s 취소(사유 %s)", job.job_id, reason)
            extra = await self._call_finish_hook(job, None)
            await self._finish(job, "cancelled", None, extra)
            raise
        except Exception:  # noqa: BLE001 - 실행기 밖 예외도 작업을 종료 상태로 닫는다
            logger.exception("goose 작업 %s 실행 중 예외", job.job_id)
            extra = await self._call_finish_hook(job, None)
            await self._finish(job, "error", "exit_error", extra)
            return
        extra = await self._call_finish_hook(job, result)
        if result.status == "done":
            data = {"delivery_status": result.delivery_status, **extra}
            await self._finish(job, "done", None, data)
        else:
            await self._finish(job, "error", result.error_kind or "exit_error", extra)

    async def _call_finish_hook(self, job: Job, result: goose_runner.RunResult | None) -> dict[str, Any]:
        if self._on_finish is None:
            return {}
        try:
            outcome = self._on_finish(job, result)
            if inspect.isawaitable(outcome):
                outcome = await outcome
        except Exception:  # noqa: BLE001 - 보관 실패는 종료 상태를 바꾸지 않는다(best-effort)
            logger.exception("goose 작업 %s 종료 훅 실패", job.job_id)
            return {}
        return dict(outcome) if isinstance(outcome, dict) else {}

    async def _emit(self, job: Job, type_: str, data: dict[str, Any]) -> None:
        async with job.cond:
            job.events.append(JobEvent(len(job.events) + 1, type_, data))
            job.cond.notify_all()

    async def _finish(self, job: Job, status: str, error_kind: str | None, extra: dict[str, Any]) -> None:
        """종료 상태 기록 → active 해제 → 종료 이벤트. 종료 상태는 다시 바뀌지 않는다."""
        if job.finished:
            return
        job.status = status
        job.error_kind = error_kind
        job.finished_at = datetime.now(_KST)
        job.result = dict(extra)
        if self._active_job_id == job.job_id:
            self._active_job_id = None
        if status == "error":
            data = {"error_kind": error_kind, "message": _ERROR_MESSAGES.get(error_kind or "", ""), **extra}
        else:
            data = dict(extra)
        await self._emit(job, status, data)
        self._prune()

    def _prune(self) -> None:
        finished = [j for j in self._jobs.values() if j.finished]
        for job in finished[: max(len(finished) - self._max_finished, 0)]:
            del self._jobs[job.job_id]

    # ── 구독 (design §4.4) ──────────────────────────────────────────────────

    async def subscribe(self, job_id: str, after: int = 0) -> AsyncIterator[JobEvent]:
        """``after``보다 큰 순번의 이벤트를 재생한 뒤 실시간으로 전달한다. 종료 이벤트 뒤 끝난다.

        없는 작업은 KeyError. 구독을 끊어도(제너레이터 닫힘) 작업 태스크는 영향받지 않는다.
        """
        job = self._jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        idx = max(after, 0)
        while True:
            async with job.cond:
                if idx >= len(job.events) and job.finished:
                    return
                await job.cond.wait_for(lambda: len(job.events) > idx)
                pending = job.events[idx:]
            idx += len(pending)
            for event in pending:
                yield event
                if event.type in TERMINAL_STATES:
                    return

    # ── 취소·종료 ───────────────────────────────────────────────────────────

    async def cancel(self, job_id: str, reason: str = "cancel") -> Job | None:
        """실행 중이면 태스크를 취소하고 종료 정리까지 기다린다. 끝난 작업은 그대로, 없는 작업은 None."""
        job = self._jobs.get(job_id)
        if job is None:
            return None
        if job.finished or job.task is None:
            return job
        job.cancel_reason = reason
        job.task.cancel()
        await asyncio.gather(job.task, return_exceptions=True)
        return job

    async def shutdown(self) -> None:
        """design §4.6: lifespan 종료 시 실행 중 작업을 사유 `shutdown`으로 끝낸다(상태 cancelled)."""
        if self._active_job_id is not None:
            await self.cancel(self._active_job_id, reason="shutdown")


# @MX:WARN: [AUTO] 프로세스 전역 작업 서비스 — 라우터·lifespan이 같은 인스턴스를 쓴다.
# @MX:REASON: 서버 전체 동시 1개(D10)와 이벤트 재생은 단일 uvicorn 워커의 메모리 상태에 의존한다.
#             워커를 늘리면 작업이 워커별로 갈라진다. 테스트는 set_service()로 교체한다.
_service = GooseJobService()


def get_service() -> GooseJobService:
    return _service


def set_service(service: GooseJobService) -> None:
    global _service
    _service = service
