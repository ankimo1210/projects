/**
 * 監査レポートのパネル群 (共通)。
 * 既存 page.tsx (サンプル) と /report (ユーザー分析) で共有。
 */
import type { components } from "@/types/api";
import { Badge, Panel, Row, fmtPct, fmtYen, KpiCell } from "@/components/bloomberg";

// ===== ストレス（崩れ方） =====
export type ScenarioResult = {
  scenario: string;
  atcf_year1_yen: number;
  irr: number | null;
  dscr_min: number;
  net_proceeds_yen: number;
  dscr_min_delta?: number;
  irr_delta?: number | null;
  judgment: "good" | "warn" | "bad";
};

export type SensitivityResult = {
  base: ScenarioResult;
  scenarios: ScenarioResult[];
};

const SCENARIO_LABEL: Record<string, string> = {
  base: "標準条件",
  rate_up_100bp: "金利 +1.0%",
  rent_down_5: "賃料 -5%",
  vacancy_up_5pt: "空室 +5pt",
  opex_up_10pct: "OPEX +10%",
  repair_up_20pct: "修繕 +20%",
  exit_down_10pct: "売却価格 -10%",
  combined_stress: "複合ストレス",
};

// ===== 収支耐性価格帯 =====
export type MaxOfferResult = {
  current_price_yen: number;
  max_price_yen: number;
  safe_price_yen: number;
  required_discount_yen: number;
  binding_constraints: string[];
  iterations: number;
  converged: boolean;
};

// ===== クロスアセット比較 =====
export type ComparisonRow = {
  asset_class: string;
  label_jp: string;
  expected_return: number;
  premium_over_re_pt: number;
  liquidity: "high" | "medium" | "low";
  effort: "high" | "medium" | "low";
  note: string;
};

export type CrossAssetResult = {
  re_label_jp: string;
  re_after_tax_irr: number | null;
  rows: ComparisonRow[];
  disclaimer: string;
};

type SummarizeResponse = components["schemas"]["SummarizeResponse"];

type AnalyzeResponse = components["schemas"]["AnalyzeResponse"];

export function PropertyPanel({
  data,
  title,
  subtitle,
}: {
  data: AnalyzeResponse;
  title?: string;
  subtitle?: string;
}) {
  const p = data.analysis.assumptions.property;
  const gpi = data.analysis.assumptions.income.gpi_monthly_yen;
  const completionYear = parseInt(p.building_completion_ym.split("-")[0], 10);
  const age = p.acquisition_year - completionYear;
  return (
    <Panel className="col-span-4" title="[ PROPERTY ]">
      <div className="p-4 text-[11px]">
        <div className="text-[13px] font-bold mb-1">{title ?? "監査対象物件"}</div>
        <div className="text-[10px] text-[var(--text-muted)] mb-3">
          {subtitle ?? `${p.location_pref} / ${p.property_type}`}
        </div>
        <Row label="価格" value={fmtYen(p.purchase_price_yen)} />
        <Row label="構造" value={p.structure.toUpperCase()} />
        <Row label="築年" value={`${completionYear} (${age}Y)`} />
        <Row label="専有面積" value={`${p.building_area_sqm.toFixed(2)} m²`} />
        <Row label="想定賃料" value={`${fmtYen(gpi)}/mo`} />
        <Row
          label="表面利回り"
          value={fmtPct((gpi * 12) / p.purchase_price_yen)}
          warn
        />
        <Row label="NOI利回" value={fmtPct(data.analysis.kpi.cap_rate)} bad />
      </div>
    </Panel>
  );
}

export function KpiPanel({ data }: { data: AnalyzeResponse }) {
  const k = data.analysis.kpi;
  return (
    <Panel className="col-span-5" title="[ KPI ]">
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
          note={k.equity_irr === null ? "未収束 (赤字)" : "保有期間"}
          bad={k.equity_irr === null || k.equity_irr < 0.06}
        />
        <KpiCell
          name="EQ MULT"
          value={`${k.equity_multiple.toFixed(2)}x`}
          note="CUM"
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

export function ScorePanel({ data }: { data: AnalyzeResponse }) {
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

export function CashflowPanel({ data }: { data: AnalyzeResponse }) {
  const cfs = data.analysis.yearly_cashflows;
  return (
    <Panel className="col-span-7" title="[ CASHFLOW ] PROJECTION">
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
                <td className="text-right px-2 py-1.5">
                  {fmtYen(cf.debt_service_yen)}
                </td>
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

export function ExitPanel({ data }: { data: AnalyzeResponse }) {
  const e = data.analysis.exit;
  return (
    <Panel className="col-span-5" title="[ EXIT ] SALE">
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

export function ScoreComponentPanel({ data }: { data: AnalyzeResponse }) {
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

/** 監査の3つの所見 (Findings)。LLMサマリー未接続時はルールベース。 */
export function FindingsPanel({ data }: { data: AnalyzeResponse }) {
  const k = data.analysis.kpi;
  const exit = data.analysis.exit;
  const findings: { severity: "good" | "warn" | "bad"; text: string }[] = [];
  if (k.dscr_min < 1.0) {
    findings.push({
      severity: "bad",
      text: `DSCR 最低値 ${k.dscr_min.toFixed(2)} → 返済をキャッシュフローで賄えない年が存在`,
    });
  } else if (k.dscr_min < 1.25) {
    findings.push({
      severity: "warn",
      text: `DSCR 最低値 ${k.dscr_min.toFixed(2)} → 銀行の安全閾値 1.25 未満`,
    });
  }
  if (k.atcf_first_year_yen < 0) {
    findings.push({
      severity: "bad",
      text: `初年度の税後CF が ${fmtYen(k.atcf_first_year_yen)} → 自腹で持ち出し`,
    });
  }
  if (exit.net_proceeds_yen < 0) {
    findings.push({
      severity: "bad",
      text: `売却時の税後手残りが ${fmtYen(exit.net_proceeds_yen)} → 出口で損失`,
    });
  }
  const gpi = data.analysis.assumptions.income.gpi_monthly_yen;
  const price = data.analysis.assumptions.property.purchase_price_yen;
  const surfaceYield = (gpi * 12) / price;
  if (surfaceYield - k.cap_rate > 0.02) {
    findings.push({
      severity: "warn",
      text: `表面利回り ${fmtPct(surfaceYield)} と NOI Cap ${fmtPct(k.cap_rate)} の乖離が大きい → 経費見落としに注意`,
    });
  }
  if (findings.length === 0) {
    findings.push({
      severity: "good",
      text: "致命的なリスクシグナルは検出されませんでした。前提を変えて感応度も確認を。",
    });
  }
  return (
    <Panel className="col-span-12" title="[ FINDINGS ] 主要所見">
      <ul className="p-4 space-y-1.5 text-[12px]">
        {findings.slice(0, 5).map((f, i) => (
          <li key={i} className="flex items-start gap-2">
            <span className="mt-0.5">
              <Badge level={f.severity}>
                {f.severity === "bad" ? "危険" : f.severity === "warn" ? "警告" : "良好"}
              </Badge>
            </span>
            <span className="text-[var(--text)]">{f.text}</span>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

/** 業者に聞くべき5つの質問 (ルールベース fallback)。 */
export function QuestionsPanel({ data }: { data: AnalyzeResponse }) {
  const k = data.analysis.kpi;
  const qs: string[] = [
    "過去5年間の空室期間 (年単位の空室日数) を教えてください",
    "修繕積立金の値上げ計画はありますか (長期修繕計画の確認)",
    "近隣の同条件物件の成約賃料・成約利回りを教えてください",
    "売主が手放す理由を教えてください",
    "瑕疵担保 (契約不適合責任) の期間と範囲を教えてください",
  ];
  if (k.dscr_min < 1.25) {
    qs[0] = "想定空室率を上げると DSCR が割れます。実績空室率と最長空室期間を確認させてください";
  }
  return (
    <Panel className="col-span-12" title="[ INQUIRY ] 買付前の確認質問">
      <ol className="p-4 space-y-1 text-[12px] list-decimal list-inside">
        {qs.map((q) => (
          <li key={q} className="text-[var(--text)]">
            {q}
          </li>
        ))}
      </ol>
    </Panel>
  );
}

/** AI が生成した 3 行サマリー + 確認質問パネル。 */
export function AiInsightPanel({
  aiData,
  loading,
}: {
  aiData: SummarizeResponse | null;
  loading: boolean;
}) {
  const catLabel = (c: string) =>
    c === "essential" ? "必須" : c === "precision" ? "精度" : "買付前";

  if (loading) {
    return (
      <Panel className="col-span-12" title="[ AI INSIGHT ] AI 分析中…">
        <div className="p-4 text-[11px] font-mono text-[var(--text-muted)] animate-pulse">
          ▶ AI が分析結果を読み取っています (10〜30秒)…
        </div>
      </Panel>
    );
  }
  if (!aiData) return null;

  return (
    <>
      {/* 3行サマリー */}
      <Panel className="col-span-12" title="[ AI SUMMARY ] 3行で読む">
        <div className="p-4 space-y-2">
          {aiData.summary_lines.map((line, i) => (
            <p key={i} className="text-[12px] text-[var(--text)] leading-relaxed">
              <span className="text-[var(--accent)] font-mono font-bold mr-2">
                {i + 1}.
              </span>
              {line}
            </p>
          ))}
          {aiData.ng_filtered && (
            <p className="text-[9px] text-[var(--text-subtle)] font-mono mt-1">
              * NG ワードフィルタ適用済み
            </p>
          )}
        </div>
      </Panel>

      {/* AI 確認質問 */}
      {aiData.questions.length > 0 && (
        <Panel className="col-span-12" title="[ AI INQUIRY ] 仲介への確認質問">
          <ol className="p-4 space-y-2 text-[12px]">
            {aiData.questions.map((q, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="font-mono text-[9px] text-[var(--accent)] mt-0.5 shrink-0">
                  [{catLabel(q.category)}]
                </span>
                <span className="text-[var(--text)]">{q.question}</span>
              </li>
            ))}
          </ol>
        </Panel>
      )}
    </>
  );
}

// ===== 感応度分析パネル =====

export function SensitivityPanel({
  data,
  loading,
}: {
  data: SensitivityResult | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <Panel className="col-span-12" title="[ STRESS ] 崩れ方">
        <div className="p-4 text-[11px] text-[var(--text-muted)] font-mono animate-pulse">
          計算中…
        </div>
      </Panel>
    );
  }
  if (!data) return null;

  const judgeColor = (j: "good" | "warn" | "bad") =>
    j === "good" ? "var(--good)" : j === "warn" ? "var(--warn)" : "var(--bad)";

  const allRows = [data.base, ...data.scenarios];

  return (
    <Panel className="col-span-12" title="[ STRESS ] 崩れ方 — 固定7ストレス">
      <div className="px-3 py-1.5 text-[9px] text-[var(--text-subtle)] border-b border-[var(--border)]">
        以下は投資判断ではなく、入力条件に対する感応度分析です。ΔDSCRは標準条件との差。
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] font-mono tabular-nums">
          <thead>
            <tr className="bg-[var(--surface-alt)] text-[var(--accent)] text-[9px] uppercase tracking-widest">
              <th className="text-left px-3 py-1.5">シナリオ</th>
              <th className="text-right px-3 py-1.5">ATCF Y1</th>
              <th className="text-right px-3 py-1.5">税後IRR</th>
              <th className="text-right px-3 py-1.5">DSCR MIN</th>
              <th className="text-right px-3 py-1.5">ΔDSCR</th>
              <th className="text-right px-3 py-1.5">売却手残</th>
              <th className="text-center px-3 py-1.5">判定</th>
            </tr>
          </thead>
          <tbody>
            {allRows.map((row) => (
              <tr
                key={row.scenario}
                className="border-t border-[var(--border)]"
                style={
                  row.scenario === "base"
                    ? { background: "var(--surface-alt)" }
                    : undefined
                }
              >
                <td className="px-3 py-1.5 font-bold text-[var(--text-muted)]">
                  {SCENARIO_LABEL[row.scenario] ?? row.scenario}
                </td>
                <td
                  className="text-right px-3 py-1.5"
                  style={{ color: row.atcf_year1_yen < 0 ? "var(--bad)" : undefined }}
                >
                  {fmtYen(row.atcf_year1_yen)}
                </td>
                <td className="text-right px-3 py-1.5">
                  {row.irr === null ? "N/A" : fmtPct(row.irr)}
                </td>
                <td
                  className="text-right px-3 py-1.5"
                  style={{ color: row.dscr_min < 1.0 ? "var(--bad)" : row.dscr_min < 1.25 ? "var(--warn)" : undefined }}
                >
                  {row.dscr_min.toFixed(2)}
                </td>
                <td
                  className="text-right px-3 py-1.5"
                  style={{ color: (row.dscr_min_delta ?? 0) < 0 ? "var(--bad)" : undefined }}
                >
                  {row.scenario === "base" || row.dscr_min_delta == null
                    ? "—"
                    : row.dscr_min_delta.toFixed(2)}
                </td>
                <td
                  className="text-right px-3 py-1.5"
                  style={{ color: row.net_proceeds_yen < 0 ? "var(--bad)" : undefined }}
                >
                  {fmtYen(row.net_proceeds_yen)}
                </td>
                <td className="text-center px-3 py-1.5">
                  <span
                    className="font-mono text-[9px] px-1.5 py-px uppercase"
                    style={{
                      color: judgeColor(row.judgment),
                      border: `1px solid ${judgeColor(row.judgment)}`,
                    }}
                  >
                    {row.judgment}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}

// ===== 収支耐性価格帯パネル =====

export function MaxOfferPanel({
  data,
  loading,
}: {
  data: MaxOfferResult | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <Panel className="col-span-6" title="[ RESILIENCE ] 収支耐性価格帯">
        <div className="p-4 text-[11px] text-[var(--text-muted)] font-mono animate-pulse">
          計算中…
        </div>
      </Panel>
    );
  }
  if (!data) return null;

  const notViable = data.max_price_yen === 0;
  const needsDiscount = data.required_discount_yen > 0;

  return (
    <Panel className="col-span-6" title="[ RESILIENCE ] 収支耐性価格帯">
      <div className="p-4">
        {notViable ? (
          <div className="text-[var(--bad)] font-mono text-[12px] font-bold py-4 text-center">
            [ 成立価格なし ] 最低価格でも収支耐性の条件を満たせません
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-px bg-[var(--border)] border border-[var(--border)] mb-3">
            <KpiCell
              name="現状条件 上限"
              value={fmtYen(data.max_price_yen)}
              note="条件を満たす価格帯の上限"
              severity={needsDiscount ? "warn" : "good"}
            />
            <KpiCell
              name="保守条件 上限"
              value={fmtYen(data.safe_price_yen)}
              note="上限×95%"
              severity="good"
            />
            <KpiCell
              name={needsDiscount ? "売出価格との差" : "余裕"}
              value={`${needsDiscount ? "-" : "+"}${fmtYen(Math.abs(data.required_discount_yen))}`}
              note={needsDiscount ? "売出価格から下げが必要な額" : "売出価格で条件成立"}
              severity={needsDiscount ? "bad" : "good"}
            />
          </div>
        )}
        <div className="text-[10px] space-y-1">
          <Row
            label="売出価格"
            value={fmtYen(data.current_price_yen)}
          />
          <Row
            label="収束"
            value={data.converged ? "Yes" : `No (${data.iterations} iter)`}
            severity={data.converged ? undefined : "warn"}
          />
        </div>
        {data.binding_constraints.length > 0 && (
          <div className="mt-3 border-t border-[var(--border)] pt-2">
            <div className="text-[9px] text-[var(--text-muted)] uppercase tracking-widest mb-1">
              Binding Constraints
            </div>
            <ul className="space-y-0.5">
              {data.binding_constraints.map((c, i) => (
                <li key={i} className="text-[10px] text-[var(--warn)] font-mono">
                  · {c}
                </li>
              ))}
            </ul>
          </div>
        )}
        <div className="mt-3 text-[9px] text-[var(--text-subtle)] font-mono">
          制約: DSCR≥1.25 / IRR≥8% / ATCF Y1≥0 (デフォルト)
        </div>
      </div>
    </Panel>
  );
}

// ===== クロスアセット比較パネル =====

export function CrossAssetPanel({
  data,
  loading,
}: {
  data: CrossAssetResult | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <Panel className="col-span-6" title="[ CROSS ASSET ] 代替資産比較">
        <div className="p-4 text-[11px] text-[var(--text-muted)] font-mono animate-pulse">
          計算中…
        </div>
      </Panel>
    );
  }
  if (!data) return null;

  const liquidityLabel = (l: string) =>
    l === "high" ? "高" : l === "medium" ? "中" : "低";
  const effortLabel = (e: string) =>
    e === "high" ? "高" : e === "medium" ? "中" : "低";

  return (
    <Panel className="col-span-6" title="[ CROSS ASSET ] 代替資産比較 (参考)">
      <div className="overflow-x-auto">
        <table className="w-full text-[10px] font-mono tabular-nums">
          <thead>
            <tr className="bg-[var(--surface-alt)] text-[var(--accent)] text-[9px] uppercase tracking-widest">
              <th className="text-left px-3 py-1.5">資産クラス</th>
              <th className="text-right px-3 py-1.5">参考リターン</th>
              <th className="text-right px-3 py-1.5">vs 本物件</th>
              <th className="text-center px-3 py-1.5">流動性</th>
              <th className="text-center px-3 py-1.5">手間</th>
            </tr>
          </thead>
          <tbody>
            {/* 本物件行 */}
            <tr className="border-t border-[var(--border)] bg-[var(--surface-alt)]">
              <td className="px-3 py-1.5 font-bold">{data.re_label_jp}</td>
              <td className="text-right px-3 py-1.5">
                {data.re_after_tax_irr === null ? "N/A" : fmtPct(data.re_after_tax_irr)}
              </td>
              <td className="text-right px-3 py-1.5 text-[var(--text-muted)]">—</td>
              <td className="text-center px-3 py-1.5 text-[var(--text-muted)]">低</td>
              <td className="text-center px-3 py-1.5 text-[var(--text-muted)]">高</td>
            </tr>
            {data.rows.map((row) => {
              const premium = row.premium_over_re_pt;
              const color =
                premium > 2 ? "var(--warn)" : premium < -2 ? "var(--good)" : undefined;
              return (
                <tr key={row.asset_class} className="border-t border-[var(--border)]">
                  <td className="px-3 py-1.5 text-[var(--text-muted)]">{row.label_jp}</td>
                  <td className="text-right px-3 py-1.5">{fmtPct(row.expected_return)}</td>
                  <td
                    className="text-right px-3 py-1.5 font-bold"
                    style={{ color }}
                  >
                    {premium >= 0 ? "+" : ""}{premium.toFixed(2)}pt
                  </td>
                  <td className="text-center px-3 py-1.5 text-[var(--text-muted)]">
                    {liquidityLabel(row.liquidity)}
                  </td>
                  <td className="text-center px-3 py-1.5 text-[var(--text-muted)]">
                    {effortLabel(row.effort)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="px-3 py-2 text-[9px] text-[var(--text-subtle)] font-mono border-t border-[var(--border)]">
        {data.disclaimer}
      </div>
    </Panel>
  );
}

// ===== Market Context（国交省 実取引データ） =====
export type MarketResponse = {
  available: boolean;
  snapshot: {
    period: string | null;
    trade: {
      median_yen_per_sqm: number | null;
      p25_yen_per_sqm: number | null;
      p75_yen_per_sqm: number | null;
      sample_count: number;
    } | null;
    source: string;
    fetched_at: string;
  } | null;
  property_yen_per_sqm: number | null;
  deviation_vs_median_pct: number | null;
};

export function MarketContextPanel({
  data,
  loading,
}: {
  data: MarketResponse | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <Panel className="col-span-6" title="[ MARKET ] 市場相場照合（国交省 実取引）">
        <div className="p-4 text-[11px] text-[var(--text-muted)] font-mono animate-pulse">
          実取引データ取得中…
        </div>
      </Panel>
    );
  }
  if (!data) return null;
  const t = data.snapshot?.trade;
  if (!data.available || !t || t.median_yen_per_sqm == null) {
    return (
      <Panel className="col-span-6" title="[ MARKET ] 市場相場照合（国交省 実取引）">
        <div className="p-4 text-[10px] text-[var(--text-muted)] leading-relaxed">
          該当エリアの公的取引データを取得できませんでした（APIキー未設定 / 対象データ無し）。
        </div>
      </Panel>
    );
  }
  const dev = data.deviation_vs_median_pct;
  return (
    <Panel className="col-span-6" title="[ MARKET ] 市場相場照合（国交省 実取引）">
      <div className="p-4 text-[11px] space-y-1">
        <Row
          label={`エリア中央値 (実取引 ${t.sample_count}件)`}
          value={`${fmtYen(t.median_yen_per_sqm)}/㎡`}
        />
        <Row
          label="エリア p25 / p75"
          value={`${fmtYen(t.p25_yen_per_sqm ?? 0)} / ${fmtYen(t.p75_yen_per_sqm ?? 0)}`}
        />
        {data.property_yen_per_sqm != null && (
          <Row label="本物件 単価" value={`${fmtYen(data.property_yen_per_sqm)}/㎡`} />
        )}
        {dev != null && (
          <Row
            label="相場乖離"
            value={`${dev > 0 ? "+" : ""}${dev.toFixed(1)}%`}
            severity={dev > 10 ? "bad" : dev < -10 ? "good" : undefined}
          />
        )}
        <div className="border-t border-[var(--border)] my-2" />
        <div className="text-[9px] text-[var(--text-subtle)] leading-relaxed">
          出所: {data.snapshot?.source}（{data.snapshot?.period}） / 取得{" "}
          {data.snapshot?.fetched_at
            ? new Date(data.snapshot.fetched_at).toLocaleDateString("ja-JP")
            : "—"}
        </div>
      </div>
    </Panel>
  );
}
