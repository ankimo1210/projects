// Over-the-shoulder camera rig. Pure maths on the level colliders so the
// simulation (shooting needs the camera ray) and the view (which re-runs it per
// rendered frame) agree.

import { clamp, lerp, rayBox, rightX, rightZ } from "./geom";
import type { Box } from "./geom";
import type { CamState } from "./types";

export const HEAD_Y = 1.6;
const PAD = 0.16;

export const CAM = {
  distance: 2.55,
  aimDistance: 1.2,
  side: 0.55,
  aimSide: 0.42,
  fov: 62,
  aimFov: 47,
  minDist: 0.12,
};

export function camDir(yaw: number, pitch: number): [number, number, number] {
  const cp = Math.cos(pitch);
  return [-Math.sin(yaw) * cp, Math.sin(pitch), -Math.cos(yaw) * cp];
}

function cast(
  boxes: readonly Box[],
  ox: number,
  oy: number,
  oz: number,
  dx: number,
  dy: number,
  dz: number,
  max: number,
): number {
  let best = max;
  for (const b of boxes) {
    if (!b.on || b.thin || !(b.solid || b.ceil)) continue;
    const t = rayBox(ox, oy, oz, dx, dy, dz, b, PAD);
    if (t < best) best = t;
  }
  return best;
}

/**
 * Advance the rig. The camera sits behind the right shoulder; when a wall is in
 * the way the boom shortens at once (and eases back out), so near walls the
 * camera closes in on the shoulder instead of clipping through.
 */
export function updateCamera(
  cam: CamState,
  px: number,
  pz: number,
  yaw: number,
  pitch: number,
  aim: number,
  boxes: readonly Box[],
  dt: number,
  snap = false,
): void {
  const rx = rightX(yaw);
  const rz = rightZ(yaw);
  const sideWant = lerp(CAM.side, CAM.aimSide, aim);
  // Room over each shoulder. `cam.side` is signed: positive is the right
  // shoulder, negative the left. With a wall close on the right the camera
  // crosses to the left shoulder, so the head never ends up in front of the lens.
  const roomR = clamp(cast(boxes, px, HEAD_Y, pz, rx, 0, rz, sideWant + 0.04) - 0.04, 0, sideWant);
  const roomL = clamp(cast(boxes, px, HEAD_Y, pz, -rx, 0, -rz, sideWant + 0.04) - 0.04, 0, sideWant);
  let left = cam.side < -1e-3;
  if (!left) {
    if (roomR < sideWant * 0.55 && roomL > roomR + 0.15) left = true;
  } else if (roomR >= sideWant - 0.03 || roomL <= roomR) {
    left = false;
  }
  const sideTarget = left ? -roomL : roomR;
  if (snap) {
    cam.side = sideTarget;
  } else {
    const sd = clamp(cam.side, -roomL, roomR); // never inside a wall
    cam.side = sd + clamp(sideTarget - sd, -3.2 * dt, 3.2 * dt);
  }

  const pvx = px + rx * cam.side;
  const pvy = HEAD_Y + lerp(0.06, 0.02, aim);
  const pvz = pz + rz * cam.side;
  const [fx, fy, fz] = camDir(yaw, pitch);
  const bx = -fx;
  const by = -fy;
  const bz = -fz;
  const want = lerp(CAM.distance, CAM.aimDistance, aim);
  let d = cast(boxes, pvx, pvy, pvz, bx, by, bz, want + 0.1) - 0.1;
  if (by < -1e-4) d = Math.min(d, (pvy - 0.35) / -by);
  d = clamp(d, CAM.minDist, want);
  cam.dist = snap || d < cam.dist ? d : cam.dist + Math.min(d - cam.dist, 3.2 * dt);

  // squeezed up against the player, the camera rises to look over the helmet
  const lift = Math.max(0, 1.25 - cam.dist) * 0.3;
  cam.x = pvx + bx * cam.dist;
  cam.y = pvy + by * cam.dist + lift;
  cam.z = pvz + bz * cam.dist;
}
