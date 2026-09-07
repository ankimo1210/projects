"use client";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { DataState } from "./data-state";
import { calendarRows } from "@/lib/presentation";
export type ChartRow = { date: string; [key: string]: string | number | null };
export type Series = {
  key: string;
  label: string;
  bar?: boolean;
  stack?: string;
};
export function SeriesChart({
  title,
  description,
  rows,
  series,
  unit,
  height = 240,
  thresholds = false,
  spark = false,
}: {
  title: string;
  description?: string;
  rows: ChartRow[];
  series: Series[];
  unit: string;
  height?: number;
  thresholds?: boolean;
  spark?: boolean;
}) {
  const populated = rows.some((row) =>
    series.some((s) => typeof row[s.key] === "number"),
  );
  const chart = populated ? (
    <div
      className="chart-surface"
      style={{ height }}
      role="img"
      aria-label={`${title}、${unit}。${rows.length}件の期間別記録。`}
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
        minWidth={0}
        initialDimension={{ width: 600, height }}
      >
        <ComposedChart
          data={calendarRows(rows)}
          margin={
            spark
              ? { top: 4, right: 4, bottom: 0, left: 4 }
              : { top: 12, right: 14, bottom: 0, left: -15 }
          }
          accessibilityLayer
        >
          {!spark && (
            <>
              <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={(v) =>
                  String(v).length === 10
                    ? String(v).slice(5).replace("-", "/")
                    : String(v)
                }
                minTickGap={40}
                tickLine={false}
                axisLine={false}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              />
              <YAxis
                  domain={series.some(s => s.bar) ? [0, "auto"] : ["auto", "auto"]}
                tickLine={false}
                axisLine={false}
                tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                width={60}
              />
              <Legend
                iconType="circle"
                wrapperStyle={{ fontSize: 11, paddingTop: 12 }}
              />
            </>
          )}
          <Tooltip
            contentStyle={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              color: "var(--foreground)",
              fontSize: 12,
            }}
            formatter={(v) => [v === null ? "欠損" : `${v} ${unit}`]}
            labelStyle={{ color: "var(--muted-foreground)", marginBottom: 5 }}
          />
          {thresholds &&
            [-2, 2].map((y) => (
              <ReferenceLine
                key={y}
                y={y}
                stroke="var(--chart-axis)"
                strokeDasharray="4 4"
              />
            ))}
          {series.map((s, i) =>
            s.bar ? (
              <Bar
                key={s.key}
                dataKey={s.key}
                name={s.label}
                fill={`var(--categorical-${i + 1})`}
                stackId={s.stack}
                radius={s.stack ? 0 : [3, 3, 0, 0]}
                isAnimationActive={false}
                maxBarSize={24}
              />
            ) : (
              <Line
                key={s.key}
                dataKey={s.key}
                name={s.label}
                stroke={`var(--line-${(i % 3) + 1})`}
                strokeWidth={2}
                dot={rows.length === 1 ? { r: 3 } : false}
                connectNulls={false}
                isAnimationActive={false}
              />
            ),
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  ) : (
    <DataState empty="この指標の記録はありません。" />
  );
  if (spark) return chart;
  return (
    <Card>
      <CardHeader>
        <div className="panel-heading">
          <CardTitle>{title}</CardTitle>
          <span className="unit-label">{unit}</span>
        </div>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent>{chart}</CardContent>
    </Card>
  );
}
