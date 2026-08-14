// 종목 버블 차트 컴포넌트 - ECharts scatter를 이용한 종목별 버블 시각화
// X축: 가격변동률, Y축: RS Rating, 버블 크기: 거래대금, 색상: 산업명(중) sector_minor
import { useMemo } from 'react'
import type { ReactElement } from 'react'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import type { StockBubbleItem } from '../../types/bubble'
import { useMediaQuery } from '../../hooks/useMediaQuery'
import {
  bubbleSymbolSize,
  PERIOD_SIZE_LADDER,
  STOCK_BUBBLE_R_MIN,
  STOCK_BUBBLE_R_MAX,
} from './bubbleRadius'
import type { SizePeriod } from './bubbleRadius'

interface Props {
  stocks: StockBubbleItem[]
  sectorName: string
  onStockClick?: (stockName: string) => void
  /** 기간 — 버블 크기 고정눈금 사다리 선택 (O-U4). */
  period?: SizePeriod
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

// REQ-SUX-045 (VZ-0): Stage 테두리 채널 — 색상(산업명(중))과 독립. 종목 버블 테두리는 Stage 전용.
// 결측 거래대금은 테두리를 건드리지 않는다 (REQ-SUX-057 — stage===null 점선과 구분 불가 방지).
// @MX:NOTE: [AUTO] Stage→테두리 매핑. Stage2=흰2px실선 / 1·3=없음 / 4=어두운회색1px / null=회색1px점선.
function stageBorderStyle(stage: number | null): { borderColor: string; borderWidth: number; borderType: 'solid' | 'dashed' } {
  if (stage === 2) return { borderColor: '#ffffff', borderWidth: 2, borderType: 'solid' }
  if (stage === 4) return { borderColor: '#4b5563', borderWidth: 1, borderType: 'solid' }
  if (stage === 1 || stage === 3) return { borderColor: 'transparent', borderWidth: 0, borderType: 'solid' }
  return { borderColor: '#9CA3AF', borderWidth: 1, borderType: 'dashed' } // 분류불가(null)
}

// 섹터 집계 수익률 — 시가총액 가중 평균 (VZ-5 종목 기준선). backend 필드 없어 client 연산.
function sectorAggregateReturn(stocks: StockBubbleItem[]): number | null {
  let weighted = 0
  let totalCap = 0
  for (const s of stocks) {
    if (s.market_cap > 0 && Number.isFinite(s.price_change)) {
      weighted += s.price_change * s.market_cap
      totalCap += s.market_cap
    }
  }
  return totalCap > 0 ? weighted / totalCap : null
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

export function StockBubbleChart({ stocks, sectorName, onStockClick, period = '1w' }: Props): ReactElement {
  // 모바일 분기 (max-width: 767px)
  const isMobile = useMediaQuery('(max-width: 767px)')
  // O-U4: 기간별 고정눈금 사다리 (데이터 기반 X). 종목 버블 크기 [10,52].
  const ladder = PERIOD_SIZE_LADDER[period]

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

    // 거래대금 상위 20개 종목만 라벨 표시
    const topNSet = getTopNByTradingValue(stocks, 20)
    // VZ-5 종목: X 기준선 = 섹터 집계 수익률 (시가총액 가중). 0 선은 보조(더 연한 색).
    const sectorAgg = sectorAggregateReturn(stocks)

    // colorMap 순서(legendData)에 따라 sector_minor 그룹별 series 배열 구성
    // series[i].name === legend.data[i].name 일치 → ECharts 범례 토글·hover emphasis 표준 동작
    const series = Array.from(colorMap.entries()).map(([groupName, color], idx) => {
      const groupItems = groupedData.get(groupName) ?? []
      return {
        name: groupName,
        type: 'scatter' as const,
        data: groupItems.map(({ s, i }) => {
          const tvMissing = s.trading_value == null || Number.isNaN(s.trading_value)
          return {
            value: [
              s.price_change,
              s.rs_12m,
              // VZ-1: bubbleSymbolSize (로그 면적비례, 기간별 고정눈금 클램프). 결측 → 2×rMin.
              bubbleSymbolSize(
                tvMissing ? null : s.trading_value,
                ladder.vMin, ladder.vMax, STOCK_BUBBLE_R_MIN, STOCK_BUBBLE_R_MAX,
              ),
              s.stage ?? 0,
              s.name,
              s.trading_value,
              s.stage_detail ?? '',
              i, // 인덱스 (라벨 표시 여부 판단용)
              tvMissing ? 1 : 0, // 결측 거래대금 플래그 (툴팁용)
            ],
            // REQ-SUX-045 (VZ-0): Stage 테두리 — 색상(series.itemStyle.color)과 독립.
            // 결측 거래대금은 테두리를 건드리지 않는다 (REQ-SUX-057).
            itemStyle: stageBorderStyle(s.stage),
            // tooltip formatter에서 sector_minor, product 접근을 위한 보존
            sector_minor: s.sector_minor ?? null,
            product: s.product ?? null,  // SPEC-STOCK-TOOLTIP-PRODUCT-001
            label: {
              show: topNSet.has(i),
              formatter: s.name,
              position: 'top' as const,
              fontSize: 9,
              color: '#e5e7eb',
            },
          }
        }),
        symbolSize: (val: number[]) => val[2],
        // 그룹 색상을 series 레벨에 설정 (data 레벨에서 제거)
        itemStyle: {
          color,
          opacity: 0.85,
        },
        emphasis: {
          // VZ-13: 개별 버블 hover 시 해당 버블만 강조 (다른 series 블러 없음).
          focus: 'none' as const,
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(255,255,255,0.3)' },
        },
        // 참조선: 첫 번째 series에만 (중복 렌더 방지)
        ...(idx === 0 ? {
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              // VZ-5 종목: X 기준선 = 섹터 집계 수익률 (강조) — 있을 때만.
              ...(sectorAgg != null ? [{
                xAxis: sectorAgg,
                lineStyle: { color: '#e5e7eb', type: 'solid' as const, width: 1.5 },
                label: { show: true, formatter: `${sectorName} 섹터 평균 ${sectorAgg >= 0 ? '+' : ''}${sectorAgg.toFixed(2)}%`, color: '#e5e7eb', fontSize: 10, position: 'insideEndTop' as const },
              }] : []),
              // 0선은 보조로 남기되 더 연한 색 (VZ-5).
              { xAxis: 0, lineStyle: { color: '#3a3a4e', type: 'dashed' as const, width: 1 }, label: { show: false } },
              { yAxis: 50, lineStyle: { color: '#6b7280', type: 'dashed' as const, width: 1 }, label: { show: false } },
            ],
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

    // VZ-12 (AC-SUX-050): "기타" 범례 항목에 구성 산업 개수 병기.
    // legend.data[].name 은 '기타' 그대로(series.name 연동 보존) — formatter 로 표시 텍스트만 변환.
    const etcConstituentCount = (() => {
      const distinct = new Set<string>()
      let nullExists = false
      for (const s of stocks) {
        if (s.sector_minor && s.sector_minor.trim()) distinct.add(s.sector_minor)
        else nullExists = true
      }
      const overflow = Math.max(0, distinct.size - SECTOR_MINOR_PALETTE.length)
      return overflow + (nullExists ? 1 : 0)
    })()
    const hasEtc = colorMap.has(ETC_LABEL)
    const legendFormatter = (name: string): string => {
      if (name === ETC_LABEL && hasEtc && etcConstituentCount >= 1) {
        return `${ETC_LABEL} (${etcConstituentCount}개 산업)`
      }
      return name
    }


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
            formatter: legendFormatter,
            data: legendData,
          }
        : {
            orient: 'vertical' as const,
            right: 10,
            top: 'middle',
            textStyle: { color: '#9ca3af', fontSize: 11 },
            formatter: legendFormatter,
            data: legendData,
          },
      series,
      tooltip: {
        trigger: 'item',
        backgroundColor: '#16213e',
        borderColor: '#2d2d44',
        textStyle: { color: '#e5e7eb', fontSize: 12 },
        // @MX:NOTE: [AUTO] tooltip에 주요제품 라인 추가. escapeHtml 적용 (XSS hardening).
        // @MX:SPEC: SPEC-STOCK-TOOLTIP-PRODUCT-001
        formatter: (params: { data: { value: number[]; sector_minor?: string | null; product?: string | null } }) => {
          const d = params.data
          const val = d.value
          const name = escapeHtml(val[4] as unknown as string)
          const priceChange = (val[0] as number).toFixed(2)
          const rs = (val[1] as number).toFixed(1)
          const stage = val[3] as number
          const stageDetail = val[6] as unknown as string
          const tvMissing = val[8] === 1
          const tv = tvMissing ? '데이터 없음' : formatTradingValue(val[5] as number)
          const sign = (val[0] as number) >= 0 ? '+' : ''
          const stageLabel = stage ? `S${stage}${stageDetail ? ` (${escapeHtml(stageDetail)})` : ''}` : '미분류'
          // sector_minor 라인 (null/빈 문자열은 ETC_LABEL 표시, XSS 방어)
          const sectorMinorLabel = d.sector_minor && d.sector_minor.trim()
            ? escapeHtml(d.sector_minor)
            : ETC_LABEL
          // 주요제품 라인 (null/빈 문자열은 em-dash 표시, XSS 방어)
          const productLabel = d.product && d.product.trim() ? escapeHtml(d.product) : '—'
          return [
            `<b>${name}</b>`,
            `산업명(중): ${sectorMinorLabel}`,
            `주요제품: ${productLabel}`,
            `가격변동: ${sign}${priceChange}%`,
            `RS Rating: ${rs}`,
            `Stage: ${stageLabel}`,
            `거래대금: ${tv}`,
          ].join('<br/>')
        },
      },
    }
  }, [stocks, sectorName, isMobile, colorMap, groupedData, ladder])

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
