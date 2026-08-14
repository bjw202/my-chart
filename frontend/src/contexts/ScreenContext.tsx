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
  clearResults: () => void
  // 현재 화면이 실제로 보여주는 모집단 수. 화면이 자체 필터를 갖는 경우(종목 탐색)
  // 그 화면이 게시하고, 게시자가 없으면 null → 푸터는 스크리닝 전체 수로 되돌아간다.
  visibleCount: number | null
  publishVisibleCount: (count: number | null) => void
}

const ScreenContext = createContext<ScreenContextValue | null>(null)

export function ScreenProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [filters, setFilters] = useState<ScreenRequest>(DEFAULT_SCREEN_REQUEST)
  const [results, setResults] = useState<ScreenResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [visibleCount, setVisibleCount] = useState<number | null>(null)

  const publishVisibleCount = useCallback((count: number | null) => {
    setVisibleCount((prev) => (prev === count ? prev : count))
  }, [])

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

  const clearResults = useCallback(() => {
    setResults(null)
    setFilters(DEFAULT_SCREEN_REQUEST)
  }, [])

  return (
    <ScreenContext.Provider value={{ filters, results, loading, error, applyFilters, updateFilters, clearResults, visibleCount, publishVisibleCount }}>
      {children}
    </ScreenContext.Provider>
  )
}

const noopPublish = (): void => {}

// 게시 전용 훅 — Provider 밖(단독 렌더 테스트 등)에서는 무동작이다. 보이는 모집단 수를
// 게시하려는 화면이 ScreenProvider 존재 여부에 결합되지 않게 한다.
export function usePublishVisibleCount(): (count: number | null) => void {
  return useContext(ScreenContext)?.publishVisibleCount ?? noopPublish
}

export function useScreen(): ScreenContextValue {
  const ctx = useContext(ScreenContext)
  if (!ctx) throw new Error('useScreen must be used within ScreenProvider')
  return ctx
}
