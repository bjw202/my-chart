// RED: SPEC-PRESET-001 AC-2/3/5/10/12 — PresetChips 컴포넌트 테스트 (Group B)
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PresetChips } from '../PresetChips'
import { FILTER_PRESETS } from '../../../presets/filter-presets'
import type { Preset } from '../../../types/filter'

// 테스트용 고정 프리셋 목록
const TEST_PRESETS: readonly Preset[] = FILTER_PRESETS

// REQ-PST-012 v1.0.2 에서 명시한 minervini_full 전용 title 문구 (정확 일치)
const MINERVINI_TOOLTIP =
  'SMA150 · 52주 저가(LOW_52W) · 20일 전 SMA200(SMA200_20D_AGO) 컬럼이 필요합니다. DB 업데이트(파일 재생성)를 먼저 실행하세요.'

describe('PresetChips 컴포넌트 (SPEC-PRESET-001)', () => {
  // B1: 3개 칩 버튼이 렌더되고 각각 올바른 라벨을 표시한다
  it('B1: 3개 프리셋 칩이 각각 올바른 라벨로 렌더된다', () => {
    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />
    )
    for (const preset of TEST_PRESETS) {
      expect(screen.getByRole('button', { name: preset.label })).toBeInTheDocument()
    }
  })

  // B1: 컨테이너 role="group" + aria-label
  it('B1: 컨테이너가 role="group"과 aria-label="필터 프리셋"을 가진다', () => {
    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />
    )
    const group = screen.getByRole('group', { name: '필터 프리셋' })
    expect(group).toBeInTheDocument()
  })

  // B2: 비활성 칩 클릭 → onApply가 정확한 Preset 인자로 1회 호출
  it('B2: 비활성 칩 클릭 시 onApply가 정확한 preset으로 1회 호출된다', async () => {
    const user = userEvent.setup()
    const onApply = vi.fn()
    const breakout = TEST_PRESETS.find((p) => p.id === 'breakout_init')!

    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={onApply}
        onClear={vi.fn()}
      />
    )

    await user.click(screen.getByRole('button', { name: breakout.label }))
    expect(onApply).toHaveBeenCalledTimes(1)
    expect(onApply).toHaveBeenCalledWith(breakout)
  })

  // B3: 활성 칩 클릭 → onClear가 1회 호출
  it('B3: 활성 칩 재클릭 시 onClear가 1회 호출된다', async () => {
    const user = userEvent.setup()
    const onClear = vi.fn()
    const onApply = vi.fn()
    const breakout = TEST_PRESETS.find((p) => p.id === 'breakout_init')!

    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={breakout.id}
        onApply={onApply}
        onClear={onClear}
      />
    )

    await user.click(screen.getByRole('button', { name: breakout.label }))
    expect(onClear).toHaveBeenCalledTimes(1)
    expect(onApply).not.toHaveBeenCalled()
  })

  // B4: 활성 칩은 aria-pressed="true", 나머지는 "false"
  it('B4: 활성 칩만 aria-pressed="true"이고 나머지는 "false"이다', () => {
    const minervini = TEST_PRESETS.find((p) => p.id === 'minervini_full')!

    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={minervini.id}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />
    )

    const activeBtn = screen.getByRole('button', { name: minervini.label })
    expect(activeBtn).toHaveAttribute('aria-pressed', 'true')

    for (const preset of TEST_PRESETS.filter((p) => p.id !== minervini.id)) {
      const btn = screen.getByRole('button', { name: preset.label })
      expect(btn).toHaveAttribute('aria-pressed', 'false')
    }
  })

  // B4: activePresetId=null이면 모든 칩이 aria-pressed="false"
  it('B4: activePresetId=null이면 모든 칩이 aria-pressed="false"이다', () => {
    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />
    )

    for (const preset of TEST_PRESETS) {
      const btn = screen.getByRole('button', { name: preset.label })
      expect(btn).toHaveAttribute('aria-pressed', 'false')
    }
  })

  // B5: Tab 순회 후 Enter/Space로 칩 활성화
  it('B5: Enter 키로 비활성 칩을 활성화할 수 있다', async () => {
    const user = userEvent.setup()
    const onApply = vi.fn()
    const breakout = TEST_PRESETS.find((p) => p.id === 'breakout_init')!

    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={onApply}
        onClear={vi.fn()}
      />
    )

    const btn = screen.getByRole('button', { name: breakout.label })
    btn.focus()
    await user.keyboard('{Enter}')
    expect(onApply).toHaveBeenCalledWith(breakout)
  })

  // B5: Space 키로도 칩 활성화 가능 (AC-10 접근성)
  it('B5: Space 키로 비활성 칩을 활성화할 수 있다', async () => {
    const user = userEvent.setup()
    const onApply = vi.fn()
    const breakout = TEST_PRESETS.find((p) => p.id === 'breakout_init')!

    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={onApply}
        onClear={vi.fn()}
      />
    )

    const btn = screen.getByRole('button', { name: breakout.label })
    btn.focus()
    await user.keyboard(' ')
    expect(onApply).toHaveBeenCalledWith(breakout)
  })

  // B6: minervini_full title은 DB 안내 문구 (정확 일치, REQ-PST-012)
  it('B6: minervini_full 칩의 title이 DB 안내 문구와 정확히 일치한다', () => {
    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />
    )

    const minervini = TEST_PRESETS.find((p) => p.id === 'minervini_full')!
    const btn = screen.getByRole('button', { name: minervini.label })
    expect(btn).toHaveAttribute('title', MINERVINI_TOOLTIP)
  })

  // B6: breakout_init title은 description과 일치
  it('B6: breakout_init 칩의 title은 preset.description과 일치한다', () => {
    const breakout = TEST_PRESETS.find((p) => p.id === 'breakout_init')!

    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />
    )

    const btn = screen.getByRole('button', { name: breakout.label })
    expect(btn).toHaveAttribute('title', breakout.description)
  })

  // B6: stage1_accumulation title은 description과 일치
  it('B6: stage1_accumulation 칩의 title은 preset.description과 일치한다', () => {
    const stage1 = TEST_PRESETS.find((p) => p.id === 'stage1_accumulation')!

    render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />
    )

    const btn = screen.getByRole('button', { name: stage1.label })
    expect(btn).toHaveAttribute('title', stage1.description)
  })

  // B6: 활성 상태 전환 후에도 title은 변하지 않는다 (state-invariant)
  it('B6: 활성/비활성 전환 후에도 minervini_full title이 변하지 않는다', () => {
    const minervini = TEST_PRESETS.find((p) => p.id === 'minervini_full')!
    const { rerender } = render(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={null}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />
    )

    // 비활성 상태에서 title 확인
    let btn = screen.getByRole('button', { name: minervini.label })
    expect(btn).toHaveAttribute('title', MINERVINI_TOOLTIP)

    // 활성 상태로 전환
    rerender(
      <PresetChips
        presets={TEST_PRESETS}
        activePresetId={minervini.id}
        onApply={vi.fn()}
        onClear={vi.fn()}
      />
    )

    btn = screen.getByRole('button', { name: minervini.label })
    expect(btn).toHaveAttribute('aria-pressed', 'true')
    expect(btn).toHaveAttribute('title', MINERVINI_TOOLTIP)
  })
})
