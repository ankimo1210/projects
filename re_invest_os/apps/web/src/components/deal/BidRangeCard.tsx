/**
 * 買付価格レンジ表示。
 * 「買い/見送り」判定や色だけに依存した表示は避ける。
 */
"use client";

import { Btn, Panel } from "../bloomberg";

interface BidRangesData {
  id: string;
  analysis_run_id: string;
  asking_price_yen: number;
  aggressive_price: number | null;
  base_price: number | null;
  conservative_price: number | null;
  gap_to_base_price_yen: number | null;
  gap_to_base_price_pct: number | null;
  explanation: {
    aggressive?: { text: string; binding_constraints: string[] };
    base?: { text: string; binding_constraints: string[] };
    conservative?: { text: string; binding_constraints: string[] };
    monotonicity_enforced?: boolean;
  };
}

function fmtPrice(n: number | null): string {
  if (n == null) return "成立不能";
  return `¥${(n / 10_000).toLocaleString("ja-JP", { maximumFractionDigits: 0 })}万`;
}

function fmtGapYen(n: number | null): string {
  if (n == null) return "—";
  const sign = n >= 0 ? "+" : "−";
  return `${sign}¥${(Math.abs(n) / 10_000).toLocaleString("ja-JP", { maximumFractionDigits: 0 })}万`;
}

export function BidRangeCard({
  data,
  loading,
  onGenerate,
}: {
  data: BidRangesData | null;
  loading?: boolean;
  onGenerate?: () => void;
}) {
  return (
    <Panel title="買付価格レンジ" meta="ユーザー入力条件に基づく試算">
      <div className="px-4 py-3 space-y-3">
        {!data && !loading && (
          <div className="flex items-center justify-between gap-3">
            <span className="text-[var(--text-muted)] font-mono text-[11px]">
              未生成です。生成すると 3 段階のレンジを試算します。
            </span>
            {onGenerate && (
              <Btn variant="secondary" onClick={onGenerate}>
                生成する
              </Btn>
            )}
          </div>
        )}
        {loading && (
          <div className="text-[var(--text-muted)] font-mono text-[11px]">計算中…</div>
        )}
        {data && (
          <>
            <div className="flex items-baseline gap-4 text-[12px] font-mono">
              <span className="text-[var(--text-muted)]">売出価格</span>
              <span className="text-[var(--text)] tabular-nums">
                {fmtPrice(data.asking_price_yen)}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              <RangeBlock
                title="強気レンジ"
                price={data.aggressive_price}
                explanation={data.explanation.aggressive?.text}
                binding={data.explanation.aggressive?.binding_constraints}
              />
              <RangeBlock
                title="標準レンジ"
                price={data.base_price}
                explanation={data.explanation.base?.text}
                binding={data.explanation.base?.binding_constraints}
                emphasized
              />
              <RangeBlock
                title="安全レンジ"
                price={data.conservative_price}
                explanation={data.explanation.conservative?.text}
                binding={data.explanation.conservative?.binding_constraints}
              />
            </div>

            <div className="border-t border-[var(--border)] pt-2 flex justify-between text-[11px] font-mono">
              <span className="text-[var(--text-muted)]">標準レンジとの差額</span>
              <span className="text-[var(--text)] tabular-nums">
                {fmtGapYen(data.gap_to_base_price_yen)}
                {data.gap_to_base_price_pct != null
                  ? ` (${(data.gap_to_base_price_pct * 100).toFixed(1)}%)`
                  : ""}
              </span>
            </div>

            {data.explanation.monotonicity_enforced && (
              <div className="text-[var(--text-muted)] font-mono text-[10px]">
                ※ 単調性 (安全 ≤ 標準 ≤ 強気) を保つため上位レンジを下位に合わせて調整しました
              </div>
            )}

            {onGenerate && (
              <div className="flex justify-end">
                <Btn variant="ghost" onClick={onGenerate}>
                  再生成
                </Btn>
              </div>
            )}
          </>
        )}
      </div>
    </Panel>
  );
}

function RangeBlock({
  title,
  price,
  explanation,
  binding,
  emphasized,
}: {
  title: string;
  price: number | null;
  explanation?: string;
  binding?: string[];
  emphasized?: boolean;
}) {
  return (
    <div
      className={`p-3 ${
        emphasized
          ? "bg-[var(--surface-alt)] border border-[var(--accent)]"
          : "bg-[var(--surface)] border border-[var(--border)]"
      }`}
    >
      <div className="text-[10px] text-[var(--text-muted)] uppercase tracking-widest font-mono mb-1">
        {title}
      </div>
      <div
        className="text-[20px] font-mono font-bold tabular-nums leading-none"
        style={{ color: price == null ? "var(--text-muted)" : "var(--text)" }}
      >
        {fmtPrice(price)}
      </div>
      {explanation && (
        <div className="text-[10px] text-[var(--text-muted)] mt-2 font-mono leading-snug">
          {explanation}
        </div>
      )}
      {binding && binding.length > 0 && (
        <div className="text-[10px] text-[var(--warn)] mt-1 font-mono">
          制約: {binding.join(" / ")}
        </div>
      )}
    </div>
  );
}
