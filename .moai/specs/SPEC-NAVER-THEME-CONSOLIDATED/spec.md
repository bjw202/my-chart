---
id: SPEC-NAVER-THEME-CONSOLIDATED
title: 네이버 금융 테마 분석 모듈 — 통합 SPEC (V1 + V2 backend + V2 frontend)
status: Implemented
version: 1.0.0
owner: bjw2002
created: 2026-05-07
updated: 2026-05-07
supersedes: [SPEC-NAVER-THEME-001, SPEC-NAVER-THEME-002, SPEC-NAVER-THEME-003]
---

# SPEC-NAVER-THEME-CONSOLIDATED: 네이버 금융 테마 분석 모듈 (통합)

## 메타데이터

| 항목 | 값 |
| --- | --- |
| SPEC ID | SPEC-NAVER-THEME-CONSOLIDATED |
| 제목 | Naver Finance Theme Analysis Module — Consolidated (V1 + V2 backend + V2 frontend) |
| 생성일 | 2026-05-07 |
| 상태 | Implemented |
| 우선순위 | High |
| 담당 | expert-backend, expert-frontend, expert-testing |
| 의존 SPEC | (supersedes 관계로 SPEC-NAVER-THEME-001/002/003 흡수) |
| Lifecycle | spec-anchored |
| 버전 | 1.0.0 |

---

## HISTORY

- 2026-05-07 v1.0.0: Consolidation of SPEC-NAVER-THEME-001 (V1, 12d81b1), SPEC-NAVER-THEME-002 (V2 backend, 888e2eb~b1c24eb), SPEC-NAVER-THEME-003 (V2 frontend, 6284280 + amendments v1.0.1~v1.0.5 through 2026-05-07 4e75f14). 시리즈 회고는 retrospective.md, 다음 SPEC 체크리스트는 lessons.md 참조. 원본 SPEC 001/002/003 spec.md는 supersedes 관계로 보존되며 본 통합 SPEC이 현재 시스템의 단일 source of truth.

---

## 1. Environment (환경)

### 1.1 시스템 개요

네이버 금융 테마 분석 모듈은 두 개의 데이터 경로를 cohabit한다.

- **V1 (legacy, rollback path)**: `backend/services/naver_theme/`가 데스크탑 정적 HTML(`https://finance.naver.com/sise/theme.naver`)을 EUC-KR로 크롤링하여 5종 DataFrame + metadata를 반환한다.
- **V2 (현재 main 경로)**: `backend/services/naver_theme_v2/`가 모바일 비공식 JSON API(`https://m.stock.naver.com/front-api/...`)를 호출하여 V1 schema의 superset(테마/종목 설명 컬럼 추가)을 반환한다.

프론트엔드는 V2 endpoint를 main으로 호출하며, V1 endpoint는 cohabitation Option γ(SPEC-002 잠금)에 따라 byte-identical 보존되어 즉시 rollback 가능한 상태로 유지된다.

| 항목 | V1 | V2 |
| --- | --- | --- |
| 모듈 경로 | `backend/services/naver_theme/` | `backend/services/naver_theme_v2/` |
| 데이터 출처 | finance.naver.com 데스크탑 정적 HTML | m.stock.naver.com `/front-api/...` JSON |
| 인코딩 | EUC-KR (강제) | UTF-8 (default) |
| 단일 진입점 | `from backend.services.naver_theme import collect_and_analyze` | `from backend.services.naver_theme_v2 import collect_and_analyze_v2` |
| 반환 타입 | `ThemeAnalysisResult` (5종 DataFrame + metadata) | 동일 `ThemeAnalysisResult` (V1 schema 재사용) |
| 실행 모델 | stateless (호출 1회당 1 사이클) | stateless (호출 1회당 1 사이클) |
| FastAPI 라우트 | `/api/themes/snapshot`, `/api/themes/quick` | `/api/themes/v2/snapshot`, `/api/themes/v2/quick` |
| 외부 호출 (snapshot) | 약 27회 | 약 27회 |
| 외부 호출 (quick) | 약 7회 | 약 6회 |

### 1.2 모듈 구조

**Backend V1**:

| 파일 | 역할 |
| --- | --- |
| `service.py` | 단일 진입점 (`collect_and_analyze`), 오케스트레이션 |
| `crawler.py` | HTTP 호출, Session 싱글톤 + Retry |
| `parser.py` | HTML → dict/list 변환 (EUC-KR 강제) |
| `analyzer.py` | DataFrame 가공, z-score 기반 점수 계산 |
| `db_join.py` | `stock_meta.market_cap` JOIN (read-only) |
| `schemas.py` | Pydantic 모델 (`ThemeAnalysisResult` 직렬화) |
| `config.py` | URL, 헤더, sleep, 가중치 상수 |

**Backend V2** (V1 sibling, 무수정 import):

| 파일 | 역할 |
| --- | --- |
| `__init__.py` | `collect_and_analyze_v2`, `ThemeAnalysisResult` 노출 |
| `service.py` | 진입점 (오케스트레이션), `theme_description` post-loop 머지 (REQ-NT3-014) |
| `crawler.py` | HTTP 호출 (requests + JSON), 단일 thread |
| `parser.py` | JSON dict → 정규화 dict/list, `inclusion_reason ← item.description` 매핑 |
| `config.py` | endpoint URL, 모바일 UA, sleep 등 상수 |
| `analyzer.py` | (재사용) V1 analyzer import |
| `db_join.py` | (재사용) V1 db_join import (optional fallback only) |
| `schemas.py` | (재사용) V1 ThemeAnalysisResult import |

**Frontend V2 채택**:

| 파일 | 역할 |
| --- | --- |
| `frontend/src/api/themes.ts` | V2 endpoint URL swap + `theme_description?` / `stock_description?` optional 타입 확장 |
| `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx` | mode state default `'full'`, localStorage 캐시, `🔄 갱신` 버튼, 503/timeout 에러 메시지 + retry, quick 모드 advisory |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | theme_name 셀에 `title={theme.theme_description ?? undefined}` (D-2) |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | theme_description 본문 박스 prominent 노출, stock inclusion_reason 본문 노출, "주도주" 섹션 제거 |

### 1.3 외부 의존성 (기설치, 신규 추가 없음)

**Backend** (V1 + V2 공통):
- `requests >= 2.28` (HTTP)
- `pandas >= 2.0` (DataFrame)
- `numpy >= 1.24` (z-score)
- `pydantic >= 2.0` (응답 schema)
- `fastapi >= 0.115` (라우터)
- `beautifulsoup4 >= 4.12`, `lxml >= 4.9` (V1 HTML 파서, V2 미사용)

**Frontend**:
- `react ^19`, `axios`, `vitest`, `@testing-library/react`

신규 의존성 0건. native HTML `title` 속성으로 hover Tooltip 구현하여 Radix Tooltip 등 추가 라이브러리 거부.

### 1.4 영향 범위 (애드온 경계)

- 신규 디렉토리: `backend/services/naver_theme/`, `backend/services/naver_theme_v2/`, `frontend/src/components/ThemeAnalysis/`, `frontend/src/api/themes.ts`
- 수정된 기존 파일 (V1 ship 시점 ≤ 10줄 합계):
  - `backend/main.py` — 라우터 등록 2줄
  - `backend/routers/themes.py` — V1 routes + V2 routes (V1 byte-identical 보존)
  - `frontend/src/types/market.ts` — TabId union에 `'theme-analysis'` 추가 (1줄)
  - `frontend/src/components/TabNavigation/TabNavigation.tsx` — TABS 배열에 1행 추가
  - `frontend/src/AppContent.tsx` — 조건부 렌더링 1 case 추가
- 기존 4탭 (Market Overview / Sector Analysis / Stock Explorer / Chart Grid) 무수정
- Master DB (`stock_data_daily.db`) SELECT only

### 1.5 데이터 흐름 도식 (themes_df ↔ strong_themes_df)

V2 backend의 service.py 내부 데이터 흐름은 다음과 같다 (REQ-NT3-014 머지 후 v1.0.4 최종 상태):

```
list endpoint (sectors/all)
        ↓
  themes_df (theme_description=null)
        ↓
  build_strong_themes(themes_df, top_n)
        ↓
  strong_themes_df (theme_description=null, this is the bug surface in v1.0.4)
        ↓
  for each theme in strong_themes_df:
        detail endpoint (sector/item/list)
              ↓
        themes_df.loc[idx, "theme_description"] = sectorDescription   ← detail merge
        stocks_df += parsed stocks (with stock_description, inclusion_reason)
        ↓
  desc_map = themes_df.set_index("theme_id")["theme_description"].to_dict()
  strong_themes_df["theme_description"] = strong_themes_df["theme_id"].map(desc_map)   ← REQ-NT3-014 post-loop merge
        ↓
  return ThemeAnalysisResult(...)
```

이 도식은 v1.0.4 amendment에서 발견된 결함의 핵심이다. detail 머지가 `themes_df`에만 적용되어 frontend의 `data?.strong_themes ?? data?.themes` 패턴에서 description=null이 노출되는 문제를 post-loop 머지(REQ-NT3-014)로 해결했다.

---

## 2. Assumptions (가정)

### 2.1 기술적 가정

- [A-1] V1: 네이버 금융 desktop 페이지는 EUC-KR 인코딩이며, Content-Type charset이 누락되어도 `Response.encoding = 'euc-kr'`을 명시적으로 강제하면 정상 파싱 가능
- [A-2] V2: 네이버 모바일 비공식 endpoint는 익명 호출 가능 (Cookie/Authentication 불필요), 응답 Content-Type `application/json; charset=utf-8`
- [A-3] V2: pageSize 상한 50 (서버 검증)
- [A-4] V1+V2: `Output/stock_data_daily.db.stock_meta`는 `code (TEXT)`, `market_cap (INTEGER, 원 단위)` 컬럼을 보유하며, 외부 갱신 메커니즘에 의해 최신 상태로 유지됨
- [A-5] V1: 테마 상세 페이지에는 PER/ROE 컬럼이 노출되지 않음 → NaN 고정
- [A-6] V2 list 응답의 `sectorDescription`은 항상 null. detail 응답에서만 채워짐 → `theme_description` 가시성은 detail 호출에 의존 (v1.0.3 학습)
- [A-7] V2 endpoint URL은 1주~1개월 단위로 변경될 수 있음 (sentry release `stock-web@2026.04.30~` 활발) → `config.py` 상수 일괄 교체로 대응

### 2.2 비즈니스 가정

- [A-8] 호출자(라우터 레벨)에서 backend 캐싱은 하지 않음. 캐시는 frontend localStorage로 위임 (v1.0.5 결정)
- [A-9] 시가총액 보강은 V1: DB JOIN read-only, V2: detail endpoint `marketValue` 직접 노출 + db_join optional fallback
- [A-10] 사용자는 Market Overview / Sector Analysis / Stock Explorer / Chart Grid 4탭의 기능 회귀를 허용하지 않음 (애드온 무결성)
- [A-11] **사용 패턴**: 단일 사용자 사용 시나리오 + Chart Grid DB 수동 업데이트 패턴과 일관된 "수동 갱신" 모델 (v1.0.5 학습). 자동 만료/refresh 없음, 사용자가 명시적으로 갱신 버튼 클릭 시점에만 새 fetch.

### 2.3 테스트 전략 가정

- [A-12] 파서·분석기 단위 테스트는 fixture 기반으로 네트워크 없이 실행 가능
- [A-13] 라이브 크롤링 테스트는 `@pytest.mark.live` 또는 `@pytest.mark.slow` 마커로 격리
- [A-14] frontend vitest baseline은 ChartGrid 1 fail pre-existing (V2 무관). 신규 fail 0 유지

---

## 3. Requirements (EARS 형식)

### 3.1 Functional Requirements

#### Backend V1 (`backend/services/naver_theme/`)

##### REQ-NT-001 (Ubiquitous): 단일 진입점 노출

The system **shall** expose `collect_and_analyze(top_n_themes: int = 20, leaders_per_theme: int = 3, skip_details: bool = False, theme_filter: list[str] | None = None) -> ThemeAnalysisResult` from `backend.services.naver_theme`.

##### REQ-NT-002 (Event-Driven): 테마 목록 수집

**WHEN** `collect_and_analyze`가 호출되면, **THEN** 시스템은 `https://finance.naver.com/sise/theme.naver?&page={n}`의 모든 페이지를 순회하여 `themes_df`를 생성한다 (컬럼: `theme_id`, `theme_name`, `change_pct`, `change_pct_3d`, `up_count`, `flat_count`, `down_count`, `top_stocks_preview`, `collected_at`).

##### REQ-NT-003 (Ubiquitous): 페이지네이션 자동 탐지

The system **shall** detect the last page dynamically from the first page's pagination block. 페이지 수 하드코딩 금지. `last_page = 1` 초기값을 그대로 사용하여 1회만 도는 루프 버그를 방지한다.

##### REQ-NT-004 (State-Driven): skip_details 빠른 모드

**WHILE** `skip_details == True`, **the system shall** skip theme detail crawling and return empty DataFrames for `stocks_df`, `leaders_df`, `multi_theme_stocks_df`. `themes_df`, `strong_themes_df`만 채워진 상태로 반환, 응답 시간 ≤ 10초.

##### REQ-NT-005 (Event-Driven): 강세 테마 추출

**WHEN** `themes_df`가 생성되면, **THEN** 시스템은 `change_pct` 내림차순 → 상위 `top_n_themes`개로 `strong_themes_df`를 생성한다. 추가 컬럼: `momentum_score = change_pct * 0.6 + change_pct_3d * 0.4`, `breadth_ratio = up_count / (up_count + flat_count + down_count)` (분모 0이면 0).

##### REQ-NT-006 (Event-Driven): 테마 상세 수집

**WHEN** `skip_details == False`이고 `strong_themes_df`가 비어있지 않으면, **THEN** 시스템은 각 강세 테마에 대해 `https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}`를 fetch하여 `stocks_df`를 생성한다 (컬럼: `theme_id`, `theme_name`, `stock_code`, `stock_name`, `inclusion_reason`, `price`, `change`, `change_pct`, `volume`, `trade_value`, `market_cap`, `per`, `roe`, `collected_at`).

##### REQ-NT-007 (Ubiquitous): 시가총액 DB JOIN 보강 (READ-ONLY)

The system **shall** enrich `stocks_df.market_cap` by SELECT-only JOIN against `stock_meta` in `Output/stock_data_daily.db`. SQLite URI `mode=ro` 강제 (`sqlite3.connect(f"file:{path}?mode=ro", uri=True)`). DB에 없는 코드는 `market_cap = NaN`.

##### REQ-NT-008 (Ubiquitous): 편입사유 컬럼 보존

The system **shall** capture `inclusion_reason` from the second cell (`td[1]`) of each stock row in the theme detail page and persist it as a column of `stocks_df`. 빈 문자열 또는 미존재 시 빈 string fallback.

##### REQ-NT-009 (Event-Driven): 주도주 산출

**WHEN** `stocks_df`가 비어있지 않으면, **THEN** 시스템은 테마별로 z-score 기반 `leader_score`를 계산하여 `leaders_df`를 생성한다. `leader_score = z(change_pct)*0.40 + z(volume)*0.30 + z(market_cap)*0.20 + z(trade_value)*0.10`. `std == 0`이면 `z(x) = 0`. 테마당 상위 `leaders_per_theme`개, `rank` 1..K 부여.

##### REQ-NT-010 (Event-Driven): 멀티테마 종목 추출

**WHEN** `stocks_df`가 비어있지 않으면, **THEN** 시스템은 `stock_code` 기준 group by로 `multi_theme_stocks_df`를 생성한다 (컬럼: `stock_code`, `stock_name`, `theme_count`, `theme_names`, `avg_change_pct`). `theme_count >= 2`인 종목만 포함, `theme_names`는 `sorted(set(x))`로 dedup.

##### REQ-NT-011 (Ubiquitous): metadata 반환

The system **shall** return a `metadata` dict containing `collected_at` (KST ISO-8601), `theme_count`, `stock_count`, `elapsed_sec`, `errors`. `errors: list[{"theme_id": int | None, "stage": "list" | "detail", "reason": str}]`.

#### Backend V2 (`backend/services/naver_theme_v2/`)

##### REQ-NT2-001 (Ubiquitous): V2 단일 진입점

The system **shall** expose `collect_and_analyze_v2(top_n_themes: int = 20, leaders_per_theme: int = 3, skip_details: bool = False) -> ThemeAnalysisResult` from `backend.services.naver_theme_v2`. V1과 동일한 시그니처 패턴.

##### REQ-NT2-002 (Event-Driven): V2 테마 목록 수집

**WHEN** `collect_and_analyze_v2()`가 호출되면, **THEN** 시스템은 `https://m.stock.naver.com/front-api/stock/sectors/all`에 `sectorType=theme&businessDayCategory=daily&sectorSortType=CHANGE_RATE&nationType=domestic&pageSize=50`로 요청을 issue하고 `page=1..N` (응답 `result.sectors[]` 길이 < pageSize까지) paginate한다.

##### REQ-NT2-003 (Event-Driven): V2 테마 상세 수집

**WHEN** snapshot 모드(`skip_details=False`)에서 강세 테마 top-N이 결정되면, **THEN** 시스템은 각 테마에 대해 `https://m.stock.naver.com/front-api/domestic/sector/item/list`에 `sectorType=theme&sectorCode={theme_id}&sectorSortType=CHANGE_RATE&page=1&pageSize=50`로 요청하여 `sectorDescription`, `result.items[].description`, `result.items[].marketValue`를 retrieve한다.

##### REQ-NT2-004 (Ubiquitous): theme_description 신규 컬럼

The system **shall** populate `themes_df['theme_description']` (dtype: object/nullable string) from detail endpoint response `result.sectorDescription`. detail endpoint가 `sectorDescription=null`을 반환하면 `theme_description=NaN` (예외 발생 금지).

##### REQ-NT2-005 (Ubiquitous): stock_description 신규 컬럼

The system **shall** populate `stocks_df['stock_description']` (dtype: object/nullable string) from `result.items[].description`. key 부재 또는 value null 시 `stock_description=NaN`. 동일 source가 V2 parser 정책에 의해 `inclusion_reason` 컬럼에도 매핑되어, frontend가 V1 컬럼을 그대로 사용하면 자동으로 V2 description이 노출된다.

##### REQ-NT2-006 (Ubiquitous): market_cap 직접 노출

The system **shall** populate `stocks_df['market_cap']` (단위: 원, int dtype) from `result.items[].marketValue` directly. **WHERE** `marketValue`가 missing/null이면 `backend.services.naver_theme.db_join.join_market_cap()`(read-only, `mode=ro`)로 optional fallback 가능 (필수 아님).

##### REQ-NT2-008 (Ubiquitous): ThemeAnalysisResult shape 보존

The system **shall** return a `ThemeAnalysisResult` instance preserving all V1 columns (`themes_df`, `stocks_df`, `strong_themes_df`, `leaders_df`, `multi_theme_stocks_df`, `metadata`) with identical names and dtypes. V2가 추가하는 신규 컬럼 (`theme_description`, `stock_description`)은 additional columns only — V1 컬럼 rename/drop/dtype 변경 금지.

#### Frontend V2 채택 (`frontend/src/components/ThemeAnalysis/`)

##### REQ-NT3-001 (Ubiquitous): V2 endpoint URL swap

The system **shall** update `frontend/src/api/themes.ts` so that `fetchThemesSnapshot()` calls `/themes/v2/snapshot` and `fetchThemesQuick()` calls `/themes/v2/quick`, replacing V1 endpoint URLs.

##### REQ-NT3-002 (Ubiquitous): TypeScript 타입 확장 — theme_description

The system **shall** extend `ThemeItem` interface in `frontend/src/api/themes.ts` to include optional field `theme_description?: string | null`.

##### REQ-NT3-003 (Ubiquitous): TypeScript 타입 확장 — stock_description (forward-compat)

The system **shall** extend `ThemeStockItem` interface in `frontend/src/api/themes.ts` to include optional field `stock_description?: string | null`.

##### REQ-NT3-004 (Event-Driven): theme_description Tooltip 표시 (D-2)

**WHEN** ThemeRankingTable이 렌더링되고 `theme.theme_description`이 non-null/non-empty string이면, **THEN** 시스템은 `theme_description`을 native HTML `title` 속성을 통해 theme_name 셀의 hover tooltip으로 노출한다. null/undefined/empty 시 `title` 속성 미렌더링 (D-4 hidden).

##### REQ-NT3-005 (Ubiquitous): V2 backend metadata에 V1 alias 4 필드 추가

The system **shall** populate `result.metadata` in `collect_and_analyze_v2()` with V1-compatible alias fields (`collected_at`, `theme_count`, `stock_count`, `elapsed_sec`) in addition to existing fields (`data_source`, `generated_at`, `total_themes_seen`, `errors`). All existing V2 metadata fields preserved (additive only).

##### REQ-NT3-006 (Ubiquitous): `_empty_result` 헬퍼에도 V1 alias 적용

The system **shall** populate the same V1 alias fields (`collected_at`, `theme_count=0`, `stock_count=0`, `elapsed_sec=0.0`) in the `_empty_result()` helper of `backend/services/naver_theme_v2/service.py`.

##### REQ-NT3-007 (Event-Driven): V2 endpoint 503/timeout 처리 (D-1)

**WHEN** V2 endpoint가 HTTP 5xx, network error, 또는 timeout으로 실패하면, **THEN** 시스템은 ThemeAnalysis 화면에 다음 UI를 표시한다:
- 사용자 친화적 에러 메시지 (예: "테마 데이터를 가져오지 못했습니다. 다시 시도해 주세요.")
- Retry 버튼: 클릭 시 현재 mode(`quick` or `full`)로 fetch 재시작

The system **shall not** automatically fall back to V1 endpoint.

##### REQ-NT3-008 (Event-Driven): inclusion_reason 자리 V2 description 자동 노출 (D-3)

The system **shall** preserve the existing `title={stock.inclusion_reason}` rendering in `ThemeDetailPanel.tsx`. **WHEN** V2 endpoint가 호출되고 V2 parser가 `inclusion_reason`과 `stock_description`을 동일 source(`item.description`)로 채운 응답을 반환하면, 시스템은 V2의 종목별 편입설명을 기존 inclusion_reason 자리에 자동으로 노출한다.

##### REQ-NT3-009 (Event-Driven): 테마 설명 본문 prominent 노출 (v1.0.1+v1.0.2 통합 최종)

**WHEN** ThemeDetailPanel이 렌더링되고 `theme.theme_description`이 non-null/non-empty string이면, **THEN** 시스템은 description을 테마 제목 직하단에 prominent body 컨테이너로 렌더링한다. 최종 styling:
- font-size: 13px
- color: var(--text-primary)
- line-height: 1.65
- padding: 12px 14px
- border-radius: 8px
- border-left: 4px solid var(--positive)

null/undefined/empty 시 body 컨테이너 미렌더링 (D-4 hidden).

`data-testid="theme-description-body"`로 vitest 검증.

##### REQ-NT3-010 (Event-Driven): 종목 편입설명 본문 노출

**WHEN** ThemeDetailPanel이 종목 테이블 행을 렌더링하고 해당 stock의 `inclusion_reason`이 non-null/non-empty string이면, **THEN** 시스템은 inclusion_reason을 종목 행 직하단에 visible body container로 렌더링한다 (hover tooltip 외에 본문으로도 노출, 중복 허용). null/undefined/empty 시 body 컨테이너 미렌더링.

기존 `title` 속성 보존 (hover tooltip 호환성). `data-testid="stock-inclusion-reason-body"`로 vitest 검증.

##### REQ-NT3-011 (Ubiquitous): 주도주 섹션 제거

The system **shall not** render the "주도주" (leader) section in `ThemeDetailPanel.tsx`, including section header and leader cards, regardless of whether `leaders` prop contains items. `leaders` prop은 호출부 호환을 위해 optional로 보존하되 컴포넌트 내부에서 미사용.

##### REQ-NT3-012 (Ubiquitous): 기본 조회 모드 'full'

The system **shall** initialize `ThemeAnalysis.tsx`의 `mode` state with default value `'full'` (snapshot endpoint), not `'quick'`. backend list 응답에 `sectorDescription`이 항상 null이라 quick 모드 사용자는 description을 영원히 볼 수 없으므로 default 진입에서 description이 즉시 보이도록 'full'을 기본값으로 한다.

##### REQ-NT3-013 (Event-Driven): 빠른 조회 모드 advisory

**WHEN** ThemeAnalysis 컴포넌트가 정상 데이터를 표시 중(`!loading && !error && data`)이고 `mode === 'quick'`이면, **THEN** 시스템은 ThemeDetailPanel 영역 위에 회색 advisory 박스를 렌더링한다: "빠른 조회 모드는 테마 설명과 종목 편입설명을 포함하지 않습니다. 자세한 정보는 위의 [전체 조회]를 클릭해 주세요 (약 30초 소요)."

`mode === 'full'` 시 advisory 미렌더링. `data-testid="theme-quick-advisory"`로 vitest 검증.

##### REQ-NT3-014 (Ubiquitous): strong_themes_df theme_description 머지

The system **shall** populate `theme_description` field in `strong_themes_df` (backend `service.py` output) by mapping from `themes_df` after detail endpoint loop completes. Mapping uses `theme_id` as the key:

```python
desc_map = themes_df.set_index("theme_id")["theme_description"].to_dict()
strong_themes_df["theme_description"] = strong_themes_df["theme_id"].map(desc_map)
```

Skip condition: `skip_details=True`일 때는 양 dataframe 모두 description=None이라 머지 불필요.

##### REQ-NT3-015 (Ubiquitous): localStorage 응답 캐시

The system **shall** persist successful V2 endpoint responses to `localStorage` under keys `theme-analysis-cache-quick` and `theme-analysis-cache-full`, scoped per `mode`.

**WHEN** `ThemeAnalysis` mounts or `mode` changes, **THEN** 시스템은 해당 mode의 `localStorage` entry를 우선 읽는다. 유효 캐시(matching `cache_version: 'v1'`) 존재 시 즉시 `setData(cached.data)` + fetch skip. 캐시 부재 또는 `cache_version` 불일치 시 normal fetch flow 실행.

**WHEN** fetch 성공 시 응답을 다음 schema로 localStorage에 write:
```json
{ "cache_version": "v1", "saved_at": "<ISO-8601>", "data": <ThemesSnapshotResponse> }
```

자동 만료(TTL) 없음. 캐시 무효화는 사용자가 갱신 버튼(REQ-NT3-016) 클릭 시점에만 발생.

##### REQ-NT3-016 (Event-Driven): 명시적 "🔄 갱신" 버튼

The system **shall** render a refresh button in the ThemeAnalysis toolbar (within `.sector-analysis-toolbar`), positioned next to the period toggle. label: `🔄 갱신`, attribute: `data-testid="theme-refresh-button"`.

**WHEN** 사용자가 갱신 버튼을 클릭하면, **THEN** 시스템은 다음을 순서대로 실행한다:
1. 현재 mode의 localStorage entry 제거 (`localStorage.removeItem('theme-analysis-cache-' + mode)`)
2. `loading=true` set, `error` clear
3. `setRetryNonce(n => n + 1)`로 새 fetch trigger (기존 retry 메커니즘 재사용)

새 fetch 성공 시 REQ-NT3-015에 따라 localStorage 갱신. 실패 시 REQ-NT3-007 에러 UI 표시 + 캐시는 cleared 상태 유지 (stale fallback 금지).

### 3.2 Non-Functional Requirements

##### REQ-NT-NF-001 (Ubiquitous): 매너 호출

The system **shall** sleep `>= 0.7s` between HTTP requests, use a single thread.
- V1 UA: `KR-Stock-Screener/1.0 (naver_theme_analysis)` (브라우저 위장 금지)
- V2 UA: `Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1`
- V2 Referer: `https://m.stock.naver.com/domestic/home/theme/daily`
- V2 Accept: `application/json`

##### REQ-NT-NF-002 (Ubiquitous): 인코딩 처리

V1: The system **shall** force-set `requests.Response.encoding = 'euc-kr'` before parsing HTML body.

V2: The system **shall** parse responses as `application/json; charset=utf-8`, verify Content-Type contains `application/json` substring before parsing. V2는 EUC-KR 강제 미적용.

##### REQ-NT-NF-003 (Event-Driven): 재시도 + 부분 실패 허용

**WHEN** an HTTP request fails (5xx, Timeout), **THEN** the system **shall** retry once after sleeping ≥ 1s, on persistent failure log to `metadata.errors[]` and continue processing remaining items.

V2 error stages:
- `'list_fetch'`, `'detail_fetch'`, `'schema_validation'`, `'content_type'`, `'json_decode'`, `'endpoint_drift'`

타임아웃: 10초/요청 (재시도 포함). 부분 실패 시 다른 테마/종목 계속 처리.

##### REQ-NT-NF-004 (Ubiquitous): 응답 시간

- snapshot (skip_details=False): ≤ 30초
- quick (skip_details=True): ≤ 10초

##### REQ-NT-NF-005 (Ubiquitous): 데이터 품질

| 항목 | 기준 |
| --- | --- |
| 한글 깨짐 | 없음 (V1 EUC-KR 강제 후, V2 UTF-8) |
| 숫자 단위 | 금액·거래대금·시가총액 모두 원 단위 통일 |
| NaN 처리 | PER/ROE/누락 market_cap/null description 시 NaN |
| 타임스탬프 | ISO-8601 KST |

##### REQ-NT-NF-006 (Ubiquitous): endpoint URL 격리

The system **shall** declare endpoint URLs as module-level constants in `config.py`. inline hardcode 금지. (V2 sentry release 활발 risk 대응)

V2 상수:
- `NAVER_MOBILE_BASE_URL = "https://m.stock.naver.com"`
- `NAVER_MOBILE_FRONT_API_PREFIX = "/front-api"`
- `LIST_ENDPOINT_PATH = "/stock/sectors/all"`
- `DETAIL_ENDPOINT_PATH = "/domestic/sector/item/list"`

##### REQ-NT-NF-007 (Ubiquitous): null/undefined description 렌더링 정책 (D-4)

**WHEN** `theme.theme_description` or `stock.inclusion_reason` is `null`, `undefined`, or empty string, **THEN** the system **shall** omit the related body container and `title` attribute entirely. Placeholder 텍스트("—", "(설명 없음)" 등) 금지.

##### REQ-NT-NF-008 (Ubiquitous): frontend vitest baseline 보존

The system **shall** ensure that adding new V2 endpoint mock tests does not introduce new test failures beyond the pre-existing ChartGrid baseline failure (1 fail).

### 3.3 Constraints

##### REQ-NT-C-001 (Unwanted): DB 무수정

**IF** the system attempts INSERT, UPDATE, DELETE, CREATE, DROP, ALTER on any SQLite DB, **THEN** the operation **shall** be rejected. 강제 메커니즘: read-only URI 모드 (`mode=ro`).

##### REQ-NT-C-002 (Ubiquitous): 기존 4탭 회귀 없음

The system **shall not** modify behavior of Market Overview / Sector Analysis / Stock Explorer / Chart Grid tabs. V1 ship 시점 변경되는 기존 파일 ≤ 10줄 합계 (surgical mod).

##### REQ-NT-C-003 (Ubiquitous): 신규 의존성 금지

The system **shall not** introduce new pip or npm dependencies. Backend: `requests`, `pandas`, `numpy`, `pydantic`, `fastapi`. Frontend: `react`, `axios`, `vitest`, `@testing-library/react`. Radix Tooltip 등 추가 라이브러리 거부 — native HTML `title` 속성으로 충분.

##### REQ-NT-C-004 (Ubiquitous): Stateless backend

The system **shall not** persist any data to disk or in-process global state across calls in backend. 캐시는 frontend localStorage(REQ-NT3-015)로 위임.

##### REQ-NT-C-005 (Ubiquitous): bare except 금지

The system **shall not** use bare `except:` or `except Exception:` clauses in any backend module. 특정 예외 타입만 catch:
- `requests.RequestException`, `requests.Timeout`
- `json.JSONDecodeError`
- `KeyError`, `pydantic.ValidationError`, `ValueError`(controlled cases only)

##### REQ-NT-C-006 (Unwanted): V2 endpoint failure 시 V1 자동 폴백 금지

The system **shall not** automatically fall back to V1 endpoints when V2 endpoint requests fail. 사용자가 명시적으로 retry 버튼 클릭 시에만 재시도. V1 endpoint는 cohabitation으로 보존되지만 자동 호출 금지.

##### REQ-NT-C-007 (Ubiquitous): V1 routes byte-identical 보존

The system **shall not** modify the function signatures, response shapes, decorators, or paths of V1 routes `GET /api/themes/snapshot` and `GET /api/themes/quick`. V2 routes는 additional `@router.get(...)` decorator로만 추가.

##### REQ-NT-C-008 (Ubiquitous): V1 backend 모듈 무수정

The system **shall not** modify any file in `backend/services/naver_theme/` (V1 backend modules). V1 51 단위 테스트 회귀 0건 유지.

### 3.4 Routing

##### REQ-NT-R-001 (Ubiquitous): V1 endpoints 등록 유지

The system **shall** preserve V1 endpoints `GET /api/themes/snapshot` and `GET /api/themes/quick` registered in `backend/routers/themes.py` as cohabitation rollback path.

##### REQ-NT-R-002 (Ubiquitous): V2 endpoints 메인 경로

The system **shall** preserve V2 endpoints `GET /api/themes/v2/snapshot` and `GET /api/themes/v2/quick` as the main path served to frontend, with V1-compatible metadata structure (REQ-NT3-005 alias 포함).

---

## 4. Acceptance Criteria

본 통합 SPEC은 V1 14 + V2 ~15 + V2 frontend 24를 dedup하여 최종 25 AC로 수렴한다. 세부 시나리오는 원본 SPEC들의 acceptance.md를 참조 (supersedes 관계로 보존).

| AC | 검증 대상 REQ | 시나리오 요약 |
| --- | --- | --- |
| AC-01 | REQ-NT-001/REQ-NT2-001 | V1·V2 단일 진입점 import 1줄로 동작 (`from backend.services.naver_theme[_v2] import collect_and_analyze[_v2]`) |
| AC-02 | REQ-NT-NF-002 | V1: EUC-KR 강제 후 한글 깨짐 0. V2: UTF-8 파싱 정상, Content-Type 미스매치 시 errors[]에 `'content_type'` stage 기록 |
| AC-03 | REQ-NT-NF-005 | market_cap·trade_value·marketValue 모두 원 단위 통일, list 응답 `marketCap`(백만원)은 V2에서 사용 안 함 |
| AC-04 | REQ-NT-009 | leader_score 가중치 (0.40 change_pct + 0.30 volume + 0.20 market_cap + 0.10 trade_value) 정확, std=0 시 0 처리 |
| AC-05 | REQ-NT-003 / REQ-NT2-002 | V1·V2 페이지네이션 자동 탐지 (V1: pagination 블록, V2: pageSize 미만 시 종료) |
| AC-06 | REQ-NT-NF-001 | 호출 간 sleep ≥ 0.7s 실측, 단일 thread 검증 |
| AC-07 | REQ-NT-NF-003 | 부분 실패 시 errors[]에 stage별 기록, 잔여 항목 계속 처리, 5xx/Timeout 시 1회 retry |
| AC-08 | REQ-NT-004 / REQ-NT-NF-004 | skip_details=True 시 V1 ≤ 10s, V2 ≤ 10s, snapshot ≤ 30s |
| AC-09 | (테스트 전략) | V1: 단위 테스트 51개, 커버리지 99%. V2: 단위 테스트 ≥ 24개 + 라이브 1개 PASS, 커버리지 ≥ 85% |
| AC-10 | REQ-NT-001 / REQ-NT2-008 | 외부 import 1줄 사용 가능 + ThemeAnalysisResult shape V1 = V2 superset (V1 컬럼 byte-identical 보존) |
| AC-11 | REQ-NT-C-001 / REQ-NT-C-008 | DB 무수정 (`stock_data_daily.db` mtime 무변경), V1 backend 모듈 무수정 |
| AC-12 | REQ-NT-C-002 | 기존 4탭 회귀 없음 (V1 ship 시점 ≤ 10줄 합계 surgical mod 검증) |
| AC-13 | REQ-NT-008 / REQ-NT2-005 | inclusion_reason 컬럼 fixture 검증 + V2 parser `inclusion_reason ← item.description` 매핑 검증 |
| AC-14 | REQ-NT-C-007 | V1 routes byte-identical 보존 (decorator/시그니처/응답 shape 무변경) |
| AC-15 | REQ-NT-C-005 | bare except 0건 (grep `except:`, `except Exception:` 0 결과) |
| AC-16 | REQ-NT2-004 / REQ-NT3-002 | theme_description 컬럼 V2 응답에 존재 + frontend ThemeItem optional 타입 확장 |
| AC-17 | REQ-NT3-004 | ThemeRankingTable에서 theme_name 셀의 `title` 속성이 description 존재 시 렌더, null 시 미렌더 (D-2 + D-4) |
| AC-18 | REQ-NT3-005 / REQ-NT3-006 | V2 metadata에 V1 alias 4 필드 (`collected_at`, `theme_count`, `stock_count`, `elapsed_sec`) 추가, `_empty_result`에도 동일 적용 |
| AC-19 | REQ-NT3-007 / REQ-NT3-C-006 | V2 503/timeout 시 에러 메시지 + retry 버튼 표시, V1 자동 폴백 미발생 |
| AC-20 | REQ-NT3-009 / REQ-NT3-010 | ThemeDetailPanel에 theme_description 본문 박스 (font 13px, text-primary, padding 12/14, border-radius 8, border-left 4px positive) + stock inclusion_reason 본문 노출, null 시 hidden |
| AC-21 | REQ-NT3-011 | "주도주" 섹션 미렌더 (vitest에서 텍스트 부재 + leader-inclusion-reason-body 부재 검증) |
| AC-22 | REQ-NT3-012 / REQ-NT3-013 | default mode='full', 사용자가 'quick' 토글 시 `data-testid="theme-quick-advisory"` 박스 렌더 |
| AC-23 | REQ-NT3-014 | snapshot (full) 응답의 `strong_themes` 배열에 theme_description이 detail 결과로 채워짐 (themes_df ↔ strong_themes_df 일관성) |
| AC-24 | REQ-NT3-015 | localStorage `theme-analysis-cache-{mode}` 캐시 hit 시 즉시 setData + fetch skip, miss 시 normal flow, cache_version 'v1' 검증 |
| AC-25 | REQ-NT3-016 | `🔄 갱신` 버튼(`data-testid="theme-refresh-button"`) 클릭 시 localStorage 제거 + 강제 fetch + 캐시 갱신 |

추가 회귀 게이트:
- V1 단위 테스트 51개 그대로 PASS (REQ-NT-C-008 검증)
- V2 단위 테스트 ≥ 24개 그대로 PASS (REQ-NT3-C-003 metadata additive 검증)
- frontend vitest baseline diff 0 (ChartGrid 1 fail pre-existing 외 신규 fail 0)
- evaluator-active PASS: Func 100 / Sec 90 / Craft 92 / Cons 95 (v1.0.0 ship 시점 측정값)

---

## 5. Decisions (결정 사항 누적)

본 시리즈에서 사전 잠금된 결정 사항 (annotation cycle 또는 amendment에서 사용자 승인):

- **D-1 (V2 endpoint failure 처리)**: 에러 메시지 + 명시적 retry 버튼. V1 자동 폴백 금지, 환경변수 토글 금지, race-based dual-fetch 금지. UI 분기는 정상/에러 2개로 제한.
- **D-2 (theme_name hover Tooltip)**: native HTML `title` 속성. Radix Tooltip / custom 컴포넌트 도입 거부 (의존성 추가 회피).
- **D-3 (inclusion_reason 자리 재사용)**: V2 parser가 `inclusion_reason ← item.description`으로 매핑하므로 frontend 컴포넌트 변경 0으로 자동 노출. v1.0.1에서 hover-only 발견성 부족이 확인되어 본문 표시(D-3 옵션 A 변형)로 보강됨.
- **D-4 (null hidden)**: null/undefined/empty description은 placeholder 없이 hidden. "—" 또는 "(설명 없음)" 노이즈 회피.
- **D-5 (시각 우선순위, v1.0.2)**: theme_description > stock list > [주도주 섹션 제거]. 네이버 모바일 UX의 "테마 설명 우선" prominence를 따른다.
- **D-6 (default 모드 'full', v1.0.3)**: backend list 응답이 항상 `sectorDescription=null`이므로 default 진입에서 description이 보이도록 'full' 모드를 기본값으로 한다. 'quick' 토글 시 advisory 표시.
- **D-7 (캐시 모델, v1.0.5)**: frontend localStorage + 명시적 갱신 버튼. backend stateless 유지, 자동 TTL 없음. Chart Grid DB 수동 업데이트 패턴과 일관된 단일 사용자 모델.

Cohabitation 정책:

- **Option γ (locked)**: V1 endpoint·모듈 byte-identical 보존, V2를 신규 sibling으로 추가. 즉시 rollback 경로 항상 열려있음.

---

## 6. Implementation Reference (현재 ship된 상태)

| 영역 | commit / 위치 | 비고 |
| --- | --- | --- |
| V1 backend | commit `12d81b1` (2026-05-01) | 14 AC PASS, 단위 51, 커버리지 99% |
| V2 backend | commits `888e2eb`~`b1c24eb` (2026-05-01) | Cohabitation Option γ ship |
| V2 frontend (v1.0.0 ship) | commit `6284280` (2026-05-06) | Func 100/Sec 90/Craft 92/Cons 95, 16 files +3050/-19 |
| v1.0.1 amendment | (ThemeDetailPanel 본문 박스 도입) | hover-only → 본문 표시 reverse |
| v1.0.2 amendment | commit `3ecd97c` (2026-05-06) | 주도주 섹션 제거 + theme_description prominent 강화 |
| v1.0.3 amendment | commit `2a43dc3` (2026-05-06) | default 'full' 모드 + 빠른 조회 advisory |
| v1.0.4 amendment | commit `07de0bd` (2026-05-06) | strong_themes_df theme_description post-loop 머지 |
| v1.0.5 amendment | commits `4e75f14`, `4c2d7bb` (2026-05-07) | localStorage 캐시 + 🔄 갱신 버튼 |

소스 위치 요약:
- `backend/services/naver_theme/` (V1, 7 파일)
- `backend/services/naver_theme_v2/` (V2, 5 신규 + V1 import 3 재사용)
- `backend/routers/themes.py` (V1+V2 라우트 동시 등록)
- `frontend/src/api/themes.ts` (V2 endpoint URL + optional 타입)
- `frontend/src/components/ThemeAnalysis/` (4 컴포넌트 + tests)

---

## 7. Exclusions (What NOT to Build)

본 통합 SPEC 범위에서 **명시적으로 제외**되는 항목:

### 7.1 별도 SPEC에서 처리

- `GET /api/themes/by-stock/{code}` reverse index (종목 → 테마)
- `frontend/src/components/MarketOverview/HotThemesStrip.tsx` (Market Overview 핫 테마 스트립)
- `frontend/src/components/StockList/ThemeChips.tsx` (Stock Explorer/Chart Grid 테마 칩)
- `CrossTabParams.themeId` / `themeName` 추가 (cross-tab 통신)
- Mobile hover 대체 UX (mobile touch 환경에서 theme_description 표시)
- `stock_description` 별도 컬럼/표시 (D-3 옵션 A — 마지막 컬럼 추가)
- theme_description 길이 제한 (line-clamp, truncation 정책)
- V1↔V2 toggle UI 또는 환경변수 기반 swap (`VITE_USE_V2_API`)
- frontend i18n (다국어) 지원

### 7.2 V2.1 이연

- Sparkline `mini_chart_points` 컬럼 (detail 응답의 `miniImageChartUrl` PNG 파싱 필요)
- 종목 로고 이미지 (별도 endpoint 필요)
- 테마 즐겨찾기 기능 (mobile 페이지 별 아이콘, 인증 필요)

### 7.3 V3 이후

- 일별 시계열 누적 (parquet/sqlite 저장)
- 시계열 차트 (`ThemeBumpChart`, `ThemeBubbleChart`)
- "어제 대비 부상한 테마" Banner / Rising Themes 알고리즘
- AI 코멘트 자동 생성

### 7.4 영구 제외

- DB INSERT/UPDATE/DELETE/CREATE/DROP/ALTER (REQ-NT-C-001)
- 신규 pip/npm 의존성 추가 (REQ-NT-C-003)
- 본 모듈 backend 내부 캐싱·DB 저장 (REQ-NT-C-004)
- 시각화 (프론트엔드 책임)
- 알림 (Slack, 이메일)
- 백테스트
- 스케줄링 (cron, APScheduler)
- 인증·권한
- 외부 API 호출 (FnGuide, 시총 추가 크롤링 등 — DB JOIN으로 충당)
- PER/ROE 추가 크롤링 (V1: 페이지 미노출, NaN 고정)
- 기존 4탭 (Market Overview / Sector Analysis / Stock Explorer / Chart Grid) 동작 변경
- V1 endpoint dead-code cleanup (rollback path 보존, REQ-NT-R-001)
- V1 backend 모듈 수정 또는 삭제 (REQ-NT-C-008, Cohabitation Option γ)

---

## 8. Glossary

| 용어 | 의미 |
| --- | --- |
| V1 | `backend/services/naver_theme/`, desktop HTML 크롤링, EUC-KR (SPEC-001) |
| V2 | `backend/services/naver_theme_v2/`, mobile JSON API, UTF-8 (SPEC-002) |
| sector | 모바일 API에서 V1의 "테마"에 해당. `sectorType=theme` 필터 |
| sectorCode | 모바일 API의 테마 ID (string-of-int). V2 parser에서 `int(sectorCode)`로 정규화하여 V1 schema의 `theme_id` (int)와 호환 |
| sectorDescription | 모바일 API detail 응답의 테마 설명 → V2 `theme_description` 컬럼 (list 응답에서는 항상 null) |
| description (per item) | 모바일 API의 종목별 편입 설명 → V2 `stock_description` + `inclusion_reason` 동일 source 매핑 |
| marketValue | 모바일 detail 응답의 시가총액 (단위: 원) → V2 `market_cap` 직접 |
| marketCap (list) | 모바일 list 응답의 시가총액 (단위: 백만원) → V2에서 미사용 (혼선 방지) |
| front-api | 모바일 사이트의 Fastify-based BFF prefix `/front-api/` |
| Option γ | Cohabitation 전략. V1 byte-identical 보존, V2 신규 sibling 추가 |
| D-1~D-7 | 사용자 결정 사항 (annotation cycle 또는 amendment에서 사전 잠금) |
| Tooltip | native HTML `title` 속성 기반 hover 도움말. Radix/custom 컴포넌트 미사용 |
| metadata V1 alias | V2 metadata에 추가되는 V1-호환 4 필드 (`collected_at`, `theme_count`, `stock_count`, `elapsed_sec`) |

---

## 9. References

### 9.1 본 통합 SPEC 동반 문서

- `retrospective.md` — 시리즈 회고 (timeline, amendment-cause 분석, SPEC 빈틈 카테고리화)
- `lessons.md` — 다음 SPEC 체크리스트 (anti-pattern 5건)

### 9.2 supersedes 원본 SPEC

- `.moai/specs/SPEC-NAVER-THEME-001/` — V1 (spec.md, plan.md, research.md, acceptance.md, progress.md, v2-handoff.md 보존)
- `.moai/specs/SPEC-NAVER-THEME-002/` — V2 backend (spec.md, plan.md, research.md, acceptance.md, handoff-frontend-v2.md 보존)
- `.moai/specs/SPEC-NAVER-THEME-003/` — V2 frontend + 5 amendments (spec.md, plan.md, research.md, acceptance.md, progress.md, tasks.md 보존)

### 9.3 외부 자원

- V2 mobile endpoints (config.py 격리, SPEC-002 검증):
  - `https://m.stock.naver.com/front-api/stock/sectors/all` (list)
  - `https://m.stock.naver.com/front-api/domestic/sector/item/list` (detail)
- V1 desktop endpoints (SPEC-001 검증):
  - `https://finance.naver.com/sise/theme.naver` (목록)
  - `https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}` (상세)
- frontend vitest baseline: 256/257 PASS (ChartGrid 1 fail pre-existing, V2 무관)

---

Version: 1.0.0
Status: Implemented (Consolidated)
Origin: SPEC-NAVER-THEME-001 (12d81b1) + SPEC-NAVER-THEME-002 (888e2eb~b1c24eb) + SPEC-NAVER-THEME-003 v1.0.5 (4e75f14)
