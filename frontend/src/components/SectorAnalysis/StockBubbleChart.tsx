// 종목 버블 차트 컴포넌트 - ECharts scatter를 이용한 종목별 버블 시각화
// X축: 가격변동률, Y축: RS Rating, 버블 크기: 거래대금, 색상: Weinstein Stage
import { useMemo } from 'react'
import type { ReactElement } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { StockBubbleItem } from '../../types/bubble'

interface Props {
  stocks: StockBubbleItem[]
  sectorName: string
  onStockClick?: (stockName: string) => void
}

// Weinstein Stage 색상 매핑
const STAGE_COLORS: Record<number, string> = {
  1: '#EAB308', // yellow-500: 축적 구간
  2: '#22C55E', // green-500: 상승 구간
  3: '#F97316', // orange-500: 분산 구간
  4: '#EF4444', // red-500: 하락 구간
}
const DEFAULT_COLOR = '#6B7280' // gray-500: stage 미분류

// 거래대금을 버블 픽셀 크기(15~70)로 정규화
function normalizeBubbleSize(value: number, min: number, max: number): number {
  if (max === min) return 35
  return 15 + ((value - min) / (max - min)) * 55
}

// 거래대금을 억원 단위로 포맷
function formatTradingValue(value: number): string {
  const eok = value / 100_000_000
  return `${eok.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}억원`
}

// 거래대금 상위 N개 종목 인덱스 반환 (라벨 표시용)
function getTopNByTradingValue(stocks: StockBubbleItem[], n: number): Set<number> {
  const indexed = stocks.map((s, i) => ({ i, tv: s.trading_value }))
  indexed.sort((a, b) => b.tv - a.tv)
  return new Set(indexed.slice(0, n).map(x => x.i))
}

export function StockBubbleChart({ stocks, sectorName, onStockClick }: Props): ReactElement {
  const option = useMemo((): EChartsOption => {
    if (!stocks.length) {
      return {
        backgroundColor: '#1a1a2e',
        graphic: [{
          type: 'text',
          left: 'center',
          top: 'middle',
          style: { text: '데이터 없음', fill: '#9ca3af', fontSize: 14 },
        }],
      }
    }

    const tradingValues = stocks.map(s => s.trading_value)
    const minTV = Math.min(...tradingValues)
    const maxTV = Math.max(...tradingValues)
    // 거래대금 상위 20개 종목만 라벨 표시
    const topNSet = getTopNByTradingValue(stocks, 20)

    // ECharts scatter 데이터: [x, y, bubbleSize, stage, name, tradingValue, stageDetail]
    const data = stocks.map((s, i) => ({
      value: [
        s.price_change,
        s.rs_12m,
        normalizeBubbleSize(s.trading_value, minTV, maxTV),
        s.stage ?? 0,
        s.name,
        s.trading_value,
        s.stage_detail ?? '',
        i, // 인덱스 (라벨 표시 여부 판단용)
      ],
      itemStyle: {
        color: s.stage ? (STAGE_COLORS[s.stage] ?? DEFAULT_COLOR) : DEFAULT_COLOR,
        opacity: 0.85,
      },
      label: {
        show: topNSet.has(i),
        formatter: s.name,
        position: 'top' as const,
        fontSize: 9,
        color: '#e5e7eb',
      },
    }))

    return {
      backgroundColor: '#1a1a2e',
      title: {
        text: `${sectorName} 종목 버블`,
        left: 'center',
        top: 8,
        textStyle: { color: '#9ca3af', fontSize: 13, fontWeight: 'normal' },
      },
      grid: { left: 60, right: 120, top: 50, bottom: 60 },
      xAxis: {
        type: 'value',
        name: '가격 변동률 %',
        nameLocation: 'middle',
        nameGap: 35,
        nameTextStyle: { color: '#9ca3af', fontSize: 12 },
        axisLine: { lineStyle: { color: '#2d2d44' } },
        axisTick: { lineStyle: { color: '#2d2d44' } },
        axisLabel: {
          color: '#9ca3af',
          formatter: (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
        },
        splitLine: { lineStyle: { color: '#2d2d44', type: 'dashed' } },
      },
      yAxis: {
        type: 'value',
        name: 'RS Rating (0-100)',
        nameLocation: 'middle',
        nameGap: 45,
        nameTextStyle: { color: '#9ca3af', fontSize: 12 },
        min: 0,
        max: 100,
        axisLine: { lineStyle: { color: '#2d2d44' } },
        axisTick: { lineStyle: { color: '#2d2d44' } },
        axisLabel: { color: '#9ca3af' },
        splitLine: { lineStyle: { color: '#2d2d44', type: 'dashed' } },
      },
      // Stage 범례
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'middle',
        textStyle: { color: '#9ca3af', fontSize: 11 },
        data: [
          { name: 'S1 (축적)', icon: 'circle', itemStyle: { color: STAGE_COLORS[1] } },
          { name: 'S2 (상승)', icon: 'circle', itemStyle: { color: STAGE_COLORS[2] } },
          { name: 'S3 (분산)', icon: 'circle', itemStyle: { color: STAGE_COLORS[3] } },
          { name: 'S4 (하락)', icon: 'circle', itemStyle: { color: STAGE_COLORS[4] } },
          { name: '미분류', icon: 'circle', itemStyle: { color: DEFAULT_COLOR } },
        ],
      },
      series: [
        {
          type: 'scatter',
          data,
          symbolSize: (val: number[]) => val[2],
          // 참조선: X=0 수직, Y=50 수평
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: '#6b7280', type: 'dashed', width: 1 },
            data: [
              { xAxis: 0 },
              { yAxis: 50 },
            ],
            label: { show: false },
          },
          emphasis: {
            itemStyle: { shadowBlur: 10, shadowColor: 'rgba(255,255,255,0.3)' },
          },
        },
      ],
      tooltip: {
        trigger: 'item',
        backgroundColor: '#16213e',
        borderColor: '#2d2d44',
        textStyle: { color: '#e5e7eb', fontSize: 12 },
        formatter: (params: { data: { value: number[] } }) => {
          const d = params.data.value
          const name = d[4] as unknown as string
          const priceChange = (d[0] as number).toFixed(2)
          const rs = (d[1] as number).toFixed(1)
          const stage = d[3] as number
          const stageDetail = d[6] as unknown as string
          const tv = formatTradingValue(d[5] as number)
          const sign = (d[0] as number) >= 0 ? '+' : ''
          const stageLabel = stage ? `S${stage}${stageDetail ? ` (${stageDetail})` : ''}` : '미분류'
          return [
            `<b>${name}</b>`,
            `가격변동: ${sign}${priceChange}%`,
            `RS Rating: ${rs}`,
            `Stage: ${stageLabel}`,
            `거래대금: ${tv}`,
          ].join('<br/>')
        },
      },
    }
  }, [stocks, sectorName])

  const handleEvents = {
    click: (params: { data: { value: number[] } }) => {
      if (params?.data?.value) {
        const stockName = params.data.value[4] as unknown as string
        if (stockName && onStockClick) onStockClick(stockName)
      }
    },
  }

  return (
    <div className="bubble-chart-wrapper">
      <ReactECharts
        option={option}
        style={{ height: '500px', width: '100%' }}
        onEvents={handleEvents}
        opts={{ renderer: 'svg' }}
      />
    </div>
  )
}
