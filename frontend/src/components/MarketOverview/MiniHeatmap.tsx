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

// 한국식: 양수 = red, 음수 = blue
// Clamp range is ±15 to accommodate real API data where sector returns can exceed 16%
function getHeatmapColor(returnPct: number): string {
  const clamped = Math.max(-15, Math.min(15, returnPct))
  const normalized = clamped / 15 // -1 to 1
  if (normalized >= 0) {
    const lightness = 25 - normalized * 12 // 25% to 13% (darker = stronger red)
    return `hsl(4, 70%, ${lightness}%)`
  } else {
    const lightness = 25 + normalized * 12 // 25% to 13% (darker = stronger blue)
    return `hsl(211, 80%, ${lightness}%)`
  }
}

// Format return percentage with sign
function formatReturn(returnPct: number): string {
  const sign = returnPct >= 0 ? '+' : ''
  return `${sign}${returnPct.toFixed(1)}%`
}

// 섹터명이 유효하지 않으면 "기타" 반환
function normalizeSectorName(name: string): string {
  const trimmed = name.trim()
  if (!trimmed || trimmed === '-' || trimmed.toLowerCase() === 'nan' || trimmed === 'None') {
    return '기타'
  }
  return trimmed
}

// @MX:NOTE: [AUTO] MiniHeatmap renders CSS Grid of colored sector tiles; color driven by w1 return
export function MiniHeatmap({ sectors, onSectorClick }: MiniHeatmapProps): ReactElement {
  return (
    <div className="mini-heatmap">
      <div className="mini-heatmap-title">Sector Performance (1W)</div>
      <div className="mini-heatmap-grid">
        {sectors.map(sector => {
          const displayName = normalizeSectorName(sector.name)
          return (
            <div
              key={sector.name}
              className="mini-heatmap-cell"
              style={{ backgroundColor: getHeatmapColor(sector.returns.w1) }}
              onClick={() => onSectorClick(sector.name)}
            >
              <div className="mini-heatmap-cell-name">{displayName}</div>
              <div className="mini-heatmap-cell-return">{formatReturn(sector.returns.w1)}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
