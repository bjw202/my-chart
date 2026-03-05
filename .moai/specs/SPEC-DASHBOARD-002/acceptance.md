---
id: SPEC-DASHBOARD-002
type: acceptance
version: 1.0.0
---

# SPEC-DASHBOARD-002 수락 기준

## Given-When-Then 시나리오

---

### Scenario 1: Happy Path — ActivityRatios 정상 반환

```gherkin
Given FnGuide 에 정상 데이터가 존재하는 IFRS(연결) 종목코드 "005930"
  And df_fs_ann 에 매출채권및기타유동채권, 재고자산, 매입채무및기타유동채무, 매출원가, 매출액, 자산 행이 모두 존재
  And 4개년 연간 재무제표가 존재
When analyze_dashboard("005930") 을 호출하면
Then DashboardResult.activity_ratios 가 None 이 아니어야 한다
  And activity_ratios.receivable_turnover 리스트 길이가 4 이어야 한다
  And activity_ratios.receivable_days 리스트 길이가 4 이어야 한다
  And activity_ratios.inventory_turnover 리스트 길이가 4 이어야 한다
  And activity_ratios.inventory_days 리스트 길이가 4 이어야 한다
  And activity_ratios.payable_turnover 리스트 길이가 4 이어야 한다
  And activity_ratios.payable_days 리스트 길이가 4 이어야 한다
  And activity_ratios.ccc 리스트 길이가 4 이어야 한다
  And activity_ratios.asset_turnover 리스트 길이가 4 이어야 한다
  And activity_ratios.periods 리스트 길이가 4 이어야 한다
```

---

### Scenario 2: 첫째 연도 None 처리

```gherkin
Given 4개년 재무제표가 존재하는 종목코드
When analyze_dashboard(code) 를 호출하면
Then activity_ratios.receivable_turnover[0] 이 None 이어야 한다
  And activity_ratios.receivable_days[0] 이 None 이어야 한다
  And activity_ratios.inventory_turnover[0] 이 None 이어야 한다
  And activity_ratios.inventory_days[0] 이 None 이어야 한다
  And activity_ratios.payable_turnover[0] 이 None 이어야 한다
  And activity_ratios.payable_days[0] 이 None 이어야 한다
  And activity_ratios.ccc[0] 이 None 이어야 한다
  And activity_ratios.asset_turnover[0] 이 None 이어야 한다
  And activity_ratios.receivable_turnover[1] 이 None 이 아니어야 한다
```

---

### Scenario 3: 삼성전자 검증 예시 (3번째 연도)

```gherkin
Given 삼성전자 (005930) 의 df_fs_ann 데이터:
  | 행 | Y-3 | Y-2 | Y-1 | Y0 |
  | 매출채권및기타유동채권 | 418708 | 432806 | 532460 | 586090 |
  | 재고자산 | 521879 | 516259 | 517549 | 526368 |
  | 매입채무및기타유동채무 | 587468 | 535497 | 615226 | 681144 |
  | 매출원가 | 1900418 | 1803886 | 1865623 | 2022355 |
  | 매출액 | 3022314 | 2589355 | 3008709 | 3336059 |
  | 자산 | 4484245 | 4559060 | 5145319 | 5669421 |
When analyze_dashboard("005930") 을 호출하면
Then 3번째 연도 (Y-1) 기준으로:
  And receivable_turnover[2] 가 약 6.2 이어야 한다 (허용 오차 0.1)
  And receivable_days[2] 가 59 이어야 한다
  And inventory_turnover[2] 가 약 3.6 이어야 한다 (허용 오차 0.1)
  And inventory_days[2] 가 101 이어야 한다
  And payable_turnover[2] 가 약 3.2 이어야 한다 (허용 오차 0.1)
  And payable_days[2] 가 113 이어야 한다
  And ccc[2] 가 47 이어야 한다 (59 + 101 - 113)
  And asset_turnover[2] 가 약 0.62 이어야 한다 (허용 오차 0.02)
```

---

### Scenario 4: 금융업 종목 — activity_ratios None

```gherkin
Given 금융업 종목코드 (은행, 보험, 증권 등)
When analyze_dashboard(code) 를 호출하면
Then DashboardResult.activity_ratios 가 None 이어야 한다
  And 기존 7개 섹션은 정상 반환되어야 한다
```

---

### Scenario 5: 매출원가 = 0 (서비스업 등)

```gherkin
Given df_fs_ann 에서 매출원가 행이 모두 0 인 종목코드
When analyze_dashboard(code) 를 호출하면
Then activity_ratios.inventory_turnover 의 모든 요소가 None 이어야 한다
  And activity_ratios.inventory_days 의 모든 요소가 None 이어야 한다
  And activity_ratios.payable_turnover 의 모든 요소가 None 이어야 한다
  And activity_ratios.payable_days 의 모든 요소가 None 이어야 한다
  And activity_ratios.ccc 의 모든 요소가 None 이어야 한다
  And activity_ratios.receivable_turnover 은 정상 계산되어야 한다 (매출액 기준)
  And activity_ratios.asset_turnover 은 정상 계산되어야 한다 (매출액 기준)
```

---

### Scenario 6: df_fs_ann 행 부재

```gherkin
Given df_fs_ann 에 "재고자산" 행이 존재하지 않는 종목코드
When analyze_dashboard(code) 를 호출하면
Then activity_ratios.inventory_turnover 의 모든 요소가 None 이어야 한다
  And activity_ratios.inventory_days 의 모든 요소가 None 이어야 한다
  And 나머지 지표 (receivable, payable, asset_turnover) 는 정상 계산되어야 한다
  And activity_ratios.ccc 의 모든 요소가 None 이어야 한다 (구성 요소 부재)
  And ValueError 가 발생하지 않아야 한다
```

---

### Scenario 7: API 하위 호환성

```gherkin
Given SPEC-DASHBOARD-001 에서 정상 동작하던 API 클라이언트
When GET /api/analysis/{code} 를 요청하면
Then 기존 7개 섹션 (business_performance, health_indicators, balance_sheet,
    rate_decomposition, profit_waterfall, trend_signals, five_questions) 의
    응답 구조와 값이 SPEC-DASHBOARD-001 과 동일해야 한다
  And 추가로 activity_ratios 필드가 응답에 포함되어야 한다
  And activity_ratios 가 null 이거나 ActivityRatios 구조여야 한다
```

---

### Scenario 8: Frontend — 활동성 섹션 테이블 렌더링

```gherkin
Given API 가 activity_ratios 데이터를 정상 반환한 상태
When 재무분석 모달이 열리면
Then "활동성" 섹션이 기존 섹션 아래에 표시되어야 한다
  And 테이블에 다음 행이 표시되어야 한다:
    | 행 이름 | 포맷 |
    | 매출채권 회전율 | X.X회 |
    | 매출채권 회수기간 | X일 |
    | 재고자산 회전율 | X.X회 |
    | 재고 보유기간 | X일 |
    | 매입채무 회전율 | X.X회 |
    | 매입채무 지급기간 | X일 |
    | 현금전환주기 (CCC) | X일 |
    | 총자산 회전율 | X.X회 |
  And 열은 기간 (periods) 라벨이어야 한다
  And None 값은 "-" 으로 표시되어야 한다
```

---

### Scenario 9: Frontend — CCC 색상 코딩

```gherkin
Given activity_ratios.ccc 값이 [-5, 30, 47, 75] 인 상태
When 활동성 섹션이 렌더링되면
Then CCC = -5 인 셀은 green 색상이어야 한다
  And CCC = 30 인 셀은 기본 색상이어야 한다
  And CCC = 47 인 셀은 기본 색상이어야 한다
  And CCC = 75 인 셀은 red 색상이어야 한다
  And CCC 행에 마우스를 올리면 "현금을 투입해서 다시 현금으로 회수하기까지 걸리는 일수" 툴팁이 표시되어야 한다
```

---

### Scenario 10: Frontend — activity_ratios null 일 때 섹션 미표시

```gherkin
Given API 가 activity_ratios: null 을 반환한 상태 (금융업 종목)
When 재무분석 모달이 열리면
Then "활동성" 섹션이 표시되지 않아야 한다
  And 기존 7개 섹션은 정상 표시되어야 한다
```

---

## 품질 게이트

### Definition of Done

- [ ] `ActivityRatios` dataclass 에 타입 힌트 + docstring
- [ ] 활동성 비율 계산 로직 테스트 커버리지 85% 이상
- [ ] 기존 SPEC-DASHBOARD-001 테스트 전부 통과 (regression 없음)
- [ ] Pydantic `ActivityRatiosSchema` 직렬화/역직렬화 테스트 통과
- [ ] API 응답에 `activity_ratios` 필드 포함 확인
- [ ] 하위 호환성: 기존 7개 섹션 응답 구조 불변
- [ ] 프론트엔드 활동성 섹션 테이블 렌더링 확인
- [ ] CCC 색상 코딩 (green/default/red) 정상 동작
- [ ] CCC 툴팁 표시 확인
- [ ] 금융업 종목에서 활동성 섹션 미표시 확인
- [ ] None 값 "-" 표시 확인
- [ ] ruff / black 포맷팅 통과
- [ ] pyright 타입 체크 통과 (zero errors)

### 검증 방법

| 영역 | 도구 | 기준 |
|------|------|------|
| 단위 테스트 | pytest + session-scope fixture | 모든 시나리오 통과, coverage >= 85% |
| 산식 검증 | 삼성전자 검증 예시 대조 | 허용 오차 내 일치 |
| 하위 호환성 | characterization test | 기존 7개 섹션 동일 출력 |
| API 테스트 | httpx AsyncClient | activity_ratios 필드 존재 + 타입 검증 |
| 타입 체크 | pyright | zero errors |
| 린트 | ruff | zero warnings |
| 프론트엔드 | 수동 테스트 / Playwright (선택) | 테이블 렌더링 + CCC 색상 + 툴팁 |
