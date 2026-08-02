import { describe, expect, it } from 'vitest';
import { destinationPoint, KSFO_28R, runwayPosition } from '../src/index.js';

/**
 * Runway-frame geometry (R-08). Scenario logic decides runway entry, exit and
 * incursion from these numbers, so the signs and the footprint test matter.
 */
describe('runwayPosition', () => {
  const rwy = KSFO_28R;

  it('is the origin at the threshold', () => {
    const p = runwayPosition(rwy, rwy.thresholdLatDeg, rwy.thresholdLonDeg);
    expect(p.alongM).toBeCloseTo(0, 1);
    expect(p.crossM).toBeCloseTo(0, 1);
    expect(p.onSurface).toBe(true);
  });

  it('measures distance along the centerline from the threshold', () => {
    const d = destinationPoint(rwy.thresholdLatDeg, rwy.thresholdLonDeg, rwy.headingDegTrue, 1500);
    const p = runwayPosition(rwy, d.latDeg, d.lonDeg);
    expect(p.alongM).toBeCloseTo(1500, 0);
    expect(Math.abs(p.crossM)).toBeLessThan(1);
    expect(p.onSurface).toBe(true);
  });

  it('is positive to the right of the landing direction', () => {
    const mid = destinationPoint(rwy.thresholdLatDeg, rwy.thresholdLonDeg, rwy.headingDegTrue, 900);
    const right = destinationPoint(mid.latDeg, mid.lonDeg, rwy.headingDegTrue + 90, 20);
    const left = destinationPoint(mid.latDeg, mid.lonDeg, rwy.headingDegTrue - 90, 20);
    expect(runwayPosition(rwy, right.latDeg, right.lonDeg).crossM).toBeCloseTo(20, 0);
    expect(runwayPosition(rwy, left.latDeg, left.lonDeg).crossM).toBeCloseTo(-20, 0);
  });

  it('leaves the surface beyond half the runway width', () => {
    const mid = destinationPoint(rwy.thresholdLatDeg, rwy.thresholdLonDeg, rwy.headingDegTrue, 900);
    const halfWidthM = (rwy.widthFt * 0.3048) / 2; // ≈30.5 m
    const inside = destinationPoint(
      mid.latDeg,
      mid.lonDeg,
      rwy.headingDegTrue + 90,
      halfWidthM - 5,
    );
    const outside = destinationPoint(
      mid.latDeg,
      mid.lonDeg,
      rwy.headingDegTrue + 90,
      halfWidthM + 5,
    );
    expect(runwayPosition(rwy, inside.latDeg, inside.lonDeg).onSurface).toBe(true);
    expect(runwayPosition(rwy, outside.latDeg, outside.lonDeg).onSurface).toBe(false);
  });

  it('leaves the surface past the far end and behind the threshold', () => {
    const lengthM = rwy.lengthFt * 0.3048;
    const past = destinationPoint(
      rwy.thresholdLatDeg,
      rwy.thresholdLonDeg,
      rwy.headingDegTrue,
      lengthM + 100,
    );
    const behind = destinationPoint(
      rwy.thresholdLatDeg,
      rwy.thresholdLonDeg,
      rwy.headingDegTrue + 180,
      100,
    );
    expect(runwayPosition(rwy, past.latDeg, past.lonDeg).onSurface).toBe(false);
    expect(runwayPosition(rwy, behind.latDeg, behind.lonDeg).onSurface).toBe(false);
  });
});
