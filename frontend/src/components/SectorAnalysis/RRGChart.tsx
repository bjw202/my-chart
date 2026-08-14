// @MX:NOTE: [AUTO] RRGChart - StockCharts 스타일 Relative Rotation Graph
// @MX:SPEC: SPEC-TOPDOWN-002B
// DB 전체 기간에서 8주 윈도우 슬라이딩, 벤치마크 스파크라인 + 하이라이트
import { useState, useEffect, useCallback, useMemo } from 'react'
import type { ReactElement } from 'react'
import ReactECharts from 'echarts-for-react'
import { fetchRRGData } from '../../api/rrg'
import type { RRGResponse, RRGSectorItem, KospiPoint } from '../../types/rrg'
import { useAnalysisParams } from '../../contexts/AnalysisParamsContext'
import { metricText, toMetricValue } from '../common/MetricCell'

// 시장 필터 → 벤치마크 이름 (VZ-7/VZ-10). RRG 기준선 100 = 벤치마크 동일 성과.
// @MX:NOTE: [AUTO] RRG 벤치마크 라벨은 market 필터 추종. 응답에 benchmark 필드 없어 client 파생.
const MARKET_BENCHMARK_LABEL: Record<string, string> = {
  all: '전체 상한가중',
  kospi: 'KOSPI',
  kosdaq: 'KOSDAQ',
}

const SECTOR_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
  '#BB8FCE', '#85C1E9', '#F0B27A', '#82E0AA',
]

const QUADRANT_COLORS = {
  leading: 'rgba(34, 197, 94, 0.15)',
  weakening: 'rgba(250, 204, 21, 0.12)',
  lagging: 'rgba(239, 68, 68, 0.12)',
  improving: 'rgba(96, 165, 250, 0.12)',
}

const TRAIL_WINDOW = 8 // 8주 트레일 윈도우

// VZ-8 (AC-SUX-045): RRG 축 자동 대칭 반폭. half = max(5, ceil(maxDev × 1.1)).
// 100 중심 대칭(min=100−half, max=100+half). 최소 반폭 5 로 과확대 방지.
// @MX:ANCHOR: [AUTO] RRG 축 반폭 공식 — plan §3.3 / 02-screen-flow.md §9.4 VZ-8 리터럴 고정.
// @MX:REASON: 공식(×1.1 계수·max(5,…) 하한) 변경 시 100-중심 대칭·과확대 방지가 동시에 깨짐. AC-SUX-045 대조 단언이 본 함수에 의존.
export function rrgHalf(maxDev: number): number {
  return Math.max(5, Math.ceil(maxDev * 1.1))
}

interface RRGChartProps {
  onSectorClick?: (sectorName: string) => void
}

// ── 벤치마크 스파크라인 컴포넌트 ──
function KospiSparkline({
  kospiData, allDates, windowEnd, windowSize, onWindowEndChange, benchmarkLabel, trailStartDate,
}: {
  kospiData: KospiPoint[]
  allDates: string[]
  windowEnd: number
  windowSize: number
  onWindowEndChange: (idx: number) => void
  benchmarkLabel: string
  trailStartDate: string | null
}): ReactElement {
  const svgWidth = 700
  const svgHeight = 55

  if (kospiData.length < 2 || allDates.length < 2) {
    return (
      <div style={{ height: svgHeight }}>
        <input type="range" min={windowSize} max={allDates.length} value={windowEnd}
          onChange={(e) => onWindowEndChange(Number(e.target.value))}
          className="rrg-slider" style={{ width: '100%' }} />
      </div>
    )
  }

  // allDates 범위에 해당하는 벤치마크 데이터 매핑
  const dateSet = new Set(allDates)
  const relevantKospi = kospiData.filter((k) => dateSet.has(k.date))
  if (relevantKospi.length < 2) {
    return (
      <div style={{ height: svgHeight }}>
        <input type="range" min={windowSize} max={allDates.length} value={windowEnd}
          onChange={(e) => onWindowEndChange(Number(e.target.value))}
          className="rrg-slider" style={{ width: '100%' }} />
      </div>
    )
  }

  const closes = relevantKospi.map((k) => k.close)
  const minC = Math.min(...closes)
  const maxC = Math.max(...closes)
  const rng = maxC - minC || 1

  const points = relevantKospi.map((k, i) => ({
    x: 2 + (i / (relevantKospi.length - 1)) * (svgWidth - 4),
    y: 2 + (1 - (k.close - minC) / rng) * (svgHeight - 4),
    date: k.date,
  }))
  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
  const areaPath = linePath + ` L${points[points.length - 1].x},${svgHeight} L${points[0].x},${svgHeight} Z`

  // 8주 윈도우 하이라이트 영역 계산
  const winStartDate = allDates[Math.max(0, windowEnd - windowSize)]
  const winEndDate = allDates[windowEnd - 1]
  const hlStart = points.find((p) => p.date >= winStartDate)
  const hlEnd = [...points].reverse().find((p) => p.date <= winEndDate)
  const hlX1 = hlStart ? hlStart.x : 0
  const hlX2 = hlEnd ? hlEnd.x : svgWidth

  // 현재 종가
  const currentClose = relevantKospi[relevantKospi.length - 1]?.close ?? 0
  const endDateLabel = allDates[windowEnd - 1] ?? ''

  return (
    <div className="rrg-sparkline-container">
      <div className="rrg-sparkline-header">
        <span className="rrg-sparkline-title">
          {/* VZ-9/VZ-10: 벤치마크 라벨(market 추종) + lookback(TRAIL_WINDOW) + 궤적 시작일. */}
          {benchmarkLabel} ({TRAIL_WINDOW}주 lookback{trailStartDate ? ` · 궤적 시작 ${trailStartDate}` : ''} · 종료 {endDateLabel})
        </span>
        <span className="rrg-sparkline-price">
          {currentClose.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}
        </span>
      </div>
      <svg width="100%" height={svgHeight} viewBox={`0 0 ${svgWidth} ${svgHeight}`} preserveAspectRatio="none">
        <path d={areaPath} fill="rgba(156,163,175,0.08)" />
        <rect x={hlX1} y={0} width={Math.max(hlX2 - hlX1, 3)} height={svgHeight}
          fill="rgba(100,100,100,0.35)" />
        <path d={linePath} fill="none" stroke="#9ca3af" strokeWidth="1.5" />
        <line x1={hlX1} y1={0} x2={hlX1} y2={svgHeight} stroke="#6b7280" strokeWidth="1" />
        <line x1={hlX2} y1={0} x2={hlX2} y2={svgHeight} stroke="#6b7280" strokeWidth="1" />
      </svg>
      <input type="range" min={windowSize} max={allDates.length} value={windowEnd}
        onChange={(e) => onWindowEndChange(Number(e.target.value))}
        className="rrg-slider" style={{ width: '100%', marginTop: '2px' }} />
    </div>
  )
}

// ── 메인 RRG 차트 ──
export function RRGChart({ onSectorClick }: RRGChartProps): ReactElement {
  // VZ-10: 벤치마크 라벨은 market 필터 추종 (데이터 시리즈 자체는 API 미지원으로 debt).
  const { market } = useAnalysisParams()
  const benchmarkLabel = MARKET_BENCHMARK_LABEL[market] ?? '전체 상한가중'
  const [data, setData] = useState<RRGResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [visibleSectors, setVisibleSectors] = useState<Set<string>>(new Set())
  // windowEnd: 8주 윈도우의 끝 인덱스 (1-based, allDates 기준)
  const [windowEnd, setWindowEnd] = useState<number>(0)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchRRGData()
      .then((res) => {
        if (cancelled) return
        setData(res)
        setVisibleSectors(new Set(res.sectors.map((s) => s.name)))
        // 전체 날짜 수 계산, 슬라이더를 끝으로
        const maxLen = Math.max(...res.sectors.map((s) => s.trail.length), 0)
        setWindowEnd(maxLen)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setError(err.message ?? 'RRG 데이터 로드 실패')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  // 전체 RRG 날짜 목록 (가장 긴 trail에서 추출)
  const allDates = useMemo(() => {
    if (!data) return []
    const longest = data.sectors.reduce((a, b) =>
      a.trail.length >= b.trail.length ? a : b, data.sectors[0])
    return longest?.trail.map((t) => t.date) ?? []
  }, [data])

  const handleToggleAll = useCallback((selectAll: boolean) => {
    if (!data) return
    setVisibleSectors(selectAll ? new Set(data.sectors.map((s) => s.name)) : new Set())
  }, [data])

  const handleToggleSector = useCallback((name: string) => {
    setVisibleSectors((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }, [])

  // ECharts 옵션: windowEnd 기준 8주 윈도우 슬라이스
  const buildOption = useCallback((sectors: RRGSectorItem[]): object => {
    const visible = sectors.filter((s) => visibleSectors.has(s.name))
    const winStart = Math.max(0, windowEnd - TRAIL_WINDOW)
    const winEndIdx = windowEnd

    const bgSeries = {
      type: 'line', name: '__bg__', data: [], silent: true, legendHoverLink: false,
      markArea: {
        silent: true,
        data: [
          [{ xAxis: 100, yAxis: 100, itemStyle: { color: QUADRANT_COLORS.leading } }, { xAxis: 125, yAxis: 125 }],
          [{ xAxis: 100, yAxis: 75, itemStyle: { color: QUADRANT_COLORS.weakening } }, { xAxis: 125, yAxis: 100 }],
          [{ xAxis: 75, yAxis: 75, itemStyle: { color: QUADRANT_COLORS.lagging } }, { xAxis: 100, yAxis: 100 }],
          [{ xAxis: 75, yAxis: 100, itemStyle: { color: QUADRANT_COLORS.improving } }, { xAxis: 100, yAxis: 125 }],
        ],
      },
      markLine: {
        silent: true, symbol: 'none',
        lineStyle: { color: '#6b7280', type: 'solid', width: 1 },
        data: [{ xAxis: 100 }, { yAxis: 100 }],
        label: { show: false },
      },
    }

    // VZ-7: 사분면 라벨에 벤치마크 대비 의미 병기. 벤치마크 이름은 market 필터 추종.
    const quadrantLabels = [
      { text: `Leading (${benchmarkLabel} 대비 강함·개선)`, x: '80%', y: '8%', color: 'rgba(34,197,94,0.5)' },
      { text: `Weakening (${benchmarkLabel} 대비 강함·약화)`, x: '80%', y: '90%', color: 'rgba(250,204,21,0.5)' },
      { text: `Lagging (${benchmarkLabel} 대비 약함·미개선)`, x: '8%', y: '90%', color: 'rgba(239,68,68,0.5)' },
      { text: `Improving (${benchmarkLabel} 대비 약함·개선)`, x: '8%', y: '8%', color: 'rgba(96,165,250,0.5)' },
    ]

    const sectorSeries = visible.map((sector, idx) => {
      const color = SECTOR_COLORS[idx % SECTOR_COLORS.length]
      // 8주 윈도우 슬라이스
      const slice = sector.trail.slice(winStart, winEndIdx)
      if (slice.length === 0) return null

      const points = slice.map((p) => [p.rs_ratio, p.rs_momentum])
      const total = points.length

      return {
        type: 'line', name: sector.name, showSymbol: true, smooth: true,
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        data: points.map((pt: any, i: number) => ({
          value: pt,
          symbol: 'circle',
          symbolSize: i === total - 1 ? 14 : Math.max(3, 3 + (i / Math.max(total - 1, 1)) * 5),
          itemStyle: { color, opacity: 0.15 + (i / Math.max(total - 1, 1)) * 0.85 },
          label: i === total - 1
            ? { show: true, formatter: sector.name, position: 'right', color: '#e5e7eb', fontSize: 11 }
            : { show: false },
        })),
        lineStyle: { color, width: 2, opacity: 0.7 },
        emphasis: { focus: 'series', blurScope: 'global', lineStyle: { width: 3 } },
      }
    }).filter(Boolean)

    // VZ-8 (AC-SUX-045): 100 중심 자동 대칭 축. half = max(5, ceil(max|v−100| × 1.1)).
    // 표시 중인 점의 rs_ratio·rs_momentum 에서 최대 편차를 측정. 최소 반폭 5(과확대 방지).
    let maxDev = 0
    for (const sector of visible) {
      const slice = sector.trail.slice(winStart, winEndIdx)
      for (const p of slice) {
        maxDev = Math.max(maxDev, Math.abs(p.rs_ratio - 100), Math.abs(p.rs_momentum - 100))
      }
    }
    const half = rrgHalf(maxDev)

    return {
      backgroundColor: 'transparent',
      graphic: quadrantLabels.map((q) => ({
        type: 'text', left: q.x, top: q.y, silent: true,
        style: { text: q.text, fill: q.color, fontSize: 16, fontWeight: 'bold' },
      })),
      grid: { left: 60, right: 120, top: 20, bottom: 50 },
      xAxis: {
        type: 'value', name: 'JdK RS-Ratio', nameLocation: 'middle', nameGap: 32,
        nameTextStyle: { color: '#9ca3af', fontSize: 12 },
        axisLine: { lineStyle: { color: '#9ca3af' } },
        axisLabel: { color: '#9ca3af', fontSize: 11 },
        splitLine: { show: true, lineStyle: { color: '#2d2d44', type: 'dashed' } },
        min: 100 - half, max: 100 + half,
      },
      yAxis: {
        type: 'value', name: 'JdK RS-Momentum', nameLocation: 'middle', nameGap: 50,
        nameTextStyle: { color: '#9ca3af', fontSize: 12 },
        axisLine: { lineStyle: { color: '#9ca3af' } },
        axisLabel: { color: '#9ca3af', fontSize: 11 },
        splitLine: { show: true, lineStyle: { color: '#2d2d44', type: 'dashed' } },
        min: 100 - half, max: 100 + half,
      },
      legend: { show: false },
      tooltip: {
        trigger: 'item', backgroundColor: '#1a1a2e', borderColor: '#2d2d44',
        textStyle: { color: '#e5e7eb', fontSize: 12 },
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: (params: any) => {
          if (!params || params.seriesName === '__bg__') return ''
          const pt = params.data?.value ?? params.data
          if (!pt) return ''
          const q = Number(pt[0]) > 100
            ? (Number(pt[1]) > 100 ? 'Leading' : 'Weakening')
            : (Number(pt[1]) > 100 ? 'Improving' : 'Lagging')
          // D2: 결측 표기는 표 셀(MetricCell)과 같은 metricText 로 생성한다.
          // 값이 있을 때의 포맷(toFixed(2))은 종전과 동일하다.
          return [
            `<b>${params.seriesName}</b>`,
            `RS-Ratio: ${metricText(toMetricValue(pt[0]), n => n.toFixed(2))}`,
            `RS-Momentum: ${metricText(toMetricValue(pt[1]), n => n.toFixed(2))}`,
            `Quadrant: ${q}`,
          ].join('<br/>')
        },
      },
      series: [bgSeries, ...sectorSeries],
    }
  }, [visibleSectors, windowEnd, benchmarkLabel])

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleChartClick = useCallback((params: any) => {
    if (!params || params.seriesName === '__bg__') return
    onSectorClick?.(params.seriesName)
  }, [onSectorClick])

  if (loading) return <div className="rrg-chart-container"><div className="rrg-chart-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}><span style={{ color: 'var(--text-muted)' }}>RRG 데이터 로딩 중...</span></div></div>
  if (error) return <div className="rrg-chart-container"><div className="rrg-chart-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}><span style={{ color: 'var(--error)' }}>오류: {error}</span></div></div>
  if (!data || data.sectors.length === 0) return <div className="rrg-chart-container"><div className="rrg-chart-body" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}><span style={{ color: 'var(--text-muted)' }}>RRG 데이터가 없습니다.</span></div></div>

  const option = buildOption(data.sectors)

  // VZ-9: 궤적 시작일 = 이용 가능한 가장 이른 trail 날짜 (응답에 trail_start_date 필드 없어 client 파생).
  const trailStartDate = allDates.length > 0 ? allDates[0] : null

  return (
    <div className="rrg-chart-container">
      {/* VZ-7: 기준선 100 = 벤치마크 동일성 상설 고지 (벤치마크 이름은 market 추종). */}
      <div className="rrg-baseline-legend" data-testid="rrg-baseline-legend">
        기준선 100 = 벤치마크({benchmarkLabel})와 동일 성과 · 롤링 정규화 미적용(표준 JdK RRG와 발산)
      </div>
      <div className="rrg-main-area">
        <KospiSparkline
          kospiData={data.kospi}
          allDates={allDates}
          windowEnd={windowEnd}
          windowSize={TRAIL_WINDOW}
          onWindowEndChange={setWindowEnd}
          benchmarkLabel={benchmarkLabel}
          trailStartDate={trailStartDate}
        />
        <div className="rrg-chart-body">
          <ReactECharts
            option={option}
            style={{ width: '100%', height: '100%' }}
            onEvents={{ click: handleChartClick }}
            notMerge lazyUpdate={false}
          />
        </div>
      </div>

      <div className="rrg-filter-panel">
        <div className="rrg-filter-header">
          <button className="rrg-filter-toggle-btn" onClick={() => handleToggleAll(true)}>전체 선택</button>
          <button className="rrg-filter-toggle-btn" onClick={() => handleToggleAll(false)}>전체 해제</button>
        </div>
        <div className="rrg-filter-list">
          {data.sectors.map((sector, idx) => (
            <label key={sector.name} className="rrg-filter-item">
              <input type="checkbox" checked={visibleSectors.has(sector.name)}
                onChange={() => handleToggleSector(sector.name)} />
              <span className="rrg-filter-color-dot" style={{ backgroundColor: SECTOR_COLORS[idx % SECTOR_COLORS.length] }} />
              <span className="rrg-filter-label">{sector.name}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}
