// RED: AC-SUX-052 (ER-1 셀 5상태) / AC-SUX-053 (ER-2 0·50.0·NaN 렌더 금지)
import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { MetricCell, percent2, percent1, MISSING_TEXT, INSUFFICIENT_TEXT } from '../MetricCell'

afterEach(() => cleanup())

describe('AC-SUX-052 — MetricCell 5상태 (ER-1)', () => {
  it('{value:null, reason:"missing"} → "–"', () => {
    render(<MetricCell value={{ value: null, reason: 'missing' }} format={percent2} />)
    expect(screen.getByTestId('metric-cell')).toHaveTextContent(MISSING_TEXT)
    expect(screen.getByTestId('metric-cell').textContent).toBe('–')
  })

  it('0.0 → "0.00%" — 결측이 아니라 실제 0 이다 (ER-2 핵심)', () => {
    render(<MetricCell value={0.0} format={percent2} />)
    expect(screen.getByTestId('metric-cell').textContent).toBe('0.00%')
  })

  it('{value:null, reason:"insufficient"} → "계산 불가" + 사유 툴팁', () => {
    render(<MetricCell value={{ value: null, reason: 'insufficient' }} format={percent2} />)
    const el = screen.getByTestId('metric-cell')
    expect(el.textContent).toBe(INSUFFICIENT_TEXT)
    expect(el.textContent).toBe('계산 불가')
    expect(el.getAttribute('title')).toBeTruthy()
  })

  it('{value:42, low_confidence:true} → "42 ⚠" + 사유 툴팁', () => {
    render(<MetricCell value={{ value: 42, low_confidence: true }} />)
    const el = screen.getByTestId('metric-cell')
    expect(el.textContent).toBe('42 ⚠')
    expect(el.getAttribute('title')).toBeTruthy()
  })

  it('{value:42, warnings:[...]} → "42 ❗" + 경고 문구가 툴팁에 들어간다', () => {
    render(<MetricCell value={{ value: 42, warnings: ['거래정지 이력', '분할 미반영'] }} />)
    const el = screen.getByTestId('metric-cell')
    expect(el.textContent).toBe('42 ❗')
    expect(el.getAttribute('title')).toContain('거래정지 이력')
    expect(el.getAttribute('title')).toContain('분할 미반영')
  })

  it('한 행 5셀 동시 렌더 — 5상태가 서로 구분되는 텍스트를 낸다', () => {
    render(
      <table><tbody><tr>
        <td><MetricCell value={{ value: null, reason: 'missing' }} format={percent2} /></td>
        <td><MetricCell value={0.0} format={percent2} /></td>
        <td><MetricCell value={{ value: null, reason: 'insufficient' }} format={percent2} /></td>
        <td><MetricCell value={{ value: 42, low_confidence: true }} /></td>
        <td><MetricCell value={{ value: 42, warnings: ['w'] }} /></td>
      </tr></tbody></table>,
    )
    const texts = screen.getAllByTestId('metric-cell').map(e => e.textContent)
    expect(texts).toEqual(['–', '0.00%', '계산 불가', '42 ⚠', '42 ❗'])
    // 5개 텍스트가 전부 서로 다르다 — 결측/0/계산불가가 뭉개지지 않는다
    expect(new Set(texts).size).toBe(5)
  })

  it('같은 상태는 화면과 무관하게 같은 CSS class 를 낸다 (공용 컴포넌트 단언)', () => {
    render(
      <>
        <MetricCell value={{ value: null, reason: 'missing' }} />
        <MetricCell value={{ value: null, reason: 'missing' }} />
      </>,
    )
    const [a, b] = screen.getAllByTestId('metric-cell')
    expect(a.className).toBe(b.className)
    expect(a.className).toContain('metric-cell--missing')
  })

  it('상태별 class 가 서로 다르다 — 스타일 채널이 상태를 구분한다', () => {
    render(
      <>
        <MetricCell value={{ value: null, reason: 'missing' }} />
        <MetricCell value={{ value: null, reason: 'insufficient' }} />
        <MetricCell value={0} />
        <MetricCell value={{ value: 42, low_confidence: true }} />
        <MetricCell value={{ value: 42, warnings: ['w'] }} />
      </>,
    )
    const classes = screen.getAllByTestId('metric-cell').map(e => e.className)
    expect(new Set(classes).size).toBe(5)
  })
})

describe('AC-SUX-053 — 결측의 0/50.0/NaN 렌더 금지 (ER-2)', () => {
  it('null 은 절대 0 계열 텍스트로 렌더되지 않는다', () => {
    render(<MetricCell value={null} format={percent1} />)
    const t = screen.getByTestId('metric-cell').textContent ?? ''
    expect(t).not.toContain('0.0')
    expect(t).not.toContain('0%')
    expect(t).toBe('–')
  })

  it('undefined 도 결측으로 처리된다 (런타임 예외 없음)', () => {
    render(<MetricCell value={undefined} format={percent1} />)
    expect(screen.getByTestId('metric-cell').textContent).toBe('–')
  })

  it('NaN 은 "NaN" 문자열로 새지 않는다 — 결측으로 흡수', () => {
    render(<MetricCell value={Number.NaN} format={percent1} />)
    const t = screen.getByTestId('metric-cell').textContent ?? ''
    expect(t).not.toContain('NaN')
    expect(t).toBe('–')
  })

  it('{value:null} 안의 null 도 50.0 같은 중립값으로 대체되지 않는다', () => {
    render(<MetricCell value={{ value: null }} format={(n) => n.toFixed(1)} />)
    const t = screen.getByTestId('metric-cell').textContent ?? ''
    expect(t).not.toContain('50.0')
    expect(t).toBe('–')
  })

  it('percent1/percent2 는 결측을 받지 않는다 — 숫자 전용 포맷터 (무조건 toFixed 경로 제거)', () => {
    expect(percent1(0)).toBe('0.0%')
    expect(percent1(-3.2)).toBe('-3.2%')
    expect(percent1(3.2)).toBe('+3.2%')
    expect(percent2(0)).toBe('0.00%')
    expect(percent2(12.5)).toBe('+12.50%')
  })
})
