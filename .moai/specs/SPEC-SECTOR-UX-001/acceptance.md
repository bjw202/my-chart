# SPEC-SECTOR-UX-001 Acceptance — 수용 기준

> `development_mode: tdd`. Vitest + React Testing Library. 각 AC는 **실행 가능한 검사**(렌더 단언 / 이벤트 시뮬레이션 / 정적 스캔 / tsc)로 기술한다.
> 백엔드 응답은 `SPEC-SECTOR-AGGREGATION-001`이 정의한 스키마의 **픽스처**로 대체한다.

---

## 1. 상태 모델

### AC-SUX-001 — AnalysisParamsContext 계약

- **Given** `AnalysisParamsProvider`로 감싼 테스트 트리에서
- **Then** `market === 'all'`, `period === '1m'`, `asOfDate === null`, `asOfIsPartialWeek === false`가 초기값이다.
- **And** `setAsOfDate`류의 쓰기 API가 **노출되지 않는다** — `asOfDate` / `asOfIsPartialWeek` / `gridVersion`은 서버 응답 기록 전용 내부 경로로만 갱신된다(읽기 전용 계약).
- **And** 탭 전환 시뮬레이션 후에도 값이 유지된다(세션 지속).

### AC-SUX-002 — SelectionContext 계약

- **Then** `selectedSector === null`, `sectorScopeFollow === true`가 초기값이다.
- **And** 임의 화면에서 `selectSector('반도체')` 호출 후 다른 화면 컴포넌트가 `selectedSector === '반도체'`를 읽는다.
- **And** 소비해도 값이 소멸하지 않는다 — 두 소비자가 연속으로 읽어도 둘 다 값을 본다.

### AC-SUX-003 — NavIntent 주소 지정 (규칙 SM-1/SM-2)

- **Given** `navigate({ target: 'stock-explorer', payload: {...} })`를 호출하고 `activeTab === 'stock-explorer'`일 때
- **Then** 종목 탐색 소비자만 처리하고, 섹터 분석 소비자는 **처리하지 않는다**(핸들러 spy 호출 0회).
- **And** `activeTab !== 'stock-explorer'`이면 종목 탐색 소비자도 처리하지 않는다(3조건 중 활성 조건).
- **And** 같은 payload로 2회 `navigate` 시 `id`가 증가하여 소비자가 **2회** 처리한다(재전송 구분).
- **And** 동일 `id`로 리렌더가 발생해도 소비자는 **1회만** 처리한다.

### AC-SUX-004 — NavIntent 타입 계약 [게이트 2분할]

> **이전 판의 결함 — 게이트가 달성 불가능했다.** 이전 판은 `tsc` **종료 코드 0**을 요구했다. 실측(2026-08-12, `npx tsc -p tsconfig.app.json --noEmit`): **총 33건**의 오류가 존재하며 그중 `TS2353`은 **정확히 1건**(③가 해소 책임을 지는 `MarketOverview.tsx:46` `stockName`)이다. 나머지 32건은 **선행 결함**이고, 상당수는 ③의 모듈 범위 안에 있다 — `SectorAnalysis/__tests__/StockBubbleChart.test.tsx` 9건, `SectorDetailPanel.test.tsx` 1건, `StockBubbleChart.tsx` 1건, `StockExplorer.test.tsx` 1건.
>
> 즉 종료 코드 0을 요구하면 **③의 범위 밖 선행 결함 32건을 함께 고쳐야만 ship할 수 있다.** 이는 §4 Exclusions의 범위 규율과 충돌하며, 실무적으로는 게이트가 무시되는 결과를 낳는다. **게이트를 두 개로 나눈다 — (b)의 완화가 (a)를 약화시켜서는 안 된다.**

**(a) HARD 게이트 — `TS2353 == 0`** [이 게이트는 완화 대상이 아니다]

- **When** `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -c "error TS2353"`을 실행하면
- **Then** 출력이 **`0`**이다.
- **And** 특히 `MarketOverview.tsx`의 `'stockName' does not exist in type 'CrossTabParams'` 오류가 사라진다 — `CrossTabParams` 타입 자체가 삭제되고 `NavIntent`로 대체되므로 근본 소멸이다.
- **And** `NavIntent['payload']`에 `subTab`, `stockCodes`, `focusStock` 필드가 정의되어 있다.

**(b) 회귀 게이트 — 총량 비증가 + ③ 수정 파일 NEW 0건**

- **Given** run 착수 시점에 baseline을 측정해 **`progress.md §E.2`에 총 오류 수 `N`을 기록**한다(측정 시점 실측: `N = 33`)
- **When** 구현 완료 후 `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -cE "error TS"`을 실행하면
- **Then** 결과가 **`<= N`**이다 — 총량이 늘지 않는다.
- **And** **③가 수정한 파일에서 NEW 오류가 0건**이다. 판정 절차: baseline 로그와 최종 로그를 `파일:코드` 키로 diff해, ③의 수정 파일 목록에 속하면서 baseline에 없던 항목이 0건임을 단언한다.
- **And** ③가 수정하지 않은 파일의 선행 오류는 **감소를 요구하지 않는다**(범위 규율).

**주의 — `crossTabParams` 삭제로 필연 감소하는 오류**: `CrossTabParams` / `setCrossTabParams`를 참조하는 파일이 13개 존재하며(`AppContent.tsx`, `TabContext.tsx`, `ChartGrid.tsx`, `SectorAnalysis.tsx`, `StockExplorer.tsx`, `types/market.ts` + 테스트 7종), M3의 X5 삭제가 이들을 필연적으로 건드린다. 따라서 ChartGrid 테스트군의 `TS2741 setCrossTabParams is missing` 계열 오류는 **③의 수정 파일에 포함되어 (b)의 NEW-0 판정 대상**이 된다 — 손대는 이상 남겨 둘 수 없다. 이 사실을 baseline 기록 시 명시한다.

### AC-SUX-005 — 전역 clear 부재 (정적 스캔, 규칙 SM-3)

- **When** `grep -rn "clearCrossTabParams\|crossTabParams\|CrossTabParams" frontend/src/`를 실행하면
- **Then** 출력이 **0행**이다.
- **And** 각 소비자가 `lastHandledId` 로컬 상태를 갖는다.

### AC-SUX-006 — 섹터명은 의도 페이로드가 아니다 (규칙 SM-4)

- **When** `NavIntent` 타입 정의와 전 `navigate()` 호출부를 스캔하면
- **Then** `payload`에 `sectorName` 필드가 존재하지 않는다(타입 수준 + grep 0행).

### AC-SUX-007 — 스코프 추종 토글 (규칙 SM-5/SM-6)

- **Given** `selectedSector === '반도체'`, `sectorScopeFollow === true`일 때
- **When** 종목 탐색에서 섹터 칩 `×`를 클릭하면
- **Then** `sectorScopeFollow === false`이고 **`selectedSector`는 `'반도체'` 그대로**다.
- **And** 종목 표 모집단이 전체로 바뀐다.
- **And** 섹터 분석 탭으로 이동하면 `'반도체'` 행이 여전히 하이라이트되고 상세 패널이 열려 있다.
- **And** 다시 어디서든 섹터를 선택하면 `sectorScopeFollow`가 `true`로 강제된다.

### AC-SUX-008 — 컨트롤 단일 인스턴스 (규칙 SM-7)

- **Given** 섹터 분석 탭에서 Table 서브탭의 기간을 `3m`으로 바꾸고
- **When** Bubble 서브탭으로 전환하면
- **Then** Bubble의 기간도 `3m`이다(현행은 Table `m1` / Bubble `1w` 독립).
- **And** 렌더 트리에 기간 토글 컴포넌트 인스턴스가 섹터 분석 화면당 **1개**다(`getAllByTestId('period-toggle')` 길이 1).
- **And** 시장 토글도 동일하게 1개다.

### AC-SUX-009 — 기간 표기 단일화 (규칙 CT-12)

- **When** `grep -rn "'w1'\|'m1'\|'m3'" frontend/src/ | grep -v "excess_returns\|types/market.ts"`를 실행하면
- **Then** 출력이 **0행**이다 — 상태 값은 `'1w' | '1m' | '3m'`만 쓴다.
- **And** 응답 스키마 키(`excess_returns.w1` 등)는 그대로 유지된다(별개 축).

### AC-SUX-010 — 복귀 시 컨텍스트 보존 (규칙 SM-8)

- **Given** 섹터 분석에서 `selectedSector='반도체'`, `period='3m'`, `subTab='bubble'`, `sortField='rs_avg'`를 설정하고 종목 탐색으로 이동해 `stageFilter='2'`와 종목 3개 체크를 설정한 뒤
- **When** 상단 탭으로 섹터 분석 → 종목 탐색을 왕복하면
- **Then** 위 6개 상태가 **모두 보존**된다.
- **And** 뒤로 가기 전용 버튼 컴포넌트가 렌더 트리에 없다.

---

## 2. 전환 규칙

### AC-SUX-011 — 행 클릭은 필터 전용 (규칙 TR-3/TR-3b)

- **When** 순위표 행을 클릭하면
- **Then** `selectedSector`가 설정되고 상세 패널이 열리며, **`navigate()` spy 호출 0회**이고 `activeTab`이 바뀌지 않는다.
- **And** 선택된 행을 재클릭하면 `selectedSector === null`이고 패널이 닫힌다.

### AC-SUX-012 — `[이 섹터 종목 보기 →]` 동선 (규칙 TR-4)

- **Given** 상세 패널이 열려 있고 3개 종목이 체크되어 있을 때
- **When** `[이 섹터 종목 보기 →]`를 클릭하면
- **Then** `activeTab === 'stock-explorer'`, `sectorScopeFollow === true`, `selectedStocks.size === 0`이다.
- **And** `period`, `market`, `stageFilter`는 유지된다.
- **And** 이 버튼이 상세 패널에 실제로 렌더된다(현행 부재).

### AC-SUX-013 — 종목 버블 클릭 배선 (규칙 TR-9, ST-8 해소)

- **When** 종목 버블을 클릭하면 (ECharts `click` 이벤트 시뮬레이션)
- **Then** `activeTab === 'stock-explorer'`이고 `NavIntent.payload.focusStock === 클릭 종목명`이며 `selectedStocks.size === 0`이다.
- **And** `BubbleChart`가 `StockBubbleChart`에 `onStockClick` prop을 실제로 전달한다(props 단언).

### AC-SUX-014 — 트리맵 종목 클릭 (규칙 TR-2, ST-7 해소)

- **When** `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -c "MarketOverview.tsx.*TS2353"`을 실행하면
- **Then** 출력이 **`0`**이다 — `'stockName' does not exist` 오류가 사라진다 (AC-SUX-004 (a) HARD 게이트와 동일 대상).
- **And** 트리맵 종목 클릭 시뮬레이션 후 차트 그리드 소비자가 `focusStock`을 수신한다(spy 단언).
- **And** `grep -rn "stockName" frontend/src/` 결과에 쓰기만 있고 읽기가 없는 상태가 해소된다.

### AC-SUX-015 — 종목 체크 초기화 규칙 (규칙 TR-16)

- **Given** 종목 3개가 체크된 상태에서
- **Then** 다음 조작 후 `selectedStocks.size === 0`이다: `[이 섹터 종목 보기]`(TR-4), 종목 버블 클릭(TR-9), 섹터 칩 `×`(TR-12), `selectedSector` 변경.
- **And** Stage 세그먼트 클릭/해제(TR-10/11) 후에는 `selectedStocks.size === 3`으로 **유지**된다.
- **And** 회귀 검출: 섹터 A에서 3개 체크 → 섹터 B로 전환 시 `"3 selected"`가 표시되면서 표에 해당 행이 없는 상태가 **재현되지 않는다**.

### AC-SUX-016 — 버블 뒤로가기 시 선택 유지 (규칙 TR-6)

- **When** 종목 버블 뷰에서 `← 섹터 목록`을 클릭하면
- **Then** `bubbleView === 'sector'`이고 **`selectedSector`가 유지**된다(현행은 `null`).
- **And** `stockData` / `stockError`는 초기화된다.

### AC-SUX-017 — RRG/Bump 요소 클릭 (규칙 TR-7/TR-8)

- **When** RRG 궤적을 클릭하면
- **Then** `selectedSector`가 설정되고 `subTab === 'table'`이며 `visibleSectors` / `windowEnd`가 보존된다.
- **And** RRG로 되돌아가면 보고 있던 시점(`windowEnd`)이 그대로다.
- **And** Bump 선 클릭도 동일하며 `topFilter`가 보존된다.

---

## 3. 컨트롤

### AC-SUX-018 — 시장 토글 실동작 (규칙 CT-1, ST-4 해소)

- **When** 시장 토글을 `KOSPI`로 바꾸면
- **Then** Table / Bubble(섹터·종목) / RRG / Bump / 종목 탐색 **5개 경로 전부**가 `market=kospi`를 포함한 요청을 발행한다(fetch mock 인자 단언).
- **And** 응답의 `benchmark.name`이 바뀌어 헤더 벤치마크 표기가 갱신된다.
- **And** 버튼 활성 CSS만 바뀌고 요청이 없는 상태가 **재현되지 않는다**.

### AC-SUX-019 — 제외 섹터 가시성 (규칙 CT-2)

> **검증 범위 — Table · 섹터 Bubble · RRG 한정. Bump는 대상이 아니다.** O-U9(=②의 O-A7)가 **"AG-5를 Bump에 미적용"으로 확정**되었다(2026-08-14 사용자 결정, §7 참조). Bump는 AG-5 제외를 적용하지 않으므로 제외 영역을 렌더하지 않는다 — 이는 미구현이 아니라 **계약**이다.

- **Given** 응답 `excluded: [{sector:'디스플레이', reason:'insufficient_members', count:4}, {sector:'스마트폰', ..., count:4}]`
- **Then** 표 하단에 `순위 대상 제외 (2)` 영역이 렌더되고 각 항목에 섹터명·사유·종목 수가 표시된다.
- **And** 해당 섹터가 `data[]`에 없어도 **화면에서 사라지지 않는다**.
- **And (Bump 반대 방향 단언 — 미적용 계약의 실증)** 같은 `market` 파라미터의 `/sectors/history` 응답을 렌더한 Bump 차트에는 `순위 대상 제외` 영역이 **렌더되지 않으며**, `excluded`로 분류된 섹터(`디스플레이`·`스마트폰`)의 선이 Bump에 **정상적으로 존재한다**.
  - **대조 단언 (Lesson #9 — 되돌림 RED 실증 필수)**: 이 단언은 항진명제가 아니다. Bump 소비자에 Table과 동일한 `excluded` 필터링을 주입하는 변형 `mut_bump_applies_ag5`(렌더 직전 `data[]`의 섹터 집합으로 Bump 시계열을 교집합)를 적용하면 두 섹터의 선이 사라져 **RED가 관측되어야 한다**. RED 출력을 verbatim 캡처해 `progress.md §E.2`에 기록하고, 트리 복원을 `git status --short`로 증명한다. 실증하지 못하면 GREEN이 아니라 **Gaps**로 기록한다.
  - **배경 실측 (2026-08-14)**: `/sectors/history` → `compute_sector_history` → `compute_sector_ranking` → `_compute_sector_metrics`. 이 함수는 `my_chart/analysis/sector_metrics.py:947-948`에서 *"AG-5 제외는 여기에 적용하지 않는다 — 규칙 AG-5는 `data[]`가 소유한다"* 를 명시한다. `get_sector_history`(`backend/services/sector_advanced_service.py:218`)는 `SectorHistoryResponse` 생성 3곳 어디에서도 `excluded=`를 전달하지 않으므로 봉투의 `excluded[]`는 항상 빈 배열이다.

### AC-SUX-020 — 선택 섹터가 제외될 때 (규칙 CT-3)

- **Given** `selectedSector='디스플레이'`이고 시장을 `KOSPI`로 바꿔 해당 섹터가 `excluded`가 되면
- **Then** `selectedSector`는 `'디스플레이'`로 **유지**된다.
- **And** 상세 패널 자리에 `이 시장 필터에서는 표본 부족(n=4)으로 순위 대상에서 제외되었습니다` 취지의 안내가 렌더된다.
- **And** 조용한 선택 해제가 일어나지 않는다.

### AC-SUX-021 — Rank 열과 행 순서 일치 (규칙 CT-4)

- **Given** `period='1w'` 응답의 `rank`가 `1..N` 연속일 때
- **When** 화면 진입 또는 period/market 변경 후 표를 렌더하면
- **Then** 렌더된 Rank 열의 값 시퀀스가 `1, 2, 3, ...` 오름차순이고 행 순서와 일치한다.
- **And** 회귀 검출: `1, 2, 4, 26, 3, 6, 15` 같은 시퀀스가 **재현되지 않는다**.
- **And** **클라이언트가 `rank`를 재계산하지 않는다** — 이전 판의 "정적 스캔: 정렬 유틸에 rank 재부여 코드 없음"은 무엇을 실행하는지 알 수 없어 검사가 아니었다. 두 개의 실행 가능한 검사로 대체한다:
  - **(1) 정적 스캔 (실행 명령)**:
    ```bash
    grep -rnE "\.rank\s*=|rank:\s*(idx|index|i)\s*\+\s*1|map\(\(.*,\s*(idx|i)\).*rank" \
         frontend/src/components/SectorAnalysis/ frontend/src/utils/
    ```
    → **0행**. 인덱스로 `rank`를 재부여하는 표현이 없다.
  - **(2) 행동 단언 (스캔보다 강함)**: 응답 `data[]`의 `rank`를 `[3, 1, 2]`처럼 **불연속·비정렬**로 주고 배열 순서도 그와 다르게 준 픽스처에서, 렌더된 Rank 열 값이 **응답 값을 그대로** 반영한다(`3, 1, 2` 각각이 해당 섹터 행에 붙는다). 클라이언트가 재계산했다면 `1, 2, 3`이 되어 실패한다. 이 단언은 rename·구현 방식 변경에 내성이 있다.

### AC-SUX-022 — 정렬 고지 띠 (규칙 CT-6)

- **When** `RS 평균` 컬럼 헤더를 클릭해 정렬하면
- **Then** 표 상단에 고지 띠가 렌더되고, 그 문구에 현재 정렬 기준·`period`·`market`이 포함된다.
- **And** `[순위순으로]` 버튼 클릭 시 `sortField='rank'`, `sortDirection='asc'`로 복귀하고 띠가 사라진다.
- **And** `rank` 정렬 상태에서는 띠가 렌더되지 않는다.

### AC-SUX-023 — 정렬 리셋 (규칙 CT-7)

- **Given** `sortField='rs_avg'`, `sortDirection='desc'`일 때
- **When** `period` 또는 `market`을 바꾸면
- **Then** `sortField==='rank'`, `sortDirection==='asc'`로 리셋된다.

### AC-SUX-024 — 정렬 시 null 처리

- **Given** 값이 `[5, null, 3, null, 9]`인 컬럼에서
- **When** 오름차순/내림차순 각각 정렬하면
- **Then** **두 경우 모두** `null` 행이 맨 뒤에 온다.
- **And** `NaN` 비교로 순서가 흔들리지 않는다(같은 입력 3회 정렬 결과 동일).

### AC-SUX-025 — 순위변동 3상태 + 기준일 (규칙 CT-8/CT-9)

- **Given** `rank_change`가 각각 `3`, `-2`, `0`, `null`인 4행에서
- **Then** 각각 `▲3`(positive), `▼2`(negative), `–`(muted), `신규`(muted + 툴팁)로 렌더된다.
- **And** `0`과 `null`이 **다른 텍스트**로 구분된다(현행은 둘 다 `-`).
- **And** 열 헤더에 `baseline_date`가 표기된다 — 헤더 텍스트에 응답의 `baseline_date` 문자열이 포함된다.

### AC-SUX-026 — 가중 방식 배지 (규칙 CT-14, Lesson #1 본문 상설)

- **Then** 초과수익률 3개 컬럼 헤더에 `ⓦ`, RS/신고가/Stage 컬럼 헤더에 `ⓔ`가 **텍스트로 상설** 렌더된다(hover 불필요).
- **And** 표 하단에 `ⓦ 시총가중(상한10%) ⓔ 등가중` 범례 한 줄이 렌더된다.
- **And** 각 배지에 hover 툴팁이 붙되, **툴팁 없이도 배지 자체로 구분 가능**하다(모바일 대응, A5).

### AC-SUX-027 — RRG/Bump 기간 토글 비활성 (규칙 CT-13)

- **When** 서브탭을 RRG 또는 Bump로 전환하면
- **Then** 기간 토글이 `disabled` 상태로 **여전히 렌더**된다(숨겨지지 않음).
- **And** 툴팁 텍스트에 해당 서브탭의 자체 시간 파라미터 설명이 포함된다.
- **And** Table/Bubble로 돌아오면 다시 활성화되고 이전 `period` 값이 유지된다.

### AC-SUX-028 — Bump 구간 컨트롤

- **Then** `8주 / 12주 / 26주` 토글이 렌더되고 기본 선택이 `12주`다.
- **And** `26주` 선택 시 `weeks=26`을 포함한 요청이 발행된다.
- **And** 축 하단에 응답의 `weeks`와 `span_days`가 병기된다(`12주 (84일)` 형태) — 프론트가 값을 계산하지 않고 응답을 그대로 표기한다.

### AC-SUX-029 — Stage 분포 바 모집단 일치 (규칙 CT-10, ST-5 해소)

- **Given** `sectorScopeFollow === true`, `selectedSector === '반도체'`, 응답 `by_sector['반도체'] = {s1:38, s2:68, s3:31, s4:22, unclassified:5, total:164}`
- **Then** 분포 바 헤더가 `반도체`와 `164`를 포함한다.
- **And** 세그먼트 합(38+68+31+22+5)이 **종목 표의 렌더 행 수(164)와 일치**한다.
- **And** `sectorScopeFollow === false`이면 전체 `distribution`을 쓰고 헤더가 전체 종목 수를 표시한다.
- **And** 회귀 검출: 분포 바는 전체, 표는 섹터인 불일치 상태가 **재현되지 않는다**.

### AC-SUX-030 — 미분류 세그먼트 (규칙 CT-11)

- **Then** 분포 바에 `미분류` 세그먼트가 렌더되고, 5개 세그먼트 너비 비율의 합이 **100%**다(현행 4개는 미달).
- **And** 미분류 세그먼트 클릭 시 `stageFilter === 'unclassified'`가 되고 표가 분류 불가 종목만 렌더한다.
- **And** 범례에 `○ 미분류(SMA40 부족)` 항목이 존재한다.

### AC-SUX-031 — 종목 표 신규 열

- **Then** 종목 표에 `1W%`, `1M%`, `3M%`, `섹터비중` 4개 열이 렌더된다.
- **And** `weight_capped: true`인 종목의 셀에 `⊤` 마커가 붙는다.
- **And** `period` 토글을 바꿔도 **열 집합은 변하지 않고** 기본 정렬 키만 해당 기간 열로 바뀐다.

### AC-SUX-032 — **default 진입 가시성** [Lesson #3 필수 게이트]

- **Given** 앱을 부팅해 아무 설정 없이 종목 탐색 탭에 처음 진입했을 때 (기본 모드, 추가 조작 0회)
- **Then** 화면에서 다음이 **모두 보인다**: `1W%` 열, `3M%` 열, `섹터비중` 열, 기준일 배지, (해당 시) 진행 중인 주 배지, Stage 미분류 세그먼트.
- **And** 어떤 항목도 "상세 모드"나 "확장 토글" 뒤에 숨어 있지 않다.
- **And** 섹터 분석 탭 첫 진입에서도 기준일 배지·벤치마크 표기·가중 배지가 보인다.
- **근거**: Lesson #3 — 신규 컬럼이 default 모드에서 보이지 않아 그림자 결함이 된 선례.

---

## 4. 로딩·갱신

### AC-SUX-033 — 쿼리 키와 조회 시점 (규칙 LD-A, LD-1/LD-2 해소)

- **When** 앱을 부팅하면
- **Then** 활성 탭(`chart-grid`) 외 탭의 섹터 엔드포인트 fetch가 **발생하지 않는다**(fetch mock 호출 URL 집합 단언).
- **And** 섹터 분석 탭을 활성화하면 그때 fetch가 발생한다.
- **And** 같은 쿼리 키로 재활성화하면 TTL 내에서는 추가 fetch가 없다.
- **And** `period`/`market` 변경 시 **활성 화면만** 즉시 fetch하고 비활성 화면은 활성화 시점에 fetch한다.

### AC-SUX-034 — TTL (규칙 LD-B)

- **Given** TTL 상수가 1시간이고
- **When** 59분 경과 후 재활성화 → fetch 없음, 61분 경과 후 재활성화 → fetch 발생
- **Then** 위가 성립한다(타이머 mock).
- **And** TTL 상수가 단일 위치에 정의되고 전 엔드포인트가 공유한다.

### AC-SUX-035 — 재조회 중 기존 데이터 유지 (규칙 LD-C)

- **Given** 표에 데이터가 렌더된 상태에서
- **When** `period`를 바꿔 재조회가 시작되면
- **Then** 기존 행이 **계속 렌더**되고 기준일 배지 옆에 로딩 인디케이터가 나타난다.
- **And** 차트가 언마운트되지 않는다(DOM 노드 동일성 단언) — 현행 `BubbleChart.tsx:151-162`의 깜빡임이 재현되지 않는다.
- **And** 재조회 실패 시 기존 데이터를 유지하고 상단에 `갱신 실패 — 표시 중인 데이터는 {이전 기준일} 기준입니다 [다시 시도]` 띠를 렌더한다.

### AC-SUX-036 — 재시도와 수동 새로고침 (규칙 LD-D, ST-6 해소)

- **Given** 첫 3회 응답이 실패하고 4회째 성공하도록 mock했을 때
- **Then** 자동 재시도가 2s/4s/8s 간격으로 3회 발생한 뒤 **멈추고** `[다시 시도]` 버튼이 나타난다.
- **And** `⟳ 새로고침` 버튼이 기준일 배지 옆에 **항상** 렌더되며, 클릭 시 전 캐시를 무효화하고 활성 화면을 재조회한다.
- **And** 백엔드 워밍업 실패 후 탭 재활성화만으로 자가 복구된다.

### AC-SUX-037 — 기준일 합치 검증 (규칙 LD-E, 불변식 **SN-3** 클라이언트 측)

- **Given** 두 패널이 각각 `as_of_date` `2026-08-07`과 `2026-08-11`을 응답하면
- **Then** 화면 상단에 두 날짜와 패널명을 포함한 경고 띠가 렌더되고 `[새로고침]` 액션이 있다.
- **And** 동일 날짜면 띠가 렌더되지 않는다.
- **And** `grid_version`이 캐시된 값과 다르면 전 캐시가 무효화되고 재조회가 발생한다.
- **And** 기준일 배지 텍스트가 **응답 값과 문자열 동등**하다 — 프론트에서 날짜를 계산·포맷 변환해 만들어낸 값이 아니다.
- **And (SN-4 상설 노출)**: 섹터 분석 4개 서브탭과 종목 탐색 **5개 화면 전부**에서 기준일 배지가 상단에 렌더된다(화면별 루프 단언). `as_of_is_partial_week === true`인 픽스처에서는 진행 중 표기가 배지 옆에 함께 렌더된다.

---

## 5. 시각화

### AC-SUX-038 — 버블 크기 면적 비례 + 로그 (규칙 VZ-1)

- **Given** 거래대금이 `[1e8, 1e10, 1e12]`인 3개 버블에서
- **When** `symbolSize`를 계산하면
- **Then** 결과가 공식 `2×sqrt(r_min² + u×(r_max² − r_min²))`과 일치하고, 섹터 버블은 `[14, 68]` 범위, 종목 버블은 `[10, 52]` 범위에 든다.
- **And** 최소값 버블의 지름이 `2×r_min`, 최대값 버블이 `2×r_max`다.
- **And** 중간값 버블이 최소 크기 근처에 뭉치지 않는다 — 선형 정규화 결과와 **다름**을 대조 단언한다.
- **And** `v_max === v_min`이면 `u = 0.5`로 모든 버블이 동일 중간 크기다.

### AC-SUX-039 — 크기 범례 의무 (규칙 VZ-2)

- **Then** 두 버블 차트 모두 크기 범례를 렌더하고, 3개 참조 버블과 각각의 **실제 값 텍스트**가 존재한다.
- **And** 범례가 없는 상태로 크기 채널이 렌더되는 경로가 없다(범례 컴포넌트 필수 렌더 단언).
- **And (O-U4 결정 반영 — 기간별 고정 눈금)** 참조 값이 `period`에 따라 다음 리터럴과 **정확히 일치**한다. 데이터에 따라 움직이지 않는다.

| `period` | 참조 값 3개 |
| --- | --- |
| `1w` | 100억 / 1,000억 / 1조 |
| `1m` | 500억 / 5,000억 / 5조 |
| `3m` | 1,000억 / 1조 / 10조 |

- **And 데이터 불변성 단언**: 같은 `period`에서 거래대금 분포가 전혀 다른 두 픽스처(예: 전부 소액 / 전부 거액)를 렌더해도 **범례 값 3개가 동일**하다. 데이터 적응형이면 실패한다.
- **And 클램프**: 사다리 최대를 넘는 값은 `symbolSize === 2×r_max`, 최소 미만은 `2×r_min`이며, **툴팁에는 클램프되지 않은 실제 값**이 표기된다.
- **And 기간 병기**: 범례 텍스트에 어느 기간의 거래대금인지 포함된다(예: `크기 = 거래대금 3M (로그·고정 눈금)`) — 기간마다 사다리가 다르므로 기간 표기 없이는 눈금이 모호하다.
- **And** `v_min` / `v_max`가 데이터가 아니라 **해당 기간 사다리의 최소·최대 상수**임을 확인한다(VZ-1 로그 정규화 입력).

### AC-SUX-040 — 결측 거래대금 (규칙 VZ-3, REQ-SUX-057 채널 단일화 반영)

> **개정**: 이전 판은 두 차트 모두에 `borderType === 'dashed'`를 요구했다. 그러나 종목 버블의 테두리는 **Stage 전용 채널**(REQ-SUX-045: 분류 불가 = 회색 1px 점선)이므로, 결측 거래대금도 점선을 쓰면 두 상태가 **구분 불가**해진다. 차트별로 분기한다.

- **Given** `trading_value: null`인 버블에서
- **Then** 두 차트 모두 `symbolSize === 2×r_min`이고 툴팁에 `거래대금 데이터 없음`이 포함된다.
- **And** 0으로 치환되지 않는다 — `u` 계산에 그 값이 참여하지 않는다(고정 눈금 채택 후에도 툴팁 실제 값 표기 대상에서 제외).
- **And (섹터 버블)** `itemStyle.borderType === 'dashed'`다.
- **And (종목 버블)** `itemStyle`의 `borderType` / `borderWidth` / `borderColor`가 **해당 종목의 Stage가 결정한 값과 동일**하다 — 결측 거래대금이 테두리를 바꾸지 않는다.
- **And 구분 가능성 단언**: 종목 버블에서 `{stage: 2, trading_value: null}`과 `{stage: null, trading_value: 1e10}` 두 버블의 테두리가 **서로 다르다**(전자 = 흰 2px 실선, 후자 = 회색 1px 점선). 이전 판의 규칙에서는 전자도 점선이 되어 구분이 무너졌다.

### AC-SUX-041 — axisPointer 삭제 (규칙 VZ-4)

- **When** `grep -n "axisPointer" frontend/src/components/SectorAnalysis/SectorBubbleChart.tsx`를 실행하면
- **Then** 출력이 **0행**이다.
- **And** ECharts option에 `markLine`은 그대로 존재한다(참조선 유지 확인).

### AC-SUX-042 — 기준선 의미 표기 (규칙 VZ-5)

- **Then** 섹터 버블의 X=0 `markLine` 라벨 텍스트에 벤치마크 이름과 **실제 값**이 포함된다(예: `전체 상한가중 +1.88%`).
- **And** 종목 버블의 X 기준선이 `0`이 아니라 응답의 `sector_aggregate` 값 위치에 있고, 라벨에 섹터명과 값이 포함된다.
- **And** 종목 버블의 `0` 선은 **보조선으로 남되 더 연한 색**이다(두 markLine의 색상 값이 다름).

### AC-SUX-043 — 축 범위 (규칙 VZ-6)

- **Given** X 데이터가 전부 양수인 픽스처에서
- **Then** `xAxis.min <= 0`이다(0을 항상 포함).
- **And** X축 `axisLabel.formatter` 결과가 `+1.5%` 형태 부호 표기다.
- **And** Y축(RS)은 `min:0, max:100` 고정이다.

### AC-SUX-044 — RRG 사분면 의미 표기 (규칙 VZ-7)

- **Then** 4개 사분면 라벨 텍스트가 각각 벤치마크 대비 의미를 포함한다(예: `Leading (전체 상한가중 대비 강함·개선)`).
- **And** 범례 영역에 `기준선 100 = 벤치마크(...)와 동일 성과` 한 줄이 **상설** 렌더된다.
- **And** 벤치마크 이름이 응답 `benchmark_name`에서 오며 시장 토글에 따라 바뀐다.

### AC-SUX-045 — RRG 축 자동 대칭 (규칙 VZ-8)

- **Given** 표시 중인 점의 `max(|v − 100|) === 11`이면
- **Then** `half === Math.max(5, Math.ceil(11 * 1.1)) === 13`, `min === 87`, `max === 113`이며 100이 정확히 중앙이다.

> **이전 판의 탈출구 제거**: 이전 판은 `half === ceil(11 × 1.1) === 13` **`(또는 명세된 반올림 규칙)`**이라고 적었다. 괄호 안 문구가 어떤 결과값이든 "명세된 규칙을 따랐다"고 주장하면 통과시켜 주므로 **단언이 아무것도 고정하지 못했다.** 공식은 `02-screen-flow.md §9.4 VZ-8`에 이미 확정되어 있다 — `half = max(5, ceil(max(|v−100|) × 1.1))`. 그 공식의 결과를 리터럴로 못 박는다.

- **And** 경계 케이스를 리터럴로 고정한다: `max|v−100| = 10` → `half === 11`; `= 4` → `half === 5`(최소 반폭 구속); `= 0` → `half === 5`.
- **And** **대조 단언**: `× 1.1` 계수나 `Math.max(5, ...)` 하한을 제거한 변형에서 위 케이스 중 최소 1건이 **실패**한다.
- **And** 모든 점이 100에 근접한 픽스처(`max|v−100| = 0.3`)에서 `half === 5`(최소 반폭)로 과확대되지 않는다.
- **And** `grep -n "min: 75\|max: 125" RRGChart.tsx` → 0행.

### AC-SUX-046 — RRG 궤적 시작·벤치마크 추종 (규칙 VZ-9/VZ-10)

- **Then** 스파크라인 헤더 텍스트에 응답의 `lookback_weeks`와 `trail_start_date`가 포함된다.
- **And** 시장 토글이 `KOSDAQ`일 때 스파크라인 라벨과 시리즈가 KOSDAQ으로 바뀐다 — `KOSPI` 하드코딩(`RRGChart.tsx:94, 288`)이 남아 있지 않다(grep 0행).

### AC-SUX-047 — Stage 테두리 채널 (규칙 VZ-0)

- **Given** stage가 각각 2 / 1 / 3 / 4 / null인 5개 종목 버블에서
- **Then** `itemStyle.borderWidth`/`borderColor`/`borderType`이 각각 (2px 흰 실선) / (없음) / (없음) / (1px 어두운 회색) / (1px 회색 점선)이다.
- **And** 툴팁에 Stage 라인이 유지된다.

### AC-SUX-048 — **색상 채널 회귀 금지** [보존 계약]

- **Then** 동일 `sector_minor`를 가진 종목들의 `itemStyle.color`가 서로 **동일**하고, 서로 다른 `sector_minor`는 **다른** 색이며, null/오버플로는 `#9CA3AF`(기타)다.
- **And** 색상 매핑이 `stage` 값에 **의존하지 않는다** — 동일 데이터에서 stage만 바꾼 픽스처의 색상 배열이 동일하다.
- **And** `legend.data`가 `(count desc, name asc)` 정렬을 유지하고 `기타`가 마지막이다.
- **And** 리렌더 2회 간 색상 배열이 동일하다(결정성).
- **근거**: `SPEC-SECTOR-MINOR-COLOR-001` + `StockBubbleChart.tsx:28` `@MX:ANCHOR`.

### AC-SUX-049 — 다크 배경 대비 (규칙 VZ-11)

- **Given** 배경 `#1a1a2e`와 팔레트 10색 + `#9CA3AF`에서
- **When** 각 색의 상대 휘도 대비비를 계산하면
- **Then** **모든** 색이 `>= 3.0`이다(계산 함수 포함한 테스트).
- **And** 현행 팔레트 0번 `#4E79A7`이 기준 미달이면 교체된 값이 기준을 만족한다.

### AC-SUX-050 — 기타 범례 개수 병기 (규칙 VZ-12 신규분)

- **Given** 오버플로 + null로 `기타`에 7개 산업이 묶였을 때
- **Then** 범례 항목 텍스트가 `기타 (7개 산업)` 형태로 개수를 포함한다.

### AC-SUX-051 — hover 강조 범위 (규칙 VZ-13)

- **Then** 종목 버블 산점도의 `series.emphasis.focus === 'none'`이다.
- **And** 범례 항목 hover 시에는 해당 그룹만 유지하고 나머지가 블러된다(`highlight` 액션 경로).
- **And** RRG(`RRGChart.tsx:221`)와 Bump(`BumpChart.tsx:99-108`)의 `focus: 'series'`는 **그대로 유지**된다(변경 금지 회귀 단언).

---

## 6. 오류·빈 상태

### AC-SUX-052 — 셀 수준 5상태 (규칙 ER-1)

- **Given** 한 행에 `{value:null, reason:'missing'}`, `0.0`, `{value:null, reason:'insufficient'}`, `{value:42, low_confidence:true}`, `{value:42, warnings:[...]}` 5셀이 있을 때
- **Then** 각각 `–` / `0.00%` / `계산 불가` / `42 ⚠` / `42 ❗`로 렌더된다.
- **And** 동일 상태가 순위표·버블·RRG·Bump·종목 탐색 5개 화면에서 **같은 텍스트·같은 스타일**로 렌더된다(공용 컴포넌트 단언).
- **And** `계산 불가` / `⚠` / `❗`에 사유 툴팁이 붙는다.

### AC-SUX-053 — 결측의 0/50.0 렌더 금지 (규칙 ER-2)

- **Given** `null`이 섞인 응답 픽스처에서
- **When** 전 화면을 렌더하면
- **Then** DOM 텍스트에 `NaN` 문자열이 **0건**이고, 결측 자리에 `0.0%` / `50.0`이 나타나지 않는다.
- **And** 런타임 예외가 발생하지 않는다 — 현행 `formatReturn`의 무조건 `toFixed(1)` 경로가 제거되었다.

### AC-SUX-054 — 빈 상태는 원인을 말한다 (규칙 ER-3)

- **Given** 섹터=디스플레이 + Stage=2 + 시장=KOSPI로 결과가 0건일 때
- **Then** 활성 필터 3개가 모두 텍스트로 표시되고, `[Stage 필터 해제]` / `[시장 전체로]` / `[섹터 스코프 해제]` 액션이 렌더된다.
- **And** 각 액션 클릭 시 해당 상태만 해제된다.

### AC-SUX-055 — 섹터 상세 오류 표시 (규칙 §10.2, LD-7 해소)

- **Given** 상세 fetch가 실패하도록 mock했을 때
- **Then** 상세 패널에 오류 상태와 `[다시 시도]`가 렌더된다.
- **And** `grep -n "catch(() => {})" frontend/src/components/SectorAnalysis/SectorDetailPanel.tsx` → 0행.
- **And** `Sub-sector breakdown available in future update` 문자열이 코드베이스에서 **사라진다**(grep 0행).

### AC-SUX-056 — **회귀 방지 AC**: 기대되는 변화

전부 **올바른 결과**다. 테스트 docstring에 "의도된 변화"를 명시한다.

| # | 변화 | 단언 |
| --- | --- | --- |
| R1 | 기간을 바꾸면 로딩이 생긴다 (이전엔 클라이언트 재정렬이라 즉시) | 로딩 인디케이터 렌더 단언 + 아래 grep |
| R2 | 정렬을 바꾸면 안내 띠가 뜬다 | 고지 띠 렌더 단언 + 아래 grep |
| R3 | 버블 크기 분포가 바뀐다 (15/29가 2px 밴드에 뭉치던 상태 해소) | 크기 배열의 표준편차가 선형 방식 대비 증가 |
| R4 | RRG 궤적이 짧아진다 | `trail.length < history.length` |
| R5 | KOSPI 필터 시 순위표 행 수가 줄고 하단 제외 영역이 생긴다 | 행 수 감소 + `excluded` 영역 렌더. **검증 범위 = Table · 섹터 Bubble · RRG 한정** (Bump 제외 — O-U9 확정, 아래) |

#### R1 / R2 — "그런 테스트가 없음을 확인한다"를 실행 가능하게

이전 판의 "**로딩 부재를 요구하는 테스트가 없음**을 확인", "띠 부재를 요구하는 테스트 없음"은 **확인 절차가 없어 실행할 수 없다.** 각각 긍정 단언 + grep 부재 확인 2단으로 대체한다:

- **R1 긍정**: `period`를 `1w → 3m`으로 바꾸면 로딩 인디케이터가 `기준일 배지` 옆에 렌더된다(`findByTestId('refetch-spinner')`).
- **R1 부재 확인 (실행 명령)**:
  ```bash
  grep -rnE "queryBy(TestId|Text)\(.*(spinner|loading|로딩).*\)\s*\)\.(toBeNull|not\.toBeInTheDocument)" \
       frontend/src/components/SectorAnalysis/__tests__/ frontend/src/components/StockExplorer/__tests__/
  ```
  → **0행**. 기간 변경 경로에서 로딩 부재를 요구하는 단언이 없다.
- **R2 긍정**: 비-`rank` 열로 정렬하면 고지 띠가 렌더된다(AC-SUX-022와 동일 대상).
- **R2 부재 확인 (실행 명령)**:
  ```bash
  grep -rnE "queryBy(TestId|Text)\(.*(sort-notice|정렬 고지|순위순으로).*\)\s*\)\.(toBeNull|not\.toBeInTheDocument)" \
       frontend/src/components/SectorAnalysis/__tests__/
  ```
  → **0행**. 단, `rank` 정렬 상태에서 띠가 없어야 한다는 AC-SUX-022의 정당한 단언은 **allowlist로 명시 제외**한다(테스트 파일명 + 라인 주석으로 표시).

#### R5 — O-U9(②의 O-A7) **해결** (2026-08-14 사용자 결정)

R5와 **AC-SUX-019**(제외 섹터 가시성)는 v0.3.0까지 "AG-5(최소 구성수 5)가 Bump에도 적용된다"를 암묵 전제로 했다. 그 전제는 **거짓이었다.**

**결정: AG-5는 Bump에 적용하지 않는다.** `01 §5.4 AG-5`가 "순위·버블·RRG"만 명시하고 Bump를 언급하지 않은 것이 곧 계약이며, ②의 출하 구현도 이미 그렇게 동작한다(`sector_metrics.py:947-948` 주석 + `get_sector_history`의 `excluded=` 미전달 — AC-SUX-019 배경 실측 참조). 따라서 ②의 백엔드 변경은 **없다.**

확정된 검증 범위:

- R5·AC-SUX-019의 검증 범위는 **Table · 섹터 Bubble · RRG로 한정**한다. Bump는 대상이 아니다.
- Bump에 대해서는 **반대 방향 단언**을 둔다 — 제외 섹터의 선이 Bump에 **남아 있어야 한다**(AC-SUX-019의 `mut_bump_applies_ag5` 대조 변형). 범위에서 뺀 채 아무 단언도 두지 않으면, 이후 누군가 Bump에 AG-5를 넣어도 어떤 AC도 반대하지 않는다 — Lesson #3(신규 동작이 어떤 게이트에도 안 걸려 그림자 결함이 된 선례)의 재현 경로다.
- **`connectNulls:false` 선 끊김 단언은 도입하지 않는다.** 그 단언은 "Bump에도 적용" 분기에서만 필요했다. `connectNulls:false` 자체는 §1.2 보존 항목으로 **그대로 유지**되며(다른 사유의 결측 처리), 본 결정으로 변경되지 않는다.
- **잔여 위험 (범위 밖, 관측만)**: Bump와 Table은 서로 다른 섹터 모집단 위에서 순위를 매긴다(Bump = 전 섹터, Table `data[]` = AG-5 통과 섹터). 따라서 같은 주·같은 섹터의 rank가 두 화면에서 다를 수 있다. 이는 본 결정의 **의도된 귀결**이며 회귀가 아니다. `CT-4`(AC-SUX-021)의 rank 일치 단언은 **순위표 내부**(rank 열 ↔ 행 순서)에 한정되며 Table↔Bump 교차 일치를 요구하지 않는다 — 요구하도록 확대하지 말 것.

### ~~AC-SUX-057~~ — **결번** (REQ-SUX-054 철회)

산업명(중) 필터는 구현하지 않기로 결정되어(2026-08-12 사용자 결정, spec.md §3.7) 이 AC는 삭제되었다. **번호는 재사용하지 않는다** — 재사용하면 이력 추적이 끊긴다.

- **대신 유지되는 단언 (범위 밖 확인)**: `frontend/src/components/StockExplorer/StockTable.tsx`의 필터 술어에 `sector_minor` 분기가 **추가되지 않았음**을 확인한다 — `grep -n "sector_minor" frontend/src/components/StockExplorer/StockTable.tsx` → **0행**. 범위 밖 기능이 슬쩍 들어오는 것을 막는다.
- **And** `sector_minor` 필드 자체는 종목 버블(`StockBubbleChart.tsx`)에서 계속 소비된다 — 색상 매핑·범례·툴팁(AC-SUX-048 보존 계약). 필드 소비와 필터 술어는 별개다.

### AC-SUX-058 — 순위의 총 섹터 수 병기 (REQ-SUX-055) [설계서 미수용분 해소]

- **Given** 응답 `data[]`에 `rank`가 부여된 섹터 27개 + `rank is null` 2개, `excluded[]` 2개인 픽스처에서
- **Then** 순위 표시가 `7 / 27` 형태로 **분자(해당 섹터 rank)와 분모(순위 대상 총수)를 함께** 렌더한다.
- **And** 분모가 **27**이다 — 전체 29가 아니다. `excluded`된 섹터는 분모에서 빠진다.
- **And** `market=kospi`로 제외가 늘어난 픽스처에서 분모가 **줄어든다**(동일하면 하드코딩).
- **And** **정적 스캔**: `grep -rnE "/\s*29|29\s*개 섹터" frontend/src/components/SectorAnalysis/` → **0행**. 총 섹터 수를 상수로 박지 않는다.
- **And** 분모가 `data[]` 중 `rank !== null`인 개수에서 도출되며, 프론트가 별도 카운터를 두지 않는다.

### AC-SUX-059 — 섹터 버블 색상 채널 (REQ-SUX-056) [설계서 미수용분 해소]

- **Given** 기간 수익률이 `[-12%, -3%, 0%, +4%, +15%]`인 5개 섹터 버블에서
- **Then** 각 버블의 `itemStyle.color`가 **발산형 5단계 팔레트의 서로 다른 5색**에 매핑된다.
- **And** 발산 기준점이 **0%**다 — `0%` 버블이 중립색(팔레트 중앙)이다. 벤치마크 값 기준이 **아니다**(벤치마크가 `+1.88%`인 픽스처에서도 중립색은 `0%` 버블에 붙는다).
- **And** 5단계 경계값이 **상수 단일 위치**에 정의되고, 색상 범례에 **실제 구간 값**이 텍스트로 표기된다(예: `≤−10% / −10~−3% / −3~+3% / +3~+10% / ≥+10%`).
- **And** 범례 없이 색상 채널이 렌더되는 경로가 없다(범례 컴포넌트 필수 렌더 단언 — 크기 범례 VZ-2와 동일 원칙).
- **And 채널 독립 단언**: X축(초과수익률)을 고정한 채 기간 수익률만 바꾼 픽스처에서 **색이 바뀐다**. 반대로 기간 수익률을 고정하고 초과수익률만 바꾸면 **색이 바뀌지 않는다** — 색이 X축의 중복 인코딩이 아님을 증명한다(VZ-0).
- **And** **종목 버블의 색상 배열에는 영향이 없다**(AC-SUX-048 회귀 단언 동시 통과).

### AC-SUX-060 — 버블 테두리 채널 단일화 (REQ-SUX-057) [VZ-0 충돌 해소]

- **Given** 저커버리지(`coverage_ratio: 0.6`) + 결측 거래대금(`trading_value: null`) + `stage: 2`가 동시에 성립하는 종목 버블에서
- **Then** 테두리가 **Stage 2의 값**(흰색 2px 실선)이다 — 저커버리지도 결측 거래대금도 테두리를 덮어쓰지 않는다.
- **And** 저커버리지는 **툴팁의 `⚠`**와 **하단 저신뢰 요약 목록**으로 표현된다(테두리 미사용).
- **And (섹터 버블)** 저커버리지 + 결측 거래대금이 동시 성립하면 테두리가 **점선**(결측 거래대금)이며, 저커버리지는 툴팁·하단 요약으로 표현된다.
- **And 정적 스캔**: 테두리 속성을 커버리지에서 도출하는 코드가 없다 —
  ```bash
  grep -rnE "coverage.*border|border.*coverage|low_confidence.*border" \
       frontend/src/components/SectorAnalysis/
  ```
  → **0행**.
- **And 채널 1:1 단언**: 종목 버블에서 `borderType`/`borderWidth`/`borderColor` 3속성이 **오직 `stage` 값의 함수**임을 확인한다 — `stage`를 고정한 채 `coverage_ratio`·`trading_value`를 바꾼 픽스처들의 테두리 속성이 **전부 동일**하다.

### AC-SUX-061 — 좁은 화면 열 접기 우선순위 (REQ-SUX-058, §7 O-U7 결정)

- **Given** 종목 표 12열이 렌더된 상태에서 뷰포트 폭을 단계적으로 줄이면
- **Then** 열이 **섹터비중 → Vol배 → 52W고** 순서로 숨겨진다(3단계, 순서 단언).
- **And** **1W% / 1M% / 3M% · Stage · RS · Name 열은 어떤 폭에서도 숨겨지지 않는다** — Lesson #3 게이트. 기간 3열이 좁은 화면에서 사라지면 AC-SUX-032(default 진입 가시성)의 취지가 무너진다.
- **And** 숨겨진 열의 값은 **행 확장 또는 툴팁으로 접근 가능**하다 — 정보가 소실되지 않는다(A5 모바일 대응).
- **And** 폭을 되돌리면 숨겨진 열이 **원래 순서대로 복귀**한다.
- **And** 3열 전부 숨긴 뒤에도 넘치면 **가로 스크롤**로 처리하고 추가로 열을 숨기지 않는다.

---

## 7. 에지 케이스

| # | 상황 | 기대 |
| --- | --- | --- |
| E1 | `selectedSector`가 응답 `data[]`에 없음 (제외됨) | CT-3 안내. 선택 유지 |
| E2 | 응답 `excluded[]`가 빈 배열 | 제외 영역 자체를 렌더하지 않음 |
| E3 | `by_sector`에 `selectedSector` 키가 없음 | 분포 바를 전체로 폴백하고 헤더에 그 사실을 명시 (조용한 불일치 금지) |
| E4 | 버블 데이터가 1개 | `v_max == v_min` → 중간 크기 1개. 범례는 단일 값 표기 |
| E5 | RRG `trail[]`이 빈 배열 | `RRG 데이터가 없습니다` + `trail_start_date` 부재 사유 표기 |
| E6 | 모바일 폭(<768px) | hover 정보가 전부 본문/탭으로 접근 가능. 배지·라벨이 잘리지 않음 (A5) |
| E7 | 종목 표 12열이 좁은 화면에서 넘침 | **O-U7 결정 (해결됨)**: 섹터비중 → Vol배 → 52W고 순으로 접는다. 기간 3열·Stage·RS·Name은 접지 않는다. 3열 접은 뒤에도 넘치면 가로 스크롤. AC-SUX-061 |
| E8 | `focusStock`을 받은 차트 그리드에 그 종목이 **이미 있음** | **O-U6 결정 (해결됨)**: 해당 셀로 **스크롤 + 일시 하이라이트**하고 **중복 추가하지 않는다**. 기존 그리드를 교체하지 않는다 |
| E10 | `focusStock`을 받았는데 그 종목이 그리드에 **없음** | **O-U6 결정**: 그리드 끝에 **추가**한 뒤 스크롤·하이라이트한다 |
| E11 | `focusStock` 수신 시 그리드가 **정원 도달** | 추가하지 않고 안내를 표시한다. **조용히 다른 종목을 밀어내지 않는다** — 사용자가 구성한 그리드를 파괴하지 않는다는 O-U6 결정의 연장 |
| E9 | 두 패널이 동시에 로딩 중이라 `as_of_date`가 하나만 존재 | 경고 띠를 띄우지 않는다 (둘 다 도착한 뒤 비교) |

---

## 8. 품질 게이트 (Definition of Done)

- [ ] AC-SUX-001 ~ AC-SUX-056, AC-SUX-058 ~ AC-SUX-061 전부 PASS (**AC-SUX-057은 결번** — REQ-SUX-054 철회)
- [ ] **AC-SUX-032 (default 진입 가시성) PASS** — Lesson #3 [HARD] 게이트
- [ ] **AC-SUX-048 (색상 채널 회귀 금지) PASS** — `SPEC-SECTOR-MINOR-COLOR-001` 보존 계약
- [ ] `SPEC-SECTOR-AGGREGATION-001` close 확인
- [x] ~~**②의 O-A7(최소 구성수 5의 Bump 적용) 해소 확인**~~ — **해결 (2026-08-14): 미적용 확정.** AC-SUX-019 / AC-SUX-056 R5의 검증 범위를 Table·섹터 Bubble·RRG로 한정. ② 백엔드 변경 없음
- [ ] **AC-SUX-019의 Bump 반대 방향 단언 PASS** — 제외 섹터의 선이 Bump에 남아 있음 + `mut_bump_applies_ag5` 되돌림 **RED 관측** verbatim 기록 (Lesson #9 [HARD] 게이트)
- [ ] **tsc 게이트 (a) HARD**: `npx tsc -p tsconfig.app.json --noEmit 2>&1 | grep -c "error TS2353"` → **0**
- [ ] **tsc 게이트 (b) 회귀**: 총 오류 수 `<= N` (baseline `N`을 progress.md §E.2에 기록 — 측정 시점 실측 `N = 33`) **AND** ③가 수정한 파일에서 NEW 오류 0건
- [ ] (b)의 완화가 (a)를 약화시키지 않았음을 확인 — `TS2353 == 0`은 총량 조건과 무관하게 독립 HARD 게이트다
- [ ] 신규/변경 컴포넌트·컨텍스트 커버리지 >= 85%
- [ ] 기존 프론트엔드 테스트 전량 통과 (회귀 0건)
- [ ] §0.2 성능 baseline/목표 실측 기록 (progress.md §E.2) — 특히 **Context 분리에 따른 리렌더 범위** 측정
- [ ] §1.2 보존 대상 10항목이 변경되지 않았음을 확인 (grep/단언)
- [ ] §0.3 제거 목록 X1~X6가 실제로 제거되었음을 grep으로 확인
- [ ] 모바일(<768px) 시뮬레이션에서 hover-only 정보 0건 (Lesson #1, A5)
- [ ] `@MX:ANCHOR` — `NavIntent` 소비 조건, `AnalysisParamsContext` 소유권, 버블 크기 매핑 3지점
- [ ] ship commit에 frontmatter `status` 갱신 포함 (Lesson #6)
- [ ] §7 미결 해소 상태 확인 — **해결됨**: O-U1(비활성+툴팁, 잠정) · O-U4(기간별 고정 눈금) · O-U6(스크롤·하이라이트 or 추가) · O-U7(접기 우선순위). **추가 해결**: **O-U9(②의 O-A7 전파 — 2026-08-14 AG-5 Bump 미적용 확정)**. **미결 유지**: O-U2(URL 동기화) · O-U3(2섹터 비교) · O-U5(워치리스트 접점) · O-U8(저커버리지 시각 인코딩) — **전부 착수 차단 항목 아님**
- [ ] §0.1 정량 지표가 자동 검증 3항목(rank 불일치 0 / 기준일 불일치 경고 0 / 되돌아가기 UI 0)으로 측정됨. "탭 전환 4회 이하"는 측정 절차 부재로 삭제되어 정성 지표로 이관됨
