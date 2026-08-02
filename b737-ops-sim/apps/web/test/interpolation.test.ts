import { describe, expect, it } from 'vitest';
import { makeTestAircraftState } from '@b737/shared/testing';
import { StateInterpolator, interpolateStates } from '../src/net/interpolation.js';

function sample(timestampMs: number, iasKt: number, headingDegMag = 0) {
  const s = makeTestAircraftState();
  s.timestampMs = timestampMs;
  s.speeds.iasKt = iasKt;
  s.attitude.headingDegMag = headingDegMag;
  return s;
}

describe('interpolateStates', () => {
  it('lerps continuous fields', () => {
    const mid = interpolateStates(sample(0, 100), sample(1000, 200), 0.5);
    expect(mid.speeds.iasKt).toBe(150);
  });

  it('interpolates heading across the 360° wrap', () => {
    const mid = interpolateStates(sample(0, 0, 350), sample(1000, 0, 10), 0.5);
    expect(mid.attitude.headingDegMag).toBeCloseTo(0, 5);
  });

  it('snaps discrete fields to the newer sample', () => {
    const a = sample(0, 100);
    const b = sample(1000, 100);
    b.weightOnWheels = false;
    b.controls.flapHandleDetent = 10;
    const mid = interpolateStates(a, b, 0.2);
    expect(mid.weightOnWheels).toBe(false);
    expect(mid.controls.flapHandleDetent).toBe(10);
  });
});

describe('StateInterpolator', () => {
  it('renders behind the newest sample and interpolates between pairs', () => {
    const interp = new StateInterpolator(100);
    interp.push(sample(1000, 100));
    interp.push(sample(1100, 110));
    interp.push(sample(1200, 120));
    // render time = 1250 - 100 = 1150 → halfway between 1100 and 1200
    const view = interp.sample(1250);
    expect(view!.speeds.iasKt).toBeCloseTo(115, 5);
  });

  it('holds the latest sample when starved', () => {
    const interp = new StateInterpolator(100);
    interp.push(sample(1000, 100));
    interp.push(sample(1100, 110));
    const view = interp.sample(5000);
    expect(view!.speeds.iasKt).toBe(110);
  });

  it('reports staleness', () => {
    const interp = new StateInterpolator(100);
    expect(interp.staleness(1000)).toBeNull();
    interp.push(sample(1000, 100));
    expect(interp.staleness(3500)).toBe(2500);
  });
});
