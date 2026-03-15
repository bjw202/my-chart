import React from 'react'
import type { CSSProperties } from 'react'
import type { StockItem as StockItemData } from '../../types/stock'

interface StockItemProps {
  stock: StockItemData
  isSelected: boolean
  isChecked: boolean
  style: CSSProperties
  onClick: () => void
  onToggleCheck: () => void
}

// Display NULL values as "-"
function fmt(v: number | null, decimals = 2, suffix = ''): string {
  if (v === null || v === undefined) return '-'
  return `${v.toFixed(decimals)}${suffix}`
}

function fmtChange(v: number | null): { text: string; className: string } {
  if (v === null || v === undefined) return { text: '-', className: '' }
  const text = `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`
  const className = v >= 0 ? 'positive' : 'negative'
  return { text, className }
}

export function StockItemRow({ stock, isSelected, isChecked, style, onClick, onToggleCheck }: StockItemProps): React.ReactElement {
  const change = fmtChange(stock.change_1d)
  // market_cap은 원 단위로 저장됨 → 조/억 환산 표시
  const marketCapDisplay = stock.market_cap === null || stock.market_cap === 0
    ? '-'
    : (() => {
        const cho = stock.market_cap / 1_000_000_000_000
        if (cho >= 1) return `${cho.toFixed(1)}조`
        const eok = stock.market_cap / 100_000_000
        return `${Math.round(eok).toLocaleString('ko-KR')}억`
      })()

  return (
    <div
      className={`stock-item${isSelected ? ' stock-item--selected' : ''}${isChecked ? ' stock-item--checked' : ''}`}
      style={style}
      onClick={onClick}
      role="option"
      aria-selected={isSelected}
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
      <div
        className="stock-item-check"
        onClick={(e) => {
          e.stopPropagation()
          onToggleCheck()
        }}
        role="checkbox"
        aria-checked={isChecked}
      >
        <span className={`stock-item-checkbox${isChecked ? ' stock-item-checkbox--on' : ''}`} />
      </div>
      <div className="stock-item-content">
        <div className="stock-item-main">
          <span className="stock-item-name">{stock.name}</span>
          <span className="stock-item-code">{stock.code}</span>
        </div>
        <div className="stock-item-meta">
          <span className={`stock-item-change ${change.className}`}>{change.text}</span>
          <span className="stock-item-rs">RS {fmt(stock.rs_12m, 0)}</span>
          <span className="stock-item-cap">{marketCapDisplay}</span>
        </div>
      </div>
    </div>
  )
}
