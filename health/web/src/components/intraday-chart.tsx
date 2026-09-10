"use client";
import { useMemo, useState } from "react";
import {
  Brush,
  CartesianGrid,
  ComposedChart,
  Line,
  Bar,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { isIntraday, isIntradayIndex, type Intraday } from "@/lib/data";
import { sampleWindow } from "@/lib/downsample";
import { formatValue, units } from "@/lib/presentation";
import { useSnapshot } from "./data-provider";
import { DataState } from "./data-state";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription,
} from "./ui/card";
import { Button } from "./ui/button";
function clock(value: number) {
  const seconds = Math.floor(value / 1000000);
  return `${String(Math.floor(seconds / 3600)).padStart(2, "0")}:${String(Math.floor((seconds % 3600) / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}
function Detail({ data, unit }: { data: Intraday; unit: string }) {
  const original = useMemo(
    () => data.points.map(([x, y]) => ({ x, y })),
    [data],
  );
  const first = original[0]?.x ?? 0,
    last = original.at(-1)?.x ?? 86399000000;
  const [range, setRange] = useState<[number, number]>([first, last]);
  const overview = useMemo(
    () => sampleWindow(original, first, last, 1000),
    [original, first, last],
  );
  const visible = useMemo(
    () => sampleWindow(original, range[0], range[1]),
    [original, range],
  );
  return (
    <>
      <div className="intraday-stats">
        <span>
          全点 <strong>{original.length.toLocaleString()}</strong>
        </span>
        <span>
          範囲内 <strong>{visible.sourceCount.toLocaleString()}</strong>
        </span>
        <span>
          描画 <strong>{visible.points.length.toLocaleString()}</strong>
        </span>
        <span>
          最小 <strong>{formatValue(visible.min)}</strong> / 最大{" "}
          <strong>{formatValue(visible.max)}</strong> {unit}
        </span>
      </div>
      <div
        className="chart-surface h-[290px]"
        aria-label={`${data.date} 日内${data.metric}グラフ`}
      >
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={0}
          initialDimension={{ width: 600, height: 290 }}
        >
          <ComposedChart
            data={visible.points}
            margin={{ left: -16, right: 18, top: 12 }}
          >
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis
              dataKey="x"
              type="number"
              domain={range}
              tickFormatter={clock}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
              minTickGap={45}
            />
            <YAxis
              domain={["auto", "auto"]}
              tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
            />
            <Tooltip
              labelFormatter={(v) =>
                `${data.date} ${clock(Number(v))}（現地時計）`
              }
              formatter={(v) => [
                `${v} ${unit}`,
                data.metric === "hr" ? "心拍" : "歩数",
              ]}
              contentStyle={{
                background: "var(--card)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                color: "var(--foreground)",
              }}
            />
            {data.metric === "steps" ? (
              <Bar
                dataKey="y"
                fill="var(--categorical-1)"
                isAnimationActive={false}
              />
            ) : (
              <Line
                dataKey="y"
                stroke="var(--line-1)"
                strokeWidth={1.5}
                dot={visible.sourceCount < 100 ? { r: 2 } : false}
                connectNulls={false}
                isAnimationActive={false}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="zoom-controls">
        <label>
          開始
          <input
            aria-label="ズーム開始"
            type="time"
            step="1"
            value={clock(range[0])}
            onChange={(e) => {
              const [h, m, s = 0] = e.target.value.split(":").map(Number);
              const x = (h * 3600 + m * 60 + s) * 1000000;
              if (Number.isFinite(x) && x < range[1]) setRange([x, range[1]]);
            }}
          />
        </label>
        <label>
          終了
          <input
            aria-label="ズーム終了"
            type="time"
            step="1"
            value={clock(range[1])}
            onChange={(e) => {
              const [h, m, s = 0] = e.target.value.split(":").map(Number);
              const x = (h * 3600 + m * 60 + s) * 1000000;
              if (Number.isFinite(x) && x > range[0]) setRange([range[0], x]);
            }}
          />
        </label>
        <Button variant="outline" onClick={() => setRange([first, last])}>
          全日へ戻す
        </Button>
      </div>
      <div className="chart-surface h-[72px]">
        <ResponsiveContainer
          width="100%"
          height="100%"
          minWidth={0}
          initialDimension={{ width: 600, height: 72 }}
        >
          <ComposedChart data={overview.points}>
            <Line
              dataKey="y"
              stroke="var(--line-1)"
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
            <Brush
              key={`${range[0]}:${range[1]}`}
              dataKey="x"
              height={28}
              tickFormatter={clock}
              stroke="var(--chart-axis)"
              fill="var(--chart-surface)"
              startIndex={Math.max(
                0,
                overview.points.findIndex((p) => p.x >= range[0]),
              )}
              endIndex={Math.max(
                0,
                overview.points.findLastIndex((p) => p.x <= range[1]),
              )}
              onChange={(r) => {
                const a = overview.points[r.startIndex ?? 0],
                  b = overview.points[r.endIndex ?? overview.points.length - 1];
                if (a && b && a.x < b.x) setRange([a.x, b.x]);
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="chart-note">
        範囲を選ぶと全点から再描画します。5分を超える時刻の飛びは線を接続しません。現地時計の値で、UTC
        offset は未提供です。描画の間引きは保存データを変更しません。
      </p>
    </>
  );
}
function SelectedDay({
  path,
  metric,
  date,
  unit,
}: {
  path: string;
  metric: string;
  date: string;
  unit: string;
}) {
  const result = useSnapshot(path, isIntraday);
  if (result.loading || result.error || !result.data)
    return <DataState loading={result.loading} error={result.error} />;
  if (result.data.date !== date || result.data.metric !== metric)
    return (
      <DataState
        error={new Error("選択日と日内ファイルの内容が一致しません。")}
      />
    );
  return result.data.points.length ? (
    <Detail key={path} data={result.data} unit={unit} />
  ) : (
    <DataState empty="この日の詳細記録は空です。" />
  );
}
export function IntradayChart({ metric }: { metric: "hr" | "steps" }) {
  const result = useSnapshot("intraday-index.json", isIntradayIndex);
  const [selected, setSelected] = useState("");
  const index = result.data?.metrics[metric];
  const day =
    index?.days.find((d) => d.date === selected) ?? index?.days.at(-1);
  return (
    <Card className="full-span">
      <CardHeader>
        <div className="panel-heading">
          <CardTitle>
            {metric === "hr" ? "一日の心拍を詳しく" : "一日の歩数を詳しく"}
          </CardTitle>
          {day && (
            <label className="date-select">
              <span>記録日</span>
              <select
                aria-label={`${metric === "hr" ? "心拍" : "歩数"}の記録日`}
                value={day.date}
                onChange={(e) => setSelected(e.target.value)}
              >
                {index!.days.toReversed().map((d) => (
                  <option key={d.date}>{d.date}</option>
                ))}
              </select>
            </label>
          )}
        </div>
        <CardDescription>
          保存された日別系列を、元の時間粒度で読み込みます。
        </CardDescription>
      </CardHeader>
      <CardContent>
        {result.error || result.loading ? (
          <DataState error={result.error} loading={result.loading} />
        ) : day ? (
          <SelectedDay
            key={`${metric}:${day.date}`}
            metric={metric}
            date={day.date}
            path={day.path}
            unit={units[index!.unit] ?? index!.unit}
          />
        ) : (
          <DataState empty="保存済みの日内記録がありません。" />
        )}
      </CardContent>
    </Card>
  );
}
