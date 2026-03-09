import { useCallback, useEffect, useRef, useState } from 'react'
import type { IChartApi, ISeriesApi, Time, MouseEventParams } from 'lightweight-charts'

interface MeasurePoint {
  price: number
  time: Time
  logical: number
}

export interface MeasureResult {
  startPoint: MeasurePoint
  endPoint: MeasurePoint
  priceDiff: number
  percent: number
  barCount: number
}

export type MeasurePhase = 'idle' | 'measuring' | 'locked'

interface UsePriceRangeMeasureReturn {
  phase: MeasurePhase
  result: MeasureResult | null
  toggleMeasure: () => void
  reset: () => void
}

export function usePriceRangeMeasure(
  chart: IChartApi | null,
  candleSeries: ISeriesApi<'Candlestick'> | null
): UsePriceRangeMeasureReturn {
  const [phase, setPhase] = useState<MeasurePhase>('idle')
  const [result, setResult] = useState<MeasureResult | null>(null)

  const phaseRef = useRef<MeasurePhase>('idle')
  const startPointRef = useRef<MeasurePoint | null>(null)

  phaseRef.current = phase

  const reset = useCallback(() => {
    setPhase('idle')
    setResult(null)
    startPointRef.current = null
    phaseRef.current = 'idle'
  }, [])

  const toggleMeasure = useCallback(() => {
    if (phaseRef.current === 'idle') {
      setPhase('measuring')
      setResult(null)
      startPointRef.current = null
      phaseRef.current = 'measuring'
    } else if (phaseRef.current === 'locked') {
      // 측정 완료 후 % 재클릭 → 새 측정 시작 (idle 경유 없이 바로 measuring)
      setResult(null)
      startPointRef.current = null
      phaseRef.current = 'measuring'
      setPhase('measuring')
    } else {
      // measuring 중 % → 취소 후 idle
      reset()
    }
  }, [reset])

  useEffect(() => {
    if (!chart || !candleSeries) return

    const handleClick = (param: MouseEventParams) => {
      const currentPhase = phaseRef.current
      if (currentPhase === 'idle') return
      if (!param.point || !param.time) return

      const price = candleSeries.coordinateToPrice(param.point.y)
      const logical = param.logical
      if (price === null || logical === undefined) return

      const point: MeasurePoint = { price, time: param.time, logical }

      if (currentPhase === 'locked') {
        // 측정 완료 상태에서 클릭 → 해당 위치를 시작점으로 새 측정 시작
        startPointRef.current = point
        phaseRef.current = 'measuring'
        setPhase('measuring')
        setResult(null)
        return
      }

      if (currentPhase === 'measuring' && !startPointRef.current) {
        startPointRef.current = point
      } else if (currentPhase === 'measuring' && startPointRef.current) {
        const start = startPointRef.current
        const priceDiff = point.price - start.price
        const percent = (priceDiff / start.price) * 100
        const barCount = Math.round(point.logical - start.logical)

        setResult({
          startPoint: start,
          endPoint: point,
          priceDiff,
          percent,
          barCount,
        })
        setPhase('locked')
        phaseRef.current = 'locked'
      }
    }

    const handleCrosshairMove = (param: MouseEventParams) => {
      const currentPhase = phaseRef.current
      if (currentPhase !== 'measuring' || !startPointRef.current) return
      if (!param.point) {
        setResult(null)
        return
      }

      const price = candleSeries.coordinateToPrice(param.point.y)
      const logical = param.logical
      if (price === null || logical === undefined) return

      const start = startPointRef.current
      const priceDiff = price - start.price
      const percent = (priceDiff / start.price) * 100
      const barCount = Math.round(logical - start.logical)

      setResult({
        startPoint: start,
        endPoint: { price, time: param.time ?? start.time, logical },
        priceDiff,
        percent,
        barCount,
      })
    }

    chart.subscribeClick(handleClick)
    chart.subscribeCrosshairMove(handleCrosshairMove)

    return () => {
      chart.unsubscribeClick(handleClick)
      chart.unsubscribeCrosshairMove(handleCrosshairMove)
    }
  }, [chart, candleSeries])

  return { phase, result, toggleMeasure, reset }
}
