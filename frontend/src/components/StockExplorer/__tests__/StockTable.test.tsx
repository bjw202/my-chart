// RED: Tests for StockTable component
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { Stage2Candidate } from '../../../types/stage'
import { StockTable } from '../StockTable'

const makeCandidates = (): Stage2Candidate[] => [
  {
    code: '005930',
    name: '삼성전자',
    market: 'KOSPI',
    sector_major: 'IT',
    sector_minor: '반도체',
    stage: 'Stage 2',
    stage_detail: 'Stage 2 Strong',
    rs_12m: 75.5,
    chg_1m: 3.2,
    volume_ratio: 1.5,
    close: 75000,
    sma50: 72000,
    sma200: 68000,
  },
  {
    code: '000660',
    name: 'SK하이닉스',
    market: 'KOSPI',
    sector_major: 'IT',
    sector_minor: '반도체',
    stage: 'Stage 2',
    stage_detail: 'Stage 2 entry',
    rs_12m: 45.0,
    chg_1m: 1.5,
    volume_ratio: 1.2,
    close: 180000,
    sma50: 175000,
    sma200: 160000,
  },
  {
    code: '035420',
    name: 'NAVER',
    market: 'KOSPI',
    sector_major: 'IT',
    sector_minor: '인터넷',
    stage: 'Stage 1',
    stage_detail: 'Stage 1',
    rs_12m: 30.0,
    chg_1m: -1.0,
    volume_ratio: 0.9,
    close: 220000,
    sma50: 215000,
    sma200: 210000,
  },
]

describe('StockTable', () => {
  it('should render all candidates when no filters applied', () => {
    render(
      <StockTable
        candidates={makeCandidates()}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />
    )

    expect(screen.getByText('삼성전자')).toBeInTheDocument()
    expect(screen.getByText('SK하이닉스')).toBeInTheDocument()
    expect(screen.getByText('NAVER')).toBeInTheDocument()
  })

  it('should filter by stage when stageFilter is set', () => {
    render(
      <StockTable
        candidates={makeCandidates()}
        stageFilter="Stage 2"
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />
    )

    expect(screen.getByText('삼성전자')).toBeInTheDocument()
    expect(screen.getByText('SK하이닉스')).toBeInTheDocument()
    expect(screen.queryByText('NAVER')).not.toBeInTheDocument()
  })

  it('should filter by sector when sectorFilter is set', () => {
    const candidates: Stage2Candidate[] = [
      ...makeCandidates(),
      {
        code: '207940',
        name: '삼성바이오로직스',
        market: 'KOSPI',
        sector_major: 'Healthcare',
        sector_minor: '바이오',
        stage: 'Stage 2',
        stage_detail: 'Stage 2 Strong',
        rs_12m: 65.0,
        chg_1m: 2.1,
        volume_ratio: 1.3,
        close: 900000,
        sma50: 880000,
        sma200: 850000,
      },
    ]

    render(
      <StockTable
        candidates={candidates}
        stageFilter={null}
        sectorFilter="IT"
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />
    )

    expect(screen.getByText('삼성전자')).toBeInTheDocument()
    expect(screen.queryByText('삼성바이오로직스')).not.toBeInTheDocument()
  })

  it('should show Stage 2 Strong badge with bold border for rs > 60', () => {
    const { container } = render(
      <StockTable
        candidates={[makeCandidates()[0]]} // 삼성전자 rs=75.5, Stage 2 Strong
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />
    )

    const strongBadge = container.querySelector('.stage-badge--s2-strong')
    expect(strongBadge).toBeTruthy()
  })

  it('should show star badge for Stage 2 entry candidates', () => {
    render(
      <StockTable
        candidates={[makeCandidates()[1]]} // SK하이닉스 stage_detail="Stage 2 entry"
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />
    )

    expect(screen.getByText('★')).toBeInTheDocument()
  })

  it('should call onStockSelect when checkbox is clicked', async () => {
    const user = userEvent.setup()
    const onStockSelect = vi.fn()

    render(
      <StockTable
        candidates={makeCandidates()}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={onStockSelect}
        selectedStocks={new Set()}
      />
    )

    const checkboxes = screen.getAllByRole('checkbox')
    await user.click(checkboxes[0])

    expect(onStockSelect).toHaveBeenCalledWith('005930')
  })

  it('should show checked state for selected stocks', () => {
    render(
      <StockTable
        candidates={makeCandidates()}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set(['005930'])}
      />
    )

    const checkboxes = screen.getAllByRole('checkbox') as HTMLInputElement[]
    // First checkbox corresponds to 005930 (삼성전자)
    expect(checkboxes[0].checked).toBe(true)
    expect(checkboxes[1].checked).toBe(false)
  })

  it('should display RS rating with correct value', () => {
    render(
      <StockTable
        candidates={[makeCandidates()[0]]} // rs=75.5
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />
    )

    expect(screen.getByText('76')).toBeInTheDocument() // rounded rs_12m
  })

  it('should display market column (KOSPI/KOSDAQ)', () => {
    render(
      <StockTable
        candidates={makeCandidates()}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />
    )

    const kospiElements = screen.getAllByText('KOSPI')
    expect(kospiElements.length).toBeGreaterThan(0)
  })

  it('should display stock code alongside name', () => {
    render(
      <StockTable
        candidates={[makeCandidates()[0]]}
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />
    )

    expect(screen.getByText('005930')).toBeInTheDocument()
  })

  it('should show volume ratio column', () => {
    render(
      <StockTable
        candidates={[makeCandidates()[0]]} // volume_ratio=1.5
        stageFilter={null}
        sectorFilter={null}
        onStockSelect={vi.fn()}
        selectedStocks={new Set()}
      />
    )

    expect(screen.getByText('1.50')).toBeInTheDocument()
  })
})
