import React, { useCallback, useEffect, useRef, useState } from 'react'
import { VariableSizeList } from 'react-window'
import type { ListChildComponentProps } from 'react-window'
import { useScreen } from '../../contexts/ScreenContext'
import { useNavigation } from '../../contexts/NavigationContext'
import { useStockNavigation } from '../../hooks/useStockNavigation'
import { useScrollSync } from '../../hooks/useScrollSync'
import type { StockItem as StockItemData, SectorGroup as SectorGroupData } from '../../types/stock'
import { SectorGroupHeader } from './SectorGroup'
import { StockItemRow } from './StockItem'

// Virtual list item types
type ListItem =
  | { type: 'sector'; sector: SectorGroupData }
  | { type: 'stock'; stock: StockItemData; globalIndex: number }

const SECTOR_HEIGHT = 40
const STOCK_ITEM_HEIGHT = 56

export function StockList(): React.ReactElement {
  const { results } = useScreen()
  const { selectedIndex } = useNavigation()
  const [collapsedSectors, setCollapsedSectors] = useState<Set<string>>(new Set())
  const [listHeight, setListHeight] = useState(600)
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

  // Build flat list of items (sector headers + stocks)
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

  const totalStocks = results?.sectors.reduce((acc, s) => acc + s.stocks.length, 0) ?? 0
  useStockNavigation(totalStocks)

  const getItemSize = (index: number): number =>
    flatItems[index]?.type === 'sector' ? SECTOR_HEIGHT : STOCK_ITEM_HEIGHT

  const toggleSector = useCallback((sectorName: string): void => {
    setCollapsedSectors((prev) => {
      const next = new Set(prev)
      if (next.has(sectorName)) {
        next.delete(sectorName)
      } else {
        next.add(sectorName)
      }
      return next
    })
    listRef.current?.resetAfterIndex(0)
  }, [])

  // Reset list size cache when items change
  useEffect(() => {
    listRef.current?.resetAfterIndex(0)
  }, [results, collapsedSectors])

  // Scroll to selected item
  useEffect(() => {
    if (selectedIndex < 0) return
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
  }, [selectedIndex]) // eslint-disable-line react-hooks/exhaustive-deps

  const Row = useCallback(
    ({ index, style }: ListChildComponentProps): React.ReactElement | null => {
      const item = flatItems[index]
      if (!item) return null

      if (item.type === 'sector') {
        return (
          <SectorGroupHeader
            sectorName={item.sector.sector_name}
            stockCount={item.sector.stock_count}
            collapsed={collapsedSectors.has(item.sector.sector_name)}
            style={style}
            onToggle={() => toggleSector(item.sector.sector_name)}
          />
        )
      }

      return (
        <StockItemRow
          stock={item.stock}
          isSelected={selectedIndex === item.globalIndex}
          style={style}
          onClick={() => onStockSelect(item.globalIndex)}
        />
      )
    },
    [flatItems, collapsedSectors, selectedIndex, onStockSelect, toggleSector]
  )

  if (flatItems.length === 0) {
    return (
      <aside className="stock-list stock-list--empty">
        <p className="empty-message">검색 결과가 없습니다.</p>
      </aside>
    )
  }

  return (
    <aside className="stock-list" role="listbox" aria-label="Stock list">
      <div className="stock-list-header">
        <span>종목</span>
        <span>등락률 / RS</span>
      </div>
      <div ref={bodyRefCallback} className="stock-list-body">
        <VariableSizeList
          ref={listRef}
          height={listHeight}
          itemCount={flatItems.length}
          itemSize={getItemSize}
          width="100%"
          overscanCount={5}
        >
          {Row}
        </VariableSizeList>
      </div>
    </aside>
  )
}
