import {
  TENORS,
  type CurveSnapshot,
  type RatesDataset,
  type TenorYears,
} from "./types.ts"

const TENOR_SET = new Set<number>(TENORS)
const DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value)

const isValidDate = (value: unknown): value is string => {
  if (typeof value !== "string" || !DATE_PATTERN.test(value)) return false
  const parsed = new Date(`${value}T00:00:00.000Z`)
  return (
    !Number.isNaN(parsed.valueOf()) &&
    parsed.toISOString().slice(0, 10) === value
  )
}

const fail = (message: string): never => {
  throw new TypeError(`Invalid rates dataset: ${message}`)
}

export function validateDataset(value: unknown): RatesDataset {
  if (!isRecord(value)) return fail("root must be an object")
  if (value.schemaVersion !== 1) return fail("schemaVersion must be 1")
  if (value.dataKind !== "synthetic") return fail("dataKind must be synthetic")
  if (value.currency !== "JPY") return fail("currency must be JPY")
  if (value.curve !== "JGB") return fail("curve must be JGB")
  if (
    typeof value.sourceLabel !== "string" ||
    value.sourceLabel.trim() === ""
  ) {
    return fail("sourceLabel must be a non-empty string")
  }
  if (!Array.isArray(value.snapshots) || value.snapshots.length === 0) {
    return fail("snapshots must be a non-empty array")
  }

  const seenDates = new Set<string>()
  let previousDate: string | undefined

  value.snapshots.forEach((snapshotValue, snapshotIndex) => {
    if (!isRecord(snapshotValue))
      return fail(`snapshot ${snapshotIndex} must be an object`)
    if (!isValidDate(snapshotValue.date)) {
      return fail(
        `snapshot ${snapshotIndex} date must be a valid YYYY-MM-DD date`,
      )
    }
    const date = snapshotValue.date
    if (seenDates.has(date)) fail(`duplicate snapshot date ${date}`)
    if (previousDate !== undefined && date <= previousDate) {
      fail(
        `snapshot dates must be strictly ascending; found ${date} after ${previousDate}`,
      )
    }
    seenDates.add(date)
    previousDate = date

    if (!Array.isArray(snapshotValue.points)) {
      return fail(`snapshot ${date} points must be an array`)
    }

    const seenTenors = new Set<number>()
    let previousTenor: number | undefined
    snapshotValue.points.forEach((pointValue, pointIndex) => {
      if (!isRecord(pointValue)) {
        return fail(`snapshot ${date} point ${pointIndex} must be an object`)
      }
      const tenor = pointValue.tenorYears
      if (typeof tenor !== "number" || !TENOR_SET.has(tenor)) {
        return fail(`snapshot ${date} has unsupported tenor ${String(tenor)}`)
      }
      if (seenTenors.has(tenor))
        fail(`snapshot ${date} has duplicate tenor ${tenor}`)
      if (previousTenor !== undefined && tenor <= previousTenor) {
        fail(`snapshot ${date} tenors must be strictly ascending`)
      }
      seenTenors.add(tenor)
      previousTenor = tenor

      const yieldPct = pointValue.yieldPct
      if (
        yieldPct !== null &&
        (typeof yieldPct !== "number" || !Number.isFinite(yieldPct))
      ) {
        fail(
          `snapshot ${date} tenor ${tenor} yieldPct must be a finite number or null`,
        )
      }
    })

    if (
      snapshotValue.points.length !== TENORS.length ||
      TENORS.some((tenor) => !seenTenors.has(tenor))
    ) {
      fail(
        `snapshot ${date} must contain all required tenors: ${TENORS.join(", ")}`,
      )
    }
  })

  return value as unknown as RatesDataset
}

export function getSnapshot(
  dataset: RatesDataset,
  date: string,
): CurveSnapshot | undefined {
  return dataset.snapshots.find((snapshot) => snapshot.date === date)
}

export function getPreviousSnapshot(
  dataset: RatesDataset,
  date: string,
  lag = 1,
): CurveSnapshot | undefined {
  if (!Number.isInteger(lag) || lag < 1) {
    throw new RangeError("lag must be a positive integer")
  }
  const currentIndex = dataset.snapshots.findIndex(
    (snapshot) => snapshot.date === date,
  )
  return currentIndex < lag ? undefined : dataset.snapshots[currentIndex - lag]
}

export function yieldAt(
  snapshot: CurveSnapshot | undefined,
  tenor: TenorYears,
): number | null {
  return (
    snapshot?.points.find((point) => point.tenorYears === tenor)?.yieldPct ??
    null
  )
}

export function bpChange(
  current: number | null,
  comparison: number | null,
): number | null {
  return current === null || comparison === null
    ? null
    : 100 * (current - comparison)
}

export function spreadBp(
  snapshot: CurveSnapshot | undefined,
  shortTenor: TenorYears,
  longTenor: TenorYears,
): number | null {
  return bpChange(yieldAt(snapshot, longTenor), yieldAt(snapshot, shortTenor))
}

export function formatYield(value: number | null): string {
  return value === null ? "—" : `${value.toFixed(3)}%`
}

export function formatBp(value: number | null): string {
  if (value === null) return "—"
  // Round only for display, then normalize signed zero at that precision.
  const rounded = Number(value.toFixed(1))
  const normalized = rounded === 0 ? 0 : rounded
  const sign = normalized > 0 ? "+" : ""
  return `${sign}${normalized.toFixed(1)} bp`
}
