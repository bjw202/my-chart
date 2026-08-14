// RED: AC-SUX-033 (쿼리 키·조회 시점) / 034 (TTL) / 035 (stale-but-showing) /
//      036 (재시도·수동 새로고침) / 037 (기준일 합치 + grid_version 무효화)
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor, render, screen, cleanup } from '@testing-library/react'
import type { ReactNode } from 'react'
import { AnalysisParamsProvider, useAnalysisParams } from '../AnalysisParamsContext'
import {
  DataLoadProvider,
  useQuery,
  useDataRefresh,
  useAsOfCoherence,
  buildQueryKey,
  RETRY_DELAYS_MS,
} from '../DataLoadContext'

function wrapper({ children }: { children: ReactNode }) {
  return (
    <AnalysisParamsProvider>
      <DataLoadProvider>{children}</DataLoadProvider>
    </AnalysisParamsProvider>
  )
}

interface Envelope { rows: number[]; as_of_date: string; as_of_is_partial_week?: boolean; grid_version?: string }

const env = (over: Partial<Envelope> = {}): Envelope => ({
  rows: [1, 2, 3],
  as_of_date: '2026-08-11',
  as_of_is_partial_week: false,
  grid_version: 'g1',
  ...over,
})

const META = (d: Envelope) => ({
  asOfDate: d.as_of_date,
  asOfIsPartialWeek: d.as_of_is_partial_week ?? false,
  gridVersion: d.grid_version ?? null,
})

afterEach(() => { cleanup(); vi.useRealTimers() })

describe('buildQueryKey — 쿼리 키 (AC-SUX-033 LD-A)', () => {
  it('엔드포인트 + 파라미터가 같으면 같은 키, 하나라도 다르면 다른 키다', () => {
    expect(buildQueryKey('sector-bubble', { period: '1m', market: 'all' }))
      .toBe(buildQueryKey('sector-bubble', { market: 'all', period: '1m' }))
    expect(buildQueryKey('sector-bubble', { period: '1m', market: 'all' }))
      .not.toBe(buildQueryKey('sector-bubble', { period: '3m', market: 'all' }))
    expect(buildQueryKey('sector-bubble', { period: '1m', market: 'all' }))
      .not.toBe(buildQueryKey('sector-ranking', { period: '1m', market: 'all' }))
  })
})

describe('AC-SUX-033 — 조회 시점: 비활성 화면은 fetch 하지 않는다', () => {
  it('enabled:false 면 fetch 가 발생하지 않는다 (부팅 시 비활성 탭)', async () => {
    const fetcher = vi.fn().mockResolvedValue(env())
    renderHook(() => useQuery('k1', fetcher, { enabled: false, panel: 'p', meta: META }), { wrapper })
    await new Promise(r => setTimeout(r, 10))
    expect(fetcher).not.toHaveBeenCalled()
  })

  it('enabled:true 로 활성화되는 순간 fetch 가 1회 발생한다', async () => {
    const fetcher = vi.fn().mockResolvedValue(env())
    const { rerender } = renderHook(
      ({ on }: { on: boolean }) => useQuery('k1', fetcher, { enabled: on, panel: 'p', meta: META }),
      { wrapper, initialProps: { on: false } },
    )
    expect(fetcher).not.toHaveBeenCalled()
    rerender({ on: true })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
  })

  it('같은 키로 비활성→재활성 왕복해도 TTL 내에서는 추가 fetch 가 없다', async () => {
    const fetcher = vi.fn().mockResolvedValue(env())
    const { rerender } = renderHook(
      ({ on }: { on: boolean }) => useQuery('k1', fetcher, { enabled: on, panel: 'p', meta: META }),
      { wrapper, initialProps: { on: true } },
    )
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
    rerender({ on: false })
    rerender({ on: true })
    await new Promise(r => setTimeout(r, 10))
    expect(fetcher).toHaveBeenCalledTimes(1)
  })

  it('키가 바뀌면(period 변경) 활성 화면은 즉시 재조회한다', async () => {
    const fetcher = vi.fn().mockResolvedValue(env())
    const { rerender } = renderHook(
      ({ k }: { k: string }) => useQuery(k, fetcher, { enabled: true, panel: 'p', meta: META }),
      { wrapper, initialProps: { k: 'sector|1m' } },
    )
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
    rerender({ k: 'sector|3m' })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  })

  it('키가 바뀌어도 비활성 화면은 fetch 하지 않는다 — 활성화 시점에 조회한다', async () => {
    const fetcher = vi.fn().mockResolvedValue(env())
    const { rerender } = renderHook(
      ({ k, on }: { k: string; on: boolean }) => useQuery(k, fetcher, { enabled: on, panel: 'p', meta: META }),
      { wrapper, initialProps: { k: 'sector|1m', on: false } },
    )
    rerender({ k: 'sector|3m', on: false })
    await new Promise(r => setTimeout(r, 10))
    expect(fetcher).not.toHaveBeenCalled()
    rerender({ k: 'sector|3m', on: true })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
  })
})

describe('AC-SUX-034 — TTL 1시간 (LD-B)', () => {
  it('59분 경과 후 재활성화 → fetch 없음 / 61분 경과 후 → fetch 발생', async () => {
    const fetcher = vi.fn().mockResolvedValue(env())
    const nowRef = { v: 1_000_000 }
    vi.spyOn(Date, 'now').mockImplementation(() => nowRef.v)

    const { rerender } = renderHook(
      ({ on }: { on: boolean }) => useQuery('k1', fetcher, { enabled: on, panel: 'p', meta: META }),
      { wrapper, initialProps: { on: true } },
    )
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))

    // 59분 경과 후 재활성화 → 캐시 fresh → fetch 없음
    nowRef.v += 59 * 60 * 1000
    rerender({ on: false })
    rerender({ on: true })
    await new Promise(r => setTimeout(r, 10))
    expect(fetcher).toHaveBeenCalledTimes(1)

    // 추가 2분(총 61분) 경과 후 재활성화 → 캐시 stale → fetch 발생
    nowRef.v += 2 * 60 * 1000
    rerender({ on: false })
    rerender({ on: true })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  })
})

describe('AC-SUX-035 — 재조회 중 기존 데이터 유지 (LD-C)', () => {
  it('키 변경 재조회 동안 이전 data 가 유지되고 refetching=true 다', async () => {
    let resolveSecond: ((v: Envelope) => void) | null = null
    const fetcher = vi.fn()
      .mockResolvedValueOnce(env({ rows: [1] }))
      .mockImplementationOnce(() => new Promise<Envelope>(res => { resolveSecond = res }))

    const { result, rerender } = renderHook(
      ({ k }: { k: string }) => useQuery(k, fetcher, { enabled: true, panel: 'p', meta: META }),
      { wrapper, initialProps: { k: 'a' } },
    )
    await waitFor(() => expect(result.current.data).toEqual(env({ rows: [1] })))

    rerender({ k: 'b' })
    await waitFor(() => expect(result.current.refetching).toBe(true))
    // 재조회 중에도 이전 데이터가 그대로 노출된다 (표가 비지 않는다)
    expect(result.current.data).toEqual(env({ rows: [1] }))
    expect(result.current.loading).toBe(false)

    await act(async () => { resolveSecond!(env({ rows: [9] })) })
    await waitFor(() => expect(result.current.data).toEqual(env({ rows: [9] })))
    expect(result.current.refetching).toBe(false)
  })

  it('재조회 실패 시 이전 데이터를 유지하고 이전 기준일을 error 와 함께 노출한다', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(env({ rows: [1], as_of_date: '2026-08-07' }))
      .mockRejectedValue(new Error('boom'))

    const { result, rerender } = renderHook(
      ({ k }: { k: string }) => useQuery(k, fetcher, { enabled: true, panel: 'p', meta: META, retryDelays: [] }),
      { wrapper, initialProps: { k: 'a' } },
    )
    await waitFor(() => expect(result.current.data).not.toBeNull())

    rerender({ k: 'b' })
    await waitFor(() => expect(result.current.error).not.toBeNull())
    // 기존 데이터 유지 + 이전 기준일 노출 → "갱신 실패 — 표시 중인 데이터는 {이전 기준일} 기준입니다"
    expect(result.current.data).toEqual(env({ rows: [1], as_of_date: '2026-08-07' }))
    expect(result.current.staleAsOf).toBe('2026-08-07')
  })
})

describe('AC-SUX-036 — 자동 재시도 + 수동 새로고침 (LD-D)', () => {
  it('RETRY_DELAYS_MS 는 2s/4s/8s 지수 백오프다 (MarketContext 기존 계약 공유)', () => {
    expect(RETRY_DELAYS_MS).toEqual([2000, 4000, 8000])
  })

  it('첫 3회 실패 → 2s/4s/8s 간격 3회 재시도 후 멈추고 retryExhausted 가 선다', async () => {
    vi.useFakeTimers()
    const fetcher = vi.fn().mockRejectedValue(new Error('down'))
    const { result } = renderHook(
      () => useQuery('k1', fetcher, { enabled: true, panel: 'p', meta: META }),
      { wrapper },
    )
    await act(async () => { await vi.advanceTimersByTimeAsync(0) })
    expect(fetcher).toHaveBeenCalledTimes(1)

    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    expect(fetcher).toHaveBeenCalledTimes(2)
    await act(async () => { await vi.advanceTimersByTimeAsync(4000) })
    expect(fetcher).toHaveBeenCalledTimes(3)
    await act(async () => { await vi.advanceTimersByTimeAsync(8000) })
    expect(fetcher).toHaveBeenCalledTimes(4)

    // 3회 소진 후에는 아무리 시간이 흘러도 더 재시도하지 않는다
    await act(async () => { await vi.advanceTimersByTimeAsync(60_000) })
    expect(fetcher).toHaveBeenCalledTimes(4)
    expect(result.current.retryExhausted).toBe(true)
    expect(result.current.error).not.toBeNull()
  })

  it('4회째 성공하도록 mock 하면 데이터가 채워지고 retryExhausted 가 서지 않는다', async () => {
    vi.useFakeTimers()
    const fetcher = vi.fn()
      .mockRejectedValueOnce(new Error('1'))
      .mockRejectedValueOnce(new Error('2'))
      .mockRejectedValueOnce(new Error('3'))
      .mockResolvedValue(env({ rows: [7] }))
    const { result } = renderHook(
      () => useQuery('k1', fetcher, { enabled: true, panel: 'p', meta: META }),
      { wrapper },
    )
    await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
    await act(async () => { await vi.advanceTimersByTimeAsync(4000) })
    await act(async () => { await vi.advanceTimersByTimeAsync(8000) })
    expect(fetcher).toHaveBeenCalledTimes(4)
    expect(result.current.data).toEqual(env({ rows: [7] }))
    expect(result.current.retryExhausted).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('retry() 수동 호출은 소진 상태를 풀고 다시 조회한다', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('down'))
    const { result } = renderHook(
      () => useQuery('k1', fetcher, { enabled: true, panel: 'p', meta: META, retryDelays: [] }),
      { wrapper },
    )
    await waitFor(() => expect(result.current.retryExhausted).toBe(true))
    fetcher.mockResolvedValue(env({ rows: [5] }))
    act(() => { result.current.retry() })
    await waitFor(() => expect(result.current.data).toEqual(env({ rows: [5] })))
  })

  it('refreshAll() 은 전 캐시를 무효화하고 활성 화면을 재조회한다', async () => {
    const fetcher = vi.fn().mockResolvedValue(env())
    const { result } = renderHook(
      () => ({
        q: useQuery('k1', fetcher, { enabled: true, panel: 'p', meta: META }),
        r: useDataRefresh(),
      }),
      { wrapper },
    )
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
    // TTL 내이지만 수동 새로고침은 캐시를 무시하고 재조회한다
    act(() => { result.current.r.refreshAll() })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  })
})

describe('AC-SUX-037 — 기준일 합치 + grid_version 무효화 (LD-E / SN-3 / SN-5)', () => {
  it('두 패널의 as_of_date 가 다르면 충돌이 보고된다 (패널명 + 두 날짜)', async () => {
    const fa = vi.fn().mockResolvedValue(env({ as_of_date: '2026-08-07' }))
    const fb = vi.fn().mockResolvedValue(env({ as_of_date: '2026-08-11' }))
    const { result } = renderHook(
      () => {
        useQuery('a', fa, { enabled: true, panel: '섹터 순위', meta: META })
        useQuery('b', fb, { enabled: true, panel: '종목 탐색', meta: META })
        return useAsOfCoherence()
      },
      { wrapper },
    )
    await waitFor(() => expect(result.current.conflict).not.toBeNull())
    expect(result.current.conflict!.dates.sort()).toEqual(['2026-08-07', '2026-08-11'])
    expect(result.current.conflict!.panels.sort()).toEqual(['섹터 순위', '종목 탐색'])
  })

  it('두 패널의 as_of_date 가 같으면 충돌이 없다', async () => {
    const fa = vi.fn().mockResolvedValue(env({ as_of_date: '2026-08-11' }))
    const fb = vi.fn().mockResolvedValue(env({ as_of_date: '2026-08-11' }))
    const { result } = renderHook(
      () => {
        useQuery('a', fa, { enabled: true, panel: 'A', meta: META })
        useQuery('b', fb, { enabled: true, panel: 'B', meta: META })
        return useAsOfCoherence()
      },
      { wrapper },
    )
    await waitFor(() => expect(fa).toHaveBeenCalled())
    await waitFor(() => expect(fb).toHaveBeenCalled())
    await new Promise(r => setTimeout(r, 10))
    expect(result.current.conflict).toBeNull()
  })

  it('grid_version 이 바뀌면 전 캐시가 무효화되고 재조회가 발생한다', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(env({ grid_version: 'g1' }))
      .mockResolvedValue(env({ grid_version: 'g2' }))
    // 실제 백엔드는 전 엔드포인트가 같은 grid_version 을 내린다 — 다른 패널도 g1 → g2 로 따라간다.
    const other = vi.fn()
      .mockResolvedValueOnce(env({ grid_version: 'g1' }))
      .mockResolvedValue(env({ grid_version: 'g2' }))

    const { rerender } = renderHook(
      ({ k }: { k: string }) => {
        useQuery(k, fetcher, { enabled: true, panel: 'A', meta: META })
        useQuery('static', other, { enabled: true, panel: 'B', meta: META })
      },
      { wrapper, initialProps: { k: 'a' } },
    )
    await waitFor(() => expect(other).toHaveBeenCalledTimes(1))
    // 키를 바꿔 g2 응답을 받으면 grid_version 변경 → 전 캐시 무효 → 'static' 도 재조회
    rerender({ k: 'b' })
    await waitFor(() => expect(other).toHaveBeenCalledTimes(2))
  })

  it('응답의 as_of_date/partial_week/grid_version 이 AnalysisParamsContext 읽기전용 필드에 기록된다', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      env({ as_of_date: '2026-08-11', as_of_is_partial_week: true, grid_version: 'gX' }),
    )
    const { result } = renderHook(
      () => {
        useQuery('k1', fetcher, { enabled: true, panel: 'A', meta: META })
        return useAnalysisParams()
      },
      { wrapper },
    )
    await waitFor(() => expect(result.current.asOfDate).toBe('2026-08-11'))
    expect(result.current.asOfIsPartialWeek).toBe(true)
    expect(result.current.gridVersion).toBe('gX')
  })

  it('배지 텍스트는 응답 값과 문자열 동등하다 — 프론트에서 포맷 변환하지 않는다', async () => {
    const fetcher = vi.fn().mockResolvedValue(env({ as_of_date: '2026-08-11' }))
    function Probe() {
      const q = useQuery('k1', fetcher, { enabled: true, panel: 'A', meta: META })
      return <span data-testid="asof">{q.asOfDate ?? ''}</span>
    }
    render(<AnalysisParamsProvider><DataLoadProvider><Probe /></DataLoadProvider></AnalysisParamsProvider>)
    await waitFor(() => expect(screen.getByTestId('asof').textContent).toBe('2026-08-11'))
  })
})

describe('AC-SUX-036 — 백엔드 워밍업 실패 후 탭 재활성화 자가 복구', () => {
  beforeEach(() => { vi.useRealTimers() })

  it('실패로 캐시가 비어 있으면 재활성화만으로 재조회된다', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('warming up'))
    const { result, rerender } = renderHook(
      ({ on }: { on: boolean }) => useQuery('k1', fetcher, { enabled: on, panel: 'A', meta: META, retryDelays: [] }),
      { wrapper, initialProps: { on: true } },
    )
    await waitFor(() => expect(result.current.error).not.toBeNull())
    expect(fetcher).toHaveBeenCalledTimes(1)

    fetcher.mockResolvedValue(env({ rows: [42] }))
    rerender({ on: false })
    rerender({ on: true })
    await waitFor(() => expect(result.current.data).toEqual(env({ rows: [42] })))
  })
})
