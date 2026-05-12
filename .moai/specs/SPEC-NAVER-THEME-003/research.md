---
id: SPEC-NAVER-THEME-003
title: V2 frontend 채택 — Research
status: Draft
version: 1.0.0
owner: bjw2002
created: 2026-05-06
updated: 2026-05-06
predecessor: SPEC-NAVER-THEME-002 (v1.0.1, V2 backend ship)
handoff_source: .moai/specs/SPEC-NAVER-THEME-002/handoff-frontend-v2.md
---

# Research: SPEC-NAVER-THEME-003 V2 frontend 채택

## 0. TL;DR

본 SPEC은 SPEC-NAVER-THEME-002 V2 backend ship 결과물(`/api/themes/v2/snapshot`, `/api/themes/v2/quick`)을 frontend가 채택하도록 한다. 핸드오프 문서(`handoff-frontend-v2.md`)가 이미 self-contained 컨텍스트를 제공하므로 본 research는 핸드오프 §3에서 정밀화 + 4 사용자 결정 사항(D-1 ~ D-4) rationale + risk 정리를 담당한다.

핵심 결정 (annotation cycle 회피용으로 사전 확정):
- D-1: V2 endpoint 503/timeout 시 **자동 폴백 없음 — 에러 메시지 + retry 버튼**
- D-2: theme_description은 **theme_name hover Tooltip**으로 표시 (레이아웃 변경 0)
- D-3: stock_description은 **기존 inclusion_reason 컬럼 자리 재사용** (V2 parser가 동일 source로 채움 → frontend 변경 거의 0)
- D-4: description=null 항목은 **hidden** (placeholder/icon 미표시)

---

## 1. 현재 상태 (As-Is)

### 1.1 V2 backend ship 결과 (SPEC-002 종료 시점, 2026-05-01)

| 항목 | 결과 | 출처 |
|---|---|---|
| V2 단위 테스트 | 24/24 GREEN | `tests/test_naver_theme_v2_*.py` |
| 라이브 통합 | 1/1 PASS (`@pytest.mark.live`) | 동일 |
| V1 회귀 | 51/51 PASS (변경 0) | `tests/test_naver_theme_*.py` |
| frontend vitest | 256/257 PASS (1 fail은 ChartGrid baseline pre-existing, V2 무관) | baseline |
| bare except | 0건 (REQ-NT2-C-005 준수) | grep |
| inline URL | 0건 (config.py 외, REQ-NT2-NF-005 준수) | AC-14 |
| DB mtime | 무변경 (REQ-NT2-C-004, AC-11 준수) | DB stat |

### 1.2 운영 중 frontend 호출 현황

frontend `frontend/src/api/themes.ts`가 V1 endpoint만 호출:
- line 68: `client.get('/themes/snapshot', ...)` (V1)
- line 75: `client.get('/themes/quick', ...)` (V1)

V2 endpoint(`/themes/v2/snapshot`, `/themes/v2/quick`) 호출 코드 0건 → V2가 V1과 동일 화면으로 보이는 원인. SPEC-002 §5 Exclusions에서 명시적으로 "frontend ThemeAnalysisResult 컬럼 활용 — 별도 SPEC"로 분리 — 본 SPEC가 그 분리된 작업을 담당.

### 1.3 V2 service.py metadata 현황 (handoff §3.2 도출)

`backend/services/naver_theme_v2/service.py:131-136`의 metadata는 다음 4 필드만 존재:
- `data_source`: "naver_mobile_v2"
- `generated_at`: ISO-8601 UTC
- `total_themes_seen`: int
- `errors`: list[dict]

frontend `themes.ts:46-52`가 기대하는 V1 metadata 필드는 다음과 같다 (V1 호환):
- `collected_at`: str (ISO-8601)
- `theme_count`: int
- `stock_count`: int
- `elapsed_sec`: float
- `errors`: list

V2 → V1 매핑 필요:
- `collected_at` ← `generated_at` (alias)
- `theme_count` ← `total_themes_seen` (alias)
- `stock_count` ← `len(stocks_df)` (계산)
- `elapsed_sec` ← 실측 측정 (현재 미보유)
- `errors`: 동일

`_empty_result` 헬퍼에도 동일 alias 필요 (handoff §3.2).

---

## 2. V1 vs V2 endpoint/스키마 차이 매트릭스

### 2.1 endpoint URL

| 모드 | V1 | V2 |
|---|---|---|
| Snapshot | `GET /api/themes/snapshot` | `GET /api/themes/v2/snapshot` |
| Quick | `GET /api/themes/quick` | `GET /api/themes/v2/quick` |
| 응답 시간 (snapshot) | ~30s (desktop HTML 크롤) | ~30s (mobile JSON) |
| 응답 시간 (quick) | ~10s | ~10s |
| 인코딩 | EUC-KR (강제) | UTF-8 (default) |

### 2.2 응답 schema 컬럼 (frontend 시점)

| 위치 | V1 | V2 (additive) |
|---|---|---|
| ThemeItem | `theme_id`, `theme_name`, `change_pct`, `change_pct_3d`, `momentum_score?`, `breadth_ratio?`, `top_stocks_preview?` | + `theme_description?: string \| null` (NEW) |
| ThemeStockItem | `theme_id`, `theme_name`, `stock_code`, `stock_name`, `inclusion_reason`, `price`, `change`, `change_pct`, `volume`, `trade_value`, `market_cap`, `leader_score?`, `rank?` | + `stock_description?: string \| null` (NEW, optional) |
| metadata | `collected_at`, `theme_count`, `stock_count`, `elapsed_sec`, `errors` | 동일 (V2 alias 추가 후 1:1 매칭) |

### 2.3 D-3 핵심 관찰 — inclusion_reason과 description의 동일 source

V2 `backend/services/naver_theme_v2/parser.py:271-272` (handoff §7.2 인용):
```python
"inclusion_reason": item.get("description"),  # V1 컬럼 호환성 — V1의 inclusion_reason 자리에 V2 description 매핑
"stock_description": item.get("description"),  # V2 신규 컬럼 (REQ-NT2-005)
```

→ V2 parser가 mobile API의 `item.description`을 두 컬럼(`inclusion_reason`, `stock_description`)에 동일하게 채움. 따라서 frontend ThemeDetailPanel이 기존 `stock.inclusion_reason`을 그대로 표시하면 V2의 description이 자동으로 노출됨. **stock_description 컬럼은 forward-compat용으로 타입에만 추가, 실제 UI 변경 0.**

V1 desktop HTML의 `inclusion_reason`(편입사유)과 V2 mobile의 `description`(편입설명)은 의미상 동일하므로 cohabitation 시 정합 ✓.

---

## 3. 코드 위치 매트릭스 (변경 영향 범위)

### 3.1 Backend (V2 — 변경 대상)

| 파일 | 변경 유형 | 변경 내용 |
|---|---|---|
| `backend/services/naver_theme_v2/service.py` | EDIT | `collect_and_analyze_v2` metadata에 V1 alias 4 필드 추가 + `_empty_result` 동일 적용 |
| `backend/services/naver_theme/` (V1) | 무수정 | REQ-NT3-C-002 — SPEC-001 정책 계승 |
| `backend/routers/themes.py` | 무수정 | V1+V2 routes 모두 byte-identical 보존 (REQ-NT3-R-001/R-002) |

### 3.2 Frontend (변경 대상)

| 파일 | 변경 유형 | 변경 내용 |
|---|---|---|
| `frontend/src/api/themes.ts` | EDIT | endpoint URL을 V2로 swap (line 68, 75). ThemeItem에 `theme_description?: string \| null` 추가. ThemeStockItem에 `stock_description?: string \| null` 추가 (forward-compat). V2 endpoint 503/timeout 에러 처리 (D-1) |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | EDIT | theme_name 셀에 hover Tooltip 추가 — `theme_description` 표시 (D-2). null이면 미표시 (D-4) |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | 무수정 (검증만) | 기존 `title={stock.inclusion_reason}` (line 62, 92)이 V2 description을 자동 노출 (D-3) — 변경 없음 |
| `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx` | EDIT (소) | V2 endpoint 실패 시 에러 메시지 + retry 버튼 (D-1). race condition fix(`ba3f20c`)는 그대로 |

### 3.3 Tests (변경 대상)

| 파일 | 변경 유형 | 변경 내용 |
|---|---|---|
| `tests/test_naver_theme_v2_service.py` | EDIT | V1 alias 4 필드 (collected_at, theme_count, stock_count, elapsed_sec) AC 추가 |
| `frontend/src/components/ThemeAnalysis/__tests__/*.test.tsx` | EDIT or NEW | V2 endpoint mock URL 검증 + tooltip rendering + null hidden + 에러 retry 시나리오 |

---

## 4. 사용자 결정 사항 Rationale (annotation cycle 사전 확정)

### 4.1 D-1: V2 endpoint failure 시 처리 — 에러 메시지 + retry

**선택지** (handoff §3.4):
- A. V1 자동 폴백
- **B. 에러 메시지만 표시 (사용자 수동 retry)** ✓
- C. 환경변수 toggle (VITE_USE_V2_API)
- D. 두 endpoint 동시 호출 + 빠른 응답

**Rationale**:
- A는 V1↔V2 schema 차이(theme_description 부재)로 UI rendering 분기 필요 → 복잡도 증가
- D는 backend 부하 2배 → mobile API 비공식 endpoint에 무례한 호출 (REQ-NT2-NF-001 매너 호출 정책 spirit 위배)
- C는 환경변수 빌드 단계 결정으로 fallback 동작 X (배포 후 변경 불가)
- **B**는 가장 단순. Sentry release `stock-web@` 활발한 risk(R-1) 시 사용자가 즉시 인지 + 재시도 가능. UI 분기 최소화 (REQ-NT3-NF-001).

**구현**: ThemeAnalysis.tsx의 `setError` state 활용. retry 버튼은 useEffect의 mode 의존성을 트리거하는 패턴 (이미 `ba3f20c` race condition fix 패턴과 호환).

### 4.2 D-2: theme_description 표시 위치 — Tooltip

**선택지** (handoff §3.4):
- **A. theme_name hover Tooltip** ✓
- B. 별도 컬럼 (테이블 가로 길이 증가)
- C. ThemeDetailPanel 확장
- D. accordion/collapse

**Rationale**:
- B는 테이블 가로 1 컬럼 증가 → 기존 6 컬럼(테마명/등락률/3일등락률/모멘텀/상승비율/대표종목) 대비 ~14% 폭 증가. 모니터 폭 좁은 사용자 가독성 저해.
- C는 description이 detail panel만 노출 → 강세 테마 ranking 시점에 정보 비공개 → UX 비효율
- D는 모바일 UX 우선. 데스크탑 위주 본 V1 화면에는 부적합.
- **A**는 레이아웃 변경 0 + desktop hover UX 일관성. CSS `title` 속성 또는 Radix Tooltip 사용 (테마 이름 셀에 wrap).

**구현 방식**: ThemeRankingTable.tsx line 79 `<td>{theme.theme_name}</td>`를 `<td title={theme.theme_description ?? undefined}>{theme.theme_name}</td>`로 EDIT. Radix UI 도입 없이 native HTML tooltip로 충분.

**모바일 hover 부재 한계**: HTML title 속성은 mobile touch에서 미동작. 본 SPEC 범위 외 — 별도 SPEC에서 추후 처리. 본 SPEC에서는 desktop hover만 보장.

### 4.3 D-3: stock_description 표시 — inclusion_reason 컬럼 재사용

**선택지** (handoff §3.4):
- A. ThemeDetailPanel stocks 테이블 마지막 컬럼 추가
- **B. inclusion_reason 컬럼 대체** ✓ (V2 parser가 동일 source)
- C. 종목 클릭 상세 panel
- D. 두 줄 표시

**Rationale**:
- A는 컬럼 추가 → 테이블 폭 증가
- C는 클릭 인터랙션 추가 → 현재 `title` 속성 hover와 UX 충돌
- D는 행 높이 2배 → 종목 많은 테마(20+ 종목)에서 스크롤 부하
- **B**는 V2 parser의 핵심 관찰(§2.3) 활용 — `inclusion_reason`과 `stock_description`이 V2에서 동일 source. ThemeDetailPanel이 이미 `title={stock.inclusion_reason}` 사용 중(line 62, 92)이므로 **frontend 변경 0**. V2 endpoint로 swap 시 자동 노출.

**구현 방식**: ThemeDetailPanel 무수정. `stock_description?` 필드만 ThemeStockItem 타입에 forward-compat용으로 추가 (향후 별도 SPEC에서 사용 가능).

**검증**: V2 endpoint 응답으로 받은 stocks의 `inclusion_reason`이 V1 desktop과 동일하게 표시되는지 vitest로 검증.

### 4.4 D-4: null 처리 — Hidden

**선택지** (handoff §3.4):
- **A. Hidden — null이면 렌더 안 함** ✓
- B. "—" placeholder
- C. italic placeholder
- D. tooltip만 표시 안 함

**Rationale**:
- B/C는 description이 null인 항목이 많을 때(라이브 PoC 기준 일부 sectorDescription null) 시각적 노이즈 누적. ThemeRankingTable이 264개 테마 표시 가능 — null placeholder 100개+ 표시 시 가독성 저하.
- **A**는 native HTML title 속성이 빈 문자열/undefined일 때 자동으로 tooltip 미표시 → 데이터 없으면 자연스럽게 hidden. 추가 분기 코드 0.
- D는 A와 동일 효과지만 의미 모호 (사용자 입장에서 동일).

**구현**: `title={theme.theme_description ?? undefined}` — nullish 시 attribute 자체 미렌더링. 혹은 `title={theme.theme_description || undefined}` (빈 문자열도 hidden). null/undefined/빈문자열 모두 hidden 보장.

---

## 5. Risk 분석 (handoff §3.5 정리 + 신규)

| ID | 위험 | 가능성 | 영향 | 완화 |
|---|---|---|---|---|
| R-1 | V2 endpoint URL 변경 (sentry release `stock-web@` 활발) | High | V2 데이터 수집 실패 → frontend 빈 화면 | D-1: 에러 메시지 + retry. SPEC-002 §config.py 격리 정책 그대로 (REQ-NT2-NF-005 계승) |
| R-2 | V2 응답 시간 30s — V1과 동일 | Medium | 사용자 체감 동일, 캐시 정책(별도 SPEC, Stage C)로 개선 | 본 SPEC 범위 외 |
| R-3 | theme_description/inclusion_reason 한국어 인코딩 | Low | UTF-8 default 정상 처리 (REQ-NT2-NF-002 검증 완료) | V2 응답 Content-Type `application/json; charset=utf-8` 검증 보존 |
| R-4 | description 길이 가변 (예: 100자~500자) | Medium | tooltip 가독성 저하 | native HTML title은 브라우저별 자동 wrap. 별도 CSS 처리 불필요. 길이 제한 정책은 별도 SPEC |
| R-5 | V2 frontend 채택 후 V1 endpoint dead code | Low | cleanup 별도 SPEC | V1 endpoint cohabitation 보존 (REQ-NT3-R-001) — V2 ship 후 즉시 V1로 rollback 가능 |
| R-6 | frontend vitest baseline 1 fail (ChartGrid pre-existing) 회귀 노이즈 | Low | 본 SPEC 회귀 판정 시 false signal | 본 SPEC ship 전 baseline diff 적용 (256/257 → 신규 vitest 추가 후 동일하게 1 fail 유지 검증) |
| R-7 | metadata V1 alias 추가가 V2 단위 테스트 AC-2(`data_source` 검증)와 충돌 | Low | 회귀 0 — additive only (REQ-NT3-C-003) | V2 SPEC v1.0.1 amendment 패턴 — superset 검증으로 재정의 |
| R-8 | D-3 가정(inclusion_reason과 stock_description 동일 source) 미래 변경 시 fragility | Low | parser 정책 변경 시 inclusion_reason 별도 source로 분기 → ThemeDetailPanel 수정 필요 | 본 SPEC가 구체적으로 V2 parser 현재 정책 의존성을 명시 (§2.3). 미래 변경은 별도 SPEC가 다룸 |
| R-9 | mobile hover 부재로 D-2 tooltip 미동작 | Medium (모바일 사용자) | 모바일 사용자가 theme_description 확인 불가 | 본 SPEC desktop only 보장. 모바일 UX는 별도 SPEC |
| R-10 | V2 endpoint 503 시 사용자 retry 무한 클릭 부하 | Low | 사용자 직접 클릭 패턴 — backend 부하 자연 제한 | retry 로직은 자동 재시도 X — 사용자 명시적 재시도만 (D-1) |

---

## 6. 의존성 그래프

```
SPEC-NAVER-THEME-001 (V1, ship 완료, 무수정)
                │
                ▼
SPEC-NAVER-THEME-002 (V2 backend ship 완료, v1.0.1)
                │
                ▼
SPEC-NAVER-THEME-003 (본 SPEC, V2 frontend 채택)  ← 본 작업
                │
                ▼ (선택, 향후)
SPEC-NAVER-THEME-CACHE (캐시 정책, handoff §5 — 별도 SPEC)
```

본 SPEC은 SPEC-002 ship 완료가 hard prerequisite. SPEC-001 V1 무수정 정책 계승. 이후 캐시 SPEC은 본 SPEC 완료 후 진행 권장 (V1+V2 양쪽 캐시 적용 정책 단순화).

---

## 7. 작업 분량 추정 (LOC + files)

handoff §3.2 매트릭스 정밀화 (D-3 결정 반영 후 ~30 LOC 감소):

| 파일 | 변경 규모 | 비고 |
|---|---|---|
| `backend/services/naver_theme_v2/service.py` | +20 LOC | metadata V1 alias 4 필드 + `_empty_result` 적용 |
| `frontend/src/api/themes.ts` | +10 LOC | endpoint swap + 타입 확장 + 에러 처리 |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | +1 LOC | tooltip 추가 (single line edit) |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | 0 LOC | 무수정 (D-3 — 검증만) |
| `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx` | +15 LOC | 에러 메시지 + retry 버튼 (D-1) |
| `tests/test_naver_theme_v2_service.py` | +15 LOC | metadata alias AC 추가 |
| `frontend/src/components/ThemeAnalysis/__tests__/` | +60 LOC | V2 endpoint mock + tooltip + 에러 + retry vitest |

**합계 예상**: ~120 LOC, 7 files (handoff 추정 145 LOC 대비 D-3 결정으로 ~25 LOC 감소).

---

## 8. References

### 8.1 SPEC 문서

- `.moai/specs/SPEC-NAVER-THEME-001/spec.md` (V1 v1.0.0)
- `.moai/specs/SPEC-NAVER-THEME-002/spec.md` (V2 backend v1.0.0)
- `.moai/specs/SPEC-NAVER-THEME-002/acceptance.md` (V2 14-AC v1.0.1)
- `.moai/specs/SPEC-NAVER-THEME-002/plan.md` (V2 implementation plan v1.0.0)
- `.moai/specs/SPEC-NAVER-THEME-002/handoff-frontend-v2.md` (488 lines, Stage B 컨텍스트, 본 SPEC의 핵심 입력)

### 8.2 코드 위치

- backend V2 ship: `backend/services/naver_theme_v2/{__init__,service,crawler,parser,config}.py`
- backend routes: `backend/routers/themes.py` (V1+V2 등록 완료)
- frontend API client: `frontend/src/api/themes.ts`
- frontend ThemeAnalysis 컴포넌트: `frontend/src/components/ThemeAnalysis/{ThemeAnalysis,ThemeRankingTable,ThemeDetailPanel}.tsx`
- 단위 테스트 (V2): `tests/test_naver_theme_v2_{parser,crawler,service,routes}.py`
- 통합 테스트 (V1+V2 라이브): 동일 디렉토리

### 8.3 Git history (브랜치 `chore/integrated-main-merge-2026-04-25`)

- `ba3f20c` race condition fix (Stage A, ThemeAnalysis.tsx)
- `b1c24eb` V2 T4 amendment (acceptance.md v1.0.1)
- `ad9e30d` V2 T2+T3 fixtures + 단위 테스트
- `888e2eb` V2 T1 backend 5 모듈 + routes
- `027f571` V1 ship documentation 동기화 + V2 핸드오프
- `12d81b1` V1 ship

---

Version: 1.0.0
Status: Draft (Pending User Approval)
Note: 핸드오프 문서가 self-contained이므로 본 research는 핸드오프의 정밀화 + 4 결정사항 rationale + 작업 분량 정밀화에 집중.
