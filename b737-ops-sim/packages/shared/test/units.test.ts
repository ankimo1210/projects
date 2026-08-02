import { describe, expect, it } from 'vitest';
import {
  KT_TO_MPS,
  MPS_TO_FPM,
  angleDiffDeg,
  clamp,
  createSeededRandom,
  normalizeDeg180,
  normalizeDeg360,
} from '../src/units.js';

describe('units', () => {
  it('converts knots to m/s', () => {
    expect(100 * KT_TO_MPS).toBeCloseTo(51.4444, 3);
  });

  it('converts m/s to fpm', () => {
    expect(5 * MPS_TO_FPM).toBeCloseTo(984.25, 1);
  });

  it('normalizes angles to [0,360)', () => {
    expect(normalizeDeg360(-10)).toBe(350);
    expect(normalizeDeg360(370)).toBe(10);
    expect(normalizeDeg360(360)).toBe(0);
  });

  it('normalizes angles to (-180,180]', () => {
    expect(normalizeDeg180(190)).toBe(-170);
    expect(normalizeDeg180(180)).toBe(180);
  });

  it('computes shortest signed angle difference', () => {
    expect(angleDiffDeg(350, 10)).toBe(20);
    expect(angleDiffDeg(10, 350)).toBe(-20);
    expect(angleDiffDeg(90, 270)).toBe(180);
  });

  it('clamps', () => {
    expect(clamp(5, 0, 1)).toBe(1);
    expect(clamp(-5, 0, 1)).toBe(0);
  });

  it('seeded random is deterministic and in [0,1)', () => {
    const a = createSeededRandom(42);
    const b = createSeededRandom(42);
    const seqA = [a(), a(), a()];
    const seqB = [b(), b(), b()];
    expect(seqA).toEqual(seqB);
    for (const v of seqA) {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThan(1);
    }
    const c = createSeededRandom(43);
    expect(c()).not.toBe(seqA[0]);
  });
});
