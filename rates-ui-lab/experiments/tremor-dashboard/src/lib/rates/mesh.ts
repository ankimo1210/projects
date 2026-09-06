import type { RatesDataset } from "./types.ts"

// Fixed scale across all demo cases: x = tenor years, y = yield %, z = calendar date.
export function buildRatesMesh(dataset: RatesDataset) {
  const positions: number[] = []
  const colors: number[] = []
  const indices: number[] = []
  const rows: number[][] = []
  const firstDate = Date.parse(dataset.snapshots[0].date)
  const dateSpan = Math.max(1, Date.parse(dataset.snapshots.at(-1)!.date) - firstDate)
  let missingCount = 0

  for (const snapshot of dataset.snapshots) {
    const row: number[] = []
    for (const point of snapshot.points) {
      if (point.yieldPct === null) {
        row.push(-1)
        missingCount++
        continue
      }
      row.push(positions.length / 3)
      positions.push(
        ((point.tenorYears - 21) / 38) * 7.6,
        (point.yieldPct - 1.25) * 1.7,
        2.75 - ((Date.parse(snapshot.date) - firstDate) / dateSpan) * 5.5,
      )
      const t = Math.max(0, Math.min(1, (point.yieldPct + 0.5) / 3.5))
      colors.push(0.12 + t * 0.68, 0.55 + t * 0.4, 0.58 - t * 0.43)
    }
    rows.push(row)
  }

  for (let row = 0; row < rows.length - 1; row++) {
    for (let col = 0; col < rows[row].length - 1; col++) {
      const a = rows[row][col]
      const b = rows[row][col + 1]
      const c = rows[row + 1][col]
      const d = rows[row + 1][col + 1]
      // Require all four corners: never interpolate a surface across missing data.
      if ([a, b, c, d].every(index => index !== undefined && index >= 0)) {
        indices.push(a, b, c, b, d, c)
      }
    }
  }
  return {
    positions: new Float32Array(positions),
    colors: new Float32Array(colors),
    indices: new Uint32Array(indices),
    vertexCount: positions.length / 3,
    triangleCount: indices.length / 3,
    missingCount,
  }
}

export type RatesMeshData = ReturnType<typeof buildRatesMesh>

export function ratesCsv(dataset: RatesDataset) {
  return "date,tenor_years,yield_pct\n" + dataset.snapshots.flatMap(snapshot =>
    snapshot.points.map(point => `${snapshot.date},${point.tenorYears},${point.yieldPct ?? ""}\n`),
  ).join("")
}
