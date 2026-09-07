import { expect, it, vi } from "vitest";
import { isDaily, isIntraday, loadMeta, loadSnapshot, type Meta } from "./data";
const meta: Meta = {
  schemaVersion: 1,
  generation: "new",
  generatedAt: "2026-09-07T00:00:00Z",
  basePath: "generations/new/",
  files: { daily: "daily.json" },
  freshness: { archiveStatus: "partial", projectionStatus: "complete" },
};
const daily = {
  dates: ["2026-09-01"],
  series: { steps: [0] },
  units: { steps: "steps" },
};
const response = (v: unknown) =>
  vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(v)));
it("loads a valid snapshot and preserves a real zero", async () => {
  expect(
    await loadSnapshot(
      meta,
      "daily",
      isDaily,
      response({ schemaVersion: 1, generation: "new", data: daily }),
    ),
  ).toEqual(daily);
});
it("rejects mixed generations", async () => {
  await expect(
    loadSnapshot(
      meta,
      "daily",
      isDaily,
      response({ schemaVersion: 1, generation: "old", data: daily }),
    ),
  ).rejects.toMatchObject({ kind: "generation" });
});
it.each([
  null,
  { ...daily, series: { steps: [] } },
  { ...daily, series: { steps: [NaN] } },
  { ...daily, series: { steps: [Infinity] } },
  { ...daily, dates: ["2026-02-30"] },
  { ...daily, dates: ["2026-01-02", "2026-01-01"], series: { steps: [1, 2] } },
])("rejects malformed daily payload %j", (v) => {
  expect(isDaily(v)).toBe(false);
});
it("accepts missing values but rejects nonfinite and reversed intraday points", () => {
  const intra = {
    date: "2026-01-01",
    metric: "hr",
    timeBasis: "civil",
    timeUnit: "microseconds_since_local_midnight",
    points: [
      [0, null],
      [1000000, 60],
    ],
  };
  expect(isIntraday(intra)).toBe(true);
  expect(
    isIntraday({
      ...intra,
      points: [
        [2, 60],
        [1, 80],
      ],
    }),
  ).toBe(false);
  expect(isIntraday({ ...intra, points: [[86400000000, 60]] })).toBe(false);
});
it.each([
  "../daily.json",
  "https://evil.test/a",
  "//evil.test/a",
  "/daily.json",
  "%2e%2e/a",
  "a\\b",
  "a?b",
  "a#b",
])("rejects unsafe paths before fetching: %s", async (path) => {
  await expect(
    loadSnapshot(
      { ...meta, files: { daily: path } },
      "daily",
      isDaily,
      response({}),
    ),
  ).rejects.toMatchObject({ kind: "schema" });
});
it("rejects a basePath inconsistent with generation", async () => {
  await expect(
    loadSnapshot(
      { ...meta, basePath: "generations/old/" },
      "daily",
      isDaily,
      response({}),
    ),
  ).rejects.toMatchObject({ kind: "schema" });
});
it("classifies missing, HTTP, malformed JSON and schema versions", async () => {
  for (const [status, kind] of [
    [404, "missing"],
    [500, "http"],
  ] as const)
    await expect(
      loadMeta(
        vi.fn<typeof fetch>().mockResolvedValue(new Response("", { status })),
      ),
    ).rejects.toMatchObject({ kind });
  await expect(
    loadMeta(vi.fn<typeof fetch>().mockResolvedValue(new Response("broken"))),
  ).rejects.toMatchObject({ kind: "schema" });
  await expect(
    loadMeta(response({ ...meta, schemaVersion: 2 })),
  ).rejects.toMatchObject({ kind: "schema" });
  await expect(
    loadSnapshot(
      meta,
      "daily",
      isDaily,
      response({ schemaVersion: 2, generation: "new", data: daily }),
    ),
  ).rejects.toMatchObject({ kind: "schema" });
});
it("honors aborts even when an old request resolves after cancellation", async () => {
  const controller = new AbortController();
  const fetcher: typeof fetch = async () => {
    controller.abort();
    return new Response(JSON.stringify(meta));
  };
  await expect(loadMeta(fetcher, controller.signal)).rejects.toMatchObject({
    name: "AbortError",
  });
});

it("rejects invalid inventory interval status while retaining valid extra status fields", async () => {
  const { isInventory } = await import("./data");
  const source = {
    stream_id: "a",
    data_type: "heart_rate",
    label: "心拍",
    representation: "original",
    status: "failed",
    method: "list",
    requested_start: null,
    requested_end: null,
    history_complete: false,
    intervals: [{ start: "2026-01-01", end: "2026-01-07", status: "complete" }],
    pages: 12,
    points: 900,
    last_attempt_at: null,
    reason: "failed",
    http_status: 500,
    projection_status: "available",
  };
  const inventory = { sources: [source], series: [], quality: [] };
  const data = await loadSnapshot(
    { ...meta, files: { "inventory.json": "inventory.json" } },
    "inventory.json",
    isInventory,
    response({ schemaVersion: 1, generation: "new", data: inventory }),
  );
  expect(data.sources[0].intervals[0].status).toBe("complete");
  expect(data.sources[0].status).toBe("failed");
  expect(data.sources[0].points).toBe(900);
  expect(
    isInventory({
      ...inventory,
      sources: [
        { ...source, intervals: [{ start: null, end: null, status: 42 }] },
      ],
    }),
  ).toBe(false);
});
it("rejects prototype-inherited manifest names as missing files", async () => {
  await expect(
    loadSnapshot(meta, "toString", isDaily, response({})),
  ).rejects.toMatchObject({ kind: "missing" });
});
it("validates all payload families rather than accepting arrays or shallow objects", async () => {
  const { isSleep, isAnalytics, isInventory, isIntradayIndex } =
    await import("./data");
  for (const guard of [isSleep, isAnalytics, isInventory, isIntradayIndex]) {
    expect(guard(null)).toBe(false);
    expect(guard([])).toBe(false);
    expect(guard({})).toBe(false);
  }
  expect(isSleep({ sessions: [], timeBasis: "civil" })).toBe(true);
  expect(isInventory({ sources: [], series: [], quality: [] })).toBe(true);
  expect(
    isIntradayIndex({
      metrics: {
        hr: {
          unit: "bpm",
          days: [{ date: "2026-09-07", path: "../bad", count: 5 }],
        },
      },
    }),
  ).toBe(false);
  expect(
    isAnalytics({
      baselines: {},
      movingAverages: {},
      periods: {},
      socialJetlag: {
        hours: null,
        scope: "all_saved_sleep",
        firstDate: null,
        lastDate: null,
      },
    }),
  ).toBe(false);
});
