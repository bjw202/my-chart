# SPEC-UI-001 Implementation Plan

## Architecture

### State Design

새로운 `WatchlistContext`를 생성하여 ScreenContext/NavigationContext와 독립적으로 관리한다.

- **Why separate context**: 체크 상태 변경 시 FilterBar나 ChartGrid pagination의 불필요한 re-render 방지. 필터 재검색으로 results가 변경되어도 watchlist는 독립 유지.
- **Why Map<string, StockItem>**: Set<string>보다 Map을 사용하는 이유는 이전 필터 결과에서 체크한 종목의 이름/코드를 체크 탭에서 표시해야 하기 때문.

```
WatchlistContext API:
- checkedStocks: Map<string, StockItem>
- isChecked(code): boolean
- toggleStock(stock): void
- uncheckStock(code): void
- clearAll(): void
- checkedCount: number
- exportText: string (computed KRX:code1,KRX:code2,...)
```

### Provider Hierarchy

```
ErrorBoundary
  ScreenProvider
    NavigationProvider
      WatchlistProvider     ← NEW
        <App UI>
```

### UI Changes

**StockItem (체크박스)**:
- flex-direction: column → row 변경
- 왼쪽 20px 영역에 14x14px 커스텀 체크박스
- e.stopPropagation()으로 navigation click 분리
- checked 시 좌측 초록 accent border

**StockList (탭 전환)**:
- 헤더: `[전체] [체크(N)] [Export]`
- viewMode state: 'all' | 'checked'
- all: 기존 섹터별 목록 + 체크박스
- checked: 체크된 종목만 flat list + 해제 버튼

**ChartCell (체크 버튼)**:
- TR 버튼 왼쪽에 체크 토글 버튼
- 미체크: `+`, 체크: `✓`
- 초록 강조 (.chart-cell-check-btn--on)

**StatusBar (카운트)**:
- `| 관심 N개` 표시 (checkedCount > 0일 때)

## Implementation Phases

### Phase 1: WatchlistContext 생성
- CREATE `frontend/src/contexts/WatchlistContext.tsx`
- Dependencies: None

### Phase 2: StockItem 체크박스
- MODIFY `frontend/src/components/StockList/StockItem.tsx` (props, checkbox UI)
- MODIFY `frontend/src/components/StockList/StockList.tsx` (context 소비, props 전달)
- MODIFY `frontend/src/styles/global.css` (checkbox styles)
- Dependencies: Phase 1

### Phase 3: StockList 탭 전환
- MODIFY `frontend/src/components/StockList/StockList.tsx` (viewMode, tab UI, Export)
- MODIFY `frontend/src/styles/global.css` (tab styles)
- Dependencies: Phase 2

### Phase 4: ChartCell 체크 버튼
- MODIFY `frontend/src/components/ChartGrid/ChartCell.tsx` (context, button)
- MODIFY `frontend/src/styles/global.css` (button styles)
- Dependencies: Phase 1

### Phase 5: App.tsx + StatusBar 통합
- MODIFY `frontend/src/App.tsx` (WatchlistProvider wrapping)
- MODIFY `frontend/src/components/StatusBar/StatusBar.tsx` (count badge)
- Dependencies: Phase 1

## Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|------------|
| StockItem flex-direction 변경으로 레이아웃 깨짐 | Medium | .stock-item-content wrapper로 기존 2줄 구조 유지 |
| react-window 가상화와 체크 상태 불일치 | Low | Context에서 isChecked() O(1) lookup, DOM 재활용 안전 |
| navigator.clipboard.writeText 실패 | Low | localhost에서 동작, 프로덕션 시 HTTPS 필요 |
| 체크박스 클릭이 navigation 트리거 | High | e.stopPropagation() 필수 적용 |
