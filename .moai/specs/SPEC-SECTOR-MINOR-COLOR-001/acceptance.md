# SPEC-SECTOR-MINOR-COLOR-001 Acceptance — 수용 기준

> `development_mode: tdd`. 각 시나리오는 RED 테스트로 작성 가능한 구체·검증 가능 기준이다.
> 시나리오 ID는 REQ-SBM-NNN과 매핑된다.

---

## 1. Given/When/Then 시나리오

### AC-1 — StockBubbleItem 응답 모델에 sector_minor 존재 (REQ-SBM-001, REQ-SBM-002)

- **Given** `backend/schemas/sector_advanced.py` 의 `StockBubbleItem` 정의가 있고
- **When** `StockBubbleItem.model_fields` 를 조회하면
- **Then** `"sector_minor"` 키가 존재하고, 타입은 `str | None` 으로 정의된다.
- **And (응답 빌드 시점)** 합성 stock_meta(`sector_minor` 컬럼 포함)로 `compute_stock_bubble` 호출 → 결과 각 `StockBubble.sector_minor` 가 stock_meta 의 `sector_minor` 값과 일치하고, 빈/None 입력은 `None` 으로 보존된다.

### AC-2 — `_get_stock_meta` SELECT 확장 (REQ-SBM-002)

- **Given** daily DB stock_meta 테이블이 `name, code, sector_major, sector_minor, market, market_cap` 컬럼을 가지고
- **When** `_get_stock_meta(daily_db_path)` 가 호출되면
- **Then** 반환 dict 의 각 value 에 `"sector_minor"` 키가 존재하고, DB 의 해당 컬럼 값(또는 NULL → None)이 채워진다. 기존 키(`Code`, `sector_major`, `시장구분`, `market_cap`)는 그대로 유지된다.

### AC-3 — Frontend StockBubbleItem 타입 미러 (REQ-SBM-003)

- **Given** `frontend/src/types/bubble.ts` 의 `StockBubbleItem` 인터페이스가 있고
- **When** TypeScript 컴파일이 실행되면
- **Then** `StockBubbleItem.sector_minor: string | null` 가 존재한다(타입 누락 시 컴파일 에러). 기존 필드(`name`, `price_change`, `rs_12m`, `trading_value`, `stage`, `stage_detail`, `market_cap`, `volume_ratio`)는 변경 없다.

### AC-4 — 동일 sector_minor 종목의 fill 색상 일치 (REQ-SBM-004)

- **Given** `StockBubbleChart` 에 `stocks: StockBubbleItem[]` 가 주어지고, 그 중 sector_minor 값이 "반도체" 인 종목이 3개, "디스플레이" 인 종목이 2개, sector_minor 가 null 인 종목이 1개 있을 때
- **When** `StockBubbleChart` 가 렌더되어 ECharts option 이 구성되면
- **Then** option.series[0].data 중 sector_minor=="반도체" 인 3개 항목의 `itemStyle.color` 가 정확히 동일하고, "디스플레이" 인 2개도 정확히 동일하고, null 인 1개는 회색 `#9CA3AF` 와 동일하다. 세 그룹의 색상은 서로 다르다.

### AC-5 — 동적 범례 컨텐츠 (REQ-SBM-005)

- **Given** stocks 데이터에 sector_minor 종류가 N개(예: "반도체", "디스플레이", "장비") + sector_minor 가 null/빈 종목이 M개(>=1) 있을 때
- **When** `StockBubbleChart` option 이 빌드되면
- **Then** `option.legend.data` 의 길이는 `min(N, 10) + 1` (마지막은 "기타"). N <= 10 이면 N + 1. 정렬은 종목 수 내림차순 → 동률 시 이름 오름차순. "기타"는 **마지막**.
- **And** N=11 인 경우 — palette overflow 시 11번째 sector_minor 와 null 모두 "기타"에 흡수되어 legend.data 길이는 11 (palette 10 + 기타 1).

### AC-6 — 범례 클릭 그룹 토글 (REQ-SBM-006)

- **Given** 차트가 렌더되어 있고 "반도체" 그룹이 visible 상태이고
- **When** 사용자가 "반도체" 범례 항목을 클릭하면 (ECharts `legendselectchanged` 이벤트 시뮬레이션)
- **Then** option/state 상의 `legend.selected["반도체"] === false` 가 되어 해당 그룹의 bubble 이 화면에서 숨겨진다.
- **And** 재클릭 시 `legend.selected["반도체"] === true` 로 복귀.
- **And** "디스플레이" 등 다른 그룹의 selected 상태는 영향받지 않는다.

### AC-7 — 범례 hover 강조 (데스크탑 전용) (REQ-SBM-007)

- **Given** viewport >= 768px (`window.matchMedia('(max-width: 767px)').matches === false`) 이고 차트가 렌더되어 있을 때
- **When** 사용자가 "반도체" 범례 항목 위에 hover 하면 (ECharts `highlight` 시뮬레이션 또는 `series.emphasis.focus === 'series'` 설정 확인)
- **Then** "반도체" 그룹의 bubble 은 emphasis 스타일(shadowBlur/shadowColor)을 받고, 나머지 그룹은 dim(또는 fade) 된다.
- **And (모바일 fallback)** viewport < 768px 시뮬레이션에서는 hover emphasis 가 트리거되지 않는다 (terminal touch 환경 — 자연스러운 fallback). click-toggle 만 동작.

### AC-8 — Tooltip 산업명(중) 라인 + Stage 라인 보존 (REQ-SBM-008)

- **Given** 차트 데이터에 sector_minor="반도체", stage=2, stage_detail="entry" 인 종목 "삼성전자"가 있을 때
- **When** ECharts tooltip.formatter 가 해당 데이터 포인트에 대해 호출되면
- **Then** 반환 HTML 문자열에 `산업명(중): 반도체` 라인과 `Stage: S2 (entry)` 라인이 **모두** 포함된다.
- **And (NULL 케이스)** sector_minor 가 null/빈 종목 → tooltip 에 `산업명(중): 기타` 표시.
- **And (회귀 방지)** Stage 라인 형식 `Stage: S{n} ({stage_detail or ''})` 은 기존 그대로(L173 부근) 유지된다.

### AC-9 — 색상 매핑 결정성 round-trip (REQ-SBM-004) [HARD]

- **Given** 동일 stocks 배열 `S` 가 주어지고
- **When** `buildSectorMinorColorMap(S)` 를 **두 번** 호출하면
- **Then** 두 결과 Map 의 모든 entry (sector_minor → color) 가 정확히 동일하다.
- **And** 종목 수 동률(같은 sector_minor count) 인 두 그룹은 이름 오름차순으로 palette 인덱스를 받아 결정적이다.
- **And** 다른 순서로 정렬된 stocks 배열을 입력해도 (예: shuffle), 매핑 결과는 동일하다 (set-기반 입력의 idempotency).

- **And (component re-render):** Testing Library `rerender()`로 동일 props로 2회 마운트 후 `option.series[0].data[i].itemStyle.color` 배열을 모든 i에 대해 비교 — 완전 일치해야 한다 (canvas redraw 시 비결정성 회귀 차단).

### AC-10 — Stage 시각 인코딩 회귀 방지 [HARD] (REQ-SBM-009)

- **Given** 차트가 렌더되어 option 이 빌드되었을 때
- **When** `option.legend.data` 를 조회하면
- **Then** 라벨 `'S1 (바닥)'`, `'S2 (상승)'`, `'S3 (천장)'`, `'S4 (하락)'`, `'미분류'` 중 **어느 것도 존재하지 않는다**.
- **And** 컴포넌트 소스에 `STAGE_COLORS` 식별자가 itemStyle.color / legend.data 결정 경로에서 참조되지 않는다 (정적 검사: Vitest source-string regex (`fs.readFileSync` of StockBubbleChart.tsx → `/STAGE_COLORS\s*[:=]/` 부재 단언)).
- **And** Stage 정보 자체는 tooltip 라인(`Stage: S{n}`)에 **여전히 보존된다** (사용자 결정 — AC-8 의 보존 단언과 연결).

### AC-11 — 모바일 좁은 폭 범례 하단 배치 (REQ-SBM-010)

- **Given** Vitest 가 `window.matchMedia('(max-width: 767px)').matches === true` 를 반환하도록 mock 되어 있을 때
- **When** `StockBubbleChart` 가 렌더되어 option 이 빌드되면
- **Then** `option.legend.orient === 'horizontal'`, `option.legend.bottom` 가 정의됨, `option.legend.type === 'scroll'`.
- **And** `option.grid.right === 60`, `option.grid.bottom === 80`.
- **And (데스크탑)** matches === false 시뮬레이션에서는 `option.legend.orient === 'vertical'`, `option.legend.right` 정의됨, `option.grid.right` 는 기존 120 유지.

### AC-12 — 200+ 종목 P95 렌더 회귀 방지 (REQ-SBM-011) [HARD]

- **Given** 200개 이상의 stocks 가 포함된 응답 데이터 (실제 "IT" 같은 큰 섹터의 production 응답 권장) 와
- **When** Chrome DevTools Performance 탭으로 ECharts SVG 첫 렌더 시점을 3회 측정하여 P95 를 산출하면
- **Then** P95 < (baseline P95 측정값) * 1.20.
- **And (baseline 측정 가이드)** 변경 전 main 브랜치에서 동일 데이터셋·동일 측정 절차로 baseline 을 1회 측정해 plan.md (또는 retrospective.md)에 기록한다. baseline 값 부재 시 본 AC 는 라이브 검증 시점까지 **pending** 상태로 둔다.

> AC-9 결정성 round-trip 과 AC-10 Stage 회귀 방지 + AC-12 P95 게이트는 **HIGH-risk 무음 회귀 검출** 용 핵심 게이트다.

---

## 2. 에지케이스

| 케이스 | 기대 동작 |
| --- | --- |
| 모든 종목 sector_minor === null | 범례 1개 항목 "기타" (회색). 모든 bubble 회색. tooltip `산업명(중): 기타`. |
| 단일 sector_minor 만 존재 | 범례 1개 항목(해당 sector_minor). palette[0] 색상. 모든 bubble 동일 색. |
| sector_minor 11개 + null 종목 0개 | 상위 10개 → palette[0..9]. 11번째 → "기타" 그룹으로 흡수. 범례 11개 항목 (10 + 기타). |
| sector_minor 5개 + null 종목 다수 | 상위 5개 + "기타" → 범례 6개 항목. |
| stocks 배열 빈 배열 | 기존 "데이터 없음" 그래픽 유지. legend 없음. AC-5 적용 안 됨. |
| sector_minor 종목 수 동률 (예: 3개씩 2개 sector_minor) | 이름 오름차순으로 palette 인덱스 결정 — 결정성 확보 (AC-9). |
| 모바일 → 데스크탑 viewport 회전 | useMediaQuery 가 isMobile state 갱신 → useMemo 재계산 → legend orient 자동 전환. |
| 범례 클릭 → 모든 그룹 숨김 | 빈 차트 상태. 재클릭으로 복귀. ECharts 표준 동작. |
| 범례 클릭 토글 후 데이터 새로고침 (fetchStockBubble) | ECharts legend.selected state 초기화 (component unmount → mount). 모든 그룹 visible 로 복귀. |
| 같은 sector_major 다른 sector_minor 가 다른 색을 받음 | 정상. 같은 sector_minor 만 같은 색 (AC-4). |
| Stage 가 null/0 인 종목 | bubble 색상은 sector_minor 기준 (Stage 무관). tooltip Stage 라인 `Stage: 미분류` (기존 동작 유지). |

---

## 3. 품질 게이트 (Quality Gates)

- **결정성 게이트 [HARD]**: AC-9 round-trip 으로 같은 입력 → 같은 색상 매핑 단언. 정렬 키 (count desc, name asc) 명시.
- **회귀 방지 게이트 [HARD]**: AC-10 으로 Stage 라벨 5개("S1 바닥" / "S2 상승" / "S3 천장" / "S4 하락" / "미분류") 가 legend.data 에 어느 것도 없음 단언. `STAGE_COLORS` 식별자 정적 검사.
- **성능 게이트 [HARD]**: AC-12 P95 < baseline * 1.20. 200+ 종목 케이스 필수.
- **타입 게이트**: AC-3 frontend TypeScript 컴파일 + AC-1 backend Pydantic model_fields.
- **테스트 커버리지**: 변경 모듈 85% 이상. Vitest + pytest.
- **TRUST 5**:
  - **Tested**: 신규 시나리오 AC-1~AC-12 RED→GREEN.
  - **Readable**: 한국어 주석/MX 태그(`code_comments: ko`), `buildSectorMinorColorMap` 의 정렬·overflow 정책 docstring 명시.
  - **Unified**: ruff/black (Python), TypeScript strict, ESLint.
  - **Secured**: 서버사이드 SELECT 화이트리스트 컬럼만 — SQL injection 표면 없음. 프론트엔드 sector_minor 값은 React가 자동 escape.
  - **Trackable**: conventional commit + SPEC-SECTOR-MINOR-COLOR-001 참조.
- **기존 테스트 회귀 없음**: `backend/tests/test_sector_advanced.py` 의 기존 compute_stock_bubble 테스트(L334-388) + `SectorDetailPanel.test.tsx`, `SectorAnalysis.test.tsx`, `SectorRankingTable.test.tsx` 회귀 없음 확인.
- **prominence 게이트 (Lesson #2)**: 차트 영역 > 범례 영역. 데스크탑 grid.right 120, 모바일 grid.right 60 + grid.bottom 80. AC-11.
- **hover 정책 (Lesson #1)**: hover emphasis 는 enhancement, click-toggle 이 baseline. 모바일 fallback 사전 정의 — AC-7.
- **라이브 가설 검증 (Lesson #7)**: ship 후 사용자 1일 사용 회고 1회. 동일 색상 군집 5초 이내 인지 + tooltip 산업명(중) 명확성 + 그룹 격리 사용성 평가.

---

## 4. Definition of Done

- [ ] REQ-SBM-001 ~ REQ-SBM-011 전부 구현 및 검증.
- [ ] AC-1 ~ AC-12 전 시나리오 테스트 통과 (AC-12 는 라이브 측정 완료 시점까지 pending 허용).
- [ ] `StockBubbleItem` (Pydantic + TS) 에 `sector_minor` 필드 존재 (AC-1, AC-3).
- [ ] `_get_stock_meta` SELECT 에 `sector_minor` 포함, 결과 dict 에 키 존재 (AC-2).
- [ ] `compute_stock_bubble` → `StockBubble.sector_minor` 전파 (AC-1 sub).
- [ ] `get_stock_bubble` 서비스 변환 시 `sector_minor` 전달 (AC-1 sub).
- [ ] `StockBubbleChart.tsx`: `STAGE_COLORS` + `DEFAULT_COLOR` 완전 삭제, `SECTOR_MINOR_PALETTE` + `ETC_COLOR` + `buildSectorMinorColorMap` 추가 (AC-4, AC-9, AC-10).
- [ ] `option.legend.data` 가 sector_minor 기반 동적 생성 (AC-5).
- [ ] 범례 click-toggle 동작 (AC-6).
- [ ] 범례 hover emphasis 동작 (데스크탑) + 모바일 비활성 fallback (AC-7).
- [ ] Tooltip 에 `산업명(중):` 라인 추가, Stage 라인 보존 (AC-8).
- [ ] Stage 5-항목 범례 완전 제거, `STAGE_COLORS` 미참조 정적 검사 통과 (AC-10).
- [ ] 모바일 (`<768px`) 시뮬레이션에서 범례 하단 배치 + grid.right 60 / grid.bottom 80 (AC-11).
- [ ] 200+ 종목 P95 렌더 < baseline * 1.20 (AC-12) — 라이브 측정 완료 후 plan.md / retrospective.md 에 baseline + 측정값 기록.
- [ ] Exclusions 항목 미구현 확인 (대분류 섹터 버블 / BubbleChart / RRG / Bump / 통계 사이드패널 / 컬럼 존재 가드 / 사용자 정의 팔레트).
- [ ] 한국어 주석 + MX 태그 (`code_comments: ko`) 적용.
- [ ] 라이브 smoke test: "IT" 같은 큰 섹터 드릴다운 → 색상 군집·범례·tooltip·범례 클릭·hover·모바일 fallback 확인.
- [ ] Lesson #1/#2/#7 SPEC 체크 항목 충족 (hover live verification, prominence priority 명시, 라이브 가설 + 성능 baseline + UI 매핑 표).
