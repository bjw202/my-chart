---
id: SPEC-DASHBOARD-001
type: plan
version: 1.0.0
methodology: ddd
---

# SPEC-DASHBOARD-001 구현 계획

## 개발 방법론

**DDD (Domain-Driven Development)**: quality.yaml `development_mode: ddd` 에 따라 ANALYZE-PRESERVE-IMPROVE 사이클을 적용한다.

- ANALYZE: 기존 fnguide 패키지의 `fs_analysis()`, `CompResult` 구조를 분석
- PRESERVE: 기존 `analyze_comp()` 동작에 대한 characterization test 작성
- IMPROVE: dashboard.py 모듈 추가 및 API/프론트엔드 확장

---

## Phase 1: Backend (Primary Goal)

### Task 1-1: fnguide/analysis.py 수정 (PRESERVE)

- `fs_analysis()` 반환값에 `df_financing` 추가 (현재 로컬 변수로 폐기)
- 반환 타입: `tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]` → (df_anal, df_invest, df_financing)
- 기존 `analyze_comp()` 호출부 수정 (언패킹 대응)
- **Characterization test**: 기존 fs_analysis 반환값이 변경되지 않는 것을 검증

### Task 1-2: fnguide/dashboard.py 핵심 데이터 구조 생성

- `DashboardResult` dataclass 및 7개 섹션 dataclass 정의
- `BusinessPerformance`, `HealthIndicators`, `BalanceSheet`, `RateDecomposition`, `ProfitWaterfall`, `TrendSignals`, `FiveQuestions`
- 각 dataclass 에 타입 힌트 + docstring

### Task 1-3: Section 1 - 사업 성과 계산 로직

- 매출액/영업이익/당기순이익/지배순이익 4개년 추출
- 영업활동현금흐름 추출 (`df_fs_ann.loc["영업활동으로인한현금흐름"]`)
- GPM, OPM, NPM 계산
- YoY 성장률 계산 (매출, 영업이익, 순이익)
- Profit Quality (CF/OP) 계산

### Task 1-4: Section 2 - 건전성 지표 계산 로직

- 7개 지표 산식 구현
- 임계값 기반 ok/warn/danger 판정 로직
- 이자비용 = 0 인 경우 이자보상배율 None 처리

### Task 1-5: Section 3-5 계산 로직

- Section 3: `df_financing` + `df_invest` 시계열 그대로 노출
- Section 4: 기존 3-rate + ROE 에 Ke (CAPM) + Spread 추가
- Section 5: 8단계 워터폴 계산 (예상 컬럼 기준)

### Task 1-6: Section 6-7 계산 로직

- Section 6: 6개 지표 선형 회귀 기울기 → up/flat/down 판정
- Section 7: 5대 질문 판정 로직 + 종합 verdict

### Task 1-7: Backend API 엔드포인트

- `backend/routers/analysis.py` — GET /api/analysis/{code}
- `backend/schemas/analysis.py` — Pydantic v2 응답 모델 (중첩 구조)
- `backend/services/analysis_service.py` — TTL 캐시 + analyze_dashboard 호출
- `backend/main.py` 에 router 등록

### Task 1-8: Backend 테스트

- fnguide/dashboard.py 단위 테스트 (session-scope fixture 로 HTTP 캐싱)
- Edge case 테스트 (IFRS 별도, zero interest, insufficient data)
- API integration 테스트 (정상/에러 응답)
- characterization test: 기존 analyze_comp 동작 보존 확인

---

## Phase 2: Frontend (Secondary Goal)

### Task 2-1: TypeScript 타입 정의

- `frontend/src/types/analysis.ts` — API 응답 타입 (DashboardResult 미러링)

### Task 2-2: API 호출 훅

- `frontend/src/hooks/useAnalysis.ts` — fetch + loading/error/data 상태 관리
- abort controller 로 중복 요청 방지

### Task 2-3: AnalysisModal 컴포넌트

- 풀스크린 모달 (loading/error/success 상태)
- Escape 키 + 외부 클릭 닫기
- 7개 섹션 스크롤 레이아웃

### Task 2-4: AnalysisSections 컴포넌트

- Section 1-4: 테이블 렌더링
- Section 5: 워터폴 표시 (양수=green, 음수=red)
- Section 6: 시그널 배지
- Section 7: 체크리스트 아이콘

### Task 2-5: ChartCell "FS" 버튼 통합

- ChartCell 헤더에 "FS" 버튼 추가
- 클릭 시 AnalysisModal 열기 (종목코드 전달)

### Task 2-6: 한국어 로케일 + 스타일링

- 금액 포맷 (억원, 콤마), 비율 (%), 배수 (x배)
- 반응형 모달 스타일
- 섹션별 헤더/구분선

---

## 파일 목록

### 신규 파일 (10개)

| 파일 | 설명 |
|------|------|
| `fnguide/dashboard.py` | DashboardResult + analyze_dashboard() |
| `backend/routers/analysis.py` | GET /api/analysis/{code} |
| `backend/schemas/analysis.py` | Pydantic 응답 모델 |
| `backend/services/analysis_service.py` | 캐시 + 서비스 레이어 |
| `frontend/src/types/analysis.ts` | TypeScript 타입 |
| `frontend/src/hooks/useAnalysis.ts` | API 호출 훅 |
| `frontend/src/components/AnalysisModal.tsx` | 모달 컨테이너 |
| `frontend/src/components/AnalysisSections.tsx` | 7개 섹션 |
| `tests/test_dashboard.py` | dashboard.py 단위 테스트 |
| `tests/test_analysis_api.py` | API 통합 테스트 |

### 수정 파일 (5개)

| 파일 | 변경 사항 |
|------|----------|
| `fnguide/analysis.py` | `fs_analysis()` 반환값에 df_financing 추가 |
| `fnguide/analyzer.py` | `analyze_comp()` df_financing 언패킹 대응 |
| `fnguide/__init__.py` | `analyze_dashboard` export 추가 |
| `backend/main.py` | analysis router 등록 |
| `frontend/src/components/ChartCell.tsx` | "FS" 버튼 추가 |

---

## 리스크 분석

### 높음

| 리스크 | 영향 | 대응 |
|--------|------|------|
| `fs_analysis()` 반환값 변경 시 기존 코드 파손 | analyze_comp 동작 오류 | characterization test 로 기존 동작 보존 확인 후 수정 |
| FnGuide HTML 구조 변경 | 크롤링 실패 | 503 에러 핸들링 + 크롤러 모듈 분리 유지 |

### 중간

| 리스크 | 영향 | 대응 |
|--------|------|------|
| Beta 값 누락 종목 | Ke/Spread 미산출 | None fallback + UI 에서 "N/A" 표시 |
| IFRS(별도) 엣지 케이스 | 비지배 관련 지표 오산출 | account_type 분기 처리 + 전용 테스트 |
| 대용량 응답 (7개 섹션) | 프론트엔드 렌더링 지연 | lazy section rendering + skeleton UI |

### 낮음

| 리스크 | 영향 | 대응 |
|--------|------|------|
| TTL 캐시 메모리 사용 | 다수 종목 동시 조회 시 메모리 증가 | maxsize 제한 (100) + TTL 5분 |

---

## 의존성 그래프

```
Task 1-1 (analysis.py 수정)
  └→ Task 1-2 (dataclass 정의)
       ├→ Task 1-3 (Section 1)
       ├→ Task 1-4 (Section 2)
       ├→ Task 1-5 (Section 3-5)
       └→ Task 1-6 (Section 6-7)
            └→ Task 1-7 (API 엔드포인트)
                 └→ Task 1-8 (Backend 테스트)

Task 2-1 (TypeScript 타입) ─ Task 1-7 이후
  └→ Task 2-2 (API 훅)
       └→ Task 2-3 (Modal)
            ├→ Task 2-4 (Sections)
            └→ Task 2-5 (ChartCell 통합)
                 └→ Task 2-6 (로케일 + 스타일)
```

---

## 품질 기준

- 테스트 커버리지: 85% 이상 (fnguide/dashboard.py)
- 기존 테스트 통과: fnguide 패키지 69개 테스트 전부 통과
- Pydantic 스키마 검증: 모든 필드 타입 힌트 + 검증
- 에러 핸들링: 503/422/404 분기 완전 커버
- TRUST 5 게이트: Tested + Readable + Unified + Secured + Trackable
