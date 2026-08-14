import { useEffect, useState } from 'react'
import type { RefObject } from 'react'

// AC-SUX-061 (REQ-SUX-058): 측정한 폭으로부터 열 접기 단계(0..3)를 도출.
// 단일 접기 순서 상수는 stockTableColumns.ts COLLAPSE_ORDER 가 소유 — 여기서는 폭→단계 변환만.
// jsdom 에는 ResizeObserver 가 없으므로 level 0(전체 표시)로 안전 결손 — 테스트는 collapseLevel prop 으로 주입.
export function useCollapseLevel(
  ref: RefObject<HTMLElement | null>,
  // [t1, t2, t3]: w<t3 → 3, w<t2 → 2, w<t1 → 1, 그 외 0.
  thresholds: readonly number[] = [900, 750, 600],
): number {
  const [level, setLevel] = useState(0)

  useEffect(() => {
    if (typeof ResizeObserver === 'undefined') return
    const el = ref.current
    if (!el) return

    const compute = (w: number): void => {
      let lvl = 0
      if (w < thresholds[2]) lvl = 3
      else if (w < thresholds[1]) lvl = 2
      else if (w < thresholds[0]) lvl = 1
      setLevel(lvl)
    }

    const ro = new ResizeObserver((entries) => {
      const entry = entries[0]
      compute(entry?.contentRect.width ?? el.clientWidth)
    })
    ro.observe(el)
    compute(el.clientWidth)
    return () => ro.disconnect()
  }, [ref, thresholds])

  return level
}
