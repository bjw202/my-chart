// RED: AC-SUX-002 — SelectionContext 계약 (초기값 + 화면 간 읽기 + 비소멸)
import { describe, it, expect } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { SelectionProvider, useSelection } from '../SelectionContext'

// 소비자 A — selectedSector 표시 + 선택 버튼
function ReaderA(): React.ReactElement {
  const { selectedSector, selectSector } = useSelection()
  return (
    <div>
      <span data-testid="reader-a-sector">{String(selectedSector)}</span>
      <button data-testid="select-a" onClick={() => selectSector('반도체')}>선택 A</button>
    </div>
  )
}

// 소비자 B — 다른 화면에서 selectedSector 를 읽는다
function ReaderB(): React.ReactElement {
  const { selectedSector } = useSelection()
  return <span data-testid="reader-b-sector">{String(selectedSector)}</span>
}

describe('AC-SUX-002 — SelectionContext 계약', () => {
  it('초기값: selectedSector=null, sectorScopeFollow=true', () => {
    function InitConsumer(): React.ReactElement {
      const { selectedSector, sectorScopeFollow } = useSelection()
      return (
        <div>
          <span data-testid="sel-sector">{String(selectedSector)}</span>
          <span data-testid="scope-follow">{String(sectorScopeFollow)}</span>
        </div>
      )
    }
    render(
      <SelectionProvider>
        <InitConsumer />
      </SelectionProvider>,
    )
    expect(screen.getByTestId('sel-sector').textContent).toBe('null')
    expect(screen.getByTestId('scope-follow').textContent).toBe('true')
  })

  it('임의 화면에서 selectSector("반도체") 호출 후 다른 화면 소비자가 "반도체" 를 읽는다', async () => {
    const user = userEvent.setup()
    render(
      <SelectionProvider>
        <ReaderA />
        <ReaderB />
      </SelectionProvider>,
    )
    // 초기 — 둘 다 null
    expect(screen.getByTestId('reader-a-sector').textContent).toBe('null')
    expect(screen.getByTestId('reader-b-sector').textContent).toBe('null')

    // 소비자 A 에서 선택
    await user.click(screen.getByTestId('select-a'))
    // 다른 화면 소비자 B 가 같은 값을 본다
    expect(screen.getByTestId('reader-a-sector').textContent).toBe('반도체')
    expect(screen.getByTestId('reader-b-sector').textContent).toBe('반도체')
  })

  it('비소멸: 두 소비자가 연속으로 읽어도 둘 다 값을 본다 (context 재평가 후에도 유지)', async () => {
    const user = userEvent.setup()
    function Tree(): React.ReactElement {
      return (
        <SelectionProvider>
          <ReaderA />
          <ReaderB />
        </SelectionProvider>
      )
    }
    const { rerender } = render(<Tree />)
    await user.click(screen.getByTestId('select-a'))
    expect(screen.getByTestId('reader-a-sector').textContent).toBe('반도체')
    expect(screen.getByTestId('reader-b-sector').textContent).toBe('반도체')
    // 리렌더(화면 전환 시뮬레이션) 후에도 두 소비자 모두 값을 유지
    await act(async () => {
      rerender(<Tree />)
    })
    expect(screen.getByTestId('reader-a-sector').textContent).toBe('반도체')
    expect(screen.getByTestId('reader-b-sector').textContent).toBe('반도체')
  })
})
