// M7 — §0.2 성능 실측 + 모바일 폭 hover-only 0건 (E6 / A5).
//
// 측정 방식에 대한 정직한 한정:
// React DevTools Profiler 는 헤드리스에서 구동할 수 없다. 따라서 리렌더 범위는
// **렌더 카운터**로, 조회 수는 **fetcher 호출 수**로, 표 렌더 비용은 **wall-clock**
// 으로 기계적으로 측정한다. 기계적으로 측정할 수 없는 항목은 단언하지 않고
// progress.md §E.2 에 Gap 으로 기록한다 (수치를 지어내지 않는다).
import { describe, it, expect, afterEach } from 'vitest'
import { render, cleanup, act as actFn } from '@testing-library/react'
import { useEffect } from 'react'
import type { ReactElement } from 'react'
import { AnalysisParamsProvider, useAnalysisParams } from '../../../contexts/AnalysisParamsContext'
import { SelectionProvider, useSelection } from '../../../contexts/SelectionContext'
import { StockTable } from '../StockTable'
import { SectorRankingTable } from '../../SectorAnalysis/SectorRankingTable'
import type { Stage2Candidate } from '../../../types/stage'
import type { SectorRankItem } from '../../../types/market'

afterEach(() => cleanup())

// ── §0.2 — selectedSector 변경 시 무관 컴포넌트 리렌더 0 (Context 분리 목적) ──
describe('§0.2 — Context 분리에 따른 리렌더 범위', () => {
  // 렌더 카운트와 Context 핸들은 콜백 prop 으로 넘긴다. 렌더 중 외부 변수에 대입하면
  // react-hooks/globals 위반이고, prop 객체를 직접 변형하면 react-hooks/immutability 위반이다.
  // 둘 다 피하려면 effect 안에서 콜백을 호출하는 형태여야 한다.
  type Handle = { selectSector: (s: string) => void; setPeriod: (p: '1w' | '1m' | '3m') => void }

  function ParamsOnlyConsumer({ onRender }: { onRender: () => void }): ReactElement {
    useAnalysisParams()
    useEffect(() => { onRender() })
    return <div data-testid="params-consumer" />
  }

  function SelectionOnlyConsumer({ onRender }: { onRender: () => void }): ReactElement {
    useSelection()
    useEffect(() => { onRender() })
    return <div data-testid="selection-consumer" />
  }

  function Handles({ onReady }: { onReady: (h: Handle) => void }): ReactElement {
    const { selectSector } = useSelection()
    const { setPeriod } = useAnalysisParams()
    useEffect(() => { onReady({ selectSector, setPeriod }) })
    return <div />
  }

  // 두 소비자의 리렌더 횟수를 세고, Context 조작 핸들을 돌려준다.
  function mount() {
    const counts = { params: 0, selection: 0 }
    let handle: Handle = { selectSector: () => {}, setPeriod: () => {} }
    render(
      <AnalysisParamsProvider><SelectionProvider>
        <Handles onReady={h => { handle = h }} />
        <ParamsOnlyConsumer onRender={() => { counts.params += 1 }} />
        <SelectionOnlyConsumer onRender={() => { counts.selection += 1 }} />
      </SelectionProvider></AnalysisParamsProvider>,
    )
    return { counts, act: (fn: (h: Handle) => void) => actFn(() => fn(handle)) }
  }

  it('selectedSector 변경 → AnalysisParams 만 소비하는 컴포넌트 리렌더 0', () => {
    const m = mount()
    const paramsBefore = m.counts.params
    const selectionBefore = m.counts.selection

    m.act(h => h.selectSector('반도체'))

    // 무관 컴포넌트(기간·시장만 소비)는 리렌더되지 않는다.
    expect(m.counts.params - paramsBefore).toBe(0)
    // 관련 컴포넌트는 정확히 1회 리렌더된다.
    expect(m.counts.selection - selectionBefore).toBe(1)
  })

  it('반대 방향도 성립한다 — period 변경 → Selection 만 소비하는 컴포넌트 리렌더 0', () => {
    const m = mount()
    const paramsBefore = m.counts.params
    const selectionBefore = m.counts.selection

    m.act(h => h.setPeriod('3m'))

    // 두 Context 를 하나로 합치면(=Selection value 가 period 에 의존하면) 여기서 실패한다.
    expect(m.counts.selection - selectionBefore).toBe(0)
    expect(m.counts.params - paramsBefore).toBe(1)
  })
})

// ── §0.2 — 종목 표 500행 렌더 시간 ──────────────────────────────────────────
function makeCandidates(n: number): Stage2Candidate[] {
  return Array.from({ length: n }, (_, i) => ({
    code: String(100000 + i),
    name: `종목${i}`,
    market: i % 2 === 0 ? 'KOSPI' : 'KOSDAQ',
    sector_major: '반도체',
    sector_minor: '반도체장비',
    stage: (i % 4) + 1,
    stage_detail: 'detail',
    rs_12m: 50 + (i % 50),
    chg_1m: (i % 20) - 10,
    volume_ratio: 1 + (i % 5) / 10,
    close: 10000 + i,
    sma50: 9000 + i,
    sma200: 8000 + i,
    chg_1w: (i % 10) - 5,
    chg_3m: (i % 30) - 15,
    weight_in_sector: (i % 100) / 1000,
    weight_capped: i % 50 === 0,
    near_52w_high: i % 7 === 0,
  }))
}

function renderStockTable(rows: Stage2Candidate[], collapseLevel = 0) {
  return render(
    <StockTable
      candidates={rows}
      stageFilter={null}
      sectorFilter={null}
      marketFilter="all"
      onStockSelect={() => {}}
      selectedStocks={new Set()}
      collapseLevel={collapseLevel}
    />,
  )
}

describe('§0.2 — 종목 표 500행 렌더 (절대 실측)', () => {
  it('500행이 실제로 렌더되고 소요 시간을 실측한다', () => {
    const rows = makeCandidates(500)
    const t0 = performance.now()
    const { container } = renderStockTable(rows)
    const elapsed = performance.now() - t0

    expect(container.querySelectorAll('tbody tr').length).toBe(500)
    // 실측값 자체가 산출물이다. 상한은 회귀 감시용의 느슨한 가드로만 둔다
    // (CI 머신 편차를 고려해 넉넉하게 — 정밀 임계값은 §0.2 Gap 으로 남긴다).
    expect(elapsed).toBeLessThan(10_000)
    // 실측 기록: progress.md §E.2 에 이 테스트의 출력값을 옮긴다.
    expect(Number.isFinite(elapsed)).toBe(true)
  })

  it('기간 3열(1W/1M/3M)은 어떤 접기 단계에서도 사라지지 않는다 (AC-SUX-061 게이트)', () => {
    const rows = makeCandidates(50)
    for (const level of [0, 1, 2, 3]) {
      const { container } = renderStockTable(rows, level)
      const head = container.querySelector('thead')!.textContent!
      expect(head).toContain('1W')
      expect(head).toContain('1M')
      expect(head).toContain('3M')
      cleanup()
    }
  })
})

// ── E6 / A5 — 모바일 폭에서 hover-only 정보 0건 ────────────────────────────
describe('E6 / A5 — 좁은 화면에서 hover 로만 접근되는 정보가 없다', () => {
  const row = (name: string, rank: number): SectorRankItem => ({
    name, stock_count: 20,
    returns: { w1: 1, m1: 2, m3: 3 }, excess_returns: { w1: 0.5, m1: 1, m3: 2 },
    rs_avg: 60, rs_top_pct: 20, nh_pct: 10, stage2_pct: 30,
    composite_score: 70, rank, rank_change: 0,
  })

  // title 을 가진 요소는 전부 본문 텍스트도 함께 가진다 = 값이 hover 뒤에만 숨지 않는다.
  function hoverOnlyElements(container: HTMLElement): string[] {
    return Array.from(container.querySelectorAll('[title]'))
      .filter(el => (el.textContent ?? '').trim() === '')
      .map(el => `${el.tagName}[title="${el.getAttribute('title')}"]`)
  }

  it('순위표: 접기 최대 단계에서도 title 전용(본문 텍스트 없는) 요소가 0건이다', () => {
    const { container } = render(
      <SectorRankingTable
        sectors={[row('반도체', 1), row('은행', 2)]}
        excluded={[{ sector: '디스플레이', reason: 'insufficient_members', count: 4 }]}
        baselineDate="2026-08-01"
        onSectorClick={() => {}} selectedSector={null}
        sortField="rank" sortDirection="asc" onSort={() => {}}
      />,
    )
    expect(hoverOnlyElements(container)).toEqual([])
    // 제외 섹터의 사유·종목 수가 본문 텍스트로 보인다 (툴팁 전용 아님).
    const ex = container.querySelector('[data-testid="excluded-sectors"]')!
    expect(ex.textContent).toContain('디스플레이')
    expect(ex.textContent).toContain('4')
  })

  it('종목 표: 접기 3단계(가장 좁은 폭)에서도 title 전용 요소가 0건이다', () => {
    const { container } = renderStockTable(makeCandidates(30), 3)
    expect(hoverOnlyElements(container)).toEqual([])
  })

  it('접힌 열의 값은 소실되지 않는다 — 접기 전/후 행 수가 같다', () => {
    const rows = makeCandidates(30)
    const a = renderStockTable(rows, 0)
    const before = a.container.querySelectorAll('tbody tr').length
    cleanup()
    const b = renderStockTable(rows, 3)
    expect(b.container.querySelectorAll('tbody tr').length).toBe(before)
  })
})
