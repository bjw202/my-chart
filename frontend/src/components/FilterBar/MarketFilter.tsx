import React from 'react'
import type { MarketName } from '../../types/filter'

interface MarketFilterProps {
  markets: MarketName[]
  onChange: (markets: MarketName[]) => void
}

const ALL_MARKETS: MarketName[] = ['KOSPI', 'KOSDAQ']

export function MarketFilter({ markets, onChange }: MarketFilterProps): React.ReactElement {
  const toggle = (market: MarketName): void => {
    const next = markets.includes(market)
      ? markets.filter((m) => m !== market)
      : [...markets, market]
    onChange(next)
  }

  return (
    <div className="filter-group">
      <label className="filter-label">시장</label>
      {ALL_MARKETS.map((market) => (
        <label key={market} className="filter-checkbox">
          <input
            type="checkbox"
            checked={markets.includes(market)}
            onChange={() => toggle(market)}
          />
          <span>{market}</span>
        </label>
      ))}
    </div>
  )
}
