// AC-SUX-038 (REQ-SUX-035/036, 규칙 VZ-1) — 버블 크기 면적 비례 + 로그 정규화 단위 테스트
// 공용 유틸 bubbleRadius/bubbleSymbolSize 가 plan §3.2 공식과 일치하는지 검증.
import { describe, it, expect } from 'vitest'
import {
  bubbleRadius,
  bubbleSymbolSize,
  sizeLegendRefs,
  PERIOD_SIZE_LADDER,
  SECTOR_BUBBLE_R_MIN,
  SECTOR_BUBBLE_R_MAX,
  STOCK_BUBBLE_R_MIN,
  STOCK_BUBBLE_R_MAX,
} from '../bubbleRadius'

describe('AC-SUX-038 — 버블 크기: 면적 비례 + 로그 정규화 (VZ-1)', () => {
  it('최소값 버블 지름 = 2×r_min, 최대값 버블 지름 = 2×r_max', () => {
    // 섹터 버블 [14, 68], 종목 버블 [10, 52]
    const sMin = bubbleSymbolSize(PERIOD_SIZE_LADDER['1w'].vMin, PERIOD_SIZE_LADDER['1w'].vMin, PERIOD_SIZE_LADDER['1w'].vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    const sMax = bubbleSymbolSize(PERIOD_SIZE_LADDER['1w'].vMax, PERIOD_SIZE_LADDER['1w'].vMin, PERIOD_SIZE_LADDER['1w'].vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    expect(sMin).toBeCloseTo(2 * SECTOR_BUBBLE_R_MIN, 10) // 14
    expect(sMax).toBeCloseTo(2 * SECTOR_BUBBLE_R_MAX, 10) // 68

    const kMin = bubbleSymbolSize(PERIOD_SIZE_LADDER['1w'].vMin, PERIOD_SIZE_LADDER['1w'].vMin, PERIOD_SIZE_LADDER['1w'].vMax, STOCK_BUBBLE_R_MIN, STOCK_BUBBLE_R_MAX)
    const kMax = bubbleSymbolSize(PERIOD_SIZE_LADDER['1w'].vMax, PERIOD_SIZE_LADDER['1w'].vMin, PERIOD_SIZE_LADDER['1w'].vMax, STOCK_BUBBLE_R_MIN, STOCK_BUBBLE_R_MAX)
    expect(kMin).toBeCloseTo(2 * STOCK_BUBBLE_R_MIN, 10) // 10
    expect(kMax).toBeCloseTo(2 * STOCK_BUBBLE_R_MAX, 10) // 52
  })

  it('섹터 버블 지름은 [14, 68], 종목 버블 지름은 [10, 52] 범위에 든다', () => {
    const { vMin, vMax } = PERIOD_SIZE_LADDER['1m']
    // 사다리 내 임의값 + 사다리 밖 초과값(클램프)
    for (const v of [vMin, 5e11, vMax, 1e20]) {
      const s = bubbleSymbolSize(v, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
      expect(s).toBeGreaterThanOrEqual(2 * SECTOR_BUBBLE_R_MIN)
      expect(s).toBeLessThanOrEqual(2 * SECTOR_BUBBLE_R_MAX)
      const k = bubbleSymbolSize(v, vMin, vMax, STOCK_BUBBLE_R_MIN, STOCK_BUBBLE_R_MAX)
      expect(k).toBeGreaterThanOrEqual(2 * STOCK_BUBBLE_R_MIN)
      expect(k).toBeLessThanOrEqual(2 * STOCK_BUBBLE_R_MAX)
    }
  })

  it('symbolSize = 2×sqrt(r_min² + u×(r_max² − r_min²)) — 공식과 정확히 일치 (섹터 중간값)', () => {
    // 1W 사다리, 중간 참조값 1e11 → u = ln(1e11/1e10) = 0.5 (로그 스케일)
    const { vMin, vMax } = PERIOD_SIZE_LADDER['1w']
    const v = 1e11
    const lo = Math.log(vMin + 1)
    const hi = Math.log(vMax + 1)
    const u = (Math.log(v + 1) - lo) / (hi - lo)
    const expectedR = Math.sqrt(SECTOR_BUBBLE_R_MIN ** 2 + u * (SECTOR_BUBBLE_R_MAX ** 2 - SECTOR_BUBBLE_R_MIN ** 2))
    expect(bubbleRadius(v, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)).toBeCloseTo(expectedR, 10)
    expect(bubbleSymbolSize(v, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)).toBeCloseTo(2 * expectedR, 10)
  })

  it('중간값 버블이 최소 크기 근처에 뭉치지 않는다 — 선형 정규화 결과와 다름을 대조 단언', () => {
    // 동일 u=0.5 지점에서 로그(면적비례) vs 선형(지름비례) 결과가 다르다.
    // 선형: 2×(rMin + u×(rMax − rMin))  /  로그: 2×sqrt(rMin² + u×(rMax² − rMin²))
    const { vMin, vMax } = PERIOD_SIZE_LADDER['3m']
    const v = 1e12 // 3M 중간 참조값 → u = 0.5
    const logDiameter = bubbleSymbolSize(v, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    const u = 0.5
    const linearDiameter = 2 * (SECTOR_BUBBLE_R_MIN + u * (SECTOR_BUBBLE_R_MAX - SECTOR_BUBBLE_R_MIN))
    // 로그 면적비례가 선형보다 크다 → 최소 근처 뭉침 해소
    expect(logDiameter).toBeGreaterThan(linearDiameter)
    // 최소 지름(14)에서 유의미하게 떨어져 있다
    expect(logDiameter - 2 * SECTOR_BUBBLE_R_MIN).toBeGreaterThan(10)
  })

  it('v_max === v_min 이면 u = 0.5 — 모든 버블이 동일 중간 크기', () => {
    // 단일 버블 데이터(E4) 케이스: vMin==vMax → u=0.5 → 모든 v 가 동일 r
    const same = 1e11
    const rA = bubbleRadius(1e10, same, same, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    const rB = bubbleRadius(1e13, same, same, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    expect(rA).toBe(rB) // 결정성: v 무관 동일
    const expectedMid = Math.sqrt((SECTOR_BUBBLE_R_MIN ** 2 + SECTOR_BUBBLE_R_MAX ** 2) / 2)
    expect(rA).toBeCloseTo(expectedMid, 10)
  })

  it('결측 거래대금(null) → 최소 지름(2×r_min), NaN 도 동일', () => {
    const { vMin, vMax } = PERIOD_SIZE_LADDER['1w']
    expect(bubbleSymbolSize(null, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)).toBe(2 * SECTOR_BUBBLE_R_MIN)
    expect(bubbleSymbolSize(Number.NaN, vMin, vMax, STOCK_BUBBLE_R_MIN, STOCK_BUBBLE_R_MAX)).toBe(2 * STOCK_BUBBLE_R_MIN)
  })

  it('사다리 밖 값은 vMin/vMax 로 클램프 — symbolSize 는 경계값, 툴팁은 실제값 (AC-SUX-039 클램프)', () => {
    const { vMin, vMax } = PERIOD_SIZE_LADDER['1w']
    const overClamped = bubbleSymbolSize(1e20, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    const atMax = bubbleSymbolSize(vMax, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    const underClamped = bubbleSymbolSize(1, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    const atMin = bubbleSymbolSize(vMin, vMin, vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    expect(overClamped).toBeCloseTo(atMax, 10)
    expect(underClamped).toBeCloseTo(atMin, 10)
  })
})

describe('AC-SUX-039 — 크기 범례 참조값 (VZ-2, O-U4 기간별 고정 눈금)', () => {
  it('기간별 참조값 3개가 리터럴과 정확히 일치 (데이터 무관)', () => {
    expect(PERIOD_SIZE_LADDER['1w'].refs).toEqual([1e10, 1e11, 1e12])   // 100억/1000억/1조
    expect(PERIOD_SIZE_LADDER['1m'].refs).toEqual([5e10, 5e11, 5e12])   // 500억/5000억/5조
    expect(PERIOD_SIZE_LADDER['3m'].refs).toEqual([1e11, 1e12, 1e13])   // 1000억/1조/10조
  })

  it('sizeLegendRefs 가 3개 참조버블 [값, 지름] 을 반환 — 최소/최대 지름이 사다리 양끝', () => {
    const refs = sizeLegendRefs('1w', SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    expect(refs).toHaveLength(3)
    expect(refs[0].value).toBe(1e10)
    expect(refs[2].value).toBe(1e12)
    expect(refs[0].diameter).toBeCloseTo(2 * SECTOR_BUBBLE_R_MIN, 10) // 14
    expect(refs[2].diameter).toBeCloseTo(2 * SECTOR_BUBBLE_R_MAX, 10) // 68
    // 중간 참조버블 지름이 양끝 사이
    expect(refs[1].diameter).toBeGreaterThan(refs[0].diameter)
    expect(refs[1].diameter).toBeLessThan(refs[2].diameter)
  })

  it('기간별 고정 눈금 — 거래대금 분포가 달라도 참조값 3개는 동일 (데이터 적응형이면 실패)', () => {
    // 이 단언은 sizeLegendRefs 가 PERIOD_SIZE_LADDER 상수만 읽고 데이터를 보지 않음을 고정.
    const a = sizeLegendRefs('3m', SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    const b = sizeLegendRefs('3m', SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
    expect(a.map(r => r.value)).toEqual(b.map(r => r.value))
    expect(a.map(r => r.value)).toEqual([1e11, 1e12, 1e13])
  })
})
