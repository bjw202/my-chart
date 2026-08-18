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
  // 억 = 1e8, 조 = 1e12 — 종목 버블 기준(원 단위 Close×Volume 스케일)
  '1w': { vMin: 1e10, vMax: 1e12, refs: [1e10, 1e11, 1e12], periodLabel: '1W' }, // 100억 / 1,000억 / 1조
  '1m': { vMin: 5e10, vMax: 5e12, refs: [5e10, 5e11, 5e12], periodLabel: '1M' }, // 500억 / 5,000억 / 5조
  '3m': { vMin: 1e11, vMax: 1e13, refs: [1e11, 1e12, 1e13], periodLabel: '3M' }, // 1,000억 / 1조 / 10조
}

// 섹터 전용 사다리 (SPEC-SECTOR-METRIC-UNIFY-001 M5.5 / AC-SMU-018·갭 G-3).
// M4 이후 섹터 버블의 trading_value는 VolumeWon 기간 누적 = 억원 단위
// (실측: close×volume/1e8 — 삼성전자·SK하이닉스·에코프로비엠 ratio 1.00e8 공히).
// 종목 버블(원 단위 Close×Volume)과 단위가 갈려 사다리를 분리한다 —
// frozen fixture 2026-08-11 post-M4 분포(18섹터, all)의 5~95 백분위가 구간 안으로
// 들어오도록 재산출했고, 로그 중간값을 refs 중간 참조로 둔다:
//   1w 분포 [2.2e3, 9.4e5] p5 3.6e3 / p95 1.8e5 → [1e3, 1e6]
//   1m 분포 [4.9e3, 4.0e6] p5 1.1e4 / p95 7.3e5 → [5e3, 5e6]
//   3m 분포 [3.6e4, 1.5e7] p5 4.4e4 / p95 3.2e6 → [1e4, 1e7]
// 종목 버블의 억원 단위 통일은 SPEC-SECTOR-DISPLAY-UNIFY-001 판단 사항으로 이월.
// @MX:SPEC: SPEC-SECTOR-METRIC-UNIFY-001 (REQ-SMU-023)
export const SECTOR_PERIOD_SIZE_LADDER: Readonly<Record<SizePeriod, SizeLadder>> = {
  '1w': { vMin: 1e3, vMax: 1e6, refs: [1e3, 3e4, 1e6], periodLabel: '1W' },
  '1m': { vMin: 5e3, vMax: 5e6, refs: [5e3, 1.5e5, 5e6], periodLabel: '1M' },
  '3m': { vMin: 1e4, vMax: 1e7, refs: [1e4, 3e5, 1e7], periodLabel: '3M' },
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
 * ladder 인자 생략 시 종목 버블용 PERIOD_SIZE_LADDER (기존 호환) —
 * 섹터 버블은 SECTOR_PERIOD_SIZE_LADDER를 명시적으로 전달한다 (M5.5 단위 분리).
 */
export function sizeLegendRefs(
  period: SizePeriod,
  rMin: number,
  rMax: number,
  ladder?: SizeLadder,
): { value: number; diameter: number }[] {
  const { vMin, vMax, refs } = ladder ?? PERIOD_SIZE_LADDER[period]
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
