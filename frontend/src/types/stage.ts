// Stage analysis types - mirrors backend /api/stage/overview response

export interface StageDistribution {
  stage1: number
  stage2: number
  stage3: number
  stage4: number
  // AC-SUX-030 (REQ-SUX-028): SMA40/10 결측 분류 불가 종목 수 (② unclassified_count).
  unclassified_count?: number
  total: number
}

export interface StageBySector {
  sector: string
  stage1: number
  stage2: number
  stage3: number
  stage4: number
  // AC-SUX-029 (REQ-SUX-027): by_sector 항목도 분포와 동일 불변식. ② unclassified_count.
  unclassified_count?: number
  total?: number
}

export interface Stage2Candidate {
  code: string
  name: string
  market: string
  sector_major: string
  sector_minor: string
  // API always returns integer stage values (1-4)
  stage: number
  stage_detail: string
  rs_12m: number
  chg_1m: number
  volume_ratio: number
  close: number
  sma50: number
  sma200: number
  // M4 (AC-SUX-031, REQ-SUX-029/030): 종목 표 3열 확장 + 섹터비중. ② StageStock 추가 필드.
  chg_1w?: number | null        // 1W% 열
  chg_3m?: number | null        // 3M% 열
  weight_in_sector?: number | null  // 섹터비중 열
  // ⊤ 마커 — 상한 적용(capped) 종목. ② 가 별도 플래그를 내리지 않으므로, weight_in_sector 가
  // 상한선(WEIGHT_CAP=0.1)에 근접해 clipped 된 경우를 표현. 백엔드 확장 전까지 optional.
  weight_capped?: boolean
  // 52W고 열 — ② StageStock.near_52w_high. 52주 고가 근접 여부.
  near_52w_high?: boolean | null
}

export interface StageOverviewResponse {
  distribution: StageDistribution
  by_sector: StageBySector[]
  stage2_candidates: Stage2Candidate[]
  all_stocks: Stage2Candidate[]
  // ② 봉투(EnvelopeMixin) 선택 필드 — M6 AC-SUX-037 기준일 배지 / SN-5.
  as_of_date?: string | null
  as_of_is_partial_week?: boolean | null
  grid_version?: string | null
}
