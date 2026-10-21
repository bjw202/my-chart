

# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-006 M4 — 후처리(화면 캡처 → 감수 세션 → 영수증)와 전달 상태
# AC-AIR6-001·002·003·004·005·014(서비스 몫)·015 S9·020·022
# 가짜 캡처기·가짜 감수기를 주입한다. 실제 브라우저·실제 claude(AC-022의 스크립트 제외)는 쓰지 않는다.
# ─────────────────────────────────────────────────────────────────────────────

import hashlib
import json
from datetime import datetime, timedelta, timezone

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
    assert receipt["reasons"] == ["review_not_completed", "tile_not_read"]
    assert job.events[-1].data["delivery_status"] == "draft"


# ── AC-AIR6-015 S9 (영수증 쓰기 실패의 이벤트 값) ──────────────────────────────


async def test_air6_015_s9a_replace_failure_removes_session_receipt(mods, tmp_path, monkeypatch, caplog):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=True)
    real_run = ctx.rev.__call__

    async def writes_receipt(**kw):
        result = await real_run(**kw)
        (tmp_path / "runs" / kw["job_id"] / "review" / "receipt.json").write_text('{"visual_admissible": true}')
        return result

    ctx.svc._reviewer = writes_receipt

    def fail_replace(src, dst):
        raise OSError("replace boom")

    monkeypatch.setattr(mods.gjs.goose_review, "_replace", fail_replace)
    with caplog.at_level("ERROR"):
        job = await _run_post(ctx)
    assert job.status == "done"
    assert _receipt(tmp_path, job.job_id) is None  # 세션이 쓴 영수증이 남아 있지 않다
    assert sum("receipt_write_failed" in r.getMessage() for r in caplog.records) == 1
    assert mods.gr.select_report(tmp_path / "runs" / job.job_id)[0] == "draft"
    assert job.events[-1].data["delivery_status"] == "draft"


async def test_air6_015_s9b_removal_and_write_failure_event_is_draft(mods, tmp_path, monkeypatch):
    ctx = _post_service(mods, tmp_path, monkeypatch, hook=False)
    real_run = ctx.rev.__call__

    async def writes_receipt(**kw):
        result = await real_run(**kw)
        (tmp_path / "runs" / kw["job_id"] / "review" / "receipt.json").write_text('{"visual_admissible": true}')
        return result

    ctx.svc._reviewer = writes_receipt

    def fail(*a, **k):
        raise OSError("boom")

    monkeypatch.setattr(mods.gjs.goose_review, "_remove", fail)
    monkeypatch.setattr(mods.gjs.goose_review, "_replace", fail)
    job = await _run_post(ctx)
    assert job.status == "done"
    assert job.events[-1].data["delivery_status"] == "draft"  # 낡은 영수증이 남아도 이벤트는 final이 아니다


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
