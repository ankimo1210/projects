import { civilDate, isSourceCoverage, record } from "./data";
import { downsampleMinMax } from "./downsample";
import { clipRows, inventoryCSV } from "./presentation";
import type { HealthPlanet, HealthPlanetMeasurement, HealthPlanetMetric, Period } from "./types";

export const healthPlanetLabels: Record<HealthPlanetMetric, string> = {
  weight_kg: "体重",
  body_fat_pct: "体脂肪率",
  systolic_mmhg: "収縮期血圧",
  diastolic_mmhg: "拡張期血圧",
  pulse_bpm: "脈拍",
  steps: "歩数",
};
const text = (v: unknown): v is string => typeof v === "string";
const nonempty = (v: unknown): v is string => text(v) && v.length > 0;
/** Check civil components directly: the browser timezone/DST must not change validity. */
function timestamp(v: unknown): v is string {
  return text(v) &&
    /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?$/.test(v) &&
    civilDate(v.slice(0, 10));
}
export function isHealthPlanet(v: unknown): v is HealthPlanet {
  return record(v) &&
    v.provider === "healthplanet" && v.timeBasis === "civil" &&
    ["not_connected", "pending", "partial", "available"].includes(v.status as string) &&
    v.historyComplete === false &&
    Array.isArray(v.sources) && v.sources.every(isSourceCoverage) &&
    Array.isArray(v.measurements) && v.measurements.every((m) =>
      record(m) && nonempty(m.id) && nonempty(m.metric) &&
      Object.hasOwn(healthPlanetLabels, m.metric) && nonempty(m.tag) &&
      timestamp(m.timestamp) && typeof m.value === "number" && Number.isFinite(m.value) &&
      nonempty(m.unit) && text(m.model)
    ) &&
    Array.isArray(v.unsupported) && v.unsupported.every((u) =>
      record(u) && nonempty(u.metric) && text(u.label) && text(u.reason)
    ) && record(v.quality) && typeof v.quality.unparsedRecords === "number" &&
    Number.isSafeInteger(v.quality.unparsedRecords) && v.quality.unparsedRecords >= 0;
}

export type HealthPlanetFilter = {
  period: Period;
  startDate?: string;
  endDate?: string;
  metric?: HealthPlanetMetric | "all";
};
/** The period ends at this provider's latest stored civil day, across all metrics. */
export function filterHealthPlanetMeasurements(
  measurements: HealthPlanetMeasurement[],
  { period, startDate = "", endDate = "", metric = "all" }: HealthPlanetFilter,
) {
  const dated = measurements.map((measurement) => ({
    date: measurement.timestamp.slice(0, 10), measurement,
  }));
  const latest = dated.reduce((end, row) => row.date > end ? row.date : end, "");
  return clipRows(dated, period, latest)
    .filter(({ date, measurement }) =>
      (!startDate || date >= startDate) && (!endDate || date <= endDate) &&
      (metric === "all" || measurement.metric === metric)
    )
    .map(({ measurement }) => measurement)
    .sort((a, b) => a.timestamp < b.timestamp ? -1 : a.timestamp > b.timestamp ? 1 : 0);
}

export function healthPlanetCSV(measurements: HealthPlanetMeasurement[]) {
  return inventoryCSV(measurements.map((m) => ({
    provider: "healthplanet", timeBasis: "civil", id: m.id, metric: m.metric,
    tag: m.tag, timestamp: m.timestamp, value: m.value, unit: m.unit, model: m.model,
  })));
}

/** Display only, one metric/unit at a time. Index sampling retains observation identity. */
export function healthPlanetChartRows(measurements: HealthPlanetMeasurement[], target = 2000) {
  return downsampleMinMax(measurements.map((m, x) => ({ x, y: m.value })), target)
    .map(({ x: index }) => {
      const m = measurements[index];
      const [hours, minutes, seconds] = m.timestamp.slice(11).split(":").map(Number);
      // Numeric civil coordinates only, not an assertion that the source uses UTC.
      const x = Date.parse(m.timestamp.slice(0, 10)) +
        (hours * 3600 + minutes * 60 + seconds) * 1000;
      return { ...m, x };
    });
}
