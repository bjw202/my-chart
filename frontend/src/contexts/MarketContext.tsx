import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { fetchMarketOverview, fetchSectorRanking } from '../api/market'
import type { MarketOverviewResponse, SectorRankingResponse } from '../types/market'

// Cache TTL: 1 hour in milliseconds
const CACHE_TTL_MS = 60 * 60 * 1000
// 백엔드 미응답 시 재시도 설정 (2초, 4초, 8초)
export const RETRY_DELAYS_MS = [2000, 4000, 8000]

interface MarketContextValue {
  overview: MarketOverviewResponse | null
  sectorRanking: SectorRankingResponse | null
  loading: boolean
  error: string | null
  refresh: () => void
}

const MarketContext = createContext<MarketContextValue | null>(null)

// @MX:ANCHOR: [AUTO] MarketProvider fetches and caches market overview + sector ranking
// @MX:REASON: Used by ContextBar and future market tabs; central data source, high fan_in

export function MarketProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [overview, setOverview] = useState<MarketOverviewResponse | null>(null)
  const [sectorRanking, setSectorRanking] = useState<SectorRankingResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // Track last fetch timestamp for 1-hour cache TTL
  const lastFetchRef = useRef<number>(0)

  const fetchAll = useCallback(async (force = false, retryCount = 0) => {
    const now = Date.now()
    // Skip if within cache TTL and not forced
    if (!force && lastFetchRef.current > 0 && now - lastFetchRef.current < CACHE_TTL_MS) {
      return
    }
    setLoading(true)
    setError(null)

    let shouldRetry = false

    try {
      // Fetch both endpoints in parallel; settle independently so one failure
      // does not block the other from providing data to the UI.
      const [overviewResult, rankingResult] = await Promise.allSettled([
        fetchMarketOverview(),
        fetchSectorRanking(),
      ])
      if (overviewResult.status === 'fulfilled') {
        setOverview(overviewResult.value)
      }
      if (rankingResult.status === 'fulfilled') {
        setSectorRanking(rankingResult.value)
      }
      // Only set error if both failed
      if (overviewResult.status === 'rejected' && rankingResult.status === 'rejected') {
        if (retryCount < RETRY_DELAYS_MS.length) {
          shouldRetry = true
        } else {
          setError(overviewResult.reason instanceof Error ? overviewResult.reason.message : 'Failed to fetch market data')
        }
      } else {
        lastFetchRef.current = Date.now()
      }
    } catch (err) {
      if (retryCount < RETRY_DELAYS_MS.length) {
        shouldRetry = true
      } else {
        setError(err instanceof Error ? err.message : 'Failed to fetch market data')
      }
    }

    // 백엔드 미응답 시 자동 재시도 (최대 3회, 2/4/8초 간격)
    if (shouldRetry) {
      setTimeout(() => void fetchAll(true, retryCount + 1), RETRY_DELAYS_MS[retryCount])
    } else {
      setLoading(false)
    }
  }, [])

  // Fetch on mount
  useEffect(() => {
    void fetchAll(true)
  }, [fetchAll])

  const refresh = useCallback(() => {
    void fetchAll(true)
  }, [fetchAll])

  return (
    <MarketContext.Provider value={{ overview, sectorRanking, loading, error, refresh }}>
      {children}
    </MarketContext.Provider>
  )
}

export function useMarket(): MarketContextValue {
  const ctx = useContext(MarketContext)
  if (!ctx) throw new Error('useMarket must be used within MarketProvider')
  return ctx
}
