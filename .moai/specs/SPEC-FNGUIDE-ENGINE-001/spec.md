# SPEC-FNGUIDE-ENGINE-001: FnGuide 재무 분석 엔진 검증

## 메타데이터

| 항목 | 값 |
|------|-----|
| SPEC ID | SPEC-FNGUIDE-ENGINE-001 |
| 제목 | FnGuide Financial Analysis Engine Validation |
| 생성일 | 2026-03-05 |
| 상태 | Completed |
| 우선순위 | High |
| 담당 | expert-backend, expert-testing |
| Lifecycle | spec-first |

---

## 1. Environment (환경)

### 1.1 시스템 개요

`fnguide/` 패키지는 FnGuide 웹사이트에서 기업 재무 데이터를 크롤링하고 재무 분석을 수행하는 독립형 Python 모듈이다. 메인 백엔드/프론트엔드와 통합되지 않은 독립 엔진이다.

### 1.2 모듈 구조

| 모듈 | 역할 | 네트워크 의존성 |
|------|------|----------------|
| `fnguide/parser.py` | HTML/JSON 파싱 유틸리티 (순수 함수) | 없음 |
| `fnguide/crawler.py` | FnGuide HTTP 크롤링 | 있음 (FnGuide) |
| `fnguide/analysis.py` | 재무 분석 (fs_analysis, calc_weight_coeff) | 없음 |
| `fnguide/analyzer.py` | 종합 분석 오케스트레이터 (analyze_comp) | 있음 (crawler 경유) |
| `fnguide/__init__.py` | 패키지 export | 없음 |

### 1.3 외부 의존성

- FnGuide 웹사이트 (`comp.fnguide.com`) - 스냅샷, 재무제표, 컨센서스

> **제거된 의존성 (v2.0):** FinanceDataReader (종가/거래량), numpy-financial (RIM 계산)

### 1.4 재무제표 유형

- **IFRS(연결)**: 연결 재무제표 (삼성전자, SK하이닉스 등 대부분 대기업)
- **IFRS(별도)**: 별도 재무제표 (일부 기업, 비지배주주지분 없음)

### 1.5 현재 테스트 상태

- **69 tests** (65 passed, 4 skipped), **93% coverage**
- 원본 코드: `rim_fnguide/rim_fnguide_ver20.py` (2019년 monolithic 스크립트)에서 리팩토링
- v2.0: RIM/FinanceDataReader 제거, ProfitTrend 추가로 패키지 경량화 완료

---

## 2. Assumptions (가정)

### 2.1 기술적 가정

- [A-1] FnGuide 웹사이트 HTML 구조가 테스트 실행 시점에 정상 접근 가능하다
- [A-3] 테스트 대상 종목 코드는 FnGuide에 등록된 상장 기업이다
- ~~[A-4] FinanceDataReader가 해당 종목의 시세 데이터를 정상 반환한다~~ (v2.0에서 제거)

### 2.2 비즈니스 가정

- [A-5] 연결(연결) 기업과 별도(별도) 기업 모두 테스트 커버리지에 포함해야 한다
- [A-6] 재무제표 항목(매입채무, 유형자산 등)은 FnGuide 표준 항목명을 따른다
- ~~[A-7] RIM 가격 검증은 본 SPEC 범위 밖이다~~ (v2.0에서 RIM 기능 자체 제거)

### 2.3 테스트 전략 가정

- [A-8] 모든 크롤링 테스트는 라이브 HTTP 요청을 사용한다 (mock 없음)
- [A-9] 네트워크 의존성이 있는 테스트는 별도 마커(`@pytest.mark.live`)로 구분한다
- [A-10] 파서 유닛 테스트는 네트워크 없이 실행 가능해야 한다

---

## 3. Requirements (요구사항)

### 3.1 Parser 유닛 테스트 (순수 함수, 네트워크 불필요)

**[REQ-P-001] Ubiquitous: 숫자 변환 함수 검증**
시스템은 **항상** `to_num()` 함수가 콤마 포맷 문자열을 올바른 int/float로 변환해야 한다.

- 입력: `"1,234"` -> 출력: `1234` (int)
- 입력: `"1,234.56"` -> 출력: `1234.56` (float)
- 입력: `""` 또는 잘못된 문자열 -> 출력: `0`

**[REQ-P-002] Ubiquitous: DataFrame 문자열-숫자 변환**
시스템은 **항상** `convert_string_to_number()` 함수가 DataFrame의 문자열 셀을 수치형으로 정확히 변환해야 한다.

- `"-"` 문자열 -> `0` (기본) 또는 `NaN` (fillna=NaN 옵션)
- 빈 문자열 -> `0` (기본) 또는 `NaN`
- 콤마 포함 숫자 문자열 -> 수치형

**[REQ-P-003] Ubiquitous: 문자열 정리 함수**
시스템은 **항상** `remove_E()`가 `"(E)"` 접미사를 제거하고, `remove_space()`가 공백을 제거해야 한다.

**[REQ-P-004] Event-Driven: table_parsing 함수 검증**
**WHEN** BeautifulSoup `<table>` Tag가 입력되면 **THEN** `table_parsing()`은 `(account_type, DataFrame)` 튜플을 반환하며, account_type은 `"IFRS(연결)"` 또는 `"IFRS(별도)"` 형식이어야 한다.

### 3.2 Crawler 통합 테스트 (라이브 HTTP)

**[REQ-C-001] Event-Driven: 재무제표 크롤링 (연결)**
**WHEN** IFRS(연결) 종목 코드(예: `005930`)로 `read_fs()`를 호출하면 **THEN** 다음을 반환해야 한다:
- `account_type`이 `"IFRS(연결)"`
- `df_fs_ann`이 4개 이상 컬럼 (`YYYY/MM` 형식)
- `df_fs_quar`이 4개 이상 컬럼
- 주요 재무제표 항목 인덱스 존재: `"매출액"`, `"영업이익"`, `"당기순이익"`, `"자산총계"`, `"부채총계"`, `"자본총계"`

**[REQ-C-002] Event-Driven: 재무제표 크롤링 (별도)**
**WHEN** IFRS(별도) 종목으로 `read_fs()`를 호출하면 **THEN** `account_type`이 `"IFRS(별도)"`이고, 연결과 동일한 기본 구조를 갖되 `"비지배주주지분"` 관련 항목이 없을 수 있다.

**[REQ-C-003] Event-Driven: 스냅샷 크롤링**
**WHEN** 종목 코드로 `read_snapshot()`을 호출하면 **THEN** 다음을 반환해야 한다:
- `report` dict에 필수 키 존재: `"시가총액(상장예정포함,억원)"`, `"발행주식수(보통주)"`, `"발행주식수(우선주)"`, `"자기주식"`, `"PER"`, `"PBR"`
- `report["시가총액(상장예정포함,억원)"]` > 0
- `df_snap`과 `df_snap_ann`이 비어있지 않은 DataFrame

**[REQ-C-004] Event-Driven: 컨센서스 크롤링**
**WHEN** 종목 코드로 `read_consensus()`를 호출하면 **THEN** 다음을 반환해야 한다:
- DataFrame의 인덱스에 재무 항목명 존재
- 컬럼이 `YYYY/MM` 형식의 연도 정보
- 수치형 데이터 (문자열이 아닌 숫자)

**[REQ-C-005] Event-Driven: 통합 크롤링 함수**
**WHEN** `get_fnguide(code)`를 호출하면 **THEN** 7개 요소 튜플을 반환하며, 각 요소가 올바른 타입이어야 한다:
- `(df_fs_ann, df_fs_quar, df_snap, df_snap_ann, df_cons, report, account_type)`

**[REQ-C-006] Unwanted: 잘못된 종목 코드 처리**
시스템은 존재하지 않는 종목 코드(예: `"999999"`)로 크롤링 시 적절한 예외를 발생시키거나, 빈 결과를 반환**하지 않아야 한다** (명시적 에러 처리).

### 3.3 Financial Analysis 로직 테스트

**[REQ-A-001] Event-Driven: fs_analysis 기본 동작**
**WHEN** `read_fs()` 결과를 `fs_analysis()`에 전달하면 **THEN** 다음을 반환해야 한다:
- `df_anal` DataFrame에 필수 행 존재:
  - 자본 구성: `"주주몫"`, `"비지배주주지분"`, `"외부차입"`, `"영업부채"`
  - 자산 구성: `"영업자산"`, `"비영업자산"`
  - 손익: `"영업이익"`, `"비영업이익"`, `"이자비용"`, `"법인세비용"`, `"지배주주순이익"`
  - 이익률: `"영업자산이익률"`, `"비영업자산이익률"`, `"차입이자율"`, `"지배주주ROE"`
- `df_invest` DataFrame에 필수 행 존재: `"설비투자"`, `"운전자산"`, `"금융투자"`, `"여유자금"`

**[REQ-A-002] State-Driven: 이익률 계산 정합성**
**IF** fs_analysis가 정상 수행되면 **THEN** 다음을 만족해야 한다:
- `"영업자산이익률"` 값이 `-1.0 ~ 1.0` 범위 내 (합리적 범위)
- `"차입이자율"` 값이 `0.0 ~ 0.5` 범위 내
- `"지배주주ROE"` 값이 `-1.0 ~ 1.0` 범위 내
- `"가중평균"` 컬럼이 존재하고 NaN이 아님

**[REQ-A-003] State-Driven: 영업자산이익률 1순위 선택 로직**
**IF** 영업자산이익률이 3년간 상승 추세(a < b < c) 또는 하락 추세(a > b > c)이면 **THEN** 1순위 = 최근값(c).
**IF** 추세가 없으면 **THEN** 1순위 = 가중평균.

**[REQ-A-004] Event-Driven: 예상 순이익 추정**
**WHEN** fs_analysis가 이익률 기반으로 예상치를 계산하면 **THEN** `"예상"` 컬럼에 다음 항목이 존재해야 한다:
- `"영업이익"`, `"비영업이익"`, `"이자비용"`, `"법인세비용"`, `"지배주주순이익"`, `"지배주주ROE"`
- 예상 법인세율이 22% 기준으로 계산됨을 검증

**[REQ-A-005] State-Driven: IFRS 별도 처리**
**IF** account_type이 `"IFRS(별도)"`이면 **THEN**:
- `"비지배주주지분"`이 0으로 처리
- `"지배주주순이익"` = `"당기순이익"` (동일값)
- ZeroDivisionError 없이 정상 처리

**[REQ-A-006] Event-Driven: calc_weight_coeff 검증**
**WHEN** 연간 재무제표 컬럼 인덱스가 전달되면 **THEN** 가중평균 계수 `(w1, w2, w3, denom)`을 올바르게 반환해야 한다:
- 12개월 간격: `(1.0, 2.0, 3.0, 6.0)`
- 3개월 간격: `(1.0, 0.5, 3.0, 4.5)`
- 6개월 간격: `(1.0, 1.0, 3.0, 5.0)`
- 9개월 간격: `(1.0, 1.5, 3.0, 5.5)`

### 3.4 End-to-End 분석 테스트

**[REQ-E-001] Event-Driven: analyze_comp 전체 파이프라인**
**WHEN** `analyze_comp("005930")`을 호출하면 **THEN** `CompResult` dataclass를 반환하며:
- `code` == `"005930"`
- `market_cap` > 0
- `shares` > 0
- `trailing_eps` != 0 (삼성전자는 이익 기업)
- `book_value_per_share` > 0
- `profit_trend`가 유효한 `ProfitTrend` (periods >= 4, revenue/op_profit/net_income/op_margin 동일 길이)
- 이익률 추이 (RateHistory) 4개 필드가 모두 유효한 float

**[REQ-E-002] Event-Driven: analyze_comp 복수 종목 검증**
**WHEN** 서로 다른 특성의 종목에 대해 analyze_comp를 호출하면 **THEN** 모든 종목에서 CompResult가 에러 없이 반환되어야 한다:
- 대형주 연결: `005930` (삼성전자)
- 대형주 연결: `000660` (SK하이닉스)
- 중소형 연결: 1개 이상

**[REQ-E-003] Ubiquitous: CompResult 데이터 일관성**
시스템은 **항상** CompResult의 다음 관계가 성립해야 한다:
- `shares` = `발행주식수(보통주)` + `발행주식수(우선주)` - `자기주식`
- `trailing_eps` = Trailing 12M 순이익 / shares * 1억
- `net_cash_ratio` = net_cash / market_cap * 100

---

## 4. Specifications (세부 사양)

### 4.1 테스트 종목 선정

| 유형 | 종목코드 | 종목명 | 회계유형 | 선정 사유 |
|------|---------|--------|---------|----------|
| 대형주 | 005930 | 삼성전자 | IFRS(연결) | 대표 연결 기업, 풍부한 데이터 |
| 대형주 | 000660 | SK하이닉스 | IFRS(연결) | 반도체 업종, 높은 변동성 |
| IFRS 별도 | TBD | TBD | IFRS(별도) | 별도 재무제표 검증용 (테스트 시 확인 필요) |
| 에러 케이스 | 999999 | - | - | 존재하지 않는 종목 코드 |

> 참고: IFRS(별도) 종목은 `read_fs()`의 account_type 반환값으로 식별 가능. 테스트 구현 시 코드 레벨에서 탐색하거나 알려진 별도 종목(예: 지주회사 계열사)을 사용.

### 4.2 테스트 파일 구조

```
tests/fnguide/
    __init__.py
    conftest.py               # 공통 fixture (종목코드, 크롤링 결과 캐시)
    test_parser.py             # [REQ-P-*] Parser 유닛 테스트
    test_crawler.py            # [REQ-C-*] Crawler 통합 테스트 (live)
    test_analysis.py           # [REQ-A-*] Analysis 로직 테스트
    test_analyzer.py           # [REQ-E-*] End-to-end 테스트
```

### 4.3 pytest 마커 설정

```python
# pyproject.toml 또는 conftest.py
markers = [
    "live: 라이브 HTTP 요청이 필요한 테스트",
    "slow: 실행 시간이 긴 테스트 (크롤링 포함)",
]
```

### 4.4 conftest.py 캐싱 전략

라이브 크롤링 테스트의 효율성을 위해 session-scope fixture로 크롤링 결과를 캐시한다:

```python
@pytest.fixture(scope="session")
def samsung_fnguide():
    """삼성전자 FnGuide 전체 데이터 (세션 1회 크롤링)"""
    return get_fnguide("005930")

@pytest.fixture(scope="session")
def samsung_fs():
    """삼성전자 재무제표 (세션 1회 크롤링)"""
    return read_fs("005930")
```

### 4.5 범위 제한

- **포함**: Parser, Crawler, fs_analysis, calc_weight_coeff, analyze_comp, ProfitTrend
- **제거됨 (v2.0)**: RIM 가격 계산 (cal_rim, calculate_historical_rim, price_analysis), FinanceDataReader, get_required_rate
- **제외**: 시각화, 차트 생성
- **제외**: 메인 백엔드/프론트엔드 통합

### 4.6 데이터 무결성 검증 기준

| 검증 항목 | 기준 |
|----------|------|
| DataFrame shape | 최소 행/열 수 충족 |
| 컬럼명 형식 | `YYYY/MM` 패턴 매칭 |
| 수치 범위 | 이익률 -100% ~ +100% |
| 필수 인덱스 | 주요 재무제표 항목명 존재 확인 |
| 타입 검증 | DataFrame 셀이 numeric 타입 |
| NaN 처리 | 예상 위치 외 unexpected NaN 없음 |

---

## 5. Traceability (추적성)

| 요구사항 ID | 테스트 파일 | 테스트 대상 함수 |
|------------|-----------|----------------|
| REQ-P-001 ~ P-003 | test_parser.py | to_num, convert_string_to_number, remove_E, remove_space |
| REQ-P-004 | test_parser.py | table_parsing |
| REQ-C-001 ~ C-002 | test_crawler.py | read_fs |
| REQ-C-003 | test_crawler.py | read_snapshot |
| REQ-C-004 | test_crawler.py | read_consensus |
| REQ-C-005 | test_crawler.py | get_fnguide |
| REQ-C-006 | test_crawler.py | 에러 처리 |
| REQ-A-001 ~ A-006 | test_analysis.py | fs_analysis, calc_weight_coeff |
| REQ-E-001 ~ E-003 | test_analyzer.py | analyze_comp |

---

## Expert Consultation 권고

- **expert-backend**: 크롤링 안정성, 에러 핸들링 패턴, session-scope fixture 설계
- **expert-testing**: 라이브 HTTP 테스트 전략, 데이터 무결성 검증 패턴, 테스트 격리
