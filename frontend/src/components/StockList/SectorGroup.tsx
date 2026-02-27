import React from 'react'
import type { CSSProperties } from 'react'

interface SectorGroupHeaderProps {
  sectorName: string
  stockCount: number
  collapsed: boolean
  style: CSSProperties
  onToggle: () => void
}

export function SectorGroupHeader({
  sectorName,
  stockCount,
  collapsed,
  style,
  onToggle,
}: SectorGroupHeaderProps): React.ReactElement {
  return (
    <div
      className="sector-header"
      style={style}
      onClick={onToggle}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onToggle()}
      aria-expanded={!collapsed}
    >
      <span className="sector-header-arrow">{collapsed ? '▶' : '▼'}</span>
      <span className="sector-header-name">{sectorName}</span>
      <span className="sector-header-count">{stockCount}</span>
    </div>
  )
}
