import assert from "node:assert/strict"
import { describe, test } from "node:test"

import {
  buildStressDataset,
  estimateStressBytes,
  getVirtualRange,
  sampleTenorSeries,
} from "./stress.ts"

describe("massive rates dataset", () => {
  test("builds deterministic columnar data with one value per requested row", () => {
    const first = buildStressDataset(70)
    const second = buildStressDataset(70)

    assert.equal(first.rowCount, 70)
    assert.equal(first.timestamps.length, 70)
    assert.equal(first.tenorIndexes.length, 70)
    assert.equal(first.yields.length, 70)
    assert.equal(first.changesBp.length, 70)
    assert.deepEqual(Array.from(first.tenorIndexes.slice(0, 9)), [0, 1, 2, 3, 4, 5, 6, 0, 1])
    assert.deepEqual(Array.from(first.yields), Array.from(second.yields))
    assert.deepEqual(Array.from(first.changesBp), Array.from(second.changesBp))
  })

  test("reports the typed-array payload without counting object overhead", () => {
    const dataset = buildStressDataset(100)
    assert.equal(estimateStressBytes(dataset), 1_700)
  })

  test("samples the requested tenor to a bounded chart series", () => {
    const dataset = buildStressDataset(70_000)
    const series = sampleTenorSeries(dataset, 3, 600)

    assert.equal(series.length, 600)
    assert.equal(series[0]!.rowIndex % 7, 3)
    assert.equal(series.at(-1)!.rowIndex % 7, 3)
    assert.ok(series.every((point) => Number.isFinite(point.yieldPct)))
  })
})

describe("virtual table range", () => {
  test("renders only the viewport plus overscan and stays inside row bounds", () => {
    assert.deepEqual(getVirtualRange(0, 400, 36, 1_000_000, 5), {
      start: 0,
      end: 17,
    })
    assert.deepEqual(
      getVirtualRange(35_999_700, 400, 36, 1_000_000, 5),
      { start: 999_986, end: 1_000_000 },
    )
  })
})
