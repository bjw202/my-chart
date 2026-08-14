// AC-SUX-061 / REQ-SUX-058 — 열 접기 순서 단일 상수 단위 테스트.
import { describe, it, expect } from 'vitest'
import { COLLAPSE_ORDER, INVARIANT_COLUMN_KEYS, hiddenColumnKeys } from '../stockTableColumns'

describe('AC-SUX-061 / REQ-SUX-058 — 열 접기 순서 (단일 상수)', () => {
  it('접기 순서가 섹터비중 → Vol배 → 52W고 다', () => {
    expect([...COLLAPSE_ORDER]).toEqual(['weight_in_sector', 'volume_ratio', 'near_52w_high'])
  })

  it('불변 열에 기간 3열·Stage·RS·Name 이 포함된다 (Lesson #3)', () => {
    const inv = new Set(INVARIANT_COLUMN_KEYS)
    expect(inv.has('name')).toBe(true)
    expect(inv.has('stage')).toBe(true)
    expect(inv.has('rs_12m')).toBe(true)
    expect(inv.has('chg_1w')).toBe(true)
    expect(inv.has('chg_1m')).toBe(true)
    expect(inv.has('chg_3m')).toBe(true)
  })

  it('불변 열은 어떤 접기 단계에서도 숨겨지지 않는다', () => {
    const inv = new Set(INVARIANT_COLUMN_KEYS)
    for (let level = 0; level <= COLLAPSE_ORDER.length; level++) {
      const hidden = hiddenColumnKeys(level)
      inv.forEach((k) => {
        expect(hidden.has(k)).toBe(false)
      })
    }
  })

  it('collapseLevel 0 → 숨김 없음 / 1 → 섹터비중 / 2 → +Vol배 / 3 → +52W고', () => {
    expect(hiddenColumnKeys(0).size).toBe(0)
    expect(hiddenColumnKeys(1).has('weight_in_sector')).toBe(true)
    expect(hiddenColumnKeys(2).has('volume_ratio')).toBe(true)
    expect(hiddenColumnKeys(2).has('weight_in_sector')).toBe(true)
    expect(hiddenColumnKeys(3).has('near_52w_high')).toBe(true)
    expect(hiddenColumnKeys(3).size).toBe(3)
  })
})
