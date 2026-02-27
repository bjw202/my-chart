import React, { useEffect, useState } from 'react'
import { fetchSectors } from '../../api/sectors'
import type { SectorInfo } from '../../types/stock'

interface SectorFilterProps {
  selected: string[]
  onChange: (sectors: string[]) => void
}

export function SectorFilter({ selected, onChange }: SectorFilterProps): React.ReactElement {
  const [sectors, setSectors] = useState<SectorInfo[]>([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    fetchSectors()
      .then(setSectors)
      .catch(() => setSectors([]))
  }, [])

  const toggle = (name: string): void => {
    const next = selected.includes(name)
      ? selected.filter((s) => s !== name)
      : [...selected, name]
    onChange(next)
  }

  const label = selected.length === 0
    ? '전체 섹터'
    : `${selected.length}개 섹터 선택`

  return (
    <div className="filter-group filter-group--sector">
      <label className="filter-label">섹터</label>
      <div className="sector-dropdown">
        <button
          type="button"
          className="sector-trigger"
          onClick={() => setOpen((o) => !o)}
        >
          {label} ▾
        </button>

        {open && (
          <div className="sector-panel" role="listbox" aria-multiselectable="true">
            {sectors.map((s) => (
              <label key={s.sector_name} className="sector-option">
                <input
                  type="checkbox"
                  checked={selected.includes(s.sector_name)}
                  onChange={() => toggle(s.sector_name)}
                />
                <span>{s.sector_name}</span>
                <span className="sector-count">({s.stock_count})</span>
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
