# SPEC-CHART-SEARCH-001 — Phase 0.5 Deep Research

문서 분류: Research (Phase 0.5)
작성일: 2026-05-11
브랜치: `chore/integrated-main-merge-2026-04-25` (clean)
참조 archive: `feat/SPEC-CHART-NAV-001` (9 commits, HEAD `df3ca36`, 폐기 보존)

---

## 1. Executive Summary

본 SPEC은 ChartGrid 화면에 **종목 검색 기능**을 추가한다. 핵심 설계 결정:

1. **검색 결과 표시는 ChartGrid 외부 모달**(React Portal → `document.body`)로 격리한다. ChartGrid 부모 리렌더로 인한 ChartCell useEffect 중복 실행(SPEC-CHART-NAV-001 롤백의 근본 원인)을 React 트리 분리로 원천 차단한다.
2. **백엔드 `GET /api/stocks/master`**는 archive에서 그대로 cherry-pick 가능하다(약 119 LOC, 의존성 0). ETag + Cache-Control(max-age=300) + 503 미준비 처리까지 검증 완료.
3. **한글 초성/영문 검색**은 archive `frontend/src/utils/hangul.ts`(47 LOC, 외부 라이브러리 0)를 그대로 채택한다. 4단계 score(코드 prefix=4, 이름 prefix=3, 이름 부분일치=2, 초성=1) 기준 충분히 검증된 알고리즘.
4. **2544개 종목**(현재 `stock_meta`)에서 클라이언트 1회 fetch 후 메모리 필터링이 latency·복잡도 균형 최적. 추정 페이로드 약 110~140 KB(gzip 후 30~40 KB), 입력당 매칭 비용 < 5 ms.
5. archive에서 cherry-pick 대상은 **6개 파일**(backend 2 + frontend 4), 신규 작성 대상은 **1개 파일**(`StockSearchModal.tsx` 모달 + 결과 차트 인스턴스). 테마→그리드(REQ-CN-005~006), appliedContext chip(REQ-CN-014~015) 등 grid 통합 자산은 본 SPEC 범위 밖이므로 **제외**.

Lesson #7 의무 준수: 라이브 사용 가설(§9), 성능 baseline·목표(§10), SPEC↔UI 매핑(§11) 모두 본 문서에 포함되었다.

---

## 2. Archive Cherry-pick Plan

### 2.1 archive 커밋·파일 인벤토리

archive `feat/SPEC-CHART-NAV-001` 9 커밋 중 본 SPEC에 관련된 작업 단위는 5개:

| 커밋 | 영역 | 본 SPEC 관련성 |
|---|---|---|
| `9be9767` (T1 backend) | `backend/routers/stocks.py` (+52), `backend/services/stocks_master_service.py` (+65), `backend/main.py` (+2) | **그대로 채택** |
| `1e20dd8` (T3+T4 frontend infra) | `frontend/src/api/stocks.ts` (+25), `frontend/src/hooks/useStockMaster.ts` (+42), `frontend/src/utils/hangul.ts` (+47), `frontend/src/types/market.ts` (+2), `frontend/src/contexts/ScreenContext.tsx` (+22), `frontend/src/AppContent.tsx` (+11) | **부분 채택** — api/hooks/hangul만 채택, ScreenContext.appliedContext와 AppContent의 cross-tab 분기는 **제외**(grid 통합 자산) |
| `2a0c4b7` (T5 UX) | `StockSearchBox.tsx` (+154), `ChartGrid.tsx` (+41), `ThemeDetailPanel.tsx` (+36), `ThemeRankingTable.tsx` (+42), `ThemeAnalysis.tsx` (+1), `FilterBar.tsx` (+31) | **재설계** — StockSearchBox 로직 90%는 재사용하되 선택 핸들러를 `navigateToTab(...)` → `openSearchModal(stock)`로 변경, 테마/필터 chip 코드는 **전부 제외** |
| `91fd63b` (FilterBar chip layout fix) | `FilterBar.tsx` (+28/-27) | **제외** — appliedContext chip 자체를 도입하지 않으므로 무관 |
| `df3ca36` (ChartCell race guard) | `ChartCell.tsx` (+6) | **참고만** — 본 SPEC은 ChartCell을 건드리지 않고 모달 차트를 별도 인스턴스로 만든다. 단, 모달 차트 인스턴스에도 동일한 cancelled flag 패턴을 적용한다(아래 §4 참조). |

### 2.2 cherry-pick 대상 파일별 상세

**즉시 채택 가능 (변경 불필요):**

1. `backend/routers/stocks.py` — `feat/SPEC-CHART-NAV-001:backend/routers/stocks.py` 그대로. 공개 export: `stocks_router` (APIRouter, prefix `/api/stocks`), `StockMasterItem`/`StockMasterResponse` (pydantic). 의존성: `backend.deps.DAILY_DB_PATH` (chore branch에 존재, `backend/deps.py:10`), `stocks_master_service.list_stock_master`.
2. `backend/services/stocks_master_service.py` — `feat/SPEC-CHART-NAV-001:backend/services/stocks_master_service.py` 그대로. 공개 export: `list_stock_master(daily_db_path) -> (list[dict], str|None)`. `mode=ro` URI로 SELECT-only(C-005 SQL 안전 invariant). 의존성: `sqlite3` 표준.
3. `backend/main.py` — import + `app.include_router(stocks_router)` 2 line 추가만.
4. `frontend/src/api/stocks.ts` — `feat/SPEC-CHART-NAV-001:frontend/src/api/stocks.ts` 그대로. 공개 export: `StockMasterItem`, `StockMasterResponse`, `fetchStockMaster()`. 503 → `Error('stock_meta_not_ready')` rethrow.
5. `frontend/src/hooks/useStockMaster.ts` — `feat/SPEC-CHART-NAV-001:frontend/src/hooks/useStockMaster.ts` 그대로. 공개 export: `useStockMaster(): {data, loading, error, dispatched}`. 모듈 레벨 `cachedPromise`로 컴포넌트 재마운트 시에도 1회 fetch 보장(REQ-CN-010 호환).
6. `frontend/src/utils/hangul.ts` — `feat/SPEC-CHART-NAV-001:frontend/src/utils/hangul.ts` 그대로. 공개 export: `extractInitialConsonants(s)`, `matchesQuery(item, q)`. 외부 라이브러리 0(C-003 호환).

   > **참고**: chore 브랜치에 `frontend/src/utils/` 디렉토리 자체가 없다. 신규 생성 필요.

**부분 채택 (변경 필요):**

7. `frontend/src/components/ChartGrid/StockSearchBox.tsx` — archive 버전 154 LOC 기준, 변경 범위:
   - 유지: input 컨트롤, debounce 150 ms, MAX_RESULTS=8, 503 disabled+placeholder, 외부 클릭 닫기 useEffect, 드롭다운 list/option 마크업, ARIA 속성.
   - **변경**: `handleSelect` 안의 `navigateToTab('chart-grid', { stockCodes: [item.code], searchLabel: ... })` 호출을 제거하고 신규 `onSelect(item: StockMasterItem)` prop을 받아 부모(ChartGrid 또는 SearchModal 호스트)에 위임한다.
   - **변경**: `useTab` import 제거.
   - **변경**: `data-testid="stock-search-box"`는 유지.
   - **신규**: 키보드 네비게이션(ArrowDown/ArrowUp/Enter/Escape)을 추가한다(archive에는 마우스 전용). a11y 요건(§6).

**완전 제외 (본 SPEC 범위 밖):**

- `frontend/src/contexts/ScreenContext.tsx`의 `AppliedContext` 타입·`setAppliedContext`·`clearAppliedContext` (검색 결과를 grid에 주입하지 않으므로 불필요)
- `frontend/src/AppContent.tsx`의 cross-tab `appliedContext` 분기 useEffect
- `frontend/src/components/ChartGrid/ChartGrid.tsx`의 `mismatch banner`(REQ-CN-014)
- `frontend/src/components/FilterBar/FilterBar.tsx`의 chip + clearAppliedContext UI(REQ-CN-015)
- `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` "차트 그리드로 보기" 버튼(REQ-CN-005)
- `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` "차트" chip(REQ-CN-006)
- `frontend/src/types/market.ts`의 `themeName`/`searchLabel` CrossTabParams 확장

### 2.3 cherry-pick 절차 권장

archive 커밋을 `git cherry-pick` 으로 가져오기보다 **파일 단위 `git show feat/SPEC-CHART-NAV-001:<path> > <path>`** 방식이 안전하다. 이유:
- archive 한 커밋(예: `2a0c4b7`)이 grid 통합 코드(제외 대상)와 검색 박스 코드(채택 대상)를 함께 변경한 monolithic 커밋이라 cherry-pick conflict 발생 확률 높음.
- 6개 파일 분리 적용 후 RED·GREEN 분할 커밋을 새로 만들면 SPEC 추적성도 명확해진다.

---

## 3. Current State Audit

### 3.1 ChartGrid 구조 (chore branch)

- `frontend/src/components/ChartGrid/ChartGrid.tsx:14` — 함수형 컴포넌트.
- `frontend/src/components/ChartGrid/ChartGrid.tsx:15` — `useScreen()` 으로 `results`, `applyFilters` 구독.
- `frontend/src/components/ChartGrid/ChartGrid.tsx:38-43` — `crossTabParams.stockCodes` 수신 시 `applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes })` 트리거. (검색을 grid에 주입하려면 이 분기가 필요했지만, 본 SPEC은 modal 격리이므로 **사용하지 않음**.)
- `frontend/src/components/ChartGrid/ChartGrid.tsx:46-49` — `flatStocks`는 매 렌더 새 배열 reference. key는 `${stock.code}-${currentPage}` (line 129)로 안정.
- `frontend/src/components/ChartGrid/ChartGrid.tsx:128-134` — `<ChartCell key={...} stock={stock} timeframe={timeframe} ... />` 4~9개 마운트.
- `frontend/src/components/ChartGrid/ChartCell.tsx:114-266` — 거대한 useEffect (dep array `[stock.code, timeframe]`) — 여기서 `createChart`, `fetchChartData`, `setData` 모두 실행.

### 3.2 통합 진입점 분석 — 검색 트리거를 어디에 둘 것인가?

3개 후보, 각각 trade-off:

| 후보 | 위치 | 장점 | 단점 |
|---|---|---|---|
| (A) **ChartGrid toolbar 좌측 inline** | `ChartGrid.tsx:93-116` toolbar 좌측 | grid 화면에 자연스럽게 노출. archive와 유사 위치 | toolbar는 grid 헤더 안 → ChartGrid 재렌더 시 검색 박스도 같이 재렌더(state는 useState로 보존되지만 마운트 비용 발생 가능). 검색 박스 자체는 가벼우므로 영향 미미. |
| (B) **FilterBar 우측** | `FilterBar.tsx:142` DbUpdateButton 옆 | FilterBar는 이미 가로 flex 라인. 시각 통합도 ↑ | FilterBar는 ChartGrid 탭 전용 영역 위에 있어 다른 탭에서는 숨김. 동일. |
| (C) **TabNavigation/ContextBar (헤더)** | `AppContent.tsx` 상단 헤더 | 어느 탭에서든 검색 가능 | 본 SPEC은 ChartGrid 화면 한정 기능이므로 scope 위반. |

권장: **(A) ChartGrid toolbar 좌측**. archive와 동일 위치이며 SPEC 의도("ChartGrid 화면 + 모달")에 자연스럽다. (B)도 무방하나 FilterBar에 추가 위젯이 늘면 prim/secondary 액션 구분이 흐려진다.

### 3.3 모달 인프라 — 이미 존재

chore 브랜치에는 React Portal 기반 모달 **이미 2개**가 동작 중:
- `frontend/src/components/AnalysisModal.tsx:810` — `return ReactDOM.createPortal(modal, document.body)`. 헤더 + Esc 핸들러(`AnalysisModal.tsx:738`) + `role="dialog"` + `aria-modal="true"`(line 757-758) 패턴 검증 완료.
- `frontend/src/components/AiReportModal.tsx:340` — 동일 패턴.

새 `StockSearchModal.tsx`는 이 두 모달의 마크업·a11y 패턴을 그대로 모사하면 코드 중복 없이 빠르게 구현 가능. 공통 컴포넌트 추출은 본 SPEC 범위 밖(refactor 별도 SPEC 권장).

### 3.4 chore branch clean 확인

- `frontend/src/components/ChartGrid/` 디렉토리에 `StockSearchBox.tsx` 없음. (`ChartCell.tsx`, `ChartGrid.tsx`, `ChartPagination.tsx`, `PriceRangeOverlay.tsx`, `__tests__/` 만 존재)
- `frontend/src/api/stocks.ts` 없음.
- `frontend/src/hooks/useStockMaster.ts` 없음.
- `frontend/src/utils/` 디렉토리 자체 없음.
- `backend/routers/stocks.py` 없음.
- `backend/services/stocks_master_service.py` 없음.
- `backend/routers/` 에 `ai_report.py`, `analysis.py`, `chart.py`, `db.py`, `market.py`, `screen.py`, `sectors.py`, `stage.py`, `themes.py` 9개만 존재.

추가 확인: chore branch `frontend/src/components/FilterBar/FilterBar.tsx` 에는 `appliedContext` chip 없음(`FilterBar.tsx:104-144` 전체 검토 — preset chips만 존재). ✓

---

## 4. Performance Root Cause + Modal Isolation Proof

### 4.1 SPEC-CHART-NAV-001 롤백 원인 재구성

archive 커밋 `df3ca36`(2026-05-08)의 commit body에서 직접 인용:

> "backend log 분석 결과 같은 종목이 동일 timeframe으로 빠르게 반복 호출 (예: 005380이 100ms 내 2회). => React StrictMode 또는 부모 frequent re-render로 ChartCell useEffect 가 double-mount. => 첫 cycle cleanup이 chart.remove() 호출 → 진행 중이던 fetchChartData promise는 미abort. => 응답 도착 시 destroyed candleSeries.setData() 호출 → exception → catch가 silently swallow. => chart container는 init됐으나 setData 못 함 → 빈 차트 영원히 유지."

같은 커밋의 후속 메모:

> "별도 issue (후속 SPEC 가능): 같은 종목 5회+ 반복 fetch는 부모 컴포넌트의 frequent re-render가 ChartCell useEffect를 매번 재실행시키는 더 깊은 문제. race guard로 즉시 영향 완화는 됐지만 근본 fix는 ChartGrid 또는 부모의 memoization/key 안정화 필요."

### 4.2 실제 메커니즘 분석

`ChartCell.tsx:266`의 useEffect dependency array는 `[stock.code, timeframe]` — **둘 다 primitive**. 정상이면 동일 stock·timeframe에서는 effect가 1회만 실행되어야 한다. 그러나 실측 5+회 재실행이 관찰되었다. 가능한 트리거:

1. **React StrictMode 이중 마운트** — dev에서만, prod 영향 0이지만 race 노출.
2. **`stock.code` 자체가 바뀌는 경우** — `ChartGrid.tsx:46-49`에서 매 렌더 새 `flatStocks` 배열이 생성되지만 key가 `${stock.code}-${currentPage}` 안정 → 같은 셀의 stock.code는 동일 → 해당 셀 effect는 재실행 안 됨. ❌ (이건 트리거 아님)
3. **다른 useEffect 분기와의 인터리브** — `ChartCell.tsx:269-273` (showRsLine useEffect)는 별도이므로 무관.
4. **부모의 빠른 state 토글** — 사용자가 page 빠르게 이동, 또는 FilterBar에서 검색 박스 키 입력당 `useScreen.results` 흔들림(but FilterBar는 form submit 시에만 applyFilters 호출이라 키 입력만으로는 results 안 바뀜).
5. **archive 도입 코드가 `useScreen.setAppliedContext` 등 새 dispatch를 추가** — `AppContent.tsx:23` 의 useEffect dep가 `crossTabParams`이며 `crossTabParams`는 검색 선택 시 setting되고 ChartGrid useEffect(`ChartGrid.tsx:38-43`)에서 clear되며 동시에 `applyFilters` 호출 → results 변경 → ChartGrid 재렌더 → cells flatStocks 재생성. 이 사이클 중 useEffect dep는 primitive지만, StrictMode + cleanup 비동기 + setState batching 미흡이 race를 만들었을 가능성 높음.

### 4.3 모달 격리가 race를 차단하는 증명

**핵심 가설**: 검색된 종목의 차트를 `document.body` 포털로 마운트하면 ChartGrid 부모 트리의 어떤 state·context 변화도 modal subtree로 전파되지 않는다.

**React 렌더링 모델 검증**:

1. `ReactDOM.createPortal(modal, document.body)` — DOM 트리는 분리되지만 React 가상 트리는 **호출자 컴포넌트의 자식**이다. 즉, 부모가 리렌더되면 portal 내부도 리렌더 trigger됨.
2. 그러나 React.memo / 안정적 props로 **portal 호스트 컴포넌트** 자체를 ChartGrid 외부(예: `AppContent`)에 두면 ChartGrid 부모 리렌더 영향 0.
3. 본 SPEC 권장 구조:

```
AppContent (호스트)
├── ChartGrid (검색 박스만 toolbar에 마운트, 선택 시 콜백으로 selectedStock 상태 AppContent로 끌어올림)
└── StockSearchModal (selectedStock 있을 때만 마운트, ReactDOM.createPortal로 document.body 렌더)
```

**증명 단계**:
- ChartGrid는 `selectedStock` state를 보유하지 않는다. ChartGrid 내부 state(currentPage, gridSize, timeframe) 변경은 modal에 전파되지 않는다(React 트리상 sibling).
- modal의 차트 셀은 자체 useEffect dep array `[selectedStock.code, timeframe]` 으로 1회만 마운트. selectedStock이 닫힐 때만 cleanup.
- `useScreen.results` 변경은 ChartGrid 서브트리만 리렌더한다. AppContent의 selectedStock state는 변하지 않으므로 modal은 리렌더 0.

**잔여 위험**: AppContent 자체가 무언가로 리렌더되면 modal도 리렌더된다. AppContent 리렌더 트리거는:
- `useTab.activeTab` 변경
- `useScreen.applyFilters` 호출 (REQ는 dispatch 안 트리거 — selectedStock 흐름과 무관)
- `setAppliedContext` 호출 — **본 SPEC은 이 흐름 사용 안 함** ✓

따라서 modal 차트 셀의 useEffect 재실행 트리거는 selectedStock 변경 1개뿐 → race 발생 불가능.

### 4.4 modal 차트 셀의 자체 race guard

ChartCell이 아닌 신규 모달 차트 인스턴스에도 `df3ca36` 패턴을 그대로 적용한다:

```typescript
useEffect(() => {
  let cancelled = false
  const chart = createChart(...)
  fetchChartData(stock.code, timeframe).then(data => {
    if (cancelled) return  // skip setData on destroyed chart
    candleSeries.setData(data.candles)
  })
  return () => {
    cancelled = true
    chart.remove()
  }
}, [stock.code, timeframe])
```

이는 방어적 코드이며 modal 컨텍스트에서는 트리거 가능성이 거의 없으나, StrictMode 보호를 위해 포함한다.

### 4.5 memoization 패턴 검토

chore 브랜치 검색 결과 `React.memo`, `useMemo`, `useCallback` 사용처:
- `useCallback`: `ChartCell.tsx` 다수, `ChartGrid.tsx:56` `handlePageChange`. 일반적 패턴.
- `useMemo`: `FilterBar.tsx:40` `activePresetId`. 검색 박스에서도 매 입력당 정렬·필터 결과를 `useMemo` 후보로 검토 가능. archive `StockSearchBox.tsx:23-35` 는 매 debounce tick마다 sort+slice를 setState로 처리. 2544개 입력당 5 ms 미만이라 useMemo 없이도 충분.

---

## 5. Korean Search UX Reference

### 5.1 산업 표준 패턴 (Naver 금융·Toss·KB증권)

웹 리서치 결과, 한국 증권 앱·웹 검색 UX의 공통 요소(2025-2026):

1. **자동완성 prefix 매칭**: 첫 글자부터 일치하는 종목명을 상위 노출. 코드 prefix 일치도 동시 노출(예: "005" → 005380 현대차, 005490 POSCO ...).
2. **초성 검색**: "ㅎㄷㅊ"로 "현대차" 매칭. 사용자가 모바일 자판에서 빠르게 좁힐 때 사용. ([Mienxiu — Korean Query Auto-completion with Elasticsearch](https://mienxiu.com/building-korean-query-autocompletion/) 참조)
3. **영문→한글 매핑**: "samsung" → "삼성전자". 보통 별도 사전 테이블을 운영하거나 alias 컬럼을 둠.
4. **추천어/최근 검색**: 본 SPEC에서는 **제외**(scope 확정).
5. **debounce**: 보통 100~200 ms. archive는 150 ms 채택.
6. **highlight**: 매칭된 부분을 굵게 처리. 본 SPEC에서는 **제외**(scope 확정).

### 5.2 초성 알고리즘 선택

[Choi-Seunghwan/hangul-chosung-search](https://github.com/Choi-Seunghwan/hangul-chosung-search), [ryuken73/node_chosung_search](https://github.com/ryuken73/node_chosung_search), [hwahyeon — Extracting Initial Consonants from Hangul (Medium)](https://medium.com/@hwahyeon.dev/javascript-extracting-initial-consonants-%EC%B4%88%EC%84%B1-from-hangul-the-korean-alphabet-03d23d70b7d8) 모두 동일 산식:

```
syllable code in [0xAC00, 0xD7A3]
choseong_index = (code - 0xAC00) / 588
choseong = INITIAL_CONSONANTS[choseong_index]
```

여기서 `INITIAL_CONSONANTS = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ'` (19자). 588 = 21 (jungseong) × 28 (jongseong).

archive `hangul.ts` 의 구현은 이 표준 산식 그대로이며 외부 라이브러리 0이다. 2544개 종목 × 평균 4 글자 = 약 10000 글자 처리, 키 입력당 약 1~3 ms.

### 5.3 자료구조 선택 — Trie vs naive 배열

- **Trie**: 검색 시간 O(query length). 2544개 항목 × 평균 4글자 = 10000 노드. 메모리 ~200 KB. 빌드 시간 ~10 ms. 대량 prefix 검색에 강점.
- **naive 배열 + filter+sort**: 검색 시간 O(N × query length) = O(2544 × 8) ≈ 20000 비교 / 입력. 측정상 < 5 ms. 메모리 추가 0.

**결정**: naive 배열 채택(archive 선택 그대로). 2544 규모에서는 trie의 latency 이득이 측정 불가능하며, 코드 단순성과 외부 라이브러리 0 제약(C-003)에 부합.

### 5.4 영문→한글 매핑

archive는 영문 매핑을 명시 구현하지 않았다(matchesQuery는 lowercase 비교만). 즉 "samsung" 입력 시 "삼성전자"는 안 잡힌다. 본 SPEC에서 옵션:

| 옵션 | 구현 | 비용 | 결정 |
|---|---|---|---|
| (a) **alias 무시** | 영문 입력 시 영문 종목명만 매칭 | 0 | 사용자가 "삼"이라고 시작해야 함 — 한국 사용자 자연스러움 |
| (b) **백엔드 alias 컬럼 추가** | stock_meta에 `name_en` 컬럼 + 데이터 채우기 | 백엔드 마이그레이션, 데이터 정합성 관리 | 별도 SPEC |
| (c) **프론트 hardcoded 사전** | 50~100 주요 종목만 `samsung→삼성전자` 매핑 | JSON 파일 ~5 KB | **권장** — 주요 종목만 cover, 상세는 manager-spec 결정 |

**권장**: 옵션 (c). 주요 종목 매핑 사전을 `frontend/src/utils/stock-aliases.json` 형태로 유지하고, `matchesQuery`에 추가 score=5 분기(alias prefix 일치)를 도입한다. 정확한 매핑 리스트는 manager-spec 단계에서 확정한다.

### 5.5 Source URLs

- [Mienxiu — Building Korean Query Auto-completion using Elasticsearch](https://mienxiu.com/building-korean-query-autocompletion/)
- [hwahyeon — Extracting Initial Consonants from Hangul (Medium)](https://medium.com/@hwahyeon.dev/javascript-extracting-initial-consonants-%EC%B4%88%EC%84%B1-from-hangul-the-korean-alphabet-03d23d70b7d8)
- [Choi-Seunghwan/hangul-chosung-search GitHub](https://github.com/Choi-Seunghwan/hangul-chosung-search)
- [ryuken73/node_chosung_search GitHub](https://github.com/ryuken73/node_chosung_search)
- [jonghwanhyeon/hangul-jamo GitHub](https://github.com/jonghwanhyeon/hangul-jamo)
- [Wikipedia — Hangul Syllables](https://en.wikipedia.org/wiki/Hangul_Syllables)

---

## 6. Modal Pattern + Accessibility

### 6.1 기존 자산

`AnalysisModal.tsx` (810 LOC)와 `AiReportModal.tsx`(340 LOC) 모두:
- `ReactDOM.createPortal(modal, document.body)`
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby`
- Esc 키 닫기 (`onClose` 핸들러)
- 백드롭 클릭 닫기
- 모달 콘텐츠 컨테이너 `tabIndex={-1}` + 초기 포커스

`AnalysisModal.tsx:757-758` 확인된 마크업:
```tsx
<div className="analysis-modal" role="dialog" aria-modal="true" aria-labelledby="analysis-modal-title">
```

### 6.2 신규 StockSearchModal 권장 패턴

```
StockSearchModal (createPortal → document.body)
├── backdrop (click → close)
└── modal-content (tabIndex={-1}, role="dialog", aria-modal="true", aria-labelledby="search-modal-title")
    ├── header
    │   ├── h2#search-modal-title — "{stock.name} ({stock.code})"
    │   ├── timeframe toggle (D/W)
    │   └── close button (aria-label="닫기")
    └── chart container (lightweight-charts 인스턴스, 자체 fetch + race guard)
```

### 6.3 a11y 체크리스트

- [x] role="dialog" + aria-modal="true" — 배경 inert ([MDN aria-modal](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-modal))
- [x] aria-labelledby로 헤더 연결
- [x] Esc 키 → onClose
- [x] 백드롭 클릭 → onClose
- [x] 모달 열림 시 초기 focus를 close 버튼 또는 modal-content에 설정
- [x] 모달 닫힘 시 trigger 요소(SearchBox input)로 focus 복귀 (`useRef`로 trigger 기억)
- [x] body scroll lock (overflow:hidden) — 기존 모달은 적용 여부 확인 후 일관성 유지
- [x] focus trap — Tab/Shift+Tab을 모달 내부로 제한. AnalysisModal 패턴 확인 필요. archive 패턴이 없다면 manager-spec 단계에서 결정.

검색 박스 자체의 a11y (archive 누락 보완):
- [x] input `aria-label="종목 검색"`, `aria-autocomplete="list"`, `aria-expanded`, `aria-controls="search-listbox"`, `aria-activedescendant`
- [x] listbox `role="listbox"`, option `role="option" aria-selected`
- [x] **신규**: ArrowDown/ArrowUp → 하이라이트 이동, Enter → 선택, Escape → 닫기. archive 누락.

### 6.4 Native `<dialog>` 검토

[UXPin — How to Build Accessible Modals with Focus Traps](https://www.uxpin.com/studio/blog/how-to-build-accessible-modals-with-focus-traps/) 등 2025 가이드는 native `<dialog>` + `.showModal()` 추천(focus trap·top-layer 자동). 그러나 본 프로젝트의 기존 모달 2개는 `createPortal` 패턴. 일관성 유지(refactor 별도 SPEC) 차원에서 본 SPEC도 `createPortal` 채택을 권장한다.

### 6.5 Source URLs

- [UXPin — How to Build Accessible Modals with Focus Traps (2026)](https://www.uxpin.com/studio/blog/how-to-build-accessible-modals-with-focus-traps/)
- [MDN — aria-modal](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Attributes/aria-modal)
- [The A11Y Collective — Mastering Accessible Modals with ARIA](https://www.a11y-collective.com/blog/modal-accessibility/)
- [Nutrient — Building accessible modals in React](https://www.nutrient.io/blog/building-accessible-modals-with-react/)
- [Chris Henrick — Building an Accessible Modal Dialog in React](https://clhenrick.io/blog/react-a11y-modal-dialog/)

---

## 7. stocks_master Backend Design

### 7.1 엔드포인트 사양 (archive 그대로)

- 메서드: `GET /api/stocks/master`
- 응답: `{ stocks: [{ code, name, market }, ...], generated_at: <ISO-8601 KST> }`
- 헤더: `ETag: "<MAX(last_updated)>"`, `Cache-Control: max-age=300`
- 503: `stock_meta` 테이블 부재 또는 빈 결과 → `{ detail: "stock_meta_not_ready" }`
- DB: SQLite `mode=ro` URI로 SELECT-only 강제(C-005)

### 7.2 페이로드 크기 추정

실측: 현재 `stock_meta`에 **2544개 named 종목**(`Output/stock_data_daily.db`).
- 항목당 추정 JSON: `{"code":"005930","name":"삼성전자","market":"KOSPI"}` 약 50~60 bytes
- 2544 × 55 = **약 140 KB raw JSON**
- gzip 후 약 25~35 KB
- ETag로 304 비-수정 캐싱 후 0 KB

자동완성용 단일 fetch로 충분히 작다. 페이지네이션 불필요.

### 7.3 갱신 주기

- `stock_meta`는 KRX 일일 업데이트 시 갱신 (신규 상장/상폐 반영). 보통 영업일 18:00 KST 이후.
- 클라이언트 캐싱: `Cache-Control: max-age=300` (5분). archive는 모듈 레벨 `cachedPromise`로 SPA 세션 1회 fetch. 이중 캐시 안전.
- 사용자가 DB 업데이트를 강제 트리거(DbUpdateButton)하면 `cachedPromise = null` reset이 이상적. archive는 미구현. 본 SPEC에서 결정 필요 — manager-spec 단계.

### 7.4 데이터 소스

- 테이블: `stock_meta(code TEXT, name TEXT, market TEXT, last_updated TEXT, ...)`
- 채우기: KRX 크롤러(`my_chart.config`/data update 워크플로). 본 SPEC scope 밖.
- 503 상황: 새 DB 초기화 직후 first run에서 발생. UI는 "DB 업데이트가 필요합니다" 안내(archive 패턴).

### 7.5 보안 및 데이터 노출

- 응답에는 종목 메타만 포함. 사용자 정보·관심종목 등 PII 없음.
- 인증 없음(현재 API 전체 정책과 일관).
- 1 RPM 미만 요청 빈도. rate-limit 불필요.

---

## 8. Risks, Constraints, Rejected Alternatives (UltraThink 깊이)

### 8.1 Rejected Architecture #1 — 검색을 ChartGrid 안에 inline 렌더

archive 방식. 검색 선택 → `applyFilters({ codes: [code] })` → ChartGrid가 1개 셀로 렌더 → ChartCell useEffect 재실행.

**거부 사유**:
- ChartGrid 재렌더 사이클이 ChartCell mount race를 트리거(§4). race guard로 mitigate해도 근본 원인 미해결.
- 사용자가 검색 결과를 본 후 원래 필터 결과로 돌아가려면 chip ✕ 클릭 + applyFilters 1회 더 — 2단 작업. modal은 닫기 1회.
- 검색이 grid 필터를 덮어쓰면 사용자가 "내 필터는 어디 갔지?" 혼란 가능. modal은 grid를 변경하지 않음 → mental model 단순.

### 8.2 Rejected Architecture #2 — 별도 라우트 (`/chart/:code`)

**거부 사유**:
- 현재 SPA에 router 없음. 도입 비용 큼.
- 검색은 빠른 일회성 조회 행위. 페이지 이동 = 컨텍스트 전환 비용.
- 라우트 복귀 시 ChartGrid scroll/페이지 위치 보존 추가 작업 필요.

### 8.3 Rejected Architecture #3 — Floating panel (drag·resize 가능)

**거부 사유**:
- 복잡도 증가, 본 SPEC 의도(빠른 단일 종목 조회)와 불일치.
- 모달 1개로 충분. drag·resize는 yagni.

### 8.4 Performance trap re-check — modal도 트리거할 수 있나?

가능한 indirect 트리거를 모두 점검:

| 잠재 트리거 | 영향 여부 | 차단책 |
|---|---|---|
| ChartGrid context update (results 변경) | ❌ 영향 없음 — modal은 ChartGrid sibling | (선언적 격리) |
| useScreen 전역 변경 | ⚠ AppContent에서 useScreen 구독 시 영향. **modal 컴포넌트가 useScreen을 직접 구독하지 않아야 함** | StockSearchModal은 useScreen 구독 금지 |
| useTab.activeTab 변경 | ⚠ AppContent 리렌더 → modal 리렌더 가능. selectedStock state는 useState로 보존되므로 modal 재마운트는 안 됨. | useState ref 유지로 OK |
| body scroll lock(overflow:hidden) | DOM 변경, layout reflow 1회. chart에는 영향 없음 | OK |
| ResizeObserver | modal 차트 자체의 ResizeObserver는 modal 컨테이너만 관찰 | OK |
| 모달 백드롭 → keyboard focus shift | AnalysisModal 패턴 그대로 → trigger 요소(input)로 복귀 | OK |

결론: ChartGrid 부모 리렌더 → modal 차트 useEffect 재실행 경로는 **없다**.

### 8.5 State 동기화 위험

**선택**: 검색 결과는 **grid에 주입하지 않는다** (Disjoint semantic).
- 사용자가 검색으로 차트를 본 후 "이 종목을 grid 필터에 추가" 의도면 별도 액션 필요 — 본 SPEC scope 밖.
- 이 결정의 trade-off: 검색은 빠른 일회성 lookup. 통합 워크플로(테마→검색→grid 누적)는 별도 SPEC에서 다룬다.

### 8.6 Search algorithm scaling

2544 종목 × 입력당:
- prefix scan: 2544회 startsWith — < 1 ms (V8 JIT 후)
- 초성 추출: 평균 4글자 × 2544 = 10000 char 처리 — 약 2~3 ms
- 정렬: 매칭된 최대 N개(보통 < 50) — < 1 ms
- 합계: 입력당 약 5 ms (debounce 150 ms와 잘 떨어짐)

서버 사이드 자동완성 불필요. 5만 종목 규모까지는 client-side로 충분.

### 8.7 Hangul 정확성 — 복자모

`INITIAL_CONSONANTS` 19자: ㄱ ㄲ ㄴ ㄷ ㄸ ㄹ ㅁ ㅂ ㅃ ㅅ ㅆ ㅇ ㅈ ㅉ ㅊ ㅋ ㅌ ㅍ ㅎ.

쟁점:
- 사용자가 "ㅎㄷㅊ"(현대차)는 잘 입력. "ㅆㅁㅋ"(쌍방울)도 OK.
- 그러나 사용자가 "ㅅㅁㅋ"(쌍방울 의도)로 입력하면 매칭 실패 — initial consonant가 ㅆ인데 ㅅ로 입력. archive는 "쌍방울"의 첫 글자 초성을 ㅆ로 추출하므로 ㅅ→ㅆ 관용 매칭 안 됨. 한국 사용자는 보통 정확히 입력하므로 acceptable. 보완 옵션: ㅅ 입력 시 ㅆ 항목도 매칭(score 감점).

권장: archive 그대로 두고 manager-spec/run 단계에서 사용자 피드백 보면 추가.

### 8.8 a11y

- 키보드 only 사용자: ArrowDown/Up/Enter/Escape 보강 필수 (archive 누락).
- 스크린 리더: `aria-live` 영역으로 "검색 결과 N건" 안내 권장.
- 색약 사용자: 매칭 hover 색상이 충분한 대비 보장(WCAG AA, 4.5:1).

### 8.9 다른 환경 lock-in

- 검색 박스 추가가 ChartGrid toolbar layout을 부수면 안 됨(`91fd63b` 같은 패치 회피). archive `StockSearchBox` 폭 220 px 고정 + flexShrink:0이면 안전.
- 모바일 화면 폭(< 480 px): toolbar 4개 버튼 + 검색 220 px → 가로 스크롤 가능. UX 결정 필요. 본 PJ 데스크탑 우선이므로 manager-spec/run 단계에서 결정.

### 8.10 검색 정렬 안정성

archive `matchesQuery` 의 score sort는 stable이 아니다 (Array.prototype.sort는 V8 stable 보장 ES2019+, OK). 다만 동일 score 내 정렬 키 미정의 → 결과 순서가 입력에 따라 흔들릴 가능성. 추가 tiebreaker `name.localeCompare(other.name)` 권장.

---

## 9. Live Use Hypothesis (lesson #7 필수)

### 9.1 사용 빈도 예측

| 시나리오 | 1세션당 검색 횟수 | 비고 |
|---|---|---|
| 일반 사용자(평일 장중) | 1~3회 | 필터 결과에 없는 종목을 잠깐 확인 |
| 평일 장 마감 후 분석 | 3~5회 | 다른 종목과 비교하며 메모 작성 |
| 주말 리서치 모드 | 5~10회 | 테마별·이벤트 기반 종목 탐색 |
| 모바일·고지력 | 0~1회 | 모바일 UX 미흡 시 사용 안 함 |

평균 1세션 ~3회. archive SPEC-CHART-NAV-001은 grid 통합 흐름까지 묶어 "1세션 1회 미만"으로 평가되어 폐기되었다. 본 SPEC은 modal 격리로 **검색→차트 표시까지 1 클릭**으로 단축되어 실용성이 더 높다.

### 9.2 진입점

| Entry point | 가시성 | 트리거 |
|---|---|---|
| ChartGrid toolbar 좌측 input | 항상 | 클릭 → 입력 시작 |
| 단축키 `Ctrl/Cmd+K` | 숨김 | `keydown` 글로벌 핸들러(power user) — 본 SPEC 옵션. manager-spec 결정. |
| 필터 결과 0건 안내 라인의 "검색해보기" 링크 | 조건부 | filter 결과 0건일 때 자동 안내. **권장 — UX 친절도 ↑** |

### 9.3 만족 신호

- **성공 신호 1**: 입력 시작 후 200 ms 이내 후보 8건 노출.
- **성공 신호 2**: 선택 후 500 ms 이내 차트 first paint(candles 표시).
- **성공 신호 3**: ChartGrid 화면에 시각적 흐트러짐 0(grid behind modal 그대로).
- **성공 신호 4**: Esc 키 1번으로 모달 닫힘 + 검색 input에 focus 복귀.
- **실패 신호**: 사용자가 modal 닫고 다시 검색 / 닫지 않고 modal 그대로 둔 채 다른 탭 이동 — 모달 stale 상태 점검 필요.

### 9.4 폐기 기준 (rollback trigger)

본 SPEC도 lesson #7 패턴대로 다음 조건 충족 시 폐기 검토:
- 사용자 1세션당 평균 사용 횟수 < 0.5회 (2주 라이브 후)
- 검색 → 차트 표시 평균 latency > 1 s
- ChartGrid 성능 저하 발견 (모달 격리에도 불구하고 race 발생)
- 사용자 명시적 "이거 안 써요" 피드백 1건 이상

---

## 10. Performance Baseline + Targets (lesson #7 필수)

### 10.1 측정 baseline (current chore branch)

manager-spec/run 단계에서 다음 baseline을 실측한다(현재 chore branch, modal 없음 상태):

| 지표 | 측정 방법 | 목표(베이스라인) |
|---|---|---|
| ChartGrid 초기 렌더 시간 | React Profiler `ChartGrid` commit time | < 50 ms |
| ChartCell 1개 mount → first paint | DevTools Performance, `createChart` → setData 콜백 | < 300 ms (네트워크 포함) |
| FilterBar 입력당 ChartGrid 재렌더 횟수 | React Profiler "Highlight updates when re-render" | 0회 (submit 전) |
| ChartCell useEffect 호출 횟수/마운트 | console.log + grep | 1회 (StrictMode dev 제외) |
| ChartGrid scroll/page change FPS | DevTools Performance recording | 55+ FPS |

### 10.2 본 SPEC 도입 후 목표

| 지표 | 목표 | 측정 방법 |
|---|---|---|
| 검색 박스 input → 후보 노출 latency | ≤ 80 ms (debounce 150 ms 종료 후 5 ms 내) | performance.now() before/after setCandidates |
| 후보 선택 → 모달 차트 first paint | ≤ 300 ms (네트워크 9~19 ms + chart init + setData) | DevTools Performance |
| 모달 표시 중 ChartGrid 재렌더 추가 횟수 | 0회 (baseline과 동일) | React Profiler |
| 모달 차트 useEffect 호출 횟수/모달 열림당 | 1회 (StrictMode dev에서는 2회 허용) | console.log |
| ChartGrid scroll/page change FPS during modal open | ≥ 55 FPS (baseline 회귀 0) | DevTools Performance |
| 페이로드 — `GET /api/stocks/master` | gzip 후 < 50 KB | curl -H "Accept-Encoding: gzip" \| wc -c |
| `stocks/master` 응답 시간 (cold) | < 150 ms (현재 backend 평균 응답 9~19 ms, SQLite read 가벼움) | timing log |

### 10.3 성능 회귀 검증 자동화

- Vitest로 ChartGrid·ChartCell render count 단위 테스트: 모달 열림 전후 `vi.fn()` 으로 호출 횟수 검증
- Playwright e2e: 검색 → 선택 → 모달 표시 → 닫기 시나리오 자동 측정, performance.timing 캡처
- 본 SPEC `acceptance.md`에 NFR로 명시 권장

---

## 11. SPEC ID ↔ UI Element Mapping (lesson #7 필수, placeholder)

본 SPEC이 추가·변경하는 모든 UI 요소를 미리 열거한다. manager-spec 단계에서 실제 문구·data-testid 확정.

| # | UI 요소 | 위치 | 텍스트(잠정) | data-testid (제안) | 본 SPEC 관계 |
|---|---|---|---|---|---|
| 1 | 검색 input | ChartGrid toolbar 좌측 | placeholder: "종목명/코드/초성 검색" (정상) / "DB 업데이트 필요" (503) | `chart-search-input` | 신규 |
| 2 | 검색 후보 listbox | input 바로 아래 (relative position) | (동적) | `chart-search-listbox` | 신규 |
| 3 | 후보 option (per item) | listbox 내부 | "{name} {code} {market}" | `chart-search-option-{code}` | 신규 |
| 4 | "검색 결과 없음" 안내 | listbox 내부 (matches.length === 0) | "검색 결과 없음" | `chart-search-empty` | 신규 |
| 5 | StockSearchModal backdrop | document.body | (시각만) | `stock-search-modal-backdrop` | 신규 |
| 6 | StockSearchModal 컨테이너 | document.body | role="dialog" aria-modal="true" | `stock-search-modal` | 신규 |
| 7 | Modal 타이틀 | Modal header | "{name} ({code})" | `stock-search-modal-title` | 신규 |
| 8 | Modal timeframe 토글 | Modal header | "D" / "W" | `stock-search-modal-timeframe-toggle` | 신규 |
| 9 | Modal 닫기 버튼 | Modal header 우측 | "✕" (aria-label="닫기") | `stock-search-modal-close-btn` | 신규 |
| 10 | Modal chart canvas | Modal body | (시각만 — lightweight-charts container) | `stock-search-modal-chart` | 신규 |
| 11 | Modal 로딩 indicator | chart load 중 | (스피너) | `stock-search-modal-loading` | 신규 |
| 12 | Modal 에러 표시 | fetch 실패 시 | "{errorMessage}" | `stock-search-modal-error` | 신규 |
| 13 | 503 disabled tooltip | search input hover (503 상태) | "DB 업데이트가 필요합니다" | (title attribute) | 신규 |
| 14 | (옵션) "검색해보기" 링크 in 필터 0건 empty state | ChartGrid empty message | "검색해보기" → input focus | `chart-grid-empty-search-link` | manager-spec 결정 |
| 15 | (옵션) Cmd/Ctrl+K 단축키 | 글로벌 keydown | (시각 없음) | (test via key event) | manager-spec 결정 |

> manager-spec은 이 표를 최종 spec.md에 옮기고 문구·data-testid를 확정한다. 라이브 사용 중 "X UI 요소가 보여요/안 보여요" 신고 시 본 표로 SPEC ID 역추적.

---

## 12. Recommendations for manager-spec

### 12.1 REQ 후보 (EARS 형식)

manager-spec 단계에서 다음 REQ를 EARS 형식으로 작성 권장:

- **REQ-CS-001 (R)**: GET /api/stocks/master 엔드포인트는 stock_meta 전체 종목을 ETag·Cache-Control 헤더와 함께 반환한다.
- **REQ-CS-002 (R)**: stock_meta 부재 또는 빈 결과 시 503 stock_meta_not_ready 반환.
- **REQ-CS-003 (W)**: ChartGrid 화면에서 사용자가 검색 input에 입력하면 150 ms debounce 후 후보 최대 8건이 listbox로 노출된다.
- **REQ-CS-004 (W)**: 사용자가 후보를 클릭/Enter로 선택하면 StockSearchModal이 document.body에 portal로 렌더되며, 선택된 종목의 일봉 차트가 표시된다.
- **REQ-CS-005 (W)**: 모달 열림 중 ChartGrid는 변경되지 않는다(disjoint semantic).
- **REQ-CS-006 (E)**: 검색 매칭은 (a) 종목코드 prefix(숫자 입력), (b) 종목명 prefix, (c) 종목명 부분일치, (d) 한글 초성 prefix, 4단계 score로 정렬되어 반환된다.
- **REQ-CS-007 (W)**: 사용자가 Esc/백드롭/닫기 버튼으로 모달을 닫으면 검색 input으로 focus가 복귀한다.
- **REQ-CS-008 (W)**: 503 stock_meta_not_ready 상태에서는 검색 input이 disabled되고 placeholder가 "DB 업데이트 필요"로 변경된다.

### 12.2 NFR 후보

- **NFR-CS-P1**: 입력 후 후보 노출 ≤ 80 ms (debounce 종료 기준), 모달 차트 first paint ≤ 300 ms.
- **NFR-CS-P2**: 모달 표시 중 ChartGrid 재렌더 횟수는 baseline 대비 0회 증가.
- **NFR-CS-A1**: WCAG 2.1 AA — role/aria-modal/aria-labelledby/Esc/focus 복귀 모두 충족.
- **NFR-CS-A2**: 검색 listbox 키보드 네비게이션 — ArrowDown/Up/Enter/Escape 지원.
- **NFR-CS-C1**: 외부 라이브러리 추가 없음(한글 초성 알고리즘은 자체 47 LOC 구현).
- **NFR-CS-C2**: 백엔드 SQL은 SELECT-only, mode=ro URI.

### 12.3 Constraints

- **C-CS-001**: ChartGrid·FilterBar·ChartCell의 기존 동작 회귀 0. 본 SPEC은 ChartGrid에 input 위젯 1개만 추가하고 기존 cells 흐름·필터 흐름을 건드리지 않는다.
- **C-CS-002**: 모달은 React Portal → document.body. ChartGrid 트리 내부에 마운트 금지.
- **C-CS-003**: 검색 선택은 grid 필터에 영향 미치지 않는다(disjoint).
- **C-CS-004**: StockSearchBox는 useScreen·useTab을 직접 구독하지 않는다(부모 컨텍스트 격리).

### 12.4 Test 후보

- 단위(Vitest): `hangul.ts` (extractInitialConsonants, matchesQuery score), `useStockMaster` (lazy fetch + cache), `StockSearchBox` (debounce, key nav, 503 disabled), `StockSearchModal` (portal, esc, focus return)
- 백엔드(pytest): `stocks_master_service.list_stock_master` (정상/빈 테이블/테이블 없음/last_updated ETag)
- e2e(Playwright): 검색→선택→모달→Esc 1cycle, ChartGrid scroll FPS 측정, 503 stock_meta 미준비 시나리오

### 12.5 결정해야 할 미해결 항목 (manager-spec 단계)

1. 영문→한글 alias 사전 — 옵션 (c) 채택 여부 + 사전 크기
2. Cmd/Ctrl+K 단축키 — 추가 여부
3. ChartGrid empty state "검색해보기" 링크 — 추가 여부
4. 모달 닫기 시 검색 input 초기화 vs 입력 유지 — 어느 쪽이 사용자 mental model에 맞나
5. focus trap 구현 방법 — 기존 모달 패턴 답습 vs 새 헬퍼 컴포넌트 도입
6. DbUpdateButton 클릭 → `cachedPromise` reset 연동 여부

---

## 13. 참고: 신규/수정 파일 목록 요약

### 13.1 archive에서 cherry-pick

| # | 파일 | LOC(예상) | 변경 |
|---|---|---|---|
| 1 | `backend/routers/stocks.py` | +52 | 신규(archive 그대로) |
| 2 | `backend/services/stocks_master_service.py` | +65 | 신규(archive 그대로) |
| 3 | `backend/main.py` | +2 | import + include_router |
| 4 | `frontend/src/api/stocks.ts` | +25 | 신규(archive 그대로) |
| 5 | `frontend/src/hooks/useStockMaster.ts` | +42 | 신규(archive 그대로) |
| 6 | `frontend/src/utils/hangul.ts` | +47 | 신규(archive 그대로). `utils/` 디렉토리 신규. |

### 13.2 신규 작성

| # | 파일 | LOC(예상) | 비고 |
|---|---|---|---|
| 7 | `frontend/src/components/ChartGrid/StockSearchBox.tsx` | ~180 | archive 154 LOC 기반 + 키보드 네비게이션 추가 + onSelect prop |
| 8 | `frontend/src/components/ChartGrid/StockSearchModal.tsx` | ~250 | 신규. Portal + lightweight-charts 차트 인스턴스 + 자체 race guard + a11y |
| 9 | `frontend/src/components/ChartGrid/ChartGrid.tsx` | (수정 ~20줄) | toolbar에 StockSearchBox 마운트, AppContent로 selectedStock 전달 콜백. **기존 셀 흐름 변경 0.** |
| 10 | `frontend/src/AppContent.tsx` | (수정 ~15줄) | selectedStock state + StockSearchModal 렌더 호스트 |
| 11 | (선택) `frontend/src/utils/stock-aliases.json` | ~5 KB | 영문→한글 alias 매핑(manager-spec 결정) |

### 13.3 archive에서 가져오지 않음

- ScreenContext appliedContext 확장
- AppContent cross-tab appliedContext 분기
- FilterBar appliedContext chip
- ThemeDetailPanel/ThemeRankingTable 차트 버튼·chip
- ChartGrid mismatch banner
- types/market.ts CrossTabParams 확장

> 이 7개 자산은 SPEC-CHART-NAV-001 grid 통합 흐름의 일부였으며, 본 SPEC은 grid 통합을 의도적으로 제외한다.

---

## 부록 A. lesson #7 명시 준수 체크리스트

- [x] §9 라이브 사용 가설 — 빈도/진입점/만족·실패 신호/폐기 기준 모두 명시
- [x] §10 성능 baseline + 목표 — 측정 방법·수치 모두 명시(목표는 jw가 manager-spec 단계에서 baseline 실측 후 미세 조정 가능)
- [x] §11 SPEC↔UI 매핑 — 15개 UI 요소 placeholder 표 제공, manager-spec 단계에서 확정
- [x] §8.1~8.3 거부된 대안 — 3개 대안의 거부 사유 정량화
- [x] §4 성능 root cause — 메커니즘·증명·잔여 위험·차단책 모두 분석

---

**End of research.md**

다음 단계: manager-spec이 본 문서 기반으로 `spec.md`(EARS 요구사항), `plan.md`(태스크 분할), `acceptance.md`(AC + NFR 측정 기준) 작성.
