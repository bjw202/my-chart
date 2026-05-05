// RED: themes.ts API 클라이언트 — V2 endpoint URL 검증 (SPEC-NAVER-THEME-003 AC-1~AC-3)
import { describe, it, expect, vi, beforeEach } from 'vitest'

// axios client mock — market.test.ts 동일 패턴
vi.mock('../client', () => ({
  default: {
    get: vi.fn(),
  },
}))

import client from '../client'
import { fetchThemesSnapshot, fetchThemesQuick } from '../themes'
import type { ThemeItem, ThemeStockItem } from '../themes'

// AC-1 검증용 mock 응답 (빈 배열 + 필수 metadata)
const mockSnapshotResponse = {
  themes: [],
  stocks: [],
  strong_themes: [],
  leaders: [],
  multi_theme_stocks: [],
  metadata: {
    collected_at: '2026-05-06T00:00:00+00:00',
    theme_count: 0,
    stock_count: 0,
    elapsed_sec: 1.5,
    errors: [],
  },
}

const mockQuickResponse = {
  themes: [],
  strong_themes: [],
  metadata: {
    collected_at: '2026-05-06T00:00:00+00:00',
    theme_count: 0,
    stock_count: 0,
    elapsed_sec: 0.3,
    errors: [],
  },
}

describe('themes API — V2 endpoint URL (AC-1)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('fetchThemesSnapshot calls /themes/v2/snapshot with params', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockSnapshotResponse })

    await fetchThemesSnapshot(20, 3)

    // V2 URL 호출 검증
    expect(client.get).toHaveBeenCalledWith('/themes/v2/snapshot', expect.any(Object))

    // V1 endpoint 호출 0건 검증 (REQ-NT3-C-006)
    const calls = vi.mocked(client.get).mock.calls
    const v1Calls = calls.filter(([url]) => url === '/themes/snapshot' || url === '/themes/quick')
    expect(v1Calls.length).toBe(0)
  })

  it('fetchThemesQuick calls /themes/v2/quick with params', async () => {
    vi.mocked(client.get).mockResolvedValue({ data: mockQuickResponse })

    await fetchThemesQuick(20)

    // V2 URL 호출 검증
    expect(client.get).toHaveBeenCalledWith('/themes/v2/quick', expect.any(Object))

    // V1 endpoint 호출 0건 검증 (REQ-NT3-C-006)
    const calls = vi.mocked(client.get).mock.calls
    const v1Calls = calls.filter(([url]) => url === '/themes/snapshot' || url === '/themes/quick')
    expect(v1Calls.length).toBe(0)
  })
})

// AC-2: ThemeItem.theme_description? 타입 존재 확인 (TypeScript compile 실패 시 vitest run 자체가 fail)
describe('ThemeItem 타입 — theme_description optional field (AC-2)', () => {
  it('theme_description string 값 할당 가능', () => {
    const theme: ThemeItem = {
      theme_id: 1,
      theme_name: '전선',
      change_pct: 9.2,
      change_pct_3d: 12.0,
      theme_description: '각종 전선 및 전람(電纜) 제조 테마',
    }
    expect(theme.theme_description).toBe('각종 전선 및 전람(電纜) 제조 테마')
  })

  it('theme_description null 할당 가능', () => {
    const theme: ThemeItem = {
      theme_id: 2,
      theme_name: '바이오',
      change_pct: 5.0,
      change_pct_3d: 7.0,
      theme_description: null,
    }
    expect(theme.theme_description).toBeNull()
  })

  it('theme_description 미포함 (undefined) 할당 가능', () => {
    const theme: ThemeItem = {
      theme_id: 3,
      theme_name: 'IT',
      change_pct: 1.0,
      change_pct_3d: 2.0,
    }
    expect(theme.theme_description).toBeUndefined()
  })
})

// AC-3: ThemeStockItem.stock_description? 타입 존재 확인 (forward-compat)
describe('ThemeStockItem 타입 — stock_description optional field (AC-3)', () => {
  it('stock_description string 값 할당 가능', () => {
    const stock: ThemeStockItem = {
      theme_id: 1,
      theme_name: '전선',
      stock_code: '009470',
      stock_name: '삼화전기',
      inclusion_reason: '전선 제조사',
      price: 12000,
      change: 100,
      change_pct: 0.84,
      volume: 100000,
      trade_value: 1_200_000_000,
      market_cap: 100_000_000_000,
      stock_description: '전선 제조사로 자동차 와이어하네스 등 다각화',
    }
    expect(stock.stock_description).toBe('전선 제조사로 자동차 와이어하네스 등 다각화')
  })

  it('stock_description null 할당 가능', () => {
    const stock: ThemeStockItem = {
      theme_id: 1,
      theme_name: '전선',
      stock_code: '009470',
      stock_name: '삼화전기',
      inclusion_reason: '전선 제조사',
      price: 12000,
      change: 100,
      change_pct: 0.84,
      volume: 100000,
      trade_value: 1_200_000_000,
      market_cap: null,
      stock_description: null,
    }
    expect(stock.stock_description).toBeNull()
  })

  it('stock_description 미포함 (undefined) 할당 가능', () => {
    const stock: ThemeStockItem = {
      theme_id: 1,
      theme_name: '전선',
      stock_code: '009470',
      stock_name: '삼화전기',
      inclusion_reason: '전선 제조사',
      price: 12000,
      change: 100,
      change_pct: 0.84,
      volume: 100000,
      trade_value: 1_200_000_000,
      market_cap: null,
    }
    expect(stock.stock_description).toBeUndefined()
  })
})
