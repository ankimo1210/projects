import type {
  Meta,
  Daily,
  Intraday,
  Sleep,
  Analytics,
  Inventory,
  IntradayIndex,
} from "./types";
export type * from "./types";
export class DataLoadError extends Error {
  constructor(
    public kind: "missing" | "http" | "schema" | "generation",
    message: string,
  ) {
    super(message);
    this.name = "DataLoadError";
  }
}
export const record = (v: unknown): v is Record<string, unknown> =>
  typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): v is string => typeof v === "string";
const nullableText = (v: unknown) => v === null || text(v);
const finite = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v);
const nullableNumber = (v: unknown) => v === null || finite(v);
const count = (v: unknown) => finite(v) && Number.isSafeInteger(v) && v >= 0;
export function civilDate(v: unknown): v is string {
  return (
    text(v) &&
    /^\d{4}-\d{2}-\d{2}$/.test(v) &&
    Number.isFinite(Date.parse(v)) &&
    new Date(v).toISOString().slice(0, 10) === v
  );
}
const nullableDate = (v: unknown) => v === null || civilDate(v);
const civilTimestamp = (v: unknown) =>
  v === null ||
  (text(v) &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?$/.test(v) &&
    civilDate(v.slice(0, 10)) &&
    Number.isFinite(Date.parse(v)));
export function safePath(v: unknown): v is string {
  return (
    text(v) &&
    v.length > 0 &&
    v
      .split("/")
      .every(
        (p) =>
          /^[A-Za-z0-9_-][A-Za-z0-9_.-]*$/.test(p) && p !== "." && p !== "..",
      )
  );
}
const values = (v: unknown, guard: (v: unknown) => boolean) =>
  record(v) && Object.values(v).every(guard);
export function isMeta(v: unknown): v is Meta {
  return (
    record(v) &&
    v.schemaVersion === 1 &&
    text(v.generation) &&
    /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/.test(v.generation) &&
    v.basePath === `generations/${v.generation}/` &&
    text(v.generatedAt) &&
    /T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v.generatedAt) &&
    Number.isFinite(Date.parse(v.generatedAt)) &&
    record(v.files) &&
    Object.entries(v.files).every(([k, p]) => safePath(k) && safePath(p)) &&
    record(v.freshness) &&
    text(v.freshness.archiveStatus) &&
    text(v.freshness.projectionStatus)
  );
}
export function isDaily(v: unknown): v is Daily {
  if (
    !record(v) ||
    !Array.isArray(v.dates) ||
    !record(v.series) ||
    !values(v.units, text)
  )
    return false;
  const dates = v.dates;
  const units = v.units as Record<string, string>;
  return (
    dates.every((d, i) => civilDate(d) && (i === 0 || d > dates[i - 1])) &&
    Object.entries(v.series).every(
      ([key, a]) =>
        text(units[key]) &&
        Array.isArray(a) &&
        a.length === dates.length &&
        a.every(nullableNumber),
    )
  );
}
export function isIntraday(v: unknown): v is Intraday {
  if (
    !record(v) ||
    !civilDate(v.date) ||
    !text(v.metric) ||
    !safePath(v.metric) ||
    v.metric.includes("/") ||
    v.timeBasis !== "civil" ||
    v.timeUnit !== "microseconds_since_local_midnight" ||
    !Array.isArray(v.points)
  )
    return false;
  let previous = -1;
  return v.points.every((p) => {
    if (
      !Array.isArray(p) ||
      p.length !== 2 ||
      !count(p[0]) ||
      p[0] >= 86400000000 ||
      p[0] < previous ||
      !nullableNumber(p[1])
    )
      return false;
    previous = p[0];
    return true;
  });
}
export function isSleep(v: unknown): v is Sleep {
  return (
    record(v) &&
    v.timeBasis === "civil" &&
    Array.isArray(v.sessions) &&
    v.sessions.every(
      (s) =>
        record(s) &&
        text(s.provider_id) &&
        civilDate(s.date) &&
        civilTimestamp(s.start_ts) &&
        civilTimestamp(s.end_ts) &&
        [
          "minutes_asleep",
          "minutes_deep",
          "minutes_light",
          "minutes_rem",
          "minutes_wake",
          "efficiency",
        ].every((k) => nullableNumber(s[k])) &&
        (s.is_main === null || typeof s.is_main === "boolean"),
    )
  );
}
export function isIntradayIndex(v: unknown): v is IntradayIndex {
  return (
    record(v) &&
    values(
      v.metrics,
      (m) =>
        record(m) &&
        text(m.unit) &&
        Array.isArray(m.days) &&
        m.days.every(
          (d, i, a) =>
            record(d) &&
            civilDate(d.date) &&
            safePath(d.path) &&
            count(d.count) &&
            (i === 0 || d.date > (a[i - 1] as { date: string }).date),
        ),
    )
  );
}
export function isAnalytics(v: unknown): v is Analytics {
  const datedValues = (rows: unknown, keys: string[]) =>
    Array.isArray(rows) &&
    rows.every(
      (r) =>
        record(r) &&
        civilDate(r.date) &&
        keys.every((k) => nullableNumber(r[k])),
    );
  return (
    record(v) &&
    values(v.baselines, (r) =>
      datedValues(r, ["value", "baseline", "sd", "z"]),
    ) &&
    values(v.movingAverages, (r) => datedValues(r, ["value"])) &&
    record(v.periods) &&
    ["30", "90", "180", "365", "all"].every((key) => {
      const p = (v.periods as Record<string, unknown>)[key];
      return (
        record(p) &&
        nullableDate(p.startDate) &&
        nullableDate(p.endDate) &&
        Array.isArray(p.correlations) &&
        p.correlations.every(
          (c) =>
            record(c) &&
            text(c.x) &&
            text(c.y) &&
            count(c.lag) &&
            count(c.n) &&
            nullableNumber(c.spearman) &&
            (c.spearman === null || Math.abs(c.spearman as number) <= 1) &&
            [null, "insufficient_pairs", "constant_series"].includes(
              c.reason as null,
            ),
        ) &&
        values(
          p.coverage,
          (a) =>
            Array.isArray(a) &&
            a.every(
              (d) =>
                record(d) &&
                civilDate(d.date) &&
                typeof d.has_data === "boolean",
            ),
        )
      );
    }) &&
    record(v.socialJetlag) &&
    nullableNumber(v.socialJetlag.hours) &&
    v.socialJetlag.scope === "all_saved_sleep" &&
    nullableDate(v.socialJetlag.firstDate) &&
    nullableDate(v.socialJetlag.lastDate)
  );
}
export function isInventory(v: unknown): v is Inventory {
  return (
    record(v) &&
    Array.isArray(v.sources) &&
    v.sources.every(
      (s) =>
        record(s) &&
        [
          "stream_id",
          "data_type",
          "label",
          "representation",
          "status",
          "projection_status",
        ].every((k) => text(s[k])) &&
        [
          "method",
          "requested_start",
          "requested_end",
          "last_attempt_at",
          "reason",
        ].every((k) => nullableText(s[k])) &&
        typeof s.history_complete === "boolean" &&
        count(s.pages) &&
        count(s.points) &&
        (s.stored_pages === undefined || count(s.stored_pages)) &&
        (s.stored_points === undefined || count(s.stored_points)) &&
        nullableNumber(s.http_status) &&
        Array.isArray(s.intervals) &&
        s.intervals.every(
          (i) =>
            record(i) &&
            nullableText(i.start) &&
            nullableText(i.end) &&
            (i.status === undefined || text(i.status)),
        ),
    ) &&
    Array.isArray(v.series) &&
    v.series.every(
      (s) =>
        record(s) &&
        text(s.metric) &&
        (s.storage === "daily" ||
          s.storage === "intraday" ||
          s.storage === "sleep") &&
        count(s.n) &&
        nullableDate(s.first_date) &&
        nullableDate(s.last_date) &&
        (s.first_date === null ||
          s.last_date === null ||
          s.first_date <= s.last_date) &&
        text(s.unit),
    ) &&
    Array.isArray(v.quality) &&
    v.quality.every(
      (q) =>
        record(q) &&
        safePath(q.path) &&
        q.reason === "non_finite_number" &&
        count(q.count),
    )
  );
}
async function readJson(
  path: string,
  fetcher: typeof fetch,
  signal?: AbortSignal,
  noStore = false,
): Promise<unknown> {
  signal?.throwIfAborted();
  let response: Response;
  try {
    response = await fetcher(path, {
      signal,
      cache: noStore ? "no-store" : "default",
      redirect: "error",
      credentials: "same-origin",
    });
  } catch (error) {
    signal?.throwIfAborted();
    if (error instanceof DOMException && error.name === "AbortError")
      throw error;
    throw new DataLoadError(
      "http",
      "データを読み込めません。ローカル配信サーバーを確認してください。",
    );
  }
  signal?.throwIfAborted();
  if (!response.ok)
    throw new DataLoadError(
      response.status === 404 ? "missing" : "http",
      `データ取得に失敗しました (HTTP ${response.status})。`,
    );
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    signal?.throwIfAborted();
    throw new DataLoadError("schema", "JSON の形式が正しくありません。");
  }
  signal?.throwIfAborted();
  return value;
}
export async function loadMeta(
  fetcher: typeof fetch = fetch,
  signal?: AbortSignal,
): Promise<Meta> {
  const value = await readJson("/data/meta.json", fetcher, signal, true);
  if (!isMeta(value))
    throw new DataLoadError("schema", "エクスポート情報の形式が一致しません。");
  return value;
}
export async function loadSnapshot<T>(
  meta: Meta,
  name: string,
  validate: (v: unknown) => v is T,
  fetcher: typeof fetch = fetch,
  signal?: AbortSignal,
): Promise<T> {
  if (!isMeta(meta))
    throw new DataLoadError("schema", "安全なデータ参照ではありません。");
  const path = Object.hasOwn(meta.files, name) ? meta.files[name] : undefined;
  if (!path)
    throw new DataLoadError("missing", `${name} は書き出されていません。`);
  if (!safePath(path))
    throw new DataLoadError("schema", "安全なデータ参照ではありません。");
  const value = await readJson(
    `/data/${meta.basePath}${path}`,
    fetcher,
    signal,
  );
  if (!record(value) || value.schemaVersion !== 1)
    throw new DataLoadError("schema", "対応しないスナップショット形式です。");
  if (value.generation !== meta.generation)
    throw new DataLoadError(
      "generation",
      "異なる世代のデータです。再読み込みしてください。",
    );
  if (!validate(value.data))
    throw new DataLoadError("schema", `${name} のデータ形式が一致しません。`);
  return value.data;
}
