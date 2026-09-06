import assert from "node:assert/strict"
import { describe, test } from "node:test"

import { TENORS, type CurveSnapshot, type RatesDataset } from "./types.ts"
import { buildRatesViewModel } from "./view-model.ts"

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

const assertClose = (actual: number | null | undefined, expected: number) => {
  assert.notEqual(actual, null)
  assert.notEqual(actual, undefined)
  assert.ok(Math.abs((actual as number) - expected) < 1e-12)
}

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

describe("rates view model", () => {
  test("builds tenor rows with selected, comparison, day, and five-observation changes", () => {
    const model = buildRatesViewModel(
      dataset(snapshots),
      "2026-09-04",
      "2026-08-27",
    )
    const tenYear = model.points.find((point) => point.tenorYears === 10)

    assert.equal(tenYear?.tenorYears, 10)
    assert.equal(tenYear?.current, 1.85)
    assert.equal(tenYear?.comparison, 1.8)
    assertClose(tenYear?.changeBp, 5)
    assertClose(tenYear?.dayBp, 2)
    assertClose(tenYear?.weekBp, 4)
  })

  test("builds level and spread KPIs with the correct units and spread day differences", () => {
    const model = buildRatesViewModel(
      dataset(snapshots),
      "2026-09-04",
      "2026-08-27",
    )

    const tenY = model.kpis.find((kpi) => kpi.id === "tenY")
    const thirtyY = model.kpis.find((kpi) => kpi.id === "thirtyY")
    const twoTen = model.kpis.find((kpi) => kpi.id === "twoTen")
    const fiveThirty = model.kpis.find((kpi) => kpi.id === "fiveThirty")

    assert.deepEqual(
      model.kpis.map(({ id, label, unit }) => ({ id, label, unit })),
      [
        { id: "tenY", label: "10Y", unit: "%" },
        { id: "thirtyY", label: "30Y", unit: "%" },
        { id: "twoTen", label: "2s10s", unit: "bp" },
        { id: "fiveThirty", label: "5s30s", unit: "bp" },
      ],
    )
    assert.equal(tenY?.value, 1.85)
    assertClose(tenY?.dayBp, 2)
    assert.equal(thirtyY?.value, 2.51)
    assertClose(thirtyY?.dayBp, 1)
    assertClose(twoTen?.value, 93)
    assertClose(twoTen?.dayBp, 1.5)
    assertClose(fiveThirty?.value, 123)
    assertClose(fiveThirty?.dayBp, 0)
  })

  test("propagates null through point changes, KPI values, and spread histories", () => {
    const missingSnapshots: CurveSnapshot[] = [
      {
        date: "2026-09-03",
        points: points([0.9, 1.2, 1.4, 1.8, 2.2, 2.4, 2.5]),
      },
      {
        date: "2026-09-04",
        points: points([0.91, 1.21, 1.41, null, 2.21, 2.41, 2.51]),
      },
    ]
    const model = buildRatesViewModel(
      dataset(missingSnapshots),
      "2026-09-04",
      "2026-09-03",
    )

    assert.deepEqual(
      model.points.find((point) => point.tenorYears === 10),
      {
        tenorYears: 10,
        current: null,
        comparison: 1.8,
        changeBp: null,
        dayBp: null,
        weekBp: null,
      },
    )
    assert.equal(model.kpis.find((kpi) => kpi.id === "tenY")?.value, null)
    assert.equal(model.kpis.find((kpi) => kpi.id === "twoTen")?.dayBp, null)
    assert.deepEqual(model.kpis.find((kpi) => kpi.id === "twoTen")?.history, [
      { date: "2026-09-03", value: 90 },
      { date: "2026-09-04", value: null },
    ])
  })

  test("preserves negative levels and zero spreads for a flat curve", () => {
    const values: CurveSnapshot[] = [
      {
        date: "2026-09-03",
        points: points([-0.2, -0.2, -0.2, -0.2, -0.2, -0.2, -0.2]),
      },
      {
        date: "2026-09-04",
        points: points([-0.1, -0.1, -0.1, -0.1, -0.1, -0.1, -0.1]),
      },
    ]
    const model = buildRatesViewModel(
      dataset(values),
      "2026-09-04",
      "2026-09-03",
    )

    assert.equal(model.kpis.find((kpi) => kpi.id === "tenY")?.value, -0.1)
    assert.equal(model.kpis.find((kpi) => kpi.id === "twoTen")?.value, 0)
    assert.equal(model.kpis.find((kpi) => kpi.id === "twoTen")?.dayBp, 0)
  })

  test("limits KPI histories to the last 30 observations through the selected date", () => {
    const manySnapshots: CurveSnapshot[] = Array.from(
      { length: 35 },
      (_, index) => {
        const date = new Date(Date.UTC(2026, 7, index + 1))
          .toISOString()
          .slice(0, 10)
        return { date, points: points([0.9, 1.2, 1.4, 1.8, 2.2, 2.4, 2.5]) }
      },
    )
    const model = buildRatesViewModel(
      dataset(manySnapshots),
      "2026-09-04",
      "2026-08-01",
    )

    for (const kpi of model.kpis) {
      assert.equal(kpi.history.length, 30)
      assert.equal(kpi.history[0]?.date, "2026-08-06")
      assert.equal(kpi.history.at(-1)?.date, "2026-09-04")
    }
  })

  test("rejects selected or comparison dates that are not observations", () => {
    const value = dataset(snapshots)
    assert.throws(
      () => buildRatesViewModel(value, "2026-09-05", "2026-08-27"),
      /Selected date 2026-09-05 is not an observation/,
    )
    assert.throws(
      () => buildRatesViewModel(value, "2026-09-04", "2026-08-30"),
      /Comparison date 2026-08-30 is not an observation/,
    )
  })
})
