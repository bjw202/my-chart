---
id: SPEC-NAVER-THEME-003
title: V2 frontend 채택 (theme_description tooltip + V2 endpoint swap)
status: Draft
version: 1.0.0
owner: bjw2002
created: 2026-05-06
updated: 2026-05-06
depends_on: SPEC-NAVER-THEME-002
---

# SPEC-NAVER-THEME-003: V2 frontend 채택

## 메타데이터

| 항목 | 값 |
| --- | --- |
| SPEC ID | SPEC-NAVER-THEME-003 |
| 제목 | Naver Mobile Theme Analysis Frontend Adoption (V2 endpoint swap + tooltip) |
| 생성일 | 2026-05-06 |
| 상태 | Draft |
| 우선순위 | High |
| 담당 | expert-backend, expert-frontend, expert-testing |
| 의존 SPEC | SPEC-NAVER-THEME-002 (V2 backend ship 완료, v1.0.1) |
| Lifecycle | spec-anchored |
| 버전 | 1.0.0 |

---

## HISTORY

- 2026-05-06 v1.0.0: 초안 작성 (manager-spec). SPEC-NAVER-THEME-002 V2 backend ship 후속 작업으로 frontend가 V2 endpoint를 채택하도록 한다. 핸드오프 문서(`.moai/specs/SPEC-NAVER-THEME-002/handoff-frontend-v2.md`) Stage B 기반. 사용자 결정 D-1(에러 메시지+retry), D-2(theme_name hover Tooltip), D-3(inclusion_reason 컬럼 자리 재사용 — V2 parser 동일 source 활용), D-4(null hidden) 사전 잠금. V1 routes/모듈 byte-identical 보존(REQ-NT3-C-001/C-002), V2 backend metadata는 additive-only V1 alias 4 필드 추가(REQ-NT3-005), pip 신규 의존성 금지(REQ-NT3-C-004), bare except 금지(REQ-NT3-C-005). V2 endpoint 503/timeout 시 V1 자동 폴백 금지(REQ-NT3-C-006).

---

## 1. Environment (환경)

### 1.1 시스템 개요

본 SPEC은 SPEC-NAVER-THEME-002에서 ship된 V2 백엔드 endpoint(`/api/themes/v2/snapshot`, `/api/themes/v2/quick`)를 frontend ThemeAnalysis 컴포넌트가 호출하도록 swap하고, V2가 제공하는 추가 컬럼 `theme_description`(테마 설명)을 사용자 화면에 노출한다.

V2 mobile parser의 핵심 관찰(`backend/services/naver_theme_v2/parser.py:271-272`): `inclusion_reason`과 `stock_description`은 mobile API의 동일 source(`item.description`)에서 채워진다. ThemeDetailPanel이 이미 `inclusion_reason`을 hover tooltip(`title` 속성)으로 노출 중이므로 V2 endpoint로 swap만 하면 종목별 편입설명이 자동으로 표시된다 (D-3, frontend 변경 거의 0).

V1 desktop endpoint와 V1 backend 모듈은 무수정으로 유지되며 (cohabitation 보존), V1 endpoint는 즉시 rollback 경로로 남긴다.

| 항목 | 값 |
| --- | --- |
| frontend API client | `frontend/src/api/themes.ts` (EDIT — V1 → V2 URL swap + 타입 확장) |
| ThemeAnalysis 컴포넌트 | `frontend/src/components/ThemeAnalysis/{ThemeAnalysis,ThemeRankingTable,ThemeDetailPanel}.tsx` |
| backend V2 service | `backend/services/naver_theme_v2/service.py` (EDIT — metadata V1 alias 추가) |
| backend V1 모듈 | `backend/services/naver_theme/*` (무수정, REQ-NT3-C-002) |
| backend routes | `backend/routers/themes.py` (무수정, V1+V2 모두 등록 유지) |
| 실행 모델 | stateless (V1+V2 동일) — 호출 1회당 1 사이클 |

### 1.2 모듈 변경 매트릭스

| 파일 | 변경 유형 | 변경 LOC (예상) | 변경 내용 |
|------|------|------|------|
| `backend/services/naver_theme_v2/service.py` | EDIT | +20 | metadata에 V1 alias 4 필드 추가 (`collected_at`, `theme_count`, `stock_count`, `elapsed_sec`). `_empty_result` 동일 적용 |
| `frontend/src/api/themes.ts` | EDIT | +10 | endpoint URL swap (`/themes/snapshot` → `/themes/v2/snapshot`, 동일 quick). ThemeItem에 `theme_description?: string \| null`, ThemeStockItem에 `stock_description?: string \| null` 추가 (forward-compat). axios 503/timeout 처리 보강 |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | EDIT | +1 | theme_name 셀에 `title={theme.theme_description ?? undefined}` 추가 (D-2 + D-4) |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | 무수정 | 0 | D-3 — V2 parser가 inclusion_reason과 stock_description을 동일 source로 채움. 기존 `title={stock.inclusion_reason}` 호환 유지 |
| `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx` | EDIT | +15 | V2 endpoint 503/timeout 시 에러 메시지 + retry 버튼 (D-1). `ba3f20c` race condition cleanup 패턴 보존 |
| `tests/test_naver_theme_v2_service.py` | EDIT | +15 | metadata V1 alias 4 필드 AC 추가 |
| `frontend/src/components/ThemeAnalysis/__tests__/` | EDIT or NEW | +60 | V2 endpoint mock URL 검증 + tooltip rendering + null hidden + 에러 retry 시나리오 |

**합계 예상**: ~120 LOC, 7 files.

### 1.3 외부 의존성 (기설치, 신규 추가 없음 — REQ-NT3-C-004)

Backend (V2 SPEC-002 의존성 그대로):
- `requests`, `pandas`, `numpy`, `pydantic`, `fastapi`

Frontend (기존 의존성 그대로):
- `react ^19`, `axios`, `vitest`, `@testing-library/react`

신규 라이브러리(예: Radix Tooltip) 도입 없이 native HTML `title` 속성으로 D-2 tooltip 구현.

---

## 2. Assumptions (가정)

### 2.1 외부 시스템 가정

- SPEC-NAVER-THEME-002 V2 backend ship 결과 (24/24 GREEN, 라이브 1 PASS)가 그대로 유효
- V2 endpoint(`/api/themes/v2/snapshot`, `/api/themes/v2/quick`)가 등록된 상태 — `backend/routers/themes.py`에서 확인 가능
- V2 mobile API 응답 schema (sectorDescription, item.description 컬럼 보존)가 SPEC-002 ship 시점과 동일

### 2.2 호환성 가정

- frontend `ThemeItem`/`ThemeStockItem` 타입 확장은 optional field(`theme_description?`, `stock_description?`)로만 추가 → V1 응답에서 해당 필드가 부재해도 TypeScript compile error 없음
- ThemeDetailPanel의 `title={stock.inclusion_reason}` 패턴이 V2 응답에서 V2 mobile parser 정책(`inclusion_reason ← item.description`)에 의해 자동 호환
- frontend vitest baseline 1 fail (ChartGrid pre-existing, V2 무관)은 본 SPEC 회귀 판정 시 baseline diff 적용

### 2.3 Risk-bound 가정

- V2 endpoint URL이 SPEC 작업 진행 중 변경되지 않음 (sentry release `stock-web@` 활발, 변경 시 backend `config.py` 수정 — REQ-NT2-NF-005 그대로)
- 사용자 화면이 desktop 우선 — mobile hover 부재로 인한 D-2 tooltip 미동작은 본 SPEC 범위 외 (별도 SPEC에서 추후 처리)

---

## 3. Requirements (요구사항, EARS format)

### 3.1 Functional Requirements

#### REQ-NT3-001: V2 endpoint URL swap

**The system shall** update `frontend/src/api/themes.ts` so that `fetchThemesSnapshot()` calls `/themes/v2/snapshot` and `fetchThemesQuick()` calls `/themes/v2/quick`, replacing V1 endpoint URLs.

**Rationale**: V2 backend ship 완료 후 사용자가 V2 데이터를 화면에서 확인 가능하도록 하는 본 SPEC의 핵심 변경.

#### REQ-NT3-002: TypeScript 타입 확장 — theme_description

**The system shall** extend `ThemeItem` interface in `frontend/src/api/themes.ts` to include optional field `theme_description?: string | null`.

**Rationale**: V2 응답이 V1 응답의 superset이므로 optional 필드 추가는 backward-compatible. V1으로 즉시 rollback 시 해당 필드 부재해도 TypeScript compile 정상.

#### REQ-NT3-003: TypeScript 타입 확장 — stock_description (forward-compat)

**The system shall** extend `ThemeStockItem` interface in `frontend/src/api/themes.ts` to include optional field `stock_description?: string | null`.

**Rationale**: V2 parser가 동일 source로 채우는 forward-compat 필드. 본 SPEC에서 직접 사용하지 않으나(D-3 — inclusion_reason 자리 재사용) 향후 별도 SPEC에서 활용 가능.

#### REQ-NT3-004: theme_description Tooltip 표시 (D-2)

**WHEN** ThemeRankingTable이 렌더링되고 `theme.theme_description`이 non-null/non-empty string이면, **the system shall** expose `theme_description`을 native HTML `title` 속성을 통해 theme_name 셀의 hover tooltip으로 노출한다.

**WHEN** `theme.theme_description`이 null, undefined, 또는 빈 문자열이면, **the system shall not** render the `title` 속성 (hidden — D-4).

**Rationale**: D-2 결정 — Tooltip은 레이아웃 변경 0, desktop hover UX 일관성. D-4 — null placeholder 노이즈 회피.

#### REQ-NT3-005: V2 backend metadata에 V1 alias 4 필드 추가

**The system shall** populate `result.metadata` in `collect_and_analyze_v2()` with the following V1-compatible alias fields, in addition to existing fields (`data_source`, `generated_at`, `total_themes_seen`, `errors`):

- `collected_at`: str (alias of `generated_at`, ISO-8601 UTC)
- `theme_count`: int (alias of `total_themes_seen`)
- `stock_count`: int (`len(stocks_df)` 계산값)
- `elapsed_sec`: float (`time.monotonic()` 측정값, snapshot 호출 전체 시간)

**The system shall** preserve all existing V2 metadata fields (additive only — REQ-NT3-C-003).

**Rationale**: frontend `ThemesSnapshotResponse.metadata` (V1 호환)가 4 필드를 기대 — V2 응답이 frontend 타입과 1:1 매칭되도록 alias 추가. V1 alias 4 필드 부재 시 frontend metadata 표시 영역(예: 응답 시간 표시)이 누락됨.

#### REQ-NT3-006: `_empty_result` 헬퍼에도 V1 alias 적용

**The system shall** populate the same V1 alias fields (`collected_at`, `theme_count=0`, `stock_count=0`, `elapsed_sec=0.0`) in the `_empty_result()` helper of `backend/services/naver_theme_v2/service.py`.

**Rationale**: 모든 list endpoint 호출 실패 시(REQ-NT2-NF-003) 부분 결과 반환 — frontend가 metadata 4 필드 기대 시 빈 결과에서도 schema consistency 보장.

#### REQ-NT3-007: V2 endpoint 503/timeout 처리 (D-1)

**WHEN** V2 endpoint가 HTTP 5xx, network error, 또는 timeout으로 실패하면, **the system shall** display an error message in the ThemeAnalysis 화면 with the following structure:
- Error 메시지: 사용자 친화적 텍스트 (예: "테마 데이터를 가져오지 못했습니다. 다시 시도해 주세요.")
- Retry 버튼: 클릭 시 현재 mode(`quick` or `full`)로 fetch 재시작

**The system shall not** automatically fall back to V1 endpoint (REQ-NT3-C-006).

**Rationale**: D-1 결정. UI 분기 최소화 + Sentry release 활발한 risk(R-1) 시 사용자 즉시 인지 + 수동 retry. 자동 폴백은 V1↔V2 schema 차이로 복잡도 증가 → 회피.

#### REQ-NT3-008: ThemeDetailPanel inclusion_reason 자리에서 V2 description 자동 노출 (D-3)

**The system shall** preserve the existing `title={stock.inclusion_reason}` rendering in `ThemeDetailPanel.tsx` (line 62, 92) without modification.

**WHEN** V2 endpoint가 호출되고 V2 parser가 `inclusion_reason`과 `stock_description`을 동일 source(`item.description`)로 채운 응답을 반환하면, **the system shall** display V2의 종목별 편입설명을 기존 inclusion_reason 자리에 자동으로 노출한다.

**Rationale**: D-3 결정. V2 mobile parser의 동일 source 정책(§2.3 research) 활용 → frontend 컴포넌트 변경 0. inclusion_reason cell의 hover tooltip이 V1 desktop의 편입사유 → V2 mobile의 편입설명으로 자연스럽게 전환.

### 3.2 Non-Functional Requirements

#### REQ-NT3-NF-001: V2 endpoint failure 처리 — UI 분기 최소화

**The system shall** implement V2 endpoint failure handling (REQ-NT3-007) with no more than 2 conditional UI branches:
- branch 1: error state 렌더링 (메시지 + retry 버튼)
- branch 2: 정상 응답 렌더링 (기존 ThemeRankingTable + ThemeDetailPanel)

**The system shall not** introduce V1 fallback branches, environment-variable toggle branches, or race-based dual-fetch logic.

**Rationale**: D-1 결정. 복잡도 최소화로 회귀 risk 감소.

#### REQ-NT3-NF-002: null/undefined description 렌더링 정책 (D-4)

**WHEN** `theme.theme_description` or `stock.inclusion_reason` is `null`, `undefined`, or empty string, **the system shall** omit the related `title` attribute entirely (no placeholder text such as "—" or "(설명 없음)").

**Rationale**: D-4 결정. 264개 테마 + 다수 종목 화면에서 placeholder 노이즈 회피.

#### REQ-NT3-NF-003: V2 응답 시간 보존

**The system shall** preserve V2 SPEC-002 NF-004 응답 시간 목표:
- `/api/themes/v2/snapshot` SHALL respond within 30 seconds under nominal conditions
- `/api/themes/v2/quick` SHALL respond within 10 seconds under nominal conditions

**Rationale**: 본 SPEC 변경은 frontend swap + metadata alias 추가만 — V2 backend 호출 패턴/외부 호출 횟수 변경 없음.

#### REQ-NT3-NF-004: frontend vitest baseline 보존

**The system shall** ensure that adding new V2 endpoint mock tests does not introduce new test failures beyond the pre-existing ChartGrid baseline failure (1 fail).

**Rationale**: vitest baseline 256/257 PASS — 신규 vitest 추가 후에도 ChartGrid 외 신규 fail 0 유지.

### 3.3 Constraints

#### REQ-NT3-C-001: V1 routes byte-identical 보존

**The system shall not** modify the function signatures, response shapes, decorators, or paths of V1 routes `GET /api/themes/snapshot` and `GET /api/themes/quick` in `backend/routers/themes.py`.

**The system shall** preserve V1 routes as immediately available rollback path during and after V2 frontend adoption.

(Mirrors V2 SPEC REQ-NT2-R-003.)

#### REQ-NT3-C-002: V1 backend 모듈 무수정

**The system shall not** modify any file in `backend/services/naver_theme/` (V1 backend modules).

**Rationale**: SPEC-001 무수정 정책 계승. V1 51 단위 테스트는 본 SPEC 작업 후에도 그대로 PASS (회귀 0).

#### REQ-NT3-C-003: V2 backend metadata additive only

**The system shall not** remove, rename, or change the dtype of existing V2 metadata fields (`data_source`, `generated_at`, `total_themes_seen`, `errors`).

**The system shall** add V1 alias fields (REQ-NT3-005) as additional keys only.

**Rationale**: V2 단위 테스트 AC-2 (`data_source == "naver_mobile_v2"` 검증)와 호환 보장. V2 SPEC-002 v1.0.1 amendment 패턴 (superset 검증).

#### REQ-NT3-C-004: 신규 pip/npm 의존성 금지

**The system shall not** introduce new entries to `requirements.txt`, `pyproject.toml`, `frontend/package.json`, or any dependency manifest.

**The system shall** rely exclusively on existing dependencies:
- backend: `requests`, `pandas`, `numpy`, `pydantic`, `fastapi`
- frontend: `react`, `axios`, `vitest`, `@testing-library/react`

**Rationale**: D-2 tooltip은 native HTML `title` 속성으로 구현 가능 → Radix Tooltip 등 신규 라이브러리 불필요. SPEC-002 정책 계승.

#### REQ-NT3-C-005: bare except 금지

**The system shall not** use bare `except:` or `except Exception:` clauses in any Python file modified by this SPEC.

**The system shall** catch only specific exception types relevant to the operation (`requests.RequestException`, `requests.Timeout`, `json.JSONDecodeError`, `pydantic.ValidationError`, `KeyError`, `ValueError`).

**Rationale**: SPEC-002 REQ-NT2-C-005 정책 계승. V2 service.py 수정 시 기존 exception handling 패턴 유지.

#### REQ-NT3-C-006: V2 endpoint failure 시 V1 자동 폴백 금지

**The system shall not** automatically fall back to V1 endpoints when V2 endpoint requests fail.

**The system shall** display an error state and require explicit user action (retry button click) to re-attempt the V2 request.

**Rationale**: D-1 결정. UI 분기 최소화 + V1↔V2 schema 차이로 인한 자동 폴백 복잡도 회피. V1 endpoint는 cohabitation으로 보존되지만 자동 호출은 금지.

### 3.4 Routing Requirements

#### REQ-NT3-R-001: V1 endpoints 등록 유지

**The system shall** preserve V1 endpoints `GET /api/themes/snapshot` and `GET /api/themes/quick` registered in `backend/routers/themes.py` as a cohabitation rollback path.

**The system shall not** delete, comment out, or modify V1 route definitions.

#### REQ-NT3-R-002: V2 endpoints 등록 유지

**The system shall** preserve V2 endpoints `GET /api/themes/v2/snapshot` and `GET /api/themes/v2/quick` registered in `backend/routers/themes.py`, serving V2 data with V1-compatible metadata structure (after REQ-NT3-005 alias addition).

**Rationale**: SPEC-002 REQ-NT2-R-001/R-002에서 추가된 V2 routes를 본 SPEC 진행 중에도 무변경 보존.

---

## 4. Dependencies and Cohabitation

### 4.1 V1·V2 cohabitation strategy (Option γ 계승)

| Aspect | V1 (`backend/services/naver_theme/`) | V2 (`backend/services/naver_theme_v2/`) |
|---|---|---|
| Data source | finance.naver.com 데스크탑 정적 HTML | m.stock.naver.com `/front-api/...` JSON |
| FastAPI route | `/api/themes/snapshot`, `/api/themes/quick` | `/api/themes/v2/snapshot`, `/api/themes/v2/quick` |
| Module status | 무수정 (REQ-NT3-C-002) | metadata alias 추가 (REQ-NT3-005, REQ-NT3-C-003) |
| Frontend impact | V1 호출 중지 (frontend swap) — backend 자체는 등록 유지 | V2가 frontend 신규 호출 대상 |
| Rollback path | api/themes.ts URL을 V1으로 되돌리면 즉시 복귀 | — |

### 4.2 SPEC 계승 관계

- SPEC-NAVER-THEME-001 (V1, ship 완료): V1 backend + frontend ship의 baseline. 본 SPEC에서 무수정 보존.
- SPEC-NAVER-THEME-002 (V2 backend, ship 완료, v1.0.1): V2 backend 모듈 + V2 routes 등록 완료. 본 SPEC의 hard prerequisite.
- SPEC-NAVER-THEME-003 (본 SPEC): V2 frontend 채택 + V2 backend metadata V1 alias 추가.

---

## 5. Exclusions (What NOT to Build)

본 SPEC 범위에서 **명시적으로 제외**되는 항목 (별도 SPEC에서 다룬다):

| 항목 | 분류 | 사유 |
|---|---|---|
| 캐시 정책 (TTL, lru_cache) | 별도 SPEC (handoff §5 — "SPEC-NAVER-THEME-CACHE") | 본 SPEC 완료 후 V1+V2 양쪽 캐시 적용 정책 단순화 가능 |
| V1 endpoint dead-code cleanup | 별도 SPEC | V1 cohabitation rollback path 보존 (REQ-NT3-R-001) |
| Mobile hover 대체 UX (모바일 화면에서 theme_description 표시) | 별도 SPEC | native HTML `title`은 mobile touch 미동작. 본 SPEC desktop only 보장 |
| Radix Tooltip 또는 custom Tooltip 컴포넌트 도입 | 별도 SPEC | 신규 의존성 추가 (REQ-NT3-C-004 위배). native `title` 속성으로 충분 |
| stock_description 별도 컬럼/표시 (D-3 옵션 A — 마지막 컬럼 추가) | 별도 SPEC | D-3 결정으로 inclusion_reason 자리 재사용 — 신규 컬럼 표시는 미래 작업 |
| theme_description 길이 제한 (line-clamp, truncation 정책) | 별도 SPEC | native HTML title 자동 wrap 의존. CSS 정책은 추후 |
| V1↔V2 toggle UI (사용자가 V1/V2 선택) | 별도 SPEC 또는 미정 | D-1 결정으로 V2-only + 에러 retry. toggle 불필요 |
| 환경변수 기반 V1/V2 swap (`VITE_USE_V2_API`) | 별도 SPEC | D-1 옵션 C 거부. 빌드 단계 결정으로 fallback 동작 X |
| V2 응답 schema 검증 강화 (Pydantic response model 확장) | V2 SPEC-002 범위 | V2 backend ship 완료 시점에 결정됨 |
| SPEC-001 V1 모듈 수정 또는 삭제 | 절대 금지 (REQ-NT3-C-002) | 무수정 정책 계승 |
| frontend i18n (다국어) 지원 | 별도 SPEC | 본 SPEC는 한국어 description 표시만 |

---

## 6. Acceptance Criteria 요약

세부 AC는 `acceptance.md` 참조. 총 15개 AC (V2 14-AC 스타일 mirror + D-1 retry 검증 1 추가).

### Pass 조건 요약

- AC-1 ~ AC-15: 자동 검증 (pytest + vitest)
- frontend vitest baseline diff 0 (ChartGrid 기존 fail 그대로, 신규 fail 0)
- V1 단위 테스트 51개 그대로 PASS (회귀 0건, REQ-NT3-C-002 검증)
- V2 단위 테스트 24개 → metadata alias 추가 후 그대로 PASS (REQ-NT3-C-003 검증)
- V1 routes byte-identical (REQ-NT3-C-001 검증)

---

## 7. Glossary

| 용어 | 의미 |
|---|---|
| V1 endpoint | `/api/themes/snapshot`, `/api/themes/quick` (desktop HTML 크롤링 backend, SPEC-001) |
| V2 endpoint | `/api/themes/v2/snapshot`, `/api/themes/v2/quick` (mobile JSON API backend, SPEC-002) |
| theme_description | V2 mobile API `result.sectorDescription` — 테마 설명 (예: "각종 전선 및 전람(電纜)제조...") |
| stock_description | V2 mobile API `result.items[].description` — 종목별 편입설명 (forward-compat 필드, 본 SPEC 미사용) |
| inclusion_reason | V1/V2 ThemeStockItem의 편입사유 컬럼. V2 parser는 `inclusion_reason ← item.description`으로 매핑 → V2 endpoint 응답 시 자동으로 V2 description 노출 |
| metadata V1 alias | V2 metadata에 추가되는 `collected_at`, `theme_count`, `stock_count`, `elapsed_sec` — frontend가 기대하는 V1-호환 필드명 |
| Cohabitation | V1과 V2 endpoint 동시 등록. V2 frontend 채택 후에도 V1 즉시 rollback 가능 |
| D-1 ~ D-4 | 사용자 결정 사항 (annotation cycle 사전 잠금) — 각각 에러 처리, tooltip 위치, description 표시 자리, null 처리 |
| Tooltip | native HTML `title` 속성 기반 hover 도움말. Radix/custom 컴포넌트 미사용 |

---

## 8. References

### 8.1 SPEC 문서

- `.moai/specs/SPEC-NAVER-THEME-001/spec.md` (V1 v1.0.0 Approved)
- `.moai/specs/SPEC-NAVER-THEME-002/spec.md` (V2 backend v1.0.0)
- `.moai/specs/SPEC-NAVER-THEME-002/acceptance.md` (V2 14-AC v1.0.1)
- `.moai/specs/SPEC-NAVER-THEME-002/plan.md` (V2 implementation plan)
- `.moai/specs/SPEC-NAVER-THEME-002/handoff-frontend-v2.md` (Stage B 핸드오프, 488 lines, 본 SPEC의 핵심 입력)
- `.moai/specs/SPEC-NAVER-THEME-003/research.md` (본 SPEC research — 4 결정 rationale + 작업 분량)
- `.moai/specs/SPEC-NAVER-THEME-003/plan.md` (본 SPEC implementation plan)
- `.moai/specs/SPEC-NAVER-THEME-003/acceptance.md` (본 SPEC 15-AC)

### 8.2 외부 자원

- V2 mobile endpoint (config.py 격리, SPEC-002에서 검증 완료):
  - `https://m.stock.naver.com/front-api/stock/sectors/all` (list)
  - `https://m.stock.naver.com/front-api/domestic/sector/item/list` (detail)
- frontend vitest baseline: 256/257 PASS (ChartGrid 1 fail pre-existing, V2 무관)

---

Version: 1.0.0
Status: Draft (Pending User Approval)
Next phase: `/moai run SPEC-NAVER-THEME-003` (after approval + `/clear`)
