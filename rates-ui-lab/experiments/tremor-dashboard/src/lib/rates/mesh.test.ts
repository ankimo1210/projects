import assert from "node:assert/strict"
import { describe, it } from "node:test"
import { buildRatesMesh, ratesCsv } from "./mesh.ts"
import type { RatesDataset } from "./types.ts"

const fixture = (missing = false): RatesDataset => ({
  schemaVersion: 1, dataKind: "synthetic", currency: "JPY", curve: "JGB", sourceLabel: "test",
  snapshots: ["2026-09-03", "2026-09-04", "2026-09-07"].map((date, day) => ({
    date,
    points: [
      { tenorYears: 2, yieldPct: -0.2 },
      { tenorYears: 5, yieldPct: missing && day === 1 ? null : 0.1 },
      { tenorYears: 10, yieldPct: 0.6 },
    ],
  })),
})

describe("rates mesh data", () => {
  it("preserves tenor and calendar-day spacing and negative yields", () => {
    const mesh = buildRatesMesh(fixture())
    assert.equal(mesh.vertexCount, 9)
    assert.equal(mesh.triangleCount, 8)
    const p = mesh.positions
    assert.ok(Math.abs((p[6] - p[3]) / (p[3] - p[0]) - 5 / 3) < 1e-5)
    assert.ok(Math.abs((p[20] - p[11]) / (p[11] - p[2]) - 3) < 1e-5)
    assert.ok(p[1] < (0 - 1.25) * 1.7)
    assert.equal(mesh.missingCount, 0)
  })

  it("removes missing vertices and all touching cells instead of bridging holes", () => {
    const mesh = buildRatesMesh(fixture(true))
    assert.equal(mesh.vertexCount, 8)
    assert.equal(mesh.missingCount, 1)
    assert.equal(mesh.triangleCount, 0)
    assert.ok(Array.from(mesh.positions).every(Number.isFinite))
  })

  it("exports every observation with a blank for a missing yield", () => {
    const csv = ratesCsv(fixture(true))
    assert.equal(csv.trimEnd().split("\n").length, 10)
    assert.ok(csv.startsWith("date,tenor_years,yield_pct\n"))
    assert.ok(csv.includes("2026-09-04,5,\n"))
    assert.ok(csv.includes("2026-09-03,2,-0.2\n"))
  })
})
