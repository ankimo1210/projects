import assert from "node:assert/strict"
import { describe, test } from "node:test"

import {
  bpChange,
  formatBp,
  formatYield,
  getPreviousSnapshot,
  getSnapshot,
  spreadBp,
  validateDataset,
  yieldAt,
} from "./metrics.ts"
import { TENORS, type CurveSnapshot, type RatesDataset } from "./types.ts"

const points = (
  values: ReadonlyArray<number | null>,
): CurveSnapshot["points"] =>
  TENORS.map((tenorYears, index) => ({
    tenorYears,
    yieldPct: values[index] ?? null,
  }))

const dataset = (snapshots: CurveSnapshot[]): RatesDataset => ({
  schemaVersion: 1,
  dataKind: "synthetic",
  currency: "JPY",
  curve: "JGB",
  sourceLabel: "Synthetic test data",
  snapshots,
})

const snapshots: CurveSnapshot[] = [
  { date: "2026-08-27", points: points([0.9, 1.25, 1.5, 1.8, 2.3, 2.48, 2.6]) },
  {
    date: "2026-08-28",
    points: points([0.91, 1.26, 1.51, 1.81, 2.31, 2.49, 2.61]),
  },
  {
    date: "2026-08-31",
    points: points([0.89, 1.24, 1.49, 1.79, 2.29, 2.47, 2.59]),
  },
  { date: "2026-09-01", points: points([0.9, 1.25, 1.5, 1.8, 2.3, 2.48, 2.6]) },
  {
    date: "2026-09-02",
    points: points([0.91, 1.26, 1.51, 1.82, 2.31, 2.49, 2.61]),
  },
  {
    date: "2026-09-03",
    points: points([0.915, 1.27, 1.52, 1.83, 2.32, 2.5, 2.62]),
  },
  {
    date: "2026-09-04",
    points: points([0.92, 1.28, 1.54, 1.85, 2.34, 2.51, 2.63]),
  },
]

describe("rates metrics", () => {
  test("converts percentage-point differences to basis points without rounding", () => {
    assert.ok(Math.abs((bpChange(1.85, 1.8) ?? NaN) - 5) < 1e-12)
    assert.equal(bpChange(null, 1.8), null)
    assert.equal(bpChange(1.85, null), null)
  })

  test("computes 2s10s and 5s30s spreads in basis points", () => {
    const current = snapshots.at(-1)
    assert.ok(Math.abs((spreadBp(current, 2, 10) ?? NaN) - 93) < 1e-12)
    assert.ok(Math.abs((spreadBp(current, 5, 30) ?? NaN) - 123) < 1e-12)
  })

  test("propagates missing yields through yield and spread calculations", () => {
    const missing: CurveSnapshot = {
      date: "2026-09-04",
      points: points([0.92, 1.28, 1.54, null, 2.34, 2.51, 2.63]),
    }
    assert.equal(yieldAt(undefined, 10), null)
    assert.equal(yieldAt(missing, 10), null)
    assert.equal(spreadBp(missing, 2, 10), null)
  })

  test("handles negative and flat curves without special casing", () => {
    const negative: CurveSnapshot = {
      date: "2026-09-04",
      points: points([-0.2, -0.1, -0.05, 0, 0.1, 0.15, 0.2]),
    }
    const flat: CurveSnapshot = {
      date: "2026-09-04",
      points: points([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5]),
    }
    assert.equal(yieldAt(negative, 2), -0.2)
    assert.equal(spreadBp(negative, 2, 10), 20)
    assert.equal(spreadBp(flat, 2, 10), 0)
  })

  test("selects comparison snapshots by observation index across weekends", () => {
    const value = dataset(snapshots)
    assert.equal(getSnapshot(value, "2026-09-04")?.date, "2026-09-04")
    assert.equal(getPreviousSnapshot(value, "2026-09-04")?.date, "2026-09-03")
    assert.equal(
      getPreviousSnapshot(value, "2026-09-04", 5)?.date,
      "2026-08-28",
    )
    assert.equal(getPreviousSnapshot(value, "2026-08-27"), undefined)
    assert.equal(getPreviousSnapshot(value, "2099-01-01"), undefined)
    assert.throws(
      () => getPreviousSnapshot(value, "2026-09-04", 0),
      /positive integer/,
    )
  })

  test("formats yields and basis points with the display precision contract", () => {
    assert.equal(formatYield(1.85), "1.850%")
    assert.equal(formatYield(-0.05), "-0.050%")
    assert.equal(formatYield(null), "—")
    assert.equal(formatBp(5), "+5.0 bp")
    assert.equal(formatBp(-2.25), "-2.3 bp")
    assert.equal(formatBp(0), "0.0 bp")
    assert.equal(formatBp(-0.01), "0.0 bp")
    assert.equal(formatBp(0.01), "0.0 bp")
    assert.equal(formatBp(null), "—")
  })
})

describe("dataset validation", () => {
  test("accepts the complete schema and returns the same typed value", () => {
    const value = dataset(snapshots)
    assert.equal(validateDataset(value), value)
  })

  test("rejects malformed or non-calendar dates", () => {
    const malformed = dataset([{ ...snapshots[0]!, date: "2026-9-04" }])
    const impossible = dataset([{ ...snapshots[0]!, date: "2026-02-30" }])
    assert.throws(() => validateDataset(malformed), /valid YYYY-MM-DD/)
    assert.throws(() => validateDataset(impossible), /valid YYYY-MM-DD/)
  })

  test("rejects duplicate and non-ascending observation dates", () => {
    assert.throws(
      () => validateDataset(dataset([snapshots[0]!, snapshots[0]!])),
      /duplicate snapshot date/,
    )
    assert.throws(
      () => validateDataset(dataset([snapshots[1]!, snapshots[0]!])),
      /strictly ascending/,
    )
  })

  test("rejects duplicate, missing, unsupported, and non-ascending tenors", () => {
    const base = structuredClone(snapshots[0]!)
    const duplicate = structuredClone(base)
    duplicate.points[1]!.tenorYears = 2
    const missing = structuredClone(base)
    missing.points.pop()
    const unsupported = structuredClone(base) as unknown as {
      date: string
      points: Array<{ tenorYears: number; yieldPct: number | null }>
    }
    unsupported.points[6]!.tenorYears = 50
    const descending = structuredClone(base)
    ;[descending.points[0], descending.points[1]] = [
      descending.points[1]!,
      descending.points[0]!,
    ]

    assert.throws(
      () => validateDataset(dataset([duplicate])),
      /duplicate tenor/,
    )
    assert.throws(() => validateDataset(dataset([missing])), /required tenors/)
    assert.throws(
      () => validateDataset(dataset([unsupported as CurveSnapshot])),
      /unsupported tenor/,
    )
    assert.throws(
      () => validateDataset(dataset([descending])),
      /strictly ascending/,
    )
  })

  test("rejects non-finite yields and invalid top-level metadata", () => {
    const infinite = structuredClone(snapshots[0]!)
    infinite.points[0]!.yieldPct = Number.POSITIVE_INFINITY
    assert.throws(
      () => validateDataset(dataset([infinite])),
      /finite number or null/,
    )
    assert.throws(
      () => validateDataset({ ...dataset(snapshots), currency: "USD" }),
      /currency must be JPY/,
    )
  })
})
