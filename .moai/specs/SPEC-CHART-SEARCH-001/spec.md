---
id: SPEC-CHART-SEARCH-001
title: 종목 검색 + 한국어 자동완성 + ChartGrid 통합 주입
status: Draft
version: 2.0.0
owner: bjw2002
created: 2026-05-11
updated: 2026-05-12
priority: High
issue_number: 5
replaces: SPEC-CHART-NAV-001 (Search portion only)
depends_on: SPEC-NAVER-THEME-CONSOLIDATED
lifecycle: spec-first
---

# SPEC-CHART-SEARCH-001 — 종목 검색 + 한국어 자동완성 + ChartGrid 통합 주입

## 메타데이터

| 항목 | 값 |
| --- | --- |
| SPEC ID | SPEC-CHART-SEARCH-001 |
| 제목 | 종목 검색 + 한국어 자동완성 + ChartGrid 통합 주입 |
| 생성일 | 2026-05-11 |
| 상태 | Draft (v2.0.0) |
| 버전 | 2.0.0 |
| 우선순위 | High |
| Owner | bjw2002 |
| Lifecycle | spec-first |
| Replaces | SPEC-CHART-NAV-001 (Search portion only) |
| Depends on | SPEC-NAVER-THEME-CONSOLIDATED |
| Development Mode | TDD (RED → GREEN → REFACTOR) |
| BREAKING CHANGE | v1.0.0 modal 격리 패턴 폐기 → ChartGrid 통합 주입 패턴 도입 |

---

## HISTORY

| 일자 | 버전 | 작성자 | 변경 요약 |
| --- | --- | --- | --- |
| 2026-05-11 | v1.0.0 (Draft 초안) | manager-spec | `research.md` 635 line Phase 0.5 분석 기반 초안. SPEC-CHART-NAV-001(rollback, 2026-05-09)의 Search portion만 계승하여 modal 격리 전략으로 재설계. Lesson #7 의무 3항(라이브 사용 가설 §2, 성능 baseline+목표 §3, SPEC↔UI 매핑 §4) 모두 포함. archive `feat/SPEC-CHART-NAV-001` 9 commits 중 6개 파일 cherry-pick + StockSearchBox 부분 재설계 + StockSearchModal 신규. Theme→Grid 진입, appliedContext chip, mismatch banner는 의도적 scope OUT. |
| 2026-05-11 | v1.0.0 (Amendment, audit iteration 1) | manager-spec | I-1~I-6 + Q-1~Q-7 smart defaults 일괄 적용 (annotation cycle 옵션 A). 자세한 내용은 v1.0.0 spec 본문 참조. |
| 2026-05-11 | v1.0.0 Implemented | manager-docs | 12 commits 구현 완료. evaluator-active iter 2 PASS (84/100). 352 frontend vitest + 8 backend pytest PASS, LSP 0. Anti-regression MP-1~MP-5 검증 완료. SPEC-CHART-NAV-001 rollback 재발 방지 invariant 충족. |
| 2026-05-12 | v2.0.0 (BREAKING amendment) | manager-spec | 라이브 사용 후 mental model drift 발견 (PR #6 closed). modal 격리 패턴(REQ-MODAL-001~004) 폐기, ChartGrid 통합 패턴(REQ-INTEGRATE-001~004) 도입. 검색 종목을 ChartGrid 표시 stocks에 주입(필터 결과에 있으면 scroll+highlight, 없으면 prepend), filter state는 deep-equal 보존. v1.0.0 modal 자산은 archive `feat/SPEC-CHART-SEARCH-001` 브랜치에 보존. lesson #7 사례 — plan 단계 mental model이 라이브 가치와 어긋남. |
| 2026-05-12 | v2.0.0 (audit iter 1 minor improvements) | manager-spec | I-1/I-2/I-7 audit iter 1 minor improvements applied. plan-auditor frontmatter false positive (D-1/D-2)는 본 프로젝트 컨벤션 확인 후 무효 처리(labels/created field 기존 SPEC 컨벤션 유지). I-1: REQ-PERF-001 wording 명확화 — unrelated state change vs `injectedStock` prop change 구분, ChartGrid가 `useScreen()` 직접 호출 안 함 전제 명시. I-2: AC-INTEGRATE-005 시나리오를 현실 cascade source 3종 (FilterBar typing / currentPage 변경 / `injectedStock` 변경)으로 교체. I-7: AC-INTEGRATE-001에 prepend 후 `setCurrentPage(0)` reset 동작 추가 (currentPage > 0 조건부). |

---

## 1. Overview

### 1.1 의도

ChartGrid 화면 사용자에게 "필터와 무관하게 임의 종목의 차트를 1 클릭으로 ChartGrid 내부에서 확인"하는 경로를 제공한다. ChartGrid의 기존 필터 흐름(시가총액·등락률·RS·섹터)은 건드리지 않으면서, 검색 결과 종목은 ChartGrid의 표시 stocks 배열에 주입한다.

### 1.2 사용자 가치

- 필터에 잡히지 않는 종목(예: 소형주, 신규상장)도 ChartGrid의 풍부한 차트 포맷으로 즉시 확인 가능.
- 한국어 사용자가 한글/초성/영문/코드 어느 입력 방식으로도 종목을 빠르게 찾을 수 있음.
- 검색 사용 중 ChartGrid 필터 상태는 변경되지 않으므로, 사용자 멘탈 모델 보존.
- 필터 결과에 있는 종목 검색 시 자동 scroll + highlight로 위치 식별 보조.

### 1.3 이전 SPEC과의 차이 (v1.0.0 → v2.0.0 + SPEC-CHART-NAV-001 rollback 반영)

본 SPEC v2.0.0은 두 번의 mental model drift를 거쳐 도달한 최종 설계다.

**SPEC-CHART-NAV-001 (2026-05-09 rollback)**:
- 검색 선택 시 `applyFilters({ codes: [stockCode] })`로 ChartGrid 자체를 덮어씀.
- ChartGrid 재렌더 + ChartCell useEffect race condition + 필터 상태 손실.
- 사용자 라이브 검증: "기능 불필요 + 성능 저하" → 폐기.

**SPEC-CHART-SEARCH-001 v1.0.0 (2026-05-12 PR #6 closed)**:
- 별도 modal portal로 격리 (사용자 선택: "별도 단독 차트 모달 (권장)").
- evaluator-active 84/100 PASS, anti-regression MP-1~MP-5 충족.
- 라이브 사용 후 사용자 피드백: "동작은 하는데, 따로 팝업으로 뜨는건 내가 의도한 바는 아닌데..."
- 추가 명확화: "Chart Grid가 굉장히 좋은 차트 포맷이거든, 그래서 여기서 해당 종목으로 이동하는 것이 좋아."
- lesson #7 패턴 재발 — plan 단계 mental model이 라이브 가치와 어긋남.

**SPEC-CHART-SEARCH-001 v2.0.0 (본 amendment)**:
- ChartGrid 표시 stocks 배열에 검색 종목 주입.
- 필터 결과에 이미 있으면 → 해당 셀로 자동 scroll + 셀 테두리 2~3초 깜박임.
- 필터 결과에 없으면 → ChartGrid 첫 셀로 prepend + 셀 테두리 깜박임.
- `useScreen().screenState.request` deep-equal 보존 (필터 state mutate 금지).

**3가지 패턴 비교**:

| 회귀 축 | NAV-001 (rollback) | SEARCH-001 v1.0 (modal, closed) | SEARCH-001 v2.0 (본 SPEC) |
| --- | --- | --- | --- |
| 검색 결과 표시 위치 | ChartGrid 자체 덮어씀 | 별도 modal (portal → body) | ChartGrid 표시 stocks 주입 |
| ChartGrid UX 가치 활용 | N/A (덮어씀) | 미활용 (별도 modal) | 완전 활용 |
| ChartGrid parent re-render | 전체 재렌더 | 0회 (sibling 격리) | 1회 (injectedStock prop 변경 의도된 동작) |
| 기존 ChartCell useEffect 재실행 | 모든 cells | 0회 | 0회 (cell key 동일성 보장) |
| 필터 상태 보존 (`useScreen.request`) | full reset | deep-equal 보존 | deep-equal 보존 |
| 사용자 mental model 일치 | 손상 | 손상 (팝업 분리감) | 일치 (Grid 내부 동선) |
| 중복 검색 처리 | N/A | N/A (modal 재오픈) | scroll + highlight (no duplicate) |
| 닫기 동선 | chip ✕ + applyFilters | Esc/백드롭/✕ | 닫을 것 없음 (Grid 내부 통합) |

### 1.4 SPEC scope 경계

본 SPEC은 검색 + 자동완성 + ChartGrid 표시 stocks 주입만 다룬다. 다음은 명시적으로 **제외**된다(§8 Exclusions 참조):

- Theme → ChartGrid 진입 (이전 SPEC Feature A 전체)
- 검색 결과 → ChartGrid `filters/request` state mutation (단, 표시 stocks 배열에 주입은 허용)
- appliedContext chip, mismatch banner, FilterBar 검색 라벨 chip
- 검색 기록 / 최근 검색 / 인기 종목
- Fuzzy matching, 오타 보정
- 매치 텍스트 highlight
- modal / popover / overlay 패턴 (v1.0.0 archive로 이동)

---

## 2. Live Use Hypothesis (Lesson #7 의무)

### 2.1 사용 빈도 예측 (v2.0.0 갱신)

| 사용자 시나리오 | 1세션당 예상 검색 횟수 | 기준 |
| --- | --- | --- |
| 평일 장중 일반 사용 | 2~4회 | ChartGrid 통합으로 사용 부담 ↓ (modal close 동선 제거) |
| 장 마감 후 비교 분석 | 4~6회 | 검색 종목 prepend → 다른 cells와 즉시 비교 |
| 주말 리서치 | 6~12회 | 테마·이벤트 종목 탐색 + 필터와 함께 보기 |
| 모바일 사용 | 0~1회 | 데스크탑 우선, 모바일은 best-effort |

예상 평균: **세션당 약 4회** (v1.0.0의 3회 대비 +33%, ChartGrid 통합으로 진입 부담 감소).

### 2.2 진입점

| Entry Point | 가시성 | 트리거 | 본 SPEC 채택 |
| --- | --- | --- | --- |
| ChartGrid toolbar 좌측 input | 항상 | 클릭 → 입력 | 채택 (REQ-SEARCH-001) |
| Cmd/Ctrl+K 단축키 | 숨김 | 글로벌 keydown | 제외 (v2 scope OUT) |
| ChartGrid empty state "검색해보기" 링크 | 조건부 | 필터 결과 0건 시 | 제외 (v2 scope OUT) |

### 2.3 만족 신호 (라이브 검증 의무)

ship 후 2주 라이브 데이터로 측정한다.

> **Latency 정의**: "후보 노출 latency"는 사용자가 타이핑을 정지한 시점부터 측정한다. 즉 debounce(150 ms)가 끝난 후 80 ms 내에 candidates가 화면에 노출되어야 한다.

| 신호 | 정의 | 측정 방법 |
| --- | --- | --- |
| 성공-1 | 타이핑 정지 후 후보 노출 ≤ 80 ms — 첫 keystroke 기준 총 ≤ 230 ms | DevTools Performance 마크 |
| 성공-2 | 후보 선택 후 ChartGrid 첫 셀에 검색 종목 차트 first paint ≤ 300 ms | DevTools Performance 마크 |
| 성공-3 | ChartGrid 기존 셀의 시각적 회귀 0 (cell key 동일성 → 기존 ChartCell instance 재사용) | manual A/B 비교, 검색 전후 ChartCell screenshot 일치 |
| 성공-5 (신규) | 검색 종목이 첫 셀로 보이는 시간 ≤ 300 ms (prepend + scroll 완료) | DevTools Performance 마크 |
| 실패-1 | 사용자가 검색 직후 다른 종목으로 즉시 이동 (검색 가치 미달) | 행동 로그 (수동 관찰) |
| 실패-2 | 검색 종목을 차트로 확인하지 않고 input clear (검색 무산) | 수동 관찰 |

> 성공-4 (modal Esc 닫힘)는 modal 폐기로 삭제됨.

### 2.4 폐기 기준 (Rollback Trigger)

다음 조건 충족 시 SPEC 폐기 검토:

- 사용자 세션당 평균 사용 횟수 < 1.0회 (ship 후 2주)
- 검색 → ChartGrid 첫 셀 표시 평균 latency > 1000 ms
- ChartGrid 성능 회귀 측정값 발생 (MP-1/MP-2 invariant 위반)
- 사용자 명시적 "이거 안 써요" 또는 "Grid 통합 패턴이 원하는 게 아님" 피드백 1건 이상 + 정량 지표 보조 근거
- v3.0.0 후보: 사이드바 fixed panel, 별도 route 등 (별도 SPEC으로 분리)

---

## 3. Performance Baseline + Target (Lesson #7 의무)

### 3.1 측정 Baseline (현재 chore branch, 검색 통합 전 상태)

run phase 시작 시 다음을 React Profiler + DevTools Performance로 실측한다.

| 지표 | 측정 방법 | 예상 Baseline |
| --- | --- | --- |
| ChartGrid 초기 렌더 시간 | React Profiler `ChartGrid` commit time | < 50 ms |
| ChartCell 1개 mount → first paint | `createChart()` → `setData()` 콜백 | < 300 ms (네트워크 포함) |
| FilterBar 입력 → ChartGrid 재렌더 횟수 (submit 전) | React Profiler "Highlight updates" | 0회 |
| ChartCell useEffect 호출 횟수 / 마운트 | console.count() 또는 dev 로그 | 1회 (StrictMode dev 제외) |
| ChartGrid scroll / page change FPS | DevTools Performance recording | ≥ 55 FPS |

### 3.2 SPEC 도입 후 Target

본 SPEC ship 후 다음 측정값을 acceptance gate로 잠근다.

| 지표 | Target | 측정 방법 | 매핑 REQ |
| --- | --- | --- | --- |
| 검색 input → 후보 노출 latency | ≤ 80 ms (debounce 150 ms 종료 후) | `performance.now()` before/after `setCandidates` | NFR-PERF-001 |
| 후보 선택 → ChartGrid 첫 셀 검색 종목 차트 first paint | ≤ 300 ms (prepend + scroll + chart init + setData) | DevTools Performance mark | NFR-PERF-002 |
| ChartGrid parent re-render count (검색 시점) | injectedStock prop 변경으로 인한 1회 cascade 허용 (의도된 동작), 기타 cause로 인한 추가 commit 0회 | React Profiler commit count diff | REQ-PERF-001 |
| 기존 ChartCell useEffect 호출 횟수 (검색 전후) | 0회 증가 (cell key 동일성 → instance 재사용) | `console.count` instrumentation | REQ-PERF-002 |
| ChartGrid scroll / page change FPS during search injection | ≥ 55 FPS (baseline 회귀 0) | DevTools Performance recording | NFR-PERF-003 |
| `GET /api/stocks/master` 응답 시간 (cold) | < 150 ms | timing log | NFR-PERF-004 |
| `GET /api/stocks/master` payload (gzip) | < 50 KB | `curl -H "Accept-Encoding: gzip" \| wc -c` | NFR-PERF-005 |
| Highlight CSS animation 종료 후 class 자동 제거 | 2~3초 후 0개 element가 `cell-search-highlight` class 보유 | DOM querySelector polling | REQ-INTEGRATE-002/003 |

### 3.3 회귀 검증 자동화

- Vitest: `ChartGrid` integration tests (검색 주입 전후 cells 비교, ScreenContext.request deep-equal)
- Vitest: ChartCell useEffect 재실행 0회 검증 (mock spy with cell key tracking)
- Vitest: React Profiler 기반 ChartGrid commit count 측정 (검색 cascade ≤ 1)
- Vitest: 자동완성 latency 단위 테스트 (`performance.now()` 활용)
- Playwright (옵션): 검색 → 선택 → ChartGrid 첫 셀 표시 → highlight 종료 1cycle e2e

---

## 4. SPEC ID ↔ UI Element Mapping (Lesson #7 의무)

본 SPEC이 추가·변경하는 모든 UI 요소를 명시한다.

| # | UI 요소 | 위치 | 텍스트 (확정) | `data-testid` | SPEC 관계 |
| --- | --- | --- | --- | --- | --- |
| 1 | 검색 input | ChartGrid toolbar 좌측 | placeholder `종목명/코드/초성 검색` (정상) / `DB 업데이트 필요` (503) | `chart-search-input` | NEW |
| 2 | 검색 후보 listbox | input 바로 아래 (relative position) | (동적 목록) | `chart-search-listbox` | NEW |
| 3 | 후보 option (per item) | listbox 내부 | `{name} {code} {market}` | `chart-search-option-{code}` | NEW |
| 4 | "검색 결과 없음" 안내 | listbox 내부 (matches.length === 0) | `검색 결과 없음` | `chart-search-empty` | NEW |
| 5 | 503 disabled tooltip | search input hover (503 상태) | `DB 업데이트가 필요합니다` | (`title` 속성) | NEW |
| 6 | **ChartGrid 검색 주입 셀 (v2 신규)** | ChartGrid 첫 셀 위치 (prepend) 또는 기존 셀 (필터 결과에 있으면) | (검색 종목의 ChartCell 동일 포맷) | `chart-cell-injected-{code}` | NEW (v2.0.0) |
| 7 | **ChartGrid 검색 highlight CSS class (v2 신규)** | 검색 주입된 cell 또는 scroll 대상 cell의 outer container | (visual: 셀 테두리 2~3초 깜박임 blue glow) | CSS class `cell-search-highlight` (2~3s 후 자동 제거) | NEW (v2.0.0) |

**v2.0.0 삭제된 UI elements** (v1.0.0 modal 자산, archive 보존):
- ~~stock-search-modal-backdrop~~
- ~~stock-search-modal~~
- ~~stock-search-modal-title~~
- ~~stock-search-modal-timeframe-toggle~~
- ~~stock-search-modal-close-btn~~
- ~~stock-search-modal-chart~~
- ~~stock-search-modal-loading~~
- ~~stock-search-modal-error~~
- ~~stock-search-modal-content~~ (focus trap container)

> Row 6 보충: `chart-cell-injected-{code}`는 ChartGrid의 첫 cell 위치에 prepend된 경우, 또는 필터 결과에 이미 있던 cell이 검색 대상으로 식별되는 경우 동일 testid를 부여. cell 자체는 기존 `ChartCell` 컴포넌트를 그대로 재사용한다 (별도 차트 인스턴스 신규 생성 없음 — 기존 cells의 경우).

> Row 7 보충: highlight class는 검색 주입 시점에 cell outer container에 추가되며, CSS `@keyframes border-flash` animation (2~3s duration)으로 blue glow 효과 부여. useEffect cleanup에서 `setTimeout(() => classList.remove(...), 2500)` + `clearTimeout` 보장.

---

## 5. EARS Requirements

EARS 키워드는 영어로 유지한다(SHALL, WHEN, WHILE, IF, WHERE). 식별자·경로는 영어, 설명문은 한국어로 작성한다.

### 5.1 Module: Search Input + Autocomplete (REQ-SEARCH-001 ~ 006) — 변경 없음

#### REQ-SEARCH-001 (Ubiquitous)

The system **SHALL** mount a single `StockSearchBox` input component on the left side of the `chart-grid-toolbar` div within `ChartGrid.tsx`. Input의 시각 폭은 약 220 px로 고정되며 `flexShrink: 0`을 적용한다.

#### REQ-SEARCH-002 (Event-Driven)

**WHEN** the user first focuses the `StockSearchBox` input within a session, **THEN** the system **SHALL** invoke `useStockMaster()` which dispatches a single `fetchStockMaster()` call to `GET /api/stocks/master` and caches the resolved promise at module level.

#### REQ-SEARCH-003 (Event-Driven)

**WHEN** the user types into `StockSearchBox` and the input value passes a 150 ms debounce, **THEN** the system **SHALL** compute candidates using `matchesQuery(item, query)` and render up to 8 candidates in a `<ul role="listbox">` directly below the input, sorted by descending score (5단계 score 유지: alias prefix=5, code prefix=4, name prefix=3, name substring=2, hangul 초성=1, tiebreaker `name.localeCompare`).

#### REQ-SEARCH-004 (State-Driven)

**WHILE** `matchesQuery` 결과가 0건이고 입력값이 비어있지 않은 상태, the system **SHALL** render a `<li data-testid="chart-search-empty">검색 결과 없음</li>` placeholder.

#### REQ-SEARCH-005 (Ubiquitous)

The system **SHALL** support full keyboard navigation in `StockSearchBox`: ArrowDown/Up (wrap-around + aria-activedescendant), Enter (select), Escape (close + clear), Tab (close + focus next).

#### REQ-SEARCH-006 (Unwanted Behavior)

**IF** `GET /api/stocks/master` returns HTTP 503 with body `{"detail": "stock_meta_not_ready"}`, **THEN** the system **SHALL** disable the `StockSearchBox` input, replace placeholder with `DB 업데이트 필요`, and surface a `title` attribute reading `DB 업데이트가 필요합니다`.

### 5.2 Module: ChartGrid Integration Injection (REQ-INTEGRATE-001 ~ 004) — v2.0.0 신규

> **v1.0.0 DEPRECATED**: REQ-MODAL-001 ~ 004 (modal portal 패턴) 폐기. archive `feat/SPEC-CHART-SEARCH-001` 브랜치에 자산 보존. v3 후보(sidebar/route) 검토 시 참고 가능.

#### REQ-INTEGRATE-001 (Event-Driven)

**WHEN** the user selects a candidate from `StockSearchBox` (mouse click OR Enter key), **THEN** the system **SHALL** inject the searched stock into ChartGrid's displayed stocks list WITHOUT modifying ScreenContext filters. 주입 메커니즘은 `AppContent.tsx`에서 `searchedStock: StockMasterItem | null` state를 lift하고 `<ChartGrid injectedStock={searchedStock} ... />`로 prop drilling한다. ChartGrid 내부에서 `displayedStocks` 계산은 filter results와 `injectedStock`을 union하되 `useScreen().screenState.request` 객체는 절대 수정하지 않는다.

#### REQ-INTEGRATE-002 (Event-Driven)

**WHEN** the searched stock already exists in current filter results (i.e., `filterResults.find(s => s.code === injectedStock.code)` returns truthy), **THEN** the system **SHALL** auto-scroll to that cell's page (via ChartGrid `setCurrentPage(targetPageIndex)`) AND apply a `cell-search-highlight` CSS class to the cell's outer container for 2~3 seconds, NOT prepend a duplicate cell. Duplicate count must be 0. Highlight class는 2~3초 후 useEffect cleanup의 `setTimeout` + `clearTimeout`을 통해 자동 제거된다.

#### REQ-INTEGRATE-003 (Event-Driven)

**WHEN** the searched stock does NOT exist in current filter results, **THEN** the system **SHALL** prepend the stock as the first cell of ChartGrid (i.e., `displayedStocks = [injectedStock, ...filterResults]`) AND apply the `cell-search-highlight` CSS class to the newly prepended cell's outer container, preserving all filter results in subsequent cells unchanged. 기존 cells의 React key는 `stock.code`로 안정성 유지 — prepend는 새 key 추가일 뿐 기존 keys 동일성을 보존하므로 React reconciliation이 기존 ChartCell instances를 재사용한다.

#### REQ-INTEGRATE-004 (Ubiquitous)

The system **SHALL** preserve `useScreen().screenState.request` deep-equal across search injection events. Search injection MUST NOT modify any field of the filter state object (`market_cap_min`, `change_rate_min/max`, `rs_min/max`, `sector`, `codes`, etc.). 정적 분석 가능: `AppContent.tsx`, `ChartGrid.tsx`, `StockSearchBox.tsx` 어디서도 `useScreen()` setter 호출 또는 `applyFilters()` 호출은 검색 동선에서 발생하지 않는다.

### 5.3 Module: Performance Invariants (REQ-PERF-001 ~ 002) — v2.0.0 재작성

#### REQ-PERF-001 (Unwanted Behavior — Anti-regression)

**IF** unrelated state change occurs (FilterBar input typing during compose, ScreenContext result reload, currentPage prop change), **THEN** ChartGrid React.memo **SHALL** block cascade — 추가 commit 0회. **EXCEPT** when `injectedStock` prop changes (intent: 1회 cascade 허용 for prepend + highlight effect).

**아키텍처 전제 (cascade 차단 가능 조건)**: ChartGrid는 `useScreen()`을 **직접 호출하지 않는다**. 대신 AppContent가 `useScreen()`을 호출하고 `filterResults` (또는 동등 prop)를 prop으로 ChartGrid에 전달한다. 이로써 React.memo의 shallow equal이 동일 reference의 `filterResults` prop을 받았을 때 cascade를 차단할 수 있다. 만약 ChartGrid가 `useScreen()`을 직접 호출한다면 context subscription으로 인해 result 변경 시 항상 re-render 발생 → React.memo와 무관하게 cascade. 본 invariant는 이 prop drilling 구조를 전제로 한다.

**Baseline 정의**: §3.1에서 측정한 React Profiler commit count. baseline에는 (i) 초기 mount commits + (ii) ChartGrid 자체 의도된 state 변경 (currentPage prop, pageSize 등)으로 인한 정상 commit이 포함된다. 검색 주입 시점의 추가 cascade는 `injectedStock` prop 변경 1회만 허용.

**검증**: vitest + React Profiler API로 측정. AC-INTEGRATE-005에서 3가지 현실 시나리오 (FilterBar typing / currentPage 변경 / `injectedStock` 변경) 모두 cover.

#### REQ-PERF-002 (Unwanted Behavior — Anti-regression)

**IF** a search injection event occurs, **THEN** the existing ChartCell instances' `useEffect (dependency [stock.code, timeframe])` **SHALL NOT** be re-invoked. 검증: cell key는 `stock.code`로 안정 → React reconciliation이 동일 key의 ChartCell instance를 재사용하며 dependency array도 변경되지 않음 → useEffect skip. 새로 prepend된 cell(필터 결과에 없던 경우)의 useEffect는 1회 호출됨(StrictMode dev에서 2회 허용)으로 mount 동작 정상.

### 5.4 Module: Stocks Master Data Endpoint (REQ-DATA-001 ~ 003) — 변경 없음

#### REQ-DATA-001 (Ubiquitous)

The system **SHALL** expose `GET /api/stocks/master` returning the full set of named active stocks from `stock_meta`. Response body schema unchanged from v1.0.0. Response headers **SHALL** include `ETag` and `Cache-Control: max-age=300`.

#### REQ-DATA-002 (Ubiquitous)

The system **SHALL** query `stock_meta` using `SELECT code, name, market FROM stock_meta WHERE name IS NOT NULL ORDER BY name` against a SQLite connection opened with read-only URI mode (`mode=ro`). INSERT, UPDATE, DELETE, CREATE, DROP, ALTER prohibited.

#### REQ-DATA-003 (Unwanted Behavior)

**IF** the underlying SQLite database does not contain a `stock_meta` table OR the table is empty, **THEN** the system **SHALL** return HTTP 503 with body `{"detail": "stock_meta_not_ready"}`.

### 5.5 Non-Functional Requirements (NFR-PERF / NFR-A11Y / NFR-CONST) — v2.0.0 갱신

| ID | Statement |
| --- | --- |
| NFR-PERF-001 | 검색 input → 후보 노출 ≤ 80 ms (debounce 종료 시점 기준). |
| NFR-PERF-002 | 후보 선택 → ChartGrid 첫 셀에 검색 종목 차트 first paint ≤ 300 ms (의미 재정의: modal first paint → ChartGrid 첫 셀 first paint). 신규 prepend cell의 경우 mount + fetch + setData 포함. 기존 cell scroll의 경우 setCurrentPage 적용 시점 ≤ 50 ms. |
| NFR-PERF-003 | 검색 주입 중 ChartGrid scroll/page change FPS ≥ 55. |
| NFR-PERF-004 | `GET /api/stocks/master` — cold start ≤ 500 ms, warm cache (ETag 304) ≤ 50 ms. |
| NFR-PERF-005 | `GET /api/stocks/master` payload < 50 KB (gzip). |
| NFR-A11Y-001 (v2 갱신) | 검색 후 ChartGrid scroll 또는 prepend 완료 후 `chart-search-input`에 keyboard focus 유지된다 (사용자가 추가 검색 가능). 별도 modal focus trap는 v2에서 불필요 (modal 없음). |
| NFR-A11Y-002 | `StockSearchBox`는 listbox/option ARIA 패턴 + 키보드 only navigation 지원. |
| NFR-CONST-001 | 신규 외부 라이브러리(pip/npm) 추가 0건. 한글 초성은 자체 47 LOC 구현. highlight CSS animation도 자체 keyframes로 구현 (no animation library). |
| NFR-CONST-002 | `stock_meta` DB SELECT-only. |

---

## 6. Delta Markers (Brownfield, v2.0.0)

v1.0.0 modal 자산은 archive `feat/SPEC-CHART-SEARCH-001` 브랜치에 보존됨. 본 SPEC v2.0.0은 새 브랜치 `feat/SPEC-CHART-SEARCH-001-v2`에서 작업.

| Marker | 파일 (project-root-relative) | 비고 |
| --- | --- | --- |
| [REMOVE] | `frontend/src/components/ChartGrid/StockSearchModal.tsx` | v1.0.0 modal — archive 브랜치에 보존, 본 SPEC에서 제거 |
| [REMOVE] | `frontend/src/components/ChartGrid/useFocusTrap.ts` | modal focus trap 헬퍼 — modal 폐기로 불필요 |
| [REMOVE] | `frontend/src/components/ChartGrid/__tests__/StockSearchModal.test.tsx` | modal 테스트 일괄 제거 |
| [REMOVE] | `frontend/src/components/ChartGrid/__tests__/ChartGrid.perf.test.tsx` (modal-coupled portion) | MP-4 portal scope assertion 등 modal-coupled 시나리오 제거 (또는 통합 test로 재작성) |
| [MODIFY] | `frontend/src/components/ChartGrid/ChartGrid.tsx` | `injectedStock?: StockMasterItem \| null` prop 추가, `displayedStocks` union 로직, useEffect로 page scroll + highlight CSS class apply/remove. React.memo 유지. |
| [MODIFY] | `frontend/src/AppContent.tsx` | modal mount 코드 제거, `searchedStock` state 유지하되 ChartGrid에 `injectedStock` prop 전달 |
| [NEW] | `frontend/src/components/ChartGrid/cellHighlight.css` (또는 ChartGrid.tsx 내 inline `<style>`) | `@keyframes border-flash` + `.cell-search-highlight` class 정의 (2~3s blue glow border animation) |
| [NEW] | `frontend/src/components/ChartGrid/__tests__/ChartGrid.integration.test.tsx` | REQ-INTEGRATE-001~004 통합 테스트 (6+ 시나리오) |
| [EXISTING] | `frontend/src/components/ChartGrid/StockSearchBox.tsx` | 재사용, onSelect prop signature 유지 (변경 없음) |
| [EXISTING] | `frontend/src/utils/hangul.ts` | 재사용 |
| [EXISTING] | `frontend/src/utils/hangul-aliases.ts` | 재사용 |
| [EXISTING] | `frontend/src/hooks/useStockMaster.ts` | 재사용 |
| [EXISTING] | `frontend/src/api/stocks.ts` | 재사용 |
| [EXISTING] | `frontend/src/components/ChartGrid/ChartCell.tsx` | 변경 없음. 기존 props 그대로 사용 (cell key 동일성으로 instance 재사용). |
| [EXISTING] | `frontend/src/contexts/ScreenContext.tsx` | 변경 없음. 검색 동선이 filter state mutate하지 않음. |
| [EXISTING] | `frontend/src/components/FilterBar/FilterBar.tsx` | 변경 없음. |
| [EXISTING] | `backend/routers/stocks.py`, `backend/services/stocks_master_service.py`, `backend/main.py`, `backend/tests/test_stocks_master.py` | 변경 없음. Backend는 v1.0.0 그대로 활용. |

---

## 7. Anti-regression Acceptance (Must-pass) — v2.0.0 재정의

SPEC-CHART-NAV-001 rollback + SPEC-CHART-SEARCH-001 v1.0.0 closure 두 사례의 실패 모드를 명시적으로 방어한다.

### MP-1: ChartGrid 부모 re-render count 제한 (v2 재정의)

**조건**: 검색 주입 이벤트(`injectedStock` prop 변경) 발생 시 `ChartGrid` 컴포넌트의 React Profiler commit count는 baseline 대비 **+1 cascade 허용** (의도된 동작). 그 외 cause(filter change, scroll, theme change, modal open in other modules)로 인한 추가 cascade는 0회. React.memo + props referential equality로 차단.

**검증**: `acceptance.md` AC-INTEGRATE-005 (vitest + React Profiler API).

### MP-2: 기존 ChartCell useEffect 재실행 0회 (v2 wording 명확화)

**조건**: 검색 주입 이벤트 시 기존 `ChartCell.tsx`의 `useEffect(..., [stock.code, timeframe])` 호출 횟수 증가는 0회. cell key는 `stock.code`로 안정 → React reconciliation이 동일 cell instance를 재사용 → dependency array 미변경 → useEffect skip. 새로 prepend된 cell의 useEffect는 1회 mount 호출(StrictMode dev 2회)이며 본 invariant 대상이 아님.

**검증**: `acceptance.md` AC-INTEGRATE-006 (vitest + console.count instrumentation with cell key tracking).

### MP-3: 필터 상태 보존 (v1 유지)

**조건**: 검색 주입 전후 `useScreen().screenState.request` 객체가 deep-equal.

**검증**: `acceptance.md` AC-INTEGRATE-003 (vitest deep-equal assertion).

### MP-4: ChartGrid stocks 변경 시 ScreenContext.request 미변경 (v2 재정의)

**조건**: ChartGrid의 `displayedStocks` 배열이 검색 주입으로 변경되더라도 `useScreen().screenState.request` 객체는 절대 mutate되지 않음. 정적 분석으로 `AppContent.tsx`, `ChartGrid.tsx`, `StockSearchBox.tsx`에서 `useScreen()` setter 또는 `applyFilters()` 호출이 검색 동선에서 발생하지 않음을 확인.

**검증**: `acceptance.md` AC-INTEGRATE-003 (deep-equal) + AC-ARCH-001 (정적 grep 분석).

> v1.0.0 MP-4 (portal subtree scope)는 modal 폐기로 폐기됨.

### MP-5: 외부 라이브러리 추가 0 (v1 유지)

**조건**: `package.json`, `requirements.txt` 신규 의존성 0건. highlight CSS animation도 자체 keyframes로 구현 (no animation library).

**검증**: 수동 diff 검토 + CI lint.

---

## 8. Exclusions (What NOT to Build) — v2.0.0 갱신

본 SPEC이 의도적으로 다루지 않는 항목.

| # | 제외 항목 | 사유 |
| --- | --- | --- |
| EX-1 | Theme → ChartGrid 진입 (이전 SPEC Feature A 전체) | SPEC-CHART-NAV-001 rollback. 별도 SPEC 재제안 가능. |
| EX-2 (v2 wording 수정) | 검색 결과 → ChartGrid `filters/request` state mutation | 본 SPEC의 핵심 결정. 필터 state mutate는 SPEC-CHART-NAV-001 회귀의 핵심 원인이므로 절대 금지. **단, 표시 stocks 배열에 추가는 허용** (REQ-INTEGRATE-001~003). 두 동작의 차이: stocks 배열은 ChartGrid 내부 derived state이며 `useScreen().screenState.request`와 분리됨. |
| EX-3 | `appliedContext` chip / `mismatch banner` / FilterBar 검색 라벨 chip | 필터 state mutate하지 않으므로 chip 의미 없음. |
| EX-4 | 검색 기록 / 최근 검색 / 인기 종목 / 연관 종목 | scope 확정. v3 후보. |
| EX-5 | Fuzzy matching, 오타 보정 | 한국 사용자는 정확 입력 우세. v3 후보. |
| EX-6 | 매치 텍스트 highlight (굵게/색상) | listbox 후보 텍스트의 매치 부분 강조는 scope 외. cell highlight (REQ-INTEGRATE-002/003)와 다름. |
| EX-7 | debounce 시간 조정 / 적응형 debounce | 150 ms 고정. |
| EX-9 | Cmd/Ctrl+K 글로벌 키보드 단축키 | 글로벌 keydown 리스너 도입은 본 SPEC scope 외. |
| EX-10 | ChartGrid empty state UX 변경 (검색 진입 링크 등) | scope 외. |
| EX-11 | URL deep linking (`?tab=chart-grid&code=005930`) | SPEC-TAB-URL-001로 분리. |
| EX-12 | `DbUpdateButton` 클릭 시 stocks_master cache invalidation | `useStockMaster` cachedPromise reset은 본 SPEC scope 외. |
| EX-13 | 백엔드 in-memory TTL 캐시 | DB ETag 기반 캐싱으로 충분. |
| EX-14 | 신규 pip / npm 의존성 | NFR-CONST-001로 강제. |
| EX-15 | ETF / 해외종목 / 5만 종목 규모 scaling | 본 SPEC은 현재 2546개 한국 종목 한정. |
| EX-16 (v2 신규) | **modal / popover / overlay 패턴** | v1.0.0 modal 패턴은 archive `feat/SPEC-CHART-SEARCH-001` 브랜치에 보존되어 있으나 v2 본 SPEC scope 외. v3 후보(sidebar fixed panel, separate route)도 별도 SPEC으로 분리. |
| EX-17 (v2 신규) | 검색 종목 차트 시간프레임(timeframe) 토글 | v1.0.0 modal의 `일봉/주봉` 토글은 modal 폐기로 함께 폐기. 검색 종목 차트는 ChartGrid의 현재 timeframe state를 그대로 사용 (별도 토글 불필요). |
| EX-18 (v2 신규) | 검색 종목 차트 닫기 동선 | ChartGrid 내부 통합으로 별도 close 동선 불필요. 다음 검색 또는 페이지 변경/필터 변경 시 자연스럽게 대체. |
| EX-19 (v2 신규) | 사이드바 fixed panel, 별도 route 등 v3 후보 패턴 | v2 ship 후 사용자 피드백에 따라 v3 후보로 분리. |

---

## 9. v2.0 Decisions (Annotation cycle resolved)

v1.0 Q-1~Q-7 결정사항은 그대로 유지 (alias 50종, 키보드 nav, 5단계 score, debounce 150 ms 등 변경 없음). 단 Q-4 (modal close → input clear)와 Q-7 (timeframe 계승)은 modal 폐기로 의미 변경됨.

### v2.0 신규 결정사항 (사용자 결정, 2026-05-12)

| ID | 결정 | 반영 위치 | Scope |
| --- | --- | --- | --- |
| V2-Q1 | **검색 결과 표시 위치 = ChartGrid 첫 셀 prepend** (필터 결과에 없는 경우). 필터 결과에 있는 경우 해당 cell로 scroll. 사용자 결정: "검색 결과에 없는 경우 목록에 추가해서 가는 것도 나쁘지 않아." | REQ-INTEGRATE-001/003 | **포함** |
| V2-Q2 | **중복 처리 = scroll + highlight only** (no prepend duplicate). 검색 종목이 이미 필터 결과에 있으면 자동 scroll to page + highlight, prepend 0건. 사용자 결정 (권장 옵션): "해당 셀로 자동 scroll + highlight 애니메이션". | REQ-INTEGRATE-002 | **포함** |
| V2-Q3 | **Highlight 스타일 = 셀 테두리 2~3초 깜박임** (CSS animation, blue glow). 사용자 결정 (권장 옵션): "셀 테두리 2~3초 깜박임 — 차분한 UX, 가볍고 세련". | REQ-INTEGRATE-002/003 + §4 row 7 | **포함** |
| V2-Q4 | **modal 패턴 폐기**. v1.0.0 modal 자산은 archive `feat/SPEC-CHART-SEARCH-001` 브랜치에 보존. 향후 v3 후보(sidebar/route) 검토 시 참고. 사용자 라이브 피드백: "동작은 하는데, 따로 팝업으로 뜨는건 내가 의도한 바는 아닌데..." | §1.3 비교 표 + EX-16 | **포함** |
| V2-Q5 | **검색 종목 차트의 timeframe = ChartGrid 현재 timeframe 그대로** (별도 토글 없음). 기존 cells의 timeframe 환경과 일치. | EX-17 | **제외 (timeframe 토글)** |
| V2-Q6 | **검색 종목 차트 닫기 동선 없음**. ChartGrid 내부 통합이므로 다음 검색 또는 필터 변경 시 자연스럽게 대체. | EX-18 | **제외 (close 동선)** |

status는 `Draft (v2.0.0)` 유지 (annotation cycle resolved, run phase 진입 가능).

---

## 10. References

- `.moai/specs/SPEC-CHART-SEARCH-001/plan.md` (v2.0.0) — TDD task decomposition + file change matrix + risk register
- `.moai/specs/SPEC-CHART-SEARCH-001/acceptance.md` (v2.0.0) — Given/When/Then scenarios + must-pass criteria
- `.moai/specs/SPEC-CHART-SEARCH-001/spec-compact.md` (v2.0.0) — run phase compact reference
- `.moai/specs/SPEC-CHART-SEARCH-001/research.md` — Phase 0.5 Deep Research (research §2 cherry-pick, §3 perf root cause, §8 risks)
- `.moai/specs/SPEC-CHART-NAV-001/retrospective.md` — Rollback 원인 정리
- `.moai/reports/eval/SPEC-CHART-SEARCH-001-eval-2.md` — v1.0.0 PASS 84/100 (Anti-regression evidence)
- archive: `git checkout feat/SPEC-CHART-SEARCH-001` (v1.0.0 modal 자산 보존)
- archive: `git checkout feat/SPEC-CHART-NAV-001` (rollback 9 commits 보존)
- `~/.claude/projects/-Users-byunjungwon-Dev-my-project-01-my-chart/memory/lessons.md` — Lesson #7 (라이브 사용 가설 + 성능 + UI 매핑 의무)

---

Version: 2.0.0 (BREAKING amendment)
Status: Draft
Last Updated: 2026-05-12
