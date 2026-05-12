---
id: SPEC-NAVER-THEME-003
title: V2 frontend 채택 — Implementation Plan
status: Draft
version: 1.0.0
owner: bjw2002
created: 2026-05-06
updated: 2026-05-06
depends_on: SPEC-NAVER-THEME-002
---

# Implementation Plan: SPEC-NAVER-THEME-003 V2 frontend 채택

## 메타

| 항목 | 값 |
|------|-----|
| SPEC | SPEC-NAVER-THEME-003 |
| 버전 | 1.0.0 |
| 상태 | Draft (Pending User Approval) |
| 우선순위 | High |
| 의존성 | SPEC-NAVER-THEME-002 v1.0.1 (V2 backend ship 완료) |
| 위험 등급 | Low (대부분의 변경이 additive — V1 무수정, V2 backend metadata 추가, frontend swap) |

---

## 1. Phase 분해 (RUN Phase 실행 순서)

| Phase | 담당 | 우선순위 | 선행 의존성 | 산출물 |
|-------|------|----------|-------------|------|
| Phase 1 — V2 backend metadata V1 alias 추가 | expert-backend | High | 없음 | service.py EDIT (+20 LOC) |
| Phase 2 — V2 service.py metadata AC 단위 테스트 추가 | expert-testing | High | Phase 1 | test_naver_theme_v2_service.py EDIT (+15 LOC) |
| Phase 3 — frontend api/themes.ts swap + 타입 확장 + 에러 처리 | expert-frontend | High | Phase 1 (V2 응답 schema 정합) | api/themes.ts EDIT (+10 LOC) |
| Phase 4 — ThemeRankingTable theme_name hover Tooltip 추가 (D-2) | expert-frontend | High | Phase 3 (타입 확장) | ThemeRankingTable.tsx EDIT (+1 LOC) |
| Phase 5 — ThemeAnalysis 에러 메시지 + retry 버튼 (D-1) | expert-frontend | High | Phase 3 | ThemeAnalysis.tsx EDIT (+15 LOC) |
| Phase 6 — ThemeDetailPanel D-3 검증 (변경 없음) | expert-testing | High | Phase 3 | 검증만 (코드 변경 0) |
| Phase 7 — frontend vitest 작성/업데이트 (V2 mock + tooltip + null + retry) | expert-testing | High | Phase 3, 4, 5, 6 | vitest 신규 또는 EDIT (+60 LOC) |
| Phase 8 — 통합 검증 (V1 51 + V2 24 + vitest baseline + git diff) | manager-quality | High | Phase 1~7 | AC-1~15 PASS 보고 |

> 시간 추정 사용 금지 (`.claude/rules/moai/core/agent-common-protocol.md` "Time Estimation" 준수). 우선순위 라벨 + Phase 순서로 진행 관리.

### 1.1 의존성 그래프

```
Phase 1 (backend metadata) ──┬──→ Phase 2 (backend test)
                             │
                             └──→ Phase 3 (frontend swap)
                                    │
                                    ├──→ Phase 4 (tooltip)
                                    ├──→ Phase 5 (error+retry)
                                    └──→ Phase 6 (DetailPanel 검증)
                                            │
                                    Phase 4 ┴ Phase 5 ┴ Phase 6 ──→ Phase 7 (vitest)
                                                                       │
                                                Phase 1~7 ──→ Phase 8 (통합)
```

병렬 가능 단계:
- Phase 4, 5, 6은 Phase 3 완료 후 동시 진행 가능 (서로 다른 파일 수정 — 충돌 없음)
- Phase 2와 Phase 3은 Phase 1 완료 후 동시 진행 가능 (Phase 2는 backend, Phase 3은 frontend)

---

## 2. Phase 1 — V2 backend metadata V1 alias 추가

### 2.1 변경 파일

`backend/services/naver_theme_v2/service.py`

### 2.2 변경 내용 sketch

`collect_and_analyze_v2()` 함수의 정상 반환 경로에 elapsed_sec 측정 + V1 alias 4 필드 추가:

```python
# backend/services/naver_theme_v2/service.py (EDIT)
import time  # 신규 import (existing import 수정 없음)

def collect_and_analyze_v2(
    top_n_themes: int = 20,
    leaders_per_theme: int = 3,
    skip_details: bool = False,
) -> ThemeAnalysisResult:
    errors: list[dict] = []
    _start_time = time.monotonic()  # NEW — elapsed 측정 시작

    # ... (기존 Phase A ~ Phase E 로직 그대로) ...

    _generated_at = datetime.now(timezone.utc).isoformat()
    _elapsed = time.monotonic() - _start_time

    return ThemeAnalysisResult(
        themes_df=themes_df,
        stocks_df=stocks_df,
        strong_themes_df=strong_themes_df,
        leaders_df=leaders_df,
        multi_theme_stocks_df=multi_theme_stocks_df,
        metadata={
            # 기존 V2 필드 보존 (REQ-NT3-C-003 additive only)
            "data_source": config.DATA_SOURCE,
            "generated_at": _generated_at,
            "total_themes_seen": len(themes_df),
            "errors": errors,
            # NEW: V1 alias 4 필드 (REQ-NT3-005)
            "collected_at": _generated_at,
            "theme_count": len(themes_df),
            "stock_count": len(stocks_df),
            "elapsed_sec": _elapsed,
        },
    )


def _empty_result(errors: list[dict], elapsed: float = 0.0) -> ThemeAnalysisResult:
    """모든 list 호출 실패 시 빈 결과 반환. V1 alias 4 필드 zero values 보장 (REQ-NT3-006)."""
    empty_themes = pd.DataFrame(columns=[...])  # 기존 컬럼 그대로
    empty_stocks = _empty_stocks_df()
    _generated_at = datetime.now(timezone.utc).isoformat()
    return ThemeAnalysisResult(
        themes_df=empty_themes,
        stocks_df=empty_stocks,
        strong_themes_df=empty_themes.copy(),
        leaders_df=empty_stocks.copy(),
        multi_theme_stocks_df=empty_stocks.copy(),
        metadata={
            "data_source": config.DATA_SOURCE,
            "generated_at": _generated_at,
            "total_themes_seen": 0,
            "errors": errors,
            # NEW: V1 alias zero values
            "collected_at": _generated_at,
            "theme_count": 0,
            "stock_count": 0,
            "elapsed_sec": elapsed,
        },
    )
```

`_empty_result` 호출처(`collect_and_analyze_v2` Phase A 종료 분기)도 elapsed를 전달하도록 EDIT:

```python
themes_df = pd.DataFrame(all_themes)
if themes_df.empty:
    return _empty_result(errors, elapsed=time.monotonic() - _start_time)
```

### 2.3 정책 준수

- **REQ-NT3-C-003 (additive only)**: 기존 4 필드(`data_source`, `generated_at`, `total_themes_seen`, `errors`)는 dict literal에 그대로 유지. 신규 4 필드만 추가.
- **REQ-NT3-C-005 (bare except 금지)**: 본 변경은 try/except 추가 없음 → 정책 자동 준수.
- **REQ-NT3-C-002 (V1 무수정)**: 본 변경은 V2 모듈만 — V1 무수정.
- **@MX:ANCHOR 보존**: service.py의 기존 `# @MX:ANCHOR: V2 단일 진입점 (REQ-NT2-001)` 주석 그대로 유지. 신규 변경에 대한 추가 @MX 태그는 RUN phase에서 결정.

### 2.4 검증

- AC-6 ~ AC-10 (acceptance.md) 가 PASS해야 한다.
- V2 단위 테스트 24개 그대로 PASS (회귀 0).

---

## 3. Phase 2 — V2 service.py metadata AC 단위 테스트 추가

### 3.1 변경 파일

`tests/test_naver_theme_v2_service.py`

### 3.2 추가 테스트 케이스

기존 V2 service 단위 테스트 8건에 4건 추가 (AC-6 ~ AC-10 매핑):

```python
# tests/test_naver_theme_v2_service.py (EDIT — 함수 추가)

def test_metadata_v1_alias_fields_present(synthetic_v2_response):
    """AC-6: V2 metadata에 V1 alias 4 필드 모두 존재."""
    # ... (기존 fixture mock 패턴 활용)
    result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)
    metadata = result.metadata

    # V1 alias 4 필드
    assert "collected_at" in metadata
    assert "theme_count" in metadata
    assert "stock_count" in metadata
    assert "elapsed_sec" in metadata

    # 기존 V2 필드 보존 (REQ-NT3-C-003)
    assert metadata["data_source"] == "naver_mobile_v2"
    assert "generated_at" in metadata
    assert "total_themes_seen" in metadata
    assert "errors" in metadata


def test_metadata_collected_at_iso8601(synthetic_v2_response):
    """AC-7: collected_at은 ISO-8601 parsable."""
    from datetime import datetime
    result = collect_and_analyze_v2(top_n_themes=5)
    collected_at = result.metadata["collected_at"]
    parsed = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
    assert parsed.tzinfo is not None


def test_metadata_stock_count_matches_df(synthetic_v2_response):
    """AC-8: stock_count == len(stocks_df)."""
    result = collect_and_analyze_v2(top_n_themes=5)
    assert result.metadata["stock_count"] == len(result.stocks_df)


def test_metadata_elapsed_sec_positive(synthetic_v2_response):
    """AC-9: elapsed_sec은 float >= 0."""
    result = collect_and_analyze_v2(top_n_themes=5)
    elapsed = result.metadata["elapsed_sec"]
    assert isinstance(elapsed, float)
    assert elapsed >= 0.0
    assert elapsed < 60.0


def test_empty_result_has_v1_alias(mock_5xx_all_pages):
    """AC-10: _empty_result도 V1 alias 4 필드 (zero values) 가짐."""
    result = collect_and_analyze_v2(top_n_themes=5)
    metadata = result.metadata

    assert metadata["collected_at"]  # truthy ISO string
    assert metadata["theme_count"] == 0
    assert metadata["stock_count"] == 0
    assert metadata["elapsed_sec"] >= 0.0
    assert len(metadata["errors"]) >= 1  # 5xx errors 기록
```

### 3.3 fixtures 재사용

기존 SPEC-002 fixture(`tests/fixtures/naver_theme_v2/list_synthetic.json` 등) 재사용. 신규 fixture 추가 없음.

### 3.4 검증

- 신규 5개 테스트 모두 PASS
- 기존 V2 24 테스트 회귀 0

---

## 4. Phase 3 — frontend api/themes.ts swap + 타입 확장

### 4.1 변경 파일

`frontend/src/api/themes.ts`

### 4.2 변경 내용 sketch

```typescript
// @MX:ANCHOR: [AUTO] themes.ts는 /themes/v2/snapshot, /themes/v2/quick API 클라이언트 함수를 노출
// @MX:REASON: ThemeAnalysis 컴포넌트에서 참조; SPEC-NAVER-THEME-003 V2 endpoint adoption
// @MX:SPEC: SPEC-NAVER-THEME-003 REQ-NT3-001, REQ-NT3-002, REQ-NT3-003
import client from './client'

export interface ThemeItem {
  theme_id: number
  theme_name: string
  change_pct: number
  change_pct_3d: number
  momentum_score?: number
  breadth_ratio?: number
  top_stocks_preview?: string
  theme_description?: string | null  // NEW (REQ-NT3-002)
}

export interface ThemeStockItem {
  theme_id: number
  theme_name: string
  stock_code: string
  stock_name: string
  inclusion_reason: string  // V2에서는 mobile API의 item.description으로 채워짐 (D-3)
  price: number
  change: number
  change_pct: number
  volume: number
  trade_value: number
  market_cap: number | null
  leader_score?: number
  rank?: number
  stock_description?: string | null  // NEW (REQ-NT3-003, forward-compat)
}

// MultiThemeStockItem, ThemesSnapshotResponse, ThemesQuickResponse 등은 무변경

export async function fetchThemesSnapshot(topN?: number, leadersPerTheme?: number): Promise<ThemesSnapshotResponse> {
  // EDIT: V1 → V2 endpoint URL swap (REQ-NT3-001)
  const response = await client.get('/themes/v2/snapshot', {
    params: { top_n: topN, leaders_per_theme: leadersPerTheme },
  })
  return response.data as ThemesSnapshotResponse
}

export async function fetchThemesQuick(topN?: number): Promise<ThemesQuickResponse> {
  // EDIT: V1 → V2 endpoint URL swap (REQ-NT3-001)
  const response = await client.get('/themes/v2/quick', { params: { top_n: topN } })
  return response.data as ThemesQuickResponse
}
```

### 4.3 정책 준수

- **REQ-NT3-001/002/003**: endpoint URL swap + 두 optional 필드 추가 — 모두 충족.
- **REQ-NT3-C-006 (V1 자동 폴백 금지)**: api/themes.ts 함수 내부에 V1 fallback 호출 코드 없음.
- **@MX:ANCHOR 업데이트**: 기존 SPEC-001 ANCHOR를 SPEC-003 ANCHOR로 EDIT (SPEC ID 갱신).

### 4.4 검증

- AC-1, AC-2, AC-3 PASS
- TypeScript compile 성공 (`tsc --noEmit`)

---

## 5. Phase 4 — ThemeRankingTable theme_name hover Tooltip 추가 (D-2)

### 5.1 변경 파일

`frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx`

### 5.2 변경 내용 sketch

기존 line 79 (theme_name 셀):
```tsx
<td style={{ textAlign: 'left' }}>{theme.theme_name}</td>
```

EDIT:
```tsx
<td
  style={{ textAlign: 'left' }}
  title={theme.theme_description ?? undefined}
>
  {theme.theme_name}
</td>
```

(또는 더 엄격하게 `theme.theme_description || undefined`로 빈 문자열도 hidden — D-4)

### 5.3 정책 준수

- **REQ-NT3-004 (D-2)**: native HTML `title` 속성으로 tooltip 노출.
- **REQ-NT3-NF-002 (D-4)**: nullish coalescing(`??`)으로 null/undefined 시 attribute 자체 미렌더링 → hidden.
- **REQ-NT3-C-004 (신규 의존성 금지)**: Radix Tooltip 등 라이브러리 도입 없이 native HTML — 충족.
- **@MX:NOTE 보존**: 기존 `// @MX:NOTE: [AUTO] ThemeRankingTable은 강세 테마 목록을 정렬 가능한 테이블로 렌더링` 그대로 유지. SPEC ID 추가 (`@MX:SPEC: SPEC-NAVER-THEME-001 REQ-NT-005, SPEC-NAVER-THEME-003 REQ-NT3-004`).

### 5.4 검증

- AC-4 (description 채워진 셀에 title 존재), AC-5 (null 시 title hidden) PASS
- vitest baseline 회귀 0

---

## 6. Phase 5 — ThemeAnalysis 에러 메시지 + retry 버튼 (D-1)

### 6.1 변경 파일

`frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx`

### 6.2 변경 내용 sketch

기존 ThemeAnalysis.tsx (race condition fix `ba3f20c` 패턴 보존):

```tsx
// 기존 useEffect cleanup 패턴 (ba3f20c)
useEffect(() => {
  let cancelled = false
  setLoading(true)
  setError(null)
  const promise = mode === 'quick' ? fetchThemesQuick() : fetchThemesSnapshot()

  promise
    .then(result => { if (cancelled) return; setData(result); /* ... */ })
    .catch(e => { if (cancelled) return; setError(e); /* ... */ })
    .finally(() => { if (cancelled) return; setLoading(false) })

  return () => { cancelled = true }
}, [mode, retryNonce])  // retryNonce 추가 (NEW)
```

신규 state + retry 핸들러 추가:

```tsx
// NEW: retry trigger
const [retryNonce, setRetryNonce] = useState(0)
const handleRetry = () => setRetryNonce(n => n + 1)

// 렌더링 분기 (REQ-NT3-007, REQ-NT3-NF-001)
if (error) {
  return (
    <div className="theme-analysis-error">
      <p>테마 데이터를 가져오지 못했습니다. 다시 시도해 주세요.</p>
      <button type="button" onClick={handleRetry}>다시 시도</button>
    </div>
  )
}
```

### 6.3 정책 준수

- **REQ-NT3-007 (D-1 에러+retry)**: 에러 메시지 + 버튼 표시. retry 클릭 시 useEffect의 retryNonce 의존성으로 fetch 재시작.
- **REQ-NT3-NF-001 (UI 분기 ≤ 2)**: error state 분기 + 정상 렌더링 분기 — 정확히 2개. 추가 분기(V1 fallback, env toggle 등) 없음.
- **REQ-NT3-C-006 (V1 자동 폴백 금지)**: catch 블록에서 V1 endpoint 호출 코드 없음. fetchThemesSnapshot/Quick 만 호출.
- **race condition cleanup 패턴 보존**: cancelled flag 패턴 + cleanup 함수 그대로.
- **@MX:NOTE 추가** (RUN phase에서 결정): 신규 retry 패턴에 대한 NOTE 또는 SPEC ID 추가.

### 6.4 검증

- AC-11 (503 시 에러 메시지 + retry 버튼 렌더링), AC-12 (retry 클릭 시 V2 재호출) PASS
- vitest baseline 회귀 0

---

## 7. Phase 6 — ThemeDetailPanel D-3 검증 (변경 없음)

### 7.1 변경 파일

없음. 본 phase는 검증만 수행.

### 7.2 검증 시나리오

ThemeDetailPanel.tsx의 line 62, 92에 있는 기존 `title={stock.inclusion_reason}` 패턴이 V2 응답에서도 정상 동작하는지 확인.

V2 parser 정책(`backend/services/naver_theme_v2/parser.py:271`):
```python
"inclusion_reason": item.get("description"),  # V1 컬럼 호환성
```

→ V2 endpoint 응답이 frontend에 도달했을 때 `stock.inclusion_reason`이 V2 mobile description 텍스트로 채워짐 → 기존 hover tooltip이 자동으로 V2 description 노출.

### 7.3 정책 준수

- **REQ-NT3-008 (D-3)**: ThemeDetailPanel.tsx 무수정 — 변경 0 LOC.
- **REQ-NT3-C-002 (V1 무수정 정책 spirit)**: V1 frontend 컴포넌트 패턴 보존.

### 7.4 검증

- AC-13 (ThemeDetailPanel에서 V2 description이 inclusion_reason 자리에 노출) PASS
- ThemeDetailPanel.tsx git diff empty
- 본 phase는 단독 코드 변경 없으나 vitest 시나리오에서 V2 mock 응답으로 패널 렌더링 검증 (Phase 7에서 함께 작성)

---

## 8. Phase 7 — frontend vitest 작성/업데이트

### 8.1 변경 파일

`frontend/src/components/ThemeAnalysis/__tests__/` 디렉토리 (기존 vitest 파일 EDIT 또는 신규 추가)

검토 대상 파일 (실제 파일 구조는 RUN phase에서 확인):
- `ThemeAnalysis.test.tsx` (기존 if exists, 또는 신규)
- `ThemeRankingTable.test.tsx`
- `ThemeDetailPanel.test.tsx`
- `api/themes.test.ts` (또는 통합 테스트로 ThemeAnalysis.test.tsx에 포함)

### 8.2 vitest 케이스 매트릭스

| AC | test 함수 (vitest) | 파일 |
|---|---|---|
| AC-1 | `test('fetchThemesSnapshot calls /themes/v2/snapshot')` | api/themes.test.ts |
| AC-1 | `test('fetchThemesQuick calls /themes/v2/quick')` | api/themes.test.ts |
| AC-2, AC-3 | TypeScript compile 검증 — vitest 직접 케이스 불필요 | (tsc --noEmit) |
| AC-4 | `test('renders title attribute when theme_description present')` | ThemeRankingTable.test.tsx |
| AC-5 | `test('omits title attribute when theme_description is null/undefined/empty')` | ThemeRankingTable.test.tsx |
| AC-11 | `test('shows error message + retry button on V2 503')` | ThemeAnalysis.test.tsx |
| AC-12 | `test('retry button triggers V2 endpoint re-fetch')` | ThemeAnalysis.test.tsx |
| AC-13 | `test('ThemeDetailPanel exposes V2 description via inclusion_reason title')` | ThemeDetailPanel.test.tsx |

### 8.3 mock 패턴

```typescript
// vitest mock — axios client.get
import { vi } from 'vitest'
import client from '../../../api/client'

vi.mock('../../../api/client', () => ({
  default: { get: vi.fn() }
}))

// 케이스 1: 정상 응답
;(client.get as any).mockResolvedValue({
  data: { themes: [...], stocks: [...], strong_themes: [...], leaders: [...], multi_theme_stocks: [...], metadata: { collected_at: '2026-05-06T00:00:00+00:00', theme_count: 1, stock_count: 1, elapsed_sec: 1.5, errors: [] } }
})

// 케이스 2: 503 에러
;(client.get as any).mockRejectedValueOnce({ response: { status: 503 }, message: 'Service Unavailable' })

// 케이스 3: retry 시나리오 (mockResolvedValueOnce + mockResolvedValueOnce 조합)
```

### 8.4 baseline diff 검증

본 SPEC 작업 전 baseline:
```
Test Files  N passed | 1 failed (ChartGrid)
     Tests  256 passed | 1 failed (ChartGrid)
```

본 SPEC 작업 후 expected:
```
Test Files  (N + 신규) passed | 1 failed (ChartGrid only — REQ-NT3-NF-004)
     Tests  (256 + 신규) passed | 1 failed (ChartGrid only)
```

신규 fail이 ChartGrid 외 발생하면 본 SPEC 회귀로 판정 — 즉시 수정 또는 rollback.

### 8.5 검증

- AC-15 (frontend vitest baseline diff 0) PASS
- 신규 vitest 케이스 모두 PASS

---

## 9. Phase 8 — 통합 검증

### 9.1 검증 명령

```bash
# Backend V1 회귀 (REQ-NT3-C-002)
source .venv/bin/activate
pytest tests/test_naver_theme_parser.py tests/test_naver_theme_analyzer.py -v -m "not live"
# Expected: 51 passed (회귀 0)

# Backend V2 회귀 + 신규 (REQ-NT3-C-003 + Phase 2)
pytest tests/test_naver_theme_v2_*.py -v -m "not live"
# Expected: 24 + 5 (신규) = 29 passed

# Backend route 검증 (REQ-NT3-R-001, REQ-NT3-R-002)
pytest tests/test_naver_theme_v2_routes.py -v -m "not live"
# AC-14 검증

# Frontend vitest (REQ-NT3-NF-004)
cd frontend && npm run test -- --run
# Expected: 256 + 신규 passed, 1 failed (ChartGrid only)

# git diff 검증 (REQ-NT3-C-002 V1 무수정)
git diff --stat backend/services/naver_theme/
# Expected: empty (no changes)

# 신규 의존성 검증 (REQ-NT3-C-004)
git diff requirements.txt frontend/package.json
# Expected: empty (no dependency changes)

# bare except 검증 (REQ-NT3-C-005)
grep -rn "except:" backend/services/naver_theme_v2/ frontend/src/components/ThemeAnalysis/
grep -rn "except Exception" backend/services/naver_theme_v2/
# Expected: empty (only specific exceptions)
```

### 9.2 AC 매트릭스 PASS 확인

| AC | 검증 방식 | 통과 기준 |
|---|---|---|
| AC-1 | vitest | client.get 호출 URL이 V2 |
| AC-2, AC-3 | tsc + vitest | TypeScript compile + 타입 assertion |
| AC-4, AC-5 | vitest RTL | title 속성 렌더링 검증 |
| AC-6 ~ AC-10 | pytest | V2 metadata alias 4 필드 + zero values |
| AC-11, AC-12 | vitest RTL | 에러 메시지 + retry 시나리오 |
| AC-13 | vitest RTL | ThemeDetailPanel inclusion_reason 자리 |
| AC-14 | pytest TestClient | V1+V2 routes 등록 |
| AC-15 | pytest + vitest 통합 | baseline diff 0 |

### 9.3 회귀 risk 점검

- V1 endpoint 호출 (smoke test, manual): `curl http://127.0.0.1:8000/api/themes/snapshot | jq '.themes | length'` — > 0
- V2 endpoint 호출 (smoke test, manual): `curl http://127.0.0.1:8000/api/themes/v2/snapshot | jq '.metadata | keys'` — V1 alias 4 필드 포함

### 9.4 PR 준비

- 본 SPEC commit chain은 SPEC-NAVER-THEME-002 v1.0.1 commit `ba3f20c` 이후에 위치
- commit 메시지 prefix: `feat(naver-theme-v2-frontend):` (SPEC ID `SPEC-NAVER-THEME-003`)
- PR 제목 권장: `feat(naver-theme): SPEC-NAVER-THEME-003 — V2 frontend 채택 + theme_description tooltip + V2 metadata V1 alias`

---

## 10. @MX 태그 정책

### 10.1 본 SPEC 변경 시 @MX 태그 영향

| 파일 | 기존 @MX 태그 | 본 SPEC 변경 시 처리 |
|---|---|---|
| `backend/services/naver_theme_v2/service.py` | `@MX:ANCHOR: V2 단일 진입점 (REQ-NT2-001)` | 보존. SPEC ID 추가 가능 (`SPEC-NAVER-THEME-003 REQ-NT3-005`) |
| `frontend/src/api/themes.ts` | `@MX:ANCHOR: ... SPEC-NAVER-THEME-001 REQ-NT-R-001, REQ-NT-R-002` | SPEC ID 갱신 — `SPEC-NAVER-THEME-001 REQ-NT-R-001/R-002, SPEC-NAVER-THEME-003 REQ-NT3-001/002/003` |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | `@MX:NOTE: ... SPEC-NAVER-THEME-001 REQ-NT-005` | SPEC ID 갱신 — `SPEC-NAVER-THEME-001 REQ-NT-005, SPEC-NAVER-THEME-003 REQ-NT3-004` |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | `@MX:NOTE: ... SPEC-NAVER-THEME-001 REQ-NT-008` | 무수정 (D-3) — SPEC ID 갱신만 옵션 (`SPEC-NAVER-THEME-003 REQ-NT3-008`) |
| `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx` | (있다면 보존) | retry state 패턴에 대한 `@MX:NOTE` 추가 옵션 |

### 10.2 신규 @MX 태그 후보

- `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx`의 retry 핸들러 — `@MX:NOTE: [AUTO] retry 패턴은 race-safe — useEffect cleanup 패턴(ba3f20c) + retryNonce trigger`

### 10.3 @MX 태그 언어

`.moai/config/sections/language.yaml` `code_comments: ko` → @MX 태그 description은 한국어. 본 plan의 sketch 그대로 한국어 사용.

---

## 11. RUN phase 전환 체크리스트

본 plan 승인 후 RUN phase 시작 전 다음 사항 확인:

- [ ] research.md, spec.md, acceptance.md, plan.md 4 artifact 모두 작성됨 (본 SPEC 디렉토리)
- [ ] SPEC-NAVER-THEME-002 v1.0.1 ship 결과 그대로 (V2 24/24 GREEN, V1 51/51 GREEN, frontend 256/257 baseline)
- [ ] `chore/integrated-main-merge-2026-04-25` 브랜치에서 작업 — 별도 worktree/branch 생성 X (사용자 요청)
- [ ] 운영 서버 재시작 시점은 본 SPEC ship 후 결정 (V2 endpoint metadata alias 적용 후 frontend 호출 가능)
- [ ] `/clear` 후 `/moai run SPEC-NAVER-THEME-003`로 RUN phase 시작 (또는 Phase 8 통합 검증을 manager-quality 단독 위임)

### 11.1 RUN phase 권장 명령

```bash
# 본 plan 승인 후
/clear
/moai run SPEC-NAVER-THEME-003

# 또는 phase 별 위임 (병렬 가능 phase는 단일 메시지에 multi-Agent)
# Phase 1+3 (backend metadata + frontend swap) 병렬 가능 — 서로 다른 파일
# Phase 4+5+6 (tooltip + retry + DetailPanel 검증) 병렬 가능 — Phase 3 완료 후
# Phase 2+7 (backend test + frontend test) Phase 1, 3-6 완료 후 병렬
# Phase 8 (통합) 마지막 — 단독 manager-quality
```

---

## 12. 회귀 차단 매트릭스

| 정책 (REQ ID) | 검증 방식 | 자동 차단 |
|---|---|---|
| V1 routes byte-identical (REQ-NT3-C-001, R-001) | AC-14 + git diff | ✓ |
| V1 backend 모듈 무수정 (REQ-NT3-C-002) | git diff `backend/services/naver_theme/` empty | ✓ |
| V2 backend metadata additive only (REQ-NT3-C-003) | AC-6 기존 4 필드 보존 검증 | ✓ |
| 신규 pip/npm 의존성 금지 (REQ-NT3-C-004) | git diff `requirements.txt` `package.json` empty | ✓ |
| bare except 금지 (REQ-NT3-C-005) | grep `except:` `except Exception` empty | ✓ |
| V2 503 시 V1 자동 폴백 금지 (REQ-NT3-C-006) | AC-11에서 V1 endpoint 호출 0건 검증 | ✓ |
| V1 51 단위 테스트 회귀 0 | pytest -m "not live" PASS | ✓ |
| V2 24 단위 테스트 회귀 0 | pytest -m "not live" PASS | ✓ |
| frontend vitest baseline diff 0 (REQ-NT3-NF-004) | vitest 비교 (ChartGrid 1 fail only) | ✓ |

---

## 13. 작업 분량 정밀화 (research §7 mirror)

| 파일 | 변경 LOC | files |
|---|---|---|
| `backend/services/naver_theme_v2/service.py` | +20 | 1 |
| `tests/test_naver_theme_v2_service.py` | +15 | 1 |
| `frontend/src/api/themes.ts` | +10 | 1 |
| `frontend/src/components/ThemeAnalysis/ThemeRankingTable.tsx` | +1 | 1 |
| `frontend/src/components/ThemeAnalysis/ThemeAnalysis.tsx` | +15 | 1 |
| `frontend/src/components/ThemeAnalysis/ThemeDetailPanel.tsx` | 0 | 0 (무수정) |
| `frontend/src/components/ThemeAnalysis/__tests__/*.test.tsx` | +60 | 1~3 |

**합계 예상**: ~120 LOC, 7 files (handoff 추정 145 LOC 대비 D-3 결정으로 ~25 LOC 감소).

---

Version: 1.0.0
Status: Draft (Pending User Approval)
Predecessor: SPEC-NAVER-THEME-002 v1.0.1
Branch: `chore/integrated-main-merge-2026-04-25` (별도 worktree/branch 생성 X)
Next phase: `/moai run SPEC-NAVER-THEME-003` (after approval + `/clear`)
