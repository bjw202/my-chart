# SPEC-SECTOR-UX-001 Plan — 구현 계획

> 마일스톤은 **되돌리기 어려운 결정 순**. 상태 소유권·타입 계약을 앞에, 차트 세부 튜닝을 뒤에 둔다.

---

## 0. 착수 전 차단 항목 (BLOCKING)

| ID | 사항 | 상태 | 차단 대상 |
| --- | --- | --- | --- |
| ~~②의 close~~ | `SPEC-SECTOR-AGGREGATION-001` `status: completed` | **해결 (2026-08-14)** — v0.5.0 `completed`, sync commit `13d74d0`, main `65dfe2d`. AC-SAG-037 Gap도 `b703dc2`로 종결 | 차단 해제 |
| ~~**O-U9 / ②의 O-A7**~~ | 최소 구성수 5(AG-5)가 Bump에도 적용되는가 | **해결 (2026-08-14 사용자 결정)** — **미적용 확정**. ②의 출하 구현이 이미 미적용이므로 백엔드 변경 없음 | M4·M7 차단 해제. AC-SUX-019 / AC-SUX-056 R5의 범위를 Table·섹터 Bubble·RRG로 한정 + Bump 반대 방향 단언 신설 |

**2026-08-14 기준 — run 착수 차단 항목이 전부 해소됐다.** `blocking_before_run: []`. 단, 본 개정으로 plan-artifact hash가 바뀌었으므로 `/moai run` Phase 1의 **plan-audit는 재실행이 필수**다(v0.3.0 PASS 0.87은 skip 근거로 무효).
| ~~O-U4~~ | 크기 범례 값 산출 | **해결** — 기간별 고정 눈금 (1W 100억/1,000억/1조 · 1M 500억/5,000억/5조 · 3M 1,000억/1조/10조) | M5 차단 해제 |
| ~~O-U6~~ | `focusStock` 수신 시 차트 그리드 동작 | **해결** — 있으면 스크롤·하이라이트, 없으면 추가. **교체 금지** | M3 차단 해제 |
| ~~O-U7~~ | 종목 표 12열의 좁은 화면 처리 | **해결** — 섹터비중 → Vol배 → 52W고 순 접기. 기간 3열·Stage·RS·Name 불변 | M4 차단 해제 |
| ~~O-U1~~ | RRG/Bump 기간 토글 비활성 vs 숨김 | **해결(잠정)** — 비활성 + 툴팁. §0.1 재평가 시점 ③에서 재확인 | M4 차단 해제 |

---

## 1. [HARD] 결정 사항

| # | 결정 | 선택 | 근거 |
| --- | --- | --- | --- |
| D1 | 상태 관리 | **React Context 2개 + 로컬 `useState`**. 외부 라이브러리 무도입 | 02 §3.3 소유권 표를 만족하면 구현 자유. 의존성 추가는 이 규모에 과설계 |
| D2 | **Context 분리** | `AnalysisParamsContext`와 `SelectionContext`를 **합치지 않는다** | 기간 변경이 섹터 선택 소비자를 리렌더시키면 §0.2 리렌더 목표를 못 맞춘다 |
| D3 | `NavIntent` 소비 | 소비자 로컬 `lastHandledId` + `useEffect` 3조건 가드 | 전역 clear 경쟁(ST-2)의 구조적 제거 |
| D4 | 캐시 계층 | Context 내부 `Map<queryKey, {data, at}>` + TTL 1h. React Query 등 무도입 | Lesson #5 — `MarketContext` 기존 패턴 확산. 학습 비용 0 |
| D5 | 기간 값 표기 | `'1w' | '1m' | '3m'` 단일화. 응답 키(`w1/m1/m3`)는 변환 계층에서 흡수 | CT-12 |
| D6 | 셀 상태 렌더 | 공용 `MetricCell` 컴포넌트 1개로 5상태 전부 처리 | 화면마다 다른 표기를 막는 구조적 보장 (ER-1) |
| D7 | 버블 크기 | 공용 유틸 `bubbleRadius(v, vMin, vMax, rMin, rMax)` 1개를 두 차트가 공유 | 두 차트가 다른 공식을 쓰면 크기 비교가 무의미 |
| D8 | 색상 채널 | **변경 없음** — `StockBubbleChart.tsx:32-61` 그대로. Stage는 테두리로만 | `SPEC-SECTOR-MINOR-COLOR-001` + `@MX:ANCHOR` 보존 |

---

## 2. 마일스톤 (되돌리기 어려운 순)

### M1 — Context 신설 (소비자 0, 무해)

- `AnalysisParamsContext` / `SelectionContext` 생성 + Provider 배치 (D1, D2)
- 쿼리 키 + TTL 캐시 유틸 (D4)
- RED: AC-SUX-001, 002, 034
- **이 시점까지 기존 화면은 전혀 바뀌지 않는다** — rollback 무해

### M2 — 토글 단일화 (사용자 체감 첫 변화)

- 헤더에 기간·시장 토글 단일 인스턴스 배치, Table/Bubble 로컬 토글 제거 (X1, X2)
- 기간 표기 단일화 (D5)
- RED: AC-SUX-008, 009
- 시장 토글의 실제 파라미터 전달 (AC-SUX-018)

### M3 — NavIntent 교체 [전면 rollback 경계]

- `CrossTabParams` 삭제 + `NavIntent` 도입 (X5). **참조 파일 13개**를 함께 손대게 된다 — `AppContent.tsx`, `TabContext.tsx`, `ChartGrid.tsx`, `SectorAnalysis.tsx`, `StockExplorer.tsx`, `types/market.ts` + 테스트 7종. 이들은 tsc 게이트 (b)의 "③가 수정한 파일" 집합에 들어가므로 **NEW 오류 0건 판정 대상**이 된다
- 3조건 소비 가드, `lastHandledId` (D3)
- `focusStock` 정식 필드화 + 차트 그리드 소비자 (ST-7 해소). **O-U6 결정 반영**: 이미 있으면 스크롤·하이라이트(중복 추가 금지), 없으면 추가, 정원 도달 시 안내. **기존 그리드 교체 금지**
- 종목 버블 `onStockClick` 배선 (ST-8 해소)
- 전환 규칙 TR-1 ~ TR-16
- RED: AC-SUX-003 ~ 007, 011 ~ 017 (E8/E10/E11 포함)
- **tsc 게이트 (a) HARD 확인**: `TS2353 == 0` (`MarketOverview.tsx:46` 해소). 종료 코드 0은 요구하지 않는다 — 선행 결함 32건은 ③ 범위 밖이다(AC-SUX-004)

### M4 — 표·컨트롤 규약 (화면별 개별 commit)

- 순위표: rank 일치(CT-4), 고지 띠(CT-6), 정렬 리셋(CT-7), null 정렬, 순위변동 3상태(CT-8), 기준일 헤더(CT-9), 가중 배지(CT-14), 제외 영역(CT-2), 선택 유지 안내(CT-3), 복합점수 열, **순위 총수 병기 `7 / 27`(REQ-SUX-055)** — 분모는 `rank !== null` 개수에서 도출, `29` 하드코딩 금지
- 종목 탐색: Stage 분포 모집단 일치(CT-10), 미분류 세그먼트(CT-11), 3열 상설 + 섹터비중 열
  - **산업명(중) 필터는 구현하지 않는다** (REQ-SUX-054 철회, spec.md §3.7). `StockTable.tsx:86`의 `sector_major`-only 술어를 **그대로 둔다.** 툴바 컨트롤도 추가하지 않는다
  - **좁은 화면 열 접기 (REQ-SUX-058, O-U7 결정)**: 섹터비중 → Vol배 → 52W고 순. 기간 3열·Stage·RS·Name은 접지 않는다(Lesson #3). 3열 접은 뒤에도 넘치면 가로 스크롤. **접기 순서는 단일 위치의 상수 배열**로 정의한다 — 컴포넌트마다 다시 적으면 발산한다
- Bump: `weeks` 컨트롤 + `span_days` 표기
- RRG/Bump: 기간 토글 **비활성 + 툴팁**(CT-13, O-U1 결정 — 숨기지 않는다)
- **AC-SUX-019(제외 섹터)의 검증 범위 = Table·섹터 Bubble·RRG 한정** (O-U9 확정 — AG-5 Bump 미적용). Bump 케이스는 **추가하지 않는다**. 대신 Bump에는 **반대 방향 단언**을 구현한다 — 제외 섹터의 선이 남아 있어야 하며, `mut_bump_applies_ag5` 되돌림에서 RED를 관측해 `progress.md §E.2`에 verbatim 기록한다(Lesson #9)
- RED: AC-SUX-019 ~ 032, AC-SUX-058, AC-SUX-061 (**AC-SUX-057은 결번**)

### M5 — 시각화 (차트별 개별 commit)

- 버블 크기 유틸 (D7) + 크기 범례. **O-U4 결정 반영 — 기간별 고정 눈금**: `v_min`/`v_max`를 데이터가 아니라 기간별 사다리 상수로 잡고, 범위 밖은 클램프(툴팁엔 실제 값), 범례에 기간 병기
- **테두리 채널 단일화 (REQ-SUX-057)**: 섹터 버블 = 결측 거래대금(점선), 종목 버블 = Stage 단독. 종목 버블의 결측 거래대금은 **테두리를 건드리지 않는다** — 점선으로 만들면 `stage === null`(회색 점선)과 구분 불가
- **섹터 버블 색상 채널 (REQ-SUX-056)**: 기간 수익률 발산형 5단계 + 색상 범례. 발산 기준점은 0%(벤치마크 아님)
- `axisPointer` 삭제, 기준선 라벨, 축 범위
- RRG 사분면 라벨·자동 축(공식 리터럴 고정)·궤적 시작·벤치마크 추종. **②의 O-A1 결정(롤링 정규화 미적용) 반영 — 표준 JdK RRG와의 발산을 범례에 고지**
- Stage 테두리 채널, hover 완화, 대비 팔레트, 기타 개수 병기
- **색상 채널 회귀 금지 테스트를 먼저 작성**(AC-SUX-048)한 뒤 착수. REQ-SUX-056(섹터 버블 색상)이 종목 버블 색상 배열에 영향을 주지 않음을 함께 단언
- RED: AC-SUX-038 ~ 051, AC-SUX-059, AC-SUX-060

### M6 — 로딩·오류·빈 상태

- 탭 활성화 트리거, TTL, stale-but-showing, 재시도·수동 새로고침, 기준일 합치 검증
- `MetricCell` 공용 컴포넌트 (D6)
- 상세 패널 오류 표시 + 거짓 안내 삭제 (X4)
- RED: AC-SUX-033 ~ 037, 052 ~ 055

### M7 — 회귀 게이트 + 성능 측정

- **tsc baseline 기록** — run 착수 시점(M1 이전)에 `npx tsc -p tsconfig.app.json --noEmit`의 총 오류 수 `N`과 **파일:코드 목록 전량**을 progress.md §E.2에 남긴다. 목록이 없으면 (b) 게이트의 "NEW 오류" 판정이 불가능하다. 측정 시점 실측: `N = 33`, `TS2353 = 1`
- AC-SUX-056 (R1·R2 grep 부재 확인 포함, R3·R4, **R5는 Table·섹터 Bubble·RRG 한정** — O-U9 확정으로 Bump 케이스는 추가하지 않는다)
- §0.3 제거 목록 X1~X6 grep 확인
- §1.2 보존 대상 10항목 회귀 단언
- §0.2 성능 측정 → progress.md §E.2 (특히 리렌더 범위)
- 모바일 시뮬레이션 hover-only 0건 확인

---

## 3. 기술 노트

### 3.1 NavIntent 소비 가드

```tsx
const { intent } = useNavIntent()
const { activeTab } = useTab()
const lastHandled = useRef<number | null>(null)

useEffect(() => {
  if (!intent) return
  if (intent.target !== MY_TAB_ID) return
  if (activeTab !== MY_TAB_ID) return
  if (lastHandled.current === intent.id) return
  lastHandled.current = intent.id
  handle(intent.payload)          // 전역 clear 호출 없음
}, [intent, activeTab])
```

### 3.2 버블 반지름 공용 유틸

```ts
export function bubbleRadius(v: number, vMin: number, vMax: number, rMin: number, rMax: number) {
  const lo = Math.log(vMin + 1), hi = Math.log(vMax + 1)
  const u = hi === lo ? 0.5 : (Math.log(v + 1) - lo) / (hi - lo)
  return Math.sqrt(rMin * rMin + u * (rMax * rMax - rMin * rMin))
}
// symbolSize = 2 * bubbleRadius(...)
```

### 3.3 RRG 축 자동 대칭

```ts
const half = Math.max(5, Math.ceil(Math.max(...pts.map(p => Math.abs(p - 100))) * 1.1))
// min = 100 - half, max = 100 + half
```

### 3.4 리렌더 범위 통제

- `AnalysisParamsContext` value는 `useMemo`로 안정화하고, 읽기 전용 필드(`asOfDate` 등)는 별도 하위 Context로 분리 가능성을 열어 둔다.
- `SelectionContext` 소비자는 `selectedSector`만 구독하고 `sectorScopeFollow`는 종목 탐색만 구독한다.
- §0.2 목표 미달 시 selector 패턴(`useContextSelector` 유사 구현) 도입을 검토한다 — **선제 도입 금지**(과설계).

### 3.5 캐시 무효화

`grid_version` 변경 감지 시 `Map`을 통째로 비운다. TTL은 `Date.now() - at > 3_600_000` 판정.

---

## 4. 리스크 분석

| 리스크 | 심각도 | 완화 |
| --- | --- | --- |
| **라이브 사용 후 가치 재평가로 폐기** (`SPEC-CHART-NAV-001` 선례) | HIGH | §0.1 재평가 절차 + §0.4 rollback 경계(M3 직전) 사전 정의. 브랜치 archive 보존 |
| Context 도입으로 광범위 리렌더 → 체감 저하 | HIGH | D2 분리 + §0.2 Profiler 측정 의무. 목표 미달 시 §3.4 |
| M3 이후 부분 rollback 불가 | HIGH | M3를 단일 commit으로 고정하고 그 직전을 전면 rollback 경계로 명시 |
| 색상 채널 실수 변경 (출하 SPEC 되돌림 + ANCHOR 위반) | HIGH | AC-SUX-048을 **M5 착수 전에** 작성. §1.2 보존 목록 명시 |
| 기간 토글마다 서버 재조회 → "느려졌다" 신고 | MEDIUM | LD-C stale-but-showing으로 체감 완화. R1 릴리스 노트 |
| `sectorScopeFollow` 이중 상태의 사용자 혼란 | MEDIUM | §0.1 재평가 항목 ①. 폐기 시 SM-6만 제거하는 amendment 경로 확보 |
| 종목 표 12열 가로 넘침 | MEDIUM | O-U7. 결정 전 가로 스크롤(열 숨김 금지 — Lesson #3) |
| ② revert 시 ③ 라벨이 거짓말 | MEDIUM | §0.4에 명시. ②/③ 동시 revert 원칙 |
| 모바일에서 hover 정보 접근 불가 | LOW | A5 + 배지 본문 상설. E6 확인 |

---

## 5. mx_plan

| 위치 | 태그 | 내용 |
| --- | --- | --- |
| `NavIntent` 소비 가드 | `@MX:ANCHOR` | 3조건 계약(target/id/active). 소비자 fan_in >= 3 |
| `AnalysisParamsContext` | `@MX:ANCHOR` | 02 §3.3 소유권 표. 읽기 전용 필드의 쓰기 금지 |
| `bubbleRadius` 유틸 | `@MX:ANCHOR` | VZ-1 공식. 두 차트 공유 |
| `StockBubbleChart.tsx:28` 기존 앵커 | (보존) | 색상 결정성 계약 — **수정 금지** |
| `MetricCell` | `@MX:NOTE` | ER-1 5상태. 0/50.0 렌더 금지 사유 |
| 삭제된 `axisPointer` 자리 | `@MX:NOTE` | VZ-4 재도입 금지 사유 |

---

## 6. 검증 순서

1. ② close 확인
2. `npx tsc -p tsconfig.app.json --noEmit`
3. `npx vitest run` (신규 + 기존 회귀)
4. 정적 스캔: X1~X6 제거 확인, §1.2 보존 확인
5. React DevTools Profiler로 리렌더 범위 측정 (§0.2)
6. 라이브 브라우저 스모크: W1 5단계 완주 + 복귀 경로
7. 모바일 폭 시뮬레이션 (E6)
