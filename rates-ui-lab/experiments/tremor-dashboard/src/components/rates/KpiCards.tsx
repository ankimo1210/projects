// Adapted from Tremor Blocks KPI Cards 1 and 14 (MIT).
// See licenses/tremor-blocks-MIT.md and rates-ui-lab/docs/sources.md.
import { Card } from "@/components/Card"
import { SparkAreaChart } from "@/components/SparkChart"
import { formatBp, formatYield } from "@/lib/rates/metrics"
import type { buildRatesViewModel } from "@/lib/rates/view-model"
import { cx } from "@/lib/utils"

export type RatesView = ReturnType<typeof buildRatesViewModel>
export type LayoutVariant = "template" | "blocks"

export function moveColor(value: number | null) {
  if (value === null || Math.abs(value) < 0.05)
    return "text-gray-500 dark:text-gray-400"
  return value > 0
    ? "text-indigo-600 dark:text-indigo-400"
    : "text-amber-700 dark:text-amber-400"
}

export function KpiCards({
  kpis,
  layout,
}: {
  kpis: RatesView["kpis"]
  layout: LayoutVariant
}) {
  return (
    <dl
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4"
      aria-label="金利指標"
    >
      {kpis.map((kpi) => (
        <Card key={kpi.id} className="p-5" data-testid={`kpi-${kpi.id}`}>
          <dt className="flex items-center justify-between gap-2 text-sm font-medium text-gray-500 dark:text-gray-400">
            {kpi.label}
            <span className="text-xs font-normal">
              {kpi.unit === "%" ? "利回り" : "スプレッド"}
            </span>
          </dt>
          <dd
            className="mt-3 text-3xl font-semibold tabular-nums tracking-tight text-gray-900 dark:text-gray-50"
            data-testid="kpi-value"
          >
            {kpi.unit === "%" ? formatYield(kpi.value) : formatBp(kpi.value)}
          </dd>
          <dd className="mt-2 flex items-baseline gap-2 text-xs">
            <span
              className={cx("font-medium tabular-nums", moveColor(kpi.dayBp))}
              data-testid="kpi-day"
            >
              {formatBp(kpi.dayBp)}
            </span>
            <span className="text-gray-500 dark:text-gray-400">前営業日比</span>
          </dd>
          {layout === "blocks" && (
            <dd className="mt-4">
              <SparkAreaChart
                data={kpi.history}
                index="date"
                categories={["value"]}
                colors={["indigo"]}
                fill="gradient"
                autoMinValue
                connectNulls={false}
                className="h-12 w-full"
                aria-label={`${kpi.label} 選択日までの最大30観測日の推移`}
                role="img"
              />
              <span className="mt-2 block text-xs text-gray-500 dark:text-gray-400">
                直近 {kpi.history.length} 観測日
              </span>
            </dd>
          )}
        </Card>
      ))}
    </dl>
  )
}
