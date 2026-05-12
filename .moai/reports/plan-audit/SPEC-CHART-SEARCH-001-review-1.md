# SPEC-CHART-SEARCH-001 Audit — Iteration 1

Reasoning context ignored per M1 Context Isolation. This audit reads only `spec.md`, `plan.md`, `acceptance.md`, and `spec-compact.md`. `research.md` was opened but not used for verdict (contextual only).

## Verdict
PASS

## Summary

SPEC-CHART-SEARCH-001 is a well-structured, evidence-citing, anti-regression-aware specification that explicitly inherits the rollback lessons from SPEC-CHART-NAV-001 and re-routes the search feature through a portal-isolated modal pattern. All 15 REQs and 10 NFRs follow EARS patterns with no informal modal verbs, sequential numbering with no gaps, complete coverage by 27 Given/When/Then acceptance scenarios, and full Lesson #7 compliance (Live Use Hypothesis §2, Performance Baseline+Target §3, UI Mapping §4). All 5 must-pass criteria (MP-1..MP-5) have concrete vitest assertions with named measurement APIs (React Profiler, console.count, performance.now, DOM scope queryByTestId, deep-equal). External dependency invariant (zero new pip/npm) is triple-locked via NFR-CONST-001, MP-5, and AC-ARCH-002. Cherry-pick faithfulness from archive `feat/SPEC-CHART-NAV-001` is documented file-by-file in §6 Delta Markers and plan.md §5. Five minor improvement opportunities exist (latency description discrepancy, Q-7 vs REQ-MODAL-001 default conflict, API parameter ambiguity, missing modal-content node in UI Mapping, no warm-cache target for /api/stocks/master) but none block PASS.

## Findings

### Blocking defects (MUST fix before PASS)
None.

### Recommended improvements (non-blocking)

- I-1: spec.md §2.3 success signal 1 says `입력 시작 후 후보 노출 latency ≤ 80 ms`, but NFR-PERF-001 (spec.md L290) and §3.2 row 1 (L148) explicitly anchor the 80 ms measurement to `debounce 종료 시점 기준`. Since debounce is 150 ms (REQ-SEARCH-003), latency from `입력 시작` cannot be ≤ 80 ms physically. The narrative in §2.3 should read `debounce 종료 후 후보 노출 latency ≤ 80 ms` or `후보 계산 latency ≤ 80 ms` to match the locked-in NFR. — Location: spec.md §2.3 row 1 — Severity: minor — Suggestion: Reword to align with §3.2.

- I-2: Q-7 (spec.md L402) asks whether modal default timeframe should be `일봉` or `the user's last-viewed ChartGrid timeframe`, but REQ-MODAL-001 (L234) already commits to `default 일봉`. Either the Open Question is moot (REQ-MODAL-001 wins) or REQ-MODAL-001 should be relaxed pending Q-7 resolution. — Location: spec.md §5.2 REQ-MODAL-001 and §9 Q-7 — Severity: minor — Suggestion: Either remove Q-7 (decision is made) or change REQ-MODAL-001 to "default behavior pending Q-7".

- I-3: AC-MODAL-006 says `fetchChartData('005930', 'W') (또는 weekly)` — the test contract should be deterministic. The API parameter must be one specific string. — Location: acceptance.md L423 — Severity: minor — Suggestion: Pin the timeframe parameter to a single value (`'W'` or `'weekly'`) based on the existing chart-data API contract, then update the AC.

- I-4: spec.md §4 UI Element Mapping (13 rows) omits the `modal-content` (`tabIndex={-1}`) intermediary node referenced in AC-MODAL-002 (acceptance.md L356) as an initial focus target. Since the audit criterion requires "every UI element this SPEC adds/changes" be listed, this is a completeness gap. — Location: spec.md §4 — Severity: minor — Suggestion: Add row 14 `modal-content` with `data-testid="stock-search-modal-content"` and `tabIndex={-1}` annotation.

- I-5: NFR-PERF-004 specifies `GET /api/stocks/master` cold response time `< 150 ms` but does not specify a warm/cached target. With `Cache-Control: max-age=300`, the browser will serve from cache after first fetch; runtime measurement may always hit cache. — Location: spec.md L293 — Severity: informational — Suggestion: Either add a warm-response target (e.g., `≤ 20 ms from disk cache`) or explicitly note that the 150 ms cold target is measured with `Cache-Control: no-cache` request header in tests.

- I-6: plan.md §6 R-2 mitigation cites `useCallback` for `onSelectStock` to prevent ChartGrid prop reference changes when AppContent re-renders, but does not explicitly state that `ChartGrid` should be wrapped in `React.memo` to actually prevent re-renders. Without `React.memo`, useCallback alone does not stop reconciliation traversal. The plan defers the implementation strategy but the audit gate (commit count == 0) will catch any failure in T7/T8. — Location: plan.md §6 R-2 — Severity: informational — Suggestion: Add `React.memo(ChartGrid)` to the T6 GREEN strategy or document why it is unnecessary.

### Observations (informational)

- O-1: `issue_number: 0` in frontmatter is a placeholder. If GitHub issue tracking is desired, link the SPEC to a real issue; otherwise the field is benign.
- O-2: spec.md §3.1 Performance Baseline contains predictions (`예상 < 50 ms`), not actual measurements. The doc explicitly states baselines are to be measured at run-phase start. This is acceptable for a Draft SPEC but reviewers should not treat §3.1 numbers as locked-in baselines.
- O-3: Both `acceptance.md` Module 5 and `plan.md` T5 reference `df3ca36` (the rolled-back cancelled-flag pattern). The reuse of this pattern in a NEW modal chart instance is sound — the rollback was due to ChartGrid being overwritten, not because the race-guard pattern itself failed.
- O-4: All anti-regression must-pass criteria (MP-1..MP-5) are independently verifiable and do not overlap. MP-4 (DOM portal scope) is specifically the corrective lesson from SPEC-CHART-NAV-001 rollback — verified by AC-MODAL-001 with concrete `within(chartGridRoot).queryByTestId('stock-search-modal') === null` assertion.
- O-5: SPEC↔UI mapping (§4) uses unique `chart-search-*` and `stock-search-modal-*` data-testid prefixes that do not collide with any NAVER-THEME tab elements. Future user complaints about either UI surface will be traceable to this SPEC.

## Coverage matrix

| REQ | Has AC? | Must-pass mapped? | Notes |
|---|---|---|---|
| REQ-SEARCH-001 | Y (AC-SEARCH-001 + T6 integration) | — | Toolbar mount |
| REQ-SEARCH-002 | Y (AC-SEARCH-002, AC-SEARCH-007) | AC-SEARCH-002 must-pass | cachedPromise invariant |
| REQ-SEARCH-003 | Y (AC-SEARCH-001, 004, 005, 006) | — | Hangul + score matching |
| REQ-SEARCH-004 | Y (AC-SEARCH-008) | — | 0-result placeholder |
| REQ-SEARCH-005 | Y (AC-SEARCH-010) | — | Keyboard navigation |
| REQ-SEARCH-006 | Y (AC-SEARCH-007, 009) | — | 503 disabled state |
| REQ-MODAL-001 | Y (AC-MODAL-001, AC-SEARCH-003) | AC-MODAL-001 must-pass MP-4 | Portal mount |
| REQ-MODAL-002 | Y (AC-MODAL-003, 004, 005) | — | Close + focus return |
| REQ-MODAL-003 | Y (AC-MODAL-002) | — | a11y |
| REQ-MODAL-004 | Y (AC-MODAL-006) | — | Timeframe toggle |
| REQ-PERF-001 | Y (AC-PERF-001, 002, 003) | AC-PERF-001/002/003 must-pass MP-1/2/3 | Anti-regression |
| REQ-PERF-002 | Y (AC-MODAL-007, AC-MODAL-008) | AC-MODAL-007 must-pass | useEffect ≤ 1 + race guard |
| REQ-DATA-001 | Y (AC-DATA-001) | AC-DATA-001 must-pass | endpoint + ETag |
| REQ-DATA-002 | Y (AC-DATA-001, AC-DATA-004) | AC-DATA-004 must-pass | SELECT-only |
| REQ-DATA-003 | Y (AC-DATA-002, AC-DATA-003) | AC-DATA-002/003 must-pass | 503 |
| NFR-PERF-001 | Y (AC-PERF-004) | — | 80 ms latency |
| NFR-PERF-002 | Indirect (AC-MODAL-001 + AC-MODAL-007) | — | first-paint not directly tested |
| NFR-PERF-003 | Manual measurement only | — | FPS in plan §7.3 |
| NFR-PERF-004 | Manual / pytest timing | — | Endpoint cold time |
| NFR-PERF-005 | Manual diff | — | gzip payload |
| NFR-A11Y-001 | Y (AC-MODAL-002, 003) | — | WCAG 2.1 AA |
| NFR-A11Y-002 | Y (AC-SEARCH-010) | — | listbox ARIA |
| NFR-CONST-001 | Y (AC-ARCH-002) | AC-ARCH-002 must-pass MP-5 | Zero new deps |
| NFR-CONST-002 | Y (AC-DATA-004) | AC-DATA-004 must-pass | mode=ro URI |

Every REQ has at least one AC. NFR-PERF-002/003/004/005 are operational/manual measurements — acceptable for non-functional gates but flagged for run-phase instrumentation discipline.

## Must-pass results

- PASS MP-1 REQ numbering consistency — spec.md §5: REQ-SEARCH-001..006, REQ-MODAL-001..004, REQ-PERF-001..002, REQ-DATA-001..003. NFR-PERF-001..005, NFR-A11Y-001..002, NFR-CONST-001..002. No gaps, no duplicates, consistent zero-padding (3 digits).
- PASS MP-2 EARS format compliance — Verified each requirement: Ubiquitous (SHALL): REQ-SEARCH-001, 005; REQ-MODAL-003; REQ-DATA-001, 002. Event-Driven (WHEN…THEN…SHALL): REQ-SEARCH-002, 003; REQ-MODAL-001, 002. State-Driven (WHILE…SHALL): REQ-SEARCH-004 (spec.md L216). Optional (WHERE…SHALL): REQ-MODAL-004 (L249). Unwanted (IF…THEN…SHALL/SHALL NOT): REQ-SEARCH-006, REQ-PERF-001, REQ-PERF-002, REQ-DATA-003. EARS keywords appear in English even inside Korean prose, per spec.md L190.
- PASS MP-3 YAML frontmatter validity — id (string SPEC-CHART-SEARCH-001 L2), title (L3), status (Draft L4), version (1.0.0 L5), owner (bjw2002 L6), created (2026-05-11 L7), updated (L8), priority (High L9), issue_number (0 L10). All 8 required fields present with valid types/values.
- N/A MP-4 Section 22 language neutrality — This SPEC is scoped to a single product (`my_chart`, a Python/FastAPI + React/TypeScript stack), not a multi-language tooling system. Language neutrality requirement does not apply.

## Category scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.90 | 0.75–1.0 band | Every REQ has unambiguous interpretation; only I-1 (latency narrative) and I-2 (Q-7 vs REQ-MODAL-001) introduce mild interpretation conflict. spec.md §5 requirements use precise units (ms, KB, FPS) and named APIs. |
| Completeness | 0.95 | 1.0 band | HISTORY (L35), Overview WHY+WHAT (§1), Live Use Hypothesis (§2), Performance Baseline (§3), UI Mapping (§4), Requirements (§5), Delta Markers (§6), Anti-regression (§7), Exclusions (§8, 16 entries), Open Questions (§9), References (§10). One minor omission: modal-content node missing from §4 (I-4). |
| Testability | 0.95 | 1.0 band | Every must-pass has named measurement methodology — React Profiler (AC-PERF-001), console.count (AC-PERF-002, AC-MODAL-007), performance.now (AC-PERF-004), DOM scope queryByTestId (AC-MODAL-001), deep-equal (AC-PERF-003), static analysis (AC-DATA-004, AC-ARCH-003). One ambiguity: AC-MODAL-006 timeframe API parameter (I-3). |
| Traceability | 1.00 | 1.0 band | 15 REQs map to 27 ACs without gaps. AC-XXX entries each cite `REQ 매핑` field (acceptance.md L24, L106, L156, etc.). Anti-regression MP-1..MP-5 each maps to one or more ACs in §6, §7 of acceptance.md. |

Overall: 0.95 (rounded). Strong PASS.

## Lesson #7 compliance check

- [x] **Live Use Hypothesis present with all 4 elements** — Frequency §2.1 (per-session counts 1~10), Entry points §2.2 (3 entry candidates with adoption decisions), Success indicators §2.3 (4 success + 2 failure signals with measurement methods), Abandonment criteria §2.4 (rollback triggers: <0.5/session, >1000ms, ChartGrid perf regression, explicit user feedback).
- [x] **Performance Baseline + Target has measurable numbers** — §3.1 lists 5 baseline metrics with units (ChartGrid render <50ms, ChartCell mount <300ms, FilterBar render count 0, useEffect 1 call, FPS ≥55). §3.2 locks 7 targets with units (80ms, 300ms, 0 commits, 1 effect, 55 FPS, 150ms, 50KB). No vague language ("fast", "responsive", "acceptable") detected.
- [x] **SPEC ↔ UI mapping table covers every added element** — §4 lists 13 UI elements with location/text/data-testid/SPEC-relation columns. One minor completeness gap (modal-content node, I-4), but the core requirement is satisfied. All elements are namespaced (`chart-search-*`, `stock-search-modal-*`) to prevent naming confusion that caused the SPEC-CHART-NAV-001 rollback.

## Chain-of-Verification Pass

Second-pass re-read of `spec.md` §5 EARS requirements, `acceptance.md` Modules 1-7, and `plan.md` §3 task decomposition. Findings:
- One additional contradiction surfaced: REQ-MODAL-001 commits `일봉` default while Q-7 still asks the same question (now flagged as I-2). First-pass missed this.
- One additional API ambiguity surfaced: AC-MODAL-006 `'W' (또는 weekly)` (now flagged as I-3). First-pass missed this.
- One additional UI mapping gap surfaced: modal-content tabIndex={-1} (now flagged as I-4). First-pass missed this.
- One additional NFR scope gap surfaced: NFR-PERF-004 no warm-cache target (now flagged as I-5). First-pass missed this.
- One additional implementation-strategy gap surfaced: plan.md R-2 missing explicit React.memo (now flagged as I-6). First-pass missed this.

None of the second-pass findings rise to blocking severity. Verdict unchanged.

## Anti-bloat audit

- No requirement adds unjustified complexity. `useStockMaster` module-level `cachedPromise` is the only "non-obvious" pattern, justified by NFR-PERF and AC-SEARCH-002 cross-test pollution concern.
- No future-proofing hooks: ETF/foreign stocks (EX-15), Cmd+K (EX-9/Q-2), URL deep linking (EX-11), mobile UX (EX-16), alias dictionary (EX-8/Q-1) are all explicitly excluded.
- No trivial-test ACs: every AC tests a risky behavior (race condition, scope isolation, ARIA contract, performance commit count, SELECT-only invariant, ETag header presence).
- Open Questions Q-1..Q-7: Most are legitimate v1.0.0 deferrals (alias, Cmd+K, empty-state link, DbUpdateButton coordination). Q-4 (modal close + input reset) and Q-7 (default timeframe) are UX decisions that the author could have made — flagged but not blocking.

## Naming confusion prevention (cross-reference SPEC-CHART-NAV-001 rollback)

- §4 UI Element Mapping lists 13 elements with specific Korean text labels (`종목명/코드/초성 검색`, `검색 결과 없음`, `DB 업데이트 필요`, `일봉/주봉`, `닫기`, `DB 업데이트가 필요합니다`) and data-testid prefixes (`chart-search-*`, `stock-search-modal-*`).
- Data-testid namespace is distinct from anything in SPEC-NAVER-THEME-001/002/003 (`theme-*`, `naver-theme-*`) or the rolled-back SPEC-CHART-NAV-001 (which used filter-injection chips, not a portal modal).
- Future user complaints of the form "X UI showed up unexpectedly" can be traced via the table to either this SPEC or to existing SPECs. The mapping satisfies the Lesson #7 traceability mandate.

## Conclusion

Recommendation: PASS → proceed.

Rationale citing must-pass evidence:
- MP-1: REQ numbering verified across spec.md §5 — sequential and consistent (spec.md L194-298).
- MP-2: All EARS patterns verified — Ubiquitous/Event-Driven/State-Driven/Optional/Unwanted all present and correctly used.
- MP-3: YAML frontmatter all 8 required fields present (spec.md L1-L13).
- MP-4: N/A — single-language project.

The SPEC may proceed to annotation cycle with the 6 minor recommendations (I-1..I-6) as feedback to the author. I-1 and I-2 are the highest-priority recommendations (latency narrative inconsistency and REQ vs Open Question conflict). The remaining (I-3..I-6) are informational and can be deferred to v1.0.1 amendment if not addressed in annotation.

Verdict: PASS
