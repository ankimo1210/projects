import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, test } from "node:test";

import { validateDataset } from "../experiments/tremor-dashboard/src/lib/rates/metrics.ts";
import {
  DATASET_FILENAMES,
  generateCanonicalDataset,
  generateFixtureDatasets,
  serializeDataset,
  writeDatasets,
} from "./generate-jgb-demo.mjs";

const projectRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const hash = (contents) => createHash("sha256").update(contents).digest("hex");

describe("JGB demo generator", () => {
  test("reproduces exactly 60 weekday observations ending at the fixed final curve", () => {
    const first = generateCanonicalDataset();
    const second = generateCanonicalDataset();

    assert.equal(serializeDataset(first), serializeDataset(second));
    assert.equal(first.snapshots.length, 60);
    assert.equal(first.snapshots[0].date, "2026-06-15");
    assert.equal(first.snapshots.at(-1).date, "2026-09-04");
    assert.deepEqual(
      first.snapshots.at(-1).points.map((point) => point.yieldPct),
      [0.92, 1.28, 1.54, 1.85, 2.34, 2.51, 2.63],
    );
    assert.ok(
      first.snapshots.every(({ date }) => {
        const weekday = new Date(`${date}T00:00:00.000Z`).getUTCDay();
        return weekday >= 1 && weekday <= 5;
      }),
    );
    assert.equal(validateDataset(first), first);
  });

  test("produces valid and distinct missing, negative, and flat fixtures", () => {
    const fixtures = generateFixtureDatasets();

    assert.deepEqual(Object.keys(fixtures), ["missing", "negative", "flat"]);
    for (const fixture of Object.values(fixtures)) validateDataset(fixture);
    assert.equal(fixtures.missing.snapshots.at(-1).points[3].yieldPct, null);
    assert.ok(
      fixtures.negative.snapshots
        .at(-1)
        .points.some((point) => (point.yieldPct ?? 0) < 0),
    );
    assert.equal(
      new Set(
        fixtures.flat.snapshots.at(-1).points.map((point) => point.yieldPct),
      ).size,
      1,
    );
  });

  test("writes byte-identical canonical and app copies", async () => {
    const temporaryRoot = await mkdtemp(join(tmpdir(), "rates-ui-data-"));
    try {
      await writeDatasets(temporaryRoot);
      for (const filename of DATASET_FILENAMES) {
        const canonical = await readFile(join(temporaryRoot, "data", filename));
        const appCopy = await readFile(
          join(
            temporaryRoot,
            "experiments",
            "tremor-dashboard",
            "src",
            "data",
            "rates",
            filename,
          ),
        );
        assert.equal(hash(canonical), hash(appCopy));
      }
    } finally {
      await rm(temporaryRoot, { recursive: true, force: true });
    }
  });

  test("keeps all checked-in app JSON files byte-identical to their canonical copies", async () => {
    const fixtures = generateFixtureDatasets();
    const expectedDatasets = [
      generateCanonicalDataset(),
      fixtures.missing,
      fixtures.negative,
      fixtures.flat,
    ];
    for (const [index, filename] of DATASET_FILENAMES.entries()) {
      const canonical = await readFile(join(projectRoot, "data", filename));
      const appCopy = await readFile(
        join(
          projectRoot,
          "experiments",
          "tremor-dashboard",
          "src",
          "data",
          "rates",
          filename,
        ),
      );
      assert.equal(hash(canonical), hash(appCopy));
      assert.equal(
        canonical.toString("utf8"),
        serializeDataset(expectedDatasets[index]),
      );
    }
  });
});
