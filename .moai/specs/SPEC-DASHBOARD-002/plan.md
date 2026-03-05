---
id: SPEC-DASHBOARD-002
type: plan
version: 1.0.0
methodology: ddd
---

# SPEC-DASHBOARD-002 구현 계획

## 개발 방법론

**DDD (Domain-Driven Development)**: quality.yaml `development_mode: ddd` 에 따라 ANALYZE-PRESERVE-IMPROVE 사이클을 적용한다.

- ANALYZE: 기존 `dashboard.py` 의 DashboardResult 구조, `df_fs_ann` 데이터 접근 패턴 분석
- PRESERVE: 기존 7개 섹션 동작에 대한 characterization test 보존
- IMPROVE: ActivityRatios 섹션 추가 및 API/프론트엔드 확장

---

## Phase 1: Backend (Primary Goal)

### Task 1-1: fnguide/dashboard.py — ActivityRatios dataclass 추가

- `ActivityRatios` dataclass 정의 (9개 필드: 5개 회전율/기간 + CCC + 총자산 회전율 + periods)
- `DashboardResult` 에 `activity_ratios: ActivityRatios | None` 필드 추가
- 기존 7개 섹션 dataclass 에 영향 없음 확인

### Task 1-2: fnguide/dashboard.py — 활동성 비율 계산 로직

- `_calc_activity_ratios(df_fs_ann, periods)` 내부 함수 작성
- `df_fs_ann` 에서 6개 행 추출: 매출채권및기타유동채권, 재고자산, 매입채무및기타유동채무, 매출원가, 매출액, 자산
- 평균값 계산 (당해 + 전년 / 2), 첫째 연도 = None
- 회전율 산출: 매출채권, 재고자산, 매입채무, 총자산
- 기간 산출: 365 / 회전율, 정수 반올림
- CCC 산출: 매출채권 회수기간 + 재고 보유기간 - 매입채무 지급기간
- 0으로 나누기 방지: 평균값 == 0 이면 해당 지표 None
- 행 부재 방지: KeyError 시 해당 지표 None

### Task 1-3: fnguide/dashboard.py — analyze_dashboard 통합

- `analyze_dashboard()` 내에서 `_calc_activity_ratios()` 호출
- 금융업 종목 분기: `activity_ratios = None`
- `DashboardResult` 생성 시 `activity_ratios` 포함

### Task 1-4: backend/schemas/analysis.py — Pydantic 스키마 확장

- `ActivityRatiosSchema` Pydantic v2 모델 추가
- `AnalysisResponse` 에 `activity_ratios: ActivityRatiosSchema | None = None` 필드 추가
- 기존 7개 섹션 스키마에 영향 없음 확인 (하위 호환성)

### Task 1-5: Backend 테스트

- `test_activity_ratios_structure`: ActivityRatios 필드 존재 및 타입 검증
- `test_receivable_turnover`: 삼성전자 매출채권 회전율 검증 (검증 예시 기준)
- `test_inventory_turnover`: 재고자산 회전율 검증
- `test_payable_turnover`: 매입채무 회전율 검증
- `test_ccc_and_asset_turnover`: CCC 및 총자산 회전율 검증
- `test_first_year_none`: 첫째 연도 모든 지표 None 검증
- `test_zero_division`: 매출원가 0, 매출채권 0 등 edge case
- `test_missing_row`: df_fs_ann 에 행 부재 시 None 반환
- `test_activity_ratios_schema`: Pydantic 스키마 직렬화 검증
- **Characterization test**: 기존 7개 섹션이 activity_ratios 추가 전후로 동일한 값을 반환하는지 검증

---

## Phase 2: Frontend (Secondary Goal)

### Task 2-1: frontend/src/types/analysis.ts — TypeScript 타입 추가

- `ActivityRatios` 인터페이스 정의
- `AnalysisResponse` 에 `activity_ratios: ActivityRatios | null` 필드 추가

### Task 2-2: frontend/src/components/AnalysisModal.tsx — 활동성 섹션 추가

- Section 8 "활동성" 컴포넌트 구현
- 테이블 레이아웃: 기존 섹션과 동일한 스타일
- 행 구성:
  - 매출채권 회전율 / 회수기간
  - 재고자산 회전율 / 보유기간
  - 매입채무 회전율 / 지급기간
  - 현금전환주기 (CCC) — 강조 행
  - 총자산 회전율
- 포맷: 회전율 `X.X회`, 기간 `X일`, None = "-"

### Task 2-3: CCC 색상 코딩 + 툴팁

- CCC < 0: green 색상
- 0 <= CCC <= 60: 기본 색상
- CCC > 60: red 색상
- 툴팁: "현금을 투입해서 다시 현금으로 회수하기까지 걸리는 일수"

### Task 2-4: 조건부 렌더링

- `activity_ratios === null` 이면 섹션 미표시
- 기존 7개 섹션 렌더링에 영향 없음 확인

---

## 파일 목록

### 수정 파일 (4개)

| 파일 | 변경 사항 |
|------|----------|
| `fnguide/dashboard.py` | ActivityRatios dataclass + 계산 로직 + DashboardResult 확장 |
| `backend/schemas/analysis.py` | ActivityRatiosSchema + AnalysisResponse 확장 |
| `frontend/src/types/analysis.ts` | ActivityRatios 인터페이스 + AnalysisResponse 확장 |
| `frontend/src/components/AnalysisModal.tsx` | Section 8 활동성 컴포넌트 + CCC 색상/툴팁 |

### 신규 파일

없음 (기존 파일 확장만으로 구현)

---

## 의존성 그래프

```
Task 1-1 (ActivityRatios dataclass)
  └→ Task 1-2 (계산 로직)
       └→ Task 1-3 (analyze_dashboard 통합)
            └→ Task 1-4 (Pydantic 스키마)
                 └→ Task 1-5 (Backend 테스트)

Task 2-1 (TypeScript 타입) ─ Task 1-4 이후
  └→ Task 2-2 (활동성 섹션)
       ├→ Task 2-3 (CCC 색상/툴팁)
       └→ Task 2-4 (조건부 렌더링)
```

---

## 리스크 분석

### 낮음

| 리스크 | 영향 | 대응 |
|--------|------|------|
| `df_fs_ann` 에 활동성 관련 행 부재 (일부 종목) | 지표 미산출 | None fallback + UI "-" 표시 |
| 기존 DashboardResult 구조 변경으로 인한 regression | 기존 API 응답 파손 | `activity_ratios` 를 Optional 필드로 추가 (하위 호환성) + characterization test |
| 매출원가 = 0 종목 (서비스업 등) | 재고/매입채무 회전율 0 나누기 | None fallback |

### 중간

| 리스크 | 영향 | 대응 |
|--------|------|------|
| 회전율 계산 시 평균값 왜곡 (합병/분할 기업) | 비정상적 회전율 산출 | 사용자 판단에 위임 (주석/툴팁으로 안내 불필요) |

---

## 품질 기준

- 테스트 커버리지: 85% 이상 (활동성 비율 관련 코드)
- 기존 테스트 통과: SPEC-DASHBOARD-001 관련 테스트 전부 통과 (regression 없음)
- Pydantic 스키마 검증: 모든 필드 타입 힌트 + 검증
- 하위 호환성: 기존 7개 섹션 API 응답 구조 불변
- TRUST 5 게이트: Tested + Readable + Unified + Secured + Trackable
