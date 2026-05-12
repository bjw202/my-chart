/**
 * SPEC-CHART-SEARCH-001 T3 RED — useStockMaster hook 테스트
 *
 * AC-SEARCH-002 (must-pass): SPA 세션 1회 fetch + cachedPromise invariant
 * AC-SEARCH-007: 503 응답 시 error: stock_meta_not_ready
 *
 * 구현 노트: cachedPromise는 모듈 레벨이므로 vi.isolateModules()로 각 테스트를 격리한다.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

const mockData = {
  stocks: [
    { code: '005930', name: '삼성전자', market: 'KOSPI' },
    { code: '000660', name: 'SK하이닉스', market: 'KOSPI' },
  ],
  generated_at: '2026-05-10T18:00:00+09:00',
}

beforeEach(() => {
  vi.resetModules()
})

// ---------------------------------------------------------------------------
// AC-SEARCH-002 — cachedPromise: 세션 1회 fetch
// ---------------------------------------------------------------------------

describe('useStockMaster — cachedPromise invariant (AC-SEARCH-002)', () => {
  it('첫 호출 시 fetchStockMaster 1회 호출', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockData)
    vi.doMock('../../api/stocks', () => ({ fetchStockMaster: fetchMock }))

    const { useStockMaster } = await import('../useStockMaster')
    const { result } = renderHook(() => useStockMaster())
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toEqual(mockData)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('동일 hook 재마운트 시 추가 fetch 0 (cachedPromise reuse)', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockData)
    vi.doMock('../../api/stocks', () => ({ fetchStockMaster: fetchMock }))

    const { useStockMaster } = await import('../useStockMaster')

    // 첫 마운트
    const { result: r1, unmount: u1 } = renderHook(() => useStockMaster())
    await waitFor(() => expect(r1.current.loading).toBe(false))

    // unmount 후 재마운트
    u1()
    const { result: r2 } = renderHook(() => useStockMaster())
    await waitFor(() => expect(r2.current.loading).toBe(false))

    // fetchStockMaster는 첫 호출 1회만
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(r2.current.data).toEqual(mockData)
  })

  it('dispatched: true 반환', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockData)
    vi.doMock('../../api/stocks', () => ({ fetchStockMaster: fetchMock }))

    const { useStockMaster } = await import('../useStockMaster')
    const { result } = renderHook(() => useStockMaster())
    await waitFor(() => expect(result.current.dispatched).toBe(true))
  })
})

// ---------------------------------------------------------------------------
// AC-SEARCH-007 — 503 응답 시 error 노출
// ---------------------------------------------------------------------------

describe('useStockMaster — 503 error (AC-SEARCH-007)', () => {
  it('503 → data null + error stock_meta_not_ready', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error('stock_meta_not_ready'))
    vi.doMock('../../api/stocks', () => ({ fetchStockMaster: fetchMock }))

    const { useStockMaster } = await import('../useStockMaster')
    const { result } = renderHook(() => useStockMaster())
    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.data).toBeNull()
    expect(result.current.error?.message).toBe('stock_meta_not_ready')
    expect(result.current.dispatched).toBe(true)
  })
})
