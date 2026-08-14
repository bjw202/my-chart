// 종목 표 세로 스크롤 회귀 가드.
// 결함: 표 래퍼(.stock-table-wrapper)를 감싼 ref div 가 클래스 없는 블록이라
// 안쪽의 flex:1 이 무효가 되고, 표가 내용 높이(75,239px)만큼 펼쳐진 뒤
// .stock-explorer 의 overflow:hidden 에 잘려 스크롤이 사라졌다.
// jsdom 은 레이아웃을 계산하지 않으므로, 스크롤을 성립시키는 두 계약을 직접 검증한다:
//   (1) 표 래퍼의 부모가 잔여 높이를 받는 flex 열 컨테이너다.
//   (2) 그 컨테이너와 래퍼가 flex:1 + min-height:0 을 선언한다.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import type { StageOverviewResponse, Stage2Candidate } from '../../../types/stage'
import '../../../styles/global.css'
import { AnalysisParamsProvider } from '../../../contexts/AnalysisParamsContext'
import { DataLoadProvider } from '../../../contexts/DataLoadContext'
import { fetchStageOverview } from '../../../api/stage'
import { StockExplorer } from '../StockExplorer'

vi.mock('../../../api/stage', () => ({ fetchStageOverview: vi.fn() }))
vi.mock('../../../contexts/TabContext', () => ({
  useTab: () => ({ activeTab: 'stock-explorer', setActiveTab: vi.fn() }),
  useNavIntent: () => ({ intent: null, navigate: vi.fn() }),
}))
vi.mock('../../../contexts/SelectionContext', () => ({
  useSelection: () => ({ selectedSector: null, sectorScopeFollow: false, setSectorScopeFollow: vi.fn() }),
}))

function stock(over: Partial<Stage2Candidate>): Stage2Candidate {
  return {
    code: '000100', name: '종목A', market: 'KOSDAQ',
    sector_major: '스마트폰', sector_minor: '부품',
    stage: 4, stage_detail: 'stage4',
    rs_12m: 50, chg_1m: 1, volume_ratio: 1, close: 100, sma50: 90, sma200: 80,
    ...over,
  }
}

const overview = (rows: Stage2Candidate[]): StageOverviewResponse => ({
  distribution: { stage1: 0, stage2: 0, stage3: 0, stage4: rows.length, total: rows.length },
  by_sector: [],
  stage2_candidates: [],
  all_stocks: rows,
  as_of_date: '2026-08-11',
  as_of_is_partial_week: false,
} as never)

beforeEach(() => {
  vi.mocked(fetchStageOverview).mockReset()
  vi.mocked(fetchStageOverview).mockResolvedValue(overview([stock({}), stock({ code: '000200', name: '종목B' })]))
})
afterEach(() => cleanup())

// 해당 선택자 규칙의 선언 블록만 읽는다(다른 규칙의 같은 속성에 걸려 통과하는 것을 막는다).
function ruleBody(selector: string): string {
  const sheets = [...document.styleSheets]
  for (const sheet of sheets) {
    for (const rule of [...sheet.cssRules]) {
      if (rule instanceof CSSStyleRule && rule.selectorText === selector) return rule.style.cssText
    }
  }
  throw new Error(`${selector} 규칙이 없다`)
}

describe('종목 표 세로 스크롤 계약', () => {
  it('표 래퍼의 부모가 stock-table-fill flex 컨테이너다', async () => {
    render(
      <AnalysisParamsProvider>
        <DataLoadProvider>
          <StockExplorer />
        </DataLoadProvider>
      </AnalysisParamsProvider>,
    )
    await screen.findByText('종목A')
    const wrapper = document.querySelector('.stock-table-wrapper')
    expect(wrapper).not.toBeNull()
    expect(wrapper?.parentElement?.classList.contains('stock-table-fill')).toBe(true)
  })

  it('컨테이너와 래퍼가 잔여 높이 + 스크롤 선언을 갖는다', () => {
    const fill = ruleBody('.stock-table-fill')
    expect(fill).toMatch(/flex:\s*1/)
    expect(fill).toMatch(/min-height:\s*0/)
    expect(fill).toMatch(/flex-direction:\s*column/)

    const wrap = ruleBody('.stock-table-wrapper')
    expect(wrap).toMatch(/flex:\s*1/)
    expect(wrap).toMatch(/min-height:\s*0/)
    expect(wrap).toMatch(/overflow-y:\s*auto/)
  })
})
