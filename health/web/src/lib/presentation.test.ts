import { expect, it } from "vitest";
import {
  latestMetric,
  clipRows,
  inventoryCSV,
  sleepWeekdays,
  sleepKind,
  nightRange,
} from "./presentation";
import type { SleepSession } from "./types";
it("compares calendar yesterday only, retains zero, and exposes stale value dates", () => {
  const daily = {
    dates: ["2026-09-01", "2026-09-02", "2026-09-03"],
    series: { steps: [10, null, 0], resting_hr: [60, 61, null] },
    units: { steps: "steps", resting_hr: "bpm" },
  };
  expect(latestMetric(daily, "steps")).toEqual({
    value: 0,
    date: "2026-09-03",
    delta: null,
    stale: false,
  });
  expect(latestMetric(daily, "resting_hr")).toEqual({
    value: 61,
    date: "2026-09-02",
    delta: 1,
    stale: true,
  });
  expect(latestMetric(daily, "weight_kg")).toBeNull();
});
it("clips an inclusive calendar window rather than a number of records", () => {
  expect(
    clipRows(
      [{ date: "2025-12-01" }, { date: "2025-12-03" }, { date: "2026-01-01" }],
      "30",
      "2026-01-01",
    ),
  ).toEqual([{ date: "2025-12-03" }, { date: "2026-01-01" }]);
});
it("exports quoted CSV and neutralizes spreadsheet formulas without changing source", () => {
  const rows = [
    { label: '=HYPERLINK("bad")', reason: "one,two\nthree", points: 0 },
  ];
  const old = structuredClone(rows);
  const csv = inventoryCSV(rows);
  expect(csv).toContain('"\'=HYPERLINK(""bad"")"');
  expect(csv).toContain('"one,two\nthree"');
  expect(rows).toEqual(old);
});
const session = {
  provider_id: "a",
  date: "2026-09-07",
  start_ts: "2026-09-06T23:30:00",
  end_ts: "2026-09-07T07:00:00",
  minutes_asleep: 400,
  minutes_deep: null,
  minutes_light: null,
  minutes_rem: null,
  minutes_wake: 20,
  efficiency: 90,
  is_main: true,
} satisfies SleepSession;
it("distinguishes classic, detailed and unknown stages while excluding naps from weekdays", () => {
  expect(sleepKind(session)).toBe("classic");
  expect(sleepKind({ ...session, minutes_deep: 70 })).toBe("stages");
  expect(
    sleepKind({ ...session, minutes_asleep: null, minutes_wake: null }),
  ).toBe("unknown");
  const week = sleepWeekdays([
    session,
    { ...session, is_main: false, minutes_asleep: 10 },
  ]);
  expect(week[0]).toEqual({ date: "月", minutes: 400, n: 1 });
  expect(week[1].minutes).toBeNull();
});
it("places civil sleep crossing midnight on the previous-noon axis", () => {
  expect(nightRange(session)).toEqual([11.5, 19]);
  expect(nightRange({ ...session, start_ts: null })).toBeNull();
});
it("inserts missing calendar days into charts without inventing zeros or mutating source rows", async () => {
  const { calendarRows } = await import("./presentation");
  const rows = [
    { date: "2026-09-01", y: 5 },
    { date: "2026-09-03", y: 7 },
  ];
  expect(calendarRows(rows)).toEqual([
    { date: "2026-09-01", y: 5 },
    { date: "2026-09-02" },
    { date: "2026-09-03", y: 7 },
  ]);
  expect(rows).toHaveLength(2);
});
