"use client";
import { useMemo, useState } from "react";
import { Download } from "lucide-react";
import {
  CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  filterHealthPlanetMeasurements, healthPlanetChartRows, healthPlanetCSV,
  healthPlanetLabels, isHealthPlanet,
} from "@/lib/healthplanet";
import type { HealthPlanet, HealthPlanetMeasurement, HealthPlanetMetric } from "@/lib/types";
import { statusLabel, units } from "@/lib/presentation";
import { useMeta, useSnapshot } from "./data-provider";
import { usePeriod } from "./period-provider";
import { DataState } from "./data-state";
import { Button } from "./ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";

const connectionLabels: Record<HealthPlanet["status"], string> = {
  not_connected: "未接続", pending: "未取得", partial: "一部取得", available: "表示データあり",
};

export function HealthPlanetPanel() {
  const { meta, loading, error } = useMeta();
  const included = Boolean(meta && Object.hasOwn(meta.files, "healthplanet.json"));
  // An empty name disables the existing hook's fetch; old manifests remain valid.
  const result = useSnapshot(included ? "healthplanet.json" : "", isHealthPlanet);
  if (included && result.data)
    return <HealthPlanetView key={meta!.generation} data={result.data} />;
  return (
    <Card>
      <CardHeader><CardTitle>Health Planet · タニタ</CardTitle></CardHeader>
      <CardContent>
        {loading || error || included ? (
          <DataState loading={loading || result.loading} error={error || result.error} />
        ) : (
          <p className="chart-note" role="status">
            この書き出しには Health Planet データが含まれていません。
            連携後にローカルで同期・書き出しすると、ここに表示されます。
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function ObservationChart({ measurements }: { measurements: HealthPlanetMeasurement[] }) {
  const rows = useMemo(() => healthPlanetChartRows(measurements), [measurements]);
  const first = measurements[0];
  const label = healthPlanetLabels[first.metric];
  const unit = units[first.unit] ?? first.unit;
  const oneDay = first.timestamp.slice(0, 10) === measurements.at(-1)!.timestamp.slice(0, 10);
  return (
    <Card>
      <CardHeader>
        <CardTitle>{label} · Health Planet</CardTitle>
        <CardDescription>
          {measurements.length.toLocaleString("ja-JP")}件の観測記録 · 描画 {rows.length.toLocaleString("ja-JP")}点 · {unit}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="chart-surface h-[250px]" role="img" aria-label={`Health Planet ${label}、${unit}。現地時計の観測記録。`}>
          <ResponsiveContainer width="100%" height="100%" minWidth={0} initialDimension={{ width: 600, height: 250 }}>
            <ComposedChart data={rows} margin={{ left: -10, right: 18, top: 12 }} accessibilityLayer>
              <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
              <XAxis
                dataKey="x" type="number" domain={["dataMin", "dataMax"]}
                tickFormatter={(v) => {
                  // x is a civil coordinate. Format components without browser timezone conversion.
                  const civil = new Date(Number(v)).toISOString();
                  return oneDay ? civil.slice(11, 16) : civil.slice(5, 10).replace("-", "/");
                }}
                minTickGap={45} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              />
              <YAxis domain={["auto", "auto"]} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} />
              <Tooltip
                content={({ active, payload }) => {
                  const m = payload?.[0]?.payload as HealthPlanetMeasurement | undefined;
                  if (!active || !m) return null;
                  return (
                    <div className="rounded-lg border bg-card p-3 text-xs text-card-foreground">
                      <p>{m.timestamp.replace("T", " ")}（現地時計）</p>
                      <p>{label}: {m.value} {unit}</p>
                      <p>機種: {m.model || "不明"}</p>
                      <p className="max-w-64 break-all">観測ID: {m.id}</p>
                    </div>
                  );
                }}
              />
              <Line dataKey="value" name={label} type="linear" stroke="var(--line-1)" strokeWidth={1.5}
                dot={rows.length < 100 ? { r: 2 } : false} connectNulls={false} isAnimationActive={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function ObservationTable({ measurements }: { measurements: HealthPlanetMeasurement[] }) {
  const [page, setPage] = useState(0);
  const pageSize = 100;
  const lastPage = Math.max(0, Math.ceil(measurements.length / pageSize) - 1);
  const current = Math.min(page, lastPage);
  const start = current * pageSize;
  return (
    <>
      <div className="inventory-controls my-3">
        <span className="chart-note">{start + 1}–{Math.min(start + pageSize, measurements.length)} / {measurements.length.toLocaleString("ja-JP")}件</span>
        <Button variant="outline" disabled={current === 0} onClick={() => setPage(current - 1)}>前の100件</Button>
        <Button variant="outline" disabled={current === lastPage} onClick={() => setPage(current + 1)}>次の100件</Button>
      </div>
      <div className="table-scroll">
        <table className="min-w-[900px]">
          <caption className="sr-only">Health Planet の全観測記録（100件ずつ表示）</caption>
          <thead><tr>{["日時（現地時計）", "指標", "値", "単位", "機種", "タグ", "観測ID"].map(h => <th scope="col" key={h}>{h}</th>)}</tr></thead>
          <tbody>{measurements.slice(start, start + pageSize).map((m, i) => (
            <tr key={`${m.id}:${start + i}`}>
              <td className="whitespace-nowrap">{m.timestamp.replace("T", " ")}</td>
              <td>{healthPlanetLabels[m.metric]}</td><td>{m.value}</td><td>{units[m.unit] ?? m.unit}</td>
              <td>{m.model || "不明"}</td><td>{m.tag}</td><td className="max-w-64 break-all">{m.id}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </>
  );
}

export function HealthPlanetView({ data }: { data: HealthPlanet }) {
  const { period } = usePeriod();
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [metric, setMetric] = useState<HealthPlanetMetric | "all">("all");
  const measurements = useMemo(() => filterHealthPlanetMeasurements(data.measurements, {
    period, startDate, endDate, metric,
  }), [data.measurements, period, startDate, endDate, metric]);
  const latest = data.measurements.reduce((end, m) => m.timestamp.slice(0, 10) > end ? m.timestamp.slice(0, 10) : end, "");
  const groups = useMemo(() => {
    const result = new Map<string, HealthPlanetMeasurement[]>();
    for (const m of measurements) {
      // Different units never share an axis; Google series never enter these groups.
      const key = JSON.stringify([m.metric, m.unit]);
      const group = result.get(key);
      if (group) group.push(m);
      else result.set(key, [m]);
    }
    return [...result.entries()];
  }, [measurements]);
  const invalidRange = Boolean(startDate && endDate && startDate > endDate);
  function download() {
    const url = URL.createObjectURL(new Blob([healthPlanetCSV(measurements)], { type: "text/csv;charset=utf-8;" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "healthplanet_observations.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader>
          <CardTitle>Health Planet · タニタ</CardTitle>
          <CardDescription>
            提供元: Health Planet · <span className="status-badge">{connectionLabels[data.status]}</span>
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="chart-note">
            全履歴の取得は未確認です。体重・体脂肪率はHealth Planetの個別測定を使用し、
            Googleの日次平均は身体ページに表示しません。取得範囲は取得状況で確認できます。
          </p>
          <p className="chart-note">
            保存したすべての観測記録を対象にします。同日複数回の記録・同時刻の更新版も保持し、日次集計は行いません。
            提供元に測定IDがないため、観測IDは保存時の識別子であり、記録件数は実際の測定回数とは限りません。
            日時は現地時計のままで、タイムゾーンは補っていません。
          </p>
          <p className="chart-note">
            表示期間: {period === "all" ? "全期間" : `${period}日間`} · Health Planet の保存最新日 {latest || "未確認"} を基準にします。
            開始日・終了日でさらに絞り込めます。同じ日を指定すると1日分を表示します。
          </p>
          <div className="inventory-controls">
            <label className="period-select">指標
              <select aria-label="Health Planet 指標" value={metric} onChange={e => setMetric(e.target.value as HealthPlanetMetric | "all")}>
                <option value="all">すべての指標</option>
                {Object.entries(healthPlanetLabels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
              </select>
            </label>
            <label className="period-select">開始日
              <input aria-label="Health Planet 開始日" type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
            </label>
            <label className="period-select">終了日
              <input aria-label="Health Planet 終了日" type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
            </label>
            <Button variant="outline" onClick={() => { setStartDate(""); setEndDate(""); setMetric("all"); }}>絞り込みを解除</Button>
            <Button variant="outline" disabled={!measurements.length || invalidRange} onClick={download}><Download />絞り込み結果を全件CSV</Button>
          </div>
          {invalidRange && <p role="alert" className="inline-error">開始日を終了日以前にしてください。</p>}
          <p className="chart-note">
            該当 {measurements.length.toLocaleString("ja-JP")} / 保存 {data.measurements.length.toLocaleString("ja-JP")}件。
            グラフのみ約2,000点に間引きます。日付変更時は全記録から再描画し、表とCSVには絞り込み後の全件を残します。
            線は観測記録を日時順に結んだもので、連続測定や更新版の優先順位を表しません。
          </p>
          <details>
            <summary>取得状況 · {data.sources.length}経路 / 未解析 {data.quality.unparsedRecords.toLocaleString("ja-JP")}件</summary>
            <p className="chart-note my-3">未解析・未知の原本はバックエンドで保持し、この画面の測定値には含めません。</p>
            {data.sources.length ? data.sources.map((s, i) => (
              <div className="my-3 text-xs" key={`${s.stream_id}:${i}`}>
                <p>{s.label} · {statusLabel[s.status] ?? s.status} · 表示: {statusLabel[s.projection_status] ?? s.projection_status}</p>
                <p>最終試行: {s.last_attempt_at || "未確認"}{s.http_status !== null ? ` · HTTP ${s.http_status}` : ""}</p>
                {s.reason && <p>{s.reason}</p>}
                <p>要求範囲: {s.requested_start || "未確認"} ～ {s.requested_end || "未確認"}</p>
                {s.intervals.map((interval, j) => <p key={j}>確認区間: {interval.start || "未確認"} ～ {interval.end || "未確認"}{interval.status ? ` · ${statusLabel[interval.status] ?? interval.status}` : ""}</p>)}
              </div>
            )) : <p className="chart-note">取得経路の記録はありません。</p>}
          </details>
          {data.unsupported.length > 0 && (
            <div>
              <h3 className="text-sm font-medium">取得・表示非対応の項目</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs">
                {data.unsupported.map((u, i) => <li key={`${u.metric}:${i}`}>{u.label || u.metric}: {u.reason || "理由は未提供"}</li>)}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>
      {measurements.length ? (
        <>
          <div className="chart-grid">{groups.map(([key, group]) => <ObservationChart key={key} measurements={group} />)}</div>
          <Card>
            <CardHeader><CardTitle>Health Planet · 観測記録</CardTitle></CardHeader>
            <CardContent><ObservationTable key={`${period}:${startDate}:${endDate}:${metric}`} measurements={measurements} /></CardContent>
          </Card>
        </>
      ) : <p className="chart-note" role="status">この条件に該当する Health Planet の観測記録はありません。</p>}
    </div>
  );
}
