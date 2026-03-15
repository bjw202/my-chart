// @MX:NOTE: [AUTO] SectorRankingTable renders sector ranking with sortable columns and color-coded cells
// @MX:SPEC: SPEC-TOPDOWN-001D R1
import type { ReactElement } from 'react'
import type { SectorRankItem } from '../../types/market'

interface SectorRankingTableProps {
  sectors: SectorRankItem[]
  sortField: string
  sortDirection: 'asc' | 'desc'
  onSort: (field: string) => void
  onSectorClick: (sectorName: string) => void
  selectedSector: string | null
}

// Map display column names to sort field keys
const COLUMNS: { label: string; field: string; align: 'left' | 'right' }[] = [
  { label: 'Rank', field: 'rank', align: 'right' },
  { label: 'Sector', field: 'name', align: 'left' },
  { label: '1W', field: 'excess_w1', align: 'right' },
  { label: '1M', field: 'excess_m1', align: 'right' },
  { label: '3M', field: 'excess_m3', align: 'right' },
  { label: 'RS Avg', field: 'rs_avg', align: 'right' },
  { label: 'RS Top %', field: 'rs_top_pct', align: 'right' },
  { label: '52W High %', field: 'nh_pct', align: 'right' },
  { label: 'Stage 2 %', field: 'stage2_pct', align: 'right' },
]

function getCellColor(value: number, type: 'return' | 'percentage'): string {
  if (type === 'return') {
    // Clamp to ±15 to handle large sector returns (API returns up to 16%+)
    if (value > 0) return `rgba(38, 166, 154, ${Math.min(Math.abs(value) / 15, 0.4)})`
    if (value < 0) return `rgba(239, 83, 80, ${Math.min(Math.abs(value) / 15, 0.4)})`
    return 'transparent'
  }
  // percentage: 0-100 scale
  return `rgba(59, 130, 246, ${Math.min(value / 100, 0.3)})`
}

function formatReturn(value: number): string {
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}%`
}

function RankChange({ change }: { change: number }): ReactElement {
  if (change > 0) {
    return <span className="rank-change rank-change--up">▲{change}</span>
  }
  if (change < 0) {
    return <span className="rank-change rank-change--down">▼{Math.abs(change)}</span>
  }
  return <span className="rank-change rank-change--flat">-</span>
}

export function SectorRankingTable({
  sectors,
  sortField,
  sortDirection,
  onSort,
  onSectorClick,
  selectedSector,
}: SectorRankingTableProps): ReactElement {
  return (
    <table className="sector-ranking-table">
      <thead>
        <tr>
          {COLUMNS.map(col => (
            <th
              key={col.field}
              style={{ textAlign: col.align }}
              onClick={() => onSort(col.field)}
            >
              {col.label}
              {sortField === col.field && (
                <span className="sort-arrow">{sortDirection === 'asc' ? ' ▲' : ' ▼'}</span>
              )}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {sectors.map(sector => (
          <tr
            key={sector.name}
            className={selectedSector === sector.name ? 'selected' : undefined}
            onClick={() => onSectorClick(sector.name)}
          >
            {/* Rank column with rank change indicator */}
            <td style={{ textAlign: 'right' }}>
              <span>{sector.rank}</span>
              {' '}<RankChange change={sector.rank_change} />
            </td>
            {/* Sector name */}
            <td style={{ textAlign: 'left' }}>{sector.name}</td>
            {/* 1W excess return */}
            <td
              style={{
                textAlign: 'right',
                background: getCellColor(sector.excess_returns.w1, 'return'),
              }}
            >
              {formatReturn(sector.excess_returns.w1)}
            </td>
            {/* 1M excess return */}
            <td
              style={{
                textAlign: 'right',
                background: getCellColor(sector.excess_returns.m1, 'return'),
              }}
            >
              {formatReturn(sector.excess_returns.m1)}
            </td>
            {/* 3M excess return */}
            <td
              style={{
                textAlign: 'right',
                background: getCellColor(sector.excess_returns.m3, 'return'),
              }}
            >
              {formatReturn(sector.excess_returns.m3)}
            </td>
            {/* RS Avg */}
            <td
              style={{
                textAlign: 'right',
                background: getCellColor(sector.rs_avg, 'percentage'),
              }}
            >
              {sector.rs_avg}
            </td>
            {/* RS Top % */}
            <td
              style={{
                textAlign: 'right',
                background: getCellColor(sector.rs_top_pct, 'percentage'),
              }}
            >
              {sector.rs_top_pct}%
            </td>
            {/* 52W High % */}
            <td
              style={{
                textAlign: 'right',
                background: getCellColor(sector.nh_pct, 'percentage'),
              }}
            >
              {sector.nh_pct}%
            </td>
            {/* Stage 2 % */}
            <td
              style={{
                textAlign: 'right',
                background: getCellColor(sector.stage2_pct, 'percentage'),
              }}
            >
              {sector.stage2_pct}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
