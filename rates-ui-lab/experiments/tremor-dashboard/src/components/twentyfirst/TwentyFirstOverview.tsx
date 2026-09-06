// UI composition adapted from the public 21st.dev Stats Bento pattern (MIT).
// No registry source code is bundled; see rates-ui-lab/docs/sources.md.
"use client"

import { formatBp, formatYield } from "@/lib/rates/metrics"
import type { buildRatesViewModel } from "@/lib/rates/view-model"
import { RiArrowRightUpLine, RiPulseLine } from "@remixicon/react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

type RatesView = ReturnType<typeof buildRatesViewModel>

function BentoCard({
  children,
  className = "",
  testId,
  tone = "default",
}: {
  children: React.ReactNode
  className?: string
  testId?: string
  tone?: "default" | "inverted"
}) {
  return (
    <section
      className={`overflow-hidden rounded-3xl border border-gray-200 shadow-sm dark:border-gray-800 ${
        tone === "inverted"
          ? "bg-gray-950 text-white dark:bg-white dark:text-gray-950"
          : "bg-white dark:bg-gray-950"
      } ${className}`}
      data-testid={testId}
    >
      {children}
    </section>
  )
}

export function TwentyFirstOverview({ model }: { model: RatesView }) {
  const tenYear = model.kpis.find((kpi) => kpi.id === "tenY")!
  const thirtyYear = model.kpis.find((kpi) => kpi.id === "thirtyY")!
  const twoTen = model.kpis.find((kpi) => kpi.id === "twoTen")!
  const fiveThirty = model.kpis.find((kpi) => kpi.id === "fiveThirty")!

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      <BentoCard className="relative p-6 md:col-span-2 md:row-span-2">
        <div className="absolute right-5 top-5 flex size-10 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-300">
          <RiPulseLine className="size-5" aria-hidden="true" />
        </div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gray-500 dark:text-gray-400">
          Headline rate
        </p>
        <h2 className="mt-8 text-sm font-medium text-gray-600 dark:text-gray-300">
          JGB 10Y
        </h2>
        <p
          className="mt-2 text-5xl font-semibold tabular-nums tracking-[-0.05em] text-gray-950 sm:text-6xl dark:text-white"
          data-testid="twentyfirst-kpi-tenY"
        >
          {formatYield(tenYear.value)}
        </p>
        <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
          前営業日比 <span className="font-semibold text-indigo-600 dark:text-indigo-400">{formatBp(tenYear.dayBp)}</span>
        </p>
        <div className="mt-8 h-40" role="img" aria-label="10Yの直近30観測日の推移">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={tenYear.history} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="twentyfirst-area" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="currentColor" stopOpacity={0.28} />
                  <stop offset="100%" stopColor="currentColor" stopOpacity={0} />
                </linearGradient>
              </defs>
              <YAxis hide domain={["dataMin - 0.03", "dataMax + 0.03"]} />
              <Area
                type="monotone"
                dataKey="value"
                stroke="currentColor"
                fill="url(#twentyfirst-area)"
                strokeWidth={2.5}
                className="text-indigo-600 dark:text-indigo-400"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">30 observations · synthetic</p>
      </BentoCard>

      <BentoCard className="p-5" testId="twentyfirst-kpi-twoTen">
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">2s10s</p>
        <p className="mt-6 text-3xl font-semibold tabular-nums tracking-tight text-gray-950 dark:text-white">
          {formatBp(twoTen.value)}
        </p>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">10Y − 2Y</p>
      </BentoCard>

      <BentoCard className="p-5" tone="inverted">
        <div className="flex items-start justify-between">
          <p className="text-sm font-medium text-gray-400 dark:text-gray-600">5s30s</p>
          <RiArrowRightUpLine className="size-4" aria-hidden="true" />
        </div>
        <p className="mt-6 text-3xl font-semibold tabular-nums tracking-tight">
          {formatBp(fiveThirty.value)}
        </p>
        <p className="mt-2 text-xs text-gray-400 dark:text-gray-600">30Y − 5Y</p>
      </BentoCard>

      <BentoCard className="p-5">
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">JGB 30Y</p>
        <p className="mt-6 text-3xl font-semibold tabular-nums tracking-tight text-gray-950 dark:text-white">
          {formatYield(thirtyYear.value)}
        </p>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
          前営業日比 {formatBp(thirtyYear.dayBp)}
        </p>
      </BentoCard>

      <BentoCard className="p-5">
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Curve range</p>
        <p className="mt-6 text-3xl font-semibold tabular-nums tracking-tight text-gray-950 dark:text-white">
          2Y–40Y
        </p>
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">7 standard tenors</p>
      </BentoCard>

      <BentoCard className="p-6 md:col-span-2 xl:col-span-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-gray-950 dark:text-white">JGB Yield Curve</h2>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {model.date} · 年限は数値間隔
            </p>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">yield %</p>
        </div>
        <div className="mt-6 h-72" data-testid="twentyfirst-yield-curve">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={model.points} margin={{ top: 10, right: 8, bottom: 5, left: 4 }} accessibilityLayer>
              <CartesianGrid vertical={false} stroke="currentColor" className="text-gray-100 dark:text-gray-800" />
              <XAxis
                type="number"
                dataKey="tenorYears"
                domain={[2, 40]}
                ticks={[2, 5, 7, 10, 20, 30, 40]}
                tickFormatter={(value) => `${value}Y`}
                tickLine={false}
                axisLine={false}
                fontSize={11}
                stroke="currentColor"
                className="text-gray-500"
              />
              <YAxis
                domain={["dataMin - 0.1", "dataMax + 0.1"]}
                tickFormatter={(value) => Number(value).toFixed(2)}
                tickLine={false}
                axisLine={false}
                width={44}
                fontSize={11}
                stroke="currentColor"
                className="text-gray-500"
              />
              <Tooltip
                formatter={(value) => [formatYield(Number(value)), "Yield"]}
                labelFormatter={(value) => `${value}Y`}
                contentStyle={{ borderRadius: 16, fontSize: 12 }}
              />
              <Line
                type="linear"
                dataKey="current"
                stroke="currentColor"
                className="text-indigo-600 dark:text-indigo-400"
                strokeWidth={3}
                dot={{ r: 4 }}
                isAnimationActive={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </BentoCard>
    </div>
  )
}
