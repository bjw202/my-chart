import React from 'react'

// Phase display configuration mapping phase key to label and CSS modifier
const PHASE_CONFIG = {
  bull: { label: 'Bull', className: 'phase-badge--bull' },
  sideways: { label: 'Sideways', className: 'phase-badge--sideways' },
  bear: { label: 'Bear', className: 'phase-badge--bear' },
} as const

export interface MarketPhaseCardProps {
  kospiClose: number
  kospiChg1w: number
  kosdaqClose: number | null
  kosdaqChg1w: number | null
  phase: 'bull' | 'sideways' | 'bear'
  choppy: boolean
  confidence: number
}

// Format a price change value as a signed percentage string
function formatChange(chg: number): string {
  const sign = chg >= 0 ? '+' : ''
  return `${sign}${chg.toFixed(1)}%`
}

// @MX:NOTE: [AUTO] MarketPhaseCard is a pure presentational component; all data from parent
export function MarketPhaseCard({
  kospiClose,
  kospiChg1w,
  kosdaqClose,
  kosdaqChg1w,
  phase,
  choppy,
  confidence: _confidence,
}: MarketPhaseCardProps): React.ReactElement {
  const phaseConfig = PHASE_CONFIG[phase]
  const kospiChangeColor = kospiChg1w >= 0 ? 'var(--positive)' : 'var(--negative)'
  const kosdaqChangeColor =
    kosdaqChg1w !== null
      ? kosdaqChg1w >= 0
        ? 'var(--positive)'
        : 'var(--negative)'
      : undefined

  return (
    <div className="market-phase-card">
      {/* KOSPI card */}
      <div className="market-phase-card-item">
        <div className="market-phase-card-label">KOSPI</div>
        <div className="market-phase-card-price">
          {kospiClose.toLocaleString('ko-KR')}
        </div>
        <div className="market-phase-card-change" style={{ color: kospiChangeColor }}>
          {formatChange(kospiChg1w)}
        </div>
      </div>

      {/* KOSDAQ card - only renders when data is available */}
      {kosdaqClose !== null && (
        <div className="market-phase-card-item">
          <div className="market-phase-card-label">KOSDAQ</div>
          <div className="market-phase-card-price">
            {kosdaqClose.toLocaleString('ko-KR')}
          </div>
          {kosdaqChg1w !== null && (
            <div className="market-phase-card-change" style={{ color: kosdaqChangeColor }}>
              {formatChange(kosdaqChg1w)}
            </div>
          )}
        </div>
      )}

      {/* Phase badge and choppy indicator */}
      <div className="market-phase-card-item">
        <span className={`phase-badge ${phaseConfig.className}`}>
          {phaseConfig.label}
        </span>
        {choppy && (
          <span className="choppy-badge">Choppy</span>
        )}
      </div>
    </div>
  )
}
