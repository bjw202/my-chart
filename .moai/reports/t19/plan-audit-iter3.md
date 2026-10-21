# SPEC Review Report: SPEC-AI-REPORT-007
Iteration: 3/3 (final)
Verdict: PASS
Overall Score: 0.88 (harmonic mean; Tier M PASS threshold 0.80; iter-1 0.81 → iter-2 0.85 → iter-3 0.88, no regression, no STOP signal)

Reasoning context ignored per M1 Context Isolation. Inputs read: `.moai/specs/SPEC-AI-REPORT-007/{spec,plan,acceptance,progress}.md` at HEAD `991800f` (working tree clean except untracked `.moai/logs/`), iter-2 report `.moai/reports/t19/plan-audit-iter2.md`, the real `backend/goose_harness_src/harness-instructions.md`, and SPEC-AI-REPORT-006 v0.2.0 at commit `86b7c0d` (branch `WT-goose-review-pass`, read-only `git show`).

Tier M threshold source: the main checkout's `.claude/rules/moai/workflow/spec-workflow.md` L141, `| M (Medium) | 300 - 1000 LOC | 5 - 15 files | **3 files**: spec.md + plan.md + acceptance.md | 0.80 |`.

Scope (iteration-3 delta): N1 and N4 verified by my own probes, the status of N2/N3/N5/N6/N7, a regression scan, and a search for new defects. Probe scripts and outputs are kept under `.moai/state/verify/t19-audit-iter3/` (gitignored evidence folder).

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: the REQs appear in document order `001 … 014`, with no gaps and no duplicates (probe R). REQ-014 now sits in §5.7, spec.md L169.
- [PASS] MP-2 GEARS compliance (judged on the requirement layer only, the REQ entries in spec.md §5): unchanged in form from iter-2. 001 is a compound Where+When. 002/008/009/011/013 are When. 003 is Where. 004 is the negative ubiquitous form. 005/006/007/010/012/014 are ubiquitous. The revised REQ-013 (L165) is still a single When-clause requirement. REQ-005 (L141) is still ubiquitous. No REQ uses IF/THEN (probe R: `IF/THEN in REQ 0`). The ACs are Given-When-Then, the verification-layer format, and were not graded here.
- [PASS] MP-3 YAML frontmatter: spec.md L2-15 has all 12 canonical keys, `version: "0.3.0"` is quoted, and there are no rejected aliases (probe R). `moai spec lint` reports `✓ No findings`.
- [N/A] MP-4: single-language (Python backend) SPEC.
- [PASS] MP-5 D7: 004, 005 and TEST-HERMETIC-001 are `completed`. SPEC-AI-REPORT-006 gives SHOULD "not found in .moai/specs/" because it lives only on branch `WT-goose-review-pass`. That is expected and explained (spec.md L28). No BLOCKING finding.
- [PASS] MP-6 D8: the `syscall` count is `[0, 0, 0, 0]`.
- [PASS] MP-7: `[NEEDS CLARIFICATION` count is 0 in plan.md. There is no research.md (Tier M).

## Category Scores

| Dimension | Score | Rubric Band | Evidence |
|---|---|---|---|
| Clarity | 0.80 | 0.75 band | REQ-013 L165 now states exactly which form applies per index outcome, and the N1 contradiction is gone. REQ-010 L157 and REQ-013 L165 are still single sentences of 200+ words. A reader can resolve them consistently, but slowly. One narrow residual interpretation gap remains (N10). |
| Completeness | 0.90 | 0.75–1.0 | All sections are present. There are three `### Out of Scope — …` H3 headings with bullets (L186, L192, L198). HISTORY covers 0.1.0–0.3.0 (L24-26). Gaps G1-G5 and residual risk §9 are present. The HISTORY 0.3.0 row does not name N3/N5/N6 (O-H, cosmetic). |
| Testability | 0.90 | 0.75–1.0 | Check 3 gave 34/34 synthetic cases as expected (probe A). The AC-005 size reverts are independently RED (probe B). The AC-011 #4 block catches all three merge mistakes (probe C). Residuals are optional (N8, N9). |
| Traceability | 0.95 | 1.0 band, small deduction | Every REQ has an AC heading: AC-008→008+009, AC-009/010→010, AC-012→013, AC-013→012. No dangling REQ or AC id in any of the four files. plan.md cites AC-001/004/010/011/012, and all of them exist (probe R). |

Harmonic mean = 4 / (1/0.80 + 1/0.90 + 1/0.90 + 1/0.95) = 0.884.

## Per-defect status (iter-2 defects)

| Iter-2 | Class | Status | Evidence |
|---|---|---|---|
| N1 GATE-OTHER-RUN | blocking | FIXED | REQ-013 L165 splits the record check into a success form (outcome `complete`/`partial`) and a fabrication form (every other outcome), and explicitly allows honest `blocked`, outside-index `read`, and `no_results` for a `no_results` index. AC-012 L213-226 (3F/3S plus a per-outcome table) and spec §6 L179 agree. Probe A: all 9 rule-following other-run cases print `violations 0` (failed+blocked, failed+fallback read, meta-only failed+blocked, no_results+no_results, no_results+re-searched read, disabled+blocked, missing+blocked, missing+fallback read). All 5 fabricated other-run cases are RED. |
| N4 AC005-SIZE-REVERT | blocking | FIXED | REQ-005 L141 now requires rejecting a declared length "before reading any of the body". AC-005 (ii-a) asserts `본문 조각 읽힘 수 == 0`, and (ii-b) streams without a declared length. Probe B (my own stand-in on httpx 0.28.1 `MockTransport` with a chunk-counting `AsyncByteStream`): declared check removed → (ii-a) `chunks=2 -> RED`; stream check removed → (ii-b) `ok 2097153 bytes -> RED`; each revert RED independently. The numbers match progress P16 / AC L97, L99 (`body_chunks_read=2`, `ok 3145731 bytes`, `body_chunks_read=3`). |
| N2 CHECK3-VACUOUS | optional | FIXED | In success mode, an empty, missing, or string `source_ids` → `naver read entry has no source_ids`. A `read` entry plus extra `blocked` → `naver entries=2 …` (probe A). |
| N3 CHECK3-CRASH | optional | FIXED | `[7]` → `7: source id not in sources`, and `[None]` → `None: source id not in sources`. No traceback (probe A). |
| N5 RULENUM-PROSE-REF | optional | FIXED, but the fix introduces N9 | The AC-011 #4 block now scans in-text `N-M`. A stale `9-2` inside rule 10 → `line 32: in-text reference 9-2 inside rule 10` (probe C). plan §5 step 1 L91 adds the hand check for prose such as "9번 규칙". |
| N6 MERGE-OWNER | optional | ADDRESSED | plan §5 L87 assigns the lead to record the four steps on the integration card. Re-checked: 006 v0.2.0 still does not mention 007 (probe D), so the card is the only carrier. That is acceptable as stated. |
| N7 REQ-ORDER | optional | FIXED | REQ order is `001…014` (probe R). REQ-014 is now in §5.7, L169. |

## Defects Found (structured defect-list)

No blocking defects. All items below are optional, non-blocking debt.

N8. CHECK3-3F-NONLIST — acceptance.md:L273-278 — In 3F-only mode, a `read` entry whose `source_ids` is not a list (for example the string `"m1"`) is skipped by `continue`, so the F2 fabrication check never looks at it. Probe A, case "failed(meta-only): read claims metadata_only, ids as string" → `violations 0`. This cannot produce a false naver pass: the run is not a passing run (check 1 fails), and the audit's `read_ids` rejects a non-list (audit_report.py L22), so `LATEST_SEARCH_NAVER` stays. The only effect is that one fabrication shape goes unreported on a non-passing day. — Severity: minor — Class: optional — Required fix (optional): in the 3F branch, treat a non-list `source_ids` that is a string as `[source_ids]`, or emit `naver read entry source_ids is not a list` in every mode.

N9. RULENUM-CROSSREF-FALSE-POSITIVE (introduced by the N5 fix) — acceptance.md:L195-198, L208 — The new in-text check flags any `N-M` inside a rule whose first number is not the rule's own. That includes legitimate cross-references (`8-2` cited inside rule 9) and numeric ranges (`1-12`). Probe C: "review9 citing 8-2 + draft as 10" → `line 28: in-text reference 8-2 inside rule 9`; "range 1-12 in rule 9" → `line 26: in-text reference 1-12 inside rule 9`. REQ-011 L159 requires only that sub-item labels carry the parent number. It does not forbid cross-references, so the AC is stricter than the REQ. The SPEC constrains only its own Naver draft (L208). SPEC-006's rule 9 text is not drafted yet (probe D found no `N-M` in its spec/plan/acceptance rule descriptions), so a 006 rule citing DART rule `8-2`/`8-3`, which 006's receipt logic plausibly would, would make AC-011 #4 print an error on a correctly numbered merge. This fails safe: the merge is held, never falsely passed. — Severity: minor — Class: optional — Required fix (optional): restrict the in-text finding to references whose first number equals the renumbered rule's *old* number (for example, only `9-M` inside rule 10), or add to plan §5 step 1: "an in-text reference line pointing to a rule other than the renumbered one is checked by hand and recorded in progress.md, not treated as a failure".

N10. SUCCESS-FORM-NO-OPEN — spec.md:L157 vs L165 — REQ-010's "otherwise fall back … and record the actual result" also covers a `complete`/`partial` index where goose opened no `ok` file. REQ-013's other-run clause requires the success form for every `complete`/`partial` run, so such a run is a violation (probe A: "partial: only blocked" → `no naver read entry`). In practice, REQ-010 also obliges goose to open the `ok` files, and they are local, so this arises only if the Read tool itself fails. The gate fails safe. — Severity: minor — Class: optional — Required fix (optional): none needed. If desired, add one sentence to AC-012 L226: "a `complete`/`partial` run in which goose did not open any `ok` file is treated as non-compliance with REQ-010's first obligation".

O-H. HISTORY-COVERAGE — spec.md:L26 — The 0.3.0 row lists N1, N2, N4 and N7. N3, N5 and N6 are recorded in progress.md L9 but not in HISTORY. — Severity: minor — Class: optional — Required fix (optional): append "N3·N5·N6 (acceptance/plan)" to the row.

## Regression Check (iter-2 → iter-3)

- N1: RESOLVED (probe A, 9/9 rule-following other runs pass, 5/5 fabricated other runs RED).
- N4: RESOLVED (probe B, declared-only and stream-only reverts each RED).
- No item regressed. The REQ/AC numbering, frontmatter, lint, D7/D8/MP-7, the AC-009 baseline and the plan cross-references are unchanged or improved (probe R).
- Stagnation: no defect appears unchanged across all three iterations.

## Focus-area answers

1. N1/N4: fixed (see the table). I searched for a D1a-class hole, meaning a fabricated naver pass that check 3 accepts. In success mode, every fabrication shape I built was RED: a fabricated `no_results` alone or alongside a `read`; an extra `blocked`; two `read` entries; empty, missing, string, int or None ids; a metadata_only url; an outside url; a mix of ok and outside sources; a missing or wrong `text_file` in `read_scope`; missing `limitations`; no naver entry at all. The only accepted fabrication is goose claiming it opened an `ok` file it did not actually read. That is undetectable without a stream record, and spec §9 L216 and AC-012 L289 state it honestly. One non-passing-run blind spot was found (N8). One narrow strictness case was found (N10). Neither can produce a false pass.
2. N4: confirmed on my own stand-in. I added a third variant (declared > 2 MB with a 10-byte body): declared check removed → `ok 10 bytes chunks=1 -> RED`. So the declared-length revert goes RED whatever body size the run lane picks.
3. N2/N3/N5/N6/N7: all fixed or addressed (see the table). The N5 fix carries a new optional false-positive risk (N9).
4. Regression: lint clean, MP-1..MP-7 pass, numbering sequential, the nine AC-009 strings still at baseline 0 in the real harness (the dart control string is 2), all present in the plan draft, and no dangling REQ/AC references. The version is `0.3.0` in the spec frontmatter, the HISTORY last row, the plan header L3, the acceptance header L3, and the progress plan_status L6.
5. New defects: N9 (introduced by this revision, optional), N8 and N10 (pre-existing shapes surfaced by deeper probing, optional), O-H (cosmetic).

## Probe log (verbatim, 2026-10-21, worktree root, HEAD 991800f)

P-0. Tree state and threshold
```
$ git status --short; git rev-parse --short HEAD
?? .moai/logs/
991800f
$ git diff --stat efa8c88 991800f
 .moai/specs/SPEC-AI-REPORT-007/acceptance.md | 105 +++++++++++++++++++--------
 .moai/specs/SPEC-AI-REPORT-007/plan.md       |   6 +-
 .moai/specs/SPEC-AI-REPORT-007/progress.md   |  12 +--
 .moai/specs/SPEC-AI-REPORT-007/spec.md       |  14 ++--
 4 files changed, 95 insertions(+), 42 deletions(-)
$ grep -n "PASS threshold\|^| M (Medium)" <main>/.claude/rules/moai/workflow/spec-workflow.md
138:| Tier | Scope guidance (LOC) | Files affected | Artifact set | plan-auditor PASS threshold |
141:| M (Medium) | 300 - 1000 LOC | 5 - 15 files | **3 files**: spec.md + plan.md + acceptance.md | 0.80 |
$ grep -rn "audit_model" .moai/config/      (no output → Claude-only audit)
```

Probe A. AC-012 check-3 block, extracted verbatim from acceptance.md by regex and `exec`'d in memory, with `open`/`os.path.exists` redirected to synthetic JSON (`python3 -I .moai/state/verify/t19-audit-iter3/probe_check3.py .moai/specs/SPEC-AI-REPORT-007/acceptance.md`). Column 1 is the expectation: 0 = rule-following, R = must be RED, ? = exploratory.
```
check3 blocks: 1 lines: 47
0  good partial (2 ok read)                                       violations 0 | mode 3F+3S
0  good partial, opened only one ok                               violations 0 | mode 3F+3S
0  good complete + other Naver article in original_news           violations 0 | mode 3F+3S
R  partial: fabricated no_results (no read)                       violations 2 | mode 3F+3S |   naver no_results while index outcome=partial |   no naver read entry
R  partial: read + fabricated no_results                          violations 2 | mode 3F+3S |   naver no_results while index outcome=partial |   naver entries=2 (the read entry must be the only naver entry)
R  partial: read + extra blocked                                  violations 1 | mode 3F+3S |   naver entries=2 (the read entry must be the only naver entry)
R  partial: read source_ids []                                    violations 1 | mode 3F+3S |   naver read entry has no source_ids
R  partial: read source_ids missing                               violations 1 | mode 3F+3S |   naver read entry has no source_ids
R  partial: read source_ids string 'nv1'                          violations 1 | mode 3F+3S |   naver read entry has no source_ids
R  partial: read source_ids [7] (int, absent)                     violations 1 | mode 3F+3S |   7: source id not in sources
R  partial: read source_ids [None]                                violations 1 | mode 3F+3S |   None: source id not in sources
R  partial: read cites metadata_only url                          violations 1 | mode 3F+3S |   m1: url is not an ok index article_url
R  partial: read cites url outside index                          violations 1 | mode 3F+3S |   w1: url is not an ok index article_url
R  partial: read mixes ok + outside                               violations 1 | mode 3F+3S |   w1: url is not an ok index article_url
R  partial: read_scope missing text_file                          violations 1 | mode 3F+3S |   nv1: read_scope/limitations mismatch
R  partial: read_scope names wrong file (02 for 01)               violations 1 | mode 3F+3S |   nv1: read_scope/limitations mismatch
R  partial: limitations missing                                   violations 1 | mode 3F+3S |   nv1: read_scope/limitations mismatch
R  partial: only blocked (goose ignored ok files)                 violations 1 | mode 3F+3S |   no naver read entry
R  partial: no naver entry at all                                 violations 1 | mode 3F+3S |   no naver read entry
R  partial: two read entries                                      violations 1 | mode 3F+3S |   naver entries=2 (the read entry must be the only naver entry)
0  failed(empty): honest blocked                                  violations 0 | mode 3F only (outcome=failed)
0  failed(empty): fallback WebFetch read outside index            violations 0 | mode 3F only (outcome=failed)
R  failed(empty): fabricated no_results                           violations 1 | mode 3F only (outcome=failed) |   naver no_results while index outcome=failed
0  failed(meta-only): honest blocked                              violations 0 | mode 3F only (outcome=failed)
R  failed(meta-only): read claims metadata_only article           violations 1 | mode 3F only (outcome=failed) |   m1: url is not an ok index article_url
?  failed(meta-only): read claims metadata_only, ids as string    violations 0 | mode 3F only (outcome=failed)
0  no_results: goose no_results                                   violations 0 | mode 3F only (outcome=no_results)
0  no_results: re-searched, read outside                          violations 0 | mode 3F only (outcome=no_results)
0  disabled: blocked                                              violations 0 | mode 3F only (outcome=disabled)
R  disabled: fabricated no_results                                violations 1 | mode 3F only (outcome=disabled) |   naver no_results while index outcome=disabled
0  missing index: blocked                                         violations 0 | mode 3F only (outcome=missing)
R  missing index: fabricated no_results                           violations 1 | mode 3F only (outcome=missing) |   naver no_results while index outcome=missing
0  missing index: fallback read                                   violations 0 | mode 3F only (outcome=missing)
R  index without outcome key + no_results                         violations 1 | mode 3F only (outcome=None) |   naver no_results while index outcome=None
mismatches: 0 of 34
```

Probe B. AC-005 size design on my own stand-in fetcher: httpx `MockTransport`, `client.stream(...)`, a chunk-counting `httpx.AsyncByteStream`, and the two checks toggled (`/Users/byunjungwon/Dev/my_chart/.venv/bin/python -I .moai/state/verify/t19-audit-iter3/probe_size.py`). ii-a = declared 2097153 with a 3 × (1 MB+1) body. ii-a-short = declared 2097153 with a 10-byte body. ii-b = no declared length, 2 MB+1 streamed. ii-a passes only if `too large` and chunks == 0. ii-b passes if `too large`.
```
httpx 0.28.1
both checks       | ii-a: failed: too large (declared) chunks=0 -> PASS | ii-a-short: failed: too large (declared) chunks=0 -> PASS | ii-b: failed: too large (stream) chunks=3 -> PASS
declared removed  | ii-a: failed: too large (stream) chunks=2 -> RED | ii-a-short: ok 10 bytes chunks=1 -> RED | ii-b: failed: too large (stream) chunks=3 -> PASS
stream removed    | ii-a: failed: too large (declared) chunks=0 -> PASS | ii-a-short: failed: too large (declared) chunks=0 -> PASS | ii-b: ok 2097153 bytes chunks=3 -> RED
both removed      | ii-a: ok 3145731 bytes chunks=3 -> RED | ii-a-short: ok 10 bytes chunks=1 -> RED | ii-b: ok 2097153 bytes chunks=3 -> RED
```

Probe C. AC-011 #4 block, extracted verbatim and `exec`'d on the real harness plus the plan §4 draft rendered as rule 9/10 (`python3 -I .moai/state/verify/t19-audit-iter3/probe_rulenum.py`)
```
draft first line: 10. 백엔드가 goose 실행 직전에 네이버 증권 모바일 뉴스를 받아 `runs/<job_id>/naver
draft has 'N-2에서': True
real file                                                          rules [1, 2, 3, 4, 5, 6, 7, 8] | rule numbering ok
M4: real + draft as 9                                              rules [1, 2, 3, 4, 5, 6, 7, 8, 9] | rule numbering ok
merge: review9(clean) + draft as 10                                rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] | rule numbering ok
merge: review9 citing 8-2 + draft as 10 (rule-following 006 text)  rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] | line 28: in-text reference 8-2 inside rule 9
merge: draft left as 9 (dup)                                       rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 9] | top-level numbers not 1..K unique: [1, 2, 3, 4, 5, 6, 7, 8, 9, 9]
merge: top 10, labels 9-*                                          rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] | line 30: sub-item 9-* under rule 10 | line 31: sub-item 9-* under rule 10 | line 32: sub-item 9-* under rule 10 | line 32: in-text reference 9-2 inside rule 10 | line 33: sub-item 9-* under rule 10 | line 34: sub-item 9-* under rule 10 | line 35: sub-item 9-* under rule 10
merge: labels 10, prose 9-2 left                                   rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] | line 32: in-text reference 9-2 inside rule 10
date in text 2026-10-21                                            rules [1, 2, 3, 4, 5, 6, 7, 8, 9] | rule numbering ok
range 1-12 in rule 9                                               rules [1, 2, 3, 4, 5, 6, 7, 8, 9] | line 26: in-text reference 1-12 inside rule 9
```

Probe D. SPEC-AI-REPORT-006 current state (read-only `git show` of `86b7c0d` exported to the evidence folder, then grep)
```
$ git log --oneline -3 WT-goose-review-pass
86b7c0d docs(SPEC-AI-REPORT-006): plan 감사 1차 반영 v0.2.0 (카드 t18)
4663bb3 docs(SPEC-AI-REPORT-006): plan 단계 SPEC 초안 작성 (카드 t18)
7abdcac chore(SPEC-TEST-HERMETIC-001): sync_commit_sha 기록
$ grep -nE "규칙 ?(7|8|9|10)|…N-M…|SPEC-AI-REPORT-007|^version:|^phase:|^status:" 006-spec.md 006-plan.md 006-acceptance.md   (tail)
006-spec.md:4:version: "0.2.0"
006-spec.md:10:phase: "v0.6.0 target"
006-spec.md:69:| [MODIFY] | `backend/goose_harness_src/harness-instructions.md` | 규칙 7 개정, 감수 세션 규칙 9 추가 |
006-acceptance.md:139:  1. 지침 존재: `harness-instructions.md`가 (i) 규칙 7에서 … (ii) 규칙 9에서 `review/context.json` 읽기 …
006-acceptance.md:145:- 잡는 구현: (a) 규칙 9의 핵심 문구(`[렌더 차이]` 표지 문구 포함) 삭제 → #1 RED …
(no SPEC-AI-REPORT-007 match; no rule-sub-item N-M text drafted for rule 9)
```
Note: 006 is now at v0.2.0 (`86b7c0d`). 007's text still cites `4663bb3` and spec.md "65~67행". The current 006 spec has the harness line at L69. This is informational only: plan §5's merge steps do not depend on these line numbers.

Probe R. Regression (`python3 -I .moai/state/verify/t19-audit-iter3/probe_regress.py`; `moai spec lint .moai/specs/SPEC-AI-REPORT-007/spec.md`)
```
✓ No findings — all SPEC documents are valid
FM keys ['id', 'title', 'version', 'status', 'created', 'updated', 'author', 'priority', 'phase', 'module', 'lifecycle', 'tags', 'tier', 'related_specs']
FM version line ['version: "0.3.0"']
REQ order ['001', '002', '003', '004', '005', '006', '007', '008', '009', '010', '011', '012', '013', '014'] sorted-ok True dups False
AC order ['001', '002', '003', '004', '005', '006', '007', '008', '009', '010', '011', '012', '013', '014']
 AC-001 -> ['001'] … AC-008 -> ['008', '009'] AC-009 -> ['010'] AC-010 -> ['010'] AC-011 -> ['011'] AC-012 -> ['013'] AC-013 -> ['012'] AC-014 -> ['014']
REQs without AC heading ref: []
dangling in spec/plan/acc/progress: REQ [] AC []
plan AC refs ['AC-AIR7-001', 'AC-AIR7-004', 'AC-AIR7-010', 'AC-AIR7-011', 'AC-AIR7-012']
spec version 0.3.0 | spec HISTORY rows ['0.1.0', '0.2.0', '0.3.0'] | plan header 버전 0.3.0 | acc header 버전 0.3.0 | progress plan_status plan-audit 3회차 대기 (v0.3.0)
D7 SPEC-AI-REPORT-004 status: completed
D7 SPEC-AI-REPORT-005 status: completed
D7 SHOULD: referenced SPEC SPEC-AI-REPORT-006 not found in .moai/specs/
D7 SPEC-AI-REPORT-007 status: draft
D7 SPEC-TEST-HERMETIC-001 status: completed
D8 syscall counts [0, 0, 0, 0]
MP-7 NEEDS CLARIFICATION 0 research.md exists False
AC009 harness=0 plan_draft=2  runs/<job_id>/naver/index.json
AC009 harness=0 plan_draft=1  article_url
AC009 harness=0 plan_draft=1  channel: "naver"
AC009 harness=0 plan_draft=1  metadata_only
AC009 harness=0 plan_draft=1  "no_results"
AC009 harness=0 plan_draft=2  모바일 뉴스 API 응답의 제목·본문 필드
AC009 harness=0 plan_draft=1  서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음
AC009 harness=0 plan_draft=1  이번 세션에서 그 파일을 연 시각
AC009 harness=0 plan_draft=1  original_news
AC009 harness=2 plan_draft=0  runs/<job_id>/dart/index.json
weasel words in acc []
IF/THEN in REQ 0
```

## Gaps (what this audit did not observe)

- No network request. G1-G5 stand as the SPEC states them.
- The goose test suite was not run. AC-005 was probed on a stand-in fetcher, not the future module. A real module that reads the body through `client.get()` (non-streaming) would fail (ii-a) even with both checks present. That is the intended pressure toward REQ-005's streaming form, not a defect.
- Check 3 and the rule-numbering block ran on synthetic inputs only, not on a merged tree or live goose output. SPEC-006's rule 9 text does not exist yet, so N9's real impact is unknown.
- Cross-model backends were not invoked (no `audit_model` configured; Claude-only audit).

## Recommendation

PASS. Evidence for each must-pass criterion:
- MP-1: REQ-AIR7-001..014 sequential and unique (probe R).
- MP-2: every REQ in spec.md §5 matches a GEARS form, and REQ-013 is still a When-requirement after the N1 split (L165).
- MP-3: 12/12 canonical keys, quoted version, lint clean.
- MP-5/6/7: no D7 BLOCKING, syscall 0, no clarification markers.

The two iter-2 blocking defects are resolved by the observed probes A and B. The aggregate 0.88 clears the Tier M bar of 0.80.

Optional, non-blocking debt for the run lane or a later touch-up: N8 (3F non-list ids), N9 (cross-reference false positive in AC-011 #4, worth recording on the integration card next to the four merge steps), N10 (one clarifying sentence), O-H (HISTORY row). None of them can turn a failing gate into a passing one.
