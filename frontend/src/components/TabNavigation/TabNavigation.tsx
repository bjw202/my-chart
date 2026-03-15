import React from 'react'
import { useTab } from '../../contexts/TabContext'
import type { TabId } from '../../types/market'

interface TabConfig {
  id: TabId
  label: string
}

const TABS: TabConfig[] = [
  { id: 'market-overview', label: 'Market Overview' },
  { id: 'sector-analysis', label: 'Sector Analysis' },
  { id: 'stock-explorer', label: 'Stock Explorer' },
  { id: 'chart-grid', label: 'Chart Grid' },
]

// @MX:ANCHOR: [AUTO] TabNavigation renders the 4-tab header bar for the app
// @MX:REASON: Consumed by AppContent (App.tsx); single source of truth for tab UI

export function TabNavigation(): React.ReactElement {
  const { activeTab, setActiveTab } = useTab()

  return (
    <div className="tab-navigation">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`tab-btn${activeTab === tab.id ? ' tab-btn--active' : ''}`}
          onClick={() => setActiveTab(tab.id)}
          aria-selected={activeTab === tab.id}
          role="tab"
        >
          {tab.label}
        </button>
      ))}
    </div>
  )
}
