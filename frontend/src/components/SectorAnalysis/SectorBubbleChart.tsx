// 섹터 버블 차트 컴포넌트 - ECharts scatter를 이용한 섹터별 버블 시각화
// X축: 초과수익률, Y축: RS 평균, 버블 크기: 거래대금, 색상: 기간 수익률
import { useMemo } from 'react'
import type { ReactElement } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { SectorBubbleItem } from '../../types/bubble'

interface Props {
  sectors: SectorBubbleItem[]
  onSectorClick: (sectorName: string) => void
}

// 거래대금을 버블 픽셀 크기(20~80)로 정규화
function normalizeBubbleSize(value: number, min: number, max: number): number {
  if (max === min) return 40
  return 20 + ((value - min) / (max - min)) * 60
}

// 거래대금을 억원 단위로 포맷
function formatTradingValue(value: number): string {
  const eok = value / 100_000_000
  return `${eok.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}억원`
}

export function SectorBubbleChart({ sectors, onSectorClick }: Props): ReactElement {
  const option = useMemo((): EChartsOption => {
    if (!sectors.length) {
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

    const tradingValues = sectors.map(s => s.trading_value)
    const minTV = Math.min(...tradingValues)
    const maxTV = Math.max(...tradingValues)

    // ECharts scatter 데이터: [x, y, bubbleSize, periodReturn, sectorName, tradingValue, rsAvg]
    const data = sectors.map(s => [
      s.excess_return,
      s.rs_avg,
      normalizeBubbleSize(s.trading_value, minTV, maxTV),
      s.period_return,
      s.name,
      s.trading_value,
      s.rs_avg,
    ])

    return {
      backgroundColor: '#1a1a2e',
      grid: { left: 60, right: 40, top: 40, bottom: 60 },
      xAxis: {
        type: 'value',
        name: 'KOSPI 대비 초과수익률 %',
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
        // 참조선: X=0 수직선
        axisPointer: { show: true, lineStyle: { color: '#4b5563', type: 'dashed' } },
      },
      yAxis: {
        type: 'value',
        name: 'RS 평균 (0-100)',
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
      // period_return 기준 색상 매핑
      visualMap: {
        show: false,
        dimension: 3,
        pieces: [
          { lt: -3, color: '#DC2626' },       // 강한 음수: red-600
          { gte: -3, lt: -1, color: '#F87171' }, // 약한 음수: red-400
          { gte: -1, lt: 1, color: '#9CA3AF' },  // 중립: gray-400
          { gte: 1, lt: 3, color: '#4ADE80' },   // 약한 양수: green-400
          { gte: 3, color: '#16A34A' },           // 강한 양수: green-600
        ],
      },
      series: [
        {
          type: 'scatter',
          data,
          symbolSize: (val: number[]) => val[2],
          label: {
            show: true,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter: (params: any) => params.data[4] as string,
            position: 'inside',
            fontSize: 10,
            color: '#e5e7eb',
            overflow: 'break',
          },
          // X=0 참조 수직선, Y=50 참조 수평선
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
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        formatter: (params: any) => {
          const d = params.data
          const name = d[4] as string
          const excessReturn = Number(d[0]).toFixed(2)
          const rsAvg = Number(d[1]).toFixed(1)
          const periodReturn = Number(d[3]).toFixed(2)
          const tv = formatTradingValue(Number(d[5]))
          const sign = Number(d[3]) >= 0 ? '+' : ''
          return [
            `<b>${name}</b>`,
            `초과수익률: ${excessReturn}%`,
            `RS 평균: ${rsAvg}`,
            `기간수익률: ${sign}${periodReturn}%`,
            `거래대금: ${tv}`,
          ].join('<br/>')
        },
      },
    }
  }, [sectors])

  // 섹터 클릭 핸들러
  const handleEvents = {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    click: (params: any) => {
      if (params?.data) {
        const sectorName = params.data[4] as string
        if (sectorName) onSectorClick(sectorName)
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
