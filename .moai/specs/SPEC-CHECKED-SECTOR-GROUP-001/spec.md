---
id: SPEC-CHECKED-SECTOR-GROUP-001
title: "Chart Grid 종목 목록 — 체크 탭 섹터 그룹핑"
version: "0.3.0"
status: in-progress
created: 2026-08-17
updated: 2026-08-17
author: manager-spec
priority: P2
phase: "v1.1.0 target"
module: "frontend/src/components/StockList"
lifecycle: spec-anchored
tags: "frontend, react, stocklist, sector, grouping, virtual-list"
related_specs: [SPEC-SECTOR-AGGREGATION-001, SPEC-SECTOR-UX-001]
tier: M
---

# SPEC-CHECKED-SECTOR-GROUP-001: Chart Grid 종목 목록 — 체크 탭 섹터 그룹핑

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 0.3.0 | 2026-08-17 | manager-spec | plan-audit iteration 2 **PASS-WITH-DEBT 0.875**(Δ +0.155) 잔여 6건 정리. **(R1)** `AC-CSG-013` (b) leg가 D1 결함 유형을 그 D1 수정 안에서 재생산하고 있었다 — `StockList.tsx:45`의 `useRef<VariableSizeList | null>`은 **타입 인자**인데 스캔이 인스턴스로 세어, 손대지 않은 트리에서 이미 2건이 나오고 기대값 "정확히 1건"이 처음부터 거짓이었다. `| grep -v 'useRef<'` 추가 후 **실행해 1건을 측정**하고 결함 형태·정정 형태의 출력을 AC에 verbatim 고정. 앵커 정규식(`[[:space:]]*$`) 대안은 같은 1건을 내지만 JSX 줄바꿈이라는 서식 우연에 의존하므로 기각. **(R2)** `전체` 탭 characterization 테스트를 M3 → **M0**으로 이관. M2가 `StockList.tsx`를 건드린 뒤 작성하면 변경 후 상태를 정답으로 고정해 회귀 검출이 무효가 된다 — "제약은 관측자가 아니다"를 AC·plan 양쪽에 명문화하고, 손대지 않은 트리 GREEN을 완료 조건으로, 단독 commit을 rollback 기준점으로 지정. **(R3)** 픽스처 규약 (f)를 **종목 수 → 헤더+종목 총 항목 수 ≤ 15**로 교정. 헤더도 같은 렌더 창을 차지하므로 종목만 세면 10종목×7섹터 같은 적법 픽스처가 조용히 잘렸다 — (f)가 막으려던 실패 그 자체. `AC-CSG-001`·`AC-CSG-006`의 전제와 근거 문단에 헤더 항 반영. **(R4)** `plan.md §H` "AC 16건" → 15건. **(R5)** 교차 참조 2건 정정 — §1.4 단일 `VariableSizeList` 행의 소유 REQ `009` → **`011`**, §2 D-4 합계 항등식 `AC-CSG-005` → **`AC-CSG-006`**. **(R6)** `AC-CSG-016` (b) `Then`이 경로 ①만 서술해 ②를 택한 실행이 서술 밖 경로로 충족되던 문제 — ①을 기본, ②를 문서화된 대체로 명시하고 `Then`을 양 경로에 걸쳐 재기술. |
| 0.2.0 | 2026-08-17 | manager-spec | plan-audit iteration 1 **FAIL 0.72**(Tier M thresh 0.80; testability 0.55) 결함 델타 반영. 요구사항 층·traceability·범위 규율은 건전 판정이라 손대지 않았다. **(D4 — 지시 반려 후 채택)** `REQ-CSG-010`/`AC-CSG-012` **철회**. deps 공백은 실재하나 도달 불가능하다 — 체크 상태 변경 지점 3곳(`StockList.tsx:152`·`:168`, `ChartCell.tsx:358`)이 전부이며 모두 1회 제스처당 1종목만 바꾸므로 `checkedCount`가 항상 함께 바뀐다. 같은 수 교체는 한 `act()` 안에서 컨텍스트를 두 번 구동해야만 연출되며, 그런 테스트는 제품이 아니라 하네스를 검사한다. 근거·재도입 조건은 §2 D-3, 묘비는 §3.5. **(D5)** `REQ-CSG-001`/`002`/`006`을 관측 가능한 행동 서술로 재작성하고 구현 수단(단일 `VariableSizeList` 재사용, "내보내진 순수 함수", Set 분리)을 `plan.md §D`로 이관. **(D10)** `REQ-CSG-005` 태그 `(Where)` → `(While)` — 데이터 필드 결측은 정적 역량 게이트가 아니라 상태다. 총계 15 REQ/16 AC → **14 REQ/15 AC**. `acceptance.md`/`plan.md` 동반 개정(D1·D2·D3·D6·D7·D8·D9·D11). |
| 0.1.0 | 2026-08-17 | manager-spec | 초기 SPEC. `StockList.tsx`의 `체크(N)` 탭을 평면 목록에서 섹터 그룹 목록으로 전환. 설계 결정 4건(접기 상태 격리 / 결측 섹터 / 라이브 재그룹핑 / 헤더 카운트 의미)을 §2·§3에서 명시 해결. **정렬 기준 편차 명시**: 착수 지시는 "locale-aware 오름차순"이었으나, 요구의 본질은 백엔드 `sorted()` 결과와의 **일치**이므로 `localeCompare`가 아니라 **코드포인트 오름차순**을 채택한다(§3.1 REQ-CSG-003 근거). |

---

## 0. BRIEF (Lesson #7 [HARD] 의무 항목)

### 0.1 라이브 사용 가설 + 재평가 체크포인트

| 항목 | 내용 |
| --- | --- |
| 가설 | 사용자는 `전체` 탭에서 섹터 헤더를 훑으며 종목을 체크한다. 체크가 10건을 넘어가면 "내가 지금 어느 섹터에 몰려 있나"를 알고 싶어지는데, 현행 `체크(N)` 탭은 평면 목록이라 그 판단을 머릿속으로 해야 한다. 그룹핑이 들어가면 편중(예: 반도체 8 / 나머지 2)이 한 눈에 보인다. |
| 기대 행동 | ship 후 7일 시점에 (a) 체크 탭을 실제로 열어 보는가, (b) 그룹 헤더를 접어 보는가(=목록이 길어질 만큼 체크를 쌓는가), (c) 편중을 보고 체크를 해제하는 행동이 나오는가. |
| 정량 지표 | **자동 검증 가능 항목만 정량으로 둔다** — 체크 탭 헤더 텍스트와 `전체` 탭 헤더 텍스트의 불일치 **0건**(AC-CSG-011). 마지막 종목 해제 후 잔존 헤더 **0건**(AC-CSG-008). 접힌 그룹의 종목 행 렌더 **0개**(AC-CSG-007). 사용 빈도류 지표는 계측 코드가 없으므로 **정성 지표로만 둔다**(A1 단일 사용자·localhost — 계측 도입은 과설계). |
| 재평가 시점 | ship 후 **7일**에 확인 — ① 체크가 5건 이하일 때도 헤더가 유용한가 아니면 잡음인가, ② 접기 상태가 탭별로 다른 것이 자연스러운가 헷갈리는가(§2 D-1 되돌림 판단 근거), ③ 헤더 카운트가 "체크 수"로 읽히는가 "섹터 전체 수"로 오독되는가. |
| 폐기 조건 | ②에서 탭별 독립 접기 상태가 혼란만 준다면 D-1을 뒤집어 공유 Set으로 되돌린다. 이 경우에도 그룹핑 자체는 유지하며 **후속 amendment**로 처리한다 — SPEC 전체를 폐기하지 않는다. |

### 0.2 성능 baseline + 목표값 [Lesson #7 필수]

본 SPEC은 fetch를 추가하지 않고 Context를 신설하지 않는다. 위험은 **렌더 경로 1곳**(`StockList` 재렌더 시 그룹 재계산)에 한정된다.

| 측정 지점 | baseline (측정 의무) | 목표 |
| --- | --- | --- |
| 체크 탭 전환 → 목록 표시 완료 | 현행 실측 (평면 목록) | 회귀 없음. 체크 50건 기준 +10ms 이내 |
| 체크/해제 1회 → 목록 갱신 | 현행 실측 | 회귀 없음. 그룹 재계산은 O(n log n), n = 체크 수(실사용 상한 수십) |
| `전체` 탭 스크롤 프레임 | 현행 실측 | **불변** — `전체` 경로는 코드 변경 대상이 아니다(REQ-CSG-013) |

**측정 의무**: run 착수 시 baseline을 먼저 측정해 `progress.md §E.2`에 기록한다. 그룹 재계산을 `useMemo`로 감쌀지는 baseline 측정 후 결정한다 — 측정 없이 선제 메모이제이션하지 않는다(과설계 방지).

### 0.3 SPEC ID ↔ UI 요소 매핑 표 [Lesson #7 필수]

| # | UI 요소 | 라벨/텍스트 | 위치 | 신규/변경 |
| --- | --- | --- | --- | --- |
| U1 | 체크 탭 섹터 헤더 | `▼ 내수 > 리조트   4` (화살표 · 섹터명 · 체크 수) | `체크(N)` 탭 목록 내부 | **신규** (핵심 변경) |
| U2 | 체크 탭 섹터 헤더의 접힘 표시 | `▶` / `▼` | U1 좌측 | 신규 (기존 `SectorGroupHeader` 재사용) |
| U3 | 결측 섹터 헤더 | `기타` | U1 위치 | 신규 |

**변경되지 않는 요소** (Lesson #2):

| # | 요소 | 조치 |
| --- | --- | --- |
| K1 | 체크 행(`stock-item--checked`) — 종목명 · 코드 · `x` 해제 버튼 | **불변** |
| K2 | `Export` 버튼 및 복사 동작 | **불변** |
| K3 | `체크된 종목이 없습니다.` 빈 상태 | **불변** |
| K4 | `전체` 탭의 모든 동작 | **불변** (REQ-CSG-013) |
| K5 | `체크(N)` 탭 라벨의 N (전체 체크 수) | **불변** — 헤더 카운트와 의미가 다르다(§2 D-4) |

**시각 우선순위 (위 → 아래)** (Lesson #2):

```
체크(N) 탭:
  1. 섹터 헤더 (섹터명 + 그 섹터의 체크 수)   ← 편중을 읽는 단위
  2. 해당 섹터의 체크 종목 행                  ← 개별 종목
  (헤더 없는 평면 행은 존재하지 않는다 — 모든 행은 어떤 헤더 아래에 있다)
```

### 0.4 rollback 시나리오

| 단계 | 안전 commit 경계 | rollback |
| --- | --- | --- |
| M0 (`전체` 탭 characterization 테스트) | 신규 테스트 파일만, 단독 commit | 삭제로 무해. **구현 커밋과 섞지 않는다** — 이후 어느 커밋이 `전체` 탭을 깼는지 이분 탐색으로 짚기 위한 기준점이다 |
| M1 (그룹 키 헬퍼 신설, 소비자 0) | 신규 파일만 | 삭제로 무해 |
| M2 (`checkedItems` 그룹 목록으로 교체 + 접기 상태 분리) | 단일 commit | revert 시 평면 목록 복귀 |
| M3 (테스트 추가) | 단일 commit | revert 안전 |

**전면 rollback 경계**: M2 직전 commit. M2는 `StockList.tsx` 한 파일 안에서 완결되므로 부분 revert가 아니라 **파일 단위 checkout**으로 되돌린다.

---

## 1. Environment (환경)

### 1.1 현행 구조 (실측, `frontend/src/components/StockList/StockList.tsx`)

| 위치 | 현행 동작 |
| --- | --- |
| L14-16 | `ListItem` 유니온 = `{type:'sector', sector: SectorGroupData}` \| `{type:'stock', stock, globalIndex}` |
| L18-19 | `SECTOR_HEIGHT = 40`, `STOCK_ITEM_HEIGHT = 56` |
| L49-61 | `flatItems`(전체 모드) — `results.sectors`를 순회하며 헤더 삽입 + `collapsedSectors` 반영 |
| **L64-68** | **`checkedItems`(체크 모드) — `Array.from(checkedStocks.values()).map(...)` 평면 목록. 섹터 헤더 없음. 본 SPEC의 결함 지점** |
| L70 | `displayItems = viewMode === 'all' ? flatItems : checkedItems` |
| L75-78 | `getItemSize` — `type === 'sector'` → 40, 그 외 56 |
| L80-91 | `toggleSector` — `collapsedSectors: Set<string>` **단일 state**를 두 탭이 공유 |
| L94-96 | `resetAfterIndex(0)` 효과 — deps `[results, collapsedSectors, viewMode, checkedCount]` |
| L141-159 | 체크 모드 행 렌더 — 인라인 `<div className="stock-item stock-item--checked">` + `x` 해제 버튼. `StockItemRow`를 쓰지 않는다 |
| L209 | `viewMode === 'checked' && checkedCount === 0` → 빈 상태 메시지, 가상 목록 생략 |

### 1.2 데이터 가용성

- `frontend/src/types/stock.ts` — `StockItem`이 `sector_major: string | null` · `sector_minor: string | null`을 이미 보유. `SectorGroup = { sector_name, stock_count, stocks }`.
- `frontend/src/contexts/WatchlistContext.tsx:17` — `checkedStocks: Map<string, StockItem>`가 **StockItem 전체 객체**를 저장한다. 따라서 섹터 필드는 클라이언트에 이미 있다. **백엔드 호출은 필요 없다**(REQ-CSG-012).

### 1.3 백엔드 정본 규칙 [HARD — 재현 대상]

`backend/services/screen_service.py:221-223` 실측:

```python
major = sector_major or "기타"
minor = sector_minor or ""
bucket = f"{major} > {minor}" if minor else major
```

그리고 그룹 방출은 `sorted(sector_map.items())` — 즉 **버킷 문자열의 코드포인트 오름차순**이다.

### 1.4 보존 대상 [HARD — 되돌리면 회귀]

| 항목 | 위치 | 이유 |
| --- | --- | --- |
| `SectorGroupHeader` 컴포넌트 | `StockList/SectorGroup.tsx` | 재사용 대상. `전체` 탭과 시각·접근성(`role="button"`, `aria-expanded`) 동작이 갈라지면 안 된다 |
| 단일 `VariableSizeList` + `getItemSize` | `StockList.tsx:75-78, 212-221` | 가변 높이 메커니즘은 이미 헤더/종목 2종을 처리한다. 두 번째 목록 구현을 만들지 않는다(REQ-CSG-011) |
| 체크 행 인라인 렌더 + `x` 버튼 | `StockList.tsx:141-159` | 본 SPEC의 변경 대상이 아니다(K1) |
| `전체` 탭 `flatItems` 경로 | `StockList.tsx:49-61` | 회귀 금지(REQ-CSG-013) |
| 빈 상태 분기 | `StockList.tsx:209` | 불변(K3) |

### 1.5 개발 방법론

TDD (Vitest + React Testing Library). 기존 테스트 표면: `frontend/src/components/ChartGrid/__tests__/ChartGrid.integration.test.tsx`. `StockList` 전용 테스트 디렉터리는 **아직 없으며** run 단계에서 `frontend/src/components/StockList/__tests__/`를 신설한다.

---

## 2. Assumptions (가정, Lesson #5) — 설계 결정 4건 포함

- **A1 (사용 패턴)**: 단일 사용자(jw), localhost, 데스크탑. 체크 종목 수는 실사용에서 수십 건 규모다. 팀 공유·영속 요구 없음.
- **A2 (세션)**: 체크 목록과 접기 상태는 페이지 새로고침 전까지만 유지된다. localStorage를 도입하지 않는다.
- **A3 (캐시)**: 신규 fetch·캐시 모델 없음. `checkedStocks`가 이미 SSOT다 — 새 모델을 발명하지 않는다(Lesson #5).
- **A4 (결측 필드, Lesson #3 관련)**: `sector_major`가 `null`인 종목이 존재할 수 있다. 프론트는 이 경로를 반드시 렌더할 수 있어야 한다.
- **A5 (모바일, Lesson #1)**: 헤더의 섹터명·카운트는 **본문 상설**이다. hover 뒤에 숨기지 않는다. 접기 토글은 클릭/탭 모두로 동작한다(기존 `SectorGroupHeader`가 이미 그렇다).

### D-1 [결정] 접기 상태는 **탭별로 독립**이다

현행 `collapsedSectors`는 두 탭이 공유하는 단일 `Set<string>`이다. 본 SPEC은 **체크 탭 전용 Set을 분리**한다.

**근거 (공유를 기각하는 이유)**: 공유 시 `전체` 탭에서 스캔 편의로 접어 둔 섹터가 체크 탭에서도 접힌다. 체크 탭은 **5~20건 규모의 큐레이션된 요약 화면**이고, 그 화면에서 항목이 안 보이는 상태는 목적 자체를 무효화한다. 최악의 형태는 `체크(12)`인데 목록이 텅 비어 보이는 화면이며, 이것은 사용자가 원인을 추적할 수 없는 결함 형태다 — 접기 상태는 다른 탭에 있기 때문이다.

**반대 근거(채택하지 않음)**: "같은 섹터를 두 번 접어야 한다"는 조작 비용. 그러나 체크 탭에서 접기 자체가 드문 조작(항목이 적다)이므로 비용이 작고, 위 결함 형태의 비용이 훨씬 크다.

**되돌림 조건**: §0.1 재평가 ②에서 사용자가 탭별 독립이 헷갈린다고 답하면 공유로 되돌린다(amendment).

### D-2 [결정] 결측 섹터는 `기타` 헤더로 모은다

`sector_major`가 `null`/빈 문자열이면 `기타`, `sector_minor`가 `null`/빈 문자열이면 대분류만 쓴다 — §1.3 백엔드 규칙과 **동일**하다. 헤더를 만들지 않고 평면으로 흘리는 처리는 금지한다(모든 행은 어떤 헤더 아래에 있다).

### D-3 [결정] 라이브 재그룹핑은 **파생 계산 + 기존 `checkedCount` deps**로 충분하다 — 시그니처 deps는 도입하지 않는다

그룹 목록은 `checkedStocks`에서 **렌더마다 파생**되므로 체크/해제 즉시 반영된다. 남는 문제는 `VariableSizeList`의 **높이 캐시**뿐이다.

현행 L94-96 효과의 deps는 `[results, collapsedSectors, viewMode, checkedCount]`이며, 마지막 종목 해제 시 `checkedCount`가 바뀌므로 헤더 제거 시나리오는 **덮인다**. `collapsedSectors` 공유 state는 D-1에 따라 체크 탭 전용 Set으로 교체되며, 두 Set 모두 deps에 들어간다.

**기각한 안 — 그룹 구성 시그니처 deps (기록 목적으로 남긴다)**

초판은 "항목 수는 같은데 그룹 구성만 바뀌는 교체(1건 해제 + 다른 섹터 1건 체크)"를 검출하려 정렬된 `섹터명:개수` 시그니처를 deps에 추가하려 했다. **deps 공백 자체는 실재한다** — `checkedCount`만으로는 같은 수의 교체를 검출하지 못한다. 그러나 **그 상태는 사용자에게 도달 불가능하다**:

| 체크 상태 변경 지점 | 1회 제스처당 변화 |
| --- | --- |
| `StockList.tsx:152` `uncheckStock` | 정확히 1종목 |
| `StockList.tsx:168` `toggleStock` (`StockItemRow`) | 정확히 1종목 |
| `ChartGrid/ChartCell.tsx:358` `toggleStock` | 정확히 1종목 |

세 곳이 전부이며 모두 단일 종목만 바꾸므로, 도달 가능한 모든 구성 변경에서 `checkedCount`가 함께 바뀌고 효과가 발화한다. 같은 수의 교체는 **두 mutation을 한 커밋에 배치**해야 성립하는데, 어떤 단일 핸들러도 그것을 만들지 않는다 — 하나의 `act()` 안에서 컨텍스트를 두 번 구동해야만 연출된다. 즉 그 요구를 검사하는 테스트는 제품이 아니라 테스트 하네스를 검사하게 된다.

따라서 **REQ와 AC를 두지 않는다**(§3.7 묘비). 도달 불가능한 상태를 지키는 기계 장치는 검출력 없는 복잡도이며, 여기서는 단순성이 방어보다 우선한다. **재도입 조건**: 다중 종목을 한 번에 토글하는 UI(섹터 일괄 체크, 범위 선택 등)가 생기면 그 SPEC이 이 deps 공백을 함께 해결해야 한다 — 그때는 도달 가능해진다.

### D-4 [결정] 헤더 카운트는 **그 섹터의 체크된 종목 수**다

`전체` 탭 헤더는 `sector.stock_count`(섹터 전체 종목 수)를 쓴다. 체크 탭은 **그 섹터에서 체크된 수**를 쓴다. 두 값은 다르며, 체크 탭에서 유니버스 수를 보여주는 구현은 충족이 아니라 **위반**이다(REQ-CSG-004).

또한 이 카운트의 총합은 탭 라벨 `체크(N)`의 N과 항등이어야 한다(**AC-CSG-006** — 합계 항등식. `AC-CSG-005`는 섹터별 카운트 값 자체를 검사한다) — 이 항등식이 깨지면 어느 한쪽이 종목을 누락한 것이다.

---

## 3. Requirements (요구사항, GEARS)

### 3.1 그룹 구성

#### REQ-CSG-001 (Ubiquitous) — 체크 탭의 그룹 구조

The checked tab **shall** render its list as sector headers followed by that sector's checked stock rows, and **shall not** render any stock row that is not preceded by a header.

- 근거: 헤더 없는 평면 행이 남으면 "모든 종목은 어떤 섹터에 속한다"는 화면 규약이 깨진다.
- 구현 수단(같은 `ListItem` 유니온·같은 단일 `VariableSizeList` 재사용)은 관측 대상이 아니라 제약이다 — `plan.md §D`가 소유한다.
- 검증: AC-CSG-001

#### REQ-CSG-002 (Ubiquitous) — 그룹 키는 백엔드 규칙의 재현

The grouping key **shall** be derived as: `major = sector_major || '기타'`, `minor = sector_minor || ''`, `key = minor ? `${major} > ${minor}` : major` — reproducing `backend/services/screen_service.py:221-223` exactly, and the rule **shall** have exactly one definition site in the frontend.

- 관측 가능한 형태: 키 규칙을 한 곳에서 바꾸면 체크 탭의 모든 헤더 텍스트가 함께 바뀐다(정의 지점이 둘이면 한쪽만 바뀌어 발산한다).
- "내보내진 순수 함수"라는 **구현 수단**은 `plan.md §D`가 소유한다 — 여기서는 정의 지점이 하나라는 **성질**만 요구한다.
- 검증: AC-CSG-002, AC-CSG-003, AC-CSG-011

#### REQ-CSG-003 (Ubiquitous) — 그룹 순서의 결정성

Sector groups **shall** be ordered by ascending **code-point** comparison of the grouping key, matching Python `sorted()` in `screen_service.py:225`.

**`localeCompare`를 채택하지 않는 근거**: 요구의 본질은 "보기 좋은 정렬"이 아니라 **두 탭의 순서 일치**다. 백엔드는 코드포인트 정렬을 방출하므로, 프론트가 로케일 정렬을 쓰면 ASCII·한글 혼재 키에서 두 탭의 순서가 갈릴 수 있고 그 불일치는 조용하다. 코드포인트 비교는 백엔드와 기계적으로 동치이므로 이 위험을 제거한다.

- 검증: AC-CSG-004

#### REQ-CSG-004 (Ubiquitous) — 헤더 카운트의 의미

Each checked-tab sector header **shall** display the number of **checked** stocks in that sector — NOT the sector's universe `stock_count` (§2 D-4).

- 검증: AC-CSG-005, AC-CSG-006

#### REQ-CSG-005 (While) — 결측 섹터

While a checked stock's `sector_major` is null or empty, it **shall** appear under a `기타` header; while its `sector_minor` is null or empty, the header **shall** show the major name alone (§2 D-2).

> 초판은 이 요구를 `(Where)`로 태그했으나 `Where`는 **역량 게이트 / 기능 플래그 / 정적 설정**을 뜻한다. 데이터 필드의 결측은 정적 역량이 아니라 **상태**이므로 `While`이 맞다.

- 검증: AC-CSG-003

### 3.2 접기 상태

#### REQ-CSG-006 (Ubiquitous) — 탭별 독립 접기 상태

The checked tab's collapse state **shall** be independent of the all tab's: collapsing a sector in either tab **shall not** change that sector's collapse state in the other (§2 D-1).

- 근거: 두 탭이 하나의 Set을 공유하면 `전체` 탭에서 접어 둔 섹터 때문에 `체크(N)`이 비어 보이는 화면이 만들어진다(§2 D-1).
- 검증: AC-CSG-009, AC-CSG-010 (양방향 각각 관측)

#### REQ-CSG-007 (When) — 헤더 토글

When the user clicks (or presses Enter on) a checked-tab sector header, that sector's stock rows **shall** collapse or expand, and the header's arrow **shall** switch between `▶` and `▼` — reusing `SectorGroupHeader` unchanged.

- 검증: AC-CSG-007

#### REQ-CSG-008 (While) — 접힌 그룹의 렌더 부재

While a checked-tab sector is collapsed, its stock rows **shall not** be present in the rendered list (not merely hidden by CSS), and the header **shall** remain visible with its count intact.

- 검증: AC-CSG-007

### 3.3 라이브 갱신

#### REQ-CSG-009 (When) — 마지막 종목 해제 시 헤더 제거

When the last checked stock of a sector is unchecked, that sector's header **shall** disappear in the same render — no stale-header frame (§2 D-3).

- 검증: AC-CSG-008

### 3.4 재사용·보존

#### REQ-CSG-011 (Unwanted Behavior) — 두 번째 목록 구현 금지

The implementation **shall not** introduce a second list component, a second virtualization library, a new dependency, or a duplicate sector-header component. `SectorGroupHeader` and the existing `VariableSizeList` are reused (§1.4).

- 검증: AC-CSG-013

#### REQ-CSG-012 (Unwanted Behavior) — 백엔드 변경 금지

The implementation **shall not** add an API endpoint, change a response schema, or issue any network request for grouping. `checkedStocks` already carries the sector fields (§1.2).

- 검증: AC-CSG-014

#### REQ-CSG-013 (Ubiquitous) — `전체` 탭 회귀 금지

The all tab's grouping, ordering, header counts (`sector.stock_count`), collapse behavior, and selection/scroll-sync **shall** remain unchanged.

- 검증: AC-CSG-015

#### REQ-CSG-014 (Ubiquitous) — 체크 행·Export·빈 상태 불변

The checked row rendering (name, code, `x` uncheck button), the `Export` button behavior, and the `체크된 종목이 없습니다.` empty state **shall** remain unchanged (K1·K2·K3).

- 검증: AC-CSG-016

#### REQ-CSG-015 (Ubiquitous) — 크로스탭 섹터명 동일성

For any checked stock that also appears in `results.sectors`, the header text under which it renders in the checked tab **shall** be byte-identical to the `sector_name` of the backend group that contains it.

- 이 단언의 한 변은 **서버 응답 문자열**에서 와야 한다. 양변이 프론트 헬퍼에서 오면 항진명제다(Lesson #9).
- 검증: AC-CSG-011

### 3.5 철회된 요구사항 (묘비)

> 번호를 재사용하지 않고 철회 사실을 남긴다.

#### ~~REQ-CSG-010~~ — 높이 캐시 무효화용 그룹 시그니처 deps **[철회 — 도입하지 않는다]**

**결정 (2026-08-17, plan-audit iteration 1 D4)**: 초판은 `resetAfterIndex(0)` 효과의 deps에 그룹 구성 시그니처를 추가하도록 요구했다. **deps 공백은 실재하지만 그 상태가 사용자에게 도달 불가능하다** — 근거와 재도입 조건은 §2 D-3에 전문 기록.

- 함께 삭제되는 산출물: `AC-CSG-012`(결번), `plan.md §F` M2의 시그니처 deps 항목.
- **AC-CSG-012는 결번이며 재사용하지 않는다** — 번호를 돌려쓰면 이력 추적이 끊긴다.
- 도달 불가능한 상태를 지키는 기계 장치는 검출력 없는 복잡도다. 이 SPEC에서 유일한 사변적 장치였다.

---

## 4. Exclusions (What NOT to Build)

### Out of Scope — 백엔드

- 신규 API 엔드포인트·응답 스키마 변경·집계 로직 변경: 없다. 프론트는 이미 가진 필드만 쓴다.
- `screen_service.py`의 버킷 규칙 수정: 없다. 본 SPEC은 그 규칙을 **재현**할 뿐이며, 규칙을 바꾸면 두 탭이 함께 바뀌어야 하므로 별도 SPEC이다.

### Out of Scope — 기능 확장

- **체크 탭 정렬 옵션**(섹터 수 내림차순, RS순 등): 없다. 순서는 REQ-CSG-003 하나로 고정한다.
- **섹터 단위 일괄 해제** (헤더에서 그 섹터 전부 언체크): 없다. 헤더는 접기 전용이다.
- **섹터 비중 요약·편중 경고 배지**: 없다. 편중은 헤더 카운트를 눈으로 읽어 판단한다.
- **체크 목록의 localStorage 영속**: 없다 (A2).
- **`전체` 탭의 그룹 구조 변경**: 없다 (REQ-CSG-013).
- **중분류(`sector_minor`) 단위 필터·드릴다운**: 없다. 중분류는 그룹 키의 일부로만 쓴다.

### Out of Scope — 구현 수단

- 신규 가상 스크롤 라이브러리·신규 npm 의존성: 도입하지 않는다 (REQ-CSG-011).
- 외부 상태 라이브러리(Redux/Zustand/Jotai): 도입하지 않는다. `useState` 하나로 충분하다.
- 그룹 계산의 서버 위임: 하지 않는다 (REQ-CSG-012).

### Out of Scope — 섹터 지표 SPEC과의 관계

- `SPEC-SECTOR-AGGREGATION-001` / `SPEC-SECTOR-UX-001`은 **섹터 지표 집계·섹터 분석 화면** SPEC이며 본 SPEC과 코드 중첩이 없다. 공유하는 것은 분류 체계(taxonomy)뿐이다. 두 SPEC을 확장하지 않으며 그 AC를 참조하지도 않는다.

---

## 5. Specifications (수용 기준 연결)

### Traceability (REQ ↔ AC) — REQ 단위

| REQ | AC | 비고 |
| --- | --- | --- |
| REQ-CSG-001 | AC-CSG-001 | 그룹 구조 존재 |
| REQ-CSG-002 | AC-CSG-002, AC-CSG-003, AC-CSG-011 | 키 규칙 |
| REQ-CSG-003 | AC-CSG-004 | 코드포인트 순서 |
| REQ-CSG-004 | AC-CSG-005, AC-CSG-006 | 카운트 의미 + 항등식 |
| REQ-CSG-005 | AC-CSG-003 | `기타` 경로 |
| REQ-CSG-006 | AC-CSG-009, AC-CSG-010 | 접기 격리 |
| REQ-CSG-007 | AC-CSG-007 | 토글 동작 |
| REQ-CSG-008 | AC-CSG-007 | 접힘 = 렌더 부재 |
| REQ-CSG-009 | AC-CSG-008 | 헤더 즉시 제거 |
| ~~REQ-CSG-010~~ | ~~AC-CSG-012~~ | **철회** — 도달 불가 상태 (§2 D-3, §3.5) |
| REQ-CSG-011 | AC-CSG-013 | 재사용 강제 (2-leg: 헤더 중복 + 두 번째 목록) |
| REQ-CSG-012 | AC-CSG-014 | 네트워크 0 |
| REQ-CSG-013 | AC-CSG-015 | `전체` 회귀 금지 |
| REQ-CSG-014 | AC-CSG-016 | 행·Export·빈 상태 불변 |
| REQ-CSG-015 | AC-CSG-011 | 크로스탭 동일성 |

AC 정의는 `acceptance.md`가 SSOT다. **총 14 REQ / 15 AC** (Tier M 상한 16/16 이내). `REQ-CSG-010`·`AC-CSG-012`는 철회 결번이며 총계에 포함하지 않는다.

---

## 6. 의존 관계

- **선행 SPEC**: 없다. `checkedStocks`와 `sector_major/minor`는 이미 출하돼 있다.
- **차단 요소**: 없다. 착수 가능.

---

## 7. 미결 사항 (SPEC 레벨 open questions)

| ID | 사항 | 상태 |
| --- | --- | --- |
| **O-C1** | 체크가 3건 이하일 때 헤더가 정보 대비 잡음일 가능성 | **의도적 미결** — 임계치 기반 조건부 헤더는 "언제 헤더가 나타나는가"라는 새 규칙을 낳고, 그 규칙 자체가 혼란원이다. 무조건 헤더를 채택하고 §0.1 재평가 ①에서 사용자에게 확인한다. |
| **O-C2** | 헤더 카운트와 탭 라벨 `체크(N)`의 의미 차이가 오독되는가 | **의도적 미결** — 라벨 문구 변경(예: `반도체 4/12`)은 유니버스 수를 다시 끌어와야 하고, 체크 탭에는 그 값이 없다(체크된 종목만 보유). 현행 단순 카운트로 ship하고 §0.1 재평가 ③에서 확인한다. |
