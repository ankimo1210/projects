import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { ALL_HAND_LABELS_GRID } from "@gto/domain";
import {
  PackFormatError,
  actionFraction,
  parsePreflopChartPack,
} from "./preflop-chart-pack.ts";

const FIXTURE_URL = new URL(
  "../../../fixtures/packs/preflop-charts.dev.v1.json",
  import.meta.url,
);

function loadFixture(): unknown {
  return JSON.parse(readFileSync(FIXTURE_URL, "utf8"));
}

test("parses the committed dev fixture (15 charts, all invariants)", () => {
  const pack = parsePreflopChartPack(loadFixture());
  assert.equal(pack.charts.length, 15);
  assert.equal(pack.quality, "CHART");
  const kinds = new Map<string, number>();
  for (const c of pack.charts) kinds.set(c.kind, (kinds.get(c.kind) ?? 0) + 1);
  assert.deepEqual(Object.fromEntries(kinds), { rfi: 5, facing: 5, vs3bet: 5 });
});

test("known chart values: BTN opens AA at 100%, folds 72o", () => {
  const pack = parsePreflopChartPack(loadFixture());
  const btn = pack.charts.find((c) => c.id === "rfi:BTN")!;
  const aa = ALL_HAND_LABELS_GRID.indexOf("AA");
  const trash = ALL_HAND_LABELS_GRID.indexOf("72o");
  assert.equal(actionFraction(btn, aa, "R"), 1);
  assert.equal(actionFraction(btn, aa, "F"), 0);
  assert.equal(actionFraction(btn, trash, "F"), 1);
});

test("rejects unknown schema and wrong major", () => {
  const base = loadFixture() as Record<string, unknown>;
  assert.throws(
    () => parsePreflopChartPack({ ...base, schema: "gto.other" }),
    PackFormatError,
  );
  assert.throws(
    () => parsePreflopChartPack({ ...base, schema_version: "2.0.0" }),
    PackFormatError,
  );
});

test("rejects structural corruption", () => {
  const mutate = (fn: (p: any) => void) => {
    const p = loadFixture() as any;
    fn(p);
    return p;
  };
  // wrong row count
  assert.throws(
    () => parsePreflopChartPack(mutate((p) => p.charts[0].freqs.pop())),
    PackFormatError,
  );
  // row sum broken
  assert.throws(
    () => parsePreflopChartPack(mutate((p) => { p.charts[0].freqs[0][0] += 1; })),
    PackFormatError,
  );
  // non-integer frequency
  assert.throws(
    () => parsePreflopChartPack(mutate((p) => { p.charts[0].freqs[0] = [254.5, 0.5]; })),
    PackFormatError,
  );
  // duplicate chart id
  assert.throws(
    () => parsePreflopChartPack(mutate((p) => { p.charts[1].id = p.charts[0].id; })),
    PackFormatError,
  );
  // row length != actions length
  assert.throws(
    () => parsePreflopChartPack(mutate((p) => p.charts[0].freqs[3].push(0))),
    PackFormatError,
  );
});

test("actionFraction bounds", () => {
  const pack = parsePreflopChartPack(loadFixture());
  const chart = pack.charts[0]!;
  assert.throws(() => actionFraction(chart, 0, "NOPE"), RangeError);
  assert.throws(() => actionFraction(chart, 169, chart.actions[0]!), RangeError);
});
