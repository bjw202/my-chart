---
id: SPEC-DASHBOARD-001
type: acceptance
version: 1.0.0
---

# SPEC-DASHBOARD-001 수락 기준

## Given-When-Then 시나리오

---

### Scenario 1: Happy Path — IFRS(연결) 종목 전체 섹션 반환

```gherkin
Given FnGuide 에 정상 데이터가 존재하는 IFRS(연결) 종목코드 "005930"
  And 4개년 연간 재무제표 + 4개 분기 재무제표가 존재
When analyze_dashboard("005930") 을 호출하면
Then DashboardResult 가 반환되어야 한다
  And 7개 섹션 (business_performance, health_indicators, balance_sheet,
      rate_decomposition, profit_waterfall, trend_signals, five_questions) 이
      모두 None 이 아니어야 한다
  And business_performance.revenue 리스트 길이가 4 이어야 한다
  And health_indicators 의 7개 지표가 모두 status (ok/warn/danger) 를 가져야 한다
  And profit_waterfall.steps 길이가 8 이어야 한다
```

---

### Scenario 2: IFRS(별도) 종목 — 비지배주주지분 = 0 처리

```gherkin
Given IFRS(별도) 회계 유형의 종목코드
  And 비지배주주지분이 재무제표에 존재하지 않는 상태
When analyze_dashboard(code) 를 호출하면
Then balance_sheet.financing 의 비지배주주지분이 4개년 모두 0 이어야 한다
  And profit_waterfall.minority_profit 이 0 이어야 한다
  And profit_waterfall.controlling_profit == profit_waterfall.net_income
  And health_indicators 중 비지배귀속비율 값이 0.0 이어야 한다
  And health_indicators 중 비지배귀속비율 status 가 "ok" 이어야 한다
```

---

### Scenario 3: Consensus ROE 부재 — 가중평균 fallback

```gherkin
Given FnGuide 에서 컨센서스 ROE 가 제공되지 않는 종목코드
  And 3개년 실적 기반 ROE 이력이 존재하는 상태
When analyze_dashboard(code) 를 호출하면
Then rate_decomposition.roe.expected 는 가중평균으로 산출된 값이어야 한다
  And 가중평균 공식: (w1*Y-2 + w2*Y-1 + w3*Y0) / denom
  And five_questions 의 ROE > Ke 판정이 가중평균 ROE 기준으로 수행되어야 한다
```

---

### Scenario 4: 이자비용 = 0 (무차입 경영)

```gherkin
Given 외부차입이 0 이고 이자비용이 0 인 종목코드
When analyze_dashboard(code) 를 호출하면
Then rate_decomposition.borrowing_rate 가 전 기간 0.0 이어야 한다
  And health_indicators 중 이자보상배율 값이 None 이어야 한다
  And health_indicators 중 이자보상배율 status 가 "ok" 이어야 한다
  And profit_waterfall.interest_expense 가 0 이어야 한다
```

---

### Scenario 5: 데이터 부족 (<3년)

```gherkin
Given FnGuide 에서 연간 재무제표 컬럼이 3개 미만인 종목코드
When analyze_dashboard(code) 를 호출하면
Then ValueError("Insufficient historical data") 가 발생해야 한다

Given 위 ValueError 가 발생한 상태에서 API 를 호출하면
When GET /api/analysis/{code} 요청이 도달하면
Then HTTP 404 응답이 반환되어야 한다
  And 응답 body 에 error: "insufficient_data" 가 포함되어야 한다
```

---

### Scenario 6: Frontend — FS 버튼 클릭 시 모달 오픈 + 로딩 상태

```gherkin
Given ChartCell 에 종목코드 "005930" 이 표시되어 있는 상태
When 사용자가 "FS" 버튼을 클릭하면
Then 풀스크린 모달이 열려야 한다
  And 모달에 로딩 스피너가 표시되어야 한다
  And API 호출 GET /api/analysis/005930 이 발생해야 한다

Given API 가 성공 응답을 반환한 상태
When 데이터 로딩이 완료되면
Then 로딩 스피너가 사라져야 한다
  And 7개 섹션이 스크롤 가능한 레이아웃으로 표시되어야 한다
```

---

### Scenario 7: Frontend — 모달 닫기 (Escape + 외부 클릭)

```gherkin
Given 재무분석 모달이 열려 있는 상태
When 사용자가 Escape 키를 누르면
Then 모달이 닫혀야 한다

Given 재무분석 모달이 열려 있는 상태
When 사용자가 모달 외부 영역을 클릭하면
Then 모달이 닫혀야 한다
```

---

### Scenario 8: 건전성 지표 임계값 평가

```gherkin
Given 다음 재무 데이터를 가진 종목:
  | 지표 | 값 |
  | 외부차입/자기자본 | 15% |
  | 부채비율 | 80% |
  | 차입금의존도 | 3% |
  | 순차입금의존도 | -5% |
  | 이자보상배율 | 12x |
  | 영업자산비율 | 75% |
  | 비지배귀속비율 | 2% |
When analyze_dashboard(code) 를 호출하면
Then 7개 건전성 지표의 status 가 모두 "ok" 이어야 한다

Given 다음 재무 데이터를 가진 종목:
  | 지표 | 값 |
  | 외부차입/자기자본 | 60% |
  | 부채비율 | 250% |
  | 차입금의존도 | 25% |
When health_indicators 를 확인하면
Then 외부차입/자기자본 status 가 "danger" 이어야 한다
  And 부채비율 status 가 "danger" 이어야 한다
  And 차입금의존도 status 가 "danger" 이어야 한다
```

---

### Scenario 9: 워터폴 — 음수 세전이익 처리

```gherkin
Given 영업자산이익이 양수이나 이자비용이 더 큰 종목
  And 세전이익이 음수인 상태
When analyze_dashboard(code) 를 호출하면
Then profit_waterfall.pretax_income 이 음수여야 한다
  And profit_waterfall.net_income 이 음수여야 한다
  And 프론트엔드에서 음수 항목은 red 색상으로 표시되어야 한다
```

---

### Scenario 10: 5대 질문 종합 verdict 계산

```gherkin
Given 다음 질문별 상태를 가진 종목:
  | 질문 | 상태 |
  | 이익을 내는 사업인가? | ok |
  | 이익의 질이 좋은가? | ok |
  | 재무구조가 안전한가? | ok |
  | 성장하고 있는가? | ok |
  | 주주에게 돌아가는가? | warn |
When five_questions.verdict 를 확인하면
Then verdict 가 "양호" 이어야 한다 (ok 4개 >= 4)

Given ok 가 2개인 종목
When five_questions.verdict 를 확인하면
Then verdict 가 "주의" 이어야 한다 (ok 2개 <= 2)
```

---

## 품질 게이트

### Definition of Done

- [ ] fnguide/dashboard.py 의 모든 public 함수에 타입 힌트 + docstring
- [ ] 테스트 커버리지 85% 이상 (fnguide/dashboard.py)
- [ ] 기존 fnguide 테스트 69개 전부 통과 (regression 없음)
- [ ] Pydantic 응답 모델에서 모든 필드 검증 통과
- [ ] API 에러 코드 503/422/404 분기 테스트 통과
- [ ] 프론트엔드 모달 열기/닫기/로딩/에러 상태 동작 확인
- [ ] 한국어 포맷 (억원, %, x배) 정상 표시 확인
- [ ] ruff / black 포맷팅 통과
- [ ] pyright 타입 체크 통과 (zero errors)

### 검증 방법

| 영역 | 도구 | 기준 |
|------|------|------|
| 단위 테스트 | pytest + pytest-asyncio | 모든 시나리오 통과, coverage >= 85% |
| API 테스트 | httpx AsyncClient | 정상/에러 응답 검증 |
| 타입 체크 | pyright | zero errors |
| 린트 | ruff | zero warnings |
| 프론트엔드 | 수동 테스트 / Playwright (선택) | 모달 동작 + 렌더링 확인 |
