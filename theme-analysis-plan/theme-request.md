# \[요청\] 네이버 금융 테마·주도주 분석 모듈 신규 개발

> **요청자**: Jungwon **작성일**: 2026-05-01 **대상**: 기존 Python 백엔드 프로젝트에 신규 모듈로 추가 **구현 도구**: Claude Code

---

## 1. 한 줄 요약

네이버 금융 테마 페이지를 온디맨드로 크롤링하여 **강세 테마**와 **테마별 주도주**를 분석한 결과를 pandas DataFrame으로 반환하는 모듈을 개발해 주세요.

---

## 2. 배경 및 목적

- 네이버 증시 테마(`https://finance.naver.com/sise/theme.naver`)는 시장 자금 흐름을 가장 빠르게 파악할 수 있는 정보원입니다.
- 매일·매시간 수동으로 보기 어려우므로, 호출 한 번으로 "지금 강한 테마 + 그 안의 주도주"를 정리해 주는 모듈이 필요합니다.
- 본 모듈은 **단독 실행이 아니라 기존 Python 백엔드의 한 모듈**로 통합됩니다.

---

## 3. 핵심 요구사항 (반드시 충족)

| ID | 요구사항 |
| --- | --- |
| R1 | 외부 호출 시 1회 크롤링 → 분석 → 결과 반환 (스케줄러 없음, stateless) |
| R2 | 모든 결과는 `pandas.DataFrame`으로 반환 |
| R3 | 매너 크롤링: 호출 간 sleep ≥ 0.5초, 단일 스레드, User-Agent 명시 |
| R4 | EUC-KR 인코딩 정상 처리 (한글 깨짐 없음) |
| R5 | 부분 실패 허용: 일부 테마 파싱 실패해도 모듈 전체가 죽지 않음 |
| R6 | 단일 진입점 함수 1개만 노출 (외부에서 import 단순화) |
| R7 | 데이터 저장은 본 모듈 책임 아님 (호출자 시스템이 처리) |

---

## 4. 수집 대상 데이터

### 4.1 테마 목록 (`themes_df`)

`https://finance.naver.com/sise/theme.naver?&page={n}` 의 모든 페이지를 순회하여 다음 컬럼 수집:

| 컬럼 | 설명 |
| --- | --- |
| theme_id | 테마 상세 URL의 `no` 파라미터 |
| theme_name | 테마명 |
| change_pct | 전일대비 등락률(%) |
| change_pct_3d | 최근 3일 등락률(%) |
| up_count / flat_count / down_count | 상승/보합/하락 종목 수 |
| top_stocks_preview | 목록에 노출된 주도주 미리보기 (참고용) |
| collected_at | 수집 시각 (KST) |

> 페이지네이션 마지막 페이지는 동적으로 탐지하세요 (하드코딩 금지).

### 4.2 종목 상세 (`stocks_df`)

각 테마의 `sise_group_detail.naver?type=theme&no={theme_id}` 페이지에서 종목 리스트 수집:

| 컬럼 | 설명 |
| --- | --- |
| theme_id, theme_name | 소속 테마 |
| stock_code | 6자리 종목코드 |
| stock_name | 종목명 |
| price | 현재가 |
| change | 전일대비 (원) |
| change_pct | 등락률(%) |
| volume | 거래량 |
| trade_value | 거래대금 (원 단위로 정규화) |
| market_cap | 시가총액 (원 단위로 정규화) |
| per | PER (없으면 NaN) |
| roe | ROE (없으면 NaN) |
| collected_at | 수집 시각 |

> **중요**: 시가총액·거래대금이 페이지에 "억", "백만" 등으로 표기되는 경우가 있으니 **원 단위로 통일**해 주세요.

---

## 5. 분석 요구사항

### 5.1 강세 테마 추출 → `strong_themes_df`

- 입력: `themes_df`
- 정렬: `change_pct` 내림차순 상위 N개 (N은 호출 인자, 기본 20)
- 추가 컬럼:
  - `momentum_score` = `change_pct * 0.6 + change_pct_3d * 0.4`
  - `breadth_ratio` = `up_count / (up_count + flat_count + down_count)`

### 5.2 주도주 산출 → `leaders_df`

각 테마 내에서 종목별 점수 계산:

```
leader_score = z(change_pct)*0.40 + z(volume)*0.30 + z(market_cap)*0.20 + z(trade_value)*0.10
```

- `z(x)` = 해당 테마 내 z-score (`(x - mean) / std`, std=0이면 0)
- 음수 등락률은 그대로 반영 (하락 주도주는 음수 점수)
- 테마당 상위 K개 반환 (K는 호출 인자, 기본 3)

반환 컬럼: `theme_id, theme_name, rank, stock_code, stock_name, leader_score, change_pct, volume, market_cap, trade_value`

### 5.3 멀티테마 종목 → `multi_theme_stocks_df`

- `stocks_df`에서 `stock_code` 기준 group by
- 2개 이상 테마에 동시 등장하는 종목 추출
- 컬럼: `stock_code, stock_name, theme_count, theme_names (list), avg_change_pct`

---

## 6. 외부 인터페이스 (필수)

다음 함수 시그니처를 반드시 제공해 주세요. 이름·인자·반환 형태는 그대로 지켜야 합니다.

```python
from modules.naver_theme.service import collect_and_analyze, ThemeAnalysisResult

result: ThemeAnalysisResult = collect_and_analyze(
    top_n_themes=20,        # 강세 테마 상위 N
    leaders_per_theme=3,    # 테마당 주도주 K
    skip_details=False,     # True면 종목 상세 생략 (테마 목록만 빠르게)
    theme_filter=None,      # list[str] 주면 해당 테마명만 수집
)

# 반환 객체 속성
result.themes_df              # pd.DataFrame
result.stocks_df              # pd.DataFrame  (skip_details=True면 빈 DataFrame)
result.strong_themes_df       # pd.DataFrame
result.leaders_df             # pd.DataFrame  (skip_details=True면 빈 DataFrame)
result.multi_theme_stocks_df  # pd.DataFrame  (skip_details=True면 빈 DataFrame)
result.metadata               # dict: collected_at, theme_count, stock_count, elapsed_sec, errors
```

`metadata.errors`는 `[{"theme_id": int, "stage": "list|detail", "reason": str}, ...]` 형식.

---

## 7. 모듈 구조 가이드 (권장)

```
modules/naver_theme/
├── __init__.py
├── service.py      # 진입점 (collect_and_analyze)
├── crawler.py      # HTTP 호출, 페이지 순회
├── parser.py       # HTML → dict/list
├── analyzer.py     # DataFrame 가공, 점수 계산
├── schemas.py      # 데이터 모델
├── config.py       # URL, 헤더, sleep, 가중치 상수
└── tests/
    ├── fixtures/   # 샘플 HTML
    ├── test_parser.py
    └── test_analyzer.py
```

> 디렉토리 위치는 기존 프로젝트 컨벤션에 맞춰 조정 가능. 단 단일 진입점(`service.py`) 원칙은 유지.

---

## 8. 비기능 요구사항

| 항목 | 기준 |
| --- | --- |
| 호출 간 sleep | 0.7초 (config 상수로 노출) |
| 재시도 | 실패 시 1회, 그래도 실패하면 errors에 기록하고 skip |
| 타임아웃 | 10초 |
| User-Agent | 식별 가능한 문자열 (브라우저 위장 금지) |
| 동시 요청 | 금지 (단일 스레드 순차) |
| 로깅 | `logging.getLogger("naver_theme")` 사용, 진행률 INFO, 실패 WARNING |

---

## 9. 의존성

신규로 추가될 라이브러리만 명시해 주세요. 가능한 다음 범위 내에서 해결:

```
requests
beautifulsoup4
lxml
pandas
```

(기존 프로젝트에 이미 있으면 추가 설치 없이 사용)

---

## 10. 인수 조건 (Acceptance Criteria)

다음을 모두 만족해야 완료로 간주합니다.

- \[ \] `collect_and_analyze()` 호출 1회로 5종 DataFrame + metadata 반환
- \[ \] 한글 깨짐 없음 (테마명, 종목명 모두)
- \[ \] 시가총액·거래대금이 원 단위로 통일됨
- \[ \] 주도주 점수 가중치(0.4 / 0.3 / 0.2 / 0.1) 정확히 적용
- \[ \] 페이지네이션 자동 탐지 (페이지 수 하드코딩 없음)
- \[ \] 호출 간 sleep ≥ 0.5초가 실측으로 확인됨
- \[ \] 일부 테마 실패해도 나머지 결과 반환 + errors에 기록
- \[ \] `skip_details=True`로 호출 시 10초 이내 응답 (테마 목록만)
- \[ \] 단위 테스트: 파서·분석기 모두 fixture 기반으로 통과
- \[ \] 외부에서 `from modules.naver_theme.service import collect_and_analyze` 한 줄로 사용 가능
- \[ \] DataFrame 컬럼명·타입이 본 문서와 일치

---

## 11. 명시적으로 제외 (Out of Scope)

다음은 본 작업 범위가 **아닙니다**. 호출 측 시스템에서 처리합니다.

- 데이터베이스 저장 (DataFrame을 그대로 반환만)
- 일별 누적·시계열 분석
- 시각화 (차트, 대시보드)
- 알림 (Slack, 이메일)
- 백테스트
- 스케줄링 (cron, APScheduler 등)
- 인증·권한
- API 엔드포인트 작성 (호출 측에서 자체 구현)

---

## 12. 참고 사항

- 네이버 금융은 정적 HTML 위주이므로 Selenium 불필요. `requests + beautifulsoup4`로 충분합니다.
- 동일 코드를 1초 이내 반복 호출 시 일시 차단될 수 있습니다 → sleep 0.7초가 안전 마진입니다.
- 일부 ETF·우선주는 PER/ROE 컬럼이 비어 있을 수 있습니다 → NaN 처리.
- 종목 상세 페이지는 페이지네이션 없이 한 페이지에 모든 종목이 표시되는 것이 일반적이지만, 혹시 모를 케이스 대비 페이지네이션 체크 로직 포함 권장.

---

## 13. 질문이 있으면 먼저 확인

구현 중 다음 상황이 발생하면 임의 결정하지 말고 요청자에게 확인해 주세요.

- 네이버 페이지 구조가 본 문서와 달라 컬럼이 누락되는 경우
- 시가총액·거래대금 단위가 모호한 경우
- 주도주 점수 산출 시 표본이 너무 작아(n&lt;3) z-score가 무의미한 경우의 처리 방침
- 모듈 디렉토리 위치가 기존 프로젝트 컨벤션과 충돌하는 경우