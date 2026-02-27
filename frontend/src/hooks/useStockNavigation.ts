import { useCallback, useEffect } from 'react'
import { useNavigation } from '../contexts/NavigationContext'

export function useStockNavigation(totalStocks: number): void {
  const { selectedIndex, navigateToStock } = useNavigation()

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'ArrowDown') {
        event.preventDefault()
        const next = Math.min(selectedIndex + 1, totalStocks - 1)
        if (next !== selectedIndex) navigateToStock(next)
      } else if (event.key === 'ArrowUp') {
        event.preventDefault()
        const prev = Math.max(selectedIndex - 1, 0)
        if (prev !== selectedIndex) navigateToStock(prev)
      }
    },
    [selectedIndex, totalStocks, navigateToStock]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}
