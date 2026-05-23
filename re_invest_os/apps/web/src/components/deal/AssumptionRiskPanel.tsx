/**
 * 前提リスク表示。
 * 信頼度 (A/B/C/D) と risk_level (low/medium/high/unknown) をテーブル化。
 */
"use client";

import { Badge, Btn, Panel } from "../bloomberg";

interface RiskItem {
  id: string;
  category: string;
  confidence: "A" | "B" | "C" | "D";
  risk_level: "low" | "medium" | "high" | "unknown";
  reason: string;
}

interface RisksData {
  analysis_run_id: string;
  items: RiskItem[];
  summary: string;
}

const CATEGORY_LABEL: Record<string, string> = {
  rent: "賃料",
  vacancy: "空室率",
  opex: "OPEX",
  repair: "修繕費",
  interest_rate: "金利",
  exit_price: "出口価格",
  tax: "税率",
};

const CONF_TIP: Record<string, string> = {
  A: "一次資料または実データで確認",
  B: "販売図面・URL等に明記",
  C: "ユーザー入力のみ",
  D: "デフォルト仮定",
};

function riskLevel(level: RiskItem["risk_level"]) {
  switch (level) {
    case "high":
      return <Badge level="bad">HIGH</Badge>;
    case "medium":
      return <Badge level="warn">MED</Badge>;
    case "low":
      return <Badge level="good">LOW</Badge>;
    default:
      return (
        <span className="text-[var(--text-muted)] font-mono text-[10px]">UNK</span>
      );
  }
}

export function AssumptionRiskPanel({
  data,
  loading,
  onGenerate,
}: {
  data: RisksData | null;
  loading?: boolean;
  onGenerate?: () => void;
}) {
  return (
    <Panel title="前提リスク" meta={data?.summary ?? ""}>
      <div className="px-4 py-3 space-y-3">
        {!data && !loading && (
          <div className="flex items-center justify-between gap-3">
            <span className="text-[var(--text-muted)] font-mono text-[11px]">
              未生成です。生成すると 7 カテゴリのリスクを評価します。
            </span>
            {onGenerate && (
              <Btn variant="secondary" onClick={onGenerate}>
                生成する
              </Btn>
            )}
          </div>
        )}
        {loading && (
          <div className="text-[var(--text-muted)] font-mono text-[11px]">評価中…</div>
        )}
        {data && (
          <table className="w-full text-[11px] font-mono">
            <thead>
              <tr className="text-[var(--text-muted)] text-[10px] uppercase tracking-widest">
                <th className="text-left py-1 w-24">カテゴリ</th>
                <th className="text-left py-1 w-16">信頼度</th>
                <th className="text-left py-1 w-16">リスク</th>
                <th className="text-left py-1">理由</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it) => (
                <tr key={it.id} className="border-t border-[var(--border)]">
                  <td className="py-1.5 text-[var(--text)]">
                    {CATEGORY_LABEL[it.category] ?? it.category}
                  </td>
                  <td className="py-1.5" title={CONF_TIP[it.confidence]}>
                    <span className="text-[var(--accent)] font-bold">{it.confidence}</span>
                  </td>
                  <td className="py-1.5">{riskLevel(it.risk_level)}</td>
                  <td className="py-1.5 text-[var(--text-muted)] leading-snug">
                    {it.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {data && onGenerate && (
          <div className="flex justify-end">
            <Btn variant="ghost" onClick={onGenerate}>
              再評価
            </Btn>
          </div>
        )}
      </div>
    </Panel>
  );
}
