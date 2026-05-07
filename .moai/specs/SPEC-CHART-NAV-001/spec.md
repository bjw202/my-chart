---
id: SPEC-CHART-NAV-001
title: 차트 그리드 종목 네비게이션 통합 (테마→그리드 + 종목 검색 + 필터 우회)
status: Draft
version: 1.0.0
owner: bjw2002
created: 2026-05-07
updated: 2026-05-07
depends_on: SPEC-NAVER-THEME-CONSOLIDATED
---

# SPEC-CHART-NAV-001: 차트 그리드 종목 네비게이션 통합

## 메타데이터

| 항목 | 값 |
| --- | --- |
| SPEC ID | SPEC-CHART-NAV-001 |
| 제목 | 차트 그리드 종목 네비게이션 통합 — 테마 진입 + 종목 검색 + 필터 우회 |
| 생성일 | 2026-05-07 |
| 상태 | Draft |
| 우선순위 | High |
| 담당 | expert-backend, expert-frontend, expert-testing |
| 의존 SPEC | SPEC-NAVER-THEME-CONSOLIDATED v1.0.0 |
| Lifecycle | spec-anchored |
| 버전 | 1.0.0 |

---

## HISTORY

- 2026-05-07 v1.0.0: 초안 작성 (manager-spec). 사용자 승인된 plan 파일(`/Users/byunjungwon/.claude/plans/swirling-napping-canyon.md`) 기반. SPEC-NAVER-THEME-CONSOLIDATED 회고에서 도출된 LESSON-NTC-001~005 적용. 사용자 사전 잠금 결정 사항(D-1~D-8): A 액션 위치(상세 패널 메인 버튼 + 행별 chip 둘 다), 필터 reset 정책(full reset), 누락 안내 문구(비개발자 친화), 검색 매칭(종목명 부분 + 코드 prefix + 초성), stock master 데이터 소스(신규 GET /api/stocks/master), 검색 결과 0건 표시, 503 처리, URL deep linking 별도 SPEC 분리.

---

## 1. Environment (환경)

### 1.1 시스템 개요

본 SPEC은 두 개의 사용자 동선을 단일 cross-tab 인프라 위에서 통합 구현한다.

- **Feature A (Theme→Grid)**: 테마 분석 화면에서 사용자가 특정 테마의 모든 종목을 ChartGrid에서 동시에 비교할 수 있도록 진입점 추가. ThemeDetailPanel 헤더 메인 버튼 + ThemeRankingTable 행별 chip의 두 진입점 제공.
- **Feature B (Search→Grid)**: ChartGrid 툴바 좌측에 인라인 종목 검색 입력 추가. 사용자가 활성 필터(시가총액 / 등락률 / RS / 섹터) 조건과 무관하게 원하는 종목을 즉시 ChartGrid에 표시할 수 있도록 한다.

핵심 발견 (Phase 1 코드베이스 탐사 결과):

- `useTab().navigateToTab('chart-grid', { stockCodes: [...] })` cross-tab 채널은 이미 StockExplorer→ChartGrid 동선에서 작동 중이다.
- `frontend/src/AppContent.tsx` useEffect가 `crossTabParams.stockCodes`를 감지하면 자동으로 `applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes })`를 실행한다 → codes만 적용되고 다른 필터는 reset된다.
- 따라서 두 기능 모두 같은 cross-tab 채널을 통해 실현하면 "필터 우회"가 한 곳에서 일관되게 처리된다. 새 상태 라이브러리/컨텍스트 도입 불필요.

### 1.2 모듈 변경 매트릭스

신규 9 + 수정 10 = 총 19 files. (출처: plan §"핵심 파일 경로 요약")

**신규 (Backend, 3 files)**:

| 파일 | 역할 |
| --- | --- |
| `backend/routers/stocks.py` | `GET /api/stocks/master` 라우트 정의 |
| `backend/services/stocks_master_service.py` | `list_stock_master(daily_db_path)` 서비스 함수 |
| `backend/tests/test_stocks_master.py` | 200/503/정렬/row count 단위 테스트 |

**신규 (Frontend, 6 files)**:

| 파일 | 역할 |
| --- | --- |
| `frontend/src/api/stocks.ts` | `fetchStockMaster()` axios 호출 + 503 처리 |
| `frontend/src/hooks/useStockMaster.ts` | module-level cached promise + lazy fetch |
| `frontend/src/utils/hangul.ts` | `extractInitialConsonants` + `matchesQuery` 매칭 점수 함수 |
| `frontend/src/utils/__tests__/hangul.test.ts` | 가→ㄱ, 한→ㅎ, A→A, 1→1 등 단위 테스트 |
| `frontend/src/components/ChartGrid/StockSearchBox.tsx` | 입력 + dropdown 컴포넌트 (debounce 150ms) |
| `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx` | "삼성"/"005"/"ㅅㅅ"/0건/onSelect 검증 |

**수정 (Backend, 1 file)**:

| 파일 | 변경 |
| --- | --- |
| `backend/main.py` | `stocks_router` import 1줄 + `app.include_router(stocks_router)` 1줄 |

**수정 (Frontend, 9 files)**:

| 파일 | 변경 |
| --- | --- |
| `frontend/src/types/market.ts` | `CrossTabParams.themeName?: string`, `searchLabel?: string` 추가 |
| `frontend/src/AppContent.tsx` | 기존 cross-tab useEffect 확장 — `themeName` / `searchLabel` / `requestedCodeCount`를 ScreenContext.appliedContext로 위임 |
| `frontend/src/contexts/ScreenContext.tsx` | `appliedContext` state 신설 (source/label/requestedCodeCount) + setter/clear |
| `frontend/src/components/ChartGrid/ChartGrid.tsx` | StockSearchBox 마운트 + onSelect 시 navigateToTab + mismatch banner 렌더링 |
| `frontend/src/components/FilterBar/FilterBar.tsx` | `appliedContext.label` chip 렌더링 (✕로 reset) |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | 헤더 "차트 그리드로 보기 (N종목)" 버튼 + onClick → navigateToTab |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | 각 행 끝 셀에 "차트" chip + onClick → navigateToTab |
| `frontend/src/components/ThemeAnalysis/__tests__/ThemeDetailPanel.test.tsx` | 버튼 클릭 시 navigateToTab 호출 검증, N종목 라벨 검증 |
| `frontend/src/components/ThemeAnalysis/__tests__/ThemeRankingTable.test.tsx` | 행별 chip 클릭 시 해당 테마 stocks만 전달 검증 |

### 1.3 외부 의존성

신규 pip / npm 패키지 0건. SPEC-NAVER-THEME-CONSOLIDATED REQ-NT-C-003(신규 의존성 금지) 원칙 계승.

- Backend (기설치): `fastapi`, `pydantic`, `sqlite3` (stdlib).
- Frontend (기설치): `react`, `axios`, `vitest`, `@testing-library/react`. Hangul 매칭 라이브러리 미사용 — 자체 ~25줄 TypeScript 유틸로 자체 구현.

### 1.4 영향 범위 (애드온 경계)

- 신규 backend 라우트: `GET /api/stocks/master` 1건.
- 기존 backend 라우트(`/api/screen`, `/api/themes/v2/*`, `/api/stage/overview`, `/api/sectors`, `/api/themes/snapshot`, `/api/themes/quick`) 무수정.
- 기존 4탭 + ThemeAnalysis 탭 회귀 0건 (SPEC-NAVER-THEME-CONSOLIDATED REQ-NT-C-002 계승).
- Master DB (`stock_data_daily.db`) `stock_meta` 테이블 SELECT only (REQ-NT-C-001 계승).
- ThemeAnalysis localStorage 캐시(SPEC-NAVER-THEME-CONSOLIDATED REQ-NT3-015) 호환 — 신규 액션은 read-only 활용만 함.

### 1.5 데이터 흐름 도식

**Feature A (Theme→Grid)**:

```
ThemeDetailPanel 헤더 버튼 클릭  OR  ThemeRankingTable 행별 chip 클릭
                                  ↓
useTab().navigateToTab('chart-grid', { stockCodes: theme.stocks.map(s => s.stock_code), themeName: theme.theme_name })
                                  ↓
TabContext state update (activeTab='chart-grid', crossTabParams 갱신)
                                  ↓
AppContent.tsx useEffect (crossTabParams.stockCodes 감지)
                                  ↓
ScreenContext.applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes: stockCodes })
ScreenContext.setAppliedContext({ source: 'theme', label: '테마: <name> (N)', requestedCodeCount: stockCodes.length })
                                  ↓
POST /api/screen
                                  ↓
ChartGrid 렌더 + (requestedCodeCount > flatStocks.length 시) mismatch banner 표시
FilterBar appliedContext chip 렌더 (✕ 클릭 시 reset)
```

**Feature B (Search→Grid)**:

```
ChartGrid 툴바 StockSearchBox 입력 첫 focus
                                  ↓
useStockMaster() lazy fetch → GET /api/stocks/master (세션 1회)
                                  ↓
사용자 키 입력 (debounce 150ms)
                                  ↓
matchesQuery(item, query) 4-tier 점수 매칭 (코드 prefix > 종목명 prefix > 종목명 substring > 초성)
                                  ↓
dropdown 최대 8개 노출 (또는 "검색 결과 없음")
                                  ↓
사용자 항목 선택 → onSelect(code, name)
                                  ↓
useTab().navigateToTab('chart-grid', { stockCodes: [code], searchLabel: '종목: <name> <code>' })
                                  ↓
(이후 동선은 Feature A와 동일 — applyFilters + setAppliedContext + ChartGrid 렌더)
```

---

## 2. Assumptions (가정)

### 2.1 외부 시스템 가정

- [A-1] `Output/stock_data_daily.db.stock_meta` 테이블이 가용하며 `code` (TEXT, 6자리 zero-padded), `name` (TEXT, nullable), `market` (TEXT, "KOSPI" / "KOSDAQ"), `last_updated` 컬럼을 보유한다.
- [A-2] `/api/screen` 엔드포인트는 SPEC-NAVER-THEME-CONSOLIDATED REQ-NT-C-002에 따라 무수정 상태이며, `codes: list[str]` 파라미터를 정상 처리한다.
- [A-3] stock_meta는 활성 종목 약 2,500개 row 수준이며, 응답 페이로드는 raw ~80KB / gzip ~30KB 범위에 들어간다.

### 2.2 호환성 가정

- [A-4] 기존 cross-tab 인프라(`useTab().navigateToTab`, AppContent useEffect, `useScreen().applyFilters`)는 SPEC-CHART-NAV-001 변경 후에도 무수정 상태로 작동한다 (REQ-CN-C-001).
- [A-5] StockExplorer→ChartGrid 동선(StockExplorer.tsx:80 navigateToTab 호출)은 본 SPEC 작업과 무관하게 정상 작동을 유지한다.
- [A-6] ThemeAnalysis localStorage 캐시(SPEC-NAVER-THEME-CONSOLIDATED REQ-NT3-015/016)는 본 SPEC의 Feature A 액션(테마 종목 코드 목록 read)에 대해 read-only 호환성을 가진다.

### 2.3 사용 패턴 가정 (LESSON-NTC-005 계승)

- [A-7] 단일 사용자 사용 시나리오. stock master는 한 세션 1회 fetch면 충분하며, 자동 만료/refresh는 불필요하다. 캐시 무효화는 DB의 `stock_meta.last_updated` 변경 시 ETag 갱신으로만 발생한다.
- [A-8] 검색은 명시적 사용자 액션이며 keystroke 단위 네트워크 호출 0건. 매칭은 클라이언트 인메모리에서 수행한다.

### 2.4 테스트 전략 가정

- [A-9] 백엔드 단위 테스트는 fixture 기반으로 네트워크 / 라이브 DB 없이 실행 가능하다.
- [A-10] 프론트엔드 단위 테스트는 vitest + Testing Library 환경에서 mock된 axios / TabContext 위에서 실행 가능하다.
- [A-11] 라이브 검증(LESSON-NTC-001 적용) 시나리오는 manual browser 검증으로 8건 수행한다 (§verification 섹션 참조).

---

## 3. Requirements (EARS 형식)

### 3.1 Functional Requirements

#### Backend

##### REQ-CN-001 (Ubiquitous): 신규 stock master 엔드포인트

The system **shall** expose `GET /api/stocks/master` returning the full set of active stocks from `stock_meta` for client-side search. 라우터 파일 `backend/routers/stocks.py`에 정의되며 `backend/main.py`에 register된다.

##### REQ-CN-002 (Ubiquitous): SELECT-only 조회

The system **shall** read `code, name, market` columns from `stock_meta` via `SELECT code, name, market FROM stock_meta WHERE name IS NOT NULL ORDER BY name` against the read-only SQLite URI (`mode=ro`). DB INSERT / UPDATE / DELETE / CREATE / DROP / ALTER is prohibited (REQ-CN-C-005).

##### REQ-CN-003 (Ubiquitous): ETag 발급

The system **shall** compute the response `ETag` header from `MAX(stock_meta.last_updated)` (ISO-8601 KST). DB 업데이트가 실제로 발생할 때에만 ETag 변경. 응답 추가 헤더: `Cache-Control: max-age=300`.

##### REQ-CN-004 (Unwanted): stock_meta 부재 시 503 응답

**IF** the underlying SQLite DB does not contain `stock_meta` table or the table is empty, **THEN** the system **shall** return HTTP 503 with body `{"detail": "stock_meta_not_ready"}`. 응답 패턴은 `/api/screen`의 stock_meta 부재 처리와 일관된다.

#### Frontend Theme→Grid (Feature A)

##### REQ-CN-005 (Event-Driven): ThemeDetailPanel 헤더 메인 버튼

**WHEN** ThemeDetailPanel이 렌더링되고 `selectedTheme.stocks`가 비어있지 않으면, **THEN** the system **shall** render a primary button labeled `차트 그리드로 보기 (N종목)` in the panel header. N은 `selectedTheme.stocks.length` 라이브 값.

##### REQ-CN-006 (Event-Driven): ThemeRankingTable 행별 chip

**WHEN** ThemeRankingTable이 행을 렌더링하면, **THEN** the system **shall** render a `차트` chip in the trailing cell of each row. Chip 클릭 시 `event.stopPropagation()`을 호출하여 행의 상세 패널 열기 핸들러는 발화하지 않는다.

##### REQ-CN-007 (Event-Driven): navigateToTab 호출 (Theme)

**WHEN** REQ-CN-005 버튼 또는 REQ-CN-006 chip이 클릭되면, **THEN** the system **shall** call `useTab().navigateToTab('chart-grid', { stockCodes: theme.stocks.map(s => s.stock_code), themeName: theme.theme_name })`.

##### REQ-CN-008 (Event-Driven): appliedContext 설정 (Theme)

**WHEN** AppContent useEffect가 `crossTabParams.themeName`을 감지하면, **THEN** the system **shall** call `setAppliedContext({ source: 'theme', label: '테마: <theme_name> (N)', requestedCodeCount: stockCodes.length })` after invoking `applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes: stockCodes })`.

#### Frontend Search→Grid (Feature B)

##### REQ-CN-009 (Ubiquitous): ChartGrid 툴바 StockSearchBox 마운트

The system **shall** mount `StockSearchBox` component on the left side of `chart-grid-toolbar` div within `ChartGrid.tsx`. Width ~220px. 모달 / cmd+K / 글로벌 헤더 검색은 채택하지 않는다 (D-1 사전 잠금).

##### REQ-CN-010 (Event-Driven): stock master lazy fetch

**WHEN** the user first focuses `StockSearchBox` input within a session, **THEN** the system **shall** invoke `useStockMaster()` hook which dispatches a single `fetchStockMaster()` call to `GET /api/stocks/master` and caches the resolved promise at module level. 같은 세션 내 두 번째 focus부터는 cached promise를 reuse — 추가 네트워크 호출 0.

##### REQ-CN-011 (Ubiquitous): Hangul 매칭 유틸리티

The system **shall** implement `extractInitialConsonants(s: string): string` and `matchesQuery(item: StockMasterItem, query: string): { matched: boolean; score: number }` in `frontend/src/utils/hangul.ts`. `extractInitialConsonants`는 Hangul 음절(0xAC00~0xD7A3)을 `(code - 0xAC00) / 588`로 나눈 leading consonant index를 ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ 14자에 매핑한다. 비-Hangul 문자는 그대로 통과.

##### REQ-CN-012 (Event-Driven): dropdown 매칭 및 정렬

**WHEN** 사용자 입력이 150ms 디바운스를 통과하면, **THEN** the system **shall** filter stock master items by `matchesQuery` and render up to 8 items in dropdown sorted by score:

1. (score 4) 코드 정확 prefix — 6자리 숫자 입력 시
2. (score 3) 종목명 정확 prefix
3. (score 2) 종목명 substring (부분 일치)
4. (score 1) 초성 매치

매칭 결과 0건 시 dropdown은 "검색 결과 없음" 안내 노출 (D-6 사전 잠금).

##### REQ-CN-013 (Event-Driven): navigateToTab 호출 (Search)

**WHEN** dropdown 항목이 선택되면, **THEN** the system **shall** call `useTab().navigateToTab('chart-grid', { stockCodes: [chosen.code], searchLabel: '종목: <chosen.name> <chosen.code>' })`. 선택 후 dropdown은 닫히고 입력 필드는 clear된다.

#### Frontend 공통 (mismatch banner + chip + AppContent)

##### REQ-CN-014 (Event-Driven): mismatch banner

**WHEN** ChartGrid가 렌더링되고 `screenState.appliedContext?.requestedCodeCount > flatStocks.length`이면, **THEN** the system **shall** render a dismissible inline notice at the top of the grid:

> "요청한 X종목 중 Y종목 표시 — Z종목은 현재 DB에서 조회되지 않는 종목입니다 (상장폐지 / 신규상장 / 메타 미반영)."

X = requestedCodeCount, Y = flatStocks.length, Z = X − Y. 비개발자 친화 문구이며 `stock_meta` 같은 내부 용어는 노출하지 않는다 (D-3 사전 잠금). `data-testid="chart-grid-mismatch-banner"`로 vitest 검증.

##### REQ-CN-015 (Event-Driven): FilterBar appliedContext chip

**WHEN** FilterBar가 렌더링되고 `screenState.appliedContext?.label`이 non-null/non-empty string이면, **THEN** the system **shall** render a dismissible chip with the label and an ✕ close button. ✕ 클릭 시 `clearAppliedContext()`를 호출하여 appliedContext를 null로 리셋하고 ChartGrid 렌더 결과를 비운다 (`applyFilters(DEFAULT_SCREEN_REQUEST)` 호출). `data-testid="filter-bar-applied-context-chip"`로 vitest 검증.

##### REQ-CN-016 (Event-Driven): AppContent cross-tab useEffect 확장

**WHEN** `crossTabParams.stockCodes`가 변경되면, **THEN** AppContent useEffect는 다음을 순서대로 수행한다:

1. `applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes: crossTabParams.stockCodes })` (기존 동작 — REQ-CN-C-001 보존)
2. `setAppliedContext({ source, label, requestedCodeCount })` 호출. source/label 결정 로직:
   - `crossTabParams.themeName` 존재 → `source='theme'`, `label='테마: <themeName> (<N>)'`
   - `crossTabParams.searchLabel` 존재 → `source='search'`, `label=<searchLabel>`
   - 둘 다 없음 (StockExplorer 동선) → `source='explorer'`, `label='시총 상위'` 또는 기존 default

기존 StockExplorer→Grid 동선의 동작은 회귀하지 않는다 (REQ-CN-C-002).

### 3.2 Non-Functional Requirements

##### REQ-CN-NF-001 (Ubiquitous): stock master 응답 시간

The system **shall** respond to `GET /api/stocks/master` within 500ms (P95) under normal SQLite load. ~2,500 row 단순 SELECT 쿼리 기준.

##### REQ-CN-NF-002 (Ubiquitous): 검색 매칭 성능

The system **shall** complete `matchesQuery` filtering across ~2,500 stock master items within 30ms per keystroke (인메모리 substring + 초성 매칭). 입력 디바운스 150ms로 렌더 부담 감소.

##### REQ-CN-NF-003 (Ubiquitous): payload 크기

The system **shall** keep `GET /api/stocks/master` response payload at gzip ≤ 50KB (raw ~80KB) for ~2,500 rows. `Cache-Control: max-age=300` + ETag로 브라우저 캐시도 활용.

##### REQ-CN-NF-004 (Ubiquitous): ThemeAnalysis 캐시 호환

The system **shall** preserve compatibility with SPEC-NAVER-THEME-CONSOLIDATED REQ-NT3-015 localStorage 캐시 (`theme-analysis-cache-{mode}`). Feature A 액션은 cached `selectedTheme.stocks` 데이터를 read-only로 활용하며 캐시 schema는 변경하지 않는다.

##### REQ-CN-NF-005 (Ubiquitous): 검색 매칭 정확도 (LESSON-NTC-001 라이브 검증 의무)

The system **shall** ensure that for any stock name / 6-digit code / 초성 input typed by the user, the intended match appears within the top 3 results of the dropdown. 본 요구사항은 fixture 단위 테스트로 검증되며, 추가로 manual browser 시나리오 (§verification D, E, F)에서 라이브 검증 후 잠근다 (LESSON-NTC-001 라이브 UX 검증 패턴).

### 3.3 Constraints

##### REQ-CN-C-001 (Ubiquitous): 기존 cross-tab 인프라 무수정

The system **shall not** modify the public API of `useTab().navigateToTab`, `useScreen().applyFilters`, or AppContent의 기존 useEffect logic. 변경은 **확장만 허용** (extension only) — 기존 동작 회귀 0건.

##### REQ-CN-C-002 (Ubiquitous): 기존 4탭 + ThemeAnalysis 회귀 0

The system **shall not** modify the behavior of Market Overview / Sector Analysis / Stock Explorer / Chart Grid (기본 동작) / ThemeAnalysis tabs. SPEC-NAVER-THEME-CONSOLIDATED REQ-NT-C-002 계승.

##### REQ-CN-C-003 (Ubiquitous): 신규 의존성 금지

The system **shall not** introduce new pip or npm dependencies. SPEC-NAVER-THEME-CONSOLIDATED REQ-NT-C-003 계승. Hangul 매칭은 자체 ~25줄 TypeScript 유틸로 구현.

##### REQ-CN-C-004 (Ubiquitous): bare except 금지

The system **shall not** use bare `except:` or `except Exception:` clauses in new backend code. 특정 예외 타입만 catch:

- `sqlite3.OperationalError` (DB 무결성)
- `sqlite3.DatabaseError` (DB connect 실패)
- `KeyError`, `pydantic.ValidationError`

SPEC-NAVER-THEME-CONSOLIDATED REQ-NT-C-005 계승.

##### REQ-CN-C-005 (Unwanted): stock_meta DB 무수정

**IF** the system attempts INSERT, UPDATE, DELETE, CREATE, DROP, ALTER on `stock_meta` or any other table in `stock_data_daily.db`, **THEN** the operation **shall** be rejected. 강제 메커니즘: 신규 service에서 `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` URI 모드 사용. SPEC-NAVER-THEME-CONSOLIDATED REQ-NT-C-001 계승.

##### REQ-CN-C-006 (Ubiquitous): default 모드 가시성 (LESSON-NTC-003)

The system **shall** treat incoming `stockCodes` (from any source — theme, search, explorer) as the sole filter — always applied as `{ ...DEFAULT_SCREEN_REQUEST, codes: stockCodes }`. 활성 필터(market_cap_min 등) 보존 시 사용자가 의도하지 않은 종목 누락이 발생하므로 **명시적 full reset이 default**임을 모든 동선에서 일관되게 유지한다 (LESSON-NTC-003 default 모드 가시성 적용).

##### REQ-CN-C-007 (Ubiquitous): stock master 자동 만료 없음 (LESSON-NTC-005)

The system **shall not** apply automatic TTL or background refresh to the stock master cache. 캐시 무효화는 DB의 `stock_meta.last_updated` 변경에 의한 ETag 갱신으로만 발생한다. SPEC-NAVER-THEME-CONSOLIDATED v1.0.5 frontend localStorage 캐시 + Chart Grid DB 수동 업데이트 모델과 일관 (LESSON-NTC-005 사용 패턴 → 캐시 모델 적용).

### 3.4 Routing

##### REQ-CN-R-001 (Ubiquitous): /api/stocks/master 신규 등록

The system **shall** register `stocks_router` from `backend/routers/stocks.py` in `backend/main.py` via `app.include_router(stocks_router)`. import 1줄 + include_router 1줄, 그 외 main.py 변경 금지.

##### REQ-CN-R-002 (Ubiquitous): 기존 라우트 무수정

The system **shall not** modify the function signatures, response shapes, decorators, or paths of `/api/screen`, `/api/themes/v2/snapshot`, `/api/themes/v2/quick`, `/api/themes/snapshot`, `/api/themes/quick`, `/api/stage/overview`, `/api/sectors`. 라우트 추가는 신규 router (`/api/stocks/master`) 한 건만 허용.

---

## 4. Acceptance Criteria

총 26 AC. 분류: A 동선 6, B 동선 8, 공통 4, 백엔드 4, 회귀 4.

| AC | 검증 대상 REQ | 시나리오 요약 | 통과 기준 |
| --- | --- | --- | --- |
| **A 동선** | | | |
| AC-A1 | REQ-CN-005 | ThemeDetailPanel 헤더 버튼 라이브 라벨 | "차트 그리드로 보기 (12종목)" 등 N종목 라벨이 selectedTheme.stocks.length로 라이브 표시 |
| AC-A2 | REQ-CN-007 / REQ-CN-008 | 헤더 버튼 클릭 → ChartGrid 진입 | activeTab='chart-grid'로 전환, 해당 테마 stock_code 목록(stock_meta 교집합)으로 ChartGrid 채워짐 |
| AC-A3 | REQ-CN-006 / REQ-CN-007 | ThemeRankingTable 행별 chip 클릭 | "차트" chip 클릭 시 상세 패널이 열리지 않고 그 테마 stocks만으로 ChartGrid가 채워짐 (event.stopPropagation 검증) |
| AC-A4 | REQ-CN-015 / REQ-CN-008 | FilterBar chip 표시 + ✕ reset | 이동 후 `테마: <name> (N) ✕` chip 표시. ✕ 클릭 시 ChartGrid 비워지고 appliedContext null |
| AC-A5 | REQ-CN-C-006 / REQ-CN-016 | full reset 검증 | 이동 후 FilterBar의 다른 필터(market_cap_min 등)는 모두 DEFAULT 상태 (DEFAULT_SCREEN_REQUEST 일치) |
| AC-A6 | REQ-CN-014 | mismatch banner | 요청 종목 수 > 렌더 종목 수일 때 그리드 상단에 비개발자 친화 문구 banner 표시, `stock_meta` 등 내부 용어 미노출 |
| **B 동선** | | | |
| AC-B1 | REQ-CN-010 | stock master 1회 fetch | 첫 검색 입력 focus 시 `/api/stocks/master` 1회 호출, 같은 세션 내 재호출 0 (DevTools Network 검증) |
| AC-B2 | REQ-CN-012 (score 2) | 부분 일치 매칭 | "삼성전" 입력 시 dropdown 상단에 삼성전자 노출 |
| AC-B3 | REQ-CN-012 (score 4) | 코드 prefix 매칭 | "005" 입력 시 005930 등 코드 prefix 매치가 우선 순위로 노출 |
| AC-B4 | REQ-CN-011 / REQ-CN-012 (score 1) | 초성 매칭 | "ㅅㅅㅈㅈ" 입력 시 삼성전자 dropdown 상단 노출 |
| AC-B5 | REQ-CN-013 / REQ-CN-C-006 | 항목 선택 → ChartGrid 렌더 + full reset | 선택 시 ChartGrid가 해당 종목 단일 chart로 채워지고, FilterBar 다른 필터는 모두 DEFAULT 상태 |
| AC-B6 | REQ-CN-015 | 검색 후 chip 표시 | 선택 후 FilterBar에 `종목: <name> <code> ✕` chip 표시 |
| AC-B7 | REQ-CN-012 (0건) | 0건 처리 | 매칭 결과 0건이면 dropdown에 "검색 결과 없음" 안내 (D-6 사전 잠금) |
| AC-B8 | REQ-CN-004 | 503 처리 | `/api/stocks/master`가 503 응답 시 search 입력은 disabled 상태, hover 시 "DB 업데이트가 필요합니다" tooltip 노출 (D-7 사전 잠금) |
| **공통** | | | |
| AC-C1 | REQ-CN-014 | mismatch banner — 비개발자 친화 문구 | banner 텍스트에 "stock_meta", "DB schema" 등 내부 용어 미노출, "상장폐지 / 신규상장 / 메타 미반영" 사용자 친화 문구 사용 |
| AC-C2 | REQ-CN-015 | chip dismiss → reset | ✕ 클릭 시 appliedContext=null, applyFilters(DEFAULT_SCREEN_REQUEST), ChartGrid 빈 상태로 복귀 |
| AC-C3 | REQ-CN-008 / REQ-CN-016 | appliedContext clear (자연 흐름) | 사용자가 FilterBar에서 다른 필터 액션 수행 시 appliedContext는 보존되거나 명시적으로 reset (구현 정책 §5 D-2 참조) |
| AC-C4 | REQ-CN-C-002 | cross-tab 회귀 0 | StockExplorer→Grid (시총 사진), SectorAnalysis→StockExplorer 동선 모두 SPEC 적용 후 정상 동작 |
| **백엔드** | | | |
| AC-S1 | REQ-CN-001 / REQ-CN-002 | /api/stocks/master 200 응답 | 정상 stock_meta 보유 DB에 대해 200 + `{ stocks: [...], generated_at: <ISO-8601> }` 반환, name IS NOT NULL ORDER BY name 정렬 |
| AC-S2 | REQ-CN-004 | /api/stocks/master 503 응답 | stock_meta 부재 시 503 + `{"detail": "stock_meta_not_ready"}` 반환 |
| AC-S3 | REQ-CN-003 | ETag 헤더 | 응답 헤더에 `ETag: <max-last-updated>` + `Cache-Control: max-age=300` 포함 |
| AC-S4 | REQ-CN-002 | 정렬 검증 | 응답 stocks 배열이 name ascending 정렬, name이 NULL인 row 미포함 |
| **회귀** | | | |
| AC-R1 | REQ-CN-C-002 / SPEC-NAVER-THEME-CONSOLIDATED 25 AC | 선행 SPEC 25 AC PASS | SPEC-NAVER-THEME-CONSOLIDATED v1.0.0의 AC-01~AC-25 모두 PASS 유지 (V1 51 단위 + V2 24+ + frontend baseline) |
| AC-R2 | REQ-CN-C-001 | StockExplorer→Grid 동선 정상 | 시총 상위 사진 클릭 → ChartGrid 진입 동선이 SPEC 적용 후 정상 작동 |
| AC-R3 | REQ-CN-C-002 | SectorAnalysis→StockExplorer 정상 | 섹터 카드 클릭 → StockExplorer 종목 리스트 진입 동선이 SPEC 적용 후 정상 작동 |
| AC-R4 | REQ-CN-NF-004 / REQ-NT3-015 | ThemeAnalysis localStorage 캐시 정상 | `theme-analysis-cache-full` / `theme-analysis-cache-quick` 캐시 hit/miss 동작이 SPEC 적용 후 정상 작동 |

총 26개 AC. 자세한 Given-When-Then 시나리오는 `acceptance.md` 참조.

---

## 5. Decisions (사용자 사전 잠금 사항)

본 SPEC에서 plan 파일과 사용자 승인을 통해 사전 잠금된 결정 사항. 향후 변경 시 amendment HISTORY 추가 필요.

- **D-1 (A 액션 위치)**: ThemeDetailPanel 헤더 메인 버튼 + ThemeRankingTable 행별 chip **둘 다** 제공. 이유: 상세 패널을 열지 않은 상태에서도 한 번의 클릭으로 ChartGrid 진입을 원하는 행별 chip 사용자 패턴과, 상세 정보를 본 후 종목 비교를 원하는 메인 버튼 패턴 모두를 만족한다. 멀티테마 종목 위젯 진입점은 v1 제외 (단일 종목 단위는 Feature B 검색이 자연스럽다).
- **D-2 (필터 reset 정책)**: full reset — `{ ...DEFAULT_SCREEN_REQUEST, codes: stockCodes }`. 활성 필터(market_cap_min=1000억 등) 보존 시 소형 테마 종목이 묵묵히 누락되어 사용자가 명시적으로 제기한 우려("필터 때문에 종목 리스트에 없는 경우")가 정확히 재현된다. StockExplorer→ChartGrid의 기존 동작과 일관 (LESSON-NTC-003 default 모드 가시성).
- **D-3 (누락 안내 문구)**: 비개발자 친화 — "요청한 X종목 중 Y종목 표시 — Z종목은 현재 DB에서 조회되지 않는 종목입니다 (상장폐지 / 신규상장 / 메타 미반영)." `stock_meta`, `DB schema`, `JOIN failure` 등 내부 용어 노출 금지.
- **D-4 (검색 매칭 scope)**: 종목명 부분 일치 + 코드 prefix + 초성. 정렬 우선순위: (1) 코드 정확 prefix > (2) 종목명 정확 prefix > (3) 종목명 substring > (4) 초성. 섹터/제품 키워드 검색은 v2.
- **D-5 (stock master 데이터 소스)**: 신규 `GET /api/stocks/master`. 응답 페이로드 raw ~80KB / gzip ~30KB, 한 세션 1회 lazy fetch. 대안 검토 결과 (frontend hardcode JSON / 기존 endpoint piggyback / GraphQL) 모두 trade-off가 더 큼.
- **D-6 (검색 결과 0건 처리)**: dropdown에 "검색 결과 없음" 안내. 입력 disabled 또는 dropdown 미렌더 옵션은 사용자 의도 파악을 어렵게 하므로 거부.
- **D-7 (stock master 503 처리)**: search 입력 disabled + hover tooltip "DB 업데이트가 필요합니다". V1 자동 폴백 / 환경변수 토글 / silent retry 모두 거부 (SPEC-NAVER-THEME-CONSOLIDATED D-1 처리 패턴 계승).
- **D-8 (URL deep linking 분리)**: `?tab=chart-grid&code=005930` 등 URL 기반 deep linking은 본 SPEC 제외, 별도 SPEC-TAB-URL-001로 분리. 기존 SPA tab toggle 모델 변경 필요 시 SPA routing 재설계와 함께 진행.

---

## 6. Implementation Reference (구현 참조)

### 6.1 Feature A 변경 매트릭스 + REQ 매핑

| 파일 | 변경 유형 | 핵심 변경 | 매핑 REQ |
| --- | --- | --- | --- |
| `frontend/src/types/market.ts` | EDIT | `CrossTabParams.themeName?: string` 추가 | REQ-CN-007 |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | EDIT | 헤더에 "차트 그리드로 보기 (N종목)" 버튼 + onClick → navigateToTab | REQ-CN-005, REQ-CN-007 |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | EDIT | 각 행 끝 셀에 "차트" chip + onClick → navigateToTab (event.stopPropagation) | REQ-CN-006, REQ-CN-007 |
| `frontend/src/AppContent.tsx` | EDIT | 기존 useEffect 확장 — `themeName` & `requestedCodeCount` 보존을 ScreenContext.appliedContext로 위임 | REQ-CN-008, REQ-CN-016 |
| `frontend/src/contexts/ScreenContext.tsx` | EDIT | `appliedContext` state 신설 (source/label/requestedCodeCount) + setter/clear | REQ-CN-008, REQ-CN-015 |
| `frontend/src/components/ChartGrid/ChartGrid.tsx` | EDIT | mismatch banner 렌더링 (requestedCodeCount > flatStocks.length일 때) | REQ-CN-014 |
| `frontend/src/components/FilterBar/FilterBar.tsx` | EDIT | `appliedContext.label` chip 렌더링 (✕로 reset) | REQ-CN-015 |
| `frontend/src/components/ThemeAnalysis/__tests__/ThemeDetailPanel.test.tsx` | EDIT | 버튼 클릭 시 navigateToTab 호출 검증, N종목 라벨 검증 | AC-A1, AC-A2 |
| `frontend/src/components/ThemeAnalysis/__tests__/ThemeRankingTable.test.tsx` | EDIT | 행별 chip 클릭 시 해당 테마 stocks만 전달 검증, event.stopPropagation 검증 | AC-A3 |

### 6.2 Feature B 변경 매트릭스 + REQ 매핑

| 파일 | 변경 유형 | 핵심 변경 | 매핑 REQ |
| --- | --- | --- | --- |
| `backend/routers/stocks.py` | NEW | `GET /api/stocks/master` 라우트 | REQ-CN-001, REQ-CN-003, REQ-CN-004 |
| `backend/services/stocks_master_service.py` | NEW | `list_stock_master(daily_db_path)` 서비스 함수 | REQ-CN-002, REQ-CN-C-005 |
| `backend/main.py` | EDIT | `stocks_router` 등록 (1 import + 1 include_router) | REQ-CN-R-001 |
| `backend/tests/test_stocks_master.py` | NEW | 200/503 응답, 정렬, 정상 row count 테스트 | AC-S1~S4 |
| `frontend/src/api/stocks.ts` | NEW | `fetchStockMaster()` axios 호출 + 503 처리 | REQ-CN-010, AC-B8 |
| `frontend/src/hooks/useStockMaster.ts` | NEW | module-level cached promise + retry 1회 + lazy fetch | REQ-CN-010 |
| `frontend/src/utils/hangul.ts` | NEW | `extractInitialConsonants` + `matchesQuery` 매칭 점수 함수 | REQ-CN-011, REQ-CN-012 |
| `frontend/src/utils/__tests__/hangul.test.ts` | NEW | 가→ㄱ, 한→ㅎ, A→A, 1→1 등 단위 테스트 | REQ-CN-011 |
| `frontend/src/components/ChartGrid/StockSearchBox.tsx` | NEW | 입력 + dropdown 컴포넌트 (debounce 150ms) | REQ-CN-009, REQ-CN-012, REQ-CN-013 |
| `frontend/src/components/ChartGrid/__tests__/StockSearchBox.test.tsx` | NEW | "삼성"/"005"/"ㅅㅅ"/0건/onSelect 검증 | AC-B2, AC-B3, AC-B4, AC-B7 |
| `frontend/src/components/ChartGrid/ChartGrid.tsx` | EDIT (Feature A와 함께) | StockSearchBox mount + onSelect 시 navigateToTab | REQ-CN-009, REQ-CN-013 |
| `frontend/src/types/market.ts` | EDIT (Feature A와 함께) | `CrossTabParams.searchLabel?: string` 추가 | REQ-CN-013 |

### 6.3 재사용할 기존 자산 (변경 금지)

- `useTab().navigateToTab(tab, params)` — `frontend/src/contexts/TabContext.tsx:23-26` (REQ-CN-C-001)
- `useScreen().applyFilters(filters)` — `frontend/src/contexts/ScreenContext.tsx:25` (REQ-CN-C-001)
- `DEFAULT_SCREEN_REQUEST` — `frontend/src/types/filter.ts` (REQ-CN-C-006)
- AppContent의 cross-tab effect — `frontend/src/AppContent.tsx:21~` (확장만 허용, 핵심 분기 보존)
- StockExplorer:80의 navigateToTab 호출 — Feature A/B와 동일 패턴 유지 (REQ-CN-C-002)

### 6.4 신규 타입 정의

- `CrossTabParams` (frontend/src/types/market.ts):
  - `themeName?: string` 추가 (Feature A)
  - `searchLabel?: string` 추가 (Feature B)
  - `stockCodes`는 기존 그대로 유지
- `ScreenContext` state 추가:
  - `appliedContext: { source: 'theme' | 'search' | 'explorer' | 'filter'; label?: string; requestedCodeCount?: number } | null`
  - `setAppliedContext`, `clearAppliedContext` 액션
- 신규 frontend 타입 (api/stocks.ts):
  - `interface StockMasterItem { code: string; name: string; market: string; }`
  - `interface StockMasterResponse { stocks: StockMasterItem[]; generated_at: string; }`
- 신규 backend Pydantic 모델 (`backend/routers/stocks.py`):
  - `class StockMasterItem(BaseModel)` with code/name/market
  - `class StockMasterResponse(BaseModel)` with stocks/generated_at
- `ScreenRequest`는 변경 없음.

---

## 7. Exclusions (별도 SPEC / v2)

### 7.1 별도 SPEC에서 처리

- **URL 기반 deep linking** (`?tab=chart-grid&code=005930` 등) — 별도 SPEC-TAB-URL-001로 분리 (D-8 사전 잠금). 기존 SPA tab toggle 모델 변경 필요.
- **모바일 UX** (검색창 터치 keyboard, theme 헤더 버튼 hover 대체 등) — 데스크탑 우선, SPEC-NAVER-THEME-003 D-2 패턴 계승.

### 7.2 v2 candidate

- **검색 history / 최근 검색** (recent searches dropdown).
- **종목 다중 선택 검색** (v1 = 단일 종목 jump). 멀티 선택 후 한 번에 ChartGrid 추가는 v2.
- **섹터/제품/테마 키워드 검색** ("반도체", "AI" 등 keyword → matching themes).
- **서버 측 fuzzy 매칭** — 초성/오타 보정은 클라이언트 전용으로 한정. 추후 ranking 향상 필요 시 검토.
- **멀티테마 종목 위젯 → ChartGrid 진입점** (단일 종목 단위는 Feature B 검색으로 충분).

### 7.3 영구 제외

- **백엔드 in-memory 장시간 TTL 캐시** — 자동 만료 없음 정책(LESSON-NTC-005) 유지 (REQ-CN-C-007).
- **DB INSERT/UPDATE/DELETE/CREATE/DROP/ALTER** (REQ-CN-C-005).
- **신규 pip / npm 의존성 추가** (REQ-CN-C-003).
- **기존 cross-tab 인프라 (`useTab`, `useScreen`, navigateToTab) 핵심 API 변경** (REQ-CN-C-001).
- **Hangul 매칭 라이브러리 도입** (`hangul-js`, `es-hangul` 등) — 자체 ~25줄 TS로 충분.

---

## 8. References

### 8.1 본 SPEC 동반 문서

- `research.md` — Phase 1 코드베이스 탐사 결과 (ChartGrid / ThemeAnalysis / cross-tab / stock_meta / 매칭 정책)
- `plan.md` — 구현 로드맵 + 파일별 변경 매트릭스 + 시퀀싱 + 롤백 전략
- `acceptance.md` — 26개 AC의 Given-When-Then 시나리오 + 통과 기준 + 라이브 검증 의무

### 8.2 외부 참조

- 사용자 승인된 plan: `/Users/byunjungwon/.claude/plans/swirling-napping-canyon.md`
- 선행 SPEC: `.moai/specs/SPEC-NAVER-THEME-CONSOLIDATED/spec.md` v1.0.0
- 시리즈 회고: `.moai/specs/SPEC-NAVER-THEME-CONSOLIDATED/retrospective.md`
- 시리즈 교훈: `.moai/specs/SPEC-NAVER-THEME-CONSOLIDATED/lessons.md` (LESSON-NTC-001~006)
- 프로젝트 메모리 lessons.md: `~/.claude/projects/-Users-byunjungwon-Dev-my-project-01-my-chart/memory/lessons.md` (#1~#6)

### 8.3 lesson 적용 매핑

| Lesson | 본 SPEC 적용 위치 |
| --- | --- |
| LESSON-NTC-001 (라이브 UX 검증) | REQ-CN-NF-005 + AC-B2/B3/B4 manual 시나리오 + AC-A6 banner 라이브 검증 |
| LESSON-NTC-002 (시각 우선순위) | §1.5 데이터 흐름 + REQ-CN-009 (검색창 툴바 좌측), REQ-CN-014 (banner 그리드 상단), REQ-CN-015 (chip FilterBar 영역) |
| LESSON-NTC-003 (default 모드 가시성) | REQ-CN-C-006 + D-2 + AC-A5/B5 |
| LESSON-NTC-004 (stock_meta 단일 source) | REQ-CN-002 + REQ-CN-014 mismatch banner를 검증 surface로 명시 |
| LESSON-NTC-005 (사용 패턴 → 캐시 모델) | REQ-CN-C-007 + A-7/A-8 + REQ-CN-003 ETag DB-mtime 기반 |

---

Version: 1.0.0
Status: Draft
Last Updated: 2026-05-07
