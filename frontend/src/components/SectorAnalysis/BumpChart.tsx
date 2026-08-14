// @MX:ANCHOR: [AUTO] BumpChart는 섹터 순위 변동을 12주 bump chart(ranked line chart)로 시각화
// @MX:REASON: SectorAnalysis에서 bump 서브탭 활성화 시 마운트; onSectorClick 통해 Table 탭 연동
// @MX:SPEC: SPEC-TOPDOWN-002D
import { useState, useEffect, useCallback, useMemo } from 'react'
import type { ReactElement } from 'react'
import ReactECharts from 'echarts-for-react'
import { fetchSectorHistory } from '../../api/history'
import type { SectorHistoryItem } from '../../api/history'
import { formatWeeksSpan } from './bumpFormat'
import { metricText } from '../common/MetricCell'

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

// AC-SUX-028 (REQ-SUX-026): Bump 구간 컨트롤 옵션. 기본 12주.
const WEEKS_OPTIONS = [8, 12, 26] as const
const DEFAULT_WEEKS = 12

export function BumpChart({ onSectorClick }: Props): ReactElement {
  const [sectors, setSectors] = useState<SectorHistoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [topFilter, setTopFilter] = useState<TopFilter>('all')
  // AC-SUX-028: weeks 구간 + 응답의 weeks/span_days (프론트 계산 금지 — 응답 그대로 표기)
  const [weeks, setWeeks] = useState<number>(DEFAULT_WEEKS)
  const [respWeeks, setRespWeeks] = useState<number | null>(null)
  const [spanDays, setSpanDays] = useState<number | null>(null)

  // 히스토리 데이터 로드 (weeks 구간)
  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchSectorHistory(weeks)
      setSectors(res.sectors)
      setRespWeeks(res.weeks)
      setSpanDays(res.span_days ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : '데이터 로드 실패')
    } finally {
      setLoading(false)
    }
  }, [weeks])

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

  // X축 날짜 레이블: 모든 섹터 history 날짜의 합집합 (정렬·중복제거)
  // 단일 섹터 기반이 아닌 합집합을 쓰면 섹터별 history 차이가 있어도
  // 날짜 축이 항상 일관되게 정렬된다 (방어적 설계).
  const dates = useMemo((): string[] => {
    const dateSet = new Set<string>()
    filteredSectors.forEach(sector => {
      sector.history.forEach(w => dateSet.add(w.date))
    })
    return Array.from(dateSet).sort()
  }, [filteredSectors])

  // 전체 섹터 수 (Y축 max 계산용)
  const totalSectors = sectors.length

  // ECharts 시리즈 데이터 구성
  const seriesData = useMemo(() => {
    return filteredSectors.map((sector, idx) => {
      // 날짜 키 기반 매핑: dates 축의 각 날짜에 해당 섹터 순위를 매핑한다.
      // 해당 날짜 데이터가 없으면 null → ECharts가 선을 끊어 표시 (잘못된 인덱스
      // 매핑으로 인해 마지막 날 섹터가 누락되던 버그의 근본 방어).
      const rankByDate = new Map(sector.history.map(w => [w.date, w.rank]))
      return {
        name: sector.name,
        type: 'line' as const,
        data: dates.map(d => {
          const rank = rankByDate.get(d)
          return rank === undefined ? null : rank
        }),
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
        connectNulls: false,  // 누락 날짜는 선을 끊어 정확한 시각화 보장
      }
    })
  }, [filteredSectors, dates])

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
        // D2: 결측 표기는 표 셀(MetricCell)과 같은 metricText 로 생성한다.
        // 종전의 ASCII '-' 는 표의 '–'(MISSING_TEXT)와 달라 같은 결측이 화면마다 다르게 보였다.
        const score = metricText(weekData?.composite_score, n => n.toFixed(2))

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
      {/* 툴바: Top-N 필터 + AC-SUX-028 weeks 구간 컨트롤 */}
      <div className="bump-chart-toolbar">
        <div className="bump-weeks-filter" data-testid="bump-weeks-filter">
          {WEEKS_OPTIONS.map(w => (
            <button
              key={w}
              className={weeks === w ? 'active' : undefined}
              onClick={() => setWeeks(w)}
              data-weeks={w}
            >
              {w}주
            </button>
          ))}
        </div>
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

      {/* AC-SUX-028 (REQ-SUX-026): 축 하단에 weeks 와 span_days 를 병기 — 응답 값 그대로 표기(프론트 계산 금지) */}
      {!loading && !error && (
        <div className="bump-span-caption" data-testid="bump-span-caption">
          {formatWeeksSpan(respWeeks ?? weeks, spanDays)}
        </div>
      )}
    </div>
  )
}
