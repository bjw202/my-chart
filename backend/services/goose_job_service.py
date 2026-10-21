"""SPEC-AI-REPORT-004 M4 — goose 작업 서비스: 시작 판정·상태 기계·이벤트 재생·취소·종료 정리.

설계: design.md §4.1(상태 기계), §4.2(메모리 구조), §4.3(시작 판정 4~8단계), §4.4(재생),
§4.5(실행 중 작업 조회), §4.6(서버 종료), §8(라우터는 1~3단계, start()는 4~8단계를 잠금 하나 안에서).

경계:
- 무결성 검사는 goose_harness.check_job_integrity(), 실행은 goose_runner.run_goose()에 맡긴다.
- 리포트 복사·job.json(M5)은 ``on_finish`` 훅(goose_storage.make_finish_hook)으로 붙인다. 훅이
  돌려준 dict는 종료 이벤트 데이터에 합쳐진다(run, report_url, interrupted 등). 훅은 취소·오류
  경로에서도 불리며, 그 전에 ``job.ending``에 종료 상태를 기록한다. 생성자 기본값은 훅 없음이고
  운영용 모듈 인스턴스에만 보관 훅을 붙인다.
- 하루 실행 횟수 제한은 없다(사용자 결정 2026-10-21 — 단일 사용자). 서버 전체 동시 실행 1개만 지킨다.
- SPEC-AI-REPORT-005: ``prefetcher``(DART 원문 사전 수집기)를 주입하면 백그라운드 태스크가 goose 실행 직전에
  ``runs/<job_id>/dart/``로 수집하고 무결성을 다시 검사한다. 생성자 기본값은 수집기 없음(기존 동작 그대로)이고
  운영용 모듈 인스턴스에만 실제 DART 수집기를 붙인다. 끄기 스위치 `AI_REPORT_GOOSE_DART_PREFETCH=0`의
  소유자는 이 서비스다(REQ-AIR5-004).
- SPEC-AI-REPORT-007: ``naver_prefetcher``(네이버 최신 뉴스 사전 수집기)를 주입하면 DART 수집 뒤·무결성 재검사
  앞에 ``runs/<job_id>/naver/``로 수집한다. 진행 이벤트는 새로 만들지 않는다(REQ-AIR7-004). ``code_check``(서버
  종목 목록 조회)의 결과를 색인 ``code_validated``로 넘기며, 결과와 무관하게 수집은 실행한다(REQ-AIR7-015).
  생성자 기본값은 둘 다 없음이고 운영용 모듈 인스턴스에만 붙인다. 끄기 스위치
  `AI_REPORT_GOOSE_NAVER_PREFETCH=0`의 소유자는 이 서비스다(REQ-AIR7-003).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import os
import shutil
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Collection
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.services import goose_dart_prefetch, goose_harness, goose_naver_prefetch, goose_runner, goose_storage

logger = logging.getLogger(__name__)

ENV_DART_PREFETCH = "AI_REPORT_GOOSE_DART_PREFETCH"  # "0"이면 DART 사전 수집을 끈다(REQ-AIR5-004)
ENV_NAVER_PREFETCH = "AI_REPORT_GOOSE_NAVER_PREFETCH"  # "0"이면 네이버 사전 수집을 끈다(REQ-AIR7-003)
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
    ending: tuple[str, str | None] | None = None  # 훅 호출 직전에 정한 (종료 상태, 오류 종류)
    result: dict[str, Any] = field(default_factory=dict)
    events: list[JobEvent] = field(default_factory=list)
    cond: asyncio.Condition = field(default_factory=asyncio.Condition)
    task: asyncio.Task | None = None

    @property
    def finished(self) -> bool:
        return self.status in TERMINAL_STATES


@dataclass(frozen=True)
class StartOutcome:
    """start() 판정 결과. kind: started | existing | busy | integrity.

    busy면 ``job``은 실행 중인 다른 종목 작업(라우터가 종목명을 안내에 쓴다).
    """

    kind: str
    job: Job | None


Runner = Callable[..., Awaitable[goose_runner.RunResult]]
FinishHook = Callable[[Job, "goose_runner.RunResult | None"], Any]
# 호출 계약: ``await prefetcher(code, out_dir) -> index``. 실패는 색인에 적고 정상 반환, 취소만 전파한다.
Prefetcher = Callable[[str, Path], Awaitable[Any]]
# 호출 계약: ``await naver_prefetcher(code, out_dir, code_validated=<bool>) -> index``. 실패는 색인에 적고
# 정상 반환, 취소만 전파한다(REQ-AIR7-002·008).
NaverPrefetcher = Callable[..., Awaitable[Any]]
CodeCheck = Callable[[str], bool]


def _default_runs_root() -> Path:
    return goose_harness.resolve_harness_dir() / "runs"


def _default_integrity() -> goose_harness.IntegrityResult:
    return goose_harness.check_job_integrity()


# ─────────────────────────────────────────────────────────────────────────────
# 작업 폴더 보존 (design §5.2 "보존 기간은 구현 단계에서 정함" — 사용자 결정 2026-10-20: 최근 10개)
# ─────────────────────────────────────────────────────────────────────────────

ENV_RUNS_KEEP = "AI_REPORT_GOOSE_RUNS_KEEP"
RUNS_KEEP = 10


def runs_keep() -> int:
    """보존할 작업 폴더 수. 환경 변수가 양의 정수가 아니면 기본 10."""
    raw = os.environ.get(ENV_RUNS_KEEP)
    if not raw:
        return RUNS_KEEP
    try:
        value = int(raw)
    except ValueError:
        return RUNS_KEEP
    return value if value > 0 else RUNS_KEEP


# @MX:WARN: [AUTO] 하네스 runs/ 아래 폴더를 지운다(shutil.rmtree).
# @MX:REASON: 지우는 대상은 runs/ 바로 아래의 실제 폴더(심볼릭 링크 아님)이며 resolve() 결과가
#             runs/ 안인지 다시 확인한다. 실행 중 작업 폴더(protect)는 개수와 상관없이 남긴다.
def prune_runs(runs_root: Path, keep: int, protect: Collection[str]) -> list[str]:
    """수정 시각이 최근인 ``keep``개만 남기고 나머지 작업 폴더를 지운다. 지운 이름 목록을 돌려준다."""
    if not runs_root.is_dir():
        return []
    root = runs_root.resolve()
    dirs = []
    for entry in runs_root.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            continue
        if entry.resolve().parent != root:
            continue
        dirs.append(entry)
    dirs.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
    removed: list[str] = []
    for entry in dirs[keep:]:
        if entry.name in protect:
            continue
        shutil.rmtree(entry)
        removed.append(entry.name)
    return removed


class GooseJobService:
    """서버 전체 goose 작업 관리(동시 실행 1개, D10). 단일 uvicorn 워커 전제."""

    def __init__(
        self,
        *,
        runner: Runner | None = None,
        integrity_check: Callable[[], goose_harness.IntegrityResult] | None = None,
        runs_root: Callable[[], Path] | None = None,
        on_finish: FinishHook | None = None,
        prefetcher: Prefetcher | None = None,
        naver_prefetcher: NaverPrefetcher | None = None,
        code_check: CodeCheck | None = None,
        max_finished: int = MAX_FINISHED_JOBS,
    ) -> None:
        self._runner: Runner = runner or goose_runner.run_goose
        self._integrity = integrity_check or _default_integrity
        self._runs_root = runs_root or _default_runs_root
        self._on_finish = on_finish
        self._prefetcher = prefetcher
        self._naver_prefetcher = naver_prefetcher
        self._code_check = code_check
        self._max_finished = max_finished
        self._jobs: dict[str, Job] = {}
        self._active_job_id: str | None = None
        # @MX:WARN: [AUTO] 판정-후-등록 전체를 묶는 단일 잠금(design §4.2·§8).
        # @MX:REASON: 무결성 검사가 스레드로 넘어가며 await가 생긴다. 잠금 밖에서 4~8단계를 판정하면
        #             동시 요청 두 개가 모두 통과해 서버 전체 동시 1개(D10)가 깨진다(B5 테스트).
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
    #             → 무결성 → 등록 순서를 바꾸면 AC-007·008, AC-001 (2b)(3)(4)가 깨진다.
    #             무결성 실패는 실행·active 등록 없이 error/integrity 작업만 남긴다(닫힌 실패).
    #             6단계(일일 쿼터)는 사용자 결정(2026-10-21)으로 없앴다 — 단계 번호는 설계 문서와 맞춰 둔다.
    async def start(self, code: str, stock_name: str) -> StartOutcome:
        async with self._lock:
            running = self._jobs.get(self._active_job_id) if self._active_job_id else None
            if running is not None and not running.finished:
                if running.code == code:  # 4. 같은 종목 실행 중 → 기존 작업
                    return StartOutcome("existing", running)
                return StartOutcome("busy", running)  # 5. 다른 종목 실행 중
            integrity = await asyncio.to_thread(self._integrity)  # 7. 무결성(파일 해시 — 스레드)
            job = Job(job_id=uuid.uuid4().hex, code=code, stock_name=stock_name)
            self._jobs[job.job_id] = job
            if not integrity.ok:
                logger.error("goose 작업 %s 무결성 실패 — 실행하지 않음: %s", job.job_id, integrity.reason)
                await self._finish(job, "error", "integrity", {})
                return StartOutcome("integrity", job)
            # 8. 작업 디렉터리 → active 등록 → 백그라운드 태스크
            runs_root = self._runs_root()
            (runs_root / job.job_id).mkdir(parents=True, exist_ok=True)
            self._prune_runs(runs_root, job.job_id)
            self._active_job_id = job.job_id
            job.task = asyncio.create_task(self._run(job), name=f"goose-{job.job_id}")
            logger.info("goose 작업 시작 %s (%s %s)", job.job_id, code, stock_name)
            return StartOutcome("started", job)

    def _prune_runs(self, runs_root: Path, new_job_id: str) -> None:
        """새 작업 폴더를 만든 직후 오래된 작업 폴더를 정리한다. 실패는 로그만 남긴다(시작은 계속)."""
        protect = {new_job_id} | {j.job_id for j in self._jobs.values() if not j.finished}
        try:
            removed = prune_runs(runs_root, runs_keep(), protect)
        except Exception:  # noqa: BLE001 - 정리 실패가 작업 시작을 막지 않는다
            logger.exception("goose 작업 폴더 정리 실패 (%s)", runs_root)
            return
        if removed:
            logger.info("goose 작업 폴더 %d개 정리: %s", len(removed), ", ".join(removed))

    # ── 실행 ────────────────────────────────────────────────────────────────

    async def _run(self, job: Job) -> None:
        async def on_event(ev: goose_runner.ProgressEvent) -> None:
            await self._emit(job, "progress", {"stage": ev.stage, "detail": ev.detail})

        try:
            if self._prefetcher is not None:
                await self._prefetch(job)
            if self._naver_prefetcher is not None:
                await self._prefetch_naver(job)  # DART 뒤·무결성 재검사 앞(REQ-AIR7-001)
            if self._prefetcher is not None or self._naver_prefetcher is not None:
                # 수집 때문에 시작 판정 검사와 claude 실행 사이가 벌어진다 — 실행 직전에 다시 검사한다(T13, 007 T7)
                integrity = await asyncio.to_thread(self._integrity)
                if not integrity.ok:
                    logger.error("goose 작업 %s 실행 직전 무결성 재검사 실패 — 실행하지 않음: %s",
                                 job.job_id, integrity.reason)
                    extra = await self._call_finish_hook(job, None, ("error", "integrity"))
                    await self._finish(job, "error", "integrity", extra)
                    return
            result = await self._runner(
                job_id=job.job_id, stock_name=job.stock_name, code=job.code, on_event=on_event
            )
        except asyncio.CancelledError:
            # 실행기는 그룹을 정리한 뒤 CancelledError를 다시 던진다(M3). 취소는 오류 종류가 아니다.
            reason = job.cancel_reason or "cancel"
            logger.info("goose 작업 %s 취소(사유 %s)", job.job_id, reason)
            extra = await self._call_finish_hook(job, None, ("cancelled", None))
            await self._finish(job, "cancelled", None, extra)
            raise
        except Exception:  # noqa: BLE001 - 실행기 밖 예외도 작업을 종료 상태로 닫는다
            logger.exception("goose 작업 %s 실행 중 예외", job.job_id)
            extra = await self._call_finish_hook(job, None, ("error", "exit_error"))
            await self._finish(job, "error", "exit_error", extra)
            return
        if result.status == "done":
            extra = await self._call_finish_hook(job, result, ("done", None))
            data = {"delivery_status": result.delivery_status, **extra}
            await self._finish(job, "done", None, data)
        else:
            kind = result.error_kind or "exit_error"
            extra = await self._call_finish_hook(job, result, ("error", kind))
            await self._finish(job, "error", kind, extra)

    # @MX:ANCHOR: [AUTO] _prefetch — DART 사전 수집 단계의 단일 정의(REQ-AIR5-001~004·010).
    # @MX:REASON: 끄기 스위치 판단·진행 이벤트·fail-open의 소유자가 여기다. 이벤트는 수집기 호출 전에
    #             정확히 1번(AC-003), 스위치 0이면 수집기 미호출·disabled 색인·이벤트 없음(AC-004).
    #             except를 BaseException으로 넓히면 취소가 삼켜져 goose가 실행된다(AC-002 대조 (a)).
    # @MX:SPEC: SPEC-AI-REPORT-005
    async def _prefetch(self, job: Job) -> None:
        out_dir = self._runs_root() / job.job_id / "dart"
        if os.environ.get(ENV_DART_PREFETCH, "").strip() == "0":
            try:
                goose_dart_prefetch.write_disabled_index(out_dir, job.code)
            except Exception:  # noqa: BLE001 - 색인 쓰기 실패도 goose 실행을 막지 않는다
                logger.exception("goose 작업 %s DART 사전 수집 끄기 색인 쓰기 실패", job.job_id)
            return
        await self._emit(job, "progress", {"stage": "dart_prefetch", "detail": None})
        try:
            await self._prefetcher(job.code, out_dir)
        except Exception:  # noqa: BLE001 - fail-open(REQ-AIR5-010). CancelledError는 Exception이 아니라 전파된다
            logger.exception("goose 작업 %s DART 사전 수집 실패 — goose 실행은 계속", job.job_id)

    async def _code_validated(self, job: Job) -> bool:
        """서버 종목 목록 조회 결과(REQ-AIR7-015). 확인 함수가 없거나 예외를 던지면 False."""
        if self._code_check is None:
            return False
        try:
            # 첫 호출은 종목 목록(엑셀)을 읽을 수 있어 이벤트 루프를 막지 않게 스레드로 넘긴다
            return bool(await asyncio.to_thread(self._code_check, job.code))
        except Exception:  # noqa: BLE001 - 확인 실패는 기록만 하고 수집은 계속한다(D9)
            logger.exception("goose 작업 %s 종목코드 확인 실패 — code_validated=false", job.job_id)
            return False

    # @MX:ANCHOR: [AUTO] _prefetch_naver — 네이버 사전 수집 단계의 단일 정의(REQ-AIR7-001~004·008·015).
    # @MX:REASON: 끄기 스위치 판단·code_validated 전달·fail-open의 소유자가 여기다. 진행 이벤트를 보내지 않는다
    #             (AC-004). except를 BaseException으로 넓히면 취소가 삼켜져 goose가 실행된다(AC-002).
    # @MX:SPEC: SPEC-AI-REPORT-007
    async def _prefetch_naver(self, job: Job) -> None:
        out_dir = self._runs_root() / job.job_id / "naver"
        validated = await self._code_validated(job)
        if os.environ.get(ENV_NAVER_PREFETCH, "").strip() == "0":
            try:
                goose_naver_prefetch.write_disabled_index(out_dir, job.code, code_validated=validated)
            except Exception:  # noqa: BLE001 - 색인 쓰기 실패도 goose 실행을 막지 않는다
                logger.exception("goose 작업 %s 네이버 사전 수집 끄기 색인 쓰기 실패", job.job_id)
            return
        try:
            await self._naver_prefetcher(job.code, out_dir, code_validated=validated)
        except Exception:  # noqa: BLE001 - fail-open(REQ-AIR7-008). CancelledError는 Exception이 아니라 전파된다
            logger.exception("goose 작업 %s 네이버 사전 수집 실패 — goose 실행은 계속", job.job_id)

    async def _call_finish_hook(
        self, job: Job, result: goose_runner.RunResult | None, ending: tuple[str, str | None]
    ) -> dict[str, Any]:
        # 훅(M5 보관)은 종료 상태를 알아야 interrupted·job.json을 쓴다. 종료 이벤트보다 먼저 확정해 둔다.
        job.ending = ending
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
# 보관 훅(M5)·DART 사전 수집기(SPEC-AI-REPORT-005)·네이버 사전 수집기와 종목코드 확인(SPEC-AI-REPORT-007)은
# 이 운영용 인스턴스에만 붙인다. 생성자 기본값은 모두 없음 — 테스트가 만든 서비스가 실제 backend/reports에
# 쓰거나 DART·네이버에 요청하지 않게 한다.
def _server_code_check(code: str) -> bool:
    """라우터와 같은 서버 종목 목록 조회(네트워크 없음, spec §2.7). 목록에 있으면 True."""
    # 지연 가져오기: my_chart.registry(종목 목록 엑셀) 로드를 첫 확인 때까지 미룬다
    from backend.services import ai_report_service

    return ai_report_service.get_stock_name(code) is not None


_service = GooseJobService(
    on_finish=goose_storage.make_finish_hook(runs_root=_default_runs_root),
    prefetcher=goose_dart_prefetch.DartPrefetcher(),
    naver_prefetcher=goose_naver_prefetch.NaverPrefetcher(),
    code_check=_server_code_check,
)


def get_service() -> GooseJobService:
    return _service


def set_service(service: GooseJobService) -> None:
    global _service
    _service = service
