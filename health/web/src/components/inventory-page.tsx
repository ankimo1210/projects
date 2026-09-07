"use client";
import { useState } from "react";
import { Download, Search } from "lucide-react";
import { isInventory, type Inventory } from "@/lib/data";
import { inventoryCSV, statusLabel, labels, units } from "@/lib/presentation";
import { failures, summarizeSources, sourceCounts } from "@/lib/inventory";
import { useSnapshot } from "./data-provider";
import { DataState } from "./data-state";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "./ui/card";
import { Button } from "./ui/button";
function Badge({
  value,
  projection = false,
}: {
  value: string;
  projection?: boolean;
}) {
  const warning = failures.has(value) || value === "unknown_history";
  return (
    <span
      className={`status-badge ${warning ? "warning" : value === "complete" || value === "available" ? "positive" : ""}`}
    >
      {projection && value === "unsupported"
        ? "表示未対応"
        : (statusLabel[value] ?? value)}
    </span>
  );
}
export function InventoryPage() {
  const result = useSnapshot("inventory.json", isInventory);
  if (result.loading || result.error || !result.data)
    return <DataState loading={result.loading} error={result.error} />;
  return <InventoryView data={result.data} />;
}
export function InventoryView({ data }: { data: Inventory }) {
  const [onlyFailures, setOnlyFailures] = useState(false);
  const [query, setQuery] = useState("");
  const { sources, series, quality } = data;
  const summary = summarizeSources(sources);
  const shown = sources.filter(
    (s) =>
      (!onlyFailures || failures.has(s.status)) &&
      `${s.label} ${s.data_type} ${s.stream_id}`
        .toLowerCase()
        .includes(query.toLowerCase()),
  );
  function download(rows: Record<string, unknown>[], filename: string) {
    const blob = new Blob([inventoryCSV(rows)], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <>
      <div className="inventory-metrics">
        {[
          { label: "取得対象ストリーム", value: summary.total },
          { label: "全履歴の確認完了", value: summary.complete },
          {
            label: "失敗・権限不足",
            value: summary.failed,
          },
          { label: "未完了・未確認", value: summary.incomplete },
        ].map((m) => (
          <Card key={m.label}>
            <CardContent>
              <p className="muted">{m.label}</p>
              <div className="inventory-value">
                {m.value}
                <span>件</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      {summary.legacy > 0 && (
        <p className="chart-note">
          旧JSON {summary.legacy}
          件は履歴確認のKPIに含めず、下の表に保持しています。
        </p>
      )}
      <Card className="mt-5">
        <CardHeader>
          <CardTitle>取得と表示の対応状況</CardTitle>
          <CardDescription>
            全保存期間の棚卸しです。上の表示期間では絞り込みません。取得済み件数があっても、最新の失敗は別に表示します。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="inventory-controls">
            <label className="search-field">
              <Search size={16} />
              <input
                type="search"
                aria-label="型・名称を検索"
                placeholder="型・名称を検索"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <label className="filter-toggle">
              <input
                type="checkbox"
                checked={onlyFailures}
                onChange={(e) => setOnlyFailures(e.target.checked)}
              />
              失敗のみ
            </label>
            <Button
              variant="outline"
              onClick={() => download(shown, "health_archive_inventory.csv")}
              disabled={!shown.length}
            >
              <Download />
              取得状況をCSV
            </Button>
          </div>
          <p className="chart-note">
            {shown.length} / {sources.length} ストリーム
            ・「空」は成功確認した範囲だけを意味します。
          </p>
          {shown.length ? (
            <div className="table-scroll inventory-table">
              <table>
                <thead>
                  <tr>
                    <th>型 / リソース</th>
                    <th>取得状態</th>
                    <th>保存件数</th>
                    <th>表示対応</th>
                    <th>要求 / 確認範囲</th>
                    <th>最終試行 / 理由</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((s) => (
                    <tr key={s.stream_id}>
                      <td>
                        <strong>{s.label}</strong>
                        <small>{s.data_type}</small>
                        <small>{s.stream_id}</small>
                        <small>
                          {s.method ?? "method未確認"} ·{" "}
                          {s.representation === "legacy_json"
                            ? "旧JSON（KPI対象外）"
                            : s.representation}
                        </small>
                      </td>
                      <td>
                        <Badge value={s.status} />
                        <small>
                          {s.history_complete
                            ? "履歴境界確認済み"
                            : "全履歴は未確認"}
                        </small>
                      </td>
                      <td>
                        <StoredCounts source={s} />
                      </td>
                      <td>
                        <Badge projection value={s.projection_status} />
                      </td>
                      <td>
                        <small>
                          要求 {s.requested_start ?? "開始未確認"} →{" "}
                          {s.requested_end ?? "終了未確認"}
                        </small>
                        <div className="intervals">
                          {s.intervals.length ? (
                            s.intervals.map((r, i) => (
                              <div key={i}>
                                <span>
                                  {r.start ?? "開始不明"} →{" "}
                                  {r.end ?? "終了不明"}
                                </span>
                                {r.status && <Badge value={r.status} />}
                              </div>
                            ))
                          ) : (
                            <span className="muted">確認区間なし</span>
                          )}
                        </div>
                      </td>
                      <td>
                        {s.last_attempt_at?.replace("T", " ") ?? "未試行"}
                        {s.http_status !== null && (
                          <small>HTTP {s.http_status}</small>
                        )}
                        {s.reason && (
                          <p className="failure-reason">{s.reason}</p>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <DataState
              empty={
                sources.length
                  ? "条件に一致する取得対象はありません。"
                  : "取得対象の情報がありません。"
              }
            />
          )}
        </CardContent>
      </Card>
      <Card className="mt-5">
        <CardHeader>
          <div className="panel-heading">
            <CardTitle>保存系列</CardTitle>
            <Button
              variant="outline"
              disabled={!series.length}
              onClick={() => download(series, "health_series_inventory.csv")}
            >
              <Download />
              保存系列をCSV
            </Button>
          </div>
          <CardDescription>
            日次・日内・睡眠の保存行数と期間。欠損値を含む行数です。原本のpage /
            point件数とは別に表示します。
          </CardDescription>
        </CardHeader>
        <CardContent>
          {series.length ? (
            <div className="table-scroll">
              <table aria-label="保存系列">
                <thead>
                  <tr>
                    <th>系列</th>
                    <th>保存区分</th>
                    <th>保存行数</th>
                    <th>開始日</th>
                    <th>最終日</th>
                    <th>単位</th>
                  </tr>
                </thead>
                <tbody>
                  {series.map((row) => (
                    <tr key={`${row.metric}:${row.storage}`}>
                      <td>
                        <strong>
                          {labels[row.metric] ??
                            (row.metric === "hr"
                              ? "心拍"
                              : row.metric === "sleep_sessions"
                                ? "睡眠セッション"
                                : row.metric)}
                        </strong>
                        <small>{row.metric}</small>
                      </td>
                      <td>
                        {
                          { daily: "日次", intraday: "日内", sleep: "睡眠" }[
                            row.storage
                          ]
                        }
                      </td>
                      <td>{row.n.toLocaleString("ja-JP")}</td>
                      <td>{row.first_date ?? "—"}</td>
                      <td>{row.last_date ?? "—"}</td>
                      <td>
                        {units[row.unit] ??
                          (row.unit === "sessions" ? "件" : row.unit)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <DataState empty="保存系列はありません。" />
          )}
        </CardContent>
      </Card>
      <Card className="mt-5">
        <CardHeader>
          <CardTitle>表示データの品質</CardTitle>
          <CardDescription>
            非有限数を欠損へ変換した箇所。通常の欠損とは区別しています。
          </CardDescription>
        </CardHeader>
        <CardContent>
          {quality.length ? (
            <ul className="quality-list">
              {quality.map((q, i) => (
                <li key={i}>
                  <strong>{q.path}</strong>
                  <span>{q.count}件 · 非有限数</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="reading-note">
              このエクスポートに非有限数の品質警告はありません。取得完全性を保証する表示ではありません。
            </p>
          )}
        </CardContent>
      </Card>
    </>
  );
}

function StoredCounts({ source }: { source: Inventory["sources"][number] }) {
  const counts = sourceCounts(source);
  return (
    <>
      <strong>{counts.points.toLocaleString("ja-JP")}</strong> points
      <small>{counts.pages.toLocaleString("ja-JP")} pages</small>
      {!counts.hasStoredTotals && <small>累積値未提供・最終試行の件数</small>}
      {counts.hasStoredTotals &&
        (counts.points !== source.points || counts.pages !== source.pages) && (
          <small>
            最終試行: {source.points.toLocaleString("ja-JP")} points /{" "}
            {source.pages.toLocaleString("ja-JP")} pages
          </small>
        )}
    </>
  );
}
