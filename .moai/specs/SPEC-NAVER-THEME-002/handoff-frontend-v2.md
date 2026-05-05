---
id: HANDOFF-NAVER-THEME-FRONTEND-V2
title: V2 backend ship → V2 frontend 채택 + 캐시 정책 핸드오프
status: Active
version: 1.0.0
owner: bjw2002
created: 2026-05-01
predecessor: SPEC-NAVER-THEME-002 (v1.0.1, V2 backend ship)
successors:
  - SPEC-NAVER-THEME-FRONTEND-V2 (제안, Stage B)
  - SPEC-NAVER-THEME-CACHE (제안, Stage C)
---

# 핸드오프: SPEC-NAVER-THEME-002 → V2 frontend 채택 + 캐시 정책

## 0. TL;DR

- **V2 backend ship 완료** (commits `888e2eb` → `ad9e30d` → `b1c24eb`). V2 unit 24/24 GREEN, V1 회귀 51/51, 라이브 1건 PASS.
- **V1 운영 중 race condition UI bug 발견 → fix 완료** (commit `ba3f20c`). 빠른조회/전체조회 토글 시 stale 응답 무시 패턴 적용. 13 LOC 단일 파일.
- **V2가 V1과 동일한 화면**으로 보이는 이유: `frontend/src/api/themes.ts`가 V1 endpoint(`/themes/snapshot`, `/themes/quick`)만 호출. SPEC-002 §5 Exclusions에서 명시적으로 별도 SPEC로 분리한 의도. → **Stage B**에서 처리.
- **누를 때마다 다시 크롤링**: V1+V2 모두 stateless 설계 (REQ-NT2 §1.1 + V1 동일). 캐시 추가는 별도 SPEC. → **Stage C**에서 처리.
- **본 핸드오프 목적**: Stage B(우선) + Stage C(후속) 진행자가 self-contained로 컨텍스트를 파악하여 SPEC plan을 시작할 수 있게 한다.

---

## 1. 현재 상태 (As-Is, 2026-05-01)

### 1.1 SPEC-NAVER-THEME-002 V2 backend ship 결과

| 항목 | 결과 |
|---|---|
| V2 단위 테스트 | 24/24 GREEN (`tests/test_naver_theme_v2_*.py`) |
| 라이브 통합 | 1/1 PASS (`@pytest.mark.live`) |
| V1 회귀 | 51/51 PASS (`tests/test_naver_theme_*.py`) |
| frontend vitest | 256/257 PASS (1 fail은 ChartGrid baseline pre-existing, V2 무관) |
| bare except | 0건 (REQ-NT2-C-005) |
| inline URL | 0건 (REQ-NT2-NF-005, config.py 외) |
| DB mtime | 무변경 (REQ-NT2-C-004, AC-11) |
| coverage | 정밀 측정 미수행 (venv 환경 분리 — `my-project-01/my_chart/.venv`에 numpy/pandas 부재). manual review 추정 85-95%. **Stage B/C 진입 전 `uv sync`로 환경 정리 권장**. |
| ruff lint | skip (dev 의존성 부재) |

### 1.2 운영 중 발견된 3가지 이슈 + 진단 + 처리 상태

#### 이슈 1: 빠른조회 ↔ 전체조회 화면 sync 이상 → **Stage A에서 fix 완료** ✅

증상: 페이지 첫 진입 시 자동으로 quick fetch(10s) 시작. 응답 도착 전 사용자가 "전체조회" 클릭 시 full fetch(30s) 추가 시작. 두 in-flight fetch의 then 콜백 도착 순서 race로 quick 응답이 뒤늦게 도착하면 mode='full' 상태에서 quick 데이터로 setData → 빠른조회 화면이 전체조회 화면 자리에 표시.

원인: `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx:34-66`의 useEffect가 mode 변경 시 새 fetch 시작하지만 이전 fetch는 cancellation 없이 계속 진행. cleanup function 부재.

해결: useEffect cleanup에서 `cancelled` flag 설정. 이전 fetch의 then/catch/finally 콜백 진입 시 `cancelled=true`이면 setData/setError/setLoading 건너뜀.

commit: `ba3f20c` — fix(theme-analysis): race condition 방지 — 빠른조회/전체조회 토글 stale 응답 무시 (+12 LOC).

#### 이슈 2: V2가 V1과 동일하다 → **Stage B로 이관** 🟡

증상: V2 backend ship(`888e2eb`) 후에도 사용자 화면이 V1과 동일하게 보임 (테마 264개, change_pct 등 V1 컬럼만 표시). V2의 신규 컬럼 `theme_description`, `stock_description`은 표시 안 됨.

원인: `frontend/src/api/themes.ts`가 `/themes/snapshot`, `/themes/quick` (V1 endpoint)만 호출. V2 endpoint(`/themes/v2/snapshot`, `/themes/v2/quick`) 호출 코드 0건. SPEC-002 §5 Exclusions 명시: "frontend ThemeAnalysisResult 컬럼 활용 (theme_description, stock_description) — 별도 SPEC". 즉 의도된 분리.

처리: **Stage B** (V2 frontend 채택 SPEC) 신규 작성 후 진행.

#### 이슈 3: 누를 때마다 다시 크롤링 → **Stage C로 이관** 🟡

증상: 빠른조회/전체조회 버튼 클릭마다 backend가 mobile/desktop 사이트를 새로 크롤링. 빠른조회 10s, 전체조회 30s. 같은 메뉴 반복 클릭 시 누적 시간 낭비.

원인: V1 `backend/services/naver_theme/service.py` + V2 `backend/services/naver_theme_v2/service.py` + `backend/routers/themes.py` 모두 cache/TTL/lru_cache 0건. SPEC-002 §1.1: "stateless, 스케줄러 없음 (호출 1회당 1 사이클)". V1도 동일 패턴. 즉 의도된 stateless 설계.

처리: **Stage C** (캐시 정책 SPEC) 신규 작성 후 진행.

### 1.3 git history 요약 (chore/integrated-main-merge-2026-04-25 branch)

```
ba3f20c fix(theme-analysis): race condition 방지 — 빠른조회/전체조회 토글 stale 응답 무시
b1c24eb fix(naver-theme-v2): T4 amendment — V1 실측 컬럼 정정 + SPEC artifacts 추가
ad9e30d feat(naver-theme-v2): T2+T3 — fixtures 4종 + V2 단위 테스트 4파일 (SPEC-NAVER-THEME-002)
888e2eb feat(naver-theme-v2): T1 — V2 backend 5 모듈 + routes EDIT (SPEC-NAVER-THEME-002)
027f571 docs(naver-theme): SPEC-NAVER-THEME-001 V1 ship documentation 동기화 + V2 핸드오프
12d81b1 feat(naver-theme): SPEC-NAVER-THEME-001 V1 MVP 구현 완료
6c203d3 feat(naver-theme): phase 1 — 완전한 백엔드 모듈 구현 (config, crawler, parser, analyzer, service, routes)
```

### 1.4 운영 서버 상태

- 실행 중인 uvicorn 프로세스: PID 35179 (`/Users/byunjungwon/Dev/my_chart/.venv/bin/python3 .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1`)
- 실행 시점 확인 필요 — V2 commit (888e2eb 이후) 후 재시작 안 됐을 가능성. 재시작 시 V2 endpoint 활성화.
- venv 경로: `/Users/byunjungwon/Dev/my_chart/.venv` (다른 프로젝트의 venv — 본 my-project-01과 다름. 의존성은 동일하지만 별개 환경).

---

## 2. 다음 단계 후보 (To-Be)

### 2.1 Stage B (메인): V2 frontend 채택

- 목적: 사용자가 V2 데이터(theme_description, stock_description)를 화면에서 확인 가능하게 함
- 작업 분량: ~150-200 LOC, 4-6 files
- 의존: SPEC-NAVER-THEME-002 v1.0.1 (V2 backend ship 완료)
- 의존성 충돌: 없음 (V2 routes는 이미 등록됨, frontend 변경만)

### 2.2 Stage C (후속): 캐시 정책

- 목적: 같은 endpoint 반복 호출 시 즉시 응답 (사용자 체감 개선)
- 작업 분량: ~50-100 LOC, 1-3 files
- 의존: Stage B 권장(V2 채택 후 V1+V2 양쪽 캐시 적용 정책 결정 단순화)
- 우선순위: Medium (사용자 체감 개선이지만 functional 영향 없음)

---

## 3. Stage B 상세 — V2 frontend 채택

### 3.1 Goal & Outcome

- **Goal**: frontend가 V2 endpoint를 호출하여 V2의 신규 컬럼(theme_description, stock_description)을 화면에 표시
- **Outcome**: 사용자가 "테마 분석" 탭에서 각 테마의 설명(예: "각종 전선 및 전람(電纜)제조...")과 종목별 편입사유(예: "전선 제조사로 자동차 와이어하네스 등 다각화")를 확인 가능
- **Cohabitation**: V2 frontend 채택 후에도 V1 endpoint와 V1 backend 모듈은 무수정 유지(REQ-NTF2-C-001/C-002). 즉시 V1로 rollback 가능.

### 3.2 Scope (변경 파일 매트릭스)

| 파일 | 변경 유형 | 변경 규모 (예상) | 변경 내용 |
|---|---|---|---|
| `backend/services/naver_theme_v2/service.py` | EDIT | +20 LOC | metadata에 V1 alias 4 필드 추가 (`collected_at=generated_at`, `theme_count=total_themes_seen`, `stock_count=len(stocks_df)`, `elapsed_sec`) |
| `backend/services/naver_theme_v2/service.py` | EDIT | +5 LOC | `_empty_result` 헬퍼에도 동일 alias 추가 |
| `frontend/src/api/themes.ts` | EDIT | +10 LOC | endpoint URL을 `/themes/v2/snapshot`, `/themes/v2/quick`로 swap. ThemeItem/ThemeStockItem 타입에 `theme_description?`, `stock_description?` 추가 |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | EDIT | +20 LOC | theme_description 표시 (선택: tooltip / 별도 컬럼 / hover panel — 결정 필요) |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | EDIT | +20 LOC | stock_description 표시 (선택: inclusion_reason 대체 / 추가 컬럼 / Detail panel 확장 — 결정 필요) |
| `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx` | (선택) EDIT | +5 LOC | V1 fallback toggle UI (V2 endpoint 503 시 V1로 폴백 결정 시) |
| `frontend/src/components/ThemeAnalysis/__tests__/*.test.tsx` | NEW or EDIT | +50 LOC | V2 endpoint mock 패턴 + theme_description/stock_description rendering 검증 |
| `tests/test_naver_theme_v2_service.py` | EDIT | +15 LOC | metadata alias 검증 추가 |

**합계 예상**: ~145 LOC, 7-8 files.

### 3.3 Constraints (제약)

- [HARD] **REQ-NTF2-C-001**: V1 routes (`GET /api/themes/snapshot`, `GET /api/themes/quick`) byte-identical 보존. 회귀 차단.
- [HARD] **REQ-NTF2-C-002**: V1 backend 모듈(`backend/services/naver_theme/*`) 무수정. SPEC-001 무수정 정책 그대로 유지.
- [HARD] **REQ-NTF2-C-003**: V2 backend service.py metadata는 additive only — 기존 필드(`data_source`, `generated_at`, `total_themes_seen`, `errors`) 제거 금지. V1 alias만 추가.
- [HARD] **REQ-NTF2-C-004**: pip 신규 의존성 금지 (V1+V2 의존성 그대로).
- [HARD] **REQ-NTF2-C-005**: bare except 금지 (V2 SPEC-002 §3.3 정책 계승).

### 3.4 사전 결정 필요 사항 (annotation cycle에서 결정)

#### D-1: V2 endpoint failure 시 fallback 정책

**옵션**:
- A. V1으로 자동 폴백 (frontend가 V2 503/timeout 감지 → V1 endpoint 호출)
- B. 에러 메시지만 표시 (사용자가 새로고침/재시도 직접 선택)
- C. 환경변수로 V1/V2 선택 (`VITE_USE_V2_API=true` toggle)
- D. 두 endpoint 동시 호출 + 빠른 응답 사용 (race + abort 다른 쪽)

**권장**: B 또는 C. A는 V1과 V2의 schema 차이(theme_description 부재) 때문에 UI rendering 분기 필요 → 복잡도 증가.

#### D-2: theme_description 표시 위치/방식

**옵션**:
- A. Tooltip — theme_name hover 시 description 표시 (가장 가벼움)
- B. 별도 컬럼 — ThemeRankingTable에 새 컬럼 추가 (테이블 가로 길이 증가)
- C. 선택된 테마의 hover/click 시 panel에 표시 (ThemeDetailPanel 확장)
- D. 모바일 친화 — accordion/collapse 형태

**권장**: A (Tooltip)가 가장 간단하고 desktop UX 일관성. 모바일은 추후 별도 SPEC.

#### D-3: stock_description 표시 위치/방식

**옵션**:
- A. ThemeDetailPanel의 stocks 테이블 마지막 컬럼으로 추가
- B. inclusion_reason 컬럼 대체 (V2 mobile API의 description은 V1의 inclusion_reason과 동일 의미)
- C. 종목 클릭 시 상세 panel에 표시
- D. 두 줄 표시 (1줄: 종목명/현재가, 2줄: description)

**권장**: A 또는 B. V1의 `inclusion_reason`은 V1 desktop HTML에서 별도 cell이고 V2 mobile API의 `description`은 같은 의미. **단일 source 원칙으로 B(대체)가 더 깔끔**. 단, V2 endpoint 503 시 V1으로 폴백 케이스에서 inclusion_reason이 V1 값으로 fallback 되는지 확인.

#### D-4: null 처리 UX

**옵션**:
- A. Hidden — null이면 렌더 안 함
- B. "—" placeholder
- C. italic placeholder ("(설명 없음)")
- D. Tooltip 만 표시 안 함 (hover 시 빈 tooltip)

**권장**: A (Hidden). 데이터 풍부한 항목 위주 UX, null이 많을 때 시각적 노이즈 감소.

### 3.5 Risk 분석

| ID | 위험 | 가능성 | 영향 | 완화 |
|---|---|---|---|---|
| R-1 | V2 endpoint URL 변경(sentry release "stock-web@" 활발) | High | V2 데이터 수집 실패 → frontend 빈 화면 | D-1 fallback 정책 적용. SPEC-002 §config.py 격리 정책 그대로 유지. |
| R-2 | V2 응답 시간 30s — V1과 동일 | Medium | 사용자 체감 동일, 캐시 정책(Stage C) 후 개선 | Stage C 후순 진행 |
| R-3 | theme_description/stock_description 한국어 인코딩 | Low | UTF-8 default로 정상 처리 (REQ-NT2-NF-002에서 검증) | V2 응답 Content-Type `application/json; charset=utf-8` 검증 보존 |
| R-4 | description 길이 가변 (예: 100자~500자) | Medium | UI 레이아웃 깨짐 | CSS truncate (line-clamp 3) + 풀텍스트는 tooltip/expand로 |
| R-5 | V2 frontend 채택 후 V1 endpoint 사용처 부재 | Low | dead code (cleanup 별도 SPEC) | V1 endpoint는 cohabitation으로 유지 (REQ-NTF2-C-001) |
| R-6 | frontend vitest baseline 1 fail (ChartGrid pre-existing)로 회귀 검증 노이즈 | Low | 본 SPEC 회귀 판단 시 false signal | 본 SPEC ship 전 baseline 비교(diff) 적용 |
| R-7 | metadata 필드 4종 alias 추가가 V2 단위 테스트 AC-2(data_source 검증)와 충돌 | Low | 회귀 0 — additive only | T4 amendment처럼 superset 검증으로 재정의 |

### 3.6 EARS REQ 후보 (manager-spec이 정밀화)

#### Functional

- **REQ-NTF2-001**: The system shall update `frontend/src/api/themes.ts` to call `/api/themes/v2/snapshot` and `/api/themes/v2/quick` endpoints.
- **REQ-NTF2-002**: The `frontend/src/api/themes.ts` ThemeItem and ThemeStockItem types shall include optional fields `theme_description?: string | null` and `stock_description?: string | null`.
- **REQ-NTF2-003**: The system shall display `theme_description` in the ThemeRankingTable component (위치 D-2 결정 후 명세).
- **REQ-NTF2-004**: The system shall display `stock_description` in the ThemeDetailPanel component (위치 D-3 결정 후 명세).
- **REQ-NTF2-005**: The `backend/services/naver_theme_v2/service.py` `collect_and_analyze_v2` function shall populate `metadata` with V1-compatible alias fields: `collected_at` (str, ISO-8601), `theme_count` (int), `stock_count` (int), `elapsed_sec` (float).
- **REQ-NTF2-006**: The `_empty_result` helper shall populate the same V1 alias fields with zero values.

#### Non-Functional

- **REQ-NTF2-NF-001** (D-1 결정): WHEN V2 endpoint fails (HTTP 5xx/timeout), the frontend SHALL [표시 에러 메시지 / V1 폴백 / 환경변수 toggle].
- **REQ-NTF2-NF-002** (D-4 결정): WHEN `theme_description` or `stock_description` is null, the frontend SHALL hide the related UI element (no placeholder).
- **REQ-NTF2-NF-003**: V2 응답 시간 SHALL remain ≤ 30s (snapshot), ≤ 10s (quick) — V2 SPEC NF-004 보존.
- **REQ-NTF2-NF-004**: theme_description/stock_description rendering SHALL gracefully truncate long text (CSS line-clamp 3, full text via tooltip/expand).

#### Constraints (위 §3.3 내용)

- REQ-NTF2-C-001 ~ C-005

#### Routing

- **REQ-NTF2-R-001**: V1 endpoints `/api/themes/snapshot`, `/api/themes/quick` SHALL remain byte-identical and registered.
- **REQ-NTF2-R-002**: V2 endpoints `/api/themes/v2/snapshot`, `/api/themes/v2/quick` SHALL serve V2 data with V1-compatible metadata structure.

### 3.7 Acceptance Criteria 후보 (acceptance.md 작성 시 14-AC 패턴 권장)

| AC | 검증 항목 | 검증 방식 |
|---|---|---|
| AC-NTF2-1 | api/themes.ts가 `/themes/v2/snapshot`, `/themes/v2/quick`을 호출 | unit (mock client.get URL 캡처) |
| AC-NTF2-2 | ThemeItem 타입에 theme_description?: string \| null 존재 | unit (TypeScript type assertion 또는 runtime presence) |
| AC-NTF2-3 | ThemeStockItem에 stock_description?: string \| null 존재 | unit |
| AC-NTF2-4 | V2 service.py metadata에 V1 alias 4 필드 (collected_at, theme_count, stock_count, elapsed_sec) 모두 존재 | unit (live mock + assert) |
| AC-NTF2-5 | metadata.collected_at은 ISO-8601 형식 | unit (parsable) |
| AC-NTF2-6 | metadata.elapsed_sec은 float, 호출 시간 측정 정확 | unit |
| AC-NTF2-7 | ThemeRankingTable이 theme_description을 D-2 결정 위치에 표시 | RTL render + getByText/getByRole |
| AC-NTF2-8 | ThemeDetailPanel이 stock_description을 D-3 결정 위치에 표시 | RTL |
| AC-NTF2-9 | theme_description=null 항목은 D-4 결정대로 처리 (예: hidden) | RTL |
| AC-NTF2-10 | V1 routes가 여전히 등록되어 있고 함수명 byte-identical | TestClient route inspection |
| AC-NTF2-11 | V1 backend 모듈 0 변경 (`git diff backend/services/naver_theme/` 결과 empty) | git diff |
| AC-NTF2-12 | V2 endpoint 503 mock 시 D-1 결정대로 처리 | RTL + axios mock |
| AC-NTF2-13 | V1 51 단위 테스트 회귀 0 | pytest |
| AC-NTF2-14 | V2 22 단위 테스트(metadata alias 추가 후) 그대로 PASS | pytest |
| AC-NTF2-15 | frontend vitest baseline diff 0 (ChartGrid 기존 fail 그대로, 신규 fail 0) | vitest + baseline 비교 |

### 3.8 작업 단계 분해 (예상 phase, 사용자 결정 후 정밀화)

| Phase | 담당 | 우선순위 | 의존 |
|---|---|---|---|
| Phase 1 — V2 service.py metadata alias 추가 | backend | High | 없음 |
| Phase 2 — V2 단위 테스트 metadata alias AC 추가 | tester | High | Phase 1 |
| Phase 3 — frontend api/themes.ts swap + 타입 확장 | frontend | High | Phase 1 |
| Phase 4 — ThemeRankingTable theme_description 표시 (D-2) | frontend | High | Phase 3 |
| Phase 5 — ThemeDetailPanel stock_description 표시 (D-3) | frontend | High | Phase 3 |
| Phase 6 — frontend vitest 작성/업데이트 | tester | High | Phase 4, 5 |
| Phase 7 — V1 회귀 + frontend 통합 검증 | manager-quality | High | Phase 1~6 |

---

## 4. Stage A 상세 — 완료 (race condition fix)

### 4.1 변경 사항

파일: `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx`
변경 규모: +12 LOC (단일 파일)
commit: `ba3f20c`

핵심 패턴:
```typescript
useEffect(() => {
  let cancelled = false  // ← 추가
  setLoading(true)
  setError(null)
  const promise = mode === 'quick' ? fetchThemesQuick() : fetchThemesSnapshot()

  promise
    .then(result => {
      if (cancelled) return  // ← 추가
      // ... 기존 setData 로직
    })
    .catch(e => {
      if (cancelled) return  // ← 추가
      // ... 기존 setError
    })
    .finally(() => {
      if (cancelled) return  // ← 추가
      setLoading(false)
    })

  return () => {           // ← 추가 (cleanup)
    cancelled = true
  }
}, [mode])
```

### 4.2 검증 결과

- frontend vitest: 256/257 PASS (baseline 동일, 신규 회귀 0)
- 1 fail은 ChartGrid baseline pre-existing — 본 fix는 ThemeAnalysis 단일 파일이라 ChartGrid 영향 0
- 사용자 시나리오 재현 검증은 manual UI 테스트 권장 (실 서버 재시작 + 브라우저에서 빠른조회/전체조회 빠른 토글 시 화면 일관성 확인)

### 4.3 미수행 작업 (선택)

- ThemeAnalysis.tsx 전용 vitest 단위 테스트 추가 (race condition 시나리오 fake timers + mock fetch). 본 fix는 단순 패턴이라 baseline 회귀 0이면 충분하지만, **Stage B 진행 시 같은 컴포넌트를 수정하므로 그 시점에 통합 테스트 추가 권장**.

---

## 5. Stage C 부록 — 캐시 정책

### 5.1 옵션 비교

| 옵션 | 위치 | 장점 | 단점 | 작업 분량 |
|---|---|---|---|---|
| A. Backend in-memory TTL cache | `backend/services/naver_theme/service.py` + `naver_theme_v2/service.py` | 모든 호출자에게 즉시 효과(curl, frontend 모두). 다중 사용자 공유. | 서버 메모리 사용. 멀티 worker 시 worker별 cache. force-refresh 정책 필요. | ~50 LOC, 함수 wrapping |
| B. Backend cache with Redis/SQLite | 같은 위치 | 멀티 worker 공유. 영속화 가능. | 인프라 의존성 추가. SPEC-002 §3.3 REQ-NT2-C-003 (pip 신규 의존성 금지) 위배 가능. | ~100 LOC + 인프라 |
| C. Frontend React Query staleTime | `frontend/src/api/themes.ts` 또는 hooks | 단일 사용자 컨텍스트, 단순. | 다른 클라이언트(curl, mobile)에 효과 없음. 새로고침 시 cache 없음(default). | ~30 LOC + react-query 라이브러리 |
| D. Combined (A + C) | 양쪽 | 최강. 다층 cache. | 복잡도 증가. cache invalidation 정책 결정 필요. | ~80 LOC |

### 5.2 추천 정책

**옵션 A (Backend in-memory TTL cache)** + 짧은 TTL (예: 5분).

이유:
- pip 신규 의존성 0 — `functools.lru_cache(maxsize=2)` 또는 단순 dict + timestamp로 가능
- frontend 무수정 — Stage B와 분리하여 진행 가능
- multi-worker(workers=N)는 SPEC-001 시점에 단일 worker 정책(workers=1, backend/main.py:128) — cache가 단일 instance에 안전하게 적용
- force-refresh 옵션은 query param (예: `?force=true`) 또는 cache-bust API 추가

EARS REQ 후보 (간단):
- REQ-NTC-001: V1+V2 service.py에 5분 TTL cache 추가
- REQ-NTC-002: cache key는 (top_n_themes, leaders_per_theme, skip_details) 튜플
- REQ-NTC-003: query param `?force=true`로 cache-bypass
- REQ-NTC-NF-001: cache hit 시 응답 < 100ms
- REQ-NTC-C-001: 단일 worker 가정 — multi-worker 시 별도 SPEC

### 5.3 의존성

- Stage B 완료 후 진행 권장 (V2 채택 후 V1+V2 양쪽 cache 적용 정책 단순화). Stage B 미완 시에도 V1만 cache 적용 가능.
- 운영 서버 재시작 필요 (cache 모듈 로드).

---

## 6. Open Questions

### 6.1 Stage B Open Questions

1. **V1/V2 toggle UI 노출?** — 사용자가 직접 V1/V2 선택? 또는 환경변수만? 또는 V2 default + V1 hidden fallback?
2. **theme_description 한국어 vs 영어?** — V2 mobile API는 한국어. 프론트는 한국어만 표시? i18n 지원?
3. **description max length 정책?** — line-clamp 3 vs 5 vs unlimited (스크롤)? Tooltip 길이 제한?
4. **모바일 반응형 우선순위?** — "테마 분석" 탭이 모바일 사용 빈도가 높은가? 모바일에서 description 표시 방식 어떻게?
5. **API 버전 관리 정책?** — `/api/v2/themes/...` (api 자체에 v2) vs `/api/themes/v2/...` (현재). V3 시점에 어떻게 확장?

### 6.2 Stage C Open Questions

1. **Cache TTL 적정 값?** — 5분 vs 10분 vs 1시간? 시장 시간(09:00~15:30 KST)에는 짧게, 장 마감 후에는 길게?
2. **Cache size limit?** — `lru_cache(maxsize=N)` — N=2(snapshot+quick)로 충분?
3. **장 마감 후 frozen cache 정책?** — 장 마감 후에는 cache 무한 보관? 또는 24시간?
4. **force-refresh 권한?** — 누구나 가능 vs admin only?
5. **Stage B와 동시 진행 vs 순차?** — V2 채택 후 cache 추가가 깔끔하지만 Stage C는 V1만으로도 진행 가능

### 6.3 환경 정리 Open Question

- venv 분리 (`my_chart/.venv` vs `my-project-01/my_chart/.venv`)는 의도된 설정인지 정리 대상인지 사용자 확인 필요. SPEC 작업 전 `uv sync` 실행 권장.

---

## 7. References

### 7.1 SPEC 문서

- `.moai/specs/SPEC-NAVER-THEME-001/spec.md` (V1, v1.0.0 Approved)
- `.moai/specs/SPEC-NAVER-THEME-001/v2-handoff.md` (480 lines, V2 SPEC 작성용 self-contained)
- `.moai/specs/SPEC-NAVER-THEME-002/spec.md` (V2, v1.0.0)
- `.moai/specs/SPEC-NAVER-THEME-002/plan.md` (V2 implementation plan)
- `.moai/specs/SPEC-NAVER-THEME-002/research.md` (V2 PoC + 코드베이스 분석)
- `.moai/specs/SPEC-NAVER-THEME-002/acceptance.md` (14 AC, v1.0.1 amendment)
- 본 문서: `.moai/specs/SPEC-NAVER-THEME-002/handoff-frontend-v2.md` (현재)

### 7.2 코드 위치 매트릭스

#### Backend (V1 — 무수정)

| 파일 | 역할 |
|---|---|
| `backend/services/naver_theme/__init__.py` | `collect_and_analyze`, `ThemeAnalysisResult` re-export |
| `backend/services/naver_theme/service.py` | V1 entrypoint + ThemeAnalysisResult @dataclass 정의 |
| `backend/services/naver_theme/analyzer.py` | `build_strong_themes`, `build_leaders`, `build_multi_theme_stocks` |
| `backend/services/naver_theme/db_join.py` | `enrich_market_cap(stocks_df, db_path)` (DataFrame 단위) |
| `backend/services/naver_theme/parser.py` | bs4 + lxml HTML parsing |
| `backend/services/naver_theme/crawler.py` | EUC-KR 강제 + Retry |
| `backend/services/naver_theme/config.py` | desktop URL, EUC-KR 상수 |

#### Backend (V2 — Stage B에서 metadata alias 추가)

| 파일 | 역할 |
|---|---|
| `backend/services/naver_theme_v2/__init__.py` | `collect_and_analyze_v2`, `ThemeAnalysisResult` re-export |
| `backend/services/naver_theme_v2/service.py` | V2 entrypoint, V1 analyzer 재사용 |
| `backend/services/naver_theme_v2/crawler.py` | requests + JSON, 단일 thread, sleep 0.7s, specific exception |
| `backend/services/naver_theme_v2/parser.py` | dict access only, V1 컬럼명 매핑 (change_pct, stock_code 등) + V1 alias (change_rate, code, name) |
| `backend/services/naver_theme_v2/config.py` | mobile endpoint 4 상수 + UA + sleep |

#### Backend Routes

| 파일 | 역할 |
|---|---|
| `backend/routers/themes.py` | V1: `GET /themes/snapshot`, `GET /themes/quick` (byte-identical 보존). V2: `GET /themes/v2/snapshot`, `GET /themes/v2/quick` (T1에서 추가됨, async def + specific exception). main.py에서 `prefix="/api"` |

#### Backend Entry

| 파일 | 역할 |
|---|---|
| `backend/main.py` | FastAPI app, `app.include_router(themes_router, prefix="/api")` (line 116) |

#### Frontend

| 파일 | 역할 |
|---|---|
| `frontend/src/api/themes.ts` | API client — V1만 호출 (Stage B에서 V2 swap 대상) |
| `frontend/src/api/client.ts` | axios instance |
| `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx` | 컨테이너 — ba3f20c에서 race condition fix |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | 테마 리스트 테이블 (Stage B에서 theme_description 표시) |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | 종목 디테일 panel (Stage B에서 stock_description 표시) |

#### Tests

| 파일 | 역할 |
|---|---|
| `tests/test_naver_theme_parser.py` | V1 parser 단위 테스트 |
| `tests/test_naver_theme_analyzer.py` | V1 analyzer + service + crawler 단위 테스트 (51건) |
| `tests/test_naver_theme_v2_parser.py` | V2 parser (8건) |
| `tests/test_naver_theme_v2_crawler.py` | V2 crawler (5건) |
| `tests/test_naver_theme_v2_service.py` | V2 service (8건, live 1 deselected) |
| `tests/test_naver_theme_v2_routes.py` | V2 routes (4건) |
| `tests/fixtures/naver_theme_v2/` | 합성 fixture 4종 |

#### 운영 환경

- venv: `/Users/byunjungwon/Dev/my_chart/.venv` (다른 프로젝트의 venv) — Stage B 진입 전 환경 정리 권장 (`cd my-project-01/my_chart && uv sync`)
- 운영 서버: `uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1` (PID 35179, 본 SPEC 작업 시점에 실행 중)
- DB 파일: `Output/stock_data_daily.db` (REQ-NT2-C-004 mtime 무변경 정책)

### 7.3 외부 자원

- V2 mobile endpoint: `https://m.stock.naver.com/front-api/stock/sectors/all` (list), `https://m.stock.naver.com/front-api/domestic/sector/item/list` (detail)
- V2 endpoint URL은 `backend/services/naver_theme_v2/config.py`에 격리 (REQ-NT2-NF-005)
- V1 desktop endpoint: `finance.naver.com` (V1 config.py 참조)

---

## 8. Stage B 시작 명령 권장

다음 turn에서 Stage B를 시작하려면 다음 중 하나를 실행:

```
# 옵션 1: 명시적 SPEC 이름 + scope
/moai plan SPEC-NAVER-THEME-FRONTEND-V2 — V2 frontend 채택 (api/themes.ts swap, V2 metadata V1 alias 4종, theme_description/stock_description UI 표시)

# 옵션 2: scope만 자연어로 (manager-spec이 SPEC ID 자동 생성)
/moai plan V2 frontend 채택 + V2 metadata V1 alias + theme_description/stock_description UI 표시

# 옵션 3: 본 핸드오프 문서 참조
/moai plan @.moai/specs/SPEC-NAVER-THEME-002/handoff-frontend-v2.md 참조하여 V2 frontend 채택 SPEC 작성
```

manager-spec subagent가 `.moai/specs/SPEC-NTF2-XXX/research.md` → `spec.md` → annotation cycle 진행. 사용자는 §3.4 D-1~D-4 결정 사항에 답변하면 됨.

### Stage C 시작 명령 (Stage B 완료 후)

```
/moai plan SPEC-NAVER-THEME-CACHE — backend in-memory TTL cache (V1+V2, 5분 TTL, lru_cache 패턴, force-refresh query param)
```

---

## 9. Definition of Handoff Done

본 핸드오프 문서가 다음 단계 진행자(사용자 또는 manager-spec subagent)에게 제공해야 하는 정보:

- [x] V2 backend ship 결과 요약 (검증 결과, commit chain)
- [x] 운영 중 발견된 3 이슈의 root cause + 처리 상태
- [x] Stage B Goal/Scope/Constraints/Risk/EARS-후보/AC-후보
- [x] Stage A (race condition fix) 완료 보고
- [x] Stage C (캐시) 옵션 비교 + 추천
- [x] Open Questions 정리 (Stage B 5건, Stage C 5건, 환경 1건)
- [x] 코드 위치 매트릭스 (backend V1/V2, routes, entry, frontend, tests, 운영 환경)
- [x] Stage B 시작 명령 권장 + Stage C 후속 안내

---

Version: 1.0.0
Last Updated: 2026-05-01
Document Type: Inter-SPEC handoff (predecessor → successor)
Predecessor SPEC: SPEC-NAVER-THEME-002 v1.0.1 (V2 backend ship)
Successor SPECs: SPEC-NAVER-THEME-FRONTEND-V2 (제안), SPEC-NAVER-THEME-CACHE (제안)
References:
- `.moai/specs/SPEC-NAVER-THEME-001/v2-handoff.md` (선례 핸드오프 문서, 480 lines)
- 본 작성 시점 V1+V2 commit chain: `12d81b1 → 027f571 → 888e2eb → ad9e30d → b1c24eb → ba3f20c`
