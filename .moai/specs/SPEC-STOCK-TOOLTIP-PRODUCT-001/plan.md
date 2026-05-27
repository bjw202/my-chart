# SPEC-STOCK-TOOLTIP-PRODUCT-001 Plan — 구현 계획

> [DELTA] 마커 범례: `[EXISTING]` 변경 없는 기존 코드 / `[MODIFY]` 기존 파일 수정 / `[NEW]` 신규 추가.
> 본 SPEC은 BROWNFIELD 변경이며 `development_mode: tdd` (RED → GREEN → REFACTOR).
> 직전 SPEC-SECTOR-MINOR-COLOR-001 v1.0.1 패턴과 정확히 동일 — 새로운 결정 사항은 §1.3 escape 헬퍼 재사용/도입 1건뿐.

---

## 1. 기술 노트

### 1.1 백엔드 (Python)

- **`_get_stock_meta` (sector_advanced.py, 직전 SPEC에서 sector_minor 추가됨)**: SELECT 절에 `product` 컬럼 추가. 결과 dict의 value에 `"product": product or None` 키 추가. 직전 SPEC SELECT 확장과 정확히 동일 패턴.
  - 직전 SPEC SELECT 형태: `"SELECT name, code, sector_major, sector_minor, market, market_cap FROM stock_meta"`
  - 본 SPEC SELECT 형태: `"SELECT name, code, sector_major, sector_minor, product, market, market_cap FROM stock_meta"` (product 추가, 컬럼 순서는 DB 실제 순서를 따른다 — column-name 기반 unpack 권장).
  - **[HARD] column-name 기반 unpack 권장**: 최근 commit `8437cab fix(db): daily.py INSERT를 column-name 기반으로` 학습 — positional unpack은 컬럼 시프트 부패 위험. `cursor.description`을 이용한 dict-row 또는 `sqlite3.Row` row factory 사용 검토. 단, 직전 SPEC이 positional unpack을 유지했다면 본 SPEC도 동일 패턴 유지(consistency 우선).
  - fallback 경로(daily DB) 동일 SELECT 사용 — paths_to_try 루프 단일 SELECT.
- **`StockBubble` dataclass (sector_advanced.py)**: 신규 필드 `product: str | None = None` 추가. 기본값 `None`. (직전 SPEC `sector_minor` 추가와 정확히 동일 패턴.)
- **`compute_stock_bubble` (sector_advanced.py)**: `results.append(StockBubble(..., product=meta.get("product")))` 추가.
- **`StockBubbleItem` Pydantic 모델 (schemas/sector_advanced.py)**: `product: str | None = None` 필드 추가. Pydantic v2 디폴트 None.
- **`get_stock_bubble` 서비스 (sector_advanced_service.py)**: comprehension에 `product=s.product` 추가(한 줄).

### 1.2 프론트엔드 (TypeScript / React / ECharts)

- **타입 (types/bubble.ts)**: `product: string | null` 추가(직전 SPEC sector_minor 추가 라인 바로 아래 위치 권장).
- **`StockBubbleChart.tsx` data tuple 인덱스 확장**: 직전 SPEC이 sector_minor를 series.data tuple에 추가(예: index 8)했다면 본 SPEC은 product를 다음 인덱스(예: index 9)로 추가. ECharts dimensions/encode 설정이 인덱스 기반이라면 기존 dimensions 길이 +1.
- **`StockBubbleChart.tsx` tooltip formatter 수정**: 직전 SPEC이 추가한 `산업명(중):` 라인 **바로 아래**에 `주요제품: {product or '—'}` 라인 삽입.
  - 직전 SPEC formatter 구조(추정):
    ```typescript
    const lines = [
      `<b>${escapeHtml(name)}</b>`,
      `산업명(중): ${escapeHtml(sectorMinor || '기타')}`,  // 직전 SPEC 추가
      `Stage: S${stage} (${escapeHtml(stageDetail || '')})`,
      // ... 가격변동 / RS / 거래대금
    ]
    ```
  - 본 SPEC 후 구조:
    ```typescript
    const lines = [
      `<b>${escapeHtml(name)}</b>`,
      `산업명(중): ${escapeHtml(sectorMinor || '기타')}`,
      `주요제품: ${escapeHtml(product || '—')}`,  // ← 본 SPEC 추가
      `Stage: S${stage} (${escapeHtml(stageDetail || '')})`,
      // ... 가격변동 / RS / 거래대금
    ]
    ```
- **`escapeHtml` 헬퍼 재사용/도입 결정**:
  - **케이스 A — 직전 SPEC GREEN 단계에서 escapeHtml이 이미 도입됨**: 그대로 재사용. 추가 작업 없음. (acceptance.md AC-7 단언에서 escape 결과만 확인.)
  - **케이스 B — 직전 SPEC GREEN에서 escape 헬퍼가 도입되지 않았음(React가 string 반환 시 자동 escape 가정에 의존)**: ECharts tooltip formatter는 raw HTML 문자열을 반환하므로 React auto-escape이 적용되지 않는다 — XSS 위험. 본 SPEC GREEN 단계에서 `escapeHtml(value: string | null | undefined): string` 헬퍼를 `frontend/src/utils/escapeHtml.ts`(신규)에 도입하고 sector_minor + product 양쪽에 일관 적용. (직전 SPEC의 sector_minor 라인도 동일 헬퍼로 변경 — 정밀 수정, drift 1줄.)
  - **[HARD] 결정 기준**: 본 SPEC RED 테스트 작성 시점에 `frontend/src/utils/escapeHtml.ts` 존재 여부 + StockBubbleChart.tsx에서 `escapeHtml(` 호출 존재 여부를 확인. 두 가지 모두 true면 케이스 A, 그 외 케이스 B. 케이스 B인 경우 본 SPEC plan.md §1.3에 Task 7a로 escapeHtml 헬퍼 신규 작성을 추가.

### 1.3 [HARD] 결정 사항

- **필드명**: `product` (영문, 단수, lowercase). meta_service.py:229의 `srow.get("주요제품")` → `"product": srow.get("주요제품")` 매핑과 일관.
- **tooltip 라벨**: "주요제품" (한국어, documentation: ko). 다국어 토글 없음.
- **NULL/빈 표시**: `주요제품: —` (em-dash, U+2014). 라인 자체는 표시. (사용자 결정 — 라인 미표시 옵션은 채택하지 않음. 일관된 tooltip 행 수가 UX에 유리.)
- **라인 순서**: 종목명 → 산업명(중) → 주요제품 → Stage → 가격변동 / RS Rating / 거래대금. 종목 정성 정보(분류 + 비즈니스)를 인접 배치.
- **XSS hardening**: product + sector_minor + stage_detail + name 모두 escapeHtml 통과(케이스 B인 경우 sector_minor + name + stage_detail에도 escape 일관 적용).
- **성능 baseline**: 본 SPEC은 별도 P95 측정을 강제하지 않는다. tooltip 라인 1줄 추가는 SVG 렌더 비용 무시 가능. 직전 SPEC AC-12 상한이 유효.

---

## 2. 작업 분해 (파일별, [DELTA] 마커)

### Task 1 — [MODIFY] `backend/tests/test_sector_advanced.py` (RED, 응답 모델 + product 노출)

- [NEW] `test_stock_bubble_response_includes_product`: `StockBubbleItem.model_fields`에 `product` 존재 검증 (AC-1).
- [NEW] `test_compute_stock_bubble_propagates_product`: 합성 stock_meta(`product` 키 포함)로 `compute_stock_bubble` 호출 → 결과 각 `StockBubble.product` 값이 stock_meta와 일치 (AC-1).
- [NEW] `test_compute_stock_bubble_product_null_fallback`: stock_meta.product가 NULL/빈 종목 → `StockBubble.product == None` (AC-2 sub).
- [NEW] `test_get_stock_meta_select_includes_product`: 합성 daily DB(`stock_meta` 테이블에 `product` 컬럼 포함)로 `_get_stock_meta` 호출 → 반환 dict의 각 value에 `"product"` 키 존재, DB 값과 일치 (AC-2).
- 기존 테스트(직전 SPEC v1.0.1 compute_stock_bubble 테스트 + sector_minor 전파 테스트)는 회귀 없음 확인 — `_get_stock_meta` SELECT 확장은 기존 키(`Code`, `sector_major`, `sector_minor`, `시장구분`, `market_cap`)에 영향 없음.

### Task 2 — [MODIFY] `my_chart/analysis/sector_advanced.py` (GREEN, dataclass + SELECT + 전파)

- `_get_stock_meta`: SELECT 절에 `product` 추가 (직전 SPEC sector_minor 다음 위치, DB 실제 컬럼 순서 우선). 루프 unpack 확장. 결과 dict에 `"product": product or None` 추가.
- `StockBubble` dataclass: `product: str | None = None` 필드 추가 (직전 SPEC `sector_minor` 필드 바로 아래 권장).
- `compute_stock_bubble`: `results.append(StockBubble(..., product=meta.get("product")))` 추가.
- [HARD] 다른 호출처(`compute_sector_bubble`, `compute_treemap_data`)는 stock_meta dict의 신규 키 `"product"`를 사용하지 않으므로 영향 없음 — 검증 필요.

### Task 3 — [MODIFY] `backend/schemas/sector_advanced.py` (GREEN, 응답 모델 필드)

- `StockBubbleItem`: `product: str | None = None` 추가 (직전 SPEC `sector_minor` 필드 바로 아래 권장). 다른 필드 변경 없음.

### Task 4 — [MODIFY] `backend/services/sector_advanced_service.py` (GREEN, 변환)

- `get_stock_bubble`: comprehension에 `product=s.product` 추가 (한 줄, 직전 SPEC `sector_minor=s.sector_minor` 바로 아래).

### Task 5 — [MODIFY] `frontend/src/components/SectorAnalysis/__tests__/StockBubbleChart.test.tsx` (RED, tooltip 라인 + escape)

- [NEW] AC-3 mirror: `StockBubbleItem` 타입에 `product` 존재(컴파일 시 확인) — 직전 SPEC 테스트와 동일 패턴.
- [NEW] AC-4: tooltip formatter 호출 결과 문자열에 `주요제품: ` 포함, product 값(예: "반도체용 검사장비") 표시. 라인 위치는 `산업명(중):` 라인 다음, `Stage:` 라인 이전(문자열 인덱스 비교로 단언).
- [NEW] AC-5: product가 null/빈 → tooltip에 `주요제품: —` 라인 표시 (라인 자체는 노출).
- [NEW] AC-6 회귀 방지: 동일 시나리오에서 `option.series[0].data[i].itemStyle.color`가 sector_minor 기준임을 재단언(직전 SPEC AC-4 회귀 가드). tooltip에 `산업명(중):` 라인 여전히 포함(직전 SPEC AC-8 회귀 가드).
- [NEW] AC-7 XSS: product가 `<script>alert('xss')</script>` 페이로드 → tooltip HTML 결과에 `&lt;script&gt;` 등 escape된 문자열 포함, raw `<script>` 미포함.

### Task 6 — [MODIFY] `frontend/src/types/bubble.ts` (GREEN, 타입 미러)

- `StockBubbleItem`: `product: string | null` 추가 (직전 SPEC `sector_minor` 필드 바로 아래).

### Task 7 — [MODIFY] `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` (GREEN, tooltip 라인 추가)

- **추가**: tooltip formatter `lines` 배열에 `산업명(중):` 라인 다음 위치에 `주요제품: {escapeHtml(product || '—')}` 라인 1줄 추가.
- **수정**: data tuple(또는 dimensions encode) 에 product를 추가 — 직전 SPEC sector_minor 인덱스 다음. tooltip formatter 내부에서 `params.data[productIndex]`로 접근 가능하도록 인덱스 갱신.
- **NULL 처리**: `product || '—'` 패턴(빈 문자열/null 모두 em-dash로 표시).
- **회귀 보존**: itemStyle.color 로직(sector_minor 기준) 변경 없음. legend.data 변경 없음. grid / orient / hover emphasis 변경 없음. Stage / RS / 가격변동 라인 변경 없음.

### Task 7a — [NEW or REUSE] `frontend/src/utils/escapeHtml.ts` (조건부)

- **케이스 A (직전 SPEC에 이미 escapeHtml 존재)**: SKIP. 본 Task 자체 미실행.
- **케이스 B (직전 SPEC에 escapeHtml 부재)**:
  - [NEW] `frontend/src/utils/escapeHtml.ts` 작성: `export function escapeHtml(value: string | null | undefined): string` — `&`, `<`, `>`, `"`, `'` 5문자 escape.
  - [NEW] unit test `frontend/src/utils/__tests__/escapeHtml.test.ts`: 5문자 각각 escape + null/undefined fallback.
  - [MODIFY] `StockBubbleChart.tsx`의 sector_minor / name / stage_detail tooltip 라인도 escapeHtml 통과로 변경(drift 최소화 — 같은 컴포넌트 같은 formatter 함수 내부 일관성 확보).

### Task 8 — [REFACTOR] 회귀 검증 + 라이브 smoke

- Vitest 전체 통과 + pytest 전체 통과 확인 (backend/tests + frontend/__tests__).
- 직전 SPEC 회귀 게이트 재실행:
  - AC-4 (sector_minor 색상 일치).
  - AC-8 (산업명(중) tooltip 라인 보존).
  - AC-9 (결정성 round-trip).
  - AC-10 (Stage 색상 회귀 방지 — `STAGE_COLORS` 식별자 정적 검사).
- live smoke test: Sector Analysis → Bubble 탭 → "IT" 또는 "반도체" 같은 큰 섹터 클릭 → 종목 hover → tooltip에 `종목명 → 산업명(중) → 주요제품 → Stage` 순서로 4개 정성 라인 + 기존 가격변동/RS/거래대금 라인 확인. 적어도 1개 종목은 product NULL → `주요제품: —` 표시 확인.

### [EXISTING] 변경 없음

- `backend/routers/sectors.py` (`stock_bubble` 엔드포인트).
- `frontend/src/api/bubble.ts` (타입 자동 반영).
- `SectorBubbleChart.tsx`, `BubbleChart.tsx`, `BumpChart.tsx`, `RRGChart.tsx`, `SectorRankingTable.tsx`, `SectorDetailPanel.tsx`.
- `StockExplorer/StockTable.tsx` (다른 컨텍스트).
- `daily DB` 스키마 (이미 product 컬럼 존재 — meta_service.py:229 운영 중).
- `StockBubbleChart.tsx`의 itemStyle.color 매핑 / legend / hover emphasis / grid / mobile fallback (모두 직전 SPEC 결정 보존).

---

## 3. 마일스톤 (우선순위 기반, 시간 추정 없음)

1. **Priority High — 백엔드 응답 모델 (Task 1, 2, 3, 4)**: product 응답 노출. 프론트엔드 작업의 선행. backend 단독 ship 가능(필드 추가만, 기존 frontend는 무시 가능).
2. **Priority High — 프론트엔드 tooltip 라인 (Task 5, 6, 7, 7a)**: 타입 미러 + tooltip 라인 추가 + (조건부) escapeHtml 헬퍼. backend Task 1~4 완료 후.
3. **Priority Medium — 회귀 검증 + 라이브 smoke (Task 8)**: Vitest + pytest 통과, 직전 SPEC 회귀 게이트 재실행, 라이브 화면 확인.

순서: 백엔드 응답 모델 → 프론트엔드 tooltip 라인 → 회귀 + 라이브 smoke. backend 단독 ship → frontend 단독 ship 순차 가능(rollback 단순화).

---

## 4. 리스크 분석

| 리스크 | 심각도 | 완화 |
| --- | --- | --- |
| **direct SPEC over previous SPEC — amendment chain 유발 위험** | LOW | 별도 SPEC ID로 분리 (Lesson #1 회피). 직전 SPEC v1.0.1 머지 후 별도 ship — chain 단절 |
| **`STAGE_COLORS` 회귀 / 산업명(중) 라인 누락** | LOW | Task 5의 AC-6 회귀 가드 + Task 8의 직전 SPEC AC-4/AC-8/AC-9/AC-10 재실행. CI에서 명시적 단언 |
| **stock_meta.product 컬럼 누락 (legacy DB)** | LOW | meta_service.py:229가 운영 중이므로 정상 경로 전제. 누락 시 OperationalError → 사용자가 DB 재빌드. SPEC 범위 밖 (Exclusions, 직전 SPEC research.md §9 동일) |
| **escapeHtml 헬퍼 중복 도입 / 직전 SPEC 함수와 시그니처 충돌** | LOW | Task 5 RED 작성 시점에 헬퍼 존재 여부 확인. 케이스 A/B 명시. drift 최소화(같은 함수 1군데에서 sector_minor + product 둘 다 호출) |
| **product 길이가 길어 tooltip이 차트 영역을 가림 (예: "반도체 검사장비 / 디스플레이 부품 / IT 솔루션")** | MEDIUM | 본 SPEC plan.md에서는 raw 값 그대로 표시. 라이브 smoke에서 시인성 확인 후 후속 SPEC 대상 — 본 SPEC은 truncation/abbreviation 미구현(Exclusions) |
| **data tuple 인덱스 확장으로 직전 SPEC tooltip formatter 인덱스 오프셋 변경** | MEDIUM | tuple 확장은 append-only — 기존 인덱스 보존. 신규 인덱스(예: 9)만 추가. 직전 SPEC 인덱스(예: 8)는 그대로. dimensions encode를 명시적으로 사용한다면 더 안전 — Task 7에서 인덱스 명명 상수 권장 |
| **column-name 기반 unpack vs positional 일관성 (commit 8437cab 학습)** | LOW | 직전 SPEC이 positional unpack을 유지했다면 본 SPEC도 동일 패턴. column-name 기반은 별도 refactoring SPEC 대상 — 본 SPEC 범위 밖 |
| **사용자 의도와 라인 위치 mismatch (Stage 아래 vs 산업명(중) 다음)** | LOW | 사용자 명시 "산업명(중) 라인 다음 또는 적절한 위치". 본 SPEC은 산업명(중) → 주요제품 → Stage 순서 채택. 라이브 smoke 후 사용자 1줄 피드백으로 swap 가능 |
| **rollback 부담 (backend + frontend 양쪽 변경)** | LOW | backend 응답 필드 추가는 backward compatible → 분리 ship 가능. frontend revert만으로 tooltip 회귀 복구 가능 |

---

## 5. mx_plan (MX 태그 계획)

`code_comments: ko` 설정에 따라 MX 태그 설명은 한국어로 작성.

| 대상 | 태그 | 사유 |
| --- | --- | --- |
| `my_chart/analysis/sector_advanced.py` `_get_stock_meta` SELECT 확장 | `@MX:NOTE` | product 컬럼 추가 — meta_service.py:229와 동일 패턴, daily DB stock_meta 의존 명시. SPEC-STOCK-TOOLTIP-PRODUCT-001 참조 |
| `my_chart/analysis/sector_advanced.py` `StockBubble` dataclass `product` 필드 | `@MX:NOTE` | 신규 응답 필드. 후속 backend 호출자에게 의도 전달 |
| `backend/schemas/sector_advanced.py` `StockBubbleItem.product` | `@MX:NOTE` | API 계약 확장. SPEC 참조 |
| `frontend/src/components/SectorAnalysis/StockBubbleChart.tsx` tooltip formatter | `@MX:NOTE` | tooltip 라인 순서(종목명 → 산업명(중) → 주요제품 → Stage) 명시. data tuple 인덱스 + escapeHtml 적용 의도 전달 |
| `frontend/src/utils/escapeHtml.ts` (케이스 B 신규) | `@MX:ANCHOR` (+ `@MX:REASON`) | tooltip XSS hardening의 단일 진입점. sector_minor + product (+ name + stage_detail) 다중 호출자 의존. 시그니처 변경 시 모든 tooltip 라인 영향 |
| 신규 RED 테스트 (Task 1, Task 5) | `@MX:TODO` | GREEN 단계에서 통과 시 제거 |

REFACTOR/GREEN 단계에서 통과한 `@MX:TODO`는 제거, ANCHOR의 fan_in 변화는 후속 sync 단계에서 검증.
