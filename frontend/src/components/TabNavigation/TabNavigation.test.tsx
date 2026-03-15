// RED: Tests for TabNavigation component
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TabNavigation } from './TabNavigation'
import { TabProvider } from '../../contexts/TabContext'

function renderWithTabProvider() {
  return render(
    <TabProvider>
      <TabNavigation />
    </TabProvider>
  )
}

describe('TabNavigation', () => {
  it('should render all 4 tabs', () => {
    renderWithTabProvider()
    expect(screen.getByText('Market Overview')).toBeInTheDocument()
    expect(screen.getByText('Sector Analysis')).toBeInTheDocument()
    expect(screen.getByText('Stock Explorer')).toBeInTheDocument()
    expect(screen.getByText('Chart Grid')).toBeInTheDocument()
  })

  it('should have Chart Grid as active by default', () => {
    renderWithTabProvider()
    const chartGridTab = screen.getByText('Chart Grid').closest('button')
    expect(chartGridTab).toHaveClass('tab-btn--active')
  })

  it('should switch active tab on click', async () => {
    const user = userEvent.setup()
    renderWithTabProvider()

    await user.click(screen.getByText('Market Overview'))

    const marketOverviewTab = screen.getByText('Market Overview').closest('button')
    expect(marketOverviewTab).toHaveClass('tab-btn--active')

    const chartGridTab = screen.getByText('Chart Grid').closest('button')
    expect(chartGridTab).not.toHaveClass('tab-btn--active')
  })

  it('should render tab navigation container with correct class', () => {
    const { container } = renderWithTabProvider()
    expect(container.querySelector('.tab-navigation')).toBeInTheDocument()
  })

  it('should render all tabs as tab elements', () => {
    renderWithTabProvider()
    const tabs = screen.getAllByRole('tab')
    expect(tabs).toHaveLength(4)
  })
})
