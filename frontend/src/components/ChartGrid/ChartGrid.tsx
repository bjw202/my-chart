/**
 * ChartGrid — 종목 차트 그리드 컴포넌트
 *
 * REQ-PERF-001: filterResults prop 기반 → React.memo cascade 차단 가능
 * REQ-INTEGRATE-001~003: injectedStock prop으로 검색 종목 주입
 *
 * @MX:ANCHOR: [AUTO] ChartGrid — AppContent + StockList 등 다수 참조. fan_in >= 3
 * @MX:REASON: filterResults + injectedStock + onSelectStock props로 외부 컨트롤.
 *   AppContent가 useScreen() 결과를 prop으로 전달 → React.memo shallow equal로 cascade 차단.
 *   injectedStock 변경 시 +1 cascade 허용 (highlight/scroll 위해 필요).
 */

import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { VariableSizeList } from 'react-window'
import { useTab } from '../../contexts/TabContext'
import { useNavigation } from '../../contexts/NavigationContext'
import { useChartGrid } from '../../hooks/useChartGrid'
import { useScrollSync } from '../../hooks/useScrollSync'
import type { StockItem } from '../../types/stock'
import type { StockMasterItem } from '../../api/stocks'
import { fetchStageOverview } from '../../api/stage'
import { ChartCell } from './ChartCell'
import { ChartPagination } from './ChartPagination'
import { StockSearchBox } from './StockSearchBox'
import './cellHighlight.css'

// ────────────────────────────────────────────────────────────
// Props 인터페이스
// ────────────────────────────────────────────────────────────

export interface ChartGridProps {
  /** AppContent에서 useScreen() 결과를 flat StockItem[]으로 전달 (REQ-PERF-001 핵심) */
  filterResults: StockItem[]
  /** 검색으로 주입된 종목 — filterResults에 없으면 prepend, 있으면 scroll+highlight (REQ-INTEGRATE-001) */
  injectedStock?: StockMasterItem | null
  /** StockSearchBox onSelect 콜백 — AppContent searchedStock state 업데이트 */
  onSelectStock: (stock: StockMasterItem) => void
}

// ────────────────────────────────────────────────────────────
// StockMasterItem → StockItem 변환 (필수 필드만 채우고 나머지 null)
// ────────────────────────────────────────────────────────────

function masterToStockItem(master: StockMasterItem): StockItem {
  return {
    code: master.code,
    name: master.name,
    market: master.market,
    market_cap: null,
    sector_major: null,
    sector_minor: null,
    product: null,
    close: null,
    change_1d: null,
    rs_12m: null,
    ema10: null,
    ema20: null,
    sma50: null,
    sma100: null,
    sma200: null,
    stage: null,
  }
}

// ────────────────────────────────────────────────────────────
// ChartGrid 내부 구현 (React.memo로 감싸서 export)
// ────────────────────────────────────────────────────────────

function ChartGridInner({
  filterResults,
  injectedStock = null,
  onSelectStock,
}: ChartGridProps): React.ReactElement {
  const { crossTabParams, clearCrossTabParams } = useTab()
  const { selectedIndex } = useNavigation()
  const listRef = useRef<VariableSizeList | null>(null)
  const [timeframe, setTimeframe] = useState<'daily' | 'weekly'>('daily')
  const [stageMap, setStageMap] = useState<Map<string, number>>(new Map())

  // highlight 관련 ref
  const highlightTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // crossTabParams는 ChartGrid에서 직접 처리하지 않음 — AppContent에서 처리
  // (REQ-PERF-001: useScreen() 직접 호출 제거)
  // NOTE: crossTabParams는 AppContent의 useEffect에서 이미 처리됨
  // crossTabParams/clearCrossTabParams 참조만 유지 (기존 compat)
  void crossTabParams
  void clearCrossTabParams

  // Stage 데이터 1회 페치 (useScreen과 독립적 — REQ-PERF-001 위반 없음)
  useEffect(() => {
    fetchStageOverview()
      .then((data) => {
        const map = new Map<string, number>()
        for (const stock of data.all_stocks) {
          map.set(stock.code, stock.stage)
        }
        setStageMap(map)
      })
      .catch(() => {
        // Stage data is optional; chart grid works without it
      })
  }, [])

  // filterResults에 stage 데이터 enrich
  const enrichedFilterResults = useMemo<StockItem[]>(
    () =>
      filterResults.map((stock) => ({
        ...stock,
        stage: stageMap.get(stock.code) ?? stock.stage ?? null,
      })),
    [filterResults, stageMap],
  )

  // ────────────────────────────────────────────────────────
  // displayedStocks union 계산 (REQ-INTEGRATE-001~003)
  //
  // @MX:NOTE: [AUTO] injectedStock이 filterResults에 없으면 prepend,
  //   있으면 기존 배열 그대로 (scroll + highlight는 useEffect에서 처리).
  //   useMemo → injectedStock.code 기반 비교 (전체 object compare 불필요).
  // ────────────────────────────────────────────────────────
  const displayedStocks = useMemo<StockItem[]>(() => {
    if (!injectedStock) return enrichedFilterResults
    const alreadyPresent = enrichedFilterResults.some((s) => s.code === injectedStock.code)
    if (alreadyPresent) return enrichedFilterResults
    return [masterToStockItem(injectedStock), ...enrichedFilterResults]
  }, [injectedStock, enrichedFilterResults])

  const { currentPage, gridSize, totalPages, visibleStocks, goToPage, toggleGridSize } =
    useChartGrid(displayedStocks)

  const { onPageChange } = useScrollSync(listRef)

  const handlePageChange = useCallback(
    (page: number): void => {
      goToPage(page)
      onPageChange(page)
    },
    [goToPage, onPageChange],
  )

  const toggleTimeframe = (): void => {
    setTimeframe((prev) => (prev === 'daily' ? 'weekly' : 'daily'))
  }

  // 키보드 페이지 이동
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent): void => {
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        if (currentPage > 0) handlePageChange(currentPage - 1)
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        if (currentPage < totalPages - 1) handlePageChange(currentPage + 1)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [currentPage, totalPages, handlePageChange])

  // ────────────────────────────────────────────────────────
  // injectedStock 변경 시 자동 scroll + highlight (REQ-INTEGRATE-002/003)
  //
  // @MX:NOTE: [AUTO] injectedStock 변경 → (1) 해당 페이지로 이동 (2) highlight class 추가
  //   (3) 2500ms 후 class 제거. cleanup: clearTimeout + classList.remove.
  //   prepend 케이스 (없는 종목): displayedStocks[0] → page 0 이동.
  //   scroll 케이스 (있는 종목): Math.floor(idx / gridSize) 페이지로 이동.
  // ────────────────────────────────────────────────────────
  useEffect(() => {
    if (!injectedStock) return

    // cleanup 이전 highlight
    if (highlightTimeoutRef.current) {
      clearTimeout(highlightTimeoutRef.current)
      highlightTimeoutRef.current = null
    }

    const targetIndex = displayedStocks.findIndex((s) => s.code === injectedStock.code)
    if (targetIndex < 0) return

    const targetPage = Math.floor(targetIndex / Math.max(1, gridSize))

    // AC-INTEGRATE-001: currentPage > 0 && prepend (index 0) → page 0
    // AC-INTEGRATE-002: 기존 종목 → 해당 page로 이동
    goToPage(targetPage)

    // highlight: data-highlight-target wrapper의 자식 .chart-cell에 className 적용.
    // @MX:WARN [AUTO] wrapper는 display: contents이므로 box-shadow가 wrapper에 적용되면 표시 안 됨.
    // @MX:REASON wrapper(display:contents)는 layout-invisible → CSS box-shadow는 box 있는 element에만
    //   적용. 따라서 wrapper의 자식 .chart-cell(border + display:flex)에 className 부착해야
    //   border-flash keyframes의 box-shadow가 시각적으로 보임.
    // DOM 업데이트 후 highlight 적용
    // setTimeout(0) 사용: jsdom에서 requestAnimationFrame이 실행되지 않을 수 있음
    const applyId = setTimeout(() => {
      const wrapper = document.querySelector(`[data-highlight-target="${injectedStock.code}"]`)
      const cell = wrapper?.querySelector('.chart-cell') ?? wrapper
      if (cell) {
        cell.classList.remove('cell-search-highlight')
        // reflow 강제 (animation restart)
        void (cell as HTMLElement).offsetWidth
        cell.classList.add('cell-search-highlight')

        highlightTimeoutRef.current = setTimeout(() => {
          cell.classList.remove('cell-search-highlight')
          highlightTimeoutRef.current = null
        }, 2500)
      }
    }, 0)

    return () => {
      clearTimeout(applyId)
      if (highlightTimeoutRef.current) {
        clearTimeout(highlightTimeoutRef.current)
        highlightTimeoutRef.current = null
        const wrapper = document.querySelector(`[data-highlight-target="${injectedStock.code}"]`)
        const cell = wrapper?.querySelector('.chart-cell') ?? wrapper
        cell?.classList.remove('cell-search-highlight')
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [injectedStock?.code])
  // M-2: dep을 injectedStock?.code로 축소.
  //   displayedStocks / gridSize / goToPage를 dep에 포함하면 stageMap async fetch(~500ms) 완료 시
  //   enrichedFilterResults → displayedStocks 변경으로 highlight가 재실행됨(timing race).
  //   injectedStock?.code만 감시하면 검색 변경 시만 정확히 1회 fire됨.

  const cols = gridSize === 4 ? 2 : 3
  const rows = gridSize === 4 ? 2 : 3

  if (displayedStocks.length === 0) {
    return (
      <div className="chart-grid chart-grid--empty">
        <p className="empty-message">필터를 적용하여 종목을 검색하세요.</p>
      </div>
    )
  }

  return (
    <div className="chart-grid">
      <div className="chart-grid-toolbar">
        {/* REQ-SEARCH-001: 검색 박스 chart-grid-toolbar 좌측 배치 */}
        <StockSearchBox onSelect={onSelectStock} />
        <button
          type="button"
          className="grid-toggle-btn"
          onClick={toggleGridSize}
          aria-label={`Switch to ${gridSize === 4 ? '3×3' : '2×2'} grid`}
        >
          {gridSize === 4 ? '3×3' : '2×2'}
        </button>
        <button
          type="button"
          className="timeframe-toggle-btn"
          onClick={toggleTimeframe}
          aria-label={`Switch to ${timeframe === 'daily' ? 'weekly' : 'daily'} charts`}
        >
          {timeframe === 'daily' ? 'W' : 'D'}
        </button>
        <ChartPagination
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={handlePageChange}
        />
      </div>

      <div
        className="chart-grid-cells"
        style={{
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gridTemplateRows: `repeat(${rows}, 1fr)`,
        }}
      >
        {visibleStocks.map((stock, slotIndex) => {
          const stockIndex = currentPage * gridSize + slotIndex
          // injectedStock과 일치하는 모든 경우 testid 부여 (prepend + scroll 모두)
          // AC-INTEGRATE-002: scroll 케이스에서도 data-testid="chart-cell-injected-{code}" 필요
          const isInjectedTarget = injectedStock?.code === stock.code
          const isInjectedPrepend =
            isInjectedTarget &&
            displayedStocks[0]?.code === stock.code &&
            !enrichedFilterResults.some((s) => s.code === stock.code)
          void isInjectedPrepend // 향후 prepend 전용 스타일링에 활용 가능

          const testId = isInjectedTarget
            ? `chart-cell-injected-${stock.code}`
            : undefined

          return (
            // data-highlight-target: highlight useEffect가 DOM 요소를 찾기 위한 marker
            // data-testid: 테스트용 — injected prepend cell 식별
            // @MX:WARN [AUTO] wrapper div는 layout-invisible (display: contents)로 둔다.
            // @MX:REASON 첫 fix(height: 100% + minHeight: 0)는 wrapper 자체 stretch는 되었으나,
            //   wrapper가 default `display: block` container라 자식 `.chart-cell`에게 부모 height를
            //   전달하지 못해 chart-cell-canvas height = 0이 유지됨. lightweight-charts가 0 height
            //   chart 인스턴스 생성 → 캔들 미표시.
            //   `display: contents`로 wrapper의 box를 layout 트리에서 제거 → `.chart-cell`이 직접
            //   CSS Grid item이 되어 chore base와 동일한 grid stretch 경로가 복원된다.
            //   DOM 노드는 유지되므로 data-highlight-target querySelector와 data-testid 모두 정상 작동.
            <div
              key={stock.code}
              style={{ display: 'contents' }}
              data-highlight-target={
                injectedStock?.code === stock.code ? stock.code : undefined
              }
              data-testid={testId}
            >
              <ChartCell
                stock={stock}
                isSelected={selectedIndex === stockIndex}
                onClick={() => {
                  /* StockList click navigates; chart click just highlights */
                }}
                timeframe={timeframe}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}

// React.memo로 감싸서 shallow equal 기반 cascade 차단
// filterResults reference 변경 시 cascade (의도), injectedStock 변경 시 cascade 1회 (의도)
export const ChartGrid = memo(ChartGridInner)
