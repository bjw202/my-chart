# fnguide 패키지 API 레퍼런스

> FnGuide 웹사이트에서 기업 재무 데이터를 크롤링하고 재무건전성을 분석하는 독립형 Python 패키지.

## 패키지 구조

```
fnguide/
├── __init__.py      # 패키지 export
├── parser.py        # HTML/JSON 파싱 유틸리티 (순수 함수, 네트워크 불필요)
├── crawler.py       # FnGuide HTTP 크롤링 (comp.fnguide.com)
├── analysis.py      # 재무 분석 로직 (fs_analysis, calc_weight_coeff)
└── analyzer.py      # 종합 분석 오케스트레이터 (analyze_comp → CompResult)
```

## 외부 의존성

| 의존성 | 용도 |
|--------|------|
| `pandas` | DataFrame 기반 재무 데이터 처리 |
| `requests` | FnGuide HTTP 크롤링 |
| `beautifulsoup4` | HTML 파싱 |
| `lxml` | XPath 기반 HTML 파싱 |
| `numpy` | 수치 연산 (parser.py) |

---

## 핵심 함수

### 1. analyze_comp(code) → CompResult

**종목 재무상태 종합 분석 (최상위 API)**

```python
from fnguide import analyze_comp
result = analyze_comp("005930")  # 삼성전자
print(result)  # 텍스트 요약 출력
```

내부적으로 `get_fnguide()` → `fs_analysis()` 순서로 호출하여 CompResult를 반환한다.

### 2. get_fnguide(code) → 7-tuple

**FnGuide 전체 데이터 수집 통합 함수**

```python
from fnguide import get_fnguide
df_fs_ann, df_fs_quar, df_snap, df_snap_ann, df_cons, report, account_type = get_fnguide("005930")
```

반환값:
- `df_fs_ann`: 연간 재무제표 DataFrame (손익+재무상태+현금흐름)
- `df_fs_quar`: 분기 재무제표 DataFrame
- `df_snap`: 분기 스냅샷 DataFrame
- `df_snap_ann`: 연간 스냅샷 DataFrame
- `df_cons`: 컨센서스 DataFrame (연간 예상치)
- `report`: 시가총액, 발행주식수, PER, PBR 등 주요 지표 dict
- `account_type`: `"IFRS(연결)"` 또는 `"IFRS(별도)"`

### 3. fs_analysis(df_fs_ann, df_fs_quar) → (df_anal, df_invest)

**재무제표 기반 자금조달/자산/손익 분석**

```python
from fnguide import fs_analysis
df_anal, df_invest = fs_analysis(df_fs_ann, df_fs_quar)
```

df_anal 주요 행:
- 자본 구성: `주주몫`, `비지배주주지분`, `외부차입`, `영업부채`
- 자산 구성: `영업자산`, `비영업자산`
- 손익: `영업이익`, `비영업이익`, `이자비용`, `법인세비용`, `지배주주순이익`, `비지배주주순이익`
- 이익률: `영업자산이익률`, `비영업자산이익률`, `차입이자율`, `지배주주ROE`
- 특수 컬럼: `가중평균`, `1순위`, `예상`

df_invest 주요 행:
- `설비투자`, `운전자산`, `금융투자`, `여유자금`

---

## 크롤링 함수 (개별)

### read_fs(code) → (account_type, df_fs_ann, df_fs_quar)

재무제표 페이지 크롤링. 손익계산서 + 재무상태표 + 현금흐름표를 연결/분기별로 반환.

### read_snapshot(code, account_type) → (report, df_snap, df_snap_ann)

스냅샷 페이지 크롤링. report dict에 포함되는 주요 키:

| 키 | 설명 |
|----|------|
| `시가총액(상장예정포함,억원)` | 시가총액 (억원) |
| `시가총액(보통주,억원)` | 보통주 시가총액 |
| `발행주식수(보통주)` | 보통주 발행수 |
| `발행주식수(우선주)` | 우선주 발행수 |
| `자기주식` | 자기주식수 |
| `52주.최고가` / `52주.최저가` | 52주 고저 |
| `거래대금(억원)` | 일일 거래대금 |
| `베타(1년)` | 1년 베타 |
| `액면가` | 액면가 |
| `유통주식수` / `유통주식비율` | 유통주식 정보 |
| `PER` | FnGuide PER |
| `12M PER` | 12개월 PER |
| `업종 PER` | 업종 PER |
| `PBR` | PBR |
| `배당수익률` | 배당수익률 |
| `Summary` | 사업 요약 텍스트 |

### read_consensus(code, account_type) → df_cons

컨센서스 JSON 데이터 크롤링. 연간 예상 재무 항목 DataFrame 반환.

---

## 데이터 클래스

### CompResult

`analyze_comp()` 반환 타입. 재무건전성 종합 분석 결과.

| 필드 | 타입 | 설명 |
|------|------|------|
| `code` | str | 종목 코드 |
| `market_cap` | int | 시가총액 (억원) |
| `shares` | int | 발행주식수 (보통주+우선주-자기주식) |
| `trailing_eps` | float | Trailing 12M EPS (원) |
| `book_value_per_share` | int | 주당 순자산 BPS (원) |
| `profit_trend` | ProfitTrend | 매출/영업이익/순이익 추이 |
| `operating_asset_return` | RateHistory | 영업자산이익률 추이 |
| `non_operating_return` | RateHistory | 비영업자산이익률 추이 |
| `borrowing_rate` | RateHistory | 차입이자율 추이 |
| `roe` | RateHistory | 지배주주ROE 추이 |
| `shareholders_equity` | int | 주주몫 (억원) |
| `minority_interest` | int | 비지배주주지분 (억원) |
| `operating_liabilities` | int | 영업부채 (억원) |
| `external_debt` | int | 외부차입 (억원) |
| `operating_assets` | int | 영업자산 (억원) |
| `non_operating_assets` | int | 비영업자산 (억원) |
| `operating_profit` | int | 예상 영업이익 (억원) |
| `non_operating_profit` | int | 예상 비영업이익 (억원) |
| `interest_expense` | int | 예상 이자비용 (억원) |
| `tax_expense` | int | 예상 법인세비용 (억원) |
| `controlling_profit` | int | 예상 지배주주순이익 (억원) |
| `minority_profit` | int | 예상 비지배주주순이익 (억원) |
| `net_cash` | float | 순현금 (억원) |
| `net_cash_ratio` | float | 순현금/시가총액 (%) |
| `per_fnguide` | str | FnGuide PER |
| `per_12m` | str | 12M PER |
| `industry_per` | str | 업종 PER |
| `pbr` | str | PBR |
| `dividend_yield` | str | 배당수익률 |
| `summary` | str | 사업 요약 |

### ProfitTrend

매출/영업이익/순이익 연간 추이 (4개년 + Trailing 12M).

| 필드 | 타입 | 설명 |
|------|------|------|
| `periods` | list[str] | 기간 라벨 ['2021/12', '2022/12', ...] |
| `revenue` | list[float] | 매출액 (억원) |
| `operating_profit` | list[float] | 영업이익 (억원) |
| `net_income` | list[float] | 당기순이익 (억원) |
| `operating_margin` | list[float] | 영업이익률 (%) |

### RateHistory

이익률/ROE의 3년 추이와 예상값.

| 필드 | 타입 | 설명 |
|------|------|------|
| `year_minus_2` | float | -2년 |
| `year_minus_1` | float | -1년 |
| `recent` | float | 최근 (기준년도) |
| `expected` | float | 예상 (NaN 가능 — 컨센서스 부재 시) |

---

## 파서 유틸리티

| 함수 | 설명 |
|------|------|
| `to_num(x)` | 콤마 포맷 문자열 → int/float (실패 시 0) |
| `convert_string_to_number(df)` | DataFrame 문자열 셀 → 수치 일괄 변환 |
| `table_parsing(table_tag)` | BeautifulSoup table → (account_type, DataFrame) |
| `remove_E(columns)` | 컬럼명에서 `(E)` 접미사 제거 |
| `remove_space(index)` | 인덱스에서 공백 제거 |
| `calc_weight_coeff(date_columns)` | 회계연도 간격별 가중평균 계수 계산 |

---

## 분석 가능 항목 요약

fnguide 패키지를 통해 종목별로 다음 정보를 분석할 수 있다:

1. **수익성**: Trailing EPS, BPS, 지배주주ROE 추이
2. **매출/이익 추이**: 4개년 매출액, 영업이익, 순이익, 영업이익률
3. **재무건전성**: 자본 구성 (주주몫/비지배/영업부채/외부차입), 순현금 포지션
4. **자산 구성**: 영업자산 vs 비영업자산
5. **이익 구성**: 영업이익/비영업이익/이자비용/법인세의 예상 분해
6. **이익률 추이**: 영업자산이익률, 비영업자산이익률, 차입이자율의 3년 추이 + 예상
7. **밸류에이션**: PER(FnGuide/12M/업종), PBR, 배당수익률
8. **사업 개요**: FnGuide 사업 요약 텍스트

---

## 테스트 현황

- **69 tests**: 65 passed, 4 skipped
- **93% coverage**
- 마커: `@pytest.mark.live` (HTTP 테스트), `@pytest.mark.slow` (느린 테스트)
- 세션 스코프 픽스처로 크롤링 캐싱

---

Version: 2.0.0
Last Updated: 2026-03-05
SPEC: SPEC-FNGUIDE-ENGINE-001
