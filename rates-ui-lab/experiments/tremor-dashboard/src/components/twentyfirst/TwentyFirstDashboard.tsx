"use client"

import demo from "@/data/rates/jgb-demo.json"
import { formatBp } from "@/lib/rates/metrics"
import { validateDataset } from "@/lib/rates/metrics"
import { isStressRowCount, type StressRowCount } from "@/lib/rates/stress"
import { buildRatesViewModel } from "@/lib/rates/view-model"
import { cx, focusRing } from "@/lib/utils"
import { RiArrowRightUpLine } from "@remixicon/react"
import dynamic from "next/dynamic"
import { useRouter, useSearchParams } from "next/navigation"
import { MassiveDataLab } from "./MassiveDataLab"
import { TwentyFirstOverview } from "./TwentyFirstOverview"

const PrismRatesHero = dynamic(
  () => import("./PrismRatesHero").then((module) => module.PrismRatesHero),
  {
    ssr: false,
    loading: () => (
      <div className="-m-4 flex min-h-screen items-center justify-center bg-[#08080b] text-sm text-white/60 sm:-mx-6 sm:-mb-10 sm:-mt-10 lg:-mx-10 lg:-mt-7">
        Prism sceneを読み込んでいます…
      </div>
    ),
  },
)

const MeshyRatesStudio = dynamic(
  () => import("./MeshyRatesStudio").then(module => module.MeshyRatesStudio),
  {
    ssr: false,
    loading: () => <div className="flex min-h-screen items-center justify-center bg-gray-950 text-sm text-gray-300">Rates Mesh Studioを読み込んでいます…</div>,
  },
)

const dataset = validateDataset(demo)
const date = dataset.snapshots.at(-1)!.date
const comparisonDate = dataset.snapshots.at(-2)!.date
const model = buildRatesViewModel(dataset, date, comparisonDate)

export function TwentyFirstDashboard() {
  const params = useSearchParams()
  const router = useRouter()
  const requestedView = params.get("view")
  const view =
    requestedView === "massive"
      ? "massive"
      : requestedView === "prism"
        ? "prism"
        : requestedView === "meshy"
          ? "meshy"
          : "overview"
  const requestedRows = Number(params.get("rows"))
  const rowCount: StressRowCount = isStressRowCount(requestedRows)
    ? requestedRows
    : 100_000

  function update(nextView: "prism" | "meshy" | "overview" | "massive", rows = rowCount) {
    const query =
      nextView === "massive"
        ? `?view=massive&rows=${rows}`
        : nextView === "prism" || nextView === "meshy"
          ? `?view=${nextView}`
          : ""
    router.replace(`/rates-21st${query}`, { scroll: false })
  }

  if (view === "prism") return <PrismRatesHero model={model} />
  if (view === "meshy") return <MeshyRatesStudio />

  return (
    <div className="space-y-6 pb-5" lang="ja">
      <header className="flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-indigo-600 dark:text-indigo-400">21st.dev / Stats Bento study</p>
            <span className="rounded-full bg-amber-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-amber-800 ring-1 ring-inset ring-amber-200 dark:bg-amber-950 dark:text-amber-300 dark:ring-amber-900">synthetic data</span>
          </div>
          <h1 className="mt-3 text-3xl font-semibold tracking-[-0.04em] text-gray-950 sm:text-4xl dark:text-white">JGB Market Pulse</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-gray-500 dark:text-gray-400">
            同じJGBデータを、21st.devのBento構成で再配置。大量データ側では描画方式を切り替えて応答性を確認できます。
          </p>
        </div>
        <a
          href="https://21st.dev/@uilayout.contact/components/stats-bento"
          target="_blank"
          rel="noreferrer"
          aria-label="Stats Bento on 21st.dev"
          className={cx("inline-flex items-center gap-2 rounded-full border border-gray-200 bg-white px-4 py-2 text-xs font-semibold text-gray-700 shadow-sm hover:text-indigo-600 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300 dark:hover:text-indigo-400", focusRing)}
        >
          Source pattern
          <RiArrowRightUpLine className="size-4" aria-hidden="true" />
        </a>
      </header>

      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 dark:border-gray-800">
        <div className="flex flex-wrap gap-x-6 gap-y-3" role="group" aria-label="21st.dev 実験表示">
          {([
            { id: "prism", label: "Prism Hero" },
            { id: "meshy", label: "Meshyflix" },
            { id: "overview", label: "Market overview" },
            { id: "massive", label: "Massive data" },
          ] as const).map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={view === item.id}
              onClick={() => update(item.id)}
              className={cx(
                "-mb-px border-b-2 pb-3 text-sm font-semibold",
                focusRing,
                view === item.id
                  ? "border-gray-950 text-gray-950 dark:border-white dark:text-white"
                  : "border-transparent text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100",
              )}
            >
              {item.label}
            </button>
          ))}
        </div>
        <p className="pb-3 text-xs tabular-nums text-gray-500 dark:text-gray-400">
          as of {date} · 10Y day {formatBp(model.kpis[0]!.dayBp)}
        </p>
      </div>

      {view === "overview" ? (
        <TwentyFirstOverview model={model} />
      ) : (
        <MassiveDataLab
          rowCount={rowCount}
          onRowCount={(value) => update("massive", value)}
        />
      )}

      <footer className="border-t border-gray-200 pt-5 text-xs leading-5 text-gray-500 dark:border-gray-800 dark:text-gray-400">
        UI比較用の決定的な合成データです。100万行はファイル容量を増やさず、ブラウザ内で実行時生成します。
      </footer>
    </div>
  )
}
