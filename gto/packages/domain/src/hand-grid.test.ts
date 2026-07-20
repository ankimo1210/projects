import { test } from "node:test";
import assert from "node:assert/strict";
import {
  ALL_HAND_LABELS_GRID,
  GRID_SIZE,
  NUM_HAND_LABELS,
  comboCount,
  gridHandLabel,
} from "./hand-grid.ts";

test("grid corners and diagonal", () => {
  assert.equal(gridHandLabel(0, 0), "AA");
  assert.equal(gridHandLabel(12, 12), "22");
  assert.equal(gridHandLabel(0, 1), "AKs");
  assert.equal(gridHandLabel(1, 0), "AKo");
  assert.equal(gridHandLabel(0, 12), "A2s");
  assert.equal(gridHandLabel(12, 0), "A2o");
});

test("all 169 labels are unique and cover every hand class", () => {
  assert.equal(ALL_HAND_LABELS_GRID.length, NUM_HAND_LABELS);
  assert.equal(new Set(ALL_HAND_LABELS_GRID).size, NUM_HAND_LABELS);
  const pairs = ALL_HAND_LABELS_GRID.filter((h) => h.length === 2);
  const suited = ALL_HAND_LABELS_GRID.filter((h) => h[2] === "s");
  const offsuit = ALL_HAND_LABELS_GRID.filter((h) => h[2] === "o");
  assert.equal(pairs.length, 13);
  assert.equal(suited.length, 78);
  assert.equal(offsuit.length, 78);
});

test("combo counts sum to 1326", () => {
  const total = ALL_HAND_LABELS_GRID.reduce((s, h) => s + comboCount(h), 0);
  assert.equal(total, 1326);
});

test("row-major order matches the fixture-builder convention", () => {
  // Spot-check row 1 (K row): KAs is written AKo... row 1 col 0 = offsuit AKo,
  // diagonal KK, then suited K-x to the right.
  assert.equal(ALL_HAND_LABELS_GRID[GRID_SIZE * 1 + 0], "AKo");
  assert.equal(ALL_HAND_LABELS_GRID[GRID_SIZE * 1 + 1], "KK");
  assert.equal(ALL_HAND_LABELS_GRID[GRID_SIZE * 1 + 2], "KQs");
  assert.equal(ALL_HAND_LABELS_GRID[GRID_SIZE * 12 + 11], "32o");
});

test("bounds are rejected", () => {
  assert.throws(() => gridHandLabel(-1, 0), RangeError);
  assert.throws(() => gridHandLabel(0, 13), RangeError);
});
