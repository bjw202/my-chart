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
import importlib
import os
import signal
import sys
import time
import types
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
