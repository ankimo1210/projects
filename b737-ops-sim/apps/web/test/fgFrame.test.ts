import { describe, expect, it } from 'vitest';
import { Matrix, Quaternion, Vector3 } from '@babylonjs/core';
import {
  fgOffsetRotation,
  fgRotationInContentFrame,
  FG_X,
  FG_Y,
  FG_Z,
} from '../src/sim3d/fgFrame.js';

/**
 * Cockpit assembly rotations (R-11). The loader used to warn and drop these,
 * which silently mis-placed the flightdesk (−15°) and the overhead (90/90).
 */

function rotate(v: Vector3, q: Quaternion): Vector3 {
  const m = Matrix.Identity();
  Matrix.FromQuaternionToRef(q, m);
  return Vector3.TransformNormal(v, m);
}

function expectVectorClose(actual: Vector3, expected: Vector3): void {
  expect(actual.x).toBeCloseTo(expected.x, 6);
  expect(actual.y).toBeCloseTo(expected.y, 6);
  expect(actual.z).toBeCloseTo(expected.z, 6);
}

describe('fgOffsetRotation', () => {
  it('is the identity with no offsets', () => {
    expectVectorClose(rotate(FG_X, fgOffsetRotation(0, 0, 0)), FG_X);
    expectVectorClose(rotate(FG_Z, fgOffsetRotation(0, 0, 0)), FG_Z);
  });

  it('rotates about the FG axes, one per Euler term', () => {
    // heading turns the aft axis toward the lateral axis, leaving up alone
    expectVectorClose(rotate(FG_Z, fgOffsetRotation(0, 0, 90)), FG_Z);
    expect(rotate(FG_X, fgOffsetRotation(0, 0, 90)).z).toBeCloseTo(0, 6);
    // pitch acts about the lateral axis, leaving it alone
    expectVectorClose(rotate(FG_Y, fgOffsetRotation(90, 0, 0)), FG_Y);
    // roll acts about the longitudinal axis, leaving it alone
    expectVectorClose(rotate(FG_X, fgOffsetRotation(0, 90, 0)), FG_X);
  });

  it('applies roll, then pitch, then heading (SimGear order)', () => {
    const composed = fgOffsetRotation(90, 90, 0);
    const stepwise = Quaternion.RotationAxis(FG_X, Math.PI / 2).multiply(
      Quaternion.RotationAxis(FG_Y, Math.PI / 2),
    );
    expectVectorClose(rotate(FG_Z, composed), rotate(FG_Z, stepwise));
    expectVectorClose(rotate(FG_X, composed), rotate(FG_X, stepwise));
  });

  it('tilts the flightdesk face by the declared 15 degrees', () => {
    // The flightdesk is mounted at pitch −15°; its normal must tilt by exactly
    // that much, and stay in the vertical plane containing the aircraft axis.
    const tilted = rotate(FG_Z, fgOffsetRotation(-15, 0, 0));
    expect(Vector3.Dot(tilted, FG_Z)).toBeCloseTo(Math.cos(Math.PI / 12), 6);
    expect(tilted.y).toBeCloseTo(0, 6);
  });
});

describe('fgRotationInContentFrame', () => {
  /** The importer transform observed on the real assets: 180° about Y + z-flip. */
  const importerLinear = (): Matrix => {
    const m = Matrix.Identity();
    Matrix.FromQuaternionToRef(new Quaternion(0, 1, 0, 0), m);
    return Matrix.Scaling(1, 1, -1).multiply(m);
  };

  it('is a no-op when the content frame is the FG frame', () => {
    const q = fgOffsetRotation(-15, 0, 0);
    const conjugated = fgRotationInContentFrame(q, Matrix.Identity());
    expectVectorClose(rotate(FG_Z, conjugated), rotate(FG_Z, q));
  });

  it('commutes with the content mapping for any vector', () => {
    const L = importerLinear();
    for (const rDeg of [
      [-15, 0, 0],
      [90, 90, 0],
      [12, -7, 33],
    ] as const) {
      const q = fgOffsetRotation(rDeg[0], rDeg[1], rDeg[2]);
      const conjugated = fgRotationInContentFrame(q, L);
      for (const v of [FG_X, FG_Y, FG_Z, new Vector3(0.43, 0, 0.91)]) {
        // rotate in FG then map == map then rotate in the content frame
        expectVectorClose(
          Vector3.TransformNormal(rotate(v, q), L),
          rotate(Vector3.TransformNormal(v, L), conjugated),
        );
      }
    }
  });

  it('stays a pure rotation through a mirroring content map', () => {
    const conjugated = fgRotationInContentFrame(fgOffsetRotation(90, 90, 0), importerLinear());
    expect(conjugated.length()).toBeCloseTo(1, 6);
    const m = Matrix.Identity();
    Matrix.FromQuaternionToRef(conjugated, m);
    expect(m.determinant()).toBeCloseTo(1, 6);
  });
});
