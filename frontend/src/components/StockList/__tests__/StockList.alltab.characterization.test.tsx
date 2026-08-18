/**
 * StockList 전체(all) 탭 characterization 테스트 — SPEC-CHECKED-SECTOR-GROUP-001 M0
 *
 * M0는 그룹핑 기능 구현 이전, 손대지 않은 트리의 현재 동작을 고정하는 것이 목적.
 * viewMode 'all'의 flatItems = results.sectors 순서대로 섹터 헤더(40px) + 종목 행(56px).
 * jsdom에서 listHeight는 600(useState 초기값, ResizeObserver stub) + overscanCount 5이므로
 * 픽스처 총 아이템 수(헤더 3 + 종목 7 = 10 ≤ 15)는 전부 렌더됨이 보장된다.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import type { StockItem } from '../../../types/stock'

// ── 의존성 모킹: StockList가 소비하는 context/hook만 최소 모킹 ──
// (WatchlistContext는 실 Provider로 감싸 실동작 사용)

vi.mock('../../../contexts/ScreenContext', () => ({
  useScreen: vi.fn(),
}))

vi.mock('../../../contexts/NavigationContext', () => ({
  useNavigation: vi.fn(() => ({ selectedIndex: -1 })),
}))

// 키보드 내비게이션 구독 부수효과 제거
vi.mock('../../../hooks/useStockNavigation', () => ({
  useStockNavigation: vi.fn(),
}))

vi.mock('../../../hooks/useScrollSync', () => ({
  useScrollSync: vi.fn(() => ({ onStockSelect: vi.fn() })),
}))

import { StockList } from '../StockList'
import { WatchlistProvider } from '../../../contexts/WatchlistContext'
import { useScreen } from '../../../contexts/ScreenContext'

const mockUseScreen = vi.mocked(useScreen)

// ── 픽스처 ──

function makeStock(
  code: string,
  name: string,
  sectorMajor: string | null,
  sectorMinor: string | null,
): StockItem {
  return {
    code,
    name,
    market: 'KOSPI',
    market_cap: null,
    sector_major: sectorMajor,
    sector_minor: sectorMinor,
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
  }
}

// 섹터 그룹 3종 — (a) major+minor 모두 있음, (b) major만 있음, (c) sector_major null → '기타' 그룹.
// 그룹핑 자체는 upstream(results.sectors 생성)에서 일어나므로 픽스처는 그룹화된 결과를 반영.
// (a)의 stock_count(27)는 stocks.length(3)와 다르게 두어, 헤더 카운트가 렌더 행 수가 아니라
// 그룹 유니버스 수(sector.stock_count)임을 구분 가능하게 한다.
const results = {
  sectors: [
    {
      sector_name: '반도체',
      stock_count: 27,
      stocks: [
        makeStock('005930', '삼성전자', '테크놀로지', '반도체'),
        makeStock('000660', 'SK하이닉스', '테크놀로지', '반도체'),
        makeStock('000990', 'DB하이텍', '테크놀로지', '반도체'),
      ],
    },
    {
      sector_name: '은행',
      stock_count: 2,
      stocks: [
        makeStock('105560', 'KB금융', '금융', null),
        makeStock('055550', '신한지주', '금융', null),
      ],
    },
    {
      sector_name: '기타',
      stock_count: 5,
      stocks: [
        makeStock('132890', '다우데이타', null, null),
        makeStock('005120', '샘코', null, null),
      ],
    },
  ],
}

const ALL_STOCK_NAMES = results.sectors.flatMap((s) => s.stocks.map((st) => st.name))

function renderStockList() {
  return render(
    <WatchlistProvider>
      <StockList />
    </WatchlistProvider>,
  )
}

// ── 3단언: 유니버스 카운트 / 섹터 순서 / 그룹별 접힘 ──

describe('StockList 전체 탭 characterization (SPEC-CHECKED-SECTOR-GROUP-001 M0)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseScreen.mockReturnValue({ results } as unknown as ReturnType<typeof useScreen>)
  })

  afterEach(() => {
    cleanup()
  })

  it('각 섹터 헤더 카운트는 그룹 유니버스 sector.stock_count 값과 일치한다', () => {
    const { container } = renderStockList()

    const counts = Array.from(container.querySelectorAll('.sector-header-count')).map(
      (el) => el.textContent,
    )
    expect(counts).toEqual(results.sectors.map((s) => String(s.stock_count)))

    // (a) 그룹: 카운트 27(유니버스) ≠ 렌더된 행 수 — 카운트가 stocks.length가 아님을 구분
    expect(counts[0]).toBe('27')
    expect(container.querySelectorAll('.stock-item').length).toBe(ALL_STOCK_NAMES.length) // 7
  })

  it('헤더 순서는 results.sectors 순서와 동일하고 종목 행은 각 그룹 하위에 그 순서로 따른다', () => {
    const { container } = renderStockList()

    const headerNames = Array.from(container.querySelectorAll('.sector-header-name')).map(
      (el) => el.textContent,
    )
    expect(headerNames).toEqual(results.sectors.map((s) => s.sector_name))

    // 행 순서 = 섹터 순서 × 섹터 내 stocks 순서 (flatItems 구성 그대로)
    const rowNames = Array.from(container.querySelectorAll('.stock-item-name')).map(
      (el) => el.textContent,
    )
    expect(rowNames).toEqual(ALL_STOCK_NAMES)
  })

  it('헤더 클릭 시 해당 그룹의 종목 행만 렌더에서 제거되고 다른 그룹은 불변이다', () => {
    const { container } = renderStockList()

    const headers = () => Array.from(container.querySelectorAll<HTMLElement>('.sector-header'))

    // 초기: 전 그룹 펼침
    expect(headers().map((h) => h.getAttribute('aria-expanded'))).toEqual(['true', 'true', 'true'])

    // 반도체(첫 번째) 헤더 접기
    fireEvent.click(headers()[0])

    // (1) 해당 헤더만 aria-expanded → false, 화살표 ▶
    expect(headers()[0].getAttribute('aria-expanded')).toBe('false')
    expect(headers()[0].querySelector('.sector-header-arrow')?.textContent).toBe('▶')

    // (2) 반도체 그룹 종목 행은 렌더에서 부재 (CSS 숨김이 아님 — DOM 자체에 없음)
    for (const name of ['삼성전자', 'SK하이닉스', 'DB하이텍']) {
      expect(screen.queryByText(name)).toBeNull()
    }

    // (3) 다른 그룹 불변 — 행 존재 + 헤더 여전히 펼침
    for (const name of ['KB금융', '신한지주', '다우데이타', '샘코']) {
      expect(screen.getByText(name)).toBeInTheDocument()
    }
    expect(headers()[1].getAttribute('aria-expanded')).toBe('true')
    expect(headers()[2].getAttribute('aria-expanded')).toBe('true')

    // 전체 행 수 7 → 4 (해당 그룹 3행만 제거)
    expect(container.querySelectorAll('.stock-item').length).toBe(4)
  })
})
