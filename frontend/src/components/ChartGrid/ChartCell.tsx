import React, { useCallback, useEffect, useRef, useState } from 'react'
import { createChart } from 'lightweight-charts'
import type { IChartApi, ISeriesApi } from 'lightweight-charts'
import { fetchChartData } from '../../api/chart'
import type { ChartResponse } from '../../types/chart'
import type { StockItem } from '../../types/stock'
import { useWatchlist } from '../../contexts/WatchlistContext'
import { usePriceRangeMeasure } from '../../hooks/usePriceRangeMeasure'
import { PriceRangeOverlay } from './PriceRangeOverlay'
import { useAnalysis } from '../../hooks/useAnalysis'
import { AnalysisModal } from '../AnalysisModal'
import { useAiReport } from '../../hooks/useAiReport'
import { AiReportModal } from '../AiReportModal'

// 시가총액(원 단위)을 간결하게 포맷
function formatMarketCap(capWon: number): string {
  const cho = capWon / 1_000_000_000_000  // 조
  if (cho >= 1) return `${cho.toFixed(1)}조`
  const eok = capWon / 100_000_000        // 억
  if (eok >= 1) return `${Math.round(eok).toLocaleString('ko-KR')}억`
  const man = capWon / 10_000             // 만
  return `${Math.round(man).toLocaleString('ko-KR')}만`
}

interface ChartCellProps {
  stock: StockItem
  isSelected: boolean
  onClick: () => void
  timeframe: 'daily' | 'weekly'
}

const MA_COLORS_DAILY: Record<string, string> = {
  ema10: '#ff6b6b',
  ema20: '#ffd166',
  sma50: '#06d6a0',
  sma100: '#118ab2',
  sma200: '#073b4c',
}

const MA_COLORS_WEEKLY: Record<string, string> = {
  sma10: '#06d6a0',
  sma20: '#118ab2',
  sma40: '#073b4c',
}

export function ChartCell({ stock, isSelected, onClick, timeframe }: ChartCellProps): React.ReactElement {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const rsLineSeriesRef = useRef<ISeriesApi<'Line'> | null>(null)
  const [chartApi, setChartApi] = useState<IChartApi | null>(null)
  const [candleSeriesApi, setCandleSeriesApi] = useState<ISeriesApi<'Candlestick'> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showRsLine, setShowRsLine] = useState(true)
  const { isChecked, toggleStock } = useWatchlist()
  const checked = isChecked(stock.code)
  const { state: analysisState, load: loadAnalysis, reset: resetAnalysis } = useAnalysis()
  const [modalOpen, setModalOpen] = useState(false)

  const handleOpenAnalysis = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    setModalOpen(true)
    loadAnalysis(stock.code)
  }, [stock.code, loadAnalysis])

  const handleCloseAnalysis = useCallback(() => {
    setModalOpen(false)
    resetAnalysis()
  }, [resetAnalysis])

  const handleRetryAnalysis = useCallback(() => {
    loadAnalysis(stock.code)
  }, [stock.code, loadAnalysis])

  // AI 리포트
  const aiReport = useAiReport()
  const [aiModalOpen, setAiModalOpen] = useState(false)

  // SPEC-AI-REPORT-002 v1.0.3: AI 버튼 클릭 시 즉시 분석 시작하지 않고
  // idle 상태로 모달만 열어 사용자가 모드(빠른/심층)를 명시적으로 선택 후 시작 버튼 누르도록 변경.
  const handleOpenAiReport = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    setAiModalOpen(true)
    aiReport.reset()  // 이전 결과 클리어 + status='idle'
  }, [aiReport])

  const handleCloseAiReport = useCallback(() => {
    setAiModalOpen(false)
    aiReport.abort()
    aiReport.reset()
  }, [aiReport])

  const handleStartAiReport = useCallback((mode: 'perplexity' | 'deep') => {
    aiReport.startStream(stock.code, mode)
  }, [stock.code, aiReport])

  const handleRetryAiReport = useCallback((mode?: 'perplexity' | 'deep') => {
    aiReport.startStream(stock.code, mode ?? 'perplexity')
  }, [stock.code, aiReport])

  const handleLoadAiHistory = useCallback(() => {
    aiReport.loadHistory(stock.code)
  }, [stock.code, aiReport])

  const handleSelectAiHistory = useCallback((filename: string) => {
    aiReport.loadSavedReport(stock.code, filename)
  }, [stock.code, aiReport])

  const { phase, result, toggleMeasure, reset: resetMeasure } = usePriceRangeMeasure(
    chartApi,
    candleSeriesApi
  )

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
    setChartApi(chart)

    const candleSeries = chart.addCandlestickSeries({
      upColor: '#ef5350',
      downColor: '#1565ef',
      borderVisible: false,
      wickUpColor: '#ef5350',
      wickDownColor: '#1565ef',
    })

    const volumeSeries = chart.addHistogramSeries({
      color: '#ef5350',
      priceFormat: {
        type: 'custom',
        formatter: (val: number) => val < 1 ? val.toFixed(1) : Math.round(val).toLocaleString('ko-KR'),
      },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    })

    const maColors = timeframe === 'daily' ? MA_COLORS_DAILY : MA_COLORS_WEEKLY
    const maSeries: Record<string, ReturnType<typeof chart.addLineSeries>> = {}
    for (const [key, color] of Object.entries(maColors)) {
      maSeries[key] = chart.addLineSeries({
        color,
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
      })
    }

    // RS Line 시리즈: 별도 가격 스케일(rs-line)에 표시
    const rsLineSeries = chart.addLineSeries({
      color: 'rgba(108, 92, 231, 0.5)',
      lineWidth: 2,
      priceScaleId: 'rs-line',
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
    })
    chart.priceScale('rs-line').applyOptions({
      scaleMargins: { top: 0.1, bottom: 0.3 },
      visible: false,
    })
    rsLineSeriesRef.current = rsLineSeries

    setCandleSeriesApi(candleSeries)

    fetchChartData(stock.code, timeframe)
      .then((data: ChartResponse) => {
        // Load all data to support user zoom/scroll to full history
        candleSeries.setData(data.candles)
        volumeSeries.setData(
          data.volume.map((v) => ({
            time: v.time,
            value: v.value,
            color: (() => {
              const candle = data.candles.find((c) => c.time === v.time)
              return candle && candle.close >= candle.open ? '#ef535055' : '#1565ef55'
            })(),
          }))
        )
        for (const [key, series] of Object.entries(maSeries)) {
          const maData = data.ma[key as keyof typeof data.ma]
          if (maData && maData.length > 0) {
            series.setData(maData.filter((p) => p.value !== null))
          }
        }

        // RS Line 데이터 설정
        if (data.rs_line && data.rs_line.length > 0) {
          rsLineSeries.setData(data.rs_line)
        }

        // Set initial visible range: 200 bars for both daily (~10 months) and weekly (~4 years)
        const visibleBars = 200
        if (data.candles.length > visibleBars) {
          const recentCandles = data.candles.slice(-visibleBars)
          const fromTime = recentCandles[0].time
          const toTime = recentCandles[recentCandles.length - 1].time
          try {
            chart.timeScale().setVisibleRange({
              from: fromTime as any,
              to: toTime as any,
            })
            chart.timeScale().applyOptions({ rightOffset: 5 })
          } catch {
            // Fallback: if setVisibleRange fails, fit all content
            chart.timeScale().fitContent()
          }
        } else {
          chart.timeScale().fitContent()
        }

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
      rsLineSeriesRef.current = null
      setChartApi(null)
      setCandleSeriesApi(null)
    }
  }, [stock.code, timeframe])

  // RS Line 표시/숨김 토글
  useEffect(() => {
    if (rsLineSeriesRef.current) {
      rsLineSeriesRef.current.applyOptions({ visible: showRsLine })
    }
  }, [showRsLine])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      resetMeasure()
    } else if (e.key === 'm' || e.key === 'M') {
      e.stopPropagation()
      toggleMeasure()
    }
  }, [resetMeasure, toggleMeasure])

  const handleCellClick = useCallback(() => {
    if (phase !== 'idle') return
    onClick()
  }, [phase, onClick])

  const changeColor = stock.change_1d === null
    ? ''
    : stock.change_1d >= 0 ? 'positive' : 'negative'

  const changeDisplay = stock.change_1d === null
    ? '-'
    : `${stock.change_1d >= 0 ? '+' : ''}${stock.change_1d.toFixed(2)}%`

  const rsValue = stock.rs_12m === null ? null : Math.round(stock.rs_12m)
  const rsDisplay = rsValue === null ? '-' : rsValue.toString()
  const rsHighlight = rsValue !== null && rsValue >= 80

  const cellClassName = [
    'chart-cell',
    isSelected ? 'chart-cell--selected' : '',
    phase !== 'idle' ? 'chart-cell--measuring' : '',
  ].filter(Boolean).join(' ')

  return (
    <div
      className={cellClassName}
      onClick={handleCellClick}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      aria-label={`Chart for ${stock.name}`}
    >
      <div className="chart-cell-header">
        <div className="chart-cell-info">
          <span className="chart-cell-name">{stock.name}</span>
          <span className="chart-cell-code">{stock.code}</span>
          {stock.sector_major && (
            <span className="chart-cell-group">
              {stock.sector_minor ? `${stock.sector_major} > ${stock.sector_minor}` : stock.sector_major}
            </span>
          )}
          <span className={`chart-cell-change ${changeColor}`}>{changeDisplay}</span>
          <span className={`chart-cell-rs${rsHighlight ? ' chart-cell-rs--high' : ''}`}>RS {rsDisplay}</span>
          {stock.stage !== null && (
            <span className={`stage-badge stage-badge--s${stock.stage}`}>S{stock.stage}</span>
          )}
          {stock.market_cap != null && stock.market_cap > 0 && (
            <span className="chart-cell-mcap">{formatMarketCap(stock.market_cap)}</span>
          )}
        </div>
        <button
          className={`chart-cell-measure-btn${phase !== 'idle' ? ' chart-cell-measure-btn--active' : ''}`}
          onClick={(e) => {
            e.stopPropagation()
            toggleMeasure()
          }}
          title="등락폭 측정 (M)"
        >
          %
        </button>
        <button
          className={`chart-cell-rs-line-btn${showRsLine ? ' chart-cell-rs-line-btn--on' : ''}`}
          onClick={(e) => {
            e.stopPropagation()
            setShowRsLine((prev) => !prev)
          }}
          title="RS Line 표시/숨김"
        >
          RS
        </button>
        <button
          className={`chart-cell-check-btn${checked ? ' chart-cell-check-btn--on' : ''}`}
          onClick={(e) => {
            e.stopPropagation()
            toggleStock(stock)
          }}
          title={checked ? '관심 해제' : '관심 등록'}
        >
          {checked ? '\u2713' : '+'}
        </button>
        <button
          className="chart-cell-fs-btn"
          onClick={handleOpenAnalysis}
          title="재무 분석"
        >
          FS
        </button>
        <button
          className="chart-cell-tr-btn"
          onClick={(e) => {
            e.stopPropagation()
            window.open(`https://kr.tradingview.com/chart/?symbol=KRX:${stock.code}`, '_blank')
          }}
          title="TradingView에서 열기"
        >
          TR
        </button>
        <button
          className={`chart-cell-ai-btn${aiReport.status === 'streaming' ? ' chart-cell-ai-btn--active' : ''}`}
          onClick={handleOpenAiReport}
          title="AI 기업 분석"
        >
          AI
        </button>
      </div>

      <div className="chart-cell-canvas-wrap">
        <div ref={containerRef} className="chart-cell-canvas" />
        {result && chartRef.current && candleSeriesApi && (
          <PriceRangeOverlay
            chart={chartRef.current}
            candleSeries={candleSeriesApi}
            result={result}
          />
        )}
      </div>

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

      {modalOpen && analysisState.status !== 'idle' && (
        <AnalysisModal
          code={stock.code}
          companyName={stock.name}
          sectorMajor={stock.sector_major}
          sectorMinor={stock.sector_minor}
          product={stock.product}
          status={analysisState.status}
          data={analysisState.status === 'success' ? analysisState.data : null}
          errorMessage={analysisState.status === 'error' ? analysisState.message : ''}
          onClose={handleCloseAnalysis}
          onRetry={handleRetryAnalysis}
        />
      )}

      {aiModalOpen && (
        <AiReportModal
          code={stock.code}
          companyName={stock.name}
          status={aiReport.status}
          markdown={aiReport.markdown}
          errorMessage={aiReport.errorMessage}
          history={aiReport.history}
          progress={aiReport.progress}
          onClose={handleCloseAiReport}
          onStart={handleStartAiReport}
          onRetry={handleRetryAiReport}
          onLoadHistory={handleLoadAiHistory}
          onSelectHistory={handleSelectAiHistory}
        />
      )}
    </div>
  )
}
