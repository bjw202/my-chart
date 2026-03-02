import React from 'react'
import { ScreenProvider } from './contexts/ScreenContext'
import { NavigationProvider } from './contexts/NavigationContext'
import { WatchlistProvider } from './contexts/WatchlistContext'
import { ErrorBoundary } from './components/ErrorBoundary'
import { FilterBar } from './components/FilterBar/FilterBar'
import { ChartGrid } from './components/ChartGrid/ChartGrid'
import { StockList } from './components/StockList/StockList'
import { StatusBar } from './components/StatusBar/StatusBar'

export default function App(): React.ReactElement {
  return (
    <ErrorBoundary>
      <ScreenProvider>
        <NavigationProvider>
          <WatchlistProvider>
            <div className="app">
              <FilterBar />

              <main className="app-main">
                <ChartGrid />
                <StockList />
              </main>

              <StatusBar />
            </div>
          </WatchlistProvider>
        </NavigationProvider>
      </ScreenProvider>
    </ErrorBoundary>
  )
}
