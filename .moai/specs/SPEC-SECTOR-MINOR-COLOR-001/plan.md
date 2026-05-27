# SPEC-SECTOR-MINOR-COLOR-001 Plan — 구현 계획

> [DELTA] 마커 범례: `[EXISTING]` 변경 없는 기존 코드 / `[MODIFY]` 기존 파일 수정 / `[NEW]` 신규 추가.
> 본 SPEC은 BROWNFIELD 변경이며 `development_mode: tdd` (RED → GREEN → REFACTOR).

---

## 1. 기술 노트

### 1.1 백엔드 (Python)

- **`_get_stock_meta` (sector_advanced.py L119-156)**: SELECT 절에 `sector_minor` 추가. 결과 dict의 value에 `"sector_minor": sector_minor or None` 키를 추가한다. fallback 경로(daily DB)에서도 동일 SELECT 사용 — paths_to_try 루프 단일 SELECT.
- **`StockBubble` dataclass (sector_advanced.py L55-66)**: 신규 필드 `sector_minor: str | None = None` 추가. 기본값 `None`으로 두어 기존 호출자(있는 경우)와 호환.
- **`compute_stock_bubble` (sector_advanced.py L551-629)**: `results.append(StockBubble(..., sector_minor=meta.get("sector_minor")))` 추가. meta 값은 위 `_get_stock_meta`가 채운 dict.
- **`StockBubbleItem` Pydantic 모델 (schemas/sector_advanced.py L38-48)**: `sector_minor: str | None = None` 필드 추가. Pydantic v2 디폴트 None.
- **`get_stock_bubble` 서비스 (sector_advanced_service.py L97-134)**: comprehension에 `sector_minor=s.sector_minor` 추가.

### 1.2 프론트엔드 (TypeScript / React / ECharts)

- **타입 (types/bubble.ts L19-28)**: `sector_minor: string | null` 추가.
- **색상 매핑 함수 (StockBubbleChart.tsx 신규)**:
  ```typescript
  function buildSectorMinorColorMap(stocks: StockBubbleItem[]): Map<string, string> { @MX:REASON: fan_in=2 (itemStyle.color + legend.data) — mx-tag-protocol fan_in≥3 임계 미달이지만, 결정성·범례·색상 일관성이 단일 함수에 응집(triple-dependency)되므로 ANCHOR 격상. 해당 함수 시그니처 변경 시 색상·범례·tooltip 3축이 동시 영향.
    // 1) sector_minor → count 집계 ("기타" 묶음 포함)
    // 2) [(name, count)] 정렬: count desc, name asc, "기타" 제외
    // 3) 상위 10개 sector_minor → palette[0..9]
    // 4) 11번째부터 + null/empty → "기타" → 회색 #9CA3AF
    // 5) Map 반환 (deterministic)
  }
  ```
  palette 상수:
  ```typescript
  const SECTOR_MINOR_PALETTE = [
    '#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
    '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC',
  ] as const
  const ETC_COLOR = '#9CA3AF'
  const ETC_LABEL = '기타'
  ```
- **STAGE_COLORS 제거 [HARD]**: L16-22 완전 삭제. `DEFAULT_COLOR`도 함께 제거(다른 참조 없음 확인 완료).
- **범례 동적 생성 (L125-137 교체)**: `legend.data`를 색상 매핑 Map에서 생성. orient/위치는 미디어 쿼리로 분기 (`max-width: 767px`).
- **Tooltip (L159-181)**: formatter에 `산업명(중): {sector_minor or '기타'}` 라인을 **Stage 라인 위**에 삽입한다. Stage 라인은 그대로 유지.
- **emphasis 설정**: `series.emphasis.focus = 'series'` + legend hover 시 동일 sector_minor 그룹만 강조. 모바일은 자동 무시(touch는 hover 이벤트 없음).
- **반응형 분기**: `useMemo` 의존성에 `window.innerWidth`를 직접 두면 안 됨 → `useEffect` + `useState`로 viewport 추적, 또는 `ReactECharts` rerender. 작은 hook 사용 권장: `useMediaQuery('(max-width: 767px)')`.
  - [HARD] `useMediaQuery` 소스: 본 프로젝트에 해당 hook 미존재. **inline 구현 채택** — `window.matchMedia('(max-width: 767px)')` + `useState`/`useEffect` 5라인 커스텀 hook을 `frontend/src/hooks/useMediaQuery.ts`로 신규 작성 (외부 라이브러리 무도입). cleanup listener 포함.

### 1.3 [HARD] 결정 사항

- **색상 팔레트**: Tableau 10 변형 10색 + 회색 "기타". 변경 금지(palette overflow 시 11번째 이후 "기타" 흡수).
- **정렬 규칙**: sector_minor 종목 수 내림차순 → 동률 시 이름 오름차순 → palette 인덱스 결정성 확보.
- **NULL/누락 처리**: `sector_detail_service.py:90` 패턴(`key = sector_minor or "기타"`) 그대로 적용.
- **Stage 시각 인코딩 완전 제거**: tooltip 라인만 유지. STAGE_COLORS / 5-항목 stage 범례는 삭제 — REQ-SBM-009.
- **모바일 break point**: 767px (모바일 portrait viewport 일반 경계 — 본 프로젝트는 Tailwind 미사용. echarts grid.right=120 영역과 충돌 회피 기준).
- **차트 영역 > 범례 영역 prominence (Lesson #2)**: 데스크탑 grid.right 120(기존 유지) / 모바일 grid.right 60 + grid.bottom 80.

---

## 2. 작업 분해 (파일별, [DELTA] 마커)

### Task 1 — [MODIFY] `backend/tests/test_sector_advanced.py` (RED, 응답 모델 + sector_minor 노출)

- [NEW] `test_stock_bubble_response_includes_sector_minor`: `StockBubbleItem.model_fields`에 `sector_minor` 존재 검증.
- [NEW] `test_compute_stock_bubble_propagates_sector_minor`: 합성 stock_meta(`sector_minor` 컬럼 포함)로 `compute_stock_bubble` 호출 → 결과 각 StockBubble의 `sector_minor` 값이 stock_meta와 일치.
- [NEW] `test_compute_stock_bubble_sector_minor_null_fallback`: stock_meta.sector_minor 가 NULL인 종목 → StockBubble.sector_minor == None.
- 기존 테스트(L334-388 compute_stock_bubble 테스트)는 회귀 없음 확인 — `_get_stock_meta` SELECT 확장이 기존 키(`sector_major`, `시장구분`, `market_cap`)에 영향 없음.

### Task 2 — [MODIFY] `my_chart/analysis/sector_advanced.py` (GREEN, dataclass + SELECT + 전파)

- `_get_stock_meta` (L119-156): SELECT 절을 `"SELECT name, code, sector_major, sector_minor, market, market_cap FROM stock_meta"` 로 확장. 루프 unpack을 `(name, code, sector, sector_minor, market, cap)` 로 확장. 결과 dict 에 `"sector_minor": sector_minor or None` 추가.
- `StockBubble` dataclass (L55-66): `sector_minor: str | None = None` 필드 추가 (기존 필드 뒤에 default 가진 필드로 안전 추가).
- `compute_stock_bubble` (L551-629): `results.append(StockBubble(..., sector_minor=meta.get("sector_minor")))` 추가.
- [HARD] 다른 호출처(`compute_sector_bubble` L490+, `compute_treemap_data` L636+)는 stock_meta dict의 신규 키를 사용하지 않으므로 영향 없음 — 검증 완료.

### Task 3 — [MODIFY] `backend/schemas/sector_advanced.py` (GREEN, 응답 모델 필드)

- `StockBubbleItem` (L38-48): `sector_minor: str | None = None` 추가 (다른 필드는 변경 없음).

### Task 4 — [MODIFY] `backend/services/sector_advanced_service.py` (GREEN, 변환)

- `get_stock_bubble` (L97-134): comprehension에 `sector_minor=s.sector_minor` 추가 (한 줄).

### Task 5 — [MODIFY] `frontend/src/components/SectorAnalysis/__tests__/StockBubbleChart.test.tsx` (RED, 신규 또는 기존)

기존 테스트 파일 부재 — **[NEW]** 작성.

테스트 시나리오:
- AC-3 mirror: `StockBubbleItem` 타입에 `sector_minor` 존재(컴파일 시 확인).
- AC-4: 동일 sector_minor 종목들의 `itemStyle.color`가 정확히 동일 (option.series[0].data 의 itemStyle.color 배열 단언).
- AC-5: 데이터에 N개 sector_minor + M개 NULL 시 `option.legend.data.length === min(N,10) + (M>0 ? 1 : 0)`. "기타"는 마지막.
- AC-8: tooltip formatter 호출 결과 문자열에 `산업명(중):` 포함, Stage 라인도 포함.
- AC-9: 결정성 — 두 번 render(같은 props)해도 같은 itemStyle.color 배열.
- AC-10: legend.data에 `'S1 (바닥)'`, `'S2 (상승)'`, `'S3 (천장)'`, `'S4 (하락)'`, `'미분류'` 어느 것도 없음.
- AC-11: matchMedia mock 으로 `<768px` 시뮬레이션 → `option.legend.orient === 'horizontal'` 및 `bottom !== undefined`.

### Task 6 — [MODIFY] `frontend/src/types/bubble.ts` (GREEN, 타입 미러)

- `StockBubbleItem` (L19-28): `sector_minor: string | null` 추가.

### Task 7 — [MODIFY] `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` (GREEN, 시각 인코딩 교체)

- **삭제**: `STAGE_COLORS` Record (L16-22) + `DEFAULT_COLOR` 상수.
- **추가**: `SECTOR_MINOR_PALETTE` 상수 + `ETC_COLOR` + `ETC_LABEL` (§1.2 정의).
- **추가**: `buildSectorMinorColorMap(stocks): Map<string, string>` 함수 (§1.2 정의).
- **수정 L76 (itemStyle.color)**: `color: colorMap.get(s.sector_minor ?? ETC_LABEL) ?? ETC_COLOR`.
- **수정 L125-137 (legend.data)**: 색상 Map을 순회하며 동적 생성. orient/right/bottom 은 isMobile 분기.
- **수정 L96 (grid)**: isMobile 시 `{ left: 60, right: 60, top: 50, bottom: 80 }`, 그 외 기존 유지.
- **수정 L138-158 (series)**: `emphasis: { focus: 'series', ... }` 추가.
- **수정 tooltip (L159-181)**: formatter 의 `lines` 배열에 `산업명(중): {sectorMinor or '기타'}` 라인 추가 (Stage 라인 **위**에 삽입). data tuple 에 sector_minor를 포함하도록 인덱스 확장 (예: index 8 추가).
- **추가**: viewport tracking — `useMediaQuery` 또는 `useEffect` + `useState` 로 isMobile 상태 관리. useMemo 의존성에 isMobile 추가.

### Task 8 — [REFACTOR] 회귀 검증 + 라이브 검증 준비

- Vitest 전체 통과 + pytest 전체 통과 확인 (backend/tests + tests).
- 200+ 종목 데이터셋에서 P95 렌더 측정 (AC-12) — 사용자가 Chrome DevTools 로 직접 수행. baseline + 측정값 plan.md (또는 retrospective.md) 에 기록.
- live smoke test: Sector Analysis → Bubble 탭 → "IT" 같은 큰 섹터 클릭 → 색상 군집 + 동적 범례 + tooltip 산업명(중) 라인 + 범례 click toggle + (데스크탑) hover emphasis + (모바일) 하단 수평 범례 확인.

### [EXISTING] 변경 없음

- `backend/routers/sectors.py` (L134-151 `stock_bubble` 엔드포인트).
- `frontend/src/api/bubble.ts` (타입 자동 반영).
- `SectorBubbleChart.tsx`, `BubbleChart.tsx`, `BumpChart.tsx`, `RRGChart.tsx`, `SectorRankingTable.tsx`, `SectorDetailPanel.tsx`.
- `StockExplorer/StockTable.tsx` (다른 컨텍스트의 Stage UI).
- `daily DB` 스키마 (이미 sector_minor 존재).

---

## 3. 마일스톤 (우선순위 기반, 시간 추정 없음)

1. **Priority High — 백엔드 응답 모델 (Task 1, 2, 3, 4)**: sector_minor 응답 노출. 프론트엔드 작업의 선행. backend 단독 ship 가능(필드 추가만, 기존 frontend는 무시 가능).
2. **Priority High — 프론트엔드 시각 인코딩 (Task 5, 6, 7)**: Stage → sector_minor 색상 교체, 동적 범례, tooltip 라인, 모바일 fallback. backend Task 1~4 완료 후.
3. **Priority Medium — 회귀 검증 + 라이브 smoke (Task 8)**: Vitest + pytest 통과, 200+ 종목 P95 측정, 라이브 화면 확인.

순서: 백엔드 응답 모델 → 프론트엔드 시각 인코딩 → 회귀 + 라이브 smoke. backend 단독 ship → frontend 단독 ship 순차 가능(rollback 단순화).

---

## 4. 리스크 분석

| 리스크 | 심각도 | 완화 |
| --- | --- | --- |
| **sector_minor 종류가 10 초과 (시각 구분 한계)** | MEDIUM | palette 10색 고정 + 11번째 이후 "기타" 흡수 정책 (REQ-SBM-005 / A4). 단일 sector_major 내 10 초과는 드묾 — 데이터로 검증 가능 |
| **모바일 폭에서 범례 ↔ 차트 영역 충돌** | MEDIUM | useMediaQuery 분기로 모바일 시 범례 하단 배치 + grid.right 60 / grid.bottom 80 (REQ-SBM-010). 차트 영역 prominence 우선 (Lesson #2) |
| **legacy stock_meta 종목에 sector_minor NULL (다수)** | MEDIUM | "기타" 그룹으로 흡수 — sector_detail_service.py:90 패턴 그대로. 범례에 "기타" 1개 추가 |
| **레거시 DB에 sector_minor 컬럼 자체 누락** | LOW | `sector_detail_service.py:67`이 동일 컬럼을 운영 중이므로 정상 경로 전제. 누락 시 OperationalError — 사용자가 DB 재빌드. SPEC 범위 밖 (Exclusions, research.md §9) |
| **ECharts visualMap stage piecewise 잔존 위험** | LOW | 현재 코드는 visualMap 미사용, `data[i].itemStyle.color` 직접 칠. 변환 시 잔존 코드 없음 확인 완료 (research.md §9) |
| **성능 회귀 (color map build O(N log N), N=200)** | LOW | 1ms 미만 예상. AC-12 P95 < baseline + 20% 게이트로 검증 |
| **결정성 깨짐 (재렌더 시 색상 흔들림)** | MEDIUM | 정렬 키 (count desc, name asc) 명시 → AC-9 round-trip 테스트로 검증 |
| **rollback 부담 (backend + frontend 양쪽 변경)** | LOW | backend 응답 필드 추가는 backward compatible → 분리 ship 가능. frontend revert만으로 시각 회귀 복구 가능 |
| **Lesson #1 (hover-only) 회귀 위험** | LOW | hover emphasis는 enhancement 일 뿐, click-toggle 이 baseline. 모바일 fallback 사전 정의 — reverse amendment 위험 낮음 |

---

## 5. mx_plan (MX 태그 계획)

`code_comments: ko` 설정에 따라 MX 태그 설명은 한국어로 작성.

| 대상 | 태그 | 사유 |
| --- | --- | --- |
| `my_chart/analysis/sector_advanced.py` `_get_stock_meta` SELECT 확장 | `@MX:NOTE` | sector_minor 컬럼 추가 — sector_detail_service.py 와 동일 패턴, daily DB stock_meta 의존 명시 |
| `my_chart/analysis/sector_advanced.py` `StockBubble` dataclass `sector_minor` 필드 | `@MX:NOTE` | 신규 응답 필드. 후속 backend 호출자에게 의도 전달 |
| `backend/schemas/sector_advanced.py` `StockBubbleItem.sector_minor` | `@MX:NOTE` | API 계약 확장. SPEC 참조 |
| `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` `buildSectorMinorColorMap` | `@MX:ANCHOR` (+ `@MX:REASON`) | 색상 결정성 매핑 — 정렬 키 (count desc, name asc) + "기타" 마지막 + palette 10 overflow → "기타" 흡수 계약. fan_in 高 (itemStyle.color, legend.data 양쪽이 의존). 변경 시 결정성·범례·색상 일관성 동시 깨짐 위험 |
| `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` `SECTOR_MINOR_PALETTE` | `@MX:NOTE` | Tableau 10 변형 고정 팔레트. 변경 시 디자인 시스템 영향 |
| 신규 RED 테스트 (Task 1, Task 5) | `@MX:TODO` | GREEN 단계에서 통과 시 제거 |

REFACTOR/GREEN 단계에서 통과한 `@MX:TODO`는 제거, ANCHOR 의 fan_in 변화는 후속 sync 단계에서 검증.
