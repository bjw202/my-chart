# SPEC-CHART-SEARCH-001 Independent Evaluation

Evaluator: evaluator-active (claude-sonnet-4-6)
Date: 2026-05-11
Branch: feat/SPEC-CHART-SEARCH-001

## Overall verdict: FAIL

## Per-dimension scores

| Dimension | Raw | Weight | Verdict | Key evidence |
|-----------|-----|--------|---------|--------------|
| Functionality (40%) | 68/100 | 27.2 | FAIL | Focus restoration broken; timeframe inheritance always 'daily'; loading/error UI absent |
| Security (25%) | 88/100 | 22.0 | PASS | Static SQL; mode=ro verified; React JSX XSS-safe; GET-only; no user-controlled path |
| Craft (20%) | 52/100 | 10.4 | FAIL | AC-MODAL-007 (must-pass) untested; AC-PERF-002 (must-pass MP-2) untested; theater test for MP-1 |
| Consistency (15%) | 80/100 | 12.0 | PASS | Portal pattern correct; naming consistent; AC-ARCH-003 enforced; no useScreen/useTab leak |
| **Total** | **71.6/100** | | **FAIL** | DoD explicitly requires AC-PERF-002 PASS; two must-pass criteria have zero tests |

---

## Functionality findings

### [F-1] CRITICAL — `triggerRef` in AppContent is never attached to a DOM element

**File:** `frontend/src/AppContent.tsx:32`

```typescript
const triggerRef = useRef<HTMLInputElement>(null)
```

This ref is passed to `StockSearchModal` as the `triggerRef` prop. Inside the modal, the unmount effect calls `triggerRef.current?.focus()` to restore keyboard focus. But `triggerRef` in AppContent is **never assigned** to any DOM element — it is always `null`.

The `searchBoxRef` (line 31) exposes `StockSearchBoxHandle` (`clearInput()` only). The actual `<input>` element inside `StockSearchBox` is private and never surfaced. As a result, REQ-MODAL-002 step 3 ("Restore keyboard focus to the StockSearchBox input element via a saved trigger ref") is silently broken.

No test catches this: `StockSearchModal.test.tsx` AC-MODAL-003 checks only that `onClose` was called, not that `document.activeElement` changed. The integration test in `ChartGrid.perf.test.tsx` calls `unmount()` directly, bypassing the focus-restore path.

### [F-2] HIGH — Timeframe inheritance always 'daily' — Q-7 decision not implemented

**File:** `frontend/src/AppContent.tsx:45-48`

```typescript
const handleSelectStock = useCallback((stock: StockMasterItem): void => {
  setSelectedStock(stock)
  setSelectedTimeframe('daily')   // <-- hardcoded, never reads ChartGrid timeframe
}, [])
```

REQ-MODAL-001 (Q-7): "모달의 초기 timeframe은 ChartGrid가 마지막으로 사용한 timeframe을 계승한다."

ChartGrid's `timeframe` state (line 41) is internal to `ChartGridInner`. The `onSelectStock` prop signature is `(stock: StockMasterItem) => void` — no timeframe argument is passed. Even if the user toggles ChartGrid to `weekly`, the modal always opens with `daily`.

The plan.md T6 GREEN specified: "`<ChartGrid onSelectStock={(stock, tf) => { setSelectedStock(stock); setSelectedTimeframe(tf ?? 'daily'); }} />`" and "`ChartGrid`의 현재 `timeframe` state를 `props.onSelectStock(stock, currentTimeframe)` 시그니처로 함께 전달" — but this was never implemented.

Tests pass because AC-MODAL-009 tests `StockSearchModal` directly via `initialTimeframe="weekly"` prop injection, not through the AppContent integration path. The actual user flow (AppContent → ChartGrid timeframe toggle → select stock → modal) always produces a 'daily' modal.

### [F-3] MEDIUM — Loading and error states missing from StockSearchModal

**File:** `frontend/src/components/ChartGrid/StockSearchModal.tsx:128-132`

The SPEC §4 rows 11 and 12 require `data-testid="stock-search-modal-loading"` (spinner during fetch) and `data-testid="stock-search-modal-error"` (fetch failure message). The implementation has:

```typescript
.catch(() => {
  // 차트 로드 실패는 silent — modal은 유지
})
```

No `loading` state is tracked, no error state is tracked. A user opening the modal over a slow network sees a blank chart area indefinitely with no feedback. A network failure produces no visible error.

The `data-testid` attributes required by the SPEC (testable UI contract) are absent. No tests cover this gap.

### [F-4] PASS — Core autocomplete functionality

**Evidence:** `npx vitest run` — hangul.test.ts (24/24), useStockMaster.test.ts (4/4), StockSearchBox.test.tsx (11/11), StockSearchModal.test.tsx (13/13), ChartGrid.perf.test.tsx (5/5). All 57 frontend tests green.

Prefix Korean (삼→삼성전자 score 3), code prefix (005→score 4), chosung (ㅅㅅㅈㅈ→삼성전자 score 1), English alias (samsung→삼성전자 score 5) all verified correct.

### [F-5] PASS — Backend endpoint

**Evidence:** `pytest backend/tests/test_stocks_master.py` — 8/8 PASS.

AC-DATA-001 (200 + ETag + Cache-Control + NULL exclusion), AC-DATA-002 (empty table → 503), AC-DATA-003 (no table → 503), AC-DATA-004 (mode=ro static check + write rejection) all pass.

### [F-6] PASS — Portal isolation (MP-4)

**Evidence:** `StockSearchModal.test.tsx` "ChartGrid subtree에 modal 없음" PASS. `ChartGrid.perf.test.tsx` MP-4 integration PASS. `document.body.querySelector('[data-testid="stock-search-modal"]')` is truthy; `within(chartGridRoot).queryByTestId('stock-search-modal')` is null.

### [F-7] PASS — Filter preservation (MP-3)

**Evidence:** `ChartGrid.perf.test.tsx` "useScreen.filters deep-equal 보존" PASS. `useScreen()` mock returns static filter object; modal mount/unmount does not mutate it. `applyFilters` spy called 0 times.

---

## Security findings (HARD)

### [S-1] PASS — SQL static, no injection surface

`backend/services/stocks_master_service.py:41-47`: All SQL is static string concatenation with no user-supplied fragments. The `daily_db_path` is sourced from `backend.deps.DAILY_DB_PATH` (server-side config), not from any request parameter.

### [S-2] PASS — SQLite read-only enforcement

`stocks_master_service.py:24`: `sqlite3.connect(f"file:{daily_db_path}?mode=ro", uri=True)`. Tested by `test_stocks_master_service_uses_mode_ro` (static source scan) and `test_stocks_master_service_readonly_rejects_write` (live INSERT attempt → OperationalError). Both PASS.

### [S-3] PASS — XSS

No `dangerouslySetInnerHTML` in StockSearchBox or StockSearchModal. All stock name/code rendering via JSX expressions (`{item.name}`, `{stock.code}`) which React escapes.

### [S-4] PASS — CSRF

GET-only endpoint. No state mutation on the server via this endpoint. CSRF not applicable.

### [S-5] PASS — No sensitive data disclosure

ETag exposes `MAX(stock_meta.last_updated)` — a timestamp, not sensitive data. `generated_at` in response body is current server time. No credentials, internal paths, or PII exposed.

---

## Craft findings

### [C-1] CRITICAL — AC-MODAL-007 (must-pass) declared but not tested

**File:** `frontend/src/components/ChartGrid/__tests__/StockSearchModal.test.tsx:10`

The file header declares `* AC-MODAL-007 (must-pass): useEffect 1회 호출` but the test file contains **zero tests** for this criterion. `grep "AC-MODAL-007\|console.count\|chart-effect\|effect.*count" StockSearchModal.test.tsx` returns only the comment line.

AC-MODAL-007 (must-pass per acceptance.md §5): "production 빌드 모드: console.count === 1; StrictMode dev 모드: console.count <= 2 허용." This invariant — that the modal chart's `useEffect` fires at most once per open — is the mechanism preventing the race-condition failure from SPEC-CHART-NAV-001. No test verifies it.

### [C-2] CRITICAL — AC-PERF-002 (must-pass MP-2) declared but not tested

**File:** `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx:8`

Header declares `* AC-PERF-002 (must-pass MP-2): ChartCell useEffect 재실행 0회` but the test file has zero tests for ChartCell useEffect call count. The acceptance criteria requires: "modal 열기 → modal 닫기 중 기존 ChartCell.tsx의 useEffect 호출 횟수 증가는 0회."

Definition of Done line 3 explicitly: "AC-PERF-001 / 002 / 003 PASS (must-pass — anti-regression)." AC-PERF-002 has no test. DoD cannot be marked met.

### [C-3] HIGH — MP-1 test (AC-PERF-001) is a theater test

**File:** `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx:254-308`

The test titled "selectedStock state 변경이 React.memo ChartGrid를 re-render하지 않음" contains:

```typescript
await act(async () => {});
const baselineCommits = gridCommitCount;

await act(async () => {
  // selectedStock state 변경은 ChartGrid props에 영향 없음 — React.memo가 차단해야 함
});

expect(gridCommitCount).toBe(baselineCommits);
```

The `act` block where `setSelectedStock(stock)` should be called is **empty**. The test asserts "after doing nothing, ChartGrid commit count is unchanged" — which is trivially true regardless of whether `React.memo` is applied. This test passes even if React.memo is removed entirely. The rollback scenario (AppContent re-renders → ChartGrid subtree re-renders) is never exercised.

### [C-4] MEDIUM — Chart fetch errors silently discarded

**File:** `frontend/src/components/ChartGrid/StockSearchModal.tsx:128-132`

```typescript
.catch(() => {
  // 차트 로드 실패는 silent — modal은 유지
})
```

User sees a permanently empty chart container. SPEC §4 rows 11-12 define required `data-testid="stock-search-modal-loading"` and `data-testid="stock-search-modal-error"` testids that are absent from the implementation.

### [C-5] LOW — `useFocusTrap` listener registered on `document` at component mount only

**File:** `frontend/src/components/ChartGrid/useFocusTrap.ts:22`

The effect has `[containerRef]` as deps. If the containerRef DOM subtree changes (e.g., buttons are added after mount), the focus trap's snapshot of `focusable` elements becomes stale. For this specific modal with static buttons, the risk is low. However it's a correctness concern for maintainability.

---

## Consistency findings

### [Con-1] PASS — Portal pattern follows AnalysisModal

`StockSearchModal.tsx:252`: `ReactDOM.createPortal(modal, document.body)` matches the existing `AnalysisModal.tsx:810` pattern.

### [Con-2] PASS — No useScreen/useTab in search components

`StockSearchBox.tsx` and `StockSearchModal.tsx` contain no `useScreen` or `useTab` imports. Verified by AC-ARCH-003 test (static import line scan) PASS and by `grep`.

### [Con-3] PASS — Backend service/router split

`stocks_master_service.py` (query logic) / `stocks.py` (HTTP layer) matches the existing pattern in other backend services.

### [Con-4] MINOR — Modal title text format diverges from spec §4

**File:** `frontend/src/components/ChartGrid/StockSearchModal.tsx:193-198`

Spec §4 row 7 specifies title: `{name} ({code})`. Implementation has:

```tsx
<span id="stock-search-modal-title">{stock.name}</span>
<span style={{ ... }}>{stock.code} · {stock.market}</span>
```

The `aria-labelledby` element contains only `{stock.name}`, not the spec-mandated `{name} ({code})` format. The stock code is rendered in a separate sibling span. Minor accessibility impact — screen readers announce only the name, not the code.

---

## Anti-regression specific verdict

### MP-1 (ChartGrid commit count +0 on modal open/close): THEATER TEST

**Evidence:** `ChartGrid.perf.test.tsx:303-307` — the `act` block that should trigger `setSelectedStock(stock)` is empty. The test never changes `selectedStock` state, so it proves nothing about ChartGrid isolation. ARCHITECTURAL DESIGN is correct (`React.memo(ChartGridInner)` + `useCallback` for stable `handleSelectStock`), but the test does not prove it.

Verdict: Architecture correct, test hollow. Cannot mark as verified.

### MP-2 (ChartCell useEffect 0 additional calls): NO TEST

**Evidence:** `ChartGrid.perf.test.tsx` header declares it covered, body has zero assertions about ChartCell useEffect call count. UNTESTED.

Verdict: UNVERIFIED.

### MP-3 (useScreen deep-equal): PASS

**Evidence:** `ChartGrid.perf.test.tsx` "useScreen.filters deep-equal 보존" — mocked `useScreen` returns static object; modal mount/unmount doesn't change it. PASS (though the test uses a mock, not the real ScreenContext).

### MP-4 (portal subtree): PASS

**Evidence:** Both `StockSearchModal.test.tsx` and `ChartGrid.perf.test.tsx` confirm `within(chartGridRoot).queryByTestId('stock-search-modal') === null` and `document.body.contains(modal) === true`. PASS.

### MP-5 (no new deps): PASS

No new entries in `package.json` or `requirements.txt`. `hangul.ts` and `useFocusTrap.ts` are self-contained. PASS.

---

## Summary of all issues by severity

| # | Severity | Finding |
|---|----------|---------|
| F-1 | HIGH | `triggerRef` never attached — focus restoration silently broken (REQ-MODAL-002 step 3) |
| F-2 | HIGH | Timeframe inheritance not implemented — AppContent always sets 'daily' (Q-7 violation) |
| F-3 | MEDIUM | Loading and error states absent — spec §4 rows 11-12 testids missing |
| C-1 | CRITICAL | AC-MODAL-007 (must-pass) has zero tests — useEffect count invariant unverified |
| C-2 | CRITICAL | AC-PERF-002 (must-pass MP-2) has zero tests — DoD not met |
| C-3 | HIGH | MP-1 test never changes state — theater test, invariant unverified |
| C-4 | MEDIUM | Chart fetch errors silently swallowed, no user feedback |
| C-5 | LOW | Focus trap uses stale focusable snapshot |
| Con-4 | MINOR | Modal title `aria-labelledby` element contains only name, not `{name} ({code})` |

---

## Recommendation

FAIL — return findings to manager-tdd for fixes.

Priority order:

1. **AC-PERF-002 (MP-2) — add real test.** Write a test that spies on `ChartCell.useEffect` (or uses a render-count counter in a mock), opens the modal, and asserts the spy fires 0 additional times. This is the most important missing piece because it was the rollback trigger in SPEC-CHART-NAV-001.

2. **AC-MODAL-007 — add real test.** Instrument `StockSearchModal`'s chart useEffect with a spy counter. Open modal once, assert spy called exactly 1 time (StrictMode: ≤2). Close modal. Assert no additional calls.

3. **MP-1 theater test — replace with real assertion.** Inside the `act` block, call `handleSelect(someStock)` to trigger `setSelectedStock`. Then assert `gridCommitCount === baselineCommits` after the state change propagates.

4. **Timeframe inheritance — implement or explicitly document limitation.** Either: (a) expose `currentTimeframe` as a ref or callback from `ChartGrid`, pass it up to AppContent at select time; or (b) document explicitly in the spec that v1.0 ships with always-daily fallback and update acceptance criteria accordingly. The current code has a comment acknowledging it but the actual implementation diverges from the spec decision.

5. **Focus restoration — wire `triggerRef`.** Either add `focus(): void` to `StockSearchBoxHandle` and call `triggerRef.current?.focus()` using that handle, or restructure so AppContent holds the actual `<input>` ref. Currently `triggerRef.current` is always null.

6. **Loading/error states** (optional for DoD, required for spec §4 completeness): Add `useState<boolean>(false)` for `loading` and `useState<string|null>(null)` for `error` in StockSearchModal. Show spinner during fetch, error message on catch.

---

## Final line

Verdict: FAIL
