# SPEC-STOCK-TOOLTIP-PRODUCT-001 Acceptance — 수용 기준

> `development_mode: tdd`. 각 시나리오는 RED 테스트로 작성 가능한 구체·검증 가능 기준이다.
> 시나리오 ID는 REQ-STP-NNN과 매핑된다.
> 직전 SPEC-SECTOR-MINOR-COLOR-001 v1.0.1의 회귀 게이트(AC-4/AC-8/AC-9/AC-10)는 AC-6에서 명시적으로 재실행한다.

---

## 1. Given/When/Then 시나리오

### AC-1 — StockBubbleItem 응답 모델에 product 존재 (REQ-STP-001, REQ-STP-002, REQ-STP-007)

- **Given** `backend/schemas/sector_advanced.py`의 `StockBubbleItem` 정의가 있고
- **When** `StockBubbleItem.model_fields`를 조회하면
- **Then** `"product"` 키가 존재하고, 타입은 `str | None`으로 정의된다.
- **And (필드명 일관성)** 필드명은 정확히 `product`(영문, 단수, lowercase)이며 `main_product`, `mainProduct` 등 변형이 존재하지 않는다 (REQ-STP-007 — meta_service.py:229와 일관).
- **And (응답 빌드 시점)** 합성 stock_meta(`product` 키 포함)로 `compute_stock_bubble` 호출 → 결과 각 `StockBubble.product`가 stock_meta의 `product` 값과 일치하고, 빈/None 입력은 `None`으로 보존된다.

### AC-2 — `_get_stock_meta` SELECT 확장 (REQ-STP-002)

- **Given** daily DB stock_meta 테이블이 `name, code, sector_major, sector_minor, product, market, market_cap` 컬럼을 가지고
- **When** `_get_stock_meta(daily_db_path)`가 호출되면
- **Then** 반환 dict의 각 value에 `"product"` 키가 존재하고, DB의 해당 컬럼 값(또는 NULL → None)이 채워진다. 기존 키(`Code`, `sector_major`, `sector_minor`, `시장구분`, `market_cap`)는 그대로 유지된다.

### AC-3 — Frontend StockBubbleItem 타입 미러 (REQ-STP-003, REQ-STP-007)

- **Given** `frontend/src/types/bubble.ts`의 `StockBubbleItem` 인터페이스가 있고
- **When** TypeScript 컴파일이 실행되면
- **Then** `StockBubbleItem.product: string | null`이 존재한다(타입 누락 시 컴파일 에러).
- **And (필드명 일관성)** 필드명은 정확히 `product`이며 다른 변형이 존재하지 않는다 (REQ-STP-007).
- **And** 직전 SPEC v1.0.1로 추가된 필드(`sector_minor`)와 그 외 기존 필드(`name`, `price_change`, `rs_12m`, `trading_value`, `stage`, `stage_detail`, `market_cap`, `volume_ratio`)는 변경 없다.

### AC-4 — Tooltip 주요제품 라인 + 라인 순서 (REQ-STP-004)

- **Given** 차트 데이터에 sector_minor="반도체", product="반도체용 검사장비", stage=2, stage_detail="entry"인 종목 "삼성전자"가 있을 때
- **When** ECharts tooltip.formatter가 해당 데이터 포인트에 대해 호출되면
- **Then** 반환 HTML 문자열에 `주요제품: 반도체용 검사장비` 라인이 포함된다.
- **And (라인 순서)** 반환 HTML 문자열 내에서 `산업명(중):` 의 인덱스 < `주요제품:` 의 인덱스 < `Stage:` 의 인덱스 — 종목명 → 산업명(중) → 주요제품 → Stage 순서로 표시된다.
- **And (회귀 방지)** `산업명(중): 반도체` 라인과 `Stage: S2 (entry)` 라인이 동시에 포함된다 (직전 SPEC AC-8 보존).

### AC-5 — Tooltip 주요제품 NULL/빈 fallback (REQ-STP-004)

- **Given** 차트 데이터에 product가 `null`, 빈 문자열 `""`, 또는 누락(`undefined`)인 종목이 있을 때
- **When** tooltip.formatter가 해당 데이터 포인트에 대해 호출되면
- **Then** 반환 HTML 문자열에 `주요제품: —` 라인이 표시된다 (em-dash U+2014). 라인 자체는 노출된다(미표시 옵션 채택 안 함).
- **And** 동일 시나리오에서 `산업명(중): {sector_minor or '기타'}` 라인 + Stage 라인은 평소대로 표시된다(회귀 없음).

### AC-6 — 직전 SPEC 회귀 게이트 재실행 [HARD] (REQ-STP-005)

- **Given** 차트가 sector_minor="반도체"인 종목 3개 + sector_minor="디스플레이"인 종목 2개 + sector_minor가 null인 종목 1개 + 각각 임의의 product 값을 가진 상황으로 렌더되었을 때
- **When** ECharts option이 빌드되고 tooltip.formatter가 호출되면
- **Then (직전 AC-4 회귀)** option.series[0].data 중 sector_minor=="반도체"인 3개 항목의 `itemStyle.color`가 정확히 동일하고, "디스플레이"인 2개도 정확히 동일하고, null인 1개는 회색 `#9CA3AF`와 동일하다. 세 그룹의 색상은 서로 다르다. → product 변경이 색상 인코딩에 영향 없음을 단언.
- **And (직전 AC-8 회귀)** tooltip HTML에 `산업명(중):` 라인이 여전히 포함된다.
- **And (직전 AC-9 회귀 — 결정성)** 동일 props로 `rerender()` 2회 마운트 후 `option.series[0].data[i].itemStyle.color` 배열을 모든 i에 대해 비교 — 완전 일치한다.
- **And (직전 AC-10 회귀 — Stage 색상 금지)** 컴포넌트 소스에 `STAGE_COLORS` 식별자가 itemStyle.color / legend.data 결정 경로에서 참조되지 않는다 (Vitest source-string regex 정적 검사 재실행). legend.data에 `'S1 (바닥)'` ~ `'S4 (하락)'` / `'미분류'` 라벨 부재 단언.

### AC-7 — Tooltip XSS hardening (REQ-STP-006) [HARD]

- **Given** 차트 데이터에 product=`<script>alert('xss')</script>`인 합성 종목이 있을 때
- **When** tooltip.formatter가 해당 데이터 포인트에 대해 호출되면
- **Then** 반환 HTML 문자열에 raw `<script>` 또는 `</script>` 문자열이 **포함되지 않는다**.
- **And** 반환 HTML 문자열에 escape된 `&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;` (또는 동등한 escape 형식, `&amp;` `&lt;` `&gt;` `&quot;` `&#39;` 또는 `&apos;`)가 포함된다.
- **And (sector_minor 일관성)** sector_minor가 `<img onerror>` 같은 페이로드일 때도 동일하게 escape된 문자열만 포함된다 — `escapeHtml` 헬퍼는 sector_minor + product 양쪽에 일관 적용된다 (직전 SPEC GREEN 단계 패턴 또는 본 SPEC plan.md §1.3 케이스 B로 도입).

---

## 2. 에지케이스

| 케이스 | 기대 동작 |
| --- | --- |
| 모든 종목 product === null | 모든 tooltip에 `주요제품: —` 표시. 산업명(중) / Stage 라인은 평소대로. |
| 단일 종목 product 매우 김 (예: 100자 초과) | raw 값 그대로 표시. truncation 없음(본 SPEC Exclusions). 라이브 smoke에서 시인성 확인 후 후속 SPEC에서 truncation 검토. |
| product에 줄바꿈/탭 포함 | escapeHtml 통과 후 raw 그대로(줄바꿈은 HTML에서 공백으로 표시됨). 별도 정규화 없음. |
| product에 HTML 특수문자 (`<`, `>`, `&`, `"`, `'`) | escapeHtml 통과 — 각각 `&lt;`, `&gt;`, `&amp;`, `&quot;`, `&#39;` 또는 `&apos;`. AC-7. |
| product가 한국어 + 영문 혼재 | raw 그대로 표시. UTF-8 처리는 React/ECharts 표준 동작에 위임. |
| stocks 배열 빈 배열 | 기존 "데이터 없음" 그래픽 유지. tooltip 호출 없음. AC-4/AC-5 적용 안 됨. |
| 동일 sector_minor 그룹 내 다양한 product 값 | 색상은 sector_minor 기준 동일(AC-6). tooltip의 주요제품 라인만 종목별로 다름 — 정상. |
| backend가 product 필드 자체 누락한 응답 (구버전 호환) | frontend `product: string \| null` → `undefined`로 처리되어 `주요제품: —` fallback 표시. 라인은 노출. AC-5 sub. |
| backend가 product 컬럼 자체 누락 (legacy DB) | OperationalError → SPEC 범위 밖 (Exclusions, 사용자가 DB 재빌드). |

---

## 3. 품질 게이트 (Quality Gates)

- **회귀 방지 게이트 [HARD]**: AC-6으로 직전 SPEC AC-4/AC-8/AC-9/AC-10 4종 재실행. 색상 매핑 / 산업명(중) tooltip 라인 / 결정성 / Stage 색상 금지 모두 보존.
- **XSS 게이트 [HARD]**: AC-7 product `<script>` 페이로드 → escape된 문자열만 포함. sector_minor 라인에도 동일 escape 일관 적용 확인.
- **라인 순서 게이트 [HARD]**: AC-4 종목명 → 산업명(중) → 주요제품 → Stage 순서 인덱스 단언.
- **타입 게이트**: AC-3 frontend TypeScript 컴파일 + AC-1 backend Pydantic model_fields.
- **명명 일관성 게이트 [HARD]**: AC-1, AC-3 필드명 정확히 `product` 단언 (REQ-STP-007 — meta_service.py:229와 일관).
- **테스트 커버리지**: 변경 모듈 85% 이상. Vitest + pytest.
- **TRUST 5**:
  - **Tested**: 신규 시나리오 AC-1~AC-7 RED→GREEN. 직전 SPEC 회귀 게이트 4종 (AC-6) 재실행.
  - **Readable**: 한국어 주석/MX 태그(`code_comments: ko`), tooltip 라인 순서 명시(plan.md §1.2).
  - **Unified**: ruff/black (Python), TypeScript strict, ESLint.
  - **Secured**: 서버사이드 SELECT 화이트리스트 컬럼만 — SQL injection 표면 없음. 프론트엔드 product 값은 escapeHtml로 XSS 방지(AC-7).
  - **Trackable**: conventional commit + SPEC-STOCK-TOOLTIP-PRODUCT-001 참조. `git_commit_messages: ko` 설정 준수.
- **기존 테스트 회귀 없음**: `backend/tests/test_sector_advanced.py` (compute_stock_bubble 기존 테스트 + 직전 SPEC sector_minor 테스트) 회귀 없음. `StockBubbleChart.test.tsx` (직전 SPEC 추가 시나리오) 회귀 없음.
- **성능 게이트**: 본 SPEC은 별도 P95 게이트를 강제하지 않는다. 직전 SPEC AC-12(P95 < baseline * 1.20) 상한이 유효. tooltip 라인 1줄 추가는 SVG 렌더 비용 무시 가능.
- **라이브 검증**: ship 후 사용자 1일 사용 회고 1회 — "주요제품" 정보가 종목 식별/판단에 유효한가, 라인 길이로 인한 시인성 문제 없는가 확인.

---

## 4. Definition of Done

- [ ] REQ-STP-001 ~ REQ-STP-007 전부 구현 및 검증.
- [ ] AC-1 ~ AC-7 전 시나리오 테스트 통과.
- [ ] `StockBubbleItem` (Pydantic + TS)에 `product` 필드 존재, 필드명 정확히 `product` (AC-1, AC-3).
- [ ] `_get_stock_meta` SELECT에 `product` 포함, 결과 dict에 키 존재 (AC-2).
- [ ] `compute_stock_bubble` → `StockBubble.product` 전파 (AC-1 sub).
- [ ] `get_stock_bubble` 서비스 변환 시 `product` 전달 (AC-1 sub).
- [ ] `StockBubbleChart.tsx` tooltip formatter에 `주요제품: {product or '—'}` 라인 추가 (AC-4, AC-5).
- [ ] tooltip 라인 순서: 종목명 → 산업명(중) → 주요제품 → Stage (AC-4).
- [ ] product 값 escapeHtml 통과, sector_minor도 동일 escape 적용 일관성 (AC-7).
- [ ] 직전 SPEC 회귀 게이트 통과: 색상 인코딩 sector_minor 기준 유지 + 산업명(중) tooltip 라인 보존 + 결정성 round-trip + Stage 색상 금지 (AC-6).
- [ ] data tuple/dimensions 인덱스 갱신: product 인덱스 추가, 직전 SPEC sector_minor 인덱스 + 기타 인덱스 보존.
- [ ] Exclusions 항목 미구현 확인: SectorBubbleChart / BubbleChart / RRG / Bump / 트리맵 / StockTable / 필터링 / 색상 인코딩 변경 / truncation / i18n / 컬럼 존재 가드.
- [ ] 한국어 주석 + MX 태그 (`code_comments: ko`) 적용.
- [ ] 라이브 smoke test: 큰 섹터 드릴다운 → 종목 hover → tooltip 4개 정성 라인(종목명/산업명(중)/주요제품/Stage) + 가격변동/RS/거래대금 확인. 적어도 1개 종목은 product NULL → `주요제품: —` 표시 확인.
- [ ] Conventional commit + SPEC-STOCK-TOOLTIP-PRODUCT-001 참조, `git_commit_messages: ko`.
