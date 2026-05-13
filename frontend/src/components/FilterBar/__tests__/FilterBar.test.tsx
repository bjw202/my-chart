// RED: SPEC-PRESET-001 AC-2/3/4/5/6 — FilterBar 통합 테스트 (Group C)
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { FilterBar } from '../FilterBar'
import { ScreenProvider } from '../../../contexts/ScreenContext'
import { FILTER_PRESETS } from '../../../presets/filter-presets'
import { applyPatch } from '../../../presets/utils'
import { DEFAULT_SCREEN_REQUEST } from '../../../types/filter'

// api/screen 모킹 — 네트워크 요청 방지
vi.mock('../../../api/screen', () => ({
  screenStocks: vi.fn().mockResolvedValue({ total: 0, sectors: [] }),
}))

import { screenStocks } from '../../../api/screen'

// 테스트용 래퍼 컴포넌트
function TestWrapper(): React.ReactElement {
  return (
    <ScreenProvider>
      <FilterBar />
    </ScreenProvider>
  )
}

describe('FilterBar — PresetChips 통합 (SPEC-PRESET-001)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // URL 초기화
    window.history.replaceState(null, '', '/')
  })

  afterEach(() => {
    window.history.replaceState(null, '', '/')
  })

  // C1: breakout_init 칩 클릭 → 폼 필드 반영 + applyFilters 1회 호출
  it('C1: breakout_init 칩 클릭 시 applyFilters가 merged 상태로 1회 호출된다', async () => {
    const user = userEvent.setup()
    const breakout = FILTER_PRESETS.find((p) => p.id === 'breakout_init')!
    const expected = applyPatch(DEFAULT_SCREEN_REQUEST, breakout.patch)

    render(<TestWrapper />)

    const chipBtn = screen.getByRole('button', { name: breakout.label })
    await user.click(chipBtn)

    await waitFor(() => {
      expect(screenStocks).toHaveBeenCalledTimes(1)
      expect(screenStocks).toHaveBeenCalledWith(expected)
    })
  })

  // C1: patterns 완전 치환 검증 (A2: concat 아님)
  it('C1: breakout_init 적용 후 patterns 길이가 preset.patch.patterns.length와 일치한다', async () => {
    const user = userEvent.setup()
    const breakout = FILTER_PRESETS.find((p) => p.id === 'breakout_init')!

    render(<TestWrapper />)

    const chipBtn = screen.getByRole('button', { name: breakout.label })
    await user.click(chipBtn)

    await waitFor(() => {
      expect(screenStocks).toHaveBeenCalledWith(
        expect.objectContaining({
          patterns: expect.arrayContaining(breakout.patch.patterns!),
        })
      )
    })

    const calledWith = (screenStocks as ReturnType<typeof vi.fn>).mock.calls[0][0]
    expect(calledWith.patterns).toHaveLength(breakout.patch.patterns!.length)
  })

  // C1: 칩이 aria-pressed="true"가 된다
  it('C1: breakout_init 클릭 후 해당 칩이 aria-pressed="true"가 된다', async () => {
    const user = userEvent.setup()
    const breakout = FILTER_PRESETS.find((p) => p.id === 'breakout_init')!

    render(<TestWrapper />)

    const chipBtn = screen.getByRole('button', { name: breakout.label })
    await user.click(chipBtn)

    await waitFor(() => {
      expect(chipBtn).toHaveAttribute('aria-pressed', 'true')
    })
  })

  // C2: 드리프트 감지 — minervini_full 적용 후 RS 수정 → activePresetId = null
  it('C2: 활성 프리셋 적용 후 RS 값을 수정하면 모든 칩이 aria-pressed="false"가 된다', async () => {
    const user = userEvent.setup()
    const minervini = FILTER_PRESETS.find((p) => p.id === 'minervini_full')!

    render(<TestWrapper />)

    // minervini_full 프리셋 적용
    const chipBtn = screen.getByRole('button', { name: minervini.label })
    await user.click(chipBtn)

    await waitFor(() => {
      expect(chipBtn).toHaveAttribute('aria-pressed', 'true')
    })

    // RS 입력 필드 수정 (드리프트 유발)
    const rsInput = screen.getByPlaceholderText('최소 RS')
    await user.clear(rsInput)
    await user.type(rsInput, '80')

    // 모든 칩이 비활성화된다
    await waitFor(() => {
      for (const preset of FILTER_PRESETS) {
        const btn = screen.getByRole('button', { name: preset.label })
        expect(btn).toHaveAttribute('aria-pressed', 'false')
      }
    })
  })

  // C3: URL 반영 — 칩 적용 시 ?preset=<id> URL 업데이트
  it('C3: 칩 클릭 후 window.location.search에 ?preset=<id>가 포함된다', async () => {
    const user = userEvent.setup()
    const breakout = FILTER_PRESETS.find((p) => p.id === 'breakout_init')!

    render(<TestWrapper />)

    const chipBtn = screen.getByRole('button', { name: breakout.label })
    await user.click(chipBtn)

    await waitFor(() => {
      expect(window.location.search).toContain(`preset=${breakout.id}`)
    })
  })

  // C3: 드리프트 시 URL에서 preset 파라미터 제거
  it('C3: 드리프트 발생 시 URL에서 preset 파라미터가 제거된다', async () => {
    const user = userEvent.setup()
    const minervini = FILTER_PRESETS.find((p) => p.id === 'minervini_full')!

    render(<TestWrapper />)

    // 프리셋 적용
    const chipBtn = screen.getByRole('button', { name: minervini.label })
    await user.click(chipBtn)

    await waitFor(() => {
      expect(window.location.search).toContain('preset=')
    })

    // RS 값 수정 (드리프트)
    const rsInput = screen.getByPlaceholderText('최소 RS')
    await user.clear(rsInput)
    await user.type(rsInput, '80')

    await waitFor(() => {
      expect(window.location.search).not.toContain('preset=')
    })
  })

  // C4: 초기 마운트 자동 적용 — ?preset=stage1_accumulation URL에서 마운트
  it('C4: ?preset=stage1_accumulation URL로 마운트 시 해당 프리셋이 자동 적용된다', async () => {
    const stage1 = FILTER_PRESETS.find((p) => p.id === 'stage1_accumulation')!
    const expected = applyPatch(DEFAULT_SCREEN_REQUEST, stage1.patch)

    // 초기 URL 설정 (render 전)
    window.history.replaceState(null, '', '/?preset=stage1_accumulation')

    render(<TestWrapper />)

    // 칩이 활성 상태가 되기를 기다린다 (초기 마운트 effect 완료 후)
    await waitFor(() => {
      const chipBtn = screen.getByRole('button', { name: stage1.label })
      expect(chipBtn).toHaveAttribute('aria-pressed', 'true')
    })

    // screenStocks가 expected 상태로 호출되었음을 확인
    expect(screenStocks).toHaveBeenCalledWith(expected)
  })

  // 기본 폼 렌더링 및 검색 버튼
  it('FilterBar에 검색 버튼과 초기화 버튼이 렌더된다', () => {
    render(<TestWrapper />)
    expect(screen.getByText('검색')).toBeInTheDocument()
    expect(screen.getByText('초기화')).toBeInTheDocument()
  })

  // 초기화 버튼 클릭 시 clearResults 호출 (회귀 방어)
  it('초기화 버튼 클릭 시 모든 칩이 aria-pressed="false"가 된다', async () => {
    const user = userEvent.setup()
    const breakout = FILTER_PRESETS.find((p) => p.id === 'breakout_init')!

    render(<TestWrapper />)

    // 프리셋 적용
    const chipBtn = screen.getByRole('button', { name: breakout.label })
    await user.click(chipBtn)
    await waitFor(() => {
      expect(chipBtn).toHaveAttribute('aria-pressed', 'true')
    })

    // 초기화 클릭
    const resetBtn = screen.getByText('초기화')
    await user.click(resetBtn)

    await waitFor(() => {
      for (const preset of FILTER_PRESETS) {
        const btn = screen.getByRole('button', { name: preset.label })
        expect(btn).toHaveAttribute('aria-pressed', 'false')
      }
    })
  })

  // RED: 초기화 버튼 클릭 시 onReset 콜백이 호출되어야 한다 (검색 종목 stale state 방지)
  // Reproduction: 검색 종목 주입 후 초기화 → searchedStock도 reset되어야 다음 검색이 정상 동작
  it('초기화 버튼 클릭 시 onReset 콜백이 호출된다 (searchedStock reset)', async () => {
    const user = userEvent.setup()
    const onReset = vi.fn()

    render(
      <ScreenProvider>
        <FilterBar onReset={onReset} />
      </ScreenProvider>,
    )

    const resetBtn = screen.getByText('초기화')
    await user.click(resetBtn)

    expect(onReset).toHaveBeenCalledTimes(1)
  })

  // RED: 활성 preset 칩 재클릭 시에도 onReset 콜백이 호출되어야 한다 (handlePresetClear = handleReset)
  it('활성 preset 칩 재클릭 시에도 onReset 콜백이 호출된다', async () => {
    const user = userEvent.setup()
    const onReset = vi.fn()
    const breakout = FILTER_PRESETS.find((p) => p.id === 'breakout_init')!

    render(
      <ScreenProvider>
        <FilterBar onReset={onReset} />
      </ScreenProvider>,
    )

    // 프리셋 적용 → 활성화
    const chipBtn = screen.getByRole('button', { name: breakout.label })
    await user.click(chipBtn)
    await waitFor(() => {
      expect(chipBtn).toHaveAttribute('aria-pressed', 'true')
    })

    // 활성 칩 재클릭 → onReset 호출
    await user.click(chipBtn)

    expect(onReset).toHaveBeenCalledTimes(1)
  })

  // C4: 알 수 없는 preset id는 조용히 무시 (A9)
  it('C4: 알 수 없는 ?preset=unknown URL은 조용히 무시하고 기본 상태를 유지한다', async () => {
    window.history.replaceState(null, '', '/?preset=unknown-id-that-does-not-exist')

    render(<TestWrapper />)

    // 모든 칩이 비활성 상태임을 waitFor로 확인 (실 타이머 의존 제거)
    await waitFor(() => {
      for (const preset of FILTER_PRESETS) {
        const btn = screen.getByRole('button', { name: preset.label })
        expect(btn).toHaveAttribute('aria-pressed', 'false')
      }
    })

    // applyFilters가 호출되지 않음을 최종 확인
    expect(screenStocks).not.toHaveBeenCalled()
  })

  // AC-6: 드리프트 시 preset 파라미터만 제거되고 다른 쿼리 파라미터는 보존된다
  it('AC-6: ?other=foo&preset=<id>에서 드리프트 발생 시 other=foo는 유지된다', async () => {
    const user = userEvent.setup()
    const breakout = FILTER_PRESETS.find((p) => p.id === 'breakout_init')!

    // 다른 쿼리 파라미터와 함께 preset을 포함한 URL로 마운트
    window.history.replaceState(null, '', `/?other=foo&preset=${breakout.id}`)

    render(<TestWrapper />)

    // 초기 자동 적용으로 breakout_init이 활성화되기를 기다린다
    await waitFor(() => {
      const chipBtn = screen.getByRole('button', { name: breakout.label })
      expect(chipBtn).toHaveAttribute('aria-pressed', 'true')
    })

    // 드리프트 유발: RS 값 수정
    const rsInput = screen.getByPlaceholderText('최소 RS')
    await user.clear(rsInput)
    await user.type(rsInput, '99')

    // preset은 제거되지만 other=foo는 보존
    await waitFor(() => {
      const params = new URLSearchParams(window.location.search)
      expect(params.get('preset')).toBeNull()
      expect(params.get('other')).toBe('foo')
    })
  })

  // AC-3: 활성 칩 재클릭 시 screenStocks가 추가로 호출되지 않는다 (토글 오프, applyFilters 금지)
  it('AC-3: 활성 칩 재클릭 시 screenStocks는 추가 호출되지 않고 토글 오프된다', async () => {
    const user = userEvent.setup()
    const breakout = FILTER_PRESETS.find((p) => p.id === 'breakout_init')!

    render(<TestWrapper />)

    const chipBtn = screen.getByRole('button', { name: breakout.label })

    // 1회차 클릭: 적용
    await user.click(chipBtn)
    await waitFor(() => {
      expect(chipBtn).toHaveAttribute('aria-pressed', 'true')
      expect(screenStocks).toHaveBeenCalledTimes(1)
    })

    // 2회차 클릭: 토글 오프 — screenStocks 추가 호출 금지
    await user.click(chipBtn)
    await waitFor(() => {
      expect(chipBtn).toHaveAttribute('aria-pressed', 'false')
    })

    // 총 호출 횟수는 여전히 1회 (REQ-PST-004: applyFilters 호출 금지)
    expect(screenStocks).toHaveBeenCalledTimes(1)
    // URL에서 preset 파라미터도 제거됨
    expect(window.location.search).not.toContain('preset=')
  })
})
