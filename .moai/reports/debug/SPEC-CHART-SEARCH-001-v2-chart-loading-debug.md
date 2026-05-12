# v2.0.0 차트 미표시 root cause 진단

## Verification 결과

### V1: Hot Reload 확인

**PASS** — commit `e93dc15` 존재 확인. ChartGrid.tsx line 295에 `style={{ height: '100%', minHeight: 0 }}` 코드가 실제로 적용되어 있음. Vite HMR 정상 작동했으나 fix 자체가 불완전하여 증상이 지속된 것.

### V2: CSS 체인 정확한 측정

```
.chart-grid (display:flex; flex-direction:column; overflow:hidden)
  └─ .chart-grid-cells (flex:1; display:grid; grid-template-rows:repeat(2,1fr); overflow:hidden)
       └─ wrapper <div> style={{ height:'100%', minHeight:0 }}    ← 그리드 아이템 (NEW in v2.0.0)
            └─ .chart-cell (display:flex; flex-direction:column; min-height:0; overflow:hidden)
                 ├─ .chart-cell-header (flex-shrink:0) → ~40px 확정
                 └─ .chart-cell-canvas-wrap (flex:1; min-height:0)
                      └─ .chart-cell-canvas (width:100%; height:100%)
```

**각 element의 effective height 추론:**

| Element | CSS | Effective Height | 이유 |
|---------|-----|-----------------|------|
| `.chart-grid-cells` | `flex:1; display:grid; grid-template-rows:repeat(2,1fr)` | 확정 (e.g., 600px) | flex:1로 부모 flex column에서 stretch |
| wrapper `<div>` | `height:100%; minHeight:0` | 300px (1fr = 50%) | 그리드 아이템 → containing block = grid area = 1fr 트랙 |
| `.chart-cell` | `display:flex; flex-direction:column; min-height:0` | **~40px (헤더 높이만)** | **wrapper는 block container → 자식이 자동 stretch 안 됨. height:100% 없음** |
| `.chart-cell-canvas-wrap` | `flex:1; min-height:0` | **0px** | flex 컨테이너(.chart-cell)에 확정 높이 없음 → flex:1이 분배할 공간 없음 |
| `.chart-cell-canvas` | `width:100%; height:100%` | **0px** | containing block(canvas-wrap) = 0px |

**결과:** `container.clientHeight = 0` → `createChart(container, { height: 0 })` → lightweight-charts 0px 캔버스 생성 → 캔들 미표시.

헤더가 보이는 이유: `.chart-cell-header`는 `flex-shrink:0`로 header 자신의 content height(~40px)를 유지. 캔버스 부분만 0.

### V3: chore base vs v2.0.0 비교

**chore base** (grid item = `.chart-cell` 직접):
```tsx
// ChartGrid.tsx (chore/integrated-main-merge-2026-04-25)
{visibleStocks.map((stock, slotIndex) => (
  <ChartCell
    key={`${stock.code}-${currentPage}`}
    stock={stock}
    ...
  />
))}
```

`.chart-cell`이 직접 CSS Grid item → `align-self: stretch` (default) → `.chart-cell`의 layout height = grid track height (300px) → flex:1 체인 정상 작동.

**v2.0.0** (grid item = wrapper `<div>`, `.chart-cell`은 block child):
```tsx
// ChartGrid.tsx (e93dc15) — lines 293-309
<div
  key={stock.code}
  style={{ height: '100%', minHeight: 0 }}
  data-highlight-target={...}
  data-testid={testId}
>
  <ChartCell stock={stock} ... />
</div>
```

wrapper `<div>`가 grid item 자리를 차지 → wrapper는 `display:block` (기본값) → `.chart-cell`은 block 자식 → height stretch 없음 → 높이 체인 단절.

**핵심 차이:** chore base에서 CSS Grid의 `align-self:stretch`가 `.chart-cell`에 직접 적용되었으나, v2.0.0에서는 wrapper에 적용되고 `.chart-cell`은 stretch를 받지 못함.

### V4: 대안 가설 점수

| 가설 | 점수 | 근거 |
|------|------|------|
| (a) Hot reload 실패 — stale JS | 1/10 | 파일 내 코드 확인됨 (line 295). HMR은 정상 |
| (b) ChartCell mount 자체 실패 (lw-charts 에러) | 2/10 | 헤더가 표시됨 = mount 성공. chart 인스턴스는 생성되나 0px로 생성됨 |
| (c) fetchChartData setData 실패 (mock data shape 불일치) | 2/10 | loading state가 사라지고 빈 화면 → 데이터 로드 완료 후 캔버스가 0px인 것 |
| (d) `.chart-cell` display:flex의 flex-direction 충돌 | 3/10 | column 방향은 올바름. 문제는 flex 컨테이너에 확정 높이가 없는 것 |
| **(e) wrapper div가 `.chart-cell`에 높이를 전달하지 못함** | **9/10** | **확정 root cause. block container의 자식은 자동 stretch 없음** |

---

## 최종 Root cause 진단

wrapper `<div style={{ height:'100%', minHeight:0 }}>` 가 `display:block` (기본값)이므로 그 block child인 `.chart-cell`은 wrapper의 높이를 상속받지 못하고 content height(~40px 헤더만)로 collapse하여, flex:1 의존 체인(`chart-cell → canvas-wrap → canvas`)이 모두 0px로 무너지고 `createChart(container, { height: container.clientHeight })` 호출 시 height=0 으로 lightweight-charts 인스턴스가 생성된다.

---

## 추천 Fix 방향 (3개 옵션 비교)

### Option A: wrapper에 `display: flex; flex-direction: column` 추가

**변경 위치:** ChartGrid.tsx line 294–295 (wrapper div inline style)

```tsx
// Before
style={{ height: '100%', minHeight: 0 }}

// After
style={{ height: '100%', minHeight: 0, display: 'flex', flexDirection: 'column' }}
```

**동작:** wrapper가 flex container가 되어 `.chart-cell`(유일한 flex 자식)이 `align-self:stretch`(default)로 wrapper 높이를 채움. `.chart-cell`에 확정 높이가 생겨 flex:1 체인 복원.

**부작용:** 없음. `.chart-cell`에 CSS 변경 불필요.

**회귀 위험:** 낮음. wrapper가 생기기 전 chore base 동작을 flex 경유로 복원. `data-highlight-target`/`data-testid` DOM 속성 영향 없음.

---

### Option B: wrapper에 `display: contents` 적용 (권장)

**변경 위치:** ChartGrid.tsx line 294–295 (wrapper div inline style)

```tsx
// Before
style={{ height: '100%', minHeight: 0 }}

// After
style={{ display: 'contents' }}
```

**동작:** `display:contents`는 wrapper 박스를 레이아웃 트리에서 제거. `.chart-cell`이 직접 CSS Grid item이 되어 `align-self:stretch`가 `.chart-cell`에 적용 → chore base와 동일한 레이아웃. DOM 노드는 존재하므로 `querySelector('[data-highlight-target="..."]')`과 `data-testid` 모두 정상 작동.

**부작용:** wrapper 자체의 시각적 표현(border, padding 등)이 적용되지 않음 — 하지만 wrapper는 시각적 스타일 없음. `display:contents`에서는 wrapper에 걸린 이벤트 핸들러가 작동하지 않으나 wrapper에 이벤트 핸들러 없음.

**회귀 위험:** 가장 낮음. chore base의 layout과 100% 동일한 결과. `display:contents` 브라우저 지원: Chrome 65+, Firefox 37+, Safari 11.1+ (모두 지원).

---

### Option C: global.css `.chart-cell`에 `height: 100%` 추가

**변경 위치:** `frontend/src/styles/global.css` line 813–823 (`.chart-cell` 규칙)

```css
/* Before */
.chart-cell {
  ...
  min-height: 0;
}

/* After */
.chart-cell {
  ...
  min-height: 0;
  height: 100%;
}
```

**동작:** `.chart-cell`이 block child일 때도 containing block(wrapper div의 100% = grid track)을 기준으로 높이를 계산 → 확정 높이 확보. flex:1 체인 복원.

**부작용:** `.chart-cell`이 직접 grid item인 경우(chore base 등 다른 컨텍스트)에도 `height:100%`가 적용됨. CSS Grid item에서는 grid area가 containing block이므로 동일한 결과. `.chart-cell`이 다른 비정의 높이 컨텍스트에서 사용되면 예기치 않은 stretch 발생 가능.

**회귀 위험:** 중간. CSS 전역 변경. 현재 `.chart-cell`은 ChartGrid에서만 사용되므로 실질 위험은 낮지만, 글로벌 CSS 변경이라 미래 재사용 시 주의 필요.

---

## 권장 옵션 + 이유

**Option B (`display: contents`)를 권장.**

이유: wrapper div의 유일한 목적은 `data-highlight-target`과 `data-testid` DOM 속성을 보유하는 것이다. 레이아웃 역할이 없는 wrapper에는 `display: contents`가 의미론적으로 정확하다. 이 속성은 wrapper를 레이아웃 트리에서 제거하여 `.chart-cell`이 직접 그리드 아이템이 되게 하므로, chore base의 동작과 100% 동일한 CSS Grid + align-self:stretch 경로를 복원한다. DOM 노드는 유지되므로 `querySelector`·`data-testid` 기반 테스트 모두 영향 없다. 변경은 inline style 교체 1줄이며 CSS, ChartCell, 테스트 코드 수정이 일절 불필요하다. Option A도 기능상 동등하나 불필요한 flex 레이어를 추가한다. Option C는 글로벌 CSS를 건드리는 범위 초과 변경이다.

**구현:** ChartGrid.tsx line 294–295의 `style={{ height: '100%', minHeight: 0 }}` → `style={{ display: 'contents' }}` 교체.

---

*진단 일시: 2026-05-12*
*분석 범위: ChartGrid.tsx (e93dc15) + ChartCell.tsx + global.css + chore base ChartGrid.tsx*
