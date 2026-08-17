/**
 * StockList 체크(checked) 탭 그룹핑 통합 테스트 — SPEC-CHECKED-SECTOR-GROUP-001 M3
 *
 * M2에서 이미 구현된 체크 탭 섹터 그룹핑(buildCheckedGroups + collapsedCheckedSectors)의
 * 통합 거동을 고정한다. 되돌림(RED 관측)은 M4 소관 — 본 파일은 현재 트리에서 전부 GREEN이어야 한다.
 *
 * 픽스처 규약 (acceptance.md [HARD]):
 *   (a) major+minor 그룹('내수 > 리조트'), (b) major-only 그룹('금융'), (c) sector_major null → '기타' — 3종 포함
 *   (d) 정렬 축: CHECK_ORDER(체크 시각 순서)가 코드포인트 순서와 어긋나게 구성
 *       (삽입 순 ['내수 > 리조트','AI','기타','금융'] ≠ 정렬 ['AI','금융','기타','내수 > 리조트'])
 *   (e) 카운트 판별성: '금융' 유니버스 stock_count=3 ≠ 체크 수 1
 *   (f) 렌더 창 상한: 헤더 4 + 종목(체크 7 / 전체 9) 각각 총 11·13 ≤ 15
 *       (jsdom listHeight 600 고정 + overscanCount 5)
 *
 * AC-011 양변 규칙: 기대 섹터명은 서버 픽스처(results.sectors[].sector_name)에서 런타임 추출 —
 * 프로덕션 헬퍼(sectorKeyOf/buildCheckedGroups)를 기대값 산출에 쓰지 않는다.
 * AC-016(b) 기준선: 경로 ①(테스트 리터럴 고정) 채택 — (a)에서 강원랜드를 해제한 뒤의
 * 6종목 상태([롯데관광개발, 인터파크, 에이치엔티, 케이아이엔엠, 다우데이타, KB금융])에 대응하는 값.
 * AC-014: jsdom globalThis.fetch 존재 여부가 불확실해 vi.spyOn 대신 vi.stubGlobal으로 관측면 구성
 * (관측 대상은 동일 — fetch 호출 수).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, cleanup, act } from '@testing-library/react'
import React from 'react'
import type { StockItem } from '../../../types/stock'

// ── 의존성 모킹: StockList가 소비하는 context/hook만 최소 모킹 (M0 characterization과 동일) ──
// (WatchlistContext는 실 Provider로 감싸 실동작 사용 — 체크 상태가 그룹핑의 실제 입력이므로)

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
import { WatchlistProvider, useWatchlist } from '../../../contexts/WatchlistContext'
import { useScreen } from '../../../contexts/ScreenContext'
import { buildCheckedGroups } from '../sectorKey'

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

const GANGWON = makeStock('035250', '강원랜드', '내수', '리조트')
const LOTTE = makeStock('003490', '롯데관광개발', '내수', '리조트')
const INTERPARK = makeStock('035900', '인터파크', '내수', '리조트')
const HNT = makeStock('265960', '에이치엔티', '내수', '리조트')
const KB = makeStock('105560', 'KB금융', '금융', null)
const SHINHAN = makeStock('055550', '신한지주', '금융', null)
const HANA = makeStock('086790', '하나금융지주', '금융', null)
const DAOU = makeStock('132890', '다우데이타', null, null)
const KIENM = makeStock('036540', '케이아이엔엠', 'AI', null)

// 서버 응답 픽스처 — AC-011의 기대값 원천(런타임 추출 대상)
const SERVER_RESULTS = {
  sectors: [
    // (a) major+minor. 유니버스 4 = 체크 4
    { sector_name: '내수 > 리조트', stock_count: 4, stocks: [GANGWON, LOTTE, INTERPARK, HNT] },
    // (b) major-only. 유니버스 3 ≠ 체크 1 — 규약 (e)
    { sector_name: '금융', stock_count: 3, stocks: [KB, SHINHAN, HANA] },
    // (c) sector_major null → '기타'
    { sector_name: '기타', stock_count: 1, stocks: [DAOU] },
    // ASCII 키 — 한글 키와 섞인 코드포인트 정렬 판별용
    { sector_name: 'AI', stock_count: 1, stocks: [KIENM] },
  ],
}

// (d) 체크 시각 순서 — Map 삽입 순서가 코드포인트 순서와 어긋나게 구성
// 삽입 순서 키: ['내수 > 리조트','AI','기타','금융'] ≠ 정렬 ['AI','금융','기타','내수 > 리조트']
const CHECK_ORDER: StockItem[] = [GANGWON, LOTTE, INTERPARK, HNT, KIENM, DAOU, KB]
const CHECKED_COUNT = CHECK_ORDER.length // 7

// 기대 그룹 순서 — 테스트에서 독립적으로 산출한 리터럴 (프로덕션 정렬 함수 미사용)
// 코드포인트: 'AI'(0x41 최선두) < 금(U+AE08)융 < 기(U+AE30)타 < 내(U+B0AC)수
const EXPECTED_SORTED_KEYS = ['AI', '금융', '기타', '내수 > 리조트']

// 테스트 로컬 키 유도 — 프로덕션 sectorKeyOf를 import하지 않고 픽스처에서 독립 도출
function localKeyOf(s: StockItem): string {
  const major = s.sector_major || '기타'
  const minor = s.sector_minor || ''
  return minor ? `${major} > ${minor}` : major
}
const INSERTION_ORDER: string[] = []
for (const s of CHECK_ORDER) {
  const k = localKeyOf(s)
  if (!INSERTION_ORDER.includes(k)) INSERTION_ORDER.push(k)
}

// ── 체크 주입 하네스 ──
// 진짜 체크 버튼과 동일한 경로(ctx.toggleStock)를 렌더 커밋당 1회씩 순차 호출해
// Map 삽입 순서(=체크 시각 순서)를 결정적으로 제어한다.
type WatchlistCtx = ReturnType<typeof useWatchlist>
let capturedCtx: WatchlistCtx | null = null

function CheckProbe(): null {
  const ctx = useWatchlist()
  const idxRef = React.useRef(0)
  React.useEffect(() => {
    // 컴포넌트 외부 캡처는 부수효과이므로 효과 안에서 수행 (react-hooks/globals)
    capturedCtx = ctx
    if (idxRef.current >= CHECK_ORDER.length) return
    const stock = CHECK_ORDER[idxRef.current]
    idxRef.current += 1
    ctx.toggleStock(stock)
  })
  return null
}

function getTabButton(container: HTMLElement, tab: 'all' | 'checked'): HTMLButtonElement {
  const btn = Array.from(container.querySelectorAll<HTMLButtonElement>('.stock-list-tab'))
    .find(b => (tab === 'all' ? b.textContent === '전체' : b.textContent?.startsWith('체크(')))
  if (!btn) throw new Error(`tab button not found: ${tab}`)
  return btn
}

function renderCheckedTab() {
  const utils = render(
    <WatchlistProvider>
      <CheckProbe />
      <StockList />
    </WatchlistProvider>,
  )
  fireEvent.click(getTabButton(utils.container, 'checked'))
  return utils
}

// DOM 순서대로 헤더/행을 읽어 그룹 구조화 — 헤더 뒤따르는 행을 해당 그룹에 배속
function readCheckedGroups(container: HTMLElement) {
  const nodes = Array.from(
    container.querySelectorAll<HTMLElement>('.sector-header, .stock-item--checked'),
  )
  const groups: { name: string; count: string; codes: string[] }[] = []
  for (const n of nodes) {
    if (n.classList.contains('sector-header')) {
      groups.push({
        name: n.querySelector('.sector-header-name')?.textContent ?? '',
        count: n.querySelector('.sector-header-count')?.textContent ?? '',
        codes: [],
      })
    } else {
      groups[groups.length - 1]?.codes.push(n.querySelector('.stock-item-code')?.textContent ?? '')
    }
  }
  return groups
}

function headers(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>('.sector-header'))
}

function findHeader(container: HTMLElement, name: string): HTMLElement | undefined {
  return headers(container).find(h => h.querySelector('.sector-header-name')?.textContent === name)
}

function findCheckedRow(container: HTMLElement, code: string): HTMLElement | undefined {
  return Array.from(container.querySelectorAll<HTMLElement>('.stock-item--checked'))
    .find(r => r.querySelector('.stock-item-code')?.textContent === code)
}

// AC-011 기대값 — 서버 픽스처에서 런타임 추출 (프로덕션 헬퍼 미사용)
function serverGroupNameOf(code: string): string {
  const group = SERVER_RESULTS.sectors.find(s => s.stocks.some(st => st.code === code))
  if (!group) throw new Error(`server group not found for ${code}`)
  return group.sector_name
}

// AC-016(b) 경로 ① 리터럴 — (a)에서 강원랜드 해제 후 6종목 상태의 exportText
// (체크 시각 순서 = Map 삽입 순서 유지: 롯데관광개발→인터파크→에이치엔티→케이아이엔엠→다우데이타→KB금융)
const EXPORT_TEXT_LITERAL = 'KRX:003490,KRX:035900,KRX:265960,KRX:036540,KRX:132890,KRX:105560'

// ── 테스트 ──

describe('StockList 체크 탭 그룹핑 통합 (SPEC-CHECKED-SECTOR-GROUP-001 M3)', () => {
  let fetchMock: ReturnType<typeof vi.fn>
  let clipboardWriteText: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.clearAllMocks()
    // WatchlistProvider가 상태를 저장소에 영속화할 가능성에 대비한 초기화 (키명 미가지 — 전체 클리어)
    window.localStorage.clear()
    window.sessionStorage.clear()
    mockUseScreen.mockReturnValue({ results: SERVER_RESULTS } as unknown as ReturnType<typeof useScreen>)
    capturedCtx = null
    fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)
    clipboardWriteText = vi.fn(() => Promise.resolve())
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: clipboardWriteText },
      configurable: true,
      writable: true,
    })
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('AC-CSG-001: 체크 탭이 섹터 헤더 구조로 렌더된다 (헤더 수 = 섹터 수, 헤더 앞 행 0개)', () => {
    const { container } = renderCheckedTab()

    // 규약 (f) 전제 확인 — 헤더+행 총 항목이 렌더 창(15) 안에 전부 들어옴
    const nodes = Array.from(
      container.querySelectorAll<HTMLElement>('.sector-header, .stock-item--checked'),
    )
    expect(nodes.length).toBeLessThanOrEqual(15)

    // 섹터 수만큼 헤더 — 가상화 잘림 없이
    expect(container.querySelectorAll('.sector-header').length).toBe(SERVER_RESULTS.sectors.length) // 4

    // 모든 체크 행은 어떤 헤더 뒤에 위치 (헤더보다 앞에 오는 종목 행 0개)
    let seenHeader = false
    for (const n of nodes) {
      if (n.classList.contains('sector-header')) {
        seenHeader = true
      } else {
        expect(seenHeader).toBe(true)
      }
    }
    expect(container.querySelectorAll('.stock-item--checked').length).toBe(CHECKED_COUNT) // 7
  })

  it('AC-CSG-002: 그룹 키가 "대분류 > 중분류" 형식이다 (공백 포함 바이트 동등)', () => {
    const { container } = renderCheckedTab()

    const header = findHeader(container, '내수 > 리조트')
    expect(header).toBeDefined()
    expect(header?.querySelector('.sector-header-name')?.textContent).toBe('내수 > 리조트')
  })

  it('AC-CSG-003: 결측 섹터가 기타/대분류-only로 처리된다 (잔존 구분자 없음)', () => {
    const { container } = renderCheckedTab()

    // (c) sector_major null → '기타' 헤더 아래 다우데이타
    const etcRow = findCheckedRow(container, '132890')
    expect(etcRow).toBeDefined()
    const groups = readCheckedGroups(container)
    expect(groups.find(g => g.name === '기타')?.codes).toEqual(['132890'])

    // (b) major-only → '금융' 헤더 아래 KB금융
    expect(groups.find(g => g.name === '금융')?.codes).toEqual(['105560'])

    // '기타 > ' 같은 구분자 잔존 텍스트 부재
    expect(container.textContent).not.toContain('기타 > ')
  })

  it('AC-CSG-004: 그룹 순서가 코드포인트 오름차순이다 (체크 순서 ≠ 정렬 순서 축)', () => {
    // 규약 (d) 자기 방어 — 체크 삽입 순서가 정렬 순서와 같으면 이 단언은 무력화됨
    expect(INSERTION_ORDER).not.toEqual(EXPECTED_SORTED_KEYS)

    const { container } = renderCheckedTab()

    const names = Array.from(container.querySelectorAll('.sector-header-name')).map(
      el => el.textContent,
    )
    expect(names).toEqual(EXPECTED_SORTED_KEYS)
  })

  it('AC-CSG-005: 헤더 카운트가 그 섹터의 체크 수다 (유니버스 stock_count 아님)', () => {
    const { container } = renderCheckedTab()

    const groups = readCheckedGroups(container)
    const byName = new Map(groups.map(g => [g.name, g]))

    // (e) 판별 축: '금융' 유니버스 3 ≠ 체크 1 — 카운트는 1이어야 함
    expect(byName.get('금융')?.count).toBe('1')
    expect(byName.get('금융')?.count).not.toBe('3')
    expect(byName.get('내수 > 리조트')?.count).toBe('4')
    expect(byName.get('기타')?.count).toBe('1')
    expect(byName.get('AI')?.count).toBe('1')

    // 카운트 = 각 헤더 아래 실제 행 수
    for (const g of groups) {
      expect(Number(g.count)).toBe(g.codes.length)
    }
  })

  it('AC-CSG-006 (DOM): 헤더 카운트 총합 = 탭 라벨 N = 렌더 행 총수 (3자 항등, 전 그룹 펼침)', () => {
    const { container } = renderCheckedTab()

    // 전 그룹 펼침 전제 확인
    expect(headers(container).map(h => h.getAttribute('aria-expanded'))).toEqual(
      Array.from({ length: SERVER_RESULTS.sectors.length }, () => 'true'),
    )

    const sumOfCounts = readCheckedGroups(container).reduce((acc, g) => acc + Number(g.count), 0)
    const tabLabel = getTabButton(container, 'checked').textContent ?? ''
    const labelN = Number(/체크\((\d+)\)/.exec(tabLabel)?.[1])
    const rowCount = container.querySelectorAll('.stock-item--checked').length

    expect(sumOfCounts).toBe(labelN)
    expect(labelN).toBe(rowCount)
    expect(labelN).toBe(CHECKED_COUNT) // 7
  })

  it('AC-CSG-006 (모델): buildCheckedGroups 그룹별 stocks 합 = checkedStocks.size (창·접힘 무관)', () => {
    renderCheckedTab()
    expect(capturedCtx).not.toBeNull()

    const groups = buildCheckedGroups(Array.from(capturedCtx!.checkedStocks.values()))
    expect(groups.reduce((acc, g) => acc + g.stocks.length, 0)).toBe(capturedCtx!.checkedStocks.size)
    expect(capturedCtx!.checkedStocks.size).toBe(CHECKED_COUNT) // 7
  })

  it('AC-CSG-007: 헤더 토글이 그 그룹만 접고 편다 (DOM 부재, 화살표/aria, 타 그룹 불변, 복원)', () => {
    const { container } = renderCheckedTab()

    const first = headers(container)[0]
    expect(first.querySelector('.sector-header-name')?.textContent).toBe('AI')
    expect(first.getAttribute('aria-expanded')).toBe('true')
    expect(first.querySelector('.sector-header-arrow')?.textContent).toBe('▼')

    fireEvent.click(first)

    // (1) 해당 그룹 행은 렌더 트리에서 부재 (CSS 숨김이 아님)
    expect(screen.queryByText('케이아이엔엠')).toBeNull()

    // (2) 헤더 잔존 + aria/화살표 전환 — 클릭 후 재렌더로 DOM 요소가 교체되므로
    //     클릭 전 참조(first)가 아니라 재조회한 요소로 단언한다 (stale 참조 방지)
    expect(headers(container).length).toBe(4)
    const collapsedHeader = findHeader(container, 'AI')!
    expect(collapsedHeader.getAttribute('aria-expanded')).toBe('false')
    expect(collapsedHeader.querySelector('.sector-header-arrow')?.textContent).toBe('▶')

    // (3) 다른 그룹 불변
    for (const name of ['강원랜드', '롯데관광개발', 'KB금융', '다우데이타']) {
      expect(screen.getByText(name)).toBeInTheDocument()
    }
    expect(findHeader(container, '내수 > 리조트')?.getAttribute('aria-expanded')).toBe('true')
    expect(container.querySelectorAll('.stock-item--checked').length).toBe(CHECKED_COUNT - 1) // 6

    // (4) 재클릭 → 원상 복구 (재조회 요소로 클릭)
    fireEvent.click(collapsedHeader)
    expect(screen.getByText('케이아이엔엠')).toBeInTheDocument()
    expect(findHeader(container, 'AI')?.getAttribute('aria-expanded')).toBe('true')
    expect(container.querySelectorAll('.stock-item--checked').length).toBe(CHECKED_COUNT)
  })

  it('AC-CSG-008: 마지막 종목 해제 시 해당 헤더가 같은 렌더에서 사라진다 (잔존 헤더 0개)', () => {
    const { container } = renderCheckedTab()

    // '금융' 그룹에는 체크 종목이 정확히 1개(KB금융)
    expect(readCheckedGroups(container).find(g => g.name === '금융')?.codes).toEqual(['105560'])

    const kbRow = findCheckedRow(container, '105560')
    const xBtn = kbRow?.querySelector<HTMLButtonElement>('.watchlist-remove-btn')
    expect(xBtn).toBeDefined()
    fireEvent.click(xBtn!)

    // 같은 렌더에서 '금융' 헤더 소멸
    expect(findHeader(container, '금융')).toBeUndefined()
    expect(screen.queryByText('KB금융')).toBeNull()

    // 나머지 섹터 구성 불변 + 자식 0개인 잔존 헤더 없음
    const groups = readCheckedGroups(container)
    expect(groups.map(g => g.name)).toEqual(['AI', '기타', '내수 > 리조트'])
    for (const g of groups) {
      expect(g.codes.length).toBeGreaterThan(0)
    }
    expect(container.querySelectorAll('.stock-item--checked').length).toBe(CHECKED_COUNT - 1) // 6
  })

  it('AC-CSG-009: 전체 탭에서 접은 섹터가 체크 탭에서는 펼침 상태다 (전파 없음 →)', () => {
    const { container } = render(
      <WatchlistProvider>
        <CheckProbe />
        <StockList />
      </WatchlistProvider>,
    )

    // 전체 탭에서 AI 접기 (클릭 후 재조회 — stale 참조 방지)
    const allAiHeader = findHeader(container, 'AI')
    expect(allAiHeader).toBeDefined()
    fireEvent.click(allAiHeader!)
    expect(findHeader(container, 'AI')?.getAttribute('aria-expanded')).toBe('false')

    // 체크 탭으로 전환 → AI는 펼침 + 체크 종목 행 노출
    fireEvent.click(getTabButton(container, 'checked'))
    const checkedAiHeader = findHeader(container, 'AI')
    expect(checkedAiHeader?.getAttribute('aria-expanded')).toBe('true')
    expect(checkedAiHeader?.querySelector('.sector-header-arrow')?.textContent).toBe('▼')
    expect(findCheckedRow(container, '036540')).toBeDefined()
  })

  it('AC-CSG-010: 체크 탭에서 접은 섹터가 전체 탭에서는 펼침 상태다 (전파 없음 ←)', () => {
    const { container } = render(
      <WatchlistProvider>
        <CheckProbe />
        <StockList />
      </WatchlistProvider>,
    )

    // 체크 탭에서 AI 접기 (클릭 후 재조회 — stale 참조 방지)
    fireEvent.click(getTabButton(container, 'checked'))
    const checkedAiHeader = findHeader(container, 'AI')
    expect(checkedAiHeader).toBeDefined()
    fireEvent.click(checkedAiHeader!)
    expect(findHeader(container, 'AI')?.getAttribute('aria-expanded')).toBe('false')

    // 전체 탭으로 전환 → AI는 펼침 + 종목 행 노출
    fireEvent.click(getTabButton(container, 'all'))
    const allAiHeader = findHeader(container, 'AI')
    expect(allAiHeader?.getAttribute('aria-expanded')).toBe('true')
    expect(screen.getByText('케이아이엔엠')).toBeInTheDocument()
  })

  it('AC-CSG-011: 체크 탭 섹터명이 서버 픽스처 sector_name과 바이트 동등하다 (크로스탭 동일성)', () => {
    const { container } = renderCheckedTab()

    // 기대값은 전부 서버 픽스처에서 런타임 추출 — 프로덕션 그룹 키 헬퍼 미사용 (양변 규칙)
    const groups = readCheckedGroups(container)
    for (const stock of CHECK_ORDER) {
      const expected = serverGroupNameOf(stock.code)
      const actual = groups.find(g => g.codes.includes(stock.code))?.name
      expect(actual).toBe(expected)
    }

    // major+minor 형식 그룹도 서버 문자열과 정확 일치 ('내수 > 리조트')
    expect(groups.find(g => g.codes.includes('035250'))?.name).toBe(
      serverGroupNameOf('035250'),
    )
  })

  it('AC-CSG-014: 그룹핑에 기인한 네트워크 요청이 0건이다 (탭 전환·토글·해제 전 시나리오)', () => {
    const { container } = renderCheckedTab()

    // 헤더 토글 (AI 그룹 접기)
    fireEvent.click(headers(container)[0])
    // 종목 해제 — 접지 않은 그룹(금융)의 종목으로 (접힌 그룹의 행은 렌더에 부재가 정상)
    const xBtn = findCheckedRow(container, '105560')?.querySelector<HTMLButtonElement>('.watchlist-remove-btn')
    expect(xBtn).toBeDefined()
    fireEvent.click(xBtn!)
    // 탭 복귀
    fireEvent.click(getTabButton(container, 'all'))

    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('AC-CSG-016: 체크 행 렌더 · Export 리터럴 기준선(①) · 전량 해제 시 빈 상태', async () => {
    const { container } = renderCheckedTab()

    // (a) 행에 종목명·코드·x 버튼 존재
    const kbRow = findCheckedRow(container, '105560')
    expect(kbRow?.querySelector('.stock-item-name')?.textContent).toBe('KB금융')
    expect(kbRow?.querySelector('.stock-item-code')?.textContent).toBe('105560')
    const xBtns = container.querySelectorAll('.watchlist-remove-btn')
    expect(xBtns.length).toBe(CHECKED_COUNT)

    // (a) x 클릭 시 해당 종목만 해제 — 강원랜드 해제 → 나머지 불변, 탭 라벨 7→6
    const gangwonX = findCheckedRow(container, '035250')?.querySelector<HTMLButtonElement>('.watchlist-remove-btn')
    fireEvent.click(gangwonX!)
    expect(screen.queryByText('강원랜드')).toBeNull()
    expect(container.querySelectorAll('.stock-item--checked').length).toBe(CHECKED_COUNT - 1) // 6
    expect(getTabButton(container, 'checked').textContent).toBe('체크(6)')

    // (b) Export → 클립보드 텍스트 = 리터럴 기대 문자열(①), 버튼 Copied! 전환
    const exportBtn = container.querySelector<HTMLButtonElement>('.stock-list-export-btn')
    expect(exportBtn).toBeDefined()
    expect(exportBtn!.disabled).toBe(false)
    await act(async () => {
      fireEvent.click(exportBtn!)
    })
    expect(clipboardWriteText).toHaveBeenCalledTimes(1)
    expect(clipboardWriteText).toHaveBeenCalledWith(EXPORT_TEXT_LITERAL)
    expect(exportBtn!.textContent).toBe('Copied!')

    // (c) 남은 6종목 전량 해제 → 빈 상태 메시지, 가상 목록·헤더 미렌더
    for (;;) {
      const btn = container.querySelector<HTMLButtonElement>('.watchlist-remove-btn')
      if (!btn) break
      fireEvent.click(btn)
    }
    expect(screen.getByText('체크된 종목이 없습니다.')).toBeInTheDocument()
    expect(container.querySelectorAll('.sector-header').length).toBe(0)
    expect(container.querySelectorAll('.stock-item--checked').length).toBe(0)
    expect(exportBtn!.disabled).toBe(true)
  })
})
