/**
 * /compare — 物件比較ボード
 *
 * sessionStorage の "reio:compare" に {id, analysis, score, assumptions}[] を蓄積。
 * 最大5件横並び。レポート画面の「比較に追加」ボタンから追加。
 */
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { fmtPct, fmtYen } from "@/components/bloomberg";
import { Nav } from "@/components/nav";

interface CompareEntry {
  id: string;
  label: string;
  overall_risk: string;
  high_risk_count: number;
  noi_cap: number;
  dscr_y1: number;
  atcf_y1: number;
  equity_irr: number | null;
  purchase_price_yen: number;
  gpi_monthly_yen: number;
  structure: string;
  build_year: number;
}

function CompareCell({ value, bad, good }: { value: string; bad?: boolean; good?: boolean }) {
  const color = bad ? "var(--bad)" : good ? "var(--good)" : "var(--text)";
  return (
    <td className="text-right px-2 py-1.5 font-mono tabular-nums text-[11px]" style={{ color }}>
      {value}
    </td>
  );
}

const ROWS: { label: string; key: keyof CompareEntry; fmt: (v: CompareEntry) => string; bad?: (v: CompareEntry) => boolean; good?: (v: CompareEntry) => boolean }[] = [
  { label: "総合前提リスク", key: "overall_risk", fmt: (v) => v.overall_risk.toUpperCase(), bad: (v) => v.overall_risk === "high", good: (v) => v.overall_risk === "low" },
  { label: "高リスク前提数", key: "high_risk_count", fmt: (v) => `${v.high_risk_count}`, bad: (v) => v.high_risk_count >= 3, good: (v) => v.high_risk_count === 0 },
  { label: "価格", key: "purchase_price_yen", fmt: (v) => fmtYen(v.purchase_price_yen) },
  { label: "月額賃料", key: "gpi_monthly_yen", fmt: (v) => fmtYen(v.gpi_monthly_yen) },
  { label: "表面利回り", key: "noi_cap", fmt: (v) => fmtPct((v.gpi_monthly_yen * 12) / v.purchase_price_yen) },
  { label: "NOI Cap", key: "noi_cap", fmt: (v) => fmtPct(v.noi_cap), bad: (v) => v.noi_cap < 0.03 },
  { label: "DSCR Y1", key: "dscr_y1", fmt: (v) => v.dscr_y1.toFixed(2), bad: (v) => v.dscr_y1 < 1.0, good: (v) => v.dscr_y1 >= 1.25 },
  { label: "ATCF Y1", key: "atcf_y1", fmt: (v) => fmtYen(v.atcf_y1), bad: (v) => v.atcf_y1 < 0, good: (v) => v.atcf_y1 > 0 },
  { label: "Eq IRR", key: "equity_irr", fmt: (v) => v.equity_irr != null ? fmtPct(v.equity_irr) : "N/A", bad: (v) => v.equity_irr == null || v.equity_irr < 0.06 },
  { label: "構造", key: "structure", fmt: (v) => v.structure.toUpperCase() },
  { label: "築年", key: "build_year", fmt: (v) => `${v.build_year}年 (${new Date().getFullYear() - v.build_year}Y)` },
];

export default function ComparePage() {
  const [entries, setEntries] = useState<CompareEntry[]>([]);

  useEffect(() => {
    try {
      const raw = sessionStorage.getItem("reio:compare");
      if (raw) setEntries(JSON.parse(raw));
    } catch {}
  }, []);

  function remove(id: string) {
    const updated = entries.filter((e) => e.id !== id);
    setEntries(updated);
    sessionStorage.setItem("reio:compare", JSON.stringify(updated));
  }

  function clearAll() {
    setEntries([]);
    sessionStorage.removeItem("reio:compare");
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <Nav active="compare" />

      <main className="px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-xl font-mono font-bold text-[var(--accent)] uppercase tracking-widest">
            [ COMPARISON BOARD ]
          </h1>
          <div className="flex items-center gap-3">
            <span className="text-[11px] text-[var(--text-muted)] font-mono">{entries.length}/5 物件</span>
            {entries.length > 0 && (
              <button
                type="button"
                onClick={clearAll}
                className="px-3 py-1 text-[10px] font-mono uppercase tracking-widest border border-[var(--border)] hover:bg-[var(--surface-alt)] text-[var(--text-muted)]"
              >
                クリア
              </button>
            )}
            <Link
              href="/upload"
              className="px-3 py-1 bg-[var(--accent)] text-[var(--bg)] text-[10px] font-mono uppercase tracking-widest hover:opacity-90"
            >
              物件を追加 +
            </Link>
          </div>
        </div>

        {entries.length === 0 ? (
          <div className="text-center py-24 text-[var(--text-muted)] font-mono text-sm border border-dashed border-[var(--border)]">
            <div className="mb-4">比較する物件がありません</div>
            <p className="text-[11px] text-[var(--text-subtle)] mb-6">
              監査レポート画面の「比較に追加」ボタンから物件を追加できます
            </p>
            <Link
              href="/upload"
              className="px-4 py-2 bg-[var(--accent)] text-[var(--bg)] text-[11px] uppercase tracking-widest"
            >
              物件を監査する →
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border border-[var(--border)]">
              <thead>
                <tr className="bg-[var(--surface-alt)]">
                  <th className="text-left px-3 py-2 text-[9px] font-mono uppercase tracking-widest text-[var(--text-muted)] w-32">
                    指標
                  </th>
                  {entries.map((e) => (
                    <th key={e.id} className="text-right px-2 py-2 min-w-32">
                      <div className="text-[10px] font-mono font-bold text-[var(--accent)] truncate max-w-32">
                        {e.label}
                      </div>
                      <button
                        type="button"
                        onClick={() => remove(e.id)}
                        className="text-[9px] text-[var(--text-subtle)] hover:text-[var(--bad)] font-mono"
                      >
                        ✕ 外す
                      </button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ROWS.map((row) => (
                  <tr key={row.label} className="border-t border-[var(--border)]">
                    <td className="px-3 py-1.5 text-[10px] text-[var(--text-muted)] font-mono">
                      {row.label}
                    </td>
                    {entries.map((e) => (
                      <CompareCell
                        key={e.id}
                        value={row.fmt(e)}
                        bad={row.bad?.(e)}
                        good={row.good?.(e)}
                      />
                    ))}
                  </tr>
                ))}
                <tr className="border-t-2 border-[var(--accent)]">
                  <td className="px-3 py-2 text-[9px] text-[var(--text-muted)] font-mono uppercase">
                    詳細
                  </td>
                  {entries.map((e) => (
                    <td key={e.id} className="text-center px-2 py-2">
                      <Link
                        href={`/analyses/${e.id}`}
                        className="text-[10px] text-[var(--accent)] hover:underline font-mono"
                      >
                        レポート →
                      </Link>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
