import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'
import type { StockItem } from '../types/stock'

interface WatchlistContextValue {
  checkedStocks: Map<string, StockItem>
  isChecked: (code: string) => boolean
  toggleStock: (stock: StockItem) => void
  uncheckStock: (code: string) => void
  clearAll: () => void
  checkedCount: number
  exportText: string
}

const WatchlistContext = createContext<WatchlistContextValue | null>(null)

export function WatchlistProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [checkedStocks, setCheckedStocks] = useState<Map<string, StockItem>>(() => new Map())

  const isChecked = useCallback((code: string): boolean => {
    return checkedStocks.has(code)
  }, [checkedStocks])

  const toggleStock = useCallback((stock: StockItem): void => {
    setCheckedStocks((prev) => {
      const next = new Map(prev)
      if (next.has(stock.code)) {
        next.delete(stock.code)
      } else {
        next.set(stock.code, stock)
      }
      return next
    })
  }, [])

  const uncheckStock = useCallback((code: string): void => {
    setCheckedStocks((prev) => {
      const next = new Map(prev)
      next.delete(code)
      return next
    })
  }, [])

  const clearAll = useCallback((): void => {
    setCheckedStocks(new Map())
  }, [])

  const checkedCount = checkedStocks.size

  const exportText = useMemo((): string => {
    return Array.from(checkedStocks.keys())
      .map((code) => `KRX:${code}`)
      .join(',')
  }, [checkedStocks])

  const value = useMemo((): WatchlistContextValue => ({
    checkedStocks,
    isChecked,
    toggleStock,
    uncheckStock,
    clearAll,
    checkedCount,
    exportText,
  }), [checkedStocks, isChecked, toggleStock, uncheckStock, clearAll, checkedCount, exportText])

  return (
    <WatchlistContext.Provider value={value}>
      {children}
    </WatchlistContext.Provider>
  )
}

export function useWatchlist(): WatchlistContextValue {
  const ctx = useContext(WatchlistContext)
  if (!ctx) {
    throw new Error('useWatchlist must be used within WatchlistProvider')
  }
  return ctx
}
