import React from 'react'
import type { IndicatorName, PatternCondition, CompareOperator } from '../../types/filter'

// Exact whitelist - must match backend IndicatorName Literal
const INDICATORS: IndicatorName[] = [
  'Close', 'Open', 'High', 'Low',
  'EMA10', 'EMA20', 'SMA50', 'SMA100', 'SMA200',
]

const OPERATORS: { value: CompareOperator; label: string }[] = [
  { value: 'gt', label: '>' },
  { value: 'gte', label: '>=' },
  { value: 'lt', label: '<' },
  { value: 'lte', label: '<=' },
]

interface PatternBuilderProps {
  patterns: PatternCondition[]
  patternLogic: 'AND' | 'OR'
  onPatternsChange: (patterns: PatternCondition[]) => void
  onLogicChange: (logic: 'AND' | 'OR') => void
}

const DEFAULT_PATTERN: PatternCondition = {
  indicator_a: 'Close',
  operator: 'gt',
  indicator_b: 'SMA50',
  multiplier: 1.0,
}

export function PatternBuilder({
  patterns,
  patternLogic,
  onPatternsChange,
  onLogicChange,
}: PatternBuilderProps): React.ReactElement {
  const addPattern = (): void => {
    if (patterns.length < 3) {
      onPatternsChange([...patterns, { ...DEFAULT_PATTERN }])
    }
  }

  const removePattern = (index: number): void => {
    onPatternsChange(patterns.filter((_, i) => i !== index))
  }

  const updatePattern = (index: number, field: keyof PatternCondition, value: string | number): void => {
    const updated = patterns.map((p, i) =>
      i === index ? { ...p, [field]: value } : p
    )
    onPatternsChange(updated)
  }

  return (
    <div className="filter-group filter-group--pattern">
      <label className="filter-label">패턴 조건</label>

      {patterns.map((p, i) => (
        <div key={i} className="pattern-row">
          {i > 0 && (
            <button
              type="button"
              className="pattern-logic-btn"
              onClick={() => onLogicChange(patternLogic === 'AND' ? 'OR' : 'AND')}
            >
              {patternLogic}
            </button>
          )}

          <select
            className="filter-select filter-select--sm"
            value={p.indicator_a}
            onChange={(e) => updatePattern(i, 'indicator_a', e.target.value as IndicatorName)}
          >
            {INDICATORS.map((ind) => (
              <option key={ind} value={ind}>{ind}</option>
            ))}
          </select>

          <select
            className="filter-select filter-select--xs"
            value={p.operator}
            onChange={(e) => updatePattern(i, 'operator', e.target.value as CompareOperator)}
          >
            {OPERATORS.map((op) => (
              <option key={op.value} value={op.value}>{op.label}</option>
            ))}
          </select>

          <select
            className="filter-select filter-select--sm"
            value={p.indicator_b}
            onChange={(e) => updatePattern(i, 'indicator_b', e.target.value as IndicatorName)}
          >
            {INDICATORS.map((ind) => (
              <option key={ind} value={ind}>{ind}</option>
            ))}
          </select>

          <span className="pattern-x">×</span>

          <input
            type="number"
            className="filter-input filter-input--xs"
            value={p.multiplier}
            min={0.01}
            max={100}
            step={0.01}
            onChange={(e) => updatePattern(i, 'multiplier', parseFloat(e.target.value) || 1.0)}
          />

          <button
            type="button"
            className="pattern-remove-btn"
            onClick={() => removePattern(i)}
            aria-label="Remove pattern"
          >
            ×
          </button>
        </div>
      ))}

      {patterns.length < 3 && (
        <button type="button" className="pattern-add-btn" onClick={addPattern}>
          + 조건 추가
        </button>
      )}
    </div>
  )
}
