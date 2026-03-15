import { useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { useTab } from '../../contexts/TabContext'
import { fetchStageOverview } from '../../api/stage'
import type { StageOverviewResponse } from '../../types/stage'
import { StageDistributionBar } from './StageDistributionBar'
import { StockTable } from './StockTable'

// @MX:NOTE: [AUTO] StockExplorer is the container for SPEC-TOPDOWN-001E Stock Explorer tab
// Fetches /api/stage/overview, manages stage/sector filters, and handles cross-tab navigation

export function StockExplorer(): ReactElement {
  const { crossTabParams, clearCrossTabParams, navigateToTab } = useTab()
  const [data, setData] = useState<StageOverviewResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stageFilter, setStageFilter] = useState<number | null>(null)
  const [sectorFilter, setSectorFilter] = useState<string | null>(null)
  const [selectedStocks, setSelectedStocks] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchStageOverview()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  // Apply sector filter from cross-tab navigation (e.g. Sector Analysis tab)
  useEffect(() => {
    if (crossTabParams?.sectorName) {
      setSectorFilter(crossTabParams.sectorName)
      clearCrossTabParams()
    }
  }, [crossTabParams, clearCrossTabParams])

  const handleStockSelect = (code: string) => {
    setSelectedStocks((prev) => {
      const next = new Set(prev)
      if (next.has(code)) {
        next.delete(code)
      } else {
        next.add(code)
      }
      return next
    })
  }

  const handleViewCharts = () => {
    navigateToTab('chart-grid', { stockCodes: [...selectedStocks] })
  }

  const handleStageClick = (stage: string | null) => {
    // Map segment key (stage1/stage2/...) to stage string used in candidates
    if (stage === null) {
      setStageFilter(null)
      return
    }
    // Map distribution bar keys to API stage integer values
    const stageMap: Record<string, number> = {
      stage1: 1,
      stage2: 2,
      stage3: 3,
      stage4: 4,
    }
    setStageFilter(stageMap[stage] ?? null)
  }

  // Derive activeStage key from current stageFilter
  const activeStageKey = stageFilter !== null
    ? Object.entries({
        stage1: 1,
        stage2: 2,
        stage3: 3,
        stage4: 4,
      } as Record<string, number>).find(([, v]) => v === stageFilter)?.[0] ?? null
    : null

  if (loading) {
    return (
      <div className="stock-explorer">
        <div className="stock-explorer-loading">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="stock-explorer">
        <div className="stock-explorer-error">{error}</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="stock-explorer">
        <div className="stock-explorer-empty">No data available</div>
      </div>
    )
  }

  return (
    <div className="stock-explorer">
      {/* Toolbar */}
      <div className="stock-explorer-toolbar">
        <div className="stock-explorer-toolbar-left">
          {sectorFilter && (
            <span className="sector-filter-chip">
              {sectorFilter}
              <button
                type="button"
                onClick={() => setSectorFilter(null)}
                aria-label={`Remove sector filter ${sectorFilter}`}
              >
                ×
              </button>
            </span>
          )}
        </div>
        <div className="stock-explorer-toolbar-right">
          <span className="selected-count">
            {selectedStocks.size > 0 && `${selectedStocks.size} selected`}
          </span>
          <button
            type="button"
            className="view-charts-btn"
            disabled={selectedStocks.size === 0}
            onClick={handleViewCharts}
            aria-label="View Charts"
          >
            View Charts
          </button>
        </div>
      </div>

      {/* Stage distribution bar */}
      <StageDistributionBar
        distribution={data.distribution}
        activeStage={activeStageKey}
        onStageClick={handleStageClick}
      />

      {/* Stock table */}
      <StockTable
        candidates={data.stage2_candidates}
        stageFilter={stageFilter}
        sectorFilter={sectorFilter}
        onStockSelect={handleStockSelect}
        selectedStocks={selectedStocks}
      />
    </div>
  )
}
