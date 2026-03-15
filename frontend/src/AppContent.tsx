import { useEffect } from 'react'
import type { ReactElement } from 'react'
import { useTab } from './contexts/TabContext'
import { useScreen } from './contexts/ScreenContext'
import { DEFAULT_SCREEN_REQUEST } from './types/filter'
import { TabNavigation } from './components/TabNavigation/TabNavigation'
import { ContextBar } from './components/ContextBar/ContextBar'
import { FilterBar } from './components/FilterBar/FilterBar'
import { ChartGrid } from './components/ChartGrid/ChartGrid'
import { StockList } from './components/StockList/StockList'
import { StatusBar } from './components/StatusBar/StatusBar'
import { MarketOverview } from './components/MarketOverview/MarketOverview'
import { SectorAnalysis } from './components/SectorAnalysis/SectorAnalysis'
import { StockExplorer } from './components/StockExplorer/StockExplorer'

// @MX:NOTE: [AUTO] AppContent is extracted from App so it can consume TabContext
// Inside the provider tree, uses useTab to render tab panels via CSS display:none/block

export function AppContent(): ReactElement {
  const { activeTab, crossTabParams, clearCrossTabParams } = useTab()
  const { applyFilters } = useScreen()

  // R1: When navigating to chart-grid with stockCodes, apply codes filter
  useEffect(() => {
    if (activeTab === 'chart-grid' && crossTabParams?.stockCodes?.length) {
      void applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes: crossTabParams.stockCodes })
      clearCrossTabParams()
    }
  }, [activeTab, crossTabParams, clearCrossTabParams, applyFilters])

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
          <ChartGrid />
          <StockList />
        </main>
      </div>

      <StatusBar />
    </div>
  )
}
