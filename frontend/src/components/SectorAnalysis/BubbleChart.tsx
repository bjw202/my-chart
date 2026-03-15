// 버블 차트 컨테이너 - 섹터/종목 뷰 토글, 기간·마켓 필터 관리
// @MX:ANCHOR: [AUTO] BubbleChart는 섹터↔종목 버블 뷰 전환을 담당하는 컨테이너
// @MX:REASON: SectorAnalysis에서 마운트되며 SectorBubbleChart, StockBubbleChart 오케스트레이션
import { useState, useEffect, useCallback } from 'react'
import type { ReactElement } from 'react'
import { fetchSectorBubble, fetchStockBubble } from '../../api/bubble'
import type { SectorBubbleItem, StockBubbleItem } from '../../types/bubble'
import { SectorBubbleChart } from './SectorBubbleChart'
import { StockBubbleChart } from './StockBubbleChart'

// 지원 기간 및 마켓 타입
type Period = '1w' | '1m' | '3m'
type MarketFilter = 'ALL' | 'KOSPI' | 'KOSDAQ'

const PERIOD_LABELS: Record<Period, string> = { '1w': '1W', '1m': '1M', '3m': '3M' }
const MARKET_LABELS: Record<MarketFilter, string> = { ALL: '전체', KOSPI: 'KOSPI', KOSDAQ: 'KOSDAQ' }

type ViewMode = 'sector' | 'stock'

interface Props {
  // 외부에서 초기 섹터를 지정할 수 있음 (cross-tab 연동용)
  initialSector?: string | null
}

export function BubbleChart({ initialSector }: Props): ReactElement {
  const [view, setView] = useState<ViewMode>('sector')
  const [selectedSector, setSelectedSector] = useState<string | null>(initialSector ?? null)
  const [period, setPeriod] = useState<Period>('1w')
  const [market, setMarket] = useState<MarketFilter>('ALL')

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
      const res = await fetchSectorBubble(period, market === 'ALL' ? null : market)
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
      {/* 툴바: 뒤로가기 + 기간 토글 + 마켓 필터 */}
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

        <div className="bubble-chart-toolbar-right">
          {/* 마켓 필터 (섹터 뷰에서만) */}
          {view === 'sector' && (
            <div className="bubble-market-toggle">
              {(['ALL', 'KOSPI', 'KOSDAQ'] as MarketFilter[]).map(m => (
                <button
                  key={m}
                  className={market === m ? 'active' : undefined}
                  onClick={() => setMarket(m)}
                >
                  {MARKET_LABELS[m]}
                </button>
              ))}
            </div>
          )}

          {/* 기간 토글 */}
          <div className="bubble-period-toggle">
            {(['1w', '1m', '3m'] as Period[]).map(p => (
              <button
                key={p}
                className={period === p ? 'active' : undefined}
                onClick={() => setPeriod(p)}
              >
                {PERIOD_LABELS[p]}
              </button>
            ))}
          </div>
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
