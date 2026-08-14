// 버블 차트 컨테이너 - 섹터/종목 뷰 토글, 기간·마켓 필터 관리
// @MX:ANCHOR: [AUTO] BubbleChart는 섹터↔종목 버블 뷰 전환을 담당하는 컨테이너
// @MX:REASON: SectorAnalysis에서 마운트되며 SectorBubbleChart, StockBubbleChart 오케스트레이션
import { useState, useEffect, useCallback } from 'react'
import type { ReactElement } from 'react'
import { fetchSectorBubble, fetchStockBubble } from '../../api/bubble'
import type { SectorBubbleItem, StockBubbleItem } from '../../types/bubble'
import { SectorBubbleChart } from './SectorBubbleChart'
import { StockBubbleChart } from './StockBubbleChart'
import { useAnalysisParams } from '../../contexts/AnalysisParamsContext'

type ViewMode = 'sector' | 'stock'

interface Props {
  // 외부에서 초기 섹터를 지정할 수 있음 (cross-tab 연동용)
  initialSector?: string | null
}

export function BubbleChart({ initialSector }: Props): ReactElement {
  // AC-SUX-008: period·market 는 헤더 단일 인스턴스(AnalysisParamsContext)에서 소비 — 로컬 토글 제거 (X2)
  const { period, market } = useAnalysisParams()
  const [view, setView] = useState<ViewMode>('sector')
  const [selectedSector, setSelectedSector] = useState<string | null>(initialSector ?? null)

  // 섹터 버블 데이터
  const [sectorData, setSectorData] = useState<SectorBubbleItem[]>([])
  const [sectorLoading, setSectorLoading] = useState(false)
  const [sectorError, setSectorError] = useState<string | null>(null)

  // 종목 버블 데이터
  const [stockData, setStockData] = useState<StockBubbleItem[]>([])
  const [stockLoading, setStockLoading] = useState(false)
  const [stockError, setStockError] = useState<string | null>(null)

  // 섹터 버블 데이터 로드
  const loadSectorData = useCallback(async () => {
    setSectorLoading(true)
    setSectorError(null)
    try {
      const res = await fetchSectorBubble(period, market === 'all' ? null : market)
      setSectorData(res.sectors)
    } catch (e) {
      setSectorError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setSectorLoading(false)
    }
  }, [period, market])

  // 종목 버블 데이터 로드
  const loadStockData = useCallback(async (sectorName: string) => {
    setStockLoading(true)
    setStockError(null)
    try {
      const res = await fetchStockBubble(sectorName, period)
      setStockData(res.stocks)
    } catch (e) {
      setStockError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setStockLoading(false)
    }
  }, [period])

  // 섹터 뷰 초기 로드 및 필터 변경 시 리로드
  useEffect(() => {
    if (view === 'sector') {
      void loadSectorData()
    }
  }, [view, period, market, loadSectorData])

  // 종목 뷰 진입 시 해당 섹터 종목 로드
  useEffect(() => {
    if (view === 'stock' && selectedSector) {
      void loadStockData(selectedSector)
    }
  }, [view, selectedSector, loadStockData])

  // 섹터 클릭 → 종목 버블 뷰로 전환
  const handleSectorClick = useCallback((sectorName: string) => {
    setSelectedSector(sectorName)
    setView('stock')
  }, [])

  // 섹터 뷰로 돌아가기
  const handleBack = useCallback(() => {
    setView('sector')
    setSelectedSector(null)
    setStockData([])
    setStockError(null)
  }, [])

  return (
    <div className="bubble-chart-container">
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

      {/* 차트 영역 */}
      <div className="bubble-chart-body">
        {view === 'sector' && (
          <>
            {sectorLoading && (
              <div className="bubble-loading">섹터 버블 데이터 로딩 중...</div>
            )}
            {sectorError && (
              <div className="bubble-error">오류: {sectorError}</div>
            )}
            {!sectorLoading && !sectorError && (
              <SectorBubbleChart
                sectors={sectorData}
                onSectorClick={handleSectorClick}
              />
            )}
          </>
        )}

        {view === 'stock' && selectedSector && (
          <>
            {stockLoading && (
              <div className="bubble-loading">종목 버블 데이터 로딩 중...</div>
            )}
            {stockError && (
              <div className="bubble-error">오류: {stockError}</div>
            )}
            {!stockLoading && !stockError && (
              <StockBubbleChart
                stocks={stockData}
                sectorName={selectedSector}
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}
