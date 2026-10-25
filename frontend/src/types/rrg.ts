// RRG (Relative Rotation Graph) 타입 정의

export interface RRGTrailPoint {
  date: string
  rs_ratio: number
  rs_momentum: number
}

export interface RRGSectorItem {
  name: string
  rs_ratio: number
  rs_momentum: number
  quadrant: 'leading' | 'weakening' | 'lagging' | 'improving'
  trail: RRGTrailPoint[]
}

export interface KospiPoint {
  date: string
  close: number
}

export interface RRGResponse {
  date: string
  sectors: RRGSectorItem[]
  kospi: KospiPoint[]
  // AC-SUX-037 기준일 — 공통 봉투(EnvelopeMixin)가 제공. 기준일 레지스트리·배지가 소비한다.
  as_of_date?: string | null
}
