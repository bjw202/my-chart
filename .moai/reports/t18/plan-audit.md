# SPEC Review Report: SPEC-AI-REPORT-006
Iteration: 1/3
Verdict: FAIL (one must-pass gate open: MP-7; three blocking defects; expected to flip to PASS after the fixes below)
Overall Score: 0.76 (Tier L; the tier threshold table was not available in this worktree's spec-workflow.md, so the threshold comparison is UNVERIFIED. The verdict does not depend on it.)

Reasoning context ignored per M1 Context Isolation. Only the six SPEC artifacts, the code they cite, and the project lessons were used.
Commit audited: 4663bb3 (worktree t18, branch WT-goose-review-pass). No SPEC body file was modified. Scratch probes live in the git-ignored `.moai/state/verify/t18-audit/`.

## Must-Pass Results
- [PASS] MP-1 REQ numbering: `REQ-AIR6-001` through `REQ-AIR6-018` appear sequentially at spec.md:82-124, with no gaps or duplicates and consistent zero-padding.
- [PASS, with a minor note] MP-2 GEARS compliance, judged on the requirement layer (`REQ-XXX` in spec.md), not on the ACs. Every REQ uses Where/When/shall patterns or "The X shall". REQ-018 (spec.md:124) reads like a test scenario: a named stock code, "up to two runs", and a list of defect codes. It is grammatically "When … shall", so I did not fail it. See D11.
- [PASS, SSOT part UNVERIFIED] MP-3 frontmatter (spec.md:1-16): id, title, version "0.1.0" (quoted), status draft, created, updated, author, priority High, phase, module, lifecycle spec-anchored, and tags (comma string) are all present with correct types. `tier` and `related_specs` are extra fields. `spec-frontmatter-schema.md` does not exist in this worktree (`ls .claude/rules/moai/development/` shows agent-authoring, coding-standards, model-policy, skill-authoring), so the per-field check was made against the 12-field list in the audit charter, not the SSOT.
- [N/A] MP-4 language neutrality: single-feature Python backend SPEC, not multi-language tooling.
- [PASS] MP-5 D7 cross-SPEC: referenced IDs are SPEC-AI-REPORT-004, 005, 006 (self), and SPEC-TEST-HERMETIC-001. The first three non-self IDs all show `status: completed`. None is retired, superseded, or archived. Observed with `grep -m1 '^status:'`.
- [PASS] MP-6 D8 cross-platform: `grep -n syscall .moai/specs/SPEC-AI-REPORT-006/*.md` returned no match.
- [FAIL] MP-7 clarification gate: `grep -rn "NEEDS CLARIFICATION" plan.md research.md` matches plan.md:38 (heading), :40 (supported browser) and :41 (block all network vs allow the two font hosts). Both markers are open. Defaults exist and are safe (see D1), but this gate is score-independent. The orchestrator must resolve both via AskUserQuestion before the plan-to-run gate, then delete the markers.

## Category Scores
| Dimension | Score | Band | Evidence |
|---|---|---|---|
| Clarity | 0.75 | minor ambiguity | The owner of the done-event `delivery_status` is unstated (D8). REQ-016 says select_report classifies by a 9-item list, while design §5 says it only reads `visual_admissible` (D3). The status to record for the four non-visual checks when a defect is found is unstated (D6). |
| Completeness | 0.75 | one non-critical gap | All sections are present: HISTORY, §1 WHY, §3 WHAT, §4 REQ, Out of Scope with three H3 groups and `-` bullets at spec.md:128-144, and a plan with milestones. Gaps: no AC for the M1 gate (D4) and no pre-session snapshot of `screens/` (D2). |
| Testability | 0.75 | mostly binary | All 18 ACs carry both "잡는 구현" and "잡지 못하는 것" lines (checked AC-001 to AC-018). AC-013 #1 is a phrase-presence check, which the AC itself labels weak (acceptance.md:145). AC-005 does not state the receipt outcome for "exit 0 but no audit-review.json". AC-018 depends on model non-determinism (D10). |
| Traceability | 0.75 | indirect mapping | The REQ-to-AC mapping is 1:1 for 001-018. But three conditions inside REQ-016 have no AC case: the audit-review `preview_sha256` check, a missing tile file, and a draft changed during review. AC-016 (k) tests a condition that REQ-016 does not state (D3). |

## Probe Re-Runs (observed vs recorded)

All commands ran from the worktree root. `PY` = `/Users/byunjungwon/Dev/my_chart/.venv/bin/python` (Python 3.13.11).

**A. P17 baseline: 267 goose tests.** MATCH.
```
$ PY -m pytest backend/tests -k goose -q -p no:cacheprovider
267 passed, 214 deselected, 1 warning in 16.01s
```
Recorded: `267 passed, 214 deselected, 1 warning in 16.52s`.

**B. P2/P1: audit codes with and without a review record.** MATCH.
```
$ /usr/bin/python3 -I .moai/state/verify/t18-plan/audit_probe.py
A none       ['AUDIT_INPUT_VERSION','AUDIT_MODE','AUDIT_PREVIEW_VERSION','AUDIT_TIME','LATEST_SEARCH_NAVER','REVIEW_CALCULATIONS','REVIEW_COVERAGE','REVIEW_OPINION','REVIEW_SOURCE_ACCURACY','REVIEW_VISUAL']
B full pass  ['LATEST_SEARCH_NAVER']
C visual rev ['LATEST_SEARCH_NAVER','REVIEW_VISUAL']
D bad input  ['AUDIT_INPUT_VERSION','LATEST_SEARCH_NAVER']
E bad prev   ['AUDIT_PREVIEW_VERSION','LATEST_SEARCH_NAVER']
F bad mode   ['AUDIT_MODE','LATEST_SEARCH_NAVER']
G open issue ['LATEST_SEARCH_NAVER','UNRESOLVED_ISSUE']
```
`sed -n 90,110p audit_report.py` also confirms the P1 line citations. `checks=(…5 names…)` is at :95. `AUDIT_INPUT_VERSION` is at :96 and `AUDIT_PREVIEW_VERSION` at :97. `AUDIT_TIME` is at :99, `AUDIT_MODE` at :100, `REVIEW_<NAME>` at :101-103, and `UNRESOLVED_ISSUE` at :104-105.
Consequence: even a fully passing review record leaves `LATEST_SEARCH_NAVER` (see D7).

**C. P3/P4: live run `a5becbb9…` audit result and hashes.** MATCH.
```
revise ['AUDIT_INPUT_VERSION','AUDIT_MODE','AUDIT_PREVIEW_VERSION','AUDIT_TIME','LATEST_SEARCH_NAVER','REVIEW_CALCULATIONS','REVIEW_COVERAGE','REVIEW_OPINION','REVIEW_SOURCE_ACCURACY','REVIEW_VISUAL']
{'reviewed_at': None, 'mode': None, 'checks': None, 'issues': None}
b83f48e1…06374fc  480b6f77…2e0e6   (delivery-audit.json input_sha256 / preview_sha256)
b83f48e1…  company-input.json
b83f48e1…  draft/report-input.json
480b6f77…  draft/report.html
```
The three file hashes equal the audit output hashes.

**D. P6/P7: permission file hash and manifest regeneration.** MATCH.
```
$ shasum -a 256 backend/goose_harness_src/claude-settings.json
e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3   (equals the AC-013 #3 constant)
$ PY -m backend.services.goose_harness > regen.json ; cmp regen.json backend/goose_harness_src/goose-manifest.json
rc=0   BYTE-IDENTICAL
```
The settings file allows `Read(./**)`, `Write(./runs/**)` and `Edit(./runs/**)` (lines 9-11). This matters for D2.

**E. P15/P16: re-render is byte-identical, and the draft HTML has no script.** MATCH.
```
$ /usr/bin/python3 -I ~/.goose-harness/.claude/skills/goose/workflows/stock-report/scripts/render_report.py --input …/a5becbb9…/company-input.json --output-dir .moai/state/verify/t18-audit/rerender
480b6f772b308ecf364de6cf81bd4af0a7496f0e188e3795211562609752e0e6  report.html   (equals draft/report.html)
$ grep -c "<script" draft/report.html  -> 0 ;  <link rel="stylesheet"> x2 (Pretendard CDN, Google Fonts)
```

**F. P10: stream fixture, `Read` tool use and result shape.** PARTIAL MISMATCH.
```
{'system':93,'assistant':55,'user':43,'rate_limit_event':2,'tool_progress':2,'result':1}
6 Read tool_use calls, paths absolute (/HARNESS/…)
tool_result blocks: is_error ABSENT x33, False x4, True x3
```
Research P10 says "성공 예시에는 is_error 키가 없었다(오류 표지 이름은 미관측, G1)". The fixture actually shows the error marker `is_error: true` three times and an explicit `is_error: false` four times. The recorded observation is understated. The marker name is already known, and an implementation must treat both `False` and absent as success (see D9).

**G. P12: host browser candidates.** MATCH. `ms-playwright` holds chromium_headless_shell-1148/1208/1228/1234/1243. `Google Chrome.app` is present in /Applications.

**H. P14 extended, which also covers G3 and G9 (new observation).**
Script: `.moai/state/verify/t18-audit/tile_probe.py`. It launches chrome-headless-shell 1243 with NO `--no-sandbox`, sets `Network.setBlockedURLs ["*"]` and `Emulation.setScriptExecutionDisabled`, and loads the draft as `file://` at 390 px mobile.
```
ws_found True (no --no-sandbox used)
blockedURLs ok
scriptDisabled ok
metrics_under_script_disabled {"sw":390,"cw":390,"sh":30803}
tile y=0    h=1568 -> png (390, 1568) bytes=132770
tile y=1568 h=1568 -> png (390, 1568) bytes=172378
tile y=30703 h=100 -> png (390, 100) bytes=9459
```
- G3 is substantially resolved: a `y>0` tile `clip` works, `setScriptExecutionDisabled` works, and `setBlockedURLs ["*"]` does not prevent a `file://` load.
- G9: this host did not need `--no-sandbox` (not proven for other hosts).
- G8: with the network blocked, mobile `scrollHeight` is 30803, against the recorded 30683 with fonts loaded. The layout moves by about 120 px when the web fonts are blocked. This is concrete input for the open clarification in D1.

**I. Tile-count headroom, a new probe over all four historical drafts (blocked network, script off).** Script: `heights_probe.py`.
```
1d261a37 desktop 9807 -> 7 tiles   mobile 15047 -> 10 tiles
5695985a desktop 9053 -> 6 tiles   mobile 14169 -> 10 tiles
a5becbb9 desktop 20160 -> 13 tiles mobile 30803 -> 20 tiles   <- the 020150 gating run
d0a64dfc desktop 12066 -> 8 tiles  mobile 18797 -> 12 tiles
all four: scroll_width == client_width at 1280 and 390 (no horizontal overflow)
```
The per-viewport cap is 24 (REQ-AIR6-008). The gating stock (020150) is the heaviest of the four drafts and uses 20 of 24 tiles on mobile. Research P14 and §3-4 sampled only that one draft.

Not re-run: P13 (command-line `--screenshot`), P11 beyond `websockets 16.0` import and `playwright` ModuleNotFoundError (both confirmed), and P20 to P22.

## Defects Found

D1. MP-7 clarification gate — plan.md:40-41 — two open `[NEEDS CLARIFICATION]` markers (supported browser; block all network or allow font hosts). Defaults are safe: an unsupported browser gives `unavailable` and a `draft` delivery, and a full network block keeps capture deterministic. But the gate is score-independent. — Severity: critical (must-pass) — Class: blocking — Required fix: the orchestrator asks both questions via AskUserQuestion before the kickoff gate. Evidence to give the user: H above (blocking fonts shifts mobile height by about 120 px, so the reviewer judges a slightly different layout than users see) and G2 (`Google Chrome.app` launch is unobserved). Then fold the answers into spec.md D7/§5 and plan.md T9, and delete the markers. If the user accepts the defaults, state that in plan.md as a decision, not a marker.

D2. Rule-7 invariant has a hole: `screens/` is not integrity-checked against the review session — spec.md:112-118 (REQ-014/015/016), design §5 — The review session holds `Write(./runs/**)` and `Edit(./runs/**)` (claude-settings.json:10-11), so it can overwrite `screens/index.json` and the tile PNGs. REQ-014 snapshots only `draft/report.html` and `draft/report-input.json` before and after. REQ-015 records "the SHA-256 of the screens index" but does not say when. REQ-016 then compares tile hashes against the index and the index against the draft. If the index is hashed after the session, those comparisons check files the session could have rewritten with each other. A forged `index.json` (outcome `complete`, `horizontal_overflow` false, matching hashes of forged tiles) plus a `Read` of the forged tiles would produce a receipt that admits `visual`. That contradicts D5 ("인정 근거는 서버가 직접 확인한 사실") and the invariant paragraph at spec.md:39. The SPEC treats the session as untrusted for the receipt and `final/` (AC-015 S7) but not for its own inputs. — Severity: critical — Class: blocking — Required fix: before launching the review session, the server records the SHA-256 of `index.json`, of every tile, and the file set of `screens/` (the same step that writes `context.json`). It stores them in the receipt (for example `screens_start` and `screens_end`) and compares them at the end. A difference gives reason `screens_changed` and `visual_admissible=false`. Add the case to REQ-016, to AC-014 or AC-016, and to the `잡는 구현` list (reversal: skip the screens snapshot, so a session that rewrites a tile or `index.json` still gets `final`).

D3. REQ-016, design §5, and AC-016 disagree about what `select_report` evaluates — spec.md:118, design.md:89-98, acceptance.md:174-190 — REQ-016 says the runner classifies `final` only when the receipt "admits the screen verification, that is, all of" nine conditions. Design §5 says `select_report` checks the delivery-allowed condition, `receipt.visual_admissible == true`, and `sha256(draft/report.html) == receipt.hashes.preview_end`; everything else is computed once at receipt-write time. Consequences: (i) AC-016 (g), a tile modified after capture, can be caught only if the fixture's receipt was generated from the mutated disk, yet the case reads as a `select_report` property; a tile edited after the receipt is not detected by the design as written. (ii) AC-016 (k) tests a post-receipt draft hash check that REQ-016's text does not contain. (iii) Three REQ-016 conditions have no AC case: the audit-review `preview_sha256` equals the draft hash, every listed tile file exists (`tile_missing`), and the draft and input did not change during the review (AC-014 covers the receipt field only, not the `final` decision). Also uncovered: a receipt that is unparsable or has the wrong `schema_version`. Acceptance §E promises a reversal for "조건 11개 각각", which cannot be met for conditions with no case. — Severity: major — Class: blocking (internal consistency of a stated criterion) — Required fix: specify one pure function (for example `evaluate_admissibility(job_dir)`) used by both the receipt writer and `select_report`. `select_report` must recompute from disk plus the server-written receipt facts (`tiles_read`, start hashes), never trust the stored boolean alone. Align REQ-016, design §5, and AC-016 to the same list. Add AC-016 cases for the three missing conditions and for a malformed receipt, each with a named reversal.

D4. The M1 GO/NO-GO gate has no binary pass condition — plan.md:47, acceptance.md:245, research.md:53 (G1) — The spike is described ("does a real `claude -p` Read the PNG, and what is the stream shape") but "GO" is never defined, M1 has no AC, and acceptance §F requires only that the result be recorded. A successful non-error `tool_result` does not show the model perceived the image: it could be an "image too large" style result, or a downscaled tile unreadable at 1568 px (G4). The NO-GO path is stated only coarsely ("중단하고 manager-spec에 되돌려 보낸다", plus the DOM-summary idea at plan.md:60). — Severity: major — Class: optional-to-blocking (the SPEC calls M1 a gate, so it should be binary) — Required fix: add AC-AIR6-019 (M1 gate). GO means: (a) a headless `claude -p`, launched with the harness argv and settings, Reads a server-generated canary PNG of the real tile size (random token drawn in text at normal body size at the first tile's scale) and its reply quotes the token, and (b) the stream shows the `tool_use`/`tool_result` pair with `is_error` false or absent. NO-GO means any other outcome. On NO-GO, no M2-M6 code is merged, `progress.md` records the observation, and the SPEC returns to plan unchanged. Record G4 (legibility) as a measured threshold, not a note.

D5. Tile cap leaves thin headroom on the one gating stock — spec.md:98 (24 tiles), research.md §3-4 — Observation I shows 020150 at 20 of 24 mobile tiles (30803 px), while the other three drafts need 10-12. A somewhat longer 020150 report becomes `too_tall`, then `partial`, and can never be admitted. Reading 33 tiles in sequence within the default 900 s review limit is unmeasured (G5). Research sampled n=1 (lesson #10, single sample). — Severity: minor — Class: optional — Required fix: keep 24 for now but have M1 measure the 4 existing drafts (already available under `~/.goose-harness/runs`), record the distribution in `progress.md`, and decide a cap with at least 1.5x headroom over the largest, or a defined degrade path (coarser tiles) instead of a hard `too_tall`.

D6. AC-018 punishes an honest negative review on the four non-visual checks — acceptance.md:211-213, design §7 (rule 9) — AC-018 step 4 requires that `REVIEW_SOURCE_ACCURACY`, `REVIEW_CALCULATIONS`, `REVIEW_COVERAGE`, `REVIEW_OPINION` be absent, which per audit_report.py:101-103 means each check is `pass` with non-empty evidence. Only `visual` has an honest-`revise` carve-out (acceptance.md:213). Rule 9(d) does not say which status to write for the other four when a defect is found, so a reviewer that finds a real problem and writes `revise` leaves the SPEC unable to close, which pushes toward rubber-stamping. The SPEC guards only the visual claim (Out of Scope, spec.md:131). — Severity: major — Class: optional (design tension, not a contradiction) — Required fix: rule 9 states that on a defect the check is recorded `revise` with evidence and an `open` issue. Gate AC-018 on record well-formedness (`AUDIT_INPUT_VERSION`, `AUDIT_PREVIEW_VERSION`, `AUDIT_TIME`, `AUDIT_MODE` absent, and every check present with non-empty evidence), and treat the `pass` status of the four checks as recorded, non-gating.

D7. The receipt-to-`final` path is never observed end to end — acceptance.md:211-215, spec.md:41 — `LATEST_SEARCH_NAVER` persists even in the all-pass synthetic record (observation B) and in the live run (observation C). So for 020150 the audit decision is never `pass`, `--final` never runs, and AC-018 step 5(iii) and the admit-`final` path are vacuous in the live gate. `final` admission is tested only through hand-made fixtures (AC-016). The SPEC says so (spec.md:41) but the headline claim ("최종본은 서버가 확인한 사실에만 근거") has no integration observation. — Severity: minor — Class: optional — Required fix: add a hermetic M4 integration test that runs the real `audit_report.py` and `render_report.py --final` on a synthetic input that satisfies the search-channel rule, with a fake `claude` writing a record from `context.json`, then asserts the receipt reaches `select_report == "final"`. If such an input cannot be built, record that as a Gap in `progress.md`.

D8. The done-event `delivery_status` has an unstated owner — goose_runner.py:465-476, goose_job_service.py:270, goose_storage.py:160-169 — `run_goose` computes `delivery_status` with `select_report` right after the first session, before the receipt exists, so it will always be `draft` under the new rule. `_run` emits `{"delivery_status": result.delivery_status, **extra}`. In production the finish hook's value, computed after post-processing, overrides it. Without the hook, or if archive returns `None`, the event carries the stale pre-receipt value. The SPEC never says which one is authoritative, and AC-004/AC-018 5(ii) refer to the "delivery status" without naming it. — Severity: major — Class: blocking (an ambiguity that can produce a wrong user-visible status) — Required fix: state in REQ-001 or REQ-016 that the delivery status in the done event and `job.json` is the one computed after the receipt is written, and add an AC that the done event equals `archive_job`'s status for a case where the first-session value and the post-receipt value differ.

D9. Prose claims without a probe, and one understated observation (lesson #10) — research.md P10, spec.md:41 and §5 (135), design.md:127 — (a) P10 records the error marker as unobserved; observation F shows `is_error: true` (x3) and `false` (x4) in the fixture, so AC-015 S3 and design §6 ("is_error 등, G1에서 이름 확정") can be settled now. (b) "네이버 금융 접근 차단" is asserted as the cause of `LATEST_SEARCH_NAVER` with no probe (P3 shows only the code). (c) "초안에는 `<script>`가 0개(P16)" generalizes from one draft; the renderer's behavior was not probed. Observation I confirms that all four existing drafts have no overflow, but not the script claim. — Severity: minor — Class: optional — Required fix: add the observed `is_error` facts to P10; mark (b) as inference or add the probe; grep `render_report.py` for script emission, or restate (c) as "in the observed draft".

D10. AC-018 variance and midnight edge — acceptance.md:203-216, audit_report.py:32 — "up to two runs, every run must satisfy" does not say whether a second run is a retry or an extra gate, and an LLM gate cannot be deterministic. Also `FRESHNESS_CUTOFF` (audit_report.py:32-33) requires the cutoff date to equal the audit date, so a post-processing run that crosses midnight KST adds a defect outside the listed eight. — Severity: minor — Class: optional — Required fix: define the pass rule explicitly (for example "pass on one run, and any failing run must have a recorded cause") and note the midnight edge in AC-018 or the risk table.

D11. REQ-018 reads as a verification scenario — spec.md:124 — A named stock, a run count, and a list of defect codes belong in AC-018, where they are already repeated. It is grammatically valid GEARS, so MP-2 passes. — Severity: minor — Class: optional — Required fix: reduce REQ-018 to the behavior ("shall emit no record-related defect code and shall have the receipt list every tile as read") and keep the scenario in AC-018.

D12. Compound requirements — spec.md:82 (REQ-001), :110 (REQ-013), :118 (REQ-016) — each bundles several independent behaviors. This makes one AC-level failure hard to attribute. — Severity: minor — Class: optional — Required fix: none required; split only if the run phase finds attribution hard.

D13. MP-3 not checkable against the SSOT — `spec-frontmatter-schema.md` absent in this worktree; `related_specs` and `tier` are extra fields; research G7 acknowledges. — Severity: minor — Class: optional — Required fix: re-check against the SSOT when it is available in the main checkout.

D14. AC-005 does not name the receipt outcome for "exit 0 but no `audit-review.json`" — acceptance.md:61-68 vs design.md:38 — design says `review_failed`, AC lists outcomes only for the nonzero-exit and timeout cases. — Severity: minor — Class: optional — Required fix: add that case and its expected outcome to AC-005.

## Findings on the specific audit questions

1. Reversal probes (lesson #9) and probes for prose claims (lesson #10). All 18 ACs have "잡는 구현" and "잡지 못하는 것" lines. The reversal lists are mostly specific (AC-001, 002, 008, 011, 015, 016 are good). Weak spots: AC-013 #1 (phrase presence, self-labeled weak), AC-017 (1) (count arithmetic can hide a swapped test), and the gaps in D3. Prose probes: 22 probes in research.md, of which I re-ran 14. All matched except P10, which was understated (D9). I also added observations G3, G8, G9 and I.
2. Rule 7 as an enforceable invariant. The design is strong where it overwrites the receipt after the session (AC-015 S7) and counts a tile as read only on a matching non-error `tool_result` in the server-held stream. A model's self-assertion cannot satisfy the receipt for the tile-read part. It is not complete: D2 shows the session can rewrite the screens it is judged on, and D3 shows the final decision may trust a stored boolean. The invariant is therefore not yet airtight, and AC-016/AC-018 do not fully enforce it.
3. M1 GO/NO-GO. It is a gate in intent but not in definition (D4). The NO-GO action exists at a coarse level only.
4. Tier and milestone split, and defaults. Tier L is coherent: six milestones, about 20 files, new subsystem plus gate change. The dependency order M1 to M6 is sound, and "serial" is justified. Both clarification markers have safe fail-open defaults, but MP-7 still blocks (D1).

## Recommendation (iteration 2 scope)
1. The orchestrator resolves the two markers in D1 through AskUserQuestion and removes them.
2. Fix the blocking items: D2 (screens snapshot and comparison, plus AC case and reversal), D3 (single admissibility function, aligned REQ/design/AC, three missing cases), D8 (done-event status owner and AC).
3. Fix D4 (add AC-019 for M1 with canary-based GO criteria and NO-GO consequences) and D6 (rule 9 wording and AC-018 gate).
4. Optional: D5, D7, D9, D10, D11, D12, D13, D14.
Iteration 2 is scoped to this delta plus a regression check of D1-D14.
