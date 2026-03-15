// @MX:ANCHOR: [AUTO] BumpChart는 섹터 순위 변동을 12주 bump chart(ranked line chart)로 시각화
// @MX:REASON: SectorAnalysis에서 bump 서브탭 활성화 시 마운트; onSectorClick 통해 Table 탭 연동
// @MX:SPEC: SPEC-TOPDOWN-002D
import { useState, useEffect, useCallback, useMemo } from 'react'
import type { ReactElement } from 'react'
import ReactECharts from 'echarts-for-react'
import { fetchSectorHistory } from '../../api/history'
import type { SectorHistoryItem } from '../../api/history'

// 섹터별 구분색 팔레트 (12색)
const SECTOR_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
  '#BB8FCE', '#85C1E9', '#F0B27A', '#82E0AA',
]

// Top-N 필터 옵션
type TopFilter = 5 | 10 | 'all'
const TOP_FILTER_LABELS: Record<string, string> = {
  '5': 'Top 5',
  '10': 'Top 10',
  'all': '전체',
}

interface Props {
  // 섹터 클릭 시 Table 탭으로 이동하며 해당 섹터 선택
  onSectorClick?: (sectorName: string) => void
}

export function BumpChart({ onSectorClick }: Props): ReactElement {
  const [sectors, setSectors] = useState<SectorHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [topFilter, setTopFilter] = useState<TopFilter>('all')

  // 히스토리 데이터 로드 (12주)
  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchSectorHistory(12)
      setSectors(res.sectors)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  // Top-N 필터 적용: 12주 중 한 번이라도 Top-N에 들어간 섹터만 표시
  const filteredSectors = useMemo((): SectorHistoryItem[] => {
    if (topFilter === 'all') return sectors

    const n = topFilter as number
    return sectors.filter(sector =>
      sector.history.some(week => week.rank <= n)
    )
  }, [sectors, topFilter])

  // X축 날짜 레이블 (모든 섹터의 첫 번째 히스토리에서 추출)
  const dates = useMemo((): string[] => {
    if (filteredSectors.length === 0) return []
    return filteredSectors[0].history.map(w => w.date)
  }, [filteredSectors])

  // 전체 섹터 수 (Y축 max 계산용)
  const totalSectors = sectors.length

  // ECharts 시리즈 데이터 구성
  const seriesData = useMemo(() => {
    return filteredSectors.map((sector, idx) => ({
      name: sector.name,
      type: 'line' as const,
      data: sector.history.map(w => w.rank),
      // 마지막 순위값 endLabel로 섹터명 표시
      endLabel: {
        show: true,
        formatter: '{a}',
        color: '#e5e7eb',
        fontSize: 11,
      },
      // 호버 시 해당 시리즈 강조, 나머지 흐리게
      emphasis: {
        focus: 'series',
        blurScope: 'global',
        lineStyle: { width: 3 },
      },
      blur: {
        lineStyle: { opacity: 0.15 },
        itemStyle: { opacity: 0.15 },
      },
      lineStyle: {
        width: 2,
        color: SECTOR_COLORS[idx % SECTOR_COLORS.length],
      },
      itemStyle: {
        color: SECTOR_COLORS[idx % SECTOR_COLORS.length],
      },
      smooth: false,
      symbol: 'circle',
      symbolSize: 6,
    }))
  }, [filteredSectors])

  // ECharts 옵션 구성
  const chartOption = useMemo(() => ({
    backgroundColor: 'transparent',
    animation: true,
    grid: {
      left: 60,
      right: 120,  // endLabel 공간 확보
      top: 20,
      bottom: 40,
    },
    xAxis: {
      type: 'category' as const,
      data: dates,
      axisLabel: {
        color: '#9ca3af',
        fontSize: 11,
        // 날짜가 많을 경우 일부만 표시
        interval: Math.max(0, Math.floor(dates.length / 6) - 1),
      },
      axisLine: { lineStyle: { color: '#2d2d44' } },
      splitLine: {
        show: true,
        lineStyle: { color: '#2d2d44', type: 'dashed' },
      },
    },
    yAxis: {
      type: 'value' as const,
      // rank 1을 맨 위에 배치하기 위해 역방향
      inverse: true,
      min: 1,
      max: totalSectors || 20,
      axisLabel: {
        color: '#9ca3af',
        fontSize: 11,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: (value: any) => `${value}위`,
      },
      axisLine: { lineStyle: { color: '#2d2d44' } },
      splitLine: {
        lineStyle: { color: '#2d2d44', type: 'dashed' },
      },
    },
    tooltip: {
      trigger: 'item' as const,
      backgroundColor: '#1a1a2e',
      borderColor: '#2d2d44',
      textStyle: { color: '#e5e7eb', fontSize: 12 },
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter: (params: any) => {
        const sectorName: string = params.seriesName
        const weekDate: string = params.name
        const rank: number = params.value

        // 해당 섹터·날짜의 composite_score를 sectors에서 찾아 표시
        const sector = sectors.find(s => s.name === sectorName)
        const weekData = sector?.history.find(w => w.date === weekDate)
        const score = weekData ? weekData.composite_score.toFixed(2) : '-'

        return [
          `<b>${sectorName}</b>`,
          `날짜: ${weekDate}`,
          `순위: ${rank}위`,
          `종합점수: ${score}`,
        ].join('<br/>')
      },
    },
    series: seriesData,
  }), [dates, seriesData, sectors, totalSectors])

  // 섹터 클릭 이벤트 핸들러 (라인 클릭 → Table 탭 이동)
  const handleChartClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (params: any) => {
      if (params.seriesName && onSectorClick) {
        onSectorClick(params.seriesName)
      }
    },
    [onSectorClick],
  )

  const onEvents = useMemo(() => ({
    click: handleChartClick,
  }), [handleChartClick])

  return (
    <div className="bump-chart-container">
      {/* 툴바: Top-N 필터 */}
      <div className="bump-chart-toolbar">
        <div className="bump-top-filter">
          {(['5', '10', 'all'] as const).map(val => {
            const filterVal = val === 'all' ? 'all' : (Number(val) as 5 | 10)
            return (
              <button
                key={val}
                className={topFilter === filterVal ? 'active' : undefined}
                onClick={() => setTopFilter(filterVal)}
              >
                {TOP_FILTER_LABELS[val]}
              </button>
            )
          })}
        </div>
      </div>

      {/* 차트 본문 */}
      <div className="bump-chart-body">
        {loading && (
          <div className="bump-loading">데이터 로딩 중...</div>
        )}
        {!loading && error && (
          <div className="bump-error">{error}</div>
        )}
        {!loading && !error && filteredSectors.length > 0 && (
          <ReactECharts
            option={chartOption}
            style={{ width: '100%', height: '100%' }}
            onEvents={onEvents}
            notMerge={true}
            lazyUpdate={false}
          />
        )}
        {!loading && !error && filteredSectors.length === 0 && (
          <div className="bump-loading">표시할 데이터가 없습니다</div>
        )}
      </div>
    </div>
  )
}
