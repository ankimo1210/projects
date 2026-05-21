/**
 * /new — 新規分析画面
 *
 * 入力フォーム (property/income/opex/loan/exit/acquisition) → POST /api/analyze
 * → 結果をインライン表示。
 *
 * 物件を貼る/アップロードする画面ではなく、純粋な「手動入力で計算する」画面。
 * URL/PDF入力は Phase 3 で別ルートに追加予定。
 */
"use client";

import { useState } from "react";
import type { components } from "@/types/api";
import {
  Badge,
  Btn,
  Field,
  Input,
  KpiCell,
  Panel,
  Row,
  Select,
  fmtPct,
  fmtYen,
} from "@/components/bloomberg";
import { Nav } from "@/components/nav";

type AnalyzeResponse = components["schemas"]["AnalyzeResponse"];

// ===== Defaults (新宿区の区分マンション想定) =====
const defaults = {
  property_type: "kuubun" as const,
  purchase_price_yen: 39_800_000,
  land_value_yen: 8_000_000,
  building_value_yen: 31_800_000,
  structure: "rc" as const,
  building_completion_ym: "2011-04",
  acquisition_year: 2026,
  building_area_sqm: 38.4,
  location_pref: "13",
  location_city: "新宿区",

  gpi_monthly_yen: 145_000,
  vacancy_rate: 0.05,
  rent_growth_rate: -0.005,

  management_fee_rate: 0.05,
  building_mgmt_yen: 240_000,
  fixed_property_tax_yen: 120_000,
  insurance_yen: 20_000,
  repair_reserve_monthly_yen: 0,
  other_opex_yen: 0,

  loan_amount_yen: 27_860_000,
  interest_rate: 0.020,
  term_years: 30,

  income_tax_rate: 0.20,
  resident_tax_rate: 0.10,

  hold_period_years: 10,
  exit_cap_rate: 0.060,
  selling_cost_rate: 0.04,

  equity_yen: 12_000_000,
  acquisition_cost_rate: 0.07,
};

const PROPERTY_TYPES = [
  { value: "kuubun", label: "区分マンション" },
  { value: "ittou_apt", label: "一棟アパート" },
  { value: "ittou_mansion", label: "一棟マンション" },
  { value: "kodate", label: "戸建" },
  { value: "land", label: "土地" },
] as const;

const STRUCTURES = [
  { value: "wood", label: "木造" },
  { value: "steel", label: "鉄骨" },
  { value: "rc", label: "RC造" },
  { value: "src", label: "SRC造" },
] as const;

export default function NewAnalysisPage() {
  const [s, setS] = useState(defaults);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const update = <K extends keyof typeof defaults>(k: K, v: (typeof defaults)[K]) => {
    setS((prev) => ({ ...prev, [k]: v }));
  };
  const updNum = (k: keyof typeof defaults) => (v: string) => {
    const n = parseFloat(v);
    if (!Number.isFinite(n)) return;
    update(k, n as never);
  };
  const updInt = (k: keyof typeof defaults) => (v: string) => {
    const n = parseInt(v, 10);
    if (!Number.isFinite(n)) return;
    update(k, n as never);
  };

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const assumptions = {
        engine_version: "0.1.0",
        property: {
          property_type: s.property_type,
          purchase_price_yen: s.purchase_price_yen,
          land_value_yen: s.land_value_yen,
          building_value_yen: s.building_value_yen,
          structure: s.structure,
          building_completion_ym: s.building_completion_ym,
          acquisition_year: s.acquisition_year,
          building_area_sqm: s.building_area_sqm,
          location_pref: s.location_pref,
          location_city: s.location_city,
        },
        income: {
          gpi_monthly_yen: s.gpi_monthly_yen,
          vacancy_rate: s.vacancy_rate,
          rent_growth_rate: s.rent_growth_rate,
        },
        opex: {
          management_fee_rate: s.management_fee_rate,
          building_mgmt_yen: s.building_mgmt_yen,
          fixed_property_tax_yen: s.fixed_property_tax_yen,
          insurance_yen: s.insurance_yen,
          repair_reserve_monthly_yen: s.repair_reserve_monthly_yen,
          other_opex_yen: s.other_opex_yen,
        },
        loan: {
          loan_amount_yen: s.loan_amount_yen,
          interest_rate: s.interest_rate,
          term_years: s.term_years,
        },
        tax: {
          income_tax_rate: s.income_tax_rate,
          resident_tax_rate: s.resident_tax_rate,
        },
        exit: {
          hold_period_years: s.hold_period_years,
          exit_cap_rate: s.exit_cap_rate,
          selling_cost_rate: s.selling_cost_rate,
        },
        acquisition: {
          equity_yen: s.equity_yen,
          acquisition_cost_rate: s.acquisition_cost_rate,
        },
      };
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assumptions }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`HTTP ${res.status}: ${text.slice(0, 200)}`);
      }
      const data: AnalyzeResponse = await res.json();
      setResult(data);
      // 結果領域へスクロール
      setTimeout(() => {
        document.getElementById("result")?.scrollIntoView({ behavior: "smooth" });
      }, 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <Nav active="manual" />

      <form onSubmit={onSubmit} className="p-4 grid grid-cols-12 gap-2">
        <Panel className="col-span-6" title="[ PROPERTY ] 物件">
          <div className="p-4 grid grid-cols-2 gap-3">
            <Field label="種別">
              <Select
                value={s.property_type}
                options={PROPERTY_TYPES}
                onChange={(v) => update("property_type", v as never)}
              />
            </Field>
            <Field label="構造">
              <Select
                value={s.structure}
                options={STRUCTURES}
                onChange={(v) => update("structure", v as never)}
              />
            </Field>
            <Field label="価格 (円)">
              <Input type="number" value={s.purchase_price_yen} onChange={updInt("purchase_price_yen")} />
            </Field>
            <Field label="土地価格 (円)" hint="積算用">
              <Input type="number" value={s.land_value_yen} onChange={updInt("land_value_yen")} />
            </Field>
            <Field label="建物価格 (円)" hint="減価償却の基礎">
              <Input type="number" value={s.building_value_yen} onChange={updInt("building_value_yen")} />
            </Field>
            <Field label="築年月 (YYYY-MM)">
              <Input value={s.building_completion_ym} onChange={(v) => update("building_completion_ym", v)} />
            </Field>
            <Field label="取得年">
              <Input type="number" value={s.acquisition_year} onChange={updInt("acquisition_year")} />
            </Field>
            <Field label="専有/建物面積 (㎡)">
              <Input type="number" step="0.1" value={s.building_area_sqm} onChange={updNum("building_area_sqm")} />
            </Field>
            <Field label="都道府県コード">
              <Input value={s.location_pref} onChange={(v) => update("location_pref", v)} />
            </Field>
            <Field label="市区町村">
              <Input value={s.location_city} onChange={(v) => update("location_city", v)} />
            </Field>
          </div>
        </Panel>

        <Panel className="col-span-3" title="[ INCOME ] 収入">
          <div className="p-4 grid gap-3">
            <Field label="月額賃料 (円)" hint="満室想定">
              <Input type="number" value={s.gpi_monthly_yen} onChange={updInt("gpi_monthly_yen")} />
            </Field>
            <Field label="空室率" hint="例 0.05 = 5%">
              <Input type="number" step="0.01" value={s.vacancy_rate} onChange={updNum("vacancy_rate")} />
            </Field>
            <Field label="賃料成長率 (年)" hint="例 -0.005 = -0.5%">
              <Input type="number" step="0.001" value={s.rent_growth_rate} onChange={updNum("rent_growth_rate")} />
            </Field>
          </div>
        </Panel>

        <Panel className="col-span-3" title="[ OPEX ] 経費">
          <div className="p-4 grid gap-3">
            <Field label="管理料率 (EGI比)" hint="例 0.05 = 5%">
              <Input type="number" step="0.01" value={s.management_fee_rate} onChange={updNum("management_fee_rate")} />
            </Field>
            <Field label="建物管理費 (年/円)" hint="区分の管理費+修繕積立金">
              <Input type="number" value={s.building_mgmt_yen} onChange={updInt("building_mgmt_yen")} />
            </Field>
            <Field label="固都税 (年/円)">
              <Input type="number" value={s.fixed_property_tax_yen} onChange={updInt("fixed_property_tax_yen")} />
            </Field>
            <Field label="保険料 (年/円)">
              <Input type="number" value={s.insurance_yen} onChange={updInt("insurance_yen")} />
            </Field>
            <Field label="その他経費 (年/円)">
              <Input type="number" value={s.other_opex_yen} onChange={updInt("other_opex_yen")} />
            </Field>
          </div>
        </Panel>

        <Panel className="col-span-4" title="[ LOAN ] 融資">
          <div className="p-4 grid grid-cols-2 gap-3">
            <Field label="借入額 (円)">
              <Input type="number" value={s.loan_amount_yen} onChange={updInt("loan_amount_yen")} />
            </Field>
            <Field label="金利 (年)" hint="例 0.02 = 2%">
              <Input type="number" step="0.001" value={s.interest_rate} onChange={updNum("interest_rate")} />
            </Field>
            <Field label="期間 (年)">
              <Input type="number" value={s.term_years} onChange={updInt("term_years")} />
            </Field>
            <Field label="LTV (自動計算)" hint="借入額 / 価格">
              <Input
                value={
                  s.purchase_price_yen > 0
                    ? ((s.loan_amount_yen / s.purchase_price_yen) * 100).toFixed(1) + "%"
                    : "—"
                }
                onChange={() => {}}
              />
            </Field>
          </div>
        </Panel>

        <Panel className="col-span-4" title="[ EXIT ] 出口">
          <div className="p-4 grid grid-cols-2 gap-3">
            <Field label="保有期間 (年)">
              <Input type="number" value={s.hold_period_years} onChange={updInt("hold_period_years")} />
            </Field>
            <Field label="出口Cap" hint="例 0.06 = 6%">
              <Input type="number" step="0.001" value={s.exit_cap_rate} onChange={updNum("exit_cap_rate")} />
            </Field>
            <Field label="売却諸費用率" hint="仲介手数料等">
              <Input type="number" step="0.001" value={s.selling_cost_rate} onChange={updNum("selling_cost_rate")} />
            </Field>
          </div>
        </Panel>

        <Panel className="col-span-4" title="[ TAX & EQUITY ] 税・自己資金">
          <div className="p-4 grid grid-cols-2 gap-3">
            <Field label="所得税率" hint="限界税率">
              <Input type="number" step="0.01" value={s.income_tax_rate} onChange={updNum("income_tax_rate")} />
            </Field>
            <Field label="住民税率">
              <Input type="number" step="0.01" value={s.resident_tax_rate} onChange={updNum("resident_tax_rate")} />
            </Field>
            <Field label="自己資金 (円)">
              <Input type="number" value={s.equity_yen} onChange={updInt("equity_yen")} />
            </Field>
            <Field label="取得諸費用率">
              <Input type="number" step="0.001" value={s.acquisition_cost_rate} onChange={updNum("acquisition_cost_rate")} />
            </Field>
          </div>
        </Panel>

        <div className="col-span-12 flex items-center gap-3 justify-end mt-2">
          {error && (
            <span className="text-[var(--bad)] font-mono text-[11px]">
              [ ERROR ] {error}
            </span>
          )}
          <Btn variant="ghost" type="button" onClick={() => setS(defaults)}>
            RESET
          </Btn>
          <Btn variant="primary" type="submit" disabled={loading}>
            {loading ? "ANALYZING..." : "▶ RUN ANALYSIS"}
          </Btn>
        </div>
      </form>

      {result && (
        <div id="result" className="p-4 grid grid-cols-12 gap-2 border-t border-[var(--border)] pt-6">
          <ResultPanels data={result} />
        </div>
      )}

      <footer className="mt-4 mx-4 mb-4 px-3 py-2 bg-[var(--surface)] border border-[var(--border)] text-[9px] text-[var(--text-subtle)] leading-relaxed font-mono">
        [ DISCLAIMER ] PARAMETRIC SIMULATION FOR REFERENCE. NOT INVESTMENT ADVICE. NOT A
        SOLICITATION FOR ANY SECURITY OR REAL ESTATE TRANSACTION. © re_invest_os v0.1
      </footer>
    </div>
  );
}

function ResultPanels({ data }: { data: AnalyzeResponse }) {
  const k = data.analysis.kpi;
  const e = data.analysis.exit;
  const s = data.score;
  const scoreColor =
    s.total >= 70 ? "var(--good)" : s.total >= 50 ? "var(--warn)" : "var(--bad)";
  const scoreLevel: "good" | "warn" | "bad" =
    s.total >= 70 ? "good" : s.total >= 50 ? "warn" : "bad";

  return (
    <>
      <Panel className="col-span-3" title="[ SCORE ]">
        <div className="p-6 text-center">
          <div
            className="text-[56px] font-mono font-bold leading-none tracking-tight tabular-nums"
            style={{ color: scoreColor }}
          >
            {s.total.toFixed(1)}
          </div>
          <div className="text-[11px] text-[var(--text-muted)] mt-1">/ 100</div>
          <div className="mt-2">
            <Badge level={scoreLevel}>{s.evaluation}</Badge>
          </div>
          <div className="text-[9px] text-[var(--text-subtle)] mt-3 leading-relaxed">
            分析上の健全性スコア。買い推奨ではありません。
          </div>
        </div>
      </Panel>

      <Panel className="col-span-9" title="[ KPI ] 10Y · 自己資金IRR">
        <div className="grid grid-cols-4 gap-px bg-[var(--border)] border border-[var(--border)]">
          <KpiCell
            name="CAP RATE"
            value={fmtPct(k.cap_rate)}
            note="NOI / 価格"
            severity={k.cap_rate < 0.04 ? "bad" : k.cap_rate < 0.05 ? "warn" : "good"}
          />
          <KpiCell
            name="CoC"
            value={fmtPct(k.cash_on_cash)}
            note="BTCF Y1 / 自己資金"
            severity={k.cash_on_cash < 0 ? "bad" : k.cash_on_cash < 0.03 ? "warn" : "good"}
          />
          <KpiCell
            name="DSCR MIN"
            value={k.dscr_min.toFixed(2)}
            note={k.dscr_min < 1.0 ? "1.0未満 / 危険" : k.dscr_min < 1.25 ? "1.25未満 / 警告" : "OK"}
            severity={k.dscr_min < 1.0 ? "bad" : k.dscr_min < 1.25 ? "warn" : "good"}
          />
          <KpiCell
            name="EQ IRR"
            value={k.equity_irr === null ? "N/A" : fmtPct(k.equity_irr)}
            note={k.equity_irr === null ? "未収束" : "10年保有"}
            severity={k.equity_irr === null || k.equity_irr < 0.06 ? "bad" : k.equity_irr < 0.08 ? "warn" : "good"}
          />
          <KpiCell
            name="EQ MULT"
            value={`${k.equity_multiple.toFixed(2)}x`}
            note="10Y CUM"
            severity={k.equity_multiple < 1.0 ? "bad" : k.equity_multiple < 1.5 ? "warn" : "good"}
          />
          <KpiCell
            name="PAYBACK"
            value={k.payback_years === null ? "N/A" : `${k.payback_years.toFixed(1)}Y`}
            note="自己資金回収"
            severity={k.payback_years === null ? "bad" : k.payback_years > 15 ? "warn" : "good"}
          />
          <KpiCell
            name="ATCF Y1"
            value={fmtYen(k.atcf_first_year_yen)}
            note="post-tax"
            severity={k.atcf_first_year_yen < 0 ? "bad" : "good"}
          />
          <KpiCell name="LTV" value={fmtPct(k.ltv, 1)} note="借入比率" />
        </div>
      </Panel>

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
              {data.analysis.yearly_cashflows.map((cf) => (
                <tr key={cf.year} className="border-t border-[var(--border)]">
                  <td className="px-2 py-1.5">Y{cf.year}</td>
                  <td className="text-right px-2 py-1.5">{fmtYen(cf.egi_yen)}</td>
                  <td className="text-right px-2 py-1.5">{fmtYen(cf.noi_yen)}</td>
                  <td className="text-right px-2 py-1.5">{fmtYen(cf.debt_service_yen)}</td>
                  <td className={`text-right px-2 py-1.5 ${cf.btcf_yen < 0 ? "text-[var(--bad)]" : ""}`}>
                    {fmtYen(cf.btcf_yen)}
                  </td>
                  <td className={`text-right px-2 py-1.5 ${cf.atcf_yen < 0 ? "text-[var(--bad)]" : ""}`}>
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

      <Panel className="col-span-5" title="[ EXIT ] 売却シナリオ">
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

      <Panel className="col-span-12" title="[ SCORE BREAKDOWN ]">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="bg-[var(--surface-alt)] text-[var(--accent)] text-[9px] uppercase tracking-widest font-mono">
              <th className="text-left px-3 py-2">COMPONENT</th>
              <th className="text-right px-3 py-2">SCORE</th>
              <th className="text-right px-3 py-2">MAX</th>
              <th className="text-left px-3 py-2">DETAIL</th>
            </tr>
          </thead>
          <tbody>
            {s.components.map((c) => {
              const ratio = c.score / c.max_score;
              const color =
                ratio >= 0.7 ? "var(--good)" : ratio >= 0.4 ? "var(--warn)" : "var(--bad)";
              return (
                <tr key={c.name} className="border-t border-[var(--border)]">
                  <td className="px-3 py-1.5 font-mono uppercase">{c.name}</td>
                  <td
                    className="text-right px-3 py-1.5 font-mono tabular-nums font-bold"
                    style={{ color }}
                  >
                    {c.score.toFixed(1)}
                  </td>
                  <td className="text-right px-3 py-1.5 font-mono tabular-nums text-[var(--text-muted)]">
                    {c.max_score.toFixed(0)}
                  </td>
                  <td className="px-3 py-1.5 text-[var(--text-muted)]">{c.detail}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Panel>
    </>
  );
}
