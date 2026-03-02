---
id: SPEC-UI-001
version: "1.0.0"
status: approved
created: "2026-03-02"
updated: "2026-03-02"
author: jw
priority: high
---

## HISTORY

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-03-02 | jw | Initial SPEC creation |

---

# SPEC-UI-001: Stock Watchlist Check & Export

## Overview

스크리닝된 종목을 브라우징하면서 관심 종목을 체크하고, 체크된 종목을 TradingView 관찰종목 형식(`KRX:448900,KRX:234590`)으로 일괄 Export하는 기능. 세션 동안만 체크 기록을 유지하며, 새로고침 시 초기화된다.

## EARS Requirements

### REQ-1: Watchlist State Management (State-Driven)

**While** the application is running, **the system shall** maintain an in-memory Map of checked stocks (code -> StockItem) that persists across filter changes within the same session.

**Acceptance**: 필터 재검색 후에도 이전에 체크한 종목이 유지되어야 한다.

### REQ-2: StockItem Checkbox (Event-Driven)

**When** the user clicks the checkbox area of a StockItem, **the system shall** toggle the stock's checked state without triggering navigation.

**Acceptance**: 체크박스 클릭 시 navigation(차트 선택)이 동작하지 않아야 하고, 체크박스 외 영역 클릭 시 기존 navigation이 정상 동작해야 한다.

### REQ-3: ChartCell Check Button (Event-Driven)

**When** the user clicks the check button on a ChartCell header, **the system shall** toggle the stock's checked state, synchronized with the StockList checkbox state.

**Acceptance**: ChartCell에서 체크 시 StockList의 해당 종목도 체크 상태가 동기화되어야 한다.

### REQ-4: Watchlist Tab View (State-Driven)

**While** the user is in "체크" tab mode in StockList, **the system shall** display only checked stocks in a flat list with individual uncheck buttons.

**Acceptance**: "전체" 탭에서는 기존 섹터별 목록 + 체크박스, "체크(N)" 탭에서는 체크된 종목만 표시.

### REQ-5: TradingView Export (Event-Driven)

**When** the user clicks the Export button, **the system shall** copy all checked stocks to clipboard in `KRX:{code}` comma-separated format and display "Copied!" feedback.

**Acceptance**: 클립보드에 `KRX:448900,KRX:234590` 형식으로 복사되어야 한다.

## Technical Constraints

- Session-only state: React Context with `Map<string, StockItem>`, no localStorage/DB
- Virtualized list compatibility: checked state must be lifted above react-window VariableSizeList
- Click conflict resolution: `e.stopPropagation()` on checkbox/button areas
- Export uses `navigator.clipboard.writeText()` (requires HTTPS or localhost)
- All codes use `KRX:` prefix regardless of KOSPI/KOSDAQ market

## Affected Components

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/contexts/WatchlistContext.tsx` | CREATE | Watchlist state management context |
| `frontend/src/components/StockList/StockItem.tsx` | MODIFY | Add checkbox with stopPropagation |
| `frontend/src/components/StockList/StockList.tsx` | MODIFY | Add tab view (all/checked) + Export |
| `frontend/src/components/ChartGrid/ChartCell.tsx` | MODIFY | Add check toggle button |
| `frontend/src/App.tsx` | MODIFY | Wrap with WatchlistProvider |
| `frontend/src/components/StatusBar/StatusBar.tsx` | MODIFY | Show checked count badge |
| `frontend/src/styles/global.css` | MODIFY | Checkbox, tab, button styles |
