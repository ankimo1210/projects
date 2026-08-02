import { describe, expect, it } from 'vitest';
import {
  AircraftCommandSchema,
  AircraftStateSchema,
  flapDetentToNorm,
  flapNormToNearestDetent,
  parseClientMessage,
  vSpeedsForWeight,
} from '../src/index.js';
import { makeTestAircraftState } from './stateFixture.js';

describe('AircraftStateSchema', () => {
  it('accepts a complete valid state', () => {
    expect(AircraftStateSchema.safeParse(makeTestAircraftState()).success).toBe(true);
  });

  it('rejects an invalid flap detent', () => {
    const bad = makeTestAircraftState();
    bad.controls.flapHandleDetent = 7 as never;
    expect(AircraftStateSchema.safeParse(bad).success).toBe(false);
  });
});

describe('AircraftCommandSchema', () => {
  it('accepts valid commands', () => {
    expect(
      AircraftCommandSchema.safeParse({ type: 'set_flaps', detent: 5 }).success,
    ).toBe(true);
    expect(
      AircraftCommandSchema.safeParse({
        type: 'set_control_axis',
        axis: 'pitch',
        valueNorm: -0.5,
      }).success,
    ).toBe(true);
  });

  it('rejects out-of-range axis values', () => {
    expect(
      AircraftCommandSchema.safeParse({
        type: 'set_control_axis',
        axis: 'roll',
        valueNorm: 1.5,
      }).success,
    ).toBe(false);
  });

  it('rejects unknown command types', () => {
    expect(AircraftCommandSchema.safeParse({ type: 'explode' }).success).toBe(false);
  });
});

describe('protocol parsing', () => {
  it('returns parseError for junk', () => {
    expect(parseClientMessage('not json')).toHaveProperty('parseError');
    expect(parseClientMessage('{"t":"nope"}')).toHaveProperty('parseError');
  });

  it('parses a valid ping', () => {
    const msg = parseClientMessage(JSON.stringify({ t: 'ping', seq: 1, sentAtMs: 123 }));
    expect(msg).toMatchObject({ t: 'ping', seq: 1 });
  });
});

describe('flap detent helpers', () => {
  it('round-trips detents through norm', () => {
    for (const d of [0, 1, 2, 5, 10, 15, 25, 30, 40] as const) {
      expect(flapNormToNearestDetent(flapDetentToNorm(d))).toBe(d);
    }
  });
});

describe('vSpeedsForWeight', () => {
  it('interpolates monotonically with weight', () => {
    const light = vSpeedsForWeight(120000);
    const heavy = vSpeedsForWeight(160000);
    expect(heavy.v1Kt).toBeGreaterThan(light.v1Kt);
    expect(heavy.vrKt).toBeGreaterThan(light.vrKt);
    expect(light.vrKt).toBeGreaterThanOrEqual(light.v1Kt);
    expect(light.v2Kt).toBeGreaterThan(light.vrKt);
  });

  it('clamps outside the table', () => {
    expect(vSpeedsForWeight(50000)).toEqual(vSpeedsForWeight(110000));
  });
});
