"""SPEC-AI-REPORT-004 M5 — goose 리포트 저장과 서빙 테스트.

테스트 대상:
- backend/services/goose_storage.py — final 판정 후 허용 파일 + assumptions.md 복사, job.json, 기록 항목,
  HTML 경로 검증(design §5.1~5.4)
- backend/services/goose_job_service.py — 종료 훅 배선(종료 상태를 훅 전에 확정)
- backend/services/ai_report_service.py — get_history(kind markdown + goose), get_goose_report_path
- backend/routers/ai_report.py — GET /ai-report/{code}/goose/{run}/report.html (CSP), 기록 API
- AC-AIR4-010(보관 절반), 013, 014 (a)~(g), 015, 016, 017

격리 원칙:
- 실제 `claude`를 띄우지 않는다. 작업 디렉터리에 산출물을 쓰는 tmp_path의 가짜 실행 파일만 쓴다.
- 실제 홈·~/.goose-harness·backend/reports를 건드리지 않는다. 리포트 루트(`_REPORTS_BASE`)와
  하네스·runs 경로는 tmp_path로 바꾼다.
- 다른 테스트 모듈이 `my_chart`를 sys.modules 스텁으로 바꿔 두므로, 이 파일은 `my_chart*`·`backend*`
  항목만 잠시 비우고 실제 모듈을 불러온 뒤 그 항목만 되돌린다(test_goose_runner와 같은 방식).
"""

from __future__ import annotations

import asyncio
import functools
import importlib
import json
import sys
import time
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

_KST = timezone(timedelta(hours=9))
_NAMES = {"299030": "하나기술", "005930": "삼성전자"}
_NOW = datetime(2026, 10, 19, 14, 30, tzinfo=_KST)
_ALLOWED = {"report.html", "report-input.json", "source-ledger.json", "render-validation.json"}
_CSP = (
    "sandbox allow-popups allow-popups-to-escape-sandbox allow-downloads; "
    "default-src 'none'; style-src 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src https://cdn.jsdelivr.net https://fonts.gstatic.com; img-src data:"
)


def _ours(name: str) -> bool:
    return name in ("my_chart", "backend") or name.startswith(("my_chart.", "backend."))


@pytest.fixture(scope="module")
def real():
    saved = {name: mod for name, mod in sys.modules.items() if _ours(name)}
    for name in saved:
        del sys.modules[name]
    try:
        yield types.SimpleNamespace(
            gh=importlib.import_module("backend.services.goose_harness"),
            gr=importlib.import_module("backend.services.goose_runner"),
            gs=importlib.import_module("backend.services.goose_storage"),
            gjs=importlib.import_module("backend.services.goose_job_service"),
            ars=importlib.import_module("backend.services.ai_report_service"),
            router=importlib.import_module("backend.routers.ai_report"),
        )
    finally:
        for name in [n for n in sys.modules if _ours(n)]:
            del sys.modules[name]
        sys.modules.update(saved)


@pytest.fixture
def env(real, monkeypatch, tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    harness = tmp_path / "harness"
    runs = harness / "runs"
    runs.mkdir(parents=True)
    monkeypatch.setattr(real.ars, "_REPORTS_BASE", reports)
    monkeypatch.setattr(real.router, "get_stock_name", lambda code: _NAMES.get(code))
    app = FastAPI()
    app.include_router(real.router.router, prefix="/api")
    ns = types.SimpleNamespace(
        real=real, tmp=tmp_path, reports=reports, harness=harness, runs=runs, app=app,
        stock_dir=reports / "하나기술",
    )

    def service(runner):
        hook = real.gs.make_finish_hook(
            runs_root=lambda: runs, stock_dir=real.ars.report_dir, clock=lambda: _NOW
        )
        svc = real.gjs.GooseJobService(
            runner=runner,
            integrity_check=lambda: real.gh.IntegrityResult(True, "ok"),
            runs_root=lambda: runs,
            on_finish=hook,
        )
        monkeypatch.setattr(real.gjs, "_service", svc)
        return svc

    ns.service = service
    return ns


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def _raw_get(app, raw_path: str) -> tuple[int, bytes]:
    """httpx가 `..` 세그먼트를 지우므로 ASGI 앱을 직접 호출한다(서버가 받는 그대로의 경로)."""
    from urllib.parse import unquote

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET",
        "scheme": "http", "path": unquote(raw_path), "raw_path": raw_path.encode(),
        "root_path": "", "query_string": b"", "headers": [(b"host", b"test")],
        "client": ("127.0.0.1", 1), "server": ("test", 80),
    }
    status = 0
    body = b""

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status, body
        if message["type"] == "http.response.start":
            status = message["status"]
        elif message["type"] == "http.response.body":
            body += message.get("body", b"")

    await app(scope, receive, send)
    return status, body


# ─────────────────────────────────────────────────────────────────────────────
# 가짜 claude: 프롬프트(argv $2)의 `runs/<job_id>`에 산출물을 쓴다
# ─────────────────────────────────────────────────────────────────────────────

_HEAD = "#!/bin/bash\nJOB=$(printf '%s' \"$2\" | grep -o 'runs/[A-Za-z0-9_-]*' | head -1)\n"


def _draft(extra: str = "") -> str:
    return (
        'mkdir -p "$JOB/draft"\n'
        'printf "<html>DRAFT</html>" > "$JOB/draft/report.html"\n'
        "printf '{\"delivery_allowed\": false, \"delivery_status\": \"draft_pending_audit\"}' "
        '> "$JOB/draft/render-validation.json"\n'
        'printf "{}" > "$JOB/draft/report-input.json"\n'
        'printf "[]" > "$JOB/draft/source-ledger.json"\n' + extra
    )


def _final(allowed: bool) -> str:
    flag = "true" if allowed else "false"
    return (
        'mkdir -p "$JOB/final"\n'
        'printf "<html>FINAL</html>" > "$JOB/final/report.html"\n'
        f"printf '{{\"delivery_allowed\": {flag}}}' > \"$JOB/final/render-validation.json\"\n"
        'printf "{}" > "$JOB/final/report-input.json"\n'
        'printf "[]" > "$JOB/final/source-ledger.json"\n'
        'printf "{}" > "$JOB/final/delivery-audit.json"\n'
    )


_ASSUME = 'printf "가정 없음" > "$JOB/assumptions.md"\n'
_EXIT0 = "exit 0\n"
_WAIT = 'touch "$JOB/.ready"\nsleep 30\n'


def _runner(env, body: str, *, timeout: float = 30.0):
    script = env.tmp / "fake-claude"
    script.write_text(_HEAD + body)
    script.chmod(0o755)
    environ = {"PATH": "/usr/bin:/bin", "HOME": str(env.tmp / "home"),
               "AI_REPORT_GOOSE_HARNESS_DIR": str(env.harness)}
    return functools.partial(
        env.real.gr.run_goose, environ=environ, claude_bin=str(script),
        grace_sec=0.5, timeout_sec=timeout,
    )


async def _finish(job):
    if job.task is not None:
        await asyncio.gather(job.task, return_exceptions=True)


async def _wait_file(path: Path, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"파일이 생기지 않음: {path}")


def _archive_runs(stock_dir: Path) -> list[Path]:
    goose = stock_dir / "goose"
    return sorted(p for p in goose.iterdir()) if goose.exists() else []


async def _history(env) -> list[dict]:
    async with _client(env.app) as client:
        resp = await client.get("/api/ai-report/299030/history")
    assert resp.status_code == 200
    return resp.json()["items"]


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-014 — final 판정 7종 (실제 run_goose + 가짜 claude)
# ─────────────────────────────────────────────────────────────────────────────

# (이름, 가짜 claude 본문, 시간 상한, 취소 여부, 상태, 오류 종류, 원본 폴더, 전달 상태, 중단)
_AC014 = [
    ("a", _final(True) + _draft() + _EXIT0, 30.0, False, "done", None, "final", "final", False),
    ("b", _draft() + _EXIT0, 30.0, False, "done", None, "draft", "draft", False),
    ("c", _final(False) + _draft() + _EXIT0, 30.0, False, "done", None, "draft", "draft", False),
    ("d", _EXIT0, 30.0, False, "error", "empty_output", None, None, False),
    ("e", _draft() + _WAIT, 1.0, False, "error", "timeout", "draft", "draft", True),
    ("f", _draft() + _WAIT, 30.0, True, "cancelled", None, "draft", "draft", True),
    ("g", _final(True) + _draft() + _WAIT, 1.0, False, "error", "timeout", "final", "final", True),
    # SPEC-AI-REPORT-006: 영수증이 없으면 delivery_allowed: true인 final/도 draft로 보관된다(조건 1)
    ("a-no-receipt", _final(True) + _draft() + _EXIT0, 30.0, False, "done", None, "draft", "draft", False),
    ("g-no-receipt", _final(True) + _draft() + _WAIT, 1.0, False, "error", "timeout", "draft", "draft", True),
]
# 보관 복사 경로(final/ 원본)를 계속 시험하려고 (a)(g)는 영수증 판정만 인정으로 고정한다
_ADMISSIBLE_FIXED = {"a", "g"}


@pytest.mark.parametrize(
    "name,body,timeout,cancel,status,kind,source,delivery,interrupted",
    _AC014, ids=[row[0] for row in _AC014],
)
async def test_ac014_final_judgement_fixtures(
    env, monkeypatch, name, body, timeout, cancel, status, kind, source, delivery, interrupted
):
    if name in _ADMISSIBLE_FIXED:
        monkeypatch.setattr(env.real.gr.goose_review, "evaluate_admissibility", lambda _jd: (True, []))
    svc = env.service(_runner(env, body, timeout=timeout))
    job = (await svc.start("299030", "하나기술")).job
    job_dir = env.runs / job.job_id
    if cancel:
        await _wait_file(job_dir / ".ready")
        await svc.cancel(job.job_id)
    await _finish(job)

    assert (job.status, job.error_kind) == (status, kind)
    runs = _archive_runs(env.stock_dir)
    last = job.events[-1]
    assert last.type == status
    if source is None:  # (d) 선택되는 리포트 없음 → 보관 폴더를 만들지 않는다
        assert runs == []
        assert "run" not in last.data
        assert [i for i in await _history(env) if i["kind"] == "goose"] == []
        return

    assert [p.name for p in runs] == ["2026-10-19"]
    run_dir = runs[0]
    assert (run_dir / "report.html").read_bytes() == (job_dir / source / "report.html").read_bytes()
    meta = json.loads((run_dir / "job.json").read_text(encoding="utf-8"))
    assert meta["job_id"] == job.job_id
    assert (meta["status"], meta["error_kind"]) == (status, kind)
    assert (meta["delivery_status"], meta["interrupted"], meta["run"]) == (delivery, interrupted, "2026-10-19")
    # 종료 이벤트 데이터(design §4.4)
    assert last.data["run"] == "2026-10-19"
    assert last.data["delivery_status"] == delivery
    assert last.data["report_url"] == "/api/ai-report/299030/goose/2026-10-19/report.html"
    assert last.data.get("interrupted", False) is interrupted
    # 기록 API
    goose_items = [i for i in await _history(env) if i["kind"] == "goose"]
    assert len(goose_items) == 1
    item = goose_items[0]
    assert (item["run"], item["delivery_status"], item["interrupted"]) == ("2026-10-19", delivery, interrupted)


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-013 — 허용 파일만 복사, 모델이 출력한 경로 무시
# ─────────────────────────────────────────────────────────────────────────────


async def test_ac013_copies_only_allowlisted_files_and_ignores_model_paths(env):
    decoy = env.harness / "x.html"  # runs/<id>/../../x.html 이 가리키는 위치
    decoy.write_text("DECOY-CONTENT")
    secret = env.tmp / "secret-outside.txt"
    secret.write_text("TOP-SECRET")
    body = _draft(
        'printf "rm -rf /" > "$JOB/draft/evil.sh"\n'
        f'ln -s "{secret}" "$JOB/draft/delivery-audit.json"\n'
    ) + _ASSUME + (
        'mkdir -p "$JOB/notes"\nprintf "SECRET" > "$JOB/notes/secret.txt"\n'
        'printf "TOP" > "$JOB/input.json"\n'
        "echo '{\"type\":\"result\",\"subtype\":\"success\",\"result\":\"리포트: ../../x.html\"}'\n"
    ) + _EXIT0
    svc = env.service(_runner(env, body))
    job = (await svc.start("299030", "하나기술")).job
    await _finish(job)

    assert job.status == "done"
    (run_dir,) = _archive_runs(env.stock_dir)
    names = {p.name for p in run_dir.iterdir()}
    assert names == _ALLOWED | {"assumptions.md", "job.json"}
    assert not (run_dir / "evil.sh").exists() and not (run_dir / "secret.txt").exists()
    assert (run_dir / "assumptions.md").read_text(encoding="utf-8") == "가정 없음"
    for path in run_dir.iterdir():
        text = path.read_bytes()
        assert b"DECOY-CONTENT" not in text and b"TOP-SECRET" not in text
    assert all(not p.is_symlink() for p in run_dir.iterdir())


async def test_assumptions_absent_is_not_an_error(env):
    svc = env.service(_runner(env, _draft() + _EXIT0))
    job = (await svc.start("299030", "하나기술")).job
    await _finish(job)
    (run_dir,) = _archive_runs(env.stock_dir)
    assert job.status == "done"
    assert {p.name for p in run_dir.iterdir()} == _ALLOWED | {"job.json"}


async def test_same_day_second_run_gets_suffix(env):
    svc = env.service(_runner(env, _draft() + _EXIT0))
    for _ in range(3):
        job = (await svc.start("299030", "하나기술")).job
        await _finish(job)
        assert job.status == "done"
    assert [p.name for p in _archive_runs(env.stock_dir)] == ["2026-10-19", "2026-10-19_2", "2026-10-19_3"]
    assert job.events[-1].data["run"] == "2026-10-19_3"


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-010 보관 절반 — 구독을 끊어도 작업이 끝나고 보관된다
# ─────────────────────────────────────────────────────────────────────────────


async def test_ac010_report_archived_after_subscriber_disconnect(env):
    gr = env.real.gr
    release = asyncio.Event()

    async def runner(*, job_id, stock_name, code, on_event):
        await on_event(gr.ProgressEvent("goose_start"))
        await release.wait()
        draft = env.runs / job_id / "draft"
        draft.mkdir(parents=True)
        (draft / "report.html").write_text("<html>LATE</html>")
        return gr.RunResult(status="done", error_kind=None, exit_code=0,
                            delivery_status="draft", report_dir=draft)

    svc = env.service(runner)
    job = (await svc.start("299030", "하나기술")).job
    agen = svc.subscribe(job.job_id)
    first = await asyncio.wait_for(agen.__anext__(), 5)
    assert first.data["stage"] == "goose_start"
    await agen.aclose()  # 구독자 연결 끊김
    release.set()
    await _finish(job)

    assert job.status == "done"
    (run_dir,) = _archive_runs(env.stock_dir)
    assert (run_dir / "report.html").read_text() == "<html>LATE</html>"


async def test_production_service_has_archive_hook_with_default_paths(env, monkeypatch):
    """운영용 모듈 인스턴스는 보관 훅을 갖고, 기본 경로(하네스 runs·ai_report_service.report_dir)를 쓴다."""
    monkeypatch.setenv("AI_REPORT_GOOSE_HARNESS_DIR", str(env.harness))
    hook = env.real.gjs.get_service()._on_finish
    assert hook is not None
    job = env.real.gjs.Job(job_id="jobprod1", code="299030", stock_name="하나기술")
    draft = env.runs / "jobprod1" / "draft"
    draft.mkdir(parents=True)
    (draft / "report.html").write_text("<html>PROD</html>")
    job.ending = ("done", None)

    data = await hook(job, None)

    run_dir = env.stock_dir / "goose" / data["run"]
    assert (run_dir / "report.html").read_text() == "<html>PROD</html>"
    assert data["report_url"] == f"/api/ai-report/299030/goose/{data['run']}/report.html"
    assert "interrupted" not in data


async def test_runner_exception_still_archives_selectable_draft_as_interrupted(env):
    gr = env.real.gr

    async def runner(*, job_id, stock_name, code, on_event):
        draft = env.runs / job_id / "draft"
        draft.mkdir(parents=True)
        (draft / "report.html").write_text("<html>D</html>")
        raise RuntimeError("boom")

    svc = env.service(runner)
    job = (await svc.start("299030", "하나기술")).job
    await _finish(job)
    assert (job.status, job.error_kind) == ("error", "exit_error")
    (run_dir,) = _archive_runs(env.stock_dir)
    meta = json.loads((run_dir / "job.json").read_text(encoding="utf-8"))
    assert (meta["delivery_status"], meta["interrupted"]) == ("draft", True)
    assert gr.RunResult  # 모듈 참조 유지


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-015 — HTML 서빙 + CSP
# ─────────────────────────────────────────────────────────────────────────────


def _write_run(stock_dir: Path, run: str, delivery: str, *, interrupted: bool | None = None,
               html: str = "<html>OK</html>") -> Path:
    run_dir = stock_dir / "goose" / run
    run_dir.mkdir(parents=True)
    (run_dir / "report.html").write_text(html)
    meta = {"job_id": "j-" + run, "run": run, "delivery_status": delivery, "status": "done",
            "error_kind": None, "finished_at": f"{run[:10]}T10:00:00+09:00"}
    if interrupted is not None:
        meta["interrupted"] = interrupted
    (run_dir / "job.json").write_text(json.dumps(meta), encoding="utf-8")
    return run_dir


async def test_ac015_serves_report_with_sandbox_csp(env):
    _write_run(env.stock_dir, "2026-10-19", "final", html="<html>GOOSE</html>")
    async with _client(env.app) as client:
        resp = await client.get("/api/ai-report/299030/goose/2026-10-19/report.html")
    assert resp.status_code == 200
    assert resp.text == "<html>GOOSE</html>"
    assert resp.headers["content-type"].startswith("text/html")
    csp = resp.headers["content-security-policy"]
    assert "sandbox" in csp.split(";")[0].split()
    assert "allow-scripts" not in csp and "allow-same-origin" not in csp
    assert csp == _CSP
    assert resp.headers["x-content-type-options"] == "nosniff"


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-016 — 경로 검증 (모두 404, 루트 밖 내용 노출 없음)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def traversal(env):
    _write_run(env.stock_dir, "2026-10-19", "draft")
    outside = env.tmp / "outside"
    outside.mkdir()
    (outside / "report.html").write_text("OUTSIDE-SECRET")
    (env.reports / "report.html").write_text("ROOT-SECRET")
    (env.tmp / "x").mkdir()
    (env.tmp / "x" / "report.html").write_text("X-SECRET")
    # 심볼릭 링크로 루트 밖을 가리키는 실행 두 가지(파일 링크, 폴더 링크)
    link_file_run = env.stock_dir / "goose" / "2026-10-21"
    link_file_run.mkdir(parents=True)
    (link_file_run / "report.html").symlink_to(outside / "report.html")
    (env.stock_dir / "goose" / "2026-10-22").symlink_to(outside, target_is_directory=True)
    return env


_SECRETS = (b"OUTSIDE-SECRET", b"ROOT-SECRET", b"X-SECRET")


@pytest.mark.parametrize("raw_run", [
    "..%2F..", "2026-10-19%2F..%2F..%2Fx", "..%2Freports", "2026-10-19_x", "latest",
    "%2e%2e", "..", "%2Fetc%2Fpasswd", "2026-10-21", "2026-10-22", "2026-10-23",
])
async def test_ac016_invalid_or_escaping_run_is_404(traversal, raw_run):
    status, body = await _raw_get(traversal.app, f"/api/ai-report/299030/goose/{raw_run}/report.html")
    assert status == 404
    assert not any(secret in body for secret in _SECRETS)


@pytest.mark.parametrize("raw_path", [
    "/api/ai-report/299030/goose/2026-10-19/../../x/report.html",
    "/api/ai-report/299030/goose/../reports/report.html",
    "/api/ai-report/299030/goose/../../report.html",
])
async def test_ac016_literal_dot_segments_are_404(traversal, raw_path):
    status, body = await _raw_get(traversal.app, raw_path)
    assert status == 404
    assert not any(secret in body for secret in _SECRETS)


@pytest.mark.parametrize("code", ["29903", "abcdef", "2990300", "..", "999999"])
async def test_ac016_invalid_or_unknown_code_is_404(traversal, code):
    status, body = await _raw_get(traversal.app, f"/api/ai-report/{code}/goose/2026-10-19/report.html")
    assert status == 404
    assert not any(secret in body for secret in _SECRETS)


@pytest.mark.parametrize("run", [
    "..", "../..", "2026-10-19/../../x", "../reports", "2026-10-19_x", "latest", "/etc/passwd",
    "2026-10-19/", "2026-10-19\x00", "%2e%2e", "2026-10-21", "2026-10-22", "",
])
def test_resolver_rejects_bad_runs_without_reading(traversal, run):
    gs = traversal.real.gs
    assert gs.resolve_report_html(traversal.reports, traversal.stock_dir, run) is None


def test_resolver_accepts_valid_run(traversal):
    gs = traversal.real.gs
    path = gs.resolve_report_html(traversal.reports, traversal.stock_dir, "2026-10-19")
    assert path is not None and path.read_text() == "<html>OK</html>"


def test_resolver_rejects_stock_dir_outside_root(traversal, tmp_path):
    gs = traversal.real.gs
    other = tmp_path / "elsewhere"
    _write_run(other, "2026-10-19", "draft")
    assert gs.resolve_report_html(traversal.reports, other, "2026-10-19") is None


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR4-017 — 기록 API (markdown + goose)
# ─────────────────────────────────────────────────────────────────────────────


async def test_ac017_history_lists_markdown_and_goose_runs(env):
    env.stock_dir.mkdir(parents=True)
    (env.stock_dir / "2026-10-01.md").write_text("# a", encoding="utf-8")
    (env.stock_dir / "2026-10-02_2.md").write_text("# b", encoding="utf-8")
    _write_run(env.stock_dir, "2026-10-19", "final")
    _write_run(env.stock_dir, "2026-10-19_2", "draft")
    _write_run(env.stock_dir, "2026-10-20", "draft", interrupted=True)

    items = await _history(env)

    assert len(items) == 5
    by_key = {(i["kind"], i.get("run") or i["filename"]): i for i in items}
    assert by_key[("markdown", "2026-10-01.md")]["date"] == "2026-10-01"
    assert by_key[("markdown", "2026-10-02_2.md")]["date"] == "2026-10-02"
    goose = [i for i in items if i["kind"] == "goose"]
    assert [(i["run"], i["delivery_status"], i["interrupted"]) for i in goose] == [
        ("2026-10-20", "draft", True), ("2026-10-19_2", "draft", False), ("2026-10-19", "final", False),
    ]
    assert [i["date"] for i in items] == ["2026-10-20", "2026-10-19", "2026-10-19", "2026-10-02", "2026-10-01"]


async def test_history_markdown_only_is_unchanged_with_kind(env):
    env.stock_dir.mkdir(parents=True)
    (env.stock_dir / "2026-10-01.md").write_text("# a", encoding="utf-8")
    (env.stock_dir / "2026-10-01_2.md").write_text("# b", encoding="utf-8")
    items = await _history(env)
    assert [i["filename"] for i in items] == ["2026-10-01_2.md", "2026-10-01.md"]
    assert all(i["kind"] == "markdown" and i["run"] is None and i["interrupted"] is False for i in items)
    assert all(i["delivery_status"] is None for i in items)


async def test_history_skips_malformed_goose_runs(env):
    _write_run(env.stock_dir, "2026-10-19", "final")
    bad_json = env.stock_dir / "goose" / "2026-10-18"
    bad_json.mkdir()
    (bad_json / "job.json").write_text("{not json")
    bad_name = env.stock_dir / "goose" / "latest"
    bad_name.mkdir()
    (bad_name / "job.json").write_text(json.dumps({"delivery_status": "final"}))
    bad_status = env.stock_dir / "goose" / "2026-10-17"
    bad_status.mkdir()
    (bad_status / "job.json").write_text(json.dumps({"delivery_status": "evil"}))
    no_meta = env.stock_dir / "goose" / "2026-10-16"
    no_meta.mkdir()
    (env.stock_dir / "goose" / "2026-10-15").write_text("not a dir")

    items = await _history(env)
    assert [(i["kind"], i["run"]) for i in items] == [("goose", "2026-10-19")]


async def test_history_unknown_stock_and_empty(env):
    assert await _history(env) == []
    async with _client(env.app) as client:
        assert (await client.get("/api/ai-report/999999/history")).status_code == 404
