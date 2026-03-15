import { useEffect, useRef } from 'react'
import type { ReactElement } from 'react'
import { createChart, LineStyle } from 'lightweight-charts'
import type { UTCTimestamp } from 'lightweight-charts'
import type { BreadthHistoryEntry } from '../../types/market'

export interface BreadthChartProps {
  history: BreadthHistoryEntry[]
}

// Convert YYYY-MM-DD date string to UTC Unix timestamp (seconds)
function dateToTimestamp(dateStr: string): UTCTimestamp {
  return Math.floor(new Date(dateStr).getTime() / 1000) as UTCTimestamp
}

// Common dark theme options shared by both charts
const CHART_LAYOUT = {
  background: { color: '#1a1a2e' },
  textColor: '#9ca3af',
}

const CHART_GRID = {
  vertLines: { color: 'transparent' },
  horzLines: { color: '#2d2d44' },
}

// @MX:NOTE: [AUTO] BreadthChart redesign: two separate chart instances (main 200px + mini 80px) + HTML legend panel.
// @MX:NOTE: [AUTO] Main chart shows pct_above_sma50 and breadth_score on a shared 0-100 scale.
// @MX:NOTE: [AUTO] Mini chart shows nh_nl_ratio independently on 0-1 scale to avoid scale mismatch.
export function BreadthChart({ history }: BreadthChartProps): ReactElement {
  const mainRef = useRef<HTMLDivElement>(null)
  const miniRef = useRef<HTMLDivElement>(null)

  // Derive latest values for the legend panel
  const latest = history.length > 0
    ? [...history].sort((a, b) => a.date.localeCompare(b.date)).at(-1)!
    : null

  useEffect(() => {
    if (!mainRef.current || !miniRef.current) return

    // --- Main chart: pct_above_sma50 + breadth_score ---
    const mainChart = createChart(mainRef.current, {
      width: mainRef.current.clientWidth,
      height: 200,
      layout: CHART_LAYOUT,
      grid: CHART_GRID,
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: true },
      timeScale: { borderColor: '#2d2d44' },
    })

    const pctSeries = mainChart.addLineSeries({
      color: '#3b82f6',
      lineWidth: 2,
      priceScaleId: 'left',
    })

    const breadthSeries = mainChart.addLineSeries({
      color: '#8b5cf6',
      lineWidth: 1,
      priceScaleId: 'left',
    })

    // Overbought / oversold reference lines
    pctSeries.createPriceLine({
      price: 60,
      color: 'rgba(38,166,154,0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'Overbought',
    })
    pctSeries.createPriceLine({
      price: 40,
      color: 'rgba(239,83,80,0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'Oversold',
    })

    // --- Mini chart: nh_nl_ratio only ---
    const miniChart = createChart(miniRef.current, {
      width: miniRef.current.clientWidth,
      height: 120,
      layout: CHART_LAYOUT,
      grid: {
        vertLines: { color: 'transparent' },
        horzLines: { color: '#2d2d44' },
      },
      rightPriceScale: { visible: false },
      leftPriceScale: { visible: true },
      timeScale: { borderColor: '#2d2d44' },
    })

    const nhNlSeries = miniChart.addLineSeries({
      color: '#f59e0b',
      lineWidth: 2,
      priceScaleId: 'left',
    })

    nhNlSeries.createPriceLine({
      price: 0.6,
      color: 'rgba(38,166,154,0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'Bullish',
    })
    nhNlSeries.createPriceLine({
      price: 0.4,
      color: 'rgba(239,83,80,0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'Bearish',
    })

    // Populate series data
    if (history.length > 0) {
      const sorted = [...history].sort((a, b) => a.date.localeCompare(b.date))

      pctSeries.setData(
        sorted.map(entry => ({ time: dateToTimestamp(entry.date), value: entry.pct_above_sma50 }))
      )
      breadthSeries.setData(
        sorted.map(entry => ({ time: dateToTimestamp(entry.date), value: entry.breadth_score }))
      )
      nhNlSeries.setData(
        sorted.map(entry => ({ time: dateToTimestamp(entry.date), value: entry.nh_nl_ratio }))
      )
    }

    // Responsive width: observe both containers
    const ro = new ResizeObserver(() => {
      if (mainRef.current) {
        mainChart.applyOptions({ width: mainRef.current.clientWidth })
      }
      if (miniRef.current) {
        miniChart.applyOptions({ width: miniRef.current.clientWidth })
      }
    })
    if (mainRef.current) ro.observe(mainRef.current)
    if (miniRef.current) ro.observe(miniRef.current)

    return () => {
      ro.disconnect()
      mainChart.remove()
      miniChart.remove()
    }
  }, [history])

  return (
    <div className="breadth-chart">
      <div className="breadth-chart-title">Market Breadth (12-week)</div>

      {/* Legend panel with current values and descriptions */}
      <div className="breadth-legend" data-testid="breadth-legend">
        <div className="breadth-legend-item">
          <span className="breadth-legend-dot" style={{ background: '#3b82f6' }} />
          <span className="breadth-legend-value">
            {latest != null ? `${latest.pct_above_sma50.toFixed(1)}%` : '--'}
          </span>
          <span className="breadth-legend-label">% &gt; SMA50</span>
          <span className="breadth-legend-desc">50일 이평선 위 종목 비율</span>
        </div>
        <div className="breadth-legend-item">
          <span className="breadth-legend-dot" style={{ background: '#8b5cf6' }} />
          <span className="breadth-legend-value">
            {latest != null ? latest.breadth_score.toFixed(1) : '--'}
          </span>
          <span className="breadth-legend-label">Breadth Score</span>
          <span className="breadth-legend-desc">시장 건전성 종합점수 (0-100)</span>
        </div>
        <div className="breadth-legend-item">
          <span className="breadth-legend-dot" style={{ background: '#f59e0b' }} />
          <span className="breadth-legend-value">
            {latest != null ? latest.nh_nl_ratio.toFixed(2) : '--'}
          </span>
          <span className="breadth-legend-label">NH-NL Ratio</span>
          <span className="breadth-legend-desc">신고가 / (신고가+신저가)</span>
        </div>
      </div>

      {/* Main chart: % > SMA50 and Breadth Score */}
      <div ref={mainRef} className="breadth-main-chart" data-testid="breadth-main-chart" />

      {/* Mini chart: NH-NL Ratio */}
      <div className="breadth-mini-label">NH-NL Ratio</div>
      <div ref={miniRef} className="breadth-mini-chart" data-testid="breadth-mini-chart" />
    </div>
  )
}
