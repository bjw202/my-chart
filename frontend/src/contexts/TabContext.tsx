import React, { createContext, useCallback, useContext, useState } from 'react'
import type { TabId, CrossTabParams } from '../types/market'

interface TabContextValue {
  activeTab: TabId
  setActiveTab: (tab: TabId) => void
  navigateToTab: (tab: TabId, params?: CrossTabParams) => void
  crossTabParams: CrossTabParams | null
  clearCrossTabParams: () => void
}

const TabContext = createContext<TabContextValue | null>(null)

// @MX:ANCHOR: [AUTO] TabProvider is the central state hub for tab navigation
// @MX:REASON: Used by TabNavigation, AppContent, and any cross-tab nav trigger; high fan_in

export function TabProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  // Default active tab is 'chart-grid' per R1 requirement
  const [activeTab, setActiveTab] = useState<TabId>('chart-grid')
  const [crossTabParams, setCrossTabParams] = useState<CrossTabParams | null>(null)

  const navigateToTab = useCallback((tab: TabId, params?: CrossTabParams) => {
    setActiveTab(tab)
    setCrossTabParams(params ?? null)
  }, [])

  const clearCrossTabParams = useCallback(() => {
    setCrossTabParams(null)
  }, [])

  return (
    <TabContext.Provider value={{ activeTab, setActiveTab, navigateToTab, crossTabParams, clearCrossTabParams }}>
      {children}
    </TabContext.Provider>
  )
}

export function useTab(): TabContextValue {
  const ctx = useContext(TabContext)
  if (!ctx) throw new Error('useTab must be used within TabProvider')
  return ctx
}
