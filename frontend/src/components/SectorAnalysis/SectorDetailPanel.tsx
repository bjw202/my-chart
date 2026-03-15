// @MX:NOTE: [AUTO] SectorDetailPanel shows expanded metrics for a selected sector
// @MX:SPEC: SPEC-TOPDOWN-001D R2, R3
import { useState, useEffect } from 'react'
import type { ReactElement } from 'react'
import type { SectorRankItem } from '../../types/market'
import type { SectorDetailResponse } from '../../types/sector'
import { fetchSectorDetail } from '../../api/sectors'

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
  const [detail, setDetail] = useState<SectorDetailResponse | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Fetch sub-sector detail when sector changes
  useEffect(() => {
    setDetail(null)
    setLoadingDetail(true)
    fetchSectorDetail(sector.name)
      .then((data) => {
        setDetail(data)
      })
      .catch(() => {
        // Detail is optional; silently ignore errors
      })
      .finally(() => {
        setLoadingDetail(false)
      })
  }, [sector.name])

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

      {/* Sub-sector breakdown */}
      {loadingDetail && (
        <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text-muted)' }}>
          Loading sub-sector data...
        </div>
      )}

      {detail && detail.sub_sectors.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
            Sub-sector breakdown
          </div>
          <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ color: 'var(--text-muted)' }}>
                <th style={{ textAlign: 'left', paddingBottom: 4 }}>Sub-sector</th>
                <th style={{ textAlign: 'right', paddingBottom: 4 }}>Stocks</th>
              </tr>
            </thead>
            <tbody>
              {detail.sub_sectors.map((sub) => (
                <tr key={sub.name}>
                  <td style={{ color: 'var(--text-primary)', paddingBottom: 2 }}>{sub.name}</td>
                  <td style={{ textAlign: 'right', color: 'var(--text-secondary)', paddingBottom: 2 }}>
                    {sub.stock_count}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Top 5 stocks by RS */}
      {detail && detail.top_stocks.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
            Top 5 by RS
          </div>
          <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ color: 'var(--text-muted)' }}>
                <th style={{ textAlign: 'left', paddingBottom: 4 }}>Stock</th>
                <th style={{ textAlign: 'right', paddingBottom: 4 }}>RS</th>
                <th style={{ textAlign: 'right', paddingBottom: 4 }}>Stage</th>
              </tr>
            </thead>
            <tbody>
              {detail.top_stocks.map((stock) => (
                <tr key={stock.code}>
                  <td style={{ color: 'var(--text-primary)', paddingBottom: 2 }}>
                    {stock.name}
                    <span style={{ color: 'var(--text-muted)', marginLeft: 4 }}>{stock.code}</span>
                  </td>
                  <td style={{ textAlign: 'right', color: 'var(--text-secondary)', paddingBottom: 2 }}>
                    {Math.round(stock.rs_12m)}
                  </td>
                  <td style={{ textAlign: 'right', paddingBottom: 2 }}>
                    {stock.stage !== null ? (
                      <span className={`stage-badge stage-badge--s${stock.stage}`}>S{stock.stage}</span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)' }}>-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Fallback for when detail is not loaded yet */}
      {!loadingDetail && !detail && (
        <div style={{ marginTop: 12, fontSize: 11, color: 'var(--text-muted)', fontStyle: 'italic' }}>
          Sub-sector breakdown available in future update
        </div>
      )}
    </div>
  )
}
