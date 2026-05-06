---
id: SPEC-NAVER-THEME-003
title: V2 frontend 채택 — Acceptance Criteria
status: Implemented
version: 1.0.4
owner: bjw2002
created: 2026-05-06
updated: 2026-05-06
depends_on: SPEC-NAVER-THEME-002
---

# Acceptance Criteria: SPEC-NAVER-THEME-003 V2 frontend 채택

## 메타

| 항목 | 값 |
|------|-----|
| SPEC | SPEC-NAVER-THEME-003 |
| 버전 | 1.0.0 |
| 검증 방식 | 자동 (pytest + vitest) — 라이브 테스트 신규 추가 없음 |
| 사인오프 | Product Owner |
| 총 AC | 15개 (전부 PASS 시 본 SPEC 완료) |

---

## HISTORY

- 2026-05-06 v1.0.4 amendment: backend strong_themes_df에 theme_description 머지 누락 수정. AC-21 신규 (strong_themes_df description 매핑 검증). 총 21 AC.
- 2026-05-06 v1.0.3 amendment: default mode를 'full'로 변경 + 빠른 조회 모드 advisory. AC-19 신규 (default mode 'full' 검증) + AC-20 신규 (quick advisory 노출). 총 20 AC.
- 2026-05-06 v1.0.2 amendment: 주도주 섹션 제거 + theme_description prominent 강화. AC-18 신규 추가 (주도주 섹션 미렌더링 검증). AC-17은 stock body 검증만으로 좁힘 (leader body는 더 이상 발생 안함). 총 18 AC.
- 2026-05-06 v1.0.1 amendment: D-3 reverse로 AC-16, AC-17 신규 추가 (theme_description 본문 노출 + inclusion_reason 본문 노출). 총 17 AC.
- 2026-05-06 v1.0.0: 초안 작성 (manager-spec). 15 AC. SPEC-002 14-AC 스타일 mirror + D-1 retry 시나리오 1 추가. V1 routes/모듈 byte-identical 회귀 검증, V2 metadata V1 alias 4 필드 검증, frontend api/themes.ts URL swap 검증, theme_name hover Tooltip rendering(RTL), null hidden 검증, V2 503 mock 에러 메시지 + retry 시나리오 검증 포함. 라이브 테스트는 SPEC-002 라이브 1 PASS로 충분 — 신규 라이브 마커 미추가.

---

> 모든 frontend 변경은 `frontend/src/api/themes.ts`, `frontend/src/components/ThemeAnalysis/{ThemeAnalysis,ThemeRankingTable}.tsx`에 한정. ThemeDetailPanel은 D-3 결정으로 무수정 (검증만). V2 backend 변경은 `backend/services/naver_theme_v2/service.py`에 한정. V1 routes/모듈은 byte-identical 보존.

---

## AC-1: api/themes.ts가 V2 endpoint URL 호출 (REQ-NT3-001)

### Given
- `frontend/src/api/themes.ts`가 본 SPEC 변경 후 상태로 존재한다
- vitest 환경에서 axios client가 mock 가능

### When
```typescript
import { vi, describe, it, expect } from 'vitest'
import client from '../client'
import { fetchThemesSnapshot, fetchThemesQuick } from '../themes'

vi.mock('../client', () => ({
  default: { get: vi.fn().mockResolvedValue({ data: { themes: [], stocks: [], strong_themes: [], leaders: [], multi_theme_stocks: [], metadata: {} } }) }
}))

await fetchThemesSnapshot()
await fetchThemesQuick()
```

### Then
```typescript
expect(client.get).toHaveBeenCalledWith('/themes/v2/snapshot', expect.any(Object))
expect(client.get).toHaveBeenCalledWith('/themes/v2/quick', expect.any(Object))
// V1 endpoint URL 호출 부재 검증
const calls = (client.get as any).mock.calls
const v1Calls = calls.filter(([url]: [string]) => url === '/themes/snapshot' || url === '/themes/quick')
expect(v1Calls.length).toBe(0)
```

---

## AC-2: ThemeItem 타입에 theme_description 추가 (REQ-NT3-002)

### Given
- `frontend/src/api/themes.ts`의 `ThemeItem` interface 정의

### When
```typescript
import type { ThemeItem } from '../themes'

const theme: ThemeItem = {
  theme_id: 1,
  theme_name: 'Test',
  change_pct: 1.5,
  change_pct_3d: 2.0,
  theme_description: '테마 설명 예시',
}
const themeNull: ThemeItem = {
  theme_id: 2,
  theme_name: 'NoDesc',
  change_pct: 0,
  change_pct_3d: 0,
  theme_description: null,
}
const themeUndef: ThemeItem = {
  theme_id: 3,
  theme_name: 'Undef',
  change_pct: 0,
  change_pct_3d: 0,
}
```

### Then
- `theme_description: string | null | undefined` 모두 TypeScript compile 통과
- vitest 검증: `expect(theme.theme_description).toBe('테마 설명 예시')`
- vitest 검증: `expect(themeNull.theme_description).toBe(null)`
- vitest 검증: `expect(themeUndef.theme_description).toBeUndefined()`

---

## AC-3: ThemeStockItem 타입에 stock_description 추가 (REQ-NT3-003)

### Given
- `frontend/src/api/themes.ts`의 `ThemeStockItem` interface 정의

### When
```typescript
import type { ThemeStockItem } from '../themes'

const stock: ThemeStockItem = {
  theme_id: 1,
  theme_name: 'Test',
  stock_code: '005930',
  stock_name: '삼성전자',
  inclusion_reason: '편입사유',
  price: 70000,
  change: 500,
  change_pct: 0.7,
  volume: 1000000,
  trade_value: 70_000_000_000,
  market_cap: 400_000_000_000_000,
  stock_description: '편입 설명',
}
```

### Then
- TypeScript compile 통과
- `stock.stock_description`이 optional string | null 타입으로 인식

---

## AC-4: ThemeRankingTable이 theme_description Tooltip 렌더링 (REQ-NT3-004, D-2)

### Given
- ThemeRankingTable에 `theme_description`이 채워진 ThemeItem 1개와 채워지지 않은 ThemeItem 1개를 props로 전달

### When
```typescript
import { render } from '@testing-library/react'
import { ThemeRankingTable } from '../ThemeRankingTable'

const themes = [
  { theme_id: 1, theme_name: '전선', change_pct: 9.2, change_pct_3d: 12.0, theme_description: '각종 전선 제조 테마' },
  { theme_id: 2, theme_name: '바이오', change_pct: 5.0, change_pct_3d: 7.0, theme_description: null },
]

const { container } = render(
  <ThemeRankingTable themes={themes} sortField="change_pct" sortDirection="desc" onSort={() => {}} onThemeClick={() => {}} selectedThemeId={null} />
)
```

### Then
```typescript
// "전선" 셀에 title 속성 존재 (description 노출)
const cellWithDesc = container.querySelector('td[title="각종 전선 제조 테마"]')
expect(cellWithDesc).not.toBeNull()
expect(cellWithDesc?.textContent).toContain('전선')
```

---

## AC-5: theme_description=null/undefined 시 title 속성 hidden (REQ-NT3-NF-002, D-4)

### Given
- ThemeRankingTable에 theme_description이 null인 ThemeItem 1개 + undefined인 ThemeItem 1개 + 빈 문자열 1개 전달

### When
```typescript
const themes = [
  { theme_id: 1, theme_name: 'NullDesc', change_pct: 1.0, change_pct_3d: 1.0, theme_description: null },
  { theme_id: 2, theme_name: 'NoDesc', change_pct: 1.0, change_pct_3d: 1.0 },  // undefined
  { theme_id: 3, theme_name: 'EmptyDesc', change_pct: 1.0, change_pct_3d: 1.0, theme_description: '' },
]

const { container } = render(<ThemeRankingTable {...props} themes={themes} />)
```

### Then
```typescript
// 모든 행의 theme_name 셀에 title 속성이 없거나 빈 문자열
const rows = container.querySelectorAll('tbody tr')
rows.forEach(row => {
  const nameCell = row.querySelector('td:first-child')
  const titleAttr = nameCell?.getAttribute('title')
  // title 속성 자체가 없거나 빈 문자열 (hidden — D-4)
  expect(titleAttr === null || titleAttr === '' || titleAttr === undefined).toBe(true)
})
```

---

## AC-6: V2 service.py metadata에 V1 alias 4 필드 존재 (REQ-NT3-005)

### Given
- V2 backend service `collect_and_analyze_v2()`가 mock fixture (synthetic) 또는 라이브 응답으로 정상 실행된다

### When
```python
from backend.services.naver_theme_v2 import collect_and_analyze_v2

# mock crawler/parser로 fixture 데이터 주입
result = collect_and_analyze_v2(top_n_themes=5, leaders_per_theme=3, skip_details=False)
metadata = result.metadata
```

### Then
```python
# V1 alias 4 필드 모두 존재
assert "collected_at" in metadata
assert "theme_count" in metadata
assert "stock_count" in metadata
assert "elapsed_sec" in metadata

# 기존 V2 필드 보존 (REQ-NT3-C-003 additive only)
assert metadata["data_source"] == "naver_mobile_v2"
assert "generated_at" in metadata
assert "total_themes_seen" in metadata
assert "errors" in metadata

# alias 정합성
assert metadata["collected_at"] == metadata["generated_at"]
assert metadata["theme_count"] == metadata["total_themes_seen"]
```

---

## AC-7: collected_at은 ISO-8601 UTC 형식 (REQ-NT3-005)

### Given
- AC-6 result.metadata 가용

### When
```python
from datetime import datetime
collected_at = result.metadata["collected_at"]
```

### Then
```python
# ISO-8601 parsable
parsed = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
assert parsed.tzinfo is not None  # UTC 또는 timezone-aware
assert isinstance(collected_at, str)
```

---

## AC-8: stock_count는 len(stocks_df) 일치 (REQ-NT3-005)

### Given
- AC-6 result 가용

### When
```python
stock_count = result.metadata["stock_count"]
actual_len = len(result.stocks_df)
```

### Then
```python
assert isinstance(stock_count, int)
assert stock_count == actual_len, f"stock_count={stock_count}, len(stocks_df)={actual_len}"
```

---

## AC-9: elapsed_sec은 float, 측정값 양수 (REQ-NT3-005)

### Given
- AC-6 result 가용

### When
```python
elapsed = result.metadata["elapsed_sec"]
```

### Then
```python
assert isinstance(elapsed, float)
assert elapsed >= 0.0
# nominal call은 30초 이내 (REQ-NT3-NF-003)
assert elapsed < 60.0  # 안전 마진
```

---

## AC-10: `_empty_result`에도 V1 alias 4 필드 존재 (REQ-NT3-006)

### Given
- 모든 list endpoint 호출 실패를 mock으로 강제 (5xx 무한 반복)

### When
```python
import unittest.mock as mock
import requests

def fake_5xx(*args, **kwargs):
    resp = mock.MagicMock()
    resp.status_code = 503
    resp.headers = {"Content-Type": "application/json"}
    raise requests.HTTPError("503")

with mock.patch("backend.services.naver_theme_v2.crawler.requests.Session.get", side_effect=fake_5xx):
    result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)
metadata = result.metadata
```

### Then
```python
# 빈 결과 반환 — 예외 X (REQ-NT2-NF-003 계승)
assert len(result.themes_df) == 0
assert len(result.stocks_df) == 0

# V1 alias 4 필드 모두 존재 (zero values)
assert metadata["collected_at"]  # truthy ISO string
assert metadata["theme_count"] == 0
assert metadata["stock_count"] == 0
assert metadata["elapsed_sec"] >= 0.0

# errors 기록됨
assert len(metadata["errors"]) >= 1
```

---

## AC-11: V2 endpoint 503 시 에러 메시지 + retry 버튼 표시 (REQ-NT3-007, D-1)

### Given
- ThemeAnalysis 컴포넌트가 마운트되고 `fetchThemesQuick()` 또는 `fetchThemesSnapshot()`이 503 응답으로 실패하도록 axios mock

### When
```typescript
import { render, screen, waitFor } from '@testing-library/react'
import { ThemeAnalysis } from '../ThemeAnalysis'
import client from '../../../api/client'

vi.mock('../../../api/client', () => ({
  default: { get: vi.fn().mockRejectedValue({ response: { status: 503 }, message: 'Service Unavailable' }) }
}))

render(<ThemeAnalysis />)
```

### Then
```typescript
await waitFor(() => {
  // 에러 메시지 텍스트 존재
  expect(screen.getByText(/테마 데이터를 가져오지 못했습니다/i)).toBeTruthy()
  // retry 버튼 존재 (role="button", text 포함 "다시 시도" 또는 "Retry")
  const retryBtn = screen.getByRole('button', { name: /다시 시도|retry/i })
  expect(retryBtn).toBeTruthy()
})

// V1 endpoint 자동 폴백 호출 부재 검증 (REQ-NT3-C-006)
const calls = (client.get as any).mock.calls
const v1Calls = calls.filter(([url]: [string]) => url === '/themes/snapshot' || url === '/themes/quick')
expect(v1Calls.length).toBe(0)
```

---

## AC-12: retry 버튼 클릭 시 V2 endpoint 재호출 (REQ-NT3-007)

### Given
- AC-11과 동일한 503 mock + retry 버튼 렌더링 상태

### When
```typescript
import { fireEvent } from '@testing-library/react'

const { getByRole } = render(<ThemeAnalysis />)
await waitFor(() => getByRole('button', { name: /다시 시도|retry/i }))

// 한 번 더 mock 응답 변경 (이번엔 200 OK)
;(client.get as any).mockResolvedValueOnce({ data: { themes: [], stocks: [], strong_themes: [], leaders: [], multi_theme_stocks: [], metadata: { collected_at: '...', theme_count: 0, stock_count: 0, elapsed_sec: 0, errors: [] } } })

fireEvent.click(getByRole('button', { name: /다시 시도|retry/i }))
```

### Then
```typescript
await waitFor(() => {
  // V2 endpoint 추가 호출 검증 (총 2회 — 첫 503 + retry 200)
  const calls = (client.get as any).mock.calls
  const v2Calls = calls.filter(([url]: [string]) => url.startsWith('/themes/v2/'))
  expect(v2Calls.length).toBeGreaterThanOrEqual(2)
})
```

---

## AC-13: ThemeDetailPanel에서 V2 description이 inclusion_reason 자리에 노출 (REQ-NT3-008, D-3)

### Given
- V2 응답 mock에서 stocks의 `inclusion_reason`이 V2 mobile description 텍스트로 채워짐 (V2 parser 정책)

### When
```typescript
const theme = { theme_id: 178, theme_name: '전선', change_pct: 9.2, change_pct_3d: 12.0 }
const stocks = [
  {
    theme_id: 178, theme_name: '전선',
    stock_code: '009470', stock_name: '삼화전기',
    inclusion_reason: '전선 제조사로 자동차 와이어하네스 등 다각화',  // V2 parser가 item.description으로 채움
    price: 12000, change: 100, change_pct: 0.84,
    volume: 100000, trade_value: 1_200_000_000, market_cap: 100_000_000_000,
  }
]

const { container } = render(<ThemeDetailPanel theme={theme} stocks={stocks} leaders={[]} />)
```

### Then
```typescript
// 종목 행에 title 속성으로 V2 description이 노출 (기존 inclusion_reason 자리 — D-3)
const stockRow = container.querySelector('tr[title*="전선 제조사로"]')
expect(stockRow).not.toBeNull()

// ThemeDetailPanel 자체는 무수정 — title 속성 패턴이 V1 ship 시점과 동일
// 본 AC는 cohabitation 보장 검증
```

---

## AC-14: V1 routes byte-identical 회귀 (REQ-NT3-C-001, REQ-NT3-R-001)

### Given
- `backend/routers/themes.py`의 V1 route 함수 이름과 path가 SPEC-001 ship 시점과 동일

### When
```python
from backend.main import app
from fastapi.testclient import TestClient

client = TestClient(app)
routes = [(r.path, list(r.methods or set()), r.endpoint.__name__) for r in app.routes if hasattr(r, "path")]

v1_snapshot = [r for r in routes if r[0] == "/api/themes/snapshot"]
v1_quick = [r for r in routes if r[0] == "/api/themes/quick"]
v2_snapshot = [r for r in routes if r[0] == "/api/themes/v2/snapshot"]
v2_quick = [r for r in routes if r[0] == "/api/themes/v2/quick"]
```

### Then
```python
# V1 routes 그대로 등록 (REQ-NT3-R-001)
assert len(v1_snapshot) == 1
assert len(v1_quick) == 1
assert "GET" in v1_snapshot[0][1]
assert "GET" in v1_quick[0][1]

# V2 routes 그대로 등록 (REQ-NT3-R-002)
assert len(v2_snapshot) == 1
assert len(v2_quick) == 1
assert "GET" in v2_snapshot[0][1]
assert "GET" in v2_quick[0][1]

# V1 backend 모듈 무수정 검증 (REQ-NT3-C-002) — git diff 외부 검증으로도 보강
import backend.services.naver_theme.service
import backend.services.naver_theme.parser
import backend.services.naver_theme.analyzer
import backend.services.naver_theme.crawler
import backend.services.naver_theme.config
# import 자체 가능 + AC-15에서 V1 51 단위 테스트 PASS로 동작 보장
```

---

## AC-15: V1 51 단위 테스트 + V2 24 단위 테스트 회귀 0 + frontend vitest baseline 동일 (REQ-NT3-C-002, REQ-NT3-C-003, REQ-NT3-NF-004)

### Given
- 본 SPEC 작업 완료 시점

### When
```bash
# Backend
source .venv/bin/activate
pytest tests/test_naver_theme_parser.py tests/test_naver_theme_analyzer.py -v -m "not live"
pytest tests/test_naver_theme_v2_*.py -v -m "not live"

# Frontend
cd frontend && npm run test -- --run
```

### Then
```
Backend V1: 51 passed (회귀 0 — REQ-NT3-C-002)
Backend V2: 24 passed (metadata alias AC 추가 후에도 GREEN — REQ-NT3-C-003)
Frontend vitest: 신규 vitest 추가 후 (256 + N) passed, 1 failed (ChartGrid pre-existing only — REQ-NT3-NF-004)

baseline diff:
- 신규 fail (ChartGrid 외): 0건
- 회귀 fail (이전 PASS였던 것이 fail로 전환): 0건
```

---

## AC-16: ThemeDetailPanel에 theme_description 본문 노출 (REQ-NT3-009, v1.0.1 amendment)

### Given
- ThemeDetailPanel에 `theme_description`이 채워진 ThemeItem 1개 props 전달

### When
```typescript
import { render } from '@testing-library/react'
import { ThemeDetailPanel } from '../ThemeDetailPanel'

const theme = {
  theme_id: 178,
  theme_name: '전선',
  change_pct: 9.2,
  change_pct_3d: 12.0,
  theme_description: '각종 전선 및 전람(電纜)제조 판매업체. AI 인프라 수요 급증.',
}

const { container } = render(
  <ThemeDetailPanel theme={theme} stocks={[]} leaders={[]} />
)
```

### Then
```typescript
const descBody = container.querySelector('[data-testid="theme-description-body"]')
expect(descBody).not.toBeNull()
expect(descBody?.textContent).toContain('각종 전선')
```

또한 `theme_description`이 null/undefined/empty일 때:
```typescript
const descBody = container.querySelector('[data-testid="theme-description-body"]')
expect(descBody).toBeNull()  // D-4 hidden 정책 보존
```

---

## AC-17: ThemeDetailPanel에 inclusion_reason 본문 노출 (REQ-NT3-010, v1.0.1 amendment)

### Given
- ThemeDetailPanel에 `inclusion_reason`이 채워진 stock + leader props 전달

### When
```typescript
const theme = { theme_id: 557, theme_name: '유리 기판', change_pct: 13.58, change_pct_3d: 13.58 }
const stocks = [{
  theme_id: 557, theme_name: '유리 기판',
  stock_code: '011790', stock_name: 'SKC',
  inclusion_reason: "美 반도체 소재 자회사 SK앱솔릭스, 글라스 기판을 게임 체인저로 보고 상용화 추진",
  price: 161200, change: 37200, change_pct: 30.0,
  volume: 2100000, trade_value: 320_300_000_000, market_cap: 6_104_400_000_000,
}]
const leader = { ...stocks[0], rank: 1 }

const { container } = render(
  <ThemeDetailPanel theme={theme} stocks={stocks} leaders={[leader]} />
)
```

### Then
```typescript
// 종목 테이블 행 뒤 본문 노출 검증
const stockReasonBody = container.querySelector('[data-testid="stock-inclusion-reason-body"]')
expect(stockReasonBody).not.toBeNull()
expect(stockReasonBody?.textContent).toContain('게임 체인저')

// 주도주 카드 본문 노출 검증
const leaderReasonBody = container.querySelector('[data-testid="leader-inclusion-reason-body"]')
expect(leaderReasonBody).not.toBeNull()
expect(leaderReasonBody?.textContent).toContain('게임 체인저')

// hover tooltip(title 속성) 보존 검증 (AC-13 호환)
const stockRow = container.querySelector('tr[title*="게임 체인저"]')
expect(stockRow).not.toBeNull()
```

또한 `inclusion_reason`이 null/undefined/empty일 때:
```typescript
const reasonBody = container.querySelector('[data-testid="stock-inclusion-reason-body"]')
expect(reasonBody).toBeNull()
```

---

## AC-18: 주도주 섹션 미렌더링 (REQ-NT3-011, v1.0.2 amendment)

### Given
- ThemeDetailPanel에 leaders 배열이 채워진 props 전달

### When
```typescript
const theme = {
  theme_id: 557,
  theme_name: '유리 기판',
  change_pct: 13.58,
  change_pct_3d: 13.58,
}
const leaders = [{
  theme_id: 557, theme_name: '유리 기판',
  stock_code: '011790', stock_name: 'SKC',
  inclusion_reason: '美 반도체 소재 자회사 SK앱솔릭스, 글라스 기판을 게임 체인저로',
  price: 161200, change: 37200, change_pct: 30.0,
  volume: 2100000, trade_value: 320_300_000_000, market_cap: 6_104_400_000_000,
  rank: 1,
}]

const { container } = render(
  <ThemeDetailPanel theme={theme} stocks={[]} leaders={leaders} />
)
```

### Then
```typescript
// leader card body는 v1.0.2에서 미렌더링
const leaderReasonBody = container.querySelector('[data-testid="leader-inclusion-reason-body"]')
expect(leaderReasonBody).toBeNull()

// "주도주" 헤더 텍스트도 미렌더링
expect(screen.queryByText('주도주')).toBeNull()
```

또한 leaders prop을 omit한 경우(optional)에도 정상 렌더링:
```typescript
const { container } = render(
  <ThemeDetailPanel theme={theme} stocks={[]} />  // leaders omitted
)
const descBody = container.querySelector('[data-testid="theme-description-body"]')
expect(descBody).not.toBeNull()  // 테마 설명은 정상
expect(screen.queryByText('주도주')).toBeNull()  // 주도주 미렌더링
```

---

## AC-19: 기본 조회 모드 'full' (REQ-NT3-012, v1.0.3 amendment)

### Given
- ThemeAnalysis 컴포넌트 첫 마운트 직후

### When
```typescript
import { render, waitFor } from '@testing-library/react'
import { ThemeAnalysis } from '../ThemeAnalysis'
import client from '../../../api/client'

vi.mock('../../../api/client', () => ({ default: { get: vi.fn() } }))
vi.mocked(client.get).mockResolvedValue({ data: { themes: [], strong_themes: [], stocks: [], leaders: [], multi_theme_stocks: [], metadata: { ... } } })

render(<ThemeAnalysis />)
```

### Then
```typescript
await waitFor(() => {
  const calls = vi.mocked(client.get).mock.calls
  // default가 full이므로 snapshot endpoint 호출
  const snapshotCalls = calls.filter(([url]) => url === '/themes/v2/snapshot')
  expect(snapshotCalls.length).toBeGreaterThanOrEqual(1)
  // quick endpoint는 default 진입 시 호출되지 않음
  const quickCalls = calls.filter(([url]) => url === '/themes/v2/quick')
  expect(quickCalls.length).toBe(0)
})
```

---

## AC-20: 빠른 조회 모드 advisory 노출 (REQ-NT3-013, v1.0.3 amendment)

### Given
- ThemeAnalysis 정상 마운트 후 사용자가 "빠른 조회" 버튼 클릭

### When
```typescript
import { fireEvent, screen, render, waitFor } from '@testing-library/react'

render(<ThemeAnalysis />)

// default full → advisory 미노출
await waitFor(() => {
  expect(screen.queryByTestId('theme-quick-advisory')).toBeNull()
})

// 빠른 조회 토글
fireEvent.click(screen.getByRole('button', { name: /빠른 조회/i }))
```

### Then
```typescript
await waitFor(() => {
  const advisory = screen.queryByTestId('theme-quick-advisory')
  expect(advisory).not.toBeNull()
  expect(advisory?.textContent).toContain('빠른 조회 모드')
  expect(advisory?.textContent).toContain('전체 조회')  // CTA 안내
})
```

---

## AC-21: strong_themes_df theme_description 매핑 (REQ-NT3-014, v1.0.4 amendment)

### Given
- `_make_service_mock()` (V2 service 단위 테스트 fixture). detail_synthetic.json fixture에 sectorDescription 채워져 있음.

### When
```python
from backend.services.naver_theme_v2 import collect_and_analyze_v2

with _make_service_mock():
    result = collect_and_analyze_v2(top_n_themes=5, skip_details=False)
```

### Then
```python
# strong_themes_df 컬럼에 theme_description 존재
assert "theme_description" in result.strong_themes_df.columns

# themes_df → strong_themes_df 매핑 정합
desc_map = result.themes_df.set_index("theme_id")["theme_description"].to_dict()
for _, row in result.strong_themes_df.iterrows():
    theme_id = row["theme_id"]
    expected = desc_map.get(theme_id)
    actual = row["theme_description"]
    assert actual == expected, f"mismatch theme_id={theme_id}"

# detail fixture가 description을 채우므로 strong_themes에도 truthy description 1개 이상
truthy_count = sum(
    1 for desc in result.strong_themes_df["theme_description"] if desc
)
assert truthy_count >= 1
```

---

## 부록: 검증 자동화 매트릭스

| AC | 검증 방식 | 의존성 |
|---|---|---|
| AC-1 | unit (vitest, axios mock + URL capture) | vi.mock |
| AC-2 | unit (vitest, TypeScript type assertion) | tsc |
| AC-3 | unit (vitest, TypeScript type assertion) | tsc |
| AC-4 | unit (vitest, RTL render + querySelector title attr) | @testing-library/react |
| AC-5 | unit (vitest, RTL render + null/undefined 분기) | @testing-library/react |
| AC-6 | unit (pytest, V2 service mock + metadata 검증) | unittest.mock |
| AC-7 | unit (pytest, datetime.fromisoformat) | datetime 표준 |
| AC-8 | unit (pytest, len 비교) | pandas |
| AC-9 | unit (pytest, time.monotonic 측정값 검증) | time 표준 |
| AC-10 | unit (pytest, 5xx mock + `_empty_result` 호출 경로) | unittest.mock |
| AC-11 | unit (vitest, axios mock 503 + RTL 에러 텍스트) | @testing-library/react |
| AC-12 | unit (vitest, fireEvent click + 재호출 횟수 검증) | @testing-library/react |
| AC-13 | unit (vitest, RTL render + title attr 검증, ThemeDetailPanel 무수정 호환) | @testing-library/react |
| AC-14 | integration (FastAPI TestClient route 검사) | TestClient |
| AC-15 | integration (pytest + vitest 전체 실행 + baseline 비교) | pytest, vitest |
| AC-16 | unit (vitest, RTL render + data-testid 본문 노출 검증) | @testing-library/react |
| AC-17 | unit (vitest, RTL render + data-testid 본문 노출 + title hover 보존 검증) | @testing-library/react |
| AC-18 | unit (vitest, RTL render + leader-inclusion-reason-body 미렌더링 + "주도주" 텍스트 미렌더링) | @testing-library/react |
| AC-19 | unit (vitest, default render → /themes/v2/snapshot 호출 검증) | @testing-library/react + vi.mock |
| AC-20 | unit (vitest, quick 토글 → theme-quick-advisory data-testid 노출) | @testing-library/react |
| AC-21 | unit (pytest, _make_service_mock + strong_themes_df description 매핑 검증) | unittest.mock, fixtures |

### 라이브 테스트 정책

본 SPEC는 신규 라이브 테스트 마커 추가 없이 SPEC-002의 라이브 1 PASS(`@pytest.mark.live test_collect_and_analyze_v2_live`)에 의존한다. 본 SPEC 변경(metadata alias 추가)은 SPEC-002 라이브 테스트로도 자동 검증된다 — V1 alias 4 필드 존재 검증을 SPEC-002 라이브 테스트에 추가하지는 않으나, AC-6 ~ AC-10 unit 테스트가 fixture로 동등 검증.

---

## Definition of Done

- [ ] AC-1 ~ AC-15 자동 검증 PASS (15/15)
- [ ] 단위 테스트 커버리지 SPEC-002 baseline (≥85%) 유지
- [ ] V1 단위 테스트 51개 회귀 0 (REQ-NT3-C-002 검증)
- [ ] V2 단위 테스트 24개 + metadata alias AC 신규 추가 후 GREEN (REQ-NT3-C-003 검증)
- [ ] frontend vitest baseline diff 0 (ChartGrid 1 fail 그대로 유지, 신규 fail 0 — REQ-NT3-NF-004 검증)
- [ ] V1 endpoint `/api/themes/snapshot`, `/api/themes/quick` smoke test PASS (변경 없음 확인 — REQ-NT3-R-001)
- [ ] V2 endpoint `/api/themes/v2/snapshot`, `/api/themes/v2/quick` smoke test PASS (frontend 호출 대상 — REQ-NT3-R-002)
- [ ] V1 backend 모듈 git diff empty (REQ-NT3-C-002 자동 + 수동 확인)
- [ ] bare except 0건 (REQ-NT3-C-005, ruff/manual grep)
- [ ] pip/npm 신규 의존성 0건 (REQ-NT3-C-004, requirements.txt + package.json diff)
- [ ] V2 endpoint 503 mock 시 V1 자동 호출 0건 (REQ-NT3-C-006 — AC-11에서 검증)

---

Version: 1.0.0
Status: Draft (본 SPEC RUN phase 검증 기준)
