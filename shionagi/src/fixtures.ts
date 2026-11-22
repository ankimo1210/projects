import * as T from 'three';
import { Builder, canvasTexture, halo, nameplate, paint as p, plain, random, surface } from './materials';

export type Emitter = { x: number; y: number; z: number; color: string; energy: number; range: number };
export type SetKit = { b: Builder; root: T.Group; lights: Emitter[] };
const shadowTex = canvasTexture(64, 64, (c) => {
  const g = c.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(0,7,9,.8)');
  g.addColorStop(0.5, 'rgba(0,6,7,.64)');
  g.addColorStop(1, 'rgba(0,5,6,0)');
  c.fillStyle = g;
  c.fillRect(0, 0, 64, 64);
});
const shadow = new T.MeshBasicMaterial({
  map: shadowTex,
  transparent: true,
  depthWrite: false,
  polygonOffset: true,
  polygonOffsetFactor: -1,
});
const sheenTex = canvasTexture(128, 256, (c) => {
  const rnd = random(23);
  for (let i = 0; i < 1800; i++) {
    const x = rnd() * 128,
      y = rnd() * 256;
    const r = ((x - 64) / 56) ** 2 + ((y - 128) / 126) ** 2;
    if (r >= 1) continue;
    c.fillStyle = 'rgba(255,255,255,' + (1 - r) ** 2 * (0.05 + rnd() * 0.48) + ')';
    c.fillRect(x, y, 1 + rnd() * 12, 1 + rnd() * 1.3);
  }
});
const sheens = new Map<string, T.MeshBasicMaterial>();
export function decal(b: Builder, x: number, z: number, w: number, d: number, mat: T.Material, y = 0.033) {
  b.add(new T.PlaneGeometry(w, d), mat, x, y, z, new T.Euler(-Math.PI / 2, 0, 0));
}
export function contact(b: Builder, x: number, z: number, w: number, d: number) {
  decal(b, x, z, w, d, shadow, 0.029);
}
export function wetPatch(b: Builder, x: number, z: number, color: string, w: number, d: number) {
  let mat = sheens.get(color);
  if (!mat) {
    mat = new T.MeshBasicMaterial({
      map: sheenTex,
      color,
      transparent: true,
      opacity: 0.38,
      depthWrite: false,
      blending: T.AdditiveBlending,
      toneMapped: false,
    });
    sheens.set(color, mat);
  }
  decal(b, x, z, w, d, mat, 0.036);
}
export function emitter(
  k: SetKit,
  x: number,
  y: number,
  z: number,
  color: string,
  energy: number,
  range: number,
  size: number,
) {
  k.lights.push({ x, y, z, color, energy, range });
  halo(k.root, x, y, z, color, size);
}
export function tubeLamp(k: SetKit, x: number, y: number, z: number, width: number, warm = false) {
  k.b.box(x, y + 0.085, z, width + 0.26, 0.16, 0.38, p.dark);
  k.b.box(x, y - 0.028, z, width, 0.075, 0.17, warm ? p.warm : p.aqua);
  emitter(k, x, y - 0.14, z, warm ? '#ffc682' : '#b3e4d8', warm ? 48 : 42, 14, width * 1.45);
  wetPatch(k.b, x, z, warm ? '#ffc486' : '#9ee5d8', 1.5, 5);
}
export function beacon(k: SetKit, x: number, y: number, z: number) {
  k.b.box(x, y - 0.14, z, 0.32, 0.14, 0.27, p.rubber);
  k.b.add(new T.CylinderGeometry(0.1, 0.132, 0.22, 12), plain('#ff613c', true), x, y, z);
  k.b.tube([x - 0.115, y - 0.1, z], [x - 0.115, y + 0.11, z], 0.012, p.dark);
  k.b.tube([x + 0.115, y - 0.1, z], [x + 0.115, y + 0.11, z], 0.012, p.dark);
  emitter(k, x, y + 0.04, z, '#ff7149', 15, 8, 1.38);
}
export function bench(b: Builder, x: number, z: number, length: number) {
  const legs = p.dark,
    wood = surface('#7c7260', 'wood');
  for (const dx of [-length * 0.38, length * 0.38]) {
    b.box(x + dx, 0.22, z, 0.1, 0.46, 0.6, legs);
    b.box(x + dx, 0.047, z, 0.36, 0.085, 0.69, p.metal);
    b.tube([x + dx, 0.42, z - 0.25], [x + dx, 0.96, z - 0.45], 0.045, legs);
  }
  for (let i = 0; i < 4; i++) b.box(x, 0.47, z - 0.26 + i * 0.147, length, 0.095, 0.127, wood);
  b.box(x, 0.77, z - 0.365, length, 0.19, 0.071, wood);
  b.box(x, 0.965, z - 0.435, length, 0.139, 0.072, wood);
  for (const dx of [-length * 0.48, 0, length * 0.48]) {
    b.tube([x + dx, 0.49, z + 0.25], [x + dx, 0.66, z + 0.23], 0.024, p.metal);
    b.tube([x + dx, 0.66, z + 0.23], [x + dx, 0.67, z - 0.22], 0.024, p.metal);
  }
  contact(b, x, z, length + 0.7, 1.5);
}
export function vent(b: Builder, x: number, y: number, z: number, rot = 0) {
  const grill = nameplateVent();
  b.board(x, y, z, 1.35, 0.74, grill, rot);
}
let vents: T.Material;
function nameplateVent() {
  if (!vents) {
    const m = canvasTexture(256, 128, (c) => {
      c.fillStyle = '#52615c';
      c.fillRect(0, 0, 256, 128);
      c.fillStyle = '#293435';
      c.fillRect(6, 6, 244, 116);
      for (let v = 13; v < 120; v += 9) {
        c.fillStyle = '#76857d';
        c.fillRect(11, v, 234, 4);
        c.fillStyle = '#404d4c';
        c.fillRect(11, v + 4, 234, 2);
      }
      for (const x of [4, 249])
        for (const y of [4, 121]) {
          c.fillStyle = '#1e2e30';
          c.fillRect(x, y, 3, 3);
        }
    });
    vents = new T.MeshStandardMaterial({ map: m, roughness: 0.65, metalness: 0.32, side: T.DoubleSide });
  }
  return vents;
}
export function ring(b: Builder, x: number, y: number, z: number, r: number, ry: number) {
  const geo = new T.TorusGeometry(r, 0.062, 8, 40);
  b.add(geo, surface('#c16a42', 'metal'), x, y, z, new T.Euler(0, ry, 0));
  for (let i = 0; i < 4; i++) {
    const g = new T.TorusGeometry(r, 0.065, 8, 5, 0.33);
    g.rotateZ((i * Math.PI) / 2 + 0.4);
    b.add(g, p.cream, x, y, z, new T.Euler(0, ry, 0));
  }
}
export function van(b: Builder, x: number, z: number, w: number, d: number, scheme = '市営設備') {
  const body = surface('#778782', 'metal'),
    tint = plain('#1f383d'),
    dark = p.rubber;
  b.box(x, 0.71, z, w, 0.77, d, body);
  b.box(x, 1.36, z - 0.24, w * 0.96, 0.63, d * 0.8, body);
  b.box(x, 1.75, z - 0.18, w * 0.93, 0.14, d * 0.76, p.cream);
  b.box(x, 1.37, z + d * 0.31, w * 0.89, 0.51, 0.08, tint);
  for (const s of [-1, 1]) {
    for (const pos of [-0.25, 0.015, 0.23])
      b.box(x + s * w * 0.487, 1.36, z + pos * d, 0.045, 0.44, d * 0.19, tint);
    b.box(x + s * w * 0.502, 0.88, z, 0.033, 0.12, d * 0.89, p.blue);
    for (const v of [-1, 1]) {
      const wheel = new T.CylinderGeometry(0.34, 0.34, 0.17, 14);
      wheel.rotateZ(Math.PI / 2);
      b.add(wheel, dark, x + s * w * 0.47, 0.34, z + v * d * 0.32);
      const hub = new T.CylinderGeometry(0.17, 0.17, 0.18, 10);
      hub.rotateZ(Math.PI / 2);
      b.add(hub, p.metal, x + s * w * 0.48, 0.34, z + v * d * 0.32);
    }
    b.box(x + s * w * 0.34, 0.71, z + d * 0.503, w * 0.17, 0.14, 0.035, p.cream);
  }
  b.board(
    x,
    1.01,
    z + d * 0.506,
    w * 0.46,
    0.18,
    nameplate(scheme, 'SHIONAGI SERVICE', '#42554e', '#c5c8a7'),
  );
  contact(b, x, z, w * 1.42, d * 1.17);
}
export function container(b: Builder, x: number, z: number, w: number, d: number, h: number) {
  const shell = surface('#516b68', 'metal');
  b.box(x, h / 2, z, w, h, d, shell);
  for (const side of [-1, 1]) {
    for (let i = -d / 2 + 0.12; i < d / 2; i += 0.27)
      b.box(x + side * w * 0.5, h * 0.5, z + i, 0.065, h * 0.89, 0.1, p.dark);
    b.box(x + side * w * 0.32, h * 0.5, z + d * 0.505, 0.052, h * 0.92, 0.07, p.metal);
  }
  for (const y of [0.105, h - 0.105]) b.box(x, y, z, w + 0.12, 0.14, d + 0.12, p.metal);
  b.board(x, h * 0.65, z + d * 0.51, w * 0.62, 0.58, nameplate('汐凪港運', 'SHIONAGI CARGO', '#3a504e'));
  contact(b, x, z, w * 1.25, d * 1.1);
}
export function streetLamp(k: SetKit, x: number, z: number, dir: number, y = 5) {
  k.b.box(x, 0.22, z, 0.33, 0.44, 0.36, p.structure);
  k.b.tube([x, 0.35, z], [x, y, z], 0.065, p.metal);
  k.b.tube([x, y, z], [x + dir * 0.94, y + 0.38, z], 0.042, p.metal);
  k.b.box(x + dir * 1.03, y + 0.33, z, 0.55, 0.15, 0.34, p.dark);
  k.b.box(x + dir * 1.03, y + 0.24, z, 0.44, 0.055, 0.28, p.warm);
  emitter(k, x + dir * 1.03, y + 0.19, z, '#e7c18b', 43, 18, 2.05);
  wetPatch(k.b, x + dir * 1.03, z, '#d9bc83', 2.6, 9);
}
