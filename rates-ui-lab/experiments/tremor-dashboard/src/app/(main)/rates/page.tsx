import { RatesDashboard } from "@/components/rates/RatesDashboard"
import type { Metadata } from "next"
import { Suspense } from "react"

export const metadata: Metadata = {
  title: "JGB Rates Analytics · Rates UI Lab",
  description:
    "JGB 仮データで Tremor のテンプレートと Blocks を比較するローカル UI 実験。",
}

export default function RatesPage() {
  return (
    <Suspense
      fallback={
        <p className="text-sm text-gray-500">金利データを読み込んでいます…</p>
      }
    >
      <RatesDashboard />
    </Suspense>
  )
}
