/**
 * useFocusTrap — modal focus trap 훅 (T5a, Q-5 조건부)
 *
 * AnalysisModal / AiReportModal에 focus trap이 없어 신규 작성.
 * WCAG 2.1 AA 준수: Tab 순환 / Shift+Tab 역순환.
 * NFR-A11Y-001
 */

import { useEffect } from 'react'

const FOCUSABLE_SELECTORS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

export function useFocusTrap(containerRef: React.RefObject<HTMLElement | null>): void {
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key !== 'Tab') return

      const focusable = Array.from(
        container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTORS),
      ).filter((el) => !el.closest('[inert]'))

      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement as HTMLElement

      if (e.shiftKey) {
        // Shift+Tab: 첫 요소에서 마지막으로 wrap
        if (active === first || !container.contains(active)) {
          e.preventDefault()
          last.focus()
        }
      } else {
        // Tab: 마지막 요소에서 첫 요소로 wrap
        if (active === last || !container.contains(active)) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [containerRef])
}
