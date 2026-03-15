# SPEC-FNGUIDE-ENGINE-001: 인수 기준

## 테스트 카테고리 1: Parser 유닛 테스트

### AC-P-001: to_num 숫자 변환

```gherkin
Given 콤마 포맷 문자열 "1,234"
When to_num()을 호출하면
Then 결과는 1234 (int)

Given 소수점 포함 문자열 "1,234.56"
When to_num()을 호출하면
Then 결과는 1234.56 (float)

Given 빈 문자열 "" 또는 "abc"
When to_num()을 호출하면
Then 결과는 0
```

### AC-P-002: convert_string_to_number DataFrame 변환

```gherkin
Given "-" 문자열과 콤마 숫자가 혼합된 DataFrame
When convert_string_to_number(df)를 호출하면
Then "-"는 0으로 변환되고 콤마 숫자는 수치형으로 변환됨

Given fillna=float("nan") 옵션으로 호출하면
Then "-"와 빈 문자열은 NaN으로 유지됨
```

### AC-P-003: remove_E, remove_space

```gherkin
Given ["2024/12(E)", "2025/12(E)"] 컬럼 리스트
When remove_E()를 호출하면
Then ["2024/12", "2025/12"] 반환

Given ["매출 액", "영업 이익"] 인덱스 리스트
When remove_space()를 호출하면
Then ["매출액", "영업이익"] 반환
```

### AC-P-004: table_parsing HTML 파싱

```gherkin
Given FnGuide 형식의 HTML <table> Tag
When table_parsing(table)을 호출하면
Then (account_type, df) 튜플 반환
And account_type은 "IFRS(연결)" 또는 "IFRS(별도)" 형식
And df는 수치형 DataFrame
And df.index.name == account_type
```

---

## 테스트 카테고리 2: Crawler 통합 테스트

### AC-C-001: read_fs 연결 재무제표

```gherkin
Given 삼성전자 종목코드 "005930"
When read_fs("005930")를 호출하면
Then account_type == "IFRS(연결)"
And df_fs_ann.shape[1] >= 4
And df_fs_quar.shape[1] >= 4
And df_fs_ann.index에 "매출액", "영업이익", "당기순이익" 포함
And df_fs_ann.index에 "자산총계", "부채총계", "자본총계" 포함
And df_fs_ann 컬럼이 "YYYY/MM" 패턴
```

### AC-C-002: read_fs 별도 재무제표

```gherkin
Given IFRS(별도)로 보고하는 종목코드
When read_fs(code)를 호출하면
Then account_type == "IFRS(별도)"
And 기본 재무제표 구조는 연결과 동일
```

### AC-C-003: read_snapshot 스냅샷 데이터

```gherkin
Given 삼성전자 종목코드 "005930"
When read_snapshot("005930")을 호출하면
Then report["종가"] > 0
And report["시가총액(상장예정포함,억원)"] > 0
And report["발행주식수(보통주)"] > 0
And report에 "PER", "PBR", "배당수익률" 키 존재
And df_snap은 비어있지 않은 DataFrame
And df_snap_ann은 비어있지 않은 DataFrame
```

### AC-C-004: read_consensus 컨센서스

```gherkin
Given 삼성전자 종목코드 "005930"
When read_consensus("005930")을 호출하면
Then 반환 DataFrame이 비어있지 않음
And 인덱스에 재무 항목명 존재
And 컬럼이 "YYYY/MM" 패턴
And 셀 데이터가 numeric 타입 (int/float/NaN)
```

### AC-C-005: get_required_rate BBB- 금리

```gherkin
Given KIS Rating 웹사이트 접근 가능
When get_required_rate()를 호출하면
Then 반환값 타입은 float
And 0.01 <= 반환값 <= 0.20
```

### AC-C-006: get_fnguide 통합 크롤링

```gherkin
Given 삼성전자 종목코드 "005930"
When get_fnguide("005930")을 호출하면
Then 7-tuple 반환
And 각 DataFrame은 비어있지 않음
And report는 필수 키를 포함한 dict
And account_type은 "IFRS(연결)" 또는 "IFRS(별도)"
```

### AC-C-007: 잘못된 종목코드 에러 처리

```gherkin
Given 존재하지 않는 종목코드 "999999"
When read_fs("999999") 또는 read_snapshot("999999")을 호출하면
Then 적절한 예외가 발생하거나 에러 상태를 명시적으로 표현
And 프로그램이 crash 없이 처리됨
```

---

## 테스트 카테고리 3: Financial Analysis 로직 테스트

### AC-A-001: fs_analysis 기본 동작

```gherkin
Given read_fs("005930") 결과 (df_fs_ann, df_fs_quar)
When fs_analysis(df_fs_ann, df_fs_quar)를 호출하면
Then df_anal에 다음 행이 존재:
  - "주주몫", "비지배주주지분", "외부차입", "영업부채"
  - "영업자산", "비영업자산"
  - "영업이익", "비영업이익", "이자비용", "법인세비용"
  - "지배주주순이익", "비지배주주순이익"
  - "영업자산이익률", "비영업자산이익률", "차입이자율", "지배주주ROE"
And df_invest에 "설비투자", "운전자산", "금융투자", "여유자금" 행 존재
```

### AC-A-002: 이익률 범위 검증

```gherkin
Given fs_analysis 결과 df_anal
Then "영업자산이익률"의 모든 수치값이 -1.0 ~ 1.0 범위
And "차입이자율"의 모든 수치값이 0.0 ~ 0.5 범위
And "지배주주ROE"의 모든 수치값이 -1.0 ~ 1.0 범위
And "가중평균" 컬럼 값이 NaN이 아님
```

### AC-A-003: 영업자산이익률 1순위 선택

```gherkin
Given 영업자산이익률 3년 추이
When 상승 추세 (a < b < c) 또는 하락 추세 (a > b > c)
Then 1순위 == col[3] 값 (최근값)

When 추세 없음 (예: a < b > c)
Then 1순위 == 가중평균
```

### AC-A-004: 예상 순이익 추정

```gherkin
Given fs_analysis 결과 df_anal
Then "예상" 컬럼에 "영업이익", "비영업이익", "이자비용", "법인세비용" 존재
And "지배주주순이익", "지배주주ROE" 예상값 존재
And 법인세비용 예상 = (영업이익_est + 비영업이익_est - 이자비용_est) * 0.22 근사
```

### AC-A-005: IFRS 별도 처리

```gherkin
Given IFRS(별도) 종목의 재무제표
When fs_analysis를 호출하면
Then "비지배주주지분" 행 값이 모두 0
And "지배주주순이익" == "당기순이익"
And ZeroDivisionError 없이 정상 완료
```

### AC-A-006: calc_weight_coeff 검증

```gherkin
Given 12개월 간격 연간 컬럼 (예: "2021/12", "2022/12", "2023/12", "2024/12")
When calc_weight_coeff(columns)를 호출하면
Then (1.0, 2.0, 3.0, 6.0) 반환

Given 3개월 간격 컬럼
Then (1.0, 0.5, 3.0, 4.5) 반환
```

---

## 테스트 카테고리 4: End-to-End 분석 테스트

### AC-E-001: analyze_comp 삼성전자

```gherkin
Given 삼성전자 종목코드 "005930"
When analyze_comp("005930")을 호출하면
Then CompResult 반환
And code == "005930"
And cur_price > 0
And market_cap > 0
And shares > 0
And trailing_eps != 0
And trailing_per > 0
And book_value_per_share > 0
And operating_asset_return의 4개 필드가 모두 유효한 float
And roe의 4개 필드가 모두 유효한 float
```

### AC-E-002: analyze_comp 복수 종목

```gherkin
Given 종목 코드 리스트 ["005930", "000660"]
When 각 종목에 대해 analyze_comp(code)를 호출하면
Then 모든 종목에서 CompResult가 에러 없이 반환
And 각 CompResult의 code가 입력 코드와 일치
And 각 CompResult의 시가총액, 주가가 양수
```

### AC-E-003: CompResult 데이터 일관성

```gherkin
Given analyze_comp 결과 result
Then result.shares가 양수
And result.trailing_per >= 0 (적자 기업은 0)
And result.net_cash_ratio 값이 유효한 float
And str(result) 호출 시 에러 없이 문자열 반환
```

---

## Quality Gate

| 기준 | 목표 |
|------|------|
| Parser 테스트 통과율 | 100% |
| Crawler 테스트 통과율 | 100% (네트워크 정상 시) |
| Analysis 테스트 통과율 | 100% |
| E2E 테스트 통과율 | 100% |
| 코드 커버리지 (parser.py) | >= 90% |
| 코드 커버리지 (analysis.py) | >= 85% |
| 코드 커버리지 (crawler.py) | >= 80% |
| 코드 커버리지 (analyzer.py) | >= 80% |

---

## Definition of Done

- [ ] 4개 테스트 파일 모두 작성 완료
- [ ] conftest.py에 session-scope fixture 구현
- [ ] `pytest tests/fnguide/` 실행 시 모든 테스트 통과
- [ ] `@pytest.mark.live` 마커 설정 완료
- [ ] IFRS(연결) + IFRS(별도) 양쪽 모두 테스트 커버
- [ ] 코드 커버리지 목표 달성
- [ ] pyproject.toml에 테스트 마커 등록

---

## 추적성 태그

- SPEC: SPEC-FNGUIDE-ENGINE-001
- 요구사항: REQ-P-001 ~ REQ-P-004, REQ-C-001 ~ REQ-C-007, REQ-A-001 ~ REQ-A-006, REQ-E-001 ~ REQ-E-003
