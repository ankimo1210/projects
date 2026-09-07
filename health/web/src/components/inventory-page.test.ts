import { expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { InventoryView } from "./inventory-page";
import type { Inventory } from "../lib/types";
const data: Inventory = {
  sources: [
    {
      stream_id: "hr.list",
      data_type: "heart",
      label: "心拍",
      representation: "source",
      status: "failed",
      method: "list",
      requested_start: null,
      requested_end: null,
      history_complete: false,
      intervals: [],
      pages: 0,
      points: 0,
      stored_pages: 12,
      stored_points: 900,
      last_attempt_at: null,
      reason: "Failed",
      http_status: 500,
      projection_status: "not_implemented",
    },
  ],
  series: [
    {
      metric: "hr",
      storage: "intraday",
      n: 36544,
      first_date: "2026-09-06",
      last_date: "2026-09-07",
      unit: "bpm",
    },
    {
      metric: "sleep_sessions",
      storage: "sleep",
      n: 90,
      first_date: null,
      last_date: null,
      unit: "sessions",
    },
  ],
  quality: [],
};
it("renders typed series counts/ranges alongside cumulative storage and latest failure", () => {
  const html = renderToStaticMarkup(createElement(InventoryView, { data }));
  expect(html).toContain("36,544");
  expect(html).toContain("2026-09-06");
  expect(html).toContain("2026-09-07");
  expect(html).toContain("sleep_sessions");
  expect(html).toContain("900");
  expect(html).toContain("12 pages");
  expect(html).toContain("最終試行");
  expect(html).toContain("取得失敗");
  expect(html).toContain("保存系列をCSV");
  expect(html).toContain("取得状況をCSV");
});
it("reports an explicitly empty typed inventory separately from a failed archive source", () => {
  const html = renderToStaticMarkup(
    createElement(InventoryView, { data: { ...data, series: [] } }),
  );
  expect(html).toContain("保存系列はありません");
  expect(html).toContain("取得失敗");
});
