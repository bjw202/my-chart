---
id: SPEC-STOCK-TOOLTIP-PRODUCT-001
version: 1.0.0
status: draft
created: 2026-05-27
updated: 2026-05-27
author: jw
priority: medium
issue_number: 0
---

# SPEC-STOCK-TOOLTIP-PRODUCT-001: StockBubbleChart tooltip 주요제품 라인 추가

## HISTORY

| 버전 | 날짜 | 작성자 | 변경 내용 |
| --- | --- | --- | --- |
| 1.0.0 | 2026-05-27 | jw | 초기 SPEC 작성. 직전 SPEC-SECTOR-MINOR-COLOR-001 v1.0.1과 정확히 동일한 데이터 전파 패턴(SELECT → dataclass → Pydantic → TS → tooltip). 본 SPEC은 stock_meta.product(원본 컬럼 "주요제품") 값을 백엔드 응답 모델 + 프론트엔드 타입 + StockBubbleChart tooltip 라인으로 노출한다. 산업명(중) 라인은 보존(AC-8 회귀 방지), Stage 라인 보존, sector_minor 기준 색상 매핑 보존(REQ-SBM-004/009 회귀 방지). development_mode: tdd. issue_number: 0 (GitHub integration OFF). Lesson #1 회피: 별도 SPEC으로 분리(직전 SPEC v1.0.0 → v1.0.1 amendment 1회 후 amendment chain 회피). Lesson #4 N/A (no derived dataframe). Lesson #5 N/A (캐시 없음, 매번 fetch — 직전 SPEC과 동일). |

---

## 1. Environment (환경)

### 1.1 프로젝트 컨텍스트

- **프로젝트**: KR Stock Screener (FastAPI + React + SQLite)
- **선행 SPEC**: `.moai/specs/SPEC-SECTOR-MINOR-COLOR-001/` (v1.0.1, 2026-05-27 머지). 본 SPEC은 그 위에 추가되는 독립 변경(별도 SPEC, 별도 ship).
- **목표**: Sector Analysis → Bubble 탭 → 섹터 클릭 시 등장하는 종목 드릴다운 뷰(`StockBubbleChart`)의 hover tooltip에 "주요제품" 라인을 추가한다. 데이터 원천은 `stock_meta.product`(영문 컬럼명, 원본 한국어 컬럼명 "주요제품").
- **배포 환경**: localhost 전용, 클라우드 미사용
- **개발 방법론**: TDD (`.moai/config/sections/quality.yaml`의 `development_mode: tdd`) — acceptance 기준은 구체·검증 가능해야 하며 RED 테스트를 유도한다
- **변경 성격**: BROWNFIELD (기존 컴포넌트 + 응답 모델 확장)
- **데이터 흐름**: 직전 SPEC과 동일 패턴 — DB SELECT → dict → dataclass → Pydantic → JSON → TS. 중간 derived dataframe 없음 (Lesson #4 N/A).

### 1.2 기술 스택

- **Backend**: Python 3.13+, sqlite3, FastAPI, Pydantic v2
- **Frontend**: React 18+, TypeScript, ECharts (echarts-for-react), Vitest + React Testing Library
- **Testing**: pytest (백엔드), Vitest (프론트), 커버리지 85% 이상

### 1.3 기존 코드 현황 (직전 SPEC 패턴 인용)

| 경로 | 역할 | 본 SPEC에서의 역할 |
| --- | --- | --- |
| `my_chart/analysis/sector_advanced.py` `_get_stock_meta` (직전 SPEC v1.0.1로 sector_minor 추가됨) | stock_meta SELECT | SELECT에 `product` 추가, 결과 dict에 키 채움 [필수] |
| `my_chart/analysis/sector_advanced.py` `StockBubble` dataclass | 종목 버블 dataclass | `product: str \| None = None` 필드 추가 [필수] |
| `my_chart/analysis/sector_advanced.py` `compute_stock_bubble` | 종목 버블 계산 본체 | `StockBubble` 생성 시 `product` 전달 [필수] |
| `backend/schemas/sector_advanced.py` `StockBubbleItem` | Pydantic 응답 모델 | `product: str \| None = None` 필드 추가 [필수] |
| `backend/services/sector_advanced_service.py` `get_stock_bubble` | dataclass → Pydantic 변환 | 변환 시 `product=s.product` 전달 [필수] |
| `frontend/src/types/bubble.ts` `StockBubbleItem` | 백엔드 응답 타입 미러 | `product: string \| null` 필드 추가 [필수] |
| `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` | 종목 버블 차트 컴포넌트 | tooltip formatter에 "주요제품" 라인 추가, data tuple에 product 인덱스 확장 [필수] |
| `backend/services/meta_service.py` L229 (`"product": srow.get("주요제품")`) | meta_service 운영 경로 | 동일 영문 키 `product` 채택 — 일관성 근거 |

### 1.4 핵심 제약

- **[HARD] 산업명(중) 라인 보존**: 직전 SPEC REQ-SBM-008(`산업명(중): {sector_minor or '기타'}`)은 그대로 유지된다. 본 SPEC은 그 라인 아래에 "주요제품" 라인을 추가한다.
- **[HARD] Stage 라인 보존**: 직전 SPEC에서 결정한 Stage tooltip 라인 보존 규칙(`Stage: S{n} ({stage_detail})`)을 따른다.
- **[HARD] sector_minor 색상 매핑 보존**: 본 SPEC은 색상 인코딩에 영향을 주지 않는다(REQ-SBM-004/009 회귀 금지). itemStyle.color는 sector_minor 기준 유지.
- **[HARD] XSS hardening**: product 값은 직전 SPEC에서 도입된 (혹은 기존의) `escapeHtml` 헬퍼로 HTML escape하여 tooltip formatter HTML에 삽입한다. (직전 SPEC research.md에 escape 헬퍼 도입 흔적이 있으면 재사용, 없으면 본 SPEC plan.md에서 도입 결정. — plan.md 참조)
- **[HARD] NULL/빈 product 처리**: product가 NULL이거나 빈 문자열이면 tooltip은 `주요제품: —` (em-dash 또는 hyphen)로 표시한다(라인 자체는 표시).
- **[HARD] 명명 컨벤션**: 백엔드 dataclass/Pydantic/TS 필드명은 `product`(영문). meta_service.py:229와 일관. tooltip 표시명은 "주요제품"(한국어, documentation: ko 설정 준수).
- **[HARD] 적용 대상 한정**: 종목 드릴다운 뷰(`StockBubbleChart.tsx`) 전용. SectorBubbleChart / BubbleChart / RRG / Bump / 히스토리는 변경 없음.

---

## 2. Assumptions (가정)

- A1. `daily DB stock_meta.product` 컬럼은 이미 존재한다. `backend/services/meta_service.py:229`가 `srow.get("주요제품")` 패턴으로 운영 중이며, 본 SPEC 범위에서 컬럼 존재 가드는 추가하지 않는다(Exclusions).
- A2. 적용 대상은 **종목 드릴다운 뷰(**`StockBubbleChart.tsx`**)뿐**이다. 대분류 섹터 버블(`SectorBubbleChart.tsx`), `BubbleChart.tsx`, RRG / Bump / 히스토리 / 트리맵 컴포넌트는 범위 밖.
- A3. 일부 종목은 `product`가 NULL/빈 문자열일 수 있다 → `주요제품: —` 표시(라인은 노출).
- A4. ECharts SVG 렌더러 그대로 사용. 변경 없음.
- A5. backend 응답에 `product` 필드가 추가되어도 기존 frontend(필드 무시)와 호환된다 → backend 단독 ship 안전(rollback 단순화).
- A6. 백엔드 데이터 흐름에 derived dataframe propagation 없음 (DB SELECT → dict → Pydantic). Lesson #4 SPEC 체크 N/A.
- A7. 사용 패턴(Lesson #5 인용): chart grid 방문 시마다 사용. 캐시 없음. backend `/sectors/{sector_name}/bubble` 응답을 매번 fetch — 직전 SPEC과 동일.
- A8. tooltip 라인 추가 1줄은 ECharts SVG 렌더 비용에 무시 가능한 영향을 준다(< 1ms). 별도 성능 baseline 측정은 본 SPEC에서 강제하지 않는다(직전 SPEC AC-12가 유효한 상한).
- A9. `escapeHtml` 헬퍼는 직전 SPEC GREEN 단계에서 tooltip의 sector_minor 라인에 도입되었거나, 본 SPEC plan.md에서 신규 도입하여 sector_minor + product 양쪽에 적용한다(plan.md 결정).

---

## 3. Requirements (요구사항, EARS)

### REQ-STP-001 (Ubiquitous) — 백엔드 응답 모델 확장

The `StockBubbleItem` Pydantic response model **shall** include the optional field `product` (원본 stock_meta 컬럼 "주요제품"), typed as `str | None`, populated from `stock_meta.product`.

- 검증: `StockBubbleItem.model_fields`에 `product` 존재, 타입 `str | None`. 응답 JSON에 `"product"` 키 포함.
- 매핑: AC-1.

### REQ-STP-002 (Event-Driven) — 종목 버블 응답 빌드 시 product 채움

**When** `GET /api/sectors/{sector_name}/bubble` is invoked, the system **shall** load `product` for each stock from `stock_meta` and include it in the corresponding `StockBubbleItem` of the response.

- 구현 위치(HOW, plan.md 참조): `_get_stock_meta` SELECT 확장 → `compute_stock_bubble`에서 `StockBubble.product` 채움 → `get_stock_bubble` 서비스에서 Pydantic 변환 시 전달. (직전 SPEC sector_minor 패턴과 동일)
- 검증: 응답의 각 stock 항목에 product 필드 존재, 값은 해당 종목의 stock_meta.product와 일치(또는 None).
- 매핑: AC-1, AC-2.

### REQ-STP-003 (Ubiquitous) — Frontend 타입 미러

The frontend `StockBubbleItem` TypeScript interface **shall** include the field `product: string | null`, mirroring the backend response model.

- 검증: `frontend/src/types/bubble.ts`의 `StockBubbleItem`에 `product: string | null` 존재.
- 매핑: AC-3.

### REQ-STP-004 (Ubiquitous) — Tooltip 주요제품 라인 추가

The bubble tooltip **shall** include a `주요제품: {product or "—"}` line, in addition to the existing `산업명(중): {sector_minor or "기타"}` and `Stage: S{n} ({stage_detail})` lines which **shall be preserved**.

- 위치: 산업명(중) 라인의 **다음 줄(아래)** — Stage 라인보다는 위, 또는 산업명(중) 라인 바로 다음에 표시한다(plan.md에서 확정). 직관: 산업명(중) → 주요제품 → Stage 순서로 종목 정성 정보가 인접.
- NULL/빈 product: `주요제품: —` (em-dash 또는 hyphen) 라인을 표시 — 라인 자체는 노출.
- 검증: tooltip HTML에 `주요제품:` 문자열 포함, product 값 표시. 산업명(중) 라인 + Stage 라인도 동일하게 표시(회귀 방지).
- 매핑: AC-4, AC-5.

### REQ-STP-005 (Unwanted Behavior) — Stage / sector_minor 색상 인코딩 회귀 금지

**If** any change introduces Stage-based or non-sector_minor-based fill color, or removes the existing `산업명(중)` tooltip line, **then** the implementation **shall not** ship — sector_minor 기준 색상 매핑 및 산업명(중) tooltip 라인은 직전 SPEC(SPEC-SECTOR-MINOR-COLOR-001)의 결정사항이며 본 SPEC은 이를 보존한다.

- 검증: option.series[0].data[i].itemStyle.color는 sector_minor 기준(직전 AC-4/AC-9 회귀 재실행). tooltip에 `산업명(중):` 라인 여전히 포함(직전 AC-8 회귀 재실행).
- 매핑: AC-6.

### REQ-STP-006 (Ubiquitous) — Tooltip XSS hardening

The product value **shall** be HTML-escaped before insertion into the tooltip formatter output. The escape mechanism **shall** match the escape mechanism used for the existing `sector_minor` tooltip line (consistency with SPEC-SECTOR-MINOR-COLOR-001 — escape 헬퍼가 부재한 경우 본 SPEC plan.md에서 신규 도입하여 sector_minor + product 양쪽에 적용).

- 검증: product가 `<script>alert('xss')</script>` 같은 페이로드일 때 tooltip HTML 결과에 `&lt;script&gt;` 등 escape된 문자열만 포함, raw `<script>` 미포함.
- 매핑: AC-7.

### REQ-STP-007 (Ubiquitous) — 명명 컨벤션 (meta_service 일관성)

The backend dataclass field, Pydantic field, and frontend TypeScript field for the 주요제품 value **shall** all be named `product` (영문, 단수, lowercase), matching the existing operational pattern in `backend/services/meta_service.py:229` (`"product": srow.get("주요제품")`).

- 검증: 코드베이스에 새로 추가되는 식별자는 모두 `product`(영문). `main_product` 또는 다른 변형은 사용하지 않는다.
- 매핑: AC-1, AC-3 (필드명 단언).

---

## 4. Exclusions (What NOT to Build)

본 SPEC은 다음을 **구현하지 않는다**:

- **대분류 섹터 버블(**`SectorBubbleChart.tsx`**)**: 변경 없음. 본 SPEC은 종목 드릴다운 뷰 전용.
- `BubbleChart.tsx` **(별도 컴포넌트)**: 변경 없음.
- **RRG / Bump / 히스토리 / 트리맵 / SectorRankingTable / SectorDetailPanel**: 변경 없음.
- **그리드 결과 테이블 / StockTable.tsx / StockExplorer**: 변경 없음. 본 SPEC은 StockBubbleChart 단일 차트 컴포넌트 한정.
- **stock_meta.product 컬럼 존재 가드**: 정상 경로 전제(`meta_service.py:229`가 운영 중). 컬럼 누락 시 OperationalError → 사용자가 DB 재빌드 필요(직전 SPEC research.md §9 동일).
- **sector_minor 색상 매핑 / 범례 / hover / 모바일 fallback 재변경**: 직전 SPEC-SECTOR-MINOR-COLOR-001의 결정사항을 그대로 보존. 본 SPEC은 그 위에 tooltip 라인 1줄을 추가할 뿐 색상·범례 로직은 손대지 않는다.
- **product 기반 필터링 / 그룹핑 / 검색**: tooltip 표시만. 사용자 인터랙션(클릭, 필터)은 본 SPEC 범위 밖. 후속 SPEC 대상.
- **product 기반 색상 인코딩**: itemStyle.color는 sector_minor 기준 그대로(REQ-STP-005 회귀 금지).
- **backend 응답에 product 길이 truncation / abbreviation**: tooltip 표시 시점에 컴포넌트가 자체 판단(긴 product 문자열은 CSS overflow 또는 그대로 표시 — plan.md 결정). backend는 raw 값을 그대로 응답.
- **i18n / 다국어 지원**: tooltip 라벨 "주요제품"은 documentation: ko 설정에 따른 한국어 고정. 다국어 토글 없음.
- **차트 축 / grid / 버블 크기 정규화 / Top 20 라벨 규칙**: 모두 기존 동작 유지.
- **성능 baseline 재측정**: tooltip 1줄 추가는 SVG 렌더 비용에 무시 가능한 영향. 직전 SPEC AC-12(P95 < baseline * 1.20) 상한이 유효. 본 SPEC은 별도 성능 게이트를 강제하지 않는다.

---

## 5. Specifications (수용 기준 연결)

상세 Given/When/Then 시나리오, 에지케이스, 품질 게이트는 `acceptance.md` 참조. 구현 작업 분해, 기술 노트, 리스크, mx_plan은 `plan.md` 참조.

### Traceability (REQ ↔ AC)

| REQ | 매핑 AC |
| --- | --- |
| REQ-STP-001 | AC-1 |
| REQ-STP-002 | AC-1, AC-2 |
| REQ-STP-003 | AC-3 |
| REQ-STP-004 | AC-4, AC-5 |
| REQ-STP-005 | AC-6 |
| REQ-STP-006 | AC-7 |
| REQ-STP-007 | AC-1, AC-3 |
