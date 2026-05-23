/**
 * Deal Workspace ヘッダー。
 * 物件名・ステータス・最終更新日時。
 */
import { Badge } from "../bloomberg";

interface Deal {
  id: string;
  title: string;
  source_type: string;
  source_url?: string | null;
  property_type?: string | null;
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

const STATUS_LEVEL: Record<string, "good" | "warn" | "bad"> = {
  analyzing: "warn",
  waiting_for_broker: "warn",
  ready_to_bid: "good",
  bid_submitted: "good",
  rejected: "bad",
  passed: "bad",
  archived: "warn",
};

export function DealHeader({ deal }: { deal: Deal }) {
  return (
    <header className="bg-[var(--surface)] border-b border-[var(--border)] px-4 py-3">
      <div className="flex items-baseline gap-3 flex-wrap">
        <span className="text-[var(--text-subtle)] font-mono text-[10px] uppercase tracking-widest">
          DEAL
        </span>
        <h1 className="text-[var(--text)] font-mono text-base font-bold">{deal.title}</h1>
        <Badge level={STATUS_LEVEL[deal.status] ?? "warn"}>
          {STATUS_LABEL[deal.status] ?? deal.status}
        </Badge>
        <span className="text-[var(--text-muted)] font-mono text-[10px]">
          {deal.property_type ?? "未分類"} · {deal.source_type}
        </span>
        {deal.source_url && (
          <a
            href={deal.source_url}
            target="_blank"
            rel="noreferrer"
            className="text-[var(--accent)] font-mono text-[10px] underline opacity-80 hover:opacity-100"
          >
            元URL ↗
          </a>
        )}
      </div>
      <div className="text-[var(--text-muted)] font-mono text-[10px] mt-1">
        更新 {deal.updated_at.slice(0, 19).replace("T", " ")} · 作成 {deal.created_at.slice(0, 10)}
      </div>
    </header>
  );
}
