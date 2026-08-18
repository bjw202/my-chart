// SPEC-SECTOR-DISPLAY-UNIFY-001 M6 — REQ-SDU-008 / AC-SDU-008: RS 문자열 3면 동일성.
// 같은 섹터의 RS 가 Table / Bubble 툴팁 / 상세 패널에서 동일 문자열로 표시되는지.
// 비교 양변은 서로 다른 컴포넌트의 (렌더 또는 프로덕션 포매터) 출력에서 온다 —
// 같은 헬퍼를 세 번 호출해 비교하면 무효다(lessons #9).
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import type { ReactElement } from 'react'
import type { SectorRankItem } from '../../../types/market'
import type { SectorBubbleItem } from '../../../types/bubble'

// Bubble 면은 ECharts 렌더 대신 프로덕션 option 의 tooltip.formatter 를 직접 호출한다.
// formatter 는 SectorBubbleChart 가 차트에 넘기는 프로덕션 코드 경로다.
vi.mock('echarts-for-react', () => ({
  default: vi.fn((): ReactElement => <div data-testid="echarts-mock" />),
}))

import ReactECharts from 'echarts-for-react'
import { SectorRankingTable } from '../SectorRankingTable'
import { SectorDetailPanel } from '../SectorDetailPanel'
import { SectorBubbleChart } from '../SectorBubbleChart'
import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'

vi.mock('../../../api/sectors', () => ({
  fetchSectorDetail: vi.fn().mockResolvedValue({ sector_name: 'Alpha', sub_sectors: [], top_stocks: [] }),
}))

const mockChart = vi.mocked(ReactECharts)

// 소수점 rs_avg — 반올림 규약(rating0)이 세 면에서 같게 적용되는지를 드러낸다.
const RS_AVG = 62.6
const EXPECTED = '63'

const sector: SectorRankItem = {
  name: 'Alpha',
  stock_count: 10,
  returns: { w1: 1, m1: 2, m3: 3 },
  excess_returns: { w1: 0.5, m1: 1.5, m3: 2.5 },
  rs_avg: RS_AVG,
  rs_top_pct: 30,
  nh_pct: 20,
  stage2_pct: 40,
  composite_score: 70,
  rank: 1,
  rank_change: 0,
}

const tableProps = {
  sectors: [sector],
  sortField: 'rank',
  sortDirection: 'asc' as const,
  onSort: vi.fn(),
  onSectorClick: vi.fn(),
  selectedSector: null,
}

function readTableCell(): string {
  const row = screen.getByText('Alpha').closest('tr') as HTMLTableRowElement
  const tds = row.querySelectorAll('td')
  return tds[5].textContent ?? '' // 열 순서상 6번째 td = RS Avg
}

function readPanelCard(): string {
  const cards = Array.from(document.querySelectorAll('.sector-detail-metric'))
  const rsCard = cards.find(c => c.querySelector('.sector-detail-metric-label')?.textContent === 'RS Avg')
  return rsCard?.querySelector('.sector-detail-metric-value')?.textContent ?? ''
}

function readBubbleTooltip(): string {
  const call = mockChart.mock.calls.at(-1)
  if (!call) throw new Error('SectorBubbleChart 가 ECharts 를 렌더하지 않았다')
  const option = call[0].option as { tooltip: { formatter: (p: { data: { value: (string | number)[] } }) => string } }
  // value: [x(초과수익률), y(RS), size, periodReturn, name, tradingValue, rsAvg, isMissingTV]
  return option.tooltip.formatter({ data: { value: [1.2, RS_AVG, 20, 2, 'Alpha', 1e11, RS_AVG, 0] } })
}

describe('REQ-SDU-008 — RS 문자열 3면 동일성', () => {
  it('Table · Bubble 툴팁 · 상세 패널의 RS 표시가 동일 문자열(63)이다', () => {
    // 1) Table 면 — 프로덕션 렌더 출력
    const { unmount: unmountTable } = render(<SectorRankingTable {...tableProps} />)
    const tableText = readTableCell()
    unmountTable()

    // 2) 상세 패널 면 — 프로덕션 렌더 출력
    const { unmount: unmountPanel } = render(
      <AnalysisParamsProvider><DataLoadProvider>
        <SectorDetailPanel sector={sector} />
      </DataLoadProvider></AnalysisParamsProvider>,
    )
    const panelText = readPanelCard()
    unmountPanel()

    // 3) Bubble 툴팁 면 — 프로덕션 tooltip formatter 출력
    mockChart.mockClear()
    const bubbleItem: SectorBubbleItem = {
      name: 'Alpha',
      excess_return: 1.2,
      rs_avg: RS_AVG,
      trading_value: 1e11,
      period_return: 2,
    }
    render(<SectorBubbleChart sectors={[bubbleItem]} period="1m" onSectorClick={() => {}} />)
    const tooltipText = readBubbleTooltip()

    expect(tableText).toBe(EXPECTED)
    expect(panelText).toBe(EXPECTED)
    expect(tooltipText).toContain(`RS 평균: ${EXPECTED}`)

    // 세 면의 최종 문자열이 상호 동일함(툴팁은 라벨 접두를 제외한 값 부분).
    expect(tableText).toBe(panelText)
  })
})
