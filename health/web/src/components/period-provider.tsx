"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import type { Period } from "@/lib/types";
const PeriodContext = createContext<{
  period: Period;
  setPeriod: (p: Period) => void;
}>({ period: "90", setPeriod: () => {} });
export function PeriodProvider({ children }: { children: ReactNode }) {
  const [period, setPeriod] = useState<Period>("90");
  return (
    <PeriodContext value={{ period, setPeriod }}>{children}</PeriodContext>
  );
}
export const usePeriod = () => useContext(PeriodContext);
export function PeriodSelector() {
  const { period, setPeriod } = usePeriod();
  return (
    <label className="period-select">
      <span>表示期間</span>
      <select
        aria-label="表示期間"
        value={period}
        onChange={(e) => setPeriod(e.target.value as Period)}
      >
        {["30", "90", "180", "365", "all"].map((p) => (
          <option key={p} value={p}>
            {p === "all" ? "全期間" : `${p}日間`}
          </option>
        ))}
      </select>
    </label>
  );
}
