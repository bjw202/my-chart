// 섹터 버블 차트 컴포넌트 - ECharts scatter를 이용한 섹터별 버블 시각화
// X축: 초과수익률, Y축: RS 평균, 버블 크기: 거래대금(로그 고정눈금), 색상: 기간 수익률(발산형 5단계)
// SPEC-SECTOR-UX-001 M5: VZ-1(크기)·VZ-2(범례)·VZ-3(결측 점선)·VZ-4(축 포인터 삭제)·VZ-5(기준선 라벨)·VZ-6(축 범위)·REQ-SUX-056(발산형 색상)
import { useEffect, useMemo, useRef } from 'react'
import type { ReactElement } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { SectorBubbleItem } from '../../types/bubble'
import {
  bubbleSymbolSize,
  sizeLegendRefs,
  formatTradingValueEok,
  PERIOD_SIZE_LADDER,
  SECTOR_BUBBLE_R_MIN,
  SECTOR_BUBBLE_R_MAX,
} from './bubbleRadius'
import type { SizePeriod } from './bubbleRadius'
import { metricText, toMetricValue } from '../common/MetricCell'

// 시장 필터 → 벤치마크 이름 (VZ-10). X=0 초과수익률 = 벤치마크 동일 성과.
// @MX:NOTE: [AUTO] 벤치마크 절대 수익률 값(+1.88% 등)은 backend 가 미전달 — VZ-5 절대값은 debt(AC-SUX-042 섹터 PASS-WITH-DEBT).
const MARKET_BENCHMARK_LABEL: Record<string, string> = {
  all: '전체 상한가중',
  kospi: 'KOSPI',
  kosdaq: 'KOSDAQ',
}

// REQ-SUX-056: 기간 수익률 발산형 5단계 — 기준점 0%(벤치마크 아님). 경계값 단일 위치 상수.
// @MX:ANCHOR: [AUTO] 섹터 버블 발산형 색상 경계 — 0% 중립. X축(초과수익률)과 독립 (VZ-0 채널 중복 금지).
// @MX:REASON: 색 = 기간수익률(절대 부호), X = 초과수익률(벤치마크 대비) — 두 축이 다른 변수. 경계/팔레트 변경 시 범례 텍스트와 동기 필수.
interface DivergingBand { label: string; color: string; test?: (v: number) => boolean }
const SECTOR_RETURN_BANDS: readonly DivergingBand[] = [
  { label: '≤−10%', color: '#1565C0', test: (v) => v <= -10 },       // 강한 음수 — blue-800
  { label: '−10% ~ −3%', color: '#64B5F6', test: (v) => v > -10 && v <= -3 }, // 약한 음수 — blue-300
  { label: '−3% ~ +3%', color: '#9CA3AF', test: (v) => v > -3 && v < 3 },     // 중립(0% 포함) — gray-400
  { label: '+3% ~ +10%', color: '#EF9A9A', test: (v) => v >= 3 && v < 10 },   // 약한 양수 — red-200
  { label: '≥+10%', color: '#C62828', test: (v) => v >= 10 },                 // 강한 양수 — red-800
]
export function sectorReturnColor(periodReturn: number): string {
  for (const b of SECTOR_RETURN_BANDS) {
    if (b.test!(periodReturn)) return b.color
  }
  return SECTOR_RETURN_BANDS[2].color // fallback 중립
}

interface Props {
  sectors: SectorBubbleItem[]
  onSectorClick: (sectorName: string) => void
  period: SizePeriod
  /** 시장 필터 — 벤치마크 이름 표기 (VZ-5/VZ-10). 기본 'all'. */
  market?: string | null
}

// 크기 범례 (VZ-2) — 3개 참조 버블 + 실제 값 텍스트 + 기간 병기.
function SizeLegend({ period }: { period: SizePeriod }): ReactElement {
  const refs = sizeLegendRefs(period, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX)
  const { periodLabel } = PERIOD_SIZE_LADDER[period]
  return (
    <div className="bubble-size-legend" data-testid="sector-size-legend">
      <span className="bubble-size-legend-title">크기 = 거래대금 {periodLabel} (로그·고정 눈금)</span>
      <span className="bubble-size-legend-items">
        {refs.map((r, i) => (
          <span className="bubble-size-legend-item" key={i}>
            <span
              className="bubble-size-legend-bubble"
              style={{ width: r.diameter, height: r.diameter }}
              aria-hidden
            />
            <span className="bubble-size-legend-value">{formatTradingValueEok(r.value)}</span>
          </span>
        ))}
      </span>
    </div>
  )
}

// 색상 범례 (REQ-SUX-056) — 발산형 5단계 실제 구간 값.
function ColorLegend(): ReactElement {
  return (
    <div className="bubble-color-legend" data-testid="sector-color-legend">
      <span className="bubble-color-legend-title">색상 = 기간 수익률 (발산형, 기준 0%)</span>
      <span className="bubble-color-legend-items">
        {SECTOR_RETURN_BANDS.map((b) => (
          <span className="bubble-color-legend-item" key={b.label}>
            <span className="bubble-color-legend-swatch" style={{ backgroundColor: b.color }} aria-hidden />
            <span className="bubble-color-legend-label">{b.label}</span>
          </span>
        ))}
      </span>
    </div>
  )
}

export function SectorBubbleChart({ sectors, onSectorClick, period, market = 'all' }: Props): ReactElement {
  const ladder = PERIOD_SIZE_LADDER[period]
  const benchmarkLabel = MARKET_BENCHMARK_LABEL[market ?? 'all'] ?? '전체 상한가중'

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

    // ECharts scatter 데이터: [x(초과수익률), y(RS), bubbleSize, periodReturn, name, tradingValue, rsAvg, isMissingTV]
    const data = sectors.map(s => {
      const missing = s.trading_value == null || Number.isNaN(s.trading_value)
      const size = bubbleSymbolSize(
        missing ? null : s.trading_value,
        ladder.vMin, ladder.vMax, SECTOR_BUBBLE_R_MIN, SECTOR_BUBBLE_R_MAX,
      )
      // REQ-SUX-056 색상(발산형) + REQ-SUX-057 테두리(결측=점선) 동시 인코딩.
      // borderType 리터럴 고정 — ECharts itemStyle 타입 부합 + Record<string,unknown> 로 series 대입 단순화.
      const itemStyle: Record<string, unknown> = { color: sectorReturnColor(s.period_return) }
      if (missing) {
        itemStyle.borderColor = '#9CA3AF'
        itemStyle.borderWidth = 1.5
        itemStyle.borderType = 'dashed'
      }
      return {
        value: [s.excess_return, s.rs_avg, size, s.period_return, s.name, s.trading_value, s.rs_avg, missing ? 1 : 0],
        itemStyle,
      }
    })

    return {
      backgroundColor: '#1a1a2e',
      // top: 48 — 최대 버블 반지름(34)의 상단 돌출이 toolbox 밴드(10~30px)를 과도히 침범하지 않게 하는 여백
      grid: { left: 60, right: 40, top: 48, bottom: 60 },
      xAxis: {
        type: 'value',
        name: `${benchmarkLabel} 대비 초과수익률 %`,
        nameLocation: 'middle',
        nameGap: 35,
        nameTextStyle: { color: '#9ca3af', fontSize: 12 },
        // VZ-6: 0(기준선)을 항상 포함. 데이터가 전부 양수여도 min <= 0.
        min: (v: { min: number }) => Math.min(0, v.min),
        axisLine: { lineStyle: { color: '#2d2d44' } },
        axisTick: { lineStyle: { color: '#2d2d44' } },
        axisLabel: {
          color: '#9ca3af',
          formatter: (v: number) => `${v > 0 ? '+' : ''}${v.toFixed(1)}%`,
        },
        splitLine: { lineStyle: { color: '#2d2d44', type: 'dashed' } },
        // @MX:NOTE: [AUTO] VZ-4 — 축 포인터(커서 추종 값 상자) 삭제됨. 참조선은 markLine 이 담당. 재도입 금지.
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
      // SPEC-BUBBLE-ZOOM-001 REQ-BZ-001/002: X축 전용 dataZoom — 휠 줌 + 드래그 팬 (StockBubbleChart와 동일 계약).
      // yAxisIndex 키 생략이 X축만 제어하는 관용구다(감사 D1). filterMode 'none': 줌 창 밖 버블도 클리핑 표시.
      dataZoom: [{
        type: 'inside',
        xAxisIndex: 0,
        zoomOnMouseWheel: true,
        moveOnMouseMove: true,
        moveOnMouseWheel: false,
        filterMode: 'none',
        minSpan: 20,   // 퍼센트 단위(0~100) — 최소 창 20% (REQ-BZ-001c). 분율 0.2가 아님에 주의
        maxSpan: 100,  // 최대 창 100% = 전체 범위
      }],
      // SPEC-BUBBLE-ZOOM-001 REQ-BZ-007: 영역 선택 줌 (툴박스 내장, StockBubbleChart와 동일 계약).
      // 박스의 가로 범위만 X축 창에 적용 (yAxisIndex: false = Y축 제어 비활성) — Y는 RS 평균 0-100 고정.
      toolbox: {
        right: 10,
        top: 10,
        iconStyle: { borderColor: '#9ca3af' },
        feature: {
          dataZoom: {
            xAxisIndex: [0],
            yAxisIndex: false,
            filterMode: 'none',
          },
          restore: {},
        },
      },
      series: [
        {
          type: 'scatter' as const,
          data,
          symbolSize: (val: number[]) => val[2],
          // REQ-SUX-056: 색상 = 기간 수익률 발산형 (itemStyle.color per-data).
          label: {
            show: true,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            formatter: (params: any) => params.data.value[4] as string,
            position: 'inside',
            fontSize: 10,
            color: '#e5e7eb',
            overflow: 'break',
          },
          // VZ-5: X=0 기준선(벤치마크) 라벨 + Y=50(RS 중앙).
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              { xAxis: 0, label: { show: true, formatter: `${benchmarkLabel} (초과수익률 0 = 벤치마크)`, color: '#9ca3af', fontSize: 10, position: 'insideEndTop' } },
              { yAxis: 50, label: { show: true, formatter: 'RS 중앙', color: '#9ca3af', fontSize: 10, position: 'insideEndTop' } },
            ],
            lineStyle: { color: '#6b7280', type: 'dashed', width: 1 },
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
          const d = params.data.value as (string | number)[]
          const missing = d[7] === 1
          const name = d[4] as unknown as string
          // D2: 결측·저신뢰 표기는 표 셀(MetricCell)과 같은 metricText 로 생성한다.
          // 값이 있을 때의 포맷은 종전과 동일하다 — 바뀐 것은 결측 경로뿐이다.
          const excessReturn = metricText(toMetricValue(d[0]), n => `${n.toFixed(2)}%`)
          const rsAvg = metricText(toMetricValue(d[1]), n => n.toFixed(1))
          const periodReturn = metricText(toMetricValue(d[3]), n => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`)
          const tvLine = missing
            ? '거래대금: 데이터 없음'
            : `거래대금: ${formatTradingValueEok(Number(d[5]))}`
          return [
            `<b>${name}</b>`,
            `초과수익률: ${excessReturn}`,
            `RS 평균: ${rsAvg}`,
            `기간수익률: ${periodReturn}`,
            tvLine,
          ].join('<br/>')
        },
      },
    }
  }, [sectors, ladder, benchmarkLabel])

  // SPEC-BUBBLE-ZOOM-001 REQ-BZ-003: 빈 공간 더블클릭 → X축 전체 범위 복원 (StockBubbleChart와 동일 계약).
  // REQ-BZ-003d: e.target 부재(빈 공간)에서만 동작 — 버블 위 더블클릭은 기존 click(onSectorClick) 유지.
  const chartRef = useRef<ReactECharts | null>(null)
  useEffect(() => {
    const chart = chartRef.current?.getEchartsInstance()
    if (!chart) return
    const zr = chart.getZr()
    const handleDblClick = (e: { target?: unknown }) => {
      if (e.target) return // 그래픽 요소(버블 등) 위 → 리셋하지 않음
      chart.dispatchAction({ type: 'dataZoom', start: 0, end: 100 })
    }
    zr.on('dblclick', handleDblClick)
    return () => {
      zr.off('dblclick', handleDblClick)
    }
  }, [])

  // 섹터 클릭 핸들러
  const handleEvents = {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    click: (params: any) => {
      if (params?.data?.value) {
        const sectorName = params.data.value[4] as string
        if (sectorName) onSectorClick(sectorName)
      }
    },
  }

  return (
    <div className="bubble-chart-wrapper">
      <ColorLegend />
      {/* notMerge 필수 — 사유는 StockBubbleChart 의 @MX:NOTE 참조(섹터/모집단 변경 시
          series 인덱스 병합으로 이전 데이터가 잔존한다). */}
      <ReactECharts
        ref={chartRef}
        option={option}
        notMerge={true}
        style={{ height: '500px', width: '100%' }}
        onEvents={handleEvents}
        opts={{ renderer: 'svg' }}
      />
      <SizeLegend period={period} />
    </div>
  )
}
