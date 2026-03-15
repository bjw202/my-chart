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
}
