import React from 'react'

interface MarketCapFilterProps {
  value: number | null
  onChange: (value: number | null) => void
}

const PRESETS: { label: string; value: number | null }[] = [
  { label: '전체', value: null },
  { label: '1000억+', value: 1000 },
  { label: '5000억+', value: 5000 },
  { label: '1조+', value: 10000 },
]

export function MarketCapFilter({ value, onChange }: MarketCapFilterProps): React.ReactElement {
  const handleSelect = (e: React.ChangeEvent<HTMLSelectElement>): void => {
    const raw = e.target.value
    onChange(raw === '' ? null : Number(raw))
  }

  return (
    <div className="filter-group">
      <label className="filter-label">시가총액</label>
      <select
        className="filter-select"
        value={value ?? ''}
        onChange={handleSelect}
      >
        {PRESETS.map((p) => (
          <option key={p.label} value={p.value ?? ''}>
            {p.label}
          </option>
        ))}
      </select>
    </div>
  )
}
