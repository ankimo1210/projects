import { expect, it } from "vitest";
import { isInventory } from "./data";
import { inventoryCSV } from "./presentation";
import { summarizeSources, sourceCounts } from "./inventory";
import type { SourceCoverage } from "./types";
const source: SourceCoverage = {
  stream_id: "heart.list",
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
  last_attempt_at: null,
  reason: "Failed",
  http_status: 500,
  projection_status: "not_implemented",
};
const series = {
  metric: "hr",
  storage: "intraday",
  n: 36544,
  first_date: "2026-09-06",
  last_date: "2026-09-07",
  unit: "bpm",
};
it("requires and validates typed inventory counts, ranges and storage independently of sources", () => {
  const inventory = { sources: [source], series: [series], quality: [] };
  expect(isInventory(inventory)).toBe(true);
  expect(isInventory({ sources: [], quality: [] })).toBe(false);
  for (const update of [
    { n: -1 },
    { n: 1.5 },
    { n: Infinity },
    { storage: "archive" },
    { first_date: "2026-02-30" },
    { first_date: "2026-09-08" },
    { last_date: undefined },
    { unit: 3 },
  ])
    expect(
      isInventory({ ...inventory, series: [{ ...series, ...update }] }),
    ).toBe(false);
  expect(isInventory({ ...inventory, series: [] })).toBe(true);
  expect(
    isInventory({
      ...inventory,
      series: [{ ...series, n: 0, first_date: null, last_date: null }],
    }),
  ).toBe(true);
});
it("keeps typed inventory CSV values and columns distinct from archival point counts", () => {
  const csv = inventoryCSV([series]);
  expect(csv).toContain(
    '"metric","storage","n","first_date","last_date","unit"',
  );
  expect(csv).toContain(
    '"hr","intraday","36544","2026-09-06","2026-09-07","bpm"',
  );
});
it("excludes only legacy_json from KPI totals, keeps projection and latest failed states", () => {
  expect(
    summarizeSources([
      { ...source, status: "complete", history_complete: true },
      {
        ...source,
        stream_id: "projection",
        representation: "projection",
        status: "pending",
      },
      { ...source, stream_id: "latest-failed", history_complete: true },
      {
        ...source,
        stream_id: "legacy",
        representation: "legacy_json",
        status: "unknown_history",
      },
      { ...source, stream_id: "legacy-failed", representation: "legacy_json" },
    ]),
  ).toEqual({ total: 3, complete: 1, failed: 1, incomplete: 2, legacy: 2 });
  expect(
    summarizeSources([{ ...source, representation: "legacy_json" }]),
  ).toEqual({ total: 0, complete: 0, failed: 0, incomplete: 0, legacy: 1 });
});
it("prefers stored totals, preserves explicit zero, and falls back only when totals are absent", () => {
  expect(
    sourceCounts({ ...source, stored_pages: 12, stored_points: 900 }),
  ).toEqual({ pages: 12, points: 900, hasStoredTotals: true });
  expect(
    sourceCounts({
      ...source,
      pages: 8,
      points: 500,
      stored_pages: 0,
      stored_points: 0,
    }),
  ).toEqual({ pages: 0, points: 0, hasStoredTotals: true });
  expect(sourceCounts({ ...source, pages: 8, points: 500 })).toEqual({
    pages: 8,
    points: 500,
    hasStoredTotals: false,
  });
});
it("validates optional stored totals while accepting older source records", () => {
  const inventory = { sources: [source], series: [], quality: [] };
  expect(isInventory(inventory)).toBe(true);
  expect(
    isInventory({
      ...inventory,
      sources: [{ ...source, stored_pages: 12, stored_points: 900 }],
    }),
  ).toBe(true);
  for (const value of [-1, 0.5, NaN, Infinity, null, "100"])
    expect(
      isInventory({
        ...inventory,
        sources: [{ ...source, stored_points: value }],
      }),
    ).toBe(false);
});

it("keeps unknown parent coverage in status KPIs even when its list and discovered child are complete", () => {
  const rows = [
    {
      ...source,
      stream_id: "weight.get",
      status: "unknown_history",
      history_complete: false,
      stored_pages: 12,
      stored_points: 900,
    },
    {
      ...source,
      stream_id: "weight.list",
      status: "complete",
      history_complete: true,
    },
    {
      ...source,
      stream_id: "weight.get.resource.a",
      status: "complete",
      history_complete: true,
      stored_pages: 12,
      stored_points: 900,
    },
  ];
  const before = structuredClone(rows);
  expect(summarizeSources(rows)).toEqual({
    total: 3,
    complete: 2,
    failed: 0,
    incomplete: 1,
    legacy: 0,
  });
  expect(rows).toEqual(before);
});
