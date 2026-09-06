import {
  bpChange,
  getPreviousSnapshot,
  getSnapshot,
  spreadBp,
  yieldAt,
} from "./metrics.ts"
import {
  TENORS,
  type CurveSnapshot,
  type RatesDataset,
  type TenorYears,
} from "./types.ts"

export interface RatesViewPoint {
  tenorYears: TenorYears
  current: number | null
  comparison: number | null
  changeBp: number | null
  dayBp: number | null
  weekBp: number | null
}

export interface RatesKpiHistoryPoint {
  date: string
  value: number | null
}

export interface RatesKpi {
  id: "tenY" | "thirtyY" | "twoTen" | "fiveThirty"
  label: "10Y" | "30Y" | "2s10s" | "5s30s"
  value: number | null
  unit: "%" | "bp"
  dayBp: number | null
  history: RatesKpiHistoryPoint[]
}

export interface RatesViewModel {
  date: string
  comparisonDate: string
  points: RatesViewPoint[]
  kpis: RatesKpi[]
}

const difference = (
  current: number | null,
  previous: number | null,
): number | null =>
  current === null || previous === null ? null : current - previous

const levelHistory = (
  snapshots: CurveSnapshot[],
  tenor: TenorYears,
): RatesKpiHistoryPoint[] =>
  snapshots.map((snapshot) => ({
    date: snapshot.date,
    value: yieldAt(snapshot, tenor),
  }))

const spreadHistory = (
  snapshots: CurveSnapshot[],
  shortTenor: TenorYears,
  longTenor: TenorYears,
): RatesKpiHistoryPoint[] =>
  snapshots.map((snapshot) => ({
    date: snapshot.date,
    value: spreadBp(snapshot, shortTenor, longTenor),
  }))

export function buildRatesViewModel(
  dataset: RatesDataset,
  date: string,
  comparisonDate: string,
): RatesViewModel {
  const current = getSnapshot(dataset, date)
  if (current === undefined) {
    throw new RangeError(`Selected date ${date} is not an observation`)
  }
  const comparison = getSnapshot(dataset, comparisonDate)
  if (comparison === undefined) {
    throw new RangeError(
      `Comparison date ${comparisonDate} is not an observation`,
    )
  }

  const previous = getPreviousSnapshot(dataset, date)
  const weekPrevious = getPreviousSnapshot(dataset, date, 5)
  const selectedIndex = dataset.snapshots.findIndex(
    (snapshot) => snapshot.date === date,
  )
  const historySnapshots = dataset.snapshots
    .slice(0, selectedIndex + 1)
    .slice(-30)

  const points: RatesViewPoint[] = TENORS.map((tenorYears) => {
    const currentYield = yieldAt(current, tenorYears)
    return {
      tenorYears,
      current: currentYield,
      comparison: yieldAt(comparison, tenorYears),
      changeBp: bpChange(currentYield, yieldAt(comparison, tenorYears)),
      dayBp: bpChange(currentYield, yieldAt(previous, tenorYears)),
      weekBp: bpChange(currentYield, yieldAt(weekPrevious, tenorYears)),
    }
  })

  const twoTen = spreadBp(current, 2, 10)
  const previousTwoTen = spreadBp(previous, 2, 10)
  const fiveThirty = spreadBp(current, 5, 30)
  const previousFiveThirty = spreadBp(previous, 5, 30)

  const kpis: RatesKpi[] = [
    {
      id: "tenY",
      label: "10Y",
      value: yieldAt(current, 10),
      unit: "%",
      dayBp: bpChange(yieldAt(current, 10), yieldAt(previous, 10)),
      history: levelHistory(historySnapshots, 10),
    },
    {
      id: "thirtyY",
      label: "30Y",
      value: yieldAt(current, 30),
      unit: "%",
      dayBp: bpChange(yieldAt(current, 30), yieldAt(previous, 30)),
      history: levelHistory(historySnapshots, 30),
    },
    {
      id: "twoTen",
      label: "2s10s",
      value: twoTen,
      unit: "bp",
      dayBp: difference(twoTen, previousTwoTen),
      history: spreadHistory(historySnapshots, 2, 10),
    },
    {
      id: "fiveThirty",
      label: "5s30s",
      value: fiveThirty,
      unit: "bp",
      dayBp: difference(fiveThirty, previousFiveThirty),
      history: spreadHistory(historySnapshots, 5, 30),
    },
  ]

  return { date, comparisonDate, points, kpis }
}
