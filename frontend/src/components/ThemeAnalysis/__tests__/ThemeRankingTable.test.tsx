// RED: ThemeRankingTable — theme_description tooltip 렌더링 검증 (SPEC-NAVER-THEME-003 AC-4, AC-5)
import { describe, it, expect, vi } from 'vitest'
import { render } from '@testing-library/react'
import { ThemeRankingTable } from '../ThemeRankingTable'

// 공통 props (sort/callback 무관)
const defaultProps = {
  sortField: 'change_pct',
  sortDirection: 'desc' as const,
  onSort: vi.fn(),
  onThemeClick: vi.fn(),
  selectedThemeId: null,
}

// AC-4: theme_description 채워진 셀에 title 속성 존재
describe('ThemeRankingTable — theme_description Tooltip 렌더링 (AC-4)', () => {
  it('renders title attribute when theme_description present', () => {
    const themes = [
      {
        theme_id: 1,
        theme_name: '전선',
        change_pct: 9.2,
        change_pct_3d: 12.0,
        theme_description: '각종 전선 및 전람(電纜) 제조 테마',
      },
    ]

    const { container } = render(
      <ThemeRankingTable {...defaultProps} themes={themes} />
    )

    // theme_name 셀에 title 속성이 description 값으로 설정되어야 함
    const cellWithDesc = container.querySelector('td[title="각종 전선 및 전람(電纜) 제조 테마"]')
    expect(cellWithDesc).not.toBeNull()
    expect(cellWithDesc?.textContent).toContain('전선')
  })
})

// AC-5: theme_description null/undefined/빈 문자열 시 title 속성 hidden (D-4)
describe('ThemeRankingTable — null/undefined/empty description hidden (AC-5)', () => {
  it('omits title attribute when theme_description is null', () => {
    const themes = [
      {
        theme_id: 1,
        theme_name: 'NullDesc',
        change_pct: 1.0,
        change_pct_3d: 1.0,
        theme_description: null,
      },
    ]

    const { container } = render(
      <ThemeRankingTable {...defaultProps} themes={themes} />
    )

    const rows = container.querySelectorAll('tbody tr')
    rows.forEach(row => {
      // theme_name 셀은 첫 번째 td
      const nameCell = row.querySelector('td:first-child')
      const titleAttr = nameCell?.getAttribute('title')
      // title 속성 없거나 빈 문자열이어야 함 (hidden — D-4)
      expect(titleAttr === null || titleAttr === '' || titleAttr === undefined).toBe(true)
    })
  })

  it('omits title attribute when theme_description is undefined', () => {
    const themes = [
      {
        theme_id: 2,
        theme_name: 'NoDesc',
        change_pct: 1.0,
        change_pct_3d: 1.0,
        // theme_description 미포함
      },
    ]

    const { container } = render(
      <ThemeRankingTable {...defaultProps} themes={themes} />
    )

    const rows = container.querySelectorAll('tbody tr')
    rows.forEach(row => {
      const nameCell = row.querySelector('td:first-child')
      const titleAttr = nameCell?.getAttribute('title')
      expect(titleAttr === null || titleAttr === '' || titleAttr === undefined).toBe(true)
    })
  })

  it('omits title attribute when theme_description is empty string', () => {
    const themes = [
      {
        theme_id: 3,
        theme_name: 'EmptyDesc',
        change_pct: 1.0,
        change_pct_3d: 1.0,
        theme_description: '',
      },
    ]

    const { container } = render(
      <ThemeRankingTable {...defaultProps} themes={themes} />
    )

    const rows = container.querySelectorAll('tbody tr')
    rows.forEach(row => {
      const nameCell = row.querySelector('td:first-child')
      const titleAttr = nameCell?.getAttribute('title')
      // 빈 문자열도 hidden — D-4 (|| 연산자로 보장)
      expect(titleAttr === null || titleAttr === '' || titleAttr === undefined).toBe(true)
    })
  })
})
