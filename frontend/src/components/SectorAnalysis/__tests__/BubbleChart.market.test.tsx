// RED: 버블 탭 시장 토글 실동작 — 섹터 뷰와 드릴다운(종목 버블) 뷰 양쪽.
// 사용자 보고: "Bubble 탭에서 시장 토글이 아무 반응 없다".
// 결함: fetchStockBubble 이 market 을 받지 않고, stock 쿼리 키에도 market 이 없어
//       드릴다운 상태에서는 재조회조차 일어나지 않았다.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react'
import type { ReactElement } from 'react'
import { AnalysisParamsProvider, useAnalysisParams } from '../../../contexts/AnalysisParamsContext'
import type { Market } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'
import { fetchSectorBubble, fetchStockBubble } from '../../../api/bubble'
import { BubbleChart } from '../BubbleChart'

vi.mock('../../../api/bubble', () => ({
  fetchSectorBubble: vi.fn(),
  fetchStockBubble: vi.fn(),
}))
vi.mock('../../../contexts/TabContext', () => ({
  useNavIntent: () => ({ navigate: vi.fn(), intent: null }),
}))
vi.mock('../../../contexts/SelectionContext', () => ({
  useSelection: () => ({ selectSector: vi.fn() }),
}))
// 실제 ECharts 대신 관측 가능한 노드 — 드릴다운 트리거와 렌더 내용을 노출한다.
vi.mock('../SectorBubbleChart', () => ({
  SectorBubbleChart: ({ sectors, onSectorClick }: { sectors: { name: string }[]; onSectorClick: (n: string) => void }) => (
    <div data-testid="sector-bubble" data-names={sectors.map(s => s.name).join(',')}>
      <button onClick={() => onSectorClick('반도체')}>drill-반도체</button>
    </div>
  ),
}))
vi.mock('../StockBubbleChart', () => ({
  StockBubbleChart: ({ stocks }: { stocks: { name: string }[] }) => (
    <div data-testid="stock-bubble" data-names={stocks.map(s => s.name).join(',')}>stock</div>
  ),
}))

// 시장별로 실제로 다른 응답 — market 이 누락되면 all 응답이 그대로 나와 단언이 깨진다.
const SECTORS_BY_MARKET: Record<string, string[]> = {
  all: ['반도체', '은행'],
  kospi: ['반도체'],
  kosdaq: ['은행'],
}
const STOCKS_BY_MARKET: Record<string, string[]> = {
  all: ['삼성전자', '에코프로'],
  kospi: ['삼성전자'],
  kosdaq: ['에코프로'],
}

const envelope = (over: Record<string, unknown>) => ({
  date: '2026-08-11',
  period: '1m',
  as_of_date: '2026-08-11',
  as_of_is_partial_week: false,
  grid_version: 'g1',
  ...over,
})

// 헤더 토글 대신 테스트가 직접 market 을 바꾼다.
function MarketSwitch(): ReactElement {
  const { setMarket } = useAnalysisParams()
  return (
    <>
      {(['all', 'kospi', 'kosdaq'] as Market[]).map(m => (
        <button key={m} onClick={() => setMarket(m)}>set-{m}</button>
      ))}
    </>
  )
}

function renderBC(): void {
  render(
    <AnalysisParamsProvider>
      <DataLoadProvider>
        <MarketSwitch />
        <BubbleChart initialSector={null} />
      </DataLoadProvider>
    </AnalysisParamsProvider>,
  )
}

beforeEach(() => {
  vi.mocked(fetchSectorBubble).mockReset()
  vi.mocked(fetchStockBubble).mockReset()
  // 응답은 호출 시 넘어온 market 으로 결정된다. market 이 안 넘어오면 all 로 떨어진다.
  vi.mocked(fetchSectorBubble).mockImplementation(async (_period: string, market?: string | null) =>
    envelope({ market: market ?? null, sectors: (SECTORS_BY_MARKET[market ?? 'all'] ?? []).map(name => ({ name })) }) as never,
  )
  vi.mocked(fetchStockBubble).mockImplementation(async (sector: string, _period: string, market?: string | null) =>
    envelope({
      sector_name: sector,
      market: market ?? null,
      stocks: (STOCKS_BY_MARKET[market ?? 'all'] ?? []).map(name => ({ name })),
    }) as never,
  )
})
afterEach(() => cleanup())

describe('시장 토글 — 섹터 버블 뷰 (진단: 섹터 레벨도 고장인가?)', () => {
  it('KOSPI 로 바꾸면 market="kospi" 로 재조회하고 렌더 내용이 바뀐다', async () => {
    renderBC()
    await waitFor(() => expect(screen.getByTestId('sector-bubble')).toBeInTheDocument())
    expect(screen.getByTestId('sector-bubble').getAttribute('data-names')).toBe('반도체,은행')

    fireEvent.click(screen.getByText('set-kospi'))

    await waitFor(() => {
      expect(screen.getByTestId('sector-bubble').getAttribute('data-names')).toBe('반도체')
    })
    expect(vi.mocked(fetchSectorBubble).mock.calls.at(-1)?.[1]).toBe('kospi')
  })
})

describe('시장 토글 — 드릴다운(종목 버블) 뷰 [보고된 결함]', () => {
  it('섹터 드릴다운 후 KOSPI 로 바꾸면 fetchStockBubble 이 market="kospi" 로 재조회된다', async () => {
    renderBC()
    await waitFor(() => expect(screen.getByTestId('sector-bubble')).toBeInTheDocument())

    // 섹터 클릭 → 종목 버블 뷰 진입
    fireEvent.click(screen.getByText('drill-반도체'))
    await waitFor(() => expect(screen.getByTestId('stock-bubble')).toBeInTheDocument())
    expect(screen.getByTestId('stock-bubble').getAttribute('data-names')).toBe('삼성전자,에코프로')
    expect(vi.mocked(fetchStockBubble).mock.calls.at(-1)?.[2]).toBe('all')

    // 드릴다운 상태에서 시장 변경 → 재조회 + 렌더 변화
    fireEvent.click(screen.getByText('set-kospi'))
    await waitFor(() => {
      expect(screen.getByTestId('stock-bubble').getAttribute('data-names')).toBe('삼성전자')
    })
    expect(vi.mocked(fetchStockBubble).mock.calls.at(-1)?.[2]).toBe('kospi')
  })

  it('KOSDAQ 로 바꾸면 KOSDAQ 응답으로 갱신된다 (한 시장만 통하는 우연 통과 차단)', async () => {
    renderBC()
    await waitFor(() => expect(screen.getByTestId('sector-bubble')).toBeInTheDocument())
    fireEvent.click(screen.getByText('drill-반도체'))
    await waitFor(() => expect(screen.getByTestId('stock-bubble')).toBeInTheDocument())

    fireEvent.click(screen.getByText('set-kosdaq'))
    await waitFor(() => {
      expect(screen.getByTestId('stock-bubble').getAttribute('data-names')).toBe('에코프로')
    })
    expect(vi.mocked(fetchStockBubble).mock.calls.at(-1)?.[2]).toBe('kosdaq')
  })

  it('시장이 다르면 종목 버블 캐시 키도 달라진다 (키 미분리로 인한 재조회 누락 가드)', async () => {
    renderBC()
    await waitFor(() => expect(screen.getByTestId('sector-bubble')).toBeInTheDocument())
    fireEvent.click(screen.getByText('drill-반도체'))
    await waitFor(() => expect(fetchStockBubble).toHaveBeenCalledTimes(1))

    fireEvent.click(screen.getByText('set-kospi'))
    await waitFor(() => expect(fetchStockBubble).toHaveBeenCalledTimes(2))
    fireEvent.click(screen.getByText('set-kosdaq'))
    await waitFor(() => expect(fetchStockBubble).toHaveBeenCalledTimes(3))

    // 이미 조회한 all 로 되돌아가면 TTL 캐시 적중 — 추가 호출은 없다.
    fireEvent.click(screen.getByText('set-all'))
    await waitFor(() => expect(screen.getByTestId('stock-bubble').getAttribute('data-names')).toBe('삼성전자,에코프로'))
    expect(fetchStockBubble).toHaveBeenCalledTimes(3)
  })
})
