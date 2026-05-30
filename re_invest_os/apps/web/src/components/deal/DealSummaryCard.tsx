/**
 * Deal Workspace の最上段サマリーカード。
 * 最新 analysis_run の主要 KPI を表示。
 */
import { KpiCell, Panel } from "../bloomberg";

interface RunMetrics {
  analysis?: {
    kpi?: {
      cap_rate?: number;
      dscr_year1?: number;
      dscr_min?: number;
      equity_irr?: number | null;
      equity_multiple?: number;
      atcf_first_year_yen?: number;
      payback_years?: number | null;
    };
  };
  assumption_score?: {
    overall_risk?: string;
  };
}

function yen(n: number | null | undefined): string {
  if (n == null) return "—";
  if (Math.abs(n) >= 10_000_000) return `¥${(n / 10_000_000).toFixed(2)}千万`;
  if (Math.abs(n) >= 10_000) return `¥${(n / 10_000).toFixed(1)}万`;
  return `¥${n.toLocaleString()}`;
}

function pct(n: number | null | undefined): string {
  if (n == null) return "—";
  return `${(n * 100).toFixed(2)}%`;
}

function num(n: number | null | undefined, digits = 2): string {
  if (n == null) return "—";
  return n.toFixed(digits);
}

export function DealSummaryCard({ metrics }: { metrics: RunMetrics | null }) {
  const kpi = metrics?.analysis?.kpi ?? {};
  const overallRisk = metrics?.assumption_score?.overall_risk ?? "";
  return (
    <Panel title="SUMMARY · KPI" meta={overallRisk.toUpperCase()}>
      <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-y divide-[var(--border)]">
        <KpiCell name="OVERALL RISK" value={overallRisk ? overallRisk.toUpperCase() : "—"} />
        <KpiCell name="CAP RATE" value={pct(kpi.cap_rate)} />
        <KpiCell name="DSCR Y1" value={num(kpi.dscr_year1)} />
        <KpiCell name="DSCR MIN" value={num(kpi.dscr_min)} />
        <KpiCell name="EQUITY IRR" value={pct(kpi.equity_irr)} />
        <KpiCell name="MULTIPLE" value={num(kpi.equity_multiple)} />
        <KpiCell name="ATCF Y1" value={yen(kpi.atcf_first_year_yen)} />
        <KpiCell
          name="PAYBACK"
          value={kpi.payback_years == null ? "—" : `${kpi.payback_years.toFixed(1)}y`}
        />
      </div>
    </Panel>
  );
}
