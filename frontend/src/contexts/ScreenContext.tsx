import React, { createContext, useCallback, useContext, useState } from 'react'
import { screenStocks } from '../api/screen'
import type { ScreenRequest } from '../types/filter'
import { DEFAULT_SCREEN_REQUEST } from '../types/filter'
import type { ScreenResponse } from '../types/stock'

interface ScreenContextValue {
  filters: ScreenRequest
  results: ScreenResponse | null
  loading: boolean
  error: string | null
  applyFilters: (filters: ScreenRequest) => Promise<void>
  updateFilters: (partial: Partial<ScreenRequest>) => void
}

const ScreenContext = createContext<ScreenContextValue | null>(null)

export function ScreenProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [filters, setFilters] = useState<ScreenRequest>(DEFAULT_SCREEN_REQUEST)
  const [results, setResults] = useState<ScreenResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const applyFilters = useCallback(async (newFilters: ScreenRequest) => {
    setFilters(newFilters)
    setLoading(true)
    setError(null)
    try {
      const data = await screenStocks(newFilters)
      setResults(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Screen request failed')
      setResults(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const updateFilters = useCallback((partial: Partial<ScreenRequest>) => {
    setFilters((prev) => ({ ...prev, ...partial }))
  }, [])

  return (
    <ScreenContext.Provider value={{ filters, results, loading, error, applyFilters, updateFilters }}>
      {children}
    </ScreenContext.Provider>
  )
}

export function useScreen(): ScreenContextValue {
  const ctx = useContext(ScreenContext)
  if (!ctx) throw new Error('useScreen must be used within ScreenProvider')
  return ctx
}
