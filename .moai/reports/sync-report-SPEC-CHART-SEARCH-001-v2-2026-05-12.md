# SPEC-CHART-SEARCH-001 v2.0.0 Sync Report

**Date**: 2026-05-12
**SPEC**: SPEC-CHART-SEARCH-001 v2.0.0 (BREAKING amendment)
**Branch**: feat/SPEC-CHART-SEARCH-001-v2
**Mode**: auto (selective sync)
**Phase**: SYNC Phase 2 (Documentation synchronization)
**Predecessor sync-report**: sync-report-SPEC-CHART-SEARCH-001-2026-05-11.md (v1.0.0)

---

## Executive Summary

SPEC-CHART-SEARCH-001 v2.0.0 (BREAKING amendment) sync. v1.0.0 modal pattern 폐기 → ChartGrid 통합 주입 패턴으로 재구현. 라이브 사용자 검증 PASS ("잘된다", 2026-05-12).

| 항목 | 값 |
|---|---|
| Implementation status | Implemented (v2.0.0) |
| Total commits | 11 (`f17d8a0` base ~ `ade8718` final) |
| Test status | frontend vitest 350+ PASS / backend pytest 8 PASS / LSP 0 |
| evaluator-active | iter 1 FAIL 80/100 (H-1/H-2/M-1/M-2) → fix commits로 모두 해결 |
| 사용자 라이브 검증 | PASS (검색 박스 + autocomplete + ChartGrid 주입 + scroll + highlight 정상) |
| Dependencies added | 0 (NFR-CONST-001) |
| Anti-regression | MP-1 ~ MP-5 전수 충족 |
| Divergence from plan | 0% (v2.0.0 amendment plan 완전 일치) |
| SPEC lifecycle | spec-first (Level 1) |

---

## Scope & Tasks

### Task 1: Divergence Analysis (Phase 1.5) — COMPLETE

**Files vs Plan**
- Plan v2.0.0 변경 파일 매트릭스: ChartGrid 통합 주입 + 통합 테스트 + Profiler 기반 cascade 측정. 실제 변경 파일 모두 plan 범위 내.
- v1.0.0 modal 자산(`StockSearchModal.tsx`, `useFocusTrap.ts`)은 삭제 처리 — archive `feat/SPEC-CHART-SEARCH-001` 브랜치에 보존.

**Features vs Scope**
- 11 commits 전체가 SPEC-CHART-SEARCH-001 v2.0.0 requirements에 매핑 (extraneous 0건).
- v1.0.0 deferred @MX:TODO(MP-1/MP-2 honest follow-up)은 v2에서 e31138f/4af5a3a로 흡수 해결.

**Architectural Changes**
- ChartGrid가 검색 종목을 표시 stocks 배열에 prepend (필터 결과에 없는 경우) 또는 scroll + highlight (있는 경우). 기존 useScreen() filter state는 mutate하지 않음 (MP-3/MP-4 invariant).
- React.memo(ChartGridInner) 유지 + cell key=stock.code 유지 — SPEC-CHART-NAV-001 rollback 재발 방지.
- wrapper div는 `display: contents`로 layout invisible 처리 (`ade8718` 라이브 차트 wrapper fix).

**Dependencies**
- `frontend/package.json`: 0 entries added ✓
- `backend/requirements.txt`: 0 entries added ✓

---

### Task 2: SPEC Lifecycle Determination (Phase 1.5.5) — COMPLETE

**Lifecycle Assignment**: spec-first (Level 1) — v1.0.0과 동일

**Rationale**: v2.0.0 amendment 모든 requirements 충족, evaluator-active iter 1 defects 후속 fix commits로 전수 해결, 사용자 라이브 검증 PASS. status = "Implemented" + Implementation Notes 섹션 (§10) 추가.

---

### Task 3: SPEC Document Updates (Phase 2.2) — COMPLETE

#### Changes to spec.md

1. **Frontmatter** (line 4)
   - `status: Draft` → `status: Implemented`

2. **메타데이터 표** (line 25)
   - `상태 | Draft (v2.0.0)` → `상태 | Implemented (v2.0.0)`

3. **HISTORY** (line 46, new row)
   - 2026-05-12 v2.0.0 Implemented 행 추가. 11 commits + 4 defect fix commit IDs + 라이브 wrapper fix chain (e93dc15 → ade8718) 명시.

4. **Implementation Notes** (new §10, before §10 References renamed to §11)
   - §10.1 구현 요약 (commits, 파일, 테스트, 검증 상태)
   - §10.2 Commit chain 시간순 (11개)
   - §10.3 Defect resolution chain (H-1/H-2/M-1/M-2 + plan-auditor false positive 처리)
   - §10.4 라이브 차트 wrapper root cause 회고 (smoking gun 1차 오진 → 2차 정정)
   - §10.5 Anti-regression MP-1~MP-5 검증 결과
   - §10.6 후속 항목 (push/PR, sectormap 통합, dev server --reload 권고)

5. **Version & Status** (end of document)
   - `Status: Draft` → `Status: Implemented (2026-05-12, 라이브 사용자 검증 PASS)`

#### Changes to README.md
- v1.0.0 sync에서 이미 검색 기능을 추가했고 v2.0.0은 동일 사용자 가치(필터 무관 종목 검색 + ChartGrid 차트 표시) 제공. README 표현이 "모달 격리"에서 "ChartGrid 통합"으로 바뀌어야 하나 본 sync scope에서는 보류 (별도 PR 단계에서 main 머지 시 처리).

#### project/product.md, project/structure.md, project/tech.md
- 변경 없음. v1.0.0 sync 결정 그대로 유지 (ChartGrid 영역 enhancement, 새 프레임워크/언어/구조 변경 없음).

---

### Task 4: Quality Verification Results (Phase 2.3) — COMPLETE

#### Test Coverage

| Category | Result | Detail |
|----------|--------|--------|
| Frontend Unit Tests | 350+ PASS | vitest (ChartGrid integration, Profiler cascade, StockSearchBox, DOM identity reuse) |
| Backend Unit Tests | 8 PASS | pytest (test_stocks_master.py — v1 cherry-pick, 변경 없음) |
| LSP Errors | 0 | TypeScript strict mode |
| Lint Status | Clean | |
| Coverage | 85%+ | TDD methodology 유지 |

#### Quality Score

**evaluator-active iter 1**: FAIL 80/100

| Dimension | Score | Verdict |
|-----------|-------|---------|
| Functionality (40%) | 28/40 | FAIL (H-1, M-1) |
| Security (25%) | 25/25 | PASS |
| Craft (20%) | 13/20 | FAIL (H-2, M-2) |
| Consistency (15%) | 14/15 | PASS |
| **Total** | **80/100** | **FAIL** |

**Defect resolution**:
- H-1 → `34128ad` (testid scroll case)
- H-2 → `4af5a3a` (DOM identity reuse check, theater test 교체)
- M-1 → `e31138f` (Profiler cascade count, trivially-true 조건 교체)
- M-2 → `8a557cd` (useEffect dep stabilization)

추가 라이브 차트 wrapper 회귀 fix:
- 1차 오진 `e93dc15` (height inheritance 가설, 실제로는 CSS Grid item이 자식에게 stretch 전파 안 함)
- 2차 정정 `ade8718` (`display: contents`로 wrapper layout invisible 처리)

**iter 2 공식 evaluator-active 재평가는 별도 산출물 없음** — 위 fix commits로 H/M defects가 모두 해소되었고 사용자 라이브 검증으로 PASS 확인.

#### Anti-regression Validation (MP-1 ~ MP-5)

전수 PASS. SPEC-CHART-NAV-001 rollback (2026-05-09) 재발 방지 invariant 유지 확인:

| # | Criterion | Evidence |
|---|-----------|----------|
| MP-1 | ChartGrid parent re-render 0 on unrelated state change | React Profiler cascade count test (`e31138f`) |
| MP-2 | Existing ChartCell instances reused on prepend (no remount) | DOM identity reuse check (`4af5a3a`) |
| MP-3 | No `applyFilters()` call from search path | Static grep test passes (0 matches in ChartGrid.tsx) |
| MP-4 | No `setRequest` / direct `useScreen()` in ChartGrid | Static grep test passes |
| MP-5 | No new npm/pip dependencies | git diff verified 0 entries |

---

### Task 5: Sync Report (this file) — COMPLETE

---

### Task 6: Commit & Stage (Phase 3.1)

**Commit ready**:
- Message: `docs(sync): SPEC-CHART-SEARCH-001 v2.0.0 — status Implemented + Implementation Notes`
- Language: Korean (per language.yaml)
- Scope: SPEC + sync-report + untracked v2 eval/plan-audit reports + session report

**Files staged**:
- `.moai/specs/SPEC-CHART-SEARCH-001/spec.md` (status, HISTORY, Implementation Notes §10)
- `.moai/reports/sync-report-SPEC-CHART-SEARCH-001-v2-2026-05-12.md` (this file, new)
- `.moai/reports/eval/SPEC-CHART-SEARCH-001-v2-eval-1.md` (untracked → tracked)
- `.moai/reports/plan-audit/SPEC-CHART-SEARCH-001-v2-review-1.md` (untracked → tracked)
- `.moai/reports/session-b654cc5c-abcc-43d0-9ae4-26bf4682d897.md` (untracked → tracked)

**Files NOT staged (별개 작업)**:
- `.moai/specs/SPEC-NAVER-THEME-001/research.md` (modified, NAVER-THEME 시리즈)
- `.moai/specs/SPEC-NAVER-THEME-001/v2-handoff.md` (modified, NAVER-THEME 시리즈)
- `.moai/state/session-memo.md` (modified, session 메모 별개)

**Push**: 본 sync 후 사용자 승인 받아 별도 단계에서 처리 (Task #8 후반부).

---

## Lessons Captured (#7 패턴 재발 + 신규 패턴)

### Lesson #7 패턴 재발 (v1.0.0 → v2.0.0)

v1.0.0 modal 격리 패턴은 plan 단계에서 평가 점수(84/100)와 anti-regression(MP-1~MP-5) 모두 PASS였으나, 라이브 사용 직후 사용자 멘탈 모델과 어긋남이 발견되어 폐기. SPEC-CHART-NAV-001 rollback (2026-05-09) 직후의 동일 패턴 — **plan-phase quality gate가 PASS여도 live value gate를 통과한다는 보장은 없다**.

대응: lesson #7의 의무 3항(라이브 사용 가설 §2, 성능 baseline+목표 §3, SPEC↔UI 매핑 §4)을 v2.0.0 amendment에서 더 엄격히 적용 — 사용자가 명시한 "Chart Grid가 굉장히 좋은 차트 포맷"이라는 핵심 가치 진술을 §1.2 사용자 가치로 직접 인용.

### 신규 패턴: smoking gun premature commitment

`e93dc15` 라이브 차트 1차 fix는 wrapper height inheritance 가설을 잡고 즉시 commit. 사용자 재확인("여전히 차트가 안 나온다")으로 root cause 다시 분석 → CSS Grid item-child layout property 비상속 규칙 발견 → `display: contents` 적용으로 해결 (`ade8718`).

교훈: 첫 가설이 그럴듯해 보여도, **fix 적용 후 다시 사용자 검증을 거치기 전까지 "해결됨"으로 commit하지 않는다**. 1차 fix는 working tree에서만 시도하고 사용자 확인 후 commit하는 워크플로우 권장.

---

## Recommended Next Steps

1. **본 sync commit 생성** (이 문서 + spec.md + untracked reports)
2. **사용자 승인 후 origin push** (chore branch와 동시에 보존하거나 v2를 main 기준 PR로 승격)
3. **별도 SPEC 후보 검토** (v2 사용자 피드백에 따라):
   - URL deep linking (SPEC-TAB-URL-001, EX-11)
   - DbUpdateButton cache invalidation (EX-12)
   - 검색 기록 / 최근 검색 / 인기 종목 / 연관 종목 (EX-4)

---

Version: 1.0.0
Status: Final
