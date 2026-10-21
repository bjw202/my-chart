"""SPEC-AI-REPORT-004 M4 — goose 작업 서비스(goose_job_service) 단위·통합 테스트.

테스트 대상: backend/services/goose_job_service.py
- 시작 판정 4~8단계와 단일 잠금(design §4.3·§8, AC-AIR4-007·008, B5 동시성)
- 닫힌 실패(AC-AIR4-001 (2b) — 시작 시 실패 기록이 있으면 모든 작업 error/integrity)
- 하루 실행 횟수 제한 없음(사용자 결정 2026-10-21), 동시 실행 1개만 유지
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
import hashlib
import importlib
import json
import os
import signal
import subprocess
import sys
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

_BACKEND = Path(__file__).resolve().parents[1]


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
    gh, gr, gjs, gdp = _isolated_import(
        monkeypatch,
        "backend.services.goose_harness",
        "backend.services.goose_runner",
        "backend.services.goose_job_service",
        "backend.services.goose_dart_prefetch",
    )
    yield types.SimpleNamespace(gh=gh, gr=gr, gjs=gjs, gdp=gdp)
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


def _service(mods, tmp_path, runner, *, integrity=None, monkeypatch=None, **kw):
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
# 하루 실행 횟수 제한 없음 (사용자 결정 2026-10-21) — Fast 카운터와도 무관
# ─────────────────────────────────────────────────────────────────────────────


def test_goose_service_does_not_touch_fast_or_deep_counters(mods):
    # Fast/Deep 카운터를 import하지 않는다 — 모듈 원문에 옛 함수 이름이 없어야 한다.
    src = Path(mods.gjs.__file__).read_text()
    assert "check_rate_limit" not in src
    assert "check_deep_rate_limit" not in src
    assert "_deep_daily_call_count" not in src


# ─────────────────────────────────────────────────────────────────────────────
# 시작 판정 4~8 (design §4.3)
# ─────────────────────────────────────────────────────────────────────────────


async def test_ac007_same_code_twice_returns_existing_job(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
    first = await svc.start("299030", "하나기술")
    await runner.started.wait()
    second = await svc.start("299030", "하나기술")
    assert (first.kind, second.kind) == ("started", "existing")
    assert second.job.job_id == first.job.job_id
    assert len(runner.calls) == 1
    assert (tmp_path / "runs" / first.job.job_id).is_dir()
    runner.release.set()
    await _finish(first.job)


async def test_other_code_while_running_is_busy_with_running_name(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
    first = await svc.start("299030", "하나기술")
    await runner.started.wait()
    busy = await svc.start("005930", "삼성전자")
    assert busy.kind == "busy"
    assert busy.job.stock_name == "하나기술"
    assert len(runner.calls) == 1
    runner.release.set()
    await _finish(first.job)


async def test_many_sequential_starts_same_day_are_never_refused(mods, tmp_path, monkeypatch):
    """사용자 결정(2026-10-21): 하루 실행 횟수 제한을 없앤다. 같은 날 7번 연달아 시작해도 모두 started."""
    monkeypatch.delenv("AI_REPORT_GOOSE_DAILY_QUOTA", raising=False)
    runner = FakeRunner(mods.gr)
    runner.release.set()  # 각 작업이 바로 끝나게 한다(동시 1개 제한과 무관하게 순차 시작)
    svc = _service(mods, tmp_path, runner)
    kinds = []
    for _ in range(7):
        out = await svc.start("299030", "하나기술")
        kinds.append(out.kind)
        await _finish(out.job)
    assert kinds == ["started"] * 7
    assert len(runner.calls) == 7
    assert not hasattr(svc, "limiter")


async def test_integrity_failure_records_error_job_without_run_or_active(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(
        mods, tmp_path, runner, monkeypatch=monkeypatch,
        integrity=lambda: mods.gh.IntegrityResult(False, "installed sha256 mismatch: x"),
    )
    out = await svc.start("299030", "하나기술")
    assert out.kind == "integrity"
    job = svc.get(out.job.job_id)
    assert (job.status, job.error_kind) == ("error", "integrity")
    assert svc.active() is None
    assert runner.calls == []
    assert not (tmp_path / "runs" / job.job_id).exists()
    events = await _collect(svc.subscribe(job.job_id), 1)
    assert [(e.seq, e.type) for e in events] == [(1, "error")]
    assert events[0].data["error_kind"] == "integrity"


async def test_b5_fail_closed_startup_failure_blocks_every_later_start(mods, tmp_path, monkeypatch):
    """AC-001 (2b) 서비스 쪽: 시작 시 실패 기록 → 모든 시작이 error/integrity, 실행기 불변."""
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
    kinds = []
    for code, name in (("299030", "하나기술"), ("299030", "하나기술"), ("005930", "삼성전자")):
        out = await svc.start(code, name)
        kinds.append((out.kind, out.job.status, out.job.error_kind))
    assert kinds == [("integrity", "error", "integrity")] * 3
    assert runner.calls == []
    assert svc.active() is None
    gh.reset_state()


async def test_b5_concurrent_starts_different_codes_exactly_one_runs(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
    a, b = await asyncio.gather(svc.start("299030", "하나기술"), svc.start("005930", "삼성전자"))
    assert sorted([a.kind, b.kind]) == ["busy", "started"]
    await runner.started.wait()
    assert len(runner.calls) == 1
    runner.release.set()
    await _finish((a if a.kind == "started" else b).job)


async def test_b5_concurrent_starts_same_code_one_job(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
    outs = await asyncio.gather(*(svc.start("299030", "하나기술") for _ in range(3)))
    assert sorted(o.kind for o in outs) == ["existing", "existing", "started"]
    assert len({o.job.job_id for o in outs}) == 1
    runner.release.set()
    await _finish(outs[0].job)


# ─────────────────────────────────────────────────────────────────────────────
# 종료 상태 (design §4.1)
# ─────────────────────────────────────────────────────────────────────────────


async def test_done_result_emits_done_and_clears_active(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr, events=("goose_start", "plan"))
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
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
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
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
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
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
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch, on_finish=on_finish)
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
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch, on_finish=on_finish)
    out = await svc.start("299030", "하나기술")
    runner.release.set()
    await _finish(out.job)
    assert out.job.status == "done"


async def test_finished_jobs_are_pruned_beyond_limit(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    runner.release.set()
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch, max_finished=2)
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
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
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
    svc = _service(mods, tmp_path, FakeRunner(mods.gr), monkeypatch=monkeypatch)
    with pytest.raises(KeyError):
        await _collect(svc.subscribe("nope"), 1)


async def test_subscribe_after_last_seq_of_finished_job_ends_immediately(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    runner.release.set()
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
    out = await svc.start("299030", "하나기술")
    await _finish(out.job)
    assert [e async for e in svc.subscribe(out.job.job_id, after=99)] == []


async def test_ac010_subscriber_disconnect_does_not_cancel_job(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr, events=("goose_start",))
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
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
    svc = _service(mods, tmp_path, FakeRunner(mods.gr), monkeypatch=monkeypatch)
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


# ─────────────────────────────────────────────────────────────────────────────
# 작업 폴더 보존 개수 (사용자 결정 2026-10-20: 최근 10개 유지, 새 작업 시작 때 정리)
# ─────────────────────────────────────────────────────────────────────────────


def _make_old_runs(root: Path, n: int, *, base: float = 1_700_000_000.0) -> list[str]:
    """수정 시각이 오래된 순서대로 n개 작업 폴더를 만든다(이름 r00이 가장 오래됨)."""
    root.mkdir(parents=True, exist_ok=True)
    names = []
    for i in range(n):
        d = root / f"r{i:02d}"
        d.mkdir()
        (d / "input.json").write_text("{}")
        os.utime(d, (base + i * 60, base + i * 60))
        names.append(d.name)
    return names


def test_runs_keep_default_is_10_and_env_override(mods, monkeypatch):
    monkeypatch.delenv("AI_REPORT_GOOSE_RUNS_KEEP", raising=False)
    assert mods.gjs.RUNS_KEEP == 10
    assert mods.gjs.runs_keep() == 10
    monkeypatch.setenv("AI_REPORT_GOOSE_RUNS_KEEP", "3")
    assert mods.gjs.runs_keep() == 3
    for bad in ("abc", "0", "-2"):
        monkeypatch.setenv("AI_REPORT_GOOSE_RUNS_KEEP", bad)
        assert mods.gjs.runs_keep() == 10


def test_prune_runs_keeps_most_recent_and_removes_older(mods, tmp_path):
    root = tmp_path / "runs"
    names = _make_old_runs(root, 13)
    removed = mods.gjs.prune_runs(root, keep=10, protect=())
    assert sorted(removed) == names[:3]
    assert sorted(p.name for p in root.iterdir()) == names[3:]


def test_prune_runs_never_removes_protected_dirs(mods, tmp_path):
    root = tmp_path / "runs"
    names = _make_old_runs(root, 13)
    # 가장 오래된 폴더가 실행 중 작업의 폴더라고 가정한다.
    removed = mods.gjs.prune_runs(root, keep=10, protect=(names[0],))
    assert names[0] not in removed
    assert (root / names[0]).is_dir()
    assert sorted(removed) == names[1:3]


def test_prune_runs_skips_symlinks_files_and_targets_outside(mods, tmp_path):
    root = tmp_path / "runs"
    names = _make_old_runs(root, 3, base=1_800_000_000.0)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("OUTSIDE")
    link = root / "aa_link"
    link.symlink_to(outside, target_is_directory=True)
    os.utime(link, (1.0, 1.0), follow_symlinks=False)
    (root / "note.txt").write_text("x")
    removed = mods.gjs.prune_runs(root, keep=1, protect=())
    assert sorted(removed) == names[:2]
    assert link.is_symlink() and (outside / "keep.txt").read_text() == "OUTSIDE"
    assert (root / "note.txt").is_file()
    assert (root / names[2]).is_dir()


def test_prune_runs_missing_root_is_noop(mods, tmp_path):
    assert mods.gjs.prune_runs(tmp_path / "nope", keep=10, protect=()) == []


async def test_start_prunes_old_run_dirs_but_keeps_new_job_dir(mods, tmp_path, monkeypatch):
    monkeypatch.delenv("AI_REPORT_GOOSE_RUNS_KEEP", raising=False)
    root = tmp_path / "runs"
    names = _make_old_runs(root, 12)
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
    out = await svc.start("299030", "하나기술")
    left = sorted(p.name for p in root.iterdir())
    assert out.job.job_id in left
    assert len(left) == 10
    assert sorted(set(left) - {out.job.job_id}) == names[3:]
    runner.release.set()
    await _finish(out.job)


async def test_start_without_new_job_does_not_prune(mods, tmp_path, monkeypatch):
    # 같은 종목(기존 작업 반환)·다른 종목(busy)은 새 작업이 아니므로 정리하지 않는다.
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)
    first = await svc.start("299030", "하나기술")
    root = tmp_path / "runs"
    names = _make_old_runs(root, 11)
    assert (await svc.start("299030", "하나기술")).kind == "existing"
    assert (await svc.start("005930", "삼성전자")).kind == "busy"
    assert len(list(root.iterdir())) == 12
    assert sorted(p.name for p in root.iterdir()) == sorted(names + [first.job.job_id])
    runner.release.set()
    await _finish(first.job)


async def test_prune_failure_does_not_block_start(mods, tmp_path, monkeypatch):
    runner = FakeRunner(mods.gr)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch)

    def boom(*a, **k):
        raise OSError("disk")

    monkeypatch.setattr(mods.gjs, "prune_runs", boom)
    out = await svc.start("299030", "하나기술")
    assert out.kind == "started"
    runner.release.set()
    await _finish(out.job)


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-005 M3 — DART 사전 수집 연결 (REQ-AIR5-001~004·010, AC-AIR5-001~004·010)
# ─────────────────────────────────────────────────────────────────────────────

_DART_FIX = Path(__file__).parent / "fixtures" / "dart" / "recorded"


class FakePrefetcher:
    """호출 인자·순서를 기록하고, gate가 열릴 때까지 기다리는 가짜 수집기(코루틴)."""

    def __init__(self, order: list | None = None, *, wait: bool = False, job_events=None, raise_exc=None):
        self.order = order if order is not None else []
        self.calls: list[tuple[str, Path]] = []
        self.entered = asyncio.Event()
        self.gate = asyncio.Event()
        if not wait:
            self.gate.set()
        self.snapshots: list[list] = []
        self.job_events = job_events  # 호출 순간 job.events 사본을 남길 때 쓰는 접근자
        self.raise_exc = raise_exc

    async def __call__(self, code, out_dir):
        self.order.append("prefetch")
        self.calls.append((code, Path(out_dir)))
        if self.job_events is not None:
            self.snapshots.append(list(self.job_events()))
        self.entered.set()
        if self.raise_exc is not None:
            raise self.raise_exc
        await self.gate.wait()
        return {"outcome": "complete"}


class OrderRunner(FakeRunner):
    def __init__(self, gr, order: list, **kw):
        super().__init__(gr, **kw)
        self.order = order
        self.release.set()

    async def __call__(self, **kw):
        self.order.append("runner")
        return await super().__call__(**kw)


def _order_integrity(gh, order: list, fail_on: int | None = None):
    count = {"n": 0}

    def check():
        count["n"] += 1
        order.append("integrity")
        if fail_on is not None and count["n"] == fail_on:
            return gh.IntegrityResult(False, "manifest mismatch")
        return gh.IntegrityResult(True, "ok")

    return check


def _dart_stages(job) -> list:
    return [e for e in job.events if e.type == "progress" and e.data.get("stage") == "dart_prefetch"]


class _FastClock:
    """실제 DART 수집기용 가짜 시계·대기 — 1초 간격을 실제로 기다리지 않는다."""

    def __init__(self) -> None:
        self.t = 0.0

    def monotonic(self) -> float:
        return self.t

    async def sleep(self, s: float) -> None:
        self.t += max(0.0, s)


def _real_prefetcher(mods, handler):
    clock = _FastClock()
    return mods.gdp.DartPrefetcher(
        transport=__import__("httpx").MockTransport(handler), clock=clock.monotonic, sleep=clock.sleep
    )


async def test_air5_001_prefetch_runs_outside_lock_before_runner(mods, tmp_path, monkeypatch):
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    order: list = []
    pre = FakePrefetcher(order, wait=True)
    runner = OrderRunner(mods.gr, order)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch,
                   integrity=_order_integrity(mods.gh, order), prefetcher=pre)
    # (a) 첫 start는 수집이 끝나기 전에 돌아온다(1초 상한)
    out = await asyncio.wait_for(svc.start("020150", "롯데에너지머티리얼즈"), 1)
    assert out.kind == "started"
    await asyncio.wait_for(pre.entered.wait(), 1)
    # 수집 대기 중: 같은 종목 → existing, 다른 종목 → busy
    assert (await asyncio.wait_for(svc.start("020150", "롯데에너지머티리얼즈"), 1)).kind == "existing"
    assert (await asyncio.wait_for(svc.start("005930", "삼성전자"), 1)).kind == "busy"
    pre.gate.set()
    await asyncio.wait_for(_finish(out.job), 5)
    # (d) 출력 폴더는 <runs>/<job_id>/dart, (b)(c)(e) 순서
    assert pre.calls == [("020150", tmp_path / "runs" / out.job.job_id / "dart")]
    assert order == ["integrity", "prefetch", "integrity", "runner"]
    assert (out.job.status, out.job.error_kind) == ("done", None)


async def test_air5_001_second_integrity_failure_ends_job_without_runner(mods, tmp_path, monkeypatch):
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    order: list = []
    runner = OrderRunner(mods.gr, order)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch,
                   integrity=_order_integrity(mods.gh, order, fail_on=2), prefetcher=FakePrefetcher(order))
    out = await svc.start("020150", "롯데에너지머티리얼즈")
    assert out.kind == "started"
    await asyncio.wait_for(_finish(out.job), 5)
    assert (out.job.status, out.job.error_kind) == ("error", "integrity")
    assert runner.calls == []
    assert order == ["integrity", "prefetch", "integrity"]
    assert svc.active() is None
    last = out.job.events[-1]
    assert last.type == "error" and last.data["error_kind"] == "integrity"


async def test_air5_001_default_constructor_has_no_prefetch(mods, tmp_path, monkeypatch):
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    order: list = []
    runner = OrderRunner(mods.gr, order, events=("goose_start",))
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch,
                   integrity=_order_integrity(mods.gh, order))
    out = await svc.start("020150", "롯데에너지머티리얼즈")
    await asyncio.wait_for(_finish(out.job), 5)
    assert order == ["integrity", "runner"]
    assert _dart_stages(out.job) == []
    assert not (tmp_path / "runs" / out.job.job_id / "dart").exists()


def test_air5_001_production_service_injects_dart_prefetcher(mods):
    svc = mods.gjs.get_service()
    assert isinstance(svc._prefetcher, mods.gdp.DartPrefetcher)
    assert mods.gjs.GooseJobService()._prefetcher is None


async def test_air5_002_cancel_and_shutdown_during_fake_prefetch(mods, tmp_path, monkeypatch):
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)

    async def scenario():
        for how in ("cancel", "shutdown"):
            pre = FakePrefetcher(wait=True)  # gate가 열리지 않는다 = 영원히 대기
            runner = FakeRunner(mods.gr)
            runner.release.set()
            svc = _service(mods, tmp_path / how, runner, monkeypatch=monkeypatch, prefetcher=pre)
            job = (await svc.start("020150", "롯데에너지머티리얼즈")).job
            await pre.entered.wait()
            if how == "cancel":
                await svc.cancel(job.job_id)
            else:
                await svc.shutdown()
            assert (job.status, job.error_kind) == ("cancelled", None), how
            assert job.events[-1].type == "cancelled", how
            assert runner.calls == [], how
            assert svc.active() is None

    await asyncio.wait_for(scenario(), 5)


async def test_air5_002_cancel_and_shutdown_during_real_prefetch_request(mods, tmp_path, monkeypatch):
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)

    async def scenario():
        for how in ("cancel", "shutdown"):
            gate, entered = asyncio.Event(), asyncio.Event()

            async def hang(request):  # 비동기 처리기 — 스레드를 쓰지 않는다
                entered.set()
                await gate.wait()
                return __import__("httpx").Response(200, content=b"")

            runner = FakeRunner(mods.gr)
            runner.release.set()
            svc = _service(mods, tmp_path / how, runner, monkeypatch=monkeypatch,
                           prefetcher=_real_prefetcher(mods, hang))
            job = (await svc.start("020150", "롯데에너지머티리얼즈")).job
            await entered.wait()
            if how == "cancel":
                await svc.cancel(job.job_id)
            else:
                await svc.shutdown()
            assert (job.status, job.error_kind) == ("cancelled", None), how
            assert job.events[-1].type == "cancelled", how
            assert runner.calls == [], how

    await asyncio.wait_for(scenario(), 5)


async def test_air5_003_dart_prefetch_stage_emitted_once_before_prefetch(mods, tmp_path, monkeypatch):
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    holder: dict = {}
    pre = FakePrefetcher(job_events=lambda: holder["job"].events)
    runner = FakeRunner(mods.gr, events=("goose_start",))
    runner.release.set()
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch, prefetcher=pre)
    out = await svc.start("020150", "롯데에너지머티리얼즈")
    holder["job"] = out.job
    await asyncio.wait_for(_finish(out.job), 5)
    # 수집기 진입 시점 사본에 dart_prefetch가 정확히 1개
    snap = pre.snapshots[0]
    assert [e.data for e in snap if e.type == "progress"] == [{"stage": "dart_prefetch", "detail": None}]
    stages = [e.data["stage"] for e in out.job.events if e.type == "progress"]
    assert stages.count("dart_prefetch") == 1
    assert stages.index("dart_prefetch") < stages.index("goose_start")


@pytest.mark.parametrize("variant", ["switch_off", "no_prefetcher"])
async def test_air5_003_no_dart_prefetch_stage_when_off_or_absent(mods, tmp_path, monkeypatch, variant):
    kw = {}
    if variant == "switch_off":
        monkeypatch.setenv("AI_REPORT_GOOSE_DART_PREFETCH", "0")
        kw["prefetcher"] = FakePrefetcher()
    else:
        monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    runner = FakeRunner(mods.gr, events=("goose_start",))
    runner.release.set()
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch, **kw)
    out = await svc.start("020150", "롯데에너지머티리얼즈")
    await asyncio.wait_for(_finish(out.job), 5)
    assert _dart_stages(out.job) == []
    assert out.job.status == "done"


async def test_air5_004_switch_off_skips_prefetcher_writes_disabled_index(mods, tmp_path, monkeypatch):
    requests: list = []

    def record(request):
        requests.append(str(request.url))
        return __import__("httpx").Response(500, content=b"down")

    real = _real_prefetcher(mods, record)
    calls = {"n": 0}

    async def spy(code, out_dir):  # 작업 서비스가 수집기를 부른 횟수를 센다
        calls["n"] += 1
        return await real(code, out_dir)

    # 끄기 스위치 0: 요청 0, 색인 disabled, 수집기 호출 0, dart_prefetch 0, 실행기 1
    monkeypatch.setenv("AI_REPORT_GOOSE_DART_PREFETCH", "0")
    runner = FakeRunner(mods.gr)
    runner.release.set()
    svc = _service(mods, tmp_path / "off", runner, monkeypatch=monkeypatch, prefetcher=spy)
    out = await svc.start("020150", "롯데에너지머티리얼즈")
    await asyncio.wait_for(_finish(out.job), 5)
    index_path = tmp_path / "off" / "runs" / out.job.job_id / "dart" / "index.json"
    index = __import__("json").loads(index_path.read_text(encoding="utf-8"))
    assert requests == []
    assert index["outcome"] == "disabled" and index["files"] == []
    assert calls["n"] == 0
    assert _dart_stages(out.job) == []
    assert len(runner.calls) == 1 and out.job.status == "done"

    # 대조: 변수 미설정이면 수집기 호출 1, 요청 ≥ 1
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    runner2 = FakeRunner(mods.gr)
    runner2.release.set()
    svc2 = _service(mods, tmp_path / "on", runner2, monkeypatch=monkeypatch, prefetcher=spy)
    out2 = await svc2.start("020150", "롯데에너지머티리얼즈")
    await asyncio.wait_for(_finish(out2.job), 5)
    assert calls["n"] == 1
    assert len(requests) >= 1
    assert len(runner2.calls) == 1


def _fail_handler(case):
    httpx = __import__("httpx")
    list_html = (_DART_FIX / "list_020150_recent.html").read_bytes()

    def handler(request):
        if case == "a_list_500":
            return httpx.Response(500, content=b"server error")
        if case == "b_connect_error":
            raise httpx.ConnectError("refused", request=request)
        if case == "c_timeout":
            raise httpx.ReadTimeout("slow", request=request)
        # d: 목록은 정상, 목차는 노드 없는 HTML
        if request.method == "POST":
            return httpx.Response(200, content=list_html)
        return httpx.Response(200, content=b"<html><body>no toc</body></html>")

    return handler


@pytest.mark.parametrize("case", ["a_list_500", "b_connect_error", "c_timeout", "d_no_toc"])
async def test_air5_010_prefetch_failures_still_run_goose(mods, tmp_path, monkeypatch, case):
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    runner = FakeRunner(mods.gr)
    runner.release.set()
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch,
                   prefetcher=_real_prefetcher(mods, _fail_handler(case)))
    out = await svc.start("020150", "롯데에너지머티리얼즈")
    await asyncio.wait_for(_finish(out.job), 5)
    assert len(runner.calls) == 1
    assert (out.job.status, out.job.error_kind) == ("done", None)
    index = __import__("json").loads(
        (tmp_path / "runs" / out.job.job_id / "dart" / "index.json").read_text(encoding="utf-8"))
    assert index["outcome"] in {"failed", "partial"}


async def test_air5_010_prefetcher_exception_is_logged_and_runner_continues(mods, tmp_path, monkeypatch, caplog):
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    runner = FakeRunner(mods.gr)
    runner.release.set()
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch,
                   prefetcher=FakePrefetcher(raise_exc=RuntimeError("prefetch boom")))
    with caplog.at_level("ERROR"):
        out = await svc.start("020150", "롯데에너지머티리얼즈")
        await asyncio.wait_for(_finish(out.job), 5)
    assert len(runner.calls) == 1
    assert (out.job.status, out.job.error_kind) == ("done", None)
    recs = [r for r in caplog.records if r.levelname == "ERROR" and out.job.job_id in r.getMessage()]
    assert recs and recs[0].exc_info is not None
    assert isinstance(recs[0].exc_info[1], RuntimeError)


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-006 M4 — 후처리(화면 캡처 → 감수 세션 → 영수증)와 전달 상태
# AC-AIR6-001·002·003·004·005·014(서비스 몫)·015 S9·020·022
# 가짜 캡처기·가짜 감수기를 주입한다. 실제 브라우저·실제 claude(AC-022의 스크립트 제외)는 쓰지 않는다.
# ─────────────────────────────────────────────────────────────────────────────

ENV_REVIEW = "AI_REPORT_GOOSE_REVIEW"
_PNG = b"\x89PNG\r\n\x1a\n"
_KST = timezone(timedelta(hours=9))
_TILE_NAMES = ["desktop-01.png", "mobile-01.png"]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _kst_now() -> str:
    return datetime.now(_KST).isoformat(timespec="seconds")


def _write_draft(job_dir: Path) -> None:
    (job_dir / "draft").mkdir(parents=True, exist_ok=True)
    (job_dir / "draft" / "report.html").write_text("<html><body>draft</body></html>", encoding="utf-8")
    (job_dir / "draft" / "report-input.json").write_text('{"k": 1}', encoding="utf-8")


class DraftRunner(OrderRunner):
    """호출 순서를 남기고, 1차 세션 직후 상태(draft)를 디스크에 만든 가짜 실행기."""

    def __init__(self, gr, order, runs: Path, *, make_draft=True, **kw):
        super().__init__(gr, order, **kw)
        self.runs = runs
        self.make_draft = make_draft

    async def __call__(self, **kw):
        if self.make_draft:
            _write_draft(self.runs / kw["job_id"])
        return await super().__call__(**kw)


class FakeShot:
    """가짜 캡처기(`await shot(job_dir)`). 호출 순서·진입 시점 이벤트 사본을 남기고 결정적 화면 파일을 쓴다."""

    def __init__(self, order, *, outcome="complete", raise_exc=None, wait=False, job_events=None):
        self.order = order
        self.outcome = outcome
        self.raise_exc = raise_exc
        self.calls: list[Path] = []
        self.entered = asyncio.Event()
        self.gate = asyncio.Event()
        if not wait:
            self.gate.set()
        self.job_events = job_events
        self.snapshots: list[list] = []

    async def __call__(self, job_dir):
        self.order.append("screenshot")
        self.calls.append(Path(job_dir))
        if self.job_events is not None:
            self.snapshots.append(list(self.job_events()))
        self.entered.set()
        await self.gate.wait()
        if self.raise_exc is not None:
            raise self.raise_exc
        screens = Path(job_dir) / "screens"
        screens.mkdir(parents=True, exist_ok=True)
        html = (Path(job_dir) / "draft" / "report.html").read_bytes()
        ok = self.outcome == "complete"
        viewports = []
        for name, width, files in (("desktop", 1280, _TILE_NAMES[:1]), ("mobile", 390, _TILE_NAMES[1:])):
            tiles = []
            if ok:
                for f in files:
                    data = _PNG + f.encode()
                    (screens / f).write_bytes(data)
                    tiles.append({"file": f, "y": 0, "width": width, "height": 10, "bytes": len(data),
                                  "sha256": _sha(data)})
            viewports.append({
                "name": name, "width": width, "status": "ok" if ok else "skipped",
                "error": None if ok else "browser_not_found",
                "metrics": {"scroll_width": width if ok else None, "client_width": width if ok else None,
                            "scroll_height": 10 if ok else None, "horizontal_overflow": False if ok else None},
                "tiles": tiles,
            })
        index = {
            "schema_version": 1, "source": "draft/report.html", "preview_sha256": _sha(html),
            "started_at": _kst_now(), "finished_at": _kst_now(), "outcome": self.outcome,
            "browser": {"name": "Fake", "version": "1", "path_kind": "env"}, "viewports": viewports,
        }
        (screens / "index.json").write_text(json.dumps(index), encoding="utf-8")
        return index


class FakeReviewer:
    """가짜 감수기(`await reviewer(job_id=, code=, on_event=)`). mode로 세션 결과를 고른다."""

    def __init__(self, gr, order, runs: Path, *, mode="honest", skip_tile=None, job_events=None):
        self.gr = gr
        self.order = order
        self.runs = runs
        self.mode = mode
        self.skip_tile = skip_tile
        self.calls: list[dict] = []
        self.entered = asyncio.Event()
        self.gate = asyncio.Event()
        if mode != "wait":
            self.gate.set()
        self.job_events = job_events
        self.snapshots: list[list] = []
        self.audit_at_entry = None
        self.final_at_entry = None
        self.context_at_entry = None

    async def __call__(self, *, job_id, code, on_event):
        self.order.append("review")
        self.calls.append({"job_id": job_id, "code": code})
        if self.job_events is not None:
            self.snapshots.append(list(self.job_events()))
        job_dir = self.runs / job_id
        ctx_path = job_dir / "review" / "context.json"
        self.context_at_entry = json.loads(ctx_path.read_text()) if ctx_path.exists() else None
        self.audit_at_entry = (job_dir / "audit-review.json").exists()
        self.final_at_entry = (job_dir / "final").exists()
        self.entered.set()
        await self.gate.wait()
        if self.mode == "raise":
            raise RuntimeError("review boom")
        ctx = self.context_at_entry or {}
        reads = [t for t in ctx.get("screens", {}).get("tiles", []) if Path(t).name != self.skip_tile]
        if self.mode in ("honest", "wait"):
            copy = ctx["copy_into_review_record"]
            checks = {k: {"status": "pass", "evidence": "확인함"} for k in
                      ("source_accuracy", "calculations", "coverage", "opinion")}
            checks["visual"] = {"status": "pass", "evidence": "[렌더 차이] 글꼴을 막고 그려 조금 다르다. 타일을 열었다."}
            (job_dir / "audit-review.json").write_text(
                json.dumps({**copy, "checks": checks, "issues": []}), encoding="utf-8")
            (job_dir / "final").mkdir(exist_ok=True)
            (job_dir / "final" / "report.html").write_text("<html>final</html>", encoding="utf-8")
            (job_dir / "final" / "render-validation.json").write_text('{"delivery_allowed": true}')
            await on_event(self.gr.ProgressEvent("render_final"))
        exit_code = 1 if self.mode == "exit1" else 0
        return self.gr.ReviewRunResult(
            started=True, exit_code=None if self.mode == "timeout" else exit_code,
            timed_out=self.mode == "timeout", reads=reads, writes=[],
        )


def _receipt(tmp_path: Path, job_id: str) -> dict | None:
    path = tmp_path / "runs" / job_id / "review" / "receipt.json"
    return json.loads(path.read_text()) if path.exists() else None


def _stages(job) -> list[str]:
    return [e.data["stage"] for e in job.events if e.type == "progress"]


def _stages_of(events) -> list[str]:
    return [e.data["stage"] for e in events if e.type == "progress"]


def _post_service(mods, tmp_path, monkeypatch, *, shot_kw=None, rev_kw=None, runner_kw=None,
                  integrity_fail_on=None, hook=False, inject=True):
    """후처리가 켜진 서비스와 가짜들을 묶어 돌려준다."""
    monkeypatch.delenv(ENV_REVIEW, raising=False)
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    order: list = []
    runs = tmp_path / "runs"
    holder: dict = {}

    def events():
        return holder["svc"]._jobs[holder["job_id"]].events

    runner = DraftRunner(mods.gr, order, runs, **(runner_kw or {}))
    shot = FakeShot(order, job_events=events, **(shot_kw or {}))
    rev = FakeReviewer(mods.gr, order, runs, job_events=events, **(rev_kw or {}))
    kw: dict = {}
    if inject:
        kw.update(screenshotter=shot, reviewer=rev)
    if hook:
        kw["on_finish"] = mods.gjs.goose_storage.make_finish_hook(
            runs_root=lambda: runs, stock_dir=lambda name: tmp_path / "reports" / name)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch,
                   integrity=_order_integrity(mods.gh, order, fail_on=integrity_fail_on), **kw)
    holder["svc"] = svc
    return types.SimpleNamespace(svc=svc, order=order, runner=runner, shot=shot, rev=rev, holder=holder)


async def _run_post(ctx, code="020150", name="롯데에너지머티리얼즈"):
    out = await ctx.svc.start(code, name)
    ctx.holder["job_id"] = out.job.job_id
    await asyncio.wait_for(_finish(out.job), 10)
    return out.job


# ── AC-AIR6-001 ─────────────────────────────────────────────────────────────


async def test_air6_001_order_and_runs_outside_start_lock(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, shot_kw={"wait": True})
    out = await asyncio.wait_for(ctx.svc.start("020150", "롯데에너지머티리얼즈"), 1)
    assert out.kind == "started"
    ctx.holder["job_id"] = out.job.job_id
    await asyncio.wait_for(ctx.shot.entered.wait(), 3)
    # 캡처 대기 중에도 작업은 active로 등록돼 있다: 같은 종목 → existing, 다른 종목 → busy
    assert (await asyncio.wait_for(ctx.svc.start("020150", "롯데에너지머티리얼즈"), 1)).kind == "existing"
    assert (await asyncio.wait_for(ctx.svc.start("005930", "삼성전자"), 1)).kind == "busy"
    ctx.shot.gate.set()
    await asyncio.wait_for(_finish(out.job), 10)
    assert ctx.order == ["integrity", "runner", "integrity", "screenshot", "review"]
    assert out.job.status == "done"


async def test_air6_001_second_integrity_failure_launches_nothing(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, integrity_fail_on=2)
    job = await _run_post(ctx)
    assert ctx.order == ["integrity", "runner", "integrity"]
    assert ctx.shot.calls == [] and ctx.rev.calls == []
    assert _receipt(tmp_path, job.job_id)["outcome"] == "integrity_failed"
    assert job.status == "done"  # 러너 결과대로 종료


async def test_air6_001_no_draft_launches_nothing(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, runner_kw={"make_draft": False})
    job = await _run_post(ctx)
    assert ctx.shot.calls == [] and ctx.rev.calls == []
    assert job.status == "done"


async def test_air6_001_default_constructor_has_no_post_processing(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, inject=False)
    job = await _run_post(ctx)
    assert ctx.order == ["integrity", "runner"]
    assert not {"screenshot", "review", "render_final"} & set(_stages(job))
    assert _receipt(tmp_path, job.job_id) is None


async def test_air6_001_production_service_injects_both(mods):
    svc = mods.gjs.get_service()
    assert svc._screenshotter is not None and svc._reviewer is not None


# ── AC-AIR6-002 ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("variant", ["shot", "review"])
@pytest.mark.parametrize("how", ["cancel", "shutdown"])
async def test_air6_002_cancel_during_post_processing(mods, tmp_path, monkeypatch, variant, how):
    kw = {"shot_kw": {"wait": True}} if variant == "shot" else {"rev_kw": {"mode": "wait"}}
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True, **kw)
    out = await ctx.svc.start("020150", "롯데에너지머티리얼즈")
    ctx.holder["job_id"] = out.job.job_id
    await asyncio.wait_for((ctx.shot if variant == "shot" else ctx.rev).entered.wait(), 3)
    if how == "cancel":
        await asyncio.wait_for(ctx.svc.cancel(out.job.job_id), 5)
    else:
        await asyncio.wait_for(ctx.svc.shutdown(), 5)
    await asyncio.wait_for(_finish(out.job), 5)
    assert out.job.status == "cancelled" and out.job.events[-1].type == "cancelled"
    if variant == "shot":
        assert ctx.rev.calls == []  # 취소가 삼켜져 다음 단계가 실행되면 안 된다
    receipt = _receipt(tmp_path, out.job.job_id)
    assert receipt is not None and receipt["outcome"] == "cancelled" and receipt["visual_admissible"] is False
    sel = mods.gr.select_report(tmp_path / "runs" / out.job.job_id)
    assert sel is not None and sel[0] == "draft"


async def test_air6_002_cancel_kills_real_review_process_group(mods, tmp_path, monkeypatch):
    environ = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home"),
               "AI_REPORT_GOOSE_HARNESS_DIR": str(tmp_path)}
    (tmp_path / "runs").mkdir(exist_ok=True)
    order: list = []
    shot = FakeShot(order)
    reviewer = functools.partial(mods.gr.run_review, environ=environ, claude_bin=str(_fake_claude(tmp_path)),
                                 grace_sec=0.5, timeout_sec=30)
    drunner = DraftRunner(mods.gr, order, tmp_path / "runs")
    monkeypatch.delenv(ENV_REVIEW, raising=False)
    svc = _service(mods, tmp_path, drunner, monkeypatch=monkeypatch, screenshotter=shot, reviewer=reviewer)
    out = await svc.start("020150", "롯데에너지머티리얼즈")
    pids = await _wait_pids(tmp_path)
    try:
        await asyncio.wait_for(svc.cancel(out.job.job_id), 10)
        await asyncio.wait_for(_finish(out.job), 10)
        assert out.job.status == "cancelled"
        assert not any(_alive(pid) for pid in pids)
        assert _receipt(tmp_path, out.job.job_id)["outcome"] == "cancelled"
    finally:
        _kill_leftovers(pids)


# ── AC-AIR6-003 ─────────────────────────────────────────────────────────────


async def test_air6_003_stage_events_exactly_once_and_ordered(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, runner_kw={"events": ("goose_start", "session_end")})
    job = await _run_post(ctx)
    # 캡처기 진입 시점: screenshot 1개, review 0개 / 감수기 진입 시점: review 1개
    assert _stages_of(ctx.shot.snapshots[0]).count("screenshot") == 1
    assert _stages_of(ctx.shot.snapshots[0]).count("review") == 0
    assert _stages_of(ctx.rev.snapshots[0]).count("review") == 1
    stages = _stages(job)
    for stage in ("screenshot", "review", "render_final"):
        assert stages.count(stage) == 1
    assert stages.index("goose_start") < stages.index("screenshot") < stages.index("review") < stages.index(
        "render_final")


async def test_air6_003_no_stage_events_when_switch_off(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch)
    monkeypatch.setenv(ENV_REVIEW, "0")
    job = await _run_post(ctx)
    assert not {"screenshot", "review", "render_final"} & set(_stages(job))


async def test_air6_003_render_final_emitted_once_for_repeated_final_runs(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch)
    real_call = ctx.rev.__call__

    async def twice(*, job_id, code, on_event):
        result = await real_call(job_id=job_id, code=code, on_event=on_event)
        await on_event(mods.gr.ProgressEvent("render_final"))  # 같은 세션이 --final을 다시 실행
        return result

    ctx.svc._reviewer = twice
    job = await _run_post(ctx)
    assert _stages(job).count("render_final") == 1


async def test_air6_003_other_review_tool_calls_are_not_relayed(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch)
    real_call = ctx.rev.__call__

    async def noisy(*, job_id, code, on_event):
        for stage in ("audit", "render_draft", "plan", "research_tick"):
            await on_event(mods.gr.ProgressEvent(stage))
        return await real_call(job_id=job_id, code=code, on_event=on_event)

    ctx.svc._reviewer = noisy
    job = await _run_post(ctx)
    assert not {"audit", "render_draft", "plan", "research_tick"} & set(_stages(job))


# ── AC-AIR6-004 ─────────────────────────────────────────────────────────────


async def test_air6_004_switch_off_skips_post_processing_and_writes_disabled_receipt(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, runner_kw={"delivery_status": "draft"}, hook=True)
    monkeypatch.setenv(ENV_REVIEW, "0")
    job = await _run_post(ctx)
    assert ctx.shot.calls == [] and ctx.rev.calls == []
    assert not {"screenshot", "review", "render_final"} & set(_stages(job))
    assert _receipt(tmp_path, job.job_id)["outcome"] == "disabled"
    assert len(ctx.runner.calls) == 1
    assert job.events[-1].data["delivery_status"] == "draft"
    # 대조: 변수 미설정이면 캡처기 1·감수기 1
    monkeypatch.delenv(ENV_REVIEW)
    ctx2 = _post_service(mods, tmp_path / "second", monkeypatch)
    await _run_post(ctx2)
    assert len(ctx2.shot.calls) == 1 and len(ctx2.rev.calls) == 1


# ── AC-AIR6-005 ─────────────────────────────────────────────────────────────

_FAIL_ROWS = [
    ("shot_raises", {"shot_kw": {"raise_exc": RuntimeError("shot boom")}}, None, "failed"),
    ("shot_unavailable", {"shot_kw": {"outcome": "unavailable"}}, None, "unavailable"),
    ("review_raises", {"rev_kw": {"mode": "raise"}}, "review_failed", None),
    ("review_exit1", {"rev_kw": {"mode": "exit1"}}, "review_failed", None),
    ("review_timeout", {"rev_kw": {"mode": "timeout"}}, "timeout", None),
    ("review_no_record", {"rev_kw": {"mode": "no_record"}}, "review_failed", None),
]


@pytest.mark.parametrize(("case", "kw", "outcome", "screens_outcome"), _FAIL_ROWS, ids=[r[0] for r in _FAIL_ROWS])
async def test_air6_005_post_failures_end_done_with_draft(mods, tmp_path, monkeypatch, case, kw, outcome,
                                                          screens_outcome):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True, **kw)
    job = await _run_post(ctx)
    assert job.status == "done" and job.error_kind is None
    assert [e for e in job.events if e.type == "error"] == []
    assert job.events[-1].data["delivery_status"] == "draft"
    assert len(ctx.rev.calls) == 1  # 캡처만 실패해도 감수는 실행된다
    receipt = _receipt(tmp_path, job.job_id)
    assert receipt is not None
    if screens_outcome is not None:
        context = json.loads((tmp_path / "runs" / job.job_id / "review" / "context.json").read_text())
        assert context["screens"]["outcome"] == screens_outcome
    if outcome is not None:
        assert receipt["outcome"] == outcome
    if case == "review_no_record":
        assert "no_audit_review" in receipt["reasons"]


async def test_air6_005_unexpected_post_exception_is_fail_open(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True)

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(mods.gjs.goose_review, "prepare_review", boom)
    job = await _run_post(ctx)
    assert job.status == "done" and job.events[-1].data["delivery_status"] == "draft"
    assert ctx.rev.calls == []


# ── AC-AIR6-014 (서비스 몫: 사전 심기·삭제 실패) ───────────────────────────────


async def test_air6_014_service_planted_files_removed_before_reviewer(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True, rev_kw={"mode": "no_record"})
    real_run = ctx.runner.__call__

    async def planting(**kw):
        result = await real_run(**kw)
        job_dir = tmp_path / "runs" / kw["job_id"]
        (job_dir / "audit-review.json").write_text('{"mode": "separate_review_pass"}')
        (job_dir / "final").mkdir()
        (job_dir / "final" / "report.html").write_text("<html>planted</html>")
        (job_dir / "final" / "render-validation.json").write_text('{"delivery_allowed": true}')
        return result

    ctx.svc._runner = planting
    job = await _run_post(ctx)
    assert ctx.rev.audit_at_entry is False and ctx.rev.final_at_entry is False
    assert _receipt(tmp_path, job.job_id)["outcome"] == "review_failed"
    assert job.events[-1].data["delivery_status"] == "draft"


async def test_air6_014_service_delete_failure_does_not_launch_reviewer(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True)
    monkeypatch.setattr(mods.gjs.goose_review, "_delete_planted", lambda _jd: False)
    job = await _run_post(ctx)
    assert ctx.rev.calls == [] and ctx.order[-1] == "screenshot"
    assert job.status == "done"
    receipt = _receipt(tmp_path, job.job_id)
    assert receipt["outcome"] == "review_failed"
    # 심은 기록이 없는 이 시나리오의 손으로 유도한 목록: 3 미충족, 11 미충족(감수기 미호출), 13 미충족
    # (AC-014 (13)의 `[review_not_completed, tile_not_read]`는 심은 audit-review.json이 있을 때의 값이다)
    assert receipt["reasons"] == ["review_not_completed", "tile_not_read", "no_audit_review"]
    assert job.events[-1].data["delivery_status"] == "draft"


# ── AC-AIR6-015 S9 (영수증 쓰기 실패의 이벤트 값) ──────────────────────────────


def _forge_admissible_receipt(mods, tmp_path, job_id, ctx):
    """감수 세션이 서버가 쓰는 것과 똑같은 인정 영수증을 직접 써 두는 공격(S7·S9). 쓰기 실패 시험의 전제다."""
    gv = mods.gjs.goose_review
    job_dir = tmp_path / "runs" / job_id
    tiles = ctx["screens"]["tiles"]
    start = gv.ReviewStart(job_id, ctx["now"], True, gv._measure_draft(job_dir), gv.measure_screens(job_dir),
                           [Path(t).name for t in tiles])
    gv.finish_review(job_dir, start, harness_dir=tmp_path, exit_code=0, read_paths=tiles)
    assert gv.evaluate_admissibility(job_dir) == (True, [])  # 위조 영수증은 그대로 두면 최종본을 연다


def _session_forges_receipt(mods, tmp_path, ctx, after_forge):
    real_run = ctx.rev.__call__

    async def forging(**kw):
        result = await real_run(**kw)
        _forge_admissible_receipt(mods, tmp_path, kw["job_id"], ctx.rev.context_at_entry)
        after_forge()
        return result

    ctx.svc._reviewer = forging


async def test_air6_015_s9a_replace_failure_removes_session_receipt(mods, tmp_path, monkeypatch, caplog):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True)

    def fail_replace(src, dst):
        raise OSError("replace boom")

    _session_forges_receipt(mods, tmp_path, ctx,
                            lambda: monkeypatch.setattr(mods.gjs.goose_review, "_replace", fail_replace))
    with caplog.at_level("ERROR"):
        job = await _run_post(ctx)
    assert job.status == "done"
    assert _receipt(tmp_path, job.job_id) is None  # 세션이 쓴 인정 영수증이 남아 있지 않다
    assert sum("receipt_write_failed" in r.getMessage() for r in caplog.records) == 1
    assert mods.gr.select_report(tmp_path / "runs" / job.job_id)[0] == "draft"
    assert job.events[-1].data["delivery_status"] == "draft"


async def test_air6_015_s9b_removal_and_write_failure_event_is_draft(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=False)

    def fail(*a, **k):
        raise OSError("boom")

    def break_writes():
        monkeypatch.setattr(mods.gjs.goose_review, "_remove", fail)
        monkeypatch.setattr(mods.gjs.goose_review, "_replace", fail)

    _session_forges_receipt(mods, tmp_path, ctx, break_writes)
    job = await _run_post(ctx)
    assert job.status == "done"
    assert _receipt(tmp_path, job.job_id) is not None  # 낡은(위조) 영수증이 남아 있다
    # 이 서비스는 훅이 없어 재계산 경로다: 남은 위조 영수증을 믿으면 final이 된다 — 이벤트는 draft로 확정해야 한다
    assert job.events[-1].data["delivery_status"] == "draft"


# ── AC-AIR6-020 (완료 이벤트의 전달 상태) ───────────────────────────────────────


async def test_air6_020_1_event_and_job_json_carry_post_receipt_status(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True, runner_kw={"delivery_status": "draft"})
    job = await _run_post(ctx)
    assert job.events[-1].data["delivery_status"] == "final"
    metas = list((tmp_path / "reports").glob("*/goose/*/job.json"))
    assert len(metas) == 1
    assert json.loads(metas[0].read_text())["delivery_status"] == "final"
    assert job.events[-1].data["run"] == metas[0].parent.name


async def test_air6_020_2_no_hook_recomputes(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=False, runner_kw={"delivery_status": "draft"})
    job = await _run_post(ctx)
    assert job.events[-1].data["delivery_status"] == "final"


async def test_air6_020_3_hook_returning_empty_dict_recomputes(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, runner_kw={"delivery_status": "draft"})
    ctx.svc._on_finish = lambda job, result: {}
    job = await _run_post(ctx)
    assert job.events[-1].data["delivery_status"] == "final"


async def test_air6_020_4_not_admitted_is_draft(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True, runner_kw={"delivery_status": "final"},
                        rev_kw={"skip_tile": "mobile-01.png"})
    job = await _run_post(ctx)
    assert job.events[-1].data["delivery_status"] == "draft"
    metas = list((tmp_path / "reports").glob("*/goose/*/job.json"))
    assert json.loads(metas[0].read_text())["delivery_status"] == "draft"


async def test_air6_020_5_switch_off_keeps_runner_value(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, runner_kw={"delivery_status": "final"})
    monkeypatch.setenv(ENV_REVIEW, "0")
    job = await _run_post(ctx)
    assert job.events[-1].data["delivery_status"] == "final"  # 재계산하면 draft가 되어 어긋난다


async def test_air6_020_6_integrity_failure_keeps_runner_value(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, runner_kw={"delivery_status": "final"}, integrity_fail_on=2)
    job = await _run_post(ctx)
    assert job.events[-1].data["delivery_status"] == "final"


async def test_air6_014_13_service_delete_failure_with_planted_record(mods, tmp_path, monkeypatch):
    """(13) 심은 audit-review.json·final/이 있고 삭제만 실패: 감수기 호출 0, 작성기 사유 [3, 11], draft."""
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True)
    real_run = ctx.runner.__call__

    async def planting(**kw):
        result = await real_run(**kw)
        job_dir = tmp_path / "runs" / kw["job_id"]
        html = (job_dir / "draft" / "report.html").read_bytes()
        checks = {k: {"status": "pass", "evidence": "x"} for k in
                  ("source_accuracy", "calculations", "coverage", "opinion")}
        checks["visual"] = {"status": "pass", "evidence": "[렌더 차이] 심음"}
        (job_dir / "audit-review.json").write_text(json.dumps({
            "mode": "separate_review_pass", "input_sha256": _sha(b'{"k": 1}'), "preview_sha256": _sha(html),
            "reviewed_at": "2999-01-01T00:00:00+09:00", "checks": checks, "issues": []}))
        (job_dir / "final").mkdir()
        (job_dir / "final" / "report.html").write_text("<html>planted</html>")
        (job_dir / "final" / "render-validation.json").write_text('{"delivery_allowed": true}')
        return result

    ctx.svc._runner = planting
    monkeypatch.setattr(mods.gjs.goose_review, "_delete_planted", lambda _jd: False)
    job = await _run_post(ctx)
    assert ctx.rev.calls == [] and job.status == "done"
    receipt = _receipt(tmp_path, job.job_id)
    assert receipt["outcome"] == "review_failed"
    assert receipt["reasons"] == ["review_not_completed", "tile_not_read"]
    assert receipt["screens"]["snapshot_start"] == receipt["screens"]["snapshot_end"]
    assert mods.gr.select_report(tmp_path / "runs" / job.job_id)[0] == "draft"
    assert job.events[-1].data["delivery_status"] == "draft"


# ── AC-AIR6-022 — 최종본 인정 경로의 격리 통합 시험 ─────────────────────────────
# 벤더링된 실제 audit_report.py·render_report.py를 가짜 claude 스크립트가 실행한다. 입력은 라이브 초안
# (020150, 2026-10-21)의 입력에서 네이버 채널의 `blocked` 항목을 `no_results`로 바꾼 합성 입력이다(research P24·P25).
# 날짜는 `historical` 모드(+`user_requested_as_of`)로 고정해 시험 시점의 날짜와 무관하게 만든다(research G10 대체).

_SKILLS = Path(__file__).resolve().parents[1] / "goose_harness_src" / "skills" / "goose" / "workflows"
_AUDIT = _SKILLS / "fact-check" / "scripts" / "audit_report.py"
_RENDER = _SKILLS / "stock-report" / "scripts" / "render_report.py"
_LIVE_INPUT = Path(__file__).parent / "fixtures" / "goose_review" / "live-draft-input.json"


def _synthetic_input() -> bytes:
    data = json.loads(_LIVE_INPUT.read_bytes())
    window = data["research_window"]
    window["searches"] = [s for s in window["searches"] if s.get("result") != "blocked"]
    window["searches"].append({"channel": "naver", "searched_at": window["cutoff"], "query": "synthetic query",
                               "note": "synthetic note", "result": "no_results"})
    window["mode"] = "historical"
    window["user_requested_as_of"] = True
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def _py_run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", "-I", *args], capture_output=True, text=True, timeout=120)


_FAKE_CLAUDE_REVIEW = r'''#!{python}
import json, os, pathlib, re, subprocess, sys
prompt = sys.argv[sys.argv.index("-p") + 1]
job = re.search(r"runs/([A-Za-z0-9_-]+)", prompt).group(1)
harness = pathlib.Path.cwd()
base = harness / "runs" / job
ctx = json.loads((base / "review" / "context.json").read_text())
skip = (harness / "skip-tile.txt").read_text().strip() if (harness / "skip-tile.txt").exists() else None
n = 0
def emit(obj): print(json.dumps(obj), flush=True)
def use(name, inp):
    global n
    n += 1
    emit({{"type": "assistant", "parent_tool_use_id": None, "message": {{"content": [
        {{"type": "tool_use", "id": "t%d" % n, "name": name, "input": inp}}]}}}})
    return "t%d" % n
def result(tid):
    emit({{"type": "user", "parent_tool_use_id": None, "message": {{"content": [
        {{"type": "tool_result", "tool_use_id": tid, "content": [{{"type": "image"}}]}}]}}}})
emit({{"type": "system", "subtype": "init"}})
tid = use("Read", {{"file_path": str(base / "review" / "context.json")}})
result(tid)
for tile in ctx["screens"]["tiles"]:
    if skip and tile.endswith(skip):
        continue
    result(use("Read", {{"file_path": str(harness / tile)}}))
copy = ctx["copy_into_review_record"]
checks = {{k: {{"status": "pass", "evidence": "원장과 대조함"}} for k in ("source_accuracy", "calculations", "coverage", "opinion")}}
checks["visual"] = {{"status": "pass", "evidence": "[렌더 차이] 글꼴을 막고 그려 조금 다르다. 모든 타일을 열었다."}}
record = dict(copy, checks=checks, issues=[])
use("Write", {{"file_path": str(base / "audit-review.json")}})
(base / "audit-review.json").write_text(json.dumps(record, ensure_ascii=False))
audit_cmd = [sys.executable, "-B", "-I", {audit!r}, "--input", str(base / "draft" / "report-input.json"),
             "--preview", str(base / "draft" / "report.html"), "--review", str(base / "audit-review.json"),
             "--output", str(harness / ctx["audit_output_path"])]
use("Bash", {{"command": "python3 audit_report.py --input runs/%s/draft/report-input.json" % job}})
rc = subprocess.run(audit_cmd, capture_output=True, text=True).returncode
if rc == 0:
    render_cmd = [sys.executable, "-B", "-I", {render!r}, "--final", "--input", str(base / "draft" / "report-input.json"),
                  "--preview", str(base / "draft" / "report.html"), "--audit-review", str(base / "audit-review.json"),
                  "--output-dir", str(base / "final")]
    use("Bash", {{"command": "python3 render_report.py --final --input runs/%s/draft/report-input.json" % job}})
    subprocess.run(render_cmd, capture_output=True, text=True)
emit({{"type": "result", "subtype": "success"}})
'''


def _integration_env(mods, tmp_path, monkeypatch, *, skip_tile=None, hook=True):
    monkeypatch.delenv(ENV_REVIEW, raising=False)
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    runs = tmp_path / "runs"
    runs.mkdir(exist_ok=True)
    script = tmp_path / "fake-claude-review"
    script.write_text(_FAKE_CLAUDE_REVIEW.format(python=sys.executable, audit=str(_AUDIT), render=str(_RENDER)))
    script.chmod(0o755)
    if skip_tile:
        (tmp_path / "skip-tile.txt").write_text(skip_tile)
    environ = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home"),
               "AI_REPORT_GOOSE_HARNESS_DIR": str(tmp_path)}
    order: list = []

    async def runner(*, job_id, stock_name, code, on_event):
        job_dir = runs / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "input.json").write_bytes(_synthetic_input())
        proc = _py_run(str(_RENDER), "--input", str(job_dir / "input.json"), "--output-dir", str(job_dir / "draft"))
        assert proc.returncode == 0, proc.stderr[:300]
        return mods.gr.RunResult(status="done", error_kind=None, exit_code=0, delivery_status="draft")

    shot = FakeShot(order)
    reviewer = functools.partial(mods.gr.run_review, environ=environ, claude_bin=str(script),
                                 grace_sec=0.5, timeout_sec=120)
    kw = {}
    if hook:
        kw["on_finish"] = mods.gjs.goose_storage.make_finish_hook(
            runs_root=lambda: runs, stock_dir=lambda name: tmp_path / "reports" / name)
    svc = _service(mods, tmp_path, runner, monkeypatch=monkeypatch, screenshotter=shot, reviewer=reviewer, **kw)
    return svc


async def test_air6_022_admissible_final_path_with_real_audit_and_renderer(mods, tmp_path, monkeypatch):
    svc = _integration_env(mods, tmp_path, monkeypatch)
    out = await svc.start("020150", "롯데에너지머티리얼즈")
    await asyncio.wait_for(_finish(out.job), 120)
    job, job_dir = out.job, tmp_path / "runs" / out.job.job_id
    assert job.status == "done"
    audit = json.loads((job_dir / "review" / "delivery-audit.json").read_text())
    assert audit["decision"] == "pass" and audit["findings"] == []
    assert json.loads((job_dir / "final" / "render-validation.json").read_text())["delivery_allowed"] is True
    receipt = _receipt(tmp_path, job.job_id)
    assert receipt["outcome"] == "reviewed" and receipt["visual_admissible"] is True and receipt["reasons"] == []
    assert mods.gr.select_report(job_dir) == ("final", job_dir / "final")
    assert job.events[-1].data["delivery_status"] == "final"
    assert _stages(job).count("render_final") == 1
    metas = list((tmp_path / "reports").glob("*/goose/*/job.json"))
    assert json.loads(metas[0].read_text())["delivery_status"] == "final"


async def test_air6_022_control_unopened_tile_falls_to_draft(mods, tmp_path, monkeypatch):
    svc = _integration_env(mods, tmp_path, monkeypatch, skip_tile="mobile-01.png")
    out = await svc.start("020150", "롯데에너지머티리얼즈")
    await asyncio.wait_for(_finish(out.job), 120)
    job_dir = tmp_path / "runs" / out.job.job_id
    assert (job_dir / "final" / "render-validation.json").exists()  # 실제 감사기·렌더러는 통과시켰다
    receipt = _receipt(tmp_path, out.job.job_id)
    assert receipt["reasons"] == ["tile_not_read"]
    assert mods.gr.select_report(job_dir)[0] == "draft"
    assert out.job.events[-1].data["delivery_status"] == "draft"




# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-007 M3 — 네이버 최신 뉴스 사전 수집 연결 (REQ-AIR7-001~004·008·012·015)
# ─────────────────────────────────────────────────────────────────────────────

_NAVER_FIX = Path(__file__).parent / "fixtures" / "naver"
_ENV_NAVER = "AI_REPORT_GOOSE_NAVER_PREFETCH"


class FakeNaver:
    """네이버 수집기 대역: 순서·인자를 기록하고, gate가 열릴 때까지 기다린다."""

    def __init__(self, order: list | None = None, *, wait: bool = False, raise_exc=None):
        self.order = order if order is not None else []
        self.calls: list[tuple[str, Path, bool]] = []
        self.entered = asyncio.Event()
        self.gate = asyncio.Event()
        if not wait:
            self.gate.set()
        self.raise_exc = raise_exc

    async def __call__(self, code, out_dir, *, code_validated=False):
        self.order.append("naver")
        self.calls.append((code, Path(out_dir), code_validated))
        self.entered.set()
        if self.raise_exc is not None:
            raise self.raise_exc
        await self.gate.wait()
        return {"outcome": "complete"}


def _fake_dart(order: list):
    async def dart(code, out_dir):
        order.append("dart")
        return {"outcome": "complete"}

    return dart


def _naver_recorder(body: bytes | None = None, *, status: int = 200, respond=None):
    """실제 네이버 수집기 + 모든 요청을 기록하는 MockTransport."""
    httpx = __import__("httpx")
    requests: list = []

    async def handle(request):
        requests.append(str(request.url))
        if respond is not None:
            resp = respond(request)
            if asyncio.iscoroutine(resp):
                resp = await resp
            return resp
        return httpx.Response(status, content=body or b"")

    return httpx.MockTransport(handle), requests


def _real_naver(mods, transport):
    return mods.gjs.goose_naver_prefetch.NaverPrefetcher(transport=transport)


def _naver_index(tmp_path: Path, job) -> dict:
    path = tmp_path / "runs" / job.job_id / "naver" / "index.json"
    return __import__("json").loads(path.read_text(encoding="utf-8"))


def _progress_stages(job) -> list:
    return [e.data.get("stage") for e in job.events if e.type == "progress"]


async def _run_job(svc):
    out = await asyncio.wait_for(svc.start("020150", "롯데에너지머티리얼즈"), 2)
    assert out.kind == "started"
    await asyncio.wait_for(_finish(out.job), 5)
    return out.job


# ── AC-AIR7-001 — 실행 순서 ─────────────────────────────────────────────────


async def test_air7_001_order_with_dart_and_naver(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    order: list = []
    naver = FakeNaver(order)
    svc = _service(mods, tmp_path, OrderRunner(mods.gr, order), integrity=_order_integrity(mods.gh, order),
                   prefetcher=_fake_dart(order), naver_prefetcher=naver)
    job = await _run_job(svc)
    assert order == ["integrity", "dart", "naver", "integrity", "runner"]
    assert [c[:2] for c in naver.calls] == [("020150", tmp_path / "runs" / job.job_id / "naver")]
    assert (job.status, job.error_kind) == ("done", None)


async def test_air7_001_order_with_naver_only(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    order: list = []
    svc = _service(mods, tmp_path, OrderRunner(mods.gr, order), integrity=_order_integrity(mods.gh, order),
                   naver_prefetcher=FakeNaver(order))
    job = await _run_job(svc)
    assert order == ["integrity", "naver", "integrity", "runner"]
    assert job.status == "done"


async def test_air7_001_order_without_prefetchers(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    order: list = []
    svc = _service(mods, tmp_path, OrderRunner(mods.gr, order), integrity=_order_integrity(mods.gh, order))
    job = await _run_job(svc)
    assert order == ["integrity", "runner"]
    assert not (tmp_path / "runs" / job.job_id / "naver").exists()


async def test_air7_001_second_integrity_failure_with_naver_only(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    order: list = []
    runner = OrderRunner(mods.gr, order)
    svc = _service(mods, tmp_path, runner, integrity=_order_integrity(mods.gh, order, fail_on=2),
                   naver_prefetcher=FakeNaver(order))
    job = await _run_job(svc)
    assert (job.status, job.error_kind) == ("error", "integrity")
    assert runner.calls == []


def test_air7_013_defaults_have_no_naver_and_production_injects_it(mods):
    default = mods.gjs.GooseJobService()
    assert default._naver_prefetcher is None and default._code_check is None
    prod = mods.gjs.get_service()
    assert isinstance(prod._naver_prefetcher, mods.gjs.goose_naver_prefetch.NaverPrefetcher)
    assert callable(prod._code_check)


# ── AC-AIR7-002 — 수집 중 취소 ──────────────────────────────────────────────


async def test_air7_002_cancel_and_shutdown_during_fake_naver_prefetch(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)

    async def scenario():
        for how in ("cancel", "shutdown"):
            naver = FakeNaver(wait=True)  # gate가 열리지 않는다 = 영원히 대기
            runner = FakeRunner(mods.gr)
            runner.release.set()
            svc = _service(mods, tmp_path / how, runner, naver_prefetcher=naver)
            job = (await svc.start("020150", "롯데에너지머티리얼즈")).job
            await naver.entered.wait()
            if how == "cancel":
                await svc.cancel(job.job_id)
            else:
                await svc.shutdown()
            assert (job.status, job.error_kind) == ("cancelled", None), how
            assert job.events[-1].type == "cancelled", how
            assert runner.calls == [], how
            assert svc.active() is None

    await asyncio.wait_for(scenario(), 5)


async def test_air7_002_cancel_and_shutdown_during_real_naver_request(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)

    async def scenario():
        for how in ("cancel", "shutdown"):
            entered, never = asyncio.Event(), asyncio.Event()

            async def hang(request):  # 비동기 처리기 — 스레드를 쓰지 않는다
                entered.set()
                await never.wait()
                return __import__("httpx").Response(200, content=b"[]")

            transport, _ = _naver_recorder(respond=hang)
            runner = FakeRunner(mods.gr)
            runner.release.set()
            svc = _service(mods, tmp_path / how, runner, naver_prefetcher=_real_naver(mods, transport))
            job = (await svc.start("020150", "롯데에너지머티리얼즈")).job
            await entered.wait()
            if how == "cancel":
                await svc.cancel(job.job_id)
            else:
                await svc.shutdown()
            assert (job.status, job.error_kind) == ("cancelled", None), how
            assert job.events[-1].type == "cancelled", how
            assert runner.calls == [], how

    await asyncio.wait_for(scenario(), 5)


# ── AC-AIR7-003 — 끄기 스위치 ───────────────────────────────────────────────


async def test_air7_003_switch_off_skips_naver_prefetcher_and_writes_disabled_index(mods, tmp_path, monkeypatch):
    transport, requests = _naver_recorder((_NAVER_FIX / "recorded" / "020150_p1.json").read_bytes())
    real = _real_naver(mods, transport)
    calls = {"n": 0}

    async def spy(code, out_dir, *, code_validated=False):  # 작업 서비스가 수집기를 부른 횟수
        calls["n"] += 1
        return await real(code, out_dir, code_validated=code_validated)

    monkeypatch.setenv(_ENV_NAVER, "0")
    runner = FakeRunner(mods.gr)
    runner.release.set()
    job = await _run_job(_service(mods, tmp_path / "off", runner, naver_prefetcher=spy))
    index = _naver_index(tmp_path / "off", job)
    assert requests == []
    assert calls["n"] == 0
    assert index["outcome"] == "disabled" and index["articles"] == []
    assert len(runner.calls) == 1 and job.status == "done"

    # 대조: 변수 미설정이면 수집기 호출 1, 요청 1
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    runner2 = FakeRunner(mods.gr)
    runner2.release.set()
    job2 = await _run_job(_service(mods, tmp_path / "on", runner2, naver_prefetcher=spy))
    assert calls["n"] == 1
    assert len(requests) == 1
    assert _naver_index(tmp_path / "on", job2)["outcome"] == "complete"


# ── AC-AIR7-004 — 진행 이벤트 없음 ──────────────────────────────────────────


async def test_air7_004_naver_prefetch_adds_no_progress_event(mods, tmp_path, monkeypatch):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    monkeypatch.delenv("AI_REPORT_GOOSE_DART_PREFETCH", raising=False)
    stages = {}
    for variant in ("with_naver", "without_naver"):
        kw = {"naver_prefetcher": FakeNaver()} if variant == "with_naver" else {}
        runner = FakeRunner(mods.gr, events=("goose_start",))
        runner.release.set()
        job = await _run_job(_service(mods, tmp_path / variant, runner, prefetcher=FakePrefetcher(), **kw))
        stages[variant] = _progress_stages(job)
    assert stages["with_naver"] == stages["without_naver"] == ["dart_prefetch", "goose_start"]
    assert not [s for s in stages["with_naver"] if "naver" in str(s)]


# ── AC-AIR7-008 — 실패해도 goose는 진행 ─────────────────────────────────────


def _naver_failure(case):
    httpx = __import__("httpx")
    syn = _NAVER_FIX / "synthetic"

    def connect_error(request):
        raise httpx.ConnectError("refused", request=request)

    return {
        "connect_error": dict(respond=connect_error),
        "http_410": dict(body=b"gone", status=410),
        "http_500": dict(body=b"down", status=500),
        "not_json": dict(body=(syn / "not_json.txt").read_bytes()),
        "missing_items_path": dict(body=(syn / "missing_items_path.json").read_bytes()),
        "top_level_object": dict(body=(syn / "top_level_object.json").read_bytes()),
    }[case]


@pytest.mark.parametrize(
    "case", ["connect_error", "http_410", "http_500", "not_json", "missing_items_path", "top_level_object"]
)
async def test_air7_008_naver_failures_still_run_goose(mods, tmp_path, monkeypatch, case):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    transport, requests = _naver_recorder(**_naver_failure(case))
    runner = FakeRunner(mods.gr)
    runner.release.set()
    job = await _run_job(_service(mods, tmp_path, runner, naver_prefetcher=_real_naver(mods, transport)))
    assert len(requests) == 1
    assert len(runner.calls) == 1
    assert (job.status, job.error_kind) == ("done", None)
    index = _naver_index(tmp_path, job)
    assert index["outcome"] == "failed" and index["search"]["error"]


async def test_air7_008_naver_prefetcher_exception_does_not_stop_goose(mods, tmp_path, monkeypatch, caplog):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    runner = FakeRunner(mods.gr)
    runner.release.set()
    svc = _service(mods, tmp_path, runner, naver_prefetcher=FakeNaver(raise_exc=RuntimeError("naver boom")))
    with caplog.at_level("ERROR"):
        job = await _run_job(svc)
    assert len(runner.calls) == 1
    assert (job.status, job.error_kind) == ("done", None)
    recs = [r for r in caplog.records if r.levelname == "ERROR" and job.job_id in r.getMessage()]
    assert recs and isinstance(recs[0].exc_info[1], RuntimeError)


# ── AC-AIR7-015 — 종목코드 확인 기록 ────────────────────────────────────────


def _raise_check(code):
    raise RuntimeError("registry unavailable")


@pytest.mark.parametrize(
    "variant,check,expected",
    [("a_true", lambda c: True, True), ("b_false", lambda c: False, False),
     ("c_absent", None, False), ("d_raises", _raise_check, False)],
)
async def test_air7_015_code_validated_passed_to_index(mods, tmp_path, monkeypatch, variant, check, expected):
    monkeypatch.delenv(_ENV_NAVER, raising=False)
    transport, requests = _naver_recorder((_NAVER_FIX / "recorded" / "999999_p1.json").read_bytes())
    real = _real_naver(mods, transport)
    calls = {"n": 0}

    async def spy(code, out_dir, *, code_validated=False):
        calls["n"] += 1
        return await real(code, out_dir, code_validated=code_validated)

    kw = {"code_check": check} if check is not None else {}
    runner = FakeRunner(mods.gr)
    runner.release.set()
    job = await _run_job(_service(mods, tmp_path, runner, naver_prefetcher=spy, **kw))
    index = _naver_index(tmp_path, job)
    assert calls["n"] == 1 and len(requests) == 1
    assert index["outcome"] == "no_results" and index["search"]["item_count"] == 0
    assert index["code_validated"] is expected
    assert len(runner.calls) == 1 and job.status == "done"


async def test_air7_015_disabled_index_records_code_validated(mods, tmp_path, monkeypatch):
    monkeypatch.setenv(_ENV_NAVER, "0")
    transport, requests = _naver_recorder((_NAVER_FIX / "recorded" / "999999_p1.json").read_bytes())
    runner = FakeRunner(mods.gr)
    runner.release.set()
    job = await _run_job(_service(mods, tmp_path, runner, naver_prefetcher=_real_naver(mods, transport),
                                  code_check=lambda c: True))
    index = _naver_index(tmp_path, job)
    assert index["outcome"] == "disabled"
    assert index["code_validated"] is True
    assert requests == []


async def test_air7_015_production_code_check_uses_server_stock_list(mods, monkeypatch):
    # test_ai_report_service.py가 sys.modules에 my_chart.registry 스텁을 영구히 심는다(같은 세션에서 먼저
    # 돌면 이 검사가 스텁을 보게 된다). 이 테스트 동안만 지워 실제 서버 종목 목록을 읽게 한다(종료 때 복원)
    monkeypatch.delitem(sys.modules, "my_chart.registry", raising=False)
    monkeypatch.delitem(sys.modules, "backend.services.ai_report_service", raising=False)
    check = mods.gjs.get_service()._code_check
    assert await asyncio.wait_for(asyncio.to_thread(check, "020150"), 30) is True
    assert await asyncio.wait_for(asyncio.to_thread(check, "999999"), 30) is False


# ── 병합 통합 (SPEC-AI-REPORT-007 plan §5 단계 4) — 006 후처리와 007 네이버 수집이 함께 주입된 경우 ──────


async def test_merge_007_006_run_order_and_identical_event_lists(mods, tmp_path, monkeypatch):
    """DART → 네이버 → 1차 세션 → 캡처 → 감수 순서이고, 진행 이벤트 목록은 네이버 주입 유무와 같다."""
    stages: dict = {}
    orders: dict = {}
    for variant in ("with_naver", "without_naver"):
        ctx = _post_service(mods, tmp_path / variant, monkeypatch)
        ctx.svc._prefetcher = _fake_dart(ctx.order)
        if variant == "with_naver":
            ctx.svc._naver_prefetcher = FakeNaver(ctx.order)
        monkeypatch.delenv(_ENV_NAVER, raising=False)
        job = await _run_post(ctx)
        assert job.status == "done"
        stages[variant] = _stages(job)
        orders[variant] = list(ctx.order)
    assert orders["with_naver"] == ["integrity", "dart", "naver", "integrity", "runner", "integrity", "screenshot", "review"]
    assert orders["without_naver"] == ["integrity", "dart", "integrity", "runner", "integrity", "screenshot", "review"]
    assert stages["with_naver"] == stages["without_naver"]
    assert stages["with_naver"].index("dart_prefetch") < stages["with_naver"].index("screenshot")
    assert not [s for s in stages["with_naver"] if "naver" in str(s)]
