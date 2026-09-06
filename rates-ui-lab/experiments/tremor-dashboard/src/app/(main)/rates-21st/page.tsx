import { TwentyFirstDashboard } from "@/components/twentyfirst/TwentyFirstDashboard"
import type { Metadata } from "next"
import { Suspense } from "react"

export const metadata: Metadata = {
  title: "21st.dev + Meshyflix JGB Samples · Rates UI Lab",
  description:
    "Stats Bento、Prism、Meshyflix風の金利メッシュと最大100万行の合成データを試すローカル UI 実験。",
}

export default function Rates21stPage() {
  return (
    <Suspense
      fallback={
        <p className="text-sm text-gray-500">21st.dev sampleを読み込んでいます…</p>
      }
    >
      <TwentyFirstDashboard />
    </Suspense>
  )
}
