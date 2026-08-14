// RED: Tests for market types - verifying type structure (AC-SUX-004 / AC-SUX-006, M3)
import { describe, it, expect } from 'vitest'
import type { TabId, NavIntent, NavIntentPayload, MarketOverviewResponse, SectorRankingResponse, SectorRankItem } from '../market'

describe('TabId type', () => {
  it('should accept valid tab ids', () => {
    // Type-level test: these assignments should compile
    const tabs: TabId[] = ['market-overview', 'sector-analysis', 'stock-explorer', 'chart-grid']
    expect(tabs).toHaveLength(4)
  })
})

describe('NavIntent type contract (AC-SUX-004 (b) / AC-SUX-006)', () => {
  it('payload shall define subTab, stockCodes, focusStock', () => {
    const payload: NavIntentPayload = { subTab: 'bubble', stockCodes: ['005930', '000660'], focusStock: '삼성전자' }
    expect(payload.subTab).toBe('bubble')
    expect(payload.stockCodes).toEqual(['005930', '000660'])
    expect(payload.focusStock).toBe('삼성전자')
  })

  it('all payload fields are optional', () => {
    const payload: NavIntentPayload = {}
    expect(payload).toBeDefined()
  })

  it('NavIntent carries id (monotonic), target, payload', () => {
    const intent: NavIntent = { id: 7, target: 'stock-explorer', payload: { focusStock: '삼성전자' } }
    expect(intent.id).toBe(7)
    expect(intent.target).toBe('stock-explorer')
    expect(intent.payload.focusStock).toBe('삼성전자')
  })

  it('payload shall NOT carry sectorName (AC-SUX-006, type-level)', () => {
    // sectorName is intentionally absent from NavIntentPayload — sector selection
    // is written directly to SelectionContext (REQ-SUX-005 / SM-4).
    // @ts-expect-error sectorName is NOT a NavIntent payload field
    const bad: NavIntentPayload = { sectorName: '반도체' }
    expect(bad).toBeDefined()
  })
})

describe('MarketOverviewResponse', () => {
  it('should have kospi, kosdaq, breadth, cycle, breadth_history fields', () => {
    const mock: MarketOverviewResponse = {
      kospi: { close: 2700, chg_1w: 1.5, sma50: 2650, sma200: 2600, sma50_slope: 0.1, sma200_slope: 0.05 },
      kosdaq: { close: 850, chg_1w: -0.5, sma50: 840, sma200: 820, sma50_slope: -0.02, sma200_slope: 0.01 },
      breadth: {
        kospi: { pct_above_sma50: 65, pct_above_sma200: 72, nh_nl_ratio: 1.5, nh_nl_diff: 50, ad_ratio: 0.6, breadth_score: 70 },
        kosdaq: { pct_above_sma50: 55, pct_above_sma200: 60, nh_nl_ratio: 1.2, nh_nl_diff: 30, ad_ratio: 0.55, breadth_score: 58 },
      },
      cycle: { phase: 'bull', choppy: false, criteria: [{ name: 'SMA50', value: '2650', signal: 'bullish' }], confidence: 0.8 },
      breadth_history: [{ date: '2025-01-01', pct_above_sma50: 60, nh_nl_ratio: 1.3, breadth_score: 65 }],
    }
    expect(mock.cycle.phase).toBe('bull')
    expect(mock.kospi.close).toBe(2700)
  })

  it('should allow bear and sideways phases', () => {
    const bearPhase: MarketOverviewResponse['cycle']['phase'] = 'bear'
    const sidewaysPhase: MarketOverviewResponse['cycle']['phase'] = 'sideways'
    expect(bearPhase).toBe('bear')
    expect(sidewaysPhase).toBe('sideways')
  })
})

describe('SectorRankItem', () => {
  it('should have all required rank fields', () => {
    const item: SectorRankItem = {
      name: 'IT',
      stock_count: 50,
      returns: { w1: 1.5, m1: 3.0, m3: 8.0 },
      excess_returns: { w1: 0.5, m1: 1.0, m3: 2.0 },
      rs_avg: 75,
      rs_top_pct: 60,
      nh_pct: 30,
      stage2_pct: 50,
      composite_score: 80,
      rank: 1,
      rank_change: 2,
    }
    expect(item.rank).toBe(1)
    expect(item.composite_score).toBe(80)
  })
})

describe('SectorRankingResponse', () => {
  it('should have date and sectors array', () => {
    const mock: SectorRankingResponse = {
      date: '2025-01-01',
      sectors: [],
    }
    expect(mock.date).toBe('2025-01-01')
    expect(Array.isArray(mock.sectors)).toBe(true)
  })
})
