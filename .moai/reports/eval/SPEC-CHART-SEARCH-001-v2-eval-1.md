# SPEC-CHART-SEARCH-001 v2.0.0 Independent Evaluation — Iteration 1

Evaluator: evaluator-active (skeptical mode)
Branch: feat/SPEC-CHART-SEARCH-001-v2
Commits: 4303fdd (test integration), 6f445fd (feat T10~T12), f17d8a0 (base cherry-pick)
Date: 2026-05-12

---

## Overall verdict: FAIL

---

## Per-dimension scores

| Dimension | Score | Verdict |
|-----------|-------|---------|
| Functionality (40%) | 28/40 | FAIL |
| Security (25%) | 25/25 | PASS |
| Craft (20%) | 13/20 | FAIL |
| Consistency (15%) | 14/15 | PASS |
| **Total** | **80/100** | **FAIL** |

---

## Anti-regression specific

| Point | Verdict | Evidence |
|-------|---------|----------|
| MP-1 | PASS | React.memo(ChartGridInner) confirmed at ChartGrid.tsx:304. ChartGrid does NOT call useScreen() directly — grep confirms 0 matches for `useScreen(` in ChartGrid.tsx (only comments). goToPage spy called correctly in cascade tests. |
| MP-2 | FAIL (theater test) | Cell key = stock.code confirmed at ChartGrid.tsx:280. Implementation is correct. BUT AC-INTEGRATE-006/ChartGrid.perf.test.tsx assertion `expect(countAAfterRerender).toBeGreaterThanOrEqual(countAAfterFirst)` is TRIVIALLY TRUE — it asserts "render count didn't decrease" which is always satisfied. No useEffect invocation count is tracked. This is a theater test. The critical invariant has no real automated guard. |
| MP-3 | PASS | grep: 0 matches for `applyFilters\s*(` in ChartGrid.tsx source. perf test line 361-376 static source grep also confirms 0 matches. integration test asserts `mockApplyFilters.not.toHaveBeenCalled()`. |
| MP-4 | PASS | grep: 0 matches for `applyFilters` or `setRequest` in ChartGrid.tsx. AppContent prop drilling pattern confirmed. AC-ARCH-001 static grep test passes. |
| MP-5 | PASS | Modal assets deleted (StockSearchModal.tsx, useFocusTrap.ts confirmed not present). git diff verifies: `ls frontend/src/components/ChartGrid/` shows no modal files. No new npm/pip dependencies introduced. |

---

## Test execution results

- Frontend vitest (ChartGrid-specific): 46/46 PASS (5 test files: ChartGrid.test.tsx, ChartGrid.integration.test.tsx, ChartGrid.perf.test.tsx, StockSearchBox.test.tsx, ChartCellRsBadge.test.tsx)
- Frontend vitest (total): 350/350 PASS (38 suites) — 2 Playwright e2e suites show as "failed" due to test runner misconfiguration (Playwright `test.describe()` called inside Vitest runner), pre-existing unrelated to this SPEC
- Backend pytest: 8/8 PASS (test_stocks_master.py)
- act() warnings: Present in all ChartGrid test renders (async state update from fetchStageOverview not wrapped in act). Tests pass despite warnings, but warning count is high enough to mask real issues.

---

## Findings

### High

**H-1: AC-INTEGRATE-002 must-pass — data-testid="chart-cell-injected-{code}" missing for scroll case**

File: `frontend/src/components/ChartGrid/ChartGrid.tsx` lines 267-273

Spec (acceptance.md line 241): "data-testid="chart-cell-injected-X"는 stock X의 기존 cell에 부여됨 (prepend cell이 아님)"
Spec (spec.md §4 Row 6 보충): "chart-cell-injected-{code}는 … 필터 결과에 이미 있던 cell이 검색 대상으로 식별되는 경우 동일 testid를 부여"

Implementation:
```
const isInjectedPrepend =
  injectedStock?.code === stock.code &&
  displayedStocks[0]?.code === stock.code &&       // ← FALSE when stock already in filterResults
  !enrichedFilterResults.some((s) => s.code === stock.code)  // ← FALSE

const testId = isInjectedPrepend
  ? `chart-cell-injected-${stock.code}`
  : undefined  // ← testid NOT assigned for scroll case
```

Consequence: When a stock already in filterResults is searched (scroll case), `data-testid="chart-cell-injected-{code}"` is never rendered. The spec explicitly requires it.

Compounding issue: ChartGrid.perf.test.tsx line 657 ASSERTS the wrong behavior:
```
expect(document.querySelector(`[data-testid="chart-cell-injected-${stockA.code}"]`)).toBeNull()
```
This test reinforces the wrong implementation. Any future fix will cause this test to fail until the test is also corrected.

AC-INTEGRATE-002 is a must-pass criterion. The test titled "AC-INTEGRATE-002: injectedStock이 filterResults에 있고 다른 페이지이면 해당 페이지로 이동" does NOT check the testid for the existing cell — only checks setCurrentPage() call. The spec requirement is not exercised.

**H-2: MP-2 theater test — AC-INTEGRATE-006 does not verify useEffect non-invocation**

File: `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx` lines 246-270

The test tracks `cellRenderCounts` (a render counter in the ChartCell mock), but the assertion is:
```
expect(countAAfterRerender).toBeGreaterThanOrEqual(countAAfterFirst)
```

This asserts "render count did not decrease," which is mathematically impossible to violate. It tells us nothing about whether useEffect was re-triggered. The spec's actual invariant (AC-INTEGRATE-006 / MP-2) requires zero additional useEffect calls for existing cells after prepend.

The implementation IS correct (key=stock.code ensures React reconciliation preserves instances), but this test cannot catch a future regression where someone changes cell keys to use index-based keys, or wraps cells in a re-keying container.

Given the history (SPEC-CHART-NAV-001 rollback was precisely a ChartCell useEffect mass-re-invocation event), this theater test is a critical gap.

### Medium

**M-1: AC-INTEGRATE-005 scenario (a) test asserts trivially true condition**

File: `frontend/src/components/ChartGrid/__tests__/ChartGrid.integration.test.tsx` lines 516-549

The test titled "filterResults reference 동일 시 ChartGrid cascade 없음" does a rerender with identical filterResults reference, then asserts:
```
expect(mockUseChartGrid.mock.calls.length).toBeGreaterThan(0) // only confirms initial render
```
This only confirms the component rendered at least once. It does NOT verify that the rerender with identical props did NOT trigger an additional useChartGrid call. The note at line 544-547 in the test itself acknowledges this: "vi.fn()으로 만든 onSelectStock은 매 rerender마다 새 reference → cascade 발생."

The test passes but proves nothing about React.memo cascade blocking.

**M-2: useEffect dependencies include `displayedStocks` — can re-trigger highlight on stageMap load**

File: `frontend/src/components/ChartGrid/ChartGrid.tsx` line 216

```
}, [injectedStock, displayedStocks, gridSize, goToPage])
```

`displayedStocks` depends on `enrichedFilterResults`, which depends on `stageMap`. When `fetchStageOverview()` resolves (async, after initial render), `setStageMap` fires → `enrichedFilterResults` changes → `displayedStocks` changes reference → useEffect fires again with `injectedStock` still set → `goToPage` called again + new setTimeout for highlight.

Result: If a user searches and the stageMap loads concurrently, the highlight will be re-applied (clearTimeout cancels first, new setTimeout starts), and goToPage is called again. Practically this means the highlight timing resets after stage data loads rather than after the search event. This creates a subtle but observable UX bug in the common case (stage data typically loads within 500ms of mount).

**M-3: Widespread act() warnings in all ChartGrid tests**

The `fetchStageOverview` mock resolves a Promise but state updates are not wrapped in `act()`. While tests pass, these warnings suppress real act() warnings and indicate the test render setup is incomplete for async state.

### Low

**L-1: @vitest/coverage-v8 not installed — cannot verify 85% threshold**

Running `npx vitest run --coverage` returns "MISSING DEPENDENCY Cannot find dependency '@vitest/coverage-v8'". Coverage for ChartGrid.tsx changes cannot be formally verified against the TRUST 5 85% target.

---

## Detailed AC Verification

| AC | Result | Evidence |
|----|--------|----------|
| AC-DATA-001 | PASS | pytest 8/8 |
| AC-DATA-002 | PASS | pytest 8/8 |
| AC-DATA-003 | PASS | pytest 8/8 |
| AC-DATA-004 | PASS | pytest test_stocks_master_service_readonly_rejects_write |
| AC-SEARCH-002 | PASS | useStockMaster.test.ts |
| AC-INTEGRATE-001 | PASS | integration test case A/B/C + goToPage(0) spy |
| AC-INTEGRATE-002 | FAIL | Core scroll+highlight works; testid="chart-cell-injected-X" NOT assigned for existing cell (H-1) |
| AC-INTEGRATE-003 (MP-3) | PASS | applyFilters: 0 calls confirmed by test + grep |
| AC-INTEGRATE-004 | PASS | CSS class applied + 2500ms timer verified with vi.useFakeTimers |
| AC-INTEGRATE-005 (MP-1) | PARTIAL | goToPage cascade verified; cascade-blocking (scenario a) test is trivially true (M-1) |
| AC-INTEGRATE-006 (MP-2) | UNVERIFIED | Cell key=stock.code confirmed in code; test is theater (H-2) |
| AC-ARCH-001 (MP-4) | PASS | grep + static test confirm 0 applyFilters calls |
| AC-ARCH-002 (MP-5) | PASS | Modal files deleted; no new deps |
| AC-ARCH-003 | PASS | StockSearchBox.test.tsx AC-ARCH-003 test passes |

---

## Recommendation

**FAIL → Required re-fixes before PASS:**

**Fix 1 (H-1 — required for must-pass AC-INTEGRATE-002):**
In `ChartGrid.tsx` lines 267-273, change testId assignment to cover both cases:
```
// BEFORE: only prepend case
const isInjectedPrepend = injectedStock?.code === stock.code && ...

// AFTER: both cases (prepend AND scroll)
const isInjectedTarget = injectedStock?.code === stock.code

const testId = isInjectedTarget
  ? `chart-cell-injected-${stock.code}`
  : undefined
```
Also update `isInjectedPrepend` variable name / logic for `data-highlight-target` to keep them separate.
Then update the test at ChartGrid.perf.test.tsx line 657 to assert the testid IS present (not null) for existing cells.
Add a new test in the integration file that verifies `data-testid="chart-cell-injected-X"` is present on existing cell in scroll case.

**Fix 2 (H-2 — required for MP-2 confidence):**
Replace the trivially-true assertion in `ChartGrid.perf.test.tsx` with a real key-invariant check. Concretely:
- Before rerender, record the DOM element reference for stockA: `const elemA = document.querySelector('[data-code="REUSE-A"]')`
- After rerender with stockX prepended, check `document.querySelector('[data-code="REUSE-A"]') === elemA`
- This verifies React preserved the DOM instance (no unmount/remount), which is the structural proof that useEffect didn't re-run for existing cells.

**Fix 3 (M-2 — recommended):**
Remove `displayedStocks` from the useEffect dependency array in ChartGrid.tsx. The effect only needs `injectedStock` to be correct:
```
// BEFORE:
}, [injectedStock, displayedStocks, gridSize, goToPage])

// AFTER (the displayedStocks is used inside via closure, doesn't need to be a dep
// because it's always computed from injectedStock + filterResults, and re-running
// whenever displayedStocks changes but injectedStock is stable is wrong behavior):
}, [injectedStock, gridSize, goToPage])
```
Note: The effect uses `displayedStocks.findIndex(...)` — this should be computed fresh each time injectedStock changes. If we remove `displayedStocks` from deps, React will use the stale closure value. This needs more careful analysis. Alternative: compute the target index directly from the ref or by recalculating inline with the current values. The safest fix is to compute targetIndex using `enrichedFilterResults` and injectedStock directly, avoiding the `displayedStocks` dependency.

Verdict: FAIL
