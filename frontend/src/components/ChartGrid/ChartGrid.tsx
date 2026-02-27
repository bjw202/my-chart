import React, { useRef } from 'react'
import type { VariableSizeList } from 'react-window'
import { useScreen } from '../../contexts/ScreenContext'
import { useNavigation } from '../../contexts/NavigationContext'
import { useChartGrid } from '../../hooks/useChartGrid'
import { useScrollSync } from '../../hooks/useScrollSync'
import type { StockItem } from '../../types/stock'
import { ChartCell } from './ChartCell'
import { ChartPagination } from './ChartPagination'

export function ChartGrid(): React.ReactElement {
  const { results } = useScreen()
  const { selectedIndex } = useNavigation()
  const listRef = useRef<VariableSizeList | null>(null)

  // Flatten all stocks from sector groups
  const flatStocks: StockItem[] = results?.sectors.flatMap((s) => s.stocks) ?? []

  const { currentPage, gridSize, totalPages, visibleStocks, goToPage, toggleGridSize } =
    useChartGrid(flatStocks)

  const { onPageChange } = useScrollSync(listRef)

  const handlePageChange = (page: number): void => {
    goToPage(page)
    onPageChange(page)
  }

  const cols = gridSize === 4 ? 2 : 3

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
        <ChartPagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      </div>

      <div
        className="chart-grid-cells"
        style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
      >
        {visibleStocks.map((stock, slotIndex) => {
          const stockIndex = currentPage * gridSize + slotIndex
          return (
            <ChartCell
              key={`${stock.code}-${currentPage}`}
              stock={stock}
              isSelected={selectedIndex === stockIndex}
              onClick={() => {/* StockList click navigates; chart click just highlights */}}
            />
          )
        })}
      </div>
    </div>
  )
}
