import type { ReactElement } from 'react'

// Phase display configuration for badges
const PHASE_CONFIG = {
  bull: { label: 'Bull', className: 'phase-badge--bull' },
  sideways: { label: 'Sideways', className: 'phase-badge--sideways' },
  bear: { label: 'Bear', className: 'phase-badge--bear' },
} as const

export interface WeeklyHighlightsProps {
  phase: 'bull' | 'sideways' | 'bear'
  choppy: boolean
  sectors: Array<{ name: string; rank_change: number }>
  // R7: Stage 2 stock count; null means not yet loaded
  stage2Count?: number | null
}

// Format a rank change number as a signed string
function formatRankChange(change: number): string {
  const sign = change >= 0 ? '+' : ''
  return `${sign}${change}`
}

// @MX:NOTE: [AUTO] WeeklyHighlights shows phase summary + top-3 rank movers + Stage 2 count
// @MX:SPEC: SPEC-TOPDOWN-001 R7
export function WeeklyHighlights({ phase, choppy, sectors, stage2Count }: WeeklyHighlightsProps): ReactElement {
  const phaseConfig = PHASE_CONFIG[phase]

  // Top 3 sectors by absolute rank change
  const topMovers = [...sectors]
    .sort((a, b) => Math.abs(b.rank_change) - Math.abs(a.rank_change))
    .slice(0, 3)

  return (
    <div className="weekly-highlights">
      <div className="weekly-highlights-title">Weekly Highlights</div>

      {/* Market phase section */}
      <div className="weekly-highlights-section">
        <h4>Market Phase</h4>
        <span className={`phase-badge ${phaseConfig.className}`}>
          {phaseConfig.label}
        </span>
        {choppy && (
          <span className="choppy-badge" style={{ marginLeft: '8px' }}>Choppy</span>
        )}
      </div>

      {/* Biggest rank changes */}
      <div className="weekly-highlights-section">
        <h4>Biggest Rank Change</h4>
        {topMovers.length === 0 ? (
          <div className="rank-change-item">No data</div>
        ) : (
          topMovers.map(sector => {
            const isPositive = sector.rank_change >= 0
            const arrow = isPositive ? '↑' : '↓'
            const color = isPositive ? 'var(--positive)' : 'var(--negative)'
            return (
              <div
                key={sector.name}
                className="rank-change-item"
                style={{ color }}
              >
                {`${arrow} ${sector.name} ${formatRankChange(sector.rank_change)}`}
              </div>
            )
          })
        )}
      </div>

      {/* Stage 2 stock count */}
      <div className="weekly-highlights-section">
        <h4>Stage 2</h4>
        {stage2Count !== null && stage2Count !== undefined ? (
          <div className="stage2-count">
            <span className="stage2-count-number">{stage2Count}</span>
            <span className="stage2-count-label"> stocks</span>
          </div>
        ) : (
          <div className="rank-change-item" style={{ color: 'var(--text-muted)' }}>
            —
          </div>
        )}
      </div>
    </div>
  )
}
