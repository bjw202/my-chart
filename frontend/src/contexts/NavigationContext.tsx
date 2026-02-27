import React, { createContext, useCallback, useContext, useState } from 'react'

type GridSize = 4 | 9

interface NavigationContextValue {
  selectedIndex: number
  currentPage: number
  gridSize: GridSize
  setSelectedIndex: (index: number) => void
  setCurrentPage: (page: number) => void
  setGridSize: (size: GridSize) => void
  navigateToStock: (stockIndex: number) => void
}

const NavigationContext = createContext<NavigationContextValue | null>(null)

export function NavigationProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [currentPage, setCurrentPage] = useState(0)
  const [gridSize, setGridSize] = useState<GridSize>(4)

  const navigateToStock = useCallback(
    (stockIndex: number) => {
      setSelectedIndex(stockIndex)
      setCurrentPage(Math.floor(stockIndex / gridSize))
    },
    [gridSize]
  )

  return (
    <NavigationContext.Provider
      value={{
        selectedIndex,
        currentPage,
        gridSize,
        setSelectedIndex,
        setCurrentPage,
        setGridSize,
        navigateToStock,
      }}
    >
      {children}
    </NavigationContext.Provider>
  )
}

export function useNavigation(): NavigationContextValue {
  const ctx = useContext(NavigationContext)
  if (!ctx) throw new Error('useNavigation must be used within NavigationProvider')
  return ctx
}
