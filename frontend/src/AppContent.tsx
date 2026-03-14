import React from 'react'
import { useTab } from './contexts/TabContext'
import { TabNavigation } from './components/TabNavigation/TabNavigation'
import { ContextBar } from './components/ContextBar/ContextBar'
import { FilterBar } from './components/FilterBar/FilterBar'
import { ChartGrid } from './components/ChartGrid/ChartGrid'
import { StockList } from './components/StockList/StockList'
import { StatusBar } from './components/StatusBar/StatusBar'

// @MX:NOTE: [AUTO] AppContent is extracted from App so it can consume TabContext
// Inside the provider tree, uses useTab to render tab panels via CSS display:none/block

export function AppContent(): React.ReactElement {
  const { activeTab } = useTab()

  return (
    <div className="app">
      <TabNavigation />
      <ContextBar />

      {/* Tab content panels - all mounted, visibility toggled via CSS */}
      <div className="tab-content" style={{ display: activeTab === 'market-overview' ? 'flex' : 'none' }}>
        <div className="tab-placeholder">Market Overview - Coming in SPEC-TOPDOWN-001C</div>
      </div>

      <div className="tab-content" style={{ display: activeTab === 'sector-analysis' ? 'flex' : 'none' }}>
        <div className="tab-placeholder">Sector Analysis - Coming in SPEC-TOPDOWN-001D</div>
      </div>

      <div className="tab-content" style={{ display: activeTab === 'stock-explorer' ? 'flex' : 'none' }}>
        <div className="tab-placeholder">Stock Explorer - Coming in SPEC-TOPDOWN-001E</div>
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
