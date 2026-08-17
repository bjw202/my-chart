import React, { useCallback, useEffect, useRef, useState } from 'react'
import { VariableSizeList } from 'react-window'
import type { ListChildComponentProps } from 'react-window'
import { useScreen } from '../../contexts/ScreenContext'
import { useNavigation } from '../../contexts/NavigationContext'
import { useWatchlist } from '../../contexts/WatchlistContext'
import { useStockNavigation } from '../../hooks/useStockNavigation'
import { useScrollSync } from '../../hooks/useScrollSync'
import type { StockItem as StockItemData, SectorGroup as SectorGroupData } from '../../types/stock'
import { SectorGroupHeader } from './SectorGroup'
import { StockItemRow } from './StockItem'
import { buildCheckedGroups } from './sectorKey'

// Virtual list item types
type ListItem =
  | { type: 'sector'; sector: SectorGroupData }
  | { type: 'stock'; stock: StockItemData; globalIndex: number }

const SECTOR_HEIGHT = 40
const STOCK_ITEM_HEIGHT = 56

export function StockList(): React.ReactElement {
  const { results } = useScreen()
  const { selectedIndex } = useNavigation()
  const { isChecked, toggleStock, uncheckStock, checkedStocks, checkedCount, exportText } = useWatchlist()
  const [collapsedSectors, setCollapsedSectors] = useState<Set<string>>(new Set())
  // 체크 탭 전용 접힘 상태 — 전체 탭 collapsedSectors와 독립 (탭별 분리, M2)
  const [collapsedCheckedSectors, setCollapsedCheckedSectors] = useState<Set<string>>(new Set())
  const [listHeight, setListHeight] = useState(600)
  const [viewMode, setViewMode] = useState<'all' | 'checked'>('all')
  const [copied, setCopied] = useState(false)
  const observerRef = useRef<ResizeObserver | null>(null)

  // Callback ref: fires when the div mounts/unmounts, including after empty→populated transition
  const bodyRefCallback = useCallback((node: HTMLDivElement | null) => {
    observerRef.current?.disconnect()
    observerRef.current = null
    if (!node) return
    const observer = new ResizeObserver((entries) => {
      setListHeight(entries[0].contentRect.height)
    })
    observer.observe(node)
    observerRef.current = observer
  }, [])

  useEffect(() => () => { observerRef.current?.disconnect() }, [])

  const listRef = useRef<VariableSizeList | null>(null)
  const { onStockSelect } = useScrollSync(listRef)

  // Build flat list of items (sector headers + stocks) for "all" mode
  const flatItems: ListItem[] = []
  let globalIndex = 0
  for (const sector of results?.sectors ?? []) {
    flatItems.push({ type: 'sector', sector })
    if (!collapsedSectors.has(sector.sector_name)) {
      for (const stock of sector.stocks) {
        flatItems.push({ type: 'stock', stock, globalIndex })
        globalIndex++
      }
    } else {
      globalIndex += sector.stocks.length
    }
  }

  // Build checked items list for "checked" mode — 섹터 헤더 + 종목 행 구조 (M2)
  const checkedItems: ListItem[] = []
  let checkedIndex = 0
  for (const group of buildCheckedGroups(Array.from(checkedStocks.values()))) {
    checkedItems.push({
      type: 'sector',
      sector: {
        sector_name: group.sectorName,
        stock_count: group.stocks.length, // 그룹의 체크 종목 수 (유니버스 stock_count 아님)
        stocks: group.stocks,
      },
    })
    if (!collapsedCheckedSectors.has(group.sectorName)) {
      for (const stock of group.stocks) {
        checkedItems.push({ type: 'stock', stock, globalIndex: -1 - checkedIndex })
        checkedIndex++
      }
    } else {
      checkedIndex += group.stocks.length
    }
  }

  const displayItems = viewMode === 'all' ? flatItems : checkedItems

  const totalStocks = results?.sectors.reduce((acc, s) => acc + s.stocks.length, 0) ?? 0
  useStockNavigation(totalStocks)

  const getItemSize = (index: number): number => {
    const item = displayItems[index]
    return item?.type === 'sector' ? SECTOR_HEIGHT : STOCK_ITEM_HEIGHT
  }

  // 접기 토글은 활성 탭의 Set만 변경 — 두 Set은 병합/공유되지 않음 (M2)
  const toggleSector = useCallback((sectorName: string): void => {
    const setter = viewMode === 'checked' ? setCollapsedCheckedSectors : setCollapsedSectors
    setter((prev) => {
      const next = new Set(prev)
      if (next.has(sectorName)) {
        next.delete(sectorName)
      } else {
        next.add(sectorName)
      }
      return next
    })
    listRef.current?.resetAfterIndex(0)
  }, [viewMode])

  // 소멸한 체크 그룹의 접힘 키 정리 — 체크 목록에서 그룹이 사라지면 해당 키를 제거해
  // 재등장하는 그룹이 펼침 상태로 시작하게 한다 (접힘 키 잔존 결함, AC-008 보강)
  useEffect(() => {
    const liveKeys = new Set(
      buildCheckedGroups(Array.from(checkedStocks.values())).map((g) => g.sectorName),
    )
    if (!Array.from(collapsedCheckedSectors).some((key) => !liveKeys.has(key))) return
    setCollapsedCheckedSectors((prev) => new Set(Array.from(prev).filter((key) => liveKeys.has(key))))
  }, [checkedStocks, collapsedCheckedSectors])

  // Reset list size cache when items change
  useEffect(() => {
    listRef.current?.resetAfterIndex(0)
  }, [results, collapsedSectors, collapsedCheckedSectors, viewMode, checkedCount])

  // Scroll to selected item (only in "all" mode)
  useEffect(() => {
    if (viewMode !== 'all' || selectedIndex < 0) return
    let count = 0
    for (let i = 0; i < flatItems.length; i++) {
      const item = flatItems[i]
      if (item.type === 'stock') {
        if (count === selectedIndex) {
          listRef.current?.scrollToItem(i, 'smart')
          break
        }
        count++
      }
    }
  }, [selectedIndex, viewMode]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleExport = (): void => {
    if (checkedCount === 0) return
    navigator.clipboard.writeText(exportText).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    }).catch(() => {
      // Fallback: prompt user
    })
  }

  const Row = useCallback(
    ({ index, style }: ListChildComponentProps): React.ReactElement | null => {
      const item = displayItems[index]
      if (!item) return null

      if (item.type === 'sector') {
        // 활성 탭의 접힘 Set 참조 — 전체는 collapsedSectors, 체크는 collapsedCheckedSectors (M2)
        const collapsedSet = viewMode === 'checked' ? collapsedCheckedSectors : collapsedSectors
        return (
          <SectorGroupHeader
            sectorName={item.sector.sector_name}
            stockCount={item.sector.stock_count}
            collapsed={collapsedSet.has(item.sector.sector_name)}
            style={style}
            onToggle={() => toggleSector(item.sector.sector_name)}
          />
        )
      }

      if (viewMode === 'checked') {
        return (
          <div className="stock-item stock-item--checked" style={style}>
            <div className="stock-item-content">
              <div className="stock-item-main">
                <span className="stock-item-name">{item.stock.name}</span>
                <span className="stock-item-code">{item.stock.code}</span>
              </div>
            </div>
            <button
              className="watchlist-remove-btn"
              onClick={() => uncheckStock(item.stock.code)}
              title="해제"
            >
              x
            </button>
          </div>
        )
      }

      return (
        <StockItemRow
          stock={item.stock}
          isSelected={selectedIndex === item.globalIndex}
          isChecked={isChecked(item.stock.code)}
          style={style}
          onClick={() => onStockSelect(item.globalIndex)}
          onToggleCheck={() => toggleStock(item.stock)}
        />
      )
    },
    [displayItems, collapsedSectors, collapsedCheckedSectors, selectedIndex, onStockSelect, toggleSector, isChecked, toggleStock, uncheckStock, viewMode]
  )

  if (viewMode === 'all' && flatItems.length === 0) {
    return (
      <aside className="stock-list stock-list--empty">
        <p className="empty-message">검색 결과가 없습니다.</p>
      </aside>
    )
  }

  return (
    <aside className="stock-list" role="listbox" aria-label="Stock list">
      <div className="stock-list-header">
        <div className="stock-list-tabs">
          <button
            className={`stock-list-tab${viewMode === 'all' ? ' stock-list-tab--active' : ''}`}
            onClick={() => setViewMode('all')}
          >
            전체
          </button>
          <button
            className={`stock-list-tab${viewMode === 'checked' ? ' stock-list-tab--active' : ''}`}
            onClick={() => setViewMode('checked')}
          >
            체크({checkedCount})
          </button>
        </div>
        <button
          className={`stock-list-export-btn${copied ? ' stock-list-export-btn--copied' : ''}`}
          onClick={handleExport}
          disabled={checkedCount === 0}
        >
          {copied ? 'Copied!' : 'Export'}
        </button>
      </div>
      <div ref={bodyRefCallback} className="stock-list-body">
        {viewMode === 'checked' && checkedCount === 0 ? (
          <p className="empty-message" style={{ padding: '20px 10px' }}>체크된 종목이 없습니다.</p>
        ) : (
          <VariableSizeList
            ref={listRef}
            height={listHeight}
            itemCount={displayItems.length}
            itemSize={getItemSize}
            width="100%"
            overscanCount={5}
          >
            {Row}
          </VariableSizeList>
        )}
      </div>
    </aside>
  )
}
