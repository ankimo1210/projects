// The standard 13x13 preflop hand grid (AA top-left), row-major.
// Row i / col j over RANKS_DESC "AKQJT98765432": diagonal = pair,
// upper triangle (col > row) = suited, lower triangle = offsuit.
// Chart packs store per-hand rows in exactly this order — keep in sync with
// grid_hand_labels() in scripts/build_preflop_fixture.py.

export const RANKS_DESC = "AKQJT98765432";
export const GRID_SIZE = 13;
export const NUM_HAND_LABELS = 169;

/** Hand label for grid cell (row, col), e.g. "AA", "AKs", "AKo". */
export function gridHandLabel(row: number, col: number): string {
  if (!Number.isInteger(row) || row < 0 || row >= GRID_SIZE) {
    throw new RangeError(`row out of range: ${row}`);
  }
  if (!Number.isInteger(col) || col < 0 || col >= GRID_SIZE) {
    throw new RangeError(`col out of range: ${col}`);
  }
  const hi = RANKS_DESC[Math.min(row, col)]!;
  const lo = RANKS_DESC[Math.max(row, col)]!;
  if (row === col) return hi + lo;
  return hi + lo + (col > row ? "s" : "o");
}

/** All 169 labels in row-major grid order (= chart-pack row order). */
export const ALL_HAND_LABELS_GRID: readonly string[] = (() => {
  const labels: string[] = [];
  for (let row = 0; row < GRID_SIZE; row++) {
    for (let col = 0; col < GRID_SIZE; col++) {
      labels.push(gridHandLabel(row, col));
    }
  }
  return labels;
})();

/** Number of card combos a hand label covers: pair 6, suited 4, offsuit 12. */
export function comboCount(label: string): number {
  if (label.length === 2) return 6;
  return label[2] === "s" ? 4 : 12;
}
