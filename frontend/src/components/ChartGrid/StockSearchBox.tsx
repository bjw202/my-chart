/**
 * StockSearchBox — 종목 검색 자동완성 입력 컴포넌트
 *
 * REQ-SEARCH-001: chart-grid-toolbar 좌측 배치, 220px
 * REQ-SEARCH-003: 5단계 score 매칭 (alias=5 > 코드prefix=4 > 명prefix=3 > 명sub=2 > 초성=1)
 * REQ-SEARCH-005: ArrowDown/Up/Enter/Escape/Tab 키보드 navigation
 * REQ-SEARCH-006: 503 → disabled + placeholder "DB 업데이트 필요"
 *
 * @MX:ANCHOR: [AUTO] 검색 진입점 컴포넌트 — ChartGrid + AppContent 양쪽 참조 (fan_in >= 2)
 * @MX:REASON: onSelect prop → AppContent에서 selectedStock state lift + modal 트리거
 */

import React, {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react'
import { useStockMaster } from '../../hooks/useStockMaster'
import { matchesQuery } from '../../utils/hangul'
import type { StockMasterItem } from '../../api/stocks'

const MAX_RESULTS = 8
const DEBOUNCE_MS = 150

export interface StockSearchBoxHandle {
  clearInput: () => void
  /** focus 복귀 — modal close 시 검색 입력창으로 focus를 돌려보낸다 (REQ-MODAL-002 step 3) */
  focus: () => void
}

export interface StockSearchBoxProps {
  onSelect: (item: StockMasterItem) => void
}

/**
 * StockSearchBox는 useScreen/useTab을 구독하지 않는다 (AC-ARCH-003).
 * 검색 결과는 AppContent를 통해 modal로 표시하며 ChartGrid 필터를 변경하지 않는다.
 */
export const StockSearchBox = forwardRef<StockSearchBoxHandle, StockSearchBoxProps>(
  function StockSearchBox({ onSelect }, ref) {
    const { data, error } = useStockMaster()
    const [query, setQuery] = useState('')
    const [candidates, setCandidates] = useState<StockMasterItem[]>([])
    const [open, setOpen] = useState(false)
    const [highlightIndex, setHighlightIndex] = useState(-1)
    const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
    const containerRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    const is503 = error?.message === 'stock_meta_not_ready'

    // clearInput + focus imperative handle (REQ-MODAL-002 step 3+4)
    useImperativeHandle(ref, () => ({
      clearInput() {
        setQuery('')
        setCandidates([])
        setOpen(false)
        setHighlightIndex(-1)
      },
      focus() {
        inputRef.current?.focus()
      },
    }))

    const runSearch = useCallback(
      (q: string) => {
        if (!data || !q.trim()) {
          setCandidates([])
          setOpen(false)
          return
        }
        const results = data.stocks
          .map((item) => ({ item, result: matchesQuery(item, q) }))
          .filter(({ result }) => result.matched)
          .sort((a, b) => {
            if (b.result.score !== a.result.score) return b.result.score - a.result.score
            return a.item.name.localeCompare(b.item.name)
          })
          .slice(0, MAX_RESULTS)
          .map(({ item }) => item)
        setCandidates(results)
        setOpen(true)
        setHighlightIndex(-1)
      },
      [data],
    )

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
      const val = e.target.value
      setQuery(val)
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => runSearch(val), DEBOUNCE_MS)
    }

    const handleSelect = useCallback(
      (item: StockMasterItem): void => {
        onSelect(item)
        setQuery('')
        setCandidates([])
        setOpen(false)
        setHighlightIndex(-1)
      },
      [onSelect],
    )

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>): void => {
      if (!open) return
      switch (e.key) {
        case 'ArrowDown': {
          e.preventDefault()
          if (candidates.length === 0) return
          setHighlightIndex((prev) => (prev + 1) % candidates.length)
          break
        }
        case 'ArrowUp': {
          e.preventDefault()
          if (candidates.length === 0) return
          setHighlightIndex((prev) => (prev - 1 + candidates.length) % candidates.length)
          break
        }
        case 'Enter': {
          e.preventDefault()
          const idx = highlightIndex >= 0 ? highlightIndex : 0
          if (candidates[idx]) {
            handleSelect(candidates[idx])
          }
          break
        }
        case 'Escape': {
          e.preventDefault()
          setQuery('')
          setCandidates([])
          setOpen(false)
          setHighlightIndex(-1)
          break
        }
        case 'Tab': {
          // Tab closes listbox, lets native focus move to next element
          setOpen(false)
          setHighlightIndex(-1)
          break
        }
      }
    }

    // 외부 클릭 시 드롭다운 닫기
    useEffect(() => {
      const onClickOutside = (e: MouseEvent): void => {
        if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
          setOpen(false)
        }
      }
      document.addEventListener('mousedown', onClickOutside)
      return () => document.removeEventListener('mousedown', onClickOutside)
    }, [])

    const activeDescendant =
      highlightIndex >= 0 && candidates[highlightIndex]
        ? `chart-search-option-${candidates[highlightIndex].code}`
        : undefined

    const listboxId = 'chart-search-listbox'

    return (
      <div
        ref={containerRef}
        style={{ position: 'relative', width: 220, flexShrink: 0 }}
        data-testid="stock-search-box"
      >
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={is503}
          placeholder={is503 ? 'DB 업데이트 필요' : '종목명/코드/초성 검색'}
          title={is503 ? 'DB 업데이트가 필요합니다' : undefined}
          data-testid="chart-search-input"
          role="combobox"
          aria-label="종목 검색"
          aria-expanded={open}
          aria-autocomplete="list"
          aria-controls={open ? listboxId : undefined}
          aria-activedescendant={activeDescendant}
          style={{
            width: '100%',
            padding: '4px 8px',
            fontSize: 13,
            background: 'var(--bg-input, #1a1a2e)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            borderRadius: 4,
            boxSizing: 'border-box',
            opacity: is503 ? 0.5 : 1,
          }}
        />
        {open && (
          <ul
            id={listboxId}
            role="listbox"
            data-testid="chart-search-listbox"
            aria-label="종목 검색 결과"
            style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              zIndex: 999,
              width: '100%',
              margin: 0,
              padding: 0,
              listStyle: 'none',
              background: 'var(--bg-surface, #16213e)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              maxHeight: 240,
              overflowY: 'auto',
            }}
          >
            {candidates.length === 0 ? (
              <li
                data-testid="chart-search-empty"
                aria-disabled="true"
                style={{ padding: '8px 10px', fontSize: 12, color: 'var(--text-muted)' }}
              >
                검색 결과 없음
              </li>
            ) : (
              candidates.map((item, idx) => (
                <li
                  key={item.code}
                  id={`chart-search-option-${item.code}`}
                  data-testid={`chart-search-option-${item.code}`}
                  role="option"
                  aria-selected={highlightIndex === idx}
                  onMouseDown={() => handleSelect(item)}
                  style={{
                    padding: '6px 10px',
                    fontSize: 13,
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: highlightIndex === idx ? 'var(--bg-hover, rgba(255,255,255,0.1))' : '',
                  }}
                >
                  <span>
                    <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{item.name}</span>
                    <span style={{ marginLeft: 6, fontSize: 11, color: 'var(--text-muted)' }}>
                      {item.code}
                    </span>
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.market}</span>
                </li>
              ))
            )}
          </ul>
        )}
      </div>
    )
  },
)
