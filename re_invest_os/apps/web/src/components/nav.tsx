/**
 * 共通ナビバー (Bloomberg 端末スタイル)
 * 全ページで使うキーバインドナビ。active は現在のページ。
 */
import Link from "next/link";

interface NavProps {
  active?: "upload" | "report" | "compare" | "history" | "sample" | "lp" | "manual" | string;
  apiStatus?: boolean;
}

export function Nav({ active, apiStatus }: NavProps) {
  const link = (key: string, name: string, href: string, page: NavProps["active"]) => (
    <Link
      href={href}
      className={`flex hover:opacity-80 transition-opacity ${active === page ? "opacity-100" : "opacity-60"}`}
    >
      <span className="bg-[var(--accent)] text-[var(--bg)] px-1.5 py-0.5 font-mono font-bold text-[10px]">
        {key}
      </span>
      <span className={`px-2 py-0.5 font-mono text-[11px] ${active === page ? "text-[var(--text)]" : "text-[var(--text-muted)]"}`}>
        {name}
      </span>
    </Link>
  );

  return (
    <nav className="flex items-center gap-4 h-9 px-4 bg-[var(--surface)] border-b border-[var(--border)]">
      <Link href="/" className="font-mono font-bold text-[var(--accent)] text-xs tracking-widest mr-2">
        RE_INVEST_OS
      </Link>
      {link("F1", "UPLOAD", "/upload", "upload")}
      {link("F2", "COMP", "/compare", "compare")}
      {link("F3", "HIST", "/history", "history")}
      {link("F4", "SAMPLE", "/", "sample")}
      {link("F5", "LP", "/lp", "lp")}
      {/* F6 REPORT は動的なので href なし (active 表示のみ) */}
      {active === "report" && (
        <span className="flex opacity-100">
          <span className="bg-[var(--accent)] text-[var(--bg)] px-1.5 py-0.5 font-mono font-bold text-[10px]">
            F6
          </span>
          <span className="px-2 py-0.5 font-mono text-[11px] text-[var(--text)]">REPORT</span>
        </span>
      )}

      <div className="ml-auto flex items-center gap-4 text-[10px] text-[var(--text-muted)] font-mono">
        {apiStatus !== undefined && (
          <span className={apiStatus ? "text-[var(--good)] animate-pulse" : "text-[var(--bad)]"}>
            ● {apiStatus ? "LIVE" : "API OFFLINE"}
          </span>
        )}
        {/* suppressHydrationWarning: 時刻はサーバー/クライアントで差異が出るため抑制 */}
        <span suppressHydrationWarning>
          {new Date().toISOString().slice(0, 16).replace("T", " ")} JST
        </span>
      </div>
    </nav>
  );
}
