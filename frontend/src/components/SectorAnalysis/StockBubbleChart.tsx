// 종목 버블 차트 컴포넌트 - ECharts scatter를 이용한 종목별 버블 시각화
// X축: 가격변동률, Y축: RS Rating, 버블 크기: 거래대금, 색상: 산업명(중) sector_minor
import { useMemo } from 'react'
import type { ReactElement } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { StockBubbleItem } from '../../types/bubble'
import { useMediaQuery } from '../../hooks/useMediaQuery'

interface Props {
  stocks: StockBubbleItem[]
  sectorName: string
  onStockClick?: (stockName: string) => void
}

// SPEC-SECTOR-MINOR-COLOR-001: 산업명(중) 기반 색상 매핑 — Tableau 10 변형
// @MX:NOTE: [AUTO] 색상 팔레트 10색 고정. 11번째 이후 sector_minor는 ETC_LABEL("기타")로 흡수.
// @MX:SPEC: SPEC-SECTOR-MINOR-COLOR-001

const SECTOR_MINOR_PALETTE = [
  '#4E79A7', '#F28E2B', '#E15759', '#76B7B2', '#59A14F',
  '#EDC948', '#B07AA1', '#FF9DA7', '#9C755F', '#BAB0AC',
] as const

const ETC_COLOR = '#9CA3AF'
const ETC_LABEL = '기타'

// @MX:ANCHOR: [AUTO] 색상 결정성 매핑 — 정렬 키 (count desc, name asc) + "기타" 마지막 + palette 10 overflow → "기타" 흡수. itemStyle.color + legend.data + tooltip 3축이 본 함수의 출력에 의존.
// @MX:REASON: 함수 시그니처/정렬키 변경 시 결정성·범례·색상 일관성·tooltip 산업명(중) 라벨이 동시에 깨질 위험 (triple-dependency 응집)
// @MX:SPEC: SPEC-SECTOR-MINOR-COLOR-001

function buildSectorMinorColorMap(stocks: StockBubbleItem[]): Map<string, string> {
  // 1) sector_minor → count 집계 (null/빈 문자열은 ETC로 흡수)
  const counts = new Map<string, number>()
  for (const s of stocks) {
    const key = s.sector_minor && s.sector_minor.trim() ? s.sector_minor : ETC_LABEL
    counts.set(key, (counts.get(key) ?? 0) + 1)
  }

  // 2) ETC 분리, 나머지 정렬: count desc, name asc
  const etcCount = counts.get(ETC_LABEL) ?? 0
  counts.delete(ETC_LABEL)
  const sorted = Array.from(counts.entries()).sort((a, b) => {
    if (b[1] !== a[1]) return b[1] - a[1]
    return a[0].localeCompare(b[0])
  })

  // 3) 상위 10개만 palette 할당, 11번째 이후는 ETC로 흡수
  const colorMap = new Map<string, string>()
  for (let i = 0; i < sorted.length && i < SECTOR_MINOR_PALETTE.length; i++) {
    colorMap.set(sorted[i][0], SECTOR_MINOR_PALETTE[i])
  }

  // 11번째 이후 + null/빈 모두 ETC
  const overflowExists = sorted.length > SECTOR_MINOR_PALETTE.length
  if (etcCount > 0 || overflowExists) {
    colorMap.set(ETC_LABEL, ETC_COLOR)
  }

  return colorMap
}

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

// HTML 특수문자 이스케이프 헬퍼 (tooltip XSS 방어적 코딩)
function escapeHtml(s: string): string {
  return s.replace(/[<>&"]/g, (c) => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c] ?? c))
}

export function StockBubbleChart({ stocks, sectorName, onStockClick }: Props): ReactElement {
  // 모바일 분기 (max-width: 767px)
  const isMobile = useMediaQuery('(max-width: 767px)')

  // sector_minor 색상 맵 (결정성: stocks 변경 시만 재계산)
  const colorMap = useMemo(() => buildSectorMinorColorMap(stocks), [stocks])

  // sector_minor 그룹별 종목 분류 (colorMap 순서 보존)
  const groupedData = useMemo(() => {
    const groups = new Map<string, Array<{ s: StockBubbleItem; i: number }>>()
    stocks.forEach((s, i) => {
      const key = s.sector_minor && s.sector_minor.trim() ? s.sector_minor : ETC_LABEL
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key)!.push({ s, i })
    })
    return groups
  }, [stocks])

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

    // colorMap 순서(legendData)에 따라 sector_minor 그룹별 series 배열 구성
    // series[i].name === legend.data[i].name 일치 → ECharts 범례 토글·hover emphasis 표준 동작
    const series = Array.from(colorMap.entries()).map(([groupName, color], idx) => {
      const groupItems = groupedData.get(groupName) ?? []
      return {
        name: groupName,
        type: 'scatter' as const,
        data: groupItems.map(({ s, i }) => ({
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
          // tooltip formatter에서 sector_minor 접근을 위한 보존
          sector_minor: s.sector_minor ?? null,
          label: {
            show: topNSet.has(i),
            formatter: s.name,
            position: 'top' as const,
            fontSize: 9,
            color: '#e5e7eb',
          },
        })),
        symbolSize: (val: number[]) => val[2],
        // 그룹 색상을 series 레벨에 설정 (data 레벨에서 제거)
        itemStyle: {
          color,
          opacity: 0.85,
        },
        emphasis: {
          focus: 'series' as const,
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(255,255,255,0.3)' },
        },
        // 참조선: 첫 번째 series에만 (중복 렌더 방지)
        ...(idx === 0 ? {
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: '#6b7280', type: 'dashed' as const, width: 1 },
            data: [{ xAxis: 0 }, { yAxis: 50 }],
            label: { show: false },
          },
        } : {}),
      }
    })

    // legend.data 동적 생성 (colorMap 순서: count desc, "기타" 마지막)
    const legendData = Array.from(colorMap.entries()).map(([name, color]) => ({
      name,
      icon: 'circle',
      itemStyle: { color },
    }))


    return {
      backgroundColor: '#1a1a2e',
      title: {
        text: `${sectorName} 종목 버블`,
        left: 'center',
        top: 8,
        textStyle: { color: '#9ca3af', fontSize: 13, fontWeight: 'normal' },
      },
      // 모바일/데스크탑 grid 분기
      grid: isMobile
        ? { left: 60, right: 60, top: 50, bottom: 80 }
        : { left: 60, right: 120, top: 50, bottom: 60 },
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
      // sector_minor 기반 동적 범례 (모바일/데스크탑 배치 분기)
      legend: isMobile
        ? {
            orient: 'horizontal' as const,
            bottom: 10,
            type: 'scroll' as const,
            textStyle: { color: '#9ca3af', fontSize: 11 },
            data: legendData,
          }
        : {
            orient: 'vertical' as const,
            right: 10,
            top: 'middle',
            textStyle: { color: '#9ca3af', fontSize: 11 },
            data: legendData,
          },
      series,
      tooltip: {
        trigger: 'item',
        backgroundColor: '#16213e',
        borderColor: '#2d2d44',
        textStyle: { color: '#e5e7eb', fontSize: 12 },
        formatter: (params: { data: { value: number[]; sector_minor?: string | null } }) => {
          const d = params.data
          const val = d.value
          const name = escapeHtml(val[4] as unknown as string)
          const priceChange = (val[0] as number).toFixed(2)
          const rs = (val[1] as number).toFixed(1)
          const stage = val[3] as number
          const stageDetail = val[6] as unknown as string
          const tv = formatTradingValue(val[5] as number)
          const sign = (val[0] as number) >= 0 ? '+' : ''
          const stageLabel = stage ? `S${stage}${stageDetail ? ` (${escapeHtml(stageDetail)})` : ''}` : '미분류'
          // sector_minor 라인 (null/빈 문자열은 ETC_LABEL 표시, XSS 방어)
          const sectorMinorLabel = d.sector_minor && d.sector_minor.trim()
            ? escapeHtml(d.sector_minor)
            : ETC_LABEL
          return [
            `<b>${name}</b>`,
            `산업명(중): ${sectorMinorLabel}`,
            `가격변동: ${sign}${priceChange}%`,
            `RS Rating: ${rs}`,
            `Stage: ${stageLabel}`,
            `거래대금: ${tv}`,
          ].join('<br/>')
        },
      },
    }
  }, [stocks, sectorName, isMobile, colorMap, groupedData])

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
