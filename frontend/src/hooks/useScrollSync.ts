import { useCallback, useRef } from 'react'
import type { VariableSizeList } from 'react-window'
import { useNavigation } from '../contexts/NavigationContext'

// Bidirectional scroll sync between ChartGrid pagination and StockList.
// Uses isInternalUpdate ref to prevent circular update loops.
export function useScrollSync(listRef: React.RefObject<VariableSizeList | null>): {
  onStockSelect: (stockIndex: number) => void
  onPageChange: (page: number) => void
} {
  const isInternalUpdate = useRef(false)
  const { gridSize, navigateToStock, setCurrentPage } = useNavigation()

  const onStockSelect = useCallback(
    (stockIndex: number) => {
      if (isInternalUpdate.current) return
      isInternalUpdate.current = true
      navigateToStock(stockIndex)
      // Scroll the virtualized list to the selected item
      listRef.current?.scrollToItem(stockIndex, 'smart')
      requestAnimationFrame(() => {
        isInternalUpdate.current = false
      })
    },
    [navigateToStock, listRef]
  )

  const onPageChange = useCallback(
    (page: number) => {
      if (isInternalUpdate.current) return
      isInternalUpdate.current = true
      setCurrentPage(page)
      // Scroll StockList to the first stock of the new page
      const firstStockIndex = page * gridSize
      listRef.current?.scrollToItem(firstStockIndex, 'start')
      requestAnimationFrame(() => {
        isInternalUpdate.current = false
      })
    },
    [setCurrentPage, gridSize, listRef]
  )

  return { onStockSelect, onPageChange }
}
