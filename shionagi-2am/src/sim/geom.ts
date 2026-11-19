// Pure 2D/3D helpers shared by the simulation, the camera rig and the bot.
// Convention: x = east, z = south, y = up. yaw 0 faces north (-z); positive yaw
// turns left (towards -x), matching three.js `rotation.y`.

export const TAU = Math.PI * 2;

export const clamp = (v: number, a: number, b: number): number => (v < a ? a : v > b ? b : v);
export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export function smoothstep(a: number, b: number, x: number): number {
  const t = clamp((x - a) / (b - a), 0, 1);
  return t * t * (3 - 2 * t);
}

/** Wrap an angle to (-PI, PI]. */
export function wrapAngle(a: number): number {
  a %= TAU;
  if (a > Math.PI) a -= TAU;
  else if (a <= -Math.PI) a += TAU;
  return a;
}

/** Yaw that faces along (dx, dz). */
export const yawTo = (dx: number, dz: number): number => Math.atan2(-dx, -dz);
export const fwdX = (yaw: number): number => -Math.sin(yaw);
export const fwdZ = (yaw: number): number => -Math.cos(yaw);
export const rightX = (yaw: number): number => Math.cos(yaw);
export const rightZ = (yaw: number): number => -Math.sin(yaw);

export function approach(cur: number, target: number, maxStep: number): number {
  const d = target - cur;
  if (Math.abs(d) <= maxStep) return target;
  return cur + Math.sign(d) * maxStep;
}

export function approachAngle(cur: number, target: number, maxStep: number): number {
  const d = wrapAngle(target - cur);
  if (Math.abs(d) <= maxStep) return wrapAngle(target);
  return wrapAngle(cur + Math.sign(d) * maxStep);
}

export interface Rect {
  x0: number;
  z0: number;
  x1: number;
  z1: number;
}

export interface Box extends Rect {
  y0: number;
  y1: number;
  /** blocks walking */
  solid: boolean;
  /** blocks enemy sight */
  opaque: boolean;
  /** rails / fences / pits: bullets and the camera pass through */
  thin: boolean;
  /** ceilings: only the camera and bullets care */
  ceil: boolean;
  /** dynamic boxes (doors, the raised bridge) switch this off */
  on: boolean;
  id?: string;
}

export const inRect = (r: Rect, x: number, z: number): boolean =>
  x >= r.x0 && x <= r.x1 && z >= r.z0 && z <= r.z1;

/**
 * Segment vs rectangle (Liang–Barsky). Returns the entry parameter t in [0, 1]
 * or -1 when the segment misses. A segment that starts inside returns 0.
 */
export function segRect(ax: number, az: number, bx: number, bz: number, r: Rect): number {
  let t0 = 0;
  let t1 = 1;
  const dx = bx - ax;
  const dz = bz - az;
  // x slabs
  if (Math.abs(dx) < 1e-9) {
    if (ax < r.x0 || ax > r.x1) return -1;
  } else {
    let ta = (r.x0 - ax) / dx;
    let tb = (r.x1 - ax) / dx;
    if (ta > tb) [ta, tb] = [tb, ta];
    if (ta > t0) t0 = ta;
    if (tb < t1) t1 = tb;
    if (t0 > t1) return -1;
  }
  if (Math.abs(dz) < 1e-9) {
    if (az < r.z0 || az > r.z1) return -1;
  } else {
    let ta = (r.z0 - az) / dz;
    let tb = (r.z1 - az) / dz;
    if (ta > tb) [ta, tb] = [tb, ta];
    if (ta > t0) t0 = ta;
    if (tb < t1) t1 = tb;
    if (t0 > t1) return -1;
  }
  return t0;
}

/**
 * Ray vs axis-aligned box in 3D, the box grown by `pad` on every side.
 * Returns the entry distance (0 when the origin is inside) or Infinity.
 * (dx, dy, dz) must be normalised for the result to be a distance.
 */
export function rayBox(
  ox: number,
  oy: number,
  oz: number,
  dx: number,
  dy: number,
  dz: number,
  b: Box,
  pad: number,
): number {
  let t0 = 0;
  let t1 = Infinity;
  const mins = [b.x0 - pad, b.y0 - pad, b.z0 - pad];
  const maxs = [b.x1 + pad, b.y1 + pad, b.z1 + pad];
  const o = [ox, oy, oz];
  const d = [dx, dy, dz];
  for (let i = 0; i < 3; i++) {
    const oi = o[i] as number;
    const di = d[i] as number;
    const mn = mins[i] as number;
    const mx = maxs[i] as number;
    if (Math.abs(di) < 1e-9) {
      if (oi < mn || oi > mx) return Infinity;
    } else {
      let ta = (mn - oi) / di;
      let tb = (mx - oi) / di;
      if (ta > tb) [ta, tb] = [tb, ta];
      if (ta > t0) t0 = ta;
      if (tb < t1) t1 = tb;
      if (t0 > t1) return Infinity;
    }
  }
  return t0;
}

/** Ray vs sphere. Returns entry distance or Infinity. Direction must be normalised. */
export function raySphere(
  ox: number,
  oy: number,
  oz: number,
  dx: number,
  dy: number,
  dz: number,
  cx: number,
  cy: number,
  cz: number,
  r: number,
): number {
  const mx = ox - cx;
  const my = oy - cy;
  const mz = oz - cz;
  const b = mx * dx + my * dy + mz * dz;
  const c = mx * mx + my * my + mz * mz - r * r;
  if (c > 0 && b > 0) return Infinity;
  const disc = b * b - c;
  if (disc < 0) return Infinity;
  const t = -b - Math.sqrt(disc);
  return t < 0 ? 0 : t;
}

/**
 * Ray vs upright cylinder (axis through (cx, cz), y in [y0, y1], caps ignored).
 * Returns entry distance or Infinity. Direction must be normalised.
 */
export function rayCylinder(
  ox: number,
  oy: number,
  oz: number,
  dx: number,
  dy: number,
  dz: number,
  cx: number,
  cz: number,
  r: number,
  y0: number,
  y1: number,
): number {
  const mx = ox - cx;
  const mz = oz - cz;
  const a = dx * dx + dz * dz;
  if (a < 1e-9) return Infinity;
  const b = mx * dx + mz * dz;
  const c = mx * mx + mz * mz - r * r;
  const disc = b * b - a * c;
  if (disc < 0) return Infinity;
  const sq = Math.sqrt(disc);
  let t = (-b - sq) / a;
  if (t < 0) {
    // origin inside the infinite cylinder: accept if within the height band
    if (c > 0) return Infinity;
    t = 0;
  }
  const y = oy + dy * t;
  if (y < y0 || y > y1) {
    // try the exit point so steep shots through the top/bottom still register
    const t2 = (-b + sq) / a;
    const yExit = oy + dy * t2;
    if ((y < y0 && yExit < y0) || (y > y1 && yExit > y1)) return Infinity;
    // crosses the band somewhere inside: find where
    if (Math.abs(dy) < 1e-9) return Infinity;
    const tBand = y < y0 ? (y0 - oy) / dy : (y1 - oy) / dy;
    return tBand >= t && tBand <= t2 ? tBand : Infinity;
  }
  return t;
}

/**
 * Push a circle out of a rectangle. Mutates and returns `out` when the circle
 * overlapped, otherwise returns null.
 */
export function pushOut(
  px: number,
  pz: number,
  r: number,
  b: Rect,
  out: { x: number; z: number },
): { x: number; z: number } | null {
  const cx = clamp(px, b.x0, b.x1);
  const cz = clamp(pz, b.z0, b.z1);
  let dx = px - cx;
  let dz = pz - cz;
  const d2 = dx * dx + dz * dz;
  if (d2 >= r * r) return null;
  if (d2 > 1e-10) {
    const d = Math.sqrt(d2);
    const k = (r - d) / d;
    out.x = px + dx * k;
    out.z = pz + dz * k;
    return out;
  }
  // centre is inside the rectangle: leave through the nearest face
  const l = px - b.x0;
  const rr = b.x1 - px;
  const t = pz - b.z0;
  const bt = b.z1 - pz;
  const m = Math.min(l, rr, t, bt);
  dx = 0;
  dz = 0;
  if (m === l) dx = -(l + r);
  else if (m === rr) dx = rr + r;
  else if (m === t) dz = -(t + r);
  else dz = bt + r;
  out.x = px + dx;
  out.z = pz + dz;
  return out;
}

/** Small deterministic PRNG (mulberry32). The state is a plain number so it can be snapshotted. */
export function rngNext(state: { seed: number }): number {
  let t = (state.seed += 0x6d2b79f5);
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}
