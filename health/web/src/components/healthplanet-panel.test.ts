import { beforeEach, expect, it, vi } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as panel from "./healthplanet-panel";
import { DashboardPage } from "./dashboard-pages";
import BodyPage from "../app/body/page";
import { DataLoadError } from "../lib/data";
import type { HealthPlanet, Meta } from "../lib/types";

const state = vi.hoisted(() => ({
  meta: null as Meta | null,
  snapshots: {} as Record<string, { data: unknown; loading: boolean; error: Error | null }>,
}));
vi.mock("./data-provider", () => ({
  useMeta: () => ({ meta: state.meta, loading: false, error: null }),
  useSnapshot: (name: string) => state.snapshots[name] ?? { data: null, loading: false, error: null },
}));
const data: HealthPlanet = {
  provider: "healthplanet", timeBasis: "civil", status: "partial", historyComplete: false,
  sources: [{
    stream_id: "demo", label: "体組成", data_type: "innerscan", representation: "original",
    status: "unknown_history", method: "GET", requested_start: null, requested_end: null,
    history_complete: false, intervals: [], pages: 1, points: 3,
    last_attempt_at: null, reason: "過去の範囲が未確認", http_status: 200, projection_status: "available",
  }],
  measurements: [
    { id: "demo-1", metric: "weight_kg", tag: "6021", timestamp: "2026-09-07T07:00:00", value: 65.123456, unit: "kg", model: "demo-model" },
    { id: "demo-2", metric: "weight_kg", tag: "6021", timestamp: "2026-09-07T07:00:00", value: 66, unit: "kg", model: "demo-model" },
    { id: "demo-3", metric: "weight_kg", tag: "6021", timestamp: "2026-09-07T21:00:00", value: 67, unit: "kg", model: "demo-model" },
  ],
  unsupported: [{ metric: "muscle_mass", label: "筋肉量", reason: "API取得非対応" }],
  quality: { unparsedRecords: 2 },
};
beforeEach(() => {
  state.meta = {
    schemaVersion: 1, generation: "demo", generatedAt: "2026-09-07T00:00:00Z",
    basePath: "generations/demo/", files: { "healthplanet.json": "healthplanet.json" },
    freshness: { archiveStatus: "partial", projectionStatus: "available" },
  };
  state.snapshots = {
    "daily.json": { data: { dates: ["2026-09-07"], series: { weight_kg: [75] }, units: { weight_kg: "kg" } }, loading: false, error: null },
    "healthplanet.json": { data, loading: false, error: null },
  };
});
it("renders all same-day observations, revisions, quality and unsupported metrics", () => {
  const html = renderToStaticMarkup(createElement(panel.HealthPlanetView, { data }));
  expect(html).toContain("Health Planet");
  expect(html).toContain("観測記録");
  expect(html).toContain("全履歴の取得は未確認");
  expect(html).toContain("更新版");
  for (const id of ["demo-1", "demo-2", "demo-3"]) expect(html).toContain(id);
  expect(html).toContain("65.123456");
  expect(html).toContain("筋肉量");
  expect(html).toContain("API取得非対応");
  expect(html).toContain("未解析");
  expect(html).toContain("絞り込み結果を全件CSV");
  expect(html).toContain('aria-label="Health Planet 開始日"');
  expect(html).toContain('aria-label="Health Planet 終了日"');
});
it("does not use the Google daily rollup as the body-weight source", () => {
  const html = renderToStaticMarkup(createElement(DashboardPage, { page: "body" }));
  expect(html).toContain("血中酸素");
  expect(html).not.toContain("体重");
  expect(html).not.toContain("体脂肪率");
});
it("puts Health Planet body measurements before the remaining Google metrics", () => {
  const html = renderToStaticMarkup(createElement(BodyPage));
  expect(html.indexOf("Health Planet · タニタ")).toBeLessThan(
    html.indexOf("Google · その他の身体データ"),
  );
});
it("keeps Google body charts usable with an older manifest lacking the optional file", () => {
  state.meta!.files = {};
  const html = renderToStaticMarkup(createElement(BodyPage));
  expect(html).toContain("Google");
  expect(html).toContain("血中酸素");
  expect(html).toContain("この書き出しには Health Planet データが含まれていません");
  expect(html).not.toContain('role="alert"');
});
it("displays Health Planet even when Google daily data fails", () => {
  state.snapshots["daily.json"] = { data: null, loading: false, error: new DataLoadError("schema", "daily.json の形式が一致しません") };
  const html = renderToStaticMarkup(createElement(BodyPage));
  expect(html).toContain("daily.json の形式が一致しません");
  expect(html).toContain("demo-3");
});
it("isolates an invalid declared Health Planet file from Google charts", () => {
  state.snapshots["healthplanet.json"] = { data: null, loading: false, error: new DataLoadError("schema", "healthplanet.json のデータ形式が一致しません") };
  const html = renderToStaticMarkup(createElement(BodyPage));
  expect(html).toContain("healthplanet.json のデータ形式が一致しません");
  expect(html).toContain("血中酸素");
  expect(html).not.toContain("データが含まれていません");
});
it.each([
  ["not_connected", "未接続"], ["pending", "未取得"],
  ["partial", "一部取得"], ["available", "表示データあり"],
] as const)("keeps %s distinct from an empty filtered result", (status, label) => {
  const html = renderToStaticMarkup(createElement(panel.HealthPlanetView, { data: { ...data, status, measurements: [] } }));
  expect(html).toContain(label);
  expect(html).toContain("観測記録はありません");
  expect(html).toContain("筋肉量");
});
