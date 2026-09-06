import { TENORS } from "./types.ts"

export const STRESS_ROW_OPTIONS = [10_000, 100_000, 1_000_000] as const
export type StressRowCount = (typeof STRESS_ROW_OPTIONS)[number]

const BASE_YIELDS = [0.92, 1.28, 1.54, 1.85, 2.34, 2.51, 2.63] as const
const START_TIME_MS = Date.UTC(2026, 8, 4, 0, 0, 0)

export interface StressDataset {
  rowCount: number
  timestamps: Float64Array
  tenorIndexes: Uint8Array
  yields: Float32Array
  changesBp: Float32Array
}

export interface StressSeriesPoint {
  rowIndex: number
  timestamp: number
  yieldPct: number
}

export interface VirtualRange {
  start: number
  end: number
}

function wave(observation: number, tenorIndex: number) {
  return (
    Math.sin(observation * 0.017 + tenorIndex * 0.31) * 0.018 +
    Math.sin(observation * 0.0019) * 0.012
  )
}

export function isStressRowCount(value: number): value is StressRowCount {
  return STRESS_ROW_OPTIONS.some((candidate) => candidate === value)
}

export function buildStressDataset(rowCount: number): StressDataset {
  if (!Number.isSafeInteger(rowCount) || rowCount < 1 || rowCount > 1_000_000) {
    throw new RangeError("rowCount must be an integer from 1 to 1,000,000")
  }

  const timestamps = new Float64Array(rowCount)
  const tenorIndexes = new Uint8Array(rowCount)
  const yields = new Float32Array(rowCount)
  const changesBp = new Float32Array(rowCount)

  for (let rowIndex = 0; rowIndex < rowCount; rowIndex += 1) {
    const tenorIndex = rowIndex % TENORS.length
    const observation = Math.floor(rowIndex / TENORS.length)
    const movement = wave(observation, tenorIndex)
    const previousMovement = wave(Math.max(0, observation - 1), tenorIndex)

    timestamps[rowIndex] = START_TIME_MS + observation * 60_000
    tenorIndexes[rowIndex] = tenorIndex
    yields[rowIndex] = BASE_YIELDS[tenorIndex]! + movement
    changesBp[rowIndex] = (movement - previousMovement) * 100
  }

  return { rowCount, timestamps, tenorIndexes, yields, changesBp }
}

export function estimateStressBytes(dataset: StressDataset) {
  return (
    dataset.timestamps.byteLength +
    dataset.tenorIndexes.byteLength +
    dataset.yields.byteLength +
    dataset.changesBp.byteLength
  )
}

export function sampleTenorSeries(
  dataset: StressDataset,
  tenorIndex: number,
  maxPoints: number,
): StressSeriesPoint[] {
  if (!Number.isInteger(tenorIndex) || tenorIndex < 0 || tenorIndex >= TENORS.length) {
    throw new RangeError("tenorIndex is outside the supported curve")
  }
  if (!Number.isSafeInteger(maxPoints) || maxPoints < 2) {
    throw new RangeError("maxPoints must be an integer of at least 2")
  }

  const available = Math.floor((dataset.rowCount - 1 - tenorIndex) / TENORS.length) + 1
  if (available <= 0) return []
  const sampleSize = Math.min(available, maxPoints)

  return Array.from({ length: sampleSize }, (_, sampleIndex) => {
    const observation =
      sampleSize === 1
        ? 0
        : Math.round((sampleIndex * (available - 1)) / (sampleSize - 1))
    const rowIndex = tenorIndex + observation * TENORS.length
    return {
      rowIndex,
      timestamp: dataset.timestamps[rowIndex]!,
      yieldPct: dataset.yields[rowIndex]!,
    }
  })
}

export function getVirtualRange(
  scrollTop: number,
  viewportHeight: number,
  rowHeight: number,
  rowCount: number,
  overscan: number,
): VirtualRange {
  const start = Math.max(0, Math.floor(scrollTop / rowHeight) - overscan)
  const end = Math.min(
    rowCount,
    Math.ceil((scrollTop + viewportHeight) / rowHeight) + overscan,
  )
  return { start, end }
}
