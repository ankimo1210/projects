// Contract: health/docs/web-data-contract.md (schema v1).
export type Period = "30" | "90" | "180" | "365" | "all";
export type Snapshot<T> = { schemaVersion: 1; generation: string; data: T };
export type Meta = {
  schemaVersion: 1;
  generation: string;
  generatedAt: string;
  basePath: string; // generations/<safe-id>/
  files: Record<string, string>; // key=relative path, value=same relative path
  freshness: { archiveStatus: string; projectionStatus: string };
};
export type Daily = {
  dates: string[]; // sorted, every civil day between first/last saved daily row
  series: Record<string, (number | null)[]>; // every column has dates.length
  units: Record<string, string>;
  providers?: Record<string, "google" | "healthplanet">; // absent in older snapshots
};
export type SleepSession = {
  provider_id: string;
  date: string;
  start_ts: string | null;
  end_ts: string | null;
  minutes_asleep: number | null;
  minutes_deep: number | null;
  minutes_light: number | null;
  minutes_rem: number | null;
  minutes_wake: number | null;
  efficiency: number | null;
  is_main: boolean | null;
};
export type Sleep = { sessions: SleepSession[]; timeBasis: "civil" };
export type Intraday = {
  date: string;
  metric: string;
  timeBasis: "civil";
  timeUnit: "microseconds_since_local_midnight";
  points: [number, number | null][];
};
export type IntradayIndex = {
  metrics: Record<
    string,
    {
      unit: string;
      days: {
        date: string;
        path: string;
        count: number;
      }[];
    }
  >;
};
export type Baseline = {
  date: string;
  value: number | null;
  baseline: number | null;
  sd: number | null;
  z: number | null;
};
export type Correlation = {
  x: string;
  y: string;
  lag: number;
  n: number;
  spearman: number | null;
  reason: "insufficient_pairs" | "constant_series" | null;
};
export type CoverageDay = { date: string; has_data: boolean };
export type Analytics = {
  baselines: Record<string, Baseline[]>;
  movingAverages: Record<string, { date: string; value: number | null }[]>;
  periods: Record<
    Period,
    {
      startDate: string | null;
      endDate: string | null;
      correlations: Correlation[];
      coverage: Record<string, CoverageDay[]>;
    }
  >;
  socialJetlag: {
    hours: number | null;
    scope: "all_saved_sleep";
    firstDate: string | null;
    lastDate: string | null;
  };
};
export type SourceCoverage = {
  stream_id: string;
  data_type: string;
  label: string;
  representation: string;
  status: string;
  method: string | null;
  requested_start: string | null;
  requested_end: string | null;
  history_complete: boolean;
  intervals: { start: string | null; end: string | null; status?: string }[];
  /** Latest attempt counts; not cumulative storage. */
  pages: number;
  points: number;
  /** Stored totals across attempts; absent in earlier exports. */
  stored_pages?: number;
  stored_points?: number;
  last_attempt_at: string | null;
  reason: string | null;
  http_status: number | null;
  projection_status: string;
};
export type SeriesInventory = {
  metric: string;
  storage: "daily" | "intraday" | "sleep";
  n: number;
  first_date: string | null;
  last_date: string | null;
  unit: string;
};
export type Inventory = {
  sources: SourceCoverage[];
  series: SeriesInventory[];
  quality: { path: string; reason: "non_finite_number"; count: number }[];
};

export type HealthPlanetMetric =
  | "weight_kg"
  | "body_fat_pct"
  | "systolic_mmhg"
  | "diastolic_mmhg"
  | "pulse_bpm"
  | "steps";
/** An archived observation, including changed values at the same civil timestamp. */
export type HealthPlanetMeasurement = {
  id: string; // Local observation identity, not a provider measurement ID.
  metric: HealthPlanetMetric;
  tag: string;
  timestamp: string; // ISO civil time, without a timezone.
  value: number;
  unit: string;
  model: string;
};
export type HealthPlanet = {
  provider: "healthplanet";
  timeBasis: "civil";
  status: "not_connected" | "pending" | "partial" | "available";
  historyComplete: false;
  sources: SourceCoverage[];
  measurements: HealthPlanetMeasurement[];
  unsupported: { metric: string; label: string; reason: string }[];
  quality: { unparsedRecords: number };
};
