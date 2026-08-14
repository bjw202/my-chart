// AC-SUX-044/045/046 — RRGChart M5 (사분면 라벨·자동 축·궤적/벤치마크)
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, cleanup, waitFor } from '@testing-library/react'
import { rrgHalf, RRGChart } from '../RRGChart'
import type { RRGResponse } from '../../../types/rrg'
// 소스 정적 스캔용 raw import (node:fs/require 미사용 — tsc NEW-0 유지)
import rrgSrc from '../RRGChart.tsx?raw'

// AC-SUX-045 — rrgHalf 순수 함수 (plan §3.3 / VZ-8 리터럴 고정)
describe('AC-SUX-045 — RRG 축 자동 대칭 반폭 (VZ-8)', () => {
  it('maxDev=11 → half=13 (min=87, max=113), 100이 정확히 중앙', () => {
    const half = rrgHalf(11)
    expect(half).toBe(13)
    expect(100 - half).toBe(87)
    expect(100 + half).toBe(113)
  })
  it('경계 케이스 리터럴: =10→11, =4→5(최소반폭), =0→5', () => {
    expect(rrgHalf(10)).toBe(11)
    expect(rrgHalf(4)).toBe(5)
    expect(rrgHalf(0)).toBe(5)
  })
  it('모든 점이 100에 근접(maxDev=0.3) → half=5 (과확대 방지)', () => {
    expect(rrgHalf(0.3)).toBe(5)
  })
  it('대조 단언 — ×1.1 계수 또는 max(5,…) 하한 제거 시 최소 1건 실패', () => {
    // ×1.1 제거: rrgHalf(11) 이 13 이 아닌 11(or ceil(11)=11) → 13 단언 실패
    const noCoeff = (d: number) => Math.max(5, Math.ceil(d))
    expect(noCoeff(11)).not.toBe(13)
    // max(5,…) 하한 제거: rrgHalf(4) 가 5 가 아닌 5(ceil(4.4)=5)... 4→ ceil(4.4)=5 동일; 0→0 실패
    const noFloor = (d: number) => Math.ceil(d * 1.1)
    expect(noFloor(0)).not.toBe(5) // 0 이 됨 → 최소반폭 위반
  })
  it('min:75/max:125 하드코딩 부재 (grep)', () => {
    // AC-SUX-045: grep "min: 75|max: 125" RRGChart.tsx → 0행
    expect(rrgSrc.match(/min: 75|max: 125/)).toBeNull()
  })
})

// 컴포넌트 테스트용 fixture + mock
const fixture: RRGResponse = {
  date: '2026-08-14',
  sectors: [
    { name: '반도체', rs_ratio: 108, rs_momentum: 112, quadrant: 'leading',
      trail: Array.from({ length: 10 }, (_, i) => ({ date: `2026-W${i + 1}`, rs_ratio: 100 + i, rs_momentum: 100 + i })) },
    { name: '디스플레이', rs_ratio: 95, rs_momentum: 90, quadrant: 'lagging',
      trail: Array.from({ length: 10 }, (_, i) => ({ date: `2026-W${i + 1}`, rs_ratio: 100 - i, rs_momentum: 100 - i })) },
  ],
  kospi: Array.from({ length: 10 }, (_, i) => ({ date: `2026-W${i + 1}`, close: 2000 + i * 10 })),
}

let mockMarket = 'all'
vi.mock('echarts-for-react', () => ({
  default: vi.fn(() => null),
}))
vi.mock('../../../api/rrg', () => ({
  fetchRRGData: vi.fn(async (): Promise<RRGResponse> => fixture),
}))
vi.mock('../../../contexts/AnalysisParamsContext', () => ({
  useAnalysisParams: () => ({ market: mockMarket, period: '1m', setMarket: () => {}, setPeriod: () => {} }),
  AnalysisParamsProvider: ({ children }: { children: React.ReactNode }) => children,
}))

beforeEach(() => { mockMarket = 'all' })
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('AC-SUX-044 — 사분면 라벨 의미 + 기준선 고지 (VZ-7)', () => {
  it('기준선 100 = 벤치마크(전체 상한가중) 상설 라인이 렌더 (market=all)', async () => {
    const { findByTestId } = render(<RRGChart />)
    const legend = await findByTestId('rrg-baseline-legend')
    expect(legend.textContent).toContain('기준선 100 = 벤치마크(전체 상한가중)와 동일 성과')
    // ② O-A1 발산 고지
    expect(legend.textContent).toContain('롤링 정규화 미적용')
  })
  it('market=kospi → 벤치마크 이름 KOSPI 추종', async () => {
    mockMarket = 'kospi'
    const { findByTestId } = render(<RRGChart />)
    const legend = await findByTestId('rrg-baseline-legend')
    expect(legend.textContent).toContain('KOSPI')
  })
})

describe('AC-SUX-046 — 궤적 시작·벤치마크 추종 (VZ-9/VZ-10)', () => {
  it('스파크라인 헤더에 lookback(8주) + 궤적 시작일 + 벤치마크 이름 포함', async () => {
    render(<RRGChart />)
    await waitFor(() => {
      // 벤치마크 이름(전체 상한가중) + 8주 lookback + 궤적 시작(첫 trail 날짜)
      expect(document.querySelector('.rrg-sparkline-title')?.textContent).toContain('전체 상한가중')
      expect(document.querySelector('.rrg-sparkline-title')?.textContent).toContain('8주 lookback')
      expect(document.querySelector('.rrg-sparkline-title')?.textContent).toContain('궤적 시작')
    })
  })
  it('KOSPI 하드코딩(label site) 부재 — grep "KOSPI (" 패턴 0행 (map 값은 제외)', () => {
    // 스파크라인 타이틀의 옛 고정 라벨 패턴 "KOSPI (" 는 소스에 없어야 함
    expect(rrgSrc.match(/KOSPI \(/)).toBeNull()
  })
})
