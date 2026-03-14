// RED: Tests for stage types - verify shape matches backend API contract
import { describe, it, expect } from 'vitest'
import type {
  StageDistribution,
  StageBySector,
  Stage2Candidate,
  StageOverviewResponse,
} from '../stage'

describe('StageDistribution type', () => {
  it('should accept valid stage distribution data', () => {
    const dist: StageDistribution = {
      stage1: 120,
      stage2: 85,
      stage3: 45,
      stage4: 30,
      total: 280,
    }
    expect(dist.total).toBe(280)
    expect(dist.stage2).toBe(85)
  })
})

describe('StageBySector type', () => {
  it('should accept valid sector stage data', () => {
    const sector: StageBySector = {
      sector: 'IT',
      stage1: 10,
      stage2: 15,
      stage3: 5,
      stage4: 2,
    }
    expect(sector.sector).toBe('IT')
    expect(sector.stage2).toBe(15)
  })
})

describe('Stage2Candidate type', () => {
  it('should accept valid stage2 candidate data', () => {
    const candidate: Stage2Candidate = {
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
    }
    expect(candidate.code).toBe('005930')
    expect(candidate.rs_12m).toBe(75.5)
  })
})

describe('StageOverviewResponse type', () => {
  it('should accept valid stage overview response', () => {
    const response: StageOverviewResponse = {
      distribution: { stage1: 120, stage2: 85, stage3: 45, stage4: 30, total: 280 },
      by_sector: [{ sector: 'IT', stage1: 10, stage2: 15, stage3: 5, stage4: 2 }],
      stage2_candidates: [
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
      ],
    }
    expect(response.distribution.total).toBe(280)
    expect(response.stage2_candidates).toHaveLength(1)
  })
})
