import type { ReactElement } from 'react'
import type { StageDistribution } from '../../types/stage'

interface StageDistributionBarProps {
  distribution: StageDistribution
  activeStage: string | null
  onStageClick: (stage: string | null) => void
  // AC-SUX-029 (REQ-SUX-027): 헤더에 섹터명·종목수 표시(선택 섹터 모집단 일치 안내).
  headerLabel?: string
}

interface StageSegmentDef {
  key: string
  // 분포 객체에서 값을 읽어올 필드명
  field: keyof StageDistribution
  label: string
  cssClass: string
  ariaLabel: string
}

// AC-SUX-030 (REQ-SUX-028): 미분류 세그먼트 추가 — 5개 세그먼트 너비 비율 합 = 100%.
const STAGE_DEFS: StageSegmentDef[] = [
  { key: 'stage1', field: 'stage1', label: 'S1', cssClass: 'stage-segment--s1', ariaLabel: 'Stage 1' },
  { key: 'stage2', field: 'stage2', label: 'S2', cssClass: 'stage-segment--s2', ariaLabel: 'Stage 2' },
  { key: 'stage3', field: 'stage3', label: 'S3', cssClass: 'stage-segment--s3', ariaLabel: 'Stage 3' },
  { key: 'stage4', field: 'stage4', label: 'S4', cssClass: 'stage-segment--s4', ariaLabel: 'Stage 4' },
  { key: 'unclassified', field: 'unclassified_count', label: '미분류', cssClass: 'stage-segment--unclassified', ariaLabel: '미분류' },
]

function readCount(distribution: StageDistribution, field: keyof StageDistribution): number {
  const v = distribution[field]
  return typeof v === 'number' ? v : 0
}

// @MX:NOTE: [AUTO] StageDistributionBar renders a proportional horizontal bar for stage distribution
// Each segment is clickable to filter stocks by stage. Clicking active segment clears filter (toggle).
// 미분류(unclassified) 세그먼트 포함 — 5세그먼트 너비 합 100% (AC-SUX-030).

export function StageDistributionBar({
  distribution,
  activeStage,
  onStageClick,
  headerLabel,
}: StageDistributionBarProps): ReactElement {
  const { total } = distribution

  // AC-SUX-030: 5개 세그먼트 너비 비율 합이 100%가 되도록 분자에 unclassified_count 포함.
  // total 이 분포 합과 다를 수 있는 구버전 응답을 방어적으로 처리: 분모는 (합계, total) 중 큰 값.
  const segmentSum = STAGE_DEFS.reduce((acc, d) => acc + readCount(distribution, d.field), 0)
  const denom = Math.max(segmentSum, total, 1)

  const handleClick = (stageKey: string) => {
    // Toggle: clicking the active stage clears the filter
    if (activeStage === stageKey) {
      onStageClick(null)
    } else {
      onStageClick(stageKey)
    }
  }

  return (
    <div>
      {headerLabel && (
        <div className="stage-distribution-header" data-testid="stage-distribution-header">
          {headerLabel}
        </div>
      )}
      <div className="stage-distribution-bar" role="group" aria-label="Stage distribution">
        {STAGE_DEFS.map(({ key, field, label, cssClass, ariaLabel }) => {
          const count = readCount(distribution, field)
          const pct = denom > 0 ? ((count / denom) * 100).toFixed(1) : '0.0'
          const widthPct = denom > 0 ? (count / denom) * 100 : 0
          const isActive = activeStage === key

          return (
            <button
              key={key}
              type="button"
              data-segment-key={key}
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
      <div className="stage-legend">
        <span className="stage-legend-item"><span className="stage-legend-dot stage-dot--s1"></span>S1 Base: SMA200 평탄, 바닥권 횡보</span>
        <span className="stage-legend-item"><span className="stage-legend-dot stage-dot--s2"></span>S2 Advance: SMA50 &gt; SMA200, 상승 추세</span>
        <span className="stage-legend-item"><span className="stage-legend-dot stage-dot--s3"></span>S3 Top: SMA200 둔화, SMA50 꺾임 (천장)</span>
        <span className="stage-legend-item"><span className="stage-legend-dot stage-dot--s4"></span>S4 Decline: SMA200 하락, 하락 추세</span>
        {/* AC-SUX-030: 미분류 범례 항목 */}
        <span className="stage-legend-item">
          <span className="stage-legend-dot stage-dot--unclassified">○</span>미분류(SMA40 부족)
        </span>
      </div>
    </div>
  )
}
