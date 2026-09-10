import { expect, it, vi } from "vitest";
import * as healthPlanet from "./healthplanet";
import { loadSnapshot, type Meta } from "./data";

const measurement = {
  id: "observation-1", metric: "weight_kg", tag: "6021",
  timestamp: "2026-09-07T07:15:00", value: 65.25, unit: "kg", model: "demo",
};
const source = {
  stream_id: "healthplanet.innerscan", data_type: "innerscan", label: "体組成",
  representation: "original", status: "partial", method: "GET",
  requested_start: null, requested_end: null, history_complete: false,
  intervals: [{ start: "2026-09-01", end: "2026-09-07", status: "complete" }],
  pages: 1, points: 3, last_attempt_at: null, reason: null,
  http_status: 200, projection_status: "available",
};
const payload = {
  provider: "healthplanet", timeBasis: "civil", status: "available", historyComplete: false,
  sources: [source], measurements: [measurement],
  unsupported: [{ metric: "muscle_mass", label: "筋肉量", reason: "API取得非対応" }],
  quality: { unparsedRecords: 2 },
};
const meta: Meta = {
  schemaVersion: 1, generation: "test", generatedAt: "2026-09-07T00:00:00Z",
  basePath: "generations/test/", files: { "healthplanet.json": "healthplanet.json" },
  freshness: { archiveStatus: "partial", projectionStatus: "complete" },
};

it.each(["not_connected", "pending", "partial", "available"])("accepts %s status and empty observations", (status) => {
  expect(healthPlanet.isHealthPlanet({ ...payload, status, measurements: [] })).toBe(true);
});
it.each([null, undefined, [], {},
  { ...payload, provider: "google" }, { ...payload, timeBasis: "utc" },
  { ...payload, status: "complete" }, { ...payload, historyComplete: true },
  { ...payload, historyComplete: undefined }, { ...payload, measurements: undefined },
  { ...payload, sources: [{}] }, { ...payload, sources: [{ ...source, stored_points: -1 }] },
  { ...payload, sources: [{ ...source, intervals: [{ start: null, end: null, status: 3 }] }] },
  { ...payload, unsupported: [{ metric: "a", label: "b" }] },
  { ...payload, quality: {} }, { ...payload, quality: { unparsedRecords: -1 } },
  { ...payload, quality: { unparsedRecords: 0.5 } },
])("rejects malformed or missing Health Planet payload %#", (value) => {
  expect(healthPlanet.isHealthPlanet(value)).toBe(false);
});
it.each([
  { value: NaN }, { value: Infinity }, { value: null }, { value: "65" },
  { id: "" }, { tag: undefined }, { unit: undefined }, { model: null },
  { metric: "unknown" }, { timestamp: null }, { timestamp: "2026-02-30T12:00:00" },
  { timestamp: "2026-09-07T24:00:00" }, { timestamp: "2026-09-07T12:60:00" },
  { timestamp: "2026-09-07T12:00:60" }, { timestamp: "2026-09-07" },
  { timestamp: "2026-09-07T07:15:00Z" }, { timestamp: "2026-09-07T07:15:00+09:00" },
])("rejects malformed measurement %#", (change) => {
  expect(healthPlanet.isHealthPlanet({ ...payload, measurements: [{ ...measurement, ...change }] })).toBe(false);
});
it("accepts all supported metrics, zero and civil fractional seconds", () => {
  for (const metric of ["weight_kg", "body_fat_pct", "systolic_mmhg", "diastolic_mmhg", "pulse_bpm", "steps"])
    expect(healthPlanet.isHealthPlanet({ ...payload, measurements: [{ ...measurement, metric, value: 0, timestamp: "2026-03-08T02:30:00.123456" }] })).toBe(true);
});
it("loads the optional file through normal envelope and generation checks", async () => {
  const fetcher = vi.fn<typeof fetch>().mockImplementation(async () => new Response(JSON.stringify({ schemaVersion: 1, generation: "test", data: payload })));
  expect(await loadSnapshot(meta, "healthplanet.json", healthPlanet.isHealthPlanet, fetcher)).toEqual(payload);
  expect(fetcher.mock.calls[0][0]).toBe("/data/generations/test/healthplanet.json");
  await expect(loadSnapshot({ ...meta, generation: "next", basePath: "generations/next/" }, "healthplanet.json", healthPlanet.isHealthPlanet, fetcher)).rejects.toMatchObject({ kind: "generation" });
  await expect(loadSnapshot({ ...meta, files: {} }, "healthplanet.json", healthPlanet.isHealthPlanet, fetcher)).rejects.toMatchObject({ kind: "missing" });
  expect(fetcher).toHaveBeenCalledTimes(2);
});

it("filters civil dates inclusively without collapsing same-day or revised observations", () => {
  const rows = [
    { ...measurement, id: "late", timestamp: "2026-09-07T21:00:00", value: 66 },
    { ...measurement, id: "old", timestamp: "2026-08-08T23:59:59", value: 64 },
    { ...measurement, id: "boundary", timestamp: "2026-08-09T00:00:00", value: 65 },
    measurement,
    { ...measurement, id: "revision", value: 65.5 },
    { ...measurement, id: "fat", metric: "body_fat_pct", value: 18.3, unit: "%" },
  ] as import("./types").HealthPlanetMeasurement[];
  const before = structuredClone(rows);
  expect(healthPlanet.filterHealthPlanetMeasurements(rows, { period: "30" }).map(r => r.id))
    .toEqual(["boundary", "observation-1", "revision", "fat", "late"]);
  expect(healthPlanet.filterHealthPlanetMeasurements(rows, { period: "all", startDate: "2026-09-07", endDate: "2026-09-07", metric: "weight_kg" }).map(r => r.id))
    .toEqual(["observation-1", "revision", "late"]);
  expect(healthPlanet.filterHealthPlanetMeasurements(rows, { period: "all", startDate: "2026-09-08", endDate: "2026-09-07" })).toEqual([]);
  expect(healthPlanet.filterHealthPlanetMeasurements([], { period: "30" })).toEqual([]);
  expect(rows).toEqual(before);
});
it("exports every filtered observation with original timestamps, precision and CSV escaping", () => {
  const rows = Array.from({ length: 5001 }, (_, i) => ({
    ...measurement, id: `observation-${i}`, value: i === 2500 ? 999 : 65.123456,
    model: i === 0 ? '=demo,"quoted"' : "demo",
  })) as import("./types").HealthPlanetMeasurement[];
  const filtered = healthPlanet.filterHealthPlanetMeasurements(rows, { period: "all" });
  const preview = healthPlanet.healthPlanetChartRows(filtered, 20);
  expect(preview.length).toBeLessThanOrEqual(20);
  expect(preview.some(r => r.value === 999)).toBe(true);
  const csv = healthPlanet.healthPlanetCSV(filtered);
  expect(csv.split("\r\n")).toHaveLength(5002);
  expect(csv).toContain('"healthplanet","civil","observation-0","weight_kg","6021","2026-09-07T07:15:00","65.123456","kg","\'=demo,""quoted"""');
  expect(csv).toContain('"observation-5000"');
  expect(rows).toHaveLength(5001);
});
it("charts duplicate timestamps without daily aggregation and preserves civil time spacing", () => {
  const rows = [
    { ...measurement, timestamp: "2026-01-01T00:00:00" },
    { ...measurement, timestamp: "2026-01-01T00:00:00", id: "revision", value: 66 },
    { ...measurement, timestamp: "2026-01-01T12:30:00.123456", id: "evening", value: 67 },
  ] as import("./types").HealthPlanetMeasurement[];
  const chart = healthPlanet.healthPlanetChartRows(rows);
  expect(chart.map(r => r.id)).toEqual(["observation-1", "revision", "evening"]);
  expect(chart.map(r => r.value)).toEqual([65.25, 66, 67]);
  expect(chart[0].x).toBe(1767225600000);
  expect(chart[1].x).toBe(chart[0].x);
  expect(chart[2].x - chart[0].x).toBeCloseTo(45000123.456, 2);
});
it("refilters original observations when a date is selected after a sampled overview", () => {
  const rows = Array.from({ length: 2500 }, (_, i) => ({ ...measurement, id: `old-${i}`, timestamp: "2026-09-06T12:00:00" }));
  rows.push({ ...measurement, id: "today-a" }, { ...measurement, id: "today-b", value: 66 });
  const original = rows as import("./types").HealthPlanetMeasurement[];
  expect(healthPlanet.healthPlanetChartRows(original, 10).length).toBeLessThan(original.length);
  const selected = healthPlanet.filterHealthPlanetMeasurements(original, { period: "all", startDate: "2026-09-07", endDate: "2026-09-07" });
  expect(healthPlanet.healthPlanetChartRows(selected).map(r => r.id)).toEqual(["today-a", "today-b"]);
  expect(healthPlanet.healthPlanetCSV(selected).split("\r\n")).toHaveLength(3);
});
