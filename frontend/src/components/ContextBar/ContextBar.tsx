import React from 'react'
import { useMarket } from '../../contexts/MarketContext'
import type { SectorRankItem } from '../../types/market'

type MarketPhase = 'bull' | 'sideways' | 'bear'

// Map phase to display label and CSS class
const PHASE_CONFIG: Record<MarketPhase, { label: string; className: string }> = {
  bull: { label: 'Bull', className: 'context-bar-phase--bull' },
  sideways: { label: 'Sideways', className: 'context-bar-phase--sideways' },
  bear: { label: 'Bear', className: 'context-bar-phase--bear' },
}

// Get top N sectors by rank ascending (strong = low rank number = best performance)
function getStrongSectors(sectors: SectorRankItem[], count: number): SectorRankItem[] {
  return [...sectors].sort((a, b) => a.rank - b.rank).slice(0, count)
}

// Get bottom N sectors by rank descending (weak = high rank number = worst performance)
function getWeakSectors(sectors: SectorRankItem[], count: number): SectorRankItem[] {
  return [...sectors].sort((a, b) => b.rank - a.rank).slice(0, count)
}

export function ContextBar(): React.ReactElement {
  const { overview, sectorRanking, loading, error } = useMarket()

  if (loading) {
    return (
      <div className="context-bar">
        <div data-testid="context-bar-loading" className="context-bar-skeleton">
          Loading...
        </div>
      </div>
    )
  }

  if (error || !overview) {
    return (
      <div className="context-bar">
        <span className="context-bar-error">Market data unavailable</span>
      </div>
    )
  }

  const phase = overview.cycle.phase
  const phaseConfig = PHASE_CONFIG[phase]
  const sectors = sectorRanking?.sectors ?? []
  const strongSectors = getStrongSectors(sectors, 2)
  const weakSectors = getWeakSectors(sectors, 2)

  return (
    <div className="context-bar">
      {/* Market phase badge */}
      <span className={`context-bar-phase ${phaseConfig.className}`}>
        {phaseConfig.label}
      </span>
      {/* Choppy warning */}
      {overview.cycle.choppy && (
        <span className="context-bar-choppy">Choppy</span>
      )}
      {/* Strong sectors */}
      {strongSectors.length > 0 && (
        <span className="context-bar-divider">|</span>
      )}
      <span data-testid="strong-sectors" className="context-bar-strong">
        {strongSectors.map((s) => s.name).join(', ')}
      </span>
      {/* Weak sectors */}
      {weakSectors.length > 0 && (
        <>
          <span className="context-bar-divider">|</span>
          <span data-testid="weak-sectors" className="context-bar-weak">
            {weakSectors.map((s) => s.name).join(', ')}
          </span>
        </>
      )}
    </div>
  )
}
