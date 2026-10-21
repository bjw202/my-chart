# SPEC Review Report: SPEC-AI-REPORT-007
Iteration: 1/3
Verdict: FAIL (narrow — two blocking defects, both in the live verification gate REQ-AIR7-013 / AC-AIR7-012; everything else is at or above the Tier M bar)
Overall Score: 0.81 (harmonic mean of the four dimensions; Tier M PASS threshold 0.80)

Reasoning context ignored per M1 Context Isolation. Inputs read: `.moai/specs/SPEC-AI-REPORT-007/{spec,plan,acceptance,progress}.md`, `.moai/reports/t19/investigation.md`, `.moai/reports/t19/a5becbb9-research-window.json`, the SPEC-AI-REPORT-005 precedent (via code it produced: `goose_job_service.py`, `goose_dart_prefetch.py`, harness rule 8), card t18's SPEC-AI-REPORT-006 in `.claude/worktrees/t18` (read-only), lessons #9/#10.

Audited tree: worktree `.claude/worktrees/t19`, branch `WT-naver-search-block`, HEAD `f8d7b85`, working tree clean apart from untracked `.moai/logs/`.

Tier M threshold source: the main checkout's `.claude/rules/moai/workflow/spec-workflow.md` L138-142 (`| M (Medium) | ... | 0.80 |`). The worktree copy of that file is older and has no tier table at all (the grep found no `PASS threshold` line in it). That is an environment note, not a defect of this SPEC.

## Must-Pass Results

- [PASS] MP-1 REQ number consistency: REQ-AIR7-001 through 013 run in sequence at spec.md L123, 125, 127, 129, 133, 137, 139, 143, 145, 149, 151, 155, 157. No gaps, no duplicates, consistent three-digit padding.
- [PASS] MP-2 GEARS compliance (judged against the requirement layer, `REQ-XXX` in spec.md §5 only): every REQ fits a GEARS pattern. 001 is a compound Where+When ("Where a Naver prefetcher has been injected ..., when a goose job's background task begins, the job service shall ..."). 002/006/008/009/011/013 are When. 003 is Where. 004 is the negative ubiquitous form ("shall emit no progress event"). 005/007/010/012 are ubiquitous. The ACs in acceptance.md are Given-When-Then, which is the correct format for the verification layer, so they were not graded here.
- [PASS] MP-3 YAML frontmatter: spec.md L2-13 carries all 12 canonical fields — `id`, `title`, `version: "0.1.0"` (quoted), `status: draft`, `created: 2026-10-21`, `updated: 2026-10-21`, `author`, `priority: High`, `phase`, `module`, `lifecycle: spec-anchored`, `tags` (comma-separated string). No rejected aliases. Extra keys `tier: M` and `related_specs` are harmless.
- [N/A] MP-4 language neutrality: single-language (Python backend) SPEC; auto-pass.
- [PASS] MP-5 D7 cross-SPEC: references are SPEC-AI-REPORT-004 (`completed`), SPEC-AI-REPORT-005 (`completed`) and SPEC-TEST-HERMETIC-001 (`completed`). None is retired, superseded or archived, so there is no BLOCKING D7 finding. There is a SHOULD-level gap: the SPEC never names SPEC-AI-REPORT-006 (card t18), which it collides with (see D3).
- [PASS] MP-6 D8: `syscall` occurs 0 times in all four files; auto-pass.
- [PASS] MP-7 clarification gate: `grep -rn '\[NEEDS CLARIFICATION' .moai/specs/SPEC-AI-REPORT-007/` found no match (exit 1). There is no research.md (Tier M).

## Category Scores

| Dimension | Score | Rubric Band | Evidence |
|---|---|---|---|
| Clarity | 0.80 | 0.75 band | Most REQs are crisp (005 sets exact URL, timeout, size and host rule). REQ-AIR7-010 (L149) is one ~170-word sentence carrying seven obligations. REQ-AIR7-013 (L157) contradicts AC-AIR7-012 3(i) (D1b). plan.md cites the wrong ACs in two places (D6). |
| Completeness | 0.85 | 0.75–1.0 | HISTORY L20, overview L30, evidence §2, decisions §3, DELTA §4, REQs §5, capability table §6, three `### Out of Scope — …` H3 headings with bullets (L171, L177, L183), Gaps §8, residual risk §9. Missing: SPEC-AI-REPORT-006 by ID (D3); `accessed_at` source in rule 9 (D8). |
| Testability | 0.75 | 0.75 band | Revert checks are mostly real and well-targeted (AC-001, 002, 003, 007, 008, 010, 013 — several confirmed against code below). Holes: the live gate passes on a fabricated `no_results` (D1a); AC-005 (iii) can hang because `MockTransport` ignores httpx timeouts, and (ii)/(iii)/host check have no revert (D4); the `outcome` derivation for mixed and all-`metadata_only` items is never asserted (D5). |
| Traceability | 0.85 | 0.75–1.0 | Every REQ has an AC: 001→AC-001 … 009→AC-008, 010→AC-009/010, 011→AC-011, 012→AC-013, 013→AC-012. No orphans. Deductions: AC numbering is offset from REQ numbering (012/013 swapped), and plan.md §3 M4 / §5 point at the wrong AC numbers (D6). |

Harmonic mean = 4 / (1/0.80 + 1/0.85 + 1/0.75 + 1/0.85) = 0.81. That is at the 0.80 threshold, but under M6 the blocking defects D1a/D1b must be fixed before the verdict is revisited. A high aggregate does not offset a gate that can close the SPEC on the very defect class it exists to prevent.

## Defects Found (structured defect-list)

D1a. GATE-NORESULTS — spec.md:L157 (REQ-AIR7-013) + acceptance.md:L159-162 (AC-AIR7-012) — The live gate can pass on a fabricated `no_results`. The audit accepts `result: "no_results"` without conditions (audit_report.py L51; probe A9 shows `no_results False`, i.e. no finding). AC-012 check 1 requires the index outcome to be `complete`/`partial`. Check 3 only inspects `naver` entries with `result == "read"`. So if goose writes `naver` = `no_results` while the server index says `complete`, all three checks pass, check 3 vacuously ("위반 0건"). That breaks the SPEC's own success criterion at spec.md L36 ("그 근거가 된 열람 기록이 사실과 일치"), and it breaks REQ-010's rule ("`no_results` only when the index outcome is `no_results`"). — Severity: critical — Class: blocking — Required fix: add to REQ-AIR7-013 and AC-AIR7-012 check 3 that, in the passing run, every `naver` entry with `result == "no_results"` requires index `outcome == "no_results"`. Because check 1 already requires `complete`/`partial`, that means zero `no_results` naver entries in the passing run. Also add the converse revert note: a hand-edited draft with `naver` = `no_results` must fail check 3.

D1b. GATE-CONSISTENCY — spec.md:L157 vs acceptance.md:L155, L162 — The REQ and the AC disagree. REQ-AIR7-013 requires that "every source cited by that `naver` entry shall map to an index entry with status `ok`". AC-012 3(i) also accepts a source that is "goose가 기존 방법으로 직접 연 다른 출처". AC-012 L155 also lets checks 1 and 2 be satisfied by "두 실행 중 하나", without saying it must be the same run. Run A could give outcome `complete` with the audit still failing, while run B gives a failed prefetch with a fallback that passes the audit. Neither run would show that the prefetch caused the pass. — Severity: major — Class: blocking (internal consistency of the gating criterion) — Required fix: pick one source rule and state it identically in both files. Recommendation: allow non-index sources only when the entry also cites at least one index `ok` source, or drop the allowance. State that checks 1, 2 and 3 must all hold in the same run, with check 3 additionally holding in every run executed.

D2. ID-RESERVATION — progress.md:L28 (fact P9) — P9 records "001~005만 존재(006·007 없음)" and `git log --all … | grep -c "AI-REPORT-00[67]"` → `0` at c8e5c20 (16:58:56). SPEC-AI-REPORT-006 does exist now: commit `4663bb3` at 17:10:50 in worktree t18, branch `WT-goose-review-pass`. The choice of 007 is therefore correct, but the fact table neither explains why 006 was skipped nor records that 006 belongs to t18. As written, P9 reads as "006 is free". — Severity: minor — Class: optional — Required fix: amend P9 in place (lessons #10, withdrawal recorded where it stands) with "006 reserved by card t18 (SPEC-AI-REPORT-006, commit 4663bb3)".

D3. T18-COLLISION — plan.md:L68-82, spec.md:L15/L173 — The overlap with t18 is handled only conditionally ("t18이 규칙을 더하면 번호가 겹칠 수 있다"). It is now certain. SPEC-AI-REPORT-006 spec.md L66 says "규칙 7 개정, 감수 세션 규칙 9 추가". Both SPECs add rule 9 to `harness-instructions.md`, both regenerate `goose-manifest.json`, and both modify `goose_job_service.py` `_run` (006 L65: post-run processing, progress events, a switch). This SPEC never names SPEC-AI-REPORT-006, so the cross-SPEC link is invisible to D7 tooling, and `related_specs` omits it. — Severity: major — Class: blocking (merge-time correctness: AC-009 greps literal `9-6`, and rule numbering decides which strings exist) — Required fix: name SPEC-AI-REPORT-006 in `related_specs` and plan §5. Either fix the rule number now (e.g. rule 10, or whichever lands second takes 10) or make AC-009's number string a parameter decided at merge, with the renumber step listed as a required action rather than a possibility. Add a line to plan §5 that 006's new progress events must not break AC-AIR7-004's with/without equality. They should not, since that comparison holds the other code paths fixed, but this should be re-run after merging.

D4. AC005-TIMEOUT — spec.md:L133 + acceptance.md:L72-85 — `httpx.MockTransport.handle_async_request` (httpx 0.28.1, probe A6) awaits the handler directly and never applies `httpx.Timeout`. If the prefetcher relies on httpx's timeout alone, which is the natural reading of REQ-005's "per-request timeout of 10 seconds", AC-005 (iii) hangs instead of turning RED, because AC-005 has no outer test bound (AC-002 has `asyncio.wait_for(..., 5)`; AC-005 does not). The DART precedent avoids this by wrapping the send in `asyncio.wait_for` (goose_dart_prefetch.py L376). Separately, (ii) size limit, (iii) timeout and item 6 host check carry no revert check. Item 6 tests a helper against a URL the module builds from a constant, which is close to tautological (lessons #9 shape 2). — Severity: major — Class: blocking for (iii) as a testability defect; optional for the item-6 note — Required fix: REQ-005 should state that the timeout bounds the whole request independently of the transport, as the DART precedent does. AC-005 should wrap (iii) in `asyncio.wait_for(..., 2)` and add reverts: remove the size check → (ii) `outcome != failed` RED; remove the outer timeout → (iii) hits the `wait_for` cap RED. Either drop item 6 or tie it to a revert that actually routes a request.

D5. OUTCOME-DERIVATION — acceptance.md:L23, L89-94, L183 — §B defines `complete`/`partial`/`failed` derivation, and §D claims "본문 없는 기사만 있음 → `outcome == "failed"` — AC-006, §B 판정". No AC asserts it. AC-006 (2)'s synthetic fixture mixes `metadata_only`, `error` and `ok` (which should yield `partial`) but asserts no `outcome`, and no fixture has items with zero `ok`. REQ-AIR7-007 lists the enum without the derivation rule. This matters because AC-012 check 1 and rule 9-5 both key on `outcome`. — Severity: major — Class: blocking (a stated criterion with no test) — Required fix: put the derivation into REQ-007 (or a new REQ) and extend AC-006 with `outcome == "partial"` for fixture (2), plus a fixture of all-`metadata_only` items asserting `outcome == "failed"`. Revert: map "items present, zero ok" to `complete` → RED.

D6. XREF-ERRORS — plan.md:L55 and L81 — plan §3 M4 says the audit-shape test is "AC-AIR7-009"; it is AC-AIR7-010. plan §5 says renumbering changes "AC-AIR7-008의 문자열 검사"; the string check is AC-AIR7-009. A run-phase agent following plan.md will touch the wrong test. — Severity: minor — Class: blocking (internal consistency, trivial fix) — Required fix: correct both references.

D7. REQ013-TAUTOLOGY — spec.md:L157 — "no `naver` search entry used for that pass shall have `result: "blocked"`" cannot fail: the audit never counts a `blocked` entry toward a pass (L51; probe A9 `v1_blocked True`). The clause adds no information. — Severity: minor — Class: optional — Required fix: delete it, or replace it with the D1a `no_results` consistency clause.

D8. ACCESSED-AT — plan.md:L62 (rule 9-2 draft) — Rule 8-2 fixes `accessed_at` = `fetched_at`. Rule 9-2 says nothing about `accessed_at`, yet `report-input.md` L37 says each source must carry `accessed_at` and `render_report.py` L117 checks it. The index has no per-article fetch time (only `started_at`/`finished_at`). goose will improvise: it may copy `published_at`, or use the server fetch time. — Severity: minor — Class: optional — Required fix: in rule 9-2, state `accessed_at` = the time goose opened the file in this session. That is accurate, because the server's fetch is not goose's read.

D9. PHASE-LABEL — spec.md:L10 — `phase: "v0.5.5 target"` follows the AI-REPORT series (004 `v0.5.3 target`, 005 `v0.5.4 target`). But the SPECs completed after 005 (TEST-HERMETIC-001, RS-REBALANCE-001) and t18's SPEC-AI-REPORT-006 are all `v0.6.0 target`. No version source in the repo pins any of these (pyproject `version = "0.1.0"`, frontend `0.0.0`, no `v*` git tags, only `moai/SPEC-*/sync-complete`). The label is therefore a free-text sequence and is out of order relative to 006 (007 < 006 in phase). — Severity: minor — Class: optional — Required fix: align with 006 (`v0.6.0 target`), or state the convention.

D10. T6-UNPROBED — plan.md:L29 — "새 단계는 프론트 3파일과 단계 목록을 고정한 기존 테스트 2개 수정을 부른다(005 M3 선례)" carries no probe in the fact table (lessons #10). A grep for `dart_prefetch` finds 3 frontend source files (`types/aiReport.ts`, `utils/gooseJob.ts`, `components/ProgressPanel.tsx`) plus 2 frontend tests, plus 2 backend test files. The claim is roughly consistent but unrecorded. — Severity: minor — Class: optional — Required fix: add the probe row to progress.md §E.1.

## Point-by-point answers to the requested focus areas

1. Codebase claims vs this tree: all fact-table probes P1–P8 reproduce (log below). Audit line numbers 21-28/44/50/51/52 are exact. `goose_job_service.py` L389 `prefetcher=goose_dart_prefetch.DartPrefetcher()`, the `_run` order (prefetch → integrity re-check → runner, L243-255), the `_prefetch` switch/emit/fail-open shape (L282-294) and `cancel`/`shutdown` (L364-379) all match what REQ-001/002/003 assume. Manifest regeneration `python -m backend.services.goose_harness` exists (`__main__` at goose_harness.py L323-324) and currently reproduces the committed manifest byte-for-byte (diff exit 0), so AC-011 #1's baseline is valid. The `claude-settings.json` sha equals the AC-011 #2 literal. P9 is stale (D2). T6 is unprobed (D10).
2. Revert checks: AC-001/002/003/007/008/010/013 have reverts that would really turn RED. AC-010 was probed against the production `audit()`: base has no `LATEST_SEARCH_NAVER`; v1 blocked, v2 `server_prefetch`, v3 empty `read_scope`, v4 25h and empty `query` each produce it (A9). That is not a self-comparison. Weak spots: AC-005 (D4), AC-006 outcome (D5), AC-012 (D1a/D1b).
3. Fabrication: the server writes no `sources` entry and no `searches` entry; the index lists only what was fetched (D2/T2). Empty body → `metadata_only` with no file (REQ-006). Zero items → `no_results` (REQ-009). Fetch failure → `failed` plus goose fallback, and `blocked` is never rewritten (REQ-008/010). The honest residual (audit does not check the host, so goose could claim `direct_read` without opening the file) is disclosed in §9, and probe A9 `foreign_host False` confirms it. The gap that remains is D1a: the gate does not catch a fabricated `no_results`.
4. Unobserved items: article-list JSON path (G4), body full-vs-summary (G4), markup (G4), `n.news.naver.com` resolvability (G5), actual block cause (G1), and sandbox WebFetch behaviour (G2) are all labeled Gaps (spec §8). REQ-006 defers the path to M1 rather than asserting it, and acceptance §B L24 makes the keys revisable via re-delegation. One addition: the goose note in the evidence file says the tool also blocked `m.stock.naver.com`. That supports the server-side choice, but it remains a model claim (G1 covers it).
5. t18 overlap: acknowledged but under-specified (D3).
6. Phase / ID: see D9 and D2. The ID 007 is correct because 006 exists in t18.
7. Scope vs DART precedent: the scope is proportionate — one request instead of up to 40, no shared-helper refactor (T8), no new progress stage, no frontend change, 13 REQs and 13 ACs against the Tier M ceiling of 16/16. The only over-engineering signal is AC-005 item 6, the host-check helper for a constant URL (optional, D4).

## Probe log (verbatim; run from the worktree root, 2026-10-21)

A1. P1 / P4–P7 batch
```
$ shasum -a 256 backend/goose_harness_src/claude-settings.json; grep -c '"WebFetch"' …; grep -c 'WebFetch(' …; grep -n "_GOOSE_PREFIXES = " backend/tests/conftest.py; ls backend/services/goose_naver_prefetch.py; grep -c naver backend/services/goose_job_service.py; grep -cF 'runs/<job_id>/naver/index.json' backend/goose_harness_src/harness-instructions.md; grep -cF 'runs/<job_id>/dart/index.json' …
e8b527ccaf01785377c8e0d9c2572ceaddb3ca906b0776801163487febd15df3  backend/goose_harness_src/claude-settings.json
1
0
20:_GOOSE_PREFIXES = ("test_goose_", "test_main_goose")
ls: backend/services/goose_naver_prefetch.py: No such file or directory
0
0
2
```

A2. Audit rule (cat -n of audit_report.py, excerpt)
```
    21	    def read_ids(ids, dart=False):
    26	            if s.get('verification')!='direct_read' or not str(s.get('read_scope','')).strip():return False
    27	            if dart and not (host=='dart.fss.or.kr' or host.endswith('.dart.fss.or.kr')):return False
    44	        channels.update({'company_ir','naver','industry'})
    50	            if s.get('channel')==channel and at and cutoff and 0<=(cutoff-at).total_seconds()<=86400 and str(s.get('query','')).strip() and str(s.get('note','')).strip():
    51	                if (s.get('result')=='read' and read_ids(s.get('source_ids'))) or s.get('result')=='no_results': matching.append(s)
    52	        if not matching:fail('LATEST_SEARCH_'+channel.upper(), … '… 차단은 완료가 아닙니다.')
```

A3. Job service wiring (grep -n, excerpt)
```
167:        prefetcher: Prefetcher | None = None,
238:    async def _run(self, job: Job) -> None:
243:            if self._prefetcher is not None:
244:                await self._prefetch(job)
246:                integrity = await asyncio.to_thread(self._integrity)
256:        except asyncio.CancelledError:
263:        except Exception:  # noqa: BLE001 - 실행기 밖 예외도 작업을 종료 상태로 닫는다
284:        if os.environ.get(ENV_DART_PREFETCH, "").strip() == "0":
290:        await self._emit(job, "progress", {"stage": "dart_prefetch", "detail": None})
293:        except Exception:  # noqa: BLE001 - fail-open(REQ-AIR5-010). CancelledError는 Exception이 아니라 전파된다
364:    async def cancel(self, job_id: str, reason: str = "cancel") -> Job | None:
376:    async def shutdown(self) -> None:
387:_service = GooseJobService(
389:    prefetcher=goose_dart_prefetch.DartPrefetcher(),
```

A4. AC-009 baseline — every rule-9 string currently absent (so the probe can see absence)
```
$ for s in … ; do printf '%s\t%s\n' "$(grep -cF "$s" backend/goose_harness_src/harness-instructions.md)" "$s"; done
0	article_url
0	channel: "naver"
0	metadata_only
0	"no_results"
1	서버 사전 수집본으로 열람
0	모바일 뉴스 API 응답의 제목·본문 필드
0	9-6
0	runs/<job_id>/naver/index.json
2	runs/<job_id>/dart/index.json
```
Note: `서버 사전 수집본으로 열람` is already 1, from rule 8-2. AC-009's revert-check claim ("앞의 8개 문자열 개수가 0으로 RED") is therefore false for that one string: after deleting rule 9 it stays 1. The other seven still go to 0, so the revert stays RED overall, but the stated expectation is inaccurate. That is a minor addendum to D6; fix by asserting a rule-9-unique string such as `서버 사전 수집본으로 열람, 기사 원문 페이지와 대조하지 않음`, or by counting ≥ 2.

A5. AC-011 #1 baseline — manifest regeneration reproduces the committed file
```
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -m backend.services.goose_harness > <scratch>/m.json; echo "exit=$?"; diff <scratch>/m.json backend/goose_harness_src/goose-manifest.json; echo "diff_exit=$?"
(pykrx pkg_resources UserWarning on stderr)
exit=0
diff_exit=0
```

A6. httpx MockTransport ignores timeouts (D4)
```
$ /Users/byunjungwon/Dev/my_chart/.venv/bin/python -I -c "import httpx,inspect; print(httpx.__version__); print(inspect.getsource(httpx.MockTransport.handle_async_request))"
0.28.1
    async def handle_async_request(self, request: Request) -> Response:
        await request.aread()
        response = self.handler(request)
        …
        if not isinstance(response, Response):
            response = await response
        return response
```
DART precedent: `goose_dart_prefetch.py:376: return await asyncio.wait_for(self._send(method, url, form, timeout), timeout)`.

A7. P2 on the main checkout's dev log
```
$ grep -c a5becbb9 …/.dev-server.log; … | grep -ci denied; … | grep -ci webfetch
3
1
0
2026-10-21 13:10:40,617 [WARNING] backend.services.goose_runner: goose 세션 permission_denied: 도구=Bash 사유=rule 명령=cd /Users/byunjungwon/.goose-harness/runs/a5becbb9b1a14483a1055c118d1b0be8/dart && for f
```

A8. Evidence file matches spec §2.1 verbatim (both copies)
```
== company-input.json / draft/report-input.json
cutoff 2026-10-21T13:15:00+09:00
  naver blocked 2026-10-21T13:13:00+09:00 ['naver_blocked']
{"channel": "naver", "searched_at": "2026-10-21T13:13:00+09:00", "query": "finance.naver.com/item/main.naver?code=020150 및 뉴스·모바일 API", "result": "blocked", "source_ids": ["naver_blocked"], "note": "검색 시각은 근사(±1분)입니다. 도구가 finance.naver.com, m.stock.naver.com, polling.finance.naver.com 접근을 차단했습니다. …"}
```

A9. AC-010 contract against production `audit()` (synthetic input; True = `LATEST_SEARCH_NAVER` emitted)
```
base False
v1_blocked True
v2_server_prefetch True
v3_empty_read_scope True
v4_25h True
no_results False
empty_query True
foreign_host False
```

A10. SPEC IDs, phases, t18
```
$ grep -h "^phase:\|^status:\|^id:" .moai/specs/SPEC-AI-REPORT-00*/spec.md .moai/specs/SPEC-TEST-HERMETIC-001/spec.md .moai/specs/SPEC-RS-REBALANCE-001/spec.md
SPEC-AI-REPORT-004 completed "v0.5.3 target" | SPEC-AI-REPORT-005 completed "v0.5.4 target" | SPEC-AI-REPORT-007 draft "v0.5.5 target" | SPEC-TEST-HERMETIC-001 completed "v0.6.0 target" | SPEC-RS-REBALANCE-001 completed "v0.6.0 target"
$ git worktree list
…/my_chart                        7abdcac [main]
…/.claude/worktrees/t18  4663bb3 [WT-goose-review-pass] locked
…/.claude/worktrees/t19  f8d7b85 [WT-naver-search-block] locked
$ git log --all --oneline | grep "AI-REPORT-00[67]"
4663bb3 docs(SPEC-AI-REPORT-006): plan 단계 SPEC 초안 작성 (카드 t18)
f8d7b85 docs(SPEC-AI-REPORT-007): plan 4종 작성 (네이버 뉴스 서버 사전 수집)
$ git log -1 --format='%h %ci' 4663bb3 / c8e5c20 / f8d7b85
4663bb3 2026-10-21 17:10:50 +0900 | c8e5c20 2026-10-21 16:58:56 +0900 | f8d7b85 2026-10-21 17:09:49 +0900
$ grep -n "^phase:" …/t18/.moai/specs/SPEC-AI-REPORT-006/spec.md ; grep -n "harness-instructions" …
10:phase: "v0.6.0 target"
66:| [MODIFY] | `backend/goose_harness_src/harness-instructions.md` | 규칙 7 개정, 감수 세션 규칙 9 추가 |
$ pyproject.toml:7:version = "0.1.0" ; frontend/package.json:4:"version": "0.0.0"; git tags: moai/SPEC-*/sync-complete only
```

A11. D7 / D8 / MP-7
```
SPEC refs: SPEC-AI-REPORT-004, SPEC-AI-REPORT-005, SPEC-TEST-HERMETIC-001 (all status completed), self
syscall count: 0 in all four files
grep -rn '\[NEEDS CLARIFICATION' .moai/specs/SPEC-AI-REPORT-007/ → no output, exit 1
```

A12. accessed_at (D8), stage-list claim (D10)
```
report-input.md:37: 각 source는 다음 문자열을 모두 갖습니다: `id`, `title`, `publisher`, `published_at`, `period`, `accessed_at`, `read_scope`, `findings`, `status`, `verification`.
render_report.py:117: for key in ("id", "title", "publisher", "published_at", "period", "accessed_at", "read_scope", "findings"):
dart_prefetch in frontend/src: types/aiReport.ts, utils/gooseJob.ts, components/ProgressPanel.tsx, utils/__tests__/gooseJob.test.ts, components/__tests__/ProgressPanel.test.tsx
```

## Gaps (what this audit did not observe)

- No network request was sent: G3/G4/G5 remain as the SPEC states them.
- The existing goose test suite was not run; the AC-013 baseline is left to run-phase M2 as specified.
- `test_air5_014_guard_records_attempt` exists (test_goose_dart_prefetch.py L862) but was not executed.
- Cross-model backends (`audit_multi`) were not invoked; this is a Claude-only audit.

## Recommendation (for manager-spec, iteration 2 delta)

1. D1a: add the `no_results` ↔ index-outcome consistency clause to REQ-AIR7-013 and AC-AIR7-012 check 3, with its revert.
2. D1b: make REQ-013 and AC-012 agree on non-index sources, and require checks 1–3 to hold in the same run.
3. D3: name SPEC-AI-REPORT-006 in `related_specs` and plan §5; state the rule-number resolution as a required merge step, and re-run AC-004 after merge.
4. D4: add the transport-independent timeout requirement to REQ-005; give AC-005 (iii) a `wait_for` cap; add reverts for size and timeout.
5. D5: move the `outcome` derivation into a REQ; assert `partial` and all-`metadata_only` → `failed` with a revert.
6. D6 plus the A4 note: fix plan.md L55/L81 AC references; replace the AC-009 string `서버 사전 수집본으로 열람` (already present from rule 8) with a rule-9-unique string.
7. Optional: D2, D7, D8, D9, D10.

The re-audit will be scoped to D1a–D6 plus the A4 note.
