// Stage analysis types - mirrors backend /api/stage/overview response

export interface StageDistribution {
  stage1: number
  stage2: number
  stage3: number
  stage4: number
  total: number
}

export interface StageBySector {
  sector: string
  stage1: number
  stage2: number
  stage3: number
  stage4: number
}

export interface Stage2Candidate {
  code: string
  name: string
  market: string
  sector_major: string
  sector_minor: string
  stage: number | string
  stage_detail: string
  rs_12m: number
  chg_1m: number
  volume_ratio: number
  close: number
  sma50: number
  sma200: number
}

export interface StageOverviewResponse {
  distribution: StageDistribution
  by_sector: StageBySector[]
  stage2_candidates: Stage2Candidate[]
}
