# Plan — SPEC-CHART-NAV-001 구현 가이드

본 문서는 SPEC-CHART-NAV-001을 `/moai run`으로 구현할 때 따르는 단계별 로드맵, 파일별 변경 매트릭스, 테스트 전략, 시퀀싱 권고, 롤백 전략을 정의한다.

작성일: 2026-05-07
출처: 사용자 승인된 plan 파일 `/Users/byunjungwon/.claude/plans/swirling-napping-canyon.md`
SPEC: `.moai/specs/SPEC-CHART-NAV-001/spec.md` v1.0.0

---

## §1 Implementation Roadmap (단계별 구현 순서)

### 1.1 권장 순서 — backend → frontend (utils/hooks → component) → integration

총 5 단계로 분리. 각 단계는 개별 commit 단위로 분리 가능하여 부분 롤백 가능 (§5 롤백 전략 참조).

| 단계 | 파일 그룹 | 산출물 | 검증 |
| --- | --- | --- | --- |
| **Step 1**: Backend stock master endpoint | `backend/routers/stocks.py`, `backend/services/stocks_master_service.py`, `backend/main.py`, `backend/tests/test_stocks_master.py` | `GET /api/stocks/master` 200/503 응답 + 단위 테스트 | `pytest backend/tests/test_stocks_master.py` |
| **Step 2**: Frontend utils + types | `frontend/src/utils/hangul.ts`, `frontend/src/utils/__tests__/hangul.test.ts`, `frontend/src/types/market.ts`, `frontend/src/api/stocks.ts`, `frontend/src/hooks/useStockMaster.ts` | Hangul 매칭 유틸 + cross-tab 타입 확장 + API client + cached hook | `npm run test -- hangul` |
| **Step 3**: ScreenContext + AppContent 확장 | `frontend/src/contexts/ScreenContext.tsx`, `frontend/src/AppContent.tsx` | appliedContext state + setter + AppContent useEffect 분기 추가 | 기존 ChartGrid baseline diff 0 확인 |
| **Step 4**: Frontend Feature B (검색) | `frontend/src/components/ChartGrid/StockSearchBox.tsx`, `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx`, `frontend/src/components/ChartGrid/ChartGrid.tsx` (StockSearchBox mount + mismatch banner), `frontend/src/components/FilterBar/FilterBar.tsx` (chip) | 검색 동선 end-to-end 작동 | `npm run test -- StockSearchBox` + manual 시나리오 D~H |
| **Step 5**: Frontend Feature A (테마) | `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx`, `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` + 두 test 파일 | 테마 진입 동선 end-to-end 작동 | `npm run test -- Theme*` + manual 시나리오 A~C |

### 1.2 sequencing 근거

- **Step 1 먼저 backend**: stock master endpoint가 없으면 Step 4의 useStockMaster() 훅이 작동 불가. 백엔드 테스트는 frontend 의존성 없음 → 격리 검증 가능.
- **Step 2 utils/types**: hangul.ts는 StockSearchBox에 의존받지만 자체적으로 단위 테스트 가능. types/market.ts의 CrossTabParams 확장은 Step 4/5의 navigateToTab 호출에서 사용.
- **Step 3 ScreenContext**: appliedContext state는 Step 4 (chip 표시), Step 5 (theme/search 동선) 모두에서 의존. 먼저 도입하면 Step 4/5에서 별도 작업 없이 바로 활용 가능.
- **Step 4 검색 먼저, Step 5 테마 나중**: 검색은 단일 종목 → 단순한 동선. 테마는 복수 종목 + mismatch banner 트리거 필요. 검색이 먼저 작동하면 chip / appliedContext / cross-tab 인프라 검증 완료된 상태에서 테마 동선만 추가하면 됨. 사용자 manual 검증도 단순한 시나리오부터 복잡한 시나리오로 진행 가능.

### 1.3 단계별 commit 권장 메시지 (참고용)

```
Step 1: feat(backend/stocks-master): add GET /api/stocks/master with 503 handling
Step 2: feat(frontend/utils): add hangul matching util + stock master API client
Step 3: feat(frontend/screen-context): add appliedContext state for cross-tab UX
Step 4: feat(frontend/chart-grid): inline stock search box with filter bypass
Step 5: feat(frontend/theme-analysis): add chart grid navigation from theme panel
```

(commit message 정책은 `.moai/config/sections/language.yaml git_commit_messages: ko` 따라 한국어 사용 가능.)

---

## §2 File-by-File Change Matrix (REQ-ID 매핑 통합)

### 2.1 Backend (신규 3 + 수정 1 = 4 files)

| 순번 | 파일 | 유형 | 핵심 변경 | 매핑 REQ | 매핑 AC |
| --- | --- | --- | --- | --- | --- |
| B-1 | `backend/routers/stocks.py` | NEW | FastAPI APIRouter 정의, `GET /api/stocks/master` endpoint, Pydantic 응답 모델 (StockMasterItem, StockMasterResponse), 200/503 분기, ETag 헤더 setting | REQ-CN-001, REQ-CN-003, REQ-CN-004, REQ-CN-R-001 | AC-S1, AC-S2, AC-S3 |
| B-2 | `backend/services/stocks_master_service.py` | NEW | `list_stock_master(daily_db_path: str) -> tuple[list[StockMasterItem], str]` 서비스 함수. SQLite read-only URI (`mode=ro`), `SELECT code, name, market FROM stock_meta WHERE name IS NOT NULL ORDER BY name`, MAX(last_updated) 별도 쿼리. 예외: sqlite3.OperationalError (table 부재), sqlite3.DatabaseError | REQ-CN-002, REQ-CN-C-004, REQ-CN-C-005 | AC-S4 |
| B-3 | `backend/main.py` | EDIT | `from backend.routers.stocks import router as stocks_router` (1줄) + `app.include_router(stocks_router, prefix="/api", tags=["stocks"])` (1줄). 그 외 변경 0 | REQ-CN-R-001 | (간접) AC-S1 |
| B-4 | `backend/tests/test_stocks_master.py` | NEW | pytest 모듈. 4 테스트: 200 정상 응답 (fixture DB), 503 응답 (stock_meta 없는 fixture DB), ETag 헤더 검증, name ASC 정렬 검증 + name NULL 미포함 검증 | (검증) AC-S1~S4 | AC-S1, AC-S2, AC-S3, AC-S4 |

### 2.2 Frontend (신규 6 + 수정 9 = 15 files)

| 순번 | 파일 | 유형 | 핵심 변경 | 매핑 REQ | 매핑 AC |
| --- | --- | --- | --- | --- | --- |
| F-1 | `frontend/src/utils/hangul.ts` | NEW | `extractInitialConsonants(s: string): string` (Hangul 음절 → 14자 leading consonant), `matchesQuery(item: StockMasterItem, query: string): { matched: boolean; score: number }` (4-tier 점수 0/1/2/3/4) | REQ-CN-011, REQ-CN-012 | AC-B2, AC-B3, AC-B4 |
| F-2 | `frontend/src/utils/__tests__/hangul.test.ts` | NEW | 단위 테스트: 가→ㄱ, 한→ㅎ, A→A, 1→1, 삼성전자→ㅅㅅㅈㅈ, 현대차→ㅎㄷㅊ, 빈 문자열, 혼합 입력 | (검증) REQ-CN-011 | AC-B4 |
| F-3 | `frontend/src/types/market.ts` | EDIT | `CrossTabParams` 인터페이스에 `themeName?: string`, `searchLabel?: string` 추가 (기존 stockCodes 보존) | REQ-CN-007, REQ-CN-013 | AC-A2, AC-B5 |
| F-4 | `frontend/src/api/stocks.ts` | NEW | `interface StockMasterItem { code: string; name: string; market: string }`, `interface StockMasterResponse { stocks: StockMasterItem[]; generated_at: string }`, `async function fetchStockMaster(): Promise<StockMasterResponse>` axios GET + 503 → custom error throw | REQ-CN-010 | AC-B1, AC-B8 |
| F-5 | `frontend/src/hooks/useStockMaster.ts` | NEW | module-level cached Promise<StockMasterResponse>. `useStockMaster()` 훅이 cached promise를 반환. lazy init: 첫 호출 시 fetchStockMaster() 발화 + retry 1회. 503 / network error 시 error state 노출 (disabled tooltip 트리거) | REQ-CN-010, AC-B8 | AC-B1, AC-B8 |
| F-6 | `frontend/src/contexts/ScreenContext.tsx` | EDIT | state 추가: `appliedContext: AppliedContext \| null`. AppliedContext 타입: `{ source: 'theme' \| 'search' \| 'explorer' \| 'filter'; label?: string; requestedCodeCount?: number }`. setter: `setAppliedContext`, `clearAppliedContext`. 기존 applyFilters 시그니처/동작 무수정 (REQ-CN-C-001) | REQ-CN-008, REQ-CN-015 | AC-A4, AC-B6, AC-C2 |
| F-7 | `frontend/src/AppContent.tsx` | EDIT | 기존 cross-tab useEffect 확장. `crossTabParams.stockCodes` 감지 시 applyFilters 호출 직후 setAppliedContext({ source, label, requestedCodeCount }) 추가. source/label 결정 로직: themeName 존재 → 'theme', searchLabel 존재 → 'search', 그 외 → 'explorer' (기존 default) | REQ-CN-008, REQ-CN-016 | AC-A4, AC-A5, AC-B5, AC-B6, AC-C4 |
| F-8 | `frontend/src/components/ChartGrid/StockSearchBox.tsx` | NEW | React 컴포넌트. props: `onSelect: (code: string, name: string) => void`. state: input value, dropdown items (filtered + scored, 최대 8), open. 디바운스 150ms. useStockMaster() 사용. 503 시 input disabled + tooltip "DB 업데이트가 필요합니다". 0건 시 "검색 결과 없음" | REQ-CN-009, REQ-CN-012, REQ-CN-013 | AC-B2, AC-B3, AC-B4, AC-B7, AC-B8 |
| F-9 | `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx` | NEW | vitest + Testing Library. 시나리오: "삼성" 입력 → dropdown에 삼성전자, "005" 입력 → 코드 prefix 매치 우선, "ㅅㅅ" 입력 → 초성 매치, 0건 입력 → "검색 결과 없음", onSelect 호출 검증, 503 mock → input disabled + tooltip | (검증) REQ-CN-009~013 | AC-B2, AC-B3, AC-B4, AC-B7, AC-B8 |
| F-10 | `frontend/src/components/ChartGrid/ChartGrid.tsx` | EDIT | (1) chart-grid-toolbar div 좌측에 `<StockSearchBox onSelect={(code, name) => navigateToTab('chart-grid', { stockCodes: [code], searchLabel: '종목: ' + name + ' ' + code })} />` 마운트. (2) 그리드 상단에 mismatch banner conditional 렌더링 (`screenState.appliedContext?.requestedCodeCount > flatStocks.length` 시) | REQ-CN-009, REQ-CN-013, REQ-CN-014 | AC-A6, AC-B5, AC-C1 |
| F-11 | `frontend/src/components/FilterBar/FilterBar.tsx` | EDIT | `screenState.appliedContext?.label` 존재 시 chip 렌더링. ✕ 클릭 시 clearAppliedContext() + applyFilters(DEFAULT_SCREEN_REQUEST). `data-testid="filter-bar-applied-context-chip"` | REQ-CN-015 | AC-A4, AC-B6, AC-C2 |
| F-12 | `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | EDIT | 헤더 영역에 primary 버튼 추가: `<button onClick={() => navigateToTab('chart-grid', { stockCodes: theme.stocks.map(s => s.stock_code), themeName: theme.theme_name })}>차트 그리드로 보기 ({theme.stocks.length}종목)</button>`. 기존 헤더 / theme_description 본문 박스 / 종목 테이블 변경 0 (REQ-NT3-009/010 보존) | REQ-CN-005, REQ-CN-007 | AC-A1, AC-A2 |
| F-13 | `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | EDIT | 각 행 trailing cell에 chip 추가: `<span className="theme-row-chip" onClick={(e) => { e.stopPropagation(); navigateToTab('chart-grid', { stockCodes: theme.stocks.map(s => s.stock_code), themeName: theme.theme_name }); }}>차트</span>`. 기존 행 click 핸들러 (상세 패널 열기) 무수정 | REQ-CN-006, REQ-CN-007 | AC-A3 |
| F-14 | `frontend/src/components/ThemeAnalysis/__tests__/ThemeDetailPanel.test.tsx` | EDIT | 신규 테스트 추가: (1) 헤더 버튼 라벨에 N종목 라이브 표시 검증, (2) 버튼 클릭 시 navigateToTab 호출 인자 검증 (stockCodes, themeName) | (검증) REQ-CN-005, REQ-CN-007 | AC-A1, AC-A2 |
| F-15 | `frontend/src/components/ThemeAnalysis/__tests__/ThemeRankingTable.test.tsx` | EDIT | 신규 테스트 추가: (1) 행별 chip 클릭 시 navigateToTab 호출 + 그 테마의 stockCodes만 전달, (2) chip 클릭이 행 클릭 핸들러를 트리거하지 않음 (event.stopPropagation 검증) | (검증) REQ-CN-006, REQ-CN-007 | AC-A3 |

### 2.3 변경 요약

- **신규**: backend 3 + frontend 6 = 9 files
- **수정**: backend 1 + frontend 9 = 10 files
- **총합**: 19 files (plan §"핵심 파일 경로 요약"과 일치)

---

## §3 Test Plan

### 3.1 신규 단위 테스트 (7개)

| ID | 파일 | 검증 대상 | 검증 시나리오 |
| --- | --- | --- | --- |
| UT-1 | `backend/tests/test_stocks_master.py::test_master_200` | REQ-CN-001 / REQ-CN-002 | fixture stock_meta DB → 200 응답, stocks 배열 정상 + name ASC 정렬 |
| UT-2 | `backend/tests/test_stocks_master.py::test_master_503` | REQ-CN-004 | stock_meta 없는 fixture → 503 + `{"detail": "stock_meta_not_ready"}` |
| UT-3 | `backend/tests/test_stocks_master.py::test_master_etag` | REQ-CN-003 | fixture DB last_updated MAX → 응답 ETag 헤더 일치 |
| UT-4 | `backend/tests/test_stocks_master.py::test_master_name_filter` | REQ-CN-002 | name NULL row → 응답에 미포함 |
| UT-5 | `frontend/src/utils/__tests__/hangul.test.ts` | REQ-CN-011 | extractInitialConsonants: 가→ㄱ, 한→ㅎ, 삼성→ㅅㅅ, A→A, 1→1, 빈 문자열, 혼합 |
| UT-6 | `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx` | REQ-CN-009/012/013, AC-B7/B8 | "삼성"/"005"/"ㅅㅅ"/0건/onSelect/503 mock 시나리오 |
| UT-7 | `frontend/src/components/ThemeAnalysis/__tests__/ThemeDetailPanel.test.tsx` + `ThemeRankingTable.test.tsx` (확장) | REQ-CN-005/006/007 | 헤더 버튼 라벨, navigateToTab 호출 인자, chip event.stopPropagation |

### 3.2 통합 / 수동 검증 시나리오 (8개)

(SPEC §verification에서 발췌, plan 파일 §verification 섹션 동일)

| 시나리오 | 검증 대상 | 매핑 AC |
| --- | --- | --- |
| A. 테마→그리드 헤더 버튼 | REQ-CN-005, REQ-CN-007 | AC-A1, AC-A2 |
| B. 테마 행별 chip | REQ-CN-006, REQ-CN-007 | AC-A3 |
| C. 누락 안내 banner (의도적 시뮬레이션) | REQ-CN-014 | AC-A6, AC-C1 |
| D. 종목 검색 — 부분 일치 ("삼성") | REQ-CN-012 (score 2) | AC-B2 |
| E. 종목 검색 — 코드 prefix ("005") | REQ-CN-012 (score 4) | AC-B3 |
| F. 종목 검색 — 초성 ("ㅅㅅㅈㅈ") | REQ-CN-011, REQ-CN-012 (score 1) | AC-B4 |
| G. 검색 → 필터 우회 (market_cap_min 적용 상태) | REQ-CN-C-006, REQ-CN-016 | AC-B5, AC-C4 |
| H. stock master 캐싱 (DevTools Network) | REQ-CN-010 | AC-B1 |

추가 회귀 검증 (manual 또는 vitest baseline diff 0 확인):

- 기존 StockExplorer→Grid 동선 정상 (시총 사진) → AC-R2
- 기존 SectorAnalysis→StockExplorer cross-tab 정상 → AC-R3
- ThemeAnalysis localStorage 캐시(REQ-NT3-015/016) 동작 정상 → AC-R4
- SPEC-NAVER-THEME-CONSOLIDATED 25 AC PASS 유지 → AC-R1

### 3.3 라이브 검증 의무 (LESSON-NTC-001)

다음 AC는 fixture 단위 테스트만으로 충분하지 않으며 manual browser 검증을 거쳐 잠근다:

- AC-B2/B3/B4 (검색 매칭 정확도) — 시나리오 D, E, F
- AC-A6 / AC-C1 (mismatch banner 비개발자 친화 문구) — 시나리오 C
- AC-A4 / AC-B6 (chip 시각 우선순위 + ✕ reset) — 시나리오 A, D 일부

---

## §4 Sequencing 조언 (TDD vs DDD)

본 프로젝트는 `.moai/config/sections/quality.yaml`의 `development_mode` 설정에 따라 manager-ddd 또는 manager-tdd 중 하나를 사용한다. 결정은 `/moai run` 시점의 quality.yaml 값에 따른다.

### 4.1 TDD 모드 권장 시퀀스 (RED-GREEN-REFACTOR)

각 Step 내부에서 RED → GREEN → REFACTOR 사이클 적용. 예시 (Step 4 StockSearchBox):

1. **RED**: `StockSearchBox.test.tsx`에 "삼성" 입력 시나리오 테스트 작성. 컴포넌트 구현 전이므로 import 실패 → RED.
2. **GREEN**: 최소 구현으로 input + dropdown 1개 항목 렌더. 테스트 PASS.
3. **REFACTOR**: 디바운스, scoring, 0건 처리, 503 처리 등 고도화. 테스트 PASS 유지.
4. 다음 시나리오 ("005" 코드 prefix) 추가 → RED → GREEN → REFACTOR 반복.

이 패턴을 모든 Step 1~5에 적용. backend는 pytest 기반 동일 사이클.

### 4.2 DDD 모드 권장 시퀀스 (ANALYZE-PRESERVE-IMPROVE)

ChartGrid / ThemeAnalysis는 기존 코드가 충분히 정비된 상태이므로 본 SPEC은 **확장 시나리오에 가깝다**. DDD 모드에서:

1. **ANALYZE**: research.md를 읽고 cross-tab 인프라 + ScreenContext + ThemeAnalysis 컴포넌트 동작 이해.
2. **PRESERVE**: 기존 ChartGrid 1 fail baseline + ThemeAnalysis vitest 시나리오 + StockExplorer 동선의 characterization 테스트가 모두 PASS 상태인지 먼저 확인 (변경 전 baseline 캡처).
3. **IMPROVE**: §1.1 5개 Step을 순차 진행. 각 Step 후 baseline diff 0 확인 → 다음 Step 진행.

### 4.3 공통 권장사항

- 단계 간 commit 분리 → 부분 롤백 가능 (§5).
- 신규 함수에 `@MX:NOTE` (의도 / 단일 책임) 추가, ChartGrid의 mismatch banner 같은 가시화 surface에는 `@MX:ANCHOR` (high fan_in 가능성) 검토.
- 신규 backend 함수에 bare except 절대 금지 — 단위 테스트로 specific exception 검증 (REQ-CN-C-004).

---

## §5 Rollback 전략

### 5.1 단계별 독립 commit

§1.1의 5개 Step은 각각 독립 commit으로 분리 가능:

| Step | 롤백 영향 |
| --- | --- |
| Step 1 (backend) 롤백 | `/api/stocks/master` 사라짐. Step 4 검색 동선이 503 처리로 disabled (회귀 안전). 기존 4탭 + ThemeAnalysis 영향 0 |
| Step 2 (utils/types) 롤백 | hangul.ts, useStockMaster, types 확장 사라짐. Step 4/5 의존성 깨짐 → Step 4/5도 함께 롤백 필요 |
| Step 3 (ScreenContext) 롤백 | appliedContext state 사라짐. Step 4/5의 chip / mismatch banner / cross-tab label 동작 불가 → Step 4/5도 함께 롤백 필요 |
| Step 4 (검색) 롤백 | StockSearchBox 사라지고 mismatch banner 사라짐. Step 5 (테마) 동선은 chip / appliedContext 의존 → Step 5도 함께 롤백 필요 (또는 Step 5만 별도 롤백 가능) |
| Step 5 (테마) 롤백 | ThemeDetailPanel 헤더 버튼 + ThemeRankingTable chip 사라짐. 검색 동선은 영향 없음 |

### 5.2 부분 롤백 패턴

- **Feature A만 롤백**: Step 5 commit revert. Feature B (검색)는 그대로 작동.
- **Feature B만 롤백**: Step 1, 4 commit revert. Step 2/3은 Feature A에서도 사용하므로 보존. Feature A는 Step 3에 의존하므로 Step 3은 보존 필요.
- **전체 롤백**: 5개 commit 역순 revert. 또는 main branch checkout으로 작업 전 상태 복귀.

### 5.3 회귀 발견 시 행동

배포 후 회귀가 발견되면:

1. AC-R1~R4 회귀 게이트 중 어느 것이 실패했는지 식별.
2. SPEC-NAVER-THEME-CONSOLIDATED 25 AC 회귀 시 → 전체 롤백 + amendment 작성.
3. StockExplorer / SectorAnalysis 동선 회귀 시 → AppContent useEffect 변경 (Step 3 또는 7) 부분 검토 + 롤백.
4. ThemeAnalysis localStorage 캐시 회귀 시 → Step 5 (ThemeDetailPanel/RankingTable) 변경 검토 + read-only 호환 확인.
5. 신규 동선만 실패 시 → 해당 Step만 부분 롤백 + amendment + retry.

### 5.4 stock_meta DB 영향 무

본 SPEC의 모든 backend 코드는 `mode=ro` SQLite URI 사용 (REQ-CN-C-005). 어떤 시나리오에서도 stock_data_daily.db에 INSERT/UPDATE/DELETE/CREATE/DROP/ALTER 발생 0건 보장. **DB rollback은 영원히 불필요**.

---

## §6 LESSON 적용 체크리스트

본 plan을 SPEC으로 변환하여 `/moai run` 진행 시 반드시 확인:

- [x] **LESSON-NTC-001 (라이브 UX 검증)**: AC-B2/B3/B4의 검색 매칭 정확도와 AC-A6/C1의 mismatch banner 문구는 fixture 테스트 외에 manual browser 시나리오 D/E/F/C에서 라이브 검증 후 잠근다 (REQ-CN-NF-005). spec.md §8.3에 매핑 명시.
- [x] **LESSON-NTC-002 (시각 우선순위)**: 검색창 = ChartGrid 툴바 좌측, mismatch banner = 그리드 상단, chip = FilterBar 영역. spec.md §1.5 데이터 흐름에 visual hierarchy 명시.
- [x] **LESSON-NTC-003 (default 모드 가시성)**: 모든 cross-tab 진입 동선에서 stockCodes는 항상 `{ ...DEFAULT_SCREEN_REQUEST, codes }`로 처리 (full reset이 default). REQ-CN-C-006 + AC-A5/B5에 명시.
- [x] **LESSON-NTC-004 (stock_meta 단일 source)**: stock_meta가 검색 데이터 흐름의 단일 source. 누락된 종목은 mismatch banner로 가시화. REQ-CN-002 + REQ-CN-014 + AC-A6에 명시.
- [x] **LESSON-NTC-005 (사용 패턴 → 캐시 모델)**: stock master 캐시는 자동 만료 없음, DB의 last_updated 변경 시에만 ETag 갱신. REQ-CN-C-007 + REQ-CN-003에 명시.

---

## §7 Out of Scope (plan 단계 명시)

다음은 본 SPEC 구현 단계에서 **수행하지 않음**. 향후 별도 SPEC 또는 v2:

- URL 기반 deep linking (별도 SPEC-TAB-URL-001)
- 모바일 UX 최적화 (데스크탑 우선)
- 검색 history / 최근 검색
- 종목 다중 선택 검색
- 섹터/제품/테마 키워드 검색
- 서버 측 fuzzy 매칭
- 백엔드 in-memory 장시간 TTL 캐시 (자동 만료 없음 정책 유지)
- 멀티테마 종목 위젯 → ChartGrid 진입점

자세한 분류는 spec.md §7 Exclusions 참조.

---

Version: 1.0.0
Status: Ready for /moai run
Last Updated: 2026-05-07
