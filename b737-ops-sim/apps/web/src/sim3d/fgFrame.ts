import { Matrix, Quaternion, Vector3 } from '@babylonjs/core/Maths/math.vector.js';
import { degToRad } from '@b737/shared';

/**
 * FlightGear model-frame conventions used by the cockpit assembly (R-11).
 *
 * Frame: +x aft, +y right, +z up (the frame the AC3D→glTF converter writes).
 *
 * Offset rotations: SimGear builds a model's `<offsets>` matrix as
 * `rotate * translate`, where the rotation is composed as roll about +x, then
 * pitch about +y, then heading about +z — all in the parent's frame. Babylon
 * shares that row-vector convention (a node's local matrix applies rotation
 * before translation), so the same order applies here.
 *
 * SOURCE_REQUIRED: derived from SimGear's documented model-offset behaviour,
 * not from a FlightGear build verified on this machine. The
 * `fgRotationInContentFrame` conjugation below is independent of that choice
 * and is exercised directly by unit tests.
 */

export const FG_X = new Vector3(1, 0, 0);
export const FG_Y = new Vector3(0, 1, 0);
export const FG_Z = new Vector3(0, 0, 1);

/** Rotation declared by a FlightGear `<offsets>` block, in the FG frame. */
export function fgOffsetRotation(
  pitchDeg: number,
  rollDeg: number,
  headingDeg: number,
): Quaternion {
  return Quaternion.RotationAxis(FG_X, degToRad(rollDeg))
    .multiply(Quaternion.RotationAxis(FG_Y, degToRad(pitchDeg)))
    .multiply(Quaternion.RotationAxis(FG_Z, degToRad(headingDeg)));
}

/**
 * Re-express an FG-frame rotation in the glTF loader's content frame.
 *
 * Content vectors are FG vectors mapped through L (`v_content = v_fg · L`), so
 * a rotation R acting in FG coordinates acts as `L⁻¹ · R · L` on content
 * coordinates. Conjugation keeps the determinant, so this stays a pure
 * rotation even when L mirrors an axis (the importer's handedness flip).
 */
export function fgRotationInContentFrame(rotation: Quaternion, contentLinear: Matrix): Quaternion {
  const r = Matrix.Identity();
  Matrix.FromQuaternionToRef(rotation, r);
  const m = contentLinear.clone().invert().multiply(r).multiply(contentLinear);
  const scale = new Vector3();
  const out = new Quaternion();
  m.decompose(scale, out, undefined);
  return out;
}
