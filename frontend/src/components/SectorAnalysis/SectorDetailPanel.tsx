// @MX:NOTE: [AUTO] SectorDetailPanel shows expanded metrics for a selected sector
// @MX:SPEC: SPEC-TOPDOWN-001D R2, R3
import { useCallback } from 'react'
import type { ReactElement } from 'react'
import type { SectorRankItem } from '../../types/market'
import type { SectorDetailResponse } from '../../types/sector'
import { fetchSectorDetail } from '../../api/sectors'
import { buildQueryKey, useQuery } from '../../contexts/DataLoadContext'
// D6 / AC-SUX-052: 셀 5상태 공용 컴포넌트.
import { MetricCell, percent1, rating0, pct0, metricDisplay, type MetricValue } from '../common/MetricCell'

interface SectorDetailPanelProps {
  sector: SectorRankItem
  // TR-4 (REQ-SUX-010 / AC-SUX-012): 상세 패널에서 종목 탐색으로 진입. sectorScopeFollow 강제는 selectSector 경로에서 이미 true.
  onViewStocks?: () => void
}

interface MetricCardProps {
  label: string
  // REQ-SDU-002 (M6/D7): MetricValue 수용 — 결측은 'null%' 문자열이 아니라
  //   metricDisplay 규약의 '–' 로 렌더한다(ER-2). null% 는 컴포넌트가 아니라
  //   호출부 템플릿 보간(value={`${x}%`})에서 만들어지므로 호출부도 함께 바꿨다.
  value: MetricValue
  // REQ-SDU-001: 숫자 포맷은 MetricCell 단일 출처(rating0/pct0/percent1)만 받는다.
  format?: (n: number) => string
}

function MetricCard({ label, value, format }: MetricCardProps): ReactElement {
  const display = metricDisplay(value, format)
  return (
    <div className="sector-detail-metric">
      <div className="sector-detail-metric-label">{label}</div>
      <div className="sector-detail-metric-value">{display.text}</div>
    </div>
  )
}

function ReturnBar({ period, excessReturn }: { period: string; excessReturn: number | null }): ReactElement {
  // AC-SUX-053 (ER-2): 결측이면 바 폭 0 + 중립색 — 0% 와 같은 모습으로 렌더하지 않는다.
  const missing = excessReturn == null || Number.isNaN(excessReturn)
  const isPositive = !missing && excessReturn >= 0
  const barWidth = missing ? 0 : Math.min(Math.abs(excessReturn) * 10, 100)
  const color = missing ? 'var(--text-muted)' : isPositive ? 'var(--positive)' : 'var(--negative)'

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
        <MetricCell value={excessReturn} format={percent1} />
      </span>
    </div>
  )
}

export function SectorDetailPanel({ sector, onViewStocks }: SectorDetailPanelProps): ReactElement {
  // AC-SUX-055 (§10.2 / LD-7): 상세 조회 실패를 조용히 삼키지 않는다 — 오류 상태 + [다시 시도].
  // 공용 조회 계층을 쓰므로 2/4/8초 자동 재시도가 먼저 돌고, 소진 후 사용자에게 노출된다.
  const detailQuery = useQuery<SectorDetailResponse>(
    buildQueryKey('sector-detail', { sector: sector.name }),
    useCallback(() => fetchSectorDetail(sector.name), [sector.name]),
    // panel 미등록: 상세는 보조 패널이라 기준일 합치(SN-3) 판정 대상이 아니다.
    { panel: `섹터 상세:${sector.name}` },
  )
  const detail = detailQuery.data
  const loadingDetail = detailQuery.loading
  const detailError = detailQuery.error

  return (
    <div className="sector-detail-panel">
      <div className="sector-detail-panel-title">{sector.name}</div>

      {/* TR-4 (AC-SUX-012): [이 섹터 종목 보기 →] — 종목 탐색으로 진입 + selectedStocks 초기화(StockExplorer consumer) */}
      {onViewStocks && (
        <button
          type="button"
          className="sector-view-stocks-btn"
          onClick={onViewStocks}
          aria-label={`View ${sector.name} stocks`}
        >
          이 섹터 종목 보기 →
        </button>
      )}

      {/* Returns comparison bars */}
      <div style={{ marginBottom: 12 }}>
        <ReturnBar period="1W" excessReturn={sector.excess_returns.w1} />
        <div style={{ height: 4 }} />
        <ReturnBar period="1M" excessReturn={sector.excess_returns.m1} />
        <div style={{ height: 4 }} />
        <ReturnBar period="3M" excessReturn={sector.excess_returns.m3} />
      </div>

      {/* Metric cards grid — REQ-SDU-001/002/004 (M6): 보간 제거·rating0/pct0 전환·라벨 개명 */}
      <div className="sector-detail-metrics">
        <MetricCard label="RS Avg" value={sector.rs_avg} format={rating0} />
        <MetricCard label="RS 80+ 비중" value={sector.rs_top_pct} format={pct0} />
        <MetricCard label="52W High %" value={sector.nh_pct} format={pct0} />
        <MetricCard label="Stage 2 %" value={sector.stage2_pct} format={pct0} />
        <MetricCard label="Composite Score" value={sector.composite_score} />
        <MetricCard label="Stock Count" value={sector.stock_count} />
      </div>

      {/* Sub-sector breakdown + Top 5 stocks: 2-column layout */}
      {loadingDetail && (
        <div style={{ marginTop: 16, fontSize: 12, color: 'var(--text-muted)' }}>
          Loading sub-sector data...
        </div>
      )}

      {detail && (detail.sub_sectors.length > 0 || detail.top_stocks.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
          {/* Sub-sector breakdown */}
          {detail.sub_sectors.length > 0 && (
            <div style={{ background: 'var(--bg-surface)', borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8, borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
                Sub-sector
              </div>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                    <th style={{ textAlign: 'left', padding: '4px 0' }}>Name</th>
                    <th style={{ textAlign: 'right', padding: '4px 6px', width: 44 }}>Stocks</th>
                    <th style={{ textAlign: 'right', padding: '4px 6px', width: 44 }}>RS</th>
                    <th style={{ textAlign: 'right', padding: '4px 0', width: 44 }}>S2%</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.sub_sectors.map((sub, idx) => (
                    <tr key={sub.name} style={{ background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                      <td style={{ color: 'var(--text-primary)', padding: '5px 0', fontWeight: 500 }}>{sub.name}</td>
                      <td style={{ textAlign: 'right', color: 'var(--text-secondary)', padding: '5px 6px' }}>
                        {sub.stock_count}
                      </td>
                      <td style={{ textAlign: 'right', color: 'var(--text-secondary)', padding: '5px 6px' }}>
                        <MetricCell value={sub.rs_avg} format={rating0} />
                      </td>
                      <td style={{ textAlign: 'right', padding: '5px 0', color: sub.stage2_pct != null && sub.stage2_pct >= 50 ? 'var(--positive)' : 'var(--text-secondary)' }}>
                        <MetricCell value={sub.stage2_pct} format={pct0} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Top 5 stocks by RS */}
          {detail.top_stocks.length > 0 && (
            <div style={{ background: 'var(--bg-surface)', borderRadius: 6, padding: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8, borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
                Top 5 by RS
              </div>
              <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                    <th style={{ textAlign: 'left', padding: '4px 0' }}>Stock</th>
                    <th style={{ textAlign: 'right', padding: '4px 6px', width: 36 }}>RS</th>
                    <th style={{ textAlign: 'right', padding: '4px 6px', width: 52 }}>1M%</th>
                    <th style={{ textAlign: 'right', padding: '4px 0', width: 36 }}>Stage</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.top_stocks.map((stock, idx) => {
                    const chgColor = stock.chg_1m == null
                      ? 'var(--text-muted)'
                      : stock.chg_1m >= 0
                        ? 'var(--positive)'
                        : 'var(--negative)'

                    return (
                      <tr key={stock.code} style={{ background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                        <td style={{ padding: '5px 0' }}>
                          <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{stock.name}</span>
                          <span style={{ color: 'var(--text-muted)', marginLeft: 4, fontSize: 11 }}>{stock.code}</span>
                        </td>
                        <td style={{ textAlign: 'right', color: 'var(--text-secondary)', padding: '5px 6px', fontWeight: 600 }}>
                          <MetricCell value={stock.rs_12m} format={rating0} />
                        </td>
                        <td style={{ textAlign: 'right', color: chgColor, padding: '5px 6px', fontWeight: 500 }}>
                          <MetricCell value={stock.chg_1m} format={percent1} />
                        </td>
                        <td style={{ textAlign: 'right', padding: '5px 0' }}>
                          {stock.stage !== null ? (
                            <span className={`stage-badge stage-badge--s${stock.stage}`}>S{stock.stage}</span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)' }}>-</span>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* AC-SUX-055: 상세 조회 실패 — 오류 상태 + [다시 시도]. 거짓 안내 문구(X4)는 삭제됐다. */}
      {detailError !== null && (
        <div className="sector-detail-error" data-testid="sector-detail-error" role="alert">
          <span>세부 구성을 불러오지 못했습니다 — {detailError}</span>
          <button
            type="button"
            className="sector-detail-retry"
            data-testid="sector-detail-retry"
            onClick={detailQuery.retry}
          >
            [다시 시도]
          </button>
        </div>
      )}

      {/* 성공했지만 내용이 비어 있는 경우 — 없는 것을 있다고 말하지 않는다 */}
      {detailError === null && !loadingDetail && detail
        && detail.sub_sectors.length === 0 && detail.top_stocks.length === 0 && (
        <div className="sector-detail-empty" data-testid="sector-detail-empty">
          이 섹터에는 표시할 세부 구성이 없습니다
        </div>
      )}
    </div>
  )
}
