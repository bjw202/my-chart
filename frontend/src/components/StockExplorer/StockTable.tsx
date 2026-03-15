import { useState } from 'react'
import type { ReactElement } from 'react'
import type { Stage2Candidate } from '../../types/stage'

interface StockTableProps {
  candidates: Stage2Candidate[]
  stageFilter: number | null
  sectorFilter: string | null
  onStockSelect: (code: string) => void
  selectedStocks: Set<string>
}

type SortKey = 'name' | 'market' | 'stage' | 'rs_12m' | 'chg_1m' | 'volume_ratio'
type SortDir = 'asc' | 'desc'

// R5: Key checklist — evaluate the three criteria for a stock
interface ChecklistResult {
  ma: boolean    // close > sma50 > sma200
  vol: boolean   // volume_ratio >= 1.5
  rs: boolean    // rs_12m >= 70
}

function computeChecklist(c: Stage2Candidate): ChecklistResult {
  return {
    ma: c.close > c.sma50 && c.sma50 > c.sma200,
    vol: c.volume_ratio >= 1.5,
    rs: c.rs_12m >= 70,
  }
}

// Render a single check indicator dot
function CheckDot({ pass, label, checkKey }: { pass: boolean; label: string; checkKey: string }): ReactElement {
  return (
    <span
      className={`check-dot ${pass ? 'check-pass' : 'check-fail'}`}
      data-check={checkKey}
      title={label}
    >
      {pass ? '●' : '○'}
    </span>
  )
}

// Determine badge class based on stage (integer 1-4) and RS rating
function getStageBadgeClass(candidate: Stage2Candidate): string {
  const { stage, stage_detail, rs_12m } = candidate

  if (stage === 2) {
    if (rs_12m > 60) return 'stage-badge--s2-strong'
    if (stage_detail?.toLowerCase().includes('entry')) return 'stage-badge--s2-entry'
    return 'stage-badge--s2'
  }
  if (stage === 1) return 'stage-badge--s1'
  if (stage === 3) return 'stage-badge--s3'
  if (stage === 4) return 'stage-badge--s4'
  return 'stage-badge--s1'
}

// @MX:NOTE: [AUTO] StockTable renders filtered/sorted stage candidates with multi-select support
// Filtering applies both stageFilter (exact stage match) and sectorFilter (sector_major match).

export function StockTable({
  candidates,
  stageFilter,
  sectorFilter,
  onStockSelect,
  selectedStocks,
}: StockTableProps): ReactElement {
  const [sortKey, setSortKey] = useState<SortKey>('rs_12m')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  // Apply filters — stage is integer, compare directly with numeric stageFilter
  const filtered = candidates.filter((c) => {
    if (stageFilter !== null && c.stage !== stageFilter) return false
    if (sectorFilter && c.sector_major !== sectorFilter) return false
    return true
  })

  // Apply sorting
  const sorted = [...filtered].sort((a, b) => {
    let aVal: string | number = a[sortKey] ?? ''
    let bVal: string | number = b[sortKey] ?? ''
    if (typeof aVal === 'string') aVal = aVal.toLowerCase()
    if (typeof bVal === 'string') bVal = bVal.toLowerCase()
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1
    return 0
  })

  const renderSortIndicator = (key: SortKey) => {
    if (sortKey !== key) return null
    return sortDir === 'asc' ? ' ▲' : ' ▼'
  }

  return (
    <div className="stock-table-wrapper">
      <table className="stock-table">
        <thead>
          <tr>
            <th style={{ width: 32 }}></th>
            <th onClick={() => handleSort('name')}>
              Name{renderSortIndicator('name')}
            </th>
            <th onClick={() => handleSort('market')}>
              Market{renderSortIndicator('market')}
            </th>
            <th onClick={() => handleSort('stage')}>
              Stage{renderSortIndicator('stage')}
            </th>
            <th onClick={() => handleSort('rs_12m')}>
              RS{renderSortIndicator('rs_12m')}
            </th>
            <th onClick={() => handleSort('chg_1m')}>
              1M%{renderSortIndicator('chg_1m')}
            </th>
            <th onClick={() => handleSort('volume_ratio')}>
              Vol Ratio{renderSortIndicator('volume_ratio')}
            </th>
            <th>Check</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((c) => {
            const badgeClass = getStageBadgeClass(c)
            const isEntry = c.stage_detail.toLowerCase().includes('entry')
            const rsRounded = Math.round(c.rs_12m)
            const chgColor = c.chg_1m >= 0 ? 'positive' : 'negative'
            const chgDisplay = `${c.chg_1m >= 0 ? '+' : ''}${c.chg_1m.toFixed(2)}%`
            // R4: Trend bar — width proportional to |chg_1m|, capped at 100% at 20%
            const trendBarWidth = Math.min(Math.abs(c.chg_1m) / 20 * 100, 100)
            const trendBarClass = c.chg_1m >= 0 ? 'trend-bar--positive' : 'trend-bar--negative'

            const checklist = computeChecklist(c)

            return (
              <tr key={c.code}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedStocks.has(c.code)}
                    onChange={() => onStockSelect(c.code)}
                    aria-label={`Select ${c.name}`}
                  />
                </td>
                <td>
                  <span className="stock-name">{c.name}</span>
                  <span className="stock-code"> {c.code}</span>
                </td>
                <td>{c.market}</td>
                <td>
                  <span className={`stage-badge ${badgeClass}`}>
                    S{c.stage}
                  </span>
                  {isEntry && <span className="entry-star">★</span>}
                </td>
                <td>{rsRounded}</td>
                <td className={`chg-cell ${chgColor}`}>
                  <div className="chg-cell-inner">
                    <span>{chgDisplay}</span>
                    <div
                      className={`trend-bar ${trendBarClass}`}
                      style={{ width: `${trendBarWidth}%` }}
                      aria-hidden="true"
                    />
                  </div>
                </td>
                <td>{c.volume_ratio.toFixed(2)}</td>
                <td className="checklist-cell">
                  <CheckDot pass={checklist.ma} label="MA Aligned (close > SMA50 > SMA200)" checkKey="ma" />
                  <CheckDot pass={checklist.vol} label="Vol Surge (ratio ≥ 1.5)" checkKey="vol" />
                  <CheckDot pass={checklist.rs} label="RS Strong (≥ 70)" checkKey="rs" />
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
