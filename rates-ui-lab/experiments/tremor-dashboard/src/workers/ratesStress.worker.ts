import {
  buildStressDataset,
  estimateStressBytes,
  sampleTenorSeries,
} from "../lib/rates/stress"

interface StressWorkerRequest {
  rowCount: number
}

interface WorkerScope {
  onmessage: ((event: MessageEvent<StressWorkerRequest>) => void) | null
  postMessage: (message: unknown, transfer: Transferable[]) => void
}

const workerScope = self as unknown as WorkerScope

workerScope.onmessage = ({ data }) => {
  const startedAt = performance.now()
  const dataset = buildStressDataset(data.rowCount)
  const series = sampleTenorSeries(dataset, 3, 600)
  const memoryBytes = estimateStressBytes(dataset)

  workerScope.postMessage(
    {
      type: "ready",
      rowCount: dataset.rowCount,
      durationMs: performance.now() - startedAt,
      memoryBytes,
      series,
      timestamps: dataset.timestamps.buffer,
      tenorIndexes: dataset.tenorIndexes.buffer,
      yields: dataset.yields.buffer,
      changesBp: dataset.changesBp.buffer,
    },
    [
      dataset.timestamps.buffer,
      dataset.tenorIndexes.buffer,
      dataset.yields.buffer,
      dataset.changesBp.buffer,
    ],
  )
}

export {}
