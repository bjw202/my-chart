import React, { useEffect, useRef, useState } from 'react'
import { createChart } from 'lightweight-charts'
import type { IChartApi } from 'lightweight-charts'
import { fetchChartData } from '../../api/chart'
import type { ChartResponse } from '../../types/chart'
import type { StockItem } from '../../types/stock'

interface ChartCellProps {
  stock: StockItem
  isSelected: boolean
  onClick: () => void
}

const MA_COLORS: Record<string, string> = {
  ema10: '#ff6b6b',
  ema20: '#ffd166',
  sma50: '#06d6a0',
  sma100: '#118ab2',
  sma200: '#073b4c',
}

export function ChartCell({ stock, isSelected, onClick }: ChartCellProps): React.ReactElement {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    setLoading(true)
    setError(null)

    const container = containerRef.current
    const chart = createChart(container, {
      layout: {
        background: { color: '#1a1a2e' },
        textColor: '#9ca3af',
      },
      localization: {
        priceFormatter: (price: number) => Math.round(price).toLocaleString('ko-KR'),
      },
      grid: {
        vertLines: { color: '#2d2d44' },
        horzLines: { color: '#2d2d44' },
      },
      timeScale: {
        borderColor: '#374151',
        timeVisible: false,
        rightOffset: 5,
      },
      rightPriceScale: {
        borderColor: '#374151',
      },
      crosshair: {
        vertLine: { color: '#6b7280' },
        horzLine: { color: '#6b7280' },
      },
      width: container.clientWidth,
      height: container.clientHeight,
    })
    chartRef.current = chart

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    })

    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    })

    const maSeries: Record<string, ReturnType<typeof chart.addLineSeries>> = {}
    for (const [key, color] of Object.entries(MA_COLORS)) {
      maSeries[key] = chart.addLineSeries({
        color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      })
    }

    fetchChartData(stock.code)
      .then((data: ChartResponse) => {
        candleSeries.setData(data.candles)
        volumeSeries.setData(
          data.volume.map((v) => ({
            time: v.time,
            value: v.value,
            color: (() => {
              const candle = data.candles.find((c) => c.time === v.time)
              return candle && candle.close >= candle.open ? '#26a69a55' : '#ef535055'
            })(),
          }))
        )
        for (const [key, series] of Object.entries(maSeries)) {
          const maData = data.ma[key as keyof typeof data.ma]
          if (maData && maData.length > 0) {
            series.setData(maData.filter((p) => p.value !== null))
          }
        }
        chart.timeScale().fitContent()
        setLoading(false)
      })
      .catch((err: Error) => {
        setError(err.message)
        setLoading(false)
      })

    const resizeObserver = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect
      chart.applyOptions({ width, height })
    })
    resizeObserver.observe(container)

    // CRITICAL: cleanup must call chart.remove() to prevent memory leaks
    return () => {
      resizeObserver.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [stock.code])

  const changeColor = stock.change_1d === null
    ? ''
    : stock.change_1d >= 0 ? 'positive' : 'negative'

  const changeDisplay = stock.change_1d === null
    ? '-'
    : `${stock.change_1d >= 0 ? '+' : ''}${stock.change_1d.toFixed(2)}%`

  return (
    <div
      className={`chart-cell${isSelected ? ' chart-cell--selected' : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      aria-label={`Chart for ${stock.name}`}
    >
      <div className="chart-cell-header">
        <span className="chart-cell-name">{stock.name}</span>
        <span className="chart-cell-code">{stock.code}</span>
        <span className={`chart-cell-change ${changeColor}`}>{changeDisplay}</span>
      </div>

      <div ref={containerRef} className="chart-cell-canvas" />

      {loading && (
        <div className="chart-cell-overlay">
          <span className="loading-spinner" />
        </div>
      )}
      {error && (
        <div className="chart-cell-overlay chart-cell-overlay--error">
          <span>{error}</span>
        </div>
      )}
    </div>
  )
}
