"use client"

import { Button } from "@/components/Button"
import { Label } from "@/components/Label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/Select"
import demo from "@/data/rates/jgb-demo.json"
import flat from "@/data/rates/jgb-demo-flat.json"
import missing from "@/data/rates/jgb-demo-missing.json"
import negative from "@/data/rates/jgb-demo-negative.json"
import { validateDataset } from "@/lib/rates/metrics"
import type { TenorYears } from "@/lib/rates/types"
import { buildRatesViewModel } from "@/lib/rates/view-model"
import { cx, focusRing } from "@/lib/utils"
import { RiMoonLine, RiSunLine } from "@remixicon/react"
import { useTheme } from "next-themes"
import { useRouter, useSearchParams } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import { KpiCards, type LayoutVariant } from "./KpiCards"
import { CurveMove, YieldCurve, type VisibleCurves } from "./RatesCharts"
import { RatesFilters } from "./RatesFilters"
import { TenorTable } from "./TenorTable"

const datasets = {
  standard: validateDataset(demo),
  missing: validateDataset(missing),
  negative: validateDataset(negative),
  flat: validateDataset(flat),
}
const cases = [
  { id: "standard", label: "標準のカーブ" },
  { id: "missing", label: "欠損のあるカーブ" },
  { id: "negative", label: "負金利のカーブ" },
  { id: "flat", label: "フラットなカーブ" },
] as const

export function RatesDashboard() {
  const params = useSearchParams()
  const router = useRouter()
  const layout: LayoutVariant =
    params.get("layout") === "blocks" ? "blocks" : "template"
  const caseName = params.get("case") || "standard"
  const dataset = Object.hasOwn(datasets, caseName)
    ? datasets[caseName as keyof typeof datasets]
    : datasets.standard
  const dates = useMemo(() => dataset.snapshots.map((s) => s.date), [dataset])
  const date = dates.includes(params.get("date") || "")
    ? params.get("date")!
    : dates[dates.length - 1]
  const defaultComparison = dates[Math.max(0, dates.indexOf(date) - 1)]
  const comparisonDate = dates.includes(params.get("compare") || "")
    ? params.get("compare")!
    : defaultComparison
  const model = useMemo(
    () => buildRatesViewModel(dataset, date, comparisonDate),
    [dataset, date, comparisonDate],
  )
  const [selectedTenor, setSelectedTenor] = useState<TenorYears | null>(null)
  const [visible, setVisible] = useState<VisibleCurves>({
    current: true,
    comparison: true,
  })
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  function update(values: Record<string, string>) {
    const next = new URLSearchParams(params.toString())
    Object.entries(values).forEach(([key, value]) => next.set(key, value))
    router.replace(`/rates?${next.toString()}`, { scroll: false })
  }
  function onDate(value: string) {
    update({
      date: value,
      compare: dates[Math.max(0, dates.indexOf(value) - 1)],
    })
  }
  const isDark = mounted && resolvedTheme === "dark"
  return (
    <div className="space-y-6 pb-4" lang="ja">
      <header>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-xs font-medium tracking-wider text-gray-500 dark:text-gray-400">
              RATES / JPY
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <h1 className="text-xl font-semibold tracking-tight text-gray-900 sm:text-2xl dark:text-gray-50">
                JGB Rates Analytics
              </h1>
              <span className="rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-800 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300">
                DEMO / 仮データ
              </span>
            </div>
            <p
              className="mt-2 text-xs text-gray-500 dark:text-gray-400"
              data-testid="as-of"
            >
              基準日 {date} · 比較日 {comparisonDate}
            </p>
          </div>
          <Button
            variant="secondary"
            aria-label={
              isDark ? "ライトモードに切り替え" : "ダークモードに切り替え"
            }
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className="gap-2"
          >
            {isDark ? (
              <RiSunLine className="size-4" />
            ) : (
              <RiMoonLine className="size-4" />
            )}
            <span>{isDark ? "Light" : "Dark"}</span>
          </Button>
        </div>
        <div className="mt-6 flex items-end justify-between gap-3 border-b border-gray-200 dark:border-gray-800">
          <div
            role="group"
            aria-label="レイアウトを比較"
            className="flex gap-5 sm:gap-7"
          >
            {(
              [
                { id: "template", label: "Template", note: "数値中心" },
                { id: "blocks", label: "Blocks", note: "推移付き" },
              ] as const
            ).map((item) => (
              <button
                key={item.id}
                type="button"
                aria-pressed={layout === item.id}
                onClick={() => update({ layout: item.id })}
                className={cx(
                  "-mb-px border-b-2 pb-3 text-sm font-medium",
                  focusRing,
                  layout === item.id
                    ? "border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400"
                    : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200",
                )}
              >
                {item.label}
                <span className="ml-2 hidden text-xs font-normal sm:inline">
                  {item.note}
                </span>
              </button>
            ))}
          </div>
          <span className="mb-3 text-xs text-gray-400 dark:text-gray-500">
            同じデータで比較
          </span>
        </div>
      </header>
      <RatesFilters
        dates={dates}
        date={date}
        comparisonDate={comparisonDate}
        layout={layout}
        onDate={onDate}
        onComparison={(value) => update({ compare: value })}
      />
      <KpiCards kpis={model.kpis} layout={layout} />
      <div className="grid min-w-0 grid-cols-1 gap-4 xl:grid-cols-[1.65fr_1fr]">
        <YieldCurve
          model={model}
          selectedTenor={selectedTenor}
          visible={visible}
          onVisible={setVisible}
        />
        <CurveMove model={model} selectedTenor={selectedTenor} />
      </div>
      <TenorTable
        model={model}
        selectedTenor={selectedTenor}
        onSelect={setSelectedTenor}
      />
      <footer className="flex flex-wrap items-end justify-between gap-5 border-t border-gray-200 pt-5 dark:border-gray-800">
        <div className="max-w-xl text-xs leading-6 text-gray-500 dark:text-gray-400">
          <p>{dataset.sourceLabel}</p>
          <p>
            合成の観測日を使用。市場の営業日・休場日を再現するものではありません。
          </p>
          <p>変化幅の色は金利の上昇・低下を表します。</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="rates-case">仮データのケース</Label>
          <Select
            value={Object.hasOwn(datasets, caseName) ? caseName : "standard"}
            onValueChange={(value) => update({ case: value })}
          >
            <SelectTrigger
              id="rates-case"
              aria-label="仮データのケース"
              className="w-52"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {cases.map((item) => (
                <SelectItem key={item.id} value={item.id}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </footer>
    </div>
  )
}
