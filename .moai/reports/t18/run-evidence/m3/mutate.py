"""M3 되돌림 관측 하네스: 보호 동작을 하나씩 임시로 되돌리고 시험이 RED가 되는지 본다.

각 변이는 (파일, 원문, 대체) 목록이며 원문은 파일에서 정확히 1번 나와야 적용된다. 끝나면 항상 원본을 복원하고
SHA-256 일치를 마지막 줄에 출력한다. 실행: `../../../.venv/bin/python -I mutate.py [이름 필터]`
"""
import hashlib
import os
import re
import subprocess
import sys

ROOT = os.getcwd()
REVIEW = "backend/services/goose_review.py"
RUNNER = "backend/services/goose_runner.py"
TESTS = "backend/tests/test_goose_review.py"


def code_drop(code: str, file: str = REVIEW):
    """조건 사유 추가 한 줄을 지운다(해당 조건의 검사 제거)."""
    return [(file, f'reasons.append("{code}")', "pass")]


MUTATIONS = [
    # ── AC-016 조건별 (수준 A: 결과 뒤집힘, 수준 B: 사유 목록 변화)
    ("016 cond1 no_receipt -> receipt_invalid (B, spec model)", [(REVIEW, 'reasons.append("no_receipt")', 'reasons.append("receipt_invalid")')]),
    ("016 cond1 no_receipt removed", code_drop("no_receipt")),
    ("016 cond2 receipt_invalid", code_drop("receipt_invalid")),
    ("016 cond3 review_not_completed", code_drop("review_not_completed")),
    ("016 cond4 judged_input_write_attempt", code_drop("judged_input_write_attempt")),
    ("016 cond5 screens_not_complete", code_drop("screens_not_complete")),
    ("016 cond6 screens_changed", code_drop("screens_changed")),
    ("016 cond7 tile_missing", code_drop("tile_missing")),
    ("016 cond8 tile_hash_mismatch", code_drop("tile_hash_mismatch")),
    ("016 cond9 draft_changed", code_drop("draft_changed")),
    ("016 cond10 preview_hash_mismatch", code_drop("preview_hash_mismatch")),
    ("016 cond11 tile_not_read", code_drop("tile_not_read")),
    ("016 cond12 mobile_overflow", code_drop("mobile_overflow")),
    ("016 cond13 no_audit_review removed", code_drop("no_audit_review")),
    ("016 cond14 mode_not_separate_review_pass", code_drop("mode_not_separate_review_pass")),
    ("016 cond15 visual_not_pass", code_drop("visual_not_pass")),
    ("016 cond16 reviewed_before_capture", code_drop("reviewed_before_capture")),
    ("016 cond17 font_note_missing", code_drop("font_note_missing")),
    ("021 b: marker regex-loosened ('렌더' substring)", [(REVIEW, "FONT_MARK in evidence", '"렌더" in evidence')]),
    ("021 e: marker must be at start", [(REVIEW, "FONT_MARK in evidence", "evidence.startswith(FONT_MARK)")]),
    ("016 stored visual_admissible used as input", [(REVIEW, "        reasons = evaluate_core(job_dir, receipt)\n    except Exception:",
        '        reasons = evaluate_core(job_dir, receipt)\n        if isinstance(receipt, dict) and receipt.get("visual_admissible") is True:\n            reasons = []\n    except Exception:')]),
    ("016 unreadable json treated as empty object (fail-open)", [(REVIEW, "    except (OSError, ValueError):\n        return None\n    return data if isinstance(data, dict) else None",
        "    except (OSError, ValueError):\n        return {}\n    return data if isinstance(data, dict) else None")]),
    ("016 writer calls disk wrapper instead of core", [(REVIEW, '    reasons = evaluate_core(job_dir, receipt)\n    receipt["visual_admissible"]',
        '    reasons = evaluate_admissibility(job_dir)[1]\n    receipt["visual_admissible"]')]),
    ("016 writer writes receipt twice", [(REVIEW, "    return _write_receipt_file(job_dir / REVIEW_DIR / RECEIPT_NAME, receipt)",
        "    _write_receipt_file(job_dir / REVIEW_DIR / RECEIPT_NAME, receipt)\n    return _write_receipt_file(job_dir / REVIEW_DIR / RECEIPT_NAME, receipt)")]),
    ("016 read guard without 16 (v0.3.0 form)", [(REVIEW, "        if index is not None:\n            reviewed_at", "        if True:\n            reviewed_at")]),
    # ── AC-014
    ("014 a: draft_end copied from start", [(REVIEW, "    draft_end = _measure_draft(job_dir)", "    draft_end = dict(start.hashes)")]),
    ("014 b: compare preview only", [(REVIEW, '"draft_unchanged": start.hashes == draft_end', '"draft_unchanged": start.hashes["preview"] == draft_end["preview"]')]),
    ("014 c: screens start snapshot measured after session", [(REVIEW, '"snapshot_start": start.snapshot,', '"snapshot_start": snapshot_end,')]),
    ("014 d: file set not part of snapshot", [(REVIEW, "        for name in names:\n            path = Path(root) / name",
        '        for name in [n for n in names if n.endswith(("index.json", "-01.png", "-02.png"))]:\n            path = Path(root) / name')]),
    ("014 e: Write/Edit attempts not recorded", [(RUNNER, 'elif name in ("Write", "Edit") and isinstance(inp.get("file_path"), str):', 'elif False and isinstance(inp.get("file_path"), str):')]),
    ("014 f: attempts with error results ignored", [(RUNNER, '                path = self._pending.pop(str(item.get("tool_use_id")), None)',
        '                if item.get("is_error") is True and self.writes:\n                    self.writes.pop()\n                path = self._pending.pop(str(item.get("tool_use_id")), None)')]),
    ("014 g: review/ writes counted as violation", [(REVIEW, '"draft", "screens"\n        ):', '"draft", "screens", "review"\n        ):')]),
    ("014 h: case-sensitive path compare", [(REVIEW, "folded = rel.casefold().split(os.sep)", "folded = rel.split(os.sep)")]),
    ("014 i: planted audit-review.json not deleted", [(REVIEW, "        (job_dir / AUDIT_REVIEW_NAME).unlink(missing_ok=True)\n", "        pass\n"),
        (REVIEW, "    return not ((job_dir / AUDIT_REVIEW_NAME).exists() or (job_dir / \"final\").exists())", "    return not (job_dir / \"final\").exists()")]),
    ("014 j: planted final/ not deleted", [(REVIEW, "        elif final.exists():\n            shutil.rmtree(final)", "        elif final.exists():\n            pass"),
        (REVIEW, "        if final.is_symlink() or final.is_file():\n            final.unlink()", "        if False:\n            final.unlink()"),
        (REVIEW, "    return not ((job_dir / AUDIT_REVIEW_NAME).exists() or (job_dir / \"final\").exists())", "    return not (job_dir / AUDIT_REVIEW_NAME).exists()")]),
    ("014 k: delete failure ignored, session started", [(REVIEW, "    cleaned = _delete_planted(job_dir)\n", "    _delete_planted(job_dir)\n    cleaned = True\n")]),
    ("014 l: non-recursive snapshot", [(REVIEW, "    for root, _dirs, names in os.walk(screens):", "    for root, _dirs, names in [next(os.walk(screens), (str(screens), [], []))]:")]),
    ("014 m: start values blank on delete failure", [(REVIEW, "    cleaned = _delete_planted(job_dir)\n",
        '    cleaned = _delete_planted(job_dir)\n    if not cleaned:\n        return ReviewStart(job_dir.name, now or _now(), False, {"input": None, "preview": None}, {"index_sha256": None, "files": {}})\n')]),
    # ── AC-015
    ("015 a: tool_use counted without result", [(RUNNER, '            self._pending[item["id"]] = inp["file_path"]', '            self._pending[item["id"]] = inp["file_path"]\n            self.reads.append(inp["file_path"])')]),
    ("015 a2: is_error key presence treated as error", [(RUNNER, 'item.get("is_error") is not True', '"is_error" not in item')]),
    ("015 b: basename comparison", [(REVIEW, "    return [name for name in expected if os.path.join(base, name) in seen]",
        "    return [name for name in expected if any(p and os.path.basename(p) == name for p in seen)]"),
        (REVIEW, "    base = os.path.join(os.path.normpath(harness_dir), \"runs\", job_id, \"screens\")\n    seen = {_normalize(p, harness_dir) for p in read_paths}",
         "    base = os.path.join(os.path.normpath(harness_dir), \"runs\", job_id, \"screens\")\n    seen = {os.path.normpath(p) for p in read_paths}")]),
    ("015 c: relative path not resolved against harness", [(REVIEW, "    path = os.path.normpath(raw if os.path.isabs(raw) else os.path.join(base, raw))", "    path = os.path.normpath(raw)")]),
    ("015 d: subagent reads ignored", [(RUNNER, "        message = data.get(\"message\") if isinstance(data, dict) else None",
        "        if isinstance(data, dict) and data.get(\"parent_tool_use_id\"):\n            return []\n        message = data.get(\"message\") if isinstance(data, dict) else None")]),
    ("015 e: session-written receipt respected", [(REVIEW, '    tmp = path.with_name(f".{path.name}.tmp")\n    try:',
        '    tmp = path.with_name(f".{path.name}.tmp")\n    if path.exists():\n        return ReceiptResult(receipt, True, False)\n    try:')]),
    ("015 f: no removal before/after failed replace", [(REVIEW, "        _remove(path)\n        tmp.write_text", "        tmp.write_text"),
        (REVIEW, "            _remove(path)  # 제거 재시도 — 세션이 쓴 영수증을 남기지 않는다", "            pass")]),
    # ── AC-011 / AC-002
    ("011 a: --strict-mcp-config missing", [(RUNNER, '        "--strict-mcp-config",\n', "")]),
    ("011 b: permission bypass flag added", [(RUNNER, '        "--no-session-persistence",\n', '        "--no-session-persistence",\n        "--dangerously-skip-permissions",\n')]),
    ("011 c: prompt carries stock name", [(RUNNER, 'f"감수 세션입니다. 종목 코드: {code}.', 'f"감수 세션입니다. 종목 코드: {code} 홍길동전자.')]),
    ("011 d: full environment passed", [(RUNNER, "    return {key: parent[key] for key in ENV_ALLOWLIST if key in parent}", "    return dict(parent)")]),
    ("011 e: review time limit ignored", [(RUNNER, "    limit = resolve_review_timeout(env) if timeout_sec is None else timeout_sec", "    limit = 3600.0")]),
    ("011/002 f: process group cleanup missing", [(RUNNER, "        await asyncio.shield(_cleanup(proc, pgid, grace_sec))", "        pass")]),
    ("011 g: review timeout default changed", [(RUNNER, "DEFAULT_REVIEW_TIMEOUT_SEC = 900.0", "DEFAULT_REVIEW_TIMEOUT_SEC = 60.0")]),
]


def sha(path):
    return hashlib.sha256(open(os.path.join(ROOT, path), "rb").read()).hexdigest()


def main():
    flt = sys.argv[1] if len(sys.argv) > 1 else ""
    originals = {f: open(os.path.join(ROOT, f), encoding="utf-8").read() for f in (REVIEW, RUNNER)}
    before = {f: sha(f) for f in originals}
    try:
        for name, edits in MUTATIONS:
            if flt and flt not in name:
                continue
            applied, texts = True, dict(originals)
            for file, old, new in edits:
                if texts[file].count(old) != 1:
                    applied = False
                    print(f"[NOT-APPLIED] {name}: '{old[:60]}' x{texts[file].count(old)}", flush=True)
                    break
                texts[file] = texts[file].replace(old, new)
            if not applied:
                continue
            for file, text in texts.items():
                open(os.path.join(ROOT, file), "w", encoding="utf-8").write(text)
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", TESTS, "-q", "-p", "no:cacheprovider", "--tb=no", "-rf"],
                capture_output=True, text=True, cwd=ROOT, timeout=300,
            )
            tail = [ln for ln in proc.stdout.splitlines() if ln.startswith("FAILED") or re.search(r"\d+ (passed|failed)", ln)]
            failed = [ln.split("::")[-1].split(" ")[0] for ln in tail if ln.startswith("FAILED")]
            summary = tail[-1] if tail else proc.stdout[-200:]
            verdict = "RED" if failed else "STILL-GREEN"
            print(f"[{verdict}] {name} :: {summary} :: first failing: {failed[:4]}", flush=True)
            for file, text in originals.items():
                open(os.path.join(ROOT, file), "w", encoding="utf-8").write(text)
    finally:
        for file, text in originals.items():
            open(os.path.join(ROOT, file), "w", encoding="utf-8").write(text)
    print("restored-sha-match:", before == {f: sha(f) for f in originals})


main()
