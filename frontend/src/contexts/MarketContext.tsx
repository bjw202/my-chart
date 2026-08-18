import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { fetchMarketOverview, fetchSectorRanking } from '../api/market'
import type { MarketOverviewResponse, SectorRankingResponse } from '../types/market'
import { useAnalysisParams } from './AnalysisParamsContext'

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
  // AC-SUX-018: market 는 AnalysisParamsContext 에서 소비 (02 §3.3 소유권 — MarketContext 가 소유하지 않음).
  // fetchAll 은 ref 로 market 을 읽어 안정적([]) 이고, 단일 effect 가 mount + market 변경 시 재조회한다 (ST-4 해소).
  // M7 (REQ-SDU-006): period 도 같은 관용(periodRef)으로 확장 — 기간 토글 시 봉투 data[] 의
  //   기간별 rank 를 받기 위해 fetchSectorRanking 에 period 를 전달한다. overview 도 함께
  //   재조회되지만(allSettled) 값은 period 무관하므로 무해하다.
  const { market, period } = useAnalysisParams()
  const marketRef = useRef(market)
  const periodRef = useRef(period)
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
        fetchSectorRanking(marketRef.current, periodRef.current),
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

  // Fetch on mount + market·period 변경 시 재조회 (AC-SUX-018 / M7 REQ-SDU-006).
  // marketRef/periodRef 동기화 후 fetchAll(true) 강제 재조회. fetchAll 은 ref 를 읽으므로
  // 안정적([]) 이고, 이 effect 의 [market, period] dep 가 변경을 감지한다.
  useEffect(() => {
    marketRef.current = market
    periodRef.current = period
    void fetchAll(true)
  }, [fetchAll, market, period])

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
