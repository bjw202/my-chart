import React, { useState } from 'react'
import { useScreen } from '../../contexts/ScreenContext'
import type { ScreenRequest } from '../../types/filter'
import { DEFAULT_SCREEN_REQUEST } from '../../types/filter'
import { DbUpdateButton } from './DbUpdateButton'
import { MarketCapFilter } from './MarketCapFilter'
import { MarketFilter } from './MarketFilter'
import { PatternBuilder } from './PatternBuilder'
import { RSFilter } from './RSFilter'
import { ReturnFilter } from './ReturnFilter'
import { SectorFilter } from './SectorFilter'

export function FilterBar(): React.ReactElement {
  const { applyFilters } = useScreen()
  const [local, setLocal] = useState<ScreenRequest>(DEFAULT_SCREEN_REQUEST)

  const update = <K extends keyof ScreenRequest>(key: K, value: ScreenRequest[K]): void => {
    setLocal((prev) => ({ ...prev, [key]: value }))
  }

  const handleApply = (e: React.SyntheticEvent): void => {
    e.preventDefault()
    void applyFilters(local)
  }

  const handleReset = (): void => {
    setLocal(DEFAULT_SCREEN_REQUEST)
  }

  return (
    <header className="filter-bar">
      <form className="filter-bar-form" onSubmit={handleApply}>
        <MarketCapFilter
          value={local.market_cap_min}
          onChange={(v) => update('market_cap_min', v)}
        />

        <ReturnFilter
          filters={local}
          onChange={(key, v) => update(key, v)}
        />

        <PatternBuilder
          patterns={local.patterns}
          patternLogic={local.pattern_logic}
          onPatternsChange={(p) => update('patterns', p)}
          onLogicChange={(l) => update('pattern_logic', l)}
        />

        <RSFilter
          value={local.rs_min}
          onChange={(v) => update('rs_min', v)}
        />

        <MarketFilter
          markets={local.markets}
          onChange={(m) => update('markets', m)}
        />

        <SectorFilter
          selected={local.sectors}
          onChange={(s) => update('sectors', s)}
        />

        <div className="filter-actions">
          <button type="submit" className="btn btn--primary">검색</button>
          <button type="button" className="btn btn--secondary" onClick={handleReset}>초기화</button>
        </div>

        <DbUpdateButton />
      </form>
    </header>
  )
}
