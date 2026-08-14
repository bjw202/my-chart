// 버블 반지름 공용 유틸 — SPEC-SECTOR-UX-001 M5 (REQ-SUX-035/036/037, 규칙 VZ-1/VZ-2/VZ-3)
// 두 버블 차트(섹터·종목)가 동일 로그-면적비례 공식을 공유한다 — 다른 공식을 쓰면 크기 비교가 무의미 (plan §1.2 D7).
// @MX:ANCHOR: [AUTO] VZ-1 버블 크기 매핑 공식 — 로그 정규화 + 면적 비례 반지름. 섹터·종목 두 차트가 공유.
// @MX:REASON: 두 차트가 같은 공식을 써야 동일 기간 내 거래대금→크기 비교가 의미를 갖는다. 공식 분기 시 크기 채널 의미 붕괴 (plan §1.2 D7, 02-screen-flow.md §9.2 VZ-1).
// @MX:SPEC: SPEC-SECTOR-UX-001 (AC-SUX-038/039)

// 차트별 반지름 상수 (02-screen-flow.md §9.2 VZ-1 표). symbolSize(지름) = 2 × r.
export const SECTOR_BUBBLE_R_MIN = 7   // 섹터 버블 — 지름 14
export const SECTOR_BUBBLE_R_MAX = 34  // 섹터 버블 — 지름 68
export const STOCK_BUBBLE_R_MIN = 5    // 종목 버블 — 지름 10
export const STOCK_BUBBLE_R_MAX = 26   // 종목 버블 — 지름 52

export type SizePeriod = '1w' | '1m' | '3m'

// 기간별 고정 눈금 사다리 (O-U4 결정 / 02-screen-flow.md §9.2 VZ-2 확정표).
// vMin/vMax 는 데이터가 아니라 해당 기간 사다리의 최소·최대 상수다 (VZ-1 로그 정규화 입력).
// refs 는 크기 범례 3개 참조 버블의 실제 값이다 — 데이터 분포가 바뀌어도 움직이지 않는다.
export interface SizeLadder {
  vMin: number
  vMax: number
  refs: readonly [number, number, number] // 최소 / 중간 / 최대 (범례 참조값)
  /** 범례 라벨에 병기할 기간 표기 (크기 = 거래대금 {periodLabel} ...) */
  periodLabel: string
}

export const PERIOD_SIZE_LADDER: Readonly<Record<SizePeriod, SizeLadder>> = {
  // 억 = 1e8, 조 = 1e12
  '1w': { vMin: 1e10, vMax: 1e12, refs: [1e10, 1e11, 1e12], periodLabel: '1W' }, // 100억 / 1,000억 / 1조
  '1m': { vMin: 5e10, vMax: 5e12, refs: [5e10, 5e11, 5e12], periodLabel: '1M' }, // 500억 / 5,000억 / 5조
  '3m': { vMin: 1e11, vMax: 1e13, refs: [1e11, 1e12, 1e13], periodLabel: '3M' }, // 1,000억 / 1조 / 10조
}

/**
 * 버블 반지름 (로그 정규화 + 면적 비례). plan §3.2 / 02-screen-flow.md §9.2 VZ-1 공식.
 *
 *   u = (ln(v+1) − ln(vMin+1)) / (ln(vMax+1) − ln(vMin+1))   // u ∈ [0,1]
 *   vMax === vMin 이면 u = 0.5 (모든 버블 동일 중간 크기)
 *   r = sqrt(rMin² + u × (rMax² − rMin²))                   // 면적이 u 에 선형 비례
 *
 * 호출자는 symbolSize(지름) = 2 × bubbleRadius(...) 로 변환한다.
 * 값이 사다리 밖이면 호출자가 미리 [vMin, vMax] 로 클램프해야 한다 (bubbleSymbolSize 참조).
 */
export function bubbleRadius(
  v: number,
  vMin: number,
  vMax: number,
  rMin: number,
  rMax: number,
): number {
  const lo = Math.log(vMin + 1)
  const hi = Math.log(vMax + 1)
  const u = hi === lo ? 0.5 : (Math.log(v + 1) - lo) / (hi - lo)
  return Math.sqrt(rMin * rMin + u * (rMax * rMax - rMin * rMin))
}

/**
 * symbolSize(지름) 계산 — 클램프 포함. 결측(null) → 최소 지름(2 × rMin).
 * 사다리 밖 값은 vMin/vMax 로 클램프하지만, 툴팁에는 실제 값을 표기해야 한다 (AC-SUX-039 클램프 항).
 */
export function bubbleSymbolSize(
  v: number | null,
  vMin: number,
  vMax: number,
  rMin: number,
  rMax: number,
): number {
  if (v == null || Number.isNaN(v)) return 2 * rMin
  const clamped = Math.max(vMin, Math.min(vMax, v))
  return 2 * bubbleRadius(clamped, vMin, vMax, rMin, rMax)
}

/**
 * 크기 범례 참조 버블 데이터 (VZ-2). [값, 지름] 쌍 3개 + 기간 라벨.
 * 범례 컴포넌트가 이 값을 그대로 렌더한다 — 프론트가 값을 계산하지 않는다.
 */
export function sizeLegendRefs(
  period: SizePeriod,
  rMin: number,
  rMax: number,
): { value: number; diameter: number }[] {
  const { vMin, vMax, refs } = PERIOD_SIZE_LADDER[period]
  return refs.map(value => ({
    value,
    diameter: 2 * bubbleRadius(value, vMin, vMax, rMin, rMax),
  }))
}

/** 거래대금(원) → 억원 표기 (1e8 원 = 1 억). 범례·툴팁 공용. */
export function formatTradingValueEok(value: number): string {
  const eok = value / 100_000_000
  if (eok >= 10000) {
    // 1조 이상 — 조 단위 병기
    const jo = value / 1e12
    return `${jo.toLocaleString('ko-KR', { maximumFractionDigits: jo >= 100 ? 0 : 1 })}조`
  }
  return `${eok.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}억`
}
