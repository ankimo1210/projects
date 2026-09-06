// Date-field composition adapted from Tremor Blocks Filterbar 11;
// segmented comparison controls from Filterbar 4 (MIT).
import { Button } from "@/components/Button"
import { Label } from "@/components/Label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/Select"
import { cx, focusRing } from "@/lib/utils"
import type { LayoutVariant } from "./KpiCards"

type Props = {
  dates: string[]
  date: string
  comparisonDate: string
  layout: LayoutVariant
  onDate: (date: string) => void
  onComparison: (date: string) => void
}

export function DateField({
  label,
  value,
  dates,
  onChange,
}: {
  label: string
  value: string
  dates: string[]
  onChange: (value: string) => void
}) {
  const id = label === "基準日" ? "rates-date" : "rates-comparison"
  return (
    <div className="w-full min-w-0 space-y-2 sm:w-auto">
      <Label htmlFor={id}>{label}</Label>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger
          id={id}
          aria-label={label}
          className="w-full min-w-0 sm:w-44"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {dates.toReversed().map((date) => (
            <SelectItem value={date} key={date}>
              {date}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}

export function RatesFilters({
  dates,
  date,
  comparisonDate,
  layout,
  onDate,
  onComparison,
}: Props) {
  const index = dates.indexOf(date)
  return (
    <section
      aria-label="日付フィルター"
      className={cx(
        "flex flex-wrap items-end gap-4",
        layout === "blocks" &&
          "rounded-lg border border-gray-200 bg-gray-50/60 p-4 dark:border-gray-800 dark:bg-gray-900/30",
      )}
    >
      <DateField label="基準日" value={date} dates={dates} onChange={onDate} />
      <DateField
        label="比較日"
        value={comparisonDate}
        dates={dates}
        onChange={onComparison}
      />
      {layout === "blocks" && (
        <div className="space-y-2">
          <span className="block text-sm font-medium text-gray-900 dark:text-gray-50">
            比較日を選ぶ
          </span>
          <div
            className="inline-flex rounded-md shadow-sm"
            role="group"
            aria-label="比較期間のショートカット"
          >
            {[
              { label: "前営業日", lag: 1 },
              { label: "5営業日前", lag: 5 },
              { label: "20営業日前", lag: 20 },
            ].map((option, i) => {
              const target = dates[index - option.lag]
              const active = target !== undefined && target === comparisonDate
              return (
                <button
                  key={option.lag}
                  type="button"
                  disabled={!target}
                  aria-pressed={active}
                  onClick={() => target && onComparison(target)}
                  className={cx(
                    "relative border px-3 py-2 text-xs font-medium disabled:cursor-not-allowed disabled:opacity-40 sm:text-sm",
                    focusRing,
                    i === 0 ? "rounded-l-md" : "-ml-px",
                    i === 2 && "rounded-r-md",
                    active
                      ? "z-10 border-indigo-300 bg-indigo-50 text-indigo-700 dark:border-indigo-700 dark:bg-indigo-950 dark:text-indigo-300"
                      : "border-gray-300 bg-white text-gray-600 hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300",
                  )}
                >
                  {option.label}
                </button>
              )
            })}
          </div>
        </div>
      )}
      <Button
        variant="ghost"
        className="ml-auto text-xs"
        onClick={() => onDate(dates[dates.length - 1])}
      >
        最新の観測日に戻す
      </Button>
    </section>
  )
}
