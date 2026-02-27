import { useCallback } from 'react'
import { useNavigation } from '../contexts/NavigationContext'
import type { StockItem } from '../types/stock'

export interface ChartGridState {
  currentPage: number
  gridSize: 4 | 9
  totalPages: number
  visibleStocks: StockItem[]
  goToPage: (page: number) => void
  toggleGridSize: () => void
}

export function useChartGrid(flatStocks: StockItem[]): ChartGridState {
  const { currentPage, setCurrentPage, gridSize, setGridSize } = useNavigation()

  const totalPages = Math.max(1, Math.ceil(flatStocks.length / gridSize))
  const safeCurrentPage = Math.min(currentPage, totalPages - 1)

  const start = safeCurrentPage * gridSize
  const visibleStocks = flatStocks.slice(start, start + gridSize)

  const goToPage = useCallback(
    (page: number) => {
      const bounded = Math.max(0, Math.min(page, totalPages - 1))
      setCurrentPage(bounded)
    },
    [setCurrentPage, totalPages]
  )

  const toggleGridSize = useCallback(() => {
    setGridSize(gridSize === 4 ? 9 : 4)
    setCurrentPage(0)
  }, [gridSize, setGridSize, setCurrentPage])

  return {
    currentPage: safeCurrentPage,
    gridSize,
    totalPages,
    visibleStocks,
    goToPage,
    toggleGridSize,
  }
}
