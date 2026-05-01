# SPEC-NAVER-THEME-001: 네이버 금융 테마 분석 모듈

**Version**: 1.0.0 | **Status**: Approved | **Last Updated**: 2026-05-01

---

## 1. 개요

네이버 금융 테마 페이지를 온디맨드로 크롤링하여 **강세 테마**, **테마별 주도주**, **멀티테마 종목**을 분석하는 Python 모듈. 기존 KR Stock Screener 백엔드에 **읽기 전용 애드온**으로 통합됨.

| 항목 | 설명 |
|------|------|
| **모듈 위치** | `backend/services/naver_theme/` |
| **진입점** | `from modules.naver_theme.service import collect_and_analyze` |
| **반환 타입** | `ThemeAnalysisResult` (5종 DataFrame + metadata) |
| **상태** | stateless, 스케줄러 없음 (온디맨드) |
| **외부 호출 횟수** | ~27회 (0.7초 sleep × 기본값, 약 19초 소요) |
| **빠른 모드** | skip_details=True 시 7회 (약 5초, R10 충족) |

---

## 2. 기능 요구사항 (FR)

### FR-001: 테마 목록 수집

**대상 URL**: `https://finance.naver.com/sise/theme.naver?&page={n}`

**입력**: 없음 (자동 페이지네이션)
**출력**: `themes_df` (pandas.DataFrame)

| 컬럼 | 타입 | 설명 | 필수 |
|------|------|------|------|
| theme_id | int | 테마 고유 ID (no 파라미터) | ✅ |
| theme_name | str | 테마명 | ✅ |
| change_pct | float | 전일대비 등락률(%) | ✅ |
| change_pct_3d | float | 최근 3일 등락률(%) | ✅ |
| up_count | int | 상승 종목 수 | ✅ |
| flat_count | int | 보합 종목 수 | ✅ |
| down_count | int | 하락 종목 수 | ✅ |
| top_stocks_preview | str | 미리보기 종목 문자열 (참고용) | ✅ |
| collected_at | str | 수집 시각 (KST, ISO-8601) | ✅ |

**규칙**:
- 페이지네이션 자동 탐지 (마지막 페이지 하드코딩 금지)
- 모든 페이지 순회 (기본값)
- 한글 깨짐 없음 (UTF-8 검증)

### FR-002: 종목 상세 수집

**대상 URL**: `https://finance.naver.com/sise/sise_group_detail.naver?type=theme&no={theme_id}`

**입력**: `strong_themes_df` (강세 테마 목록)
**출력**: `stocks_df` (pandas.DataFrame)

| 컬럼 | 타입 | 설명 | 단위 |
|------|------|------|------|
| theme_id | int | 소속 테마 ID | - |
| theme_name | str | 소속 테마명 | - |
| stock_code | str | 6자리 종목코드 | - |
| stock_name | str | 종목명 | - |
| price | float | 현재가 | 원 |
| change | float | 전일대비 변화액 | 원 |
| change_pct | float | 등락률 | % |
| volume | int | 거래량 | 주 |
| trade_value | int | 거래대금 | **원** (정규화) |
| market_cap | int | 시가총액 | **원** (DB JOIN) |
| per | float | PER | - |
| roe | float | ROE | - |
| inclusion_reason | str | 편입사유 (선택사항) | - |
| collected_at | str | 수집 시각 (KST) | ISO-8601 |

**규칙**:
- skip_details=True이면 수집 생략 (빈 DataFrame 반환)
- 시가총액 보강: DB JOIN (network call 없음)
  ```sql
  SELECT code, market_cap FROM stock_meta WHERE code IN (...)
  ```
- PER/ROE: NaN 허용 (ETF, 우선주 등)
- 부분 실패 허용 (일부 종목 파싱 실패 시에도 계속 진행)

### FR-003: 강세 테마 추출

**입력**: `themes_df`
**출력**: `strong_themes_df` (pandas.DataFrame)

| 컬럼 | 계산식 | 설명 |
|------|--------|------|
| theme_id | - | 테마 ID |
| theme_name | - | 테마명 |
| change_pct | - | 1일 등락률(%) |
| change_pct_3d | - | 3일 등락률(%) |
| up_count | - | 상승 종목수 |
| flat_count | - | 보합 종목수 |
| down_count | - | 하락 종목수 |
| momentum_score | `change_pct * 0.6 + change_pct_3d * 0.4` | 모멘텀 점수 |
| breadth_ratio | `up_count / (up_count + flat_count + down_count)` | 상승 비율 (0~1) |

**정렬**: change_pct 내림차순 → 상위 N개 (default N=20)

### FR-004: 주도주 산출

**입력**: `stocks_df`
**출력**: `leaders_df` (pandas.DataFrame)

| 컬럼 | 설명 |
|------|------|
| theme_id | 테마 ID |
| theme_name | 테마명 |
| rank | 테마 내 순위 (1~K) |
| stock_code | 종목코드 |
| stock_name | 종목명 |
| leader_score | z-score 가중 점수 |
| change_pct | 등락률(%) |
| volume | 거래량 |
| market_cap | 시가총액 (원) |
| trade_value | 거래대금 (원) |

**leader_score 계산**:
```
leader_score = z(change_pct)*0.40 + z(volume)*0.30 + z(market_cap)*0.20 + z(trade_value)*0.10
```

- `z(x)` = `(x - mean) / std` (테마별 표준화)
- std = 0이면 z = 0
- 음수 등락률 그대로 반영 (음수 점수 가능)
- 테마당 상위 K개 (default K=3)
- 정렬: leader_score 내림차순

### FR-005: 멀티테마 종목 추출

**입력**: `stocks_df`
**출력**: `multi_theme_stocks_df` (pandas.DataFrame)

| 컬럼 | 설명 |
|------|------|
| stock_code | 종목코드 |
| stock_name | 종목명 |
| theme_count | 등장한 테마 수 |
| theme_names | 테마명 리스트 |
| avg_change_pct | 평균 등락률(%) |

**규칙**:
- theme_count >= 2인 종목만 포함
- theme_names는 배열 또는 콤마 구분 문자열
- avg_change_pct = 해당 종목이 등장한 모든 테마에서의 등락률 평균

### FR-006: 메타데이터 반환

**출력**: `metadata` (dict)

```python
{
  "collected_at": "2026-05-01T13:30:00+09:00",  # ISO-8601 KST
  "theme_count": 42,                           # 수집된 테마 총 수
  "stock_count": 285,                          # 수집된 종목 총 수
  "elapsed_sec": 19.3,                         # 소요 시간
  "errors": [
    {
      "theme_id": 123,
      "stage": "list",  # 또는 "detail"
      "reason": "HTTP 429 after 2 retries"
    },
    # ...
  ]
}
```

---

## 3. 비기능 요구사항 (NFR)

### NFR-001: 성능

| 항목 | 기준 |
|------|------|
| 기본 호출 | 19초 이내 (27회 크롤링 + 0.7초 sleep) |
| skip_details=True | 5초 이내 (7회 크롤링) |
| 타임아웃 | 10초/호출 (재시도 포함) |

### NFR-002: 안정성

| 항목 | 기준 |
|------|------|
| 부분 실패 | 일부 테마/종목 실패해도 진행 (errors에 기록) |
| 재시도 | 실패 시 1회 재시도, 실패 시 skip |
| 단일 스레드 | 동시 요청 금지 |
| 매너 크롤링 | 호출 간 sleep >= 0.7초 |

### NFR-003: 데이터 품질

| 항목 | 기준 |
|------|------|
| 인코딩 | UTF-8, 한글 깨짐 없음 |
| 숫자 단위 | 모든 금액/거래량 원 단위로 통일 |
| NaN 처리 | PER/ROE/market_cap 미보유 시 NaN |
| 타임스탬프 | ISO-8601 KST |

### NFR-004: 라이브러리

- requests >= 2.28 (HTTP + Retry)
- beautifulsoup4 >= 4.12 (HTML 파싱)
- lxml >= 4.9 (파서)
- pandas >= 2.0 (DataFrame)
- numpy >= 1.24 (z-score)

### NFR-005: 라우팅 (FastAPI)

| 엔드포인트 | 메서드 | 인자 | 응답 |
|-----------|--------|------|------|
| `/api/themes/snapshot` | GET | top_n, leaders_per_theme | 5종 DF JSON |
| `/api/themes/quick` | GET | top_n, leaders_per_theme | themes_df + strong_themes_df |
| `/api/themes/by-stock/{code}` | GET | - | 종목의 테마 리스트 |

---

## 4. 외부 인터페이스

### 4.1 Python API (핵심)

```python
from modules.naver_theme.service import collect_and_analyze, ThemeAnalysisResult

result: ThemeAnalysisResult = collect_and_analyze(
    top_n_themes: int = 20,
    leaders_per_theme: int = 3,
    skip_details: bool = False,
    theme_filter: list[str] | None = None,
)

# 속성 접근
result.themes_df              # DataFrame
result.stocks_df             # DataFrame (skip_details=True면 빈 DF)
result.strong_themes_df      # DataFrame
result.leaders_df            # DataFrame (skip_details=True면 빈 DF)
result.multi_theme_stocks_df # DataFrame (skip_details=True면 빈 DF)
result.metadata              # dict
```

### 4.2 Pydantic 모델

```python
class ThemeAnalysisResult(BaseModel):
    themes_df: dict              # {columns: [...], data: [[...]]}
    stocks_df: dict
    strong_themes_df: dict
    leaders_df: dict
    multi_theme_stocks_df: dict
    metadata: dict
```

---

## 5. 기술 제약사항

### 5.1 DB 의존성 (READ-ONLY)

- **DB**: `/Output/stock_data_daily.db`
- **테이블**: `stock_meta`
- **컬럼**: `code (TEXT)`, `market_cap (INTEGER, 원 단위)`
- **쿼리 모드**: SELECT only (UPDATE/INSERT 금지)
- **갱신 주기**: 기존 DB 갱신 메커니즘에 의존 (우리 책임 아님)

### 5.2 네이버 ToS

- **User-Agent**: 식별 가능한 문자열 (브라우저 위장 금지)
  - 예: `KR-Stock-Screener/1.0 (naver_theme_analysis)`
- **크롤링 간격**: 0.7초 (0.5초 권고 상한보다 안전 마진)
- **동시 요청**: 금지 (단일 스레드)
- **재시도**: 최대 1회 (429 포함)

### 5.3 외부 API 호출 금지

- ❌ FnGuide 또는 기타 금융 데이터 API
- ❌ 시가총액 추가 크롤링 (DB JOIN으로 대체)
- ❌ PER/ROE 추가 크롤링 (NaN 허용)

---

## 6. 모듈 구조

```
backend/services/naver_theme/
├── __init__.py           # 단일 진입점 (collect_and_analyze 노출)
├── service.py            # ThemeAnalysisResult + collect_and_analyze()
├── crawler.py            # HTTP 호출, 페이지 순회
├── parser.py             # HTML → dict/list
├── analyzer.py           # DataFrame 가공, z-score 계산
├── schemas.py            # Pydantic 모델
├── config.py             # URL, 헤더, sleep, 가중치 상수
└── tests/
    ├── fixtures/         # 샘플 HTML
    ├── test_parser.py    # 단위 테스트
    └── test_analyzer.py  # 분석 로직 테스트

backend/routers/
└── themes.py             # GET /api/themes/* 엔드포인트

frontend/src/
├── components/ThemeAnalysis/   # 신규 탭
│   ├── ThemeAnalysis.tsx
│   ├── ThemeRankingTable.tsx
│   └── ThemeDetailPanel.tsx
├── api/themes.ts               # API 클라이언트
└── types/market.ts             # TabId 확장
```

---

## 7. 인수 조건 (AC)

모두 충족해야 V1 완료로 간주:

- [ ] AC-1: `collect_and_analyze()` 호출 1회로 5종 DataFrame + metadata 반환
- [ ] AC-2: 한글 깨짐 없음 (테마명, 종목명 모두)
- [ ] AC-3: 시가총액·거래대금이 원 단위로 통일됨
- [ ] AC-4: 주도주 점수 가중치(0.4 / 0.3 / 0.2 / 0.1) 정확히 적용
- [ ] AC-5: 페이지네이션 자동 탐지 (페이지 수 하드코딩 없음)
- [ ] AC-6: 호출 간 sleep ≥ 0.7초가 실측으로 확인됨
- [ ] AC-7: 일부 테마 실패해도 나머지 결과 반환 + errors에 기록
- [ ] AC-8: `skip_details=True`로 호출 시 10초 이내 응답
- [ ] AC-9: 단위 테스트: parser·analyzer 모두 fixture 기반으로 통과
- [ ] AC-10: 외부 사용 가능: `from modules.naver_theme.service import collect_and_analyze`

---

## 8. 범위 (Out of Scope)

다음은 **본 SPEC 범위가 아님** (호출자가 처리):

- 데이터베이스 저장 (DataFrame을 그대로 반환만)
- 일별 누적·시계열 분석
- 시각화 (차트, 대시보드는 프론트엔드에서)
- 알림 (Slack, 이메일)
- 백테스트
- 스케줄링 (cron, APScheduler)
- 인증·권한

---

## 9. 참고 문서

- **요청 원본**: `theme-analysis-plan/theme-request.md`
- **전략 문서**: `theme-analysis-plan/theme-strategy.md`
- **기술 리서치**: `theme-analysis-plan/research.md`

