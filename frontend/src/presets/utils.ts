// SPEC-PRESET-001 프리셋 유틸리티 헬퍼
import type { PatternCondition, ScreenRequest } from '../types/filter'

// 지표명 → 한국어 라벨 매핑 (호버 툴팁 표시 전용; backend 식별자는 그대로 보존)
const INDICATOR_LABELS: Record<string, string> = {
  Close: '종가',
  Open: '시가',
  High: '고가',
  Low: '저가',
  EMA10: 'EMA10',
  EMA20: 'EMA20',
  SMA50: 'SMA50',
  SMA100: 'SMA100',
  SMA200: 'SMA200',
}

// 비교 연산자 → 수학 기호
const OPERATOR_SYMBOLS: Record<string, string> = {
  gt: '>',
  gte: '≥',
  lt: '<',
  lte: '≤',
}

/**
 * Preset의 patch를 사람이 읽기 쉬운 조건 문장 배열로 변환한다.
 * 프리셋 칩 호버 툴팁에서 "어떤 조건인지" 표시하는 용도.
 *
 * @param patch Preset.patch (Partial<ScreenRequest>)
 * @returns 사용자 친화적 한국어 조건 문장 배열 (빈 배열 가능)
 */
export function formatPresetConditions(
  patch: Partial<ScreenRequest>,
): string[] {
  const lines: string[] = []

  if (patch.minervini_trend_template === true) {
    lines.push('미너비니 추세 템플릿 통과')
  }
  if (patch.market_cap_min != null) {
    lines.push(`시가총액 ≥ ${patch.market_cap_min.toLocaleString()}억원`)
  }
  if (patch.rs_min != null) {
    lines.push(`RS 점수 ≥ ${patch.rs_min}`)
  }
  if (patch.chg_1d_min != null) {
    lines.push(`1일 수익률 ≥ ${patch.chg_1d_min}%`)
  }
  if (patch.chg_1w_min != null) {
    lines.push(`1주 수익률 ≥ ${patch.chg_1w_min}%`)
  }
  if (patch.chg_1m_min != null) {
    lines.push(`1개월 수익률 ≥ ${patch.chg_1m_min}%`)
  }
  if (patch.chg_3m_min != null) {
    lines.push(`3개월 수익률 ≥ ${patch.chg_3m_min}%`)
  }
  if (patch.patterns && patch.patterns.length > 0) {
    const logic = patch.pattern_logic === 'OR' ? '하나 이상 만족' : '모두 만족'
    lines.push(`패턴 (${logic}):`)
    for (const p of patch.patterns) {
      const a = INDICATOR_LABELS[p.indicator_a] ?? p.indicator_a
      const op = OPERATOR_SYMBOLS[p.operator] ?? p.operator
      const b = INDICATOR_LABELS[p.indicator_b] ?? p.indicator_b
      const mul = p.multiplier !== 1.0 ? ` × ${p.multiplier}` : ''
      lines.push(`  • ${a} ${op} ${b}${mul}`)
    }
  }

  return lines
}

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
