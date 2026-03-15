import React, { useCallback, useEffect, useRef, useState } from 'react'
import type { VariableSizeList } from 'react-window'
import { useScreen } from '../../contexts/ScreenContext'
import { useTab } from '../../contexts/TabContext'
import { useNavigation } from '../../contexts/NavigationContext'
import { useChartGrid } from '../../hooks/useChartGrid'
import { useScrollSync } from '../../hooks/useScrollSync'
import type { StockItem } from '../../types/stock'
import { fetchStageOverview } from '../../api/stage'
import { DEFAULT_SCREEN_REQUEST } from '../../types/filter'
import { ChartCell } from './ChartCell'
import { ChartPagination } from './ChartPagination'

export function ChartGrid(): React.ReactElement {
  const { results, applyFilters } = useScreen()
  const { crossTabParams, clearCrossTabParams } = useTab()
  const { selectedIndex } = useNavigation()
  const listRef = useRef<VariableSizeList | null>(null)
  const [timeframe, setTimeframe] = useState<'daily' | 'weekly'>('daily')
  const [stageMap, setStageMap] = useState<Map<string, number>>(new Map())

  // Fetch stage overview once and build code->stage lookup map
  useEffect(() => {
    fetchStageOverview()
      .then((data) => {
        const map = new Map<string, number>()
        for (const stock of data.all_stocks) {
          map.set(stock.code, stock.stage)
        }
        setStageMap(map)
      })
      .catch(() => {
        // Stage data is optional; chart grid works without it
      })
  }, [])

  // crossTabParams.stockCodes 수신 시 해당 종목만 필터링하여 조회
  useEffect(() => {
    if (crossTabParams?.stockCodes && crossTabParams.stockCodes.length > 0) {
      applyFilters({ ...DEFAULT_SCREEN_REQUEST, codes: crossTabParams.stockCodes })
      clearCrossTabParams()
    }
  }, [crossTabParams, applyFilters, clearCrossTabParams])

  // Flatten all stocks from sector groups and merge stage data
  const flatStocks: StockItem[] = (results?.sectors.flatMap((s) => s.stocks) ?? []).map((stock) => ({
    ...stock,
    stage: stageMap.get(stock.code) ?? null,
  }))

  const { currentPage, gridSize, totalPages, visibleStocks, goToPage, toggleGridSize } =
    useChartGrid(flatStocks)

  const { onPageChange } = useScrollSync(listRef)

  const handlePageChange = useCallback((page: number): void => {
    goToPage(page)
    onPageChange(page)
  }, [goToPage, onPageChange])

  const toggleTimeframe = (): void => {
    setTimeframe((prev) => (prev === 'daily' ? 'weekly' : 'daily'))
  }

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent): void => {
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        if (currentPage > 0) handlePageChange(currentPage - 1)
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        if (currentPage < totalPages - 1) handlePageChange(currentPage + 1)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [currentPage, totalPages, handlePageChange])

  const cols = gridSize === 4 ? 2 : 3
  const rows = gridSize === 4 ? 2 : 3

  if (flatStocks.length === 0) {
    return (
      <div className="chart-grid chart-grid--empty">
        <p className="empty-message">필터를 적용하여 종목을 검색하세요.</p>
      </div>
    )
  }

  return (
    <div className="chart-grid">
      <div className="chart-grid-toolbar">
        <button
          type="button"
          className="grid-toggle-btn"
          onClick={toggleGridSize}
          aria-label={`Switch to ${gridSize === 4 ? '3×3' : '2×2'} grid`}
        >
          {gridSize === 4 ? '3×3' : '2×2'}
        </button>
        <button
          type="button"
          className="timeframe-toggle-btn"
          onClick={toggleTimeframe}
          aria-label={`Switch to ${timeframe === 'daily' ? 'weekly' : 'daily'} charts`}
        >
          {timeframe === 'daily' ? 'W' : 'D'}
        </button>
        <ChartPagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      </div>

      <div
        className="chart-grid-cells"
        style={{
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gridTemplateRows: `repeat(${rows}, 1fr)`,
        }}
      >
        {visibleStocks.map((stock, slotIndex) => {
          const stockIndex = currentPage * gridSize + slotIndex
          return (
            <ChartCell
              key={`${stock.code}-${currentPage}`}
              stock={stock}
              isSelected={selectedIndex === stockIndex}
              onClick={() => {/* StockList click navigates; chart click just highlights */}}
              timeframe={timeframe}
            />
          )
        })}
      </div>
    </div>
  )
}
