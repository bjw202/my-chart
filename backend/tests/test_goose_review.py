"""SPEC-AI-REPORT-006 M3 — 감수 세션·영수증·최종본 인정 판정 시험.

대상: backend/services/goose_review.py, goose_runner.py의 `run_review`·`ReviewTracker`·`build_review_prompt`
(AC-AIR6-011·012·014·015·021, AC-AIR6-016의 판정 함수 몫, AC-AIR6-002의 감수 프로세스 그룹 몫)

범위 밖(M4): `select_report`가 이 판정을 부르는 부분, 작업 서비스 후처리 순서, 완료 이벤트의 전달 상태.
그래서 여기서는 ``evaluate_admissibility``의 결과(미인정 사유 목록)를 단언한다.

격리 원칙:
- 실제 `claude`·브라우저·네트워크를 쓰지 않는다. `claude`는 tmp_path 안의 셸 스크립트로, 합성
  stream-json은 이 파일의 빌더로 만든다. 실제 홈·~/.goose-harness도 건드리지 않는다(하네스는 tmp_path).
- 이 파일 이름은 `test_goose_` 접두어라 공용 네트워크 가드(conftest)가 자동 적용된다.
- 기댓값(사유 목록 등)은 acceptance.md의 표에서 가져온 리터럴이며 시험 대상 코드로 계산하지 않는다.
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import json
import logging
import os
import re
import signal
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.services import goose_review as gv

_KST_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+09:00$")
_CODE = "020150"
_STOCK_NAME = "홍길동전자"
_JOB = "j1"
_PNG = b"\x89PNG\r\n\x1a\n"
_TILES = ["desktop-01.png", "desktop-02.png", "mobile-01.png"]
_FUTURE = "2999-01-01T00:00:00+09:00"
_EVIDENCE = "[렌더 차이] 외부 네트워크와 웹 글꼴을 막고 그려 실제 화면과 조금 다르다. 타일 desktop-01.png 등을 열었다."


@pytest.fixture(scope="module")
def gr():
    """실제 goose_runner를 불러온다(test_goose_runner와 같은 이유로 `backend*` 스텁을 잠시 비운다)."""
    saved = {n: m for n, m in sys.modules.items() if n in ("my_chart", "backend") or n.startswith(("my_chart.", "backend."))}
    for name in saved:
        del sys.modules[name]
    try:
        yield importlib.import_module("backend.services.goose_runner")
    finally:
        for name in [n for n in sys.modules if n in ("my_chart", "backend") or n.startswith(("my_chart.", "backend."))]:
            del sys.modules[name]
        sys.modules.update(saved)


# ─────────────────────────────────────────────────────────────────────────────
# 합성 stream-json 빌더 (research P10의 실제 줄 모양을 따른다)
# ─────────────────────────────────────────────────────────────────────────────


def _tu(tool_id: str, name: str, inp: dict, parent: str | None = None) -> str:
    return json.dumps({
        "type": "assistant", "parent_tool_use_id": parent,
        "message": {"content": [{"type": "tool_use", "id": tool_id, "name": name, "input": inp}]},
    })


def _tr(tool_id: str, is_error: object = "ABSENT", parent: str | None = None) -> str:
    block: dict = {"type": "tool_result", "tool_use_id": tool_id, "content": [{"type": "image"}]}
    if is_error != "ABSENT":
        block["is_error"] = is_error
    return json.dumps({"type": "user", "parent_tool_use_id": parent, "message": {"content": [block]}})


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# 작업 폴더 픽스처 빌더: 기준 픽스처 P = 모든 조건을 만족하는 상태
# ─────────────────────────────────────────────────────────────────────────────


def _build_job_files(harness: Path, index_edit=None) -> Path:
    job_dir = harness / "runs" / _JOB
    (job_dir / "draft").mkdir(parents=True)
    (job_dir / "screens").mkdir()
    html = b"<html><body>report</body></html>"
    (job_dir / "draft" / "report.html").write_bytes(html)
    (job_dir / "draft" / "report-input.json").write_text('{"k": 1}')
    tiles = {}
    for name in _TILES:
        data = _PNG + name.encode()
        (job_dir / "screens" / name).write_bytes(data)
        tiles[name] = {"file": name, "y": 0, "width": 10, "height": 10, "bytes": len(data), "sha256": _sha(data)}

    def vp(name: str, files: list[str]) -> dict:
        return {
            "name": name, "width": 10, "status": "ok", "error": None,
            "metrics": {"scroll_width": 10, "client_width": 10, "scroll_height": 20, "horizontal_overflow": False},
            "tiles": [tiles[f] for f in files],
        }

    index = {
        "schema_version": 1, "source": "draft/report.html", "preview_sha256": _sha(html),
        "started_at": "2026-10-21T10:00:00+09:00", "finished_at": "2026-10-21T10:00:05+09:00",
        "outcome": "complete", "browser": {"name": "X", "version": "1", "path_kind": "env"},
        "viewports": [vp("desktop", _TILES[:2]), vp("mobile", _TILES[2:])],
    }
    if index_edit:
        index_edit(index)
    (job_dir / "screens" / "index.json").write_text(json.dumps(index))
    return job_dir


def _abs(harness: Path, rel: str) -> str:
    return str(harness / rel)


def _honest_record(ctx: dict) -> dict:
    copy = ctx["copy_into_review_record"]
    checks = {k: {"status": "pass", "evidence": "확인함"} for k in
              ("source_accuracy", "calculations", "coverage", "opinion")}
    checks["visual"] = {"status": "pass", "evidence": _EVIDENCE}
    return {**copy, "checks": checks, "issues": []}


def _make_job(
    tmp_path: Path, *, index_edit=None, pre=None, audit_edit=None, skip_read=(), extra_reads=(), writes=(),
    session=None, write_audit=True, make_final=True, exit_code=0, timed_out=False, outcome=None,
):
    """P를 만든다: 파일 → (pre) → prepare_review → 가짜 감수기 → finish_review. 영수증은 서버 방식으로 쓴다."""
    harness = tmp_path / "harness"
    job_dir = _build_job_files(harness, index_edit)
    if pre:
        pre(job_dir)
    start = gv.prepare_review(job_dir, code=_CODE)
    seen = SimpleNamespace(audit_at_entry=None, final_at_entry=None, ctx_at_entry=None, session_ran=False,
                           review_at_entry=None)
    stream_writes = list(writes)
    if start.launch:
        seen.session_ran = True
        ctx_path = job_dir / "review" / "context.json"
        seen.ctx_at_entry = json.loads(ctx_path.read_text()) if ctx_path.exists() else None
        seen.audit_at_entry = (job_dir / "audit-review.json").exists()
        seen.final_at_entry = (job_dir / "final").exists()
        seen.review_at_entry = sorted(p.name for p in (job_dir / "review").iterdir())
        if session:
            stream_writes += session(job_dir, seen.ctx_at_entry) or []
        if write_audit and seen.ctx_at_entry:
            record = _honest_record(seen.ctx_at_entry)
            if audit_edit:
                audit_edit(record)
            (job_dir / "audit-review.json").write_text(json.dumps(record))
        if make_final:  # 감수 세션이 --final을 실행한 것으로 가정(세션 전 정리는 final/을 지운다)
            _plant_final(job_dir)
        reads = [_abs(harness, t) for t in (seen.ctx_at_entry["screens"]["tiles"] if seen.ctx_at_entry else [])
                 if Path(t).name not in skip_read] + list(extra_reads)
    else:
        reads = []
    result = gv.finish_review(
        job_dir, start, harness_dir=harness, exit_code=exit_code, timed_out=timed_out,
        read_paths=reads, write_paths=stream_writes, outcome=outcome,
    )
    return SimpleNamespace(job_dir=job_dir, harness=harness, start=start, result=result, seen=seen,
                           receipt=result.receipt)


def _receipt_path(job_dir: Path) -> Path:
    return job_dir / "review" / "receipt.json"


def _edit_receipt(job_dir: Path, fn) -> None:
    data = json.loads(_receipt_path(job_dir).read_text())
    fn(data)
    _receipt_path(job_dir).write_text(json.dumps(data))


def _edit_index(job_dir: Path, fn) -> None:
    path = job_dir / "screens" / "index.json"
    data = json.loads(path.read_text())
    fn(data)
    path.write_text(json.dumps(data))


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-016 — 최종본 인정 판정 (조건 1~17, 표 구동)
# ─────────────────────────────────────────────────────────────────────────────

_MOBILE = lambda idx: next(v for v in idx["viewports"] if v["name"] == "mobile")  # noqa: E731


def _set_mobile_overflow(idx):
    _MOBILE(idx)["metrics"]["horizontal_overflow"] = True


def _forge_overflow_false(idx):
    _MOBILE(idx)["metrics"]["horizontal_overflow"] = False


def _w(path: Path, data: bytes) -> None:
    path.write_bytes(data)


# 변경이 세션 시작 전(pre)에 일어난 격리 케이스: (id, kwargs, 기대 reasons)
_PRE_CASES = [
    ("d", {"index_edit": lambda i: i.update(outcome="partial")}, ["screens_not_complete"]),
    ("t7", {"pre": lambda jd: (jd / "screens" / "mobile-01.png").unlink()}, ["tile_missing"]),
    ("g2", {"pre": lambda jd: _w(jd / "screens" / "desktop-02.png", b"tampered")}, ["tile_hash_mismatch"]),
    ("e", {"index_edit": lambda i: i.update(preview_sha256="0" * 64)}, ["preview_hash_mismatch"]),
    ("f", {"index_edit": _set_mobile_overflow}, ["mobile_overflow"]),
    ("c", {"skip_read": ("mobile-01.png",)}, ["tile_not_read"]),
    ("h", {"audit_edit": lambda r: r.update(mode="independent_agent")}, ["mode_not_separate_review_pass"]),
    ("i", {"audit_edit": lambda r: r["checks"]["visual"].update(status="revise")}, ["visual_not_pass"]),
    ("j", {"audit_edit": lambda r: r.update(reviewed_at="2000-01-01T00:00:00+09:00")}, ["reviewed_before_capture"]),
    ("p", {"audit_edit": lambda r: r["checks"]["visual"].update(evidence="렌더 차이 없음")}, ["font_note_missing"]),
    ("m", {"audit_edit": lambda r: r.update(preview_sha256="0" * 64)}, ["preview_hash_mismatch"]),
]


def test_air6_016_baseline_p_is_admissible(tmp_path):
    job = _make_job(tmp_path)
    assert gv.evaluate_admissibility(job.job_dir) == (True, [])
    assert job.receipt["visual_admissible"] is True and job.receipt["reasons"] == []
    assert job.receipt["outcome"] == "reviewed"


@pytest.mark.parametrize(("case", "kwargs", "expected"), _PRE_CASES, ids=[c[0] for c in _PRE_CASES])
def test_air6_016_isolated_pre_session_cases(tmp_path, case, kwargs, expected):
    job = _make_job(tmp_path, **kwargs)
    admissible, reasons = gv.evaluate_admissibility(job.job_dir)
    assert (admissible, reasons) == (False, expected)
    # 영수증 작성기(코어)와 디스크 래퍼는 같은 시점에 같은 사유를 낸다
    assert job.receipt["reasons"] == expected and job.receipt["visual_admissible"] is False


def _drop_key(key):
    return lambda r: r.pop(key)


# 영수증 작성 뒤 영수증 또는 디스크를 한 군데만 바꾸는 격리 케이스
_POST_CASES = [
    ("b", lambda jd: _receipt_path(jd).unlink(), ["no_receipt"]),
    ("b2-i", lambda jd: _edit_receipt(jd, lambda r: r.update(schema_version=2)), ["receipt_invalid"]),
    ("b2-ii", lambda jd: _edit_receipt(jd, _drop_key("reasons")), ["receipt_invalid"]),
    ("b3", lambda jd: _receipt_path(jd).write_text("{not json"), ["receipt_invalid"]),
    ("r", lambda jd: _edit_receipt(jd, lambda r: r.update(outcome="timeout")), ["review_not_completed"]),
    ("w", lambda jd: _edit_receipt(jd, lambda r: r.update(judged_writes=["runs/j1/draft/report.html"])),
     ["judged_input_write_attempt"]),
    ("x", lambda jd: (jd / "screens" / "mobile-99.png").write_bytes(b"x"), ["screens_changed"]),
    ("k", lambda jd: (jd / "draft" / "report-input.json").write_text('{"k": 2}'), ["draft_changed"]),
    ("k2", lambda jd: _edit_receipt(jd, lambda r: r["hashes"].update(preview_end="0" * 64)), ["draft_changed"]),
    ("c2", lambda jd: _edit_receipt(jd, lambda r: r["screens"].update(tiles_expected=_TILES[:2])),
     ["tile_not_read"]),
    ("o", lambda jd: (jd / "audit-review.json").unlink(), ["no_audit_review"]),
    ("o2", lambda jd: (jd / "audit-review.json").write_text("garbage"), ["no_audit_review"]),
    # 자연 흐름 케이스: 여러 조건이 함께 걸린다(저장된 visual_admissible: true는 그대로)
    ("g", lambda jd: _w(jd / "screens" / "desktop-02.png", b"overwritten"),
     ["screens_changed", "tile_hash_mismatch"]),
    ("g3", lambda jd: (jd / "screens" / "mobile-01.png").unlink(), ["screens_changed", "tile_missing"]),
    ("kr", lambda jd: (jd / "draft" / "report.html").write_text("<html>changed</html>"),
     ["draft_changed", "preview_hash_mismatch"]),
]


def test_air6_016_forged_index_after_receipt(tmp_path):
    """(s) 세션 시작 전 색인은 overflow=true였고(스냅샷도 그 상태), 영수증 뒤 false로 위조."""
    job = _make_job(tmp_path, index_edit=_set_mobile_overflow)
    assert job.receipt["reasons"] == ["mobile_overflow"]
    _edit_index(job.job_dir, _forge_overflow_false)
    assert gv.evaluate_admissibility(job.job_dir) == (False, ["screens_changed"])


@pytest.mark.parametrize(
    ("case", "mutate", "expected"),
    _POST_CASES,
    ids=[c[0] for c in _POST_CASES],
)
def test_air6_016_isolated_post_receipt_cases(tmp_path, case, mutate, expected):
    job = _make_job(tmp_path)
    assert gv.evaluate_admissibility(job.job_dir) == (True, [])  # 변경 전에는 인정
    mutate(job.job_dir)
    assert gv.evaluate_admissibility(job.job_dir) == (False, expected)


def test_air6_016_condition0_is_not_this_functions_concern(tmp_path):
    """(n) `delivery_allowed: false`는 select_report의 조건 0 — 이 함수를 직접 부르면 인정이다."""
    job = _make_job(tmp_path)
    (job.job_dir / "final" / "render-validation.json").write_text('{"delivery_allowed": false}')
    assert gv.evaluate_admissibility(job.job_dir) == (True, [])


def test_air6_016_stored_visual_admissible_is_never_an_input(tmp_path):
    """영수증에 `true`가 저장돼 있어도 디스크가 바뀌면 미인정이다((g)(kr)의 핵심)."""
    job = _make_job(tmp_path)
    assert json.loads(_receipt_path(job.job_dir).read_text())["visual_admissible"] is True
    (job.job_dir / "draft" / "report.html").write_text("<html>changed</html>")
    assert gv.evaluate_admissibility(job.job_dir)[0] is False
    # 반대로 저장된 값이 false여도 디스크가 모든 조건을 만족하면 인정
    _edit_receipt(job.job_dir, lambda r: r.update(visual_admissible=False, reasons=["x"]))
    (job.job_dir / "draft" / "report.html").write_text("<html><body>report</body></html>")
    assert gv.evaluate_admissibility(job.job_dir) == (True, [])


def test_air6_016_unreadable_inputs_fail_closed_without_exception(tmp_path):
    """(d2) 깨진 색인은 색인 의존 조건을 보고하지 않고 `screens_not_complete`만 낸다."""
    job = _make_job(tmp_path)
    (job.job_dir / "screens" / "index.json").write_text("{broken")
    # 영수증 스냅샷은 정상 색인 상태였으므로 screens_changed도 함께 난다 — 색인을 읽지 못하는 상황만 본다
    admissible, reasons = gv.evaluate_admissibility(job.job_dir)
    assert admissible is False
    assert reasons == ["screens_not_complete", "screens_changed"]
    for dependent in ("tile_missing", "tile_hash_mismatch", "tile_not_read", "mobile_overflow", "reviewed_before_capture"):
        assert dependent not in reasons


def test_air6_016_d2_consistent_snapshot_reports_only_screens_not_complete(tmp_path):
    """(d2) 스냅샷이 깨진 색인 상태로 일관되면 `[screens_not_complete]`만 보고된다."""
    job = _make_job(tmp_path, pre=lambda jd: (jd / "screens" / "index.json").write_text("{broken"))
    assert gv.evaluate_admissibility(job.job_dir) == (False, ["screens_not_complete"])


@pytest.mark.parametrize("payload", ["[]", '"str"', "5", "null"])
def test_air6_016_non_object_receipt_is_invalid(tmp_path, payload):
    job = _make_job(tmp_path)
    _receipt_path(job.job_dir).write_text(payload)
    assert gv.evaluate_admissibility(job.job_dir) == (False, ["receipt_invalid"])


@pytest.mark.parametrize(
    "edit",
    [
        lambda r: r.update(judged_writes="x"),
        lambda r: r.update(hashes=5),
        lambda r: r["screens"].update(tiles_read=None, tiles_expected=[None, "a"]),
        lambda r: r.update(screens=[]),
    ],
)
def test_air6_016_malformed_receipt_fields_never_raise(tmp_path, edit):
    job = _make_job(tmp_path)
    _edit_receipt(job.job_dir, edit)
    admissible, reasons = gv.evaluate_admissibility(job.job_dir)
    assert admissible is False and reasons


def test_air6_016_writer_calls_core_with_no_receipt_on_disk_and_replaces_once(tmp_path, monkeypatch):
    """영수증 작성기는 디스크에 파일이 없을 때 코어를 부르고, 영수증 교체는 정확히 1번이다(iter3 N12)."""
    core_calls: list[bool] = []
    real_core = gv.evaluate_core
    replaced: list[str] = []
    real_replace = gv._replace

    def spy_core(job_dir, receipt):
        core_calls.append(_receipt_path(job_dir).exists())
        return real_core(job_dir, receipt)

    def spy_replace(src, dst):
        replaced.append(Path(dst).name)
        real_replace(src, dst)

    monkeypatch.setattr(gv, "evaluate_core", spy_core)
    monkeypatch.setattr(gv, "_replace", spy_replace)
    job = _make_job(tmp_path)
    assert core_calls == [False]
    assert replaced.count("receipt.json") == 1
    assert job.receipt["reasons"] == []


def test_air6_016_reason_codes_are_the_specified_vocabulary(tmp_path):
    allowed = {
        "no_receipt", "receipt_invalid", "review_not_completed", "judged_input_write_attempt",
        "screens_not_complete", "screens_changed", "tile_missing", "tile_hash_mismatch", "draft_changed",
        "preview_hash_mismatch", "tile_not_read", "mobile_overflow", "no_audit_review",
        "mode_not_separate_review_pass", "visual_not_pass", "reviewed_before_capture", "font_note_missing",
    }
    seen: set[str] = set()
    for _case, kwargs, expected in _PRE_CASES:
        seen.update(expected)
    for _case, _mutate, expected in _POST_CASES:
        seen.update(expected)
    assert seen <= allowed
    assert seen == allowed  # 17개 조건 모두 어떤 케이스든 사유를 낸다


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-021 — 글꼴 차단 증거 표지 (조건 17)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("evidence", "expected"),
    [
        ("[렌더 차이] 타일을 열었다", []),
        ("타일을 열었다. [렌더 차이]", []),  # 포함만 확인한다(시작 아님도 인정)
        ("타일을 열었다", ["font_note_missing"]),
        ("[렌더링 차이] 타일", ["font_note_missing"]),
        ("[render diff] tiles", ["font_note_missing"]),
    ],
)
def test_air6_021_font_mark_is_contained_check(tmp_path, evidence, expected):
    job = _make_job(tmp_path, audit_edit=lambda r: r["checks"]["visual"].update(evidence=evidence))
    assert gv.evaluate_admissibility(job.job_dir) == (not expected, expected)


def test_air6_021_render_note_is_fixed_sentence(tmp_path):
    job = _make_job(tmp_path)
    note = job.seen.ctx_at_entry["screens"]["render_note"]
    assert note
    assert all(word in note for word in ("외부 네트워크", "웹 글꼴", "조금 다르"))


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-012 — 감수 컨텍스트
# ─────────────────────────────────────────────────────────────────────────────

_CONTEXT_KEYS = {"schema_version", "job_id", "code", "now", "input", "preview", "screens", "audit_review_path",
                 "audit_output_path", "final_dir", "copy_into_review_record"}


def _path_values(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("index_path", "path", "audit_review_path", "audit_output_path", "final_dir"):
                yield value
            else:
                yield from _path_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from (_path_values(value) if not isinstance(value, str) else [value])


def test_air6_012_context_exists_at_session_entry_with_exact_keys_and_hashes(tmp_path):
    job = _make_job(tmp_path)
    ctx = job.seen.ctx_at_entry
    assert ctx is not None  # 가짜 감수기 진입 시점에 이미 있다
    assert set(ctx) == _CONTEXT_KEYS
    assert set(ctx["screens"]) == {"index_path", "outcome", "tiles", "render_note"}
    assert set(ctx["copy_into_review_record"]) == {"input_sha256", "preview_sha256", "reviewed_at", "mode"}
    in_bytes = (job.job_dir / "draft" / "report-input.json").read_bytes()
    html_bytes = (job.job_dir / "draft" / "report.html").read_bytes()
    assert ctx["input"] == {"path": "runs/j1/draft/report-input.json", "sha256": _sha(in_bytes)}
    assert ctx["preview"] == {"path": "runs/j1/draft/report.html", "sha256": _sha(html_bytes)}
    copy = ctx["copy_into_review_record"]
    assert (copy["input_sha256"], copy["preview_sha256"]) == (_sha(in_bytes), _sha(html_bytes))
    assert copy["mode"] == "separate_review_pass"
    assert copy["reviewed_at"] == ctx["now"] and _KST_STAMP.match(ctx["now"])
    assert ctx["job_id"] == _JOB and ctx["code"] == _CODE
    assert ctx["screens"]["outcome"] == "complete"
    assert ctx["screens"]["tiles"] == [f"runs/j1/screens/{t}" for t in _TILES]


def test_air6_012_all_paths_are_harness_relative(tmp_path):
    job = _make_job(tmp_path)
    paths = [p for p in _path_values(job.seen.ctx_at_entry)]
    assert len(paths) >= 8
    for value in paths:
        assert value.startswith("runs/j1/") and ".." not in value and not os.path.isabs(value), value


@pytest.mark.parametrize("kind", ["unavailable", "no_index"])
def test_air6_012_context_is_written_even_when_capture_failed(tmp_path, kind):
    if kind == "unavailable":
        def edit(idx):
            idx["outcome"] = "unavailable"
            for vp in idx["viewports"]:
                vp["status"], vp["tiles"] = "skipped", []
        job = _make_job(tmp_path, index_edit=edit, pre=lambda jd: [p.unlink() for p in (jd / "screens").glob("*.png")])
        assert job.seen.ctx_at_entry["screens"]["outcome"] == "unavailable"
    else:
        job = _make_job(tmp_path, pre=lambda jd: __import__("shutil").rmtree(jd / "screens"))
        assert job.seen.ctx_at_entry["screens"]["outcome"] == "failed"
    ctx = job.seen.ctx_at_entry
    assert ctx["screens"]["tiles"] == []
    assert ctx["screens"]["render_note"] and set(ctx) == _CONTEXT_KEYS


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-014 — 감수 중 판단 대상 불변과 변조 탐지
# ─────────────────────────────────────────────────────────────────────────────


def _tamper_report(jd, ctx):
    (jd / "draft" / "report.html").write_text("<html>changed</html>")


def _tamper_input(jd, ctx):
    (jd / "draft" / "report-input.json").write_text('{"k": 99}')


def _forge_index_and_tile(jd, ctx):
    forged = b"forged tile"
    (jd / "screens" / "mobile-01.png").write_bytes(forged)

    def fix(idx):
        idx["outcome"], _MOBILE(idx)["metrics"]["horizontal_overflow"] = "complete", False
        _MOBILE(idx)["tiles"][0]["sha256"] = _sha(forged)

    _edit_index(jd, fix)


def _overwrite_tile(jd, ctx):
    (jd / "screens" / "desktop-02.png").write_bytes(b"other bytes")


def _add_tile(jd, ctx):
    (jd / "screens" / "mobile-99.png").write_bytes(b"new")


def _add_nested(jd, ctx):
    (jd / "screens" / "sub").mkdir()
    (jd / "screens" / "sub" / "a.png").write_bytes(b"nested")


def _restore_tile(jd, ctx):
    tile = jd / "screens" / "desktop-01.png"
    original = tile.read_bytes()
    tile.write_bytes(b"changed")
    tile.write_bytes(original)
    return [str(jd / "screens" / "desktop-01.png")]


def _write_attempt_draft(jd, ctx):
    return [str(jd / "draft" / "report.html")]


def _write_review_only(jd, ctx):
    (jd / "review").mkdir(exist_ok=True)
    (jd / "review" / "delivery-audit.json").write_text("{}")
    return [str(jd / "audit-review.json"), str(jd / "review" / "delivery-audit.json")]


def _write_case_variant(jd, ctx):
    return [str(jd.parent.parent / "runs" / "j1" / "Screens" / "mobile-01.png")]


@pytest.mark.parametrize(
    ("case", "session", "needs"),
    [
        ("2", _tamper_report, {"draft_changed"}),
        ("3", _tamper_input, {"draft_changed"}),
        ("4", _forge_index_and_tile, {"screens_changed"}),
        ("5", _overwrite_tile, {"screens_changed"}),
        ("6", _add_tile, {"screens_changed"}),
        ("6b", _add_nested, {"screens_changed"}),
        ("7", _restore_tile, {"judged_input_write_attempt"}),
        ("8", _write_attempt_draft, {"judged_input_write_attempt"}),
        ("10", _write_case_variant, {"judged_input_write_attempt"}),
    ],
    ids=["2", "3", "4", "5", "6", "6b", "7", "8", "10"],
)
def test_air6_014_tampering_makes_screen_verification_inadmissible(tmp_path, case, session, needs):
    job = _make_job(tmp_path, session=session)
    admissible, reasons = gv.evaluate_admissibility(job.job_dir)
    assert admissible is False
    assert needs <= set(reasons), reasons
    assert job.receipt["visual_admissible"] is False and needs <= set(job.receipt["reasons"])
    if case in ("2", "3"):
        assert job.receipt["draft_unchanged"] is False
        h = job.receipt["hashes"]
        assert (h["input_start"] != h["input_end"]) or (h["preview_start"] != h["preview_end"])
    if case in ("4", "5", "6", "6b"):
        assert job.receipt["screens"]["snapshot_start"] != job.receipt["screens"]["snapshot_end"]


def test_air6_014_restored_tile_has_equal_snapshots_but_recorded_write(tmp_path):
    job = _make_job(tmp_path, session=_restore_tile)
    scr = job.receipt["screens"]
    assert scr["snapshot_start"] == scr["snapshot_end"]
    assert job.receipt["judged_writes"] == ["runs/j1/screens/desktop-01.png"]
    assert gv.evaluate_admissibility(job.job_dir) == (False, ["judged_input_write_attempt"])


def test_air6_014_case_variant_write_is_recorded_case_insensitively(tmp_path):
    job = _make_job(tmp_path, session=_write_case_variant)
    assert [p.casefold() for p in job.receipt["judged_writes"]] == ["runs/j1/screens/mobile-01.png"]


def test_air6_014_untouched_session_records_equal_measurements(tmp_path):
    job = _make_job(tmp_path)
    r = job.receipt
    assert r["draft_unchanged"] is True and r["judged_writes"] == []
    assert r["hashes"]["input_start"] == r["hashes"]["input_end"] and r["hashes"]["preview_start"] == r["hashes"]["preview_end"]
    assert r["screens"]["snapshot_start"] == r["screens"]["snapshot_end"]


def test_air6_014_normal_review_directory_writes_are_not_false_positives(tmp_path):
    job = _make_job(tmp_path, session=_write_review_only)
    assert job.receipt["judged_writes"] == []
    assert gv.evaluate_admissibility(job.job_dir) == (True, [])


def _plant_record(jd: Path) -> None:
    html = (jd / "draft" / "report.html").read_bytes()
    inp = (jd / "draft" / "report-input.json").read_bytes()
    checks = {k: {"status": "pass", "evidence": "x"} for k in ("source_accuracy", "calculations", "coverage", "opinion")}
    checks["visual"] = {"status": "pass", "evidence": _EVIDENCE}
    (jd / "audit-review.json").write_text(json.dumps({
        "mode": "separate_review_pass", "input_sha256": _sha(inp), "preview_sha256": _sha(html),
        "reviewed_at": _FUTURE, "checks": checks, "issues": [],
    }))


def _plant_final(jd: Path) -> None:
    (jd / "final").mkdir(exist_ok=True)
    (jd / "final" / "report.html").write_text("<html>planted</html>")
    (jd / "final" / "render-validation.json").write_text('{"delivery_allowed": true}')


def _make_final(jd, ctx):
    _plant_final(jd)


def test_air6_014_11_planted_audit_review_is_removed_before_session(tmp_path):
    job = _make_job(tmp_path, pre=_plant_record, write_audit=False, session=_make_final)
    assert job.seen.audit_at_entry is False  # 진입 시점에 이미 지워져 있다
    assert job.receipt["outcome"] == "review_failed"
    assert job.receipt["reasons"] == ["review_not_completed", "no_audit_review"]
    assert gv.evaluate_admissibility(job.job_dir) == (False, ["review_not_completed", "no_audit_review"])


def test_air6_014_12_planted_final_is_removed_before_session(tmp_path):
    job = _make_job(tmp_path, pre=_plant_final, make_final=False)
    assert job.seen.final_at_entry is False
    assert job.receipt["outcome"] == "reviewed" and job.receipt["reasons"] == []
    assert not (job.job_dir / "final").exists()  # 세션이 만들지 않았으므로 최종본 없음


def test_air6_014_13_delete_failure_blocks_session_and_records_start_values(tmp_path, monkeypatch):
    def plant_both(jd):
        _plant_record(jd)
        _plant_final(jd)

    monkeypatch.setattr(gv, "_delete_planted", lambda _jd: False)
    job = _make_job(tmp_path, pre=plant_both)
    assert job.seen.session_ran is False  # 감수기 호출 0
    assert job.receipt["outcome"] == "review_failed"
    assert job.receipt["reasons"] == ["review_not_completed", "tile_not_read"]
    assert gv.evaluate_admissibility(job.job_dir) == (False, ["review_not_completed", "tile_not_read"])
    r = job.receipt
    assert r["screens"]["snapshot_start"] == r["screens"]["snapshot_end"]  # 시작·종료가 같은 값
    assert r["draft_unchanged"] is True
    assert (job.job_dir / "final" / "report.html").exists()  # 삭제 못 한 파일은 그대로(세션만 안 돈다)


def _outside(tmp_path: Path) -> Path:
    """작업 폴더 밖의 파일·폴더. 심볼릭 링크가 가리키는 대상이며 지워지면 안 된다."""
    outside = tmp_path / "outside"
    (outside / "dir").mkdir(parents=True)
    (outside / "keep.txt").write_text("KEEP")
    (outside / "dir" / "inner.txt").write_text("KEEP")
    return outside


def _plant_review(outside: Path):
    def plant(jd):
        review = jd / "review"
        (review / "sub").mkdir(parents=True)
        (review / "delivery-audit.json").write_text('{"decision":"pass"}')
        (review / "receipt.json").write_text('{"outcome":"reviewed","visual_admissible":true}')
        (review / "sub" / "x.json").write_text("{}")
        (review / "link").symlink_to(outside / "keep.txt")
        (review / "linkdir").symlink_to(outside / "dir")

    return plant


def _assert_outside_intact(outside: Path) -> None:
    assert (outside / "keep.txt").read_text() == "KEEP"
    assert (outside / "dir" / "inner.txt").read_text() == "KEEP"


def test_air6_014_14_review_dir_is_emptied_without_following_links(tmp_path):
    outside = _outside(tmp_path)
    job = _make_job(tmp_path, pre=_plant_review(outside))
    assert job.seen.review_at_entry == ["context.json"]  # 서버가 쓴 것 하나뿐
    assert sorted(p.name for p in (job.job_dir / "review").iterdir()) == ["context.json", "receipt.json"]
    _assert_outside_intact(outside)  # 링크를 따라가 대상을 지우지 않았다
    assert job.receipt["outcome"] == "reviewed" and job.receipt["reasons"] == []
    assert json.loads(_receipt_path(job.job_dir).read_text()) == job.receipt  # 심은 위조가 아니라 서버가 쓴 영수증


def test_air6_014_14_review_that_is_itself_a_symlink_is_unlinked_not_followed(tmp_path):
    outside = _outside(tmp_path)

    def plant(jd):
        (jd / "review").symlink_to(outside / "dir", target_is_directory=True)

    job = _make_job(tmp_path, pre=plant)
    assert job.seen.review_at_entry == ["context.json"]
    assert not (job.job_dir / "review").is_symlink()
    assert sorted(p.name for p in (outside / "dir").iterdir()) == ["inner.txt"]  # 대상 폴더에 아무것도 쓰지 않았다
    _assert_outside_intact(outside)


def test_air6_014_14_review_that_is_a_regular_file_is_replaced(tmp_path):
    job = _make_job(tmp_path, pre=lambda jd: (jd / "review").write_text("not a dir"))
    assert job.seen.review_at_entry == ["context.json"]


def _fail_on_sub(monkeypatch):
    real = gv._remove_entry

    def remove_entry(path):
        if path.name == "sub":
            raise OSError("cannot remove")
        real(path)

    monkeypatch.setattr(gv, "_remove_entry", remove_entry)


def test_air6_014_15_review_delete_failure_blocks_session_and_records_start_values(tmp_path, monkeypatch):
    outside = _outside(tmp_path)

    def plant_all(jd):
        _plant_record(jd)
        _plant_final(jd)
        _plant_review(outside)(jd)

    _fail_on_sub(monkeypatch)
    job = _make_job(tmp_path, pre=plant_all)
    assert job.seen.session_ran is False  # 감수기 호출 0
    assert job.receipt["outcome"] == "review_failed"
    assert job.receipt["reasons"] == ["review_not_completed", "tile_not_read"]  # (13)과 같은 목록
    assert gv.evaluate_admissibility(job.job_dir) == (False, ["review_not_completed", "tile_not_read"])
    r = job.receipt
    assert r["screens"]["snapshot_start"] == r["screens"]["snapshot_end"] and r["draft_unchanged"] is True
    assert not (job.job_dir / "review" / "context.json").exists()  # 컨텍스트도 쓰지 않는다


def test_air6_014_15_without_planted_record_the_absent_record_adds_no_audit_review(tmp_path, monkeypatch):
    """(15)의 목록은 심은 audit-review.json이 있을 때의 값이다. 없으면 조건 13이 더해진다(SPEC 정밀도 기록)."""
    _fail_on_sub(monkeypatch)
    job = _make_job(tmp_path, pre=_plant_review(_outside(tmp_path)))
    assert job.seen.session_ran is False
    assert job.receipt["reasons"] == ["review_not_completed", "tile_not_read", "no_audit_review"]


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-015 — 영수증·열람 집계
# ─────────────────────────────────────────────────────────────────────────────

_RECEIPT_KEYS = {"schema_version", "outcome", "started_at", "finished_at", "process", "hashes", "draft_unchanged",
                 "screens", "judged_writes", "audit_review", "visual_admissible", "reasons"}


def test_air6_015_receipt_has_exact_fixed_keys_and_values(tmp_path):
    r = _make_job(tmp_path).receipt
    assert set(r) == _RECEIPT_KEYS
    assert set(r["process"]) == {"exit_code", "timed_out"}
    assert set(r["hashes"]) == {"input_start", "input_end", "preview_start", "preview_end"}
    assert set(r["screens"]) == {"outcome", "index_sha256", "tiles_expected", "tiles_read", "snapshot_start",
                                 "snapshot_end"}
    assert set(r["screens"]["snapshot_end"]) == {"index_sha256", "files"}
    assert set(r["audit_review"]) == {"present", "sha256", "mode", "visual_status", "input_sha256",
                                      "preview_sha256", "reviewed_at"}
    assert r["outcome"] in gv.OUTCOMES
    assert _KST_STAMP.match(r["started_at"]) and _KST_STAMP.match(r["finished_at"])
    assert r["screens"]["tiles_expected"] == _TILES and r["screens"]["tiles_read"] == _TILES
    assert r["audit_review"]["present"] is True and r["audit_review"]["visual_status"] == "pass"
    assert r["screens"]["snapshot_end"]["files"].keys() == {"index.json", *_TILES}


def _tracker_reads(gr, lines: list[str]) -> list[str]:
    tracker = gr.ReviewTracker()
    for line in lines:
        tracker.feed(line)
    return tracker.reads


def _tile(harness: Path, name: str, job: str = _JOB) -> str:
    return str(harness / "runs" / job / "screens" / name)


def _read(i: str, path: str, parent=None) -> list[str]:
    return [_tu(i, "Read", {"file_path": path}, parent)]


def test_air6_015_s1_all_tiles_read_with_successful_results(gr, tmp_path):
    h = tmp_path / "h"
    lines = []
    for n, t in enumerate(_TILES):
        lines += _read(f"r{n}", _tile(h, t)) + [_tr(f"r{n}")]
    assert gv.tiles_read(_tracker_reads(gr, lines), h, _JOB, _TILES) == _TILES


def test_air6_015_s2_tool_use_without_result_is_not_read(gr, tmp_path):
    h = tmp_path / "h"
    lines = [x for t in _TILES for x in _read("u" + t, _tile(h, t))]
    assert gv.tiles_read(_tracker_reads(gr, lines), h, _JOB, _TILES) == []


def test_air6_015_s3_error_result_is_not_read(gr, tmp_path):
    h = tmp_path / "h"
    lines = _read("a", _tile(h, _TILES[0])) + [_tr("a", is_error=True)]
    assert gv.tiles_read(_tracker_reads(gr, lines), h, _JOB, _TILES) == []


def test_air6_015_s4_relative_and_absolute_paths(gr, tmp_path):
    h = tmp_path / "h"
    lines = (_read("a", "runs/j1/screens/mobile-01.png") + [_tr("a")]
             + _read("b", _tile(h, "desktop-01.png")) + [_tr("b")])
    assert gv.tiles_read(_tracker_reads(gr, lines), h, _JOB, _TILES) == ["desktop-01.png", "mobile-01.png"]


@pytest.mark.parametrize(
    "bad",
    [
        "runs/other/screens/mobile-01.png",  # 다른 작업의 같은 이름 파일
        "runs/j1/screens/../../other/screens/mobile-01.png",  # .. 우회
        "/tmp/mobile-01.png",  # 기본 이름만 같음
        "runs/j1/screens/mobile-01.png.bak",  # 부분 문자열
        "runs/j1/Screens/mobile-01.png",  # 대소문자 변형 — 읽음으로 세지 않는다(안전 방향)
    ],
)
def test_air6_015_s5_lookalike_paths_do_not_count(gr, tmp_path, bad):
    h = tmp_path / "h"
    lines = _read("a", bad) + [_tr("a")]
    assert gv.tiles_read(_tracker_reads(gr, lines), h, _JOB, _TILES) == []


def test_air6_015_s6_subagent_reads_count(gr, tmp_path):
    h = tmp_path / "h"
    lines = _read("a", _tile(h, "mobile-01.png"), parent="toolu_parent") + [_tr("a", parent="toolu_parent")]
    assert gv.tiles_read(_tracker_reads(gr, lines), h, _JOB, _TILES) == ["mobile-01.png"]


def test_air6_015_s8_is_error_false_and_absent_are_success_true_is_error(gr, tmp_path):
    h = tmp_path / "h"
    lines = (_read("a", _tile(h, "desktop-01.png")) + [_tr("a", is_error=False)]
             + _read("b", _tile(h, "desktop-02.png")) + [_tr("b")]
             + _read("c", _tile(h, "mobile-01.png")) + [_tr("c", is_error=True)])
    assert gv.tiles_read(_tracker_reads(gr, lines), h, _JOB, _TILES) == ["desktop-01.png", "desktop-02.png"]


def test_air6_015_tracker_collects_write_and_edit_attempts_regardless_of_result(gr):
    tracker = gr.ReviewTracker()
    for line in (_tu("w", "Write", {"file_path": "runs/j1/draft/a"}), _tr("w", is_error=True),
                 _tu("e", "Edit", {"file_path": "/x/screens/b"}), _tu("r", "Read", {"file_path": "/x/c"})):
        tracker.feed(line)
    assert tracker.writes == ["runs/j1/draft/a", "/x/screens/b"]


def test_air6_015_tracker_survives_garbage_lines(gr):
    tracker = gr.ReviewTracker()
    for line in ("", "{broken", "[]", '{"type":"assistant","message":5}', '{"type":"user","message":{"content":[5]}}'):
        assert tracker.feed(line) == []


def test_air6_015_tracker_emits_render_final_only_for_final_render(gr):
    tracker = gr.ReviewTracker()
    final = _tu("b1", "Bash", {"command": "python3 render_report.py --final --input x"})
    draft = _tu("b2", "Bash", {"command": "python3 render_report.py --input x"})
    audit = _tu("b3", "Bash", {"command": "python3 audit_report.py --input x"})
    assert [e.stage for e in tracker.feed(final)] == ["render_final"]
    assert tracker.feed(draft) == [] and tracker.feed(audit) == []


def test_air6_015_s7_session_written_receipt_is_overwritten_by_server(tmp_path):
    def forge(jd, ctx):
        (jd / "review").mkdir(exist_ok=True)
        _receipt_path(jd).write_text(json.dumps({"schema_version": 1, "visual_admissible": True, "reasons": []}))

    job = _make_job(tmp_path, session=forge, skip_read=tuple(_TILES))  # 타일을 하나도 열지 않음
    stored = json.loads(_receipt_path(job.job_dir).read_text())
    assert stored["visual_admissible"] is False  # 서버 판정을 따른다
    assert stored["reasons"] == ["tile_not_read"]
    assert set(stored) == _RECEIPT_KEYS


def test_air6_015_s9a_replace_failure_leaves_no_session_receipt(tmp_path, monkeypatch, caplog):
    def forge(jd, ctx):
        (jd / "review").mkdir(exist_ok=True)
        _receipt_path(jd).write_text(json.dumps({"visual_admissible": True}))

    def fail(src, dst):
        raise OSError("replace failed")

    monkeypatch.setattr(gv, "_replace", fail)
    with caplog.at_level(logging.ERROR, logger="backend.services.goose_review"):
        job = _make_job(tmp_path, session=forge)
    assert job.result.written is False and job.result.file_remains is False
    assert not _receipt_path(job.job_dir).exists()  # 서버가 먼저 제거했다
    assert gv.evaluate_admissibility(job.job_dir) == (False, ["no_receipt"])
    assert [r.getMessage() for r in caplog.records].count(f"receipt_write_failed: {_receipt_path(job.job_dir)}") == 1


def test_air6_015_s9b_removal_and_replace_both_fail_reports_remaining_file(tmp_path, monkeypatch, caplog):
    def forge(jd, ctx):
        (jd / "review").mkdir(exist_ok=True)
        _receipt_path(jd).write_text(json.dumps({"visual_admissible": True}))

    def fail_remove(path):
        raise OSError("remove failed")

    def fail_replace(src, dst):
        raise OSError("replace failed")

    monkeypatch.setattr(gv, "_remove", fail_remove)
    monkeypatch.setattr(gv, "_replace", fail_replace)
    with caplog.at_level(logging.ERROR, logger="backend.services.goose_review"):
        job = _make_job(tmp_path, session=forge)
    assert job.result.written is False and job.result.file_remains is True  # 호출자가 이벤트를 draft로 확정한다
    assert sum("receipt_write_failed" in r.getMessage() for r in caplog.records) == 1


def test_air6_015_outcomes_follow_process_facts(tmp_path):
    assert _make_job(tmp_path / "a", timed_out=True, exit_code=None).receipt["outcome"] == "timeout"
    assert _make_job(tmp_path / "b", exit_code=3).receipt["outcome"] == "review_failed"
    assert _make_job(tmp_path / "c", write_audit=False).receipt["outcome"] == "review_failed"
    assert _make_job(tmp_path / "d", outcome="cancelled").receipt["outcome"] == "cancelled"
    r = _make_job(tmp_path / "e", write_audit=False).receipt
    assert r["reasons"] == ["review_not_completed", "no_audit_review"]


# ─────────────────────────────────────────────────────────────────────────────
# AC-AIR6-011 — 감수 세션 호출 (실행기)
# ─────────────────────────────────────────────────────────────────────────────

_STREAM_TAIL = '{"type":"result"}\n'


def _environ(tmp_path: Path, **extra: str) -> dict[str, str]:
    harness = tmp_path / "harness"
    (harness / "runs").mkdir(parents=True, exist_ok=True)
    return {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home"), "AI_REPORT_GOOSE_HARNESS_DIR": str(harness), **extra}


def _fake_claude(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "fake-claude"
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)
    return path


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _value_after(argv: list[str], flag: str) -> str:
    assert flag in argv, f"{flag} 없음"
    return argv[argv.index(flag) + 1]


async def test_air6_011_review_session_uses_goose_security_argv_cwd_and_env(gr, tmp_path):
    rec = tmp_path / "rec"
    rec.mkdir()
    fake = _fake_claude(
        tmp_path,
        f'printf "%s\\n" "$@" > "{rec}/argv"\nenv > "{rec}/env"\npwd -P > "{rec}/cwd"\n'
        f"echo '{_STREAM_TAIL.strip()}'\nexit 0\n",
    )
    environ = _environ(tmp_path, OPENAI_API_KEY="canary")
    result = await asyncio.wait_for(
        gr.run_review(job_id=_JOB, code=_CODE, environ=environ, claude_bin=str(fake)), 20
    )
    argv = (rec / "argv").read_text().splitlines()
    harness = Path(environ["AI_REPORT_GOOSE_HARNESS_DIR"])
    assert _value_after(argv, "--setting-sources") == "project"
    assert _value_after(argv, "--settings") == str(harness / ".claude" / "settings.json")
    assert _value_after(argv, "--permission-mode") == "dontAsk"
    assert "--strict-mcp-config" in argv and "--no-session-persistence" in argv
    joined = "\n".join(argv)
    assert "--dangerously-skip-permissions" not in joined and "bypassPermissions" not in joined
    prompt = _value_after(argv, "-p")
    assert _JOB in prompt and _CODE in prompt and "감수 세션" in prompt and _STOCK_NAME not in prompt
    assert Path((rec / "cwd").read_text().strip()) == harness.resolve()
    assert "canary" not in (rec / "env").read_text() and "OPENAI_API_KEY" not in (rec / "env").read_text()
    assert result.started and result.timed_out is False and result.exit_code == 0


async def test_air6_011_timeout_kills_group_and_reports_timed_out(gr, tmp_path):
    pidfile = tmp_path / "child.pid"
    fake = _fake_claude(tmp_path, f'sleep 300 &\necho $! > "{pidfile}"\nwait\n')
    environ = _environ(tmp_path, AI_REPORT_GOOSE_REVIEW_TIMEOUT="1")
    started = time.monotonic()
    try:
        result = await asyncio.wait_for(
            gr.run_review(job_id=_JOB, code=_CODE, environ=environ, claude_bin=str(fake), grace_sec=0.5), 20
        )
        child = int(pidfile.read_text())
        time.sleep(0.3)
        assert result.timed_out is True and result.exit_code is None
        assert time.monotonic() - started < 15
        assert not _pid_alive(child)
    finally:
        if pidfile.exists():
            try:
                os.kill(int(pidfile.read_text()), signal.SIGKILL)
            except (ProcessLookupError, ValueError):
                pass


async def test_air6_002_cancel_review_kills_process_group(gr, tmp_path):
    pidfile = tmp_path / "child.pid"
    fake = _fake_claude(tmp_path, f'sleep 300 &\necho $! > "{pidfile}"\nwait\n')
    task = asyncio.create_task(
        gr.run_review(job_id=_JOB, code=_CODE, environ=_environ(tmp_path), claude_bin=str(fake), grace_sec=0.5)
    )
    try:
        for _ in range(100):
            if pidfile.exists() and pidfile.read_text().strip():
                break
            await asyncio.sleep(0.05)
        child = int(pidfile.read_text())
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, 10)
        time.sleep(0.3)
        assert not _pid_alive(child)
    finally:
        if pidfile.exists():
            try:
                os.kill(int(pidfile.read_text()), signal.SIGKILL)
            except (ProcessLookupError, ValueError):
                pass


async def test_air6_011_binary_missing_is_reported_not_raised(gr, tmp_path):
    result = await gr.run_review(job_id=_JOB, code=_CODE, environ=_environ(tmp_path), claude_bin=str(tmp_path / "nope"))
    assert result.started is False and result.exit_code is None


async def test_air6_011_stream_reads_and_writes_reach_receipt_end_to_end(gr, tmp_path):
    """가짜 claude가 합성 스트림을 내보내면 run_review가 모은 기록이 영수증의 tiles_read·judged_writes가 된다."""
    harness = tmp_path / "harness"
    job_dir = _build_job_files(harness)
    start = gv.prepare_review(job_dir, code=_CODE)
    lines = []
    for n, t in enumerate(_TILES):
        lines += _read(f"r{n}", _tile(harness, t)) + [_tr(f"r{n}")]
    lines += [_tu("w1", "Write", {"file_path": str(job_dir / "audit-review.json")})]
    ctx = json.loads((job_dir / "review" / "context.json").read_text())
    (job_dir / "audit-review.json").write_text(json.dumps(_honest_record(ctx)))
    stream = tmp_path / "stream.jsonl"
    stream.write_text("\n".join(lines) + "\n")
    fake = _fake_claude(tmp_path, f'cat "{stream}"\nexit 0\n')
    environ = _environ(tmp_path)
    assert Path(environ["AI_REPORT_GOOSE_HARNESS_DIR"]) == harness
    run = await asyncio.wait_for(gr.run_review(job_id=_JOB, code=_CODE, environ=environ, claude_bin=str(fake)), 20)
    receipt = gv.finish_review(
        job_dir, start, harness_dir=harness, exit_code=run.exit_code, timed_out=run.timed_out,
        read_paths=run.reads, write_paths=run.writes,
    ).receipt
    assert receipt["screens"]["tiles_read"] == _TILES and receipt["judged_writes"] == []
    assert receipt["outcome"] == "reviewed" and receipt["visual_admissible"] is True


def test_air6_011_review_timeout_env_resolution(gr):
    assert gr.resolve_review_timeout({}) == 900.0
    assert gr.resolve_review_timeout({"AI_REPORT_GOOSE_REVIEW_TIMEOUT": "42"}) == 42.0
    assert gr.resolve_review_timeout({"AI_REPORT_GOOSE_REVIEW_TIMEOUT": "abc"}) == 900.0
    assert gr.resolve_review_timeout({"AI_REPORT_GOOSE_REVIEW_TIMEOUT": "-1"}) == 900.0
    # 1차 세션 시간 상한 해석은 그대로다
    assert gr.resolve_timeout({"AI_REPORT_GOOSE_TIMEOUT": "7"}) == 7.0


@pytest.mark.parametrize(("code", "job"), [("12345", "j"), ("abcdef", "j"), ("123456", "../x"), ("123456", "")])
def test_air6_011_review_prompt_rejects_unsafe_values(gr, code, job):
    with pytest.raises(ValueError):
        gr.build_review_prompt(job, code)


# ─────────────────────────────────────────────────────────────────────────────
# SPEC-AI-REPORT-006 M4 — select_report가 판정 함수를 부른다 (AC-AIR6-016 select_report 몫)
# 조건 0(final_not_allowed)은 select_report 자신의 기존 조건이고, 1~17은 evaluate_admissibility의 몫이다.
# ─────────────────────────────────────────────────────────────────────────────


def _draft_of(job) -> tuple[str, Path]:
    return ("draft", job.job_dir / "draft")


def test_air6_016_select_report_baseline_p_is_final(gr, tmp_path):
    job = _make_job(tmp_path)
    assert gr.select_report(job.job_dir) == ("final", job.job_dir / "final")


@pytest.mark.parametrize(("case", "kwargs", "expected"), _PRE_CASES, ids=[c[0] for c in _PRE_CASES])
def test_air6_016_select_report_pre_session_cases_fall_to_draft(gr, tmp_path, case, kwargs, expected):
    job = _make_job(tmp_path, **kwargs)
    assert gr.select_report(job.job_dir) == _draft_of(job)


@pytest.mark.parametrize(("case", "mutate", "expected"), _POST_CASES, ids=[c[0] for c in _POST_CASES])
def test_air6_016_select_report_post_receipt_cases_fall_to_draft(gr, tmp_path, case, mutate, expected):
    job = _make_job(tmp_path)
    assert gr.select_report(job.job_dir) == ("final", job.job_dir / "final")
    mutate(job.job_dir)
    assert gr.select_report(job.job_dir) == _draft_of(job)


def test_air6_016_select_report_condition0_final_not_allowed(gr, tmp_path):
    """(n) 조건 0: delivery_allowed가 거짓이면 판정 함수가 인정이어도 draft."""
    job = _make_job(tmp_path)
    (job.job_dir / "final" / "render-validation.json").write_text('{"delivery_allowed": false}')
    assert gv.evaluate_admissibility(job.job_dir) == (True, [])
    assert gr.select_report(job.job_dir) == _draft_of(job)


def test_air6_016_select_report_final_without_receipt_and_without_draft(gr, tmp_path):
    """영수증 없는 final/만 있고 draft/가 없는 폴더는 None(기존 규칙)."""
    jd = tmp_path / "harness" / "runs" / "jx"
    jd.mkdir(parents=True)
    _plant_final(jd)
    assert gr.select_report(jd) is None


def test_air6_016_select_report_is_the_single_caller_of_the_disk_wrapper(gr, tmp_path, monkeypatch):
    """select_report는 디스크 래퍼를 부른다(작성기는 코어). 래퍼 결과가 곧 판정이다."""
    job = _make_job(tmp_path)
    calls: list[Path] = []
    mod = sys.modules["backend.services.goose_review"]
    real = mod.evaluate_admissibility

    def spy(job_dir):
        calls.append(job_dir)
        return real(job_dir)

    monkeypatch.setattr(mod, "evaluate_admissibility", spy)
    assert gr.select_report(job.job_dir) == ("final", job.job_dir / "final")
    assert calls == [job.job_dir]


def test_air6_014_select_report_planted_cases(gr, tmp_path, monkeypatch):
    """(11)(12)(13)의 select_report 절반: 심은 파일은 인정 근거가 되지 못한다."""
    job11 = _make_job(tmp_path / "a", pre=_plant_record, write_audit=False, session=_make_final)
    assert gr.select_report(job11.job_dir) == _draft_of(job11)
    job12 = _make_job(tmp_path / "b", pre=_plant_final, make_final=False)
    assert gr.select_report(job12.job_dir) == _draft_of(job12)  # final/ 자체가 없음(조건 0)

    def plant_both(jd):
        _plant_record(jd)
        _plant_final(jd)

    monkeypatch.setattr(gv, "_delete_planted", lambda _jd: False)
    job13 = _make_job(tmp_path / "c", pre=plant_both)
    assert gr.select_report(job13.job_dir) == _draft_of(job13)


# ── 종료 영수증 작성기(integrity_failed·disabled·cancelled) ───────────────────


@pytest.mark.parametrize("outcome", ["integrity_failed", "disabled", "cancelled"])
def test_air6_001_004_outcome_receipt_writer(tmp_path, outcome):
    harness = tmp_path / "harness"
    job_dir = _build_job_files(harness)
    _plant_final(job_dir)  # 감수 없이 final/이 있어도 영수증은 인정하지 않는다
    result = gv.write_outcome_receipt(job_dir, outcome, harness_dir=harness)
    assert result.written is True
    receipt = json.loads(_receipt_path(job_dir).read_text())
    assert set(receipt) == _RECEIPT_KEYS
    assert receipt["outcome"] == outcome and receipt["visual_admissible"] is False
    assert receipt["screens"]["tiles_read"] == [] and receipt["judged_writes"] == []
    assert receipt["reasons"][0] == "review_not_completed"
    assert gv.evaluate_admissibility(job_dir)[0] is False


def test_air6_001_outcome_receipt_writer_rejects_unknown_outcome(tmp_path):
    harness = tmp_path / "harness"
    job_dir = _build_job_files(harness)
    with pytest.raises(ValueError):
        gv.write_outcome_receipt(job_dir, "reviewed", harness_dir=harness)
