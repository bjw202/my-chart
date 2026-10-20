// SPEC-RS-REBALANCE-001 M5 — AC-RSR-011 (REQ-RSR-015·016·022) 열기 배지 술어 단위 명세.
// 술어는 임계값을 인자로 받는다 — 호출부가 RS_TOP_THRESHOLD 를 넘겨야 상수 교체가 배지를 움직인다
// (상수 주입 대조는 rsHeat.injected.test.tsx 가 컴포넌트 렌더로 검증한다).
import { describe, it, expect } from 'vitest'
import { RS_TOP_THRESHOLD, isRsHeat, rsHeatTitle } from '../rsMetrics'

describe('isRsHeat — rs_1m >= RS_TOP_THRESHOLD (AC-RSR-011)', () => {
  it('RS_TOP_THRESHOLD 는 80 으로 유지된다 (REQ-RSR-022)', () => {
    expect(RS_TOP_THRESHOLD).toBe(80)
  })

  it('경계 사례: 79.99 → 없음, 80 → 있음, 80.01 → 있음', () => {
    expect(isRsHeat(79.99, RS_TOP_THRESHOLD)).toBe(false)
    expect(isRsHeat(80, RS_TOP_THRESHOLD)).toBe(true)
    expect(isRsHeat(80.01, RS_TOP_THRESHOLD)).toBe(true)
  })

  it('결측(null/undefined)은 배지 없음 — 높은 값으로 메우지 않는다', () => {
    expect(isRsHeat(null, RS_TOP_THRESHOLD)).toBe(false)
    expect(isRsHeat(undefined, RS_TOP_THRESHOLD)).toBe(false)
  })

  it('title 은 넘겨받은 임계값을 문자열로 담는다 (REQ-RSR-016)', () => {
    expect(rsHeatTitle(RS_TOP_THRESHOLD)).toContain(String(RS_TOP_THRESHOLD))
    expect(rsHeatTitle(85)).toContain('85')
  })
})
