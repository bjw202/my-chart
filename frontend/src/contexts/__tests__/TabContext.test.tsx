// RED: Tests for TabContext
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TabProvider, useTab } from '../TabContext'

// Helper component that exposes context values
function TestConsumer(): React.ReactElement {
  const { activeTab, setActiveTab, navigateToTab, crossTabParams, clearCrossTabParams } = useTab()
  return (
    <div>
      <div data-testid="active-tab">{activeTab}</div>
      <div data-testid="cross-tab-params">{JSON.stringify(crossTabParams)}</div>
      <button onClick={() => setActiveTab('market-overview')}>Set Market Overview</button>
      <button onClick={() => navigateToTab('sector-analysis', { sectorName: 'IT' })}>Navigate to Sector</button>
      <button onClick={() => clearCrossTabParams()}>Clear Params</button>
    </div>
  )
}

describe('TabProvider', () => {
  it('should have chart-grid as default active tab', () => {
    render(
      <TabProvider>
        <TestConsumer />
      </TabProvider>
    )
    expect(screen.getByTestId('active-tab').textContent).toBe('chart-grid')
  })

  it('should update active tab via setActiveTab', async () => {
    const user = userEvent.setup()
    render(
      <TabProvider>
        <TestConsumer />
      </TabProvider>
    )
    await user.click(screen.getByText('Set Market Overview'))
    expect(screen.getByTestId('active-tab').textContent).toBe('market-overview')
  })

  it('should navigate to a tab with params via navigateToTab', async () => {
    const user = userEvent.setup()
    render(
      <TabProvider>
        <TestConsumer />
      </TabProvider>
    )
    await user.click(screen.getByText('Navigate to Sector'))
    expect(screen.getByTestId('active-tab').textContent).toBe('sector-analysis')
    expect(JSON.parse(screen.getByTestId('cross-tab-params').textContent ?? '{}')).toEqual({ sectorName: 'IT' })
  })

  it('should clear cross tab params via clearCrossTabParams', async () => {
    const user = userEvent.setup()
    render(
      <TabProvider>
        <TestConsumer />
      </TabProvider>
    )
    await user.click(screen.getByText('Navigate to Sector'))
    await user.click(screen.getByText('Clear Params'))
    expect(screen.getByTestId('cross-tab-params').textContent).toBe('null')
  })

  it('should have null crossTabParams initially', () => {
    render(
      <TabProvider>
        <TestConsumer />
      </TabProvider>
    )
    expect(screen.getByTestId('cross-tab-params').textContent).toBe('null')
  })
})

describe('useTab hook', () => {
  it('should throw when used outside TabProvider', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    expect(() => render(<TestConsumer />)).toThrow('useTab must be used within TabProvider')
    consoleError.mockRestore()
  })
})
