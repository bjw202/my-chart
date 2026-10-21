# SPEC Review Report: SPEC-AI-REPORT-006
Iteration: 3/3
Verdict: PASS-WITH-DEBT (all seven must-pass gates pass; N1-N3 are resolved; two blocking-class text defects, N11 and N12, are new and must be patched before Implementation Kickoff; see Debt)
Overall Score: 0.90 (iter 1 0.76, iter 2 0.85; no regression, no STOP signal. The Tier L threshold table is not in this worktree, so the threshold comparison is UNVERIFIED and the verdict does not rely on it.)

Reasoning context ignored per M1 Context Isolation. Audited: the six artifacts in the working tree (HEAD 0c4b2c4, which adds the plan.md risk row the coordinator announced; spec/acceptance/design/research/progress are unchanged since 81f0d30). No SPEC file was modified. The live goose harness was not run. Audit model is Claude-only. The `Grep` tool is unavailable in this session, so I used Bash `grep`.

## Plain summary
The three blockers from iteration 2 are fixed. A missing `[렌더 차이]` marker now has one outcome everywhere (condition 17 fails, delivery is `draft`). REQ-020 and AC-019 give the same GO rule, and the M1 spike no longer depends on M2. AC-016 now claims only what holds: I walked the isolating case for all 16 "level A" conditions and each one flips only when its own check is removed. The probes I re-ran all match. Two new small defects remain in the same area. First, the read-guard list leaves out condition 16, so the broken-index case (d2) cannot produce the exact list the AC demands. Second, the receipt writer must run a function that reads the receipt before the receipt exists. A third finding is a real route to a `visual: pass` that no reviewing session judged, and I recommend closing it cheaply. None of these breaks a must-pass gate.

## Must-Pass Results
- [PASS] MP-1: REQ-AIR6-001 to 020, sequential, no gaps or duplicates. Output: `grep -o '^\*\*REQ-AIR6-[0-9]*\*\*' spec.md` lists 001..020 in order. AC-AIR6-001..022 likewise sequential.
- [PASS] MP-2 (judged on the REQ layer in spec.md, not on ACs): every REQ is a Where/When/shall or "shall" sentence. REQ-016 (spec.md:122) is a very long compound but well-formed. REQ-018/020 carry procedure text (optional, N8 from iter 2, not fixed, not required).
- [PASS, SSOT part UNVERIFIED] MP-3: spec.md:1-16 carries id, title, version "0.3.0" (quoted), status draft, created, updated, author, priority High, phase, module, lifecycle spec-anchored, tags (comma string), plus extras tier and related_specs. `ls .claude/rules/moai/development/` shows `agent-authoring.md coding-standards.md model-policy.md skill-authoring.md`, so `spec-frontmatter-schema.md` is still absent (D13).
- [N/A] MP-4: single-feature Python backend SPEC.
- [PASS] MP-5 (D7): referenced SPECs 004, 005 and SPEC-TEST-HERMETIC-001 are all `status: completed` (output below). No retired, superseded or archived reference. plan.md:68 now names SPEC-AI-REPORT-007, which does not exist under `.moai/specs/` (`ls .moai/specs | grep 007` printed nothing). D7-5 gives SHOULD severity for a future SPEC; see N16.
- [PASS] MP-6 (D8): `grep -n syscall` over the artifacts returned nothing.
- [PASS] MP-7: `grep -rn 'NEEDS CLARIFICATION' plan.md research.md` returned nothing.

## Category Scores
| Dimension | Score | Band | Evidence |
|---|---|---|---|
| Clarity | 0.80 | minor ambiguity | N11 (spec.md:122 guard list vs acceptance.md:233) and N12 (spec.md:120 vs 122) are the only places where two readings give different results. |
| Completeness | 0.90 | frontmatter SSOT unchecked | HISTORY, WHY, WHAT, REQ, AC and five Out-of-Scope H3 groups with `-` bullets (spec.md:156-174). D13 still open. |
| Testability | 0.85 | mostly binary | AC-016 level A/B restatement holds (see section 2). AC-016 (d2) exact list is unattainable under the literal rule (N11). AC-013 #1 is phrase presence and self-labelled weak. |
| Traceability | 1.00 | complete | Computed below: 20 of 20 REQ covered; 22 of 22 ACs cite a valid REQ. |

## 1. N1-N3 re-verification

N1 (marker outcome): RESOLVED, no new contradiction found.
- One outcome everywhere: spec.md:114 ("an instruction miss whose single consequence is delivery status `draft`"), spec.md:142, design.md:131, acceptance.md:273 and 322, plan.md:62. All say condition 17 unmet, delivery `draft`.
- Pass rule at acceptance.md:271 splits (가) every run satisfies 5 from (나) at least one run satisfies 1-4. Item 4 (acceptance.md:281) holds the marker and uses "contains", matching condition 17 and AC-021 case (2). Item 5 (acceptance.md:282) is the safety invariant only. Failure routing at acceptance.md:285 says 5 "만 가리키며 표지 누락·미인정 pass는 5가 아니라 4와 비게이팅 기록의 몫". The "pass but not admitted" line at acceptance.md:287 agrees. I checked each 5(i)-(iv) against the receipt design: (iv) `visual_admissible == true` iff `reasons` empty holds because the writer fills both from the same function.
- Residual: the marker obligation applies to every `visual` evidence including a `revise` for missing screens (spec.md:114 has no exception). That is consistent but strict; no defect.

N2 (GO rule, M1 independence): RESOLVED, one tiny residual (MINOR, N15).
- REQ-020 (spec.md:152) and AC-019 (acceptance.md:292-300) both require: both body-size tokens quoted exactly; a Read call with matching non-error result for every canary tile; `y > 0` token. Smaller-size tokens only feed the recorded threshold. The spike script is M1-local in spec.md:152, acceptance.md:294 and plan.md:44, and `$S`-resident, not merged.
- AC-019 GO item 3 (the `y>0` tile hash differs from the `y==0` tile and its height equals the requested span) is not spelled out in REQ-020, although acceptance.md:292 says the definitions are the same. It is implied by the token placement (the token is only readable if the `y>0` clip works), so it adds no behaviour difference; I record it as MINOR only.
- Executability gap: the canary tiles must sit inside the harness directory because the harness denies `Read(../**)` (research P6), yet acceptance.md:294 puts the spike script in `$S` (repo). A literal run could get a permission error and a spurious NO-GO. That fails safe (NO-GO), so MINOR (N15).

N3 (reversal claim): RESOLVED as restated; the restatement is accurate. New small defect N11 in the read-guard text (below).
- Counting: level A = condition 0, 2-12, 14-17 = 1+11+4 = 16; level B = 1, 13; total 18 (acceptance.md:192-193, 248-249, 370). Table at acceptance.md:201-226 covers all 18 conditions, each with one named case.
- Natural-flow cases (g), (g3), (kr) are labelled not-a-reversal-target (acceptance.md:236, 253). Expected lists (g) `[screens_changed, tile_hash_mismatch]`, (g3) `[screens_changed, tile_missing]`, (kr) `[draft_changed, preview_hash_mismatch]` follow the fixed order 6,8 / 6,7 / 9,10.
- The function is stated never to raise and to treat unreadable input as unmet (spec.md:122, design.md:94).

## 2. Independent test of the level A claim (16 of 16 walked; asked for 6)
For each case I changed exactly the named input, then asked: if only this condition's check is deleted, does any other condition still catch it? Fixture P satisfies all conditions.

| Cond | Case | Other conditions that could catch it | Flips to final when check removed? |
|---|---|---|---|
| 0 | (n) `delivery_allowed:false` | none (conditions 1-17 do not read it) | yes |
| 2 | (b2-i) schema_version 2; (b2-ii) key `reasons` deleted | dependents 3,4,6,9,11 become evaluated and pass; the function never reads `reasons` | yes |
| 3 | (r) outcome timeout | only 3 reads outcome | yes |
| 4 | (w) one judged write | only 4 reads it | yes |
| 5 | (d) index outcome partial | 7,8,11,12 read other fields; snapshot rebuilt consistent | yes |
| 6 | (s) forged overflow after receipt (receipt snapshot holds the true index); (x) extra file mobile-99.png | 12 reads the forged value (false) and passes; 7/8 unaffected | yes |
| 7 | (t7) tile deleted before session, snapshot consistent | 8 skips missing tiles (spec.md:131); 11 compares lists only | yes |
| 8 | (g2) tile bytes altered pre-session, snapshot consistent | 7 sees the file; 6 consistent | yes |
| 9 | (k) `report-input.json` altered after receipt; (k2) `preview_end` wrong | 10 reads only `report.html`, which is unchanged | yes |
| 10 | (e) index `preview_sha256` stale; (m) review record `preview_sha256` stale | 9 compares disk to receipt (equal) | yes |
| 11 | (c) tile absent from `tiles_read`; (c2) `tiles_expected` differs | nothing else reads these | yes |
| 12 | (f) mobile overflow true, snapshot consistent | 5 reads outcome only | yes |
| 14 | (h) mode independent_agent | none | yes |
| 15 | (i) visual revise | 17 still finds the marker | yes |
| 16 | (j) reviewed_at earlier than finished_at | none | yes |
| 17 | (p) marker removed | 15 sees pass | yes |

One imprecision, not a defect: case (s) changes two stored things (the receipt snapshot and the index), since P has overflow false; it still isolates condition 6 and acceptance.md:197 explains the builder rule. Level B: removing 1 changes `[no_receipt]` into `[receipt_invalid]`-style output; removing 13 changes `[no_audit_review]` into `[mode…, visual…, reviewed_before_capture, font_note_missing]`-style output; both are caught by the exact-list assertion. The claim "result flips" is correctly not made for them.

## 3. Rule 7 re-attack, deferrals G13/G14/G15

Routes still open, ordered by how much they matter:
1. Stale review record planted by the first session (NEW, N13). The first goose session has `Write(./runs/**)`, can read the hashes from its own `audit_report.py` output (research §1 and P4 say the output carries `input_sha256` and `preview_sha256`), and can choose any future `reviewed_at`. Condition 16 only checks `reviewed_at >= index.finished_at` (a lower bound), and the start snapshot (REQ-014) does not cover `audit-review.json`. If the review session opens every tile but then exits 0 without overwriting the file, the planted `visual: pass` plus `[렌더 차이]` marker is admitted: REQ-005 only tests that a file exists, not that this session wrote it. This needs a rule-violating first session and a lazy review session, so it is unlikely, but it is a recorded `visual: pass` that no session judged against the screens, which is the thing rule 7 forbids. Cheap fix: delete `audit-review.json` and `final/` before launching the review session (and note it in the receipt), or require `reviewed_at == context.now` (the value is supposed to be copied exactly, spec.md:112), which a session that ran before `context.json` existed cannot know.
2. G13 (`final/` handwritten by the review session after an honest `revise`). Not a rule 7 violation: the tiles were genuinely opened. It lets a session reach `final` while the audit decision is `revise`. This route already exists in the code before this SPEC (the current `select_report` accepts any `final/` with `delivery_allowed: true`), and the SPEC now narrows it (a receipt admitting the screen check is required). Deferral is acceptable as documented debt.
3. G14 (receipt cannot be removed or replaced): requires two filesystem failures; the completion event still carries `draft`. Acceptable.
4. G15 (`audit-review.json` changed after receipt): the actor that could do it does not exist in the job model; process groups are terminated before the snapshot (design.md:30). Acceptable.
5. G11 and snapshot depth (N14, MINOR): design.md:86 keys the snapshot by "screens/ 안 파일 이름"; whether subdirectories are included is unspecified. A write into a subdirectory made by the two allowed scripts would not be a `Write`/`Edit` record. State "recursive".

Conclusion for the question asked: deferral of N4/G13 and G14/G15 does not block. It leaves a route to `final` for a dishonest session (G13), but not a route to an unobserved visual pass. N13 does leave such a route and should be closed with the cheap fix above.

## 4. D1-D14 regression table
| ID | Status | Evidence |
|---|---|---|
| D1 MP-7 markers | Still fixed | grep empty (below); decisions at spec.md:55, plan.md:33. |
| D2 screens tampering | Still fixed; residual G11, N13, N14 | REQ-014 (spec.md:116), conditions 4 and 6. |
| D3 single function, one condition list | Still fixed | REQ-016 lists 1-17; design.md table has 0-17; order identical (read by eye against spec.md:124-140 and design.md:99-117). |
| D4 M1 gate | Fixed now | N2 resolved above. |
| D5 tile cap 30 | Still fixed | spec.md:102, research P26, acceptance.md:91, 95. |
| D6 honest negative closable | Still fixed | spec.md:114; acceptance.md:281 (status not gating). |
| D7 receipt-to-final path | Still fixed with declared Gap G10 | AC-022. |
| D8 done-event status owner | Still fixed | REQ-019 (spec.md:150); `goose_job_service.py:270` and `goose_runner.py:476` re-grepped, unchanged. AC-020 (5)(6) now use a stub returning `final` (N6 fixed). |
| D9 unprobed prose | Still fixed | P10, P23-P33 present; P29/P30/P32/P33 re-run below. |
| D10 AC-018 variance, midnight | Still fixed | acceptance.md:271, 284. |
| D11 REQ-018 reads as scenario | Partially fixed (MINOR, unchanged) | spec.md:148 still names 020150 and the defect list. |
| D12 compound requirements | Rejected by author, acceptable (optional) | |
| D13 SSOT file absent | Still pending | `ls .claude/rules/moai/development/` shows no `spec-frontmatter-schema.md`. MP-3 SSOT portion UNVERIFIED. |
| D14 AC-005 missing case | Still fixed | acceptance.md:64-68. |

## 5. N1-N10 status
| ID | Status |
|---|---|
| N1 | Resolved (section 1) |
| N2 | Resolved; MINOR residual N15 |
| N3 | Resolved; new N11 in the guard text |
| N4 | Deferred as G13; acceptable (section 3) |
| N5 | Resolved: REQ-015 (spec.md:120) removes the session file first, writes via temp file and atomic replace; AC-015 S9(a)/(b). New N12 touches the same writer. |
| N6 | Resolved (AC-020 stub returns `final`, acceptance.md:313) |
| N7 | Resolved: spec.md:122 and design.md:94 state 0 belongs to `select_report`, 1-17 to the function |
| N8 | Not fixed, optional, accepted |
| N9 | Resolved: spec.md:86 limits the claim to job flow and events; `grep -n byte-for-byte` now matches only the HISTORY row |
| N10 | (a) resolved (plan.md:51), (b) mitigated (spec.md:60 prefix rule), (c) resolved (spec.md:116, design.md:143, AC-014 case 10), (d) rejected as G15, (e) resolved (acceptance.md:302-306) |

## 6. Defects Found
N11. Read-guard list omits condition 16 — spec.md:122 and design.md:123-128 vs acceptance.md:233 — Condition 16 reads `index.finished_at`, but the guard for an unreadable index lists only 7, 8, 11, 12 and the index side of 10. Under the literal text an unreadable index yields `[screens_not_complete, reviewed_before_capture]`, while AC-016 case (d2) demands exactly `[screens_not_complete]` and the same guard text says unreadable input counts as unmet. A correct implementation of the REQ fails the AC, or the implementer must guess. Safety is unaffected (both give `draft`). — Severity: major — Class: blocking (an AC contradicts the REQ it verifies) — Required fix: add 16 to the list of conditions skipped when the index cannot be read, in spec.md:122 and in the design.md:126 table row.

N12. Writer-versus-function circularity — spec.md:120 vs 122 — REQ-015 has the writer record "the admissibility verdict … computed by the REQ-AIR6-016 function at write time", but the function takes only `job_dir` and reads `review/receipt.json` from disk, which does not exist yet while the writer is composing it (conditions 1,2,3,4,6,9,11 all read it). AC-016 requires writer `reasons` to equal the same-time `select_report` reasons, so the intended behaviour is clear, but the mechanism is not: write twice, or give the function an in-memory receipt argument. Each choice changes N5's failure analysis (a second write is a second failure point). — Severity: major — Class: blocking (internal consistency, small) — Required fix: one sentence in REQ-015 or design §5 saying the function core accepts the receipt facts as an argument (the disk wrapper reads them from the file), and the writer calls the core before the single atomic write.

N13. Stale `audit-review.json` / `final/` not cleared before the review session — spec.md:112-116, 94 — see section 3, route 1. — Severity: major — Class: optional by M6 (not a stated criterion, needs a rule-violating session) but recommended because it touches rule 7 — Required fix: remove both before launch and record that in `context.json`, or require `reviewed_at == context.now` as a new condition; add an AC-014 style case.

N14. Snapshot depth unspecified — design.md:86 — "files" is keyed by file name; subdirectories unspecified. — Severity: minor — Class: optional — Required fix: say the snapshot is recursive and keyed by relative path.

N15. M1 spike details — acceptance.md:292-300 — canary tiles must live inside the harness directory to be `Read`; GO item 3 is stricter than REQ-020's wording. — Severity: minor — Class: optional — Required fix: add "written under `~/.goose-harness/runs/<canary>/`" to the Given and mirror item 3 in REQ-020.

N16. plan.md:68 (the row added after this audit started) — no inconsistency found, not scope creep (it adds no REQ/AC and no behaviour; it is a conditional, future merge-time obligation recorded in the risk table). Checks: rule-9 references at spec.md:70, design.md:153, acceptance.md:139/145/326, plan.md:48 and research.md:76 all still say 9, which is correct for this SPEC's own tree and the row says the renumbering to 10 happens at merge time, so there is no conflict today. Two small gaps: (1) the row's step (2) names only the ACs, while design.md §7 (rule label), spec.md:70, plan.md:48 and research G13 also carry the number, and step (1) covers "하위 라벨·자기 참조" only for the rule text; (2) the row cites SPEC-AI-REPORT-007's `plan.md §5` and audit debt N9, but 007 is not in this worktree (`ls .moai/specs | grep 007` empty, `git log` shows no 007 commit), so those citations are UNVERIFIED here. Also note the row says 4 steps; I could count four. — Severity: minor — Class: optional — Required fix: extend step (2) to "every artifact of this SPEC that names rule 9" and cite 007's commit id once it exists.

## 7. Traceability (computed from the artifacts)
`grep -o '^### AC-AIR6-[0-9]* .*'` gives the AC to REQ pairs: 001..018 map to REQ-001..018 one to one; AC-019 to REQ-020; AC-020 to REQ-019; AC-021 to REQ-013 and REQ-016 (condition 17); AC-022 to REQ-016 and REQ-019. Union covers REQ-001..020 (uncovered: none); all cited REQ ids exist (invalid: none). Counts 20 REQ, 22 AC, matching spec.md:26 and progress.md:8.

## 8. Verbatim probe output
```
$ git log --oneline -3
0c4b2c4 docs(SPEC-AI-REPORT-006): 007 대비 병합 의무 한 줄 반영 (카드 t18)
81f0d30 docs(SPEC-AI-REPORT-006): plan 감사 2차 반영 v0.3.0 (카드 t18)
86b7c0d docs(SPEC-AI-REPORT-006): plan 감사 1차 반영 v0.2.0 (카드 t18)

$ git diff --stat 7abdcac HEAD -- backend frontend pyproject.toml README.md .env.example
(empty: no code or harness change)

$ grep -rn 'NEEDS CLARIFICATION' plan.md research.md        (rc=1, no match)
$ grep -n syscall .moai/specs/SPEC-AI-REPORT-006/*.md        (rc=1, no match)
$ ls .claude/rules/moai/development/
agent-authoring.md  coding-standards.md  model-policy.md  skill-authoring.md
SPEC-AI-REPORT-004: status: completed
SPEC-AI-REPORT-005: status: completed
SPEC-TEST-HERMETIC-001: status: completed

$ shasum -a 256 backend/goose_harness_src/claude-settings.json
e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3
$ PY -m backend.services.goose_harness > regen.json ; cmp regen.json goose-manifest.json
MANIFEST_BYTE_IDENTICAL

$ PY -m pytest backend/tests -k goose -q -p no:cacheprovider
267 passed, 214 deselected, 1 warning in 16.28s

$ grep -c "<script" .../stock-report/scripts/render_report.py
0
$ grep -n "delivery-audit|render-validation|delivery_allowed" render_report.py (excerpt)
437 render-validation.json ... 478 evidence['delivery_allowed'] = False ... 501 (output / 'delivery-audit.json').write_text ... 503 evidence['delivery_allowed'] = True ... 505/513 render-validation.json rewritten
$ /bin/ls -d /Users /users /USERS
/users
/Users
/USERS
$ grep -n delivery_status goose_runner.py goose_job_service.py (excerpt)
goose_runner.py:476:        delivery_status=selected[0] if selected else None,
goose_job_service.py:270:            data = {"delivery_status": result.delivery_status, **extra}

$ ls .moai/specs | grep 007
(no output)

$ /usr/bin/python3 -I -c "<literal reading of spec.md:122 guard list, index unreadable>"
d2 literal guard list (7,8,11,12,10-index only): ['screens_not_complete', 'reviewed_before_capture']
d2 expected by AC-016: [screens_not_complete]
d2 if 16 added to guard list: ['screens_not_complete']
```
Not re-run: P1-P4, P12-P16, P18-P28 (unchanged since the iteration 2 match; no code or harness change per the empty diff stat). The N11 probe is a three-line model of the guard text, not the implementation; it shows how the literal rule reads, nothing more.

## Debt (PASS-WITH-DEBT)
Must be closed before Implementation Kickoff (one small text patch to spec.md and design.md, then a delta check of these two lines, no full re-audit):
1. N11: add condition 16 to the unreadable-index skip list (spec.md:122, design.md:126).
2. N12: state how the writer computes `reasons` before the receipt exists (REQ-015 / design §5).

Recommended, route at the orchestrator's discretion: N13 (stale review record, rule 7 related).

Accepted debt, carry into the run phase: G13 (`final/` origin), G14, G15, G11, D13 (frontmatter SSOT unchecked), N8/D11 (verification detail in REQ-018/020), N14, N15, N16.
