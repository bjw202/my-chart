---
id: SPEC-DASHBOARD-001
title: S-RIM Financial Analysis Dashboard
version: 1.0.0
status: draft
created: 2026-03-05
updated: 2026-03-05
author: jw
priority: P1
tags: [fnguide, dashboard, financial-analysis, fastapi, react]
---

# SPEC-DASHBOARD-001: S-RIM 재무분석 대시보드

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0.0 | 2026-03-05 | jw | 초기 SPEC 작성 |

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **프로젝트**: KR Stock Screener (FastAPI + React + fnguide 패키지)
- **기존 인프라**: fnguide 패키지의 `analyze_comp()` / `fs_analysis()` 가 B/S 재분류, 3-rate 분해, 손익 waterfall 의 핵심 계산을 이미 수행
- **데이터 소스**: comp.fnguide.com 크롤링 (연간/분기 재무제표, 리포트, 회계 유형)
- **배포 환경**: localhost 전용, 클라우드 미사용

### 1.2 기술 스택

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, fnguide 패키지
- **Frontend**: React 18+, TypeScript, Vite, TradingView Lightweight Charts
- **Database**: SQLite (기존 스키마 활용)
- **패키지 관리**: uv / Poetry

### 1.3 기존 코드 현황 (fnguide 엔진 ~80% 완성)

- `analysis.py::fs_analysis()` — B/S 재분류 (자금조달/자산투자 양쪽), 3-rate 분해 + 가중평균, profit waterfall 구현 완료
- `analyzer.py::CompResult` — 대부분의 데이터 보유하나 GPM, 영업CF, YoY 성장률, health indicators 미노출
- `df_fs_ann` 에 `매출총이익`, `영업활동으로인한현금흐름` 데이터 존재하나 미표면화
- `df_anal` 에 자금조달/자산 데이터 이미 노출됨 — `analyze_dashboard` 에서 `fs_analysis` 호출 + 대시보드 전용 계산 추가 가능

---

## 2. Assumptions (가정)

- A1: FnGuide 크롤링 응답 형식이 현재와 동일하게 유지된다
- A2: `df_fs_ann` 에 최소 4개 연간 컬럼 (3개년 + Trailing 12M) 이 존재한다
- A3: IFRS(연결) 기업은 지배/비지배 구분이 존재하고, IFRS(별도) 기업은 비지배주주지분 = 0 이다
- A4: `report` 딕셔너리에 Beta 값이 포함되어 CAPM 기반 Ke 산출이 가능하다
- A5: consensus ROE 가 없는 경우, 기존 가중평균 ROE 로 대체한다
- A6: 프론트엔드 사용자는 한국어 locale 을 사용한다

---

## 3. Requirements (요구사항)

### Module 1: fnguide 엔진 (dashboard.py)

**REQ-1: DashboardResult 데이터 구조**

시스템은 **항상** 7개 섹션 데이터를 포함하는 `DashboardResult` dataclass 를 제공해야 한다.

- Section 1: `BusinessPerformance` (사업 성과)
- Section 2: `HealthIndicators` (재무 건전성)
- Section 3: `BalanceSheet` (B/S 재분류 시계열)
- Section 4: `RateDecomposition` (이익률 분해)
- Section 5: `ProfitWaterfall` (손익 워터폴)
- Section 6: `TrendSignals` (추세 시그널)
- Section 7: `FiveQuestions` (5대 질문 자동 평가)

**REQ-2: B/S 재분류 시계열 (Section 3)**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** `fs_analysis()` 결과로부터 4개년 자금조달 측 (신용조달, 외부차입, 주주몫, 비지배주주지분) 과 자산투자 측 (설비투자, 운전자산, 금융투자, 여유자금) 시계열을 반환해야 한다.

**REQ-3: 사업 성과 (Section 1)**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 다음 지표를 계산하여 반환해야 한다:

- 매출액, 영업이익, 당기순이익, 지배주주순이익 (4개년)
- 영업활동현금흐름 (`영업활동으로인한현금흐름` from `df_fs_ann`)
- 매출총이익률 (GPM = `매출총이익` / `매출액`)
- 영업이익률 (OPM), 순이익률 (NPM)
- YoY 성장률 (매출액, 영업이익, 순이익 각각)
- 이익의 질 (Profit Quality = 영업CF / 영업이익)

**REQ-4: 재무 건전성 (Section 2)**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 7개 건전성 지표를 임계값과 함께 계산해야 한다:

| 지표 | 산식 | 기준 | ok/warn/danger |
|------|------|------|---------------|
| 외부차입/자기자본 | 외부차입 / 주주몫 | < 20% | ok: <20%, warn: 20-50%, danger: >50% |
| 부채비율 | (외부차입+영업부채) / 주주몫 | < 100% | ok: <100%, warn: 100-200%, danger: >200% |
| 차입금의존도 | 외부차입 / 총자산 | < 5% | ok: <5%, warn: 5-20%, danger: >20% |
| 순차입금의존도 | (외부차입-여유자금) / 총자산 | negative=good | ok: <0, warn: 0-10%, danger: >10% |
| 이자보상배율 | 영업이익 / 이자비용 | > 10x | ok: >10x, warn: 3-10x, danger: <3x |
| 영업자산비율 | 영업자산 / 총자산 | > 70% | ok: >70%, warn: 50-70%, danger: <50% |
| 비지배귀속비율 | 비지배순이익 / 당기순이익 | < 5% | ok: <5%, warn: 5-20%, danger: >20% |

**REQ-5: 이익률 분해 (Section 4)**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 기존 3-rate (영업자산이익률, 비영업자산이익률, 차입이자율) + ROE + 가중평균 ROE + Spread(ROE - Ke) 를 반환해야 한다.

- Ke = Rf + Beta * (Rm - Rf), Rf = 국고채 3년 수익률 (기본값 3.5%), Rm - Rf = 시장 리스크 프리미엄 (기본값 6%)
- Beta 는 `report` 에서 추출
- **IF** Beta 가 존재하지 않으면 **THEN** Ke = None 으로 설정하고 Spread 미산출

**REQ-6: 손익 워터폴 (Section 5)**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 8단계 워터폴을 반환해야 한다:

1. 영업자산이익 (영업자산 * 영업자산이익률)
2. 비영업자산이익 (비영업자산 * 비영업자산이익률)
3. 이자비용 (외부차입 * 차입이자율)
4. 세전이익 (1 + 2 - 3)
5. 법인세비용
6. 당기순이익 (4 - 5)
7. 비지배주주순이익
8. 지배주주순이익 (6 - 7)

**REQ-7: 추세 시그널 (Section 6)**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 6개 핵심 지표에 대해 방향(up/flat/down) 과 해석 문구를 반환해야 한다:

- 매출액 추이, 영업이익률 추이, ROE 추이
- 외부차입 추이, 영업자산비율 추이, 이자보상배율 추이

방향 판단 기준: 최근 3개년 선형 회귀 기울기 부호

**REQ-8: 5대 질문 자동 평가 (Section 7)**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 5개 질문에 대해 ok/warn/danger 상태를 반환해야 한다:

1. 이익을 내는 사업인가? (영업이익률 > 0 & 3년 연속 흑자)
2. 이익의 질이 좋은가? (영업CF/영업이익 > 0.8)
3. 재무구조가 안전한가? (부채비율 < 100% & 이자보상배율 > 5x)
4. 성장하고 있는가? (매출 YoY > 0 & 영업이익 YoY > 0)
5. 주주에게 돌아가는가? (비지배귀속비율 < 5% & ROE > Ke)

- 종합 verdict: 5개 중 ok 4개 이상 = "양호", ok 3개 = "보통", ok 2개 이하 = "주의"

### Module 2: Backend API

**REQ-9: API 엔드포인트**

**WHEN** 클라이언트가 `GET /api/analysis/{code}` 를 요청하면 **THEN** 시스템은 `DashboardResult` 를 JSON 으로 반환해야 한다.

- `{code}` 는 6자리 KRX 종목코드 (예: "005930")
- 라우터 패턴은 기존 `chart.py` 를 따른다

**REQ-10: Pydantic 응답 스키마**

시스템은 **항상** 중첩 섹션 구조의 Pydantic v2 응답 모델을 사용해야 한다.

- `AnalysisResponse` > 7개 섹션별 Pydantic 모델
- `model_config = ConfigDict(from_attributes=True)`

**REQ-11: 에러 처리**

- **IF** FnGuide 크롤링이 실패하면 **THEN** HTTP 503 (Service Unavailable) 을 반환해야 한다
- **IF** 유효하지 않은 종목코드가 입력되면 **THEN** HTTP 422 (Validation Error) 를 반환해야 한다
- **IF** 종목이 존재하나 데이터가 부족하면 **THEN** HTTP 404 (Not Found) 를 반환해야 한다

**REQ-12: TTL 캐시**

**WHEN** 동일 종목코드로 5분 이내 재요청이 오면 **THEN** 캐시된 결과를 반환하여 중복 크롤링을 방지해야 한다.

- `functools.lru_cache` 또는 `cachetools.TTLCache` 활용

### Module 3: Frontend Dashboard

**REQ-13: FS 버튼**

**WHEN** 사용자가 ChartCell 헤더의 "FS" 버튼을 클릭하면 **THEN** 해당 종목의 재무분석 대시보드 모달이 열려야 한다.

**REQ-14: 풀스크린 모달**

시스템은 **항상** 다음 상태를 가진 풀스크린 모달을 제공해야 한다:

- 로딩 상태: 스피너 + "분석 중..." 텍스트
- 에러 상태: 에러 메시지 + 재시도 버튼
- 성공 상태: 7개 섹션을 스크롤 가능한 레이아웃으로 표시

**REQ-15: 섹션별 시각화**

- Section 1 (사업 성과): 테이블 (연도별 매출/이익/이익률/성장률)
- Section 2 (건전성): 테이블 (지표명, 값, 기준, 상태 배지)
- Section 3 (B/S 재분류): 좌우 테이블 (자금조달 vs 자산투자, 4개년)
- Section 4 (이익률 분해): 테이블 (3-rate + ROE + Spread, 3개년 + 예상)
- Section 5 (워터폴): 워터폴 형태 표시 (8단계, 양수=green/음수=red)
- Section 6 (추세): 시그널 배지 (up=green, flat=gray, down=red) + 해석
- Section 7 (5대 질문): 체크리스트 (ok=check/warn=warning/danger=x 아이콘)

**REQ-16: 한국어 로케일 포맷팅**

시스템은 **항상** 다음 형식을 사용해야 한다:

- 금액: 억원 단위, 천 단위 콤마 (예: 1,234억원)
- 비율: % 표기 (예: 12.3%)
- 배수: x배 표기 (예: 15.2x배)
- 모달 닫기: Escape 키 + 외부 클릭

---

## 4. Specifications (세부 사양)

### 4.1 데이터 흐름

```
사용자 클릭 "FS" → Frontend fetch GET /api/analysis/{code}
→ Backend router → analyze_dashboard(code)
→ get_fnguide(code) → fs_analysis() + dashboard 전용 계산
→ DashboardResult → Pydantic 직렬화 → JSON 응답
→ Frontend 모달 렌더링
```

### 4.2 새 파일 구조

```
fnguide/
  dashboard.py          # analyze_dashboard(), DashboardResult, 7개 섹션 dataclass

backend/
  routers/
    analysis.py         # GET /api/analysis/{code}
  schemas/
    analysis.py         # AnalysisResponse, 7개 섹션 Pydantic 모델
  services/
    analysis_service.py # analyze_dashboard 호출 + 캐시

frontend/src/
  components/
    AnalysisModal.tsx   # 풀스크린 모달 컨테이너
    AnalysisSections.tsx # 7개 섹션 컴포넌트
  hooks/
    useAnalysis.ts      # API 호출 + 상태 관리
  types/
    analysis.ts         # TypeScript 타입 정의
```

### 4.3 수정 파일

- `backend/main.py` — analysis router 등록
- `backend/routers/__init__.py` — router import 추가
- `frontend/src/components/ChartCell.tsx` — "FS" 버튼 추가
- `fnguide/__init__.py` — `analyze_dashboard` export 추가
- `fnguide/analysis.py` — `df_financing` 반환 추가 (현재 로컬 변수로 폐기됨)

### 4.4 Edge Cases

- **IFRS(별도)**: 비지배주주지분 = 0, 지배주주순이익 = 당기순이익. REQ-4 비지배귀속비율 = 0% (ok)
- **Consensus ROE 부재**: 가중평균 ROE 로 fallback (A5)
- **이자비용 = 0**: 이자보상배율 = None, health status = ok (무차입 경영)
- **데이터 부족 (<3년)**: `ValueError("Insufficient historical data")` raise → HTTP 404

### 4.5 Traceability

| 요구사항 | 파일 | 테스트 |
|---------|------|--------|
| REQ-1 | fnguide/dashboard.py | test_dashboard_result_structure |
| REQ-2 | fnguide/dashboard.py | test_balance_sheet_time_series |
| REQ-3 | fnguide/dashboard.py | test_business_performance |
| REQ-4 | fnguide/dashboard.py | test_health_indicators |
| REQ-5 | fnguide/dashboard.py | test_rate_decomposition |
| REQ-6 | fnguide/dashboard.py | test_profit_waterfall |
| REQ-7 | fnguide/dashboard.py | test_trend_signals |
| REQ-8 | fnguide/dashboard.py | test_five_questions |
| REQ-9 | backend/routers/analysis.py | test_api_analysis_endpoint |
| REQ-10 | backend/schemas/analysis.py | test_pydantic_response_schema |
| REQ-11 | backend/routers/analysis.py | test_error_handling |
| REQ-12 | backend/services/analysis_service.py | test_ttl_cache |
| REQ-13 | frontend/src/components/ChartCell.tsx | e2e_fs_button_click |
| REQ-14 | frontend/src/components/AnalysisModal.tsx | e2e_modal_states |
| REQ-15 | frontend/src/components/AnalysisSections.tsx | e2e_section_rendering |
| REQ-16 | frontend/src/components/AnalysisSections.tsx | e2e_locale_formatting |
