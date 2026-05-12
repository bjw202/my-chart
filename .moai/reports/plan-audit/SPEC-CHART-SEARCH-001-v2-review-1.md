# SPEC-CHART-SEARCH-001 v2.0.0 Audit — Iteration 1

Auditor: plan-auditor
Date: 2026-05-12
Iteration: 1 / 3
SPEC path: `.moai/specs/SPEC-CHART-SEARCH-001/`
Files audited: `spec.md` (447 lines), `acceptance.md` (499 lines), `plan.md` (316 lines)

Reasoning context ignored per M1 Context Isolation. Audit conducted as if SPEC were authored by a stranger.

## Verdict

**FAIL** (iteration 1, blocking on MP-3 frontmatter strict reading)

## Summary

The v2.0.0 amendment is a substantive, well-engineered redesign that responds to a documented mental-model-drift failure of v1.0.0 (modal pattern, PR #6 closed) and the earlier SPEC-CHART-NAV-001 rollback. The REQ/AC structure is rigorous: 11 EARS-formatted REQs spread across four namespaces (SEARCH, INTEGRATE, PERF, DATA) with 15 must-pass ACs traced explicitly, an updated UI element mapping with v1.0.0 modal artifacts struck through, and a five-layer anti-regression contract (MP-1..MP-5) re-derived for the integration pattern. Cherry-pick boundaries (v1.0.0 [EXISTING] vs v2.0.0 [REMOVE]/[MODIFY]/[NEW]) are unambiguous in plan §2. Lesson #7 mandates (live-use hypothesis, performance baseline+target, SPEC↔UI mapping, v3 fallback catalog) are all present. However, the YAML frontmatter does not satisfy MP-3 strict reading: `labels` is missing entirely and `created` does not match the canonical `created_at` field name. Additionally, REQ-PERF-001's secondary phrase about "other causes" is ambiguous regarding context-driven re-renders, and several NFRs lack AC traceability.

## Must-Pass Results

- **[PASS]** MP-1 REQ number consistency — Within each namespace numbering is sequential and gap-free: REQ-SEARCH-001..006 (spec.md:L236-258), REQ-INTEGRATE-001..004 (spec.md:L264-278), REQ-PERF-001..002 (spec.md:L282-288), REQ-DATA-001..003 (spec.md:L292-302). NFR sub-namespaces NFR-PERF-001..005, NFR-A11Y-001..002, NFR-CONST-001..002 also sequential (spec.md:L308-316). v1.0.0 REQ-MODAL-001..004 explicitly marked DEPRECATED at spec.md:L262, not a gap.

- **[PASS]** MP-2 EARS format compliance — All 11 REQs match exactly one of five EARS patterns. Sample evidence:
  - REQ-INTEGRATE-001 (spec.md:L266): "WHEN ... THEN the system SHALL inject ..." — Event-Driven
  - REQ-INTEGRATE-004 (spec.md:L278): "The system SHALL preserve ..." — Ubiquitous
  - REQ-PERF-001 (spec.md:L284): "IF ... THEN the system SHALL NOT trigger ..." — Unwanted Behavior
  - REQ-SEARCH-004 (spec.md:L250): "WHILE ..., the system SHALL render ..." — State-Driven
  EARS keywords (WHEN/WHILE/IF/THEN/SHALL) are uppercased English per project convention (spec.md:L232).

- **[FAIL]** MP-3 YAML frontmatter validity — Required `labels` field is absent from spec.md:L1-14. The `created_at` field is also absent; spec uses `created: 2026-05-11` (spec.md:L7) which does not match the canonical field name specified in the MP-3 contract. Two FC-class failures (FC-4 + FC-6) trigger MP-3 firewall.

- **[N/A]** MP-4 Section 22 language neutrality — SPEC targets a single-language stack (TypeScript/React frontend + Python backend) and is not template-bound multi-language content. Auto-pass per audit charter.

## Category Scores (rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.85 | between 0.75 and 1.0 | Every REQ has a single dominant interpretation; minor ambiguity in REQ-PERF-001 secondary clause ("다른 cause로 cascade 0회", spec.md:L284) regarding context-driven re-renders. AC scenarios use precise numeric thresholds (2400/2600 ms at acceptance.md:L266-272, baseline+1 at acceptance.md:L295-298). |
| Completeness | 0.80 | between 0.75 and 1.0 | All required sections present: HISTORY (spec.md:L37-44), WHY (§1.1/1.2/1.3), WHAT (§1.4), REQUIREMENTS (§5), ACCEPTANCE CRITERIA (delegated to acceptance.md), Exclusions (§8 with 17 EX entries). Penalty: frontmatter incomplete (`labels` missing, `created_at` named `created`). NFR-PERF-002/003/004/005 + NFR-A11Y-001 not traced to ACs (only listed in §3.2 measurement table). |
| Testability | 0.90 | between 0.75 and 1.0 | ACs are binary-testable with concrete numbers: AC-INTEGRATE-004 `advanceTimersByTime(2400)` class present, `advanceTimersByTime(2600)` class removed (acceptance.md:L266-272); AC-INTEGRATE-005 cascade count baseline+1/+0/+1 (acceptance.md:L295-298); AC-INTEGRATE-006 explicit `expect(callCounts.A).toBe(1)` for A/B/C and `D).toBe(1)` for prepended (acceptance.md:L319). AC-ARCH-001 specifies exact grep command (acceptance.md:L354). No weasel words in normative text. Minor: "2~3 seconds" range in REQ-INTEGRATE-002/003 (spec.md:L270, L274) is range-form, but AC concretizes to 2.5s. |
| Traceability | 0.80 | between 0.75 and 1.0 | All 11 functional REQs have ≥1 AC. AC list cross-references REQs explicitly. Acceptance.md §9 Must-pass Summary table maps all 15 must-pass ACs to source REQs. Penalty: NFR-PERF-002/003/004/005 and NFR-A11Y-001 are not mapped to formal AC scenarios — only listed in §3.2 measurement targets. AC-PERF-001/002/003 are cross-reference stubs that depend on AC-INTEGRATE-005/006/003 being implemented correctly. |

## Defects Found

### Blocking

- **D-1**: spec.md:L1-14 (frontmatter) — Required field `labels` is missing. MP-3 firewall: "Any missing required field = FAIL". Severity: critical (MP-3 strict reading triggers overall FAIL).

- **D-2**: spec.md:L7 — Field `created: 2026-05-11` does not match the canonical `created_at` name specified by MP-3 contract. Either rename to `created_at` or add `created_at: 2026-05-11` alongside. Severity: critical (MP-3 strict reading).

  Context note: prior v1.0.0 ship of this SPEC used identical frontmatter style and passed prior audits (per spec.md:L43 — "v1.0.0 Implemented, evaluator-active iter 2 PASS 84/100"). This suggests a project-wide convention deviation rather than a SPEC-specific defect. Fix is mechanical — add `labels: [search, chart-grid, integration]` and rename/duplicate `created` to `created_at`. Recommendation: also patch v1.0.0 frontmatter retroactively if `labels`+`created_at` are confirmed as MoAI baseline.

### Recommended (non-blocking)

- **I-1**: spec.md:L284 (REQ-PERF-001) — Secondary clause "다른 cause(filter change, theme change 등)로 인한 추가 cascade는 0회" is technically ambiguous. React.memo only blocks parent-cascade prop-driven re-renders; filter-change re-renders go through `useScreen()` context and bypass React.memo. The clause could mislead implementers/testers into expecting React.memo to block context-driven cascade. Recommend rewording to: "Within the search injection event window (no concurrent filter/theme change), ChartGrid commits beyond baseline are bounded by injectedStock prop change count alone." Severity: major.

- **I-2**: acceptance.md:L289-302 (AC-INTEGRATE-005) — Step (2) uses "AppContent의 다른 unrelated state 변경 (예: 다른 modal open)" as cascade-source stimulus. This is artificial. Real-world high-frequency cascade sources are FilterBar typing, ChartGrid currentPage change, theme switch. AC should test at least one of these (e.g., simulate `setCurrentPage(N+1)` without injectedStock change, verify ChartGrid commit count unchanged) to cover the practical regression surface. Severity: major.

- **I-3**: No AC statically verifies `key={stock.code}` invariant in ChartGrid's cell render. REQ-INTEGRATE-003 (spec.md:L274) and REQ-PERF-002 (spec.md:L288) both depend on this invariant being preserved. AC-INTEGRATE-006 (acceptance.md:L305-333) verifies it indirectly through useEffect call counts, but a static grep/AST assertion (e.g., `key={stock.code}` literal present, no `key={index}` regression) would be cheaper and more reliable. Add a static check analogous to AC-ARCH-001. Severity: major.

- **I-4**: plan.md:L133 (T11 GREEN) — Specifies `ref로 target cell outer container element 찾고 classList.add('cell-search-highlight')` but does not pin the ref mechanism. Two viable approaches differ materially: (a) cellRefs Map keyed by stock.code, (b) DOM querySelector by data-testid. Approach (b) is fragile across test environments and during transitions. Recommend specifying approach (a) and adding `cellRefs.set(code, ref)` to the T10 GREEN contract. Severity: minor.

- **I-5**: NFR-PERF-002/003/004/005 (spec.md:L309-312) and NFR-A11Y-001 (spec.md:L313) are not traced to ACs in acceptance.md. They appear only in §3.2 "Performance Target" table (spec.md:L178-187) which describes live-measurement procedures, not automated ACs. Add AC stubs (or mark NFR as live-only and document in §3 cross-reference) so traceability matrix is complete. Severity: minor.

- **I-6**: REQ-INTEGRATE-001 (spec.md:L266) and REQ-INTEGRATE-004 (spec.md:L278) contain implementation-level details (file paths `AppContent.tsx`/`ChartGrid.tsx`/`StockSearchBox.tsx`, state name `searchedStock`, prop name `injectedStock`). EARS convention prefers behavior/outcome (WHAT/WHY) at the REQ layer, with HOW deferred to plan.md. Given the brownfield context and the explicit regression-history (NAV-001 rollback driven by file-level confusion), this is defensible but should be flagged. Severity: minor.

- **I-7**: plan.md acceptance.md does not include an AC verifying that after a prepend event, ChartGrid auto-navigates to page 0 so the injected cell is visible. AC-INTEGRATE-001 (acceptance.md:L185-205) verifies array structure but not `setCurrentPage(0)` invocation. Compare AC-INTEGRATE-002 (acceptance.md:L208-229) which DOES verify `setCurrentPage(4)` for the existing-cell scroll case. Add symmetric assertion. Severity: minor.

### Observations (non-defects)

- **O-1**: §1.3 (spec.md:L61-94) is a thorough mental-model-drift retrospective. The 3-pattern comparison table (spec.md:L85-94) explicitly contrasts NAV-001 vs v1.0.0 vs v2.0.0 across 8 regression axes — meets Lesson #7 strengthening expectation.

- **O-2**: EX-2 (spec.md:L391) wording cleanly distinguishes "filters/request mutation prohibited" from "stocks array injection permitted" — directly addresses the NAV-001 rollback root cause. The same distinction is reinforced at REQ-INTEGRATE-001 (spec.md:L266), REQ-INTEGRATE-004 (spec.md:L278), and AC-INTEGRATE-003 (acceptance.md:L233-251).

- **O-3**: §4 UI Element Mapping (spec.md:L199-223) strikes through all 9 v1.0.0 modal data-testids (rows 213-222) and explicitly adds rows 6-7 (`chart-cell-injected-{code}`, `cell-search-highlight`). Row 6/7 supplementary explanations at spec.md:L224-226 cover both the prepend and existing-cell injection cases.

- **O-4**: §2.4 (spec.md:L150-156) defines four measurable rollback triggers including a v3.0.0 candidate catalog. Plan §8 (plan.md:L268-281) further enumerates Option A/B/C v3 fallback patterns. Lesson #7 "v3 fallback pre-staged" check satisfied.

- **O-5**: Plan §2 file delta matrix (plan.md:L57-99) uses unambiguous [EXISTING]/[REMOVE]/[MODIFY]/[NEW] tagging across 15 files. Cherry-pick vs rewrite boundary is clear.

- **O-6**: AC-INTEGRATE-004 (acceptance.md:L255-278) uses `vi.useFakeTimers` with precise `advanceTimersByTime(2400)` then `(200)` for total 2600 ms — concrete binary test of the "2~3 second" range stipulated in REQ-INTEGRATE-002/003.

- **O-7**: Plan §6 risk register (plan.md:L208-219) is up-to-date: R-1 (modal subtree leak) struck through as no longer applicable; R-10 explicitly captures the mental-model-drift recurrence risk with the live-validation mitigation. Lesson #7 lock-in is documented.

## Coverage matrix

| REQ | AC mapped? | Must-pass mapped? | Notes |
|-----|------------|-------------------|-------|
| REQ-SEARCH-001 | Yes (AC-SEARCH-001, AC-SEARCH-003) | AC-SEARCH-001 (#13 in §9 summary) | Search box mount + filter-bypass scenario |
| REQ-SEARCH-002 | Yes (AC-SEARCH-002, AC-SEARCH-007) | AC-SEARCH-002 (#5) | cachedPromise invariant |
| REQ-SEARCH-003 | Yes (AC-SEARCH-001, 004, 005, 006, 011) | AC-SEARCH-006 (#14), AC-SEARCH-011 (#15) | 5-stage score + alias + hangul |
| REQ-SEARCH-004 | Yes (AC-SEARCH-008) | — | "No results" placeholder |
| REQ-SEARCH-005 | Yes (AC-SEARCH-010, AC-SEARCH-012) | — | Keyboard navigation |
| REQ-SEARCH-006 | Yes (AC-SEARCH-007, AC-SEARCH-009) | — | 503 disabled state |
| REQ-INTEGRATE-001 | Yes (AC-INTEGRATE-001, AC-SEARCH-003) | AC-INTEGRATE-001 (#6) | prepend mechanism |
| REQ-INTEGRATE-002 | Yes (AC-INTEGRATE-002, AC-INTEGRATE-004) | AC-INTEGRATE-002 (#7) | scroll + highlight, no duplicate |
| REQ-INTEGRATE-003 | Yes (AC-INTEGRATE-001, AC-INTEGRATE-004, AC-SEARCH-003) | AC-INTEGRATE-001 (#6) | prepend stability + key invariant |
| REQ-INTEGRATE-004 | Yes (AC-INTEGRATE-003, AC-ARCH-001) | AC-INTEGRATE-003 (#8), AC-ARCH-001 (#11) | request deep-equal + static grep |
| REQ-PERF-001 | Yes (AC-INTEGRATE-005, AC-PERF-001 cross-ref) | AC-INTEGRATE-005 (#9) | React.memo cascade ≤ +1 |
| REQ-PERF-002 | Yes (AC-INTEGRATE-006, AC-PERF-002 cross-ref) | AC-INTEGRATE-006 (#10) | existing ChartCell useEffect 0회 |
| REQ-DATA-001 | Yes (AC-DATA-001) | AC-DATA-001 (#1) | endpoint shape |
| REQ-DATA-002 | Yes (AC-DATA-001, AC-DATA-004) | AC-DATA-004 (#4) | SELECT-only invariant |
| REQ-DATA-003 | Yes (AC-DATA-002, AC-DATA-003) | AC-DATA-002 (#2), AC-DATA-003 (#3) | 503 fallback |
| NFR-PERF-001 | Yes (AC-PERF-004) | — | 80 ms candidates latency |
| NFR-PERF-002 | **No formal AC** | — | Only §3.2 measurement target — I-5 gap |
| NFR-PERF-003 | **No formal AC** | — | Scroll FPS ≥ 55 (Playwright optional) — I-5 gap |
| NFR-PERF-004 | **No formal AC** | — | Cold start ≤ 500 ms — I-5 gap |
| NFR-PERF-005 | **No formal AC** | — | Payload < 50 KB — I-5 gap |
| NFR-A11Y-001 | **No formal AC** | — | Focus retained — I-5 gap |
| NFR-A11Y-002 | Yes (AC-SEARCH-010) | — | listbox ARIA + keyboard only |
| NFR-CONST-001 | Yes (AC-ARCH-002) | AC-ARCH-002 (#12) | external libs 0 |
| NFR-CONST-002 | Yes (AC-DATA-004) | AC-DATA-004 (#4) | SELECT-only |

## Lesson #7 strengthening check

- [x] Live Use Hypothesis present — §2.1 frequency table (spec.md:L114-119), §2.2 entry points (spec.md:L124-129), §2.3 satisfaction signals with explicit latency definition (spec.md:L131-146), §2.4 rollback triggers with v3 candidate catalog (spec.md:L148-156)
- [x] Performance numbers measurable — §3.1 baseline measurement procedure (spec.md:L162-172), §3.2 target table with 8 numerical thresholds mapped to REQ/NFR (spec.md:L174-188), §3.3 regression automation strategy (spec.md:L190-195)
- [x] UI element mapping complete — §4 table with 7 rows (5 reused + 2 new) at spec.md:L203-211, 9 v1.0.0 modal elements struck through at spec.md:L213-222, supplementary row 6/7 explanation at spec.md:L224-226
- [x] v2 변경 사유 명시 (mental model drift 사례) — §1.3 (spec.md:L61-94) 3-pattern comparison + history table (spec.md:L39-44) records NAV-001 rollback + v1.0.0 closure + v2.0.0 amendment trio. HISTORY row 4 (spec.md:L44) explicitly calls out "lesson #7 사례 — plan 단계 mental model이 라이브 가치와 어긋남."
- [x] v3 fallback 패턴 사전 명시 (sidebar / route / 폐기) — §2.4 mentions sidebar fixed panel + separate route candidates (spec.md:L156). Plan §8 §3 enumerates Option A (sidebar) / Option B (route) / Option C (feature abandonment) at plan.md:L272-275. EX-19 (spec.md:L407) re-affirms v3 candidates are explicitly scope-OUT of v2.

All five Lesson #7 mandates satisfied. The only critical gap remains MP-3 frontmatter strict-reading (D-1, D-2) which is mechanical to fix.

## Chain-of-Verification Pass

Second-look findings — re-read after initial draft:

1. **Re-verified REQ numbering end-to-end**: REQ-SEARCH-001..006, REQ-INTEGRATE-001..004, REQ-PERF-001..002, REQ-DATA-001..003. No gaps, no duplicates within namespaces. Section 5.3 explicitly labels REQ-PERF as "v2.0.0 재작성" (spec.md:L280) — re-numbered from 1 within its own namespace per project convention. Confirmed PASS for MP-1.

2. **Re-verified traceability for every REQ, not just sample**: 11 functional REQs all have ≥1 AC. 5 NFRs lack formal ACs (I-5 captured). No orphaned ACs found — every AC references a REQ that exists in spec.md.

3. **Re-checked Exclusions specificity**: §8 has 17 EX entries (EX-1..EX-19, skipping renumbered EX-8 implicitly). Each has a sufficient rationale. EX-2 wording is explicitly contrasted with NAV-001 failure mode. EX-16 explicitly preserves modal archive path. Not vague.

4. **Re-checked for contradictions between requirements**: REQ-INTEGRATE-001 ("inject... WITHOUT modifying ScreenContext filters") vs EX-2 ("filters/request mutation prohibited, stocks array injection permitted") — consistent. REQ-PERF-001 vs REQ-PERF-002 — complementary. REQ-INTEGRATE-002 (existing → scroll) vs REQ-INTEGRATE-003 (not existing → prepend) — branched on disjoint conditions, no overlap.

5. **Re-examined React.memo + key invariant claim**: AC-INTEGRATE-006 verifies useEffect non-re-invocation, which presupposes `key={stock.code}` stable identity. I-3 still applies — a static check would be more reliable than behavioral.

6. **Re-examined MP-1 cascade test (AC-INTEGRATE-005)**: Test stimulus "다른 modal open" is a narrow proxy for real-world cascade sources. I-2 still applies. However, the test IS sufficient to verify React.memo's prop-level shallow-equal blocking. Did NOT find a missed defect in this pass.

7. **Frontmatter re-read**: `id`, `version`, `status`, `priority`, `owner`, `created`, `updated`, `issue_number`, `replaces`, `depends_on`, `lifecycle`, `title` all present. `labels` definitively absent. `created_at` definitively absent (only `created`). D-1 and D-2 confirmed.

8. **New finding (chain-of-verification)**: AC-INTEGRATE-001 edge case at acceptance.md:L204 says "`injectedStock = null` 다시 set 시 prepend 되돌아감 (`displayedStocks = stocks` 복귀)". This implies the prepended cell will unmount when injection is cleared. The unmount should trigger ChartCell useEffect cleanup, which (for the prepended cell) involves chart instance disposal. AC-INTEGRATE-006 acceptance.md:L325-327 confirms this with `D는 unmount (useEffect cleanup 1회)`. Logically consistent but the chart-instance cleanup performance (e.g., does it leak chart resources?) is not formally verified. Not blocking — recorded as observation O-8.

- **O-8** (new): No formal AC verifies chart-instance disposal on prepended-cell unmount. The cleanup mechanism is mentioned only in passing. Severity: minor observation, not actionable for iteration 1.

No new blocking defects discovered in Chain-of-Verification pass. First-pass findings (D-1, D-2, I-1..I-7, O-1..O-8) are stable.

## Regression Check (Iteration 2+ only)

N/A — this is iteration 1.

## Recommendation

**FAIL on iteration 1**. Required fixes for iteration 2:

1. **D-1 fix**: Add `labels: [search, chart-grid, integration, regression-defense]` (or project-canonical label set) to spec.md frontmatter at spec.md:L13 (or wherever appropriate). MP-3 firewall blocker.

2. **D-2 fix**: Rename spec.md:L7 from `created: 2026-05-11` to `created_at: 2026-05-11`. If MoAI project convention prefers both, add `created_at` alongside `created`. MP-3 firewall blocker.

3. **I-1 fix (recommended for iteration 2)**: Rewrite REQ-PERF-001 secondary clause at spec.md:L284 to scope the "other causes" claim to the search-injection event window only, OR remove the secondary clause entirely and rely on AC-INTEGRATE-005 step (2) to enforce React.memo prop-stability.

4. **I-2 fix (recommended)**: Augment AC-INTEGRATE-005 step (2) at acceptance.md:L291 to test a realistic cascade source (e.g., simulate FilterBar typing or ChartGrid currentPage update without injectedStock change, verify ChartGrid commit count unchanged).

5. **I-3 fix (recommended)**: Add AC-ARCH-004 (static check) at acceptance.md §6 verifying `grep -E "key=\\{[^}]*\\.code\\}" frontend/src/components/ChartGrid/ChartGrid.tsx` returns at least one match, and `grep -E "key=\\{(index|i)\\}" frontend/src/components/ChartGrid/ChartGrid.tsx` returns zero matches.

6. **I-5 fix (recommended)**: Either add AC stubs for NFR-PERF-002/003/004/005 + NFR-A11Y-001, or annotate them in §3.2 as "live-only, no automated AC" with cross-reference back to the acceptance matrix.

7. **I-7 fix (recommended)**: Add to AC-INTEGRATE-001 a Then-clause: `setCurrentPage(0)` invoked exactly once when `injectedStock` is prepended, so the user sees the injected cell at the top of page 0.

If iteration 2 closes D-1 and D-2 (the only blocking defects), the SPEC is otherwise on the brink of PASS. I-1 through I-7 are quality-of-life improvements that strengthen the regression-defense posture but do not block run-phase entry on their own.

**One-paragraph rationale for FAIL**: The MP-3 firewall states unambiguously that any missing required frontmatter field forces a FAIL verdict regardless of other dimension scores. Both `labels` and `created_at` are absent from spec.md:L1-14. Per audit charter ("NEVER rationalize acceptance of a problem you identified"), this cannot be downgraded to an informational observation, even though the SPEC body is otherwise rigorous and meets Lesson #7 mandates. Once frontmatter is patched in iteration 2, the SPEC body would clear the bar with a PASS verdict.

Verdict: FAIL
