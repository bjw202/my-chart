# SPEC-SECTOR-MINOR-COLOR-001 Research — 코드베이스 조사

> 본 문서는 SPEC plan/spec/acceptance 작성을 위한 사전 리서치다. 영향 파일, 데이터 흐름, 기존 패턴 인용, 색상 팔레트 후보를 기록한다.

조사 일자: 2026-05-27
조사자: jw (manager-spec)
대상 기능: StockBubbleChart drill-down 뷰의 sector_minor 기반 색상·범례

---

## 1. 기능 요약

Sector Analysis → Bubble 탭 → 섹터 클릭 시 등장하는 **종목 버블 드릴다운 뷰**(차트 제목: `"{sector_name} 종목 버블"`)에서, 현재 Weinstein Stage(S1~S4) 기준으로 매겨지던 버블 색상과 우측 5-항목 stage 범례를, **산업명(중) = `sector_minor`** 기준으로 100% 대체한다.

- bubble fill = sector_minor 매핑된 distinct color
- legend = 데이터에 등장한 sector_minor + (NULL/누락 종목 묶음) "기타"
- tooltip = `산업명(중): {sector_minor}` 라인 추가 (Stage 라인은 그대로 유지)
- 범례 상호작용 = ECharts 표준 click-toggle + hover emphasis (모바일 fallback: click-toggle만)

차트 축(X=가격변동률, Y=RS Rating), 버블 크기(거래대금 정규화), grid 구성, 종목 라벨 표시 규칙(거래대금 Top 20)은 **변경하지 않는다**.

---

## 2. 영향 파일 (코드베이스 기반)

### 2.1 Backend (Python, FastAPI)

| 경로 | 라인 | 역할 | 본 SPEC에서의 변경 |
| --- | --- | --- | --- |
| `my_chart/analysis/sector_advanced.py` | 55-66 (`StockBubble` 데이터클래스) | 종목 버블 dataclass 정의 | `sector_minor: str | None` 필드 추가 [REQUIRED] |
| `my_chart/analysis/sector_advanced.py` | 119-156 (`_get_stock_meta`) | stock_meta SELECT — 현재 `name, code, sector_major, market, market_cap`만 가져옴 | SELECT에 `sector_minor` 추가, 결과 dict에 `"sector_minor"` key 채움 [REQUIRED] |
| `my_chart/analysis/sector_advanced.py` | 551-629 (`compute_stock_bubble`) | 종목 버블 계산 본체 | `meta["sector_minor"]`를 `StockBubble`에 전달 [REQUIRED] |
| `backend/schemas/sector_advanced.py` | 38-48 (`StockBubbleItem`) | Pydantic v2 응답 모델 | `sector_minor: str | None` 필드 추가 [REQUIRED] |
| `backend/services/sector_advanced_service.py` | 97-134 (`get_stock_bubble`) | dataclass → Pydantic 변환 | 변환 시 `sector_minor=s.sector_minor` 전달 [REQUIRED] |
| `backend/routers/sectors.py` | 134-151 (`stock_bubble` 엔드포인트) | `GET /sectors/{sector_name}/bubble` | 변경 없음 |
| `backend/tests/test_sector_advanced.py` | 334-388 (compute_stock_bubble 테스트) | 종목 버블 테스트 묶음 | `sector_minor` 필드 노출 검증 + 동일 sector_minor 그룹화 검증 RED 추가 [REQUIRED] |

### 2.2 Frontend (TypeScript, React, ECharts)

| 경로 | 라인 | 역할 | 본 SPEC에서의 변경 |
| --- | --- | --- | --- |
| `frontend/src/types/bubble.ts` | 19-28 (`StockBubbleItem`) | 백엔드 응답 타입 미러 | `sector_minor: string | null` 추가 [REQUIRED] |
| `frontend/src/api/bubble.ts` | 19-28 (`fetchStockBubble`) | API 클라이언트 | 변경 없음 (타입은 자동 반영) |
| `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` | 16-22 (`STAGE_COLORS`) | Stage 색상 매핑 | 제거(deprecated) 또는 tooltip 라벨 전용 보존 [REQUIRED] |
| `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` | 76 (itemStyle.color) | bubble fill 색상 결정 | sector_minor → 색상 매핑 함수로 전환 [REQUIRED] |
| `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` | 124-137 (legend) | 5-항목 stage 범례 | sector_minor 동적 범례로 대체 [REQUIRED] |
| `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` | 159-181 (tooltip) | tooltip formatter | `산업명(중)` 라인 추가 (Stage 라인 유지) [REQUIRED] |
| `frontend/src/components/SectorAnalysis/__tests__/StockBubbleChart.test.tsx` | 신규 또는 기존 | Vitest 테스트 | sector_minor 색상/범례/tooltip 검증 RED 추가 [REQUIRED] |

### 2.3 변경 없음 (Exclusions 대상)

- `SectorBubbleChart.tsx` (대분류 섹터 레벨 버블)
- `BubbleChart.tsx` (별도 컴포넌트, 본 SPEC과 무관)
- `BumpChart.tsx`, `RRGChart.tsx`, `SectorRankingTable.tsx`, `SectorDetailPanel.tsx`
- `frontend/src/components/StockExplorer/StockTable.tsx` L47-160 — 다른 컨텍스트의 Stage UI (변경 없음)
- 모든 주봉/RRG/Bump/히스토리 엔드포인트 및 서비스

---

## 3. 데이터 흐름

```
[daily DB stock_meta]
  └─ name, code, sector_major, sector_minor, market, market_cap  ← 본 SPEC: SELECT에 sector_minor 추가
        ↓
  _get_stock_meta(db_path) → dict[Name → {Code, sector_major, sector_minor, 시장구분, market_cap}]
        ↓
  compute_stock_bubble(db_path, sector_name, period)
        ├─ sector_stocks = [name for ...meta["sector_major"]==sector_name]
        └─ for each name in sector_stocks:
             results.append(StockBubble(name, price_change, rs_12m, trading_value,
                                        stage, stage_detail, market_cap, volume_ratio,
                                        sector_minor=meta["sector_minor"]))  ← 본 SPEC: 추가
        ↓
  get_stock_bubble(weekly_db_path, sector_name, period)  [service layer]
        └─ items = [StockBubbleItem(..., sector_minor=s.sector_minor) for s in stocks]  ← 본 SPEC: 추가
        ↓
  GET /api/sectors/{sector_name}/bubble  → StockBubbleResponse JSON
        ↓
  fetchStockBubble(sectorName, period)  → StockBubbleResponse (TS)
        ↓
  StockBubbleChart 컴포넌트
        ├─ 색상 매핑: sector_minor → palette (deterministic)
        ├─ 범례: 데이터에 등장한 sector_minor 목록 + "기타"
        └─ tooltip: 산업명(중) 라인 + Stage 라인(유지)
```

> [HARD] `_get_stock_meta`는 daily DB의 `stock_meta` 테이블을 조회한다. weekly DB 경로가 들어와도 fallback으로 daily를 시도하므로 `sector_minor` 컬럼은 daily DB의 `stock_meta`에 이미 존재해야 한다 (sector_detail_service.py L67이 동일 컬럼을 SELECT하여 사용 중 — 확인 완료).

---

## 4. 기존 코드 패턴 인용

### 4.1 sector_minor NULL 처리 — sector_detail_service.py L89-90 패턴

```python
for code, name, sector_minor, rs_12m, close, sma50, sma200, chg_1m in rows:
    key = sector_minor or "기타"
    sub_sector_stocks[key].append({ ... })
```

본 SPEC도 동일 패턴을 따른다: `sector_minor`가 `None`/빈 문자열인 종목은 모두 **"기타"** 그룹으로 묶고, 범례의 **마지막 항목**으로 배치하며 색상은 회색 계열(예: `#9CA3AF` 또는 `#6B7280`)을 고정 부여한다.

### 4.2 Stage 색상 매핑 — StockBubbleChart.tsx L16-22 (제거 대상)

```typescript
const STAGE_COLORS: Record<number, string> = {
  1: '#EAB308', // 바닥
  2: '#EF5350', // 상승
  3: '#F97316', // 천장
  4: '#42A5F5', // 하락
}
const DEFAULT_COLOR = '#6B7280' // 미분류
```

본 SPEC: 이 매핑은 **완전 제거**한다. Stage 정보 자체는 tooltip의 `Stage: S{n}` 라인을 통해 사용자에게 계속 노출되지만, 시각 인코딩(색상)에서는 사용하지 않는다.

### 4.3 ECharts 범례 + emphasis 패턴

ECharts `legend.selected` 상태는 항목 클릭 시 자동 토글된다. `legend.tooltip.show` 및 series `emphasis.itemStyle`을 통해 hover 시 dim/highlight를 구현할 수 있다. 모바일 터치에는 hover 이벤트가 없으므로 click-toggle만 동작한다(자연스러운 fallback).

ECharts API 참조(릴리스 5.x): `legend.type: 'plain' | 'scroll'`, `legend.selected: { [name]: boolean }`, series `emphasis.focus: 'series' | 'self' | 'none'`.

---

## 5. 색상 팔레트 후보

### 5.1 후보 비교

| 팔레트 | 색상 수 | 특성 | 본 SPEC 적합성 |
| --- | --- | --- | --- |
| ECharts 기본(`color` option default) | 9 (다크 친화) | ECharts 빌트인, 다크 배경에서 무난 | 적합. 추가 의존성 없음 |
| Tableau 10 | 10 | 카테고리컬 표준. 색맹 친화도 보통 | 적합. 8 초과 시 안전 |
| D3 `schemeCategory10` | 10 | D3 표준. tableau10과 유사 | 적합. tableau10과 거의 동일 |
| D3 `schemeTableau10` | 10 | tableau10 그대로 | 적합 |
| 한국식 (red/blue 강조) | 변동 | 상승/하락 의미가 이미 X축에 있음 — 색상에 의미 부여하면 혼란 | 부적합. **카테고리컬 팔레트 사용** |

### 5.2 [HARD] 본 SPEC 결정

- **카테고리컬 팔레트 = Tableau 10 변형 (10색)**.
  ```
  ['#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
   '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC']
  ```
- **"기타" 그룹 색상 = `#9CA3AF`** (gray-400) — 위 10색과 명확히 구분. 항상 범례 **마지막**.
- 종목 수 **내림차순**으로 sector_minor를 정렬 → 정렬된 순서대로 palette[0..9] 부여 → **결정성 보장**.
- **10 초과 시**: 10번째부터는 모두 "기타"에 흡수 (palette overflow → 회색 묶음). 데이터 분석상 한 sector_major 내 sector_minor가 10개를 넘는 경우는 드물지만, 안전 fallback으로 정의한다.

### 5.3 결정성(Determinism) 정의

- 같은 데이터셋(`StockBubbleResponse.stocks` 배열)에서 sector_minor → 색상 매핑은 항상 동일해야 한다.
- 매핑 함수: `f(stocks) = [(sector_minor, count) for ...] → sort by (-count, name asc) → take 10 → palette[i]`.
- 동률(count 같음) 시 sector_minor 문자열 오름차순 → 결정성 보장.
- 화면 새로고침/재렌더 시 색상 흔들림 없음.

---

## 6. 모바일 / 좁은 화면 대응

### 6.1 현재 grid 설정

`grid.right: 120` (StockBubbleChart.tsx L96). 우측 120px가 범례 영역. 데스크탑 기본 폭(>=1024px)에서는 충분하나, 모바일(<768px) 화면에서는 차트 폭이 좁아져 시각 정보 손실 위험.

### 6.2 본 SPEC 결정

- **데스크탑 (>=768px)**: 우측 수직 범례 유지 (orient: 'vertical', right: 10). 폭 120~140px.
- **모바일 (<768px)**: 범례를 **차트 하단**으로 이동 (orient: 'horizontal', bottom: 4, type: 'scroll'). `grid.right`는 60으로 축소, `grid.bottom`은 80으로 확장.
- **hover emphasis는 데스크탑 전용**. 모바일에서는 click-toggle만 동작(ECharts 기본 동작).
- 브레이크포인트 감지: `window.matchMedia('(max-width: 767px)')` + `useEffect` 또는 ECharts `media` query 옵션.

### 6.3 Lesson #1 / #2 반영

- **Lesson #1 (hover-only UX 라이브 검증)**: 본 SPEC은 hover를 **enhancement**로만 사용하며 hover 없이도 동작하는 click-toggle을 baseline으로 둔다. 모바일 fallback이 사전 정의되어 있어 reverse amendment 위험 낮음.
- **Lesson #2 (prominence priority)**: 차트 영역 > 범례 영역 prominence를 본 SPEC §3 / plan.md §2에 명시한다.

---

## 7. 라이브 사용 가설 & 성능 baseline (Lesson #7)

### 7.1 라이브 사용 가설

> 사용자는 sector_major 클릭으로 종목 버블 드릴다운에 진입한 직후, **동일 색상 군집**으로 같은 sector_minor 종목군을 즉시 식별한다. RS Rating × 가격변동률 평면에서 **같은 색상 군이 어떤 사분면에 몰려 있는가**를 보고 sub-sector 단위 강세/약세를 한눈에 파악한다. tooltip에서 산업명(중) 라벨로 군집 정체성을 확인한다.

- **사용 빈도**: chart grid 방문 시마다 (일일 단위)
- **만족도 지표**: (i) 같은 색상 군집을 5초 이내에 인지 가능, (ii) tooltip의 산업명(중) 라벨이 명확, (iii) 범례에서 sub-sector 클릭으로 그룹 격리 가능
- **라이브 검증 시점**: ship 후 사용자 자체 평가 1회 (1일 사용 후 회고)

### 7.2 성능 baseline + 목표

- **Baseline 측정 가이드** (사용자가 Plan 단계에서 직접 측정 후 본 항목 보강 가능):
  1. Chrome DevTools → Performance 탭 열기
  2. 종목 수 200+ 섹터(예: "IT") 드릴다운 진입
  3. ECharts SVG 첫 렌더 시점 측정 (Recording start → onChartReady 사이의 main thread time)
  4. 3회 측정 후 P95 기록
- **목표**: 변경 후 P95 < baseline + 20% regression. 종목 수 200+ 케이스 필수 검증 (AC-9).
- **위험 요소**: sector_minor 색상 매핑 함수가 O(N log N)으로 종목 수에 선형 (Top 10 selection sort 포함). 200 종목에서 1ms 미만 예상.

### 7.3 SPEC ID ↔ UI 매핑 표

| UI 요소 | 변경 유형 | 위치 | 비고 |
| --- | --- | --- | --- |
| 우측 수직 범례 (데스크탑) | **REPLACE** | StockBubbleChart.tsx L125-137 | Stage S1~S4 + 미분류 → sector_minor N개 + "기타" |
| 하단 수평 범례 (모바일) | **NEW** | 동일 컴포넌트, 미디어 쿼리 분기 | 모바일 폭에서 출현 |
| 범례 클릭 (legend.selected toggle) | **NEW 상호작용** | ECharts 기본 동작 | 그룹 표시/숨김 |
| 범례 hover (emphasis dim others) | **NEW 상호작용 (데스크탑)** | series.emphasis.focus | 모바일 비활성 |
| Bubble fill 색상 매핑 | **REPLACE** | L76 (itemStyle.color) | Stage → sector_minor |
| Tooltip `산업명(중): {value}` 라인 | **NEW** | L173 부근 (Stage 라인 위 또는 아래) | Stage 라인 유지 |
| Tooltip `Stage: S{n}` 라인 | **KEEP** | L173 (그대로) | Stage 정보 보존 (사용자 결정) |
| 5-항목 Stage 범례 | **REMOVE** | L125-137 (대체 후 사라짐) | "S1 바닥" / "S2 상승" / "S3 천장" / "S4 하락" / "미분류" 사라짐 |

### 7.4 Rollback 시나리오

- 본 SPEC은 frontend + backend schema 양쪽을 건드린다. backend 응답에 `sector_minor` 필드가 추가되어도 기존 frontend(필드 무시)와 호환된다 → backend 단독 ship 안전.
- 문제 발생 시: feature branch (`feat/SPEC-SECTOR-MINOR-COLOR-001`)를 archive 하고 main으로 즉시 revert. SPEC commit이 단일 PR이면 1 commit revert. branch archive 시 retrospective.md 첨부.
- 데이터 손상 없음 (DB 스키마 변경 없음, SELECT 확장만).

---

## 8. Lesson #4 — 적용 가능성

dataframe propagation 패턴(themes_df → strong_themes_df) 같은 derived dataframe이 본 SPEC 데이터 흐름에 **존재하지 않는다**:

- backend는 DB `SELECT name, code, sector_major, sector_minor, market, market_cap` 직후 dict 변환 → Pydantic model → JSON. 중간 dataframe 가공 없음.
- 따라서 Lesson #4의 SPEC 체크 항목 ("derived dataframe 컬럼 propagation")은 **N/A**. 다만 본 research.md에서 "no derived dataframe" 사실을 명시 기록한다.

---

## 9. 사전 존재 불일치 / 잠재 위험

- **stock_meta.sector_minor 컬럼 부재 위험 (LOW)**: `sector_detail_service.py:67`이 이미 동일 컬럼을 SELECT하여 사용 중이므로 컬럼은 daily DB에 존재한다고 가정 가능. 만약 레거시 DB에 누락된 경우 OperationalError 발생 → 사용자가 `POST /api/db/update`로 stock_meta 재빌드 필요. 본 SPEC 범위에서는 컬럼 존재 가드 추가하지 않는다(Exclusions).
- **legacy 종목 sector_minor NULL (MEDIUM)**: 일부 종목은 `sector_minor`가 NULL/빈 문자열일 수 있다. **"기타" fallback**으로 처리 (sector_detail_service 패턴 동일).
- **palette overflow (LOW)**: sector_minor 종류가 10을 초과하면 10번째 이하는 "기타"로 흡수. 데이터 분석상 단일 sector_major 내 sector_minor 10 초과는 드묾.
- **모바일 grid right 충돌 (MEDIUM)**: 미디어 쿼리 분기로 완화.
- **ECharts visualMap stage piecewise 잔존 (LOW)**: 현재 코드는 visualMap을 사용하지 않고 `data[i].itemStyle.color`로 직접 칠한다. 잔존 visualMap 없음 확인 완료.

---

## 10. 결론

본 SPEC은 backend 2~3 파일 + frontend 2 파일의 좁은 변경면을 가진다. 데이터 모델 확장(StockBubble dataclass + Pydantic schema에 `sector_minor` 추가)과 frontend 시각화 로직 교체(STAGE_COLORS → sector_minor palette + 동적 범례 + tooltip 한 줄)로 구성된다. development_mode: tdd 에 따라 acceptance 기준은 RED 테스트로 작성 가능하며, AC-9 결정성 round-trip + AC-perf 200종목 회귀 게이트가 핵심 품질 게이트다.
