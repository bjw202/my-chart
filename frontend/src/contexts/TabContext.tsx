// TabContext — active tab + NavIntent (cross-tab navigation single source of truth).
// SPEC-SECTOR-UX-001 M3: NavIntent replaces the legacy cross-tab params API (REQ-SUX-003/004/005).
// Consumers guard on 3 conditions (target / activeTab / lastHandledId); there is NO global clear.
import React, { createContext, useCallback, useContext, useRef, useState } from 'react'
import type { TabId, NavIntent, NavIntentPayload } from '../types/market'

interface TabContextValue {
  activeTab: TabId
  setActiveTab: (tab: TabId) => void
}

interface NavIntentValue {
  intent: NavIntent | null
  // navigate() emits an addressed intent with a fresh monotonic id and switches activeTab.
  // Single-object call form: navigate({ target, payload }) — matches AC-SUX-003.
  // payload intentionally omits sectorName (REQ-SUX-005 / SM-4).
  navigate: (args: { target: TabId; payload?: NavIntentPayload }) => void
}

type FullValue = TabContextValue & NavIntentValue

const TabContext = createContext<FullValue | null>(null)

// @MX:ANCHOR: [AUTO] TabProvider — active-tab + NavIntent hub (SPEC-SECTOR-UX-001 M3, REQ-SUX-003)
// @MX:REASON: read by AppContent/MarketOverview/SectorAnalysis/StockExplorer/ChartGrid (fan_in >= 5).
//   Two hooks (useTab / useNavIntent) read the same single provider so producers and consumers stay decoupled.

export function TabProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  // Default active tab is 'chart-grid' per R1 requirement
  const [activeTab, setActiveTab] = useState<TabId>('chart-grid')
  const [intent, setIntent] = useState<NavIntent | null>(null)
  // Monotonic id ref — incremented on every navigate() so a re-send is distinguishable from a re-render.
  const idRef = useRef(0)

  const navigate = useCallback(({ target, payload }: { target: TabId; payload?: NavIntentPayload }) => {
    idRef.current += 1
    setActiveTab(target)
    setIntent({ id: idRef.current, target, payload: payload ?? {} })
  }, [])

  return (
    <TabContext.Provider value={{ activeTab, setActiveTab, intent, navigate }}>
      {children}
    </TabContext.Provider>
  )
}

// UI consumers that only need the active tab (avoid re-subscribing to intent churn).
export function useTab(): TabContextValue {
  const ctx = useContext(TabContext)
  if (!ctx) throw new Error('useTab must be used within TabProvider')
  return { activeTab: ctx.activeTab, setActiveTab: ctx.setActiveTab }
}

// Producers (navigate) + consumers (intent) of cross-tab navigation.
export function useNavIntent(): NavIntentValue {
  const ctx = useContext(TabContext)
  if (!ctx) throw new Error('useNavIntent must be used within TabProvider')
  return { intent: ctx.intent, navigate: ctx.navigate }
}
