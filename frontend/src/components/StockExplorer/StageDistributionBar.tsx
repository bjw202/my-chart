import type { ReactElement } from 'react'
import type { StageDistribution } from '../../types/stage'

interface StageDistributionBarProps {
  distribution: StageDistribution
  activeStage: string | null
  onStageClick: (stage: string | null) => void
}

interface StageSegmentDef {
  key: keyof Omit<StageDistribution, 'total'>
  label: string
  cssClass: string
  ariaLabel: string
}

const STAGE_DEFS: StageSegmentDef[] = [
  { key: 'stage1', label: 'S1', cssClass: 'stage-segment--s1', ariaLabel: 'Stage 1' },
  { key: 'stage2', label: 'S2', cssClass: 'stage-segment--s2', ariaLabel: 'Stage 2' },
  { key: 'stage3', label: 'S3', cssClass: 'stage-segment--s3', ariaLabel: 'Stage 3' },
  { key: 'stage4', label: 'S4', cssClass: 'stage-segment--s4', ariaLabel: 'Stage 4' },
]

// @MX:NOTE: [AUTO] StageDistributionBar renders a proportional horizontal bar for stage distribution
// Each segment is clickable to filter stocks by stage. Clicking active segment clears filter (toggle).

export function StageDistributionBar({
  distribution,
  activeStage,
  onStageClick,
}: StageDistributionBarProps): ReactElement {
  const { total } = distribution

  const handleClick = (stageKey: string) => {
    // Toggle: clicking the active stage clears the filter
    if (activeStage === stageKey) {
      onStageClick(null)
    } else {
      onStageClick(stageKey)
    }
  }

  return (
    <div className="stage-distribution-bar" role="group" aria-label="Stage distribution">
      {STAGE_DEFS.map(({ key, label, cssClass, ariaLabel }) => {
        const count = distribution[key]
        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0'
        const widthPct = total > 0 ? (count / total) * 100 : 0
        const isActive = activeStage === key

        return (
          <button
            key={key}
            type="button"
            className={[
              'stage-distribution-segment',
              cssClass,
              isActive ? 'active' : '',
            ]
              .filter(Boolean)
              .join(' ')}
            style={{ width: `${widthPct}%` }}
            onClick={() => handleClick(key)}
            aria-label={`${ariaLabel}: ${count} stocks (${pct}%)`}
            aria-pressed={isActive}
            title={`${ariaLabel}: ${count} (${pct}%)`}
          >
            {label} {count}
          </button>
        )
      })}
    </div>
  )
}
