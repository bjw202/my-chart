import React from 'react'
import { ScreenProvider } from './contexts/ScreenContext'
import { NavigationProvider } from './contexts/NavigationContext'
import { WatchlistProvider } from './contexts/WatchlistContext'
import { MarketProvider } from './contexts/MarketContext'
import { TabProvider } from './contexts/TabContext'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AppContent } from './AppContent'

export default function App(): React.ReactElement {
  return (
    <ErrorBoundary>
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
    </ErrorBoundary>
  )
}
