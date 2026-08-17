import { describe, it, expect } from 'vitest'
import { sectorKeyOf, buildCheckedGroups } from '../sectorKey'
import type { StockItem } from '../../../types/stock'

const stock = (overrides: Partial<StockItem> = {}): StockItem => ({
  code: '000000',
  name: '종목',
  market: 'KOSPI',
  market_cap: null,
  sector_major: null,
  sector_minor: null,
  product: null,
  close: null,
  change_1d: null,
  rs_12m: null,
  ema10: null,
  ema20: null,
  sma50: null,
  sma100: null,
  sma200: null,
  stage: null,
  ...overrides,
})

describe('sectorKeyOf', () => {
  it('major+minor → "major > minor" 조인 (공백 포함 byte-exact)', () => {
    expect(sectorKeyOf(stock({ sector_major: '내수', sector_minor: '리조트' }))).toBe('내수 > 리조트')
  })

  it('major 단독 → separator 없이 major만', () => {
    expect(sectorKeyOf(stock({ sector_major: '금융', sector_minor: null }))).toBe('금융')
  })

  it('sector_major null → "기타" 폴백', () => {
    expect(sectorKeyOf(stock({ sector_major: null, sector_minor: '은행' }))).toBe('기타 > 은행')
  })

  it('sector_major 빈 문자열 → "기타" 폴백', () => {
    expect(sectorKeyOf(stock({ sector_major: '', sector_minor: null }))).toBe('기타')
  })

  it('sector_minor null/빈 문자열 → major 단독 (빈 minor는 조인하지 않음)', () => {
    expect(sectorKeyOf(stock({ sector_major: '금융', sector_minor: null }))).toBe('금융')
    expect(sectorKeyOf(stock({ sector_major: '금융', sector_minor: '' }))).toBe('금융')
  })
})

describe('buildCheckedGroups', () => {
  it('삽입 순서와 무관하게 key 코드포인트 오름차순으로 그룹 정렬', () => {
    // 삽입 순: 반도체, AI, 가스, 반도체>메모리 — ASCII 'AI'(U+0041)가 한글보다 작음
    const stocks = [
      stock({ code: 'A1', name: '반도체주', sector_major: '반도체' }),
      stock({ code: 'A2', name: 'AI주', sector_major: 'AI' }),
      stock({ code: 'A3', name: '가스주', sector_major: '가스' }),
      stock({ code: 'A4', name: '메모리주', sector_major: '반도체', sector_minor: '메모리' }),
    ]
    const groups = buildCheckedGroups(stocks)
    expect(groups.map((g) => g.sectorName)).toEqual(['AI', '가스', '반도체', '반도체 > 메모리'])
  })

  it('같은 key는 하나의 그룹으로 병합, 그룹 내 삽입 순서 보존', () => {
    const stocks = [
      stock({ code: 'B1', sector_major: '가스' }),
      stock({ code: 'B2', sector_major: 'AI' }),
      stock({ code: 'B3', sector_major: '가스' }),
    ]
    const groups = buildCheckedGroups(stocks)
    expect(groups).toHaveLength(2)
    const gas = groups.find((g) => g.sectorName === '가스')
    expect(gas?.stocks.map((s) => s.code)).toEqual(['B1', 'B3'])
  })

  it('합 불변식: Σ group.stocks.length === 입력 길이 (유실/중복 없음)', () => {
    const stocks = [
      stock({ code: 'C1', sector_major: '반도체', sector_minor: '메모리' }),
      stock({ code: 'C2', sector_major: '반도체', sector_minor: '메모리' }),
      stock({ code: 'C3', sector_major: null, sector_minor: null }),
      stock({ code: 'C4', sector_major: '금융', sector_minor: '' }),
    ]
    const groups = buildCheckedGroups(stocks)
    expect(groups.reduce((acc, g) => acc + g.stocks.length, 0)).toBe(stocks.length)
    // 중복 없음: 모든 code가 정확히 1회 등장
    const codes = groups.flatMap((g) => g.stocks.map((s) => s.code)).sort()
    expect(codes).toEqual(['C1', 'C2', 'C3', 'C4'])
  })

  it('빈 입력 → 빈 배열', () => {
    expect(buildCheckedGroups([])).toEqual([])
  })
})
