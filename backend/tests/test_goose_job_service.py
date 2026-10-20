"""SPEC-AI-REPORT-004 M4 — goose 작업 서비스(goose_job_service) 단위·통합 테스트.

테스트 대상: backend/services/goose_job_service.py
- 시작 판정 4~8단계와 단일 잠금(design §4.3·§8, AC-AIR4-007·008, B5 동시성)
- 닫힌 실패(AC-AIR4-001 (2b) — 시작 시 실패 기록이 있으면 모든 작업 error/integrity)
- goose 전용 일일 쿼터(AI_REPORT_GOOSE_DAILY_QUOTA, Fast 카운터와 분리)
- 이벤트 재생·Last-Event-ID·실시간 대기(AC-AIR4-009), 구독 해제와 작업 분리(AC-AIR4-010)
- 취소·서버 종료와 프로세스 그룹 정리(AC-AIR4-011)

격리 원칙:
- 실제 `claude`를 띄우지 않는다. 가짜 실행기(코루틴) 또는 tmp_path의 가짜 실행 파일만 쓴다.
- 실제 홈·~/.goose-harness를 건드리지 않는다. 하네스·runs 경로는 tmp_path로 주입한다.
- 동기화는 asyncio.Event와 조건 폴링으로 한다(고정 sleep으로 순서를 맞추지 않는다).
- `backend.services` 패키지 __init__(무거운 my_chart import)를 피하려고 가짜 상위 패키지를
  sys.modules에 잠시 넣고 goose 모듈만 새로 불러온다. 끝나면 `backend*` 항목을 되돌린다.
"""

from __future__ import annotations

import asyncio
import functools
import importlib
import os
import signal
import sys
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]
_KST = timezone(timedelta(hours=9))


def _isolated_import(monkeypatch, *names: str) -> list[types.ModuleType]:
    """가짜 상위 패키지 아래에서 goose 모듈을 새로 불러온다(__init__ 실행 없음)."""
    for pkg, path in (
        ("backend", _BACKEND),
        ("backend.services", _BACKEND / "services"),
        ("backend.schemas", _BACKEND / "schemas"),
        ("backend.routers", _BACKEND / "routers"),
    ):
        mod = types.ModuleType(pkg)
        mod.__path__ = [str(path)]  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, pkg, mod)
    for name in (
        "backend.services.goose_harness",
        "backend.services.goose_runner",
        "backend.services.goose_job_service",
    ):
        monkeypatch.delitem(sys.modules, name, raising=False)
    return [importlib.import_module(n) for n in names]


@pytest.fixture
def mods(monkeypatch):
    saved = {k: v for k, v in sys.modules.items() if k == "backend" or k.startswith("backend.")}
    gh, gr, gjs = _isolated_import(
        monkeypatch,
        "backend.services.goose_harness",
        "backend.services.goose_runner",
        "backend.services.goose_job_service",
    )
    yield types.SimpleNamespace(gh=gh, gr=gr, gjs=gjs)
    for k in [k for k in sys.modules if k == "backend" or k.startswith("backend.")]:
        if k not in saved:
            del sys.modules[k]


class FakeRunner:
    """호출을 기록하고, release()될 때까지 기다렸다가 정해진 결과를 돌려주는 가짜 실행기."""

    def __init__(self, gr, *, status="done", error_kind=None, delivery_status="draft", events=()):
        self.gr = gr
        self.calls: list[dict] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.result = gr.RunResult(
            status=status, error_kind=error_kind, exit_code=0 if status == "done" else 1,
            delivery_status=delivery_status if status == "done" else None,
        )
        self.events = list(events)
        self.raise_exc: BaseException | None = None

    async def __call__(self, *, job_id, stock_name, code, on_event):
        self.calls.append({"job_id": job_id, "stock_name": stock_name, "code": code})
        for stage in self.events:
            await on_event(self.gr.ProgressEvent(stage))
        self.started.set()
        await self.release.wait()
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.result


def _ok_integrity(gh):
    return lambda: gh.IntegrityResult(True, "ok")


def _service(mods, tmp_path, runner, *, quota=None, integrity=None, monkeypatch=None, **kw):
    if quota is not None:
        monkeypatch.setenv("AI_REPORT_GOOSE_DAILY_QUOTA", str(quota))
    return mods.gjs.GooseJobService(
        runner=runner,
        integrity_check=integrity or _ok_integrity(mods.gh),
        runs_root=lambda: tmp_path / "runs",
        **kw,
    )


async def _finish(job):
    if job.task is not None:
        await asyncio.gather(job.task, return_exceptions=True)


async def _collect(agen, n: int, timeout: float = 5.0) -> list:
    out = []
    async def _take():
        async for ev in agen:
            out.append(ev)
            if len(out) >= n:
                return
    await asyncio.wait_for(_take(), timeout)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 쿼터 (goose 전용, Fast와 분리)
# ─────────────────────────────────────────────────────────────────────────────


def test_quota_default_is_5_and_env_override(mods, monkeypatch):
    monkeypatch.delenv("AI_REPORT_GOOSE_DAILY_QUOTA", raising=False)
    assert mods.gjs.GooseRateLimiter().quota == 5
    monkeypatch.setenv("AI_REPORT_GOOSE_DAILY_QUOTA", "2")
    assert mods.gjs.GooseRateLimiter().quota == 2
    monkeypatch.setenv("AI_REPORT_GOOSE_DAILY_QUOTA", "abc")
    assert mods.gjs.GooseRateLimiter().quota == 5


def test_quota_counts_per_kst_day(mods, monkeypatch):
    monkeypatch.setenv("AI_REPORT_GOOSE_DAILY_QUOTA", "1")
    now = [datetime(2026, 10, 20, 23, 0, tzinfo=_KST)]
    lim = mods.gjs.GooseRateLimiter(clock=lambda: now[0])
    assert not lim.exhausted()
    lim.consume()
    assert lim.exhausted() and lim.used() == 1
    now[0] = datetime(2026, 10, 21, 0, 1, tzinfo=_KST)
    assert not lim.exhausted() and lim.used() == 0


def test_goose_limiter_does_not_touch_deep_counters(mods):
    # Fast/Deep 카운터를 import하지 않는다 — 모듈 원문에 옛 함수 이름이 없어야 한다.
    src = Path(mods.gjs.__file__).read_text()
    assert "check_rate_limit" not in src
    assert "check_deep_rate_limit" not in src
    assert "_deep_daily_call_count" not in src


# ─────────────────────────────────────────────────────────────────────────────
# 시작 판정 4~8 (design §4.3)
# ─────────────────────────────────────────────────────────────────────────────


async def test_ac007_same_code_twice_returns_existing_job_without_quota(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    first = await svc.start("299030", "하나기술")
    await runner.started.wait()
    second = await svc.start("299030", "하나기술")
    assert (first.kind, second.kind) == ("started", "existing")
    assert second.job.job_id == first.job.job_id
    assert len(runner.calls) == 1
    assert svc.limiter.used() == 1
    assert (tmp_path / "runs" / first.job.job_id).is_dir()
    runner.release.set()
    await _finish(first.job)


async def test_other_code_while_running_is_busy_with_running_name(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    first = await svc.start("299030", "하나기술")
    busy = await svc.start("005930", "삼성전자")
    assert busy.kind == "busy"
    assert busy.job.stock_name == "하나기술"
    assert len(runner.calls) == 1 and svc.limiter.used() == 1
    runner.release.set()
    await _finish(first.job)


async def test_quota_exhausted_blocks_new_start_but_not_same_code(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, quota=1, monkeypatch=monkeypatch)
    first = await svc.start("299030", "하나기술")
    # 같은 종목(4단계)은 쿼터(6단계)보다 먼저 판정된다
    assert (await svc.start("299030", "하나기술")).kind == "existing"
    # 다른 종목(5단계)도 쿼터보다 먼저
    assert (await svc.start("005930", "삼성전자")).kind == "busy"
    runner.release.set()
    await _finish(first.job)
    assert (await svc.start("005930", "삼성전자")).kind == "rate_limit"
    assert len(runner.calls) == 1


async def test_integrity_failure_records_error_job_without_run_quota_or_active(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(
        mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch,
        integrity=lambda: mods.gh.IntegrityResult(False, "installed sha256 mismatch: x"),
    )
    out = await svc.start("299030", "하나기술")
    assert out.kind == "integrity"
    job = svc.get(out.job.job_id)
    assert (job.status, job.error_kind) == ("error", "integrity")
    assert svc.active() is None
    assert svc.limiter.used() == 0
    assert runner.calls == []
    assert not (tmp_path / "runs" / job.job_id).exists()
    events = await _collect(svc.subscribe(job.job_id), 1)
    assert [(e.seq, e.type) for e in events] == [(1, "error")]
    assert events[0].data["error_kind"] == "integrity"


async def test_quota_is_judged_before_integrity(mods, tmp_path, monkeypatch):
    calls = []

    def integrity():
        calls.append(1)
        return mods.gh.IntegrityResult(False, "x")

    svc = _service(mods, tmp_path, FakeRunner(mods.gr), quota=1, monkeypatch=monkeypatch,
                   integrity=integrity)
    svc.limiter.consume()
    assert (await svc.start("299030", "하나기술")).kind == "rate_limit"
    assert calls == []


async def test_b5_fail_closed_startup_failure_blocks_every_later_start(mods, tmp_path, monkeypatch):
    """AC-001 (2b) 서비스 쪽: 시작 시 실패 기록 → 모든 시작이 error/integrity, 쿼터·실행기 불변."""
    gh = mods.gh
    gh.reset_state()
    # 리포 매니페스트와 맞지 않는 원본으로 시작 설치 → 실패 기록
    src = tmp_path / "src"
    (src / "skills" / "goose").mkdir(parents=True)
    (src / "harness-instructions.md").write_text("x")
    (src / "goose-manifest.json").write_text('{"files": {"CLAUDE.md": "' + "0" * 64 + '"}}')
    status = gh.install_at_startup(source_dir=src, harness_dir=tmp_path / "H")
    assert status.ok is False
    runner = FakeRunner(mods.gr)
    svc = mods.gjs.GooseJobService(runner=runner, runs_root=lambda: tmp_path / "runs")
    monkeypatch.setenv("AI_REPORT_GOOSE_DAILY_QUOTA", "5")
    kinds = []
    for code, name in (("299030", "하나기술"), ("299030", "하나기술"), ("005930", "삼성전자")):
        out = await svc.start(code, name)
        kinds.append((out.kind, out.job.status, out.job.error_kind))
    assert kinds == [("integrity", "error", "integrity")] * 3
    assert runner.calls == []
    assert svc.limiter.used() == 0
    assert svc.active() is None
    gh.reset_state()


async def test_b5_concurrent_starts_different_codes_exactly_one_runs(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    a, b = await asyncio.gather(svc.start("299030", "하나기술"), svc.start("005930", "삼성전자"))
    assert sorted([a.kind, b.kind]) == ["busy", "started"]
    assert svc.limiter.used() == 1
    await runner.started.wait()
    assert len(runner.calls) == 1
    runner.release.set()
    await _finish((a if a.kind == "started" else b).job)


async def test_b5_concurrent_starts_same_code_one_job(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    outs = await asyncio.gather(*(svc.start("299030", "하나기술") for _ in range(3)))
    assert sorted(o.kind for o in outs) == ["existing", "existing", "started"]
    assert len({o.job.job_id for o in outs}) == 1
    assert svc.limiter.used() == 1
    runner.release.set()
    await _finish(outs[0].job)


# ─────────────────────────────────────────────────────────────────────────────
# 종료 상태 (design §4.1)
# ─────────────────────────────────────────────────────────────────────────────


async def test_done_result_emits_done_and_clears_active(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr, events=("goose_start", "plan"))
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    out = await svc.start("299030", "하나기술")
    assert svc.active() == {"job_id": out.job.job_id, "code": "299030",
                            "stock_name": "하나기술", "status": "running"}
    runner.release.set()
    await _finish(out.job)
    job = svc.get(out.job.job_id)
    assert (job.status, job.error_kind) == ("done", None)
    assert svc.active() is None
    events = await _collect(svc.subscribe(job.job_id), 3)
    assert [e.type for e in events] == ["progress", "progress", "done"]
    assert events[0].data == {"stage": "goose_start", "detail": None}
    assert events[2].data["delivery_status"] == "draft"


@pytest.mark.parametrize("kind", ["binary_missing", "auth", "timeout", "empty_output", "exit_error"])
async def test_runner_error_kinds_are_kept(mods, tmp_path, monkeypatch, kind):
    runner = FakeRunner(mods.gr, status="error", error_kind=kind)
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    out = await svc.start("299030", "하나기술")
    runner.release.set()
    await _finish(out.job)
    job = svc.get(out.job.job_id)
    assert (job.status, job.error_kind) == ("error", kind)
    last = (await _collect(svc.subscribe(job.job_id), 1))[-1]
    assert last.type == "error" and last.data["error_kind"] == kind and last.data["message"]


async def test_unexpected_runner_exception_is_exit_error(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    runner.raise_exc = RuntimeError("boom")
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    out = await svc.start("299030", "하나기술")
    runner.release.set()
    await _finish(out.job)
    assert (out.job.status, out.job.error_kind) == ("error", "exit_error")
    assert svc.active() is None


async def test_on_finish_hook_result_is_merged_into_terminal_event(mods, tmp_path, monkeypatch):
    seen = []

    async def on_finish(job, result):
        seen.append((job.job_id, result.status if result else None))
        return {"run": "2026-10-20", "report_url": "/x/report.html"}

    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch, on_finish=on_finish)
    out = await svc.start("299030", "하나기술")
    runner.release.set()
    await _finish(out.job)
    last = (await _collect(svc.subscribe(out.job.job_id), 1))[-1]
    assert last.data == {"delivery_status": "draft", "run": "2026-10-20", "report_url": "/x/report.html"}
    assert seen == [(out.job.job_id, "done")]


async def test_on_finish_failure_does_not_change_terminal_state(mods, tmp_path, monkeypatch):
    def on_finish(job, result):
        raise OSError("disk full")

    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch, on_finish=on_finish)
    out = await svc.start("299030", "하나기술")
    runner.release.set()
    await _finish(out.job)
    assert out.job.status == "done"


async def test_finished_jobs_are_pruned_beyond_limit(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    runner.release.set()
    svc = _service(mods, tmp_path, runner, quota=10, monkeypatch=monkeypatch, max_finished=2)
    ids = []
    for _ in range(4):
        out = await svc.start("299030", "하나기술")
        await _finish(out.job)
        ids.append(out.job.job_id)
    assert [svc.get(i) is not None for i in ids] == [False, False, True, True]


# ─────────────────────────────────────────────────────────────────────────────
# AC-009 재생 / AC-010 구독 해제
# ─────────────────────────────────────────────────────────────────────────────


async def test_ac009_replay_then_live_and_last_event_id(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr, events=("goose_start", "plan", "plan", "research_tick", "compose"))
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    out = await svc.start("299030", "하나기술")
    await runner.started.wait()
    jid = out.job.job_id
    # (1) 헤더 없음: 1..5 재생 (작업은 아직 대기 중)
    first = await _collect(svc.subscribe(jid), 5)
    assert [e.seq for e in first] == [1, 2, 3, 4, 5]
    # (2) Last-Event-ID 3 → 4, 5 다음에 실시간 종료 이벤트까지
    agen = svc.subscribe(jid, after=3)
    got = await _collect(agen, 2)
    assert [e.seq for e in got] == [4, 5]
    pending = asyncio.ensure_future(_collect(agen, 1))
    await asyncio.sleep(0)
    assert not pending.done()  # 새 이벤트가 올 때까지 기다린다
    runner.release.set()
    live = await pending
    assert [(e.seq, e.type) for e in live] == [(6, "done")]
    # 종료 후 구독은 재생 뒤 닫힌다
    assert [e.seq for e in await _collect(svc.subscribe(jid, after=4), 2)] == [5, 6]
    await _finish(out.job)


async def test_ac009_subscribe_unknown_job_raises_keyerror(mods, tmp_path, monkeypatch):
    svc = _service(mods, tmp_path, FakeRunner(mods.gr), quota=5, monkeypatch=monkeypatch)
    with pytest.raises(KeyError):
        await _collect(svc.subscribe("nope"), 1)


async def test_subscribe_after_last_seq_of_finished_job_ends_immediately(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    runner.release.set()
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    out = await svc.start("299030", "하나기술")
    await _finish(out.job)
    assert [e async for e in svc.subscribe(out.job.job_id, after=99)] == []


async def test_ac010_subscriber_disconnect_does_not_cancel_job(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr, events=("goose_start",))
    svc = _service(mods, tmp_path, runner, quota=5, monkeypatch=monkeypatch)
    out = await svc.start("299030", "하나기술")
    await runner.started.wait()
    agen = svc.subscribe(out.job.job_id)
    assert len(await _collect(agen, 1)) == 1
    await agen.aclose()  # 구독 연결 끊김
    runner.release.set()
    await _finish(out.job)
    assert out.job.status == "done"


# ─────────────────────────────────────────────────────────────────────────────
# AC-011 취소·서버 종료 (실제 run_goose + 가짜 실행 파일 → 프로세스 그룹 확인)
# ─────────────────────────────────────────────────────────────────────────────


def _fake_claude(tmp_path: Path) -> Path:
    pid_file = tmp_path / "pids.txt"
    path = tmp_path / "fake-claude"
    path.write_text(
        "#!/bin/bash\n"
        "sleep 30 &\n"
        f'echo "$$ $!" > "{pid_file}"\n'
        "wait\n"
    )
    path.chmod(0o755)
    return path


async def _wait_pids(tmp_path: Path, timeout: float = 5.0) -> list[int]:
    deadline = time.monotonic() + timeout
    pid_file = tmp_path / "pids.txt"
    while time.monotonic() < deadline:
        if pid_file.exists() and pid_file.read_text().strip().count(" ") == 1:
            return [int(x) for x in pid_file.read_text().split()]
        await asyncio.sleep(0.02)
    raise AssertionError("가짜 claude가 PID를 기록하지 않음")


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _kill_leftovers(pids):
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def _real_runner(mods, tmp_path):
    harness = tmp_path / "harness"
    (harness / "runs").mkdir(parents=True, exist_ok=True)
    environ = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home"),
               "AI_REPORT_GOOSE_HARNESS_DIR": str(harness)}
    runner = functools.partial(
        mods.gr.run_goose, environ=environ, claude_bin=str(_fake_claude(tmp_path)),
        grace_sec=0.5, timeout_sec=30,
    )
    return runner, harness


async def test_ac011_cancel_running_finished_and_unknown(mods, tmp_path, monkeypatch):
    runner, harness = _real_runner(mods, tmp_path)
    svc = mods.gjs.GooseJobService(
        runner=runner, integrity_check=_ok_integrity(mods.gh), runs_root=lambda: harness / "runs",
    )
    monkeypatch.setenv("AI_REPORT_GOOSE_DAILY_QUOTA", "5")
    pids: list[int] = []
    try:
        # (2) 완료된 작업 J2: 즉시 끝나는 실행기로 만든다
        done_runner = FakeRunner(mods.gr)
        done_runner.release.set()
        svc._runner = done_runner
        j2 = (await svc.start("005930", "삼성전자")).job
        await _finish(j2)
        svc._runner = runner
        # (1) J1 시작 후 취소
        j1 = (await svc.start("299030", "하나기술")).job
        pids = await _wait_pids(tmp_path)
        assert all(_alive(p) for p in pids)
        cancelled = await svc.cancel(j1.job_id)
        assert cancelled is j1
        assert (j1.status, j1.error_kind) == ("cancelled", None)
        events = await _collect(svc.subscribe(j1.job_id), 1)
        assert events[-1].type == "cancelled" and events[-1].data == {}
        assert not any(_alive(p) for p in pids)
        assert svc.active() is None
        # (2) 완료 작업 취소 → 상태 그대로
        assert (await svc.cancel(j2.job_id)).status == "done"
        # (3) 없는 id
        assert await svc.cancel("nope") is None
    finally:
        _kill_leftovers(pids)


async def test_ac011_shutdown_cancels_running_job_and_kills_group(mods, tmp_path, monkeypatch):
    runner, harness = _real_runner(mods, tmp_path)
    svc = mods.gjs.GooseJobService(
        runner=runner, integrity_check=_ok_integrity(mods.gh), runs_root=lambda: harness / "runs",
    )
    monkeypatch.setenv("AI_REPORT_GOOSE_DAILY_QUOTA", "5")
    pids: list[int] = []
    try:
        j3 = (await svc.start("299030", "하나기술")).job
        pids = await _wait_pids(tmp_path)
        await svc.shutdown()
        assert (j3.status, j3.error_kind) == ("cancelled", None)
        assert j3.cancel_reason == "shutdown"
        assert not any(_alive(p) for p in pids)
        assert svc.active() is None
    finally:
        _kill_leftovers(pids)


async def test_shutdown_without_running_job_is_noop(mods, tmp_path, monkeypatch):
    svc = _service(mods, tmp_path, FakeRunner(mods.gr), quota=5, monkeypatch=monkeypatch)
    await svc.shutdown()
    assert svc.active() is None


def test_module_singleton_get_and_set(mods):
    gjs = mods.gjs
    original = gjs.get_service()
    assert isinstance(original, gjs.GooseJobService)
    other = gjs.GooseJobService()
    gjs.set_service(other)
    assert gjs.get_service() is other
    gjs.set_service(original)
