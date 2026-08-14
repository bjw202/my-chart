// RED: AC-SUX-001 — AnalysisParamsContext 계약 (초기값 + 읽기전용 필드 쓰기 API 비노출 + 세션 지속)
import { describe, it, expect } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { AnalysisParamsProvider, useAnalysisParams } from '../AnalysisParamsContext'

// 테스트 소비자 — context 값을 화면에 노출
function AnalysisParamsConsumer(): React.ReactElement {
  const { market, period, asOfDate, asOfIsPartialWeek, gridVersion } = useAnalysisParams()
  return (
    <div>
      <span data-testid="market">{market}</span>
      <span data-testid="period">{period}</span>
      <span data-testid="as-of-date">{String(asOfDate)}</span>
      <span data-testid="as-of-is-partial-week">{String(asOfIsPartialWeek)}</span>
      <span data-testid="grid-version">{String(gridVersion)}</span>
    </div>
  )
}

// 쓰기 소비자 — setMarket/setPeriod 를 호출하는 트리거
function WriteConsumer(): React.ReactElement {
  const { market, period, setMarket, setPeriod } = useAnalysisParams()
  return (
    <div>
      <span data-testid="w-market">{market}</span>
      <span data-testid="w-period">{period}</span>
      <button data-testid="set-kospi" onClick={() => setMarket('kospi')}>KOSPI</button>
      <button data-testid="set-1w" onClick={() => setPeriod('1w')}>1W</button>
    </div>
  )
}

describe('AC-SUX-001 — AnalysisParamsContext 계약', () => {
  it('초기값: market="all", period="1m", asOfDate=null, asOfIsPartialWeek=false', () => {
    render(
      <AnalysisParamsProvider>
        <AnalysisParamsConsumer />
      </AnalysisParamsProvider>,
    )
    expect(screen.getByTestId('market').textContent).toBe('all')
    expect(screen.getByTestId('period').textContent).toBe('1m')
    expect(screen.getByTestId('as-of-date').textContent).toBe('null')
    expect(screen.getByTestId('as-of-is-partial-week').textContent).toBe('false')
    expect(screen.getByTestId('grid-version').textContent).toBe('null')
  })

  it('읽기전용 필드(asOfDate/asOfIsPartialWeek/gridVersion) 의 쓰기 API 가 노출되지 않는다', () => {
    function KeysConsumer(): React.ReactElement {
      const value = useAnalysisParams()
      return <span data-testid="value-keys">{Object.keys(value).sort().join(',')}</span>
    }
    render(
      <AnalysisParamsProvider>
        <KeysConsumer />
      </AnalysisParamsProvider>,
    )
    const keys = screen.getByTestId('value-keys').textContent ?? ''
    // 사용자 제어 setter 는 노출
    expect(keys).toContain('setMarket')
    expect(keys).toContain('setPeriod')
    // 읽기전용 필드의 setter 는 비노출 (서버 응답 기록 전용 내부 경로만 갱신 — AC-SUX-001)
    expect(keys).not.toContain('setAsOfDate')
    expect(keys).not.toContain('setAsOfIsPartialWeek')
    expect(keys).not.toContain('setGridVersion')
    expect(keys).not.toContain('recordAsOf')
  })

  it('세션 지속: setMarket("kospi") 후 탭 전환(리렌더) 시뮬레이션 후에도 값이 유지된다', async () => {
    const user = userEvent.setup()
    function Tree(): React.ReactElement {
      return (
        <AnalysisParamsProvider>
          <WriteConsumer />
          <AnalysisParamsConsumer />
        </AnalysisParamsProvider>
      )
    }
    const { rerender } = render(<Tree />)
    // 초기 all
    expect(screen.getByTestId('market').textContent).toBe('all')
    // 시장 변경
    await user.click(screen.getByTestId('set-kospi'))
    expect(screen.getByTestId('market').textContent).toBe('kospi')
    // 탭 전환 시뮬레이션 — Provider 트리가 리렌더 되어도 상태는 유지
    await act(async () => {
      rerender(<Tree />)
    })
    expect(screen.getByTestId('market').textContent).toBe('kospi')
  })

  it('period 도 세션 지속 — setPeriod("1w") 후 리렌더 시 유지', async () => {
    const user = userEvent.setup()
    function Tree(): React.ReactElement {
      return (
        <AnalysisParamsProvider>
          <WriteConsumer />
        </AnalysisParamsProvider>
      )
    }
    const { rerender } = render(<Tree />)
    await user.click(screen.getByTestId('set-1w'))
    expect(screen.getByTestId('w-period').textContent).toBe('1w')
    await act(async () => {
      rerender(<Tree />)
    })
    expect(screen.getByTestId('w-period').textContent).toBe('1w')
  })
})
