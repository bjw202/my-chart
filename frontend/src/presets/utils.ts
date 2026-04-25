// SPEC-PRESET-001 프리셋 유틸리티 헬퍼
import type { PatternCondition, ScreenRequest } from '../types/filter'

// @MX:NOTE: [AUTO] applyPatch — DEFAULT_SCREEN_REQUEST 기반 얕은 병합 적용기
// @MX:REASON: patterns 배열은 얕은 병합으로는 전체 치환이 불가능하므로 명시적 분기 필요 (A2 사용자 재승인 2026-04-21)
// @MX:SPEC: SPEC-PRESET-001 A2, §4.3
export function applyPatch(
  base: ScreenRequest,
  patch: Partial<ScreenRequest>,
): ScreenRequest {
  return {
    ...base,
    ...patch,
    patterns: patch.patterns !== undefined ? patch.patterns : base.patterns,
  }
}

function isEqualPattern(a: PatternCondition, b: PatternCondition): boolean {
  return (
    a.indicator_a === b.indicator_a &&
    a.operator === b.operator &&
    a.indicator_b === b.indicator_b &&
    a.multiplier === b.multiplier
  )
}

function arrayEq<T>(
  a: readonly T[],
  b: readonly T[],
  eq: (x: T, y: T) => boolean = Object.is,
): boolean {
  if (a.length !== b.length) return false
  for (let i = 0; i < a.length; i++) {
    if (!eq(a[i], b[i])) return false
  }
  return true
}

/**
 * 두 ScreenRequest가 깊은 동등인지 비교한다.
 * 드리프트 감지에서 activePresetId 파생에 사용된다 (REQ-PST-006, A3).
 */
export function isEqualScreenRequest(a: ScreenRequest, b: ScreenRequest): boolean {
  if (
    a.market_cap_min !== b.market_cap_min ||
    a.chg_1d_min !== b.chg_1d_min ||
    a.chg_1w_min !== b.chg_1w_min ||
    a.chg_1m_min !== b.chg_1m_min ||
    a.chg_3m_min !== b.chg_3m_min ||
    a.pattern_logic !== b.pattern_logic ||
    a.rs_min !== b.rs_min ||
    a.minervini_trend_template !== b.minervini_trend_template
  ) {
    return false
  }
  return (
    arrayEq(a.markets, b.markets) &&
    arrayEq(a.sectors, b.sectors) &&
    arrayEq(a.codes, b.codes) &&
    arrayEq(a.patterns, b.patterns, isEqualPattern)
  )
}
