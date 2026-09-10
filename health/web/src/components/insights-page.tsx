"use client";
import { isAnalytics } from "@/lib/data";
import { clipRows, formatValue, labels } from "@/lib/presentation";
import { useSnapshot } from "./data-provider";
import { usePeriod } from "./period-provider";
import { DataState } from "./data-state";
import { SeriesChart } from "./series-chart";
import { Heatmap } from "./heatmap";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./ui/card";
export function InsightsPage() {
  const result = useSnapshot("analytics.json", isAnalytics);
  const { period } = usePeriod();
  if (result.loading || result.error || !result.data)
    return <DataState loading={result.loading} error={result.error} />;
  const data = result.data,
    analysis = data.periods[period],
    jetlag = data.socialJetlag;
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>いつもの自分との違い</h2>
          <p>全履歴で計算した30日ベースライン。|z| ≥ 2 が注目日の目安です。</p>
        </div>
      </div>
      <div className="baseline-grid">
        {["resting_hr", "hrv_rmssd", "temp_skin_relative"].map((metric) => {
          const rows = clipRows(
            data.baselines[metric] ?? [],
            period,
            analysis.endDate ?? "",
          );
          const latest = rows.findLast((r) => r.z !== null);
          return (
            <div key={metric}>
              <SeriesChart
                title={labels[metric]}
                rows={rows}
                series={[{ key: "z", label: "標準化スコア" }]}
                unit="z"
                thresholds
                height={190}
                description={
                  latest
                    ? `${latest.date} · 値 ${formatValue(latest.value)} · z ${formatValue(latest.z)}`
                    : "計算には30日間で10日以上の履歴が必要です。"
                }
              />
            </div>
          );
        })}
      </div>
      <div className="chart-grid mt-5">
        <Card>
          <CardHeader>
            <CardTitle>日々のつながり · ラグ相関</CardTitle>
            <CardDescription>
              {analysis.startDate ?? "—"} — {analysis.endDate ?? "—"}
              <br />
              Spearman 順位相関。1日後は、その日の値と翌日の値の関係です。
            </CardDescription>
          </CardHeader>
          <CardContent>
            {analysis.correlations.length ? (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>組み合わせ</th>
                      <th>ラグ</th>
                      <th>相関</th>
                      <th>標本数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.correlations.map((c) => (
                      <tr key={`${c.x}:${c.y}:${c.lag}`}>
                        <td>
                          {labels[c.x] ?? c.x}
                          <br />
                          <span className="muted">→ {labels[c.y] ?? c.y}</span>
                        </td>
                        <td>{c.lag}日</td>
                        <td>
                          {formatValue(c.spearman)}
                          {c.reason && (
                            <small>
                              {c.reason === "insufficient_pairs"
                                ? "20組未満"
                                : "系列が一定"}
                            </small>
                          )}
                        </td>
                        <td>{c.n}組</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <DataState empty="相関を計算できる系列がありません。" />
            )}
            <p className="chart-note">
              期間ごとに Python
              で計算した結果です。相関は因果関係を示すものではありません。
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>睡眠リズム</CardTitle>
            <CardDescription>ソーシャル・ジェットラグ</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rhythm-value">
              {formatValue(jetlag.hours)}
              <span>時間</span>
            </div>
            <p className="reading-note">
              休日と平日の睡眠中央時刻の差。プラスの値は休日の眠りが後ろにずれていることを表します。
            </p>
            {jetlag.hours === null && (
              <p className="stale-notice">
                平日・休日それぞれ2晩以上の記録が必要です。
              </p>
            )}
            <dl className="info-list">
              <dt>計算対象</dt>
              <dd>全保存睡眠（主睡眠）</dd>
              <dt>入力範囲</dt>
              <dd>
                {jetlag.firstDate ?? "—"} — {jetlag.lastDate ?? "—"}
              </dd>
              <dt>表示期間との関係</dt>
              <dd>期間選択によらず全履歴を使用</dd>
            </dl>
          </CardContent>
        </Card>
        <Heatmap
          title="データ欠損カレンダー"
          coverage
          rows={(analysis.coverage.steps ?? []).map((d) => ({
            date: d.date,
            value: d.has_data ? 1 : null,
          }))}
        />
      </div>
    </>
  );
}
