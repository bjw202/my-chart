import React from 'react'
import type { IChartApi, ISeriesApi } from 'lightweight-charts'
import type { MeasureResult } from '../../hooks/usePriceRangeMeasure'

interface PriceRangeOverlayProps {
  chart: IChartApi
  candleSeries: ISeriesApi<'Candlestick'>
  result: MeasureResult
}

export function PriceRangeOverlay({ chart, candleSeries, result }: PriceRangeOverlayProps): React.ReactElement | null {
  const { startPoint, endPoint, priceDiff, percent } = result

  const startY = candleSeries.priceToCoordinate(startPoint.price)
  const endY = candleSeries.priceToCoordinate(endPoint.price)
  const startX = chart.timeScale().timeToCoordinate(startPoint.time)
  const endX = chart.timeScale().timeToCoordinate(endPoint.time)

  if (startY === null || endY === null || startX === null || endX === null) return null

  const isPositive = priceDiff >= 0
  const colorClass = isPositive ? 'price-range--positive' : 'price-range--negative'

  const top = Math.min(startY, endY)
  const height = Math.abs(endY - startY)
  const left = Math.min(startX, endX)
  const width = Math.abs(endX - startX)

  const formattedPercent = `${isPositive ? '+' : '-'}${Math.abs(percent).toFixed(2)}%`
  const label = formattedPercent

  const labelTop = endY < startY ? top - 22 : top + height + 4
  const labelLeft = Math.max(left, 4)

  return (
    <div className="price-range-overlay">
      <div
        className={`price-range-marker ${colorClass}`}
        style={{ top: startY, left: startX - 20, width: 40 }}
      />
      <div
        className={`price-range-marker ${colorClass}`}
        style={{ top: endY, left: endX - 20, width: 40 }}
      />
      <div
        className={`price-range-area ${colorClass}`}
        style={{ top, left, width: Math.max(width, 1), height: Math.max(height, 1) }}
      />
      <div
        className={`price-range-line ${colorClass}`}
        style={{
          top,
          left: endX,
          height: Math.max(height, 1),
        }}
      />
      <div
        className={`price-range-label ${colorClass}`}
        style={{ top: labelTop, left: labelLeft }}
      >
        {label}
      </div>
    </div>
  )
}
