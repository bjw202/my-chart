// RED: Tests for TabContext — NavIntent addressing contract (AC-SUX-003, SPEC-SECTOR-UX-001 M3)
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useEffect, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import { TabProvider, useTab, useNavIntent } from '../TabContext'
import type { TabId, NavIntentPayload } from '../../types/market'

// Consumer that applies the canonical 3-condition guard (plan §3.1):
// (1) intent.target === MY_TAB_ID, (2) activeTab === MY_TAB_ID, (3) lastHandled.current !== intent.id
// NO global clear call (AC-SUX-005).
function GuardedConsumer({ tabId, spy }: { tabId: TabId; spy: (p: NavIntentPayload) => void }): ReactElement {
  const { intent } = useNavIntent()
  const { activeTab } = useTab()
  const lastHandled = useRef<number | null>(null)
  useEffect(() => {
    if (!intent) return
    if (intent.target !== tabId) return
    if (activeTab !== tabId) return
    if (lastHandled.current === intent.id) return
    lastHandled.current = intent.id
    spy(intent.payload)
  }, [intent, activeTab, tabId, spy])
  return <div data-testid={`consumer-${tabId}`} />
}

// Producer that triggers navigate({ target, payload })
function Producer({ target, payload, label }: { target: TabId; payload?: NavIntentPayload; label: string }): ReactElement {
  const { navigate } = useNavIntent()
  return (
    <button type="button" onClick={() => navigate({ target, payload })}>
      {label}
    </button>
  )
}

// Helper that also exposes intent + activeTab for direct inspection
function Probe(): ReactElement {
  const { intent } = useNavIntent()
  const { activeTab } = useTab()
  return (
    <>
      <div data-testid="active-tab">{activeTab}</div>
      <div data-testid="intent">{intent === null ? 'null' : JSON.stringify(intent)}</div>
    </>
  )
}

describe('TabProvider — active tab', () => {
  it('should have chart-grid as default active tab', () => {
    render(
      <TabProvider>
        <Probe />
      </TabProvider>,
    )
    expect(screen.getByTestId('active-tab').textContent).toBe('chart-grid')
  })

  it('should update active tab via setActiveTab', async () => {
    function Setter(): ReactElement {
      const { setActiveTab } = useTab()
      return (
        <button type="button" onClick={() => setActiveTab('market-overview')}>
          Set Market Overview
        </button>
      )
    }
    const user = userEvent.setup()
    render(
      <TabProvider>
        <Setter />
        <Probe />
      </TabProvider>,
    )
    await user.click(screen.getByText('Set Market Overview'))
    expect(screen.getByTestId('active-tab').textContent).toBe('market-overview')
  })
})

describe('NavIntent addressing (AC-SUX-003)', () => {
  it('only the addressed consumer handles the intent (target routing)', async () => {
    const user = userEvent.setup()
    const stockSpy = vi.fn()
    const sectorSpy = vi.fn()
    render(
      <TabProvider>
        <Probe />
        <GuardedConsumer tabId="stock-explorer" spy={stockSpy} />
        <GuardedConsumer tabId="sector-analysis" spy={sectorSpy} />
        <Producer target="stock-explorer" payload={{ focusStock: '삼성전자' }} label="go-stock" />
      </TabProvider>,
    )
    expect(stockSpy).not.toHaveBeenCalled()
    await user.click(screen.getByText('go-stock'))
    expect(screen.getByTestId('active-tab').textContent).toBe('stock-explorer')
    expect(stockSpy).toHaveBeenCalledTimes(1)
    expect(stockSpy).toHaveBeenCalledWith({ focusStock: '삼성전자' })
    // sector consumer MUST NOT have handled (target routing)
    expect(sectorSpy).not.toHaveBeenCalled()
  })

  it('re-sending the same payload increments id so the consumer handles twice', async () => {
    const user = userEvent.setup()
    const stockSpy = vi.fn()
    render(
      <TabProvider>
        <GuardedConsumer tabId="stock-explorer" spy={stockSpy} />
        <Producer target="stock-explorer" payload={{ focusStock: '삼성전자' }} label="go-stock" />
      </TabProvider>,
    )
    await user.click(screen.getByText('go-stock'))
    await user.click(screen.getByText('go-stock'))
    // id increments on every navigate → consumer handles twice (re-send distinction)
    expect(stockSpy).toHaveBeenCalledTimes(2)
  })

  it('a re-render on the same id is handled only once (dedup)', async () => {
    const user = userEvent.setup()
    const stockSpy = vi.fn()
    // Wrapper that can force a re-render via a state toggle
    function Rerenderer(): ReactElement {
      const [, setTick] = useState(0)
      return (
        <>
          <GuardedConsumer tabId="stock-explorer" spy={stockSpy} />
          <Producer target="stock-explorer" payload={{ focusStock: '삼성전자' }} label="go-stock" />
          <button type="button" onClick={() => setTick((t) => t + 1)}>
            rerender
          </button>
        </>
      )
    }
    render(
      <TabProvider>
        <Rerenderer />
      </TabProvider>,
    )
    await user.click(screen.getByText('go-stock'))
    expect(stockSpy).toHaveBeenCalledTimes(1)
    // force re-renders — the same intent id is already in lastHandled → no re-handle
    await user.click(screen.getByText('rerender'))
    await user.click(screen.getByText('rerender'))
    expect(stockSpy).toHaveBeenCalledTimes(1)
  })

  it('switching activeTab away does not re-handle the same intent (activeTab guard + dedup)', async () => {
    const user = userEvent.setup()
    const stockSpy = vi.fn()
    function Switcher(): ReactElement {
      const { setActiveTab } = useTab()
      return (
        <button type="button" onClick={() => setActiveTab('chart-grid')}>
          leave
        </button>
      )
    }
    render(
      <TabProvider>
        <GuardedConsumer tabId="stock-explorer" spy={stockSpy} />
        <Producer target="stock-explorer" payload={{ focusStock: '삼성전자' }} label="go-stock" />
        <Switcher />
      </TabProvider>,
    )
    await user.click(screen.getByText('go-stock'))
    expect(stockSpy).toHaveBeenCalledTimes(1)
    // leaving the tab does not re-handle the already-consumed intent
    await user.click(screen.getByText('leave'))
    expect(stockSpy).toHaveBeenCalledTimes(1)
  })

  it('navigate sets intent with id/target/payload and no sectorName in payload', async () => {
    const user = userEvent.setup()
    render(
      <TabProvider>
        <Probe />
        <Producer target="chart-grid" payload={{ stockCodes: ['005930'] }} label="go-grid" />
      </TabProvider>,
    )
    expect(screen.getByTestId('intent').textContent).toBe('null')
    await user.click(screen.getByText('go-grid'))
    const intent = JSON.parse(screen.getByTestId('intent').textContent ?? 'null')
    expect(intent).not.toBeNull()
    expect(intent.id).toBeTypeOf('number')
    expect(intent.target).toBe('chart-grid')
    expect(intent.payload).toEqual({ stockCodes: ['005930'] })
    // AC-SUX-006: sectorName MUST NOT appear in payload
    expect(intent.payload).not.toHaveProperty('sectorName')
  })
})

describe('hook guards', () => {
  it('useTab throws when used outside TabProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    function TabOnly(): ReactElement {
      useTab()
      return <div />
    }
    expect(() => render(<TabOnly />)).toThrow('useTab must be used within TabProvider')
    consoleError.mockRestore()
  })

  it('useNavIntent throws when used outside TabProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    expect(() => render(<Producer target="chart-grid" label="x" />)).toThrow(
      'useNavIntent must be used within TabProvider',
    )
    consoleError.mockRestore()
  })
})
