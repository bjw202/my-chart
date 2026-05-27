# SPEC Review Report: SPEC-SMA5-FILTER-001
Iteration: 1/3
Verdict: FAIL
Overall Score: 0.74 (gated to FAIL by MP-3 firewall)

> Reasoning context ignored per M1 Context Isolation. The invoking prompt supplied generous context about expected conclusions; this audit relied solely on the SPEC files (spec.md, plan.md, acceptance.md, research.md, spec-compact.md) and the named source files, independently verified.

## Summary

This is a technically excellent, deeply researched SPEC. Every quantitative claim I checked against source code is **correct** (column counts, line numbers, the stock_meta coupling, the stale `==27` test). EARS structure and traceability are strong, and the Exclusions section is exemplary. However, the YAML frontmatter is missing the required `labels` field and uses `created` instead of the required `created_at` field. Under the M5 Must-Pass Firewall (MP-3), any missing required frontmatter field is an automatic FAIL regardless of other dimensions. There are also two MAJOR quality defects (a wrong test path in plan.md, and the SPEC's own self-identified HIGH-risk corruption scenario lacking a binary-testable AC).

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**: REQ-SMA5-001..006 are sequential, no gaps, no duplicates, consistent 3-digit zero-padding. Evidence: spec.md:L72, L78, L84, L90, L96, L102.

- **[PASS] MP-2 EARS format compliance**: All 6 REQs match a declared EARS pattern exactly:
  - REQ-SMA5-001 Ubiquitous — "The system **shall** store `SMA5` and `FromSMA5` values..." (spec.md:L74)
  - REQ-SMA5-002 Event-Driven — "**When** the daily DB rebuild runs (...), the system **shall** compute..." (spec.md:L80)
  - REQ-SMA5-003 Ubiquitous — "The `stock_meta` snapshot table **shall** include the `sma5` column..." (spec.md:L86)
  - REQ-SMA5-004 Event-Driven — "**When** a user adds a `PatternCondition` referencing `SMA5`..., the system **shall** evaluate it..." (spec.md:L92)
  - REQ-SMA5-005 Ubiquitous — "The ChartGrid filter (`PatternBuilder`) **shall** list `SMA5`..." (spec.md:L98)
  - REQ-SMA5-006 Unwanted — "**If** a stock has fewer than 5 trading days (...), **then** the system **shall** persist..." (spec.md:L104)
  - The Given/When/Then scenarios in acceptance.md are correctly labeled as TEST SCENARIOS, not mislabeled as EARS — no violation.

- **[FAIL] MP-3 YAML frontmatter validity**: Two required fields are absent under their required names. Evidence: spec.md:L1-L10 contains only `id, version, status, created, updated, author, priority, issue_number`.
  - `labels` (array or string) — **entirely absent**. M5: "Any missing required field = FAIL."
  - `created_at` (ISO date string) — the spec uses `created: 2026-05-25` (spec.md:L5), not `created_at`. The required field name is absent.
  - Context (not a waiver): this matches the project's house style — sibling SPECs (SPEC-DASHBOARD-002, SPEC-PRESET-001) also use `created` and omit `labels`. The fix is trivial. But the firewall criterion as written has no house-style exception, and per HARD rules I do not rationalize away an identified defect. This single criterion forces the overall FAIL.

- **[N/A] MP-4 Section 22 language neutrality**: N/A — single-application SPEC (KR Stock Screener feature, Python+React), not multi-language tooling or template-bound content. Auto-passes.

## Category Scores (0.0-1.0, rubric-anchored)

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.75 | 0.75 | REQs are behaviorally unambiguous, but embed implementation detail (function/SQL names) in normative text, and insertion position is left "recommended" (spec/plan tension). spec.md:L80, L92; plan.md:L15 |
| Completeness | 0.50 | 0.50 | All sections present + excellent Exclusions, BUT frontmatter missing `labels`, and the self-declared HIGH-risk column-alignment scenario has no AC. spec.md:L1-L10; acceptance.md:L75 |
| Testability | 0.70 | 0.75 (lower edge) | AC-1..AC-8 are mostly strong binary tests (numeric expected values, PRAGMA, WHERE string), but the corruption risk lacks a test and AC-5's expected string is slightly inexact. acceptance.md:L10-L56 |
| Traceability | 1.00 | 1.0 | Every REQ has >=1 AC; every AC traces to a valid REQ; no orphans, no uncovered REQs. Mapping: 001->AC-3, 002->AC-1/2, 003->AC-4, 004->AC-5/6, 005->AC-7, 006->AC-8. acceptance.md:L10-L56 |

## Verified Technical Claims (independent source confirmation)

The audit prompt asked me to verify several technical claims. All were independently checked and found **CORRECT**:

- **(a) Screening reads from `stock_meta`, so meta_service.py is genuinely REQUIRED** — CONFIRMED. `screen_service.py:121-124` builds pattern WHERE clauses from `_INDICATOR_COLUMN` (stock_meta column names); `screen_service.py:171-178` runs `SELECT ... FROM stock_meta WHERE {where_sql}`. An SMA5 pattern would emit `sma5` against `stock_meta`; without the column it raises OperationalError. meta_service.py change is correctly classified [REQUIRED].
- **(b) Positional-column-order corruption risk is real** — CONFIRMED. `daily.py:272,282` use `INSERT OR REPLACE INTO stock_prices VALUES ({placeholders})` with NO column names; `placeholders = "?" * len(_DAILY_COLS)` (daily.py:253). The three alignment points (`_DAILY_COLS` L32-42, CREATE TABLE L56-73, value tuple L182-213) must share one position. Both new columns are REAL, so a mismatch is silent. Risk is accurately characterized (spec.md:L55; research.md §2.3). Mitigation adequacy is a defect — see D2.
- **(c) `CREATE TABLE IF NOT EXISTS` / idempotent-ALTER requirement** — CONFIRMED. `daily.py:57` is `CREATE TABLE IF NOT EXISTS` (no-op on existing table); the idempotent ALTER loop at `daily.py:81-87` currently lists `("SMA100","RS_Line","SMA150","LOW_52W","SMA200_20D_AGO")`. Adding SMA5/FromSMA5 there is correctly flagged [REQUIRED].
- **(d) `tests/test_daily.py:26` asserts `==27` while actual is 30** — CONFIRMED. `tests/test_daily.py:26` is `assert len(_DAILY_COLS) == 27`. I counted `_DAILY_COLS` (daily.py:32-42) entry-by-entry = **30**. The test is currently failing (stale); the SPEC's plan to update it to `==32` (30 + SMA5 + FromSMA5) is arithmetically correct.
- **Bonus verifications**: `_STOCK_META_DDL` = 26 columns; INSERT placeholder line 311 = 26 `?`; INSERT value tuple (279-306) = 26 entries — the SPEC's "26 -> 27" claim is correct. All daily.py and meta_service.py line references in research.md are accurate. `_build_where` (screen_service.py:124) produces exactly `close > sma5 * ?` for the AC-5 condition.

## Defects Found

**D1. spec.md:L1-L10 — MP-3 frontmatter: `labels` field missing entirely, and `created_at` required field absent (uses `created`). — Severity: critical (forces overall FAIL via M5 firewall).**

**D2. acceptance.md:L75 (+ tests/test_daily.py:155-180) — The SPEC's own HIGH-risk "silent column-shift corruption" (spec.md:L55; research.md §2.3) has NO binary-testable acceptance criterion.** The only structural guard is the existing `test_row_tuple_length_matches_daily_cols`, which asserts `len(row) == len(_DAILY_COLS)` (LENGTH only). If SMA5 and FromSMA5 are both added but their values land in swapped positions, the length test still passes (32==32) and corruption is undetected. The "컬럼명↔값 정렬 명시 검사" (column-name↔value alignment check) is named in the quality-gate prose but never specified as a concrete AC with expected values. No AC verifies that, after an INSERT/SELECT round-trip, the `SMA5` column actually holds the SMA5 value rather than FromSMA5's. — Severity: major.

**D3. plan.md:L39 — Wrong test path. Task 3 header names `backend/tests/test_screen_service.py`, but the file exists only at `tests/test_screen_service.py` (verified: `backend/tests/test_screen_service.py` does not exist; `find` returns only `./tests/test_screen_service.py`). The same task body (plan.md:L41) and research.md §4.1 correctly use `tests/test_screen_service.py`, so plan.md is internally inconsistent. Because BOTH `tests/` and `backend/tests/` exist in this repo, an implementer could create the SMA5 test in the wrong directory. — Severity: major.**

**D4. plan.md:L15 / research.md §3.1, §3.5 — Insertion POSITION is not actually fixed despite a [HARD] mandate.** plan.md:L15 opens "단일 위치 결정 [HARD] ... 하나의 일관된 위치로 결정한다" but then only offers "권장:" (recommended) positions and "방안을 우선 검토" (consider this approach first). research.md §3.1 even writes "FromEMA20(pos ~21)" with a `~` (approximate). Given D2 (no alignment AC), leaving the position unresolved at SPEC level partially invites the corruption the SPEC warns about. — Severity: minor.

**D5. spec.md:L80, L92, L98 — RQ-4 violation: requirements embed implementation detail in normative text** (`price_daily_db()`, `_INDICATOR_COLUMN`, `close > sma5 * ?`, `PatternCondition`, `PatternBuilder`). EARS clauses describe WHAT, but the parentheticals specify HOW (function names, SQL). Acceptable for a brownfield TDD aid, but technically a HOW-leak. — Severity: minor.

**D6. acceptance.md:L38 — AC-5 expected WHERE string is slightly inexact.** AC-5 states the clause is `close > sma5 * ?`, but `_build_where` (screen_service.py:127-129) wraps pattern clauses in parentheses, producing `(close > sma5 * ?)`. A literal-string TDD assertion will need to account for the outer parens. — Severity: minor.

## Chain-of-Verification Pass

Second-look findings, by re-reading sections I initially moved through quickly:

- **Re-read every REQ (001-006)**: re-confirmed EARS pattern match individually; not skimmed after the first few. No new EARS issues.
- **Re-counted `_DAILY_COLS` entry-by-entry** (not spot-checked): 30 entries confirmed; the SPEC's 30->32 arithmetic holds.
- **Re-verified traceability for every REQ** (not sampled): all 6 REQs covered; all 8 ACs traced; no orphans.
- **Re-read Exclusions for specificity** (not just presence): 6 entries, each concrete with file paths (e.g., `my_chart/charting/single.py`, `frontend/src/types/stock.ts`) — genuinely specific, not vague. Verified those excluded files actually exist.
- **NEW finding — files-to-modify completeness (independent grep of all `IndicatorName` / indicator enumeration sites)**: discovered `frontend/src/presets/utils.ts:5-15` defines `INDICATOR_LABELS` enumerating Close..SMA200 without SMA5. This is NOT a missed required modification: the consumer (`utils.ts:62-64`) uses `INDICATOR_LABELS[x] ?? x`, falling back to the raw name "SMA5" — which is exactly the SPEC's A5 desired behavior, and SMA5 patterns are not part of any predefined preset anyway. So the SPEC's files-to-modify list is functionally complete; I confirmed this independently rather than trusting the SPEC. (Optional, non-blocking: add `SMA5: 'SMA5'` to utils.ts for explicitness.)
- **NEW check — existing security test `test_column_names_are_lowercase_identifiers` (tests/test_screen_service.py:246-250)** iterates `_INDICATOR_COLUMN.values()` against regex `^[a-z][a-z0-9_]*$`. The new mapping value `"sma5"` matches (lowercase + digit) — no regression. Not mentioned in the SPEC's no-regression table but safe.
- **NEW check — `backend/tests/test_screen_patterns_limit.py`** (not in the SPEC's no-regression list) tests only the max-5 pattern limit; adding SMA5 to the Literal does not affect it. No impact.

No new blocking defects beyond D1; the new findings net-confirm the SPEC's completeness.

## Recommendation

The SPEC is substantively sound and close to passing. To clear iteration 2, manager-spec must:

1. **(Blocking, D1) Fix the frontmatter** at spec.md:L1-L10. Add a `labels` field (array or string, e.g., `labels: [db, screening, frontend, sma5]`). Add a `created_at` ISO-date field (or confirm with the user/orchestrator that the project schema intentionally uses `created`; if so, the audit schema should be reconciled — but as written, MP-3 requires `created_at` and `labels`).

2. **(D2) Add a binary-testable column-alignment AC.** Add an AC (mapped to REQ-SMA5-001/002) that round-trips through `stock_prices`: insert a known row where SMA5 != FromSMA5 (distinct values), then `SELECT SMA5, FromSMA5` and assert each column holds its own value — not just that the tuple length is 32. This is the only test that catches the silent corruption the SPEC itself rates HIGH.

3. **(D3) Correct the test path** in plan.md:L39 from `backend/tests/test_screen_service.py` to `tests/test_screen_service.py` to match L41 and research.md §4.1.

4. **(D4) Fix the insertion position as a HARD decision**, not a recommendation. State the exact final index for SMA5 and FromSMA5 in each of the alignment points (daily.py `_DAILY_COLS` / CREATE TABLE / value tuple; meta_service.py DDL / SELECT / INSERT / daily_by_name) as concrete positions, removing "권장"/"우선 검토"/"~" hedging.

5. **(D6, minor) Adjust AC-5's expected string** to reflect the parenthesized output `(close > sma5 * ?)` produced by `_build_where`, or assert via substring/normalized comparison.

D5 is optional to address (acceptable for brownfield TDD), but if pursued, move function/SQL names out of normative REQ text into the "검증" lines.

Verdict: FAIL
