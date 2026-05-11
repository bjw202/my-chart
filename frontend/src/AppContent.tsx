import { useCallback, useEffect, useRef, useState } from 'react'
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
import { ThemeAnalysis } from './components/ThemeAnalysis/ThemeAnalysis'
import { StockSearchModal } from './components/ChartGrid/StockSearchModal'
import type { StockSearchBoxHandle } from './components/ChartGrid/StockSearchBox'
import type { StockMasterItem } from './api/stocks'

// @MX:NOTE: [AUTO] AppContent is extracted from App so it can consume TabContext
// Inside the provider tree, uses useTab to render tab panels via CSS display:none/block
// selectedStock state here — ChartGrid는 React.memo로 격리되어 이 상태에 반응하지 않음 (MP-1)

export function AppContent(): ReactElement {
  const { activeTab, crossTabParams, clearCrossTabParams } = useTab()
  const { applyFilters } = useScreen()

  // 종목 검색 modal state (MP-1: ChartGrid가 이 상태에 반응하지 않아야 함)
  const [selectedStock, setSelectedStock] = useState<StockMasterItem | null>(null)
  const [selectedTimeframe, setSelectedTimeframe] = useState<'daily' | 'weekly'>('daily')
  const searchBoxRef = useRef<StockSearchBoxHandle | null>(null)
  const triggerRef = useRef<HTMLInputElement>(null)

  // R1: When navigating to chart-grid with stockCodes, apply codes filter
  useEffect(() => {
    if (activeTab === 'chart-grid' && crossTabParams?.stockCodes?.length) {
      void applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes: crossTabParams.stockCodes })
      clearCrossTabParams()
    }
  }, [activeTab, crossTabParams, clearCrossTabParams, applyFilters])

  // AC-MODAL-009: timeframe snapshot 계승 — ChartGrid 현재 timeframe을 modal에 전달
  // ChartGrid의 timeframe은 StockSearchBox onSelect 콜백 시점에 캡처되어야 하나,
  // 현재는 AppContent level에서 daily로 초기화 (간소화)
  const handleSelectStock = useCallback((stock: StockMasterItem): void => {
    setSelectedStock(stock)
    setSelectedTimeframe('daily')
  }, [])

  const handleModalClose = useCallback((): void => {
    setSelectedStock(null)
    searchBoxRef.current?.clearInput()
    // focus 복귀는 triggerRef를 통해 StockSearchModal 내부에서 처리
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
          <ChartGrid onSelectStock={handleSelectStock} />
          <StockList />
        </main>
      </div>

      <div className="tab-content" style={{ display: activeTab === 'theme-analysis' ? 'flex' : 'none' }}>
        <ThemeAnalysis />
      </div>

      <StatusBar />

      {/* StockSearchModal — portal mount on document.body (MP-4, AC-ARCH-001)
          ChartGrid subtree 외부에 mount되어 MP-1/MP-3 invariant를 보존한다 */}
      {selectedStock && (
        <StockSearchModal
          stock={selectedStock}
          initialTimeframe={selectedTimeframe}
          onClose={handleModalClose}
          triggerRef={triggerRef}
        />
      )}
    </div>
  )
}
