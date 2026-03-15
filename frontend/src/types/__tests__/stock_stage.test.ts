// RED: Tests for R2 - StockItem.stage field
import { describe, it, expect } from 'vitest'
import type { StockItem } from '../stock'

describe('StockItem.stage field', () => {
  it('should accept stage as null', () => {
    const stock: StockItem = {
      code: '005930',
      name: '삼성전자',
      market: 'KOSPI',
      market_cap: 3000000,
      sector_major: '전기전자',
      sector_minor: '반도체',
      product: null,
      close: 70000,
      change_1d: 1.5,
      rs_12m: 85,
      ema10: 68000,
      ema20: 67000,
      sma50: 65000,
      sma100: 62000,
      sma200: 60000,
      stage: null,
    }
    expect(stock.stage).toBeNull()
  })

  it('should accept stage as valid Weinstein stage number (1-4)', () => {
    const stock: StockItem = {
      code: '005930',
      name: '삼성전자',
      market: 'KOSPI',
      market_cap: 3000000,
      sector_major: '전기전자',
      sector_minor: '반도체',
      product: null,
      close: 70000,
      change_1d: 1.5,
      rs_12m: 85,
      ema10: 68000,
      ema20: 67000,
      sma50: 65000,
      sma100: 62000,
      sma200: 60000,
      stage: 2,
    }
    expect(stock.stage).toBe(2)
  })
})
