// RED: Tests for market types - verifying type structure and TabId constraints
import { describe, it, expect } from 'vitest'
import type { TabId, CrossTabParams, MarketOverviewResponse, SectorRankingResponse, SectorRankItem } from '../market'

describe('TabId type', () => {
  it('should accept valid tab ids', () => {
    // Type-level test: these assignments should compile
    const tabs: TabId[] = ['market-overview', 'sector-analysis', 'stock-explorer', 'chart-grid']
    expect(tabs).toHaveLength(4)
  })
})

describe('CrossTabParams', () => {
  it('should allow optional sectorName and stockCodes', () => {
    const params: CrossTabParams = {}
    expect(params).toBeDefined()
  })

  it('should accept sectorName', () => {
    const params: CrossTabParams = { sectorName: 'IT' }
    expect(params.sectorName).toBe('IT')
  })

  it('should accept stockCodes', () => {
    const params: CrossTabParams = { stockCodes: ['005930', '000660'] }
    expect(params.stockCodes).toEqual(['005930', '000660'])
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
