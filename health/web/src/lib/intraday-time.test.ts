import { describe, expect, it } from "vitest";
import { isIntraday } from "./data";
import { axisTime, inputTime, parseInputTime, observationTime } from "./intraday-time";
import type { Intraday } from "./types";

const physical = {
  date: "2025-01-01", metric: "hr", timeBasis: "physical",
  timeUnit: "microseconds_since_unix_epoch",
  points: [[1735707600000000, 65], [1735711200000000, 72]],
  civilTimes: [50400000000, 50400000000], utcOffsets: [32400, 28800],
};
describe("physical intraday time", () => {
  it("accepts distinct instants with identical civil clocks", () => {
    expect(isIntraday(physical)).toBe(true);
    expect(isIntraday({ ...physical, utcOffsets: [32400] })).toBe(false);
    expect(isIntraday({ ...physical, civilTimes: [86400000000, 0] })).toBe(false);
    expect(isIntraday({ ...physical, points: [...physical.points].reverse() })).toBe(false);
    expect(isIntraday({ ...physical, points: [physical.points[0], physical.points[0]] })).toBe(false);
    expect(isIntraday({ ...physical, utcOffsets: [null, 28800.5] })).toBe(true);
  });
  it("formats UTC axes and preserves the original clock and offset", () => {
    const data = physical as Intraday;
    expect(axisTime(data, 1735707600000000)).toBe("01-01 05:00:00 UTC");
    expect(observationTime(data, 1735707600000000)).toBe("2025-01-01 14:00:00（UTC+09:00）");
    expect(observationTime(data, 1735711200000000)).toBe("2025-01-01 14:00:00（UTC+08:00）");
    expect(inputTime(data, 1735707600000000)).toBe("2025-01-01T05:00:00");
    expect(parseInputTime(data, "2025-01-01T06:00:00")).toBe(1735711200000000);
    expect(parseInputTime(data, "")).toBeNaN();
  });
  it("keeps legacy civil data readable", () => {
    const data: Intraday = { date: "2025-01-01", metric: "hr", timeBasis: "civil",
      timeUnit: "microseconds_since_local_midnight", points: [[50400000000, 65]] };
    expect(isIntraday(data)).toBe(true);
    expect(axisTime(data, 50400000000)).toBe("14:00:00");
    expect(inputTime(data, 50400000000)).toBe("14:00:00");
    expect(parseInputTime(data, "15:00:00")).toBe(54000000000);
  });
});
