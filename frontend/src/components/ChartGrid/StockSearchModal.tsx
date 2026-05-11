/**
 * StockSearchModal — 개별 종목 차트 모달 (portal 마운트)
 *
 * REQ-MODAL-001: ReactDOM.createPortal(modal, document.body)
 * REQ-MODAL-002: close 시 selectedStock=null + focus 복귀 + input clear
 * REQ-MODAL-003: WCAG 2.1 AA modal patterns
 * REQ-MODAL-004: timeframe 토글 (daily/weekly)
 * REQ-PERF-002: cancelled flag race guard
 *
 * @MX:NOTE: [AUTO] portal mount on document.body — ChartGrid subtree 외부 (MP-4).
 *   scroll lock(body overflow:hidden) on mount + 해제 on unmount.
 *   initialTimeframe prop으로 ChartGrid 마지막 timeframe snapshot 계승 (Q-7, AC-MODAL-009).
 */

import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react'
import ReactDOM from 'react-dom'
import { createChart } from 'lightweight-charts'
import type { IChartApi, ISeriesApi } from 'lightweight-charts'
import { fetchChartData } from '../../api/chart'
import { useFocusTrap } from './useFocusTrap'
import type { StockMasterItem } from '../../api/stocks'

export interface StockSearchModalProps {
  stock: StockMasterItem
  initialTimeframe?: 'daily' | 'weekly'
  onClose: () => void
  /** modal close 시 focus를 복귀할 target — HTMLElement 또는 focus() 메서드를 가진 handle */
  triggerRef: React.RefObject<{ focus(): void } | null>
}

/**
 * StockSearchModal은 useScreen/useTab을 구독하지 않는다 (AC-ARCH-003).
 * ChartGrid context와 격리되어 MP-1/MP-2/MP-3 invariant를 보존한다.
 */
export function StockSearchModal({
  stock,
  initialTimeframe,
  onClose,
  triggerRef,
}: StockSearchModalProps): React.ReactPortal {
  const [timeframe, setTimeframe] = useState<'daily' | 'weekly'>(
    initialTimeframe ?? 'daily',
  )
  const [chartLoading, setChartLoading] = useState(true)
  const [chartError, setChartError] = useState(false)

  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const contentRef = useRef<HTMLDivElement>(null)

  useFocusTrap(contentRef)

  // Scroll lock (REQ-MODAL-003)
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  // Initial focus on modal-content
  useEffect(() => {
    contentRef.current?.focus()
  }, [])

  // Esc key handler (AnalysisModal.tsx:737 패턴 답습)
  useEffect(() => {
    const handler = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  // Focus restore on unmount
  useEffect(() => {
    return () => {
      // triggerRef.current가 HTMLInputElement인 경우에만 focus 복귀
      triggerRef.current?.focus()
    }
  }, [triggerRef])

  // Chart instance lifecycle
  useEffect(() => {
    const container = chartContainerRef.current
    if (!container) return

    const chart = createChart(container, {
      width: container.clientWidth || 600,
      height: 300,
      layout: {
        background: { color: '#1a1a2e' },
        textColor: '#c9d1d9',
      },
    })
    const series = chart.addCandlestickSeries()
    chartRef.current = chart
    seriesRef.current = series

    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  // @MX:WARN: [AUTO] cancelled flag race guard — fetch in-flight 중 close 시 destroyed chart setData 차단
  // @MX:REASON: archive df3ca36 ChartCell race guard 패턴 적용. modal close → cleanup → cancelled=true → setData 0회
  useEffect(() => {
    let cancelled = false
    setChartLoading(true)
    setChartError(false)

    fetchChartData(stock.code, timeframe)
      .then((data) => {
        if (cancelled) return
        seriesRef.current?.setData(
          (data.candles ?? []).map((c) => ({
            time: c.time as Parameters<typeof seriesRef.current.setData>[0][number]['time'],
            open: c.open,
            high: c.high,
            low: c.low,
            close: c.close,
          })),
        )
        chartRef.current?.timeScale().fitContent()
        setChartLoading(false)
      })
      .catch(() => {
        if (cancelled) return
        setChartLoading(false)
        setChartError(true)
      })

    return () => {
      cancelled = true
    }
  }, [stock.code, timeframe])

  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) onClose()
    },
    [onClose],
  )

  const handleContentClick = (e: React.MouseEvent<HTMLDivElement>): void => {
    e.stopPropagation()
  }

  const toggleTimeframe = (): void => {
    setTimeframe((prev) => (prev === 'daily' ? 'weekly' : 'daily'))
  }

  const modal = (
    <div
      data-testid="stock-search-modal-backdrop"
      onClick={handleBackdropClick}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 2000,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        data-testid="stock-search-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="stock-search-modal-title"
        style={{
          background: 'var(--bg-surface, #16213e)',
          borderRadius: 8,
          padding: '16px 20px',
          width: 660,
          maxWidth: '95vw',
          maxHeight: '80vh',
          overflow: 'auto',
        }}
      >
        <div
          ref={contentRef}
          data-testid="stock-search-modal-content"
          tabIndex={-1}
          onClick={handleContentClick}
          style={{ outline: 'none' }}
        >
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div>
              <span
                id="stock-search-modal-title"
                style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}
              >
                {stock.name}
              </span>
              <span style={{ marginLeft: 8, fontSize: 12, color: 'var(--text-muted)' }}>
                {stock.code} · {stock.market}
              </span>
            </div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              {/* Timeframe toggle (I-3: 'daily'/'weekly') */}
              <button
                type="button"
                data-testid="stock-search-modal-timeframe-toggle"
                onClick={toggleTimeframe}
                aria-label={`Switch to ${timeframe === 'daily' ? 'weekly' : 'daily'} chart`}
                style={{
                  padding: '3px 10px',
                  fontSize: 12,
                  background: 'var(--bg-btn, #0d2137)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border)',
                  borderRadius: 4,
                  cursor: 'pointer',
                }}
              >
                {timeframe === 'daily' ? '주봉' : '일봉'}
              </button>
              {/* Close button */}
              <button
                type="button"
                data-testid="stock-search-modal-close-btn"
                onClick={onClose}
                aria-label="닫기"
                style={{
                  padding: '3px 8px',
                  fontSize: 14,
                  background: 'none',
                  color: 'var(--text-muted)',
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Loading state (F-3 spec §4 row 11) */}
          {chartLoading && (
            <div
              data-testid="stock-search-modal-loading"
              aria-busy="true"
              style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)', fontSize: 13 }}
            >
              차트 로딩 중...
            </div>
          )}

          {/* Error state (F-3 spec §4 row 12) */}
          {chartError && (
            <div
              data-testid="stock-search-modal-error"
              role="alert"
              style={{ textAlign: 'center', padding: '16px', color: '#e74c3c', fontSize: 13 }}
            >
              차트 불러오기 실패
            </div>
          )}

          {/* Chart container */}
          <div
            ref={chartContainerRef}
            style={{ width: '100%', height: 300, display: chartLoading || chartError ? 'none' : 'block' }}
            aria-label={`${stock.name} 차트`}
          />
        </div>
      </div>
    </div>
  )

  return ReactDOM.createPortal(modal, document.body)
}
