# SPEC Delta Review: SPEC-AI-REPORT-006 v0.3.1 (commit ed8857e vs 0c4b2c4)
Iteration: 3/3 (delta check of the iter-3 conditions, not a full re-audit)
Verdict: PASS-WITH-DEBT. N11 and N12 (the kickoff conditions) are closed. N13, N14, N15, N16 step 2 are closed. One new SHOULD-FIX (N17) in the N13 deletion-failure case. No BLOCKING defect, no must-pass failure.
Overall Score: 0.91 (iter 3 was 0.90; no regression, no STOP signal)
Kickoff: MAY PROCEED. N17 is a one-sentence patch recommended before kickoff; if left, it is accepted debt that AC-014 (13) will force into the open at the first M3 RED test.

Reasoning context ignored per M1 Context Isolation. No SPEC file was modified. The live goose harness was not run. Audit model is Claude-only. The Grep and Glob tools are unavailable in this session, so I used Bash grep/sed. The only file I created besides this report is the probe script `.moai/state/verify/t18-plan3/delta_trace.py` (git-ignored path).

## Plain summary
The two conditions I set last time are fixed. The list of checks that are skipped when the screen index cannot be read now includes check 16 in all three places, and the receipt writer now calls the check logic with the facts it just measured, while the selection step reads the saved receipt from disk. The new pre-session deletion of a planted review record and a planted final folder is written consistently in the requirement, the design flow, the failure table, the threat table and the acceptance cases, and each new case has a reversal variant that really flips the outcome. I walked cases 11, 12 and 13 against the skip rules by hand. Cases 11 and 12 give exactly the lists the AC states. Case 13 only gives its stated list if the receipt already holds start measurements, and the design takes those measurements after the deletion step, which is the step that failed in that case. That is a small gap, safe in outcome (delivery is `draft` either way), and it is the only new defect.

## Must-Pass Results
- [PASS] MP-1: REQ-AIR6-001..020 sequential, AC-AIR6-001..022 sequential (probe output below).
- [PASS] MP-2 (judged on REQ entries in spec.md, not on ACs): REQ-014/015/016/020 grew longer but remain well-formed "shall" sentences; no informal wording added.
- [PASS, SSOT part still UNVERIFIED] MP-3: spec.md:4 `version: "0.3.1"` (quoted); other frontmatter fields unchanged from iter 3. `spec-frontmatter-schema.md` is still absent in this worktree (carried debt D13).
- [N/A] MP-4: single-feature Python backend SPEC.
- [PASS] MP-5 (D7): the diff adds no new SPEC-ID reference (probe: only the existing 004/005/TEST-HERMETIC references; plan.md:68 names 007 as before, unchanged text on that point).
- [PASS] MP-6 (D8): `grep -rn syscall` over the SPEC directory returned nothing.
- [PASS] MP-7: `grep -rn 'NEEDS CLARIFICATION' plan.md research.md` returned nothing.

## 1. N11 closed: YES
Condition 16 now appears in the unreadable-index skip list in all three places:
- spec.md:123 REQ-016: "the conditions that depend on the parsed index (7, 8, 11, 12, 16 and the index side of 10)".
- design.md:129 table row: "7, 8, 11, 12, 16과 10의 색인 쪽 (16은 색인의 `finished_at`을 읽는다)".
- acceptance.md:238 AC-016 (d2): "의존 조건 7·8·11·12·16은 보고하지 않음".
Old-list restatement search (`grep -n "7, 8, 11, 12\|7·8·11·12\|7, 8, 11"`) matches exactly those three lines, all with 16. No stale copy. Reversal variant at acceptance.md:259 (drop 16 from the guard list gives `[screens_not_complete, reviewed_before_capture]`, so (d2) is RED) is correct against the fixed order (5 then 16).

## 2. N12 closed: YES
- REQ-015 (spec.md:~120): the writer computes the verdict "by calling the condition core ... with the receipt facts it has just measured passed as an argument ... before it makes the single atomic write".
- REQ-016 (spec.md:123): one condition core takes facts as an argument (absent or unparseable receipt passed as such); the disk wrapper `evaluate_admissibility(job_dir)` reads `review/receipt.json` and calls the core; selection and every re-evaluation call the wrapper; the writer calls the core; `visual_admissible` and `reasons` are passed as placeholders.
- design.md:97 (section 5): same two call forms, "한 번만 원자적으로", placeholders, `select_report`와 재평가는 래퍼.
- acceptance.md:249 AC-016 When plus reversal variants at 258: asserts the core is called while `review/receipt.json` is absent and exactly one final replace on that path; wrapper-in-writer variant gives `[no_receipt]` (RED on (a)).
Placeholder keys do not change condition 2: placeholders keep the fixed keys present, so "carries every fixed key" holds. Condition 1 is satisfied by the facts argument being present. Consistent. Minor looseness only: design.md:10 and acceptance.md:194 still say both callers use "the same function", which is true of the core and does not contradict the new text (MINOR, N18).

## 3. N13 closed: YES, with one new gap (N17)
Rule present and consistent:
- REQ-014 (spec.md:~116): delete `audit-review.json` and `final/` first; on a deletion failure do not launch the session, handle under REQ-005 with outcome `review_failed`; then snapshot in the context.json step.
- design.md flow (lines 22-27) and failure row (line ~42); threat row (line 175: deletion precedes the screens snapshot and context.json).
- acceptance.md (11), (12), (13), (6b) at 158-166 and reversal variants (i)-(l) at 171; the "not caught" text at 172 limits deletion scope to the two files and states the P34 process-group reasoning.
- Reasons reuse existing codes: design table still rows 0..17 (18 conditions), REQ count 20, AC count 22 (probe).

Independent walk of the expected lists against the REQ-016 read-guard rules (conditions evaluated by the writer, 1-17, over in-memory facts):
- Case 11 (planted record deleted; reviewer reads every tile, builds `final/`, writes no `audit-review.json`, exits 0): outcome `review_failed` (REQ-005), so 3 `review_not_completed` unmet. 4 ok (`judged_writes` empty: only `final/` written). 5 ok. 6, 9 ok (start/end taken after deletion, nothing changed). 7, 8 ok. 10: index side equals draft hash; review-record side not evaluated (13 unmet). 11 ok (all tiles read). 12 ok. 13 `no_audit_review` unmet; 14-17 skipped by the guard. Result `[review_not_completed, no_audit_review]`. MATCHES AC. `select_report`: condition 0 passes (`final/` allowed), wrapper reads the same receipt, so the same reasons, `draft`. Variant (i) (no deletion): planted file present, outcome `reviewed`, hashes copied so 10 ok, `mode` ok, `visual: pass`, marker present, future `reviewed_at` passes 16: reasons `[]`, `final`. Really flips (RED).
- Case 12 (planted `final/`; reviewer writes an honest `audit-review.json`, no `final/`): after deletion `final/` absent; outcome `reviewed`; all of 1-17 hold, writer `reasons == []`; `select_report` fails condition 0 (`final_not_allowed`), `draft`. MATCHES. Variant (j) (no `final/` deletion): condition 0 passes, `reasons == []`, `final`. Really flips.
- Case 13 (deletion patched to fail; both planted files remain; reviewer never called): outcome `review_failed`, 3 unmet. 13: planted record exists and parses, so met; 14, 15, 16, 17 and 10 pass because the planted record is well-formed. 11: no tiles read, so `tile_not_read` unmet. 4 ok, 5 ok, 7, 8, 12 ok. For the AC list `[review_not_completed, tile_not_read]` to come out, conditions 6 and 9 must find start measurements equal to now. But the design takes the start snapshot AFTER the deletion step (design.md:27, REQ-014 "shall then record"), and in this case the flow jumps from the failed deletion straight to `review_failed`. See N17. Variant (k) (ignore the failure and start the session): reviewer call count 1, RED. Correct.
- Variant (l) (non-recursive snapshot) against (6b): a disk-only file `screens/sub/a.png` leaves the top-level file list unchanged, so `screens_changed` is absent and, with no stream `Write` record, `final` is chosen; RED. Correct provided the fake reviewer adds the file without a stream `Write` call (the (6) pattern; (7) is the case that names a stream call).

## 4. N14, N15, N16 step 2, and new contradictions
- N14: closed. REQ-014 "set of relative paths of all files under `screens/`, subdirectories included"; condition 6 text (spec.md:129) "recursive set of relative file paths"; design.md:89 `<screens/ 기준 상대 경로>` with `sub/a.png`; AC-014 judged-target sentence (acceptance.md:150) and case (6b). The older phrasing "file-name set" no longer appears in spec/design/acceptance except the WHAT paragraph spec.md:42 ("파일 집합"), which is generic and not contradictory.
- N15: closed. REQ-020 saves canary tiles under the installed harness `runs/<canary>/` and adds the hash-differs and clip-height clause; AC-019 Given (line ~294) and GO item 3 (line ~303) match; research P35 added. Same GO definition in both.
- N16 step 2: closed. plan.md:68 step (2) now lists: acceptance.md (AC-013 #1, catch (a), AC-021 Then), design.md (section 7 heading, `규칙 7·9`), spec.md (section 3 table), plan.md (M5 row), research.md (G13), progress.md if present, plus a grep command. I verified each location by grep: acceptance.md:139, 145, 333; design.md:156, 158; spec.md:71; plan.md:48; research.md:78; progress.md has none. Complete; no additional rule-9 location found (also searched `9번`, `규칙9`, `Rule 9`).
- Versions: spec.md:4, plan.md:3, design.md:3, acceptance.md:3, progress.md:5-8 say 0.3.1; HISTORY row 0.3.1 present (spec.md:27). research.md carries no version string (no change needed). No stale "버전 0.3.0" line (probe).
- Counts: 20 REQ, 22 AC, design rows 0..17 (18), spec conditions 1..17, condition code lists equal between spec and design (probe). The author's trace.py hard-codes 0.3.0 as you said; I did not rely on it.
- Traceability recomputed (probe): every REQ 001..020 covered; every AC cites an existing REQ; AC-019 maps to REQ-020, AC-020 to REQ-019, AC-021 to REQ-013 and 016, AC-022 to REQ-016.

## Category Scores
| Dimension | Score | Band | Evidence |
|---|---|---|---|
| Clarity | 0.85 | minor ambiguity | N17 is the only place two readings differ (spec.md/REQ-014 vs design.md:27 vs AC-014 (13)) |
| Completeness | 0.90 | frontmatter SSOT unchecked | all sections present; D13 carried |
| Testability | 0.90 | binary except (13) list | (13) exact list depends on an unstated rule |
| Traceability | 1.00 | complete | probe: 20/20 REQ covered, 22/22 AC valid |

## Defects Found
N17. Deletion-failure path never takes the start measurements — spec.md REQ-014 (L~116, "and shall then record, in the same step that writes `review/context.json`"), design.md:27 and :42, acceptance.md:166 AC-014 (13) — When the pre-session deletion fails, the flow goes straight to `review_failed` without the snapshot step, yet the receipt has fixed keys for `hashes.input_start`/`preview_start` and `snapshot_start`. Under REQ-016 ("an input it cannot read counts as unmet"; conditions 6 and 9 are guarded only by 1/2) an implementation that leaves them empty reports `[review_not_completed, screens_changed, draft_changed, tile_not_read]`, not the `[review_not_completed, tile_not_read]` that AC-014 (13) demands. Safety is unaffected (delivery is `draft` either way). — Severity: minor-to-major (SHOULD-FIX) — Class: optional for kickoff (the outcome is fail-closed), but the same shape as N11, so patch it if a text edit is cheap — Required fix: one sentence in REQ-014 and design section 2 saying that, when the deletion fails, the service measures the start values (hashes, screens snapshot) at that moment (or before attempting the deletion) and writes them as both start and end into the receipt, so conditions 6 and 9 hold; or, alternatively, change the AC-014 (13) expected list to include the two codes and say why.

N18. Loose wording "same function" — design.md:10 and acceptance.md:194 — both still say the writer and `select_report` "call the same function"; true of the core, imprecise next to the new wrapper/core split. — Severity: minor — Class: optional — Required fix: say "the same condition core" in those two lines when next edited.

## Regression Check (iter 3 defects)
- N11: RESOLVED (three places, probe below).
- N12: RESOLVED (REQ-015, REQ-016, design 97, AC-016 When and variants).
- N13: RESOLVED, with N17 residual in the failure edge.
- N14: RESOLVED. N15: RESOLVED. N16 step 2: RESOLVED; the 007 citations remain UNVERIFIED in this worktree (007 absent), unchanged.

## Recommendation
Proceed to Implementation Kickoff. Optional before kickoff: patch N17 (and N18) in a text-only commit; a grep can confirm it, no re-audit needed. Final accepted-debt list to carry into the run phase: G13 (`final/` origin not verified), G14 (receipt remove/replace double failure), G15 (`audit-review.json` changed after receipt), G11 (changes through the two allowed scripts), D13 (frontmatter SSOT file absent, MP-3 SSOT part unchecked), N8/D11 (verification detail inside REQ-018/020), N16 007 citations (re-cite at merge time), N17 and N18 if not patched, plus the pre-existing note that the Tier L threshold table is not in this worktree.

## Verbatim probe output
```
$ git diff --stat 0c4b2c4 ed8857e
 .moai/specs/SPEC-AI-REPORT-006/acceptance.md | 26 +++++++++++++++++---------
 .moai/specs/SPEC-AI-REPORT-006/design.md     | 14 +++++++++-----
 .moai/specs/SPEC-AI-REPORT-006/plan.md       |  6 +++---
 .moai/specs/SPEC-AI-REPORT-006/progress.md   |  7 ++++---
 .moai/specs/SPEC-AI-REPORT-006/research.md   |  2 ++
 .moai/specs/SPEC-AI-REPORT-006/spec.md       | 13 +++++++------
 6 files changed, 42 insertions(+), 26 deletions(-)

$ git diff --stat 0c4b2c4 ed8857e -- backend frontend pyproject.toml
(empty)

$ git log --oneline -3
ed8857e docs(SPEC-AI-REPORT-006): plan 감사 3차 부채 반영 v0.3.1 (카드 t18)
0c4b2c4 docs(SPEC-AI-REPORT-006): 007 대비 병합 의무 한 줄 반영 (카드 t18)
81f0d30 docs(SPEC-AI-REPORT-006): plan 감사 2차 반영 v0.3.0 (카드 t18)

$ grep -n "7, 8, 11, 12\|7·8·11·12\|7, 8, 11" .moai/specs/SPEC-AI-REPORT-006/*.md   (excerpt, matched fragments)
design.md:129:| 5 (색인) | 색인이 파싱되지 않음 | 7, 8, 11, 12, 16과 10의 색인 쪽 (16은 색인의 `finished_at`을 읽는다) |
acceptance.md:238:| (d2) | ... | `[screens_not_complete]` (예외 없음, 의존 조건 7·8·11·12·16은 보고하지 않음 — 16은 색인의 `finished_at`을 읽는다, iter3 N11) |
spec.md:123:... the conditions that depend on the parsed index (7, 8, 11, 12, 16 and the index side of 10) are neither evaluated nor reported ...

$ grep -rn 'NEEDS CLARIFICATION' plan.md research.md       (no output)
$ grep -rn syscall .moai/specs/SPEC-AI-REPORT-006           (no output)

$ grep -n "규칙 9\|규칙 7·9\|rule 9" .moai/specs/SPEC-AI-REPORT-006/*.md   (locations only)
acceptance.md:139, acceptance.md:145, acceptance.md:333, design.md:156, design.md:158, plan.md:48, plan.md:68 (the merge row itself), research.md:78, spec.md:71; progress.md: none

$ /usr/bin/python3 -I .moai/state/verify/t18-plan3/delta_trace.py .moai/specs/SPEC-AI-REPORT-006
REQ count 20 sequential True
AC count 22 sequential True
AC 001 -> ['001']  ... AC 018 -> ['018']
AC 019 -> ['020']
AC 020 -> ['019']
AC 021 -> ['013', '016']
AC 022 -> ['016']
uncovered REQ: []
invalid REQ cited: []
design table rows ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17'] 18
spec conditions ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17'] 17
code lists equal (spec 1-17 vs design 1-17): True
acceptance.md has 0.3.1: True stale 0.3.0 version line: False
design.md has 0.3.1: True stale 0.3.0 version line: False
plan.md has 0.3.1: True stale 0.3.0 version line: False
progress.md has 0.3.1: True stale 0.3.0 version line: False
research.md has 0.3.1: False stale 0.3.0 version line: False
spec.md has 0.3.1: True stale 0.3.0 version line: False
```
(AC 001-018 lines abbreviated above; each printed one-to-one `AC nnn -> ['nnn']`.) Not re-run: code and harness probes P1-P33 (the diff stat shows no code change; the two new probes P34, P35 in research.md were not re-executed by me and are cited from the SPEC).
