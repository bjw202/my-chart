# SPEC-NAVER-THEME-001: 네이버 금융 테마 분석 모듈 (V1 MVP)

## 메타데이터

| 항목 | 값 |
| --- | --- |
| SPEC ID | SPEC-NAVER-THEME-001 |
| 제목 | Naver Finance Theme Analysis Module (Read-Only Add-On) |
| 생성일 | 2026-05-01 |
| 상태 | Implemented |
| 우선순위 | High |
| 담당 | expert-backend, expert-frontend, expert-testing |
| Lifecycle | spec-anchored |
| 버전 | 1.0.0 |

---

## HISTORY

- 2026-05-01 v1.0.0 Implemented: /moai run --team RUN phase 완료. commit 12d81b1. 14개 AC 전체 PASS, 단위 테스트 51개, 커버리지 99%. 라이브 셀렉터 부정합 hotfix(`td a.tltle, td a[href*='code=']`) 포함. V2 핸드오프 노트는 v2-handoff.md 참조.
- 2026-05-01 v1.0.0 Approved: 12건 결함 교정 (모듈 경로, 인코딩, 컬럼 매핑, theme_id 추출, V1 범위, inclusion_reason, DB mtime AC, 4탭 회귀 AC, 시간추정 제거, surgical mod 경계 AC, read-only URI, Draft 상태) 후 사용자 최종 승인. 잔존 progress.md/tasks.md 삭제. /moai run 진행 준비 완료.
- 2026-05-01 v1.0.0: 초안 작성. EUC-KR 인코딩, `backend.services.naver_theme` 모듈 경로, V1 MVP 범위 (`/api/themes/snapshot`, `/api/themes/quick`) 확정.

---

## 1. Environment (환경)

### 1.1 시스템 개요

`backend/services/naver_theme/` 패키지는 네이버 금융 테마 페이지(`https://finance.naver.com/sise/theme.naver`)를 **온디맨드로 크롤링**하여 강세 테마, 테마별 주도주, 멀티테마 종목을 분석한다. 본 모듈은 **읽기 전용 애드온**으로 기존 KR Stock Screener 백엔드에 통합된다.

| 항목 | 값 |
| --- | --- |
| 모듈 경로 | `backend/services/naver_theme/` |
| 단일 진입점 | `from backend.services.naver_theme import collect_and_analyze, ThemeAnalysisResult` |
| 반환 타입 | `ThemeAnalysisResult` (5종 DataFrame + metadata) |
| 실행 모델 | stateless, 스케줄러 없음 (호출 1회당 1 사이클) |
| 외부 호출 횟수 (기본) | 약 27회 (테마 목록 N페이지 + 강세 테마 20개 상세) |
| 빠른 모드 (`skip_details=True`) | 약 7회 (테마 목록만), 10초 이내 응답 |

### 1.2 모듈 내부 구조

| 파일 | 역할 | 네트워크 의존성 |
| --- | --- | --- |
| `service.py` | 단일 진입점 (`collect_and_analyze`), 오케스트레이션 | 간접 (crawler 경유) |
| `crawler.py` | HTTP 호출, Session 싱글톤 + Retry | 있음 (네이버) |
| `parser.py` | HTML → dict/list 변환 (EUC-KR 강제) | 없음 |
| `analyzer.py` | DataFrame 가공, z-score 기반 점수 계산 | 없음 |
| `db_join.py` | `stock_meta.market_cap` JOIN (read-only) | 없음 (로컬 DB) |
| `schemas.py` | Pydantic 모델 (`ThemeAnalysisResult` 직렬화) | 없음 |
| `config.py` | URL, 헤더, sleep, 가중치 상수 | 없음 |

### 1.3 외부 의존성 (기설치, 신규 추가 없음)

- `requests >= 2.28` (HTTP + Retry)
- `beautifulsoup4 >= 4.12` (HTML 파싱)
- `lxml >= 4.9` (파서 엔진)
- `pandas >= 2.0` (DataFrame)
- `numpy >= 1.24` (z-score)
- `fastapi >= 0.115`, `pydantic` (라우터)

### 1.4 영향 범위 (애드온 경계)

| 영역 | 변경 유형 | 비고 |
| --- | --- | --- |
| 신규 파일 | 추가 | `backend/services/naver_theme/`, `backend/routers/themes.py`, `frontend/src/components/ThemeAnalysis/`, `frontend/src/api/themes.ts` |
| `backend/main.py` | 1 import + 1 include_router (총 2줄) | 라우터 등록만 |
| `frontend/src/types/market.ts` | TabId union에 `'theme-analysis'` 추가 (1줄) | 타입 확장 |
| `frontend/src/components/TabNavigation/TabNavigation.tsx` | TABS 배열에 1행 추가 | 탭 진입점 |
| `frontend/src/AppContent.tsx` | 신규 case 1개 (조건부 렌더링) | 마운트 |
| 기존 4탭 (Market/Sector/Stock/Chart) | 무수정 | 회귀 없음 |
| Master DB (`stock_data_daily.db`) | SELECT only | INSERT/UPDATE/DELETE/CREATE/DROP 금지 |

---

## 2. Assumptions (가정)

### 2.1 기술적 가정

- \[A-1\] 네이버 금융 테마 목록/상세 페이지 HTML 구조가 호출 시점에 정상 접근 가능하다
- \[A-2\] 네이버 금융은 정적 HTML이므로 `requests + beautifulsoup4`로 충분 (Selenium 불필요)
- \[A-3\] **네이버 페이지는 EUC-KR 인코딩으로 응답한다.** Content-Type 헤더에 charset이 명시되지 않을 수 있으므로 `Response.encoding`을 명시적으로 `'euc-kr'`로 강제해야 한다 (실측 검증 결과)
- \[A-4\] `Output/stock_data_daily.db`의 `stock_meta` 테이블은 `code (TEXT)`, `market_cap (INTEGER, 원 단위)` 컬럼을 보유하며, 외부 갱신 메커니즘에 의해 최신 상태로 유지된다
- \[A-5\] 테마 상세 페이지에는 PER/ROE 컬럼이 **노출되지 않는다** (실측 확인). PER/ROE는 NaN으로 고정한다
- \[A-6\] 테마 상세 페이지의 종목 행은 다음 컬럼 순서를 따른다 (실측 검증):

| td 인덱스 | 의미 |
| --- | --- |
| `td[0]` | 종목명 (`a.tltle` 앵커, `code`는 `href="...?code=DDDDDD"`에서 정규식 추출) |
| `td[1]` | 편입사유 텍스트 |
| `td[2]` | 현재가 |
| `td[3]` | 전일비 |
| `td[4]` | 등락률 |
| `td[5]` | 매수호가 |
| `td[6]` | 매도호가 |
| `td[7]` | 거래량 |
| `td[8]` | 거래대금 |
| `td[9]` | 전일거래량 |

- \[A-7\] 테마 목록 페이지의 `theme_id`는 행의 `td.col_type1 a` 앵커 `href` 속성에 `?no=(\d+)` 형태로 포함된다

### 2.2 비즈니스 가정

- \[A-8\] 호출자(라우터 레벨)에서 메모리 dict 기반 TTL 캐싱을 수행한다. 본 모듈은 stateless이며 캐싱·DB 저장은 책임 범위 외이다
- \[A-9\] 시가총액 보강은 **DB JOIN (read-only)** 으로 충당하며, 네이버에서 시가총액을 추가 크롤링하지 않는다
- \[A-10\] 사용자는 Market Overview / Sector Analysis / Stock Explorer / Chart Grid 4탭의 기능 회귀를 허용하지 않는다 (애드온 무결성)

### 2.3 테스트 전략 가정

- \[A-11\] 파서·분석기 단위 테스트는 fixture HTML로 네트워크 없이 실행 가능해야 한다
- \[A-12\] 라이브 크롤링 테스트는 `@pytest.mark.live` 또는 `@pytest.mark.slow` 마커로 격리한다

---

## 3. Requirements (EARS 형식)

### 3.1 기능 요구사항 (Functional)

#### REQ-NT-001 (Ubiquitous): 단일 진입점 노출

The system **shall** expose a single entry point `collect_and_analyze` from `backend.services.naver_theme`.

- 시그니처: `collect_and_analyze(top_n_themes: int = 20, leaders_per_theme: int = 3, skip_details: bool = False, theme_filter: list[str] | None = None) -> ThemeAnalysisResult`
- `from backend.services.naver_theme import collect_and_analyze, ThemeAnalysisResult` 한 줄로 사용 가능

#### REQ-NT-002 (Event-Driven): 테마 목록 수집

**WHEN** `collect_and_analyze`가 호출되면, **THEN** 시스템은 `https://finance.naver.com/sise/theme.naver?&page={n}`의 모든 페이지를 순회하여 `themes_df`(`pd.DataFrame`)를 생성해야 한다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `theme_id` | int | 테마 행 앵커 `href`의 `?no=(\d+)` 정규식 추출 결과 |
| `theme_name` | str | 테마명 |
| `change_pct` | float | 전일대비 등락률(%) |
| `change_pct_3d` | float | 최근 3일 등락률(%) |
| `up_count` | int | 상승 종목 수 |
| `flat_count` | int | 보합 종목 수 |
| `down_count` | int | 하락 종목 수 |
| `top_stocks_preview` | str | 미리보기 종목 (참고용) |
| `collected_at` | str | 수집 시각 (KST, ISO-8601) |

#### REQ-NT-003 (Ubiquitous): 페이지네이션 자동 탐지

The system **shall** detect the last page dynamically from the first page's pagination block (페이지 수 하드코딩 금지).

- 첫 페이지를 fetch → 파서가 `last_page`를 추출 → `range(2, last_page + 1)`로 후속 페이지 순회
- `last_page = 1` 같은 초기값을 그대로 사용하여 1회만 도는 루프 버그를 방지해야 한다

#### REQ-NT-004 (State-Driven): skip_details 빠른 모드

**WHILE** `skip_details == True`, **the system shall** skip theme detail crawling and return empty DataFrames for `stocks_df`, `leaders_df`, `multi_theme_stocks_df`.

- `themes_df`, `strong_themes_df`만 채워진 상태로 반환
- 응답 시간 ≤ 10초

#### REQ-NT-005 (Event-Driven): 강세 테마 추출

**WHEN** `themes_df`가 생성되면, **THEN** 시스템은 다음 규칙으로 `strong_themes_df`를 생성해야 한다.

- `change_pct` 내림차순 → 상위 `top_n_themes`개 (기본 20)
- 추가 컬럼:
  - `momentum_score = change_pct * 0.6 + change_pct_3d * 0.4`
  - `breadth_ratio = up_count / (up_count + flat_count + down_count)` (분모 0이면 0으로 fillna)

#### REQ-NT-006 (Event-Driven): 테마 상세 수집

**WHEN** `skip_details == False`이고 `strong_themes_df`가 비어있지 않으면, **THEN** 시스템은 각 강세 테마에 대해 `https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}`를 fetch하여 `stocks_df`를 생성해야 한다.

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `theme_id` | int | 소속 테마 ID |
| `theme_name` | str | 소속 테마명 |
| `stock_code` | str | 6자리 종목코드 (앵커 href에서 추출) |
| `stock_name` | str | 종목명 |
| `inclusion_reason` | str | 편입사유 텍스트 (REQ-NT-008 참조) |
| `price` | float | 현재가 (`td[2]`) |
| `change` | float | 전일비 (`td[3]`) |
| `change_pct` | float | 등락률(%) (`td[4]`) |
| `volume` | int | 거래량 (`td[7]`) |
| `trade_value` | int | 거래대금, **원 단위로 정규화** (`td[8]`) |
| `market_cap` | int | 시가총액, **DB JOIN으로 보강** (REQ-NT-007) |
| `per` | float | NaN 고정 (상세 페이지 미노출, A-5) |
| `roe` | float | NaN 고정 (상세 페이지 미노출, A-5) |
| `collected_at` | str | 수집 시각 (KST) |

- 부분 실패 허용 (REQ-NT-013)

#### REQ-NT-007 (Ubiquitous): 시가총액 DB JOIN 보강 (READ-ONLY)

The system **shall** enrich `stocks_df.market_cap` by SELECT-only JOIN against `stock_meta` in `Output/stock_data_daily.db`.

- 쿼리: `SELECT code, market_cap FROM stock_meta WHERE code IN (?, ?, ...)`
- 연결 모드: SQLite URI `mode=ro` 강제 (`sqlite3.connect(f"file:{path}?mode=ro", uri=True)`)
- DB에 없는 코드는 `market_cap = NaN` (LEFT JOIN 의미)

#### REQ-NT-008 (Ubiquitous): 편입사유 컬럼 보존

The system **shall** capture `inclusion_reason` from the second cell (`td[1]`) of each stock row in the theme detail page and persist it as a column of `stocks_df`.

- UX 차별화 포인트 (테마 상세 패널에서 툴팁/말풍선으로 노출)
- 빈 문자열 또는 미존재 시 빈 string으로 fallback

#### REQ-NT-009 (Event-Driven): 주도주 산출

**WHEN** `stocks_df`가 비어있지 않으면, **THEN** 시스템은 테마별로 z-score 기반 `leader_score`를 계산하여 `leaders_df`를 생성해야 한다.

```
leader_score = z(change_pct)*0.40 + z(volume)*0.30 + z(market_cap)*0.20 + z(trade_value)*0.10
```

- `z(x) = (x - mean) / std` (테마별 표준화)
- `std == 0`이면 `z(x) = 0`
- `market_cap == NaN`이면 해당 z-score는 0으로 처리
- 음수 등락률은 그대로 반영 (음수 점수 가능)
- 테마당 상위 `leaders_per_theme`개 (기본 3)
- 정렬: `leader_score` 내림차순 → `rank` 1..K 부여

#### REQ-NT-010 (Event-Driven): 멀티테마 종목 추출

**WHEN** `stocks_df`가 비어있지 않으면, **THEN** 시스템은 `stock_code` 기준 group by로 `multi_theme_stocks_df`를 생성해야 한다.

| 컬럼 | 설명 |
| --- | --- |
| `stock_code` | 종목코드 |
| `stock_name` | 종목명 |
| `theme_count` | 등장 테마 수 (중복 제거 기준) |
| `theme_names` | 등장 테마 리스트 (중복 제거 + 정렬) |
| `avg_change_pct` | 등장한 테마들에서의 등락률 평균 |

- `theme_count >= 2`인 종목만 포함
- 동일 종목·동일 테마 중복 행이 발생할 수 있으므로 `theme_names`는 `sorted(set(x))`로 중복 제거 후 list 변환
- `theme_count`는 `nunique()` 또는 dedup 후 `len()`으로 계산

#### REQ-NT-011 (Ubiquitous): metadata 반환

The system **shall** return a `metadata` dict containing `collected_at` (KST ISO-8601), `theme_count`, `stock_count`, `elapsed_sec`, `errors`.

```
errors: list[{"theme_id": int | None, "stage": "list" | "detail", "reason": str}]
```

### 3.2 비기능 요구사항 (Non-Functional)

#### REQ-NT-NF-001 (Ubiquitous): 매너 크롤링

The system **shall** sleep `>= 0.7s` between HTTP requests, use a single thread, and identify itself with `User-Agent: KR-Stock-Screener/1.0 (naver_theme_analysis)`.

- 브라우저 위장 금지
- 동시 요청 금지

#### REQ-NT-NF-002 (Ubiquitous): EUC-KR 인코딩

The system **shall** force-set `requests.Response.encoding = 'euc-kr'` before parsing HTML body.

- 네이버 금융 페이지는 EUC-KR로 응답한다
- Content-Type charset이 누락되면 requests는 ISO-8859-1로 추정하여 한글이 깨진다 (검증됨)
- 명시적 설정 없이 BeautifulSoup에 통과시키면 안 된다

#### REQ-NT-NF-003 (Event-Driven): 재시도 + 부분 실패 허용

**WHEN** an HTTP request fails, **THEN** the system **shall** retry once via `urllib3.util.Retry`, and on persistent failure log to `metadata.errors` and continue processing remaining items.

- 재시도 대상 status: 429, 500, 502, 503, 504
- 타임아웃: 10초/요청 (재시도 포함)
- 부분 실패가 발생해도 다른 테마/종목은 계속 처리

#### REQ-NT-NF-004 (Ubiquitous): 응답 시간

The system **shall** complete a full snapshot within \~30s (default) and a quick-mode (`skip_details=True`) within 10s.

#### REQ-NT-NF-005 (Ubiquitous): 데이터 품질

| 항목 | 기준 |
| --- | --- |
| 한글 깨짐 | 없음 (EUC-KR 강제 후) |
| 숫자 단위 | 금액·거래대금 모두 원 단위로 통일 |
| NaN 처리 | PER/ROE/누락 market_cap 시 NaN |
| 타임스탬프 | ISO-8601 KST |

### 3.3 제약 (Constraints)

#### REQ-NT-C-001 (If-Then Unwanted): DB 무수정

**IF** the system attempts INSERT, UPDATE, DELETE, CREATE, DROP, ALTER on any SQLite DB, **THEN** the operation **shall** be rejected.

- 강제 메커니즘: read-only URI 모드 (`mode=ro`)로 연결
- 본 모듈에는 SELECT 외 SQL을 작성하지 않는다

#### REQ-NT-C-002 (Ubiquitous): 기존 4탭 회귀 없음

The system **shall not** modify behavior of Market Overview / Sector Analysis / Stock Explorer / Chart Grid tabs.

- 기존 백엔드 라우터, 프론트엔드 컴포넌트, 타입 정의의 의미적 변경 금지
- 변경되는 기존 파일은 다음 4개로 한정:
  - `backend/main.py` (라우터 등록 2줄)
  - `frontend/src/types/market.ts` (TabId union에 `'theme-analysis'` 추가, 1줄)
  - `frontend/src/components/TabNavigation/TabNavigation.tsx` (TABS 배열에 1행 추가)
  - `frontend/src/AppContent.tsx` (조건부 렌더링 1 case 추가)
- 위 4개 파일에서의 변경 줄 수 합계 ≤ 10줄 (surgical mod)

#### REQ-NT-C-003 (Ubiquitous): 신규 의존성 추가 금지

The system **shall not** introduce new pip dependencies. All required libraries (`requests`, `beautifulsoup4`, `lxml`, `pandas`, `numpy`, `fastapi`, `pydantic`) are already installed.

#### REQ-NT-C-004 (Ubiquitous): Stateless

The system **shall not** persist any data to disk or in-process global state across calls. Caching is the caller's responsibility (router-level memory dict TTL).

### 3.4 라우팅 (FastAPI, V1 범위)

#### REQ-NT-R-001 (Event-Driven): /api/themes/snapshot

**WHEN** `GET /api/themes/snapshot?top_n=...&leaders_per_theme=...`를 받으면, **THEN** 시스템은 5종 DataFrame + metadata를 records list 형식 JSON으로 반환해야 한다.

#### REQ-NT-R-002 (Event-Driven): /api/themes/quick

**WHEN** `GET /api/themes/quick?top_n=...`를 받으면, **THEN** 시스템은 `skip_details=True`로 호출하여 `themes`, `strong_themes`, `metadata`만 반환해야 한다 (10초 이내).

> V1에서는 `/api/themes/by-stock/{code}` 엔드포인트를 제공하지 **않는다** (Out-of-scope §6 참조).

---

## 4. Acceptance Criteria (요약)

상세 시나리오는 `acceptance.md` 참조. 14개 AC 모두 통과 시 V1 완료.

- AC-1: 5종 DataFrame + metadata 반환
- AC-2: EUC-KR 인코딩 정상 처리 (한글 깨짐 없음)
- AC-3: market_cap·trade_value 원 단위 통일
- AC-4: leader_score 가중치 (0.40/0.30/0.20/0.10) 정확
- AC-5: 페이지네이션 자동 탐지
- AC-6: 호출 간 sleep ≥ 0.7초 실측
- AC-7: 부분 실패 허용 + errors 기록
- AC-8: skip_details=True 시 10초 이내
- AC-9: 단위 테스트 (parser, analyzer) 통과 + 커버리지 ≥ 85%
- AC-10: 외부 import 1줄로 사용 가능 (`from backend.services.naver_theme import collect_and_analyze`)
- AC-11: DB 무수정 (`stock_data_daily.db` mtime 무변경, REQ-NT-C-001)
- AC-12: 기존 4탭 회귀 없음 (REQ-NT-C-002)
- AC-13: `inclusion_reason` 컬럼 fixture 검증 (REQ-NT-008)
- AC-14: 기존 파일 surgical mod 경계 (≤ 10줄 합계, REQ-NT-C-002)

---

## 5. 참조 문서

- 전략: `theme-analysis-plan/theme-strategy.md` (확정 입력값 11개 source-of-truth)
- 요청: `theme-analysis-plan/theme-request.md` (R1\~R10)
- 리서치: `theme-analysis-plan/research.md` (코드베이스 깊이 탐사)
- 본 SPEC 동반 문서: `plan.md` (구현 계획), `acceptance.md` (인수 시나리오), `research.md` (요약 리서치)

---

## 6. Exclusions (What NOT to Build)

다음 항목은 **본 SPEC V1 범위가 아니며**, 명시적으로 미구현한다.

### 6.1 V1.5로 분류 (후속 SPEC에서 다룸)

- `GET /api/themes/by-stock/{code}` 엔드포인트 — 종목 → 소속 테마 reverse index
- `frontend/src/components/MarketOverview/HotThemesStrip.tsx` — Market Overview 상단 핫 테마 스트립
- `frontend/src/components/StockList/ThemeChips.tsx` — Stock Explorer/Chart Grid에 부착되는 테마 칩
- `CrossTabParams.themeId / themeName` 필드 추가 (필요 시 V1.5에서 확장)

### 6.2 V2 이후

- 일별 시계열 누적 (parquet/sqlite 저장)
- 시계열 차트 (`ThemeBumpChart`, `ThemeBubbleChart`)
- "어제 대비 부상한 테마" Banner
- Rising Themes 알고리즘
- AI 코멘트 자동 생성 (V3)

### 6.3 영구 제외

- DB INSERT/UPDATE/DELETE/CREATE/DROP/ALTER (REQ-NT-C-001)
- 신규 pip 의존성 추가 (REQ-NT-C-003)
- 본 모듈 내부 캐싱·DB 저장 (REQ-NT-C-004)
- 일별 누적·시계열 분석 (V2 위임)
- 시각화 (프론트엔드 책임)
- 알림 (Slack, 이메일)
- 백테스트
- 스케줄링 (cron, APScheduler)
- 인증·권한
- 외부 API 호출 (FnGuide, 시총 추가 크롤링 등 — DB JOIN으로 충당)
- PER/ROE 추가 크롤링 (NaN 고정, A-5)
- 기존 4탭 (Market Overview / Sector Analysis / Stock Explorer / Chart Grid) 동작 변경 (REQ-NT-C-002)