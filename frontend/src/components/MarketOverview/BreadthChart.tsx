import React, { useEffect, useRef } from 'react'
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

// @MX:NOTE: [AUTO] BreadthChart renders 3 series via Lightweight Charts; uses ResizeObserver for responsive width
export function BreadthChart({ history }: BreadthChartProps): React.ReactElement {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 280,
      layout: {
        background: { color: '#1a1a2e' },
        textColor: '#9ca3af',
      },
      grid: {
        vertLines: { color: '#2d2d44' },
        horzLines: { color: '#2d2d44' },
      },
      rightPriceScale: { visible: true },
      leftPriceScale: { visible: true },
    })

    // Series 1: % above SMA50 (left axis, blue)
    const pctSeries = chart.addLineSeries({
      color: '#3b82f6',
      lineWidth: 2,
      title: '% > SMA50',
      priceScaleId: 'left',
    })

    // Series 2: Breadth score (left axis, purple)
    const breadthSeries = chart.addLineSeries({
      color: '#8b5cf6',
      lineWidth: 1,
      title: 'Breadth Score',
      priceScaleId: 'left',
    })

    // Series 3: NH-NL ratio (right axis, amber)
    const nhNlSeries = chart.addLineSeries({
      color: '#f59e0b',
      lineWidth: 1,
      title: 'NH-NL Ratio',
      priceScaleId: 'nh-nl',
    })

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

    // Reference lines on pct_above_sma50: 60% (overbought) and 40% (oversold)
    pctSeries.createPriceLine({
      price: 60,
      color: 'rgba(38,166,154,0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: '60%',
    })
    pctSeries.createPriceLine({
      price: 40,
      color: 'rgba(239,83,80,0.5)',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: '40%',
    })

    // Responsive width via ResizeObserver
    const ro = new ResizeObserver(entries => {
      const { width } = entries[0].contentRect
      chart.applyOptions({ width })
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      chart.remove()
    }
  }, [history])

  return (
    <div className="breadth-chart">
      <div className="breadth-chart-title">Market Breadth (12-week)</div>
      <div ref={containerRef} className="breadth-chart-container" />
    </div>
  )
}
