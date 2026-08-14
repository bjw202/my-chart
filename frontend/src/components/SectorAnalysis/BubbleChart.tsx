// 버블 차트 컨테이너 - 섹터/종목 뷰 토글, 기간·마켓 필터 관리
// @MX:ANCHOR: [AUTO] BubbleChart는 섹터↔종목 버블 뷰 전환을 담당하는 컨테이너
// @MX:REASON: SectorAnalysis에서 마운트되며 SectorBubbleChart, StockBubbleChart 오케스트레이션
import { useState, useCallback, useMemo } from 'react'
import type { ReactElement } from 'react'
import { fetchSectorBubble, fetchStockBubble } from '../../api/bubble'
import type { SectorBubbleResponse, StockBubbleResponse } from '../../types/bubble'
import { SectorBubbleChart } from './SectorBubbleChart'
import { StockBubbleChart } from './StockBubbleChart'
import { useAnalysisParams } from '../../contexts/AnalysisParamsContext'
import { useNavIntent } from '../../contexts/TabContext'
import { useSelection } from '../../contexts/SelectionContext'
import { buildQueryKey, useQuery } from '../../contexts/DataLoadContext'
import { DataStatusBar } from '../common/DataStatusBar'

type ViewMode = 'sector' | 'stock'

interface Props {
  // 외부에서 초기 섹터를 지정할 수 있음 (cross-tab 연동용)
  initialSector?: string | null
  // AC-SUX-033: 이 화면이 활성일 때만 조회한다. 비활성 서브탭은 fetch 하지 않는다.
  active?: boolean
}

// 봉투 → 조회 메타 (AC-SUX-037). 백엔드가 안 주면 null 로 우아하게 결손 처리한다.
const bubbleMeta = (d: SectorBubbleResponse | StockBubbleResponse) => ({
  asOfDate: d.as_of_date ?? d.date ?? null,
  asOfIsPartialWeek: d.as_of_is_partial_week ?? false,
  gridVersion: d.grid_version ?? null,
})

export function BubbleChart({ initialSector, active = true }: Props): ReactElement {
  // AC-SUX-008: period·market 는 헤더 단일 인스턴스(AnalysisParamsContext)에서 소비 — 로컬 토글 제거 (X2)
  const { period, market } = useAnalysisParams()
  const { navigate } = useNavIntent()
  const { selectSector: selectSectorGlobal } = useSelection()
  const [view, setView] = useState<ViewMode>('sector')
  const [selectedSector, setSelectedSector] = useState<string | null>(initialSector ?? null)

  // AC-SUX-033/034: 쿼리 키 = 엔드포인트 + 파라미터. TTL 내 재활성화는 추가 fetch 없음.
  const sectorKey = buildQueryKey('sector-bubble', { period, market })
  const sectorQuery = useQuery<SectorBubbleResponse>(
    sectorKey,
    useCallback(() => fetchSectorBubble(period, market), [period, market]),
    { enabled: active && view === 'sector', panel: '섹터 버블', meta: bubbleMeta },
  )

  // market 이 키에 없으면 드릴다운 상태에서 시장을 바꿔도 재조회가 일어나지 않는다(무동작 결함).
  const stockKey = selectedSector
    ? buildQueryKey('stock-bubble', { sector: selectedSector, period, market })
    : null
  const stockQuery = useQuery<StockBubbleResponse>(
    stockKey,
    useCallback(
      () => fetchStockBubble(selectedSector ?? '', period, market),
      [selectedSector, period, market],
    ),
    { enabled: active && view === 'stock' && selectedSector !== null, panel: '종목 버블', meta: bubbleMeta },
  )

  // AC-SUX-035 (LD-C): 재조회 중에도 직전 데이터를 그대로 넘긴다 — 차트가 언마운트되지 않는다.
  const sectorData = useMemo(() => sectorQuery.data?.sectors ?? [], [sectorQuery.data])
  const stockData = useMemo(() => stockQuery.data?.stocks ?? [], [stockQuery.data])

  // 섹터 클릭 → 종목 버블 뷰로 전환
  const handleSectorClick = useCallback((sectorName: string) => {
    setSelectedSector(sectorName)
    setView('stock')
  }, [])

  // TR-9 (AC-SUX-013 / ST-8): 종목 버블 클릭 → 종목 탐색 focusStock 진입.
  //   현재 섹터를 전역 SelectionContext 슬롯에 동기화(StockExplorer 모집단 일치).
  //   selectedStocks 초기화는 StockExplorer NavIntent consumer에서 수행(TR-16).
  const handleStockClick = useCallback((stockName: string) => {
    if (selectedSector) selectSectorGlobal(selectedSector)
    navigate({ target: 'stock-explorer', payload: { focusStock: stockName } })
  }, [selectedSector, selectSectorGlobal, navigate])

  // 섹터 뷰로 돌아가기 — TR-6 (AC-SUX-016): selectedSector 유지(현행 null 삭제 결함 수정).
  const handleBack = useCallback(() => {
    setView('sector')
  }, [])

  const activeQuery = view === 'sector' ? sectorQuery : stockQuery

  return (
    <div className="bubble-chart-container">
      {/* SN-4: 기준일 배지 + ⟳ 새로고침 상설. LD-C: 재조회 인디케이터는 배지 옆. */}
      <DataStatusBar
        screen={view === 'sector' ? 'sector-bubble' : 'stock-bubble'}
        asOfDate={activeQuery.asOfDate}
        asOfIsPartialWeek={activeQuery.asOfIsPartialWeek}
        refetching={activeQuery.refetching}
        error={activeQuery.error}
        staleAsOf={activeQuery.staleAsOf}
        onRetry={activeQuery.retry}
      />

      {/* 툴바: 뒤로가기 + 섹터 라벨 (기간·마켓 토글은 헤더 단일 인스턴스로 이동 — X2 제거) */}
      <div className="bubble-chart-toolbar">
        <div className="bubble-chart-toolbar-left">
          {view === 'stock' && (
            <button
              className="bubble-back-btn"
              onClick={handleBack}
              title="섹터 뷰로 돌아가기"
            >
              ← 섹터 목록
            </button>
          )}
          {view === 'stock' && selectedSector && (
            <span className="bubble-sector-label">{selectedSector}</span>
          )}
        </div>
      </div>

      {/* 차트 영역 — AC-SUX-035: 재조회(refetching) 동안 차트를 언마운트하지 않는다.
          최초 로딩(표시할 데이터 없음)일 때만 자리 표시자를 렌더한다. */}
      <div className="bubble-chart-body">
        {view === 'sector' && (
          sectorQuery.loading && sectorData.length === 0 ? (
            <div className="bubble-loading">섹터 버블 데이터 로딩 중...</div>
          ) : (
            <SectorBubbleChart
              sectors={sectorData}
              onSectorClick={handleSectorClick}
              period={period}
              market={market}
            />
          )
        )}

        {view === 'stock' && selectedSector && (
          stockQuery.loading && stockData.length === 0 ? (
            <div className="bubble-loading">종목 버블 데이터 로딩 중...</div>
          ) : (
            <StockBubbleChart
              stocks={stockData}
              sectorName={selectedSector}
              onStockClick={handleStockClick}
              period={period}
            />
          )
        )}
      </div>
    </div>
  )
}
