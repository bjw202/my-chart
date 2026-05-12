# Research — SPEC-CHART-NAV-001 코드베이스 탐사 결과

본 문서는 SPEC-CHART-NAV-001 plan 작성 단계(Phase 1)에서 수행한 코드베이스 탐사의 결과를 보존한다. SPEC 본문(spec.md)과 구현 가이드(plan.md)의 근거가 되는 raw findings를 단일 문서로 묶어 향후 amendment 또는 후속 SPEC에서 재탐사 비용을 회피하는 것이 목적이다.

작성일: 2026-05-07
작성 단계: SPEC-CHART-NAV-001 Plan Phase Research
참조 SPEC: SPEC-NAVER-THEME-CONSOLIDATED v1.0.0

---

## §1 ChartGrid 구조

### 1.1 컴포넌트 위치 및 역할

- 진입점: `frontend/src/components/ChartGrid/ChartGrid.tsx`
- 역할: 사용자가 선택한 종목 집합(stockCodes)에 대해 가격 차트(주봉/일봉)를 grid layout으로 동시 렌더링.
- 현재 진입 동선:
  1. FilterBar 필터 적용 → POST /api/screen → 결과 종목들이 그리드에 표시.
  2. StockExplorer "시총 상위 사진" 클릭 → navigateToTab('chart-grid', { stockCodes: [...] }) → 그리드 표시.

### 1.2 state model

- 그리드의 종목 단위는 `stock.code` (6자리 zero-padded string).
- ChartGrid는 ScreenContext에서 `flatStocks: StockSummary[]`를 구독하여 렌더링.
- 페이지네이션 / 정렬 / 추가/제거는 ChartGrid 자체 state로 관리 (ScreenContext 영향 없음).

### 1.3 chart-grid-toolbar div

ChartGrid.tsx 내부에 `<div className="chart-grid-toolbar">`가 존재. 현재 우측에 정렬 버튼, 종목 수 indicator 등이 mount되어 있고 좌측은 비어 있음. **Feature B의 StockSearchBox 마운트 위치로 활용 가능** (~220px 너비 입력).

### 1.4 mismatch banner를 위한 빈 자리

ChartGrid 상단에는 현재 안내 banner / notice 영역이 별도로 없다. SPEC-CHART-NAV-001에서 신규 mismatch banner를 ChartGrid의 첫 번째 child로 conditional 렌더링하면 충돌 없이 도입 가능 (REQ-CN-014).

---

## §2 ThemeAnalysis 구조

### 2.1 ThemeStockItem 인터페이스

`frontend/src/api/themes.ts`에 정의:

```typescript
interface ThemeStockItem {
  stock_code: string;
  stock_name: string;
  inclusion_reason?: string | null;
  // ... 가격/거래량 필드
  stock_description?: string | null;  // V2 전용 (REQ-NT3-003)
}
```

stock_code는 6자리 zero-padded string. stock_meta.code와 1:1 매칭 가능.

### 2.2 ThemeDetailPanel 액션 부재

- 위치: `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx`
- 현재 헤더 영역: 테마명, theme_description 본문 박스 (REQ-NT3-009, v1.0.2 prominent), 종목 테이블.
- **헤더에 행동 가능한 버튼은 0건** — "차트 그리드로 보기" 같은 명시적 진입점 없음.
- 사용자가 테마 종목들을 한꺼번에 ChartGrid에서 보고 싶으면 stock_code를 외워두고 ChartGrid에서 다시 입력해야 하는 결함 동선.

### 2.3 ThemeRankingTable 행 클릭 핸들러

- 위치: `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx`
- 행 전체 click 핸들러가 ThemeDetailPanel 열기를 트리거.
- 행별 trailing cell은 비어 있음. **Feature A의 "차트" chip 마운트 위치로 활용 가능** (event.stopPropagation 필수 — 상세 패널이 동시에 열리지 않도록).

### 2.4 localStorage 캐시 인터페이스

SPEC-NAVER-THEME-CONSOLIDATED REQ-NT3-015에서 도입된 캐시:

- key: `theme-analysis-cache-{mode}` (mode: 'quick' | 'full')
- schema: `{ "cache_version": "v1", "saved_at": "<ISO-8601>", "data": <ThemesSnapshotResponse> }`
- 자동 만료 없음, 명시적 갱신 버튼만 invalidate.

**SPEC-CHART-NAV-001 영향**: cache는 read-only로 활용. 캐시된 응답에서 `selectedTheme.stocks.map(s => s.stock_code)`만 추출하여 navigateToTab의 stockCodes 인자로 전달. 캐시 schema 변경 0건.

---

## §3 cross-tab 인프라

### 3.1 TabContext.navigateToTab

- 위치: `frontend/src/contexts/TabContext.tsx:23-26`
- 시그니처: `navigateToTab(tab: TabId, params?: CrossTabParams)`
- 현재 동작: activeTab을 변경하고 crossTabParams state를 갱신. 기존 호출자: StockExplorer:80 (시총 사진 클릭).

### 3.2 AppContent useEffect

- 위치: `frontend/src/AppContent.tsx:21~`
- 현재 동작: `crossTabParams.stockCodes`가 변경되면 `applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes: stockCodes })` 자동 호출.
- 즉 codes만 적용되고 다른 필터(market_cap_min 등)는 reset된다 — **이미 default 모드 가시성(LESSON-NTC-003) 패턴이 구현되어 있음**.

### 3.3 CrossTabParams 타입

- 위치: `frontend/src/types/market.ts`
- 현재 필드: `stockCodes?: string[]`
- **SPEC-CHART-NAV-001 확장 대상**: `themeName?: string` (Feature A 라벨), `searchLabel?: string` (Feature B 라벨) 추가.
- 기존 stockCodes 필드 시그니처/타입 변경 0건 — extension only (REQ-CN-C-001).

### 3.4 핵심 발견: 두 기능을 같은 채널로 통합 가능

cross-tab 인프라가 이미 "stockCodes 전달 → full reset + codes 적용" 패턴을 구현하고 있으므로, Feature A (테마)와 Feature B (검색) 모두 동일한 navigateToTab 호출로 구현 가능. 새 상태 라이브러리 / 컨텍스트 도입 불필요. SPEC §1.1 핵심 발견에 반영됨.

---

## §4 backend stock_meta

### 4.1 스키마

`Output/stock_data_daily.db.stock_meta` 테이블:

- `code` TEXT PRIMARY KEY (6자리 zero-padded string)
- `name` TEXT (nullable — 신규 상장 / 매핑 미완료 종목 시 null)
- `market` TEXT ("KOSPI" | "KOSDAQ")
- `last_updated` TEXT (ISO-8601 KST)
- 기타 가격/시총 컬럼 (V1/V2 db_join에서 활용)

### 4.2 rebuild 메커니즘

stock_meta는 `backend/services/` 별도 batch script를 통해 외부 갱신. Chart Grid DB 수동 업데이트 모델(LESSON-NTC-005)과 일관 — 자동 cron / scheduler 없음, 사용자가 명시적으로 업데이트 명령 실행 시점에만 갱신.

### 4.3 active rows 추정

운영 데이터 기준 ~2,500 rows (KOSPI ~900 + KOSDAQ ~1,600). 페이로드 추정:

- raw: 2,500 × ~30 bytes (code 6 + name ~10 + market 5 + JSON overhead) ≈ 75-80 KB
- gzip: ~30 KB (한글 + 6자리 코드 패턴 압축률 양호)

REQ-CN-NF-003 (gzip ≤ 50KB) 충분히 만족.

### 4.4 503 처리 패턴

기존 `/api/screen` 엔드포인트는 stock_meta 부재 시 503 + `{"detail": "stock_meta_not_ready"}` 반환. SPEC-CHART-NAV-001 신규 `/api/stocks/master`는 동일 패턴 계승 (REQ-CN-004).

---

## §5 필터 시스템

### 5.1 ScreenRequest

- 위치: `frontend/src/types/filter.ts`
- 핵심 필드: `market_cap_min`, `market_cap_max`, `change_pct_min`, `change_pct_max`, `rs_min`, `rs_max`, `sectors`, `codes`
- `codes`가 채워지면 다른 모든 필터 무시 후 정확히 그 codes만 조회 (서버 측 SELECT WHERE code IN (...) 패턴).

### 5.2 DEFAULT_SCREEN_REQUEST

- 모든 수치 필터는 null/undefined (즉 "no filter").
- `codes: []` (빈 배열 = no codes filter).
- `{ ...DEFAULT_SCREEN_REQUEST, codes: stockCodes }` 패턴은 "다른 모든 필터 reset + codes만 적용"을 명시적으로 표현.

### 5.3 FilterBar UI

- 위치: `frontend/src/components/FilterBar/FilterBar.tsx`
- 현재 chip 영역 없음. **SPEC-CHART-NAV-001 신규 chip 마운트 위치**: 필터 슬라이더 영역 위 또는 옆 (구현 시점에 visual hierarchy 검토).

### 5.4 활성 필터로 인한 종목 누락 메커니즘

사용자가 명시적으로 제기한 우려: "필터 때문에 종목 리스트에 없는 경우". 재현 시나리오:

1. FilterBar에 market_cap_min=1조 설정.
2. 테마 분석 → 소형주 비중 높은 테마 (예: 바이오) 선택.
3. ChartGrid 진입 시 만약 "기존 필터 보존"이라면 일부 종목이 묵묵히 누락 (사용자가 알아차리지 못함).

**해결책 (REQ-CN-C-006 + REQ-CN-014)**:
- full reset으로 종목 누락 자체를 방지.
- 추가로 stock_meta에 없는 종목(상장폐지 등)은 mismatch banner로 명시적 안내.

---

## §6 종목 검색 인프라 부재

### 6.1 기존 검색 endpoint 미존재

- `/api/stocks/search` — 없음.
- `/api/stocks/by-name?q=...` — 없음.
- `/api/stocks/master` — 없음 (본 SPEC에서 신규).

### 6.2 frontend autocomplete 미존재

- `react-autosuggest` / `downshift` 등 자동완성 라이브러리 미사용.
- 글로벌 검색 헤더 미존재.
- ChartGrid / StockExplorer에 종목명 입력 필드 미존재.

### 6.3 master list endpoint 부재 → SPEC-CHART-NAV-001 신규 도입 사유

frontend 검색을 위해 stock_meta의 (code, name, market)만 가벼운 페이로드로 한 번에 받아오는 endpoint가 필요. 대안:

- (a) frontend hardcode JSON: stock master를 git-tracked JSON 파일로 ship. 거부 — DB 업데이트 시 frontend 빌드 재배포 필요, LESSON-NTC-005 수동 업데이트 모델과 충돌.
- (b) 기존 `/api/screen` piggyback: codes 파라미터를 비워 모든 종목 메타만 받기. 거부 — 응답이 가격/거래량 등 무거운 컬럼 포함, 검색용으로 과도하게 큼 (~수 MB).
- (c) **신규 `/api/stocks/master` (채택)**: 가벼운 페이로드 (code/name/market만), 명확한 단일 책임, ETag로 캐시 무효화 정확.

---

## §7 한글 매칭 정책 검토

### 7.1 initial-consonant 알고리즘

Hangul 음절 블록 (Unicode 0xAC00 ~ 0xD7A3, 11,172자)은 다음 공식으로 분해 가능:

```
syllable_index = code - 0xAC00
leading_consonant_index = syllable_index / 588   // 0..18
vowel_index = (syllable_index % 588) / 28          // 0..20
trailing_consonant_index = syllable_index % 28     // 0..27
```

leading_consonant_index를 14자 (ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ)에 매핑하면 초성 추출 완료.

표준 19자 leading consonant 중 일부는 5자 압축됨 (ㄲ→ㄱ, ㄸ→ㄷ, ㅃ→ㅂ, ㅆ→ㅅ, ㅉ→ㅈ) — 한국 금융앱 / 검색앱 표준 UX 정책. 사용자가 "ㄲ"을 입력할 일은 거의 없으며, "ㄱ"으로 입력하면 ㄲ 시작 종목도 매칭되는 것이 자연스럽다.

### 7.2 Unicode 분해

별도 NFD 분해 불필요. leading consonant index만 추출하면 됨. 비-Hangul 문자(영문, 숫자, 공백)는 그대로 통과시키면 됨.

### 7.3 라이브러리 미사용 결정

검토한 라이브러리: `hangul-js` (5KB minified), `es-hangul` (3KB minified), `korean-utils` (8KB).

- 모두 NFC/NFD 분해, 자모 분리, 종성 분해 등 풀-스펙 기능 제공.
- **본 SPEC에서 필요한 기능은 leading consonant 1개**만 필요.
- 자체 구현 ~25줄 TypeScript로 충분 + 신규 의존성 0건 (REQ-CN-C-003).
- 결정: 자체 구현. `frontend/src/utils/hangul.ts` 단일 파일로 분리.

### 7.4 매칭 정확도 검증 (LESSON-NTC-001)

fixture 단위 테스트:
- "삼성전자" → extract → "ㅅㅅㅈㅈ"
- "현대차" → extract → "ㅎㄷㅊ"
- "한화에어로스페이스" → extract → "ㅎㅎㅇㅇㄹㅅㅍㅇㅅ"
- "A주" → extract → "Aㅈ" (혼합 입력)
- "1번" → extract → "1ㅂ"

라이브 검증 (manual 시나리오, AC-B2/B3/B4): 사용자가 직접 입력 후 dropdown 상위 3건에 의도 종목 등장 확인.

---

## §8 cohabitation 정책 (선행 SPEC와의 관계)

### 8.1 SPEC-NAVER-THEME-CONSOLIDATED 무수정

본 SPEC은 SPEC-NAVER-THEME-CONSOLIDATED v1.0.0을 **read-only로 의존**한다. supersedes 관계 아님 — 두 SPEC은 cohabit한다.

- ThemeAnalysis 모듈 (`frontend/src/components/ThemeAnalysis/`)은 SPEC-NAVER-THEME-CONSOLIDATED 소관.
- 본 SPEC은 ThemeDetailPanel.tsx, ThemeRankingTable.tsx에 **버튼/chip만 추가** (extension only). 기존 props/state/렌더링 회귀 0건.
- ThemeAnalysis V2 endpoint, V2 metadata, localStorage 캐시 등 모든 기능은 SPEC-NAVER-THEME-CONSOLIDATED REQ를 그대로 만족 유지 (REQ-CN-C-002, AC-R1).

### 8.2 회귀 게이트 보존

- V1 단위 테스트 51개 PASS 유지.
- V2 단위 테스트 24+ PASS 유지.
- frontend vitest baseline diff 0 (ChartGrid 1 fail pre-existing 외 신규 fail 0).

### 8.3 LESSON 적용 패턴

| Lesson | SPEC-NAVER-THEME-CONSOLIDATED 출처 | SPEC-CHART-NAV-001 적용 |
| --- | --- | --- |
| LESSON-NTC-001 | v1.0.1 hover-only 발견성 부족 → 본문 노출 amendment 회고 | REQ-CN-NF-005 라이브 검증 의무 + AC manual 시나리오 |
| LESSON-NTC-002 | v1.0.2 시각 우선순위 (theme_description > stock list > [주도주 제거]) | §1.5 데이터 흐름의 visual hierarchy (검색창 좌측 / banner 상단 / chip FilterBar) |
| LESSON-NTC-003 | v1.0.3 default 'full' 모드 결정 (사용자가 default에서 description 보이도록) | REQ-CN-C-006 default = full reset 보장 + D-2 |
| LESSON-NTC-004 | v1.0.4 strong_themes_df theme_description 머지 누락 (single source 일관성) | REQ-CN-002 stock_meta = 단일 source + REQ-CN-014 banner로 누락 가시화 |
| LESSON-NTC-005 | v1.0.5 frontend localStorage 캐시 (단일 사용자 + 수동 업데이트 모델) | REQ-CN-C-007 자동 만료 없음 + REQ-CN-003 ETag DB-mtime |
| LESSON-NTC-006 (있다면) | (lessons.md 참조) | 본 SPEC 작성 시 추가 검토 |

---

## §9 탐사 결론 요약

1. **두 기능은 같은 cross-tab 채널로 통합 가능** — 신규 상태 라이브러리 도입 0건.
2. **stock master endpoint는 신규 도입이 최선** — 기존 endpoint piggyback / hardcode JSON / 라이브러리 도입은 모두 trade-off가 더 큼.
3. **Hangul 매칭은 자체 ~25줄 유틸로 충분** — 신규 npm 의존성 0건, REQ-CN-C-003 만족.
4. **mismatch banner는 LESSON-NTC-001/-004의 라이브 검증 surface 자체** — 누락된 종목을 사용자에게 즉시 노출하여 default 모드 가시성을 강화한다.
5. **stock master 캐시는 LESSON-NTC-005 단일 사용자 모델과 일관** — 자동 만료 없음, ETag는 DB의 last_updated 기반.
6. **회귀 영향 0건** — SPEC-NAVER-THEME-CONSOLIDATED 25 AC 모두 PASS 유지, 기존 4탭 무수정.

본 탐사 결과를 기반으로 spec.md 본문, plan.md 구현 가이드, acceptance.md 시나리오를 작성한다.
