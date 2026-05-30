/**
 * /history — 分析履歴一覧
 * GET /api/history → /api/analyses → DB
 */
import Link from "next/link";
import { Nav } from "@/components/nav";

const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8001";

interface HistoryItem {
  id: string;
  created_at: string;
  source_type: string;
  source_ref: string | null;
  high_risk_count: number;
  noi_cap: number | null;
  dscr_y1: number | null;
  atcf_y1: number | null;
  engine_version: string;
}

async function fetchHistory(): Promise<HistoryItem[]> {
  try {
    const r = await fetch(`${API_BASE}/analyses?limit=50`, { cache: "no-store" });
    if (!r.ok) return [];
    const data = await r.json();
    return data.items ?? [];
  } catch {
    return [];
  }
}

function HighRiskBadge({ count }: { count: number }) {
  const color =
    count === 0 ? "var(--good)" : count <= 2 ? "var(--warn)" : "var(--bad)";
  return (
    <span className="font-mono font-bold tabular-nums" style={{ color }}>
      {count}
    </span>
  );
}

export default async function HistoryPage() {
  const items = await fetchHistory();

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <Nav active="history" />

      <main className="max-w-5xl mx-auto px-4 py-8">
        <h1 className="text-xl font-mono font-bold text-[var(--accent)] mb-6 uppercase tracking-widest">
          [ ANALYSIS HISTORY ]
        </h1>

        {items.length === 0 ? (
          <div className="text-center py-16 text-[var(--text-muted)] font-mono text-sm">
            <div className="mb-4">分析履歴がまだありません</div>
            <Link
              href="/upload"
              className="px-4 py-2 bg-[var(--accent)] text-[var(--bg)] text-[11px] uppercase tracking-widest hover:opacity-90"
            >
              最初の物件を監査する →
            </Link>
          </div>
        ) : (
          <div className="border border-[var(--border)] overflow-hidden">
            <table className="w-full text-[11px] font-mono">
              <thead>
                <tr className="bg-[var(--surface-alt)] text-[var(--accent)] text-[9px] uppercase tracking-widest">
                  <th className="text-left px-3 py-2">日時</th>
                  <th className="text-left px-3 py-2">物件 / ソース</th>
                  <th className="text-right px-3 py-2">高リスク前提</th>
                  <th className="text-right px-3 py-2">NOI Cap</th>
                  <th className="text-right px-3 py-2">DSCR Y1</th>
                  <th className="text-right px-3 py-2">ATCF Y1</th>
                  <th className="text-center px-3 py-2">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-t border-[var(--border)] hover:bg-[var(--surface-alt)]">
                    <td className="px-3 py-2 text-[var(--text-muted)] whitespace-nowrap">
                      {new Date(item.created_at).toLocaleString("ja-JP", {
                        month: "2-digit", day: "2-digit",
                        hour: "2-digit", minute: "2-digit",
                        timeZone: "Asia/Tokyo",
                      })}
                    </td>
                    <td className="px-3 py-2 max-w-48 truncate">
                      <span className="text-[var(--text-subtle)] mr-1">[{item.source_type}]</span>
                      {item.source_ref ? (
                        <span className="text-[var(--text-muted)]">
                          {item.source_ref.length > 40
                            ? `${item.source_ref.slice(0, 40)}…`
                            : item.source_ref}
                        </span>
                      ) : (
                        <span className="text-[var(--text-subtle)]">manual</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <HighRiskBadge count={item.high_risk_count} />
                    </td>
                    <td className="px-3 py-2 text-right text-[var(--text-muted)]">
                      {item.noi_cap != null ? `${(item.noi_cap * 100).toFixed(2)}%` : "—"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {item.dscr_y1 != null ? (
                        <span style={{ color: item.dscr_y1 < 1 ? "var(--bad)" : "var(--text)" }}>
                          {item.dscr_y1.toFixed(2)}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-3 py-2 text-right">
                      {item.atcf_y1 != null ? (
                        <span style={{ color: item.atcf_y1 < 0 ? "var(--bad)" : "var(--good)" }}>
                          ¥{item.atcf_y1.toLocaleString()}
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <Link
                        href={`/analyses/${item.id}`}
                        className="text-[var(--accent)] hover:underline underline-offset-2"
                      >
                        詳細 →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  );
}
