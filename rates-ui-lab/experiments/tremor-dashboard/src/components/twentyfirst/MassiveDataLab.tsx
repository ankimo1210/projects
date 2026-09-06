"use client"

import { formatBp } from "@/lib/rates/metrics"
import {
  STRESS_ROW_OPTIONS,
  getVirtualRange,
  type StressDataset,
  type StressRowCount,
  type StressSeriesPoint,
} from "@/lib/rates/stress"
import { TENORS } from "@/lib/rates/types"
import { cx, focusRing } from "@/lib/utils"
import { RiCpuLine, RiDatabase2Line, RiFlashlightLine, RiListCheck3 } from "@remixicon/react"
import { useEffect, useMemo, useRef, useState } from "react"
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

interface StressWorkerResponse {
  type: "ready"
  rowCount: number
  durationMs: number
  memoryBytes: number
  series: StressSeriesPoint[]
  timestamps: ArrayBuffer
  tenorIndexes: ArrayBuffer
  yields: ArrayBuffer
  changesBp: ArrayBuffer
}

interface LoadedStressData {
  dataset: StressDataset
  durationMs: number
  memoryBytes: number
  series: StressSeriesPoint[]
}

const numberFormat = new Intl.NumberFormat("ja-JP")
const compactNumber = new Intl.NumberFormat("ja-JP", { notation: "compact" })
const timeFormat = new Intl.DateTimeFormat("ja-JP", {
  year: "2-digit",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Asia/Tokyo",
})
const ROW_HEIGHT = 32
const VIEWPORT_HEIGHT = 416

function Metric({
  label,
  value,
  note,
  icon: Icon,
  testId,
}: {
  label: string
  value: string
  note: string
  icon: typeof RiCpuLine
  testId?: string
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-950">
      <div className="flex items-center justify-between text-gray-500 dark:text-gray-400">
        <p className="text-xs font-medium">{label}</p>
        <Icon className="size-4" aria-hidden="true" />
      </div>
      <p
        className="mt-3 text-2xl font-semibold tabular-nums tracking-tight text-gray-950 dark:text-white"
        data-testid={testId}
      >
        {value}
      </p>
      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{note}</p>
    </div>
  )
}

function VirtualRatesTable({ data }: { data: LoadedStressData }) {
  const viewportRef = useRef<HTMLDivElement>(null)
  const frameRef = useRef<number | null>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const range = getVirtualRange(
    scrollTop,
    VIEWPORT_HEIGHT,
    ROW_HEIGHT,
    data.dataset.rowCount,
    6,
  )
  const indexes = useMemo(
    () => Array.from({ length: range.end - range.start }, (_, offset) => range.start + offset),
    [range.end, range.start],
  )

  useEffect(() => {
    const viewport = viewportRef.current
    if (viewport) viewport.scrollTop = 0
    setScrollTop(0)
  }, [data.dataset])

  useEffect(
    () => () => {
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
    },
    [],
  )

  function onScroll() {
    if (frameRef.current !== null) return
    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null
      setScrollTop(viewportRef.current?.scrollTop ?? 0)
    })
  }

  function jumpToMiddle() {
    if (!viewportRef.current) return
    viewportRef.current.scrollTop = Math.floor(data.dataset.rowCount / 2) * ROW_HEIGHT
    setScrollTop(viewportRef.current.scrollTop)
  }

  return (
    <section className="overflow-hidden rounded-3xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-950">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 px-5 py-4 dark:border-gray-800">
        <div>
          <h2 className="font-semibold text-gray-950 dark:text-white">Virtualized rate tape</h2>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            全行を保持し、画面付近だけDOMへ描画
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
          <span>
            visible <strong className="tabular-nums text-gray-950 dark:text-white" data-testid="stress-visible-range">
              {numberFormat.format(range.start + 1)}–{numberFormat.format(range.end)}
            </strong>
          </span>
          <button
            type="button"
            onClick={jumpToMiddle}
            className={cx(
              "rounded-full bg-gray-950 px-3 py-1.5 font-medium text-white hover:bg-gray-800 dark:bg-white dark:text-gray-950 dark:hover:bg-gray-200",
              focusRing,
            )}
          >
            50%地点へ移動
          </button>
        </div>
      </div>
      <div className="overflow-x-auto" data-testid="stress-table">
        <div className="min-w-[720px]">
          <div className="grid h-9 grid-cols-[170px_80px_120px_110px_1fr] items-center gap-3 border-b border-gray-200 bg-gray-50 px-4 text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-400" role="row">
            <span>Timestamp (JST)</span>
            <span>Tenor</span>
            <span className="text-right">Yield</span>
            <span className="text-right">Move</span>
            <span>Record ID</span>
          </div>
          <div
            ref={viewportRef}
            onScroll={onScroll}
            className="relative overflow-y-auto overscroll-contain"
            style={{ height: VIEWPORT_HEIGHT }}
            role="table"
            aria-label="大量の合成金利レコード"
            aria-rowcount={data.dataset.rowCount}
          >
            <div style={{ height: data.dataset.rowCount * ROW_HEIGHT }} aria-hidden="true" />
            {indexes.map((rowIndex) => {
              const tenor = TENORS[data.dataset.tenorIndexes[rowIndex]!]!
              const change = data.dataset.changesBp[rowIndex]!
              return (
                <div
                  key={rowIndex}
                  role="row"
                  aria-rowindex={rowIndex + 1}
                  className="absolute left-0 right-0 top-0 grid grid-cols-[170px_80px_120px_110px_1fr] items-center gap-3 border-b border-gray-100 px-4 text-xs text-gray-600 dark:border-gray-900 dark:text-gray-300"
                  style={{ height: ROW_HEIGHT, transform: `translateY(${rowIndex * ROW_HEIGHT}px)` }}
                >
                  <span className="tabular-nums">{timeFormat.format(data.dataset.timestamps[rowIndex]!)}</span>
                  <span className="font-semibold text-gray-950 dark:text-white">{tenor}Y</span>
                  <span className="text-right font-medium tabular-nums text-gray-950 dark:text-white">
                    {data.dataset.yields[rowIndex]!.toFixed(3)}%
                  </span>
                  <span className={cx("text-right tabular-nums", change >= 0 ? "text-indigo-600 dark:text-indigo-400" : "text-amber-700 dark:text-amber-400")}>
                    {formatBp(change)}
                  </span>
                  <span className="font-mono text-[11px] text-gray-500">JGB-{tenor}Y-{String(rowIndex + 1).padStart(7, "0")}</span>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </section>
  )
}

export function MassiveDataLab({
  rowCount,
  onRowCount,
}: {
  rowCount: StressRowCount
  onRowCount: (value: StressRowCount) => void
}) {
  const [loaded, setLoaded] = useState<LoadedStressData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoaded(null)
    setError(null)
    const worker = new Worker(
      new URL("../../workers/ratesStress.worker.ts", import.meta.url),
      { type: "module" },
    )
    worker.onmessage = ({ data }: MessageEvent<StressWorkerResponse>) => {
      setLoaded({
        durationMs: data.durationMs,
        memoryBytes: data.memoryBytes,
        series: data.series,
        dataset: {
          rowCount: data.rowCount,
          timestamps: new Float64Array(data.timestamps),
          tenorIndexes: new Uint8Array(data.tenorIndexes),
          yields: new Float32Array(data.yields),
          changesBp: new Float32Array(data.changesBp),
        },
      })
    }
    worker.onerror = () => setError("データ生成に失敗しました")
    worker.postMessage({ rowCount })
    return () => worker.terminate()
  }, [rowCount])

  const status = error
    ? error
    : loaded
      ? `${numberFormat.format(loaded.dataset.rowCount)} rows ready`
      : `${numberFormat.format(rowCount)} rows generating…`
  const domRows = loaded
    ? getVirtualRange(0, VIEWPORT_HEIGHT, ROW_HEIGHT, loaded.dataset.rowCount, 6).end
    : 0

  return (
    <div className="space-y-4">
      <section className="rounded-3xl bg-gray-950 p-5 text-white shadow-sm dark:bg-white dark:text-gray-950">
        <div className="flex flex-wrap items-center justify-between gap-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-400 dark:text-gray-600">Stress profile</p>
            <h2 className="mt-2 text-xl font-semibold">Columnar data + Web Worker + virtual rows</h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-400 dark:text-gray-600">
              合成レコードをブラウザ内の別スレッドで生成。チャートは10Yを最大600点に間引き、表は画面付近だけを描画します。
            </p>
          </div>
          <div className="flex rounded-full bg-white/10 p-1 dark:bg-gray-950/10" role="group" aria-label="大量データの行数">
            {STRESS_ROW_OPTIONS.map((value) => (
              <button
                key={value}
                type="button"
                aria-pressed={rowCount === value}
                onClick={() => onRowCount(value)}
                className={cx(
                  "rounded-full px-3 py-2 text-xs font-semibold transition",
                  focusRing,
                  rowCount === value
                    ? "bg-white text-gray-950 shadow-sm dark:bg-gray-950 dark:text-white"
                    : "text-gray-300 hover:text-white dark:text-gray-700 dark:hover:text-gray-950",
                )}
              >
                {compactNumber.format(value)}
              </button>
            ))}
          </div>
        </div>
        <p className="mt-5 text-xs font-medium tabular-nums text-emerald-300 dark:text-emerald-700" data-testid="stress-status" aria-live="polite">
          {status}
        </p>
      </section>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Metric label="Rows in memory" value={loaded ? numberFormat.format(loaded.dataset.rowCount) : "—"} note="all synthetic records" icon={RiDatabase2Line} testId="stress-row-count" />
        <Metric label="Worker generation" value={loaded ? `${loaded.durationMs.toFixed(1)} ms` : "—"} note="measured in this browser" icon={RiCpuLine} />
        <Metric label="Typed payload" value={loaded ? `${(loaded.memoryBytes / 1024 / 1024).toFixed(1)} MiB` : "—"} note="17 bytes per row" icon={RiFlashlightLine} />
        <Metric label="Initial DOM rows" value={loaded ? String(domRows) : "—"} note="independent of total rows" icon={RiListCheck3} testId="stress-dom-count" />
      </div>

      {loaded && (
        <section className="rounded-3xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-gray-950">
          <div className="flex flex-wrap items-end justify-between gap-2">
            <div>
              <h2 className="font-semibold text-gray-950 dark:text-white">10Y sampled series</h2>
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{numberFormat.format(Math.ceil(loaded.dataset.rowCount / 7))} observations → {loaded.series.length} chart points</p>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">yield %</p>
          </div>
          <div className="mt-5 h-48">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={loaded.series} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="stress-area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="currentColor" stopOpacity={0.24} />
                    <stop offset="100%" stopColor="currentColor" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="rowIndex" hide />
                <YAxis hide domain={["dataMin - 0.01", "dataMax + 0.01"]} />
                <Tooltip
                  formatter={(value) => [`${Number(value).toFixed(3)}%`, "10Y"]}
                  labelFormatter={(_, payload) => payload[0] ? `row ${numberFormat.format(payload[0].payload.rowIndex + 1)}` : ""}
                  contentStyle={{ borderRadius: 16, fontSize: 12 }}
                />
                <Area
                  type="monotone"
                  dataKey="yieldPct"
                  stroke="currentColor"
                  fill="url(#stress-area)"
                  strokeWidth={2}
                  className="text-indigo-600 dark:text-indigo-400"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      {loaded && <VirtualRatesTable data={loaded} />}
    </div>
  )
}
