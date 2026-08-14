import { useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { useMarket } from '../../contexts/MarketContext'
import { useNavIntent } from '../../contexts/TabContext'
import { useSelection } from '../../contexts/SelectionContext'
import { fetchStageOverview } from '../../api/stage'
import { MarketPhaseCard } from './MarketPhaseCard'
import { BreadthChart } from './BreadthChart'
import { MiniHeatmap } from './MiniHeatmap'
import { TreemapHeatmap } from './TreemapHeatmap'
import { WeeklyHighlights } from './WeeklyHighlights'

// @MX:ANCHOR: [AUTO] MarketOverview is the top-level container for the Market Overview tab
// @MX:REASON: Consumes MarketContext and TabContext; composed of 4 child components; high fan_in expected from AppContent

type HeatmapView = 'mini' | 'treemap'

export function MarketOverview(): ReactElement {
  const { overview, sectorRanking, loading, error } = useMarket()
  const { navigate } = useNavIntent()
  const { selectSector } = useSelection()

  // R7: Fetch Stage 2 count for WeeklyHighlights
  const [stage2Count, setStage2Count] = useState<number | null>(null)

  // 히트맵 뷰 전환 상태 (mini: 기존 그리드, treemap: 전체 트리맵)
  const [heatmapView, setHeatmapView] = useState<HeatmapView>('mini')

  useEffect(() => {
    fetchStageOverview()
      .then((data) => setStage2Count(data.distribution.stage2))
      .catch(() => { /* non-critical: leave as null */ })
  }, [])

  if (loading) {
    return <div className="market-overview-loading">Loading market data...</div>
  }

  if (error || !overview) {
    return <div className="market-overview-error">Failed to load market data</div>
  }

  // TR-3 / SM-4: heatmap sector click → sector selection writes to SelectionContext
  // (sectorName is NOT carried in NavIntent payload — REQ-SUX-005), then switch tab.
  const handleSectorClick = (sectorName: string): void => {
    selectSector(sectorName)
    navigate({ target: 'sector-analysis' })
  }

  // ST-7 / TR-2: treemap stock click → chart-grid focusStock consumer (REQ-SUX-012).
  // (Formerly passed a write-only `{ stockName }` → TS2353; focusStock is now a typed payload field.)
  const handleStockClick = (stockName: string): void => {
    navigate({ target: 'chart-grid', payload: { focusStock: stockName } })
  }

  return (
    <div className="market-overview">
      <MarketPhaseCard
        kospiClose={overview.kospi.close}
        kospiChg1w={overview.kospi.chg_1w}
        kosdaqClose={overview.kosdaq?.close ?? null}
        kosdaqChg1w={overview.kosdaq?.chg_1w ?? null}
        phase={overview.cycle.phase}
        choppy={overview.cycle.choppy}
        confidence={overview.cycle.confidence}
      />
      <BreadthChart history={overview.breadth_history} />
      <div className="market-overview-bottom">
        <div className="heatmap-container">
          <div className="heatmap-toggle">
            <button
              className={heatmapView === 'mini' ? 'active' : undefined}
              onClick={() => setHeatmapView('mini')}
            >
              Mini
            </button>
            <button
              className={heatmapView === 'treemap' ? 'active' : undefined}
              onClick={() => setHeatmapView('treemap')}
            >
              Treemap
            </button>
          </div>
          {heatmapView === 'mini' ? (
            <MiniHeatmap
              sectors={sectorRanking?.sectors ?? []}
              onSectorClick={handleSectorClick}
            />
          ) : (
            <TreemapHeatmap
              period="1w"
              onStockClick={handleStockClick}
            />
          )}
        </div>
        <WeeklyHighlights
          phase={overview.cycle.phase}
          choppy={overview.cycle.choppy}
          sectors={sectorRanking?.sectors ?? []}
          stage2Count={stage2Count}
          sectorAlerts={overview.sector_alerts}
        />
      </div>
    </div>
  )
}
