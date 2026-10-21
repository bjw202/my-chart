"""SPEC-AI-REPORT-004 M4 — goose 작업 라우터(mode=deep, 이벤트·취소·active) HTTP 테스트.

테스트 대상: backend/routers/ai_report.py 의 goose 경로
- AC-AIR4-001 라우터 쪽 (2b)(3)(4)(5): 실제 원본 대조·설치(tmp) + 실제 무결성 검사 + 실제 실행기
  (가짜 claude 실행 파일이 호출 횟수를 파일에 기록)
- AC-AIR4-007·008 시작 판정 순서와 응답 코드, AC-AIR4-009 SSE 재생, AC-AIR4-011 취소,
  AC-AIR4-021 `GET /ai-report/goose/active` 등록 순서, B5 동시 요청

격리 원칙:
- 실제 `claude`·실제 홈·실제 ~/.goose-harness를 쓰지 않는다(tmp_path만).
- ai_report_service는 sys.modules 스텁(monkeypatch로 되돌림)으로 대체하고
  라우터 파일을 경로로 불러온다. goose 모듈은 가짜 상위 패키지 아래에서 새로 불러온다.
- HTTP는 httpx.AsyncClient + ASGITransport — 백그라운드 작업이 테스트와 같은 이벤트 루프에서 돈다.
"""

from __future__ import annotations

import asyncio
import functools
import hashlib
import importlib
import importlib.util
import json
import re
import shutil
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import FastAPI

_BACKEND = Path(__file__).resolve().parents[1]
_ROUTER_PATH = _BACKEND / "routers" / "ai_report.py"
_SOURCE = _BACKEND / "goose_harness_src"
_NAMES = {"299030": "하나기술", "005930": "삼성전자"}


class FakeRunner:
    def __init__(self, gr, events=()):
        self.gr = gr
        self.calls: list[str] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.events = list(events)

    async def __call__(self, *, job_id, stock_name, code, on_event):
        self.calls.append(code)
        for stage in self.events:
            await on_event(self.gr.ProgressEvent(stage))
        self.started.set()
        await self.release.wait()
        return self.gr.RunResult(status="done", error_kind=None, exit_code=0, delivery_status="draft")


@pytest.fixture
def env(monkeypatch, tmp_path):
    """라우터·서비스를 격리 로드하고 테스트 앱을 만든다."""
    saved = {k: v for k, v in sys.modules.items() if k == "backend" or k.startswith("backend.")}
    for pkg, path in (
        ("backend", _BACKEND),
        ("backend.services", _BACKEND / "services"),
        ("backend.schemas", _BACKEND / "schemas"),
        ("backend.routers", _BACKEND / "routers"),
    ):
        mod = types.ModuleType(pkg)
        mod.__path__ = [str(path)]  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, pkg, mod)
    for name in ("backend.services.goose_harness", "backend.services.goose_runner",
                 "backend.services.goose_job_service", "backend.schemas.ai_report"):
        monkeypatch.delitem(sys.modules, name, raising=False)

    fast_stub = types.SimpleNamespace(
        _active_analyses=set(),
        RateLimitError=type("RateLimitError", (Exception,), {}),
        check_rate_limit=MagicMock(),
        get_history=MagicMock(return_value=[]),
        get_report_content=MagicMock(return_value=None),
        get_goose_report_path=MagicMock(return_value=None),  # M5 라우터가 불러오는 이름
        get_stock_name=lambda code: _NAMES.get(code),
        stream_codex_fast=MagicMock(),
    )
    monkeypatch.setitem(sys.modules, "backend.services.ai_report_service", fast_stub)

    gh = importlib.import_module("backend.services.goose_harness")
    gr = importlib.import_module("backend.services.goose_runner")
    gjs = importlib.import_module("backend.services.goose_job_service")
    spec = importlib.util.spec_from_file_location("_goose_test_router", _ROUTER_PATH)
    router_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(router_mod)  # type: ignore[union-attr]
    monkeypatch.setattr(router_mod.shutil, "which", lambda name: f"/usr/local/bin/{name}")

    app = FastAPI()
    app.include_router(router_mod.router, prefix="/api")
    ns = types.SimpleNamespace(gh=gh, gr=gr, gjs=gjs, router=router_mod, app=app,
                               fast=fast_stub, tmp=tmp_path)

    def use(runner, integrity=None, runs_root=None):
        svc = gjs.GooseJobService(
            runner=runner,
            integrity_check=integrity if integrity is not None else (lambda: gh.IntegrityResult(True, "ok")),
            runs_root=runs_root or (lambda: tmp_path / "runs"),
        )
        gjs.set_service(svc)
        return svc

    ns.use = use
    yield ns
    gh.reset_state()
    for k in [k for k in sys.modules if k == "backend" or k.startswith("backend.")]:
        if k not in saved:
            del sys.modules[k]


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _finish(job):
    if job.task is not None:
        await asyncio.gather(job.task, return_exceptions=True)


def _sse_ids(text: str) -> list[tuple[int, str]]:
    blocks = [b for b in re.split(r"\r?\n\r?\n", text) if b.strip()]
    out = []
    for block in blocks:
        fields = dict(
            line.split(": ", 1) for line in re.split(r"\r?\n", block) if ": " in line
        )
        if "id" in fields:
            out.append((int(fields["id"]), fields.get("event", "message")))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# AC-007 / AC-008 / B5
# ─────────────────────────────────────────────────────────────────────────────


async def test_ac007_second_same_code_request_returns_200_same_job(env):
    runner = FakeRunner(env.gr)
    svc = env.use(runner)
    async with _client(env.app) as c:
        r1 = await c.post("/api/ai-report/299030", params={"mode": "deep"})
        r2 = await c.post("/api/ai-report/299030", params={"mode": "deep"})
    assert (r1.status_code, r2.status_code) == (202, 200)
    assert r1.json()["job_id"] == r2.json()["job_id"]
    await runner.started.wait()
    assert runner.calls == ["299030"]
    runner.release.set()
    await _finish(svc.get(r1.json()["job_id"]))


# 하루 실행 횟수 제한(옛 1·7행 goose_rate_limit)은 사용자 결정(2026-10-21)으로 없앴다.
@pytest.mark.parametrize(
    "row,running,code,which,expect_status,expect_error",
    [
        (2, False, "12AB56", True, 422, None),
        (3, False, "999999", True, 404, None),
        (4, False, "299030", False, 503, None),
        (5, True, "299030", True, 200, None),
        (6, True, "005930", True, 429, "goose_busy"),
    ],
)
async def test_ac008_decision_order(env, monkeypatch, row, running, code, which,
                                    expect_status, expect_error):
    runner = FakeRunner(env.gr)
    svc = env.use(runner)
    running_job = None
    if running:
        running_job = (await svc.start("299030", "하나기술")).job
        await runner.started.wait()
    if not which:
        monkeypatch.setattr(env.router.shutil, "which", lambda name: None)
    calls_before = len(runner.calls)
    async with _client(env.app) as c:
        r = await c.post(f"/api/ai-report/{code}", params={"mode": "deep"})
    assert r.status_code == expect_status, r.text
    if expect_error:
        assert r.json()["detail"]["error"] == expect_error
    if row == 5:
        assert r.json()["job_id"] == running_job.job_id
    if row == 6:
        assert "하나기술" in r.json()["detail"]["detail"]
    assert len(runner.calls) == calls_before  # 실행기 추가 호출 0
    # Fast rate limit(분당 버스트)은 건드리지 않는다
    env.fast.check_rate_limit.assert_not_called()
    runner.release.set()
    if running_job is not None:
        await _finish(running_job)


async def test_b5_two_simultaneous_requests_exactly_one_runs(env):
    runner = FakeRunner(env.gr)
    svc = env.use(runner)
    async with _client(env.app) as c:
        r1, r2 = await asyncio.gather(
            c.post("/api/ai-report/299030", params={"mode": "deep"}),
            c.post("/api/ai-report/005930", params={"mode": "deep"}),
        )
    codes = sorted([r1.status_code, r2.status_code])
    assert codes == [202, 429]
    loser = r1 if r1.status_code == 429 else r2
    assert loser.json()["detail"]["error"] == "goose_busy"
    await runner.started.wait()
    assert len(runner.calls) == 1
    runner.release.set()
    await _finish(svc.get((r1 if r1.status_code == 202 else r2).json()["job_id"]))


async def test_many_sequential_deep_requests_same_day_are_never_rate_limited(env):
    """사용자 결정(2026-10-21): 하루 실행 횟수 제한 없음. 같은 날 7번 연달아 요청해도 모두 202."""
    runner = FakeRunner(env.gr)
    runner.release.set()
    svc = env.use(runner)
    statuses = []
    async with _client(env.app) as c:
        for _ in range(7):
            r = await c.post("/api/ai-report/299030", params={"mode": "deep"})
            statuses.append(r.status_code)
            assert "goose_rate_limit" not in r.text
            await _finish(svc.get(r.json()["job_id"]))
    assert statuses == [202] * 7
    assert len(runner.calls) == 7


# M7: 옛 test_ai_report_router_deep_mode.py(삭제)의 Fast 경로 시험(mode 없음·fast·perplexity 알리아스,
# 잘못된 mode 422)을 여기로 옮겼다.
@pytest.mark.parametrize("params", [{}, {"mode": "fast"}, {"mode": "perplexity"}],
                         ids=["no-mode", "fast", "perplexity-alias"])
async def test_fast_mode_path_is_unchanged_by_goose_routing(env, params):
    """mode 없음·fast·perplexity(옛 알리아스)는 goose 서비스를 거치지 않는다(codex 경로 그대로)."""
    runner = FakeRunner(env.gr)
    env.use(runner)
    fast_calls: list[str] = []

    async def fake_stream(name, code):
        fast_calls.append(code)
        yield {"event": "done", "data": "ok"}

    env.fast.stream_codex_fast = fake_stream
    env.router.stream_codex_fast = fake_stream
    async with _client(env.app) as c:
        r = await c.post("/api/ai-report/299030", params=params)
    assert r.status_code == 200
    assert "text/event-stream" in r.headers.get("content-type", "")
    assert fast_calls == ["299030"]
    assert runner.calls == []
    env.fast.check_rate_limit.assert_called_once()


@pytest.mark.parametrize(
    "codex,running,limited,expect_status,expect_error",
    [
        (False, True, True, 503, "codex_cli_missing"),
        (True, True, True, 429, "already_running"),
        (True, False, True, 429, "rate_limit"),
    ],
    ids=["503-first", "dup-before-quota", "quota-last"],
)
async def test_fast_guard_order_503_then_duplicate_then_quota(env, monkeypatch, codex, running, limited,
                                                               expect_status, expect_error):
    """AC-024: Fast 라우터 검사 순서(503 → 429 중복 → 429 쿼터)가 goose 라우팅 추가 뒤에도 그대로다."""
    runner = FakeRunner(env.gr)
    env.use(runner)
    monkeypatch.setattr(env.router.shutil, "which",
                        lambda name: f"/usr/local/bin/{name}" if codex else None)
    if running:
        env.router._active_analyses.add("299030")
    if limited:
        env.fast.check_rate_limit.side_effect = env.fast.RateLimitError("limit")
    try:
        async with _client(env.app) as c:
            r = await c.post("/api/ai-report/299030", params={"mode": "fast"})
    finally:
        env.router._active_analyses.discard("299030")
    assert r.status_code == expect_status, r.text
    assert r.json()["detail"]["error"] == expect_error
    assert runner.calls == []


async def test_invalid_mode_returns_422_without_any_analysis(env):
    """허용 목록(fast|deep|perplexity) 밖의 mode는 422, Fast·goose 어느 쪽도 시작하지 않는다."""
    runner = FakeRunner(env.gr)
    env.use(runner)
    async with _client(env.app) as c:
        r = await c.post("/api/ai-report/299030", params={"mode": "unknown"})
    assert r.status_code == 422
    assert runner.calls == []
    env.fast.check_rate_limit.assert_not_called()


# ─────────────────────────────────────────────────────────────────────────────
# AC-021 active / AC-009 events / AC-011 cancel
# ─────────────────────────────────────────────────────────────────────────────


async def test_ac021_active_running_and_null(env):
    runner = FakeRunner(env.gr)
    svc = env.use(runner)
    async with _client(env.app) as c:
        none = await c.get("/api/ai-report/goose/active")
        job_id = (await c.post("/api/ai-report/299030", params={"mode": "deep"})).json()["job_id"]
        running = await c.get("/api/ai-report/goose/active")
        runner.release.set()
        await _finish(svc.get(job_id))
        after = await c.get("/api/ai-report/goose/active")
    assert (none.status_code, none.json()) == (200, None)
    assert running.status_code == 200
    assert running.json() == {"job_id": job_id, "code": "299030", "stock_name": "하나기술",
                              "status": "running"}
    assert after.json() is None


def test_ac021_active_route_registered_before_code_filename_route(env):
    paths = [getattr(r, "path", "") for r in env.router.router.routes]
    assert paths.index("/ai-report/goose/active") < paths.index("/ai-report/{code}/{filename}")


async def test_ac009_sse_replay_and_last_event_id_over_http(env):
    runner = FakeRunner(env.gr, events=("goose_start", "plan", "plan", "research_tick", "compose"))
    svc = env.use(runner)
    async with _client(env.app) as c:
        job_id = (await c.post("/api/ai-report/299030", params={"mode": "deep"})).json()["job_id"]
        await runner.started.wait()
        runner.release.set()
        await _finish(svc.get(job_id))
        full = await c.get(f"/api/ai-report/jobs/{job_id}/events")
        tail = await c.get(f"/api/ai-report/jobs/{job_id}/events", headers={"Last-Event-ID": "3"})
        bad = await c.get(f"/api/ai-report/jobs/{job_id}/events", headers={"Last-Event-ID": "x"})
        missing = await c.get("/api/ai-report/jobs/nope/events")
    assert full.status_code == 200
    assert _sse_ids(full.text) == [(1, "progress"), (2, "progress"), (3, "progress"),
                                   (4, "progress"), (5, "progress"), (6, "done")]
    assert [i for i, _ in _sse_ids(tail.text)] == [4, 5, 6]
    assert [i for i, _ in _sse_ids(bad.text)] == [1, 2, 3, 4, 5, 6]
    assert missing.status_code == 404
    data_lines = [ln for ln in re.split(r"\r?\n", full.text) if ln.startswith("data: ")]
    assert json.loads(data_lines[0][6:]) == {"stage": "goose_start", "detail": None}


async def test_ac011_cancel_routes(env):
    runner = FakeRunner(env.gr)
    svc = env.use(runner)
    async with _client(env.app) as c:
        job_id = (await c.post("/api/ai-report/299030", params={"mode": "deep"})).json()["job_id"]
        await runner.started.wait()
        r = await c.post(f"/api/ai-report/jobs/{job_id}/cancel")
        again = await c.post(f"/api/ai-report/jobs/{job_id}/cancel")
        missing = await c.post("/api/ai-report/jobs/nope/cancel")
        events = await c.get(f"/api/ai-report/jobs/{job_id}/events")
    assert r.status_code == 200
    assert r.json() == {"job_id": job_id, "status": "cancelled", "error_kind": None}
    assert again.json()["status"] == "cancelled"
    assert missing.status_code == 404
    assert _sse_ids(events.text)[-1][1] == "cancelled"
    assert svc.active() is None


# ─────────────────────────────────────────────────────────────────────────────
# AC-001 라우터 쪽 (2b)(3)(4)(5) — 실제 설치·무결성·실행기
# ─────────────────────────────────────────────────────────────────────────────


def _tree_sha(root: Path) -> dict[str, str]:
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file() and "runs" not in p.relative_to(root).parts
    }


@pytest.fixture
def harness(env):
    """tmp 원본 사본을 tmp 하네스에 설치하고, 호출 횟수를 기록하는 가짜 claude를 만든다."""
    tmp = env.tmp
    src = tmp / "src"
    shutil.copytree(_SOURCE, src, ignore=shutil.ignore_patterns(".DS_Store"))
    H = tmp / "H"
    (H / "runs").mkdir(parents=True)
    (H / "runs" / "keep.txt").write_text("keep")
    counter = tmp / "calls.txt"
    fake = tmp / "fake-claude"
    fake.write_text(f'#!/bin/bash\necho run >> "{counter}"\nexit 0\n')
    fake.chmod(0o755)
    environ = {"PATH": "/usr/bin:/bin", "HOME": str(tmp / "home"),
               "AI_REPORT_GOOSE_HARNESS_DIR": str(H)}
    runner = functools.partial(env.gr.run_goose, environ=environ, claude_bin=str(fake),
                               grace_sec=0.5, timeout_sec=20)

    def restart():
        """서버 재시작: 프로세스 상태 초기화 → 시작 설치 → 새 작업 서비스."""
        env.gh.reset_state()
        status = env.gh.install_at_startup(source_dir=src, harness_dir=H)
        svc = env.gjs.GooseJobService(runner=runner, runs_root=lambda: H / "runs")
        env.gjs.set_service(svc)
        return status, svc

    def calls() -> int:
        return len(counter.read_text().splitlines()) if counter.exists() else 0

    return types.SimpleNamespace(src=src, H=H, restart=restart, calls=calls)


async def _post_integrity_case(env, svc, harness):
    async with _client(env.app) as c:
        r = await c.post("/api/ai-report/299030", params={"mode": "deep"})
        active = await c.get("/api/ai-report/goose/active")
    assert r.status_code == 202
    job = svc.get(r.json()["job_id"])
    await _finish(job)
    assert (job.status, job.error_kind) == ("error", "integrity")
    assert harness.calls() == 0
    assert active.json() is None


async def test_ac001_2b_source_changed_after_install_fails_closed(env, harness):
    status, _ = harness.restart()
    assert status.ok, status.reason
    installed_before = _tree_sha(harness.H)
    target = sorted((harness.src / "skills" / "goose").rglob("*.md"))[0]
    target.write_bytes(target.read_bytes() + b"x")
    status, svc = harness.restart()
    assert status.ok is False
    assert _tree_sha(harness.H) == installed_before  # 교체 안 됨
    assert (harness.H / "runs" / "keep.txt").read_text() == "keep"
    await _post_integrity_case(env, svc, harness)


async def test_ac001_3_installed_file_changed_blocks_job(env, harness):
    status, svc = harness.restart()
    assert status.ok, status.reason
    target = sorted((harness.H / ".claude" / "skills" / "goose").rglob("*.md"))[0]
    target.write_bytes(target.read_bytes() + b"x")
    await _post_integrity_case(env, svc, harness)


async def test_ac001_4_unlisted_installed_file_blocks_job(env, harness):
    status, svc = harness.restart()
    assert status.ok, status.reason
    (harness.H / ".claude" / "settings.local.json").write_text("{}")
    await _post_integrity_case(env, svc, harness)


async def test_ac001_5_restart_restores_install_and_runs_once(env, harness):
    status, svc = harness.restart()
    assert status.ok
    target = sorted((harness.H / ".claude" / "skills" / "goose").rglob("*.md"))[0]
    target.write_bytes(target.read_bytes() + b"x")
    await _post_integrity_case(env, svc, harness)
    status, svc = harness.restart()
    assert status.ok, status.reason
    async with _client(env.app) as c:
        r = await c.post("/api/ai-report/299030", params={"mode": "deep"})
    assert r.status_code == 202
    job = svc.get(r.json()["job_id"])
    await _finish(job)
    assert harness.calls() == 1
    # 가짜 claude는 리포트 없이 exit 0 → empty_output(실행기 분류 그대로)
    assert (job.status, job.error_kind) == ("error", "empty_output")
