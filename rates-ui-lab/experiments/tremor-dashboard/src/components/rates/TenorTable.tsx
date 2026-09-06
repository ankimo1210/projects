import { Button } from "@/components/Button"
import { Card } from "@/components/Card"
import { formatBp, formatYield } from "@/lib/rates/metrics"
import type { TenorYears } from "@/lib/rates/types"
import { cx, focusRing } from "@/lib/utils"
import {
  RiArrowDownSLine,
  RiArrowUpSLine,
  RiExpandUpDownLine,
} from "@remixicon/react"
import { useState } from "react"
import { moveColor, type RatesView } from "./KpiCards"

type SortKey = "tenorYears" | "current" | "dayBp" | "weekBp"
const columns: { key: SortKey; label: string }[] = [
  { key: "tenorYears", label: "年限" },
  { key: "current", label: "利回り" },
  { key: "dayBp", label: "前営業日比" },
  { key: "weekBp", label: "5営業日前比" },
]
export function TenorTable({
  model,
  selectedTenor,
  onSelect,
}: {
  model: RatesView
  selectedTenor: TenorYears | null
  onSelect: (tenor: TenorYears | null) => void
}) {
  const [sort, setSort] = useState<{ key: SortKey; asc: boolean }>({
    key: "tenorYears",
    asc: true,
  })
  const rows = [...model.points].sort((a, b) => {
    const x = a[sort.key],
      y = b[sort.key]
    if (x === null) return y === null ? 0 : 1
    if (y === null) return -1
    return (x - y) * (sort.asc ? 1 : -1)
  })
  return (
    <Card className="min-w-0 p-0">
      <div className="flex items-center justify-between gap-4 px-5 py-5 sm:px-6">
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-50">
            Tenor Table
          </h2>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            年限を選ぶとチャートを強調表示
          </p>
        </div>
        {selectedTenor !== null && (
          <Button
            variant="ghost"
            className="text-xs"
            onClick={() => onSelect(null)}
          >
            {selectedTenor}Y 選択解除
          </Button>
        )}
      </div>
      <div
        className="overflow-x-auto"
        tabIndex={0}
        aria-label="年限別金利テーブルのスクロール領域"
      >
        <table
          className="w-full min-w-[520px] text-sm tabular-nums"
          aria-label="年限別金利"
        >
          <thead className="border-y border-gray-200 bg-gray-50/70 dark:border-gray-800 dark:bg-gray-900/40">
            <tr>
              {columns.map((column) => (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={
                    sort.key === column.key
                      ? sort.asc
                        ? "ascending"
                        : "descending"
                      : "none"
                  }
                  className={cx(
                    "px-5 py-3 font-medium text-gray-500 sm:px-6 dark:text-gray-400",
                    column.key === "tenorYears" ? "text-left" : "text-right",
                  )}
                >
                  <button
                    type="button"
                    className={cx(
                      "inline-flex items-center gap-1.5 rounded",
                      focusRing,
                    )}
                    onClick={() =>
                      setSort({
                        key: column.key,
                        asc:
                          sort.key === column.key
                            ? !sort.asc
                            : column.key === "tenorYears",
                      })
                    }
                  >
                    {column.label}
                    {sort.key !== column.key ? (
                      <RiExpandUpDownLine
                        className="size-3"
                        aria-hidden="true"
                      />
                    ) : sort.asc ? (
                      <RiArrowUpSLine className="size-3" aria-hidden="true" />
                    ) : (
                      <RiArrowDownSLine className="size-3" aria-hidden="true" />
                    )}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800/70">
            {rows.map((point) => (
              <tr
                key={point.tenorYears}
                data-testid={`tenor-row-${point.tenorYears}`}
                className={cx(
                  "transition-colors hover:bg-gray-50 dark:hover:bg-gray-900/40",
                  selectedTenor === point.tenorYears &&
                    "bg-indigo-50/60 dark:bg-indigo-950/30",
                )}
              >
                <th scope="row" className="px-5 py-3.5 text-left sm:px-6">
                  <button
                    type="button"
                    aria-pressed={selectedTenor === point.tenorYears}
                    aria-label={`${point.tenorYears}Yを強調`}
                    onClick={() =>
                      onSelect(
                        selectedTenor === point.tenorYears
                          ? null
                          : point.tenorYears,
                      )
                    }
                    className={cx(
                      "rounded font-medium text-gray-900 dark:text-gray-50",
                      focusRing,
                    )}
                  >
                    {point.tenorYears}Y{" "}
                    <span className="ml-2 font-normal text-gray-400">JGB</span>
                  </button>
                </th>
                <td className="px-5 py-3.5 text-right font-medium text-gray-900 sm:px-6 dark:text-gray-50">
                  {formatYield(point.current)}
                </td>
                <td
                  className={cx(
                    "px-5 py-3.5 text-right sm:px-6",
                    moveColor(point.dayBp),
                  )}
                >
                  {formatBp(point.dayBp)}
                </td>
                <td
                  className={cx(
                    "px-5 py-3.5 text-right sm:px-6",
                    moveColor(point.weekBp),
                  )}
                >
                  {formatBp(point.weekBp)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="border-t border-gray-100 px-5 py-3 text-xs text-gray-500 sm:px-6 dark:border-gray-800 dark:text-gray-400">
        前営業日 = 直前の観測日。比較データがない値は —。
      </p>
    </Card>
  )
}
