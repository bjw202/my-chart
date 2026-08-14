// AC-SUX-028 (REQ-SUX-026): formatWeeksSpan 단위 테스트 — 응답 값 그대로 표기(프론트 계산 금지).
import { describe, it, expect } from 'vitest'
import { formatWeeksSpan } from '../bumpFormat'

describe('AC-SUX-028 — formatWeeksSpan (응답 값 그대로 표기)', () => {
  it('weeks 와 span_days 를 병기한다 (12주 (84일))', () => {
    expect(formatWeeksSpan(12, 84)).toBe('12주 (84일)')
  })

  it('26주 선택 시에도 응답의 span_days 를 그대로 표기한다 (프론트가 26*7 계산 금지)', () => {
    // 응답이 span_days=182 를 주면 그대로 쓴다 (26*7=182 가 우연히 맞더라도 계산 금지)
    expect(formatWeeksSpan(26, 182)).toBe('26주 (182일)')
    // 응답이 영업일 기반이라 26*7 과 다른 값이라도 그대로 표기
    expect(formatWeeksSpan(26, 180)).toBe('26주 (180일)')
  })

  it('span_days 가 없으면 주수만 표기한다 (일수 계산 금지)', () => {
    expect(formatWeeksSpan(8, null)).toBe('8주')
    expect(formatWeeksSpan(8, undefined)).toBe('8주')
  })
})
