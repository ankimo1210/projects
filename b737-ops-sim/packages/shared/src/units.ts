/**
 * Unit conversion boundary (spec §5: no silent unit mixing).
 * Every quantity in schemas carries its unit in the property name
 * (Deg, Ft, Kt, Fpm, Pct, Norm, M, Mps, Sec, Ms).
 */

export const KT_TO_MPS = 0.514444;
export const MPS_TO_KT = 1 / KT_TO_MPS;
export const FT_TO_M = 0.3048;
export const M_TO_FT = 1 / FT_TO_M;
export const FPM_TO_MPS = FT_TO_M / 60;
export const MPS_TO_FPM = 60 * M_TO_FT;
export const NM_TO_M = 1852;
export const M_TO_NM = 1 / NM_TO_M;
export const LB_TO_KG = 0.45359237;
export const G_MPS2 = 9.80665;

export function degToRad(deg: number): number {
  return (deg * Math.PI) / 180;
}

export function radToDeg(rad: number): number {
  return (rad * 180) / Math.PI;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/** Normalize an angle to [0, 360). */
export function normalizeDeg360(deg: number): number {
  const d = deg % 360;
  return d < 0 ? d + 360 : d;
}

/** Normalize an angle to (-180, 180]. */
export function normalizeDeg180(deg: number): number {
  const d = normalizeDeg360(deg);
  return d > 180 ? d - 360 : d;
}

/** Signed shortest angular difference `target - current` in (-180, 180]. */
export function angleDiffDeg(currentDeg: number, targetDeg: number): number {
  return normalizeDeg180(targetDeg - currentDeg);
}

/**
 * Deterministic PRNG (mulberry32). Used everywhere randomness is needed so
 * that a fixed seed yields a reproducible session (spec §5 mock mode).
 */
export function createSeededRandom(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
