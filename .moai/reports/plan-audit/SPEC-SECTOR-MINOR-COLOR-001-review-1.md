# SPEC Review Report: SPEC-SECTOR-MINOR-COLOR-001
Iteration: 1/3
Verdict: PASS
Overall Score: 0.93

> Reasoning context ignored per M1 Context Isolation. Audit performed against the four SPEC files and independently verified source artifacts only.

## Summary

The SPEC defines a narrow, well-scoped replacement of Weinstein Stage color encoding with sector_minor encoding inside the StockBubbleChart drill-down view. Backend additive schema extension + frontend visual re-encoding, with explicit removal of STAGE_COLORS and 5-item stage legend. EARS coverage is complete with 11 sequential REQs and 12 ACs in perfect bidirectional traceability. House-style 8-field YAML frontmatter is intact. Technical citations to source files are largely accurate (line numbers within ±2-line slack). DB-schema assumption (sector_minor column exists) is independently verified true. Backward-compatible backend ship path is explicit. The audit-prompt-flagged risk surfaces (determinism, palette overflow at exactly 10 vs 11, mobile fallback, P95 pending) are all addressed in spec/acceptance text. Minor defects: useMediaQuery hook source unspecified (no existing implementation in the codebase), `767px = Tailwind md` rationale misattributed (project does not actually use Tailwind), AC-10 static-scan method vague ("grep 또는 AST"), WCAG palette contrast against `#1a1a2e` background never claimed nor gated. All must-pass criteria PASS.

## Must-Pass Results

- **[PASS] MP-1 REQ number consistency**: REQ-SBM-001..011 sequential, 3-digit zero-padded, no gaps/duplicates. Evidence: spec.md L78, L86, L94, L100, L110, L118, L126, L134, L142, L151, L158.

- **[PASS] MP-2 EARS format compliance**: Each REQ matches its declared pattern (6 Ubiquitous / 3 Event-Driven / 1 State-Driven / 1 Unwanted).

- **[PASS] MP-3 YAML frontmatter validity (house-style 8-field)**: id/version/status/created/updated/author/priority/issue_number all present at spec.md L1-10. `created_at`/`labels` omission matches the project house-style explicitly documented in SPEC-SMA5-FILTER-001 v1.0.1 HISTORY — NOT a defect.

- **[N/A] MP-4 Section 22 language neutrality**: Single-application frontend SPEC — auto-pass.

## Category Scores

| Dimension | Score | Rubric Band | Evidence |
|-----------|-------|-------------|----------|
| Clarity | 0.90 | 0.75-1.0 | REQ language unambiguous; deterministic mapping function spelled out (spec.md L104, research.md L152, plan.md L23-30). Minor: plan.md L52 "Tailwind md 기준" misattributed (project does not use Tailwind). |
| Completeness | 0.95 | 0.75-1.0 | All sections present, Exclusions specific (10 entries), AC-12 pending explicitly authorized (acceptance.md L94). |
| Testability | 0.88 | 0.75-1.0 | AC mostly binary. Two minor weaknesses: AC-9 narrow round-trip definition, AC-10 "grep 또는 AST" disjunction. |
| Traceability | 1.00 | 1.0 | Perfect bidirectional mapping. All 11 REQ → ≥1 AC, all 12 AC → valid REQ. No orphans. |

## Verified Technical Claims (independent source confirmation)

All 10 claims independently verified:

1. **StockBubbleChart.tsx L76 STAGE_COLORS mapping** — CONFIRMED.
2. **StockBubbleItem type lacks sector_minor** — CONFIRMED (types/bubble.ts L19-28).
3. **Backend `/sectors/{name}/bubble` endpoint** — CONFIRMED (sectors.py L134-151, line-citation slack 1).
4. **sector_detail_service.py L90 fallback pattern** — CONFIRMED.
5. **Stage legend 5 entries** — CONFIRMED (StockBubbleChart.tsx L125-137, citation slack L124 vs L125).
6. **`_get_stock_meta` does not currently SELECT sector_minor** — CONFIRMED (sector_advanced.py L140).
7. **`stock_meta.sector_minor` column exists in live DB** — CONFIRMED via PRAGMA.
8. **HISTORY v1.0.0 consistent with frontmatter** — CONFIRMED.
9. **No spurious `</content>` end-tag** — CONFIRMED (all 4 files clean).
10. **REQ-AC traceability completeness** — CONFIRMED (zero orphans bidirectional).

## Defects Found

**D1. plan.md:L52 — "767px = Tailwind md 기준" misattribution.** Project does not use Tailwind (no `tailwind.config.*`, no `tailwind` in `frontend/package.json`, no `postcss.config.*`). Breakpoint choice is valid but rationale citation wrong. — Severity: minor.

**D2. plan.md:L44 — `useMediaQuery('(max-width: 767px)')` hook referenced but no such hook exists in the codebase (grep on `frontend/src` returns zero matches).** Plan does not specify import source (library vs inline). Implementation ambiguity during GREEN. — Severity: minor.

**D3. acceptance.md:L78 — AC-10 static-scan method left as "grep 또는 AST" disjunction.** For binary TDD gate, one method must be chosen (recommend Vitest source-string regex). — Severity: minor.

**D4. acceptance.md:L67-71 — AC-9 "round-trip" defined narrowly as two-call function-output equality.** Does not cover component re-mount, page reload, or ECharts canvas redraw. Acceptable as unit gate, but augmentation with re-render assertion needed. — Severity: minor.

**D5. plan.md:L161 — `buildSectorMinorColorMap` tagged `@MX:ANCHOR` with claimed fan_in=2.** Below the @MX:ANCHOR threshold of fan_in≥3 (mx-tag-protocol.md). Justified by triple-dependency reason, but threshold mismatch should be explicit in mx_plan rationale. — Severity: minor.

**D6. spec.md:L54 + plan.md:L40 + research.md:L46 — Citation of stage legend block as `L124-137`.** Actual range is `L125-137` (1-line slack across 3 documents). — Severity: minor.

**D7. SECTOR_MINOR_PALETTE (plan.md L33-37, research.md L142-144) — 10 colors against `#1a1a2e` background, but no WCAG contrast claim or gate.** Not a strict defect (no accessibility requirement stated), but a gap given dark-mode dependency. — Severity: minor (non-blocking).

## Chain-of-Verification Pass

Re-read all 11 REQs individually — EARS pattern per declared type confirmed. Re-mapped every AC→REQ and REQ→AC independently — matches §5 Traceability table (spec.md L191-203) exactly. Re-checked Exclusions for specificity — 10 entries all concrete. Re-checked palette overflow boundary at N=10 vs N=11: REQ-SBM-005 formula + AC edge case explicitly covers boundary. Re-checked sort-order tie-break: `(count desc, name asc)` specified in research.md L152-153 + AC-9 L70. Re-checked AC-12 P95 pending: acceptance.md L94 explicitly authorizes "pending". No new defects in second pass.

## Recommendation

PASS, with non-blocking improvements for v1.0.1 amendment (or absorb during run phase):

1. **plan.md L52**: Replace "Tailwind md 기준" with project-grounded rationale.
2. **plan.md L44 + Task 7**: Specify `useMediaQuery` source (recommend inline `window.matchMedia` hook).
3. **acceptance.md L78 (AC-10)**: Pick one static-scan method (recommend source-string regex).
4. **acceptance.md L67-71 (AC-9)**: Augment with component-level re-render assertion.
5. **plan.md L161 (mx_plan)**: Add explicit `@MX:REASON` acknowledging fan_in=2 + justification.
6. **Line citations**: Correct L124-137 → L125-137 in 3 documents.
7. (Optional, D7) **acceptance.md §3**: Add WCAG contrast statement for palette vs `#1a1a2e`.

None block iteration 2. SPEC is implementation-ready as-is.

Verdict: PASS — Overall 0.93.
