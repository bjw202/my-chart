# SPEC-CHART-NAV-001 Retrospective — Rolled-back

작성일: 2026-05-09
SPEC: SPEC-CHART-NAV-001 차트 그리드 종목 네비게이션 통합 (테마→그리드 + 종목 검색 + 필터 우회)
최종 상태: **Rolled-back** (2026-05-09)

---

## 1. Outcome

### 1.1 Goal vs Actual

| 항목 | Plan 단계 (2026-05-07) | Actual (2026-05-09) |
|---|---|---|
| Feature A — Theme→Grid | ThemeDetailPanel 헤더 버튼 + ThemeRankingTable 행 chip → ChartGrid 진입 | 구현 완료 후 사용자 가치 재평가로 폐기 |
| Feature B — Search→Grid | StockSearchBox(종목명 + 코드 prefix + 초성) → ChartGrid 단일 종목 진입 | 구현 완료 후 폐기 |
| 자동화 검증 | 26 AC + 14 라이브 검증 시나리오 | backend pytest 4/4, frontend vitest 47/47 + 회귀 317/317, e2e Playwright 12/12 모두 PASS |
| 라이브 사용 가치 | (plan 단계 가설 미명시) | 사용자 판단 "기능 불필요 + 성능 저하" |

### 1.2 핵심 결과

자동화 품질 검증은 100% 통과했으나 사용자가 라이브 사용 후 **기능 가치 + 성능 영향**을 종합 재평가하여 폐기 결정.

---

## 2. Timeline

| Date | Phase | Commits | Outcome |
|---|---|---|---|
| 2026-05-07 | Plan | 3f00155 docs(specs) | research.md / spec.md / plan.md / acceptance.md 4 산출물 (chore 브랜치) |
| 2026-05-07 | Run (Agent Teams `--team`) | 9be9767, 1e20dd8, 2a0c4b7, ec6b8d4 | T1 backend + T3+T4 frontend 인프라 + T5 UX + T2+T6 테스트 |
| 2026-05-07 | Sync (Phase 3) | c6ac934 docs(spec) | frontmatter Implemented |
| 2026-05-07 | E2E Playwright | a4f8307 test(e2e) | 12/12 PASS, 612 줄 spec.ts 영구 회귀 보존 |
| 2026-05-08 | Fix #1 (filter-bar) | 91fd63b fix | chip 위치 overlap 해소 (form 첫 자식 inline) |
| 2026-05-08 | Fix #2 (chart-cell) | df3ca36 fix | StrictMode race condition guard (cancelled flag) |
| 2026-05-09 | **Rollback** | — | chore/integrated-main-merge-2026-04-25 checkout (feat 브랜치 9 commits archive 보존) |

---

## 3. Rollback 결정 사유

사용자 표현 (2026-05-09): "현재 feat/SPEC-CHART-NAV-001 이 브랜치이지? 이 스펙으로 기능 추가하면서 성능이 떨어졌다. 써보니 이 기능이 필요가 없는데, 이전 버전으로 돌아갈 수 있나?"

핵심 원인:
1. **성능 저하 인식** — race guard(df3ca36) 적용 후에도 사용자 경험상 만족스럽지 못함. ChartGrid 부모 frequent re-render → ChartCell useEffect 5회+ 재실행 패턴은 race guard로 영향 완화는 됐지만 근본 fix는 부모 memoization 필요(별도 SPEC 영역).
2. **기능 가치 재평가** — 라이브 사용 후 ThemeDetailPanel 헤더 버튼 + ThemeRankingTable chip + StockSearchBox 인라인 검색 기능 자체가 사용자 워크플로우상 추가 가치 부족으로 판단.

---

## 4. 보존 자산

### 4.1 코드 자산

- **`feat/SPEC-CHART-NAV-001` 브랜치** (9 commits archive)
  - 3f00155 docs(specs)
  - 9be9767 feat(stocks-master) T1 backend
  - 1e20dd8 feat(stocks-master-frontend) T3+T4
  - 2a0c4b7 feat(stocks-master-frontend) T5
  - ec6b8d4 test(stocks-master) T2+T6
  - c6ac934 docs(spec) Implemented
  - a4f8307 test(e2e) Playwright 자동화
  - 91fd63b fix(filter-bar)
  - df3ca36 fix(chart-cell)
  - 미래 재시도 시: `git checkout feat/SPEC-CHART-NAV-001`로 복원 가능

### 4.2 작업 stash

- **stash@{0}**: rollback 직전 hooks 자동 edits (필요 시 `git stash pop` 가능)
- **stash@{1}**: SPEC-AI-REPORT-003 step 1 작업 (chore 시점 보존, 별도 작업 재개 시 사용)

### 4.3 SPEC 산출물 (chore 브랜치)

- `.moai/specs/SPEC-CHART-NAV-001/spec.md` (status: Rolled-back)
- `.moai/specs/SPEC-CHART-NAV-001/plan.md`
- `.moai/specs/SPEC-CHART-NAV-001/research.md`
- `.moai/specs/SPEC-CHART-NAV-001/acceptance.md`
- `.moai/specs/SPEC-CHART-NAV-001/retrospective.md` (본 문서, 신규)

미래 재시도 시 위 산출물 그대로 재사용 가능.

---

## 5. 명명 혼동 사실

사용자 첫 직관 (rollback 직후 검증 시점):
- 표현: "테마 메뉴가 뜬다"
- 추정: 사용자가 SPEC-CHART-NAV-001 결과로 "테마 분석" 탭이 추가됐다고 인식

실제:
- "테마 분석" 탭은 **SPEC-NAVER-THEME-001/002/003/CONSOLIDATED 시리즈** (4월 25일~5월 7일, 17 commits) 결과물
- SPEC-CHART-NAV-001과 무관 — chore 브랜치에 별도 작업으로 통합됨

결정:
- "테마 분석" 탭 + NAVER-THEME 시리즈 그대로 유지
- SPEC-CHART-NAV-001만 rollback

학습:
- SPEC ID와 UI 요소(탭 이름, 버튼 라벨, chip 텍스트) 매핑이 사용자 인식과 어긋날 수 있음
- plan 단계 BRIEF에 "이 SPEC으로 추가/변경되는 UI 요소 목록"을 명시하면 후속 혼동 방지 가능

---

## 6. 학습 사항 (project lesson #7로 lock-in)

다음 3 항목을 새 SPEC plan 단계 BRIEF 작성 의무 항목으로 lock-in:

1. **라이브 사용 가설 명시**: "사용자가 N일 사용 후 어떤 행동을 보일 것이라 기대하는가" (동선 빈도, 사용 시점, 만족도 지표)
2. **성능 측정 지점**: 사용자 경험에 영향을 주는 변경(예: chart cell 마운트, fetch 추가, useEffect 새 생성)이 발생하는 경우 plan 단계에 성능 baseline + 변경 후 목표값 명시
3. **SPEC ID ↔ UI 요소 매핑 표**: BRIEF에 "이 SPEC으로 추가/변경되는 UI 요소 목록" 명시

상세: `~/.claude/projects/-Users-byunjungwon-Dev-my-project-01-my-chart/memory/lessons.md` lesson #7 참조.

---

## 7. References

- spec.md: `.moai/specs/SPEC-CHART-NAV-001/spec.md` (status: Rolled-back)
- plan.md: `.moai/specs/SPEC-CHART-NAV-001/plan.md`
- research.md: `.moai/specs/SPEC-CHART-NAV-001/research.md`
- acceptance.md: `.moai/specs/SPEC-CHART-NAV-001/acceptance.md`
- archive branch: `feat/SPEC-CHART-NAV-001` (9 commits)
- e2e spec (archive): `frontend/e2e/chart-nav.spec.ts` (a4f8307 commit, feat 브랜치 안)
- project lesson #7: `~/.claude/projects/-Users-byunjungwon-Dev-my-project-01-my-chart/memory/lessons.md`
- project memory entry: `project_spec_chart_nav_001_rollback.md`

---

Version: 1.0.0
Status: Final
Last Updated: 2026-05-09
