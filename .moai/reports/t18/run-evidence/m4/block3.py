

# ── AC-AIR6-022 — 최종본 인정 경로의 격리 통합 시험 ─────────────────────────────
# 벤더링된 실제 audit_report.py·render_report.py를 가짜 claude 스크립트가 실행한다. 입력은 라이브 초안
# (020150, 2026-10-21)의 입력에서 네이버 채널의 `blocked` 항목을 `no_results`로 바꾼 합성 입력이다(research P24·P25).
# 날짜는 `historical` 모드(+`user_requested_as_of`)로 고정해 시험 시점의 날짜와 무관하게 만든다(research G10 대체).

import subprocess
import sys as _sys

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
    return subprocess.run([_sys.executable, "-B", "-I", *args], capture_output=True, text=True, timeout=120)


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
    script.write_text(_FAKE_CLAUDE_REVIEW.format(python=_sys.executable, audit=str(_AUDIT), render=str(_RENDER)))
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
