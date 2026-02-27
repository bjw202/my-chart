import React from 'react'

interface RSFilterProps {
  value: number | null
  onChange: (value: number | null) => void
}

export function RSFilter({ value, onChange }: RSFilterProps): React.ReactElement {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    const raw = e.target.value
    onChange(raw === '' ? null : Number(raw))
  }

  return (
    <div className="filter-group">
      <label className="filter-label">RS 점수</label>
      <input
        type="number"
        className="filter-input"
        placeholder="최소 RS"
        value={value ?? ''}
        onChange={handleChange}
        min={0}
        max={100}
        step={1}
      />
    </div>
  )
}
