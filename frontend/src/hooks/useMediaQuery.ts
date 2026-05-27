// SPEC-SECTOR-MINOR-COLOR-001: 모바일/데스크탑 뷰포트 분기를 위한 미디어 쿼리 hook
// @MX:NOTE: [AUTO] window.matchMedia 기반 반응형 hook. SSR 안전. addEventListener cleanup 포함.
// @MX:SPEC: SPEC-SECTOR-MINOR-COLOR-001

import { useEffect, useState } from 'react'

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState<boolean>(() => {
    // SSR 환경에서 window가 없으면 false 반환
    if (typeof window === 'undefined') return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    // SSR 환경 가드
    if (typeof window === 'undefined') return

    const mq = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)

    mq.addEventListener('change', handler)

    // cleanup: 리스너 제거
    return () => mq.removeEventListener('change', handler)
  }, [query])

  return matches
}
