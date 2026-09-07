"use client";
import { useState } from "react";
import { isSleep, isAnalytics } from "@/lib/data";
import {
  clipRows,
  nightRange,
  sleepKind,
  sleepWeekdays,
  formatValue,
} from "@/lib/presentation";
import { useSnapshot } from "./data-provider";
import { usePeriod } from "./period-provider";
import { DataState } from "./data-state";
import { SeriesChart, type ChartRow } from "./series-chart";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
export function SleepPage() {
  const result = useSnapshot("sleep.json", isSleep),
    analytics = useSnapshot("analytics.json", isAnalytics);
  const { period } = usePeriod();
  const [allSessions, setAllSessions] = useState(false);
  if (result.loading || result.error || !result.data)
    return <DataState loading={result.loading} error={result.error} />;
  const all = result.data.sessions;
  const end = all.reduce((last, s) => (s.date > last ? s.date : last), "");
  const selected = clipRows(all, period, end);
  const main = selected.filter((s) => s.is_main === true);
  const staged = main.filter((s) => sleepKind(s) === "stages"),
    classic = main.filter((s) => sleepKind(s) === "classic");
  const unknown = main.filter((s) => sleepKind(s) === "unknown");
  const averages = new Map(
    analytics.data?.movingAverages.sleep_main_minutes?.map((r) => [
      r.date,
      r.value,
    ]) ?? [],
  );
  const rows = main.map((s) => ({
    date: s.date,
    minutes_asleep: s.minutes_asleep,
    efficiency: s.efficiency,
    average: averages.get(s.date) ?? null,
  }));
  return (
    <>
      <div className="sleep-summary">
        <span>
          主睡眠 <strong>{main.length}</strong>件
        </span>
        <span>
          昼寝・主睡眠未分類 <strong>{selected.length - main.length}</strong>件
        </span>
        <span>
          詳細ステージ <strong>{staged.length}</strong>件
        </span>
        <span>
          Classic sleep <strong>{classic.length}</strong>件
        </span>
        <span>
          ステージ不明 <strong>{unknown.length}</strong>件
        </span>
      </div>
      <div className="chart-grid">
        <SeriesChart
          title="睡眠時間と7日平均"
          rows={rows}
          series={[
            { key: "minutes_asleep", label: "主睡眠" },
            { key: "average", label: "7日平均" },
          ]}
          unit="分"
          description={`${selected[0]?.date ?? "—"} — ${end || "—"}`}
        />
        <SeriesChart
          title="睡眠効率"
          rows={rows}
          series={[{ key: "efficiency", label: "睡眠効率" }]}
          unit="%"
        />
        {analytics.error && (
          <p role="alert" className="inline-error full-span">
            睡眠の移動平均を読み込めません: {analytics.error.message}
          </p>
        )}
        <SeriesChart
          title="ステージ構成"
          description={`詳細ステージのある主睡眠のみ。${classic.length}件のClassicと${unknown.length}件の不明記録は別扱い。`}
          rows={staged.map((s) => ({
            date: s.date,
            deep: s.minutes_deep,
            rem: s.minutes_rem,
            light: s.minutes_light,
            wake: s.minutes_wake,
          }))}
          series={[
            { key: "deep", label: "深い", bar: true, stack: "sleep" },
            { key: "rem", label: "REM", bar: true, stack: "sleep" },
            { key: "light", label: "浅い", bar: true, stack: "sleep" },
            { key: "wake", label: "覚醒", bar: true, stack: "sleep" },
          ]}
          unit="分"
        />
        <SeriesChart
          title="Classic sleep"
          description="詳細ステージがない記録。睡眠／覚醒の2区分を保持します。"
          rows={classic.map((s) => ({
            date: s.date,
            asleep: s.minutes_asleep,
            wake: s.minutes_wake,
          }))}
          series={[
            { key: "asleep", label: "睡眠", bar: true, stack: "classic" },
            { key: "wake", label: "覚醒", bar: true, stack: "classic" },
          ]}
          unit="分"
        />
        <Card>
          <CardHeader>
            <CardTitle>就寝・起床のリズム</CardTitle>
            <CardDescription>
              主睡眠の直近90夜。起床日の前日正午を基準に整列。
            </CardDescription>
          </CardHeader>
          <CardContent>
            {main.length ? (
              <div className="night-chart">
                <div className="night-axis">
                  <span>18:00</span>
                  <span>00:00</span>
                  <span>06:00</span>
                  <span>12:00</span>
                    <span>18:00</span>
                </div>
                {main
                  .slice(-90)
                  .toReversed()
                  .map((s) => {
                    const range = nightRange(s);
                    return (
                      <div className="night-row" key={s.provider_id}>
                        <span>{s.date.slice(5)}</span>
                        <div className="night-track">
                          {range ? (
                            <span
                              title={`${s.start_ts} → ${s.end_ts}`}
                              style={{
                                left: `${Math.max(0, ((range[0] - 6) / 24) * 100)}%`,
                                width: `${Math.max(1, Math.min(100, ((range[1] - range[0]) / 24) * 100))}%`,
                              }}
                            />
                          ) : (
                            <small>時刻不明</small>
                          )}
                        </div>
                        <span>
                          {s.start_ts?.slice(11, 16) ?? "—"}–
                          {s.end_ts?.slice(11, 16) ?? "—"}
                        </span>
                      </div>
                    );
                  })}
              </div>
            ) : (
              <DataState empty="主睡眠の記録がありません。" />
            )}
          </CardContent>
        </Card>
        <SeriesChart
          title="曜日ごとの睡眠"
          description="主睡眠の平均。記録のない曜日は欠損のまま表示します。"
          rows={sleepWeekdays(main) as ChartRow[]}
          series={[{ key: "minutes", label: "平均睡眠時間", bar: true }]}
          unit="分"
        />
        <Card className="full-span">
          <CardHeader>
            <div className="panel-heading">
              <CardTitle>睡眠セッション</CardTitle>
              <label className="filter-toggle">
                <input
                  type="checkbox"
                  checked={allSessions}
                  onChange={(e) => setAllSessions(e.target.checked)}
                />
                昼寝・未分類も表示
              </label>
            </div>
            <CardDescription>
              時間は記録元の現地時計です。ステージ不明を架空の内訳に変換しません。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>日付</th>
                    <th>種別</th>
                    <th>ステージ</th>
                    <th>就寝 → 起床</th>
                    <th>睡眠</th>
                    <th>効率</th>
                  </tr>
                </thead>
                <tbody>
                  {(allSessions ? selected : main).toReversed().map((s) => (
                    <tr key={s.provider_id}>
                      <td>{s.date}</td>
                      <td>
                        {s.is_main === true
                          ? "主睡眠"
                          : s.is_main === false
                            ? "昼寝"
                            : "未分類"}
                      </td>
                      <td>
                        {
                          {
                            stages: "詳細",
                            classic: "Classic",
                            unknown: "不明",
                          }[sleepKind(s)]
                        }
                      </td>
                      <td>
                        {s.start_ts?.replace("T", " ") ?? "—"} →{" "}
                        {s.end_ts?.replace("T", " ") ?? "—"}
                      </td>
                      <td>{formatValue(s.minutes_asleep)}分</td>
                      <td>{formatValue(s.efficiency)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
