import { useEffect, useRef, useState } from 'react'
import type { ReactElement } from 'react'
import { useTab, useNavIntent } from '../../contexts/TabContext'
import { useSelection } from '../../contexts/SelectionContext'
import { fetchStageOverview } from '../../api/stage'
import type { StageOverviewResponse } from '../../types/stage'
import { StageDistributionBar } from './StageDistributionBar'
import { StockTable } from './StockTable'

// 백엔드 미응답 시 재시도 설정 (2초, 4초, 8초)
export const RETRY_DELAYS_MS = [2000, 4000, 8000]

// @MX:NOTE: [AUTO] StockExplorer is the container for SPEC-TOPDOWN-001E Stock Explorer tab
// Fetches /api/stage/overview, manages stage/sector filters, and handles cross-tab navigation

export function StockExplorer(): ReactElement {
  const { activeTab } = useTab()
  const { intent, navigate } = useNavIntent()
  // SM-5/SM-6: selectedSector·sectorScopeFollow 는 전역 SelectionContext 소유 (02 §3.3).
  const { selectedSector, sectorScopeFollow, setSectorScopeFollow } = useSelection()
  const [data, setData] = useState<StageOverviewResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [stageFilter, setStageFilter] = useState<number | null>(null)
  // sectorFilter 는 지역 상태가 아니다 — 스코프 추종 토글이 true 일 때만 전역 selectedSector 로 필터 (AC-SUX-007).
  const sectorFilter = sectorScopeFollow ? selectedSector : null
  const [selectedStocks, setSelectedStocks] = useState<Set<string>>(new Set())

  useEffect(() => {
    let cancelled = false
    const fetchWithRetry = (retryCount: number) => {
      fetchStageOverview()
        .then((result) => {
          if (!cancelled) {
            setData(result)
            setLoading(false)
          }
        })
        .catch((e: Error) => {
          if (cancelled) return
          // 백엔드 미응답 시 자동 재시도 (최대 3회, 2/4/8초 간격)
          if (retryCount < RETRY_DELAYS_MS.length) {
            setTimeout(() => fetchWithRetry(retryCount + 1), RETRY_DELAYS_MS[retryCount])
            return
          }
          setError(e.message)
          setLoading(false)
        })
    }
    fetchWithRetry(0)
    return () => { cancelled = true }
  }, [])

  // TR-16 (REQ-SUX-013 / AC-SUX-015): 모집단(selectedSector) 변경 시 selectedStocks 초기화.
  //   render-time adjustment 패턴(React 권장) — effect 내 setState lint 회피.
  //   Stage 필터 변경(TR-10/11)은 별도 state 이므로 여기서 건드리지 않는다.
  const [prevSector, setPrevSector] = useState<string | null>(selectedSector)
  if (selectedSector !== prevSector) {
    setPrevSector(selectedSector)
    setSelectedStocks(new Set())
  }

  // NavIntent consumer (stock-explorer target) — TR-4/TR-9 진입 시 selectedStocks 초기화.
  //   3-condition guard (target / activeTab / lastHandledId); 전역 clear 없음 (AC-SUX-005).
  const navLastHandled = useRef<number | null>(null)
  useEffect(() => {
    if (!intent) return
    if (intent.target !== 'stock-explorer') return
    if (activeTab !== 'stock-explorer') return
    if (navLastHandled.current === intent.id) return
    navLastHandled.current = intent.id
    // TR-16: 인구 변동 진입(TR-4 상세패널 버튼 / TR-9 종목버블) → selectedStocks 초기화.
    setSelectedStocks(new Set())
  }, [intent, activeTab])

  const handleStockSelect = (code: string) => {
    setSelectedStocks((prev) => {
      const next = new Set(prev)
      if (next.has(code)) {
        next.delete(code)
      } else {
        next.add(code)
      }
      return next
    })
  }

  const handleSelectAll = (codes: string[]) => {
    if (codes.length === 0) {
      // 전체 해제
      setSelectedStocks(new Set())
    } else {
      // 전체 선택
      setSelectedStocks(new Set(codes))
    }
  }

  const handleViewCharts = () => {
    navigate({ target: 'chart-grid', payload: { stockCodes: [...selectedStocks] } })
  }

  const handleStageClick = (stage: string | null) => {
    // Map segment key (stage1/stage2/...) to stage string used in candidates
    if (stage === null) {
      setStageFilter(null)
      return
    }
    // Map distribution bar keys to API stage integer values
    const stageMap: Record<string, number> = {
      stage1: 1,
      stage2: 2,
      stage3: 3,
      stage4: 4,
    }
    setStageFilter(stageMap[stage] ?? null)
  }

  // Derive activeStage key from current stageFilter
  const activeStageKey = stageFilter !== null
    ? Object.entries({
        stage1: 1,
        stage2: 2,
        stage3: 3,
        stage4: 4,
      } as Record<string, number>).find(([, v]) => v === stageFilter)?.[0] ?? null
    : null

  if (loading) {
    return (
      <div className="stock-explorer">
        <div className="stock-explorer-loading">Loading...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="stock-explorer">
        <div className="stock-explorer-error">{error}</div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="stock-explorer">
        <div className="stock-explorer-empty">No data available</div>
      </div>
    )
  }

  return (
    <div className="stock-explorer">
      {/* Toolbar */}
      <div className="stock-explorer-toolbar">
        <div className="stock-explorer-toolbar-left">
          {sectorFilter && (
            <span className="sector-filter-chip">
              {sectorFilter}
              <button
                type="button"
                // AC-SUX-007 (TR-12): 칩 × → sectorScopeFollow=false (selectedSector는 유지).
                //   TR-16: 모집단 변경(전체)이므로 selectedStocks 초기화.
                onClick={() => {
                  setSectorScopeFollow(false)
                  setSelectedStocks(new Set())
                }}
                aria-label={`Remove sector filter ${sectorFilter}`}
              >
                ×
              </button>
            </span>
          )}
        </div>
        <div className="stock-explorer-toolbar-right">
          <span className="selected-count">
            {selectedStocks.size > 0 && `${selectedStocks.size} selected`}
          </span>
          <button
            type="button"
            className="view-charts-btn"
            disabled={selectedStocks.size === 0}
            onClick={handleViewCharts}
            aria-label="View Charts"
          >
            View Charts
          </button>
        </div>
      </div>

      {/* Stage distribution bar */}
      <StageDistributionBar
        distribution={data.distribution}
        activeStage={activeStageKey}
        onStageClick={handleStageClick}
      />

      {/* Stock table — use all_stocks for full stage coverage, fallback to stage2_candidates */}
      <StockTable
        candidates={data.all_stocks?.length ? data.all_stocks : data.stage2_candidates}
        stageFilter={stageFilter}
        sectorFilter={sectorFilter}
        onStockSelect={handleStockSelect}
        onSelectAll={handleSelectAll}
        selectedStocks={selectedStocks}
      />
    </div>
  )
}
