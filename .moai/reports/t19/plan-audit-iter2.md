# SPEC Review Report: SPEC-AI-REPORT-007
Iteration: 2/3
Verdict: FAIL (narrow — two blocking defects, both one-clause text fixes; the aggregate score clears the Tier M bar)
Overall Score: 0.85 (harmonic mean; Tier M PASS threshold 0.80; iter-1 was 0.81, so no regression and no STOP signal)

Reasoning context ignored per M1 Context Isolation. Inputs read: `.moai/specs/SPEC-AI-REPORT-007/{spec,plan,acceptance,progress}.md` at HEAD `7f80e28` (working tree clean except untracked `.moai/logs/`), iter-1 report `.moai/reports/t19/plan-audit.md`, `audit_report.py` L15-54, `harness-instructions.md`, SPEC-AI-REPORT-006 on branch `WT-goose-review-pass` (read via `git show`, read-only).

Tier M threshold source: the main checkout's `.claude/rules/moai/workflow/spec-workflow.md` L141, `| M (Medium) | 300 - 1000 LOC | 5 - 15 files | **3 files** ... | 0.80 |`.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: REQ-AIR7-001 to 014 are all present, with no gaps and no duplicates (probe P-F). REQ-014 sits between 007 and 008 in document order (spec.md L148). The numbering is still complete, so this is cosmetic.
- [PASS] MP-2 GEARS compliance (requirement layer only, the REQ entries in spec.md §5): 001 is a compound Where+When. 002/008/009/011/013 are When. 003 is Where. 004 is the negative ubiquitous form. 005/006/007/010/012/014 are ubiquitous. The new REQ-014 (L148), "The Naver prefetcher shall derive the index `outcome` as follows ...", is ubiquitous. The ACs are Given-When-Then, which is the correct verification-layer format, so they were not graded here.
- [PASS] MP-3 YAML frontmatter: spec.md L2-15 has all 12 canonical keys (`id title version status created updated author priority phase module lifecycle tags`) and `version: "0.2.0"` is quoted. Extra keys: `tier`, `related_specs`. No rejected aliases (probe P-F).
- [N/A] MP-4: single-language (Python backend) SPEC.
- [PASS] MP-5 D7: 004, 005 and TEST-HERMETIC-001 are `completed`. SPEC-AI-REPORT-006 gives a SHOULD-level "not found in .moai/specs/" because it lives only on branch `WT-goose-review-pass` (t18), not in this tree. That is expected and the SPEC explains it (spec.md L27). No BLOCKING finding.
- [PASS] MP-6 D8: `syscall` count is 0 in all four files.
- [PASS] MP-7: `[NEEDS CLARIFICATION` count is 0. There is no research.md (Tier M).

## Category Scores

| Dimension | Score | Rubric Band | Evidence |
|---|---|---|---|
| Clarity | 0.80 | 0.75 band | Most REQs are now exact: REQ-005 L140 names the `asyncio.wait_for` form, and REQ-014 L148 gives an ordered derivation. REQ-010 L158 is still one sentence of about 250 words with nine or more obligations, and it grew this round. REQ-013 L166's "check (3) shall also hold in every other run" conflicts with REQ-010's fallback path (N1). |
| Completeness | 0.90 | 0.75–1.0 | All sections are present. There are three `### Out of Scope — …` H3 headings with bullets (L182, L188, L194). 006 is named in `related_specs` (L15), in the relationship paragraph (L27) and in plan §5. Gaps G1-G5 and residual risk §9 are updated. |
| Testability | 0.80 | 0.75 band | The new scripts run as written and fail on the bad inputs claimed (P-B, P-C). The AC-005 timeout test is sound (P-D). Holes: the declared-length revert in AC-005 cannot go RED (N4), and check 3 fails runs that follow the rules on the fallback path (N1). |
| Traceability | 0.90 | 0.75–1.0 | Every REQ has an AC: 001-009→AC-001…008 (008 and 009 both map to AC-008), 010→AC-009/010, 011→AC-011, 012→AC-013, 013→AC-012, 014→AC-014. No orphans. plan.md cross-references are corrected (P-G). |

Harmonic mean = 4 / (1/0.80 + 1/0.90 + 1/0.80 + 1/0.90) = 0.847.

## Iter-1 defect regression check

| Iter-1 | Status | Evidence |
|---|---|---|
| D1a GATE-NORESULTS (blocking) | FIXED | REQ-013 (3) L166: "has zero `naver` entries with `result: "no_results"`". Check-3 script, run as extracted: replacing `read` with `no_results` → `violations 2 \| naver no_results while index outcome=partial \| no naver read entry`. A `read` entry plus an extra `no_results` → `violations 1` (P-C). |
| D1b GATE-CONSISTENCY (blocking) | FIXED, but the fix introduced N1 | REQ-013 L166 and AC-012 L206/L213 now state the same source rule (every `read` source url = an index `ok` `article_url`). "One and the same run" appears in both (L166, L204). The added clause "check (3) shall also hold in every other run" is the origin of N1. |
| D3 T18-COLLISION (blocking) | FIXED | `related_specs` L15 includes SPEC-AI-REPORT-006. D8 L107 leaves the rule number unfixed. plan §5 L85-92 lists four required merge steps, each with an observable result. AC-009 strings are number-free. 006 on `WT-goose-review-pass` still says "규칙 9 추가" (L66) and its AC text uses "규칙 9" (acceptance L138/L144); plan §5 step 2 covers that (P-H). |
| D4 AC005-TIMEOUT (blocking) | FIXED for the timeout. The size part is partially fixed (N4) | REQ-005 L140 requires `asyncio.wait_for` independent of the transport. AC-005 (iii) runs under an outer `wait_for(…, 2)`. Simulated: the implementation path gives `failed: TimeoutError`; removing the inner `wait_for` makes the outer `wait_for` raise `TimeoutError` → RED (P-D). The item-6 tautology was removed (L99). The size revert claim is false for the declared-length check (N4). |
| D5 OUTCOME-DERIVATION (blocking) | FIXED | REQ-014 L148, the §B table L24-31 and AC-014 L258-268 (fixtures a-d, with reverts) agree. They are also consistent with plan rule N-3/N-5 L67/L69, AC-012 check 1 and 3(b), and spec §6 L174-176. |
| D6 XREF-ERRORS (blocking) | FIXED | plan M4 now cites `AC-AIR7-010` and `AC-AIR7-011` (P-G). §5 step 2 says AC-009 is number-free. A4 note: every AC-009 string now has baseline 0 in the harness (except the `dart` control string, which is 2), and each appears in the plan rule draft (P-E). |
| D2 ID-RESERVATION | FIXED | progress P9a withdrawn in place, with the 4663bb3 timestamp. |
| D7 REQ013-TAUTOLOGY | FIXED | The "blocked" clause is gone from REQ-013 (P-G: `False`). |
| D8 ACCESSED-AT | FIXED | REQ-010 L158, plan N-2 L66, spec §6 L178. AC-009 checks `이번 세션에서 그 파일을 연 시각`. |
| D9 PHASE-LABEL | FIXED as an open question for the lead, as requested | spec L29 calls it a "미확정 가정", with progress Q1 L18 and plan §8 L107. The SPEC does not assert it as fact. |
| D10 T6-UNPROBED | FIXED | progress P10 L36. |

## Defects Found (structured defect-list)

N1. GATE-OTHER-RUN — spec.md:L166 (REQ-013, "check (3) shall also hold in every other run executed that day") + acceptance.md:L204 — Check 3 bundles (a) "at least one `naver` `read` entry" and (c) "every `read` source is an index `ok` article_url". Those are rules for the success path only. In a second run where the prefetch failed or found nothing, goose behaves exactly as REQ-010 L158 and plan N-5 L69 require, and check 3 still reports a violation:
- index `failed` with an honest `blocked` entry → `violations 1 | no naver read entry`
- index `failed` with a fallback WebFetch `read` of a Naver article (allowed by REQ-010 "fall back ... and record the actual result") → `violations 1 | nv1: url is not an ok index article_url`
- index `no_results` with goose writing `no_results` (REQ-010 explicitly allows this) → `violations 1 | no naver read entry`
- index `disabled` with `blocked` → `violations 1`

(probe P-C). So one API hiccup in run 1 blocks the gate even if run 2 passes everything. The gate cannot be made impossible this way, but REQ-013 contradicts REQ-010 and spec §6 L176. — Severity: major — Class: blocking (internal consistency of the gating criterion) — Required fix: limit the every-run clause to runs whose index `outcome` is `complete` or `partial`. For example: "and, in every other run executed that day whose index outcome is `complete` or `partial`, check (3) shall also hold". Alternatively, split check 3 into a fabrication check that applies to every run (no `no_results` while ok entries exist; no `read` source claiming an index file it does not match) and a success check that applies to the passing run only. Update AC-012 L204 and the script's preamble in the same way.

N4. AC005-SIZE-REVERT — acceptance.md:L85 + L97 — The text says removing only one of the two size checks turns only its own case RED ("하나만 지우면 그 하나에 해당하는 경우만 RED"). That is false for the declared-length check. The declared case's body really is 2 MB + 1, so the streaming accumulation check still rejects it. Simulated: both checks present → `failed: too large (declared)`; declared check removed → `failed: too large (stream)`, so the test stays green; both removed → `ok 2097153 bytes` (P-D). The declared-`content-length` check therefore has no revert that goes RED (lessons #9). — Severity: minor — Class: blocking (a stated revert property that does not hold; the run lane would hit it in M2) — Required fix: make the declared case discriminating. Either serve a response that declares `content-length` over 2 MB and assert that the body iterator was never consumed (byte or chunk counter == 0), or declare over 2 MB with a short body and assert `too large` before any read. Otherwise, restate the revert as "remove both checks → RED" and record the declared check as having no isolated revert.

N2. CHECK3-VACUOUS — acceptance.md:L229-236 — A `naver` `read` entry with `source_ids: []`, or with no `source_ids` key, passes check 3 (`violations 0`, P-C). In the passing run the audit catches it (`read_ids` returns False on an empty list, audit_report.py L22), but in the every-run clause it would pass. Separately, REQ-010's "it shall be the only `naver` entry" is not checked: a `read` entry plus an extra `blocked` naver entry gives `violations 0`. — Severity: minor — Class: optional — Required fix: in the script, add a violation when a `read` entry has no `source_ids`, and optionally when any non-`read` naver entry coexists with a `read` entry.

N3. CHECK3-CRASH — acceptance.md:L234 — A non-string source id (for example `7`) raises `TypeError` instead of printing a violation (P-C). This fails safe, because the first line is not `violations 0`, but the failure output is a traceback rather than a finding. — Severity: minor — Class: optional — Required fix: use `str(i)`.

N5. RULENUM-PROSE-REF — acceptance.md:L180-195 vs plan.md L67 — The rule-numbering script checks list labels only. A prose cross-reference such as "N-2에서" (plan N-3) that stays as `9-2` inside rule 10 after renumbering prints `rule numbering ok` (P-B, case "stale prose ref"). — Severity: minor — Class: optional — Required fix: either say in plan §5 step 1 that prose references must be renumbered by hand and grep them (`grep -n '9-[0-9]' harness-instructions.md` inside rule 10), or write the draft rule without prose sub-item references.

N6. MERGE-OWNER — plan.md:L85-87 — "The later-merged side performs the steps" places the obligation only in 007's documents. SPEC-AI-REPORT-006 never mentions 007 (no match on its branch, P-H). If 006 merges second, its implementer has no document telling them to do this. — Severity: minor — Class: optional — Required fix: the lead records the four steps on the integration card, or in 006's plan when 006 is next revised.

N7. REQ-ORDER — spec.md:L148 — REQ-014 is placed between 007 and 008. — Severity: minor — Class: optional — Required fix: none required. Moving it after 013 would read more naturally.

## Focus-area answers

a) Both scripts run as written. They were extracted verbatim from acceptance.md and executed in memory with `python3 -I -c`. The rule-numbering block prints `rules [1, …, 8] / rule numbering ok` on the real file. It catches a duplicate 9, a stale `9-6` label under rule 10, and a gap (1..8, 10); it does not catch stale prose references (N5). Check 3 gives `violations 0` on the good input and RED on all five claimed reverts. It misbehaves on the every-run clause (N1), passes empty source lists (N2), and crashes on int ids (N3).

b) The REQ-014 table, the §B table, plan rule N-3/N-5, AC-012 checks 1 and 3(b), AC-014, and spec §6 are mutually consistent. One wording quirk: `disabled` appears under the prefetcher's REQ although the job service writes it (REQ-003). It is clear in context.

c) The strict rule does not make the gate impossible: the passing path (goose opens `ok` files and cites them) is achievable. It does not conflict with the "read = goose opened the file this session" meaning either, because check 3 checks attribution, not the act of opening, and the SPEC says so honestly (§9 L212, AC-012 L244). Routing other Naver-family reads to `original_news` is safe: `original_news` is itself an audited channel (audit_report.py L39 `channels={'original_news'}`). The defect is only the every-run extension (N1).

d) Sound on Python 3.13.11 and httpx 0.28.1 (P-D). One small residual: the test covers a stall before headers. A body stream that stalls after headers is not tested, although REQ-005 bounds "send plus body read" (optional).

e) Each of the four merge steps has an observable output that is recorded in the later SPEC's progress.md. Weak spots: the ownership gap (N6) and the prose-reference blind spot (N5).

f) Revert checks: AC-009 (all nine strings at baseline 0, P-E), AC-012 (P-C), AC-005 timeout (P-D) and AC-011 #4 (P-B) really go RED. AC-005's declared-size revert does not (N4). AC-014's reverts follow from the fixtures: `not any(error)` on fixture (b) gives `complete`. AC-001/002/003/006/007/008/013 are unchanged from iter-1, where they were accepted.

g) The phase label is flagged as open question Q1 for the lead (spec L29, progress L18, plan L107), not asserted.

## Probe log (verbatim, 2026-10-21, worktree root, HEAD 7f80e28)

P-A. Tier threshold and tree state
```
$ grep -n "PASS threshold\|^| M (Medium)\|..." <main>/.claude/rules/moai/workflow/spec-workflow.md
138:| Tier | Scope guidance (LOC) | Files affected | Artifact set | plan-auditor PASS threshold |
141:| M (Medium) | 300 - 1000 LOC | 5 - 15 files | **3 files**: spec.md + plan.md + acceptance.md | 0.80 |
142:| L (Large) | > 1000 LOC or constitutional | > 15 files | **5 files**: ... | 0.85 |
$ git status --short; git rev-parse --short HEAD
?? .moai/logs/
7f80e28
$ grep -nE "^[0-9]+\. |^\s+- [0-9]+-[0-9]+" backend/goose_harness_src/harness-instructions.md | cut -c1-80
5:1. … 6:2. … 7:3. … 8:4. … 12:   - 4-1. … 13:   - 4-2. … 14:5. … 15:6. … 16:7. … 17:8. …
18:   - 8-1. … 19:   - 8-2. … 20:   - 8-3. … 21:   - 8-3a. … 22:   - 8-3b. … 23:   - 8-4. … 24:   - 8-5. … 25:   - 8-6. …
```

P-B. AC-011 #4 block, extracted verbatim from acceptance.md and run in memory (`python3 -I -c`, open() redirected to synthetic text for the cases)
```
python blocks: 2
real: rules [1, 2, 3, 4, 5, 6, 7, 8] | rule numbering ok
M4 (real+nav9) => rules [1, 2, 3, 4, 5, 6, 7, 8, 9] | rule numbering ok
merge ok (rev9+nav10) => rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] | rule numbering ok
merge dup 9,9 => rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 9] | top-level numbers not 1..K unique: [1, 2, 3, 4, 5, 6, 7, 8, 9, 9]
merge top10 sub 9-6 => rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] | line 30: sub-item 9-* under rule 10
merge gap 1..8,10 => rules [1, 2, 3, 4, 5, 6, 7, 8, 10] | top-level numbers not 1..K unique: [1, 2, 3, 4, 5, 6, 7, 8, 10]
stale prose ref 9-2 in rule 10 => rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] | rule numbering ok
sub-item without dot style 10-1) => rules [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] | rule numbering ok
```

P-C. AC-012 check-3 block, extracted verbatim and run in memory on a synthetic index (`partial`: one `ok`, one `metadata_only`) and on synthetic inputs
```
good partial                                                                violations 0
REVERT no_results instead of read                                           violations 2 |  naver no_results while index outcome=partial |  no naver read entry
REVERT url=metadata_only article_url                                        violations 1 |  nv1: url is not an ok index article_url
REVERT url outside index                                                    violations 1 |  nv1: url is not an ok index article_url
REVERT read_scope lacks text_file                                           violations 1 |  nv1: read_scope/limitations mismatch
REVERT limitations missing                                                  violations 1 |  nv1: read_scope/limitations mismatch
read + extra no_results                                                     violations 1 |  naver no_results while index outcome=partial
read + extra blocked naver entry                                            violations 0
read with empty source_ids only                                             violations 0
read missing source_ids key                                                 violations 0
other-run: outcome failed, goose honest blocked                             violations 1 |  no naver read entry
other-run: outcome failed, goose fallback WebFetch read (REQ-010 compliant) violations 1 |  nv1: url is not an ok index article_url
other-run: outcome no_results, goose no_results (REQ-010 compliant)         violations 1 |  no naver read entry
other-run: outcome disabled, goose blocked                                  violations 1 |  no naver read entry
int source id                                                               EXC TypeError("unsupported operand type(s) for +: 'int' and 'str'")
```

P-D. AC-005 timeout and size design, simulated with a minimal prefetcher on httpx `MockTransport` (venv python `-I`)
```
python 3.13.11 httpx 0.28.1
timeout impl     : failed: TimeoutError
timeout REVERT   : outer wait_for raised TimeoutError -> test RED
declared, both checks      : failed: too large (declared)
declared, declared removed : failed: too large (stream)
declared, both removed     : ok 2097153 bytes
```

P-E/P-F/P-G. D7, D8, MP-7, numbering, frontmatter, AC-009 baseline, fix checks (`python3 -I -c` over the four files)
```
D7 SPEC-AI-REPORT-004 status: completed
D7 SPEC-AI-REPORT-005 status: completed
D7 SHOULD: referenced SPEC SPEC-AI-REPORT-006 not found in .moai/specs/
D7 SPEC-AI-REPORT-007 status: draft
D7 SPEC-TEST-HERMETIC-001 status: completed
D8 syscall counts [0, 0, 0, 0]
MP-7 NEEDS CLARIFICATION matches 0
REQ ['001', '002', '003', '004', '005', '006', '007', '014', '008', '009', '010', '011', '012', '013']
AC  ['001', '002', '003', '004', '005', '006', '007', '008', '009', '010', '011', '012', '013', '014']
FM keys ['id', 'title', 'version', 'status', 'created', 'updated', 'author', 'priority', 'phase', 'module', 'lifecycle', 'tags', 'tier', 'related_specs']
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
REQ-013 blocked clause present: False
plan M4 refs: ['AC-AIR7-010', 'AC-AIR7-011']
```

P-H. SPEC-AI-REPORT-006 on the t18 branch (read-only `git show`)
```
$ git log --oneline -3 WT-goose-review-pass
4663bb3 docs(SPEC-AI-REPORT-006): plan 단계 SPEC 초안 작성 (카드 t18)
$ git show WT-goose-review-pass:.moai/specs/SPEC-AI-REPORT-006/spec.md | grep -n "^phase:\|^version:\|^status:\|규칙 9\|규칙 10\|harness-instructions\|goose-manifest\|SPEC-AI-REPORT-007"
4:version: "0.1.0"
5:status: draft
10:phase: "v0.6.0 target"
49:| D3 | … 바뀌는 하네스 파일은 `harness-instructions.md`와 매니페스트뿐이다 | …
66:| [MODIFY] | `backend/goose_harness_src/harness-instructions.md` | 규칙 7 개정, 감수 세션 규칙 9 추가 |
67:| [MODIFY] | `backend/goose_harness_src/goose-manifest.json` | 지침 변경에 따른 매니페스트 재생성 |
$ git show WT-goose-review-pass:.moai/specs/SPEC-AI-REPORT-006/acceptance.md | grep -n "9-[0-9]\|규칙 9"
138:  1. 지침 존재: … (ii) 규칙 9에서 `review/context.json` 읽기 …
144:- 잡는 구현: (a) 규칙 9의 핵심 문구 삭제 → #1 RED …
(no SPEC-AI-REPORT-007 match in 006 spec.md)
```

P-I. Audit facts used in (c) (Read of audit_report.py)
```
22:        if not isinstance(ids,list) or not ids:return False
39:    channels={'original_news'}
44:        channels.update({'company_ir','naver','industry'})
51:                if (s.get('result')=='read' and read_ids(s.get('source_ids'))) or s.get('result')=='no_results': matching.append(s)
```

## Gaps (what this audit did not observe)

- No network request. G3-G5 stand as the SPEC states them.
- The goose test suite was not run. AC-005/014 behaviour was simulated with a minimal stand-in prefetcher, not the future module.
- The scripts ran on synthetic inputs only, not on a merged tree or a live draft.
- Cross-model backends were not invoked (Claude-only audit).

## Recommendation (iteration 3 delta)

1. N1: in REQ-013 L166 and AC-012 L204, limit "check (3) in every other run" to runs whose index outcome is `complete`/`partial`, or split check 3 into an every-run fabrication part and a passing-run success part. Re-run the four "other-run" cases from P-C as the plan-phase observation.
2. N4: make the AC-005 declared-length case discriminating (assert the body was not consumed), or restate the revert honestly.
3. Optional: N2 and N3 (two-line script hardening), N5, N6, N7.

The re-audit will be scoped to N1 and N4 plus a regression check.
