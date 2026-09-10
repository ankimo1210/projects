"use client";
import Link from "next/link";
import { ArrowUpRight, Footprints, Heart, Moon } from "lucide-react";
import { isDaily, isAnalytics, type Daily, type Analytics } from "@/lib/data";
import {
  clipRows,
  latestMetric,
  formatValue,
  labels,
  units,
} from "@/lib/presentation";
import { useSnapshot } from "./data-provider";
import { usePeriod } from "./period-provider";
import { DataState } from "./data-state";
import { SeriesChart, type ChartRow } from "./series-chart";
import { IntradayChart } from "./intraday-chart";
import { Heatmap } from "./heatmap";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
function dailyRows(daily: Daily) {
  return daily.dates.map((date, i) => ({
    date,
    ...Object.fromEntries(
      Object.entries(daily.series).map(([k, v]) => [k, v[i]]),
    ),
  })) as ChartRow[];
}
function Panel({
  daily,
  rows,
  metrics,
  title,
  bar = false,
}: {
  daily: Daily;
  rows: ChartRow[];
  metrics: string[];
  title: string;
  bar?: boolean;
}) {
  return (
    <SeriesChart
      title={title}
      rows={rows}
      series={metrics.map((key) => ({
        key,
        label: labels[key] ?? key,
        bar,
        stack: bar ? "stack" : undefined,
      }))}
      unit={
        units[daily.units[metrics[0]]] ?? daily.units[metrics[0]] ?? "単位不明"
      }
    />
  );
}
function MovingChart({
  daily,
  rows,
  metric,
  analytics,
}: {
  daily: Daily;
  rows: ChartRow[];
  metric: string;
  analytics: ReturnType<typeof useSnapshot<Analytics>>;
}) {
  const averages = new Map(
    analytics.data?.movingAverages[metric]?.map((r) => [r.date, r.value]) ?? [],
  );
  return (
    <div>
      <SeriesChart
        title={`${labels[metric]}と7日平均`}
        rows={rows.map((r) => ({
          ...r,
          average: averages.get(r.date) ?? null,
        }))}
        series={[
          { key: metric, label: labels[metric], bar: metric === "steps" },
          { key: "average", label: "7日平均" },
        ]}
        unit={units[daily.units[metric]] ?? daily.units[metric]}
      />
      {analytics.error && (
        <p role="alert" className="inline-error">
          移動平均を取得できません: {analytics.error.message}
        </p>
      )}
    </div>
  );
}
export function DashboardPage({
  page,
}: {
  page: "overview" | "activity" | "heart" | "body";
}) {
  const daily = useSnapshot("daily.json", isDaily);
  const analytics = useSnapshot("analytics.json", isAnalytics);
  const { period } = usePeriod();
  if (daily.loading || daily.error || !daily.data)
    return <DataState error={daily.error} loading={daily.loading} />;
  const data = daily.data;
  const rows = clipRows(dailyRows(data), period, data.dates.at(-1) ?? "");
  if (page === "overview")
    return (
      <>
        <div className="metric-grid">
          {[
            { metric: "steps", icon: Footprints, route: "/activity/" },
            { metric: "sleep_minutes", icon: Moon, route: "/sleep/" },
            { metric: "resting_hr", icon: Heart, route: "/heart/" },
          ].map(({ metric, icon: Icon, route }) => {
            const visible: Daily = {
              dates: rows.map((r) => r.date),
              series: {
                [metric]: rows.map((r) => (r[metric] as number | null) ?? null),
              },
              units: data.units,
            };
            const latest = latestMetric(visible, metric);
            const unit = units[data.units[metric]] ?? data.units[metric] ?? "";
            return (
              <Card key={metric} className="metric-card">
                <CardHeader>
                  <div className="panel-heading">
                    <CardTitle>{labels[metric]}</CardTitle>
                    <Icon className="metric-icon" size={18} />
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="metric-value">
                    {formatValue(latest?.value)}
                    <span>{unit}</span>
                  </div>
                  <p className="value-date">
                    {latest
                      ? `${latest.date} 時点${latest.stale ? " · 最新日には記録なし" : ""}`
                      : "この期間に記録なし"}
                  </p>
                  <div className="metric-delta">
                    {latest?.delta != null
                      ? `暦上前日比 ${latest.delta > 0 ? "+" : ""}${formatValue(latest.delta)} ${unit}`
                      : "前日比 — 比較できる記録なし"}
                  </div>
                  <SeriesChart
                    title={labels[metric]}
                    rows={rows}
                    series={[{ key: metric, label: labels[metric] }]}
                    unit={unit}
                    height={80}
                    spark
                  />
                  <Link href={route} prefetch={false} className="detail-link">
                    記録を見る
                    <ArrowUpRight size={14} />
                  </Link>
                </CardContent>
              </Card>
            );
          })}
        </div>
        <div className="section-heading">
          <div>
            <h2>日々の積み重ね</h2>
            <p>
              {rows[0]?.date ?? "—"} — {rows.at(-1)?.date ?? "—"}{" "}
              ・保存日を基準に表示
            </p>
          </div>
          <span className="small-pill">
            {period === "all" ? "全期間" : `${period}日間`}
          </span>
        </div>
        <div className="chart-grid">
          <MovingChart
            daily={data}
            rows={rows}
            metric="steps"
            analytics={analytics}
          />
          <Panel
            daily={data}
            rows={rows}
            metrics={["resting_hr"]}
            title="安静時心拍の推移"
          />
          <Heatmap
            title="記録のある日"
            rows={rows.map((r) => ({
              date: r.date,
              value: typeof r.steps === "number" ? 1 : null,
            }))}
            coverage
          />
        </div>
      </>
    );
  if (page === "activity")
    return (
      <div className="chart-grid">
        <MovingChart
          daily={data}
          rows={rows}
          metric="steps"
          analytics={analytics}
        />
        <Panel
          daily={data}
          rows={rows}
          metrics={[
            "minutes_lightly_active",
            "minutes_fairly_active",
            "minutes_very_active",
          ]}
          title="活動時間の内訳"
          bar
        />
        <Panel
          daily={data}
          rows={rows}
          metrics={["distance_km"]}
          title="移動距離"
        />
        <Panel
          daily={data}
          rows={rows}
          metrics={["calories"]}
          title="消費エネルギー"
        />
        <Heatmap
          title="週間ヒートマップ · 歩数"
          rows={rows.slice(-182).map((r) => ({
            date: r.date,
            value: (r.steps as number | null) ?? null,
          }))}
        />
        <IntradayChart metric="steps" />
      </div>
    );
  if (page === "heart")
    return (
      <div className="chart-grid">
        <Panel
          daily={data}
          rows={rows}
          metrics={["resting_hr"]}
          title="安静時心拍"
        />
        <Panel
          daily={data}
          rows={rows}
          metrics={["hrv_rmssd", "hrv_deep_rmssd"]}
          title="心拍変動 · HRV (RMSSD)"
        />
        <IntradayChart metric="hr" />
      </div>
    );
  return (
    <div className="chart-grid">
      <Panel
        daily={data}
        rows={rows}
        metrics={["spo2_avg", "spo2_lower_bound", "spo2_upper_bound"]}
        title="血中酸素ウェルネス · SpO2"
      />
      <Panel
        daily={data}
        rows={rows}
        metrics={["temp_skin_relative"]}
        title="皮膚温 · 自分の基準からの変化"
      />
      <Panel
        daily={data}
        rows={rows}
        metrics={["breathing_rate"]}
        title="呼吸数"
      />
    </div>
  );
}
