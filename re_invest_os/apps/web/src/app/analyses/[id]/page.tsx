/**
 * /analyses/[id] — 共有 URL からの閲覧ページ
 *
 * GET /api/analyses/[id] → DB から分析結果を取得して描画。
 * ログイン不要 (Phase B: 公開共有)。
 */
import type { components } from "@/types/api";
import { Badge } from "@/components/bloomberg";
import { Nav } from "@/components/nav";
import {
  CashflowPanel,
  ExitPanel,
  FindingsPanel,
  KpiPanel,
  PropertyPanel,
  QuestionsPanel,
  ScoreComponentPanel,
  ScorePanel,
} from "@/components/report-panels";

type AnalyzeResponse = components["schemas"]["AnalyzeResponse"];

const API_BASE = process.env.API_BASE ?? "http://127.0.0.1:8001";

async function fetchAnalysis(id: string): Promise<{
  analysis_result: AnalyzeResponse["analysis"];
  score_result: AnalyzeResponse["score"];
  source_type: string;
  created_at: string;
} | null> {
  try {
    const res = await fetch(`${API_BASE}/analyses/${id}`, { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function SharedReportPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const record = await fetchAnalysis(id);

  if (!record) {
    return (
      <main className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex items-center justify-center">
        <div className="text-center font-mono">
          <div className="text-[var(--bad)] text-sm mb-2">[ 404 ] 分析が見つかりません</div>
          <a href="/upload" className="text-[var(--accent)] text-xs underline">
            新しい分析を開始 →
          </a>
        </div>
      </main>
    );
  }

  const data: AnalyzeResponse = {
    analysis: record.analysis_result,
    score: record.score_result,
  };
  const createdAt = new Date(record.created_at).toLocaleString("ja-JP", {
    timeZone: "Asia/Tokyo",
  });

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <Nav />

      <div className="flex items-center gap-3 px-4 py-2 bg-[var(--surface)] border-b border-[var(--border)] text-[10px] font-mono">
        <Badge level="warn">SHARED</Badge>
        <span className="text-[var(--text-muted)]">id: {id}</span>
        <span className="text-[var(--text-subtle)]">作成: {createdAt}</span>
        <span className="ml-auto">
          <a
            href="/upload"
            className="px-3 py-1.5 bg-[var(--accent)] text-[var(--bg)] uppercase tracking-widest"
          >
            自分の物件を試す →
          </a>
        </span>
      </div>

      <main className="p-4 grid grid-cols-12 gap-2">
        <PropertyPanel data={data} title="共有された物件分析" />
        <KpiPanel data={data} />
        <ScorePanel data={data} />
        <FindingsPanel data={data} />
        <CashflowPanel data={data} />
        <ExitPanel data={data} />
        <ScoreComponentPanel data={data} />
        <QuestionsPanel data={data} />
      </main>

      <footer className="mt-4 mx-4 mb-4 px-3 py-2 bg-[var(--surface)] border border-[var(--border)] text-[9px] text-[var(--text-subtle)] leading-relaxed font-mono">
        [ DISCLAIMER ] PARAMETRIC SIMULATION. NOT INVESTMENT ADVICE. © re_invest_os v0.1
      </footer>
    </div>
  );
}
