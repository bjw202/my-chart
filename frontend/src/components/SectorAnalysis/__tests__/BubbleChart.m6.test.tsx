// RED: AC-SUX-035 (LD-C stale-but-showing, 차트 언마운트 금지) / AC-SUX-036 (⟳ 새로고침 상설)
//      / AC-SUX-037 (기준일 배지 = 응답 문자열 그대로 + 진행 중 표기)
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor, cleanup, fireEvent } from '@testing-library/react'
import type { ReactElement } from 'react'
import { AnalysisParamsProvider, useAnalysisParams } from '../../../contexts/AnalysisParamsContext'
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
// ECharts 대신 식별 가능한 노드를 렌더한다 — DOM 노드 동일성 단언용.
vi.mock('../SectorBubbleChart', () => ({
  SectorBubbleChart: ({ sectors }: { sectors: unknown[] }) => (
    <div data-testid="sector-bubble" data-count={sectors.length}>chart</div>
  ),
}))
vi.mock('../StockBubbleChart', () => ({
  StockBubbleChart: () => <div data-testid="stock-bubble">stock</div>,
}))

const sectorEnv = (over: Record<string, unknown> = {}) => ({
  date: '2026-08-11',
  period: '1m',
  market: null,
  sectors: [{ name: '반도체' }, { name: '은행' }],
  as_of_date: '2026-08-11',
  as_of_is_partial_week: false,
  grid_version: 'g1',
  ...over,
})

// 기간을 바꿀 수 있는 하네스 — 헤더 토글 대신 테스트가 직접 period 를 바꾼다.
function PeriodSwitch(): ReactElement {
  const { setPeriod } = useAnalysisParams()
  return <button onClick={() => setPeriod('3m')}>switch-3m</button>
}

function renderBC(): void {
  render(
    <AnalysisParamsProvider>
      <DataLoadProvider>
        <PeriodSwitch />
        <BubbleChart initialSector={null} />
      </DataLoadProvider>
    </AnalysisParamsProvider>,
  )
}

beforeEach(() => {
  vi.mocked(fetchSectorBubble).mockReset()
  vi.mocked(fetchStockBubble).mockReset()
})
afterEach(() => cleanup())

describe('AC-SUX-035 — 재조회 중 차트가 언마운트되지 않는다 (LD-C)', () => {
  it('period 변경 재조회 동안 SectorBubbleChart DOM 노드가 동일하고 로딩 인디케이터만 뜬다', async () => {
    let resolveSecond: ((v: unknown) => void) | null = null
    vi.mocked(fetchSectorBubble)
      .mockResolvedValueOnce(sectorEnv() as never)
      .mockImplementationOnce(() => new Promise(res => { resolveSecond = res as (v: unknown) => void }))

    renderBC()
    await waitFor(() => expect(screen.getByTestId('sector-bubble')).toBeInTheDocument())
    const before = screen.getByTestId('sector-bubble')

    fireEvent.click(screen.getByText('switch-3m'))
    // 재조회 인디케이터가 기준일 배지 옆에 뜬다
    await waitFor(() => expect(screen.getByTestId('refetch-spinner')).toBeInTheDocument())

    // 현행 BubbleChart.tsx 의 깜빡임(로딩 중 차트 언마운트)이 재현되지 않는다:
    // 같은 DOM 노드 객체가 그대로 유지된다.
    const during = screen.getByTestId('sector-bubble')
    expect(during).toBe(before)
    expect(during.getAttribute('data-count')).toBe('2')

    resolveSecond!(sectorEnv({ sectors: [{ name: '반도체' }] }))
    await waitFor(() => expect(screen.getByTestId('sector-bubble').getAttribute('data-count')).toBe('1'))
    expect(screen.queryByTestId('refetch-spinner')).not.toBeInTheDocument()
  })

  it('재조회 실패 시 기존 데이터를 유지하고 갱신 실패 띠 + [다시 시도] 를 렌더한다', async () => {
    vi.mocked(fetchSectorBubble)
      .mockResolvedValueOnce(sectorEnv({ as_of_date: '2026-08-07' }) as never)
      .mockRejectedValue(new Error('boom'))

    renderBC()
    await waitFor(() => expect(screen.getByTestId('sector-bubble')).toBeInTheDocument())
    const before = screen.getByTestId('sector-bubble')

    fireEvent.click(screen.getByText('switch-3m'))
    await waitFor(() => expect(screen.getByTestId('stale-banner')).toBeInTheDocument(), { timeout: 20000 })

    // 기존 데이터 유지 — 차트 노드도 그대로
    expect(screen.getByTestId('sector-bubble')).toBe(before)
    expect(screen.getByTestId('stale-banner').textContent)
      .toContain('갱신 실패 — 표시 중인 데이터는 2026-08-07 기준입니다')
    expect(screen.getByTestId('stale-retry-btn')).toBeInTheDocument()
  }, 30000)
})

describe('AC-SUX-036 — ⟳ 새로고침 상설 + 전 캐시 무효화', () => {
  it('로딩/성공/실패 상태와 무관하게 ⟳ 새로고침 버튼이 항상 렌더된다', async () => {
    vi.mocked(fetchSectorBubble).mockResolvedValue(sectorEnv() as never)
    renderBC()
    // 최초 로딩 시점부터 존재
    expect(screen.getByTestId('refresh-btn')).toBeInTheDocument()
    expect(screen.getByTestId('refresh-btn').textContent).toContain('⟳ 새로고침')
    await waitFor(() => expect(screen.getByTestId('sector-bubble')).toBeInTheDocument())
    // 성공 후에도 존재
    expect(screen.getByTestId('refresh-btn')).toBeInTheDocument()
  })

  it('⟳ 새로고침 클릭은 TTL 내에서도 재조회를 일으킨다', async () => {
    vi.mocked(fetchSectorBubble).mockResolvedValue(sectorEnv() as never)
    renderBC()
    await waitFor(() => expect(fetchSectorBubble).toHaveBeenCalledTimes(1))
    fireEvent.click(screen.getByTestId('refresh-btn'))
    await waitFor(() => expect(fetchSectorBubble).toHaveBeenCalledTimes(2))
  })
})

describe('AC-SUX-037 — 기준일 배지 (SN-4)', () => {
  it('배지 텍스트가 응답 as_of_date 문자열과 동등하다 (프론트 포맷 변환 없음)', async () => {
    vi.mocked(fetchSectorBubble).mockResolvedValue(sectorEnv({ as_of_date: '2026-08-11' }) as never)
    renderBC()
    await waitFor(() => expect(screen.getByTestId('as-of-badge').textContent).toContain('2026-08-11'))
    // 08/11, 2026-08-11(금) 같은 프론트 가공 표기가 아니다
    expect(screen.getByTestId('as-of-badge').textContent).toBe('기준일 2026-08-11')
  })

  it('as_of_is_partial_week=true 면 진행 중 표기가 배지 옆에 함께 렌더된다', async () => {
    vi.mocked(fetchSectorBubble).mockResolvedValue(sectorEnv({ as_of_is_partial_week: true }) as never)
    renderBC()
    await waitFor(() => expect(screen.getByTestId('as-of-partial-week')).toBeInTheDocument())
    expect(screen.getByTestId('as-of-partial-week').textContent).toContain('진행 중')
  })

  it('as_of_is_partial_week=false 면 진행 중 표기가 없다', async () => {
    vi.mocked(fetchSectorBubble).mockResolvedValue(sectorEnv({ as_of_is_partial_week: false }) as never)
    renderBC()
    await waitFor(() => expect(screen.getByTestId('as-of-badge')).toBeInTheDocument())
    expect(screen.queryByTestId('as-of-partial-week')).not.toBeInTheDocument()
  })
})

describe('AC-SUX-033 — 비활성 화면은 조회하지 않는다', () => {
  it('active=false 면 섹터 버블 엔드포인트 fetch 가 발생하지 않는다', async () => {
    vi.mocked(fetchSectorBubble).mockResolvedValue(sectorEnv() as never)
    render(
      <AnalysisParamsProvider>
        <DataLoadProvider>
          <BubbleChart initialSector={null} active={false} />
        </DataLoadProvider>
      </AnalysisParamsProvider>,
    )
    await new Promise(r => setTimeout(r, 20))
    expect(fetchSectorBubble).not.toHaveBeenCalled()
    // 종목 엔드포인트도 마찬가지
    expect(fetchStockBubble).not.toHaveBeenCalled()
  })
})
