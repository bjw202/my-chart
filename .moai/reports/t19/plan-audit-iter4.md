# SPEC Review Report: SPEC-AI-REPORT-007
Iteration: 4 (re-audit of v0.4.0 after run-phase M1; the 3-iteration plan-loop cap was already reached at iter-3)
Verdict: PASS-WITH-DEBT
Overall Score: 0.87 (harmonic mean; Tier M PASS threshold 0.80)
STOP signal (LEAN contract, literal application): the aggregate went from 0.88 (iter-3, v0.3.0) to 0.87. The dip comes from new v0.4.0 content (AC-008 revert, REQ-009 branch), not from a deteriorating revision loop. The 3-iteration cap is also already spent. Recommended orchestrator route: PASS-with-debt. Fold D-A..D-F into the run lane or a one-shot manager-spec touch-up. No further plan-audit loop.

Reasoning context ignored per M1 Context Isolation. The prompt's V1-V5 summary was used only as the list of claims to verify. Inputs: `.moai/specs/SPEC-AI-REPORT-007/{spec,plan,acceptance,progress}.md` at HEAD `d859edf`, the iter-3 report, recorded and synthetic fixtures under `backend/tests/fixtures/naver/`, `backend/routers/ai_report.py`, `backend/services/ai_report_service.py`, `my_chart/registry.py`, `backend/services/goose_job_service.py`, `backend/goose_harness_src/harness-instructions.md`, and the goose skills. Threshold source: the main checkout's `.claude/rules/moai/workflow/spec-workflow.md` L141 `| M (Medium) | … | 0.80 |`. No `audit_model` configured, so this is a Claude-only audit. No network requests were made.

## Must-Pass Results
- [PASS] MP-1: `REQ-AIR7-001 … 015`, sequential with no gaps and no duplicates. `AC-AIR7-001 … 015` likewise. Count 15/15 is within the Tier M limit of 16. Existing ids are unchanged, and 015 is appended.
- [PASS] MP-2 (judged on the requirement layer only, spec.md §5): REQ-015 (L203) is a compound Where clause with an embedded fallback, a valid GEARS compound. REQ-006 (L175) is still a When-requirement, now longer. REQ-008/009 (L181/L183) are When. The other REQs have the same forms as iter-3. The ACs are Given-When-Then (verification layer) and were not graded here.
- [PASS] MP-3: 12 canonical keys present, `version: "0.4.0"` quoted (L4), no rejected aliases. `moai spec lint` → `✓ No findings`.
- [N/A] MP-4: single-language (Python backend) SPEC.
- [PASS] MP-5 D7: unchanged from iter-3. 004, 005 and TEST-HERMETIC-001 are completed. 006 gives only a SHOULD finding ("not found", branch-only, explained at spec L29). No BLOCKING finding.
- [PASS] MP-6 D8: `syscall` count is 0 in all four files.
- [PASS] MP-7: no `[NEEDS CLARIFICATION` markers. There is no research.md (Tier M).

## Category Scores
| Dimension | Score | Band | Evidence |
|---|---|---|---|
| Clarity | 0.80 | 0.75 | REQ-006 L175 and REQ-010 L187 are single sentences of 250+ words. They resolve consistently, but slowly. REQ-015 L203 assigns the disabled-index `code_validated` field to "the Naver prefetcher", but REQ-003 L165 says the job service writes that index (D-D). |
| Completeness | 0.90 | 0.75-1.0 | All sections are present, and HISTORY has a 0.4.0 row (L27). §2.6/§2.7 add the observation tables. G4/G5 are marked observed, with the remaining gaps listed (L246-247). §9 adds two new residual risks (L253-254). The M2 fixture count is stated inconsistently (D-E). |
| Testability | 0.85 | 0.75-1.0 | Check 3 behaves as specified on 15 of my own cases. The V3 order reverts and the V1 `total`/first-group reverts are RED on real data. The AC-008 top-level-array revert is masked by a sibling check (D-A, observed on a stand-in). The second clause of REQ-009 has no test case (D-B). |
| Traceability | 0.95 | 1.0, small deduction | AC-015→REQ-015 is new. AC-009 covers the V2/V4 strings of REQ-010. AC-012 S3 covers the V2 limitations phrase of REQ-013. D3(b), the `read_scope` summary phrase, is traced only to rule text (AC-009), not to live output (D-C). |

Harmonic mean = 4 / (1/0.80 + 1/0.90 + 1/0.85 + 1/0.95) = 0.871.

## Per-item table
| Item | Status | Evidence |
|---|---|---|
| V1 flatten `[*].items[*]`, never group `total` | CONSISTENT | spec §2.6 L106-108, REQ-006 L175, REQ-007 L177 ("item count equal to the length of the flattened article list"), REQ-008/009/014, plan T1 L28, acceptance §A L13, §B L23, AC-006/007/008/014. Leftover grep: `items[]` survives only in progress §E.2 V1 (a historical M1 quote). `total` appears only as "not used". Probe 2: 020150 `flattened 10 sum(total) 22`, 000040 `flattened 10 sum(total) 10`, so the `total` revert is RED only on 020150, exactly as AC-006/007 say. |
| V2 summary as direct_read | CONSISTENT, enforcement partial (honestly disclosed) | D3 L130, REQ-010 L187, REQ-013 L195, §6 L210, §9 L253, plan T2/N-2, AC-009 (3 strings), AC-010 honest limit L186, AC-012 S3 + script `SUMMARY`. Old wording `제목·본문 필드` is gone (grep returned 0 hits). Phrase counts: spec 5 / plan 2 / acceptance 4. Details under "(4) What the SPEC can and cannot enforce" below. |
| V3 strip → decode → trim | CONSISTENT, verified | REQ-006 L175 (steps 1-3, named and numeric references), plan T3, AC-006 6/7 + reverts. Probe 2: `strip->decode: "'a' & <b>리터럴</b> 태그"` vs `decode->strip: "'a' & 리터럴 태그"`, so the order revert is RED as AC-006 L124 predicts. Entities in the real data: 020150 group 1 body, group 4 title (+ titleFull), 000040 group 3 body. This matches P17 and AC-006 6. |
| V4 always prefetch + `code_validated` | CONSISTENT. Deviation judged SOUND | D9 L136, §2.7 L117-122, REQ-015 L203, §B L21-22, plan T5/T9/N-3, AC-009 (2 strings), AC-015. Code probe: router L63 format check → 422, L70-71 `get_stock_name` → L73 404, L147 is the only production `.start(` call. `get_stock_name` (service L88-100) → `registry._name` (L145-154) → `get_stock_registry()` (L108-119, local xlsx, cached). `ai_report_service` imports only stdlib + `my_chart.registry._name`, and mentions `goose_job_service` 0 times (no import cycle). No listing or delisting words in registry.py. Why the deviation is sound: a "skip when unvalidated" branch could never run in production, because the router already 404s those codes. Skipping would also need a new outcome value. Recording the flag keeps the `no_results` note truthful for test and direct callers, and `no_results` itself stays gated by the index outcome (check-3 F1). Residual: in production the flag is effectively always `true`, and a delisted code still listed in the xlsx would read `true`. Both are disclosed (§9 L254, AC-015 "잡지 못하는 것"). |
| V5 ignore other keys; URL from validated ids | CONSISTENT, verified | REQ-006 L175 last sentence, AC-007 cross-check + `int(officeId)` revert. Probe 2: `mobileNewsUrl==built 10` and `ids regex 10` in both files. P19 shows the int revert gives 0/10 for 020150 and 1/10 for 000040, so the revert is RED on both. |
| N8 (3F non-list `source_ids`) | OPEN, optional | The script is unchanged apart from the 3 SUMMARY lines (block diff below). My case "N8 carry: failed(meta) read ids as string" → `violations 0`. It still cannot produce a false pass. |
| N9 (AC-011 #4 cross-reference false positive) | OPEN, optional | The AC-011 #4 block diff vs v0.3.0 has 0 lines. Not re-run, since the code is byte-identical. |
| N10 (success form with no file opened) | OPEN, optional | REQ-013 L195's other-run clause is unchanged. It fails safe. |
| O-H (HISTORY coverage) | Superseded | The 0.4.0 row is complete for V1-V5. The old 0.3.0 omission remains, and it is cosmetic. |

## (4) What the SPEC can and cannot enforce (strict-source + summary acceptance)
- No contradiction with DART semantics. In this harness, `direct_read` means "opened in this run" (`render_report.py:22` label `이번 실행 직접 열람`, `research-contract.md:20` `direct_read(이번 실행 직접)`). DART rule 8-2 (harness L19) uses the same "only files actually opened this session" test. A Naver summary file that goose opened meets that test. `read_scope` names the summary field and `limitations` states `원문 미확인`, so a summary is never presented as the full article. Strict-source D7 (only index `ok` entries in the `naver` channel) is orthogonal and unchanged.
- Machine-enforced (live, check 3 S3): every naver `read` source in a passing run carries both `서버 사전 수집본으로 열람` and the exact `API 요약본(약 150자), 원문 미확인`. A paraphrase (`API 요약 150자`) is RED. A missing phrase is RED.
- Enforced only as rule-text presence (AC-009, grep): `요약에 없는 사실은 단정하지 않는다`, the `read_scope` summary phrase, and the code-validated statement.
- Not enforced anywhere: whether goose's findings or the report body assert facts absent from the ~150-char summary. My case "source asserts fact beyond summary in findings" → `violations 0`. Nothing in the audit or check 3 reads claims against the summary. The SPEC says this honestly in §9 L253 ("기계로 검사하지 않는다(규칙 문구와 goose 판단에 맡김)"). So the summary acceptance can let goose assert unsupported facts without any check catching them. The only safeguard is disclosure (the `limitations` phrase) plus the instruction. This is a risk the user accepted (D3), not a SPEC defect.

## Defects Found (structured defect-list)
No BLOCKING defects.

D-A. AC008-TOPLEVEL-REVERT-MASKED — acceptance.md:L144 — SHOULD-FIX — Class: optional (fail-safe; §A L3 requires an unobserved revert to be logged as a Gap). AC-008 predicts that removing the top-level array check gives "`outcome != failed` or an exception → RED". With a dict top level, iteration yields the key strings. Each becomes a `group not an object` error, and the retained "non-empty array with no `items` array → failed" check then returns `failed` with a non-empty `search.error`. Both AC-008 assertions stay GREEN. Observed on a stand-in parser: `REVERT top-level check | failed | error: no group has items array | n_articles 2 | … PASS`. Only removing both checks goes RED. This is the same masking shape as iter-2's N4. Required fix: for `top_level_object.json`, also assert `articles == []` (the stand-in revert gives 2) or a top-level-specific `search.error` token (for example `not an array`), and correct the predicted RED reason.

D-B. REQ009-EMPTY-GROUPS-UNTESTED — spec.md:L183, acceptance.md:L141 — MINOR — optional. REQ-009's second clause ("every group holds an empty `items` array" → `no_results`) has no fixture. Both zero-article fixtures are `[]` (`zero_articles.json groups 0 []`, `999999_p1.json groups 0`). A revert that treats empty-`items` groups as malformed or `failed` would pass every AC. Required fix: add `synthetic/empty_items_groups.json` (`[{"total":0,"items":[]}, …]`) to AC-008's zero-article variants and to plan M2.

D-C. D3B-READSCOPE-NOT-LIVE — spec.md:L130 (b) vs L195 (3) — MINOR — optional. Condition (b) of the user's acceptance (`read_scope` names `제목·요약 본문 필드`) is checked only as harness text (AC-009). It is not checked on live output. My case "read_scope lacks 요약 본문 필드 phrase" → `violations 0`. Condition (a) is checked live. Required fix: either add the phrase to check-3 S3 (one `if strict and … not in read_scope` line), or state in §9 that (b) is instruction-only.

D-D. REQ015-ACTOR-SLIP — spec.md:L203 vs L165 — MINOR — optional. REQ-015 says "the Naver prefetcher shall record it as `code_validated` … (also in the `disabled` index)". Under REQ-003 the job service writes the disabled index without invoking the prefetcher. AC-015 (e) tests the outcome, so only the wording is wrong. Required fix: "…recorded in the index by whichever component writes it (the job service for the `disabled` index)".

D-E. M2-FIXTURE-COUNT — acceptance.md:L14 — MINOR — optional. §A says "M2가 더하는 5종". plan M2 L46 and the AC references name 4 new files (`top_level_object`, `mixed_malformed_groups`, `two_items_group`, `entity_body`). The "items가 문자열" shape lives inside `mixed_malformed_groups.json`. Required fix: "4개 파일(5가지 모양)". All 4 files are defined well enough for their reverts: AC-006 (4)/(5) and AC-008 spell out their contents.

D-F. AC009-TRUE-BRANCH-STRING — acceptance.md:L170-171 — MINOR — optional. AC-009 checks `서버가 종목코드 유효성을 확인하지 못함` (the false branch) but not the true-branch statement (`서버 종목 목록에 있는 종목코드`, plan N-3). Deleting the true-branch sentence would stay GREEN. Required fix: add that string with baseline 0.

Carried over (optional, unchanged): N8, N9, N10. See the per-item table.

Observation (not a defect): spec §2.6 L109 says the bodies end with `...`. The raw value is `"... "` (trailing space, 10/10 in both files), and `...` holds after the trim step of REQ-006.

## Regression Check (iter-3 → iter-4)
- No iter-3 defect was blocking. N8/N9/N10 are still open (optional). O-H is superseded.
- Nothing that passed at iter-3 regressed: lint is clean, MP-1..MP-7 pass, numbering is sequential, versions agree (spec L4, plan L3, acceptance L3, progress L3 all `0.4.0`), and the check-3 v0.3.0 behaviour is preserved, since the diff is +3 lines and only adds the S3 summary condition.
- Stagnation: N8/N9/N10 have been unchanged since iter-3 (2 iterations), not 3. All are optional.

## Probe log (verbatim; HEAD d859edf; worktree root)

P1. Structure and leftovers
```
141:| M (Medium) | 300 - 1000 LOC | 5 - 15 files | **3 files**: spec.md + plan.md + acceptance.md | 0.80 |
--- REQ headings
**REQ-AIR7-001 … **REQ-AIR7-015   (15, sequential)
--- AC headings
### AC-AIR7-001 … ### AC-AIR7-015   (15, sequential)
4:version: "0.4.0" ; acceptance.md:3 버전 0.4.0 ; progress.md:3 버전 0.4.0 ; plan.md:3 버전 0.4.0
--- leftover items[]
progress.md:86:| V1 | spec.md:78, … | 응답에 `items[]` 목록 하나(78행 …   (historical M1 quote only)
--- v0.5.5
progress.md:23 (resolved-Q1 history) ; spec.md:31 (states it was discarded)
--- old read_scope wording      (no output)
--- summary phrase counts  plan.md:2 spec.md:5 acceptance.md:4
--- syscall  0 0 0 0 ; NEEDS CLARIFICATION (no output) ; research.md: No such file
$ moai spec lint .moai/specs/SPEC-AI-REPORT-007/spec.md
✓ No findings — all SPEC documents are valid
```

P2. Recorded fixtures (`python3 -I -c`, json.load)
```
recorded/020150_p1.json list groups 10 flattened 10 sum(total) 22 items/group [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
  entity group 1 item 0 body ['&quot;', '&quot;']
  entity group 4 item 0 title ['&quot;', '&quot;']
  entity group 4 item 0 titleFull ['&quot;', '&quot;']
  body len 129 154 endswith ... : 0 endswith "... ": 10 / 10
  tags in body 0 newline 0
  mobileNewsUrl==built 10 ids regex 10
  plain body tail repr: '인투자자의...'
recorded/000040_p1.json list groups 10 flattened 10 sum(total) 10 items/group [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
  entity group 3 item 0 body ['&quot;']
  body len 131 154 endswith ... : 0 endswith "... ": 10 / 10
  tags in body 0 newline 0
  mobileNewsUrl==built 10 ids regex 10
  plain body tail repr: '세와 함께...'
recorded/999999_p1.json list groups 0 flattened 0 sum(total) 0 items/group []
strip->decode: "'a' & <b>리터럴</b> 태그"
decode->strip: "'a' & 리터럴 태그"
```

P3. Synthetic fixtures (tail)
```
mixed_status.json groups 3 [ok-body, body '', aid '../x']                 → AC-014 (a) partial as described
parse_cases.json groups 4 [body '', aid '../x', dt '2026102113', '<b>강조</b> …'] → AC-006 (2) / AC-014 (d) as described
all_metadata_only.json groups 10, all body ''                              → AC-014 (b)
missing_items_path.json groups 10, keys ['total'] only                     → AC-008
zero_articles.json groups 0 []                                             → same shape as 999999 (D-B)
referenced new (M2): entity_body, mixed_malformed_groups, top_level_object, two_items_group (4 files)
```

P4. V4 code (grep -n)
```
63:    if not _CODE_PATTERN.match(code):
70:    stock_name = get_stock_name(code)
71:    if stock_name is None:
73:            status_code=404,
147:    outcome = await get_goose_service().start(code, stock_name)
backend/routers/ai_report.py:147: …start(code, stock_name)   (only production .start( caller; others are comments / re.Match.start / thread.start)
ai_report_service imports: __future__, logging, os, re, unicodedata, datetime, pathlib, typing, `from my_chart.registry import _name`; grep -c goose_job_service → 0
registry.py: _name L145-154 df.query("Code == @x") … "NonName"; get_stock_registry L108-119 lazy _load_sectormap(); listing/delisting words → no output
```

P5. AC-012 check-3 block extracted verbatim (`exec` with in-memory `open`/`os.path.exists`)
```
check3 blocks 1 lines 50
0 complete good (both phrases)                          violations 0 | mode 3F+3S
R success: summary phrase missing                       violations 1 | mode 3F+3S | nv1: limitations lacks summary phrase
R success: only summary phrase, MARK missing            violations 1 | mode 3F+3S | nv1: read_scope/limitations mismatch
R success: summary phrase paraphrased (요약 150자)        violations 1 | mode 3F+3S | nv1: limitations lacks summary phrase
R success: cites metadata_only url w/ both phrases      violations 1 | mode 3F+3S | nv1: url is not an ok index article_url
R success: claims 02 file for url 01                    violations 1 | mode 3F+3S | nv1: read_scope/limitations mismatch
R success: fabricated no_results alongside read         violations 2 | mode 3F+3S | naver no_results while index outcome=partial | naver entries=2 (…)
? success: read_scope lacks 요약 본문 필드 phrase          violations 0 | mode 3F+3S
? success: source asserts fact beyond summary           violations 0 | mode 3F+3S
0 failed + fallback read outside index, no summary      violations 0 | mode 3F only (outcome=failed)
R failed(all metadata) + read claims metadata_only url  violations 1 | mode 3F only (outcome=failed) | nv1: url is not an ok index article_url
0 no_results + no_results w/ code_validated note        violations 0 | mode 3F only (outcome=no_results)
R disabled + fabricated no_results                      violations 1 | mode 3F only (outcome=disabled) | …
? N8 carry: failed(meta) read ids as string             violations 0 | mode 3F only (outcome=failed)
R missing index + fabricated no_results                 violations 1 | mode 3F only (outcome=missing) | …
```

P6. AC-008 revert stand-in (shape checks per REQ-006/008/014)
```
top_level_object | impl                     | failed | error: top-level not an array | n_articles 0 | …: PASS
top_level_object | REVERT top-level check   | failed | error: no group has items array | n_articles 2 | …: PASS
top_level_object | REVERT both checks       | failed | error: None | n_articles 2 | …: RED
missing_items_path | impl                   | failed | error: no group has items array | PASS
missing_items_path | REVERT any-items check | failed | error: None | RED
groups-all-empty-items (REQ-009 2nd clause) impl -> no_results
```

P7. Code-block diff vs iter-3 (`git show 9feb1fe:…/acceptance.md`)
```
# AC-AIR7-011 #4 — harness-ins diff lines: 0
# AC-AIR7-012 검사 3 — naver 기록과 diff lines: 3
    +SUMMARY = "API 요약본(약 150자), 원문 미확인"  # 3S에서만 요구(spec D3)
    +    if strict and SUMMARY not in str(x.get("limitations", "")):
    +        return [str(sid) + ": limitations lacks summary phrase"]
```

P8. direct_read semantics
```
render_report.py:22: VERIFICATION_LABELS = {"direct_read": "이번 실행 직접 열람", …}
research-contract.md:20: - verification: `direct_read`(이번 실행 직접), …
harness-instructions.md:19 (8-2): 이번 세션에서 실제로 연 파일만 … `verification: direct_read` … `limitations`에 "서버 사전 수집본으로 열람"
```

## Gaps (what this audit did not observe)
- No network request. G3/G6 stand as the SPEC states them.
- D-A was observed on a stand-in parser, not on the future module. A real module that records no group entries before the any-items check would give `articles == []` in both paths. The revert would still be GREEN, so D-A holds either way.
- The goose test suite was not run. The AC-011 #4 block was not re-run because its code is byte-identical to the block probed at iter-3.
- AC-015 (f) (production `_service.code_check` on the real xlsx) was not executed. The registry behaviour comes from reading the code plus progress P18.

## Recommendation
PASS-WITH-DEBT. All of MP-1..MP-7 pass (P1, P4). V1-V5 are consistent across the four files, and every observation-backed claim I re-measured matches the fixtures and the code (P2-P4, P7, P8). The V4 deviation is sound for the reason the author gives, which I confirmed at router L63/L70-73/L147. No defect can turn a failing gate into a passing one.
Debt to route (none blocking): D-A should be fixed before M2 writes the AC-008 tests, by adding the `articles == []` or top-level-token assertion. D-B..D-F and N8/N9/N10 are one-line touch-ups that can ride along with D-A or be logged as run-lane Gaps. Per the LEAN contract, do not run a fifth plan-audit loop for these.
