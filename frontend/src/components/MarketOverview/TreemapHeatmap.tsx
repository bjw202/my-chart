import { useEffect, useState, useCallback } from 'react'
import type { ReactElement } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { fetchTreemap } from '../../api/treemap'
import type { TreemapResponse, TreemapSectorNode, TreemapStockNode } from '../../types/treemap'

// @MX:ANCHOR: [AUTO] TreemapHeatmap - ECharts 트리맵 컴포넌트 (드릴다운 포함)
// @MX:REASON: MarketOverview에서 직접 소비되는 주요 데이터 시각화 컴포넌트

export interface TreemapHeatmapProps {
  period: string
  onStockClick?: (stockName: string) => void
}

// 기간 옵션 정의
const PERIOD_OPTIONS = [
  { label: '1W', value: '1w' },
  { label: '1M', value: '1m' },
  { label: '3M', value: '3m' },
] as const

// price_change 값을 기반으로 트리맵 색상 결정
function getPriceChangeColor(priceChange: number): string {
  if (priceChange > 5) return '#006400'      // 짙은 초록 (> +5%)
  if (priceChange > 2) return '#228B22'      // 숲 초록 (+2~5%)
  if (priceChange > 0.5) return '#90EE90'   // 연한 초록 (+0.5~2%)
  if (priceChange >= -0.5) return '#808080' // 회색 (±0.5%)
  if (priceChange >= -2) return '#FFB6C1'   // 연한 핑크 (-0.5~2%)
  if (priceChange >= -5) return '#DC143C'   // 크림슨 (-2~5%)
  return '#8B0000'                           // 짙은 빨강 (< -5%)
}

// 시가총액을 억원 단위로 포맷
function formatMarketCap(value: number): string {
  const okuWon = Math.round(value / 100_000_000)
  return okuWon.toLocaleString('ko-KR', { maximumFractionDigits: 0 }) + '억원'
}

// API 응답을 ECharts 트리맵 데이터 형식으로 변환
function transformToTreemapData(
  sectors: TreemapSectorNode[],
): object[] {
  return sectors.map((sector: TreemapSectorNode) => ({
    name: sector.name,
    value: sector.market_cap,
    price_change: sector.price_change,
    itemStyle: {
      color: getPriceChangeColor(sector.price_change),
    },
    children: sector.stocks.map((stock: TreemapStockNode) => ({
      name: stock.name,
      value: stock.market_cap,
      price_change: stock.price_change,
      rs_12m: stock.rs_12m,
      stage: stock.stage,
      itemStyle: {
        color: getPriceChangeColor(stock.price_change),
      },
    })),
  }))
}

// @MX:NOTE: [AUTO] ECharts 트리맵 옵션 빌더 - 섹터/종목 2단계 드릴다운
function buildChartOption(data: object[]): EChartsOption {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return {
    backgroundColor: 'transparent',
    series: [
      {
        type: 'treemap',
        data,
        roam: false,
        nodeClick: 'zoomToNode',
        breadcrumb: {
          show: true,
          top: 0,
          itemStyle: { color: '#2d2d44' },
          textStyle: { color: '#e5e7eb' },
        },
        label: {
          show: true,
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          formatter: (params: any) => {
            const d = params.data as { price_change?: number }
            const pct = d.price_change !== undefined ? d.price_change.toFixed(2) : '0.00'
            return `{name|${params.name}}\n{pct|${Number(pct) >= 0 ? '+' : ''}${pct}%}`
          },
          rich: {
            name: {
              color: '#e5e7eb',
              fontSize: 11,
              lineHeight: 16,
            },
            pct: {
              color: '#e5e7eb',
              fontSize: 10,
              lineHeight: 14,
            },
          },
        },
        upperLabel: {
          show: true,
          height: 24,
          color: '#e5e7eb',
          fontSize: 12,
          fontWeight: 'bold',
        },
        levels: [
          {
            // 루트 레벨
            itemStyle: { borderColor: '#2d2d44', borderWidth: 2, gapWidth: 2 },
          },
          {
            // 섹터 레벨
            itemStyle: { borderColor: '#2d2d44', borderWidth: 1, gapWidth: 1 },
            upperLabel: { show: true },
          },
          {
            // 종목 레벨
            itemStyle: { borderColor: '#1a1a2e', borderWidth: 0.5, gapWidth: 0.5 },
            label: { show: true },
          },
        ],
      },
    ],
    visualMap: {
      type: 'piecewise',
      show: true,
      pieces: [
        { min: 5, color: '#006400', label: '> +5%' },
        { min: 2, max: 5, color: '#228B22', label: '+2~5%' },
        { min: 0.5, max: 2, color: '#90EE90', label: '+0.5~2%' },
        { min: -0.5, max: 0.5, color: '#808080', label: '±0.5%' },
        { min: -2, max: -0.5, color: '#FFB6C1', label: '-0.5~2%' },
        { min: -5, max: -2, color: '#DC143C', label: '-2~5%' },
        { max: -5, color: '#8B0000', label: '< -5%' },
      ],
      textStyle: { color: '#9ca3af' },
      orient: 'horizontal',
      bottom: 0,
      left: 'center',
    },
    tooltip: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      formatter: (params: any) => {
        const d = params.data as {
          price_change?: number
          rs_12m?: number
          stage?: number | null
          value?: number
        }
        if (!d) return ''
        const pct = d.price_change !== undefined
          ? `${d.price_change >= 0 ? '+' : ''}${d.price_change.toFixed(2)}%`
          : '-'
        const cap = d.value !== undefined ? formatMarketCap(d.value) : '-'
        const rs = d.rs_12m !== undefined ? d.rs_12m.toFixed(1) : '-'
        const stage = d.stage !== undefined && d.stage !== null ? `Stage ${d.stage}` : '-'
        return [
          `<b>${params.name}</b>`,
          `시가총액: ${cap}`,
          `수익률: ${pct}`,
          // 종목 레벨에만 RS/스테이지 표시
          ...(d.rs_12m !== undefined ? [`RS(12M): ${rs}`, `스테이지: ${stage}`] : []),
        ].join('<br/>')
      },
    },
  } as EChartsOption
}

export function TreemapHeatmap({ period, onStockClick }: TreemapHeatmapProps): ReactElement {
  const [activePeriod, setActivePeriod] = useState<string>(period)
  const [data, setData] = useState<TreemapResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    setError(null)
    fetchTreemap(activePeriod)
      .then((res) => {
        setData(res)
        setLoading(false)
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : '데이터 로드 실패'
        setError(message)
        setLoading(false)
      })
  }, [activePeriod])

  // ECharts 클릭 이벤트 핸들러 - 종목 레벨(자식 없음) 클릭 시만 동작
  const handleChartClick = useCallback(
    (params: { data?: { children?: unknown[] }; name?: string }) => {
      if (!params.data) return
      const d = params.data as { children?: unknown[] }
      // 종목 레벨은 children이 없음
      if (!d.children || d.children.length === 0) {
        if (params.name && onStockClick) {
          onStockClick(params.name)
        }
      }
    },
    [onStockClick],
  )

  const treemapData = data ? transformToTreemapData(data.sectors) : []
  const option = buildChartOption(treemapData)

  return (
    <div className="treemap-heatmap">
      <div className="treemap-heatmap-header">
        <span className="treemap-heatmap-title">시장 트리맵</span>
        <div className="period-toggle">
          {PERIOD_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={activePeriod === opt.value ? 'active' : undefined}
              onClick={() => setActivePeriod(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="treemap-heatmap-body">
        {loading && (
          <div className="treemap-heatmap-state">트리맵 데이터 로딩 중...</div>
        )}
        {!loading && error && (
          <div className="treemap-heatmap-state treemap-heatmap-error">{error}</div>
        )}
        {!loading && !error && (
          <ReactECharts
            option={option}
            style={{ width: '100%', height: '100%' }}
            onEvents={{ click: handleChartClick }}
            notMerge
            lazyUpdate
          />
        )}
      </div>
    </div>
  )
}
