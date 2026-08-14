// @MX:ANCHOR: [AUTO] SectorAnalysis is the container for sector ranking tab, consumes MarketContext and TabContext
// @MX:REASON: Called from AppContent for sector-analysis tab; orchestrates SectorRankingTable + SectorDetailPanel + BubbleChart + BumpChart
// @MX:SPEC: SPEC-TOPDOWN-001D, SPEC-TOPDOWN-002F, SPEC-TOPDOWN-002D, SPEC-SECTOR-UX-001 M4
import { useState, useMemo, useEffect } from 'react'
import type { ReactElement } from 'react'
import type { SectorRankItem } from '../../types/market'
import { useMarket } from '../../contexts/MarketContext'
import { useNavIntent } from '../../contexts/TabContext'
import { useSelection } from '../../contexts/SelectionContext'
import { useAnalysisParams } from '../../contexts/AnalysisParamsContext'
import type { Period, Market } from '../../contexts/AnalysisParamsContext'
import { compareNumericNullsLast } from '../../utils/sort'
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
const PERIOD_LABELS: Record<Period, string> = { '1w': '1W', '1m': '1M', '3m': '3M' }
const PERIOD_VALUES: Period[] = ['1w', '1m', '3m']

// RRG/Bump 서브탭 이름 — 기간 토글 비활성 대상 (AC-SUX-027). 자체 시간 파라미터(lookback/weeks)를 가진다.
const PERIOD_DISABLED_SUBTABS: SubTab[] = ['rrg', 'bump']

// 시장 값 (all/kospi/kosdaq) — 백엔드 전송 필터 소문자 (01 §8). 표시 라벨은 All/KOSPI/KOSDAQ.
const MARKET_VALUES: Market[] = ['all', 'kospi', 'kosdaq']
const MARKET_LABELS: Record<Market, string> = { all: 'All', kospi: 'KOSPI', kosdaq: 'KOSDAQ' }

// Map sort field names to sector property accessors
function getSortValue(sector: SectorRankItem, field: string): number | null {
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
    case 'composite_score': return sector.composite_score
    default: return sector.composite_score
  }
}

// AC-SUX-027: 비활성 서브탭에서 기간 토글에 붙이는 툴팁 문구.
function periodDisabledTooltip(subTab: SubTab): string {
  if (subTab === 'rrg') return 'RRG는 자체 lookback(주) 시간 파라미터를 사용합니다 — 기간 토글은 Table/Bubble에서만 동작합니다'
  if (subTab === 'bump') return 'Bump는 자체 weeks(구간) 시간 파라미터를 사용합니다 — 기간 토글은 Table/Bubble에서만 동작합니다'
  return ''
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
  // AC-SUX-024 (REQ-SUX-022): null/NaN 을 항상 마지막에 둔다 (방향 무관) — compareNumericNullsLast.
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
      return compareNumericNullsLast(aVal, bVal, sortDirection)
    })

    return sectors
  }, [sectorRanking, sortField, sortDirection])

  // AC-SUX-023 (REQ-SUX-021): period 또는 market 이 바뀌면 정렬을 rank/asc 로 리셋한다.
  // (period 토글이 정렬 키를 excess 필드로 바꾸던 기존 동작은 AC-SUX-023 이 폐기 — rank/asc 복귀.)
  useEffect(() => {
    setSortField('rank')
    setSortDirection('asc')
  }, [period, market])

  const handlePeriodChange = (newPeriod: Period): void => {
    setPeriod(newPeriod)
  }

  const handleSort = (field: string): void => {
    if (field === sortField) {
      setSortDirection(d => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortField(field)
      setSortDirection(field === 'rank' ? 'asc' : 'desc')
    }
  }

  // AC-SUX-022 (REQ-SUX-020): 비-rank 정렬 시 [순위순으로] 복귀.
  const resetToRankSort = (): void => {
    setSortField('rank')
    setSortDirection('asc')
  }

  const isRankSorted = sortField === 'rank' && sortDirection === 'asc'

  // ② 봉투 필드 (AC-SUX-019 제외 목록 / AC-SUX-025 기준일)
  const excluded = sectorRanking?.excluded ?? []
  const baselineDate = sectorRanking?.baseline_date ?? null

  const selectedSectorData = selectedSector
    ? sortedSectors.find(s => s.name === selectedSector)
    : null
  // AC-SUX-020 (REQ-SUX-018): 선택 섹터가 제외 대상이 되어도 선택을 유지 — 상세 패널 자리에 안내.
  const selectedSectorExcluded = selectedSector
    ? excluded.find(e => e.sector === selectedSector)
    : undefined

  return (
    <div className="sector-analysis">
      {/* AC-SUX-008: 헤더 단일 인스턴스 토글 — 기간·시장 각각 화면당 1개. 서브탭 전체에 걸쳐 공유. */}
      <div className="sector-analysis-header-toggle">
        <div
          className="period-toggle"
          data-testid="period-toggle"
          title={PERIOD_DISABLED_SUBTABS.includes(subTab) ? periodDisabledTooltip(subTab) : undefined}
        >
          {PERIOD_VALUES.map(p => (
            <button
              key={p}
              className={period === p ? 'active' : undefined}
              // AC-SUX-027 (REQ-SUX-025): RRG/Bump 서브탭에서는 자체 시간 파라미터를 쓰므로 기간 토글을 비활성(숨김 아님) + 툴팁.
              disabled={PERIOD_DISABLED_SUBTABS.includes(subTab)}
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
          {/* AC-SUX-022 (REQ-SUX-020): 비-rank 정렬 고지 띠 — 현재 정렬 기준·period·market 표기 + [순위순으로] 복귀 */}
          {!isRankSorted && (
            <div className="sort-notice" data-testid="sort-notice">
              <span className="sort-notice-text">
                {sortField} {sortDirection === 'asc' ? '↑' : '↓'} 기준 정렬 · 기간 {period} · 시장 {market} — 순위와 다릅니다.
              </span>
              <button
                type="button"
                className="sort-notice-reset"
                onClick={resetToRankSort}
              >
                [순위순으로]
              </button>
            </div>
          )}

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
            excluded={excluded}
            baselineDate={baselineDate}
          />

          {/* AC-SUX-020: 선택 섹터가 제외되면 선택을 유지하고 상세 패널 자리에 안내 (조용한 해제 금지). */}
          {selectedSector && selectedSectorExcluded && (
            <div className="sector-excluded-notice" data-testid="sector-excluded-notice">
              이 시장 필터에서는 표본 부족(n={selectedSectorExcluded.count})으로 순위 대상에서 제외되었습니다.
            </div>
          )}

          {selectedSector && !selectedSectorExcluded && selectedSectorData && (
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
