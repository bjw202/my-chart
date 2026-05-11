/**
 * useStockMaster — 종목 마스터 데이터 페치 훅
 *
 * REQ-SEARCH-002: SPA 세션 1회 fetch (module-level cachedPromise)
 * REQ-SEARCH-006: 503 에러 시 disabled 상태 노출
 *
 * @MX:NOTE: [AUTO] module-level cachedPromise — SPA 세션 1회 fetch invariant.
 *   향후 DbUpdateButton 연동(Q-6) 시 reset 분기 위치.
 *   vitest beforeEach에서 vi.resetModules()로 캐시 초기화 필요.
 */

import { useEffect, useState } from 'react'
import { fetchStockMaster } from '../api/stocks'
import type { StockMasterResponse } from '../api/stocks'

// 모듈 레벨 캐시 — 컴포넌트 재마운트 시에도 재요청 없음
let cachedPromise: Promise<StockMasterResponse> | null = null

export interface UseStockMasterResult {
  data: StockMasterResponse | null
  loading: boolean
  error: Error | null
  dispatched: boolean
}

export function useStockMaster(): UseStockMasterResult {
  const [data, setData] = useState<StockMasterResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const [dispatched, setDispatched] = useState(false)

  useEffect(() => {
    if (!cachedPromise) {
      cachedPromise = fetchStockMaster()
    }
    setDispatched(true)
    setLoading(true)
    cachedPromise
      .then((res) => {
        setData(res)
        setError(null)
      })
      .catch((err: Error) => {
        setError(err)
        // 503이면 캐시를 비워 재시도 가능하게 하지 않는다 — 서버 재기동 전까지 의미 없음
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  return { data, loading, error, dispatched }
}
