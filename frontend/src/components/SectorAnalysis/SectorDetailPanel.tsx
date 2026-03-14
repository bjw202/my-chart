// @MX:NOTE: [AUTO] SectorDetailPanel shows expanded metrics for a selected sector
// @MX:SPEC: SPEC-TOPDOWN-001D R2
import type { ReactElement } from 'react'
import type { SectorRankItem } from '../../types/market'

interface SectorDetailPanelProps {
  sector: SectorRankItem
}

interface MetricCardProps {
  label: string
  value: string | number
}

function MetricCard({ label, value }: MetricCardProps): ReactElement {
  return (
    <div className="sector-detail-metric">
      <div className="sector-detail-metric-label">{label}</div>
      <div className="sector-detail-metric-value">{value}</div>
    </div>
  )
}

function ReturnBar({ period, excessReturn }: { period: string; excessReturn: number }): ReactElement {
  const isPositive = excessReturn >= 0
  const barWidth = Math.min(Math.abs(excessReturn) * 10, 100)
  const color = isPositive ? 'var(--positive)' : 'var(--negative)'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ width: 24, fontSize: 11, color: 'var(--text-muted)', flexShrink: 0 }}>{period}</span>
      <div style={{ flex: 1, height: 8, background: 'var(--bg-primary)', borderRadius: 4, overflow: 'hidden' }}>
        <div
          style={{
            width: `${barWidth}%`,
            height: '100%',
            background: color,
            borderRadius: 4,
          }}
        />
      </div>
      <span style={{ width: 50, textAlign: 'right', fontSize: 11, color, flexShrink: 0 }}>
        {excessReturn >= 0 ? '+' : ''}{excessReturn.toFixed(1)}%
      </span>
    </div>
  )
}

export function SectorDetailPanel({ sector }: SectorDetailPanelProps): ReactElement {
  return (
    <div className="sector-detail-panel">
      <div className="sector-detail-panel-title">{sector.name}</div>

      {/* Returns comparison bars */}
      <div style={{ marginBottom: 12 }}>
        <ReturnBar period="1W" excessReturn={sector.excess_returns.w1} />
        <div style={{ height: 4 }} />
        <ReturnBar period="1M" excessReturn={sector.excess_returns.m1} />
        <div style={{ height: 4 }} />
        <ReturnBar period="3M" excessReturn={sector.excess_returns.m3} />
      </div>

      {/* Metric cards grid */}
      <div className="sector-detail-metrics">
        <MetricCard label="RS Avg" value={sector.rs_avg} />
        <MetricCard label="RS Top %" value={`${sector.rs_top_pct}%`} />
        <MetricCard label="52W High %" value={`${sector.nh_pct}%`} />
        <MetricCard label="Stage 2 %" value={`${sector.stage2_pct}%`} />
        <MetricCard label="Composite Score" value={sector.composite_score} />
        <MetricCard label="Stock Count" value={sector.stock_count} />
      </div>

      {/* Sub-sector placeholder */}
      <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
        Sub-sector breakdown available in future update
      </div>
    </div>
  )
}
