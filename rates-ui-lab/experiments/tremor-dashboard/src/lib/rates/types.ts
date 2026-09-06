export const TENORS = [2, 5, 7, 10, 20, 30, 40] as const

export type TenorYears = (typeof TENORS)[number]

export interface YieldPoint {
  tenorYears: TenorYears
  yieldPct: number | null
}

export interface CurveSnapshot {
  date: string
  points: YieldPoint[]
}

export interface RatesDataset {
  schemaVersion: 1
  dataKind: "synthetic"
  currency: "JPY"
  curve: "JGB"
  sourceLabel: string
  snapshots: CurveSnapshot[]
}
