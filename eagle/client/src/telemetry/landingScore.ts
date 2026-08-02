/**
 * Transparent 100-point demo score using the existing Hard-touchdown limits.
 * A zero-motion, level contact earns 100; reaching all three Hard limits
 * earns 0. The authoritative Nominal/Hard/Crash class still comes from Rust.
 */
export function landingScore(
  vVertMs: number,
  vHorizMs: number,
  tiltDeg: number,
): number {
  const vertical = 40 * Math.max(0, 1 - Math.abs(vVertMs) / 6);
  const horizontal = 35 * Math.max(0, 1 - Math.abs(vHorizMs) / 3);
  const attitude = 25 * Math.max(0, 1 - Math.abs(tiltDeg) / 20);
  return Math.round(vertical + horizontal + attitude);
}
