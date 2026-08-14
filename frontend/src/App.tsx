import React from 'react'
import { ScreenProvider } from './contexts/ScreenContext'
import { NavigationProvider } from './contexts/NavigationContext'
import { WatchlistProvider } from './contexts/WatchlistContext'
import { MarketProvider } from './contexts/MarketContext'
import { TabProvider } from './contexts/TabContext'
import { AnalysisParamsProvider } from './contexts/AnalysisParamsContext'
import { SelectionProvider } from './contexts/SelectionContext'
import { DataLoadProvider } from './contexts/DataLoadContext'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AppContent } from './AppContent'

export default function App(): React.ReactElement {
  return (
    <ErrorBoundary>
      {/* AnalysisParamsProvider 최상단 — market/period 전역 단일 출처 (02 §3.3).
          MarketProvider 보다 위에 배치되어야 M2 에서 MarketContext 가 market 를 소비할 수 있다. */}
      <AnalysisParamsProvider>
        {/* M6: 공용 조회 계층 — TTL 캐시 + 2/4/8초 백오프 + 기준일 레지스트리.
            AnalysisParamsProvider 바로 아래에 둔다 (recordAsOf 를 소비하므로). */}
        <DataLoadProvider>
        <SelectionProvider>
          <MarketProvider>
            <TabProvider>
              <ScreenProvider>
                <NavigationProvider>
                  <WatchlistProvider>
                    <AppContent />
                  </WatchlistProvider>
                </NavigationProvider>
              </ScreenProvider>
            </TabProvider>
          </MarketProvider>
        </SelectionProvider>
        </DataLoadProvider>
      </AnalysisParamsProvider>
    </ErrorBoundary>
  )
}
