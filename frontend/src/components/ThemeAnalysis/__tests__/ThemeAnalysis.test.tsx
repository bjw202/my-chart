// ThemeAnalysis vitest
// AC-11: V2 503 에러 메시지 + retry 버튼 (REQ-NT3-007)
// AC-12: retry 버튼 V2 재호출 (REQ-NT3-007)
// AC-19: default mode 'full' (REQ-NT3-012, v1.0.3 amendment)
// AC-20: quick 모드 advisory 노출 (REQ-NT3-013, v1.0.3 amendment)
// AC-22: localStorage cache hit on mount → no fetch (REQ-NT3-015, v1.0.5)
// AC-23: refresh button → cache invalidate + fetch + cache rewrite (REQ-NT3-016, v1.0.5)
// AC-24: quick/full mode별 캐시 key 분리 (REQ-NT3-015, v1.0.5)
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { ThemeAnalysis } from '../ThemeAnalysis'

// axios client mock — api client 모듈 경로 기준 (컴포넌트에서는 ../../api/client 참조)
vi.mock('../../../api/client', () => ({
  default: {
    get: vi.fn(),
  },
}))

import client from '../../../api/client'

// 정상 응답 mock 데이터 (retry 성공 시나리오용)
const mockOkResponse = {
  data: {
    themes: [],
    strong_themes: [],
    metadata: {
      collected_at: '2026-05-06T00:00:00+00:00',
      theme_count: 0,
      stock_count: 0,
      elapsed_sec: 0.5,
      errors: [],
    },
  },
}

// 503 에러 mock
const mock503Error = { response: { status: 503 }, message: 'Service Unavailable' }

describe('ThemeAnalysis — V2 503 에러 처리 (AC-11)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('shows error message + retry button on V2 503', async () => {
    // 503으로 계속 실패하도록 mock
    vi.mocked(client.get).mockRejectedValue(mock503Error)

    render(<ThemeAnalysis />)

    await waitFor(() => {
      // 에러 메시지 텍스트 존재 (AC-11)
      expect(screen.getByText(/테마 데이터를 가져오지 못했습니다/i)).toBeTruthy()
      // retry 버튼 존재
      const retryBtn = screen.getByRole('button', { name: /다시 시도|retry/i })
      expect(retryBtn).toBeTruthy()
    })

    // V1 endpoint 자동 폴백 호출 부재 검증 (REQ-NT3-C-006)
    const calls = vi.mocked(client.get).mock.calls
    const v1Calls = calls.filter(([url]) => url === '/themes/snapshot' || url === '/themes/quick')
    expect(v1Calls.length).toBe(0)
  })
})

describe('ThemeAnalysis — default mode full (AC-19, REQ-NT3-012 v1.0.3)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('default mode is full — calls /themes/v2/snapshot on initial render (not /themes/v2/quick)', async () => {
    vi.mocked(client.get).mockResolvedValue({
      data: {
        themes: [],
        strong_themes: [],
        stocks: [],
        leaders: [],
        multi_theme_stocks: [],
        metadata: {
          collected_at: '2026-05-06T00:00:00+00:00',
          theme_count: 0,
          stock_count: 0,
          elapsed_sec: 0.5,
          errors: [],
        },
      },
    })

    render(<ThemeAnalysis />)

    await waitFor(() => {
      const calls = vi.mocked(client.get).mock.calls
      const snapshotCalls = calls.filter(([url]) => url === '/themes/v2/snapshot')
      expect(snapshotCalls.length).toBeGreaterThanOrEqual(1)

      // quick endpoint는 default 진입 시 호출되지 않아야 함
      const quickCalls = calls.filter(([url]) => url === '/themes/v2/quick')
      expect(quickCalls.length).toBe(0)
    })
  })
})

describe('ThemeAnalysis — quick 모드 advisory (AC-20, REQ-NT3-013 v1.0.3)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('shows advisory when mode is toggled to quick (default full has no advisory)', async () => {
    vi.mocked(client.get).mockResolvedValue({
      data: {
        themes: [],
        strong_themes: [],
        stocks: [],
        leaders: [],
        multi_theme_stocks: [],
        metadata: {
          collected_at: '2026-05-06T00:00:00+00:00',
          theme_count: 0,
          stock_count: 0,
          elapsed_sec: 0.5,
          errors: [],
        },
      },
    })

    render(<ThemeAnalysis />)

    // default full → advisory 미노출
    await waitFor(() => {
      expect(screen.queryByTestId('theme-quick-advisory')).toBeNull()
    })

    // "빠른 조회" 토글 클릭
    fireEvent.click(screen.getByRole('button', { name: /빠른 조회/i }))

    // advisory 노출 검증
    await waitFor(() => {
      const advisory = screen.queryByTestId('theme-quick-advisory')
      expect(advisory).not.toBeNull()
      expect(advisory?.textContent).toContain('빠른 조회 모드')
    })
  })
})

describe('ThemeAnalysis — retry 버튼 V2 재호출 (AC-12)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('retry button triggers V2 endpoint re-fetch', async () => {
    // 첫 번째 호출: 503 실패
    vi.mocked(client.get).mockRejectedValueOnce(mock503Error)

    render(<ThemeAnalysis />)

    // 에러 상태 + retry 버튼 대기
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /다시 시도|retry/i })).toBeTruthy()
    })

    // 두 번째 호출(retry): 200 성공으로 mock 교체
    vi.mocked(client.get).mockResolvedValueOnce(mockOkResponse)

    // retry 버튼 클릭
    fireEvent.click(screen.getByRole('button', { name: /다시 시도|retry/i }))

    await waitFor(() => {
      // V2 endpoint 추가 호출 검증 (총 2회 이상 — 첫 503 + retry)
      const calls = vi.mocked(client.get).mock.calls
      const v2Calls = calls.filter(([url]) => typeof url === 'string' && url.startsWith('/themes/v2/'))
      expect(v2Calls.length).toBeGreaterThanOrEqual(2)
    })
  })
})

// localStorage 캐시 fixture 빌더
const buildCacheEntry = (themeName: string, savedAt = '2026-05-06T10:00:00+00:00') => ({
  cache_version: 'v1',
  saved_at: savedAt,
  data: {
    themes: [{
      theme_id: 1,
      theme_name: themeName,
      change_pct: 5,
      change_pct_3d: 7,
      momentum_score: null,
      breadth_ratio: null,
      theme_description: '캐시된 테마 설명',
    }],
    strong_themes: [{
      theme_id: 1,
      theme_name: themeName,
      change_pct: 5,
      change_pct_3d: 7,
      momentum_score: null,
      breadth_ratio: null,
      theme_description: '캐시된 테마 설명',
    }],
    stocks: [],
    leaders: [],
    multi_theme_stocks: [],
    metadata: {
      collected_at: '2026-05-06T10:00:00+00:00',
      theme_count: 1,
      stock_count: 0,
      elapsed_sec: 30,
      errors: [],
    },
  },
})

describe('ThemeAnalysis — localStorage cache hit on mount (AC-22, REQ-NT3-015 v1.0.5)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('skips fetch and renders cached data when full cache exists at mount', async () => {
    const cached = buildCacheEntry('CachedTheme')
    localStorage.setItem('theme-analysis-cache-full', JSON.stringify(cached))

    // network mock도 준비하되 호출되어선 안 됨
    vi.mocked(client.get).mockResolvedValue(mockOkResponse)

    render(<ThemeAnalysis />)

    // 캐시 데이터가 즉시 렌더링됨 (랭킹 테이블 + detail panel 양쪽에 등장 가능)
    await waitFor(() => {
      expect(screen.getAllByText('CachedTheme').length).toBeGreaterThan(0)
    })

    // network fetch는 호출되지 않음 (cache hit)
    expect(vi.mocked(client.get)).not.toHaveBeenCalled()
  })

  it('treats cache as missing when cache_version mismatches and fetches', async () => {
    // v0 (오래된 schema) → 무효화되어야 함
    const stale = { ...buildCacheEntry('Stale'), cache_version: 'v0' }
    localStorage.setItem('theme-analysis-cache-full', JSON.stringify(stale))

    vi.mocked(client.get).mockResolvedValue(mockOkResponse)

    render(<ThemeAnalysis />)

    await waitFor(() => {
      // schema mismatch → fetch 발생
      const calls = vi.mocked(client.get).mock.calls
      expect(calls.some(([url]) => url === '/themes/v2/snapshot')).toBe(true)
    })
  })
})

describe('ThemeAnalysis — refresh button invalidates cache + new fetch (AC-23, REQ-NT3-016 v1.0.5)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('refresh button removes cache, triggers fetch, and rewrites cache with new response', async () => {
    // 사전 cache (이전 데이터)
    const oldCache = buildCacheEntry('OldData')
    localStorage.setItem('theme-analysis-cache-full', JSON.stringify(oldCache))

    // 새 응답 (refresh 후 받게 될 데이터)
    vi.mocked(client.get).mockResolvedValue({
      data: {
        themes: [{
          theme_id: 99,
          theme_name: 'RefreshedData',
          change_pct: 10,
          change_pct_3d: 12,
          momentum_score: null,
          breadth_ratio: null,
          theme_description: '새로 받아온 설명',
        }],
        strong_themes: [{
          theme_id: 99,
          theme_name: 'RefreshedData',
          change_pct: 10,
          change_pct_3d: 12,
          momentum_score: null,
          breadth_ratio: null,
          theme_description: '새로 받아온 설명',
        }],
        stocks: [],
        leaders: [],
        multi_theme_stocks: [],
        metadata: {
          collected_at: '2026-05-06T11:00:00+00:00',
          theme_count: 1,
          stock_count: 0,
          elapsed_sec: 31,
          errors: [],
        },
      },
    })

    render(<ThemeAnalysis />)

    // 처음에는 cache hit으로 fetch 안 함, OldData 표시
    await waitFor(() => {
      expect(screen.getAllByText('OldData').length).toBeGreaterThan(0)
    })
    expect(vi.mocked(client.get)).not.toHaveBeenCalled()

    // 🔄 갱신 버튼 클릭
    const refreshBtn = screen.getByTestId('theme-refresh-button')
    fireEvent.click(refreshBtn)

    // V2 endpoint 호출 발생 + 새 데이터 표시
    await waitFor(() => {
      const calls = vi.mocked(client.get).mock.calls
      expect(calls.some(([url]) => url === '/themes/v2/snapshot')).toBe(true)
    })
    await waitFor(() => {
      expect(screen.getAllByText('RefreshedData').length).toBeGreaterThan(0)
    })

    // localStorage가 새 응답으로 덮어쓰여짐
    const updated = JSON.parse(localStorage.getItem('theme-analysis-cache-full')!)
    expect(updated.cache_version).toBe('v1')
    expect(updated.data.themes[0].theme_name).toBe('RefreshedData')
  })
})

describe('ThemeAnalysis — quick/full 모드별 캐시 key 분리 (AC-24, REQ-NT3-015 v1.0.5)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('quick cache is not used when default mode is full', async () => {
    // quick mode cache만 저장 (full 부재)
    localStorage.setItem('theme-analysis-cache-quick', JSON.stringify(buildCacheEntry('QuickOnly')))

    vi.mocked(client.get).mockResolvedValue(mockOkResponse)

    render(<ThemeAnalysis />)

    // default가 'full'이므로 quick 캐시는 무시 → fetch 발생
    await waitFor(() => {
      const calls = vi.mocked(client.get).mock.calls
      expect(calls.some(([url]) => url === '/themes/v2/snapshot')).toBe(true)
      expect(calls.some(([url]) => url === '/themes/v2/quick')).toBe(false)
    })
  })

  it('mode toggle to quick uses quick cache without fetching when present', async () => {
    // full cache 저장 (default 진입 시 사용)
    localStorage.setItem('theme-analysis-cache-full', JSON.stringify(buildCacheEntry('FullCached')))
    // quick cache도 저장 (quick 토글 시 사용)
    localStorage.setItem('theme-analysis-cache-quick', JSON.stringify(buildCacheEntry('QuickCached')))

    vi.mocked(client.get).mockResolvedValue(mockOkResponse)

    render(<ThemeAnalysis />)

    // default full → FullCached 표시, fetch 0
    await waitFor(() => {
      expect(screen.getAllByText('FullCached').length).toBeGreaterThan(0)
    })
    expect(vi.mocked(client.get)).not.toHaveBeenCalled()

    // quick 토글
    fireEvent.click(screen.getByRole('button', { name: /빠른 조회/i }))

    // quick cache hit → QuickCached 표시, 여전히 fetch 0
    await waitFor(() => {
      expect(screen.getAllByText('QuickCached').length).toBeGreaterThan(0)
    })
    expect(vi.mocked(client.get)).not.toHaveBeenCalled()
  })
})
