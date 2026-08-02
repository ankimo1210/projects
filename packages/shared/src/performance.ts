/**
 * Takeoff / landing reference speeds by gross weight.
 *
 * NON_CERTIFIED_APPROXIMATION — SOURCE_REQUIRED
 * These are round-number approximations with plausible magnitudes for a
 * 737-800-class aircraft (flaps 5 takeoff, flaps 30 landing, sea level,
 * light wind). They exist so callouts and scoring have consistent reference
 * values. Replace with data derived from legally obtained references placed
 * under `private/manuals/` (see README) — never commit such data.
 */

import { clamp, lerp } from './units.js';

interface VSpeedRow {
  grossWeightLb: number;
  v1Kt: number;
  vrKt: number;
  v2Kt: number;
  /** Landing reference speed, flaps 30. */
  vref30Kt: number;
}

const V_SPEED_TABLE: VSpeedRow[] = [
  { grossWeightLb: 110000, v1Kt: 122, vrKt: 125, v2Kt: 133, vref30Kt: 125 },
  { grossWeightLb: 120000, v1Kt: 128, vrKt: 131, v2Kt: 138, vref30Kt: 130 },
  { grossWeightLb: 130000, v1Kt: 134, vrKt: 137, v2Kt: 143, vref30Kt: 136 },
  { grossWeightLb: 140000, v1Kt: 140, vrKt: 143, v2Kt: 148, vref30Kt: 141 },
  { grossWeightLb: 150000, v1Kt: 146, vrKt: 149, v2Kt: 153, vref30Kt: 147 },
  { grossWeightLb: 160000, v1Kt: 152, vrKt: 155, v2Kt: 158, vref30Kt: 152 },
  { grossWeightLb: 174000, v1Kt: 159, vrKt: 162, v2Kt: 165, vref30Kt: 158 },
];

export interface VSpeeds {
  v1Kt: number;
  vrKt: number;
  v2Kt: number;
  vref30Kt: number;
  /** Final approach speed = Vref + additive (5 kt used here). */
  vappKt: number;
}

/** Linear interpolation over the table, clamped to its ends. */
export function vSpeedsForWeight(grossWeightLb: number): VSpeeds {
  const table = V_SPEED_TABLE;
  const first = table[0]!;
  const last = table[table.length - 1]!;
  const w = clamp(grossWeightLb, first.grossWeightLb, last.grossWeightLb);
  let lo = first;
  let hi = last;
  for (let i = 0; i < table.length - 1; i++) {
    if (w >= table[i]!.grossWeightLb && w <= table[i + 1]!.grossWeightLb) {
      lo = table[i]!;
      hi = table[i + 1]!;
      break;
    }
  }
  const t =
    hi.grossWeightLb === lo.grossWeightLb
      ? 0
      : (w - lo.grossWeightLb) / (hi.grossWeightLb - lo.grossWeightLb);
  const vref30Kt = Math.round(lerp(lo.vref30Kt, hi.vref30Kt, t));
  return {
    v1Kt: Math.round(lerp(lo.v1Kt, hi.v1Kt, t)),
    vrKt: Math.round(lerp(lo.vrKt, hi.vrKt, t)),
    v2Kt: Math.round(lerp(lo.v2Kt, hi.v2Kt, t)),
    vref30Kt,
    vappKt: vref30Kt + 5,
  };
}

/** Flap placard limit speeds (kt IAS). NON_CERTIFIED_APPROXIMATION. */
export const FLAP_LIMIT_SPEEDS_KT: Record<number, number> = {
  0: 340,
  1: 250,
  2: 250,
  5: 250,
  10: 210,
  15: 200,
  25: 190,
  30: 175,
  40: 162,
};

/** Landing gear extended/operating limit (kt IAS). NON_CERTIFIED_APPROXIMATION. */
export const GEAR_LIMIT_SPEED_KT = 270;
