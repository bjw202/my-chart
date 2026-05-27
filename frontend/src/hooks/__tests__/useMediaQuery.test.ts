// SPEC-SECTOR-MINOR-COLOR-001: useMediaQuery hook 테스트
// window.matchMedia 기반 반응형 hook의 초기 상태, 이벤트 갱신, cleanup 검증
import { describe, it, expect, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useMediaQuery } from '../useMediaQuery'

describe('useMediaQuery', () => {
  let listeners: Array<(e: MediaQueryListEvent) => void> = []
  let currentMatches = false

  const mockMatchMedia = (initialMatches: boolean) => {
    currentMatches = initialMatches
    listeners = []
    vi.stubGlobal(
      'matchMedia',
      vi.fn().mockImplementation((query: string) => ({
        matches: currentMatches,
        media: query,
        onchange: null,
        addListener: vi.fn(),       // deprecated API 호환
        removeListener: vi.fn(),    // deprecated API 호환
        addEventListener: vi.fn((event: string, handler: (e: MediaQueryListEvent) => void) => {
          if (event === 'change') listeners.push(handler)
        }),
        removeEventListener: vi.fn((event: string, handler: (e: MediaQueryListEvent) => void) => {
          if (event === 'change') {
            const idx = listeners.indexOf(handler)
            if (idx >= 0) listeners.splice(idx, 1)
          }
        }),
        dispatchEvent: vi.fn(),
      }))
    )
  }

  afterEach(() => {
    vi.unstubAllGlobals()
    listeners = []
  })

  it('초기 matches=true 상태를 반환한다', () => {
    mockMatchMedia(true)
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    expect(result.current).toBe(true)
  })

  it('초기 matches=false 상태를 반환한다', () => {
    mockMatchMedia(false)
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    expect(result.current).toBe(false)
  })

  it('matchMedia change 이벤트로 상태가 true→false로 갱신된다', () => {
    mockMatchMedia(false)
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    expect(result.current).toBe(false)

    act(() => {
      currentMatches = true
      listeners.forEach((h) => h({ matches: true } as MediaQueryListEvent))
    })
    expect(result.current).toBe(true)
  })

  it('matchMedia change 이벤트로 상태가 false→true로 갱신된다', () => {
    mockMatchMedia(true)
    const { result } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    expect(result.current).toBe(true)

    act(() => {
      currentMatches = false
      listeners.forEach((h) => h({ matches: false } as MediaQueryListEvent))
    })
    expect(result.current).toBe(false)
  })

  it('unmount 시 addEventListener listener를 cleanup한다', () => {
    mockMatchMedia(false)
    const { unmount } = renderHook(() => useMediaQuery('(max-width: 767px)'))
    // useEffect 등록 후 listener가 추가됨
    expect(listeners.length).toBe(1)
    unmount()
    // removeEventListener 호출로 listener 제거됨
    expect(listeners.length).toBe(0)
  })

  it('query 변경 시 이전 listener를 cleanup하고 새 listener를 등록한다', () => {
    mockMatchMedia(false)
    const { rerender } = renderHook(({ q }: { q: string }) => useMediaQuery(q), {
      initialProps: { q: '(max-width: 767px)' },
    })
    expect(listeners.length).toBe(1)

    // query 변경 → 이전 listener cleanup + 새 listener 등록
    rerender({ q: '(min-width: 1024px)' })
    // cleanup 후 재등록: 여전히 1개
    expect(listeners.length).toBe(1)
  })
})
