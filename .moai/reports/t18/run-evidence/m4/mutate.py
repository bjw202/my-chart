"""M4 되돌림 RED 관측 하네스: 보호 동작을 하나씩 임시로 되돌리고 시험을 돌려 RED를 관측한 뒤 복원한다."""
import hashlib
import subprocess
import sys
from pathlib import Path

W = Path("/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/agent-aa2a25e79f99bda02")
PY = str(W / ".moai/state/verify/t18-m4/py.sh")
NODE = str(W / ".moai/state/verify/t18-m4/node.sh")
JS = "backend/services/goose_job_service.py"
GV = "backend/services/goose_review.py"
GR = "backend/services/goose_runner.py"
SVC = "backend/tests/test_goose_job_service.py"
REV = "backend/tests/test_goose_review.py"
RUN = "backend/tests/test_goose_runner.py"
STO = "backend/tests/test_goose_storage.py"

SVC_ALL = [SVC]
SEL = [REV, RUN, STO]


def sel(*files, k=None):
    args = ["-m", "pytest", *files, "-q", "-p", "no:cacheprovider", "-x"]
    if k:
        args += ["-k", k]
    return ("py", args)


# (id, ac, 파일, old, new, 시험 선택자)
M = []


def add(mid, ac, path, old, new, runner):
    M.append((mid, ac, path, old, new, runner))


# ── AC-001 ──
add("001a-post-inside-lock", "AC-001", JS,
    "post = await self._post_process(job) if result.status == \"done\" else _PostResult()",
    "async with self._lock:\n                post = await self._post_process(job) if result.status == \"done\" else _PostResult()",
    sel(SVC, k="air6_001_order"))
add("001b-review-before-capture", "AC-001", JS,
    "await self._screenshotter(job_dir)\n            except Exception:",
    "await self._run_reviewer(job)\n            except Exception:",
    sel(SVC, k="air6_001_order"))
add("001c-no-recheck", "AC-001", JS,
    "                integrity = await asyncio.to_thread(self._integrity)\n            except Exception:  # noqa: BLE001 - 검사를 못 하면",
    "                integrity = goose_harness.IntegrityResult(True, 'ok')\n            except Exception:  # noqa: BLE001 - 검사를 못 하면",
    sel(SVC, k="air6_001_order or air6_001_second"))
add("001d-recheck-failure-proceeds", "AC-001", JS,
    "if integrity is None or not integrity.ok:", "if False:",
    sel(SVC, k="air6_001_second"))
add("001e-default-injects-real", "AC-001", JS,
    "self._screenshotter = screenshotter\n        self._reviewer = reviewer",
    "self._screenshotter = screenshotter or goose_screenshot.capture\n        self._reviewer = reviewer or goose_runner.run_review",
    sel(SVC, k="air6_001_default"))
add("001f-no-draft-check", "AC-001", JS,
    "if not draft.is_file() or draft.is_symlink():", "if False:",
    sel(SVC, k="air6_001_no_draft"))
# ── AC-002 ──
add("002a-swallow-cancel", "AC-002", JS,
    "except Exception:  # noqa: BLE001 - 캡처 실패는 색인/컨텍스트에 남고",
    "except BaseException:  # noqa: BLE001 - 캡처 실패는 색인/컨텍스트에 남고",
    sel(SVC, k="air6_002_cancel_during_post_processing and shot"))
add("002b-no-cancel-receipt", "AC-002", JS,
    "            self._write_cancel_receipt(job_dir, harness_dir, start)\n            raise",
    "            raise",
    sel(SVC, k="air6_002_cancel_during_post_processing"))
add("002c-review-group-not-killed", "AC-002", GR,
    "async def _cleanup(proc: asyncio.subprocess.Process, pgid: int, grace_sec: float) -> None:\n",
    "async def _cleanup(proc: asyncio.subprocess.Process, pgid: int, grace_sec: float) -> None:\n    return\n",
    sel(SVC, k="air6_002_cancel_kills_real_review"))
# ── AC-003 ──
add("003b-stage-after-step", "AC-003", JS,
    "            await self._emit(job, \"progress\", {\"stage\": \"screenshot\", \"detail\": None})\n            try:\n                await self._screenshotter(job_dir)",
    "            try:\n                await self._screenshotter(job_dir)\n                await self._emit(job, \"progress\", {\"stage\": \"screenshot\", \"detail\": None})",
    sel(SVC, k="air6_003_stage_events"))
add("003c-stage-twice", "AC-003", JS,
    "            await self._emit(job, \"progress\", {\"stage\": \"screenshot\", \"detail\": None})\n",
    "            await self._emit(job, \"progress\", {\"stage\": \"screenshot\", \"detail\": None})\n            await self._emit(job, \"progress\", {\"stage\": \"screenshot\", \"detail\": None})\n",
    sel(SVC, k="air6_003_stage_events"))
add("003d-stage-when-off", "AC-003", JS,
    "                await self._write_outcome_receipt(job_dir, harness_dir, \"disabled\")",
    "                await self._emit(job, \"progress\", {\"stage\": \"screenshot\", \"detail\": None})\n                await self._write_outcome_receipt(job_dir, harness_dir, \"disabled\")",
    sel(SVC, k="air6_003_no_stage_events"))
add("003f-relay-all-review-events", "AC-003", JS,
    "            if ev.stage == \"render_final\" and not render_final_sent:\n                render_final_sent = True\n                await self._emit(job, \"progress\", {\"stage\": \"render_final\", \"detail\": None})",
    "            await self._emit(job, \"progress\", {\"stage\": ev.stage, \"detail\": None})",
    sel(SVC, k="air6_003_other_review"))
add("003g-render-final-not-deduped", "AC-003", JS,
    "if ev.stage == \"render_final\" and not render_final_sent:", "if ev.stage == \"render_final\":",
    sel(SVC, k="air6_003_render_final_emitted_once"))
# ── AC-004 ──
add("004a-ignore-switch", "AC-004", JS,
    "if os.environ.get(ENV_REVIEW, \"\").strip() == \"0\":", "if False:",
    sel(SVC, k="air6_004"))
add("004c-no-disabled-receipt", "AC-004", JS,
    "                await self._write_outcome_receipt(job_dir, harness_dir, \"disabled\")\n                return post",
    "                return post",
    sel(SVC, k="air6_004"))
add("004d-switch-skips-runner", "AC-004", JS,
    "            result = await self._runner(\n                job_id=job.job_id, stock_name=job.stock_name, code=job.code, on_event=on_event\n            )",
    "            if os.environ.get(ENV_REVIEW, \"\").strip() == \"0\":\n                result = goose_runner.RunResult(status=\"done\", error_kind=None, exit_code=0, delivery_status=\"draft\")\n            else:\n                result = await self._runner(\n                    job_id=job.job_id, stock_name=job.stock_name, code=job.code, on_event=on_event\n                )",
    sel(SVC, k="air6_004"))
# ── AC-005 ──
add("005a-capture-failure-fails-job", "AC-005", JS,
    "            except Exception:  # noqa: BLE001 - 캡처 실패는 색인/컨텍스트에 남고 감수는 계속한다(REQ-AIR6-005)\n                logger.exception(\"goose 작업 %s 화면 캡처 실패 — 감수는 계속\", job.job_id)\n",
    "            except ZeroDivisionError:\n                pass\n",
    sel(SVC, k="air6_005_post_failures and shot_raises")),
add("005b-capture-failure-skips-review", "AC-005", JS,
    "                logger.exception(\"goose 작업 %s 화면 캡처 실패 — 감수는 계속\", job.job_id)\n",
    "                logger.exception(\"goose 작업 %s 화면 캡처 실패 — 감수는 계속\", job.job_id)\n                return post\n",
    sel(SVC, k="air6_005_post_failures and shot_raises"))
add("005c-review-exception-propagates", "AC-005", JS,
    "        except Exception:  # noqa: BLE001 - 감수 실패는 영수증(review_failed)으로 남기고 초안으로 끝낸다",
    "        except ZeroDivisionError:  # mutated",
    sel(SVC, k="air6_005_post_failures and review_raises"))
add("005c2-outer-failopen-removed+review-propagates", "AC-005", JS,
    "        except Exception:  # noqa: BLE001 - fail-open: 후처리의 어떤 실패도 작업을 error로 만들지 않는다",
    "        except ZeroDivisionError:  # mutated",
    sel(SVC, k="air6_005_unexpected"))
add("005d-timeout-not-recorded", "AC-005", GV,
    "    if timed_out:\n        return \"timeout\"\n", "",
    sel(SVC, k="air6_005_post_failures and review_timeout"))
add("005e-exit0-no-record-is-reviewed", "AC-005", GV,
    "if exit_code != 0 or not has_record:", "if exit_code != 0:",
    sel(SVC, k="air6_005_post_failures and review_no_record"))
# ── AC-014 서비스 몫 ──
add("014i-keep-planted-audit", "AC-014", GV,
    "        (job_dir / AUDIT_REVIEW_NAME).unlink(missing_ok=True)\n", "",
    sel(SVC, k="air6_014_service_planted"))
add("014j-keep-planted-final", "AC-014", GV,
    "        elif final.exists():\n            shutil.rmtree(final)", "        elif final.exists():\n            pass",
    sel(SVC, k="air6_014_service_planted"))
add("014k-ignore-delete-failure", "AC-014", GV,
    "    if not cleaned:\n        return start", "    if False:\n        return start",
    sel(SVC, k="air6_014_service_delete or air6_014_13"))
add("014m-delete-failure-no-start-values", "AC-014", GV,
    "    hashes = _measure_draft(job_dir)\n    snapshot = measure_screens(job_dir)\n    index = _load_json_object(job_dir / \"screens\" / \"index.json\")",
    "    hashes = _measure_draft(job_dir) if cleaned else {\"input\": None, \"preview\": None}\n    snapshot = measure_screens(job_dir) if cleaned else {\"index_sha256\": None, \"files\": {}}\n    index = _load_json_object(job_dir / \"screens\" / \"index.json\")",
    sel(SVC, k="air6_014_13"))
add("014-select-planted", "AC-014", JS.replace("goose_job_service", "goose_runner"),
    "            if admissible:\n                return \"final\", final_dir", "            if True:\n                return \"final\", final_dir",
    sel(REV, k="air6_014_select_report_planted"))
# ── AC-015 S9 ──
add("015f-keep-session-receipt-on-failure", "AC-015", GV,
    "        path.parent.mkdir(parents=True, exist_ok=True)\n        _remove(path)\n        tmp.write_text",
    "        path.parent.mkdir(parents=True, exist_ok=True)\n        tmp.write_text",
    sel(SVC, k="air6_015_s9a"))
add("015f2-no-removal-retry", "AC-015", GV,
    "        try:\n            _remove(path)  # 제거 재시도 — 세션이 쓴 영수증을 남기지 않는다\n        except OSError:\n            pass\n",
    "",
    sel(SVC, k="air6_015_s9a"))
add("015g-event-skips-receipt-block", "AC-015", JS,
    "        if post.receipt_blocked:\n            return \"draft\"\n", "",
    sel(SVC, k="air6_015_s9b"))
# ── AC-016 select_report 몫 ──
add("016n-no-condition0", "AC-016", GR,
    "        if allowed:\n            # 조건 0", "        if True:\n            # 조건 0",
    sel(RUN, REV, k="select_report_rules or condition0"))
add("016-select-skips-admissibility", "AC-016", GR,
    "            if admissible:\n                return \"final\", final_dir", "            if True:\n                return \"final\", final_dir",
    sel(REV, k="air6_016_select_report"))
add("016-select-no-receipt-regression", "AC-016", GR,
    "            admissible, reasons = goose_review.evaluate_admissibility(job_dir)",
    "            admissible, reasons = True, [\"x\"]",
    sel(RUN, k="select_report_rules"))
for cond, reason in [
    ("1", "no_receipt"), ("2", "receipt_invalid"), ("3", "review_not_completed"),
    ("4", "judged_input_write_attempt"), ("5", "screens_not_complete"), ("6", "screens_changed"),
    ("7", "tile_missing"), ("8", "tile_hash_mismatch"), ("9", "draft_changed"),
    ("10", "preview_hash_mismatch"), ("11", "tile_not_read"), ("12", "mobile_overflow"),
    ("13", "no_audit_review"), ("14", "mode_not_separate_review_pass"), ("15", "visual_not_pass"),
    ("16", "reviewed_before_capture"), ("17", "font_note_missing"),
]:
    add(f"016c{cond}-{reason}", "AC-016", GV, f'reasons.append("{reason}")', "pass",
        sel(REV, k="air6_016_select_report_pre or air6_016_select_report_post"))
# ── AC-020 ──
add("020a-stale-runner-value", "AC-020", JS,
    "data = {**extra, \"delivery_status\": status}", "data = {\"delivery_status\": result.delivery_status, **extra}",
    sel(SVC, k="air6_020_2 or air6_020_3"))
add("020b-no-recompute", "AC-020", JS,
    "        selected = await asyncio.to_thread(goose_runner.select_report, self._runs_root() / job.job_id)\n        return selected[0] if selected else None",
    "        return \"draft\"",
    sel(SVC, k="air6_020_2 or air6_020_3"))
add("020d-recompute-when-switch-off", "AC-020", JS,
    "                await self._write_outcome_receipt(job_dir, harness_dir, \"disabled\")\n                return post",
    "                await self._write_outcome_receipt(job_dir, harness_dir, \"disabled\")\n                post.launched = True\n                return post",
    sel(SVC, k="air6_020_5"))
add("020e-recompute-when-integrity-fails", "AC-020", JS,
    "                await self._write_outcome_receipt(job_dir, harness_dir, \"integrity_failed\")\n                return post",
    "                await self._write_outcome_receipt(job_dir, harness_dir, \"integrity_failed\")\n                post.launched = True\n                return post",
    sel(SVC, k="air6_020_6"))
# ── AC-022 ──
add("022a-context-wrong-preview-hash", "AC-022", GV,
    "            \"preview_sha256\": hashes[\"preview\"],\n            \"reviewed_at\": stamp,",
    "            \"preview_sha256\": \"0\" * 64,\n            \"reviewed_at\": stamp,",
    sel(SVC, k="air6_022_admissible"))
add("022b-context-wrong-input-hash", "AC-022", GV,
    "            \"input_sha256\": hashes[\"input\"],\n            \"preview_sha256\": hashes[\"preview\"],\n            \"reviewed_at\": stamp,",
    "            \"input_sha256\": \"0\" * 64,\n            \"preview_sha256\": hashes[\"preview\"],\n            \"reviewed_at\": stamp,",
    sel(SVC, k="air6_022_admissible"))
add("022c-context-reviewed-at-before-cutoff", "AC-022", GV,
    "            \"reviewed_at\": stamp,\n            \"mode\": REVIEW_MODE,",
    "            \"reviewed_at\": \"2000-01-01T00:00:00+09:00\",\n            \"mode\": REVIEW_MODE,",
    sel(SVC, k="air6_022_admissible"))
add("022d-context-wrong-mode", "AC-022", GV,
    "            \"reviewed_at\": stamp,\n            \"mode\": REVIEW_MODE,",
    "            \"reviewed_at\": stamp,\n            \"mode\": \"independent_agent_x\",",
    sel(SVC, k="air6_022_admissible"))
add("022e-control-tile-condition-removed", "AC-022", GV,
    'reasons.append("tile_not_read")', "pass",
    sel(SVC, k="air6_022_control"))
add("022f-no-render-final-relay", "AC-022", JS,
    "                render_final_sent = True\n", "                render_final_sent = True\n                return\n",
    sel(SVC, k="air6_022_admissible"))
# ── 프런트 ──
FE_STAGES = "frontend/src/utils/gooseJob.ts"
add("003a-frontend-stages-missing", "AC-003", FE_STAGES,
    "  'screenshot', // SPEC-AI-REPORT-006: 1차 세션 뒤 서버 후처리(화면 캡처 → 감수 → 최종본)\n  'review',\n", "",
    ("node", ["vitest", "run", "--root", str(W / "frontend"), "src/utils/__tests__/gooseJob.test.ts",
              "src/components/__tests__/ProgressPanel.test.tsx"]))
add("003e-frontend-render-final-before-session-end", "AC-003", FE_STAGES,
    "  'session_end',\n  'screenshot',", "  'render_final',\n  'screenshot',",
    ("node", ["vitest", "run", "--root", str(W / "frontend"), "src/utils/__tests__/gooseJob.test.ts",
              "src/components/__tests__/ProgressPanel.test.tsx"]))
FE_PANEL = "frontend/src/components/ProgressPanel.tsx"
add("003h-frontend-label-missing", "AC-003", FE_PANEL,
    "  screenshot: '화면 캡처',\n  review: '감수',\n", "  screenshot: '',\n  review: '',\n",
    ("node", ["vitest", "run", "--root", str(W / "frontend"), "src/components/__tests__/ProgressPanel.test.tsx"]))


# ── 1차 실행에서 STILL-GREEN이던 세 변이를 AC 문구(두 겹 보호 모두 제거)대로 다시 만든다 ──
add("005c-review-exception-propagates-both-layers", "AC-005", JS,
    [("        except Exception:  # noqa: BLE001 - 감수 실패는 영수증(review_failed)으로 남기고 초안으로 끝낸다", "        except ZeroDivisionError:  # mutated"),
     ("        except Exception:  # noqa: BLE001 - fail-open: 후처리의 어떤 실패도 작업을 error로 만들지 않는다", "        except ZeroDivisionError:  # mutated")],
    None, sel(SVC, k="air6_005_post_failures and review_raises"))
add("014k-launch-despite-delete-failure", "AC-014", GV,
    "start = ReviewStart(job_id, stamp, cleaned, hashes, snapshot, tiles)", "start = ReviewStart(job_id, stamp, True, hashes, snapshot, tiles)",
    sel(SVC, k="air6_014_service_delete or air6_014_13"))
add("015f-keep-session-receipt-both-removals", "AC-015", GV,
    [("        path.parent.mkdir(parents=True, exist_ok=True)\n        _remove(path)\n        tmp.write_text", "        path.parent.mkdir(parents=True, exist_ok=True)\n        tmp.write_text"),
     ("        try:\n            _remove(path)  # 제거 재시도 — 세션이 쓴 영수증을 남기지 않는다\n        except OSError:\n            pass\n", "")],
    None, sel(SVC, k="air6_015_s9a"))


def sha(path):
    return hashlib.sha256((W / path).read_bytes()).hexdigest()


def main():
    only = sys.argv[1:]
    touched = sorted({m[2] for m in M})
    before = {p: sha(p) for p in touched}
    summary = []
    for mid, ac, path, old, new, (kind, args) in M:
        if only and not any(mid.startswith(o) for o in only):
            continue
        full = W / path
        original = full.read_text(encoding="utf-8")
        pairs = old if isinstance(old, list) else [(old, new)]
        mutated = original
        bad = [o for o, _ in pairs if mutated.count(o) != 1]
        if bad:
            print(f"{mid}: NOT-APPLIED (old string count != 1)")
            summary.append((mid, ac, "NOT-APPLIED"))
            continue
        for o, nw in pairs:
            mutated = mutated.replace(o, nw)
        try:
            full.write_text(mutated, encoding="utf-8")
            cmd = [PY if kind == "py" else NODE, *args]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            lines = [ln for ln in (proc.stdout + proc.stderr).splitlines() if ln.strip()]
            tail = [ln for ln in lines if " passed" in ln or " failed" in ln or "Tests " in ln][-1:] or lines[-1:]
            verdict = "RED" if proc.returncode != 0 else "STILL-GREEN"
            print(f"{mid} [{ac}] {verdict} rc={proc.returncode} | {' '.join(tail)}")
            summary.append((mid, ac, verdict))
        finally:
            full.write_text(original, encoding="utf-8")
    after = {p: sha(p) for p in touched}
    print("restored-sha-match:", before == after)
    print("RED:", sum(1 for s in summary if s[2] == "RED"), "STILL-GREEN:",
          [s[0] for s in summary if s[2] == "STILL-GREEN"], "NOT-APPLIED:",
          [s[0] for s in summary if s[2] == "NOT-APPLIED"])


main()
