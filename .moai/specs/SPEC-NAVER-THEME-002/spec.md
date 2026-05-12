---
id: SPEC-NAVER-THEME-002
title: 모바일 stock.naver.com 기반 테마 분석 V2
status: Draft
version: 1.0.0
owner: bjw2002
created: 2026-05-01
updated: 2026-05-01
depends_on: SPEC-NAVER-THEME-001
---

# SPEC-NAVER-THEME-002: 모바일 stock.naver.com 기반 테마 분석 V2

## 메타데이터

| 항목 | 값 |
| --- | --- |
| SPEC ID | SPEC-NAVER-THEME-002 |
| 제목 | Naver Mobile Theme Analysis Module (Read-Only Add-On, V2) |
| 생성일 | 2026-05-01 |
| 상태 | Draft |
| 우선순위 | High |
| 담당 | expert-backend, expert-testing |
| 의존 SPEC | SPEC-NAVER-THEME-001 (V1 read-only 참조) |
| Lifecycle | spec-anchored |
| 버전 | 1.0.0 |

---

## HISTORY

- 2026-05-01 v1.0.0: 초안 작성 (manager-spec). 라이브 PoC 완료 (`research.md` §1) — endpoint `/front-api/stock/sectors/all` (목록), `/front-api/domestic/sector/item/list` (상세). 모듈 경로 `backend/services/naver_theme_v2/` 결정. cohabitation Option γ (사용자 결정 잠금) — V1 endpoint 무수정, V2 신규 endpoint 추가. 신규 컬럼 `theme_description`, `stock_description`. `mini_chart_points` (sparkline)는 V2.1로 이연. `bare except` 금지를 REQ-NT2-C-005로 신규 명문화 (V1 RUN phase §13-4 교훈).

---

## 1. Environment (환경)

### 1.1 시스템 개요

`backend/services/naver_theme_v2/` 패키지는 네이버 모바일 stock 사이트의 비공식 JSON API (`https://m.stock.naver.com/front-api/...`)를 **온디맨드로 호출**하여 테마 list와 detail을 수집하고, V1과 동일한 `ThemeAnalysisResult` shape으로 가공한다.

V1 (`backend/services/naver_theme/`)의 데스크탑 정적 HTML 크롤링과 **병렬로 cohabit**한다 (Option γ — V1 무수정).

본 모듈은 **읽기 전용 애드온**으로 기존 KR Stock Screener 백엔드에 추가 통합된다.

| 항목 | 값 |
| --- | --- |
| 모듈 경로 | `backend/services/naver_theme_v2/` (V1 sibling) |
| 단일 진입점 | `from backend.services.naver_theme_v2 import collect_and_analyze_v2, ThemeAnalysisResult` |
| 반환 타입 | `ThemeAnalysisResult` (V1 schema 재사용 — `from backend.services.naver_theme.schemas import ThemeAnalysisResult`) |
| 실행 모델 | stateless, 스케줄러 없음 (호출 1회당 1 사이클) |
| 외부 호출 횟수 (snapshot) | 약 27회 (테마 목록 6 페이지 + top-N 상세 ~20개) — V1과 유사 |
| 빠른 모드 (`skip_details=True`) | 약 6회 (list endpoint page 1~6만), 10초 이내 응답 |

### 1.2 모듈 내부 구조

| 파일 | 역할 | 출처 |
|------|------|------|
| `__init__.py` | `collect_and_analyze_v2`, `ThemeAnalysisResult` 노출 | 신규 |
| `service.py` | 진입점 (오케스트레이션) | 신규 |
| `crawler.py` | HTTP 호출 (requests + JSON), 단일 thread | 신규 |
| `parser.py` | JSON dict → 정규화된 dict/list 변환 (필드명 access only, 단위 변환) | 신규 |
| `config.py` | endpoint URL, 모바일 UA, sleep 등 상수 | 신규 |
| `analyzer.py` | (재사용) `from backend.services.naver_theme.analyzer import ...` | V1 재사용 |
| `db_join.py` | (재사용) `from backend.services.naver_theme.db_join import ...` (optional fallback only) | V1 재사용 |
| `schemas.py` | (재사용) `from backend.services.naver_theme.schemas import ThemeAnalysisResult` | V1 재사용 |
| `routers/themes.py` | EDIT — `/api/themes/v2/snapshot`, `/api/themes/v2/quick` 추가 (V1 routes 무수정) | EDIT |

### 1.3 외부 의존성 (기설치, 신규 추가 없음)

- `requests >= 2.28` (HTTP)
- `pandas >= 2.0` (DataFrame)
- `numpy >= 1.24` (z-score, analyzer 재사용)
- `pydantic >= 2.0` (응답 schema 검증)
- `fastapi >= 0.115` (라우터)
- (V1에서 사용하던 `beautifulsoup4`, `lxml`은 V2에서 사용하지 않음 — JSON only)

---

## 2. Assumptions (가정)

### 2.1 외부 시스템 가정

- 네이버 모바일 stock의 비공식 endpoint `https://m.stock.naver.com/front-api/stock/sectors/all` 및 `https://m.stock.naver.com/front-api/domestic/sector/item/list`가 PoC 결과(2026-05-01)와 동일한 응답 shape를 유지
- 익명 호출 가능 (Cookie/Authentication 불필요) — PoC 검증 완료
- pageSize 상한 50 (서버 검증) 유지
- 응답 Content-Type `application/json; charset=utf-8` 유지

### 2.2 호환성 가정

- V1 `backend/services/naver_theme/`는 무수정 — `analyzer.py`, `db_join.py`, `schemas.py`를 import하는 V2 코드가 V1 변경 없이 정상 동작
- frontend `ThemeAnalysisResult` shape (5종 DataFrame + metadata)는 V2가 보존
- V2 응답 `themes_df`/`stocks_df` 컬럼은 V1 컬럼 superset (V1 컬럼 100% 보존 + 신규 컬럼 2개)

### 2.3 Risk-bound 가정

- endpoint URL이 1주일~1개월 단위로 변경될 수 있음 (sentry release `stock-web@2026.04.30` 활발) — `config.py`의 endpoint 상수 일괄 교체로 대응
- `sectorDescription`이 일부 테마에서 null일 수 있음 → nullable 처리
- `description` (per stock)이 일부 종목에서 null일 수 있음 → nullable 처리

---

## 3. Requirements (요구사항, EARS format)

### 3.1 Functional Requirements

#### REQ-NT2-001: 단일 진입점 함수

**The system shall** expose a single function `collect_and_analyze_v2(top_n_themes: int = 20, leaders_per_theme: int = 3, skip_details: bool = False) -> ThemeAnalysisResult` from `backend.services.naver_theme_v2`.

**Rationale:** V1의 `collect_and_analyze`와 동일한 시그니처 패턴. 호출자는 `import` 경로만 다를 뿐 동일한 사용법.

#### REQ-NT2-002: 테마 목록 수집

**WHEN** `collect_and_analyze_v2()`가 호출되면 **the system shall** issue HTTP GET requests to `https://m.stock.naver.com/front-api/stock/sectors/all` with query parameters `sectorType=theme`, `businessDayCategory=daily`, `sectorSortType=CHANGE_RATE`, `nationType=domestic`, `pageSize=50` and paginate via `page=1..N` until response `result.sectors[]` length < `pageSize`.

#### REQ-NT2-003: 테마 상세 수집

**WHEN** snapshot 모드(`skip_details=False`)에서 강세 테마 top-N이 결정되면 **the system shall** issue HTTP GET requests to `https://m.stock.naver.com/front-api/domestic/sector/item/list` with `sectorType=theme`, `sectorCode={theme_id}`, `sectorSortType=CHANGE_RATE`, `page=1`, `pageSize=50` for each theme to retrieve `sectorDescription`, per-stock `description`, and per-stock `marketValue`.

#### REQ-NT2-004: theme_description 신규 컬럼

**The system shall** populate `themes_df['theme_description']` (dtype: `object` / nullable string) from the detail endpoint response `result.sectorDescription` for each theme.

**WHEN** detail endpoint returns `sectorDescription=null` for a given theme, **the system shall** set `theme_description=NaN` (pandas) without raising an exception.

#### REQ-NT2-005: stock_description 신규 컬럼

**The system shall** populate `stocks_df['stock_description']` (dtype: `object` / nullable string) from the detail endpoint response `result.items[].description` for each stock.

**WHEN** an item lacks `description` (key absent or value null), **the system shall** set `stock_description=NaN` without raising an exception.

#### REQ-NT2-006: market_cap 직접 노출 (db_join optional)

**The system shall** populate `stocks_df['market_cap']` (단위: 원) from the detail endpoint response `result.items[].marketValue` directly.

**WHERE** `marketValue` is missing or null for an item, **the system shall** optionally fall back to `backend.services.naver_theme.db_join.join_market_cap()` (read-only, `mode=ro` URI) — this fallback is permitted but not required.

**The system shall** treat `market_cap` as int (원 단위), matching V1 schema.

#### REQ-NT2-008: ThemeAnalysisResult shape 보존

**The system shall** return a `ThemeAnalysisResult` instance (imported from `backend.services.naver_theme.schemas`) preserving all V1 columns of `themes_df`, `stocks_df`, `strong_themes_df`, `leaders_df`, `multi_theme_stocks_df`, and `metadata` with identical names and dtypes.

**WHEN** V2 adds new columns (`theme_description`, `stock_description`), **the system shall** add them as additional columns only — never rename, drop, or change dtype of V1 columns.

### 3.2 Non-Functional Requirements

#### REQ-NT2-NF-001: 매너 호출

**The system shall** issue HTTP requests with the following constraints:
- User-Agent header: `Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1`
- Referer header: `https://m.stock.naver.com/domestic/home/theme/daily`
- Accept header: `application/json`
- Sleep ≥ 0.7 seconds between consecutive requests
- Single-threaded execution (no `concurrent.futures`, no `asyncio`)

#### REQ-NT2-NF-002: UTF-8 JSON 응답 처리

**The system shall** parse responses assuming `Content-Type: application/json; charset=utf-8`.

**The system shall** verify Content-Type contains `application/json` substring before parsing — non-JSON responses are treated as errors and recorded in `errors[]` with `stage='content_type'`.

**WHILE** V1 forces `response.encoding='euc-kr'`, V2 **shall not** apply this — UTF-8 is default for `requests` JSON responses.

#### REQ-NT2-NF-003: 에러 구조

**The system shall** return errors as a list of dicts in `metadata['errors']` with shape `[{theme_id: Optional[int], stage: str, reason: str}]`.

**WHEN** a request fails with HTTP 5xx or `requests.Timeout`, **the system shall** retry once after sleeping ≥ 1 second.

**IF** the retry also fails, **then the system shall** record the failure in `errors[]` and continue with partial results (no fatal exception propagated to the caller).

**Stages used:**
- `'list_fetch'` — list endpoint failure
- `'detail_fetch'` — detail endpoint failure
- `'schema_validation'` — Pydantic ValidationError
- `'content_type'` — non-JSON response
- `'json_decode'` — JSONDecodeError
- `'endpoint_drift'` — list/detail returned unexpected isSuccess=false

#### REQ-NT2-NF-004: 응답 시간 목표

**The system shall** complete `collect_and_analyze_v2(skip_details=False)` within 30 seconds under nominal conditions (no 5xx, no rate-limit).

**The system shall** complete `collect_and_analyze_v2(skip_details=True)` within 10 seconds under nominal conditions.

#### REQ-NT2-NF-005: endpoint URL 격리

**The system shall** declare endpoint URLs as module-level constants in `config.py`:
- `NAVER_MOBILE_BASE_URL = "https://m.stock.naver.com"`
- `NAVER_MOBILE_FRONT_API_PREFIX = "/front-api"`
- `LIST_ENDPOINT_PATH = "/stock/sectors/all"`
- `DETAIL_ENDPOINT_PATH = "/domestic/sector/item/list"`

**The system shall not** hardcode these URLs inline in `crawler.py` or `service.py` — all references must read from `config.py`.

**Rationale:** Next.js buildId/release rotation may invalidate URL hash; centralized constants enable single-point updates (REQ-NT2-NF-005, mitigates Risk R-1 in research.md).

### 3.3 Constraints

#### REQ-NT2-C-001: 인증·쿠키 사용 금지

**The system shall not** include `Cookie` headers, OAuth tokens, or any authentication artifacts in HTTP requests.

**The system shall** make all requests anonymously, identical to PoC verification (research.md §1.3).

#### REQ-NT2-C-002: 기존 4탭 회귀 0건

**The system shall not** modify any existing frontend file, V1 backend module, or existing FastAPI route during V2 implementation.

**The system shall** preserve current behavior of V1 endpoints `/api/themes/snapshot`, `/api/themes/quick` and the existing 4 frontend tabs (Stocks, Themes, Mini-map, Treemap, plus V1 Theme Analysis tab if rendered).

(Mirrors V1 AC-12.)

#### REQ-NT2-C-003: 신규 pip 의존성 금지

**The system shall not** introduce new entries to `requirements.txt`, `pyproject.toml`, or any dependency manifest.

**The system shall** rely exclusively on dependencies already used by V1 (`requests`, `pandas`, `numpy`, `pydantic`, `fastapi`).

#### REQ-NT2-C-004: DB INSERT/UPDATE 금지

**The system shall not** execute any SQL statement that modifies database state (INSERT, UPDATE, DELETE, CREATE, ALTER, DROP).

**WHERE** `db_join.py` is used as fallback for missing `marketValue`, **the system shall** open the SQLite connection with read-only URI (`file:...?mode=ro`).

(Mirrors V1 AC-11.)

#### REQ-NT2-C-005: bare except 금지 (NEW vs V1)

**The system shall not** use bare `except:` or `except Exception:` clauses in any V2 module file.

**The system shall** catch only specific exception types relevant to the operation:
- `requests.RequestException` (network/HTTP errors)
- `requests.Timeout` (timeout, sub-class of RequestException)
- `json.JSONDecodeError` (malformed JSON body)
- `KeyError` (missing dict keys during parsing)
- `pydantic.ValidationError` (response schema mismatch)
- `ValueError` (only for known controlled cases — e.g., unit conversion)

**Rationale:** V1 RUN phase §13-4 교훈. V1에서 일부 모듈이 `except Exception` 사용 → 진단 어려움 발생.

### 3.4 Routing Requirements

#### REQ-NT2-R-001: ADD `/api/themes/v2/snapshot`

**The system shall** ADD a new FastAPI route `GET /api/themes/v2/snapshot` to `backend/routers/themes.py` that calls `collect_and_analyze_v2(skip_details=False)` and returns its `ThemeAnalysisResult` serialized via existing Pydantic response model.

#### REQ-NT2-R-002: ADD `/api/themes/v2/quick`

**The system shall** ADD a new FastAPI route `GET /api/themes/v2/quick` to `backend/routers/themes.py` that calls `collect_and_analyze_v2(skip_details=True)` and returns its `ThemeAnalysisResult` serialized via existing Pydantic response model.

#### REQ-NT2-R-003: V1 routes 무수정 (regression-blocking)

**The system shall not** modify the function signatures, response shapes, decorators, or paths of V1 routes `GET /api/themes/snapshot` and `GET /api/themes/quick`.

**WHEN** the V2 routes are added, **the system shall** add them as additional `@router.get(...)` decorators only — V1 route definitions remain byte-identical except for line numbers due to insertion.

**IF** any V1 route signature drift is detected (e.g., parameter rename, response model change), **then the system shall** be considered non-compliant with REQ-NT2-R-003 and the implementation **shall** be reverted.

---

## 4. Dependencies and Cohabitation

### 4.1 V1 cohabitation strategy (Option γ — locked)

| Aspect | V1 (`backend/services/naver_theme/`) | V2 (`backend/services/naver_theme_v2/`) |
|---|---|---|
| Data source | finance.naver.com 데스크탑 정적 HTML | m.stock.naver.com `/front-api/...` JSON |
| Encoding | EUC-KR (forced) | UTF-8 (default) |
| HTTP libs | requests + bs4 + lxml | requests only |
| FastAPI route | `/api/themes/snapshot`, `/api/themes/quick` | `/api/themes/v2/snapshot`, `/api/themes/v2/quick` |
| Module status | **무수정 (READ-ONLY for V2)** | NEW |
| Frontend impact | 없음 (V1 그대로 호출) | 없음 (V2 채택은 별도 SPEC) |

### 4.2 V1 모듈 import (재사용 with read-only 의도)

V2 코드에서 V1 모듈을 다음과 같이 import:

```python
# backend/services/naver_theme_v2/service.py
from backend.services.naver_theme.schemas import ThemeAnalysisResult
from backend.services.naver_theme.analyzer import (
    compute_strong_themes,
    compute_leaders,
    compute_multi_theme_stocks,
    # ... V1 analyzer functions
)
from backend.services.naver_theme.db_join import join_market_cap  # optional fallback only
```

V1 코드는 무수정. V1을 import하는 것은 코드 변경이 아니므로 REQ-NT2-C-002에 위배되지 않는다.

---

## 5. Exclusions (What NOT to Build)

V2 SPEC 범위에서 **명시적으로 제외**되는 항목 (이 항목은 별도 SPEC에서 다룬다):

| 항목 | 분류 | 사유 |
|---|---|---|
| Sparkline `mini_chart_points` 컬럼 | V2.1 | detail 응답에 `miniImageChartUrl` (PNG)만 존재. 시계열 좌표 추출은 PNG 파싱 필요 → 별도 작업 |
| `GET /api/themes/by-stock/{code}` reverse index | 별도 SPEC (V1.5 ish-out) | 종목 → 테마 역인덱스. 데이터 모델 다름 |
| `frontend/src/components/MarketOverview/HotThemesStrip.tsx` | 별도 SPEC | 프론트 신규 컴포넌트. V2는 backend only |
| `frontend/src/components/StockList/ThemeChips.tsx` | 별도 SPEC | 프론트 컴포넌트 |
| `CrossTabParams.themeId` / `themeName` 추가 | 별도 SPEC | 프론트 cross-tab 통신 모델 변경 |
| frontend `ThemeAnalysisResult` 컬럼 활용 (theme_description, stock_description) | 별도 SPEC | V2에서는 backend가 컬럼을 채우기만 함. UI 표시는 별도 작업 |
| V1 모듈 수정 또는 삭제 | 절대 금지 (REQ-NT2-C-002) | Cohabitation Option γ |
| 테마 즐겨찾기 기능 (mobile 페이지 별 아이콘) | 별도 SPEC | 사용자 기능 (인증 필요) |
| 종목 로고 이미지 | V2.1 | mobile detail 응답에 미포함 (별도 endpoint 필요) |
| `pkg_resources` 환경 충돌 해결 (V1 §11 이슈 2) | 별도 SPEC 또는 issue | Python 3.13 호환성 — 본 V2 범위 외 |

---

## 6. Acceptance Criteria 요약

세부 AC는 `acceptance.md` 참조. 총 14~15개 AC (V1 14-AC 스타일 mirror).

### Pass 조건 요약

- AC-1 ~ AC-14: 자동 검증 (pytest)
- 단위 테스트 커버리지 ≥ 85% (V1은 99%, V2 목표는 ≥ 85%)
- 라이브 통합 테스트 1회 성공 (`@pytest.mark.live`)
- V1 단위 테스트 51개 PASS 유지 (회귀 0)

---

## 7. Glossary

| 용어 | 의미 |
|---|---|
| sector | 모바일 API에서 V1의 "테마"에 해당. `sectorType=theme`로 필터 (vs `upjong`(업종), `group`(그룹)) |
| sectorCode | 모바일 API의 테마 ID (string-of-int, 예: `"178"`). V2 parser에서 `int(sectorCode)`로 정규화하여 V1 schema의 `theme_id` (int)와 호환 |
| sectorDescription | 모바일 API의 테마 설명 (예: "각종 전선 및 전람(電纜)제조...") — V2에서 `theme_description` 컬럼으로 매핑 |
| description (per item) | 모바일 API의 종목별 편입 설명 — V2에서 `stock_description` 컬럼으로 매핑 |
| marketValue | 모바일 API detail 응답의 시가총액 (단위: 원). V1의 `market_cap` (원)과 직접 호환 |
| marketCap (list) | 모바일 API list 응답의 시가총액 (단위: 백만원). V2에서 사용하지 않음 (혼선 방지) |
| front-api | 모바일 사이트의 Fastify-based BFF (Backend-For-Frontend) prefix `/front-api/` |
| Option γ | V1·V2 cohabitation 전략 — 신규 endpoint `/api/themes/v2/...` 추가, V1 무수정 |

---

## 8. References

- `.moai/specs/SPEC-NAVER-THEME-001/v2-handoff.md` (480 lines, V2 SPEC 작성 위한 self-contained 핸드오프)
- `.moai/specs/SPEC-NAVER-THEME-001/spec.md` (V1 SPEC v1.0.0 Approved)
- `.moai/specs/SPEC-NAVER-THEME-002/research.md` (V2 PoC 결과 + 코드베이스 분석)
- `.moai/specs/SPEC-NAVER-THEME-002/plan.md` (V2 구현 계획)
- `.moai/specs/SPEC-NAVER-THEME-002/acceptance.md` (V2 14-AC)
- 라이브 PoC: 2026-05-01 12:30~12:42 KST (curl + python3 schema 분석)

---

Version: 1.0.0
Status: Draft (Pending User Approval)
Next phase: `/moai run SPEC-NAVER-THEME-002` (after approval + `/clear`)
