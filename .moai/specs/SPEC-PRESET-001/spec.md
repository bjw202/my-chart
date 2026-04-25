---
id: SPEC-PRESET-001
title: Filter Preset Chips (Frontend + Pattern Limit Expansion)
version: 1.0.1
status: planned
created: 2026-04-21
updated: 2026-04-21
author: jw
priority: P2
tags: [frontend, react, typescript, vite, filter, preset, url-sync, tdd]
related:
  - SPEC-MINERVINI-001
  - SPEC-UI-001
  - SPEC-DASHBOARD-002
---

# SPEC-PRESET-001: 필터 프리셋 칩 + 패턴 한도 확장 (Frontend)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
|------|------|--------|----------|
| 1.0.0 | 2026-04-21 | jw | 초기 SPEC 작성 (research.md 2026-04-21 기반). v1 프리셋 3종 (minervini_full, breakout_init, stage1_accumulation) 고정, 칩 UI + 드리프트 감지 + URL 동기화 + patterns 한도 3→5 확장 |
| 1.0.1 | 2026-04-21 | jw | patterns 완전 대체 확정 (A2 사용자 재승인), minervini_full DB 안내 툴팁 v1 포함 (REQ-PST-012 신설, AC-12 추가, R1 재정의, §10 out-of-scope #9 편입) |

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **프로젝트**: KR Stock Screener (FastAPI + React + SQLite)
- **선행 리서치**: `.moai/specs/SPEC-PRESET-001/research.md` (2026-04-21)
- **목표**: 미너비니·스테이지 기반 원클릭 필터 프리셋을 도입하고, 패턴 조건 한도를 3 → 5 로 확장한다.
- **범위**: 프런트엔드 UI/UX (칩 바), 상태 파생 (드리프트 감지), URL 동기화, 패턴 한도 완화. 스크리닝 엔진 로직은 SPEC-MINERVINI-001 의 책임이다.
- **배포 환경**: localhost 전용

### 1.2 기술 스택

- **Frontend**: React 18+, TypeScript (strict), Vite, 기존 `ScreenContext` 패턴
- **Testing (Unit/Integration)**: Vitest + React Testing Library (`frontend/src/**/__tests__/`)
- **Testing (E2E)**: Playwright (`frontend/e2e/`)
- **Backend**: Python 3.13+, FastAPI, Pydantic v2 — 본 SPEC 에서는 `patterns.max_length` 제약 변경만 수행
- **개발 방법론**: TDD (`.moai/config/sections/quality.yaml` 의 `development_mode: tdd`)
- **문서 언어**: 한국어 산문 + 영어 식별자

### 1.3 기존 코드 현황 (2026-04-21 기준)

| 경로 | 역할 | 본 SPEC 에서의 역할 |
|------|------|-------------------|
| `frontend/src/types/filter.ts` | `ScreenRequest`, `PatternCondition`, `DEFAULT_SCREEN_REQUEST` 정의 | `Preset` 타입 export 추가 |
| `frontend/src/components/FilterBar/FilterBar.tsx` | 필터 폼 루트 (MarketCap + Return + Pattern + RS + DbUpdate) | 상단에 `PresetChips` 삽입, 드리프트 감지, URL 동기화 |
| `frontend/src/components/FilterBar/PatternBuilder.tsx` | 패턴 조건 빌더, 현재 max 3 (`patterns.length < 3`) | 한도 3 → 5 로 변경 |
| `frontend/src/contexts/ScreenContext.tsx` | `filters`, `applyFilters`, `updateFilters`, `clearResults` 노출 | 불변 유지 또는 `activePresetId` 노출 (§6.3 참조) |
| `backend/schemas/screen.py` | `ScreenRequest.patterns` Pydantic 검증 | `max_length=3 → 5` 완화 |

### 1.4 선행 SPEC 의존성

- **SPEC-MINERVINI-001** (진행 중, blocker-free): `ScreenRequest.minervini_trend_template: bool | None` 필드 및 `StockItem.trend_template_score: int | None` 필드 도입. `minervini_full` 프리셋이 소비하는 필드이다.
- **SPEC-MINERVINI-001 REQ-MIN-005**: `patterns.max_length=5` 확장도 동일 변경을 포함한다. 두 SPEC 은 동일 변경에 대해 **중복 책임** 을 가지며, 어느 쪽이 먼저 머지되어도 무해하다 (idempotent relaxation).
- **SPEC-MINERVINI-001 REQ-MIN-007**: 백엔드 마이그레이션 미적용 환경에서 `minervini_trend_template=true` 요청은 HTTP 200 + 빈 응답을 반환한다. 본 SPEC 은 프런트엔드 가드를 추가하지 않고 이 계약에 의존한다.
- **SPEC-MINERVINI-001 배포 모델**: SPEC-MINERVINI-001 배포는 daily/weekly DB 파일 전체 재생성을 수반한다 (SPEC-MINERVINI-001 v1.0.2 Assumption A9 참조). 따라서 "컬럼 누락" 시나리오는 상시 사용자 경로가 아니라 배포 전환기 또는 운영자 오류로 발생하는 전이적 상태이며, REQ-PST-012 툴팁은 이 전이 창구에서의 사용자 안내 장치로 기능한다.

---

## 2. Assumptions (가정)

- **A1**: 사전 확정 결정 사항은 본 SPEC 의 의사결정으로 고정된다. 구체적으로 (1) UI 는 **칩 버튼 바**, (2) 최대 패턴 수는 **5**, (3) 라이프사이클은 **클릭 적용 / 활성 칩 재클릭 토글 오프**, (4) 드리프트 감지는 활성화, (5) URL 동기화 키는 `?preset=<id>`, (6) 레지스트리 위치는 `frontend/src/presets/filter-presets.ts`, (7) v1 프리셋은 **3종** (`minervini_full`, `breakout_init`, `stage1_accumulation`).
- **A2**: `Partial<ScreenRequest>` 를 `DEFAULT_SCREEN_REQUEST` 에 얕은 병합 (shallow merge) 으로 적용한다. 단, `patterns: PatternCondition[]` 배열은 프리셋 값으로 **완전 치환** 한다 (concat 아님). 이는 `breakout_init` 이 기존 patterns 를 덮어쓰고 자신의 3조건만 남기길 기대하기 때문이다. **사용자 재승인 (2026-04-21, v1.0.1)**: 본 동작은 v1.0.1 에서 사용자가 명시적으로 확정한 기본 동작이다. `concat` 또는 "기존에 5개까지 채워져 있을 때의 확인 다이얼로그" 같은 대안은 향후 별도 SPEC 에서 재평가한다 (§8 R7).
- **A3**: 드리프트 감지는 **깊은 동등 비교 (deep equality)** 로 구현한다. 현재 `filters` 와 `applyPatch(DEFAULT, preset.patch)` 결과가 일치하는 프리셋이 있으면 그 ID 를 활성으로, 없으면 null 로 판정한다 (research.md §3 참조).
- **A4**: URL 동기화는 **History API** 의 `replaceState` 로 구현한다. React Router 에 의존하지 않는다. 초기 마운트 시 `window.location.search` 를 1회 읽어 `?preset=<id>` 가 있으면 자동 적용한다 (research.md §4 참조).
- **A5**: `minervini_full` 프리셋은 SPEC-MINERVINI-001 의 `minervini_trend_template` 필드가 배포되기 전까지 결과 집합이 비어 있을 수 있다. REQ-MIN-007 의 200 OK + empty + WARN log 계약에 의존하므로 프런트엔드 가드는 추가하지 않는다.
- **A6**: 프리셋 라벨은 **한국어** 만 지원한다 (i18n 은 out of scope). 식별자 (id) 와 코드 주석은 영어.
- **A7**: 백엔드 `patterns.max_length` 완화는 **기존 클라이언트를 거부하지 않는 완화 방향** 이다. 기존 1~3 개 patterns 요청은 그대로 수용된다.
- **A8**: 프리셋 적용은 `applyFilters(merged)` 를 **정확히 1회** 호출한다. 프리셋 토글 오프는 `clearResults()` 호출로 `DEFAULT_SCREEN_REQUEST` 및 결과 초기화를 의미한다.
- **A9**: URL `?preset=<id>` 의 `<id>` 가 레지스트리에 존재하지 않는 값이면 (예: 삭제된 프리셋) 시스템은 해당 파라미터를 무시하고 기본 상태를 유지한다 (§4.3 참조).

---

## 3. Requirements (요구사항, EARS 포맷)

### Module 1: Preset Registry (신규)

**REQ-PST-001 — 프리셋 레지스트리 정의**

시스템은 **항상** `frontend/src/presets/filter-presets.ts` 파일에서 `Preset` 타입의 배열을 단일 진실 원천으로 export 해야 한다.

- `Preset` 타입은 `{ id: string; label: string; description: string; patch: Partial<ScreenRequest> }` 이다.
- 레지스트리는 v1 출시 시점에 **정확히 3개** 의 프리셋을 포함한다: `minervini_full`, `breakout_init`, `stage1_accumulation`.
- 각 `id` 는 고유하며, 각 `label` 은 비어 있지 않은 한국어 문자열이다.
- 각 `patch` 는 TypeScript strict 타입 체크에서 `Partial<ScreenRequest>` 에 할당 가능해야 한다.
- 프리셋 정의 상세는 §4.2 를 참조한다.

### Module 2: PresetChips UI (신규)

**REQ-PST-002 — 칩 바 렌더링 위치**

시스템은 **항상** FilterBar 최상단 (기존 폼 row 위) 에 `PresetChips` 컴포넌트를 렌더링하여 레지스트리의 각 프리셋당 버튼 1개를 표시해야 한다.

- 컨테이너는 `role="group"` 과 `aria-label="필터 프리셋"` 을 가진다 (REQ-PST-009 참조).
- 각 칩은 `<button type="button">` 이며 프리셋의 `label` 을 텍스트로 표시한다.
- 칩 간격, 활성/비활성 스타일, 포커스 링은 §6.5 의 스타일 가이드를 따른다.

**REQ-PST-003 — 비활성 칩 클릭 (프리셋 적용)**

**WHEN** 사용자가 비활성 (현재 활성 ID 와 다른) 프리셋 칩을 클릭하면 **THEN** 시스템은 다음 순서로 동작해야 한다:

1. `merged = applyPatch(DEFAULT_SCREEN_REQUEST, preset.patch)` 를 계산한다 (shallow merge + patterns 배열 치환, A2 참조).
2. `applyFilters(merged)` 를 **정확히 1회** 호출한다 (중복 네트워크 요청 금지).
3. URL 을 `?preset=<id>` 로 갱신한다 (REQ-PST-007 참조).

다른 프리셋이 이미 활성 상태였다면 해당 프리셋은 자동으로 비활성화된다 (단일 활성 보장).

**REQ-PST-004 — 활성 칩 재클릭 (토글 오프)**

**WHEN** 사용자가 **현재 활성 상태** 인 프리셋 칩을 다시 클릭하면 **THEN** 시스템은 다음 순서로 동작해야 한다:

1. `clearResults()` 를 호출한다 (ScreenContext 가 `filters` 를 `DEFAULT_SCREEN_REQUEST` 로 리셋하고 `results` 를 null 로 초기화).
2. URL 에서 `preset` 쿼리 파라미터를 제거한다 (REQ-PST-007 참조).
3. 네트워크 요청은 발생하지 않는다 (`applyFilters` 호출 금지).

**REQ-PST-005 — 활성 상태 시각화**

시스템은 **항상** 각 칩의 활성 여부를 `aria-pressed` 속성으로 노출하고 시각적으로 구분해야 한다.

- 활성 칩: `aria-pressed="true"`, 채도가 높은 배경색, 강조된 테두리
- 비활성 칩: `aria-pressed="false"`, 중립 배경, 옅은 테두리
- 활성 칩이 없을 수 있다 (드리프트 상태 또는 초기 상태). 이 경우 모든 칩은 `aria-pressed="false"` 이다.

**REQ-PST-012 — `minervini_full` 칩 DB 안내 툴팁 (v1.0.1 신설)**

시스템은 **항상** `id === "minervini_full"` 인 프리셋 칩에 한해 다음 한국어 안내 문구를 네이티브 툴팁으로 노출해야 한다.

- 툴팁 문구 (정확 일치): `"SMA150·52주 고저가·SMA200 추세 컬럼이 필요합니다. DB 업데이트(파일 재생성)를 먼저 실행하세요."`
- 구현 방식: 칩 버튼 엘리먼트의 `title` 속성에 위 문구를 부여한다. v1 에서는 커스텀 팝오버/툴팁 컴포넌트를 도입하지 않는다 (네이티브 충분).
- **WHEN** 칩의 `preset.id === "minervini_full"` 이면 **THEN** `title` 은 위 문구이다.
- **WHEN** 칩의 `preset.id !== "minervini_full"` 이면 **THEN** `title` 은 해당 프리셋의 `description` 문자열이다 (기본 동작).
- 활성/비활성 상태와 무관하게 툴팁 내용은 일정하다 (hover 시 같은 문구).
- 근거: SPEC-MINERVINI-001 배포가 DB 파일 재생성을 수반하므로 (§1.4) 전이적으로 컬럼이 없는 상태에서 빈 결과를 받은 사용자가 원인을 알 수 있도록 UI 단에서 선제 안내한다. REQ-PST-011 (백엔드 REQ-MIN-007 의존) 과 함께 3중 방어를 구성한다 (§8 R1 참조).

### Module 3: Drift Detection (신규)

**REQ-PST-006 — 드리프트 감지로 활성 ID 파생**

시스템은 **항상** 현재 `filters` 상태로부터 `activePresetId` 를 파생해야 한다.

- **WHEN** `filters` 가 레지스트리의 어느 프리셋 `p` 에 대해 `applyPatch(DEFAULT_SCREEN_REQUEST, p.patch)` 와 **깊은 동등** 을 이루면 **THEN** `activePresetId = p.id`.
- **WHEN** 일치하는 프리셋이 없으면 **THEN** `activePresetId = null`.
- 사용자가 임의의 필드를 수정하여 값이 프리셋 정의와 달라지면 (예: `rs_min: 70 → 80`) 자동으로 `activePresetId = null` 이 되어야 한다.
- 반대로 사용자가 우연히 값을 프리셋 정의와 정확히 일치하도록 되돌리면 해당 프리셋이 다시 활성화된다 (복구 UX).
- 구현은 `useMemo([filters, presets])` 파생값으로 처리한다.

### Module 4: URL Synchronization (신규)

**REQ-PST-007 — 활성 프리셋 URL 반영**

시스템은 **항상** `activePresetId` 의 변화를 URL 쿼리 파라미터 `preset` 에 반영해야 한다.

- **WHEN** `activePresetId` 가 비어 있지 않은 값으로 변하면 **THEN** `window.history.replaceState` 로 `?preset=<id>` 를 URL 에 기록한다.
- **WHEN** `activePresetId` 가 null 이 되면 **THEN** URL 에서 `preset` 파라미터만 제거한다 (다른 쿼리 파라미터는 보존).
- URL 변경은 **히스토리 엔트리를 생성하지 않는다** (`replaceState` 사용).
- **IF** 초기 마운트 시 `window.location.search` 에 `?preset=<id>` 가 있고 레지스트리에 `<id>` 가 존재하면 **THEN** 시스템은 해당 프리셋을 자동 적용한다 (REQ-PST-003 과 동일 경로).
- **IF** 초기 마운트 시 `?preset=<id>` 가 레지스트리에 없으면 **THEN** 시스템은 파라미터를 조용히 무시하고 기본 상태를 유지한다 (A9 참조).

### Module 5: Pattern Limit Expansion (신규 + 백엔드 소규모 변경)

**REQ-PST-008 — 프런트엔드 패턴 한도 5로 확장**

시스템은 **항상** `PatternBuilder` 컴포넌트에서 최대 **5개** 의 패턴 조건을 허용해야 한다.

- `patterns.length < 5` 일 때만 "조건 추가" 버튼을 렌더링한다 (현재 `< 3` 에서 변경).
- `patterns.length >= 5` 이면 "조건 추가" 버튼은 DOM 에서 제거되거나 `disabled` 로 표시한다 (AC-7 기준 DOM 제거를 채택).
- 기존 `removePattern` 동작은 변경 없음 (5 → 4 로 줄면 버튼이 다시 나타난다).

**REQ-PST-009 — 백엔드 Pydantic 제약 5로 완화**

시스템은 **항상** `backend/schemas/screen.py` 의 `ScreenRequest.patterns` 필드에서 `max_length=5` 를 허용해야 한다 (현재 3).

- **WHEN** 5개 patterns 를 포함한 요청이 들어오면 **THEN** Pydantic 검증을 통과하고 정상 처리된다.
- **WHEN** 6개 이상 patterns 를 포함한 요청이 들어오면 **THEN** FastAPI 는 HTTP 422 Unprocessable Entity 로 거부해야 한다.
- 기존 0 ~ 3 개 patterns 요청은 영향을 받지 않는다 (relaxation direction).
- 본 변경은 SPEC-MINERVINI-001 REQ-MIN-005 와 **동일한 변경** 이며, 어느 SPEC 이 먼저 머지되어도 멱등적이다.

### Module 6: Accessibility (신규)

**REQ-PST-010 — 접근성 준수**

시스템은 **항상** 칩 UI 에 다음 접근성 속성을 제공해야 한다.

- 컨테이너: `role="group"`, `aria-label="필터 프리셋"`
- 각 칩: `<button type="button">` 이며 `aria-pressed` 속성을 항상 가진다 (true 또는 false).
- 키보드: Tab 으로 순회 가능, Enter 또는 Space 로 활성화.
- 포커스 링: 시스템 기본 포커스 링을 제거하지 않고 가시성을 보장한다.

### Module 7: Backward Compatibility

**REQ-PST-011 — Minervini 미배포 환경 대응 위임**

**IF** `minervini_full` 프리셋이 적용되었는데 백엔드에 `minervini_trend_template` 필드가 아직 배포되지 않았다면 **THEN** 시스템은 SPEC-MINERVINI-001 REQ-MIN-007 의 계약 (HTTP 200 + empty list + WARN log) 에 의존한다.

- 프런트엔드는 별도 가드를 추가하지 않는다 (빈 결과 표시는 정상 동작).
- 칩 UI 는 프리셋이 빈 결과를 반환했다는 이유로 비활성화되지 않는다.
- 툴팁 텍스트 "DB 업데이트 필요" 는 **선택 사항** 이며 v1 에서는 생략 가능하다 (R1 완화책 참조).

---

## 4. Specifications (세부 사양)

### 4.1 상태 흐름

```
(1) 초기 마운트
      ↓
    window.location.search 파싱
      ↓
    ?preset=<id> 존재 + 레지스트리에 있음 → applyPatch → applyFilters(merged)
    ?preset=<id> 없음 또는 레지스트리에 없음 → 기본 상태 유지

(2) 사용자가 비활성 칩 클릭 (REQ-PST-003)
      ↓
    merged = applyPatch(DEFAULT, preset.patch)
      ↓
    applyFilters(merged)
      ↓
    useMemo 파생: activePresetId = <id> (깊은 동등 일치)
      ↓
    useEffect: history.replaceState → URL ?preset=<id>

(3) 사용자가 활성 칩 재클릭 (REQ-PST-004, 토글 오프)
      ↓
    clearResults()
      ↓
    filters = DEFAULT_SCREEN_REQUEST
      ↓
    useMemo 파생: activePresetId = null
      ↓
    useEffect: URL 에서 preset 파라미터 제거

(4) 사용자가 활성 상태에서 개별 필드 수정 (드리프트)
      ↓
    updateFilters 또는 applyFilters 로 filters 변경
      ↓
    useMemo 재계산: activePresetId = null (동등 불일치)
      ↓
    useEffect: URL 에서 preset 파라미터 제거
      ↓
    칩 aria-pressed 전부 false

(5) Minervini 필드 미배포 환경 + minervini_full 적용
      ↓
    applyFilters(merged) → POST /api/screen
      ↓
    SPEC-MINERVINI-001 REQ-MIN-007: HTTP 200 + total=0
      ↓
    UI 는 빈 결과 표시, 칩은 여전히 활성
```

### 4.2 프리셋 정의 (v1)

#### Preset #1 — `minervini_full` (미너비니 풀)

- **label**: "미너비니 풀"
- **description**: Mark Minervini Trend Template 8조건 엄격 적용. SPEC-MINERVINI-001 필요.
- **patch**:

```ts
{
  minervini_trend_template: true,
  rs_min: 70,
  market_cap_min: 1000,   // 1000억원
}
```

비고: `minervini_trend_template: true` 만으로 8조건이 백엔드 엔진에서 강제되며, `rs_min: 70` 과 `market_cap_min: 1000` 은 엔진 내부 조건과 중복이지만 UI 에서 "안전 최소값" 으로 가시화하기 위해 유지한다.

#### Preset #3 — `breakout_init` (Stage2 돌파)

- **label**: "Stage2 돌파"
- **description**: EMA20 위 거래 중이고 SMA50/SMA200 을 넘어선 추세 전환 초입 종목. RS 70 이상, 1주 수익률 3%+.
- **patch**:

```ts
{
  market_cap_min: 1000,
  rs_min: 70,
  chg_1w_min: 3,
  pattern_logic: "AND",
  patterns: [
    { indicator_a: "Close",  operator: "gt", indicator_b: "EMA20",  multiplier: 1.0 },
    { indicator_a: "EMA20",  operator: "gt", indicator_b: "SMA50",  multiplier: 1.0 },
    { indicator_a: "Close",  operator: "gt", indicator_b: "SMA200", multiplier: 1.0 },
  ],
}
```

#### Preset #5 — `stage1_accumulation` (Stage1 매집)

- **label**: "Stage1 매집"
- **description**: SMA200 ±5% 박스권에서 횡보하며 이평선이 수렴하는 바닥 형성 구간. 급락 종목 제외 (1개월 -5% 이상).
- **patch**:

```ts
{
  market_cap_min: 1000,
  chg_1m_min: -5,
  pattern_logic: "AND",
  patterns: [
    { indicator_a: "Close",  operator: "gt", indicator_b: "SMA200", multiplier: 0.95 },
    { indicator_a: "Close",  operator: "lt", indicator_b: "SMA200", multiplier: 1.05 },
    { indicator_a: "SMA50",  operator: "lt", indicator_b: "SMA200", multiplier: 1.02 },
  ],
}
```

### 4.3 `applyPatch` 의사 코드

```ts
function applyPatch(
  base: ScreenRequest,
  patch: Partial<ScreenRequest>
): ScreenRequest {
  return {
    ...base,
    ...patch,
    // patterns 는 배열이므로 얕은 병합으로 전체 치환 (A2)
    patterns: patch.patterns !== undefined ? patch.patterns : base.patterns,
  }
}
```

`pattern_logic` 은 문자열 스칼라이므로 `...patch` 로 자연스럽게 치환된다. 명시적 분기가 필요한 배열 타입 필드는 `patterns` 하나뿐이다.

### 4.4 타입 변경

```ts
// frontend/src/types/filter.ts

export interface Preset {
  id: string
  label: string
  description: string
  patch: Partial<ScreenRequest>
}
```

기존 `ScreenRequest`, `PatternCondition`, `DEFAULT_SCREEN_REQUEST` 는 불변이다.

### 4.5 백엔드 변경

```python
# backend/schemas/screen.py

class ScreenRequest(BaseModel):
    # ... 기존 필드 ...
    patterns: list[PatternCondition] = Field(
        default_factory=list,
        max_length=5,   # 3 → 5 로 완화
    )
```

SPEC-MINERVINI-001 이 이미 동일 변경을 수행하는 경우, 본 SPEC 의 구현 단계에서 해당 변경이 이미 적용되어 있는지 확인하고 변경이 필요하지 않다면 skip 한다 (멱등).

### 4.6 파일 목록 (수정 / 신규)

#### 신규 파일

| 경로 | 역할 |
|------|------|
| `frontend/src/presets/filter-presets.ts` | 프리셋 레지스트리 (SSOT) + `Preset` 타입 재export |
| `frontend/src/presets/__tests__/filter-presets.test.ts` | 레지스트리 형상 단위 테스트 |
| `frontend/src/components/FilterBar/PresetChips.tsx` | 칩 바 프리젠테이션 컴포넌트. 칩 버튼의 `title` 속성을 조건부로 설정: `preset.id === "minervini_full"` 이면 REQ-PST-012 의 DB 안내 문구, 그 외에는 `preset.description` (REQ-PST-012) |
| `frontend/src/components/FilterBar/__tests__/PresetChips.test.tsx` | 칩 상호작용 + 툴팁 테스트 |
| `frontend/e2e/preset-flow.spec.ts` | Playwright E2E 시나리오 |

#### 수정 파일

| 경로 | 변경 사항 | SPEC 레퍼런스 |
|------|-----------|---------------|
| `frontend/src/types/filter.ts` | `Preset` 타입 export 추가 | REQ-PST-001 |
| `frontend/src/components/FilterBar/FilterBar.tsx` | `PresetChips` 삽입, `activePresetId` 파생, URL 동기화 useEffect | REQ-PST-002/003/004/006/007 |
| `frontend/src/components/FilterBar/PatternBuilder.tsx` | `< 3` → `< 5` 변경 | REQ-PST-008 |
| `frontend/src/components/FilterBar/__tests__/FilterBar.test.tsx` (존재 시) | 프리셋 적용/토글/드리프트 흐름 커버 | REQ-PST-003/004/006 |
| `frontend/src/contexts/ScreenContext.tsx` (선택) | `activePresetId` 컨텍스트 노출 여부 결정 — §6.3 참조 | REQ-PST-006 |
| `frontend/src/styles/global.css` (또는 `FilterBar.css`) | 칩 스타일 토큰 | REQ-PST-005 |
| `backend/schemas/screen.py` | `patterns: Field(max_length=5)` | REQ-PST-009 |
| `backend/tests/test_screen.py` (또는 신규) | 5개 수용, 6개 거부 테스트 | REQ-PST-009 |

### 4.7 Traceability

| 요구사항 | 구현 파일 | 테스트 |
|---------|----------|--------|
| REQ-PST-001 | `frontend/src/presets/filter-presets.ts` | `filter-presets.test.ts` (A1 ~ A3) |
| REQ-PST-002 | `PresetChips.tsx`, `FilterBar.tsx` | `PresetChips.test.tsx` (B1) |
| REQ-PST-003 | `PresetChips.tsx`, `FilterBar.tsx` | `PresetChips.test.tsx` (B2), `FilterBar.test.tsx` (C1) |
| REQ-PST-004 | `PresetChips.tsx`, `FilterBar.tsx` | `PresetChips.test.tsx` (B3) |
| REQ-PST-005 | `PresetChips.tsx` | `PresetChips.test.tsx` (B4) |
| REQ-PST-006 | `FilterBar.tsx` (useMemo 파생) | `FilterBar.test.tsx` (C2) |
| REQ-PST-007 | `FilterBar.tsx` (useEffect + history API) | `FilterBar.test.tsx` (C3, C4) |
| REQ-PST-008 | `PatternBuilder.tsx` | `PatternBuilder.test.tsx` (D1 ~ D3) |
| REQ-PST-009 | `backend/schemas/screen.py` | `test_screen.py` (E1, E2) |
| REQ-PST-010 | `PresetChips.tsx` | `PresetChips.test.tsx` (B4, B5) |
| REQ-PST-011 | 위임 — SPEC-MINERVINI-001 REQ-MIN-007 계약 | SPEC-MINERVINI-001 AC-8 |
| REQ-PST-012 | `PresetChips.tsx` (조건부 `title` 속성) | `PresetChips.test.tsx` (B6), `FilterBar.test.tsx`/E2E AC-12 |

---

## 5. Acceptance Criteria (수용 기준)

각 항목은 Given / When / Then 시나리오로 정의된다. 모든 항목이 통과해야 `run` phase 가 완료된다.

### AC-1: 레지스트리 형상 (Registry Shape)

- **Given** `frontend/src/presets/filter-presets.ts` 가 프리셋 배열을 export 한다
- **When** TypeScript strict 타입 체크를 수행한다
- **Then**
  - 배열의 각 요소는 `Preset` 타입에 할당 가능하다
  - 각 요소의 `patch` 는 `Partial<ScreenRequest>` 에 할당 가능하다
  - `id` 는 모두 고유하며 `label` 은 비어 있지 않은 한국어 문자열이다
  - 배열 길이는 정확히 3 (`minervini_full`, `breakout_init`, `stage1_accumulation`)

### AC-2: 비활성 칩 클릭 → 프리셋 적용

- **Given** 필터가 `DEFAULT_SCREEN_REQUEST` 인 초기 상태이다
- **When** 사용자가 `breakout_init` 칩을 클릭한다
- **Then**
  - `local` 상태는 `applyPatch(DEFAULT, BREAKOUT_INIT.patch)` 와 깊은 동등이다
  - `applyFilters` 는 merged 상태로 **정확히 1회** 호출된다
  - URL 은 `?preset=breakout_init` 로 업데이트된다
  - `breakout_init` 칩은 `aria-pressed="true"` 이고 나머지 2개는 `"false"` 이다

### AC-3: 활성 칩 재클릭 → 토글 오프

- **Given** `breakout_init` 프리셋이 적용되어 활성 상태이다
- **When** 사용자가 동일한 `breakout_init` 칩을 다시 클릭한다
- **Then**
  - `local` 은 `DEFAULT_SCREEN_REQUEST` 로 리셋된다
  - `clearResults` 가 호출되고 `applyFilters` 는 호출되지 않는다
  - URL 에서 `preset` 파라미터가 제거된다 (`?` 가 제거되어 깔끔한 pathname 이 된다, 또는 다른 파라미터만 남는다)
  - 모든 칩의 `aria-pressed` 는 `"false"` 이다

### AC-4: 드리프트 감지 — 수동 수정 시 활성 해제

- **Given** `minervini_full` 프리셋이 적용되어 활성 상태 (`rs_min=70`, `aria-pressed="true"`) 이다
- **When** 사용자가 `RSFilter` 입력을 통해 `rs_min` 을 70 에서 80 으로 변경한다
- **Then**
  - `activePresetId` 는 null 이 된다
  - 모든 칩의 `aria-pressed` 는 `"false"` 이다
  - URL 에서 `preset` 파라미터가 제거된다

### AC-5: URL 동기화 — 초기 마운트 시 자동 적용

- **Given** 브라우저 URL 이 `?preset=stage1_accumulation` 이다
- **When** 페이지가 로드된다
- **Then**
  - `stage1_accumulation` 프리셋이 자동으로 적용된다
  - `stage1_accumulation` 칩이 `aria-pressed="true"` 를 가진다
  - `applyFilters` 가 merged 상태로 1회 호출된다
  - URL 은 `?preset=stage1_accumulation` 그대로 유지된다 (replaceState 중복 호출 없음)

### AC-6: URL 동기화 — 드리프트 시 파라미터 제거

- **Given** 활성 프리셋이 있고 URL 이 `?preset=<id>` 이다
- **When** 사용자가 드리프트를 유발하는 필드 변경을 수행한다
- **Then** URL 의 `preset` 파라미터만 제거된다 (`?other=foo&preset=<id>` → `?other=foo`)

### AC-7: PatternBuilder 한도 5 (프런트엔드)

- **Given** `PatternBuilder` 에 4개 patterns 가 있다
- **When** UI 를 렌더링한다
- **Then** "조건 추가" 버튼이 렌더된다
- **And Given** 5개 patterns 가 있다
- **When** UI 를 렌더링한다
- **Then** "조건 추가" 버튼이 DOM 에 존재하지 않는다
- **And When** 사용자가 1개를 제거하여 4개가 되면
- **Then** "조건 추가" 버튼이 다시 렌더된다

### AC-8: 백엔드 Pydantic 한도 5

- **Given** FastAPI 서버가 실행 중이다
- **When** `POST /api/screen` 에 5개 patterns 를 포함한 요청을 보낸다
- **Then** HTTP 200 응답이 반환된다 (정상 스크리닝 결과)
- **And When** 6개 patterns 를 포함한 요청을 보낸다
- **Then** HTTP 422 Unprocessable Entity 가 반환된다
- **And When** 1개 또는 3개 patterns 로 기존 요청을 보낸다
- **Then** 이전과 동일한 응답이 반환된다 (회귀 없음)

### AC-9: Minervini 미배포 환경 대응 (SPEC-MINERVINI-001 REQ-MIN-007 계약 의존)

- **Given** 백엔드에 `minervini_trend_template` 필드와 관련 컬럼이 아직 배포되지 않은 상태
- **When** 사용자가 `minervini_full` 칩을 클릭한다
- **Then**
  - 프리셋은 정상 적용된다 (칩은 `aria-pressed="true"`)
  - `POST /api/screen` 응답은 HTTP 200, `total=0`, `sectors=[]` (REQ-MIN-007 계약)
  - UI 는 빈 결과를 표시하며, 에러 배너나 5xx 를 표시하지 않는다

### AC-10: 접근성

- **Given** `PresetChips` 가 렌더링되어 있다
- **When** 자동화된 접근성 검사 (예: `@testing-library/react` 의 role/aria 쿼리) 를 수행한다
- **Then**
  - 컨테이너는 `role="group"` 과 `aria-label="필터 프리셋"` 을 가진다
  - 각 칩은 `<button>` 엘리먼트이며 `aria-pressed` 속성을 항상 가진다
- **And When** 키보드 Tab 순회 후 Enter 또는 Space 를 누른다
- **Then** 해당 칩이 활성화된다 (REQ-PST-003 동작)

### AC-11: 모바일 반응형

- **Given** 뷰포트 폭이 360px 로 축소되어 있다
- **When** `PresetChips` 가 렌더링되어 있다
- **Then**
  - 칩 바는 가로 스크롤로 접근 가능하다 (`overflow-x: auto`)
  - 각 칩의 라벨은 잘리지 않는다 (`white-space: nowrap`)
  - 각 칩의 터치 영역은 44px 이상이다

### AC-12: `minervini_full` DB 안내 툴팁 (v1.0.1 신설, REQ-PST-012)

- **Given** `PresetChips` 가 렌더링되어 있고 `minervini_full` 칩이 DOM 에 존재한다
- **When** 사용자가 `minervini_full` 칩 위에 마우스를 호버한다 (또는 테스트에서 `title` 속성을 읽는다)
- **Then** 네이티브 툴팁 (칩 버튼의 `title` 속성) 문자열이 정확히 다음과 일치한다:
  `"SMA150·52주 고저가·SMA200 추세 컬럼이 필요합니다. DB 업데이트(파일 재생성)를 먼저 실행하세요."`
- **And Given** `breakout_init` 또는 `stage1_accumulation` 칩이 렌더링되어 있다
- **When** 사용자가 해당 칩 위에 호버한다 (또는 `title` 속성을 읽는다)
- **Then** 네이티브 툴팁 문자열은 해당 프리셋의 `description` 필드 값과 정확히 일치한다 (DB 안내 문구가 **아니다**).
- **And** 활성/비활성 상태 변화 (클릭 전/후) 에도 툴팁 문자열은 바뀌지 않는다.

### Definition of Done

- [ ] REQ-PST-001 ~ 012 모든 코드 변경 완료
- [ ] AC-1 ~ AC-12 전부 통과
- [ ] Vitest 커버리지 (`frontend/src/presets/**`, `frontend/src/components/FilterBar/PresetChips.tsx`) ≥ 85%
- [ ] Playwright E2E 시나리오 (F1, F2) 통과
- [ ] 백엔드 pytest (E1, E2) 통과
- [ ] TypeScript strict 타입 체크 0 에러
- [ ] ESLint/ruff 경고 0
- [ ] @MX:NOTE 태그 추가 (`PresetChips.tsx`, `applyPatch` 헬퍼)
- [ ] @MX:ANCHOR 태그 (`FilterBar` — fan_in ≥ 3)

---

## 6. Technical Approach (기술 접근)

### 6.1 레지스트리 구조

`frontend/src/presets/filter-presets.ts` 는 다음 구조를 가진다:

```ts
import type { ScreenRequest } from '../types/filter'
import type { Preset } from '../types/filter'

export const FILTER_PRESETS: readonly Preset[] = [
  {
    id: 'minervini_full',
    label: '미너비니 풀',
    description: 'Mark Minervini Trend Template 8조건 엄격 적용...',
    patch: { /* §4.2 */ },
  },
  { id: 'breakout_init', /* ... */ },
  { id: 'stage1_accumulation', /* ... */ },
] as const
```

`as const` 로 불변성을 보장하고, `readonly Preset[]` 타입으로 런타임 변이를 방지한다.

### 6.2 PresetChips 컴포넌트 인터페이스

```ts
interface PresetChipsProps {
  presets: readonly Preset[]
  activePresetId: string | null
  onApply: (preset: Preset) => void   // 비활성 칩 클릭
  onClear: () => void                  // 활성 칩 재클릭
}
```

프리젠테이션 컴포넌트는 상태를 직접 보유하지 않는다. 활성 ID 판정과 상태 변이는 FilterBar 가 담당한다.

### 6.3 `activePresetId` 위치 결정 (로컬 vs 컨텍스트)

| 옵션 | 설명 | 장점 | 단점 |
|------|------|------|------|
| A: FilterBar 로컬 | `FilterBar.tsx` 내부 `useMemo` 로 파생 | 변경 범위 최소, `ScreenContext` 표면 불변 | FilterBar 외부에서 활성 ID 를 사용할 수 없음 |
| B: ScreenContext 확장 | `ScreenContext` 에 `activePresetId` 추가 | 앱 전역에서 활성 ID 접근 가능 | 컨텍스트 API 변경, 테스트 표면 확대 |

**권장**: **옵션 A (FilterBar 로컬)**. v1 에서 활성 ID 를 사용하는 곳은 PresetChips 뿐이므로 컨텍스트 확장은 과설계이다. 향후 다른 컴포넌트 (예: 결과 리스트 헤더) 가 활성 ID 를 필요로 하면 그때 옵션 B 로 리팩터한다.

### 6.4 드리프트 감지 구현

```ts
// FilterBar.tsx 내부

const activePresetId = useMemo<string | null>(() => {
  for (const preset of FILTER_PRESETS) {
    const expected = applyPatch(DEFAULT_SCREEN_REQUEST, preset.patch)
    if (isEqualScreenRequest(filters, expected)) {
      return preset.id
    }
  }
  return null
}, [filters])
```

`isEqualScreenRequest` 는 scalar 필드 동등 + `patterns` 배열 요소 단위 동등 + `pattern_logic` 동등 을 확인한다. 기존 `lodash/isEqual` 의존성이 있으면 사용하고, 없으면 경량 헬퍼를 새로 추가한다.

### 6.5 URL 동기화 구현

```ts
useEffect(() => {
  const params = new URLSearchParams(window.location.search)
  if (activePresetId) {
    params.set('preset', activePresetId)
  } else {
    params.delete('preset')
  }
  const nextQuery = params.toString()
  const nextUrl = `${window.location.pathname}${nextQuery ? `?${nextQuery}` : ''}`
  if (nextUrl !== `${window.location.pathname}${window.location.search}`) {
    window.history.replaceState(null, '', nextUrl)
  }
}, [activePresetId])

// 초기 마운트 시
useEffect(() => {
  const params = new URLSearchParams(window.location.search)
  const id = params.get('preset')
  if (id) {
    const preset = FILTER_PRESETS.find((p) => p.id === id)
    if (preset) {
      applyFilters(applyPatch(DEFAULT_SCREEN_REQUEST, preset.patch))
    }
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [])   // 초기 1회만
```

동일 URL 재기록을 피하기 위해 변경 전후 비교를 수행한다. 초기 마운트 effect 는 `[]` 의존성으로 1회만 실행한다.

### 6.6 스타일 (칩 시각 토큰)

```css
.preset-chips {
  display: flex;
  gap: 8px;
  padding: 8px 0;
  overflow-x: auto;
  scroll-snap-type: x proximity;
}

.preset-chip {
  min-height: 44px;
  padding: 8px 14px;
  border-radius: 999px;
  border: 1px solid var(--color-border-subtle);
  background: var(--color-surface-2);
  color: var(--color-text-primary);
  white-space: nowrap;
  cursor: pointer;
  transition: background 120ms ease, border-color 120ms ease;
}

.preset-chip:hover { background: var(--color-surface-3); }
.preset-chip:focus-visible { outline: 2px solid var(--color-focus-ring); outline-offset: 2px; }

.preset-chip[aria-pressed="true"] {
  background: var(--color-accent-primary);
  color: var(--color-on-accent);
  border-color: var(--color-accent-primary);
}
```

디자인 토큰은 기존 `global.css` 의 변수를 재사용한다. 신규 토큰이 필요하면 디자인 팀과 협의 후 추가한다 (별도 이슈).

### 6.7 MX 태그 계획

| 태그 | 위치 | 이유 |
|------|------|------|
| `# @MX:NOTE` | `filter-presets.ts` 상단 | 레지스트리는 단일 진실 원천이며, 프리셋 추가 시 SPEC 업데이트 필수 |
| `# @MX:NOTE` | `applyPatch` 헬퍼 | patterns 배열 치환 동작이 얕은 병합과 다름을 명시 (A2) |
| `# @MX:ANCHOR` | `FilterBar` | fan_in ≥ 3 (Dashboard, PresetChips, URL effect). `@MX:REASON: 필터 UI 진입점` |
| `# @MX:TODO` | `PresetChips.tsx` 초안 | RED 단계에서 추가, GREEN 에서 제거 |

`code_comments: ko` 설정에 따라 태그 설명은 한국어로 작성한다.

---

## 7. Dependencies (의존성)

### 7.1 Upstream (본 SPEC 이 필요로 하는 선행 요소)

- **SPEC-MINERVINI-001**: `ScreenRequest.minervini_trend_template: bool | None` 필드 도입 및 REQ-MIN-007 (마이그레이션 미적용 환경에서의 200 OK + empty + WARN log) 계약. 본 SPEC 의 `minervini_full` 프리셋과 AC-9 가 이 계약에 의존한다.
- **기존 `ScreenContext`**: `filters`, `applyFilters`, `updateFilters`, `clearResults` API 가 v1 의 사용 패턴을 충족한다.
- **기존 `DEFAULT_SCREEN_REQUEST`**: `applyPatch` 의 기준점으로 사용된다.

### 7.2 Downstream (본 SPEC 이후 가능한 후속 요소)

- **사용자 정의 프리셋 (Save/Load)**: localStorage 기반 커스텀 프리셋, 편집 다이얼로그 등. 본 SPEC 의 `Preset` 타입을 그대로 확장 가능.
- **VCP / 거래량 돌파 프리셋**: SPEC-MINERVINI-001 follow-up 으로 도입될 엔진 기능 이후 프리셋 추가 가능.
- **프리셋 분석 (텔레메트리)**: 사용 빈도 기록 후 UI 정렬 반영.
- **i18n**: 영어/일본어 라벨 추가.

### 7.3 외부 라이브러리

신규 라이브러리 도입 없음. React, TypeScript, Vite, Vitest, React Testing Library, Playwright 만 사용.

---

## 8. Risk Register (리스크와 완화)

| ID | 리스크 | 영향 | 발생 가능성 | 완화책 |
|----|--------|------|-------------|--------|
| R1 | `minervini_full` 프리셋이 SPEC-MINERVINI-001 배포 전 (또는 DB 파일 재생성 실행 전) 에 사용되어 빈 결과 반환 → 사용자 혼란 | 중 | 중 (배포 전환기에 한정) | REQ-PST-012 툴팁 + SPEC-MINERVINI-001 REQ-MIN-007 빈 결과 + 경고 로그 3중 방어. AC-9 (후방 호환) + AC-12 (툴팁 문구) 회귀 방어. SPEC-MINERVINI-001 배포가 DB 파일 전체 재생성을 수반하므로 상시 사용자 경로에서는 드문 상태이며, 전이적 상태에 한정된다 (§1.4 참조). |
| R2 | URL 쿼리 `?preset=` 가 향후 다른 쿼리 파라미터와 충돌 | 저 | 낮음 | `preset` 를 예약 키로 명시 (§4.1). 신규 쿼리 파라미터 추가 시 이 예약을 참조한다. |
| R3 | 드리프트 감지 깊은 동등 비교의 렌더당 비용 | 저 | 낮음 | v1 기준 프리셋 3개 × 필드 ~10개 → 렌더당 ~30 필드 비교. `useMemo` 메모이제이션으로 `filters` 변경 시에만 재계산. 프리셋이 10개 초과로 확장되면 Map 인덱스로 리팩터. |
| R4 | `patterns.max_length` 3→5 확장이 기존 클라이언트를 거부할 가능성 | 고 | 매우 낮음 | 완화 방향 (relaxation) 이므로 기존 0~3 개 요청은 영향 없음. AC-8 의 회귀 케이스로 확인. |
| R5 | URL 에 저장된 5개 patterns 상태가 백엔드 배포 이전에 공유되어 6개로 오염 | 저 | 매우 낮음 | 백엔드는 항상 6개 이상을 거부하므로 안전. URL 공유는 동일 버전 프런트엔드/백엔드를 전제한다. |
| R6 | 모바일 뷰포트에서 칩 바가 가로 overflow → 스크롤 힌트 부재 | 저 | 중 | `overflow-x: auto` + `scroll-snap`. 추가로 오른쪽 fade gradient 를 고려 (선택). AC-11 로 방어. |
| R7 | 사용자가 `patterns` 를 수동으로 5개까지 채운 뒤 프리셋 적용 시 당황 (덮어쓰기) | 중 | 중 | A2 (patterns 배열 완전 치환) 의 결정 사항을 UX 문서에 명시. 필요 시 확인 다이얼로그 옵션 검토 (v2 에서 고려). |
| R8 | `isEqualScreenRequest` 커스텀 구현에서 엣지 케이스 (예: `null` vs `undefined`) | 중 | 낮음 | `lodash/isEqual` 우선 사용. 커스텀 구현 시 C2 (드리프트 테스트) 에서 경계 케이스를 파라미터라이즈. |
| R9 | 초기 마운트 시 `?preset=<id>` 가 유효하지만 해당 필드가 백엔드에 아직 없으면 (예: `minervini_full` + SPEC-MINERVINI-001 미배포) 빈 결과가 즉시 표시됨 | 중 | 낮음 | R1 과 동일 계약 (REQ-MIN-007). UX 상 자동 적용이 오작동처럼 보이지 않도록 로딩 스피너와 결과 카운트 0 메시지를 명확히 표기. |
| R10 | 레지스트리 하드코딩으로 인해 프리셋 추가 시 코드 배포 필요 | 저 | 중 | v1 의도된 제약. 사용자 정의 프리셋은 후속 SPEC 에서 다룬다. |

---

## 9. Test Plan (TDD 접근)

개발 방법론은 **TDD (RED-GREEN-REFACTOR)** 이다 (`development_mode: tdd`).

### 9.1 RED Phase — 실패 테스트 선작성

아래 순서대로 테스트를 먼저 작성하고 **모두 실패함을 확인** 한다.

#### Group A — 레지스트리 (Vitest)

파일: `frontend/src/presets/__tests__/filter-presets.test.ts`

- **A1**: `FILTER_PRESETS` 가 정확히 3개의 원소를 가지며 id 가 `minervini_full`, `breakout_init`, `stage1_accumulation` 이다.
- **A2**: 각 `Preset` 의 `patch` 가 `Partial<ScreenRequest>` 로 할당 가능하다 (타입 테스트는 `// @ts-expect-error` 반증 또는 `tsd` 기반).
- **A3**: `id` 는 유니크하고 `label` 은 비어 있지 않다.

#### Group B — PresetChips UI (React Testing Library)

파일: `frontend/src/components/FilterBar/__tests__/PresetChips.test.tsx`

- **B1**: 3개 칩 버튼이 렌더되고 각각 올바른 라벨을 표시한다.
- **B2**: 비활성 칩 클릭 → `onApply` 가 정확한 `Preset` 인자로 1회 호출된다.
- **B3**: 활성 칩 클릭 → `onClear` 가 1회 호출된다.
- **B4**: 활성 칩 하나는 `aria-pressed="true"`, 나머지는 `"false"`.
- **B5**: Tab 순회 후 Enter 또는 Space 로 칩 활성화 가능 (`userEvent.keyboard`).
- **B6 (v1.0.1 신설, REQ-PST-012)**: 툴팁 `title` 속성 분기 검증.
  - `minervini_full` 칩의 `title` 은 정확히 `"SMA150·52주 고저가·SMA200 추세 컬럼이 필요합니다. DB 업데이트(파일 재생성)를 먼저 실행하세요."` 와 일치한다.
  - `breakout_init` 칩의 `title` 은 `BREAKOUT_INIT.description` 과 일치한다.
  - `stage1_accumulation` 칩의 `title` 은 `STAGE1_ACCUMULATION.description` 과 일치한다.
  - 활성 상태로 전환해도 `title` 문자열은 변하지 않는다 (state-invariant assertion).

#### Group C — FilterBar 통합 (React Testing Library)

파일: `frontend/src/components/FilterBar/__tests__/FilterBar.test.tsx` (신규 또는 확장)

- **C1**: `breakout_init` 칩 클릭 → 폼 필드가 patch 값을 반영하고, `applyFilters` 가 1회 호출된다.
- **C2**: 드리프트 감지 — `minervini_full` 적용 후 RS 입력을 수정 → `activePresetId` = null, 모든 칩 `aria-pressed="false"`.
- **C3**: URL 반영 — 칩 적용 시 `window.history.replaceState` 가 `?preset=<id>` 로 호출된다. 드리프트 시 `preset` 파라미터가 제거된다.
- **C4**: 초기 마운트 자동 적용 — `window.history.replaceState` 로 `?preset=stage1_accumulation` 을 세팅한 상태에서 FilterBar 가 마운트되면 해당 프리셋이 자동 적용된다.

#### Group D — PatternBuilder 한도 (React Testing Library)

- **D1**: 4개 patterns 상태에서 "조건 추가" 버튼이 렌더된다.
- **D2**: 5개 patterns 상태에서 "조건 추가" 버튼이 DOM 에 존재하지 않는다.
- **D3**: 5 → 4 로 제거 후 "조건 추가" 버튼이 다시 렌더된다.

#### Group E — 백엔드 (pytest)

파일: `backend/tests/test_screen.py` (확장) 또는 신규 `test_screen_patterns_limit.py`

- **E1**: `POST /api/screen` with 5 patterns → 200.
- **E2**: `POST /api/screen` with 6 patterns → 422 with Pydantic 검증 에러 상세.

#### Group F — Playwright E2E

파일: `frontend/e2e/preset-flow.spec.ts`

- **F1**: 앱 방문 → "Stage2 돌파" 칩 클릭 → FilterBar 폼 값이 패치를 반영 + 결과 리스트가 업데이트됨 + URL 이 `?preset=breakout_init` 을 포함.
- **F2**: F1 이후 사용자가 RS 값을 80 으로 변경 → 칩 활성 하이라이트 제거 + URL 에서 `preset` 파라미터 제거.

### 9.2 GREEN Phase — 최소 구현

위 테스트가 모두 통과하도록 최소 구현을 작성한다. 본 SPEC 은 코드를 포함하지 않으며, 구현은 `/moai run SPEC-PRESET-001` 단계에서 수행한다.

### 9.3 REFACTOR Phase

- `applyPatch` 와 `isEqualScreenRequest` 를 `frontend/src/presets/utils.ts` 로 추출
- `PresetChips` 의 스타일을 CSS Module 또는 기존 디자인 토큰 체계로 정리
- fixture 공통화 (테스트에서 프리셋 레퍼런스 재사용)
- @MX 태그 추가 (NOTE, ANCHOR)

### 9.4 커버리지 목표

- `frontend/src/presets/**`: 95% 이상
- `frontend/src/components/FilterBar/PresetChips.tsx`: 90% 이상
- `frontend/src/components/FilterBar/FilterBar.tsx` (프리셋 로직 경로): 85% 이상

### 9.5 수동 검증 (Post-Automation)

- 로컬 dev 서버에서 3개 프리셋을 순차 적용하고 결과 리스트가 각 프리셋의 기대 필드를 반영하는지 확인 (시가총액 1000억 이상, RS 70 이상 등).
- URL 을 복사하여 새 탭에 붙여넣고 동일 필터가 자동 적용되는지 확인.
- 모바일 에뮬레이터 (Chrome DevTools 360×640) 에서 칩 바 가로 스크롤 동작 확인.
- `minervini_full` 을 백엔드 배포 전 환경에서 적용하여 빈 결과 + 에러 없음을 확인 (AC-9).

---

## 10. Out of Scope (범위 밖 — 명시)

본 SPEC 은 다음을 **다루지 않는다**. 각 항목은 별도 SPEC 으로 분리된다.

1. **VCP 패턴 자동 감지, 거래량 서지 필터, 시장 환경 필터** — 엔진 확장 후속 SPEC.
2. **사용자 정의 프리셋 (Save/Load/Edit)** — v1 은 하드코딩된 레지스트리 3종만 제공. 커스텀 프리셋은 후속 SPEC 에서 다룬다.
3. **서버 측 프리셋 저장** — 본 SPEC 의 프리셋 로직은 프런트엔드 전용이다. 백엔드는 최종 resolved 된 `ScreenRequest` 만 인지한다.
4. **프리셋 라벨의 i18n** — v1 은 한국어만 지원한다. 영어/일본어/중국어 확장은 후속.
5. **프리셋 사용 빈도 분석 / 텔레메트리** — 후속.
6. **프리셋 그룹핑 / 카테고리 탭** — 프리셋이 10개 이상으로 늘어날 때 도입 고려.
7. **프리셋 간 전환 애니메이션** — UX 개선 후속.
8. **사용자 정의 가능한 임계값 (예: RS 기준 조정)** — SPEC-MINERVINI-001 §10 #9 와 동일한 범위 밖.
9. ~~**"DB 업데이트 필요" 툴팁 배지**~~ — **v1.0.1 에서 REQ-PST-012 로 편입됨** (더 이상 out of scope 가 아님). 네이티브 `title` 속성 기반 구현. 커스텀 팝오버 컴포넌트 도입은 여전히 out of scope (v2 이후 재평가).
10. **PatternCondition 의 새 indicator 추가** — 본 SPEC 은 개수 제약만 완화한다. 새로운 indicator (예: Volume, ATR) 는 별도 SPEC.

---

문서 버전: 1.0.1
작성일: 2026-04-21 (v1.0.0 초안), 2026-04-21 (v1.0.1 결정 반영)
작성자: MoAI (manager-spec)
기반 리서치: `.moai/specs/SPEC-PRESET-001/research.md` v1.0.0 (2026-04-21)
