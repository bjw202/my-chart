// SPEC-THEME-DISPLAY-UNIFY-001 — ThemeRankingTable 표시 통일 단언.
//   대조(§B AC-TDU-001~008): 마이그레이션이 실제로 일어났음을 반증 가능하게 증명 — 지역 포맷터
//     3종 버전으로 되돌리면 RED. 판정 기준은 lessons #9 ("작성"이 아니라 "되돌림 RED 관측").
//   불변(§C AC-TDU-009~015): 정상값 표시의 바이트 동등 고정 — 되돌려도 GREEN이 정상이며
//     되돌림 실증 대상이 아니다 (acceptance §A.2).
//   대조 단언의 기대값은 프로즌 리터럴 '–'(U+2013)로 못박는다 — MISSING_TEXT import 비교 금지
//     (정본 상수가 바뀌어도 단언이 따라가면 글리프 고정이 풀린다. acceptance §A.1 규칙 3).
//   부분 일치(toContain)/부등식(>=) 금지 — 전체 문자열 등식과 === n 프로즌 개수만 쓴다 (규칙 4·5).
import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { ThemeRankingTable } from '../ThemeRankingTable'
import { MISSING_TEXT } from '../../common/MetricCell' // AC-TDU-014 진단용 단언에서만 사용

// 공통 props — 정렬 상태·콜백은 본 단언의 대상이 아니다 (AC-TDU-015 제외, 거기서 onSort를 덮어쓴다)
const baseProps = {
  sortField: 'change_pct',
  sortDirection: 'desc' as const,
  onSort: vi.fn(),
  onThemeClick: vi.fn(),
  selectedThemeId: null,
}

// tbody 첫 행의 <td> 6개 — 열 순서는 COLUMNS 고정:
//   [0]테마명 [1]등락률 [2]3일등락률 [3]모멘텀점수 [4]상승비율 [5]대표종목
function getRowCells(container: HTMLElement, row = 0): HTMLElement[] {
  return Array.from(container.querySelectorAll(`tbody tr:nth-child(${row + 1}) td`))
}

describe('SPEC-THEME-DISPLAY-UNIFY-001 — 대조 단언 (§B, 되돌림 시 RED)', () => {
  it('AC-TDU-001: momentum_score 결측 시 모멘텀점수 셀이 정확히 "–"(en dash)다', () => {
    const themes = [
      { theme_id: 1, theme_name: '결측테마', change_pct: 1.5, change_pct_3d: -2.5 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[3]?.textContent).toBe('–')
  })

  it('AC-TDU-002: breadth_ratio 결측 시 상승비율 셀이 정확히 "–"다', () => {
    const themes = [
      { theme_id: 1, theme_name: '결측테마', change_pct: 1.5, change_pct_3d: -2.5 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[4]?.textContent).toBe('–')
  })

  it('AC-TDU-003: 지표 셀 구조 채택 — metric-cell testid가 정확히 4개다 (부분 채택도 RED)', () => {
    const themes = [
      { theme_id: 1, theme_name: '구조테마', change_pct: 1.5, change_pct_3d: -2.5 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    // >= 1이 아니라 === 4 — 등락률·3일등락률·모멘텀점수·상승비율 4열 전부 MetricCell이어야 한다
    expect(container.querySelectorAll('[data-testid="metric-cell"]').length).toBe(4)
  })

  it('AC-TDU-004: change_pct = Infinity → 등락률 셀이 정확히 "–"다 (toMetricValue 경유 강제)', () => {
    const themes = [
      { theme_id: 1, theme_name: '무한테마', change_pct: Infinity, change_pct_3d: -2.5 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    // 이 단언은 세 상태를 판별한다: 올바른 구현 '–' / 되돌림 '-' / 날값 전달 '+Infinity%'
    expect(getRowCells(container)[1]?.textContent).toBe('–')
  })

  it('AC-TDU-005: change_pct 런타임 null → 예외 없이 등락률 셀이 정확히 "–"다', () => {
    const themes = [
      {
        theme_id: 1,
        theme_name: '널테마',
        // change_pct는 TS상 필수 number지만 API 응답이 `as` 단언 캐스팅으로 검증 없이 통과하므로
        // (themes.ts fetchThemesSnapshot의 `response.data as ThemesSnapshotResponse`) 런타임 null이
        // 배제되지 않는다 (SPEC §1.3(b)). 이 테스트는 그 런타임 경로를 재현한다 — "불가능한 케이스"로
        // 오해해 삭제하지 말 것.
        change_pct: null as unknown as number,
        change_pct_3d: -2.5,
      },
    ]

    // 구현이 null을 걸러내지 못하면 render 중 TypeError가 전파되어 이 it이 실패한다.
    // "예외 없이 렌더"는 그 전파로 검증된다.
    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[1]?.textContent).toBe('–')
  })

  it('AC-TDU-006: top_stocks_preview 결측 시 대표종목 셀이 정확히 "–"다', () => {
    const themes = [
      { theme_id: 1, theme_name: '결측테마', change_pct: 1.5, change_pct_3d: -2.5 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[5]?.textContent).toBe('–')
  })

  it('AC-TDU-007: 5개 지표 전부 결측인 행의 td 6개 textContent가 프로즌 배열과 정확히 같다', () => {
    const themes = [
      {
        theme_id: 1,
        theme_name: '테스트테마',
        // 필수 타입 2개(change_pct·change_pct_3d)는 런타임 null 재현 주입 — 픽스처를 "결측 3개"로
        // 약화하면 잔여 집합 동등의 강도가 무너진다 (acceptance §B 픽스처 주입 방식 [HARD]).
        change_pct: null as unknown as number,
        change_pct_3d: null as unknown as number,
      },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    // 행 전체를 고정하므로 어느 한 열이라도 '-'로 남으면 RED — 부분 이행을 구조적으로 차단한다
    expect(getRowCells(container).map(td => td.textContent)).toEqual([
      '테스트테마',
      '–',
      '–',
      '–',
      '–',
      '–',
    ])
  })

  it('AC-TDU-008: 신뢰도 상태 무합성 — data-state는 ok/missing만, 개수는 정확히 4', () => {
    // 정상값과 결측이 섞인 1건이어야 한다 — 전부 정상이면 missing 경로가, 전부 결측이면 ok 경로가
    // 검사되지 않는다 (acceptance v0.2.0 정정).
    const themes = [
      {
        theme_id: 1,
        theme_name: '혼합테마',
        change_pct: 1.5,
        change_pct_3d: -2.5,
        momentum_score: undefined,
        breadth_ratio: 0.625,
      },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    const cells = container.querySelectorAll('[data-testid="metric-cell"]')
    // 동반 단언 [HARD]: 빈 집합은 어떤 집합의 부분집합이므로 개수를 못박지 않으면 되돌림에서
    // 공허 참으로 통과한다. 이 AC의 대조 강도 전부가 이 === 4에 실려 있다.
    expect(cells.length).toBe(4)

    const states = Array.from(cells).map(cell => cell.getAttribute('data-state'))
    expect(states.filter(s => s !== 'ok' && s !== 'missing')).toEqual([])
  })
})

describe('SPEC-THEME-DISPLAY-UNIFY-001 — 불변 단언 (§C, 되돌려도 GREEN)', () => {
  it('AC-TDU-009: change_pct = 1.5 → "+1.50%" (전체 등식)', () => {
    const themes = [
      { theme_id: 1, theme_name: '양수', change_pct: 1.5, change_pct_3d: 0 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[1]?.textContent).toBe('+1.50%')
  })

  it('AC-TDU-010: change_pct = -2.5 → "-2.50%" (전체 등식)', () => {
    const themes = [
      { theme_id: 1, theme_name: '음수', change_pct: -2.5, change_pct_3d: 0 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[1]?.textContent).toBe('-2.50%')
  })

  it('AC-TDU-011: change_pct = 0 → "0.00%" — 부호 없음 (실제 0과 결측의 구분)', () => {
    const themes = [
      { theme_id: 1, theme_name: '제로', change_pct: 0, change_pct_3d: 0 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[1]?.textContent).toBe('0.00%')
  })

  it('AC-TDU-012: breadth_ratio = 0.625 → "62.5%" — ×100·1자리·무부호 3축 동시 고정', () => {
    const themes = [
      {
        theme_id: 1,
        theme_name: '상승비율',
        change_pct: 0,
        change_pct_3d: 0,
        breadth_ratio: 0.625,
      },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    // toContain 금지 지점 — '+62.5%'(percent1 부호 회귀)도 '63%'(pct0 정밀도 회귀)도 잡는다
    expect(getRowCells(container)[4]?.textContent).toBe('62.5%')
  })

  it('AC-TDU-013: momentum_score = 3.14159 → "3.14" — 단위 접미사 없음', () => {
    const themes = [
      {
        theme_id: 1,
        theme_name: '모멘텀',
        change_pct: 0,
        change_pct_3d: 0,
        momentum_score: 3.14159,
      },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[3]?.textContent).toBe('3.14')
  })

  it('AC-TDU-014: 정본 MISSING_TEXT 상수가 "–"다 (정본 드리프트 진단)', () => {
    // §B 대조 단언들은 리터럴로 못박혀 있으므로 정본 상수가 바뀌면 그것들이 한꺼번에 RED가 된다.
    // 이 단언은 그때 원인이 Theme 구현이 아니라 정본 변경임을 가리키는 진단용이다.
    expect(MISSING_TEXT).toBe('–')
  })

  it('AC-TDU-015: 등락률 헤더 클릭 → onSort("change_pct") 정확히 1회 + td background 유지', () => {
    const onSort = vi.fn()
    const themes = [
      { theme_id: 1, theme_name: '상승', change_pct: 1.5, change_pct_3d: 2 },
      { theme_id: 2, theme_name: '하락', change_pct: -2.5, change_pct_3d: -1 },
    ]

    const { container } = render(
      <ThemeRankingTable {...baseProps} onSort={onSort} themes={themes} />
    )

    fireEvent.click(container.querySelectorAll('thead th')[1]) // 등락률 헤더
    expect(onSort).toHaveBeenCalledTimes(1)
    expect(onSort).toHaveBeenCalledWith('change_pct')

    // getChangePctColor 셰이딩은 <td>가 계속 소유한다 (REQ-TDU-008) — 양·음 두 행 모두 확인
    const up = (getRowCells(container)[1] as HTMLElement).style.background
    const down = (getRowCells(container, 1)[1] as HTMLElement).style.background
    expect(up).not.toBe('')
    expect(down).not.toBe('')
  })
})

describe('SPEC-THEME-DISPLAY-UNIFY-001 — 경계 조건 (acceptance §E)', () => {
  it('E1: momentum_score = 0 → "0.00" — 실제 0은 결측 아니다', () => {
    const themes = [
      { theme_id: 1, theme_name: '영', change_pct: 0, change_pct_3d: 0, momentum_score: 0 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[3]?.textContent).toBe('0.00')
  })

  it('E2: breadth_ratio = 0 → "0.0%" — 실제 0은 결측 아니다', () => {
    const themes = [
      { theme_id: 1, theme_name: '영', change_pct: 0, change_pct_3d: 0, breadth_ratio: 0 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[4]?.textContent).toBe('0.0%')
  })

  it('E3: breadth_ratio = 1 → "100.0%" — ×100 상한', () => {
    const themes = [
      { theme_id: 1, theme_name: '일', change_pct: 0, change_pct_3d: 0, breadth_ratio: 1 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[4]?.textContent).toBe('100.0%')
  })

  it('E4: change_pct = NaN → "–" — toMetricValue가 결측으로 접는다', () => {
    const themes = [
      { theme_id: 1, theme_name: '난', change_pct: NaN, change_pct_3d: 0 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[1]?.textContent).toBe('–')
  })

  it('E5: change_pct = -Infinity → "–" — AC-TDU-004의 대칭', () => {
    const themes = [
      { theme_id: 1, theme_name: '마이너스무한', change_pct: -Infinity, change_pct_3d: 0 },
    ]

    const { container } = render(<ThemeRankingTable {...baseProps} themes={themes} />)

    expect(getRowCells(container)[1]?.textContent).toBe('–')
  })

  it('E6: themes = [] → 빈 tbody, 예외 없음 (기존 거동)', () => {
    const { container } = render(<ThemeRankingTable {...baseProps} themes={[]} />)

    expect(container.querySelectorAll('tbody tr').length).toBe(0)
  })
})
