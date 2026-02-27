import React, { useState } from 'react'
import type { ScreenRequest } from '../../types/filter'

type PeriodKey = 'chg_1d_min' | 'chg_1w_min' | 'chg_1m_min' | 'chg_3m_min'

interface ReturnFilterProps {
  filters: Pick<ScreenRequest, 'chg_1d_min' | 'chg_1w_min' | 'chg_1m_min' | 'chg_3m_min'>
  onChange: (key: PeriodKey, value: number | null) => void
}

const PERIODS: { key: PeriodKey; label: string }[] = [
  { key: 'chg_1d_min', label: '1D' },
  { key: 'chg_1w_min', label: '1W' },
  { key: 'chg_1m_min', label: '1M' },
  { key: 'chg_3m_min', label: '3M' },
]

export function ReturnFilter({ filters, onChange }: ReturnFilterProps): React.ReactElement {
  const [selectedPeriod, setSelectedPeriod] = useState<PeriodKey>('chg_1d_min')

  const handleValueChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const raw = e.target.value
    onChange(selectedPeriod, raw === '' ? null : Number(raw))
  }

  const currentValue = filters[selectedPeriod]

  return (
    <div className="filter-group">
      <label className="filter-label">수익률</label>
      <select
        className="filter-select filter-select--sm"
        value={selectedPeriod}
        onChange={(e) => setSelectedPeriod(e.target.value as PeriodKey)}
      >
        {PERIODS.map((p) => (
          <option key={p.key} value={p.key}>
            {p.label}
          </option>
        ))}
      </select>
      <input
        type="number"
        className="filter-input"
        placeholder="최소 %"
        value={currentValue ?? ''}
        onChange={handleValueChange}
        step="0.1"
      />
    </div>
  )
}
