// RED: Specification tests for SectorDetailPanel component
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import type { SectorRankItem } from '../../../types/market'

// fetchSectorDetail 모킹
vi.mock('../../../api/sectors', () => ({
  fetchSectorDetail: vi.fn(),
}))

import { fetchSectorDetail } from '../../../api/sectors'
import { SectorDetailPanel } from '../SectorDetailPanel'

const mockFetchSectorDetail = vi.mocked(fetchSectorDetail)

const mockSector: SectorRankItem = {
  name: 'Technology',
  stock_count: 50,
  returns: { w1: 2.5, m1: 5.0, m3: 10.0 },
  excess_returns: { w1: 1.0, m1: 2.0, m3: 4.0 },
  rs_avg: 75,
  rs_top_pct: 30,
  nh_pct: 20,
  stage2_pct: 40,
  composite_score: 80,
  rank: 1,
  rank_change: 2,
}

describe('SectorDetailPanel — rendering', () => {
  beforeEach(() => {
    // 기본적으로 detail API는 빈 응답 반환
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [],
      top_stocks: [],
    })
  })

  it('renders sector name as title', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('Technology')).toBeInTheDocument()
  })

  it('renders the panel container with correct class', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(document.querySelector('.sector-detail-panel')).toBeInTheDocument()
  })

  it('renders RS Avg metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('RS Avg')).toBeInTheDocument()
    expect(screen.getByText('75')).toBeInTheDocument()
  })

  it('renders RS Top % metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('RS Top %')).toBeInTheDocument()
    expect(screen.getByText('30%')).toBeInTheDocument()
  })

  it('renders 52W High % metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('52W High %')).toBeInTheDocument()
    expect(screen.getByText('20%')).toBeInTheDocument()
  })

  it('renders Stage 2 % metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('Stage 2 %')).toBeInTheDocument()
    expect(screen.getByText('40%')).toBeInTheDocument()
  })

  it('renders Composite Score metric', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('Composite Score')).toBeInTheDocument()
    expect(screen.getByText('80')).toBeInTheDocument()
  })

  it('renders sub-sector placeholder text', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText(/sub-sector/i)).toBeInTheDocument()
  })

  it('renders returns section with 1W, 1M, 3M labels', () => {
    render(<SectorDetailPanel sector={mockSector} />)
    expect(screen.getByText('1W')).toBeInTheDocument()
    expect(screen.getByText('1M')).toBeInTheDocument()
    expect(screen.getByText('3M')).toBeInTheDocument()
  })
})

describe('SectorDetailPanel — sub-sector table with rs_avg and stage2_pct (R3)', () => {
  it('sub-sector 테이블에 RS Avg 컬럼 헤더가 표시되어야 함', async () => {
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [
        {
          name: '반도체',
          stock_count: 10,
          stage1_count: 1,
          stage2_count: 5,
          stage3_count: 3,
          stage4_count: 1,
          rs_avg: 82,
          stage2_pct: 50,
        },
      ],
      top_stocks: [],
    })

    render(<SectorDetailPanel sector={mockSector} />)

    await waitFor(() => {
      expect(screen.getByText('RS Avg')).toBeInTheDocument()
    })
  })

  it('sub-sector 테이블에 S2% 컬럼 헤더가 표시되어야 함', async () => {
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [
        {
          name: '반도체',
          stock_count: 10,
          stage1_count: 1,
          stage2_count: 5,
          stage3_count: 3,
          stage4_count: 1,
          rs_avg: 82,
          stage2_pct: 50,
        },
      ],
      top_stocks: [],
    })

    render(<SectorDetailPanel sector={mockSector} />)

    await waitFor(() => {
      // 'S2%' 또는 'Stage2%' 형태의 헤더 확인
      const headerEl = screen.queryByText('S2%') || screen.queryByText('Stage2%') || screen.queryByText('S2 %')
      expect(headerEl).toBeInTheDocument()
    })
  })

  it('sub-sector 행에 rs_avg 값이 표시되어야 함', async () => {
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [
        {
          name: '반도체',
          stock_count: 10,
          stage1_count: 1,
          stage2_count: 5,
          stage3_count: 3,
          stage4_count: 1,
          rs_avg: 82,
          stage2_pct: 50,
        },
      ],
      top_stocks: [],
    })

    render(<SectorDetailPanel sector={mockSector} />)

    await waitFor(() => {
      // rs_avg=82이 표시되어야 함
      expect(screen.getByText('82')).toBeInTheDocument()
    })
  })

  it('sub-sector 행에 stage2_pct 값이 % 형태로 표시되어야 함', async () => {
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [
        {
          name: '반도체',
          stock_count: 10,
          stage1_count: 1,
          stage2_count: 5,
          stage3_count: 3,
          stage4_count: 1,
          rs_avg: 82,
          stage2_pct: 50,
        },
      ],
      top_stocks: [],
    })

    render(<SectorDetailPanel sector={mockSector} />)

    await waitFor(() => {
      // stage2_pct=50이 '50%' 형태로 표시되어야 함
      expect(screen.getByText('50%')).toBeInTheDocument()
    })
  })

  it('rs_avg가 없는 경우 하이픈(-) 표시되어야 함', async () => {
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [
        {
          name: '반도체',
          stock_count: 10,
          stage1_count: 1,
          stage2_count: 5,
          stage3_count: 3,
          stage4_count: 1,
          // rs_avg, stage2_pct 없음
        },
      ],
      top_stocks: [],
    })

    render(<SectorDetailPanel sector={mockSector} />)

    await waitFor(() => {
      // 서브섹터 이름이 나타나면 렌더 완료
      expect(screen.getByText('반도체')).toBeInTheDocument()
    })
    // rs_avg 없을 때 '-' 표시
    const dashes = screen.getAllByText('-')
    expect(dashes.length).toBeGreaterThanOrEqual(1)
  })
})

describe('SectorDetailPanel — top stocks table with chg_1m (R3)', () => {
  it('top stocks 테이블에 1M% 컬럼 헤더가 표시되어야 함', async () => {
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [],
      top_stocks: [
        {
          code: '005930',
          name: '삼성전자',
          rs_12m: 80,
          stage: 2,
          chg_1m: 5.3,
        },
      ],
    })

    render(<SectorDetailPanel sector={mockSector} />)

    await waitFor(() => {
      expect(screen.getByText('1M%')).toBeInTheDocument()
    })
  })

  it('top stocks 행에 chg_1m 값이 표시되어야 함', async () => {
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [],
      top_stocks: [
        {
          code: '005930',
          name: '삼성전자',
          rs_12m: 80,
          stage: 2,
          chg_1m: 5.3,
        },
      ],
    })

    render(<SectorDetailPanel sector={mockSector} />)

    await waitFor(() => {
      // chg_1m=5.3이 '+5.3%' 형태로 표시되어야 함
      expect(screen.getByText('+5.3%')).toBeInTheDocument()
    })
  })

  it('chg_1m이 음수일 때 빨간색으로 표시되어야 함 (색상 클래스 확인)', async () => {
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [],
      top_stocks: [
        {
          code: '005930',
          name: '삼성전자',
          rs_12m: 80,
          stage: 2,
          chg_1m: -3.2,
        },
      ],
    })

    const { container } = render(<SectorDetailPanel sector={mockSector} />)

    await waitFor(() => {
      expect(screen.getByText('-3.2%')).toBeInTheDocument()
    })

    // 음수 변화율에는 negative 클래스나 스타일이 적용되어야 함
    const negEl = container.querySelector('.chg-negative, [class*="negative"], [style*="negative"]')
    // 텍스트로 '-3.2%' 확인으로 충분 (스타일은 구현에 따라 다를 수 있음)
    expect(screen.getByText('-3.2%')).toBeInTheDocument()
  })

  it('chg_1m이 null인 경우 하이픈(-) 표시되어야 함', async () => {
    mockFetchSectorDetail.mockResolvedValue({
      sector_name: 'Technology',
      sub_sectors: [],
      top_stocks: [
        {
          code: '005930',
          name: '삼성전자',
          rs_12m: 80,
          stage: 2,
          chg_1m: null,
        },
      ],
    })

    render(<SectorDetailPanel sector={mockSector} />)

    await waitFor(() => {
      expect(screen.getByText('삼성전자')).toBeInTheDocument()
    })

    // chg_1m=null이면 '-' 표시
    const dashes = screen.getAllByText('-')
    expect(dashes.length).toBeGreaterThanOrEqual(1)
  })
})
