// RED: SPEC-PRESET-001 AC-1 — 레지스트리 형상 단위 테스트 (Group A)
import { describe, it, expect } from 'vitest'
import { FILTER_PRESETS } from '../filter-presets'
import { isEqualScreenRequest, applyPatch } from '../utils'
import type { Preset } from '../../types/filter'
import { DEFAULT_SCREEN_REQUEST } from '../../types/filter'

describe('FILTER_PRESETS 레지스트리', () => {
  // A1: 정확히 3개 원소, id 목록 일치
  it('A1: 정확히 3개의 프리셋을 포함하며 id가 규격과 일치한다', () => {
    expect(FILTER_PRESETS).toHaveLength(3)
    const ids = FILTER_PRESETS.map((p) => p.id)
    expect(ids).toContain('minervini_full')
    expect(ids).toContain('breakout_init')
    expect(ids).toContain('stage1_accumulation')
  })

  // A2: 각 patch가 Partial<ScreenRequest>에 할당 가능 (applyPatch가 오류 없이 실행)
  it('A2: 각 프리셋의 patch를 applyPatch로 적용해도 오류가 없다', () => {
    for (const preset of FILTER_PRESETS) {
      expect(() => applyPatch(DEFAULT_SCREEN_REQUEST, preset.patch)).not.toThrow()
      const result = applyPatch(DEFAULT_SCREEN_REQUEST, preset.patch)
      // 결과는 ScreenRequest 구조를 유지해야 한다
      expect(result).toHaveProperty('patterns')
      expect(result).toHaveProperty('pattern_logic')
      expect(Array.isArray(result.patterns)).toBe(true)
    }
  })

  // A2: patterns 배열은 concat이 아니라 완전 치환 (A2 사용자 재승인)
  it('A2: breakout_init 적용 시 patterns가 완전 치환된다 (concat 아님)', () => {
    const breakout = FILTER_PRESETS.find((p) => p.id === 'breakout_init')!
    const baseWithPatterns = {
      ...DEFAULT_SCREEN_REQUEST,
      patterns: [{ indicator_a: 'Close' as const, operator: 'gt' as const, indicator_b: 'SMA200' as const, multiplier: 1.0 }],
    }
    const result = applyPatch(baseWithPatterns, breakout.patch)
    // breakout_init에는 3개 patterns가 정의됨 — 기존 1개와 concat되어 4개가 되어선 안 됨
    expect(result.patterns).toHaveLength(breakout.patch.patterns!.length)
  })

  // A3: id는 고유하고 label은 비어 있지 않다
  it('A3: 각 id는 고유하며 label은 비어 있지 않은 문자열이다', () => {
    const ids = FILTER_PRESETS.map((p) => p.id)
    const uniqueIds = new Set(ids)
    expect(uniqueIds.size).toBe(ids.length)

    for (const preset of FILTER_PRESETS) {
      expect(preset.label).toBeTruthy()
      expect(preset.label.length).toBeGreaterThan(0)
      expect(preset.description).toBeTruthy()
    }
  })

  // 타입 호환성: Preset 타입 배열임을 확인
  it('A1+: FILTER_PRESETS가 Preset 타입 배열이다', () => {
    const presets: readonly Preset[] = FILTER_PRESETS
    expect(presets).toBeDefined()
  })
})

// isEqualScreenRequest 유틸리티 테스트
describe('isEqualScreenRequest', () => {
  it('동일한 DEFAULT_SCREEN_REQUEST끼리는 true를 반환한다', () => {
    expect(isEqualScreenRequest(DEFAULT_SCREEN_REQUEST, DEFAULT_SCREEN_REQUEST)).toBe(true)
  })

  it('rs_min이 다르면 false를 반환한다', () => {
    const a = { ...DEFAULT_SCREEN_REQUEST, rs_min: 70 }
    const b = { ...DEFAULT_SCREEN_REQUEST, rs_min: 80 }
    expect(isEqualScreenRequest(a, b)).toBe(false)
  })

  it('markets 배열 길이가 다르면 false를 반환한다', () => {
    const a = { ...DEFAULT_SCREEN_REQUEST, markets: ['KOSPI' as const] }
    const b = { ...DEFAULT_SCREEN_REQUEST, markets: [] }
    expect(isEqualScreenRequest(a, b)).toBe(false)
  })

  // 커버리지 보강: 동일 길이 다른 내용 (utils.ts:57 요소 비교 분기)
  it('markets 배열 길이는 같지만 원소가 다르면 false를 반환한다', () => {
    const a = { ...DEFAULT_SCREEN_REQUEST, markets: ['KOSPI' as const] }
    const b = { ...DEFAULT_SCREEN_REQUEST, markets: ['KOSDAQ' as const] }
    expect(isEqualScreenRequest(a, b)).toBe(false)
  })

  it('sectors 배열 내용이 다르면 false를 반환한다', () => {
    const a = { ...DEFAULT_SCREEN_REQUEST, sectors: ['IT'] }
    const b = { ...DEFAULT_SCREEN_REQUEST, sectors: ['Finance'] }
    expect(isEqualScreenRequest(a, b)).toBe(false)
  })

  it('codes 배열 내용이 다르면 false를 반환한다', () => {
    const a = { ...DEFAULT_SCREEN_REQUEST, codes: ['005930'] }
    const b = { ...DEFAULT_SCREEN_REQUEST, codes: [] }
    expect(isEqualScreenRequest(a, b)).toBe(false)
  })

  // 커버리지 보강: 동일 길이 다른 내용 (utils.ts:69 요소 비교 분기)
  it('codes 배열 길이는 같지만 원소가 다르면 false를 반환한다', () => {
    const a = { ...DEFAULT_SCREEN_REQUEST, codes: ['005930'] }
    const b = { ...DEFAULT_SCREEN_REQUEST, codes: ['000660'] }
    expect(isEqualScreenRequest(a, b)).toBe(false)
  })

  it('patterns 배열 요소가 다르면 false를 반환한다', () => {
    const pattern = { indicator_a: 'Close' as const, operator: 'gt' as const, indicator_b: 'SMA50' as const, multiplier: 1.0 }
    const a = { ...DEFAULT_SCREEN_REQUEST, patterns: [pattern] }
    const b = { ...DEFAULT_SCREEN_REQUEST, patterns: [{ ...pattern, multiplier: 2.0 }] }
    expect(isEqualScreenRequest(a, b)).toBe(false)
  })

  it('동일한 patterns 배열이면 true를 반환한다', () => {
    const pattern = { indicator_a: 'Close' as const, operator: 'gt' as const, indicator_b: 'SMA50' as const, multiplier: 1.0 }
    const a = { ...DEFAULT_SCREEN_REQUEST, patterns: [pattern] }
    const b = { ...DEFAULT_SCREEN_REQUEST, patterns: [{ ...pattern }] }
    expect(isEqualScreenRequest(a, b)).toBe(true)
  })
})
