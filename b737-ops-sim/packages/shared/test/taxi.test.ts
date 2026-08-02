import { describe, expect, it } from 'vitest';
import {
  HOLD_SHORT_OFFSET_M,
  KSFO_28R,
  KSFO_TAXI,
  distanceToHoldShortM,
  distanceToStandM,
  getTaxiNetwork,
  isPastHoldShort,
  runwayPointToLatLon,
  runwayPosition,
  taxiPosition,
} from '../src/index.js';

/** Ground layout for taxi operations (M3 T1). */

const at = (alongM: number, crossM: number): { latDeg: number; lonDeg: number } =>
  runwayPointToLatLon(KSFO_28R, alongM, crossM);

describe('runwayPointToLatLon', () => {
  it('round-trips through runwayPosition', () => {
    for (const [along, cross] of [
      [0, 0],
      [1500, 25],
      [-200, -80],
      [3000, 210],
    ] as const) {
      const p = at(along, cross);
      const back = runwayPosition(KSFO_28R, p.latDeg, p.lonDeg);
      expect(back.alongM).toBeCloseTo(along, 0);
      expect(back.crossM).toBeCloseTo(cross, 0);
    }
  });
});

describe('holding position', () => {
  it('is short of the runway while outside the protected area', () => {
    const holdingPoint = runwayPosition(KSFO_28R, ...pt(at(40, 90)));
    expect(distanceToHoldShortM(holdingPoint)).toBeCloseTo(90 - HOLD_SHORT_OFFSET_M, 0);
    expect(isPastHoldShort(KSFO_28R, holdingPoint)).toBe(false);
  });

  it('is crossed before the aircraft reaches the pavement', () => {
    const between = runwayPosition(KSFO_28R, ...pt(at(40, 40))); // inside 45 m, outside the runway
    expect(isPastHoldShort(KSFO_28R, between)).toBe(true);
    expect(between.onSurface).toBe(false);
  });

  it('does not apply abeam nothing (well past the far end)', () => {
    const lengthM = KSFO_28R.lengthFt * 0.3048;
    const beyond = runwayPosition(KSFO_28R, ...pt(at(lengthM + 500, 10)));
    expect(isPastHoldShort(KSFO_28R, beyond)).toBe(false);
  });
});

describe('taxiPosition', () => {
  it('finds the parallel taxiway under the holding point', () => {
    const p = taxiPosition(KSFO_TAXI, ...pt(at(400, 90)));
    expect(p.label).toBe('A');
    expect(p.onSurface).toBe(true);
    expect(p.offsetM).toBeLessThan(2);
  });

  it('reports off-surface between the taxiway and the runway', () => {
    const p = taxiPosition(KSFO_TAXI, ...pt(at(700, 60)));
    expect(p.onSurface).toBe(false);
    expect(p.offsetM).toBeGreaterThan(11.5);
  });

  it('picks the runway entry connector when lined up on it', () => {
    const p = taxiPosition(KSFO_TAXI, ...pt(at(40, 60)));
    expect(p.segmentId).toBe('C1');
    expect(p.onSurface).toBe(true);
  });

  it('picks the high-speed exit after landing', () => {
    const p = taxiPosition(KSFO_TAXI, ...pt(at(1900, 45)));
    expect(p.segmentId).toBe('E1');
    expect(p.onSurface).toBe(true);
  });

  it('measures distance to the stand', () => {
    const near = distanceToStandM(KSFO_TAXI, 'S1', ...pt(at(350, 205)));
    expect(near).not.toBeNull();
    expect(near!).toBeLessThan(6);
    const far = distanceToStandM(KSFO_TAXI, 'S1', ...pt(at(2900, 90)));
    expect(far!).toBeGreaterThan(2000);
  });
});

describe('getTaxiNetwork', () => {
  it('resolves the KSFO 28R layout and nothing else', () => {
    expect(getTaxiNetwork('KSFO', '28R')).toBe(KSFO_TAXI);
    expect(getTaxiNetwork('KLAX', '25L')).toBeUndefined();
  });
});

/** Spread helper: {latDeg, lonDeg} → positional args. */
function pt(p: { latDeg: number; lonDeg: number }): [number, number] {
  return [p.latDeg, p.lonDeg];
}
