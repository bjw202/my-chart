// RED: ThemeDetailPanel — D-3 V2 description cohabitation 검증 (SPEC-NAVER-THEME-003 AC-13)
// ThemeDetailPanel.tsx 무수정 전제. 기존 title={stock.inclusion_reason} 패턴이 V2 mock에서도 동작하는지 검증.
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { ThemeDetailPanel } from '../ThemeDetailPanel'

describe('ThemeDetailPanel — V2 description via inclusion_reason title (AC-13, D-3)', () => {
  it('exposes V2 description via inclusion_reason title (D-3 cohabitation)', () => {
    // V2 parser 정책: inclusion_reason ← item.description (parser.py:271)
    // V2 응답에서 inclusion_reason이 V2 mobile description 텍스트로 채워진 mock
    const theme = {
      theme_id: 178,
      theme_name: '전선',
      change_pct: 9.2,
      change_pct_3d: 12.0,
    }

    const stocks = [
      {
        theme_id: 178,
        theme_name: '전선',
        stock_code: '009470',
        stock_name: '삼화전기',
        inclusion_reason: '전선 제조사로 자동차 와이어하네스 등 다각화', // V2 parser가 item.description으로 채움
        price: 12000,
        change: 100,
        change_pct: 0.84,
        volume: 100000,
        trade_value: 1_200_000_000,
        market_cap: 100_000_000_000,
      },
    ]

    const { container } = render(
      <ThemeDetailPanel theme={theme} stocks={stocks} leaders={[]} />
    )

    // 종목 행에 title 속성으로 V2 description이 노출 (기존 inclusion_reason 자리 — D-3)
    // ThemeDetailPanel.tsx line 92: title={stock.inclusion_reason || undefined}
    const stockRow = container.querySelector('tr[title*="전선 제조사로"]')
    expect(stockRow).not.toBeNull()
  })
})
