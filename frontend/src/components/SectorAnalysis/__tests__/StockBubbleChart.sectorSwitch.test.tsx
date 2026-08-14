// RED: 섹터를 바꿔도 이전 섹터의 버블이 차트에 남는 결함.
// echarts-for-react 는 notMerge 를 넘기지 않으면 setOption 이 기존 option 에 병합되고,
// series 는 인덱스로 병합되므로 이전 섹터의 series 개수가 더 많으면 남는 series 가
// 그대로 살아남는다(사용자 보고: "기계 섹터 한 번 갔다 오면 혜인이 뜬다").
//
// 주의: 다른 StockBubbleChart 테스트처럼 echarts-for-react 를 mock 하면 option prop 만
// 캡처하게 되어 setOption 의 병합 의미론을 관측할 수 없다 — 수정 전에도 통과하는
// 무의미한 가드가 된다. 그래서 여기서는 실제 ECharts 가 그린 SVG 를 읽는다.
// (실 인스턴스 getOption() 은 쓸 수 없다. vitest 에서 echarts-for-react 는 CJS 빌드를,
//  테스트의 import 는 ESM 빌드를 잡아 인스턴스 레지스트리가 갈린다.)
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, act, cleanup } from '@testing-library/react'
import type { StockBubbleItem } from '../../../types/bubble'
import { StockBubbleChart } from '../StockBubbleChart'

function stock(name: string, minor: string, tradingValue: number): StockBubbleItem {
  return {
    name, sector_minor: minor,
    price_change: 1, rs_12m: 50, trading_value: tradingValue,
    stage: 2, stage_detail: 'stage2',
    market_cap: 1_000_000_000, volume_ratio: 1, product: null,
  }
}

// 기계 섹터 — 중분류 3개
const MACHINERY: StockBubbleItem[] = [
  stock('혜인', '건설기계', 9_000_000_000),
  stock('대동', '농기계', 8_000_000_000),
  stock('대동기어', '기계부품', 7_000_000_000),
]

// 스마트폰 섹터 — 중분류 2개(기계 섹터와 완전히 서로소, series 수가 더 적다)
const SMARTPHONE: StockBubbleItem[] = [
  stock('엘앤에프', '스마트폰_부품', 6_000_000_000),
  stock('엠씨넥스', '카메라_모듈', 5_000_000_000),
]

// 차트가 실제로 그린 텍스트(종목 라벨·범례·축)
function drawnText(root: HTMLElement): string[] {
  return [...root.querySelectorAll('text')].map((t) => t.textContent ?? '')
}

// ECharts 는 다음 프레임에 그린다 — 렌더 후 잠시 흘려보낸다.
async function settle(): Promise<void> {
  await act(async () => { await new Promise((r) => setTimeout(r, 100)) })
}

beforeEach(() => {
  // jsdom 은 matchMedia 를 지원하지 않는다(useMediaQuery 의존).
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
    matches: false, media: '(min-width: 768px)', onchange: null,
    addEventListener: vi.fn(), removeEventListener: vi.fn(),
    addListener: vi.fn(), removeListener: vi.fn(), dispatchEvent: vi.fn(),
  }))
  // jsdom 은 레이아웃이 없어 ECharts 가 크기를 얻지 못한다 — init 이 성립하도록 크기를 준다.
  Object.defineProperty(HTMLElement.prototype, 'clientWidth', { configurable: true, value: 800 })
  Object.defineProperty(HTMLElement.prototype, 'clientHeight', { configurable: true, value: 500 })
})
afterEach(() => cleanup())

describe('섹터 전환 시 이전 섹터 버블 잔존', () => {
  it('기계 → 스마트폰 전환 후 기계 종목이 차트에 남지 않는다', async () => {
    const { container, rerender } = render(
      <StockBubbleChart stocks={MACHINERY} sectorName="기계" period="1m" />,
    )
    await settle()
    expect(drawnText(container)).toEqual(expect.arrayContaining(['혜인', '대동', '대동기어']))

    rerender(<StockBubbleChart stocks={SMARTPHONE} sectorName="스마트폰" period="1m" />)
    await settle()

    const drawn = drawnText(container)
    // 새 섹터 종목은 그려져야 한다.
    expect(drawn).toEqual(expect.arrayContaining(['엘앤에프', '엠씨넥스']))
    // 이전 섹터 종목은 하나도 남으면 안 된다.
    expect(drawn).not.toContain('혜인')
    expect(drawn).not.toContain('대동')
    expect(drawn).not.toContain('대동기어')
    // 범례도 새 섹터의 중분류만 남는다.
    expect(drawn).not.toContain('건설기계')
    expect(drawn).not.toContain('농기계')
    expect(drawn).not.toContain('기계부품')
  })
})
