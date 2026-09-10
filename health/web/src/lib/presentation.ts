import type { Daily, Period, SleepSession } from "./types";
const dayMs = 86400000;
export function latestMetric(daily: Daily, key: string) {
  const series = daily.series[key];
  if (!series) return null;
  for (let i = series.length - 1; i >= 0; i--)
    if (series[i] !== null) {
      const date = daily.dates[i],
        previous = new Date(Date.parse(date) - dayMs)
          .toISOString()
          .slice(0, 10);
      const j = daily.dates.indexOf(previous),
        prior = j < 0 ? null : series[j];
      return {
        value: series[i]!,
        date,
        delta: prior === null ? null : series[i]! - prior,
        stale: date !== daily.dates.at(-1),
      };
    }
  return null;
}
export function clipRows<T extends { date: string }>(
  rows: T[],
  period: Period,
  end: string,
) {
  if (!end) return [];
  if (period === "all") return rows.filter((r) => r.date <= end);
  const start = new Date(Date.parse(end) - (Number(period) - 1) * dayMs)
    .toISOString()
    .slice(0, 10);
  return rows.filter((r) => r.date >= start && r.date <= end);
}
export function inventoryCSV(rows: Record<string, unknown>[]) {
  const keys = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const cell = (v: unknown) => {
    let s =
      v === null || v === undefined
        ? ""
        : typeof v === "object"
          ? JSON.stringify(v)
          : String(v);
    if (/^[\s]*[=+@-]/.test(s)) s = "'" + s;
    return '"' + s.replaceAll('"', '""') + '"';
  };
  return (
    "\ufeff" +
    [
      keys.map(cell).join(","),
      ...rows.map((r) => keys.map((k) => cell(r[k])).join(",")),
    ].join("\r\n")
  );
}
export function sleepKind(s: SleepSession): "classic" | "stages" | "unknown" {
  return [s.minutes_deep, s.minutes_light, s.minutes_rem].some(
    (v) => v !== null,
  )
    ? "stages"
    : s.minutes_asleep !== null || s.minutes_wake !== null
      ? "classic"
      : "unknown";
}
export function sleepWeekdays(sessions: SleepSession[]) {
  return ["月", "火", "水", "木", "金", "土", "日"].map((date, i) => {
    const values = sessions
      .filter(
        (s) =>
          s.is_main === true &&
          s.minutes_asleep !== null &&
          (new Date(s.date).getUTCDay() + 6) % 7 === i,
      )
      .map((s) => s.minutes_asleep!);
    return {
      date,
      minutes: values.length
        ? values.reduce((a, b) => a + b, 0) / values.length
        : null,
      n: values.length,
    };
  });
}
export function nightRange(s: SleepSession): [number, number] | null {
  if (!s.start_ts || !s.end_ts) return null;
  // UTC is used only as arithmetic on civil components, never a claimed source timezone.
  const anchor = Date.parse(s.date) - 12 * 3600000;
  return [
    (Date.parse(s.start_ts + "Z") - anchor) / 3600000,
    (Date.parse(s.end_ts + "Z") - anchor) / 3600000,
  ];
}
export const labels: Record<string, string> = {
  steps: "歩数",
  sleep_minutes: "睡眠時間",
  resting_hr: "安静時心拍",
  hrv_rmssd: "HRV 平均",
  hrv_deep_rmssd: "HRV 深い睡眠時",
  temp_skin_relative: "皮膚温（基準比）",
  distance_km: "距離",
  calories: "消費エネルギー",
  minutes_lightly_active: "軽い活動",
  minutes_fairly_active: "中程度",
  minutes_very_active: "高強度",
  weight_kg: "体重",
  fat_pct: "体脂肪率",
  spo2_avg: "SpO2 平均",
  spo2_lower_bound: "下限",
  spo2_upper_bound: "上限",
  breathing_rate: "呼吸数",
};
export const units: Record<string, string> = {
  steps: "歩",
  min: "分",
  bpm: "bpm",
  ms: "ms",
  km: "km",
  kcal: "kcal",
  kg: "kg",
  "%": "%",
  "°C": "℃",
  "breaths/min": "回/分",
  unknown: "単位不明",
};
export const formatValue = (value: number | null | undefined) =>
  value === null || value === undefined
    ? "—"
    : value.toLocaleString("ja-JP", { maximumFractionDigits: 1 });
export const statusLabel: Record<string, string> = {
  pending: "未取得",
  complete: "確認範囲の取得完了",
  empty: "確認範囲にデータなし",
  partial: "途中",
  permission_denied: "権限不足",
  unsupported: "取得非対応",
  failed: "取得失敗",
  rate_limited: "レート制限",
  unknown_history: "過去の範囲が未確認",
  storage_error: "保存失敗",
  available: "表示データあり",
  unavailable: "表示データなし",
  not_supported: "表示未対応",
  not_implemented: "表示未対応",
  unsupported_projection: "表示未対応",
};
export function calendarRows<T extends { date: string }>(
  rows: T[],
): (T | { date: string })[] {
  const result: (T | { date: string })[] = [];
  for (const row of rows) {
    const previous = result.at(-1);
    if (previous && /^\d{4}-\d{2}-\d{2}$/.test(row.date)) {
      for (
        let time = Date.parse(previous.date) + 86400000;
        time < Date.parse(row.date);
        time += 86400000
      )
        result.push({ date: new Date(time).toISOString().slice(0, 10) });
    }
    result.push(row);
  }
  return result;
}
