/**
 * トップ画面 (サンプル分析の表示)。
 * APIから実データ (西新宿の仮想物件) を取得して Bloomberg基調で表示。
 * 共通コンポーネントは @/components/bloomberg.tsx に分離済み。
 */
import type { components } from "@/types/api";
import {
  Badge,
  Btn,
  KpiCell,
  Panel,
  Row,
  Tick,
  fmtPct,
  fmtYen,
} from "@/components/bloomberg";
import { Nav } from "@/components/nav";

type AnalyzeResponse = components["schemas"]["AnalyzeResponse"];

const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8001";

async function fetchSample(): Promise<AnalyzeResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/sample/nishi-shinjuku`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function Home() {
  const data = await fetchSample();

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <Nav active="sample" apiStatus={data !== null} />

      <div className="flex gap-6 px-4 py-1 bg-[var(--surface-alt)] border-b border-[var(--border)] text-[11px] font-mono text-[var(--text-muted)]">
        <Tick label="JGB10Y" value="1.42%" delta="+0.02" good />
        <Tick label="USDJPY" value="148.32" delta="-0.45" bad />
        <Tick label="TOPIX" value="2,841" delta="+0.8%" good />
        <Tick label="JREIT" value="1,832" delta="-0.3%" bad />
        <Tick label="FLAT35" value="1.92%" />
        <Tick label="ENGINE" value={data?.analysis.engine_version ?? "—"} />
      </div>

      {/* サンプル表示の明示 + 新規分析への導線 */}
      <div className="flex items-center justify-between px-4 py-2 bg-[var(--surface)] border-b border-[var(--border)]">
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <Badge level="warn">SAMPLE</Badge>
          <span className="text-[var(--text-muted)]">
            これはデモ用の仮想物件分析です。あなたの物件で試すには右の RUN ANALYSIS から
          </span>
        </div>
        <a href="/new">
          <Btn variant="primary">▶ RUN NEW ANALYSIS</Btn>
        </a>
      </div>

      {!data ? (
        <div className="p-8 text-center">
          <div className="inline-block px-4 py-3 border border-[var(--bad)] text-[var(--bad)] font-mono text-xs">
            [ ERROR ] API server unreachable at {API_BASE}
          </div>
        </div>
      ) : (
        <main className="p-4 grid grid-cols-12 gap-2">
          <PropertyPanel data={data} />
          <KpiPanel data={data} />
          <ScorePanel data={data} />
          <CashflowPanel data={data} />
          <ExitPanel data={data} />
          <ScoreComponentPanel data={data} />
        </main>
      )}

      <footer className="mt-4 mx-4 mb-4 px-3 py-2 bg-[var(--surface)] border border-[var(--border)] text-[9px] text-[var(--text-subtle)] leading-relaxed font-mono">
        [ DISCLAIMER ] PARAMETRIC SIMULATION FOR REFERENCE. NOT INVESTMENT ADVICE. NOT A
        SOLICITATION FOR ANY SECURITY OR REAL ESTATE TRANSACTION. CONSULT LICENSED
        PROFESSIONALS FOR TAX/LEGAL DECISIONS. © re_invest_os v0.1
      </footer>
    </div>
  );
}

function PropertyPanel({ data }: { data: AnalyzeResponse }) {
  const p = data.analysis.assumptions.property;
  const gpi = data.analysis.assumptions.income.gpi_monthly_yen;
  const completionYear = parseInt(p.building_completion_ym.split("-")[0], 10);
  const age = p.acquisition_year - completionYear;
  return (
    <Panel className="col-span-4" title="[ PROPERTY ]" meta="#A-184">
      <div className="p-4 text-[11px]">
        <div className="text-[13px] font-bold mb-1">西新宿レジデンス 504号</div>
        <div className="text-[10px] text-[var(--text-muted)] mb-3">
          東京都{p.location_city ?? p.location_pref} / 区分マンション
        </div>
        <Row label="価格" value={fmtYen(p.purchase_price_yen)} />
        <Row label="構造" value={p.structure.toUpperCase()} />
        <Row label="築年" value={`${completionYear} (${age}Y)`} />
        <Row label="専有面積" value={`${p.building_area_sqm.toFixed(2)} m²`} />
        <Row label="想定賃料" value={`${fmtYen(gpi)}/mo`} />
        <Row label="表面利回り" value={fmtPct((gpi * 12) / p.purchase_price_yen)} warn />
        <Row label="NOI利回" value={fmtPct(data.analysis.kpi.cap_rate)} bad />
      </div>
    </Panel>
  );
}

function KpiPanel({ data }: { data: AnalyzeResponse }) {
  const k = data.analysis.kpi;
  return (
    <Panel className="col-span-5" title="[ KPI ] 10Y · LTV 70% · @2.00%">
      <div className="grid grid-cols-4 gap-px bg-[var(--border)] border border-[var(--border)]">
        <KpiCell name="CAP RATE" value={fmtPct(k.cap_rate)} note="NOI / 価格" warn />
        <KpiCell
          name="CoC"
          value={fmtPct(k.cash_on_cash)}
          note="BTCF Y1 / 自己資金"
          bad={k.cash_on_cash < 0}
        />
        <KpiCell
          name="DSCR MIN"
          value={k.dscr_min.toFixed(2)}
          note={k.dscr_min < 1.25 ? "THR 1.25 BREACH" : "OK"}
          bad={k.dscr_min < 1.0}
          warn={k.dscr_min >= 1.0 && k.dscr_min < 1.25}
        />
        <KpiCell
          name="EQ IRR"
          value={k.equity_irr === null ? "N/A" : fmtPct(k.equity_irr)}
          note={k.equity_irr === null ? "未収束 (赤字)" : "10年保有"}
          bad={k.equity_irr === null || k.equity_irr < 0.06}
        />
        <KpiCell
          name="EQ MULT"
          value={`${k.equity_multiple.toFixed(2)}x`}
          note="10Y CUM"
          bad={k.equity_multiple < 1.0}
        />
        <KpiCell
          name="PAYBACK"
          value={k.payback_years === null ? "N/A" : `${k.payback_years.toFixed(1)}Y`}
          note="自己資金回収"
          bad={k.payback_years === null}
        />
        <KpiCell
          name="ATCF Y1"
          value={fmtYen(k.atcf_first_year_yen)}
          note="post-tax"
          bad={k.atcf_first_year_yen < 0}
        />
        <KpiCell name="LTV" value={fmtPct(k.ltv, 1)} note="借入比率" />
      </div>
    </Panel>
  );
}

const RISK_LABEL_JP: Record<string, string> = {
  low: "低", medium: "中", high: "高", unknown: "不明",
};
const RISK_LEVEL_UI: Record<string, "good" | "warn" | "bad"> = {
  low: "good", medium: "warn", high: "bad", unknown: "warn",
};
function riskColor(level: string): string {
  return level === "high"
    ? "var(--bad)"
    : level === "medium"
      ? "var(--warn)"
      : level === "low"
        ? "var(--good)"
        : "var(--text-muted)";
}

function ScorePanel({ data }: { data: AnalyzeResponse }) {
  const s = data.assumption_score;
  const level = RISK_LEVEL_UI[s.overall_risk] ?? "warn";
  return (
    <Panel className="col-span-3" title="[ ASSUMPTION RISK ] 前提リスク">
      <div className="p-6 text-center">
        <div
          className="text-[40px] font-mono font-bold leading-none tracking-tight uppercase"
          style={{ color: riskColor(s.overall_risk) }}
        >
          {s.overall_risk}
        </div>
        <div className="text-[11px] text-[var(--text-muted)] mt-1">総合前提リスク</div>
        <div className="mt-2">
          <Badge level={level}>{RISK_LABEL_JP[s.overall_risk] ?? s.overall_risk}</Badge>
        </div>
        <div className="text-[9px] text-[var(--text-subtle)] mt-3 leading-relaxed">
          前提リスクの検証結果です。投資判断ではありません。前提を変えれば変動します。
        </div>
      </div>
    </Panel>
  );
}

function CashflowPanel({ data }: { data: AnalyzeResponse }) {
  const cfs = data.analysis.yearly_cashflows;
  return (
    <Panel className="col-span-7" title="[ CASHFLOW ] 10Y PROJECTION">
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] font-mono tabular-nums">
          <thead>
            <tr className="bg-[var(--surface-alt)] text-[var(--accent)] text-[9px] uppercase tracking-widest">
              <th className="text-left px-2 py-1.5">Y</th>
              <th className="text-right px-2 py-1.5">EGI</th>
              <th className="text-right px-2 py-1.5">NOI</th>
              <th className="text-right px-2 py-1.5">DS</th>
              <th className="text-right px-2 py-1.5">BTCF</th>
              <th className="text-right px-2 py-1.5">ATCF</th>
              <th className="text-right px-2 py-1.5">残債</th>
            </tr>
          </thead>
          <tbody>
            {cfs.map((cf) => (
              <tr key={cf.year} className="border-t border-[var(--border)]">
                <td className="px-2 py-1.5">Y{cf.year}</td>
                <td className="text-right px-2 py-1.5">{fmtYen(cf.egi_yen)}</td>
                <td className="text-right px-2 py-1.5">{fmtYen(cf.noi_yen)}</td>
                <td className="text-right px-2 py-1.5">{fmtYen(cf.debt_service_yen)}</td>
                <td
                  className={`text-right px-2 py-1.5 ${cf.btcf_yen < 0 ? "text-[var(--bad)]" : ""}`}
                >
                  {fmtYen(cf.btcf_yen)}
                </td>
                <td
                  className={`text-right px-2 py-1.5 ${cf.atcf_yen < 0 ? "text-[var(--bad)]" : ""}`}
                >
                  {fmtYen(cf.atcf_yen)}
                </td>
                <td className="text-right px-2 py-1.5 text-[var(--text-muted)]">
                  {fmtYen(cf.loan_balance_end_yen)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

function ExitPanel({ data }: { data: AnalyzeResponse }) {
  const e = data.analysis.exit;
  return (
    <Panel className="col-span-5" title="[ EXIT ] 10Y SALE">
      <div className="p-4 text-[11px] space-y-1">
        <Row label="売却価格" value={fmtYen(e.sale_price_yen)} />
        <Row label="残債" value={fmtYen(e.remaining_loan_yen)} />
        <Row
          label="譲渡所得"
          value={fmtYen(e.capital_gain_yen)}
          severity={e.capital_gain_yen < 0 ? "bad" : undefined}
        />
        <Row label="譲渡税" value={fmtYen(e.capital_gain_tax_yen)} />
        <div className="border-t border-[var(--border)] my-2" />
        <Row
          label="税後手残り"
          value={fmtYen(e.net_proceeds_yen)}
          severity={e.net_proceeds_yen < 0 ? "bad" : "good"}
        />
      </div>
    </Panel>
  );
}

function ScoreComponentPanel({ data }: { data: AnalyzeResponse }) {
  return (
    <Panel className="col-span-12" title="[ ASSUMPTION RISK ] BREAKDOWN">
      <table className="w-full text-[11px]">
        <thead>
          <tr className="bg-[var(--surface-alt)] text-[var(--accent)] text-[9px] uppercase tracking-widest font-mono">
            <th className="text-left px-3 py-2">CATEGORY</th>
            <th className="text-center px-3 py-2">CONF</th>
            <th className="text-center px-3 py-2">RISK</th>
            <th className="text-left px-3 py-2">理由</th>
          </tr>
        </thead>
        <tbody>
          {data.assumption_score.items.map((it) => (
            <tr key={it.category} className="border-t border-[var(--border)]">
              <td className="px-3 py-1.5 font-mono uppercase">{it.category}</td>
              <td className="text-center px-3 py-1.5 font-mono">{it.confidence}</td>
              <td
                className="text-center px-3 py-1.5 font-mono font-bold uppercase"
                style={{ color: riskColor(it.risk_level) }}
              >
                {it.risk_level}
              </td>
              <td className="px-3 py-1.5 text-[var(--text-muted)]">{it.reason}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
