# SPEC-CHECKED-SECTOR-GROUP-001 — Implementation Plan

Tier **M** · 방법론 **TDD** (Vitest + React Testing Library) · Route A (Hybrid Trunk main-direct)

---

## §A Context

| 항목 | 값 |
| --- | --- |
| 프로젝트 루트 | `/Users/byunjungwon/Dev/my-project-01/my_chart` |
| 변경 범위 | `frontend/` 전용. 백엔드·스키마·API 변경 없음 |
| 주 변경 파일 | `frontend/src/components/StockList/StockList.tsx` |
| 신설 파일 | `frontend/src/components/StockList/sectorKey.ts` (그룹 키 + 그룹 빌더 순수 함수), `frontend/src/components/StockList/__tests__/StockList.alltab.characterization.test.tsx` (**M0 — 변경 전 트리에서 작성**), `frontend/src/components/StockList/__tests__/StockList.grouping.test.tsx` |
| PRESERVE | `SectorGroup.tsx`(불변) · `StockItem.tsx`(불변) · `WatchlistContext.tsx`(불변) · `StockList.tsx`의 `flatItems` 경로·체크 행 렌더·Export·빈 상태 분기 |
| SPEC 산출물 | `.moai/specs/SPEC-CHECKED-SECTOR-GROUP-001/{spec,plan,acceptance,progress}.md` |

---

## §B Known Issues (도메인 필터 적용 — 프론트 전용)

| # | 항목 | 조치 |
| --- | --- | --- |
| B-1 | **항진명제 대조 단언** (Lesson #9) | AC의 되돌림을 실제 적용해 RED를 관측한다. 단언 양변이 같은 함수에서 오면 무효 — AC-CSG-011의 기대값은 서버 픽스처에서 추출한다 |
| B-2 | **접기 상태 공유 회귀** | 두 탭 state 분리는 AC-CSG-009/010의 양방향 되돌림 관측이 유일한 방어선이다. 한 방향만 관측하면 반대 방향이 열린다 |
| B-3 | **default 진입 가시성** (Lesson #3) | 체크 탭에 들어가면 추가 조작 없이 헤더가 보여야 한다. 임계치 조건부 헤더를 넣지 않는다(§7 O-C1) |
| B-4 | **정렬 우연 통과** | 어긋나게 만들어야 하는 축은 배열 순서가 아니라 **종목을 체크하는 순서**다(그룹핑 입력 = `Map` 반복 = 체크 시각 순서, `StockList.tsx:64`) |
| B-11 | **관측자 부재** | `StockList` 행동을 보는 테스트가 트리에 0건이다(`AppContent.test.tsx:25-27`이 목킹). 회귀 AC는 관측자를 **먼저 만들어야** 되돌림이 RED를 낼 수 있다 |
| B-12 | **jsdom 렌더 창 고정** | `test-setup.ts`의 `ResizeObserver` 스텁이 no-op이라 `listHeight`가 600에 고정된다 → DOM 행/헤더를 세는 단언은 픽스처가 ≈11행을 넘으면 조용히 틀린다 |
| B-13 | **셸 이식성** | 기본 셸 zsh에서 인용 없는 `--include=*.tsx`는 grep에 닿기 전에 중단된다. 패턴 인용 + 실행 셸 기록 |
| B-5 | **카운트 되돌림 무력화** | 픽스처의 유니버스 수와 체크 수가 우연히 같으면 AC-CSG-005의 되돌림이 통과한다. 최소 한 섹터에서 달라야 한다 |
| B-6 | **커버리지 미측정** | DoD 게이트인데 측정도 §Gaps 기재도 없이 지나간 선례가 있다. 측정 명령과 수치를 §E.2에 남긴다 |
| B-7 | **frontmatter status 보정** (Lesson #6) | 구현 완료 커밋에서 `status: draft → in-progress`, sync 커밋에서 `→ completed` |
| B-8 | **AskUserQuestion 금지** | 서브에이전트는 사용자에게 직접 묻지 않는다. 막히면 구조화된 blocker 보고를 반환한다 |
| B-9 | **커밋·푸시 직접 수행** | Route A. Conventional Commits (`feat(SPEC-CHECKED-SECTOR-GROUP-001): M{N} ...`). `--no-verify` 금지 |
| B-10 | **범위 밖 파일 금지** | `.moai/state/*`, `.moai/cache/*`, 타 SPEC 디렉터리, 무관 untracked 파일을 커밋에 넣지 않는다. `git add`는 경로 명시 |

---

## §C Pre-flight

> **[HARD] 실행 셸**: 아래 명령은 **bash 기준**이다. 이 저장소 기본 셸은 zsh이고, 인용하지 않은 `--include=*.tsx`는 zsh가 grep보다 먼저 전개해 `no matches found`로 **중단**시킨다(실측 확인). 패턴은 항상 인용한다. `bash -n`은 문법만 보므로 이 문제를 잡지 못한다 — 반드시 실제 실행해 exit code를 관측하고, 어느 셸에서 실행했는지 기록한다.

```bash
git branch --show-current && git rev-parse HEAD
cd frontend && npx tsc --noEmit 2>&1 | tail -20   # 기존 오류 baseline (NEW 구분용)
cd frontend && npx vitest run 2>&1 | tail -20      # 기존 통과 수 baseline
ls frontend/src/components/StockList/              # PRESERVE 대상 확인

# 헤더 마크업 현행 위치 (패턴 인용 필수)
grep -rn "sector-header" frontend/src/components --include='*.tsx'

# 목록 인스턴스 현황 — (b) leg baseline
grep -rn "<VariableSizeList\|<FixedSizeList" frontend/src/components --include='*.tsx'

# StockList 를 관측하는 테스트가 존재하는가 (AC-CSG-015 전제 확인)
grep -rln "StockList" frontend/src --include='*.test.tsx'
grep -n "vi.mock..\.\./StockList" frontend/src/components/__tests__/AppContent.test.tsx
```

**추가 baseline — `exportText` (AC-CSG-016(b))**: 고정 픽스처에 대한 `exportText` 값을 구현 **전에** 포착해 `progress.md §E.2`에 verbatim 기록한다. 포착하지 않을 경우 AC-CSG-016(b)는 기대 문자열 리터럴 고정(①안)으로 처리하며, **둘 중 하나는 반드시 한다** — 하지 않으면 그 단언은 "어떤 문자열인가가 복사됐다"로 퇴화한다.

---

## §D Constraints [DO NOT VIOLATE]

- 백엔드 파일·스키마·엔드포인트를 건드리지 않는다.
- `package.json` / `package-lock.json`을 변경하지 않는다(신규 의존성 0).
- `SectorGroupHeader`를 복제하지 않는다. 헤더 마크업(`className="sector-header"`)은 `SectorGroup.tsx` 한 곳에만 존재한다.
- 두 번째 목록/가상화 구현을 만들지 않는다. `StockList/` 안의 `<VariableSizeList>` 인스턴스는 **정확히 1개**(`StockList.tsx:212`)를 유지한다.
- `전체` 탭의 `flatItems` 경로를 수정하지 않는다(REQ-CSG-013).
- `AppContent.test.tsx`의 `vi.mock('../StockList/StockList', ...)`을 수정하거나 제거하지 않는다 — 그 목킹은 그 테스트의 정당한 격리 수단이다. `StockList` 관측자는 `StockList/__tests__/` 아래에 신설한다.
- 되돌림 실증 후 반드시 트리를 복원하고 `git status --short`로 증명한다.

### §D.1 구현 수단 제약 (REQ에서 이관 — spec.md v0.2.0 D5)

아래는 **관측 대상 행동이 아니라 구현 수단**이므로 REQ가 아니라 여기서 강제한다. 대응 REQ는 행동만 규정한다.

| 제약 | 대응 REQ (행동) |
| --- | --- |
| 그룹 키 규칙은 **하나의 내보내진 순수 함수**(`sectorKey.ts`)로 정의하고, 컴포넌트 안에 인라인으로 다시 적지 않는다 | REQ-CSG-002 (정의 지점이 하나라는 성질) |
| 체크 탭 헤더는 기존 `ListItem` 유니온과 **단일 `VariableSizeList`**를 재사용한다 | REQ-CSG-001 (헤더 없는 평면 행 부재) |
| 접기 상태는 `collapsedSectors`와 **별개의 state**로 보유하며, 두 Set이 합쳐지지 않는다 | REQ-CSG-006 (탭 간 전파 없음) |
| `resetAfterIndex(0)` 효과 deps는 기존 `[results, collapsedSectors, viewMode, checkedCount]` + 체크 탭 접힘 Set으로 **한정**한다. 그룹 시그니처 deps는 **추가하지 않는다** | (해당 REQ 없음 — `spec.md §3.5` 철회) |

---

## §E Self-Verification

각 항목은 (a) 실행 명령 (b) verbatim 출력 (c) `(this run, this tree)` + HEAD SHA를 함께 기록한다.

| # | 항목 | 명령 |
| --- | --- | --- |
| E1 | AC PASS/FAIL 매트릭스 (15건, AC-CSG-012 결번) | `npx vitest run src/components/StockList` |
| E2 | 되돌림 실증 RED 관측 (AC별) | 되돌림 주입 → 테스트 실행 → 실패 출력 캡처 → 복원 |
| E3 | 트리 복원 증명 | `git status --short` |
| E4 | 커버리지 (≥85%) | `npx vitest run --coverage src/components/StockList` |
| E5 | 타입 체크 신규 오류 0 | `npx tsc --noEmit` (baseline과 대조) |
| E6 | 전체 스위트 회귀 0 | `npx vitest run` |
| E7 | 정적 스캔 (AC-CSG-013, 3-leg) | grep 2종(`--include='*.tsx' --exclude-dir=__tests__`) + `git diff --stat -- frontend/package*.json`. **exit code + 실행 셸 이름 기록 의무** |
| E8 | 성능 baseline·측정치 | §0.2 표 3행 |
| E9 | 커밋 SHA + 푸시 결과 | `git log --oneline -N`, `git push` |

---

## §F Milestones

> **되돌리기 어려운 결정을 먼저 배치한다.** M1~M2는 데이터 모델과 상태 소유권을 확정하므로 여기서 방향이 틀리면 이후 전부를 다시 짠다. M4의 되돌림 실증은 기계적이지만 **DoD의 실질 게이트**이므로 생략 불가다.
>
> **M0만은 예외적으로 순서가 강제된다** — 되돌리기 난도가 아니라 **관측 시점** 때문이다. characterization 테스트는 변경 전 트리에서만 의미가 있으므로 어떤 구현 작업보다 먼저 와야 한다.

### M0 — `전체` 탭 characterization 테스트 (손대지 않은 트리에서 먼저 통과시킨다)

> **[HARD] 순서가 이 마일스톤의 전부다.** characterization 테스트는 **변경 전 행동을 고정**하는 장치다. M2가 `StockList.tsx`를 건드린 뒤에 작성하면 M2가 만들어 낸 상태를 고정하게 되고, M2가 이미 `전체` 탭 행동을 바꿔 놓았다면 테스트는 **망가진 상태를 정답으로 박아 넣는다** — 회귀 검출이라는 목적 자체가 무효가 된다. `§D`의 "`flatItems` 경로를 수정하지 않는다" 제약은 노출을 줄이지만 닫지는 못한다: **제약은 관측자가 아니다.**

- `StockList/__tests__/StockList.alltab.characterization.test.tsx` 신설. 최소 3항 — (i) 헤더 카운트 = 유니버스 `sector.stock_count`, (ii) 그룹 순서 = `results.sectors` 순서, (iii) 헤더 토글 시 해당 그룹만 접힘.
- **완료 조건**: 이 테스트가 **아직 아무것도 바꾸지 않은 트리**에서 GREEN이어야 한다. 여기서 실패하면 그것은 테스트 결함이지 구현 결함이 아니므로, M1로 넘어가기 전에 테스트를 고친다.
- 단독 커밋으로 남긴다(구현 커밋과 섞지 않는다) — 이후 어떤 커밋이 `전체` 탭을 깼는지 이분 탐색으로 짚을 수 있다.
- `AppContent.test.tsx`의 목킹은 건드리지 않는다(§D).
- 검증: AC-CSG-015 전반부(관측자 존재). 되돌림 실증은 M4.

### M1 — 그룹 키·그룹 빌더 순수 함수 (되돌리기 가장 어려움: 데이터 모델)

- `sectorKey.ts` 신설: `sectorKeyOf(stock: StockItem): string` — 백엔드 규칙(`spec.md §1.3`) 재현.
- `buildCheckedGroups(stocks: StockItem[]): { sectorName: string; stocks: StockItem[] }[]` — 키로 버킷팅 후 **코드포인트 오름차순** 정렬.
- 소비자 0인 상태로 커밋 → rollback 무해.
- RED 먼저: `sectorKey.test.ts`로 키 규칙·정렬·결측 경로를 단위 검증(AC-CSG-002/003/004의 단위 층).
- 검증: AC-CSG-002, AC-CSG-003, AC-CSG-004

### M2 — 상태 소유권 확정: 접기 state 분리 + `checkedItems` 교체 (되돌리기 어려움: UX 계약)

- `collapsedCheckedSectors` state 신설. `toggleSector`를 활성 탭에 따라 해당 Set을 갱신하도록 분기(또는 탭별 토글 핸들러 2개 — 구현자 판단, 단 두 Set이 절대 합쳐지지 않을 것).
- `checkedItems`를 `buildCheckedGroups` 기반 `ListItem[]`(헤더 + 종목)으로 교체. 헤더의 `stockCount`는 **그 그룹의 체크 수**를 전달한다.
- `Row` 렌더러: 헤더 분기에서 활성 탭에 맞는 접힘 Set을 조회하고 맞는 토글을 호출한다. 체크 행 렌더(L141-159)는 **손대지 않는다**.
- `resetAfterIndex` 효과 deps에 **체크 탭 접힘 Set만** 추가한다. 그룹 시그니처 deps는 **추가하지 않는다**(`spec.md §2 D-3` — 도달 불가 상태).
- 검증: AC-CSG-001, AC-CSG-005, AC-CSG-006, AC-CSG-007, AC-CSG-008, AC-CSG-009, AC-CSG-010

### M3 — 통합 테스트 + 크로스탭 파리티

> `전체` 탭 characterization 테스트는 **M0으로 이관**했다(변경 전 트리에서 통과해야 하므로). 여기서는 신규 행동만 검증한다.

- `StockList.grouping.test.tsx`: `acceptance.md` 픽스처 규약 (a)~(f) 전부 준수 — 특히 **(d) 체크 순서 축**(그룹핑 입력은 `Map` = 체크 시각 순서이지 `results.sectors` 순서가 아니다)과 **(f) 헤더+종목 총 15항목 이하**(jsdom `ResizeObserver` 스텁 때문에 `listHeight`가 600에 고정되고, **헤더도 같은 창을 차지하므로** 종목 수만 세면 섹터가 많을 때 조용히 잘린다).
- AC-CSG-011은 기대값을 **서버 응답 픽스처의 `sector_name`에서 런타임 추출**한다.
- AC-CSG-006의 파생 모델 층 단언(`buildCheckedGroups` 합 = `checkedStocks.size`)은 렌더 창·접힘과 무관하므로 별도 단위 테스트로 둔다.
- AC-CSG-014(fetch 0), AC-CSG-016(불변 항목 + `exportText` 기대값 고정) 포함.
- 검증: AC-CSG-006(모델 층), AC-CSG-011, AC-CSG-014, AC-CSG-016

### M4 — 되돌림 실증 + 정적 스캔 + 회귀 (기계적이나 게이트)

- 각 AC의 되돌림을 순차 주입 → RED verbatim 캡처 → 복원 → `git status --short`.
- AC-CSG-004의 `localeCompare` 변형은 결과가 동일하면 **비게이팅**으로 명시한다(1차 게이팅 되돌림인 "정렬 제거"는 그대로 유지).
- AC-CSG-013 정적 스캔 **3-leg**: 문법은 `bash -n`으로, 동작은 **실제 실행**으로 각각 검증하고 exit code + 실행 셸 이름을 기록한다(zsh glob 선전개는 `bash -n`이 못 잡는다).
- AC-CSG-015 전체 스위트 회귀 + **M0** characterization 테스트를 표적으로 한 되돌림 실증(`전체` 탭 카운트 → 체크 수 변형에서 (i)이 RED).
- 커버리지 측정(≥85%).
- 검증: AC-CSG-013, AC-CSG-015 + DoD 전 항목

---

## §G Anti-Patterns (이 SPEC에서 특히 경계)

- 그룹 계산을 `useMemo`로 선제 감싸기 — baseline 측정 전 최적화는 과설계다(§0.2).
- 체크 수가 적을 때 헤더를 숨기는 조건부 로직 — §7 O-C1에서 명시적으로 기각했다.
- 헤더에 "섹터 전체 해제" 버튼 추가 — §4 Exclusions.
- `전체` 탭 코드를 "김에" 정리하기 — REQ-CSG-013 위반.
- 되돌림을 적용하지 않고 "대조 단언 N종 GREEN"으로 기록 — Lesson #9가 정확히 이 형태를 금지한다.

---

## §H Cross-References

- `spec.md §1.3` — 백엔드 정본 규칙(`screen_service.py:221-225`)
- `acceptance.md` — AC **15건** SSOT + 되돌림 의무 (`AC-CSG-012` 철회 결번)
- Lessons `#1`(라이브 검증) `#2`(시각 우선순위) `#3`(default 진입 가시성) `#5`(가정·캐시 모델) `#6`(status 보정) `#7`(BRIEF 3항목) `#9`(대조 단언 판정 기준)
- `SPEC-SECTOR-AGGREGATION-001` / `SPEC-SECTOR-UX-001` — 분류 체계만 공유. 코드 중첩 없음. 확장 대상 아님
