import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { fetchMarketOverview, fetchSectorRanking } from '../api/market'
import type { MarketOverviewResponse, SectorRankingResponse } from '../types/market'

// Cache TTL: 1 hour in milliseconds
const CACHE_TTL_MS = 60 * 60 * 1000

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

  const fetchAll = useCallback(async (force = false) => {
    const now = Date.now()
    // Skip if within cache TTL and not forced
    if (!force && lastFetchRef.current > 0 && now - lastFetchRef.current < CACHE_TTL_MS) {
      return
    }
    setLoading(true)
    setError(null)
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
        setError(overviewResult.reason instanceof Error ? overviewResult.reason.message : 'Failed to fetch market data')
      } else {
        lastFetchRef.current = Date.now()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch market data')
    } finally {
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
