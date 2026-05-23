/**
 * Deal Workspace: /deals/[id]
 *
 * 1 つの deal について
 *   - DealHeader / Summary KPI
 *   - 買付価格レンジ (BidRangeCard)
 *   - 前提リスク (AssumptionRiskPanel)
 *   - WatchlistButton (準備中)
 * を集約表示する。
 */
"use client";

import { use, useCallback, useEffect, useState } from "react";

import { Nav } from "../../../components/nav";
import { AssumptionRiskPanel } from "../../../components/deal/AssumptionRiskPanel";
import { BidRangeCard } from "../../../components/deal/BidRangeCard";
import { DealHeader } from "../../../components/deal/DealHeader";
import { DealSummaryCard } from "../../../components/deal/DealSummaryCard";
import { WatchlistButton } from "../../../components/deal/WatchlistButton";

interface Deal {
  id: string;
  title: string;
  source_type: string;
  source_url: string | null;
  property_type: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  latest_analysis_run_id: string | null;
}

// metrics_json は backend で full 分析結果を含むため、UI 側は緩い型でラップする
type MetricsJson = Parameters<typeof DealSummaryCard>[0]["metrics"];

interface AnalysisRun {
  id: string;
  deal_id: string;
  engine_version: string;
  input_snapshot_json: Record<string, unknown>;
  metrics_json: MetricsJson;
  created_at: string;
}

export default function DealPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);

  const [deal, setDeal] = useState<Deal | null>(null);
  const [run, setRun] = useState<AnalysisRun | null>(null);
  const [bidRanges, setBidRanges] = useState<Parameters<typeof BidRangeCard>[0]["data"]>(null);
  const [risks, setRisks] = useState<Parameters<typeof AssumptionRiskPanel>[0]["data"]>(null);
  const [bidLoading, setBidLoading] = useState(false);
  const [riskLoading, setRiskLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDeal = useCallback(async () => {
    const res = await fetch(`/api/backend/deals/${id}`);
    if (!res.ok) {
      setError(`deal 取得失敗: ${res.status}`);
      return null;
    }
    const d = (await res.json()) as Deal;
    setDeal(d);
    return d;
  }, [id]);

  const fetchRun = useCallback(async (runId: string) => {
    const res = await fetch(`/api/backend/analysis_runs/${runId}`);
    if (!res.ok) return null;
    const r = (await res.json()) as AnalysisRun;
    setRun(r);
    return r;
  }, []);

  const fetchBidRanges = useCallback(async (runId: string) => {
    const res = await fetch(`/api/backend/analysis_runs/${runId}/bid_ranges`);
    if (res.ok) setBidRanges(await res.json());
    else if (res.status === 404) setBidRanges(null);
  }, []);

  const fetchRisks = useCallback(async (runId: string) => {
    const res = await fetch(`/api/backend/analysis_runs/${runId}/assumption_risks`);
    if (res.ok) {
      const body = await res.json();
      if (body.items && body.items.length > 0) setRisks(body);
      else setRisks(null);
    }
  }, []);

  const generateBidRanges = useCallback(async () => {
    if (!run) return;
    setBidLoading(true);
    try {
      const res = await fetch(`/api/backend/analysis_runs/${run.id}/bid_ranges`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (res.ok) setBidRanges(await res.json());
    } finally {
      setBidLoading(false);
    }
  }, [run]);

  const generateRisks = useCallback(async () => {
    if (!run) return;
    setRiskLoading(true);
    try {
      const res = await fetch(`/api/backend/analysis_runs/${run.id}/assumption_risks`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (res.ok) setRisks(await res.json());
    } finally {
      setRiskLoading(false);
    }
  }, [run]);

  useEffect(() => {
    (async () => {
      const d = await fetchDeal();
      if (d?.latest_analysis_run_id) {
        const r = await fetchRun(d.latest_analysis_run_id);
        if (r) {
          await Promise.all([fetchBidRanges(r.id), fetchRisks(r.id)]);
        }
      }
    })();
  }, [fetchDeal, fetchRun, fetchBidRanges, fetchRisks]);

  return (
    <>
      <Nav />
      <main className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
        {error && (
          <div className="bg-[var(--bad)] text-white px-4 py-2 text-[11px] font-mono">{error}</div>
        )}
        {deal && (
          <>
            <DealHeader deal={deal} />
            <div className="px-4 py-4 space-y-4 max-w-6xl mx-auto">
              <div className="flex justify-end">
                <WatchlistButton />
              </div>

              {!run && (
                <div className="bg-[var(--surface)] border border-[var(--border)] p-6 text-center">
                  <p className="text-[var(--text-muted)] font-mono text-[12px]">
                    この deal には分析実行 (analysis_run) がまだありません。
                  </p>
                  <p className="text-[var(--text-subtle)] font-mono text-[10px] mt-2">
                    /upload または /new から分析を作成し、API 経由で deal に紐付けてください。
                  </p>
                </div>
              )}

              {run && (
                <>
                  <DealSummaryCard metrics={run.metrics_json} />
                  <BidRangeCard
                    data={bidRanges}
                    loading={bidLoading}
                    onGenerate={generateBidRanges}
                  />
                  <AssumptionRiskPanel
                    data={risks}
                    loading={riskLoading}
                    onGenerate={generateRisks}
                  />
                </>
              )}
            </div>
          </>
        )}
        {!deal && !error && (
          <div className="p-6 text-[var(--text-muted)] font-mono text-[11px]">読み込み中…</div>
        )}
      </main>
    </>
  );
}
