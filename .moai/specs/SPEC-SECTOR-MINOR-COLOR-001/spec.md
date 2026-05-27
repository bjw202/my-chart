---

## id: SPEC-SECTOR-MINOR-COLOR-001 version: 1.0.1 status: draft created: 2026-05-27 updated: 2026-05-27 author: jw priority: medium issue_number: 0

# SPEC-SECTOR-MINOR-COLOR-001: StockBubbleChart 산업명(중) 색상·범례 (Stage 색상 100% 대체)

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 1.0.0 | 2026-05-27 | jw | 초기 SPEC 작성. research.md(2026-05-27) 기반. StockBubbleChart 드릴다운 뷰의 Weinstein Stage 색상 매핑을 sector_minor(산업명(중)) 기준으로 100% 대체하고, 동적 범례(클릭 토글 + hover emphasis, 모바일 fallback 정의)와 tooltip의 산업명(중) 라인을 추가한다. Stage 정보는 tooltip에 유지(사용자 결정). development_mode: tdd. issue_number: 0 (GitHub integration OFF). Lesson #1/#2/#7 반영 — hover 정책 + 모바일 fallback + prominence priority + 라이브 가설 + 성능 baseline + UI 매핑 표 명시. Lesson #4 N/A (no derived dataframe). |
| 1.0.1 | 2026-05-27 | jw | plan-auditor review-1 PASS(0.93) 반영: D1 Tailwind 오인용 → project-grounded rationale로 정정, D2 useMediaQuery 인라인 구현 채택(외부 라이브러리 무도입), D3 AC-10 정적 스캔 binary 확정(Vitest source-string regex), D4 AC-9 component re-render 단언 추가(rerender × 2회 itemStyle.color 배열 비교), D5 @MX:ANCHOR fan_in=2 근거 명시, D6 라인 인용 L124→L125 정정(3 파일). D7 WCAG contrast는 non-blocking이라 본 amendment에서 미적용 (향후 별도 design 검토). |

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **프로젝트**: KR Stock Screener (FastAPI + React + SQLite)
- **선행 리서치**: `.moai/specs/SPEC-SECTOR-MINOR-COLOR-001/research.md` (2026-05-27)
- **목표**: Sector Analysis → Bubble 탭 → 섹터 클릭 시 등장하는 종목 드릴다운 뷰(`StockBubbleChart`)에서, Weinstein Stage 기준 색상·5-항목 범례를 **산업명(중) =** `sector_minor` 기준 동적 색상·범례로 100% 대체한다. Stage 정보는 tooltip 라인으로만 유지한다.
- **배포 환경**: localhost 전용, 클라우드 미사용
- **개발 방법론**: TDD (`.moai/config/sections/quality.yaml`의 `development_mode: tdd`) — acceptance 기준은 구체·검증 가능해야 하며 RED 테스트를 유도한다
- **변경 성격**: BROWNFIELD (기존 컴포넌트 + 응답 모델 확장)
- **데이터 흐름**: research.md §3 참조 — DB SELECT → dict → dataclass → Pydantic → JSON → TS. 중간 derived dataframe 없음 (Lesson #4 N/A).

### 1.2 기술 스택

- **Backend**: Python 3.13+, sqlite3, FastAPI, Pydantic v2
- **Frontend**: React 18+, TypeScript, ECharts (echarts-for-react), Vitest + React Testing Library
- **Testing**: pytest (백엔드), Vitest (프론트), 커버리지 85% 이상

### 1.3 기존 코드 현황 (research.md §2 요약)

| 경로 | 역할 | 본 SPEC에서의 역할 |
| --- | --- | --- |
| `my_chart/analysis/sector_advanced.py` `_get_stock_meta` (L119-156) | stock_meta SELECT | SELECT에 `sector_minor` 추가, 결과 dict 채움 \[필수\] |
| `my_chart/analysis/sector_advanced.py` `StockBubble` dataclass (L55-66) | 종목 버블 dataclass | \`sector_minor: str |
| `my_chart/analysis/sector_advanced.py` `compute_stock_bubble` (L551-629) | 종목 버블 계산 본체 | `StockBubble` 생성 시 `sector_minor` 전달 \[필수\] |
| `backend/schemas/sector_advanced.py` `StockBubbleItem` (L38-48) | Pydantic 응답 모델 | \`sector_minor: str |
| `backend/services/sector_advanced_service.py` `get_stock_bubble` (L97-134) | dataclass → Pydantic 변환 | 변환 시 `sector_minor=s.sector_minor` 전달 \[필수\] |
| `frontend/src/types/bubble.ts` `StockBubbleItem` (L19-28) | 백엔드 응답 타입 미러 | \`sector_minor: string |
| `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` | 종목 버블 차트 컴포넌트 | 색상 매핑 / 범례 / tooltip 로직 교체 \[필수\] |

### 1.4 핵심 제약 (research.md §1, §4, §5, §6 요약)

- **\[HARD\] Stage 색상 100% 대체**: 기존 `STAGE_COLORS` Record(L16-22)와 5-항목 stage 범례(L125-137)는 **완전 제거**한다. Stage 정보 자체는 tooltip 라인으로 보존한다(사용자 결정).
- **\[HARD\] 결정성**: 같은 데이터셋에서 sector_minor → 색상 매핑은 항상 동일하다. 매핑 함수는 (count desc, name asc) 정렬 후 palette\[0..9\] 순차 할당.
- **\[HARD\] 색상 팔레트**: Tableau 10 변형 10색 고정. "기타"는 별도 회색(`#9CA3AF`), 항상 범례 마지막.
- **\[HARD\] NULL/누락 sector_minor**: `sector_detail_service.py:90` 패턴(`key = sector_minor or "기타"`)을 그대로 따른다.
- **\[HARD\] 모바일 fallback**: hover emphasis는 데스크탑(&gt;=768px) 전용. 모바일(&lt;768px)은 범례를 차트 하단 수평 배치 + click-toggle만 동작.
- **\[HARD\] 차트 영역 &gt; 범례 영역 prominence**: grid.right 폭은 데스크탑 120\~140px, 모바일은 grid.bottom 80px로 전환. 차트 영역은 항상 우선.

---

## 2. Assumptions (가정)

- A1. `daily DB stock_meta.sector_minor` 컬럼은 이미 존재한다. `sector_detail_service.py:67`이 동일 컬럼을 운영 중이며, 본 SPEC 범위에서 별도 컬럼 존재 가드는 추가하지 않는다(Exclusions).
- A2. 적용 대상은 **종목 드릴다운 뷰(**`StockBubbleChart.tsx`**)뿐**이다. 대분류 섹터 버블(`SectorBubbleChart.tsx`), `BubbleChart.tsx`, RRG/Bump/히스토리 컴포넌트는 범위 밖.
- A3. 일부 종목은 `sector_minor`가 NULL/빈 문자열일 수 있다 → "기타" 그룹으로 흡수.
- A4. sector_minor 종류가 10을 초과하면 10번째 이후는 "기타"로 흡수한다(palette overflow → 회색 묶음). 단일 sector_major 내 sector_minor 10 초과 케이스는 드물지만 안전 fallback으로 정의한다.
- A5. ECharts SVG 렌더러를 그대로 사용한다(기존 `opts={{ renderer: 'svg' }}`). 변경 없음.
- A6. 사용 패턴(Lesson #5 인용): chart grid 방문 시마다 사용. 캐시 없음. backend `/sectors/{sector_name}/bubble` 응답을 매번 fetch.
- A7. backend 응답에 `sector_minor` 필드가 추가되어도 기존 frontend(필드 무시)와 호환된다 → backend 단독 ship 안전(rollback 단순화).
- A8. 백엔드 데이터 흐름에 derived dataframe propagation 없음 (DB SELECT → dict → Pydantic). Lesson #4 SPEC 체크 N/A.

---

## 3. Requirements (요구사항, EARS)

### REQ-SBM-001 (Ubiquitous) — 백엔드 응답 모델 확장

The `StockBubbleItem` Pydantic response model **shall** include the optional field `sector_minor` (산업명(중)), typed as `str | None`, populated from `stock_meta.sector_minor`.

- 검증: `StockBubbleItem.model_fields` 에 `sector_minor` 존재. 응답 JSON 에 `"sector_minor"` 키 포함.
- 매핑: AC-1.

### REQ-SBM-002 (Event-Driven) — 종목 버블 응답 빌드 시 sector_minor 채움

**When** `GET /api/sectors/{sector_name}/bubble` is invoked, the system **shall** load `sector_minor` for each stock from `stock_meta` and include it in the corresponding `StockBubbleItem` of the response.

- 구현 위치(HOW, plan.md 참조): `_get_stock_meta` SELECT 확장 → `compute_stock_bubble`에서 `StockBubble.sector_minor` 채움 → `get_stock_bubble` 서비스에서 Pydantic 변환 시 전달.
- 검증: 응답의 각 stock 항목에 sector_minor 필드 존재, 값은 해당 종목의 stock_meta.sector_minor 와 일치(또는 None).
- 매핑: AC-1, AC-2.

### REQ-SBM-003 (Ubiquitous) — Frontend 타입 미러

The frontend `StockBubbleItem` TypeScript interface **shall** include the field `sector_minor: string | null`, mirroring the backend response model.

- 검증: `frontend/src/types/bubble.ts` 의 `StockBubbleItem` 에 `sector_minor: string | null` 존재.
- 매핑: AC-3.

### REQ-SBM-004 (Ubiquitous) — Bubble fill 색상은 sector_minor 기준

In the StockBubbleChart drill-down view, the bubble fill color of every stock **shall** be determined exclusively by its `sector_minor` value via a deterministic mapping function.

- 정의: 매핑 함수 `f(stocks) = sort(unique(sector_minor or "기타"), by=(count desc, name asc))[:10] → palette[i]`. "기타" 그룹은 항상 회색 `#9CA3AF`. 10 초과 sector_minor는 "기타"로 흡수.
- \[HARD\] 같은 `sector_minor`를 가진 모든 종목은 **정확히 동일한 fill color**를 받는다.
- \[HARD\] 같은 데이터셋에서 매핑은 결정적이다(재렌더 시 색상 흔들림 없음).
- 검증: 동일 sector_minor 종목들의 `itemStyle.color` 배열이 정확히 동일. AC-4, AC-9.
- 매핑: AC-4, AC-9.

### REQ-SBM-005 (Ubiquitous) — 동적 범례 컨텐츠

The chart legend **shall** list each `sector_minor` group present in the current dataset as a separate legend item, with the matching swatch color, and an additional "기타" item appended at the end when at least one stock has `sector_minor` null or absent.

- 정렬: 종목 수 내림차순 → 동률 시 이름 오름차순. "기타"는 **항상 마지막**.
- 검증: 데이터에 N개 sector_minor (+ M개 NULL/누락) 시 범례 항목 수는 `min(N,10) + (1 if M>0 else 0)`. AC-5.
- 매핑: AC-5.

### REQ-SBM-006 (Event-Driven) — 범례 클릭 그룹 토글

**When** the user clicks a legend item, the system **shall** toggle the visibility of all bubbles belonging to that `sector_minor` group via ECharts `legend.selected` state, without affecting other groups.

- 구현: ECharts 표준 동작. 별도 단독필터 모드 없음.
- 검증: 클릭 후 해당 그룹 bubble 비표시, 재클릭 시 복귀. 다른 그룹은 영향 없음. AC-6.
- 매핑: AC-6.

### REQ-SBM-007 (Event-Driven) — 범례 hover 강조 (데스크탑 전용)

**When** the user hovers over a legend item on a desktop viewport (&gt;=768px), the system **shall** emphasize bubbles in that `sector_minor` group and dim the others via ECharts `emphasis.focus`.

- 모바일 fallback: `<768px` 뷰포트에서는 hover emphasis가 동작하지 않는다(터치 환경 — 자연스러운 fallback). 범례는 클릭 토글로만 상호작용.
- 검증: 데스크탑 뷰포트 시뮬레이션에서 hover 시 emphasis 스타일 변화 트리거. AC-7.
- 매핑: AC-7.

### REQ-SBM-008 (Ubiquitous) — Tooltip 산업명(중) 라인 추가

The bubble tooltip **shall** include a `산업명(중): {sector_minor or "기타"}` line, in addition to the existing `Stage: S{n} ({stage_detail})` line which **shall be preserved**.

- 위치: Stage 라인 위 또는 아래(plan.md에서 확정). Stage 라인은 그대로 유지(사용자 결정).
- 검증: tooltip HTML에 `산업명(중):` 문자열 포함, sector_minor 값 표시. Stage 라인도 동일하게 표시. AC-8.
- 매핑: AC-8.

### REQ-SBM-009 (Unwanted Behavior) — Stage 색상 시각 인코딩 회귀 금지

**If** the chart attempts to render bubble fill or legend items based on Weinstein Stage values, **then** the implementation **shall not** ship — Stage-based visual encoding is fully replaced by sector_minor.

- 제거 대상: `STAGE_COLORS` Record, 5-항목 stage 범례(`S1 바닥` / `S2 상승` / `S3 천장` / `S4 하락` / `미분류`).
- Stage 정보는 tooltip 라인으로만 사용자에게 노출.
- 검증: `STAGE_COLORS` 식별자가 렌더 경로(itemStyle.color, legend.data)에서 참조되지 않음. 5-항목 stage 범례 항목 어느 것도 렌더 결과에 없음. AC-10.
- 매핑: AC-10.

### REQ-SBM-010 (State-Driven) — 모바일 좁은 폭 범례 배치

**While** the viewport width is less than 768px, the chart legend **shall** render at the bottom of the chart horizontally with `type: 'scroll'`, and `grid.right` **shall** shrink to 60 with `grid.bottom` expanded to 80, so that the chart area is not occluded by the legend.

- 검증: `window.matchMedia('(max-width: 767px)')` 시뮬레이션에서 legend.orient === 'horizontal' 및 bottom 위치 확인. AC-11.
- 매핑: AC-11.

### REQ-SBM-011 (Ubiquitous) — 성능 회귀 방지

The chart rendering time at the 95th percentile for a dataset of 200+ stocks **shall not** exceed the baseline (current Stage-based implementation) by more than 20%.

- 측정: Chrome DevTools Performance 탭, ECharts SVG 첫 렌더 시점, 3회 측정 P95.
- baseline 값은 plan.md / acceptance.md 측정 가이드에 따라 사용자가 기록한다(Lesson #7).
- 매핑: AC-12.

---

## 4. Exclusions (What NOT to Build)

본 SPEC은 다음을 **구현하지 않는다**:

- **대분류 섹터 버블(**`SectorBubbleChart.tsx`**)**: 변경 없음. 본 SPEC은 종목 드릴다운 뷰 전용.
- `BubbleChart.tsx` **(별도 컴포넌트)**: 변경 없음.
- **RRG / Bump / 히스토리 / 트리맵 / SectorRankingTable / SectorDetailPanel**: 변경 없음.
- **Stage classification 폐기**: Stage 자체는 tooltip에 보존. backend stage 계산 로직(`classify_stage`) 변경 없음.
- **그리드 결과 테이블 / StockTable.tsx**: 변경 없음. 본 SPEC은 단일 차트 컴포넌트 한정.
- **별도 sector_minor 통계 사이드패널**: 후속 SPEC 대상. 본 SPEC은 색상 + 범례 + tooltip만.
- **stock_meta.sector_minor 컬럼 존재 가드**: 정상 경로 전제. 컬럼 누락 시 OperationalError → 사용자가 DB 재빌드 필요(research.md §9).
- **사용자 정의 색상 팔레트 / 다크/라이트 테마 토글**: 본 SPEC은 고정 Tableau 10 변형 + 회색 "기타" 1세트만.
- **백엔드 dataframe propagation 가드 (Lesson #4)**: 본 SPEC 데이터 흐름에 derived dataframe 없음 (N/A).
- **차트 축 / grid / 버블 크기 정규화 / Top 20 라벨 규칙**: 모두 기존 동작 유지.

---

## 5. Specifications (수용 기준 연결)

상세 Given/When/Then 시나리오, 에지케이스, 품질 게이트는 `acceptance.md` 참조. 구현 작업 분해, 기술 노트, 리스크, mx_plan은 `plan.md` 참조.

### Traceability (REQ ↔ AC)

| REQ | 매핑 AC |
| --- | --- |
| REQ-SBM-001 | AC-1 |
| REQ-SBM-002 | AC-1, AC-2 |
| REQ-SBM-003 | AC-3 |
| REQ-SBM-004 | AC-4, AC-9 |
| REQ-SBM-005 | AC-5 |
| REQ-SBM-006 | AC-6 |
| REQ-SBM-007 | AC-7 |
| REQ-SBM-008 | AC-8 |
| REQ-SBM-009 | AC-10 |
| REQ-SBM-010 | AC-11 |
| REQ-SBM-011 | AC-12 |
