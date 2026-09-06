"use client"

import { Card } from "@/components/Card"
import { formatBp, formatYield } from "@/lib/rates/metrics"
import type { TenorYears } from "@/lib/rates/types"
import { cx, focusRing } from "@/lib/utils"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { moveColor, type RatesView } from "./KpiCards"

type ChartProps = { model: RatesView; selectedTenor: TenorYears | null }
export type VisibleCurves = { current: boolean; comparison: boolean }

function yieldDomain(points: RatesView["points"]): [number, number] {
  const values = points
    .flatMap((p) => [p.current, p.comparison])
    .filter((v): v is number => v !== null)
  if (!values.length) return [-0.1, 0.1]
  return [
    Math.floor((Math.min(...values) - 0.08) * 10) / 10,
    Math.ceil((Math.max(...values) + 0.08) * 10) / 10,
  ]
}

export function YieldCurve({
  model,
  selectedTenor,
  visible,
  onVisible,
}: ChartProps & {
  visible: VisibleCurves
  onVisible: (value: VisibleCurves) => void
}) {
  const selected = model.points.find(
    (point) => point.tenorYears === selectedTenor,
  )
  const domain = yieldDomain(model.points)
  return (
    <Card className="min-w-0 p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-50">
            JGB Yield Curve
          </h2>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            年限別利回り · %
          </p>
        </div>
        <div
          className="flex flex-wrap gap-3"
          role="group"
          aria-label="カーブの凡例"
        >
          {(["current", "comparison"] as const).map((key) => (
            <button
              key={key}
              type="button"
              aria-pressed={visible[key]}
              aria-label={`${key === "current" ? "基準日" : "比較日"}のカーブ`}
              onClick={() => onVisible({ ...visible, [key]: !visible[key] })}
              className={cx(
                "flex items-center gap-2 rounded text-xs text-gray-600 dark:text-gray-300",
                focusRing,
                !visible[key] && "opacity-40",
              )}
            >
              <span
                className={cx(
                  "h-0.5 w-4",
                  key === "current"
                    ? "bg-indigo-600 dark:bg-indigo-400"
                    : "bg-gray-400",
                )}
              />
              {key === "current" ? model.date : model.comparisonDate}
            </button>
          ))}
        </div>
      </div>
      <div
        className="mt-6 h-72 w-full"
        data-testid="yield-curve"
        data-domain={domain.join(",")}
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={model.points}
            margin={{ top: 10, right: 12, bottom: 5, left: 0 }}
            accessibilityLayer
          >
            <CartesianGrid
              vertical={false}
              stroke="currentColor"
              className="text-gray-100 dark:text-gray-800"
            />
            <XAxis
              type="number"
              dataKey="tenorYears"
              domain={[2, 40]}
              ticks={[2, 5, 7, 10, 20, 30, 40]}
              tickFormatter={(v) => `${v}Y`}
              minTickGap={12}
              tickLine={false}
              axisLine={false}
              fontSize={11}
              stroke="currentColor"
              className="text-gray-500"
              dy={8}
            />
            <YAxis
              type="number"
              domain={domain}
              tickFormatter={(v) => `${Number(v).toFixed(1)}`}
              tickLine={false}
              axisLine={false}
              fontSize={11}
              width={38}
              stroke="currentColor"
              className="text-gray-500"
            />
            <Tooltip
              filterNull={false}
              cursor={{
                stroke: "currentColor",
                className: "text-gray-300 dark:text-gray-600",
              }}
              content={({ active, label }) => {
                const point = model.points.find(
                  (p) => p.tenorYears === Number(label),
                )
                return active && point ? (
                  <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs shadow-lg dark:border-gray-800 dark:bg-gray-950">
                    <p className="mb-2 font-semibold text-gray-900 dark:text-gray-50">
                      {point.tenorYears}Y
                    </p>
                    {visible.current && (
                      <p className="text-indigo-600 dark:text-indigo-400">
                        {model.date} · {formatYield(point.current)}
                      </p>
                    )}
                    {visible.comparison && (
                      <p className="mt-1 text-gray-500 dark:text-gray-400">
                        {model.comparisonDate} · {formatYield(point.comparison)}
                      </p>
                    )}
                    <p className="mt-2 border-t border-gray-100 pt-2 text-gray-600 dark:border-gray-800 dark:text-gray-300">
                      変化幅 {formatBp(point.changeBp)}
                    </p>
                  </div>
                ) : null
              }}
            />
            <Line
              type="linear"
              dataKey="comparison"
              hide={!visible.comparison}
              stroke="currentColor"
              className="text-gray-400"
              strokeWidth={2}
              strokeDasharray="4 4"
              dot={{ r: 2 }}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Line
              type="linear"
              dataKey="current"
              hide={!visible.current}
              stroke="currentColor"
              className="text-indigo-600 dark:text-indigo-400"
              strokeWidth={2.5}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls={false}
              isAnimationActive={false}
            />
            {selected && selected.current !== null && visible.current && (
              <ReferenceDot
                x={selected.tenorYears}
                y={selected.current}
                r={6}
                fill="currentColor"
                stroke="currentColor"
                className="text-indigo-600 dark:text-indigo-400"
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
        横軸は年限の実間隔。点は観測値、線は直線接続。
      </p>
    </Card>
  )
}

export function CurveMove({ model, selectedTenor }: ChartProps) {
  const extent =
    Math.ceil(
      Math.max(
        1,
        ...model.points.map((point) => Math.abs(point.changeBp ?? 0)),
      ) *
        1.25 *
        2,
    ) / 2
  return (
    <Card className="min-w-0 p-5 sm:p-6">
      <h2 className="text-base font-semibold text-gray-900 dark:text-gray-50">
        Curve Move
      </h2>
      <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
        {model.date} − {model.comparisonDate} · bp
      </p>
      <div className="mt-6 h-72" data-testid="curve-move">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={model.points}
            margin={{ top: 10, right: 0, bottom: 5, left: 0 }}
            accessibilityLayer
          >
            <CartesianGrid
              vertical={false}
              stroke="currentColor"
              className="text-gray-100 dark:text-gray-800"
            />
            <XAxis
              dataKey="tenorYears"
              tickFormatter={(v) => `${v}Y`}
              tickLine={false}
              axisLine={false}
              fontSize={11}
              stroke="currentColor"
              className="text-gray-500"
              dy={8}
              interval={0}
            />
            <YAxis
              domain={[-extent, extent]}
              ticks={[-extent, -extent / 2, 0, extent / 2, extent]}
              tickFormatter={(v) => Number(v).toFixed(1)}
              tickLine={false}
              axisLine={false}
              fontSize={11}
              width={38}
              stroke="currentColor"
              className="text-gray-500"
            />
            <ReferenceLine
              y={0}
              stroke="currentColor"
              className="text-gray-300 dark:text-gray-600"
            />
            <Tooltip
              filterNull={false}
              cursor={{
                fill: "currentColor",
                className: "text-gray-100 dark:text-gray-900",
              }}
              content={({ active, payload }) => {
                const point = payload?.[0]?.payload as
                  | RatesView["points"][number]
                  | undefined
                return active && point ? (
                  <div className="rounded-lg border border-gray-200 bg-white p-3 text-xs shadow-lg dark:border-gray-800 dark:bg-gray-950">
                    <p className="font-semibold text-gray-900 dark:text-gray-50">
                      {point.tenorYears}Y
                    </p>
                    <p className={cx("mt-1", moveColor(point.changeBp))}>
                      {formatBp(point.changeBp)}
                    </p>
                  </div>
                ) : null
              }}
            />
            <Bar
              dataKey="changeBp"
              fill="currentColor"
              maxBarSize={28}
              radius={[3, 3, 0, 0]}
              isAnimationActive={false}
            >
              {model.points.map((point) => (
                <Cell
                  key={point.tenorYears}
                  className={moveColor(point.changeBp)}
                  fill="currentColor"
                  fillOpacity={
                    selectedTenor && selectedTenor !== point.tenorYears
                      ? 0.3
                      : 0.85
                  }
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
        ＋ 上昇 / − 低下 · 1 bp = 0.01%
      </p>
    </Card>
  )
}
