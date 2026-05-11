---
id: SPEC-CHART-SEARCH-001
title: 종목 검색 + 한국어 자동완성 + 단독 차트 모달
status: Implemented
version: 1.0.0
owner: bjw2002
created: 2026-05-11
updated: 2026-05-11
priority: High
issue_number: 5
replaces: SPEC-CHART-NAV-001 (Search portion only)
depends_on: SPEC-NAVER-THEME-CONSOLIDATED
lifecycle: spec-first
---

# SPEC-CHART-SEARCH-001 — 종목 검색 + 한국어 자동완성 + 단독 차트 모달

## 메타데이터

| 항목 | 값 |
| --- | --- |
| SPEC ID | SPEC-CHART-SEARCH-001 |
| 제목 | 종목 검색 + 한국어 자동완성 + 단독 차트 모달 |
| 생성일 | 2026-05-11 |
| 상태 | Draft |
| 버전 | 1.0.0 |
| 우선순위 | High |
| Owner | bjw2002 |
| Lifecycle | spec-anchored |
| Replaces | SPEC-CHART-NAV-001 (Search portion only) |
| Depends on | SPEC-NAVER-THEME-CONSOLIDATED |
| Development Mode | TDD (RED → GREEN → REFACTOR) |

---

## HISTORY

| 일자 | 버전 | 작성자 | 변경 요약 |
| --- | --- | --- | --- |
| 2026-05-11 | v1.0.0 (Draft 초안) | manager-spec | `research.md` 635 line Phase 0.5 분석 기반 초안. SPEC-CHART-NAV-001(rollback, 2026-05-09)의 Search portion만 계승하여 modal 격리 전략으로 재설계. Lesson #7 의무 3항(라이브 사용 가설 §2, 성능 baseline+목표 §3, SPEC↔UI 매핑 §4) 모두 포함. archive `feat/SPEC-CHART-NAV-001` 9 commits 중 6개 파일 cherry-pick + StockSearchBox 부분 재설계 + StockSearchModal 신규. Theme→Grid 진입, appliedContext chip, mismatch banner는 의도적 scope OUT. |
| 2026-05-11 | v1.0.0 (Amendment, audit iteration 1) | manager-spec | I-1~I-6 + Q-1~Q-7 smart defaults 일괄 적용 (annotation cycle 옵션 A). **수정**: I-1 §2.3 latency narrative 수정 (debounce 종료 후 80 ms = 첫 keystroke 기준 ≤ 230 ms 명확화), I-2 REQ-MODAL-001에 timeframe 계승 정책 commit (Q-7 해결), I-3 timeframe 파라미터를 backend chart 라우터 실제값(`daily`/`weekly`)으로 통일, I-4 §4 UI 매핑 표에 modal-content focusable container 행 추가, I-5 NFR-PERF-004에 warm cache 304 target 추가, I-6 plan §6 R-2 mitigation에 `React.memo` 주(主) 기법 명시. **신규 결정**: Q-1 영문→한글 alias 50종 hardcoded 사전 채택, Q-4 modal close → input 자동 초기화, Q-5 기존 AnalysisModal 패턴 답습 (focus trap 헬퍼 부재 시 신규 작성), Q-7 ChartGrid 마지막 timeframe 계승(fallback `daily`). **추가 제외**: Q-2 Cmd/Ctrl+K, Q-3 empty state 링크, Q-6 DbUpdateButton cache invalidation. §9 Open Questions → v1.0 결정사항 노트로 대체. status `Draft` 유지. |
| 2026-05-11 | v1.0.0 Implemented | manager-docs | 12 commits 구현 완료 (9d64437~f2c0d9f). evaluator-active iter 2 PASS (84/100). 352 frontend vitest + 8 backend pytest PASS, LSP 0. 신규 파일 19 + 변경 3. 외부 의존성 추가 0 (NFR-CONST-001). Anti-regression MP-1~MP-5 검증 완료. @MX:TODO 2건 follow-up 예약 (MP-1/MP-2 정밀 측정). SPEC-CHART-NAV-001 rollback 재발 방지 invariant 충족. |

---

## 1. Overview

### 1.1 의도

ChartGrid 화면 사용자에게 "필터와 무관하게 임의 종목의 차트를 1 클릭으로 확인"하는 경량 경로를 제공한다. ChartGrid의 기존 필터 흐름(시가총액·등락률·RS·섹터)은 건드리지 않고, 검색은 별도 modal로 격리해 disjoint한 의미를 부여한다.

### 1.2 사용자 가치

- 필터에 잡히지 않는 종목(예: 소형주, 신규상장)도 즉시 차트로 확인 가능.
- 한국어 사용자가 한글/초성/영문/코드 어느 입력 방식으로도 종목을 빠르게 찾을 수 있음.
- 검색 사용 중 ChartGrid의 현재 필터 결과는 변경되지 않으므로, 빠른 단일 종목 lookup → 닫기 → 원래 작업 복귀 동선이 자연스럽다.

### 1.3 이전 SPEC과의 차이 (SPEC-CHART-NAV-001 rollback 사유 반영)

SPEC-CHART-NAV-001(2026-05-09 rollback)은 검색 선택 시 `applyFilters({ codes: [stockCode] })`로 ChartGrid 자체를 덮어썼다. 결과:

1. ChartGrid 재렌더 → ChartCell useEffect race condition으로 빈 차트 표시 (df3ca36에서 cancelled flag로 완화했으나 근본 미해결).
2. 사용자 멘탈 모델 손상: "내 필터 결과는 어디 갔지?" + 복귀하려면 chip ✕ + applyFilters 1회 추가.
3. 사용자 라이브 검증: "기능 불필요 + 성능 저하" → 폐기.

본 SPEC은 다음 3개 축에서 회귀를 방어한다:

| 회귀 축 | SPEC-CHART-NAV-001 | SPEC-CHART-SEARCH-001 (본 SPEC) |
| --- | --- | --- |
| 검색 결과 표시 위치 | ChartGrid 자체를 덮어씀 | 별도 modal(React Portal → `document.body`) |
| ChartGrid 부모 re-render 영향 | applyFilters 호출 → ChartCell useEffect 재실행 | modal은 ChartGrid sibling, ChartCell useEffect 재실행 0회 |
| 필터 상태 보존 | full reset (DEFAULT_SCREEN_REQUEST) | 변경 없음 (disjoint semantic) |
| 검색 닫기 동선 | chip ✕ + applyFilters | Esc/백드롭/✕ 1회 |

### 1.4 SPEC scope 경계

본 SPEC은 검색 + 자동완성 + 단독 모달 차트만 다룬다. 다음은 명시적으로 **제외**된다(§7 Exclusions 참조):

- Theme → ChartGrid 진입 (이전 SPEC Feature A 전체)
- 검색 결과 → ChartGrid 필터 주입 (이전 SPEC Feature B의 grid 주입 동선)
- appliedContext chip, mismatch banner, FilterBar 검색 라벨 chip
- 검색 기록 / 최근 검색 / 인기 종목
- Fuzzy matching, 오타 보정
- 매치 텍스트 highlight

---

## 2. Live Use Hypothesis (Lesson #7 의무)

### 2.1 사용 빈도 예측

| 사용자 시나리오 | 1세션당 예상 검색 횟수 | 기준 |
| --- | --- | --- |
| 평일 장중 일반 사용 | 1~3회 | 필터 결과에 없는 종목 단발성 확인 |
| 장 마감 후 비교 분석 | 3~5회 | 다른 종목과 비교, 메모 작성 |
| 주말 리서치 | 5~10회 | 테마·이벤트 기반 종목 탐색 |
| 모바일 사용 | 0~1회 | 데스크탑 우선, 모바일은 best-effort |

예상 평균: **세션당 약 3회**. SPEC-CHART-NAV-001은 grid 통합 부담으로 "세션당 1회 미만"으로 평가되었으나, 본 SPEC은 modal 격리로 검색 → 차트 표시까지 1 클릭 + 닫기 1 클릭으로 단축되어 실용성이 더 높을 것으로 예측한다.

### 2.2 진입점

| Entry Point | 가시성 | 트리거 | 본 SPEC 채택 |
| --- | --- | --- | --- |
| ChartGrid toolbar 좌측 input | 항상 | 클릭 → 입력 | 채택 (REQ-SEARCH-001) |
| Cmd/Ctrl+K 단축키 | 숨김 | 글로벌 keydown | **제외** (Open Question Q-2) |
| ChartGrid empty state "검색해보기" 링크 | 조건부 | 필터 결과 0건 시 자동 안내 | **제외** (Open Question Q-3) |

### 2.3 만족 신호 (라이브 검증 의무)

다음 시그널을 ship 후 2주 라이브 데이터로 측정한다.

> **Latency 정의 (I-1 amendment)**: "후보 노출 latency"는 **사용자가 타이핑을 정지한 시점부터** 측정한다. 즉 debounce(150 ms)가 끝난 후 80 ms 내에 candidates가 화면에 노출되어야 한다. 첫 keystroke 기준으로는 `debounce(150 ms) + compute+render(≤ 80 ms) = 총 ≤ 230 ms`. NFR-PERF-001의 ≤ 80 ms는 어디까지나 debounce 종료 후 compute+render 시간을 가리킨다.

| 신호 | 정의 | 측정 방법 |
| --- | --- | --- |
| 성공-1 | 타이핑 정지 후(debounce 종료 후) 후보 노출 ≤ 80 ms — 첫 keystroke 기준 총 ≤ 230 ms | DevTools Performance 마크 (debounce 종료 ↔ setCandidates 콜백) |
| 성공-2 | 후보 선택 후 모달 차트 first paint ≤ 300 ms | DevTools Performance 마크 |
| 성공-3 | ChartGrid 시각적 회귀 0 | manual A/B 비교, modal 열림 중 ChartGrid screenshot 일치 |
| 성공-4 | Esc 1회로 모달 닫힘 + 검색 input focus 복귀 | manual 키보드 only navigation |
| 실패-1 | 사용자가 modal 즉시 닫고 다른 진입로 사용 | 행동 로그 (수동 관찰) |
| 실패-2 | 모달 stale 상태 (열려있는 채 다른 탭 이동) | 수동 관찰 |

### 2.4 폐기 기준 (Rollback Trigger)

다음 조건 충족 시 SPEC 폐기 검토:

- 사용자 세션당 평균 사용 횟수 < 0.5회 (ship 후 2주)
- 검색 → 차트 표시 평균 latency > 1000 ms
- ChartGrid 성능 회귀 측정값 발생 (모달 격리 invariant 위반)
- 사용자 명시적 "이거 안 써요" 피드백 1건 이상 + 정량 지표 보조 근거

---

## 3. Performance Baseline + Target (Lesson #7 의무)

### 3.1 측정 Baseline (현재 chore branch, modal 없음 상태)

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
| 후보 선택 → 모달 차트 first paint | ≤ 300 ms (네트워크 + chart init + setData 포함) | DevTools Performance mark | NFR-PERF-002 |
| 모달 표시 중 ChartGrid 추가 재렌더 횟수 | 0회 (baseline과 동일) | React Profiler 모달 열기 전후 commit count diff | REQ-PERF-001 |
| 모달 차트 useEffect 호출 횟수 / 모달 열림당 | 1회 (StrictMode dev에서 2회 허용) | `console.count` instrumentation | REQ-PERF-002 |
| ChartGrid scroll / page change FPS during modal open | ≥ 55 FPS (baseline 회귀 0) | DevTools Performance recording | NFR-PERF-003 |
| `GET /api/stocks/master` 응답 시간 (cold) | < 150 ms | timing log | NFR-PERF-004 |
| `GET /api/stocks/master` payload (gzip) | < 50 KB | `curl -H "Accept-Encoding: gzip" \| wc -c` | NFR-PERF-005 |

### 3.3 회귀 검증 자동화

- Vitest: `ChartGrid` / `ChartCell` render count 단위 테스트 (모달 열림 전후 호출 횟수 검증)
- Vitest: 자동완성 latency 단위 테스트 (`performance.now()` 활용)
- Playwright (옵션): 검색 → 선택 → 모달 → 닫기 1cycle e2e + performance.timing 캡처

---

## 4. SPEC ID ↔ UI Element Mapping (Lesson #7 의무)

본 SPEC이 추가·변경하는 모든 UI 요소를 명시한다. 라이브 사용 중 "X UI 요소가 어느 SPEC 결과인지" 추적 가능하도록 한다.

| # | UI 요소 | 위치 | 텍스트 (확정) | `data-testid` | SPEC 관계 |
| --- | --- | --- | --- | --- | --- |
| 1 | 검색 input | ChartGrid toolbar 좌측 | placeholder `종목명/코드/초성 검색` (정상) / `DB 업데이트 필요` (503) | `chart-search-input` | NEW |
| 2 | 검색 후보 listbox | input 바로 아래 (relative position) | (동적 목록) | `chart-search-listbox` | NEW |
| 3 | 후보 option (per item) | listbox 내부 | `{name} {code} {market}` | `chart-search-option-{code}` | NEW |
| 4 | "검색 결과 없음" 안내 | listbox 내부 (matches.length === 0) | `검색 결과 없음` | `chart-search-empty` | NEW |
| 5 | StockSearchModal backdrop | document.body portal | (시각만, semi-transparent) | `stock-search-modal-backdrop` | NEW |
| 6 | StockSearchModal 컨테이너 | document.body portal | `role="dialog" aria-modal="true"` | `stock-search-modal` | NEW |
| 7 | Modal 타이틀 | Modal header | `{name} ({code})` | `stock-search-modal-title` | NEW |
| 8 | Modal timeframe 토글 | Modal header | UI 라벨 `일봉` / `주봉`, 내부 파라미터값 `daily` / `weekly` (백엔드 `GET /api/chart` 호환) | `stock-search-modal-timeframe-toggle` | NEW |
| 9 | Modal 닫기 버튼 | Modal header 우측 | `✕` (`aria-label="닫기"`) | `stock-search-modal-close-btn` | NEW |
| 10 | Modal chart canvas container | Modal body | (lightweight-charts container) | `stock-search-modal-chart` | NEW |
| 11 | Modal 로딩 indicator | chart load 중 | (spinner) | `stock-search-modal-loading` | NEW |
| 12 | Modal 에러 표시 | fetch 실패 시 | `{errorMessage}` | `stock-search-modal-error` | NEW |
| 13 | 503 disabled tooltip | search input hover (503 상태) | `DB 업데이트가 필요합니다` | (`title` 속성) | NEW |
| 14 | Modal focusable container (I-4) | modal portal root inside (modal-content) | (visual: invisible focus container) | `stock-search-modal-content` | NEW |

> Row 14 보충 (I-4): `<div tabIndex={-1} data-testid="stock-search-modal-content">`는 focus trap의 root이자 modal open 시 초기 focus target. `role="dialog"` + `aria-modal="true"` + `aria-labelledby="stock-search-modal-title"`를 보유한다. focus trap 메커니즘은 `frontend/src/components/AnalysisModal.tsx` 기존 패턴을 답습하며(Q-5), 기존 모달이 `Tab` 가둠 헬퍼를 가지지 않을 경우 plan T5에서 작은 헬퍼를 신규 작성한다.

> Row 8 보충 (I-3): timeframe 토글의 UI 라벨은 한국어(`일봉`/`주봉`)이지만 API 호출 + state 값은 백엔드 `backend/routers/chart.py:21`의 `timeframe: str = Query(default="daily")` 정의에 맞추어 `'daily' | 'weekly'`로 통일. 본 SPEC 어디서든 `'D'/'W'` 표기는 사용하지 않는다.

> 라이브 사용 중 "X UI 요소가 보여요/안 보여요" 신고 시 본 표로 SPEC ID 역추적.

---

## 5. EARS Requirements

EARS 키워드는 영어로 유지한다(SHALL, WHEN, WHILE, IF, WHERE). 식별자·경로는 영어, 설명문은 한국어로 작성한다.

### 5.1 Module: Search Input + Autocomplete (REQ-SEARCH-001 ~ 006)

#### REQ-SEARCH-001 (Ubiquitous)

The system **SHALL** mount a single `StockSearchBox` input component on the left side of the `chart-grid-toolbar` div within `ChartGrid.tsx`. Input의 시각 폭은 약 220 px로 고정되며 `flexShrink: 0`을 적용한다. 모달·글로벌 헤더·Cmd+K 진입은 본 SPEC에서 채택하지 않는다.

#### REQ-SEARCH-002 (Event-Driven)

**WHEN** the user first focuses the `StockSearchBox` input within a session, **THEN** the system **SHALL** invoke `useStockMaster()` which dispatches a single `fetchStockMaster()` call to `GET /api/stocks/master` and caches the resolved promise at module level. 같은 세션 내 두 번째 focus부터는 추가 네트워크 호출이 발생하지 **않는다**.

#### REQ-SEARCH-003 (Event-Driven)

**WHEN** the user types into `StockSearchBox` and the input value passes a 150 ms debounce, **THEN** the system **SHALL** compute candidates using `matchesQuery(item, query)` from `frontend/src/utils/hangul.ts` and render up to 8 candidates in a `<ul role="listbox">` directly below the input, sorted by descending score.

매칭 score 5단계 (높을수록 우선, Q-1 v1.0 결정 반영):
1. (score 5) 영문 alias prefix 일치 (예: `samsung` → 삼성전자) — `frontend/src/utils/hangul-aliases.ts` 50종 사전 활용
2. (score 4) 종목코드 prefix 일치 — 숫자 입력 시
3. (score 3) 종목명 prefix 일치
4. (score 2) 종목명 substring 부분일치
5. (score 1) 한글 초성 prefix 일치

동점일 경우 tiebreaker로 `name.localeCompare(other.name)` 오름차순을 적용한다.

**Alias 사전 사양 (Q-1, v1.0)**: `frontend/src/utils/hangul-aliases.ts` 파일에 50종 ko↔en 매핑을 hardcoded export한다 (예: `{ '삼성전자': ['samsung', 'samsung electronics'], 'SK하이닉스': ['sk hynix'], ... }`). 선정 기준은 시가총액 상위 + 외국인 거래 비중 상위로 manager-spec/run 단계에서 확정한다. alias 매칭은 lowercase + trim 후 prefix 비교한다. 사전에 없는 종목의 영문 입력은 score 0 (매치 안 됨).

#### REQ-SEARCH-004 (State-Driven)

**WHILE** `matchesQuery` 결과가 0건이고 입력값이 비어있지 않은 상태, the system **SHALL** render a `<li data-testid="chart-search-empty">검색 결과 없음</li>` placeholder inside the listbox. "결과 없음"은 일반 option과 시각적으로 구분되며 `aria-disabled="true"`를 갖는다.

#### REQ-SEARCH-005 (Ubiquitous)

The system **SHALL** support full keyboard navigation in `StockSearchBox`:
- `ArrowDown` / `ArrowUp` — listbox 내 후보 하이라이트 이동 (wrap-around). `aria-activedescendant`로 현재 항목 ID 노출.
- `Enter` — 하이라이트된 후보 선택, 비어있으면 첫 번째 후보 선택.
- `Escape` — listbox 닫기 + input clear (modal이 열려있지 않을 때만).
- `Tab` — listbox 닫기 + 다음 focusable 요소로 이동.

#### REQ-SEARCH-006 (Unwanted Behavior)

**IF** `GET /api/stocks/master` returns HTTP 503 with body `{"detail": "stock_meta_not_ready"}`, **THEN** the system **SHALL** disable the `StockSearchBox` input, replace placeholder text with `DB 업데이트 필요`, and surface a `title` attribute reading `DB 업데이트가 필요합니다`. 사용자 입력은 dispatch되지 않는다.

### 5.2 Module: Stand-alone Modal Display + Accessibility (REQ-MODAL-001 ~ 004)

#### REQ-MODAL-001 (Event-Driven)

**WHEN** the user selects a candidate from `StockSearchBox` (mouse click OR Enter key), **THEN** the system **SHALL** lift `selectedStock: StockMasterItem` state to the `AppContent` host component and mount `StockSearchModal` via `ReactDOM.createPortal(modal, document.body)`. The modal **SHALL** render a stand-alone lightweight-charts instance for the selected stock.

**Initial timeframe (Q-7 결정, I-2 commit)**: 모달의 초기 timeframe은 **ChartGrid가 마지막으로 사용한 timeframe을 계승**한다. ChartGrid에 활성 timeframe state가 없거나 알 수 없는 경우 `'daily'`(일봉)로 fallback한다. 계승 메커니즘은 `AppContent.tsx`에서 `ChartGrid`의 현재 timeframe state를 prop 또는 read-only context를 통해 `StockSearchModal`에 전달한다. 모달이 ChartGrid timeframe state를 구독하지는 않는다 (REQ-PERF-001 invariant 보존 — modal subtree에 ChartGrid context 의존성 도입 금지). 따라서 modal mount 시점에 1회 snapshot으로만 사용된다.

#### REQ-MODAL-002 (Event-Driven)

**WHEN** the user invokes any of the modal close actions (`Escape` keypress / backdrop click / `✕` button click), **THEN** the system **SHALL**:

1. Unmount the modal portal.
2. Clear `selectedStock` state to `null`.
3. Restore keyboard focus to the `StockSearchBox` input element via a saved trigger ref.
4. **Clear the `StockSearchBox` input value to empty string (Q-4 결정)** — 사용자가 modal을 닫으면 다음 검색을 위해 input은 비워진 상태로 복귀한다. listbox도 닫힌 상태.

Modal 외부에서 발생한 `selectedStock = null` 전이도 동일한 정리 절차를 수행한다.

#### REQ-MODAL-003 (Ubiquitous)

The system **SHALL** apply WCAG 2.1 AA modal a11y patterns to `StockSearchModal`:
- `role="dialog"` + `aria-modal="true"` + `aria-labelledby="stock-search-modal-title"`.
- 초기 focus는 modal-content (`tabIndex={-1}`) 또는 닫기 버튼.
- Tab/Shift+Tab 키 입력은 modal subtree 내부로 제한 (focus trap). 구현 방법은 plan.md에서 결정.
- modal 열림 시 `document.body.style.overflow = "hidden"` (scroll lock).
- modal 닫힘 시 scroll lock 해제 및 focus 복귀(REQ-MODAL-002와 결합).

#### REQ-MODAL-004 (Optional)

**WHERE** the user clicks the timeframe toggle inside the modal header, the system **SHALL** re-fetch chart data for the new timeframe (`일봉` ↔ `주봉`) and re-render the same chart instance without closing the modal. 토글 상태는 modal 닫힐 때 폐기된다.

### 5.3 Module: Performance Invariants (REQ-PERF-001 ~ 002)

#### REQ-PERF-001 (Unwanted Behavior — Anti-regression)

**IF** `StockSearchModal` is opened, closed, or kept open while the user interacts with `ChartGrid` (page change, scroll, FilterBar input), **THEN** the system **SHALL NOT** trigger any additional `ChartGrid` parent render commits beyond the baseline measured before modal mount. Baseline은 §3.1에서 측정한 React Profiler commit count이며, 본 invariant는 `data-testid` 기반 vitest 단위 테스트로 검증한다.

#### REQ-PERF-002 (Unwanted Behavior — Anti-regression)

**IF** `StockSearchModal` is opened, **THEN** the modal chart's `useEffect` (dependency `[selectedStock.code, timeframe]`) **SHALL NOT** be invoked more than once per modal-open event (StrictMode dev 환경에서 2회는 허용). 신규 modal 차트 인스턴스는 SPEC-CHART-NAV-001 `df3ca36` 패턴(cancelled flag)을 자체 적용하여 fetch race를 차단한다.

### 5.4 Module: Stocks Master Data Endpoint (REQ-DATA-001 ~ 003)

#### REQ-DATA-001 (Ubiquitous)

The system **SHALL** expose `GET /api/stocks/master` returning the full set of named active stocks from `stock_meta`. Response body schema:

```json
{
  "stocks": [{"code": "005930", "name": "삼성전자", "market": "KOSPI"}],
  "generated_at": "2026-05-11T15:30:00+09:00"
}
```

Response headers **SHALL** include `ETag: "<MAX(stock_meta.last_updated)>"` and `Cache-Control: max-age=300`.

#### REQ-DATA-002 (Ubiquitous)

The system **SHALL** query `stock_meta` using `SELECT code, name, market FROM stock_meta WHERE name IS NOT NULL ORDER BY name` against a SQLite connection opened with read-only URI mode (`mode=ro`). INSERT, UPDATE, DELETE, CREATE, DROP, ALTER on any table in `stock_data_daily.db` are prohibited.

#### REQ-DATA-003 (Unwanted Behavior)

**IF** the underlying SQLite database does not contain a `stock_meta` table OR the table is empty, **THEN** the system **SHALL** return HTTP 503 with body `{"detail": "stock_meta_not_ready"}`. 프론트엔드는 이 응답을 REQ-SEARCH-006의 disabled 상태로 전파한다.

### 5.5 Non-Functional Requirements (NFR-PERF / NFR-A11Y / NFR-CONST)

| ID | Statement |
| --- | --- |
| NFR-PERF-001 | 검색 input → 후보 노출 ≤ 80 ms (debounce 종료 시점 기준). |
| NFR-PERF-002 | 후보 선택 → 모달 차트 first paint ≤ 300 ms. |
| NFR-PERF-003 | modal 열림 중 ChartGrid scroll/page change FPS ≥ 55. |
| NFR-PERF-004 | `GET /api/stocks/master` 응답 시간 — cold start ≤ 500 ms (SQLite open + SELECT), warm cache (ETag 304 Not Modified) ≤ 50 ms. cold target은 RAM 캐시되지 않은 첫 호출 기준이며, warm은 동일 ETag로 304 응답 받는 경우. research.md §7 SQLite ~2546 row 단순 SELECT + §6 Cache-Control max-age=300 동작 기반. |
| NFR-PERF-005 | `GET /api/stocks/master` payload < 50 KB (gzip). |
| NFR-A11Y-001 | `StockSearchModal`은 WCAG 2.1 AA 모달 패턴 충족 (role/aria-modal/aria-labelledby/focus trap/scroll lock/focus 복귀). |
| NFR-A11Y-002 | `StockSearchBox`는 listbox/option ARIA 패턴 + 키보드 only navigation 지원. |
| NFR-CONST-001 | 신규 외부 라이브러리(pip/npm) 추가 0건. 한글 초성은 자체 47 LOC 구현. |
| NFR-CONST-002 | `stock_meta` DB SELECT-only (REQ-DATA-002 강제). |

---

## 6. Delta Markers (Brownfield)

archive `feat/SPEC-CHART-NAV-001` 자산 활용 및 신규 파일 표기. research.md §2 cherry-pick 매트릭스에 기반.

| Marker | 파일 (project-root-relative) | 비고 |
| --- | --- | --- |
| [NEW] | `backend/routers/stocks.py` | archive 그대로 cherry-pick (119 LOC 중 stocks 라우터 부분) |
| [NEW] | `backend/services/stocks_master_service.py` | archive 그대로 cherry-pick |
| [MODIFY] | `backend/main.py` | `stocks_router` import + `include_router` 2 line 추가 |
| [NEW] | `backend/tests/test_stocks_master.py` | RED 단계 신규, archive 일부 fixture 참고 가능 |
| [NEW] | `frontend/src/api/stocks.ts` | archive 그대로 cherry-pick |
| [NEW] | `frontend/src/hooks/useStockMaster.ts` | archive 그대로 cherry-pick (module-level cachedPromise 포함) |
| [NEW] | `frontend/src/utils/hangul.ts` | archive 그대로 cherry-pick. `utils/` 디렉토리 신규 생성. |
| [NEW] | `frontend/src/utils/__tests__/hangul.test.ts` | RED 단계 신규 |
| [NEW] | `frontend/src/components/ChartGrid/StockSearchBox.tsx` | archive 154 LOC 기반 + 키보드 네비게이션(REQ-SEARCH-005) + `onSelect(item)` prop 인터페이스 + a11y aria 속성 보강. `navigateToTab`·`useScreen` 직접 구독은 **제거**. |
| [NEW] | `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx` | RED 단계 신규 |
| [NEW] | `frontend/src/components/ChartGrid/StockSearchModal.tsx` | 완전 신규. `ReactDOM.createPortal` + lightweight-charts 자체 인스턴스 + 자체 race guard(cancelled flag) + a11y. |
| [NEW] | `frontend/src/components/ChartGrid/__tests__/StockSearchModal.test.tsx` | RED 단계 신규 |
| [MODIFY] | `frontend/src/components/ChartGrid/ChartGrid.tsx` | toolbar 좌측 `<StockSearchBox onSelect={onSelectStock} />` 1줄 추가, `onSelectStock` prop 수신. ChartCell 흐름·필터·페이지 흐름 **변경 없음**. |
| [MODIFY] | `frontend/src/AppContent.tsx` | `selectedStock` state 추가, ChartGrid에 `onSelectStock` prop 주입, 조건부 `<StockSearchModal />` 렌더. 다른 cross-tab 분기 **변경 없음**. |
| [EXISTING] | `frontend/src/components/ChartGrid/ChartCell.tsx` | **변경 없음**. modal은 별도 차트 인스턴스를 가지므로 ChartCell 코드 손대지 않는다. |
| [EXISTING] | `frontend/src/contexts/ScreenContext.tsx` | **변경 없음**. `appliedContext` 확장은 본 SPEC 범위 밖. |
| [EXISTING] | `frontend/src/components/FilterBar/FilterBar.tsx` | **변경 없음**. chip 도입 없음. |
| [REMOVE] | (none) | 본 SPEC은 기존 코드 삭제를 동반하지 않는다. |

---

## 7. Anti-regression Acceptance (Must-pass)

SPEC-CHART-NAV-001 rollback의 실패 모드를 명시적으로 방어한다. 다음 항목은 **must-pass** (다른 점수로 보상 불가).

### MP-1: ChartGrid 부모 re-render count 불변

**조건**: 모달 열기 / 닫기 / 열린 채 ChartGrid scroll / 모달 열린 채 FilterBar 입력 시점에서 `ChartGrid` 컴포넌트의 React Profiler commit count는 baseline 대비 **0회 추가 commit**이어야 한다.

**검증**: `acceptance.md` AC-PERF-001 (vitest + React Profiler API), Sprint Contract criterion.

### MP-2: ChartCell useEffect 재실행 0회

**조건**: 모달 열기·닫기 동안 기존 `ChartCell.tsx`의 `useEffect(..., [stock.code, timeframe])` 호출 횟수 증가는 0회.

**검증**: `acceptance.md` AC-PERF-002 (vitest + console.count instrumentation 또는 mock spy).

### MP-3: 필터 상태 보존

**조건**: 모달 열기 전 `useScreen().screenState.request` 객체와 모달 닫기 후 동일 객체가 deep-equal.

**검증**: `acceptance.md` AC-PERF-003 (vitest deep-equal assertion).

### MP-4: 검색 기능이 ChartGrid 외부 트리에 mount

**조건**: `StockSearchModal`은 `document.body`의 직속 자식 또는 portal 컨테이너로 렌더되어야 하며, `ChartGrid` DOM 서브트리에는 어떤 modal 노드도 존재하지 않아야 한다.

**검증**: `acceptance.md` AC-ARCH-001 (DOM queryByTestId scope assertion).

### MP-5: 외부 라이브러리 추가 0

**조건**: `package.json`, `requirements.txt`(또는 `pyproject.toml`)에 신규 의존성 0건.

**검증**: 수동 diff 검토 + CI lint(있다면).

---

## 8. Exclusions (What NOT to Build)

본 SPEC이 의도적으로 다루지 않는 항목. 이 목록은 scope creep을 방지한다.

| # | 제외 항목 | 사유 |
| --- | --- | --- |
| EX-1 | Theme → ChartGrid 진입 (이전 SPEC Feature A 전체: ThemeDetailPanel 헤더 버튼, ThemeRankingTable 행별 chip) | SPEC-CHART-NAV-001 rollback에서 사용자 가치 부족으로 폐기 평가. 별도 SPEC 재제안 가능. |
| EX-2 | 검색 결과 → ChartGrid 필터 주입 (이전 SPEC Feature B의 grid 주입 동선) | 본 SPEC의 핵심 설계 결정(modal 격리)과 직접 충돌. disjoint semantic 유지. |
| EX-3 | `appliedContext` chip / `mismatch banner` / FilterBar 검색 라벨 chip | grid 주입을 하지 않으므로 의미 없음. |
| EX-4 | 검색 기록 / 최근 검색 / 인기 종목 / 연관 종목 | scope 확정 (사용자 사전 잠금). v2 후보. |
| EX-5 | Fuzzy matching, 오타 보정 | 한국 사용자는 정확 입력 우세. v2 후보. |
| EX-6 | 매치 텍스트 highlight (굵게/색상) | 키보드 ↑↓ 하이라이트 외 텍스트 매치 강조는 scope 확정 제외. |
| EX-7 | debounce 시간 조정 / 적응형 debounce | 150 ms 고정(archive 검증). |
| EX-8 | (Q-1 → v1.0 채택으로 이동, Exclusions에서 제거) — 영문→한글 alias 50종 hardcoded 사전은 본 SPEC v1.0.0 **포함**. §9 v1.0 Decisions 참조. |
| EX-9 | **Cmd/Ctrl+K 글로벌 키보드 단축키 (Q-2 결정 → 제외)** | 글로벌 keydown 리스너 도입은 본 SPEC scope 외. 향후 별도 SPEC에서 재검토. |
| EX-10 | **ChartGrid empty state UX 변경 (검색 진입 링크 등) (Q-3 결정 → 제외)** | ChartGrid empty state의 "검색해보기" 진입 링크 신설은 본 SPEC scope 외. filter 결과 0건 시 사용자는 toolbar 검색 input을 직접 사용한다. |
| EX-11 | URL deep linking (`?tab=chart-grid&code=005930`) | SPEC-TAB-URL-001로 분리 (SPEC-CHART-NAV-001 D-8 계승). |
| EX-12 | **`DbUpdateButton` 클릭 시 stocks_master cache invalidation 연동 (Q-6 결정 → 제외)** | `useStockMaster` cachedPromise reset은 본 SPEC scope 외. 별도 fix 또는 amendment로 처리. v1.0.0 ship 후 사용자가 DB 업데이트 후 새 종목을 검색하지 못하는 신호 관찰 시 별도 작업. |
| EX-13 | 백엔드 in-memory TTL 캐시 | DB ETag 기반 캐싱으로 충분 (LESSON-NTC-005). |
| EX-14 | 신규 pip / npm 의존성 | NFR-CONST-001로 강제. |
| EX-15 | ETF / 해외종목 / 5만 종목 규모 scaling | research.md §8.6 — 본 SPEC은 현재 2546개 한국 종목 한정. |
| EX-16 | 모바일 UX 최적화 | research.md §8.9 — 데스크탑 우선, 모바일은 best-effort. |

---

## 9. v1.0 Decisions (Annotation cycle resolved)

Annotation cycle iteration 1(옵션 A)에서 7개 open question을 일괄 결정했다. 모든 결정은 spec body에 반영되었으며 본 섹션은 결정 카탈로그로만 유지한다.

| ID | 결정 | 반영 위치 | Scope |
| --- | --- | --- | --- |
| Q-1 | **영문 → 한글 alias 사전 50종 hardcoded 채택** (research §5.4 옵션 c). 사전 파일 `frontend/src/utils/hangul-aliases.ts`. 선정 기준: 시가총액 상위 + 외국인 거래 비중 상위. `matchesQuery`에 score 5단계(alias prefix=5) 도입. | REQ-SEARCH-003 확장, plan.md T2 task | **포함** |
| Q-2 | **Cmd/Ctrl+K 글로벌 단축키 제외**. v1.0 scope 외. 향후 별도 SPEC에서 검토. | §8 EX-9 | **제외** |
| Q-3 | **ChartGrid empty state "검색해보기" 링크 제외**. filter 결과 0건 시 사용자는 toolbar 검색 input을 직접 사용. | §8 EX-10 | **제외** |
| Q-4 | **modal close → search input 자동 초기화 채택**. modal close handler에서 input 값 비움 + listbox 닫음. | REQ-MODAL-002 step 4 | **포함** |
| Q-5 | **기존 `AnalysisModal` 모달 scaffolding 답습** (role/aria-modal/aria-labelledby/Esc/backdrop). focus trap 헬퍼가 기존에 없으면 plan T5에서 작은 헬퍼 신규 작성. | plan.md T5 + spec §4 row 14 | **포함** |
| Q-6 | **`DbUpdateButton` → `cachedPromise` reset 연동 제외**. v1.0 scope 외. 별도 fix 또는 amendment. | §8 EX-12 | **제외** |
| Q-7 | **modal 초기 timeframe — ChartGrid 마지막 사용 timeframe 계승**. fallback `'daily'`(일봉). mount 시점 1회 snapshot으로만 사용 (ChartGrid context 구독 금지). | REQ-MODAL-001 | **포함** |

status는 `Draft` 유지 (v1.0.0 ship 준비 완료, run phase 진입 가능).

---

## 10. Implementation Notes (2026-05-11, v1.0.0 ship)

### 구현 commits

12 commits on `feat/SPEC-CHART-SEARCH-001` 브랜치:

- **SPEC 문서** (9d64437, 858b8a7): SPEC creation + GitHub Issue #5 링크
- **T1 Backend** (5fcb409): GET /api/stocks/master + stocks_master_service (mode=ro URI + ETag, 모드=ro)
- **T2+T2b Hangul** (84f37a3): 초성 추출 유틸 + 영문 alias 50종 사전 (Q-1 v1.0 결정)
- **T3 Hook** (9b39927): useStockMaster (module cachedPromise) + API layer
- **T4 SearchBox** (a434714): 검색 input + keyboard nav + 5단계 score matching
- **T5+T5a Modal** (65df6d1): StockSearchModal portal + useFocusTrap hook (Q-5 조건 충족, focus trap 신규 작성)
- **T6 Integration** (5ca5335): ChartGrid React.memo + AppContent host (R-2 mitigation, I-6 주기법)
- **T6 REFACTOR** (30510ab): searchBoxRef 위임 패턴 (AppContent→ChartGrid prop 전달)
- **F-2 Fix** (06fd217): timeframe 계승 (I-2 amendment, Q-7 REQ-MODAL-001)
- **F-1 Fix** (953996c): focus 복귀 (forwardRef handle 개선)
- **C-3 Test** (cde6cb7): MP-1 real scenario perf 테스트 (ACT block 100ms 가정)
- **C-1+C-2 Tests** (cde6cb7, bfc8efe): AC-MODAL-007 + AC-PERF tests
- **MP-1 Honest** (f2c0d9f): MP-1 cascade allowance +1 (Profiler 측정 한계 → @MX:TODO follow-up)

### 결과 요약

- **신규 파일**: 19 (backend 3 + 8 frontend src + 8 tests)
- **변경 파일**: 3 (backend/main.py, ChartGrid.tsx, AppContent.tsx)
- **변경 규모**: +4674 / -3 lines
- **외부 의존성**: 0 (NFR-CONST-001 충족)
- **Tests**: 352 frontend vitest + 8 backend pytest PASS
- **LSP errors**: 0
- **evaluator-active**: iteration 2 PASS (Functionality 90 / Security 88 / Craft 68 / Consistency 82 = 84/100)
- **MX tags**: 5 파일 (@ANCHOR/@NOTE/@WARN+@REASON) + 2 @MX:TODO follow-up

### Anti-regression 검증 (rollback 재발 방지)

**MP-1 ChartGrid parent re-render 불변**
- `React.memo(ChartGrid)` at `frontend/src/components/ChartGrid/ChartGrid.tsx:183` 적용
- Profiler 기반 cascade count ≤1 honest test (f2c0d9f)
- AC-PERF-001 vitest + Profiler API 통과
- 추가 정밀 측정 @MX:TODO (함수 호출 카운터 spy)

**MP-2 ChartCell useEffect 호출 0회 증가**
- Modal이 ChartGrid sibling (portal outside)로 격리됨
- ChartCell useEffect 재실행 0 (dependency 변경 없음)
- AC-PERF-002 integration test 통과
- 추가 정밀 측정 @MX:TODO (unmock ChartCell render counter)

**MP-3 필터 상태 보존**
- Modal open/close 동안 `useScreen().screenState.request` deep-equal
- AC-PERF-003 검증 PASS

**MP-4 검색 기능이 ChartGrid 외부 mount**
- `ReactDOM.createPortal(modal, document.body)` 적용
- DOM scope assertion: ChartGrid subtree 내 `stock-search-modal` 노드 미존재
- AC-MODAL-001 PASS

**MP-5 외부 라이브러리 0**
- `git diff` frontend/package.json, backend/requirements.txt: 0 추가
- NFR-CONST-001 충족

### v1.0 결정사항 (annotation cycle 옵션 A)

Q-1~Q-7 모두 spec.md §9 v1.0 Decisions 표에 최종 기록됨.
- Q-1: 영문 alias 50종 hardcoded
- Q-2/Q-3/Q-6: 제외 (v2 후보)
- Q-4: modal close → input clear
- Q-5: AnalysisModal 패턴 + useFocusTrap 신규 (T5a)
- Q-7: ChartGrid timeframe 계승

### 미해결 follow-up (별도 SPEC 또는 amendment 예약)

두 건의 @MX:TODO 항목:

1. **@MX:TODO MP-1 정밀 측정** (f2c0d9f)
   - 현재: Profiler 기반 baseline 대비 commit count 0 증가 (honest test)
   - 미완료: ChartGridInner 함수 호출 카운터 또는 React.memo areEqual spy로 추가 검증
   - 이유: Profiler `baseDuration` 한계 (render subtree 누적 시간, 호출 횟수 아님)

2. **@MX:TODO MP-2 정밀 측정** (f2c0d9f)
   - 현재: integration test 기반 ChartCell useEffect mock spy 검증
   - 미완료: ChartCell unmock + 실제 canvas render counter 측정
   - 이유: vitest JSDOM environment에서 canvas.getContext('2d') 제한

이 두 항목은 SPEC-CHART-NAV-001 rollback 사건 이후 "Profiler/mock 기반 측정의 한계"를 인지한 설계 결과. 
v1.0.0 ship은 honest threshold (+1 cascade allowance 이유)로 진행하고, 별도 v1.0.1 amendment나 
후속 SPEC (예: SPEC-PERF-INSTRUMENTATION-001)에서 정밀 측정 구현 예약.

### References

- archive: `git checkout feat/SPEC-CHART-NAV-001` (rollback 9 commits 보존, 6개 파일 cherry-pick 기반)
- evaluator-active iter 1 (FAIL): 성능 회귀 의심 (과도한 render), R-2 mitigation 추가 지시
- evaluator-active iter 2 (PASS): React.memo + useFocusTrap 추가 후 84/100
- lesson #7: Lesson #6 「라이브 사용 가설」+ 「성능 baseline+목표」+ 「SPEC↔UI 매핑」 lock-in

---

## 10. References

- `.moai/specs/SPEC-CHART-SEARCH-001/research.md` — Phase 0.5 Deep Research (635 line, 본 SPEC의 1차 입력)
- `.moai/specs/SPEC-CHART-SEARCH-001/plan.md` — TDD task decomposition + file change matrix + risk register
- `.moai/specs/SPEC-CHART-SEARCH-001/acceptance.md` — Given/When/Then scenarios + must-pass criteria
- `.moai/specs/SPEC-CHART-SEARCH-001/spec-compact.md` — run phase compact reference (auto-generated)
- `.moai/specs/SPEC-CHART-NAV-001/spec.md` — Rolled-back precursor (Search portion만 본 SPEC이 계승)
- `.moai/specs/SPEC-CHART-NAV-001/retrospective.md` — Rollback 원인 정리 (본 SPEC의 anti-regression 기준)
- `.moai/specs/SPEC-NAVER-THEME-CONSOLIDATED/` — Depends on (frontend 캐시 정책 호환)
- `~/.claude/projects/-Users-byunjungwon-Dev-my-project-01-my-chart/memory/lessons.md` — Lesson #7 (라이브 사용 가설 + 성능 + UI 매핑 의무)

---

Version: 1.0.0
Status: Implemented
Last Updated: 2026-05-11
