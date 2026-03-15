import type { ReactElement } from 'react'

export interface MiniHeatmapSector {
  name: string
  returns: { w1: number }
  rank: number
}

export interface MiniHeatmapProps {
  sectors: MiniHeatmapSector[]
  onSectorClick: (sectorName: string) => void
}

// Map a return percentage to a heatmap background color (green = positive, red = negative)
// Clamp range is ±15 to accommodate real API data where sector returns can exceed 16%
function getHeatmapColor(returnPct: number): string {
  const clamped = Math.max(-15, Math.min(15, returnPct))
  const normalized = clamped / 15 // -1 to 1
  if (normalized >= 0) {
    const lightness = 25 - normalized * 12 // 25% to 13% (darker = stronger green)
    return `hsl(152, 60%, ${lightness}%)`
  } else {
    const lightness = 25 + normalized * 12 // 25% to 13% (darker = stronger red)
    return `hsl(4, 70%, ${lightness}%)`
  }
}

// Format return percentage with sign
function formatReturn(returnPct: number): string {
  const sign = returnPct >= 0 ? '+' : ''
  return `${sign}${returnPct.toFixed(1)}%`
}

// @MX:NOTE: [AUTO] MiniHeatmap renders CSS Grid of colored sector tiles; color driven by w1 return
export function MiniHeatmap({ sectors, onSectorClick }: MiniHeatmapProps): ReactElement {
  return (
    <div className="mini-heatmap">
      <div className="mini-heatmap-title">Sector Performance (1W)</div>
      <div className="mini-heatmap-grid">
        {sectors.map(sector => (
          <div
            key={sector.name}
            className="mini-heatmap-cell"
            style={{ backgroundColor: getHeatmapColor(sector.returns.w1) }}
            onClick={() => onSectorClick(sector.name)}
          >
            <div className="mini-heatmap-cell-name">{sector.name}</div>
            <div className="mini-heatmap-cell-return">{formatReturn(sector.returns.w1)}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
