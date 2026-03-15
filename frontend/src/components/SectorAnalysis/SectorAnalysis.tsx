// @MX:ANCHOR: [AUTO] SectorAnalysis is the container for sector ranking tab, consumes MarketContext and TabContext
// @MX:REASON: Called from AppContent for sector-analysis tab; orchestrates SectorRankingTable + SectorDetailPanel
// @MX:SPEC: SPEC-TOPDOWN-001D
import { useState, useMemo, useEffect } from 'react'
import type { ReactElement } from 'react'
import type { SectorRankItem } from '../../types/market'
import { useMarket } from '../../contexts/MarketContext'
import { useTab } from '../../contexts/TabContext'
import { SectorRankingTable } from './SectorRankingTable'
import { SectorDetailPanel } from './SectorDetailPanel'

// Period toggle label map — module-level constant to avoid re-creation on each render
const PERIOD_LABELS: Record<'w1' | 'm1' | 'm3', string> = { w1: '1W', m1: '1M', m3: '3M' }

// Market filter options
type MarketFilter = 'all' | 'KOSPI' | 'KOSDAQ'
const MARKET_LABELS: Record<MarketFilter, string> = { all: 'All', KOSPI: 'KOSPI', KOSDAQ: 'KOSDAQ' }

// Map sort field names to sector property accessors
function getSortValue(sector: SectorRankItem, field: string): number {
  switch (field) {
    case 'rank': return sector.rank
    case 'name': return 0 // handled separately for string sort
    case 'excess_w1': return sector.excess_returns.w1
    case 'excess_m1': return sector.excess_returns.m1
    case 'excess_m3': return sector.excess_returns.m3
    case 'rs_avg': return sector.rs_avg
    case 'rs_top_pct': return sector.rs_top_pct
    case 'nh_pct': return sector.nh_pct
    case 'stage2_pct': return sector.stage2_pct
    default: return sector.composite_score
  }
}

export function SectorAnalysis(): ReactElement {
  const { sectorRanking } = useMarket()
  const { crossTabParams, clearCrossTabParams } = useTab()

  const [sortField, setSortField] = useState('rank')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')
  const [selectedSector, setSelectedSector] = useState<string | null>(null)
  const [period, setPeriod] = useState<'w1' | 'm1' | 'm3'>('m1')
  // R6: Market filter — all sectors span both markets; toggle is UI state only
  const [marketFilter, setMarketFilter] = useState<MarketFilter>('all')

  // Handle cross-tab navigation from Market Overview heatmap click
  useEffect(() => {
    if (crossTabParams?.sectorName) {
      setSelectedSector(crossTabParams.sectorName)
      clearCrossTabParams()
    }
  }, [crossTabParams, clearCrossTabParams])

  // Sort sectors based on current sort field/direction
  const sortedSectors = useMemo((): SectorRankItem[] => {
    if (!sectorRanking?.sectors) return []
    const sectors = [...sectorRanking.sectors]

    sectors.sort((a, b) => {
      // String sort for sector name
      if (sortField === 'name') {
        const cmp = a.name.localeCompare(b.name)
        return sortDirection === 'asc' ? cmp : -cmp
      }

      const aVal = getSortValue(a, sortField)
      const bVal = getSortValue(b, sortField)
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    })

    return sectors
  }, [sectorRanking, sortField, sortDirection])

  // Period toggle also re-sorts by excess return for that period
  const handlePeriodChange = (newPeriod: 'w1' | 'm1' | 'm3'): void => {
    setPeriod(newPeriod)
    setSortField(`excess_${newPeriod}`)
    setSortDirection('desc')
  }

  const handleSort = (field: string): void => {
    if (field === sortField) {
      setSortDirection(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDirection(field === 'rank' ? 'asc' : 'desc')
    }
  }

  const selectedSectorData = selectedSector
    ? sortedSectors.find(s => s.name === selectedSector)
    : null

  return (
    <div className="sector-analysis">
      <div className="sector-analysis-toolbar">
        <div className="period-toggle">
          {(['w1', 'm1', 'm3'] as const).map(p => (
            <button
              key={p}
              className={period === p ? 'active' : undefined}
              onClick={() => handlePeriodChange(p)}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>
        {/* R6: Market filter toggle */}
        <div className="market-toggle">
          {(['all', 'KOSPI', 'KOSDAQ'] as const).map(m => (
            <button
              key={m}
              className={marketFilter === m ? 'active' : undefined}
              onClick={() => setMarketFilter(m)}
            >
              {MARKET_LABELS[m]}
            </button>
          ))}
        </div>
      </div>

      <SectorRankingTable
        sectors={sortedSectors}
        sortField={sortField}
        sortDirection={sortDirection}
        onSort={handleSort}
        onSectorClick={setSelectedSector}
        selectedSector={selectedSector}
      />

      {selectedSector && selectedSectorData && (
        <SectorDetailPanel sector={selectedSectorData} />
      )}
    </div>
  )
}
