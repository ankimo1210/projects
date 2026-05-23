/**
 * /deals — deal 一覧 (Deal Workspace への入口)。
 */
"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { Btn, Panel } from "../../components/bloomberg";
import { Nav } from "../../components/nav";

interface Deal {
  id: string;
  title: string;
  source_type: string;
  status: string;
  created_at: string;
  updated_at: string;
}

const STATUS_LABEL: Record<string, string> = {
  analyzing: "分析中",
  waiting_for_broker: "仲介確認待ち",
  ready_to_bid: "買付準備",
  bid_submitted: "買付提出済",
  rejected: "見送り",
  passed: "見送り済",
  archived: "アーカイブ",
};

export default function DealsListPage() {
  const [deals, setDeals] = useState<Deal[]>([]);
  const [title, setTitle] = useState("");
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    const res = await fetch("/api/backend/deals");
    if (!res.ok) return;
    const body = await res.json();
    setDeals(body.items ?? []);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const create = useCallback(async () => {
    if (!title.trim()) return;
    setCreating(true);
    try {
      const res = await fetch("/api/backend/deals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title.trim(), source_type: "manual" }),
      });
      if (res.ok) {
        setTitle("");
        await load();
      }
    } finally {
      setCreating(false);
    }
  }, [title, load]);

  return (
    <>
      <Nav />
      <main className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
        <div className="max-w-4xl mx-auto p-6 space-y-4">
          <Panel title="DEALS" meta={`${deals.length} 件`}>
            <div className="px-4 py-3">
              <div className="flex gap-2 mb-3">
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="物件名 (例: 西新宿レジデンス 504号)"
                  className="flex-1 bg-[var(--surface-alt)] border border-[var(--border)] px-3 py-1.5 text-[12px] font-mono text-[var(--text)]"
                />
                <Btn variant="primary" onClick={create} disabled={creating || !title.trim()}>
                  {creating ? "作成中…" : "新規 DEAL"}
                </Btn>
              </div>
              {deals.length === 0 ? (
                <div className="text-[var(--text-muted)] font-mono text-[11px] py-4 text-center">
                  まだ deal がありません。
                </div>
              ) : (
                <table className="w-full text-[11px] font-mono">
                  <thead>
                    <tr className="text-[var(--text-muted)] text-[10px] uppercase tracking-widest">
                      <th className="text-left py-1">物件名</th>
                      <th className="text-left py-1 w-32">ステータス</th>
                      <th className="text-left py-1 w-40">更新</th>
                    </tr>
                  </thead>
                  <tbody>
                    {deals.map((d) => (
                      <tr key={d.id} className="border-t border-[var(--border)]">
                        <td className="py-1.5">
                          <Link
                            href={`/deals/${d.id}`}
                            className="text-[var(--accent)] hover:underline"
                          >
                            {d.title}
                          </Link>
                        </td>
                        <td className="py-1.5 text-[var(--text-muted)]">
                          {STATUS_LABEL[d.status] ?? d.status}
                        </td>
                        <td className="py-1.5 text-[var(--text-subtle)] tabular-nums">
                          {d.updated_at.slice(0, 19).replace("T", " ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </Panel>
          <p className="text-[var(--text-muted)] font-mono text-[10px] leading-relaxed">
            ※ deal を作成後、API <code className="text-[var(--accent)]">POST /deals/{`{id}`}/analysis_runs</code> に
            <code className="text-[var(--accent)]"> assumptions</code> を投げると分析が実行されます。
            既存の /upload → /confirm フローからの自動連携は Phase B で実装予定です。
          </p>
        </div>
      </main>
    </>
  );
}
