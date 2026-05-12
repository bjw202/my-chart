import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactElement } from 'react'
import { useTab } from './contexts/TabContext'
import { useScreen } from './contexts/ScreenContext'
import { DEFAULT_SCREEN_REQUEST } from './types/filter'
import type { StockItem } from './types/stock'
import type { StockMasterItem } from './api/stocks'
import { TabNavigation } from './components/TabNavigation/TabNavigation'
import { ContextBar } from './components/ContextBar/ContextBar'
import { FilterBar } from './components/FilterBar/FilterBar'
import { ChartGrid } from './components/ChartGrid/ChartGrid'
import { StockList } from './components/StockList/StockList'
import { StatusBar } from './components/StatusBar/StatusBar'
import { MarketOverview } from './components/MarketOverview/MarketOverview'
import { SectorAnalysis } from './components/SectorAnalysis/SectorAnalysis'
import { StockExplorer } from './components/StockExplorer/StockExplorer'
import { ThemeAnalysis } from './components/ThemeAnalysis/ThemeAnalysis'

// @MX:NOTE: [AUTO] AppContent는 TabContext 소비를 위해 App에서 분리됨.
//   searchedStock state lift: StockSearchBox → AppContent → ChartGrid prop drilling.
//   REQ-PERF-001: useScreen().results를 filterResults로 flatten하여 prop 전달.
//   → React.memo(ChartGrid) shallow equal로 ScreenContext cascade 차단 가능.

export function AppContent(): ReactElement {
  const { activeTab, crossTabParams, clearCrossTabParams } = useTab()
  const { applyFilters, results } = useScreen()

  // searchedStock: StockSearchBox onSelect 결과 — ChartGrid injectedStock으로 전달
  const [searchedStock, setSearchedStock] = useState<StockMasterItem | null>(null)

  // R1: Chart-grid 탭 활성화 시 crossTabParams.stockCodes로 필터 적용
  useEffect(() => {
    if (activeTab === 'chart-grid' && crossTabParams?.stockCodes?.length) {
      void applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes: crossTabParams.stockCodes })
      clearCrossTabParams()
    }
  }, [activeTab, crossTabParams, clearCrossTabParams, applyFilters])

  // REQ-PERF-001: useScreen().results를 flat StockItem[]으로 변환
  // useMemo: results reference가 바뀔 때만 재계산
  const filterResults: StockItem[] = useMemo(
    () => results?.sectors.flatMap((s) => s.stocks) ?? [],
    [results],
  )

  // onSelectStock: ChartGrid → AppContent searchedStock state 업데이트
  const handleSelectStock = useCallback((stock: StockMasterItem) => {
    setSearchedStock(stock)
  }, [])

  return (
    <div className="app">
      <TabNavigation />
      <ContextBar />

      {/* Tab content panels - all mounted, visibility toggled via CSS */}
      <div className="tab-content" style={{ display: activeTab === 'market-overview' ? 'flex' : 'none' }}>
        <MarketOverview />
      </div>

      <div className="tab-content" style={{ display: activeTab === 'sector-analysis' ? 'flex' : 'none' }}>
        <SectorAnalysis />
      </div>

      <div className="tab-content" style={{ display: activeTab === 'stock-explorer' ? 'flex' : 'none' }}>
        <StockExplorer />
      </div>

      {/* Chart Grid tab - default active; preserves existing FilterBar + ChartGrid + StockList layout */}
      <div className="tab-content" style={{ display: activeTab === 'chart-grid' ? 'flex' : 'none' }}>
        <FilterBar />
        <main className="app-main">
          <ChartGrid
            filterResults={filterResults}
            injectedStock={searchedStock}
            onSelectStock={handleSelectStock}
          />
          <StockList />
        </main>
      </div>

      <div className="tab-content" style={{ display: activeTab === 'theme-analysis' ? 'flex' : 'none' }}>
        <ThemeAnalysis />
      </div>

      <StatusBar />
    </div>
  )
}
