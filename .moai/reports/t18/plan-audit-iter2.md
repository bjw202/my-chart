# SPEC Review Report: SPEC-AI-REPORT-006
Iteration: 2/3
Verdict: FAIL (no must-pass gate failed; two blocking internal-consistency defects, N1 and N2, remain, plus one stated-criterion overstatement, N3)
Overall Score: 0.85 (iteration 1 was 0.76, so there is no regression and no STOP signal. The Tier L threshold table is not present in this worktree's spec-workflow.md, `grep -n -i tier` returned nothing, so the threshold comparison is UNVERIFIED. The verdict does not depend on it.)

Reasoning context ignored per M1 Context Isolation. Only the six SPEC artifacts at commit 86b7c0d, the code they cite, and the prior report were used. No SPEC file was modified. Scratch scripts live in the git-ignored `.moai/state/verify/t18-audit2/`. The live goose harness was not run. Audit model is Claude-only: `grep -rn audit_model .moai/config/` returned nothing.

## Plain summary
The revision fixed most of what iteration 1 found. Both open clarification markers are gone, the screens-tampering hole is closed by a start/end snapshot plus a Write/Edit call record, there is now one admissibility function, and the M1 gate and the delivery-status owner are defined. I re-ran the probes the revision cites and they all matched. The requirement-to-acceptance mapping is complete (computed, 20 of 20). Three things still block a PASS. First, AC-018 contradicts itself about whether a missing `[렌더 차이]` marker fails the live gate. Second, REQ-020 and AC-019 define "GO" differently. Third, AC-016 promises a separate reversal test for each of its 18 conditions, but several conditions are redundant with a neighbour, so that promise cannot be met as written. All three are small text fixes.

## Must-Pass Results
- [PASS] MP-1 REQ numbering. Computed by `trace.py`: `REQ count 20 sequential no gaps: True`. IDs are `REQ-AIR6-001` to `REQ-AIR6-020` (spec.md:85-151) with consistent zero-padding.
- [PASS] MP-2 GEARS compliance, judged on the requirement layer (`REQ-XXX` in spec.md), not on the ACs. Every REQ is a Where/When/shall or "The X shall" sentence. REQ-018 (spec.md:147) and REQ-020 (spec.md:151) read like verification procedures but are grammatical `When … shall`; see N8. REQ-016 (spec.md:121) is a very long compound, but it is well-formed.
- [PASS, SSOT part UNVERIFIED] MP-3 frontmatter (spec.md:1-16). id, title, version `"0.2.0"` (quoted), status `draft`, created, updated, author, priority `High`, phase, module, lifecycle `spec-anchored`, tags (comma string) are present and typed correctly. `tier` and `related_specs` are extras. `ls .claude/rules/moai/development/` shows only `agent-authoring.md coding-standards.md model-policy.md skill-authoring.md`, so `spec-frontmatter-schema.md` is still absent and the check was made against the 12-field list in the charter (D13).
- [N/A] MP-4 language neutrality. Single-feature Python backend SPEC.
- [PASS] MP-5 D7 cross-SPEC. SPEC IDs referenced in spec.md: `SPEC-AI-REPORT-004`, `SPEC-AI-REPORT-005`, `SPEC-AI-REPORT-006` (self). Observed `status: completed` for 004 and 005. `SPEC-TEST-HERMETIC-001` (referenced in other artifacts) is also `completed`. None is retired, superseded, or archived.
- [PASS] MP-6 D8 cross-platform. `grep -n syscall .moai/specs/SPEC-AI-REPORT-006/*.md` returned no match (rc=1).
- [PASS] MP-7 clarification gate. `grep -rn 'NEEDS CLARIFICATION' plan.md research.md` returned no match (rc=1). Iteration 1 had two open markers.

## Category Scores
| Dimension | Score | Band | Evidence |
|---|---|---|---|
| Clarity | 0.75 | minor ambiguity | REQ-020 (spec.md:151) and AC-019 (acceptance.md:258-263) define GO differently (N2). Design §5 puts `final_not_allowed` in the function's table (design.md:100) while REQ-016 evaluates only 17 conditions (N7). |
| Completeness | 0.90 | frontmatter SSOT unchecked | HISTORY (spec.md:20), §1 overview, §3 scope, §4 REQ, AC set, and Out of Scope with five H3 groups and `-` bullets (spec.md:155-172) are all present. D13 is still open. |
| Testability | 0.75 | mostly binary | All 22 ACs carry both a "잡는 구현" and a "잡지 못하는 것" line (computed). AC-016 promises 18 individual reversals that are partly unattainable (N3). AC-018 has a gating/non-gating contradiction (N1). AC-020 mutation (d) cannot be observed (N6). |
| Traceability | 1.00 | complete | Computed: no uncovered REQ, no AC with a missing or invalid REQ; table below. |

REQ to AC mapping (output of `trace.py`): 001..012 map 1:1 to AC-001..012; REQ-013 to AC-013 and AC-021; REQ-014 to AC-014; REQ-015 to AC-015; REQ-016 to AC-016, AC-021, AC-022; REQ-017 to AC-017; REQ-018 to AC-018; REQ-019 to AC-020 and AC-022; REQ-020 to AC-019. `uncovered REQ: []`, `AC with missing/invalid REQ: []`.

## D1-D14 regression table
| ID | Status | Evidence |
|---|---|---|
| D1 MP-7 markers | Verified fixed | Grep returns nothing (rc=1). Decisions recorded at spec.md:54 (D7), plan.md:33 (T9), progress.md:10. Consequences carried into REQ-009/010 (spec.md:103-105), AC-009/010, Out of Scope (spec.md:170-171). The operator's decision itself is cited as "칸반 리드 경유"; I cannot verify that exchange from the artifacts (taken as stated). |
| D2 screens not integrity-checked | Verified fixed, residual Gap G11 plus N4/N5 | Snapshot of draft, input, index, every tile, and the file-name set before the session in the same step as `context.json` (REQ-014, spec.md:115); end snapshot and `judged_writes` from the stream (REQ-015, spec.md:119); conditions 4 and 6 (spec.md:126-128). AC-014 has nine scenarios, including forged index (4), tile swap (5), added file (6), restore-after-edit (7), blocked write (8), and a no-false-positive control (9) (acceptance.md:152-163). |
| D3 two condition lists | Verified fixed for consistency; reversal claim partially (see N3) | One function `evaluate_admissibility` (spec.md:121, design.md:94). `REQ-016 numbered conditions: 17`, design table rows 18 (0-17), and the order matches (`REQ order == design order (excluding #0): True`). AC-016 has one case per condition, and every reason code appears in acceptance.md (counts 2-8). The three previously uncovered conditions now have cases (m), (g3)/tile_missing, (k). |
| D4 M1 gate | Partially fixed | REQ-020 and AC-019 give a canary-token GO with a defined NO-GO path (no M2-M6 merge, record in progress.md, return to plan; acceptance.md:264). But the GO criterion differs between the two documents (N2). |
| D5 tile cap | Verified fixed | Cap 30 = 1.5 x 20 (spec.md:101, research.md P26). Re-run: see probe 5, 20 mobile tiles for the heaviest draft. Boundary cases in AC-008 (acceptance.md:95). |
| D6 honest negative unclosable | Verified fixed, with a side effect (N1) | REQ-013 now says a defective check is `revise` plus an `open` issue (spec.md:113); design §7 rule 9(d); AC-018 item 4 gates on record well-formedness only (acceptance.md:243). |
| D7 receipt-to-final path unobserved | Verified fixed with a declared Gap | AC-022 (acceptance.md:289-298) uses the real `audit_report.py` and `render_report.py --final`. Probes 6 and 7 re-ran and matched. The date-rewriting builder is unobserved (research G10) and AC-022 declares the fallback. |
| D8 done-event status owner | Verified fixed | REQ-019 (spec.md:149), design §2 (design.md:31), plan T14, AC-020. Code citation re-checked: `goose_job_service.py:270` `data = {"delivery_status": result.delivery_status, **extra}` and `goose_runner.py:476` (probe 9). Mutation (d) of AC-020 is weak (N6). |
| D9 unprobed prose claims | Verified fixed | P10 now records `{'ABSENT': 33, False: 4, True: 3}` (probe 3 matches). P23 and P24 re-ran (probes 6, 7). P29 `<script` count 0 (probe 8). The P16 generalization is restated per draft. |
| D10 AC-018 variance and midnight | Verified fixed | Explicit pass rule (acceptance.md:235); midnight recorded as non-gating (acceptance.md:246, plan.md:62). |
| D11 REQ-018 reads as a scenario | Partially fixed (MINOR) | REQ-018 (spec.md:147) now defers the pass rule to AC-018 but still names stock `020150`, a defect-code list, and a restart precondition. See N8. |
| D12 compound requirements | Rejected by the author. Acceptable | Iteration 1 required no fix (class optional). No rejection reason appears in the artifacts (grep for D12, compound, 복합 found nothing); the reason exists only in the invocation. |
| D13 SSOT file absent | Still pending, unchanged | Probe 10. MP-3 SSOT portion stays UNVERIFIED. |
| D14 AC-005 missing case | Verified fixed | AC-005 now lists "종료 0인데 `audit-review.json` 없음" with outcome `review_failed` and reason `no_audit_review` (acceptance.md:64, 66, 68). |

## Defects Found

N1. AC-018 contradicts itself on the `[렌더 차이]` marker — acceptance.md:235, 244, 246, 247, 249 — Item 5 must hold in every run (pass rule, L235). Item 5(i) fails when `visual: pass` is recorded but `visual_admissible` is false, and 5(iv) requires the evidence to start with `[렌더 차이]` (L244). A session that records an honest pass but omits the marker therefore produces `font_note_missing` (condition 17), so 5(i) and 5(iv) both fail and the gate fails. Yet L246 lists the frequency of `font_note_missing` from a missing marker as non-gating, and L249 lists the "pass without opening tiles" case as 5(i) failing but "classified as instruction non-compliance", while L247 says any item-5 violation is "규칙 7 불변식 결함(최우선)". The same event is therefore both gating and non-gating, and both a top-priority invariant defect and an instruction miss. Also 5(iv) says "begins with" while condition 17 and AC-021 case (2) accept "contains". — Severity: major — Class: blocking (internal consistency of a stated criterion) — Required fix: split item 5. Keep 5(ii) (not admissible implies draft) and 5(iii) as the safety invariant for every run. Move 5(i) and 5(iv) to the non-gating record, or make them gating and delete the L246 non-gating clause. Align the L247 classification so that only 5(ii)/(iii) failures count as "rule 7 invariant defect". Make 5(iv) say "contains" to match condition 17.

N2. M1 GO criterion differs between REQ-020 and AC-019 — spec.md:151 vs acceptance.md:256-263 — REQ-020: the reply must quote the token "exactly for every canary tile", the canary PNG is "captured by the screenshotter pipeline" (not built until M2), and the stream must show a `Read` per tile. AC-019: GO requires only the two body-size tokens (가), one per viewport (L259); the smaller-size tokens (나) are measured only for a legibility threshold (L262); the capture may come from "캡처 모듈 경로(또는 M1 스파이크 스크립트가 같은 CDP 호출)" (L256). Under REQ-020 a misread smaller token is NO-GO, and under AC-019 it is GO. M1 is a gate that precedes the capture module, so the REQ-020 wording is also unexecutable. AC-019 item 5 (cap at least 1.5 x max tiles, else re-delegate) is not stated as GO or NO-GO. This is exactly the binary-gate property D4 asked for. — Severity: major — Class: blocking — Required fix: make REQ-020 and AC-019 one definition. Suggested: GO = body-size tokens for both viewports quoted exactly, one at `y > 0`, matching `Read` pairs with error flag false or absent. Smaller sizes only feed the recorded threshold. Allow "capture pipeline or an equivalent spike script". State whether item 5 failure is NO-GO or an adjust-and-continue.

N3. AC-016 and §E promise a per-condition reversal that is not attainable for redundant conditions — acceptance.md:202, 204, 209, 219, 325 — The text says removing one condition's check must turn exactly its own case into `final`. Several conditions are covered by a neighbour, so removing the check changes nothing:
 - `screens_changed` (6) for case (g) and (g3): the same fault is caught by `tile_hash_mismatch` (8) and `tile_missing` (7). Only case (s) isolates condition 6.
 - `draft_changed` (9) for case (k): a changed `draft/report.html` is also caught by `preview_hash_mismatch` (10) because the index hash no longer equals it. Only a `report-input.json` change isolates condition 9.
 - `tile_missing` (7): the "deleted before receipt writing" variant (L202) is ambiguous. If deleted during the session, condition 6 fires first. If deleted before the start snapshot, condition 8's behaviour on a missing file decides whether 7 is isolable.
 - `no_audit_review` (13) and `no_receipt` (1)/`receipt_invalid` (2): a missing file also trips later reads (10, 14, 15; 2) unless the implementation guards each read.
 §E (L325) says each of the 18 is observed individually, while L3 allows Gaps for unobserved reversals; the two sentences conflict. — Severity: major — Class: blocking for the wording (a stated criterion cannot be met as written) — Required fix: for each condition name the one case that isolates it (use `report-input.json` for condition 9, a pre-snapshot deletion for 7, and say that 8 handles a missing file as a mismatch so 7 is isolated only by an implementation that guards 8), or restate the criterion as "every condition has a case that fails when its check is removed, or a recorded Gap naming the covering condition".

N4. Provenance of `final/` is not verified by the admissibility function — spec.md:121, design.md:94-119, plan.md:35 — Condition 0 accepts any regular `final/report.html` with `render-validation.json{delivery_allowed: true}`, and the review session holds `Write(./runs/**)`. REQ-014 protects only `draft/` and `screens/`. A session that really opened every tile and recorded an honest `revise` on another check (so the audit decision is `revise` and `--final` must not run) can still `Write` both `final/` files by hand and be admitted: conditions 1-17 only concern the visual evidence. Rule 7 itself holds (the visual pass is real), but D6's change makes honest negatives common, which raises the incentive. — Severity: minor — Class: optional — Required fix: add a condition that `final/delivery-audit.json` exists with `decision == "pass"` and its `preview_sha256` equals the current `draft/report.html` hash, or record it as a Gap next to G11.

N5. A session-written receipt survives if the server's overwrite fails — spec.md:119, design.md:42 — The failure row says "영수증 쓰기 실패 → draft (영수증 없음 = final 불가)", assuming no receipt exists. The session can write `review/receipt.json` (AC-015 S7). The function reads the receipt's `tiles_read`, snapshots, and `outcome` as trusted server facts. Forging it needs the SHA-256 of `index.json`, which the session cannot compute, so exploitation is impractical today, but the safety rests on that, not on a rule. — Severity: minor — Class: optional — Required fix: on receipt-write failure, delete or rename any existing `review/receipt.json` and treat the job as `draft`; add the case to AC-015.

N6. AC-020 mutation (d) cannot go RED — acceptance.md:271, 273, 275 — Scenario (5) uses the common fake runner that returns `"draft"`. A mutation that recomputes under switch 0 also returns `draft` (no receipt admits it), so the two values are identical. — Severity: minor — Class: optional — Required fix: in scenario (5) have the fake runner return a value different from the recomputed one (for example `"final"` from a stub), so that recomputing is detectable.

N7. `final_not_allowed` placement is ambiguous — spec.md:121 vs design.md:100,119 vs acceptance.md:187,194,217 — REQ-016 says the function evaluates 17 conditions and `final_not_allowed` is the "existing condition" checked by selection. Design §5 lists it as row #0 of the function table and says the receipt writer evaluates only 1-17. AC-016 says the function has "조건 18개" and case (n) calls `evaluate_admissibility`. — Severity: minor — Class: optional — Required fix: one sentence stating that `evaluate_admissibility` implements 1-17 and `select_report` adds #0, and have AC-016 call the right function for (n).

N8. Verification detail inside the requirement layer — spec.md:147, 151 — REQ-018 still names stock `020150` and a defect-code list (D11 partly fixed); REQ-020 embeds the canary procedure. They are valid `When … shall` sentences, so MP-2 stands. — Severity: minor — Class: optional — Required fix: none required; move the procedure to AC-018/AC-019 when N2 is fixed.

N9. REQ-001's "byte-for-byte" claim conflicts with REQ-016 — spec.md:85 vs 141 — A service with neither screenshotter nor reviewer injected is said to keep the pre-SPEC behavior byte-for-byte, but `select_report` now returns `draft` for any `final/` without a receipt ("Without a receipt no report is `final`"). spec.md:75 acknowledges updating existing tests. — Severity: minor — Class: optional — Required fix: say the claim covers the job flow and events, not report selection.

N10. Smaller items (all optional, MINOR):
 (a) AC-017 is assigned to no milestone in plan.md:44-49 (it is cross-cutting).
 (b) Decision IDs D1-D10 in spec.md:46-57 collide with the plan-audit defect IDs D1-D14 (spec D9 cites "plan-audit D3"), which is confusing to read.
 (c) design.md:130 normalizes paths with `normpath`; on case-insensitive macOS a `Screens/` variant would evade the `judged_writes` match. The snapshot still catches any persistent change, so rule 7 is not affected; use a case-folded comparison as defense in depth.
 (d) The receipt records `audit_review.sha256`, but no condition compares it with the file at decision time.
 (e) M1 records Read latency (acceptance.md:262) but defines no threshold tying it to the 900 s budget for the 33 tiles of the gating stock (research G5).

## Attack findings (the five areas requested)

(a) Can the session still defeat rule 7? Under a tool-using adversary the visual-pass invariant holds. Traced routes:
 - Writing screens via `Write`/`Edit`: recorded as `judged_writes` (condition 4) and, if persistent, caught by the start/end/now snapshot (condition 6).
 - Writing via the two allowed Bash scripts (`render_report.py --output-dir …/screens`, `audit_report.py --output …`): new or changed files change the snapshot, and a change-and-restore leaves the end state identical to the start state, which grants nothing. This is G11; the SPEC admits it (spec.md:158, design.md:121).
 - Symlinks: the session has no tool that creates one; tiles are written by the server.
 - Swapping tile files with identical hashes: identical bytes, no effect.
 - Timestamps: `reviewed_at` is copied from `context.now`, taken after capture (condition 16, audit `AUDIT_TIME` at audit_report.py:98-99).
 - Forged receipt: overwritten after the session (spec.md:119); only the failure path is open (N5).
 - Not covered by the 18 conditions: provenance of `final/` itself (N4), and the case-insensitive path gap (N10c, which does not affect the invariant).
 The honest limit is that a session can open every tile and still not look; the SPEC states this (spec.md:158, acceptance.md:250).

(b) Reversal probes and "cannot catch" lines (lessons #9/#10): all 22 ACs have both lines (computed, 22 of 22 true/true). Quality gaps: N3 (AC-016), N6 (AC-020), AC-013 #1 is phrase presence (self-labelled weak, acceptance.md:146), AC-017 has only the network-guard reversal. Prose claims now have probes (P23-P31); I re-ran P10, P23-P26, P28-P29.

(c) REQ to AC traceability: computed, 20 of 20 covered, 22 of 22 ACs trace to valid REQs (see table above).

(d) M1 GO/NO-GO: a real gate with a defined NO-GO path (acceptance.md:264, plan.md:44), but with the two defects in N2.

(e) New inconsistencies introduced by the revision: N1, N2, N3, N7, N9, N10. Counts agree: 20 REQ and 22 AC in the HISTORY row (spec.md:25), progress.md:8, and the computed totals. Condition numbering agrees between spec.md and design.md (computed). The 30-tile cap agrees across spec.md:101, design.md:59, acceptance.md:91, research P26, and plan.md:61.

## Probes re-run (verbatim output)

Worktree: `/Users/byunjungwon/Dev/my-project-01/my_chart/.claude/worktrees/t18`. `PY` = `/Users/byunjungwon/Dev/my_chart/.venv/bin/python` (Python 3.13.11).

Probe 1 (P17 baseline), MATCH:
```
$ PY -m pytest backend/tests -k goose -q -p no:cacheprovider
267 passed, 214 deselected, 1 warning in 16.32s
```

Probe 2 (P6/P7 permissions hash and manifest), MATCH:
```
e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3  backend/goose_harness_src/claude-settings.json
MANIFEST_BYTE_IDENTICAL          (PY -m backend.services.goose_harness | cmp with goose-manifest.json)
$ git diff --stat 7abdcac HEAD -- backend/goose_harness_src backend/services frontend backend/tests pyproject.toml
(empty: no code or harness change since the pre-SPEC base; the SPEC commits touch only .moai/)
```

Probe 3 (P10 stream fixture), MATCH (my first script crashed on a string `message`; the corrected one printed this):
```
{'ABSENT': 33, False: 4, True: 3}
{'Read': 6, 'ToolSearch': 1, 'Bash': 5, 'WebSearch': 4, 'Agent': 3, 'WebFetch': 18, 'Write': 2, 'Edit': 1}
[('Write', True), ('Write', True), ('Edit', True)]
```

Probe 4 (P23/P24 search channel and audit decision), MATCH:
```
$ /usr/bin/python3 -I .moai/state/verify/t18-plan2/search_channel_probe.py
cutoff 2026-10-21T13:15:00+09:00 mode current
search dart read 2026-10-21T13:10:00.391+09:00
search original_news read 2026-10-21T13:11:00+09:00
search original_news read 2026-10-21T13:11:40+09:00
search original_news read 2026-10-21T13:11:00+09:00
search industry read 2026-10-21T13:11:30+09:00
search company_ir read 2026-10-21T13:13:30+09:00
search naver blocked 2026-10-21T13:13:00+09:00
live-as-is    revise ['LATEST_SEARCH_NAVER']
patched-naver pass []
```

Probe 5 (P26 heights, all four historical drafts, network blocked and script off), MATCH:
```
$ PY -I .moai/state/verify/t18-audit/heights_probe.py
drafts 4
1d261a37 917991 desktop {'sw': 1280, 'cw': 1280, 'sh': 9807} tiles 7
1d261a37 917991 mobile {'sw': 390, 'cw': 390, 'sh': 15047} tiles 10
5695985a 915909 desktop {'sw': 1280, 'cw': 1280, 'sh': 9053} tiles 6
5695985a 915909 mobile {'sw': 390, 'cw': 390, 'sh': 14169} tiles 10
a5becbb9 1043346 desktop {'sw': 1280, 'cw': 1280, 'sh': 20160} tiles 13
a5becbb9 1043346 mobile {'sw': 390, 'cw': 390, 'sh': 30803} tiles 20
d0a64dfc 943631 desktop {'sw': 1280, 'cw': 1280, 'sh': 12066} tiles 8
d0a64dfc 943631 mobile {'sw': 390, 'cw': 390, 'sh': 18797} tiles 12
```
Cap check: 20 x 1.5 = 30, equal to `TILE_CAP`. The cap has headroom of 10 tiles on the heaviest mobile draft.

Probe 6 (P25 final path with the real renderer), MATCH:
```
$ /usr/bin/python3 -I .moai/state/verify/t18-plan2/final_path_probe.py
draft rc 0 
final rc 0 
delivery_allowed True review_record_passed
```

Probe 7 (P28 tile clip, script off, full network block, no `--no-sandbox`), MATCH with the recorded auditor observation:
```
$ PY -I .moai/state/verify/t18-audit/tile_probe.py
ws_found True (no --no-sandbox used)
blockedURLs ok
scriptDisabled ok
metrics_under_script_disabled {"sw":390,"cw":390,"sh":30803}
tile y=0 h=1568 -> png (390, 1568) bytes=132770
tile y=1568 h=1568 -> png (390, 1568) bytes=172378
tile y=30703 h=100 -> png (390, 100) bytes=9459
```

Probe 8 (P29 `<script` in the renderer):
```
$ grep -c "<script" backend/goose_harness_src/skills/goose/workflows/stock-report/scripts/render_report.py
0
$ grep -rc "<script" backend/goose_harness_src/skills/goose/workflows/stock-report | grep -v ':0$'
(no output: zero everywhere in the directory)
```

Probe 9 (P30 delivery_status owner), MATCH:
```
backend/services/goose_job_service.py:270:            data = {"delivery_status": result.delivery_status, **extra}
backend/services/goose_runner.py:476:        delivery_status=selected[0] if selected else None,
backend/services/goose_storage.py:166:            "delivery_status": archived.delivery_status,   (from the grep list)
```

Probe 10 (D13 SSOT, MP-7, MP-6, MP-5):
```
$ ls .claude/rules/moai/development/
agent-authoring.md  coding-standards.md  model-policy.md  skill-authoring.md
$ grep -rn 'NEEDS CLARIFICATION' plan.md research.md   -> (no match) rc=1
$ grep -n syscall .moai/specs/SPEC-AI-REPORT-006/*.md  -> (no match) rc=1
SPEC-AI-REPORT-004: status: completed
SPEC-AI-REPORT-005: status: completed
SPEC-TEST-HERMETIC-001: status: completed
```

Probe 11 (traceability and structure, `trace.py`; summary lines):
```
REQ count 20 sequential no gaps: True
AC count 22 sequential: True
uncovered REQ: []
AC with missing/invalid REQ: []
REQ-016 numbered conditions: 17
design table rows 0..17: 18
REQ order == design order (excluding #0): True design#0 = final_not_allowed
AC-AIR6-001..022: catches-line True, cannot-catch-line True (22 of 22)
```

Not re-run: P1/P2/P3/P4 (audit_probe, iteration 1 matched them and the code is unchanged), P12/P13/P15/P16 (host browser candidates and re-render), P18-P22 (frontend line numbers, interpreter, ignore rules). The live goose harness was not run.

## Recommendation (iteration 3 scope)
Blocking, fix before re-audit:
1. N1: restructure AC-018 item 5 so the safety invariant (5(ii), 5(iii)) is gating in every run and the marker/consistency checks (5(i), 5(iv)) are consistently either gating or non-gating; make 5(iv) "contains"; align the L247 and L249 classifications.
2. N2: unify REQ-020 and AC-019 into one GO definition (body-size tokens, both viewports, one tile at `y > 0`, matching Read pairs); allow the spike script as the capture source; state whether the cap check (item 5) is GO or NO-GO.
3. N3: name the isolating case for each of the 18 conditions, or restate the criterion with a recorded-Gap rule, and reconcile §E (acceptance.md:325) with acceptance.md:3.

Optional (route at the orchestrator's discretion): N4 (verify `final/` provenance), N5, N6, N7, N8, N9, N10.
Iteration 3 re-audit is scoped to N1-N3 plus a regression check of the D1-D14 table above.
