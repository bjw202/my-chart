---
id: SPEC-DASHBOARD-002
title: Activity Ratios Dashboard Section
version: 1.0.0
status: completed
created: 2026-03-06
updated: 2026-03-06
author: jw
priority: P2
tags: [fnguide, dashboard, financial-analysis, activity-ratios, fastapi, react]
parent: SPEC-DASHBOARD-001
---

# SPEC-DASHBOARD-002: 활동성 비율 대시보드 섹션 (Section 8)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0.0 | 2026-03-06 | jw | 초기 SPEC 작성 |

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **프로젝트**: KR Stock Screener (FastAPI + React + fnguide 패키지)
- **상위 SPEC**: SPEC-DASHBOARD-001 (S-RIM 재무분석 대시보드, 7개 섹션 구현 완료)
- **확장 범위**: 기존 7개 섹션에 Section 8 (활동성 비율) 추가
- **데이터 소스**: comp.fnguide.com 크롤링 — `df_fs_ann` DataFrame 의 기존 행 활용
- **배포 환경**: localhost 전용, 클라우드 미사용

### 1.2 기술 스택 (SPEC-DASHBOARD-001 동일)

- **Backend**: Python 3.11+, FastAPI, Pydantic v2, fnguide 패키지
- **Frontend**: React 18+, TypeScript, Vite
- **Database**: SQLite (기존 스키마 활용)

### 1.3 기존 코드 현황

- `fnguide/dashboard.py` — `analyze_dashboard(code)` 가 `DashboardResult` 반환 (7개 섹션)
- `backend/routers/analysis.py` — `GET /api/analysis/{code}` 엔드포인트
- `backend/schemas/analysis.py` — `AnalysisResponse` Pydantic 모델 (7개 섹션)
- `frontend/src/components/AnalysisModal.tsx` — 7개 섹션 컴포넌트
- `frontend/src/types/analysis.ts` — TypeScript 인터페이스

### 1.4 데이터 가용성 확인 (삼성전자 005930 기준)

`df_fs_ann` 에서 다음 행이 모두 존재함을 확인:

| 행 이름 | 값 (4개년) |
|---------|-----------|
| 매출채권및기타유동채권 | [418708, 432806, 532460, 586090] |
| 재고자산 | [521879, 516259, 517549, 526368] |
| 매입채무및기타유동채무 | [587468, 535497, 615226, 681144] |
| 매출원가 | [1900418, 1803886, 1865623, 2022355] |
| 매출액 | [3022314, 2589355, 3008709, 3336059] |
| 자산 | [4484245, 4559060, 5145319, 5669421] |

---

## 2. Assumptions (가정)

- A1: SPEC-DASHBOARD-001 의 가정 (A1-A6) 이 동일하게 유지된다
- A2: `df_fs_ann` 에 `매출채권및기타유동채권`, `재고자산`, `매입채무및기타유동채무`, `매출원가`, `매출액`, `자산` 행이 존재한다
- A3: "평균" 산출은 당해연도와 전년도의 산술평균을 사용한다. 따라서 첫째 연도는 평균 산출 불가로 None 이다
- A4: 금융업 종목은 활동성 비율이 의미 없으므로 Section 8 = None (기존 섹션과 동일 정책)
- A5: 데이터 행이 부재할 경우 해당 지표를 None 으로 반환한다 (에러 발생하지 않음)

---

## 3. Requirements (요구사항)

### Module 1: fnguide 엔진 (dashboard.py)

**REQ-17: ActivityRatios 데이터 구조**

시스템은 **항상** `DashboardResult` 에 Section 8 (`ActivityRatios`) 를 포함해야 한다.

- `ActivityRatios` 는 다음 필드를 가진 dataclass 이다:
  - `receivable_turnover`: 매출채권 회전율 (회) — `list[float | None]`, 4개년
  - `receivable_days`: 매출채권 회수기간 (일) — `list[int | None]`, 4개년
  - `inventory_turnover`: 재고자산 회전율 (회) — `list[float | None]`, 4개년
  - `inventory_days`: 재고 보유기간 (일) — `list[int | None]`, 4개년
  - `payable_turnover`: 매입채무 회전율 (회) — `list[float | None]`, 4개년
  - `payable_days`: 매입채무 지급기간 (일) — `list[int | None]`, 4개년
  - `ccc`: 현금전환주기 (일) — `list[int | None]`, 4개년
  - `asset_turnover`: 총자산 회전율 (회) — `list[float | None]`, 4개년
  - `periods`: 기간 라벨 — `list[str]`, 4개년
- 금융업 종목의 경우 `activity_ratios = None`

**REQ-18: 매출채권 회전율 및 회수기간 계산**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 다음 산식으로 매출채권 회전율과 회수기간을 계산해야 한다:

- 매출채권 회전율 = 매출액 / 평균 매출채권및기타유동채권 (회)
- 매출채권 회수기간 = 365 / 매출채권 회전율 (일, 정수 반올림)
- 평균 매출채권 = (당해 매출채권 + 전년 매출채권) / 2
- **IF** 전년 데이터가 없으면 **THEN** 해당 연도의 회전율과 회수기간은 None

**REQ-19: 재고자산 회전율 및 보유기간 계산**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 다음 산식으로 재고자산 회전율과 보유기간을 계산해야 한다:

- 재고자산 회전율 = 매출원가 / 평균 재고자산 (회)
- 재고 보유기간 = 365 / 재고자산 회전율 (일, 정수 반올림)
- 평균 재고자산 = (당해 재고자산 + 전년 재고자산) / 2
- **IF** 전년 데이터가 없으면 **THEN** 해당 연도의 회전율과 보유기간은 None

**REQ-20: 매입채무 회전율 및 지급기간 계산**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 다음 산식으로 매입채무 회전율과 지급기간을 계산해야 한다:

- 매입채무 회전율 = 매출원가 / 평균 매입채무및기타유동채무 (회)
- 매입채무 지급기간 = 365 / 매입채무 회전율 (일, 정수 반올림)
- 평균 매입채무 = (당해 매입채무 + 전년 매입채무) / 2
- **IF** 전년 데이터가 없으면 **THEN** 해당 연도의 회전율과 지급기간은 None

**REQ-21: 현금전환주기 (CCC) 및 총자산 회전율 계산**

**WHEN** `analyze_dashboard(code)` 가 호출되면 **THEN** 다음 산식으로 CCC 와 총자산 회전율을 계산해야 한다:

- 현금전환주기 (CCC) = 매출채권 회수기간 + 재고 보유기간 - 매입채무 지급기간 (일)
- 총자산 회전율 = 매출액 / 평균 총자산 (회)
- 평균 총자산 = (당해 자산 + 전년 자산) / 2
- **IF** 구성 요소 중 하나라도 None 이면 **THEN** CCC 도 None
- **IF** 전년 데이터가 없으면 **THEN** 총자산 회전율은 None

### Module 2: Backend API

**REQ-22: API 응답 스키마 확장**

시스템은 **항상** `AnalysisResponse` 에 `activity_ratios` 필드를 포함해야 한다.

- `ActivityRatiosSchema` Pydantic 모델 추가 (Pydantic v2, `ConfigDict(from_attributes=True)`)
- `AnalysisResponse.activity_ratios: ActivityRatiosSchema | None`
- 기존 7개 섹션 응답 구조에 영향 없어야 한다 (하위 호환성)

### Module 3: Frontend Dashboard

**REQ-23: 활동성 섹션 렌더링 (테이블 + 호버 설명)**

**WHEN** API 응답에 `activity_ratios` 가 존재하면 **THEN** 기존 섹션 뒤에 "활동성" 섹션을 테이블 형식으로 표시해야 한다.

- 테이블 구조: 행 = 지표명, 열 = 기간 (기존 섹션과 동일 레이아웃)
- 회전율 값: `X.X회` 포맷 (소수점 1자리)
- 기간 값: `X일` 포맷 (정수)
- None 값: "-" 으로 표시
- **모든 지표명에 Tooltip 호버 설명** (건전성 섹션과 동일 UX):
  - 매출채권 회전율: "매출액 ÷ 평균 매출채권. 외상 매출을 현금으로 회수하는 속도입니다. 높을수록 빠르게 현금화합니다."
  - 매출채권 회수기간: "365 ÷ 매출채권 회전율. 외상 매출 후 현금을 받기까지 걸리는 평균 일수입니다. 짧을수록 좋습니다."
  - 재고자산 회전율: "매출원가 ÷ 평균 재고자산. 재고가 팔려 나가는 속도입니다. 높을수록 재고 관리가 효율적입니다."
  - 재고 보유기간: "365 ÷ 재고자산 회전율. 재고를 매입해서 판매까지 걸리는 평균 일수입니다. 짧을수록 재고 부담이 적습니다."
  - 매입채무 회전율: "매출원가 ÷ 평균 매입채무. 공급업체에 대금을 지급하는 속도입니다. 낮을수록 결제 여유가 있습니다."
  - 매입채무 지급기간: "365 ÷ 매입채무 회전율. 원재료 매입 후 대금을 지급하기까지 걸리는 평균 일수입니다. 길수록 현금 여유가 있습니다."
  - 총자산 회전율: "매출액 ÷ 평균 총자산. 보유 자산 대비 매출 창출 효율입니다. 높을수록 자산을 효율적으로 활용합니다."

**REQ-24: CCC 타임라인 그래픽 시각화**

**WHEN** CCC 값이 존재하면 **THEN** 테이블 아래에 가장 최근 연도의 현금전환주기를 타임라인 그래픽으로 시각화해야 한다.

- 그래픽 구조: 수평 타임라인 바 3개 + CCC 결과
  ```
  ├── 재고 보유기간 ──────────────┤  (101일)
                    ├── 매출채권 회수기간 ──┤  (59일)
  ├── 매입채무 지급기간 ──────────────────┤  (113일)
  ════════════════════════════════
  현금전환주기 (CCC) = 47일
  ```
- 재고 보유기간: 원재료 매입 → 제품 판매 (좌측 시작)
- 매출채권 회수기간: 제품 판매 → 현금 회수 (재고 보유기간 끝에서 이어짐)
- 매입채무 지급기간: 원재료 매입 → 대금 지급 (좌측 시작, 별도 바)
- CCC = (재고 보유기간 + 매출채권 회수기간) - 매입채무 지급기간
- CCC 색상 코딩:
  - CCC < 0: 긍정 색상 (green) — 남의 돈으로 장사하는 우수 구조
  - 0 <= CCC <= 60: 기본 색상 — 정상 범위
  - CCC > 60: 부정 색상 (red) — 현금 순환 지연
- CCC 행에 Tooltip: "현금을 투입해서 다시 현금으로 회수하기까지 걸리는 일수. 매입 대금 지급 전에 매출 현금이 들어오면 음수가 되어 자금 여유가 생깁니다."
- 타임라인 아래에 간단한 해석 문구 추가:
  - CCC < 0: "매입 대금 지급 전에 매출이 현금화됩니다. 우수한 현금 순환 구조입니다."
  - 0 < CCC <= 60: "현금 투입 후 약 {CCC}일 만에 회수됩니다."
  - CCC > 60: "현금 회수에 {CCC}일이 소요됩니다. 운전자본 부담에 주의가 필요합니다."

**REQ-25: 활동성 섹션 조건부 표시**

**IF** `activity_ratios` 가 None 이면 **THEN** 활동성 섹션을 렌더링하지 않아야 한다 (금융업 종목 등).

---

## 4. Specifications (세부 사양)

### 4.1 데이터 흐름

```
analyze_dashboard(code) 기존 흐름
  → df_fs_ann 에서 활동성 관련 행 추출
  → 평균값 계산 (당해 + 전년 / 2)
  → 회전율, 기간, CCC, 총자산 회전율 산출
  → ActivityRatios dataclass 생성
  → DashboardResult.activity_ratios 에 포함
  → API JSON 응답 → Frontend 렌더링
```

### 4.2 산식 상세

#### 매출채권 회전율 (Accounts Receivable Turnover)

```
avg_receivable[t] = (receivable[t] + receivable[t-1]) / 2
turnover[t] = revenue[t] / avg_receivable[t]
days[t] = round(365 / turnover[t])
```

#### 재고자산 회전율 (Inventory Turnover)

```
avg_inventory[t] = (inventory[t] + inventory[t-1]) / 2
turnover[t] = cogs[t] / avg_inventory[t]
days[t] = round(365 / turnover[t])
```

#### 매입채무 회전율 (Accounts Payable Turnover)

```
avg_payable[t] = (payable[t] + payable[t-1]) / 2
turnover[t] = cogs[t] / avg_payable[t]
days[t] = round(365 / turnover[t])
```

#### 현금전환주기 (Cash Conversion Cycle)

```
ccc[t] = receivable_days[t] + inventory_days[t] - payable_days[t]
```

#### 총자산 회전율 (Total Asset Turnover)

```
avg_asset[t] = (asset[t] + asset[t-1]) / 2
turnover[t] = revenue[t] / avg_asset[t]
```

### 4.3 검증 예시 (삼성전자 005930, 3번째 연도 기준)

```
avg_receivable = (432806 + 532460) / 2 = 482633
receivable_turnover = 3008709 / 482633 = 6.23회
receivable_days = round(365 / 6.23) = 59일

avg_inventory = (516259 + 517549) / 2 = 516904
inventory_turnover = 1865623 / 516904 = 3.61회
inventory_days = round(365 / 3.61) = 101일

avg_payable = (535497 + 615226) / 2 = 575361.5
payable_turnover = 1865623 / 575361.5 = 3.24회
payable_days = round(365 / 3.24) = 113일

CCC = 59 + 101 - 113 = 47일

avg_asset = (4559060 + 5145319) / 2 = 4852189.5
asset_turnover = 3008709 / 4852189.5 = 0.62회
```

### 4.4 수정 파일

| 파일 | 변경 사항 |
|------|----------|
| `fnguide/dashboard.py` | `ActivityRatios` dataclass 추가, `analyze_dashboard()` 에 Section 8 계산 로직 추가, `DashboardResult` 에 `activity_ratios` 필드 추가 |
| `backend/schemas/analysis.py` | `ActivityRatiosSchema` Pydantic 모델 추가, `AnalysisResponse` 에 `activity_ratios` 필드 추가 |
| `frontend/src/types/analysis.ts` | `ActivityRatios` TypeScript 인터페이스 추가, `AnalysisResponse` 에 필드 추가 |
| `frontend/src/components/AnalysisModal.tsx` | Section 8 (활동성) 컴포넌트 추가, CCC 색상 코딩 + 툴팁 구현 |

### 4.5 신규 파일

없음 (기존 파일 확장만으로 구현 가능)

### 4.6 Edge Cases

- **금융업 종목**: `activity_ratios = None` (기존 섹션 정책 동일)
- **매출원가 = 0**: 재고/매입채무 회전율 = None (0으로 나누기 방지)
- **매출채권 = 0**: 회전율 계산 시 평균이 0이면 None 반환
- **첫째 연도**: 전년 데이터 부재로 모든 지표 None
- **행 부재**: `df_fs_ann` 에 특정 행이 없으면 해당 지표 None (KeyError 방지)

### 4.7 Traceability

| 요구사항 | 파일 | 테스트 |
|---------|------|--------|
| REQ-17 | fnguide/dashboard.py | test_activity_ratios_structure |
| REQ-18 | fnguide/dashboard.py | test_receivable_turnover |
| REQ-19 | fnguide/dashboard.py | test_inventory_turnover |
| REQ-20 | fnguide/dashboard.py | test_payable_turnover |
| REQ-21 | fnguide/dashboard.py | test_ccc_and_asset_turnover |
| REQ-22 | backend/schemas/analysis.py | test_activity_ratios_schema |
| REQ-23 | frontend/src/components/AnalysisModal.tsx | e2e_activity_section_rendering |
| REQ-24 | frontend/src/components/AnalysisModal.tsx | e2e_ccc_color_coding |
| REQ-25 | frontend/src/components/AnalysisModal.tsx | e2e_activity_section_hidden |
