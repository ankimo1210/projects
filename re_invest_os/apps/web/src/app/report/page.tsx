/**
 * /report — 監査レポート画面 (ユーザー分析結果)
 *
 * sessionStorage から /confirm で実行した /api/analyze の結果を読み出して描画。
 * 共通パネルは @/components/report-panels.tsx
 */
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { components } from "@/types/api";
import { Badge, Tick } from "@/components/bloomberg";
import { Nav } from "@/components/nav";
import {
  AiInsightPanel,
  CashflowPanel,
  CrossAssetPanel,
  ExitPanel,
  FindingsPanel,
  KpiPanel,
  MaxOfferPanel,
  PropertyPanel,
  QuestionsPanel,
  ScoreComponentPanel,
  ScorePanel,
  SensitivityPanel,
} from "@/components/report-panels";
import type {
  CrossAssetResult,
  MaxOfferResult,
  SensitivityResult,
} from "@/components/report-panels";

type AnalyzeResponse = components["schemas"]["AnalyzeResponse"];
type SummarizeResponse = components["schemas"]["SummarizeResponse"];
type CritiqueResponse = components["schemas"]["CritiqueResponse"];

export default function ReportPage() {
  const router = useRouter();
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [savedId, setSavedId] = useState<string | null>(null);
  const [aiData, setAiData] = useState<SummarizeResponse | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [critiqueData, setCritiqueData] = useState<CritiqueResponse | null>(null);
  const [sensitivityData, setSensitivityData] = useState<SensitivityResult | null>(null);
  const [sensitivityLoading, setSensitivityLoading] = useState(false);
  const [maxOfferData, setMaxOfferData] = useState<MaxOfferResult | null>(null);
  const [maxOfferLoading, setMaxOfferLoading] = useState(false);
  const [crossAssetData, setCrossAssetData] = useState<CrossAssetResult | null>(null);
  const [crossAssetLoading, setCrossAssetLoading] = useState(false);
  const saveAttempted = useRef(false);

  useEffect(() => {
    const raw = sessionStorage.getItem("reio:analysis");
    if (!raw) {
      router.replace("/upload");
      return;
    }
    try {
      const parsed: AnalyzeResponse = JSON.parse(raw);
      setData(parsed);

      // AI サマリー非同期生成
      setAiLoading(true);
      const extractionRaw = sessionStorage.getItem("reio:extraction");
      const extraction = extractionRaw ? JSON.parse(extractionRaw) : null;
      fetch("/api/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_result: parsed.analysis,
          assumption_score: parsed.assumption_score,
          needs_confirmation: extraction?.meta?.needs_confirmation ?? [],
        }),
      })
        .then((r) => r.json())
        .then((j) => { if (j.summary_lines) setAiData(j); })
        .catch(() => {})
        .finally(() => setAiLoading(false));

      // 前提甘さ検出 (バックグラウンド)
      fetch("/api/critique", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          analysis_result: parsed.analysis,
          assumption_score: parsed.assumption_score,
          assumptions: parsed.analysis.assumptions,
        }),
      })
        .then((r) => r.json())
        .then((j) => { if (j.critiques) setCritiqueData(j); })
        .catch(() => {});

      // 感応度分析 (バックグラウンド)
      setSensitivityLoading(true);
      fetch("/api/sensitivity", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assumptions: parsed.analysis.assumptions }),
      })
        .then((r) => r.json())
        .then((j) => { if (j.base) setSensitivityData(j); })
        .catch(() => {})
        .finally(() => setSensitivityLoading(false));

      // 最大買付価格 (バックグラウンド)
      setMaxOfferLoading(true);
      fetch("/api/max_offer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assumptions: parsed.analysis.assumptions }),
      })
        .then((r) => r.json())
        .then((j) => { if (j.current_price_yen !== undefined) setMaxOfferData(j); })
        .catch(() => {})
        .finally(() => setMaxOfferLoading(false));

      // クロスアセット比較 (バックグラウンド)
      setCrossAssetLoading(true);
      fetch("/api/cross_asset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ re_after_tax_irr: parsed.analysis.kpi.equity_irr }),
      })
        .then((r) => r.json())
        .then((j) => { if (j.rows) setCrossAssetData(j); })
        .catch(() => {})
        .finally(() => setCrossAssetLoading(false));

      // バックグラウンドで保存 (一度だけ)
      if (!saveAttempted.current) {
        saveAttempted.current = true;
        const assumptionsRaw = sessionStorage.getItem("reio:assumptions");
        const extractionRaw = sessionStorage.getItem("reio:extraction");
        const assumptions = assumptionsRaw ? JSON.parse(assumptionsRaw) : parsed.analysis.assumptions;
        const extraction = extractionRaw ? JSON.parse(extractionRaw) : null;

        fetch("/api/save", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source_type: extraction?.source_type ?? "manual",
            source_ref: extraction?.source_ref ?? null,
            extracted: extraction?.extracted ?? null,
            assumptions,
            analysis_result: parsed.analysis,
            assumption_score: parsed.assumption_score,
            pii_redactions: extraction?.meta?.pii_redactions ?? {},
            warnings: extraction?.meta?.warnings ?? [],
          }),
        })
          .then((r) => r.json())
          .then((j) => {
            if (j.id) setSavedId(j.id);
          })
          .catch(() => {
            // save failure is silent — report still works
          });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "parse error");
    }
  }, [router]);

  if (error) {
    return (
      <main className="min-h-screen bg-[var(--bg)] text-[var(--bad)] p-8 font-mono">
        セッションデータの読み込みに失敗しました: {error}
      </main>
    );
  }
  if (!data) {
    return (
      <main className="min-h-screen bg-[var(--bg)] text-[var(--text-muted)] flex items-center justify-center">
        読み込み中…
      </main>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <Nav active="report" apiStatus />

      <div className="flex items-center justify-between px-4 py-2 bg-[var(--surface)] border-b border-[var(--border)]">
        <div className="flex items-center gap-2 text-[10px] font-mono">
          <Badge level="good">YOUR ANALYSIS</Badge>
          <span className="text-[var(--text-muted)]">
            engine v{data.analysis.engine_version}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => router.push("/confirm")}
            className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-[var(--border)] hover:bg-[var(--surface-alt)]"
          >
            前提を修正
          </button>
          <button
            type="button"
            onClick={() => {
              if (!data) return;
              const kpi = data.analysis.kpi;
              const prop = data.analysis.assumptions.property;
              const entry = {
                id: savedId ?? Date.now().toString(),
                label: `¥${(prop.purchase_price_yen / 10000).toFixed(0)}万 ${prop.structure.toUpperCase()}`,
                overall_risk: data.assumption_score.overall_risk,
                high_risk_count: data.assumption_score.items.filter(
                  (i) => i.risk_level === "high",
                ).length,
                noi_cap: kpi.cap_rate,
                dscr_y1: kpi.dscr_year1,
                atcf_y1: kpi.atcf_first_year_yen,
                equity_irr: kpi.equity_irr,
                purchase_price_yen: prop.purchase_price_yen,
                gpi_monthly_yen: data.analysis.assumptions.income.gpi_monthly_yen,
                structure: prop.structure,
                build_year: parseInt(prop.building_completion_ym.split("-")[0], 10),
              };
              const prev = JSON.parse(sessionStorage.getItem("reio:compare") ?? "[]");
              const updated = [...prev.filter((e: { id: string }) => e.id !== entry.id), entry].slice(-5);
              sessionStorage.setItem("reio:compare", JSON.stringify(updated));
              router.push("/compare");
            }}
            className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest border border-[var(--accent)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-[var(--bg)]"
          >
            比較に追加
          </button>
          <button
            type="button"
            onClick={() => router.push("/upload")}
            className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-widest bg-[var(--accent)] text-[var(--bg)]"
          >
            別物件を試す
          </button>
        </div>
      </div>

      {/* 共有 URL バナー */}
      {savedId && (
        <div className="flex items-center gap-3 px-4 py-2 bg-[var(--surface-alt)] border-b border-[var(--border)] text-[11px] font-mono">
          <span className="text-[var(--good)]">✓ SAVED</span>
          <span className="text-[var(--text-muted)]">共有URL:</span>
          <a
            href={`/analyses/${savedId}`}
            className="text-[var(--accent)] underline underline-offset-2 hover:opacity-80"
          >
            /analyses/{savedId}
          </a>
          <button
            type="button"
            onClick={() => navigator.clipboard.writeText(`${window.location.origin}/analyses/${savedId}`)}
            className="ml-2 px-2 py-0.5 border border-[var(--border)] hover:bg-[var(--surface)] text-[9px] uppercase tracking-widest"
          >
            コピー
          </button>
        </div>
      )}

      <div className="flex gap-6 px-4 py-1 bg-[var(--surface-alt)] border-b border-[var(--border)] text-[11px] font-mono text-[var(--text-muted)]">
        <Tick label="JGB10Y" value="1.42%" />
        <Tick label="FLAT35" value="1.92%" />
        <Tick label="ENGINE" value={data.analysis.engine_version} />
      </div>

      <main className="p-4 grid grid-cols-12 gap-2">
        <PropertyPanel data={data} title="監査対象物件" />
        <KpiPanel data={data} />
        <ScorePanel data={data} />
        {/* AI サマリー (非同期ロード) */}
        <AiInsightPanel aiData={aiData} loading={aiLoading} />
        {/* 前提甘さ検出 (非同期ロード) */}
        {critiqueData && critiqueData.critiques.length > 0 && (
          <section className="col-span-12 bg-[var(--surface)] border border-[var(--warn)]">
            <header className="flex items-center bg-[var(--surface-alt)] border-b border-[var(--border)] px-3 py-1.5">
              <span className="text-[var(--warn)] font-mono font-bold text-[10px] tracking-widest uppercase">
                [ ASSUMPTION CRITIQUE ] 前提甘さ検出
              </span>
            </header>
            <ul className="p-4 space-y-3">
              {critiqueData.critiques.map((c, i) => (
                <li key={i} className="text-[11px]">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span
                      className="font-mono text-[9px] px-1.5 py-px uppercase"
                      style={{
                        background: c.severity === "critical" ? "var(--bad)" : c.severity === "warn" ? "var(--warn)" : "var(--surface-alt)",
                        color: c.severity === "critical" ? "white" : c.severity === "warn" ? "var(--bg)" : "var(--text-muted)",
                      }}
                    >
                      {c.severity}
                    </span>
                    <span className="font-mono text-[var(--text-muted)] text-[9px]">{c.flag_type}</span>
                  </div>
                  <p className="text-[var(--text)] leading-relaxed">{c.explanation}</p>
                  <p className="text-[var(--text-muted)] mt-0.5">→ {c.verification}</p>
                </li>
              ))}
            </ul>
          </section>
        )}
        {/* ルールベース Findings (即時表示) */}
        {!aiData && !aiLoading && <FindingsPanel data={data} />}
        <CashflowPanel data={data} />
        <ExitPanel data={data} />
        <ScoreComponentPanel data={data} />
        {/* ルールベース Questions (AI 未完時の fallback) */}
        {!aiData && !aiLoading && <QuestionsPanel data={data} />}
        {/* 感応度分析 */}
        <SensitivityPanel data={sensitivityData} loading={sensitivityLoading} />
        {/* 最大買付価格 + クロスアセット比較 */}
        <MaxOfferPanel data={maxOfferData} loading={maxOfferLoading} />
        <CrossAssetPanel data={crossAssetData} loading={crossAssetLoading} />
      </main>

      <footer className="mt-4 mx-4 mb-4 px-3 py-2 bg-[var(--surface)] border border-[var(--border)] text-[9px] text-[var(--text-subtle)] leading-relaxed font-mono">
        [ DISCLAIMER ] PARAMETRIC SIMULATION FOR REFERENCE. NOT INVESTMENT ADVICE.
        NOT A SOLICITATION FOR ANY SECURITY OR REAL ESTATE TRANSACTION. CONSULT
        LICENSED PROFESSIONALS FOR TAX/LEGAL DECISIONS. © re_invest_os v0.1
      </footer>
    </div>
  );
}
