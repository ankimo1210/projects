import { describe, expect, it } from 'vitest';
import {
  bearingDeg,
  destinationPoint,
  distanceM,
  fromLocalEnuM,
  toLocalEnuM,
} from '../src/geo.js';

describe('geo', () => {
  it('computes zero distance to self', () => {
    expect(distanceM(37.6, -122.35, 37.6, -122.35)).toBe(0);
  });

  it('one degree of latitude is ~111 km', () => {
    expect(distanceM(37, -122, 38, -122)).toBeCloseTo(111195, -3);
  });

  it('bearing due north / east', () => {
    expect(bearingDeg(37, -122, 38, -122)).toBeCloseTo(0, 1);
    expect(bearingDeg(0, 0, 0, 1)).toBeCloseTo(90, 1);
  });

  it('destinationPoint round-trips with distance/bearing', () => {
    const start = { latDeg: 37.6132, lonDeg: -122.3572 };
    const dest = destinationPoint(start.latDeg, start.lonDeg, 297.9, 3000);
    expect(distanceM(start.latDeg, start.lonDeg, dest.latDeg, dest.lonDeg)).toBeCloseTo(3000, 0);
    expect(bearingDeg(start.latDeg, start.lonDeg, dest.latDeg, dest.lonDeg)).toBeCloseTo(297.9, 1);
  });

  it('local ENU projection round-trips near the origin', () => {
    const origin = { latDeg: 37.6132, lonDeg: -122.3572 };
    const { eastM, northM } = toLocalEnuM(origin.latDeg, origin.lonDeg, 37.62, -122.34);
    const back = fromLocalEnuM(origin.latDeg, origin.lonDeg, eastM, northM);
    expect(back.latDeg).toBeCloseTo(37.62, 6);
    expect(back.lonDeg).toBeCloseTo(-122.34, 6);
  });

  it('ENU east axis matches bearing 90°', () => {
    const { eastM, northM } = toLocalEnuM(37.6, -122.35, 37.6, -122.34);
    expect(northM).toBeCloseTo(0, 3);
    expect(eastM).toBeGreaterThan(0);
  });
});
