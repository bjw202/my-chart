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
  const { gridSize, navigateToStock, setCurrentPage, setSelectedIndex } = useNavigation()

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
      // Update selectedIndex so StockList's useEffect scrolls to the first stock of the new page
      const firstStockIndex = page * gridSize
      setSelectedIndex(firstStockIndex)
      requestAnimationFrame(() => {
        isInternalUpdate.current = false
      })
    },
    [setCurrentPage, setSelectedIndex, gridSize]
  )

  return { onStockSelect, onPageChange }
}
