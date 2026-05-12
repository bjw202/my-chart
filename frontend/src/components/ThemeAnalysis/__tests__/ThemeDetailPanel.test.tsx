// SPEC-NAVER-THEME-003 ThemeDetailPanel vitest
// AC-13: V2 description via inclusion_reason title (D-3 cohabitation, hover tooltip 보존)
// AC-16: theme_description 본문 노출 (REQ-NT3-009, v1.0.1 amendment + v1.0.2 강화)
// AC-17: stock inclusion_reason 본문 노출 (REQ-NT3-010, v1.0.1 amendment)
// AC-18: 주도주 섹션 미렌더링 (REQ-NT3-011, v1.0.2 amendment — leader card 제거)
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ThemeDetailPanel } from '../ThemeDetailPanel'

const baseStock = {
  theme_id: 178,
  theme_name: '전선',
  price: 12000,
  change: 100,
  change_pct: 0.84,
  volume: 100000,
  trade_value: 1_200_000_000,
  market_cap: 100_000_000_000,
}

describe('ThemeDetailPanel — V2 description via inclusion_reason title (AC-13, D-3)', () => {
  it('exposes V2 description via inclusion_reason title (D-3 cohabitation, hover tooltip 보존)', () => {
    const theme = {
      theme_id: 178,
      theme_name: '전선',
      change_pct: 9.2,
      change_pct_3d: 12.0,
    }
    const stocks = [
      {
        ...baseStock,
        stock_code: '009470',
        stock_name: '삼화전기',
        inclusion_reason: '전선 제조사로 자동차 와이어하네스 등 다각화',
      },
    ]

    const { container } = render(
      <ThemeDetailPanel theme={theme} stocks={stocks} leaders={[]} />
    )

    const stockRow = container.querySelector('tr[title*="전선 제조사로"]')
    expect(stockRow).not.toBeNull()
  })
})

describe('ThemeDetailPanel — theme_description 본문 노출 (AC-16, REQ-NT3-009 v1.0.1+v1.0.2)', () => {
  it('renders theme_description as prominent body text when present', () => {
    const theme = {
      theme_id: 178,
      theme_name: '전선',
      change_pct: 9.2,
      change_pct_3d: 12.0,
      theme_description: '각종 전선 및 전람(電纜)제조 판매업체. AI 인프라 수요 급증.',
    }

    const { container } = render(
      <ThemeDetailPanel theme={theme} stocks={[]} leaders={[]} />
    )

    const descBody = container.querySelector('[data-testid="theme-description-body"]')
    expect(descBody).not.toBeNull()
    expect(descBody?.textContent).toContain('각종 전선')
  })

  it('omits theme_description body when null/undefined/empty (D-4 보존)', () => {
    const cases = [
      { theme_id: 1, theme_name: 'NullDesc', change_pct: 0, change_pct_3d: 0, theme_description: null },
      { theme_id: 2, theme_name: 'NoDesc', change_pct: 0, change_pct_3d: 0 },
      { theme_id: 3, theme_name: 'EmptyDesc', change_pct: 0, change_pct_3d: 0, theme_description: '' },
    ]
    cases.forEach(theme => {
      const { container } = render(
        <ThemeDetailPanel theme={theme} stocks={[]} leaders={[]} />
      )
      const descBody = container.querySelector('[data-testid="theme-description-body"]')
      expect(descBody).toBeNull()
    })
  })
})

describe('ThemeDetailPanel — stock inclusion_reason 본문 노출 (AC-17, REQ-NT3-010 v1.0.1)', () => {
  it('renders inclusion_reason as body text in stock table row', () => {
    const theme = {
      theme_id: 178,
      theme_name: '전선',
      change_pct: 9.2,
      change_pct_3d: 12.0,
    }
    const stocks = [
      {
        ...baseStock,
        stock_code: '009470',
        stock_name: '삼화전기',
        inclusion_reason: '전선 제조사로 자동차 와이어하네스 등 다각화',
      },
    ]

    const { container } = render(
      <ThemeDetailPanel theme={theme} stocks={stocks} leaders={[]} />
    )

    const reasonBody = container.querySelector('[data-testid="stock-inclusion-reason-body"]')
    expect(reasonBody).not.toBeNull()
    expect(reasonBody?.textContent).toContain('와이어하네스')
  })

  it('omits inclusion_reason body when stock has empty inclusion_reason', () => {
    const theme = {
      theme_id: 178,
      theme_name: '전선',
      change_pct: 0,
      change_pct_3d: 0,
    }
    const stocks = [
      {
        ...baseStock,
        stock_code: '000000',
        stock_name: 'NoReason',
        inclusion_reason: '',
      },
    ]

    const { container } = render(
      <ThemeDetailPanel theme={theme} stocks={stocks} leaders={[]} />
    )

    const reasonBody = container.querySelector('[data-testid="stock-inclusion-reason-body"]')
    expect(reasonBody).toBeNull()
  })
})

describe('ThemeDetailPanel — 주도주 섹션 미렌더링 (AC-18, REQ-NT3-011 v1.0.2 amendment)', () => {
  it('does NOT render leader card section even when leaders prop is provided', () => {
    const theme = {
      theme_id: 557,
      theme_name: '유리 기판',
      change_pct: 13.58,
      change_pct_3d: 13.58,
    }
    const leaders = [
      {
        ...baseStock,
        theme_id: 557,
        theme_name: '유리 기판',
        stock_code: '011790',
        stock_name: 'SKC',
        inclusion_reason: "美 반도체 소재 자회사 SK앱솔릭스, 글라스 기판을 게임 체인저로",
        rank: 1,
      },
    ]

    const { container } = render(
      <ThemeDetailPanel theme={theme} stocks={[]} leaders={leaders} />
    )

    // leader card body는 v1.0.2에서 미렌더링
    const leaderReasonBody = container.querySelector('[data-testid="leader-inclusion-reason-body"]')
    expect(leaderReasonBody).toBeNull()

    // "주도주" 헤더 텍스트도 미렌더링
    expect(screen.queryByText('주도주')).toBeNull()
  })

  it('renders correctly when leaders prop is omitted entirely', () => {
    const theme = {
      theme_id: 557,
      theme_name: '유리 기판',
      change_pct: 13.58,
      change_pct_3d: 13.58,
      theme_description: '유리 기판은 차세대 반도체 기판입니다.',
    }

    // leaders prop omitted (optional after v1.0.2)
    const { container } = render(
      <ThemeDetailPanel theme={theme} stocks={[]} />
    )

    // 테마 설명 본문은 정상 렌더링
    const descBody = container.querySelector('[data-testid="theme-description-body"]')
    expect(descBody).not.toBeNull()

    // 주도주 섹션은 미렌더링
    expect(screen.queryByText('주도주')).toBeNull()
  })
})
