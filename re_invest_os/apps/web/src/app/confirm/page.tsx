/**
 * /confirm — AI抽出結果の確認・修正
 *
 * フロー:
 *   sessionStorage から ExtractionResponse を読み出し
 *   → 主要フィールドを表示・編集 (price/structure/area/build_ym/gpi/...)
 *   → missing_required を埋めて Assumptions を組み立て (クライアント側)
 *   → POST /api/analyze → /report
 */
"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "@/types/api";

type ExtractionResponse = components["schemas"]["ExtractionResponse"];
type Assumptions = components["schemas"]["Assumptions"];

const STRUCTURES = [
  { value: "wood", label: "木造" },
  { value: "steel", label: "鉄骨" },
  { value: "rc", label: "RC造" },
  { value: "src", label: "SRC造" },
] as const;

type StructureValue = (typeof STRUCTURES)[number]["value"];

interface FormState {
  purchase_price_yen: number;
  structure: StructureValue;
  build_year_month: string; // YYYY-MM
  building_area_sqm: number;
  gpi_monthly_yen: number;
  management_fee_monthly_yen: number;
  repair_reserve_monthly_yen: number;
  equity_yen: number;
  interest_rate_pct: number;
  term_years: number;
  hold_period_years: number;
  exit_cap_rate_pct: number;
  location_pref: string;
  vacancy_rate_pct: number;
}

const PREFECTURE_OPTIONS = [
  { value: "13", label: "東京都" },
  { value: "14", label: "神奈川県" },
  { value: "11", label: "埼玉県" },
  { value: "12", label: "千葉県" },
  { value: "27", label: "大阪府" },
  { value: "23", label: "愛知県" },
  { value: "28", label: "兵庫県" },
  { value: "26", label: "京都府" },
  { value: "40", label: "福岡県" },
];

function defaultForm(ext: ExtractionResponse): FormState {
  const a = ext.assumptions;
  const e = ext.extracted;
  return {
    purchase_price_yen:
      a?.property.purchase_price_yen ?? e.asking_price_yen ?? 0,
    structure: (a?.property.structure ?? e.structure ?? "rc") as StructureValue,
    build_year_month:
      a?.property.building_completion_ym ?? e.build_year_month ?? "2015-01",
    building_area_sqm:
      a?.property.building_area_sqm ??
      e.exclusive_area_sqm ??
      e.building_area_sqm ??
      40,
    gpi_monthly_yen:
      a?.income.gpi_monthly_yen ?? e.estimated_full_rent_monthly_yen ?? 0,
    management_fee_monthly_yen: e.management_fee_monthly_yen ?? 0,
    repair_reserve_monthly_yen: e.repair_reserve_monthly_yen ?? 0,
    equity_yen:
      a?.acquisition.equity_yen ??
      Math.round((e.asking_price_yen ?? 0) * 0.3),
    interest_rate_pct: ((a?.loan.interest_rate ?? 0.02) * 100),
    term_years: a?.loan.term_years ?? 30,
    hold_period_years: a?.exit?.hold_period_years ?? 10,
    exit_cap_rate_pct: ((a?.exit?.exit_cap_rate ?? 0.06) * 100),
    location_pref: a?.property.location_pref ?? "13",
    vacancy_rate_pct: ((a?.income.vacancy_rate ?? 0.05) * 100),
  };
}

function buildAssumptions(form: FormState, currentYear: number): Assumptions {
  const price = form.purchase_price_yen;
  const land = Math.round(price * 0.2);
  const building = price - land;
  const loanAmount = Math.max(0, price - form.equity_yen);

  return {
    engine_version: "0.1.0",
    property: {
      property_type: "kuubun",
      purchase_price_yen: price,
      land_value_yen: land,
      building_value_yen: building,
      structure: form.structure,
      building_completion_ym: form.build_year_month,
      acquisition_year: currentYear,
      building_area_sqm: form.building_area_sqm,
      land_area_sqm: null,
      num_units: null,
      location_pref: form.location_pref,
      location_city: null,
    },
    income: {
      gpi_monthly_yen: form.gpi_monthly_yen,
      other_income_monthly_yen: 0,
      vacancy_rate: form.vacancy_rate_pct / 100,
      rent_growth_rate: -0.005,
      bad_debt_rate: 0,
    },
    opex: {
      management_fee_rate: 0.05,
      repair_reserve_monthly_yen: 0,
      fixed_property_tax_yen: Math.round(price * 0.003),
      insurance_yen: 20_000,
      building_mgmt_yen:
        (form.management_fee_monthly_yen + form.repair_reserve_monthly_yen) * 12,
      other_opex_yen: 0,
      opex_growth_rate: 0.005,
    },
    loan: {
      loan_amount_yen: loanAmount,
      interest_rate: form.interest_rate_pct / 100,
      term_years: form.term_years,
      repayment_type: "amortized",
      grace_period_months: 0,
    },
    tax: {
      income_tax_rate: 0.2,
      resident_tax_rate: 0.1,
      business_tax_rate: 0,
      capital_gain_short_rate: 0.39,
      capital_gain_long_rate: 0.2,
    },
    exit: {
      hold_period_years: form.hold_period_years,
      exit_cap_rate: form.exit_cap_rate_pct / 100,
      selling_cost_rate: 0.04,
    },
    acquisition: {
      equity_yen: form.equity_yen,
      acquisition_cost_rate: 0.07,
    },
  } satisfies Assumptions;
}

function ConfBadge({ label }: { label?: string }) {
  if (!label) return null;
  return (
    <span className="inline-block ml-2 px-1.5 py-px font-mono text-[9px] uppercase tracking-widest bg-[var(--surface-alt)] text-[var(--text-muted)] border border-[var(--border)]">
      {label}
    </span>
  );
}

function NumberRow({
  label,
  value,
  onChange,
  unit,
  step,
  badge,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  unit?: string;
  step?: string;
  badge?: string;
}) {
  return (
    <label className="flex items-center justify-between gap-3 py-1.5">
      <span className="text-[12px] text-[var(--text-muted)]">
        {label}
        <ConfBadge label={badge} />
      </span>
      <span className="flex items-center gap-1.5">
        <input
          type="number"
          value={Number.isFinite(value) ? value : 0}
          onChange={(e) => onChange(Number(e.target.value) || 0)}
          step={step ?? "1"}
          className="bg-[var(--bg)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none px-2 py-1 font-mono text-[12px] tabular-nums text-right w-36"
        />
        {unit && (
          <span className="text-[10px] text-[var(--text-subtle)] font-mono w-10">
            {unit}
          </span>
        )}
      </span>
    </label>
  );
}

export default function ConfirmPage() {
  const router = useRouter();
  const [ext, setExt] = useState<ExtractionResponse | null>(null);
  const [form, setForm] = useState<FormState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("reio:extraction");
    if (!raw) {
      router.replace("/upload");
      return;
    }
    try {
      const parsed: ExtractionResponse = JSON.parse(raw);
      setExt(parsed);
      setForm(defaultForm(parsed));
    } catch {
      router.replace("/upload");
    }
  }, [router]);

  const fieldConfidences = useMemo(
    () => ext?.extracted.field_confidences ?? {},
    [ext],
  );

  function confLabel(key: string): string | undefined {
    const c = (fieldConfidences as Record<string, number>)[key];
    if (typeof c !== "number") return undefined;
    if (c >= 0.9) return "AI:強";
    if (c >= 0.6) return "AI:中";
    return "AI:弱";
  }

  if (!ext || !form) {
    return (
      <main className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex items-center justify-center">
        <div className="text-[var(--text-muted)] text-sm">読み込み中…</div>
      </main>
    );
  }

  async function submit() {
    if (!form) return;
    setError(null);
    setSubmitting(true);
    try {
      const assumptions = buildAssumptions(form, new Date().getFullYear());
      const resp = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assumptions }),
      });
      const text = await resp.text();
      if (!resp.ok) {
        try {
          const j = JSON.parse(text);
          setError(j.detail ?? j.error ?? `エラー (${resp.status})`);
        } catch {
          setError(`エラー (${resp.status}): ${text.slice(0, 200)}`);
        }
        return;
      }
      sessionStorage.setItem("reio:analysis", text);
      sessionStorage.setItem(
        "reio:assumptions",
        JSON.stringify(assumptions),
      );
      router.push("/report");
    } catch (e) {
      setError(e instanceof Error ? e.message : "予期しないエラー");
    } finally {
      setSubmitting(false);
    }
  }

  const meta = ext.meta;

  return (
    <main className="min-h-screen bg-[var(--bg)] text-[var(--text)] py-12 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="font-mono text-[10px] text-[var(--accent)] tracking-widest uppercase mb-2">
          STEP 2 / CONFIRM
        </div>
        <h1 className="text-2xl font-bold mb-2">AI が読み取った内容</h1>
        <p className="text-[12px] text-[var(--text-muted)] mb-6">
          抽出に誤りがあれば修正してください。空欄や信頼度の低い項目は、必ず実資料で確認を。
        </p>

        {/* meta */}
        <div className="text-[10px] text-[var(--text-subtle)] font-mono mb-4 flex flex-wrap gap-3">
          <span>
            分類: {String(meta.classification.document_type)} (
            {Number(meta.classification.confidence).toFixed(2)})
          </span>
          <span>
            PII マスク:{" "}
            {Object.entries(meta.pii_redactions || {})
              .map(([k, v]) => `${k}=${v}`)
              .join(" ") || "0"}
          </span>
          <span>engine {meta.engine_version}</span>
          <span>
            prompts{" "}
            {Object.entries(meta.prompt_versions || {})
              .map(([k, v]) => `${k}:${v}`)
              .join(" ")}
          </span>
        </div>

        {/* 充足率スコア */}
        {meta.completeness_score !== undefined && (
          <div className="mb-4 flex items-center gap-3 text-[11px] font-mono">
            <span className="text-[var(--text-muted)]">資料充足率</span>
            <div className="flex-1 max-w-48 bg-[var(--surface)] border border-[var(--border)] h-2 overflow-hidden">
              <div
                className="h-full transition-all"
                style={{
                  width: `${meta.completeness_score}%`,
                  background: meta.completeness_score >= 80
                    ? "var(--good)"
                    : meta.completeness_score >= 40
                    ? "var(--warn)"
                    : "var(--bad)",
                }}
              />
            </div>
            <span
              style={{
                color: meta.completeness_score >= 80
                  ? "var(--good)"
                  : meta.completeness_score >= 40
                  ? "var(--warn)"
                  : "var(--bad)",
              }}
            >
              {meta.completeness_score.toFixed(0)}%
            </span>
          </div>
        )}

        {/* warnings */}
        {(meta.warnings?.length ?? 0) > 0 && (
          <div className="bg-[var(--surface)] border border-[var(--warn)] px-3 py-2 mb-6 text-[11px] font-mono text-[var(--warn)]">
            <div className="uppercase tracking-widest text-[9px] mb-1">
              warnings
            </div>
            <ul className="list-disc list-inside space-y-0.5 text-[var(--text-muted)]">
              {(meta.warnings ?? []).map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {(meta.missing_required?.length ?? 0) > 0 && (
          <div className="bg-[var(--surface)] border border-[var(--bad)] px-3 py-2 mb-6 text-[11px] font-mono text-[var(--bad)]">
            <div className="uppercase tracking-widest text-[9px] mb-1">
              missing required
            </div>
            <p className="text-[var(--text-muted)]">
              以下を入力してから次へ進んでください:{" "}
              {(meta.missing_required ?? []).join(", ")}
            </p>
          </div>
        )}

        <section className="grid md:grid-cols-2 gap-x-8 bg-[var(--surface)] border border-[var(--border)] px-4 py-3 mb-6">
          <div>
            <h2 className="text-[10px] uppercase tracking-widest text-[var(--accent)] font-mono py-2 border-b border-[var(--border)] mb-1">
              PROPERTY
            </h2>
            <NumberRow
              label="価格"
              value={form.purchase_price_yen}
              onChange={(v) => setForm({ ...form, purchase_price_yen: v })}
              unit="円"
              step="100000"
              badge={confLabel("asking_price_yen")}
            />
            <label className="flex items-center justify-between gap-3 py-1.5">
              <span className="text-[12px] text-[var(--text-muted)]">
                構造
                <ConfBadge label={confLabel("structure")} />
              </span>
              <select
                value={form.structure}
                onChange={(e) =>
                  setForm({ ...form, structure: e.target.value as StructureValue })
                }
                className="bg-[var(--bg)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none px-2 py-1 font-mono text-[12px] w-48"
              >
                {STRUCTURES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center justify-between gap-3 py-1.5">
              <span className="text-[12px] text-[var(--text-muted)]">
                築年月
                <ConfBadge label={confLabel("build_year_month")} />
              </span>
              <input
                type="month"
                value={form.build_year_month}
                onChange={(e) =>
                  setForm({ ...form, build_year_month: e.target.value })
                }
                className="bg-[var(--bg)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none px-2 py-1 font-mono text-[12px] w-48"
              />
            </label>
            <NumberRow
              label="専有面積"
              value={form.building_area_sqm}
              onChange={(v) => setForm({ ...form, building_area_sqm: v })}
              unit="㎡"
              step="0.1"
              badge={confLabel("exclusive_area_sqm")}
            />
            <label className="flex items-center justify-between gap-3 py-1.5">
              <span className="text-[12px] text-[var(--text-muted)]">都道府県</span>
              <select
                value={form.location_pref}
                onChange={(e) =>
                  setForm({ ...form, location_pref: e.target.value })
                }
                className="bg-[var(--bg)] border border-[var(--border)] focus:border-[var(--accent)] focus:outline-none px-2 py-1 font-mono text-[12px] w-48"
              >
                {PREFECTURE_OPTIONS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div>
            <h2 className="text-[10px] uppercase tracking-widest text-[var(--accent)] font-mono py-2 border-b border-[var(--border)] mb-1">
              INCOME / OPEX
            </h2>
            <NumberRow
              label="月額賃料"
              value={form.gpi_monthly_yen}
              onChange={(v) => setForm({ ...form, gpi_monthly_yen: v })}
              unit="円"
              step="1000"
              badge={confLabel("estimated_full_rent_monthly_yen")}
            />
            <NumberRow
              label="管理費"
              value={form.management_fee_monthly_yen}
              onChange={(v) =>
                setForm({ ...form, management_fee_monthly_yen: v })
              }
              unit="円/月"
              step="500"
              badge={confLabel("management_fee_monthly_yen")}
            />
            <NumberRow
              label="修繕積立金"
              value={form.repair_reserve_monthly_yen}
              onChange={(v) =>
                setForm({ ...form, repair_reserve_monthly_yen: v })
              }
              unit="円/月"
              step="500"
              badge={confLabel("repair_reserve_monthly_yen")}
            />
            <NumberRow
              label="空室率"
              value={form.vacancy_rate_pct}
              onChange={(v) => setForm({ ...form, vacancy_rate_pct: v })}
              unit="%"
              step="0.5"
            />

            <h2 className="text-[10px] uppercase tracking-widest text-[var(--accent)] font-mono py-2 border-b border-[var(--border)] mb-1 mt-4">
              LOAN / EXIT
            </h2>
            <NumberRow
              label="自己資金"
              value={form.equity_yen}
              onChange={(v) => setForm({ ...form, equity_yen: v })}
              unit="円"
              step="100000"
            />
            <NumberRow
              label="金利"
              value={form.interest_rate_pct}
              onChange={(v) => setForm({ ...form, interest_rate_pct: v })}
              unit="%"
              step="0.05"
            />
            <NumberRow
              label="返済年数"
              value={form.term_years}
              onChange={(v) => setForm({ ...form, term_years: v })}
              unit="年"
              step="1"
            />
            <NumberRow
              label="保有年数"
              value={form.hold_period_years}
              onChange={(v) => setForm({ ...form, hold_period_years: v })}
              unit="年"
              step="1"
            />
            <NumberRow
              label="出口Cap"
              value={form.exit_cap_rate_pct}
              onChange={(v) => setForm({ ...form, exit_cap_rate_pct: v })}
              unit="%"
              step="0.1"
            />
          </div>
        </section>

        <div className="flex justify-between items-center">
          <button
            type="button"
            onClick={() => router.push("/upload")}
            className="px-3 py-2 text-[11px] font-mono uppercase tracking-widest border border-[var(--border)] hover:bg-[var(--surface-alt)]"
          >
            ← やり直す
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={submitting || form.purchase_price_yen <= 0}
            className="px-6 py-2.5 bg-[var(--accent)] text-[var(--bg)] font-mono font-bold text-[11px] uppercase tracking-widest hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {submitting ? "計算中…" : "監査レポートを見る →"}
          </button>
        </div>
      </div>
    </main>
  );
}
