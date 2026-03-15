import { useEffect, useState } from 'react'
import type { ReactElement } from 'react'
import { useMarket } from '../../contexts/MarketContext'
import { useTab } from '../../contexts/TabContext'
import { fetchStageOverview } from '../../api/stage'
import { MarketPhaseCard } from './MarketPhaseCard'
import { BreadthChart } from './BreadthChart'
import { MiniHeatmap } from './MiniHeatmap'
import { WeeklyHighlights } from './WeeklyHighlights'

// @MX:ANCHOR: [AUTO] MarketOverview is the top-level container for the Market Overview tab
// @MX:REASON: Consumes MarketContext and TabContext; composed of 4 child components; high fan_in expected from AppContent

export function MarketOverview(): ReactElement {
  const { overview, sectorRanking, loading, error } = useMarket()
  const { navigateToTab } = useTab()

  // R7: Fetch Stage 2 count for WeeklyHighlights
  const [stage2Count, setStage2Count] = useState<number | null>(null)

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

  const handleSectorClick = (sectorName: string): void => {
    navigateToTab('sector-analysis', { sectorName })
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
        <MiniHeatmap
          sectors={sectorRanking?.sectors ?? []}
          onSectorClick={handleSectorClick}
        />
        <WeeklyHighlights
          phase={overview.cycle.phase}
          choppy={overview.cycle.choppy}
          sectors={sectorRanking?.sectors ?? []}
          stage2Count={stage2Count}
        />
      </div>
    </div>
  )
}
