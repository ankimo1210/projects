// Reader for the P1 preflop chart-pack dev fixture
// (gto/fixtures/packs/preflop-charts.dev.v1.json, written by
// scripts/build_preflop_fixture.py). The P0b binary pack format replaces the
// JSON carrier, but the validation contract stays: readers reject unknown
// schema majors and malformed content loudly rather than render wrong charts.

import { NUM_HAND_LABELS } from "@gto/domain";

export const PREFLOP_CHART_PACK_SCHEMA = "gto.preflop-chart-pack";
export const SUPPORTED_SCHEMA_MAJOR = 1;

/** One hand-authored preflop chart; freqs rows follow ALL_HAND_LABELS_GRID order, u8 summing to 255. */
export interface PreflopChart {
  id: string;
  kind: "rfi" | "facing" | "vs3bet";
  title: string;
  actions: string[];
  freqs: number[][];
}

export interface PreflopChartPack {
  schema: typeof PREFLOP_CHART_PACK_SCHEMA;
  schemaVersion: string;
  quality: "CHART";
  game: string;
  charts: PreflopChart[];
}

export class PackFormatError extends Error {
  override name = "PackFormatError";
}

function fail(msg: string): never {
  throw new PackFormatError(msg);
}

const CHART_KINDS = new Set(["rfi", "facing", "vs3bet"]);

/**
 * Validate raw JSON into a PreflopChartPack. Throws PackFormatError on any
 * structural problem — a chart that fails validation must never be rendered.
 */
export function parsePreflopChartPack(raw: unknown): PreflopChartPack {
  if (typeof raw !== "object" || raw === null) fail("pack is not an object");
  const obj = raw as Record<string, unknown>;

  if (obj.schema !== PREFLOP_CHART_PACK_SCHEMA) {
    fail(`unknown schema: ${String(obj.schema)}`);
  }
  const version = obj.schema_version;
  if (typeof version !== "string" || !/^\d+\.\d+\.\d+$/.test(version)) {
    fail(`bad schema_version: ${String(version)}`);
  }
  const major = Number(version.split(".")[0]);
  if (major !== SUPPORTED_SCHEMA_MAJOR) {
    fail(`unsupported schema major ${major} (reader supports ${SUPPORTED_SCHEMA_MAJOR})`);
  }
  if (obj.quality !== "CHART") fail(`unexpected quality label: ${String(obj.quality)}`);
  if (typeof obj.game !== "string" || obj.game.length === 0) fail("missing game");
  if (!Array.isArray(obj.charts) || obj.charts.length === 0) fail("missing charts");

  const seen = new Set<string>();
  const charts: PreflopChart[] = obj.charts.map((c, idx) => {
    if (typeof c !== "object" || c === null) fail(`chart[${idx}] is not an object`);
    const ch = c as Record<string, unknown>;
    const id = ch.id;
    if (typeof id !== "string" || id.length === 0) fail(`chart[${idx}] missing id`);
    if (seen.has(id)) fail(`duplicate chart id: ${id}`);
    seen.add(id);
    if (typeof ch.kind !== "string" || !CHART_KINDS.has(ch.kind)) {
      fail(`${id}: bad kind ${String(ch.kind)}`);
    }
    if (typeof ch.title !== "string" || ch.title.length === 0) fail(`${id}: missing title`);
    const actions = ch.actions;
    if (!Array.isArray(actions) || actions.length < 2 || !actions.every((a) => typeof a === "string" && a.length > 0)) {
      fail(`${id}: bad actions`);
    }
    const freqs = ch.freqs;
    if (!Array.isArray(freqs) || freqs.length !== NUM_HAND_LABELS) {
      fail(`${id}: expected ${NUM_HAND_LABELS} freq rows, got ${Array.isArray(freqs) ? freqs.length : typeof freqs}`);
    }
    freqs.forEach((row, r) => {
      if (!Array.isArray(row) || row.length !== actions.length) {
        fail(`${id}: row ${r} length != actions length`);
      }
      let sum = 0;
      for (const v of row) {
        if (!Number.isInteger(v) || v < 0 || v > 255) fail(`${id}: row ${r} has non-u8 value ${v}`);
        sum += v;
      }
      if (sum !== 255) fail(`${id}: row ${r} sums to ${sum}, expected 255`);
    });
    return {
      id,
      kind: ch.kind as PreflopChart["kind"],
      title: ch.title,
      actions: actions as string[],
      freqs: freqs as number[][],
    };
  });

  return {
    schema: PREFLOP_CHART_PACK_SCHEMA,
    schemaVersion: version,
    quality: "CHART",
    game: obj.game,
    charts,
  };
}

/** Frequency fraction (0..1) of `action` for the grid cell at row-major index. */
export function actionFraction(chart: PreflopChart, handIndex: number, action: string): number {
  const a = chart.actions.indexOf(action);
  if (a < 0) throw new RangeError(`${chart.id}: unknown action ${action}`);
  const row = chart.freqs[handIndex];
  if (row === undefined) throw new RangeError(`hand index out of range: ${handIndex}`);
  return (row[a] ?? 0) / 255;
}
