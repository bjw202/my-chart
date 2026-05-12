---
id: SPEC-NAVER-THEME-002
title: 모바일 stock.naver.com 기반 테마 분석 V2 — Research
status: Draft
version: 1.0.0
owner: bjw2002
created: 2026-05-01
updated: 2026-05-01
depends_on: SPEC-NAVER-THEME-001
---

# Research: SPEC-NAVER-THEME-002 — 모바일 stock.naver.com 기반 테마 분석 V2

## 메타

| 항목 | 값 |
|------|-----|
| SPEC | SPEC-NAVER-THEME-002 |
| 버전 | 1.0.0 |
| 모드 | read-only (파일 수정 없음) |
| PoC 결과 | **ENDPOINT_FOUND** (curl 검증, 라이브 응답 200) |
| 작성 트리거 | manager-spec subagent — V2 plan 시작 |

이 문서는 SPEC-NAVER-THEME-002 plan 시 참고한 라이브 PoC 결과 + 코드베이스 분석 요약본이다. V1 핸드오프 노트(`SPEC-NAVER-THEME-001/v2-handoff.md`)와 함께 읽는다.

---

## 0. 핵심 요약 (TL;DR)

- **PoC 성공**: 모바일 사이트의 비공식 JSON API endpoint 2종을 식별하고 라이브 응답 표본화 완료 (anonymous, no rate-limit 관측, 모바일 UA 불필요지만 V1 conventions 준수)
- **List endpoint** `GET /front-api/stock/sectors/all` (baseURL `https://m.stock.naver.com`)
  - 파라미터: `sectorType=theme`, `businessDayCategory=daily`, `page`, `pageSize` (max 50, 서버 검증), `sectorSortType=CHANGE_RATE`, `nationType=domestic`
  - 응답: `result.sectors[]` 각 sector마다 `{sectorCode, sectorName, sectorDescription(=null in list), changeRate, totalMarketCap, risingCount, unChangedCount, fallingCount, items[3]}`
  - 전체 테마 수 약 264개 (실측 2026-05-01)
- **Detail endpoint** `GET /front-api/domestic/sector/item/list` (same baseURL)
  - 파라미터: `sectorType=theme`, `sectorCode={int}`, `sectorSortType=CHANGE_RATE`, `page=1`, `pageSize=50`
  - 응답: `result.{sectorCode, sectorName, sectorDescription(=non-null), changeRate, totalMarketCap, items[]}`
  - **`sectorDescription`은 detail에서만 채워진다** (list에서는 null) — 테마 설명 컬럼은 detail 호출이 필수
  - **각 item에 `description` 필드 존재** — 종목 편입 사유 풍부 (실측 8/8 = 100%)
  - **`marketValue`(원 단위) 필드 존재** — db_join 의존 제거 가능 (실측 8/8 = 100%)
- **모듈 경로 결정**: `backend/services/naver_theme_v2/` — V1 (`backend/services/naver_theme/`)과 sibling 디렉토리. 회귀 0% 보장.
- **Cohabitation 전략**: Option γ ONLY (사용자 결정 잠금). V2는 신규 endpoint `/api/themes/v2/snapshot`, `/api/themes/v2/quick` 추가. V1 endpoint는 무수정.
- **Sparkline (`mini_chart_points`)**: V2 범위 외 (V2.1로 이연). 단, detail 응답에 `miniImageChartUrl`(PNG URL)은 포함되어 있어 향후 활용 가능.
- **Frontend `ThemeAnalysisResult` shape 호환**: `themes_df`/`stocks_df`/`leaders_df`/`strong_themes_df`/`multi_theme_stocks_df` 5종 + `metadata` shape 그대로. V1 컬럼 전체 보존 + 신규 컬럼 `theme_description`, `stock_description` 추가.

---

## 1. PoC 결과 (라이브 검증, 2026-05-01)

### 1.1 PoC 절차

PoC는 manager-spec subagent가 leader 권한으로 직접 수행했다. browser DevTools 미가용 환경이므로 `curl + jq + 정적 webpack 번들 분석` 방식을 사용했다.

#### Step A — 후보 endpoint 단순 호출 (5건, 전부 실패 또는 404)

| 후보 | URL | HTTP | 결과 |
|---|---|---|---|
| A1 | `https://api.stock.naver.com/domestic/home/theme/daily` | 404 | Spring Boot 404 (`{"timestamp":..., "status":404, "error":"Not Found"}`) |
| A2 | `https://m.stock.naver.com/api/json/sise/themes?count=20&page=1` | 404 | Next.js error HTML 반환 |
| A3 | `https://m.stock.naver.com/front-api/v1/theme/daily` | 404 | **Fastify 스타일 404** (`{"message":"Route GET:/front-api/v1/theme/daily not found"}`) — `/front-api` 라우터 존재 단서 |
| A4 | `https://m.stock.naver.com/api/v1/theme/daily` | 404 | Next.js error HTML |
| A5 | `https://m.stock.naver.com/_next/data/.../daily.json` | 200 | `__N_REDIRECT:/404` (Next.js getServerSideProps redirect — 데이터 없음) |

**핵심 단서:** A3의 응답 메시지(`Route GET:... not found`)는 Fastify 백엔드가 `m.stock.naver.com/front-api` prefix를 처리한다는 증거. `/front-api/v1/...` prefix가 아니라 `/front-api/` 직접 prefix일 가능성 부각.

#### Step B — front-api 변형 후보 5건 (전부 404, 그러나 동일 Fastify 응답 시그니처)

| 후보 | URL | HTTP |
|---|---|---|
| B1 | `https://m.stock.naver.com/front-api/v1/theme` | 404 |
| B2 | `https://m.stock.naver.com/front-api/v1/themes/daily` | 404 |
| B3 | `https://m.stock.naver.com/front-api/v1/themes` | 404 |
| B4 | `https://m.stock.naver.com/front-api/v1/theme/list` | 404 |
| B5 | `https://api.stock.naver.com/domestic/group/theme` | 404 |

#### Step C — 정적 webpack 번들 정밀 분석

1. `/domestic/home/theme/daily` HTML을 fetch하여 30개 Next.js chunk URL 추출
2. 페이지 specific chunk (`pages/domestic/home/theme/daily-4c7695402985d32f.js`) 다운로드 → 직접 endpoint 문자열 없음 (webpack `n(...)` lazy import만 존재)
3. 후보 chunk 21개 다운로드 (총 ~1.5MB) → `grep -E '/(domestic|stock|worldstock)/'` 패턴 매칭으로 chunk **5387** 식별
4. chunk 5387 분석 결과:
   - `(0,i.HE)((t,e)=>({url:"/stock/sectors/all",method:"get",params:{...t,page:e,pageSize:o.IV.DOMESTIC.HOME,sectorSortType:u.WR.CHANGE_RATE,nationType:u.FO.DOMESTIC}}))` → 테마 list endpoint 발견
   - `(0,i.rP)(t=>({url:"/domestic/sector/item/list",method:"get",params:{...t,sectorSortType:u.WR.CHANGE_RATE}}))` → 테마 detail endpoint 발견
   - `r(83414)`: `WN={UPJONG:"upjong", THEME:"theme", GROUP:"group"}` — sectorType enum 발견
   - `r(83414)`: `WR={MARKET_VALUE:"MARKET_VALUE", CHANGE_RATE:"CHANGE_RATE"}` — sectorSortType enum 발견
   - `r(83414)`: `FO={DOMESTIC:"domestic", USA:"USA", ...}` — nationType enum 발견
5. `_app.js` (841KB)에서 axios baseURL 구성 추적:
   - 모듈 24068 (API factory `rP`/`HE`/`cL`): `axios.create({baseURL:\`${s.bl}${u.vU}\`, ...})`
   - 모듈 71752 (`s`): `bl[https][real] = "https://m.stock.naver.com"`
   - 모듈 18250 (`u`): `vU = "/front-api"`
   - **결론**: production baseURL = `https://m.stock.naver.com/front-api`

#### Step D — 최종 endpoint 라이브 검증

| 시도 | URL (도출 후) | HTTP | Size | 결과 |
|---|---|---|---|---|
| D1 | `https://m.stock.naver.com/front-api/stock/sectors/all?sectorType=theme&businessDayCategory=daily&page=1&pageSize=10&sectorSortType=CHANGE_RATE&nationType=domestic` | **200** | 5.7 KB | `{"isSuccess":true, "result":{"sectors":[10건], "totalRisingCount":1392, ...}}` |
| D2 | `https://m.stock.naver.com/front-api/domestic/sector/item/list?sectorType=theme&sectorCode=178&sectorSortType=CHANGE_RATE&page=1&pageSize=10` | **200** | 4 KB+ | `{"isSuccess":true, "result":{"sectorCode":"178", "sectorName":"전선", "sectorDescription":"각종 전선 및 전람(電纜)제조...", "items":[8건 with description]}}` |

서버 응답 헤더 (D1):
```
HTTP/2 200
content-type: application/json; charset=utf-8
vary: Origin
referrer-policy: unsafe-url
server: nfront
strict-transport-security: max-age=31536000; includeSubDomains
x-request-id: <uuid>
```

### 1.2 Pagination & Limit 검증

| 검증 | 결과 |
|---|---|
| `pageSize=200` | 400 `{"detailCode":"too_big","message":"...pageSize: Too big: expected number to be <=50"}` — 서버 검증 명시 |
| `pageSize=100` | 동일 400 |
| `pageSize=50` × page 1~6 | 50, 50, 50, 50, 50, 14 → 총 264 sectors (실측 2026-05-01) |
| `pageSize=20` × page 1~? | 20씩 정상 반환 |

**결정:** 기본 pageSize=50 사용. snapshot 모드에서 페이지를 끝까지 순회 (예상 6 호출).

### 1.3 인증/UA/Referer 검증

| 검증 | 결과 |
|---|---|
| Referer 없음 | 200 정상 응답 (anonymous OK) |
| Desktop UA (`Mozilla/5.0 (X11; Linux ...)`) | 200 정상 응답 (UA 게이팅 없음) |
| Cookie 없음 | 200 정상 응답 (인증 불필요) |

**결정:** 익명 호출. UA는 V1 conventions에 따라 모바일 iPhone Safari로 명시. Referer는 정중함을 위해 명시 (`https://m.stock.naver.com/domestic/home/theme/daily`).

### 1.4 Rate Limit 관측

PoC 동안 (약 1분 30초간 ~25 호출, 0.7~1초 간격) HTTP 4xx/5xx, IP block, captcha 등 미관측. **단, 비공식 endpoint이므로 sleep ≥ 0.7s + 단일 thread 정책은 V1과 동일하게 유지 (REQ-NT2-NF-001).**

---

## 2. 응답 schema (Pydantic v2 모델 시안)

### 2.1 List endpoint response

```python
# /front-api/stock/sectors/all?sectorType=theme&...
class SectorListItem(BaseModel):
    """테마 list endpoint의 sector 단위. items는 top-3 미리보기."""
    sectorCode: str            # "178" (note: int처럼 보이지만 string)
    sectorName: str            # "전선"
    sectorDescription: Optional[str]  # null in list endpoint
    changeRate: float          # 9.2 (단위: %)
    totalMarketCap: int        # 40485714 (단위: 원? 백만원? — §2.3 참조)
    risingCount: int
    unChangedCount: int
    fallingCount: int
    items: list[SectorListItemPreview]  # top-3 종목 미리보기 only

class SectorListItemPreview(BaseModel):
    stockEndType: str          # "stock"
    itemCode: str              # "024840"
    itemName: str              # "KBI메탈"
    changeRate: float          # 29.94 (%)
    marketCap: int             # 178036 — 단위 검증 필요 (§2.3)
    itemInfo: Optional[Any]    # 실측 null

class SectorListResponse(BaseModel):
    isSuccess: bool
    detailCode: str
    message: str
    result: SectorListResult

class SectorListResult(BaseModel):
    totalRisingCount: int       # 1392 (전체 KOSPI/KOSDAQ 상승 종목 수)
    totalUnChangedCount: int    # 180
    totalFallingCount: int      # 4663
    sectors: list[SectorListItem]
```

### 2.2 Detail endpoint response

```python
# /front-api/domestic/sector/item/list?sectorType=theme&sectorCode=178
class SectorDetailItem(BaseModel):
    """테마 detail endpoint의 종목 단위. description, marketValue 풍부."""
    name: str                          # "KBI메탈"
    stockEndType: str                  # "stock"
    currentPrice: int                  # 5100
    currencyType: str                  # "KRW"
    fluctuationsType: str              # "UPPER_LIMIT" | "RISING" | "FALLING" | "UNCHANGED" | "LOWER_LIMIT"
    fluctuations: str                  # "1175" (string, 부호 없음)
    fluctuationsRatio: str             # "29.94"
    isTradingStop: bool
    accumulatedTradingVolume: int      # 39179527 (주)
    accumulatedTradingValue: int       # 181194000000 (원)
    marketValue: int                   # 178000000000 (원, V2 핵심 — db_join 대체 가능)
    miniImageChartUrl: Optional[str]   # PNG URL (V2.1 sparkline ingredient)
    marketStatus: str                  # "CLOSE" | "OPEN" | ...
    newlyListed: bool
    isDelisting: bool
    stockExchangeType: str             # "KOSPI" | "KOSDAQ"
    stockExchangeName: str             # "코스피" | "코스닥"
    feModelType: str                   # "domestic"
    id: str                            # itemCode와 동일 ("024840")
    itemCode: str                      # "024840"
    description: Optional[str]         # 종목 편입 사유 (V2 핵심) — 실측 8/8 non-null

class SectorDetailResult(BaseModel):
    sectorCode: str
    sectorName: str
    sectorDescription: Optional[str]   # 테마 설명 (V2 핵심) — 실측 non-null
    changeRate: float
    totalMarketCap: int
    risingCount: int
    unChangedCount: int
    fallingCount: int
    items: list[SectorDetailItem]

class SectorDetailResponse(BaseModel):
    isSuccess: bool
    detailCode: str
    message: str
    result: SectorDetailResult
```

### 2.3 단위 검증 (단위 안정성 — CRITICAL)

V1에서 `market_cap`은 **원 단위**(예: 178,036백만원이 아니라 178,036,000,000원)로 DB에 저장. V2 mobile API는 두 가지 단위가 혼재:

| 필드 | List 응답 | Detail 응답 | 단위 추정 |
|---|---|---|---|
| `totalMarketCap` (sector) | 40485714 (전선) | 동일 40485714 | **백만원** (40,485,714백만 = 40조 4857억 — 페이지 표시 "40조 4,857억"과 일치) |
| `marketCap` (item, list) | 178036 (KBI메탈) | — | **백만원** (178,036백만 = 1,780억 — 페이지 "1,780억"과 일치) |
| `marketValue` (item, detail) | — | 178000000000 (KBI메탈) | **원** (178,000,000,000원 = 1,780억 — 일치) |

**결정:**
- detail의 `marketValue` (원 단위) 사용 → V1 `db_join.py`의 `stock_meta.market_cap` (원 단위)과 직접 호환
- list의 `marketCap` (백만원 단위) 미사용 (혼선 방지)
- list의 `totalMarketCap` (백만원 단위) — V2에서 sector-level 표시용으로만 사용 시 명시 변환

이 단위 차이는 V2 plan §13-1 "JSON 필드명 사용 + 단위 명시 검증" 교훈으로 강화한다.

---

## 3. V1 코드베이스 분석 (재이용 vs 신규 작성)

### 3.1 V1 모듈 inventory

| 파일 | V1 역할 | V2 처리 |
|---|---|---|
| `backend/services/naver_theme/__init__.py` | `collect_and_analyze`, `ThemeAnalysisResult` 노출 | **참조만** (V1 schema dataclass 재사용 위해 import) |
| `backend/services/naver_theme/config.py` | URL, EUC-KR 상수, sleep, 가중치 | **신규 작성** (V2 mobile endpoint, EUC-KR 제거) |
| `backend/services/naver_theme/crawler.py` | requests + EUC-KR 강제 + Retry | **신규 작성** (JSON, `Accept: application/json`, 단위 thread) |
| `backend/services/naver_theme/parser.py` | bs4 + lxml + 정규식 | **신규 작성** (dict access only, no bs4) |
| `backend/services/naver_theme/analyzer.py` | z-score 기반 강세/주도주/멀티테마 계산 | **import 재사용** (입력 shape 동일) |
| `backend/services/naver_theme/service.py` | 페이지네이션 + DB JOIN + 오케스트레이션 | **신규 작성** (모바일 수집 + 옵션 fallback) |
| `backend/services/naver_theme/db_join.py` | sqlite3 mode=ro JOIN | **import 재사용** (optional fallback only) |
| `backend/services/naver_theme/schemas.py` | `ThemeAnalysisResult` Pydantic | **import 재사용** (shape 보존) |
| `backend/routers/themes.py` | `/api/themes/snapshot`, `/api/themes/quick` | **EDIT (add v2 routes only)** — V1 routes는 무수정 |
| `tests/test_naver_theme_*` | HTML fixture 기반 | **신규 작성** (`tests/test_naver_theme_v2_*`, JSON fixture) |

### 3.2 ThemeAnalysisResult shape (불변 보존)

V1 `backend/services/naver_theme/schemas.py`에 정의된 `ThemeAnalysisResult`:

```python
@dataclass
class ThemeAnalysisResult:
    themes_df: pd.DataFrame        # 강세 테마 (theme_id, theme_name, change_rate, score, rank, ...)
    stocks_df: pd.DataFrame        # 종목 raw (theme_id, theme_name, code, name, market_cap, change_rate, inclusion_reason, ...)
    strong_themes_df: pd.DataFrame # themes_df의 top-N
    leaders_df: pd.DataFrame       # 주도주 (테마별 상위 N)
    multi_theme_stocks_df: pd.DataFrame  # 다중 테마 종목
    metadata: dict                 # {data_source, generated_at, total_themes_seen, errors[], ...}
```

**V2의 변경 (additive only):**
- `themes_df`에 신규 컬럼 `theme_description: Optional[str]` 추가 (REQ-NT2-004)
- `stocks_df`에 신규 컬럼 `stock_description: Optional[str]` 추가 (REQ-NT2-005)
- `leaders_df`, `strong_themes_df`, `multi_theme_stocks_df`는 V2가 derive할 때 위 컬럼을 propagate
- `metadata['data_source']` 값을 `"naver_finance_desktop_v1"` → `"naver_mobile_v2"`로 명시
- 기타 V1 컬럼은 **전부 보존** (frontend 회귀 0% 보장)

### 3.3 frontend 의존 컬럼 식별

`frontend/src/components/ThemeAnalysis/*` (V1)이 직접 의존하는 컬럼:

| 컴포넌트 | 의존 컬럼 (themes_df/stocks_df) |
|---|---|
| `ThemesTab.tsx` | `theme_id`, `theme_name`, `change_rate`, `score`, `rank` |
| `LeadersTab.tsx` | `theme_name`, `code`, `name`, `market_cap`, `change_rate`, `inclusion_reason` |
| `MultiThemeTab.tsx` | `code`, `name`, `themes_count`, `themes_list` |

**V2 정책:**
- 위 컬럼은 100% 보존
- 신규 컬럼 `theme_description`, `stock_description`은 frontend가 V2 채택 후 별도 SPEC(V2.1?)에서 활용 (V2 범위에서 frontend 변경 0)

---

## 4. cohabitation 전략 (사용자 결정 잠금: Option γ)

V2 핸드오프 §9에서 제시된 3가지 옵션 중 **Option γ**가 사용자 결정으로 잠금됨:

| Option | 설명 | V2 채택 여부 |
|---|---|---|
| α (cutover) | V2가 V1을 즉시 대체 | ❌ 거부 (V1 회귀 위험) |
| β (flag-based) | 환경변수로 V1/V2 분기 | ❌ 거부 (코드량 2배) |
| **γ (parallel endpoints)** | **V2 신규 endpoint `/api/themes/v2/...` 추가, V1 무수정** | ✅ **선택** |

**구현 결과:**
- 신규 라우트 `GET /api/themes/v2/snapshot`, `GET /api/themes/v2/quick` 추가 (REQ-NT2-R-001, REQ-NT2-R-002)
- V1 라우트 `GET /api/themes/snapshot`, `GET /api/themes/quick`는 무수정 (REQ-NT2-R-003, regression-blocking)
- 모듈 디렉토리도 sibling 구조 (`naver_theme/` vs `naver_theme_v2/`) → 코드 격리 강화
- frontend는 V2 채택 시 호출 URL만 `v2/` prefix 추가 (V2 범위에서는 미수행, 별도 SPEC)

---

## 5. 위험 평가 (V2 specific)

| ID | 위험 | 가능성 | 영향 | 완화 |
|---|---|---|---|---|
| R-1 | 비공식 `/front-api/` endpoint 변경 (sentry release: stock-web@2026.04.30, 거의 매일 배포) | High | 데이터 수집 실패 | endpoint URL을 `config.py` 상수로 분리, 응답 schema 검증 (Pydantic ValidationError catch), errors[]에 `stage='endpoint_drift'` 기록 |
| R-2 | pageSize 상한(50) 변경 | Low | 페이지 호출 횟수 증가 | `page_size` config 상수, 서버 검증 메시지 (`detailCode: "too_big"`) catch |
| R-3 | Rate limit 도입 (현재 미관측) | Medium | 호출 차단 | sleep ≥ 0.7s, 단일 thread, 5xx 시 1회 retry |
| R-4 | `sectorDescription` 누락 (일부 테마) | Medium | `theme_description=NaN` | nullable 처리, AC-3에서 nullable 검증 |
| R-5 | `description` 누락 (일부 종목) | Medium | `stock_description=NaN` | nullable 처리, AC-4에서 nullable 검증 |
| R-6 | sectorCode가 string (V1은 int) | Resolved | V1 호환성 | parser.py에서 `int(sectorCode)` 변환 후 V1 동일 type |
| R-7 | `marketValue` 단위 혼동 (list 백만원 vs detail 원) | Resolved | 시총 1000배 오차 | detail의 `marketValue` (원 단위)만 사용, list의 `marketCap` 무시 |
| R-8 | 테마 ID 체계 변경 (V1 정수, V2 string-of-int) | Low | V1 호환성 깨짐 | parser에서 정규화. 호환성 unit test (AC-12) |
| R-9 | 인증 도입 (현재 anonymous) | Low | 통합 복잡도 증가 | 도입 시 endpoint 응답 시그니처 변경 → schema 검증으로 detect |
| R-10 | analyzer.py가 V2 입력 shape 미지원 | Low | analyzer 재구현 필요 | shape 호환 확인됨 (themes_df, stocks_df 컬럼 동일). import 재사용 가능 |

---

## 6. 외부 자원 안정성 모니터링

### 6.1 endpoint URL 변경 감지

`config.py`에 endpoint URL을 상수로 격리하면 build hash 변동 영향이 없다:

```python
# backend/services/naver_theme_v2/config.py
NAVER_MOBILE_BASE_URL = "https://m.stock.naver.com"
NAVER_MOBILE_FRONT_API_PREFIX = "/front-api"
LIST_ENDPOINT = "/stock/sectors/all"
DETAIL_ENDPOINT = "/domestic/sector/item/list"
# Full URL: f"{BASE}{PREFIX}{LIST_ENDPOINT}"
```

### 6.2 응답 schema 검증

각 응답을 Pydantic v2 model로 parse → `ValidationError`를 catch하여 `errors[]`에 stage `'schema_validation'`으로 기록 (REQ-NT2-NF-003).

### 6.3 라이브 검증 fixture

V1 RUN phase에서 학습한 교훈 §13-6, §13-7에 따라:
- `tests/fixtures/naver_theme_v2/list_p1_real.json` — 라이브 fetch 결과 보존
- `tests/fixtures/naver_theme_v2/detail_178_real.json` — 라이브 fetch 결과 (전선 테마)
- `tests/fixtures/naver_theme_v2/list_synthetic.json` — 합성 fixture (corner case 검증)
- `tests/fixtures/naver_theme_v2/detail_synthetic.json` — 합성 fixture (description=null 등)

---

## 7. 신규 의존성 (REQ-NT2-C-003 검증)

| 라이브러리 | V1 사용 여부 | V2 사용 여부 | 신규 추가? |
|---|---|---|---|
| `requests` | ✅ | ✅ | ❌ |
| `beautifulsoup4` | ✅ | ❌ (V2는 JSON only) | ❌ |
| `lxml` | ✅ | ❌ | ❌ |
| `pandas` | ✅ | ✅ | ❌ |
| `numpy` | ✅ | ✅ (analyzer 재사용) | ❌ |
| `pydantic` | ✅ (FastAPI dep) | ✅ (응답 schema 검증) | ❌ |
| `fastapi` | ✅ | ✅ | ❌ |
| `httpx`, `aiohttp` 등 비동기 | ❌ | ❌ (단일 thread + requests 유지) | ❌ |

**결론:** 신규 pip 의존성 추가 없음 (REQ-NT2-C-003 충족).

---

## 8. V1 RUN phase 학습 교훈 (재확인)

V2 핸드오프 §13의 7개 교훈을 plan.md에 인코딩하기 위해 재확인:

| § | 교훈 | V2 적용 |
|---|---|---|
| §13-1 | 컬럼 인덱스 의존 금지 | V2는 dict.get('description') 등 필드명 access only |
| §13-2 | 인코딩 강제 누락 금지 | V2 응답 Content-Type이 `application/json; charset=utf-8` 검증 |
| §13-3 | DB read-only URI | db_join을 V2 fallback으로 사용 시 mode=ro 유지 |
| §13-4 | bare except 금지 | `requests.RequestException`, `json.JSONDecodeError`, `KeyError`, `pydantic.ValidationError` 명시 catch (REQ-NT2-C-005) |
| §13-5 | errors는 dict 형식 | `[{theme_id, stage, reason}]` 일관 (REQ-NT2-NF-003) |
| §13-6 | 라이브 검증 1회 필수 | research.md §1 단계 D에서 완료 |
| §13-7 | 라이브 + synthetic fixture 혼합 | tests/fixtures/naver_theme_v2/ 디렉토리에 두 종류 모두 보존 |

---

## 9. 결론 및 plan.md 핸드오프

### 9.1 PoC 종합 결과

- **PoC 결과: ENDPOINT_FOUND** (BLOCKER 없음)
- list endpoint와 detail endpoint 모두 라이브 검증 완료
- schema, pagination, 인증, rate limit 모두 검증 완료
- Pydantic v2 모델 시안 §2 작성 완료

### 9.2 plan.md로 이관할 결정사항

1. 모듈 경로: `backend/services/naver_theme_v2/` (sibling 디렉토리)
2. 신규 라우트: `/api/themes/v2/snapshot`, `/api/themes/v2/quick`
3. V1 모듈 재사용: `analyzer.py` (import), `db_join.py` (optional fallback)
4. V1 모듈 신규 작성: `config.py`, `crawler.py`, `parser.py`, `service.py`, `__init__.py`
5. analyzer.py를 V2가 import만 하므로 V1 파일은 무수정
6. db_join.py는 detail 응답 `marketValue`가 99% 채워질 것이므로 fallback only
7. test fixture: live blend + synthetic 2종 (V1 §13-7 교훈)

### 9.3 plan.md에서 결정해야 할 항목

1. theme_id 정규화 정책: list 응답 `sectorCode`는 string, V1 schema `theme_id`는 int — `int(sectorCode)` 변환 일괄
2. snapshot 모드 N (top_n_themes) — V1 default = 20 — V2도 동일 default 유지 권장 (frontend 호환)
3. quick 모드 (skip_details=True) — V1과 동일 시그니처. V2 quick은 list endpoint만 호출 (page=1~6, pageSize=50, total=264)
4. 단위 정규화: detail의 `marketValue` (원) → V1 `market_cap` 컬럼(원 단위) 직접 매핑

---

## 10. 검증 — 이 research는 self-contained인가?

- [x] PoC 결과가 명확한가? → §1 4-step (A/B/C/D) 라이브 결과
- [x] schema가 Pydantic 모델로 정리되었는가? → §2.1, §2.2
- [x] 단위 안정성이 검증되었는가? → §2.3 단위 매트릭스
- [x] V1 코드 재이용 vs 신규 작성이 식별되었는가? → §3.1
- [x] cohabitation 전략이 잠금되었는가? → §4 Option γ
- [x] 위험이 enumerate되었는가? → §5 R-1~R-10
- [x] §13 교훈이 plan.md로 핸드오프되었는가? → §8

---

Version: 1.0.0
Document Type: Research artifact (Plan phase output)
Status: Draft, V2 plan에 핸드오프 준비 완료
References:
- `.moai/specs/SPEC-NAVER-THEME-001/v2-handoff.md` (자체 검증 5/5)
- `.moai/specs/SPEC-NAVER-THEME-001/research.md` (V1 코드베이스 분석)
- `.moai/specs/SPEC-NAVER-THEME-001/spec.md` (V1 SPEC v1.0.0)
- live PoC 2026-05-01 12:30~12:42 KST (curl + jq + python3 분석)
