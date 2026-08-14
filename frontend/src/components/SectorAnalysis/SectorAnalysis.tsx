// @MX:ANCHOR: [AUTO] SectorAnalysis is the container for sector ranking tab, consumes MarketContext and TabContext
// @MX:REASON: Called from AppContent for sector-analysis tab; orchestrates SectorRankingTable + SectorDetailPanel + BubbleChart + BumpChart
// @MX:SPEC: SPEC-TOPDOWN-001D, SPEC-TOPDOWN-002F, SPEC-TOPDOWN-002D
import { useState, useMemo } from 'react'
import type { ReactElement } from 'react'
import type { SectorRankItem } from '../../types/market'
import { useMarket } from '../../contexts/MarketContext'
import { useNavIntent } from '../../contexts/TabContext'
import { useSelection } from '../../contexts/SelectionContext'
import { useAnalysisParams } from '../../contexts/AnalysisParamsContext'
import type { Period, Market } from '../../contexts/AnalysisParamsContext'
import { SectorRankingTable } from './SectorRankingTable'
import { SectorDetailPanel } from './SectorDetailPanel'
import { BubbleChart } from './BubbleChart'
import { BumpChart } from './BumpChart'
import { RRGChart } from './RRGChart'

// 서브 탭 타입 정의
type SubTab = 'table' | 'bubble' | 'rrg' | 'bump'
const SUB_TAB_LABELS: Record<SubTab, string> = {
  table: 'Table',
  bubble: 'Bubble',
  rrg: 'RRG',
  bump: 'Bump',
}

// 기간 값 단일화 (D5 / AC-SUX-009) — 상태는 '1w'|'1m'|'3m' 만 사용.
// 응답 스키마 키(w1/m1/m3)는 PERIOD_EXCESS_FIELD 매핑에서 흡수한다 (별개 축).
const PERIOD_LABELS: Record<Period, string> = { '1w': '1W', '1m': '1M', '3m': '3M' }
const PERIOD_VALUES: Period[] = ['1w', '1m', '3m']
// 기간 → 초과수익률 정렬 필드 매핑 (D5). 상태값 표기와 응답 스키마 키를 변환 계층에서 분리한다.
const PERIOD_EXCESS_FIELD: Record<Period, string> = { '1w': 'excess_w1', '1m': 'excess_m1', '3m': 'excess_m3' }

// 시장 값 (all/kospi/kosdaq) — 백엔드 전송 필터 소문자 (01 §8). 표시 라벨은 All/KOSPI/KOSDAQ.
const MARKET_VALUES: Market[] = ['all', 'kospi', 'kosdaq']
const MARKET_LABELS: Record<Market, string> = { all: 'All', kospi: 'KOSPI', kosdaq: 'KOSDAQ' }

// Map sort field names to sector property accessors
function getSortValue(sector: SectorRankItem, field: string): number {
  switch (field) {
    case 'rank': return sector.rank
    case 'name': return 0 // handled separately for string sort
    case 'excess_w1': return sector.excess_returns.w1
    case 'excess_m1': return sector.excess_returns.m1
    case 'excess_m3': return sector.excess_returns.m3
    case 'rs_avg': return sector.rs_avg
    case 'rs_top_pct': return sector.rs_top_pct
    case 'nh_pct': return sector.nh_pct
    case 'stage2_pct': return sector.stage2_pct
    default: return sector.composite_score
  }
}

export function SectorAnalysis(): ReactElement {
  const { sectorRanking } = useMarket()
  // SM-4: selectedSector 는 SelectionContext 전역 단일 슬롯 (02 §3.3 소유권 표).
  const { selectedSector, selectSector, clearSector } = useSelection()
  const { navigate } = useNavIntent()
  // AC-SUX-008/018: period·market 는 AnalysisParamsContext 전역 단일 인스턴스 (헤더 토글이 소유)
  const { market, period, setMarket, setPeriod } = useAnalysisParams()

  // 서브 탭 상태 (로컬 상태 — context 불필요)
  const [subTab, setSubTab] = useState<SubTab>('table')

  const [sortField, setSortField] = useState('rank')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('asc')

  // Sort sectors based on current sort field/direction
  const sortedSectors = useMemo((): SectorRankItem[] => {
    if (!sectorRanking?.sectors) return []
    const sectors = [...sectorRanking.sectors]

    sectors.sort((a, b) => {
      // String sort for sector name
      if (sortField === 'name') {
        const cmp = a.name.localeCompare(b.name)
        return sortDirection === 'asc' ? cmp : -cmp
      }

      const aVal = getSortValue(a, sortField)
      const bVal = getSortValue(b, sortField)
      return sortDirection === 'asc' ? aVal - bVal : bVal - aVal
    })

    return sectors
  }, [sectorRanking, sortField, sortDirection])

  // Period toggle also re-sorts by excess return for that period (D5 단일화 — 응답 키 흡수)
  const handlePeriodChange = (newPeriod: Period): void => {
    setPeriod(newPeriod)
    setSortField(PERIOD_EXCESS_FIELD[newPeriod])
    setSortDirection('desc')
  }

  const handleSort = (field: string): void => {
    if (field === sortField) {
      setSortDirection(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDirection(field === 'rank' ? 'asc' : 'desc')
    }
  }

  const selectedSectorData = selectedSector
    ? sortedSectors.find(s => s.name === selectedSector)
    : null

  return (
    <div className="sector-analysis">
      {/* AC-SUX-008: 헤더 단일 인스턴스 토글 — 기간·시장 각각 화면당 1개. 서브탭 전체에 걸쳐 공유. */}
      <div className="sector-analysis-header-toggle">
        <div className="period-toggle" data-testid="period-toggle">
          {PERIOD_VALUES.map(p => (
            <button
              key={p}
              className={period === p ? 'active' : undefined}
              onClick={() => handlePeriodChange(p)}
            >
              {PERIOD_LABELS[p]}
            </button>
          ))}
        </div>
        <div className="market-toggle" data-testid="market-toggle">
          {MARKET_VALUES.map(m => (
            <button
              key={m}
              className={market === m ? 'active' : undefined}
              onClick={() => setMarket(m)}
            >
              {MARKET_LABELS[m]}
            </button>
          ))}
        </div>
      </div>

      {/* 서브 탭 내비게이션 */}
      <div className="sector-sub-nav">
        {(['table', 'bubble', 'rrg', 'bump'] as SubTab[]).map(tab => (
          <button
            key={tab}
            className={`sector-sub-nav-btn${subTab === tab ? ' active' : ''}`}
            onClick={() => setSubTab(tab)}
          >
            {SUB_TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      {/* Table 뷰: 기존 섹터 랭킹 테이블 + 상세 패널 */}
      {subTab === 'table' && (
        <>
          <SectorRankingTable
            sectors={sortedSectors}
            sortField={sortField}
            sortDirection={sortDirection}
            onSort={handleSort}
            onSectorClick={(name) => {
              // TR-3/TR-3b: row click sets sector + opens detail panel WITHOUT navigate (REQ-SUX-009).
              //   재클릭 시 clearSector → selectedSector=null + 패널 닫힘.
              if (name === selectedSector) clearSector()
              else selectSector(name)
            }}
            selectedSector={selectedSector}
          />

          {selectedSector && selectedSectorData && (
            <SectorDetailPanel
              sector={selectedSectorData}
              onViewStocks={() => navigate({ target: 'stock-explorer' })}
            />
          )}
        </>
      )}

      {/* Bubble 뷰: 섹터/종목 버블 차트 */}
      {subTab === 'bubble' && (
        <BubbleChart initialSector={null} />
      )}

      {/* RRG 뷰: Relative Rotation Graph */}
      {subTab === 'rrg' && (
        <RRGChart
          onSectorClick={(name) => {
            // TR-7: RRG trail click → selectSector + subTab 'table'. 로컬 state(visibleSectors/windowEnd)는 M5 keep-mounted 개편 시 보존.
            selectSector(name)
            setSubTab('table')
          }}
        />
      )}

      {/* Bump 뷰: 섹터 순위 변동 bump chart */}
      {subTab === 'bump' && (
        <BumpChart
          onSectorClick={(name) => {
            // TR-8: Bump line click → selectSector + subTab 'table'. topFilter 보존은 M5 keep-mounted 개편 시.
            selectSector(name)
            setSubTab('table')
          }}
        />
      )}
    </div>
  )
}
