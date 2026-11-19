// Turns the level's prop descriptors into meshes. Static things are batched;
// the few things that move (doors, the bridge deck, pickups, rattling shutters)
// come back as handles for the view to animate.

import * as THREE from "three";
import type { Facing, Level, LightDef, Prop } from "../sim/types";
import { Batch, mul, trs } from "./batch";
import type { Mats } from "./materials";
import {
  archTexture,
  clockTexture,
  crestTexture,
  itemTexture,
  prng,
  shopSignTexture,
  signTexture,
} from "./textures";

export interface DoorHandle {
  group: THREE.Group;
  base: number;
  swing: number;
  open: number;
}

export interface FixtureHandle {
  light: number;
  lens: THREE.Mesh | null;
}

export interface TownHandles {
  group: THREE.Group;
  doors: Record<string, DoorHandle>;
  items: Record<string, THREE.Object3D>;
  bridge: { pivot: THREE.Group; tip: THREE.Vector3 } | null;
  fixtures: FixtureHandle[];
  rattlers: { mesh: THREE.Mesh; x: number; y: number; z: number; nx: number }[];
  glass: THREE.Mesh[];
  waters: { x0: number; z0: number; x1: number; z1: number; y: number; kind: "flood" | "canal" | "sea" }[];
  lever: THREE.Object3D | null;
}

/** texture repeats per metre for the world-UV batcher */
const UVS: Record<string, [number, number]> = {
  asphalt: [1 / 6, 1 / 6],
  paving: [1 / 4, 1 / 4],
  tile: [1 / 2.4, 1 / 2.4],
  lino: [1 / 2, 1 / 2],
  concreteFloor: [1 / 3, 1 / 3],
  grate: [1, 1],
  shutter: [1, 0.8],
  warehouse: [0.4, 0.25],
  container: [0.9, 0.5],
  station: [1 / 6, 1 / 3.2],
};
for (let i = 0; i < 8; i++) UVS[`facade${i}`] = [1 / 6, 1 / 3.2];

const FACE_ROT: Record<Facing, number> = { s: 0, e: Math.PI / 2, n: Math.PI, w: -Math.PI / 2 };
const FACE_N: Record<Facing, [number, number]> = { s: [0, 1], e: [1, 0], n: [0, -1], w: [-1, 0] };
const HEADING_ROT = [0, -Math.PI / 2, Math.PI, Math.PI / 2];

const SHOP_TONES = [0x7a6f60, 0x626a70, 0x80705f, 0x5f665c, 0x74696a, 0x5e5e66, 0x77775f, 0x685d54];
const SIDE_SIGN = [0x8a2a1e, 0x1f4a6e, 0xd9c9a0, 0x2f5b3a, 0x3a3a3f, 0xb9422a, 0x274a4e, 0x8a5a22];

class Ctx {
  batch = new Batch();
  dyn = new THREE.Group();
  h: TownHandles;
  constructor(
    readonly mats: Mats,
    readonly lights: LightDef[],
  ) {
    this.h = {
      group: new THREE.Group(),
      doors: {},
      items: {},
      bridge: null,
      fixtures: [],
      rattlers: [],
      glass: [],
      waters: [],
      lever: null,
    };
  }

  box(mat: string, x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, color = 0xffffff, skip = ""): void {
    const uv = UVS[mat] ?? [1 / 3, 1 / 3];
    this.batch.box(mat, Math.min(x0, x1), y0, Math.min(z0, z1), Math.max(x0, x1), y1, Math.max(z0, z1), {
      su: uv[0],
      sv: uv[1],
      color,
      skip,
    });
  }

  /** Thin bar between two points. */
  beam(mat: string, a: THREE.Vector3, b: THREE.Vector3, thick: number, color = 0xffffff): void {
    const len = a.distanceTo(b);
    const m = new THREE.Matrix4();
    const mid = a.clone().add(b).multiplyScalar(0.5);
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), b.clone().sub(a).normalize());
    m.compose(mid, q, new THREE.Vector3(1, 1, 1));
    this.batch.obox(mat, thick, thick, len, m, color);
  }
}

function plane(w: number, h: number, mat: THREE.Material, x: number, y: number, z: number, ry: number): THREE.Mesh {
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
  mesh.position.set(x, y, z);
  mesh.rotation.y = ry;
  return mesh;
}

// -------------------------------------------------------------------- props

function buildShop(c: Ctx, p: Extract<Prop, { k: "shop" }>): void {
  const nx = p.face === "e" ? 1 : -1;
  const x = p.x;
  const xa = Math.min(x, p.back);
  const xb = Math.max(x, p.back);
  const tone = p.tone % 8;
  c.box(`facade${tone}`, xa, 0, p.z0, xb, p.h, p.z1, 0xffffff, "yY");
  c.box("roof", xa, p.h, p.z0, xb, p.h + 0.3, p.z1);
  // ground floor cladding
  const clad = SHOP_TONES[tone] as number;
  c.box("concrete", x, 0, p.z0, x + nx * 0.07, 2.85, p.z1, clad);
  const zs0 = p.z0 + 0.45;
  const zs1 = p.z1 - 0.45;
  const f0 = x + nx * 0.07;
  const f1 = x + nx * 0.14;
  if (p.shutter === "glass") {
    c.box("concreteDark", f0, 0, zs0, f1, 0.5, zs1);
    c.box("glassDark", f0, 0.5, zs0, x + nx * 0.1, 2.45, zs1);
    for (let z = zs0; z <= zs1 + 0.01; z += (zs1 - zs0) / 4) c.box("metalDark", f0, 0, z - 0.04, f1, 2.45, z + 0.04);
  } else {
    const y0 = p.shutter === "gap" ? 0.36 : p.shutter === "half" ? 1.3 : 0;
    if (y0 > 0) c.box("void", f0 - nx * 0.02, 0, zs0, f0 + nx * 0.01, y0, zs1);
    if (p.rattle) {
      const g = new THREE.BoxGeometry(0.07, 2.45 - y0, zs1 - zs0);
      // world-ish UVs so the slats match the batched shutters
      const uv = g.getAttribute("uv");
      for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * (zs1 - zs0), uv.getY(i) * (2.45 - y0) * 0.8);
      const mesh = new THREE.Mesh(g, c.mats["shutter"]);
      mesh.position.set((f0 + f1) / 2, (2.45 + y0) / 2, (zs0 + zs1) / 2);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      c.dyn.add(mesh);
      c.h.rattlers.push({ mesh, x: mesh.position.x, y: mesh.position.y, z: mesh.position.z, nx });
    } else {
      c.box("shutter", f0, y0, zs0, f1, 2.45, zs1);
    }
  }
  c.box("metalDark", f0, 2.45, zs0 - 0.12, x + nx * 0.24, 2.78, zs1 + 0.12);
  // fascia sign
  const sw = p.z1 - p.z0 - 0.7;
  c.box("metalDark", f0, 2.82, p.z0 + 0.3, x + nx * 0.2, 3.82, p.z1 - 0.3);
  const signMat = new THREE.MeshStandardMaterial({
    map: shopSignTexture(p.name, p.sub, p.tone),
    roughness: 0.55,
    metalness: 0.1,
  });
  const sign = plane(sw, 0.94, signMat, x + nx * 0.215, 3.32, (p.z0 + p.z1) / 2, nx > 0 ? Math.PI / 2 : -Math.PI / 2);
  sign.receiveShadow = true;
  c.dyn.add(sign);
  if (p.tone % 3 === 0) c.box("tarp", f0, 2.6, p.z0 + 0.35, x + nx * 1.15, 2.68, p.z1 - 0.35, 0x39597a);
  if (p.tone % 2 === 1) {
    const zc = p.z0 + 0.9;
    c.box("metalPaint", x + nx * 0.1, 4.0, zc - 0.07, x + nx * 0.95, 6.2, zc + 0.07, SIDE_SIGN[p.tone % 8] as number);
  }
}

function buildCar(c: Ctx, p: Extract<Prop, { k: "car" }>): void {
  const cx = (p.x0 + p.x1) / 2;
  const cz = (p.z0 + p.z1) / 2;
  const alongZ = p.heading === 0 || p.heading === 2;
  const L = alongZ ? p.z1 - p.z0 : p.x1 - p.x0;
  const Wd = alongZ ? p.x1 - p.x0 : p.z1 - p.z0;
  const M = trs(cx, 0, cz, HEADING_ROT[p.heading] as number);
  const b = c.batch;
  const part = (mat: string, sx: number, sy: number, sz: number, x: number, y: number, z: number, col = 0xffffff): void =>
    b.obox(mat, sx, sy, sz, mul(M, trs(x, y, z)), col);
  const wheelGeo = new THREE.CylinderGeometry(1, 1, 1, 12);
  const wheels = (r: number, zf: number, zr: number): void => {
    for (const sx of [-1, 1]) {
      for (const z of [zf, zr]) {
        const m = mul(M, trs(sx * (Wd / 2 - 0.1), r, z, 0, 0, Math.PI / 2));
        m.scale(new THREE.Vector3(r, 0.22, r));
        b.add("tire", wheelGeo, m);
      }
    }
  };
  const col = p.color;
  switch (p.model) {
    case "sedan":
    case "taxi":
    case "patrol": {
      const top = p.model === "sedan" ? 1.42 : 1.5;
      if (p.model === "patrol") {
        part("paint", Wd, 0.3, L, 0, 0.43, 0, 0x0e1012);
        part("paint", Wd, 0.27, L, 0, 0.715, 0, col);
      } else {
        part("paint", Wd, 0.57, L, 0, 0.565, 0, col);
      }
      part("carGlass", Wd - 0.18, top - 0.9, L * 0.5, 0, (top + 0.8) / 2, L * 0.05);
      part("paint", Wd - 0.14, 0.07, L * 0.48, 0, top - 0.02, L * 0.05, col);
      part("metalDark", Wd + 0.02, 0.16, 0.14, 0, 0.36, -L / 2 + 0.05);
      part("metalDark", Wd + 0.02, 0.16, 0.14, 0, 0.36, L / 2 - 0.05);
      part("metalPaint", 0.26, 0.1, 0.04, -Wd / 2 + 0.25, 0.68, -L / 2 - 0.005, 0xb9bcc0);
      part("metalPaint", 0.26, 0.1, 0.04, Wd / 2 - 0.25, 0.68, -L / 2 - 0.005, 0xb9bcc0);
      part("metalPaint", 0.24, 0.1, 0.04, -Wd / 2 + 0.25, 0.7, L / 2 + 0.005, 0x4a0d0a);
      part("metalPaint", 0.24, 0.1, 0.04, Wd / 2 - 0.25, 0.7, L / 2 + 0.005, 0x4a0d0a);
      if (p.model === "patrol") part("metalPaint", 1.05, 0.13, 0.28, 0, top + 0.08, L * 0.02, 0x6a1410);
      if (p.model === "taxi") part("metalPaint", 0.42, 0.15, 0.17, 0, top + 0.09, 0, 0xd8c890);
      wheels(0.31, -L * 0.31, L * 0.31);
      break;
    }
    case "kei": {
      part("paint", Wd, 1.4, 1.05, 0, 1.15, -L / 2 + 0.53, col);
      part("carGlass", Wd - 0.1, 0.5, 0.05, 0, 1.45, -L / 2 - 0.005);
      part("paint", Wd, 0.12, L - 1.1, 0, 0.74, 0.55, col);
      part("paint", 0.05, 0.3, L - 1.1, -Wd / 2 + 0.025, 0.95, 0.55, col);
      part("paint", 0.05, 0.3, L - 1.1, Wd / 2 - 0.025, 0.95, 0.55, col);
      part("paint", Wd, 0.3, 0.05, 0, 0.95, L / 2 - 0.025, col);
      part("metalDark", Wd - 0.3, 0.3, L - 0.4, 0, 0.5, 0.1);
      wheels(0.27, -L * 0.3, L * 0.32);
      break;
    }
    case "boxtruck": {
      part("paint", Wd - 0.2, 1.9, 1.7, 0, 1.45, -L / 2 + 0.85, 0xe2e4e0);
      part("carGlass", Wd - 0.3, 0.7, 0.05, 0, 1.9, -L / 2 - 0.005);
      part("paint", Wd, 2.2, L - 1.85, 0, 1.9, 0.92, col);
      part("metalDark", Wd - 0.5, 0.35, L - 0.3, 0, 0.62, 0.05);
      wheels(0.42, -L * 0.32, L * 0.3);
      break;
    }
    case "van": {
      part("paint", Wd, 1.9, L, 0, 1.4, 0, col);
      part("carGlass", Wd + 0.02, 0.5, L * 0.72, 0, 1.75, L * 0.06);
      part("carGlass", Wd - 0.2, 0.62, 0.05, 0, 1.72, -L / 2 - 0.005);
      part("metalPaint", Wd + 0.02, 0.2, L * 0.9, 0, 1.15, 0, 0xd9dcdf);
      part("metalPaint", 0.9, 0.12, 0.26, 0, 2.42, -L * 0.2, 0x6a1410);
      wheels(0.34, -L * 0.32, L * 0.32);
      break;
    }
    case "utility": {
      part("paint", Wd - 0.1, 1.6, 1.7, 0, 1.3, -L / 2 + 0.85, col);
      part("carGlass", Wd - 0.2, 0.6, 0.05, 0, 1.7, -L / 2 - 0.005);
      part("paint", Wd, 0.7, L - 1.85, 0, 0.95, 0.92, col);
      part("metalDark", Wd - 0.5, 0.35, L - 0.3, 0, 0.6, 0.05);
      b.obox("metalPaint", 0.26, 0.26, 2.6, mul(M, trs(0.3, 1.95, 0.9, 0, 0.38, 0)), 0x9a7a18);
      part("metalPaint", 0.5, 0.9, 0.5, 0.3, 1.6, 0.1, 0x9a7a18);
      wheels(0.4, -L * 0.32, L * 0.3);
      break;
    }
  }
  wheelGeo.dispose();
}

function buildGlassWall(c: Ctx, p: Extract<Prop, { k: "glassWall" }>): void {
  const z0 = p.z - 0.15;
  const z1 = p.z + 0.15;
  c.box("termWall", p.x0, 0, z0, p.doorX0, 0.45, z1);
  c.box("termWall", p.doorX1, 0, z0, p.x1, 0.45, z1);
  c.box("termWall", p.x0, 3.4, z0, p.x1, p.h, z1);
  const n = Math.round((p.x1 - p.x0) / 2.125);
  for (let i = 0; i <= n; i++) {
    const x = p.x0 + ((p.x1 - p.x0) * i) / n;
    if (x > p.doorX0 + 0.05 && x < p.doorX1 - 0.05) continue;
    c.box("metalDark", x - 0.045, 0.45, p.z - 0.06, x + 0.045, 3.4, p.z + 0.06);
  }
  for (const x of [p.doorX0, (p.doorX0 + p.doorX1) / 2, p.doorX1]) {
    c.box("metalDark", x - 0.05, 0, p.z - 0.07, x + 0.05, 2.5, p.z + 0.07);
  }
  c.box("metalDark", p.doorX0, 2.45, p.z - 0.07, p.doorX1, 2.56, p.z + 0.07);
  c.box("metalDark", p.doorX0, 0, p.z - 0.07, p.doorX1, 0.06, p.z + 0.07);
  const frost = c.mats["frost"] as THREE.Material;
  const pane = (xa: number, xb: number, ya: number, yb: number): void => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(xb - xa, yb - ya), frost);
    m.position.set((xa + xb) / 2, (ya + yb) / 2, p.z);
    m.renderOrder = 2;
    c.dyn.add(m);
    c.h.glass.push(m);
  };
  pane(p.x0, p.doorX0, 0.45, 3.4);
  pane(p.doorX1, p.x1, 0.45, 3.4);
  pane(p.doorX0, p.doorX1, 0.06, 3.4);
}

function buildDoor(c: Ctx, p: Extract<Prop, { k: "door" }>): void {
  const group = new THREE.Group();
  group.position.set(p.hx, 0, p.hz);
  const base = Math.atan2(-p.az, p.ax);
  group.rotation.y = base;
  const paint =
    p.style === "staff"
      ? new THREE.MeshStandardMaterial({ color: 0x8fa69b, roughness: 0.55, metalness: 0.2 })
      : p.style === "steel"
        ? new THREE.MeshStandardMaterial({ color: 0x6f757b, roughness: 0.45, metalness: 0.6 })
        : new THREE.MeshStandardMaterial({ color: 0x10161c, roughness: 0.12, metalness: 0.85 });
  const leaf = new THREE.Mesh(new THREE.BoxGeometry(p.len, p.h, 0.05), paint);
  leaf.position.set(p.len / 2, p.h / 2, 0);
  leaf.castShadow = true;
  leaf.receiveShadow = true;
  group.add(leaf);
  const dark = c.mats["metalDark"] as THREE.Material;
  if (p.style === "glass") {
    for (const [w, h, x, y] of [
      [p.len, 0.1, p.len / 2, 0.05],
      [p.len, 0.1, p.len / 2, p.h - 0.05],
      [0.1, p.h, 0.05, p.h / 2],
      [0.1, p.h, p.len - 0.05, p.h / 2],
    ] as [number, number, number, number][]) {
      const f = new THREE.Mesh(new THREE.BoxGeometry(w, h, 0.07), dark);
      f.position.set(x, y, 0);
      group.add(f);
    }
    const bar = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.9, 0.12), c.mats["pipe"]);
    bar.position.set(p.len - 0.22, 1.1, 0);
    group.add(bar);
  } else {
    if (p.style === "staff") {
      const win = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.5, 0.06), c.mats["glassDark"]);
      win.position.set(p.len / 2, 1.55, 0);
      group.add(win);
    }
    const knob = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.05, 0.16), c.mats["pipe"]);
    knob.position.set(p.len - 0.12, 1.02, 0);
    group.add(knob);
  }
  c.dyn.add(group);
  c.h.doors[p.id] = { group, base, swing: p.swing, open: 0 };
}

function buildSign(c: Ctx, p: Extract<Prop, { k: "sign" }>): void {
  const tex = signTexture(p);
  const mat = p.lit
    ? new THREE.MeshBasicMaterial({ map: tex, toneMapped: false, color: new THREE.Color(0.8, 0.8, 0.8) })
    : new THREE.MeshStandardMaterial({ map: tex, roughness: 0.6, metalness: 0.05 });
  const [nx, nz] = FACE_N[p.face];
  const mesh = plane(p.w, p.h, mat, p.x + nx * 0.035, p.y, p.z + nz * 0.035, FACE_ROT[p.face]);
  mesh.receiveShadow = !p.lit;
  c.dyn.add(mesh);
  // backing box
  const along = nx === 0;
  const hw = p.w / 2 + 0.03;
  const hh = p.h / 2 + 0.03;
  if (along) c.box("metalDark", p.x - hw, p.y - hh, p.z - nz * 0.05, p.x + hw, p.y + hh, p.z + nz * 0.03);
  else c.box("metalDark", p.x - nx * 0.05, p.y - hh, p.z - hw, p.x + nx * 0.03, p.y + hh, p.z + hw);
}

function buildLamp(c: Ctx, p: Extract<Prop, { k: "lamp" }>): void {
  const def = c.lights[p.light];
  if (!def) return;
  const lensMat = new THREE.MeshBasicMaterial({ color: def.color, toneMapped: false });
  let lens: THREE.Mesh | null = null;
  const { x, y, z } = def;
  switch (p.fixture) {
    case "ceiling":
      lens = new THREE.Mesh(new THREE.BoxGeometry(0.34, 0.04, 0.34), lensMat);
      lens.position.set(x, y + 0.045, z);
      c.box("metalDark", x - 0.2, y + 0.06, z - 0.2, x + 0.2, y + 0.09, z + 0.2);
      break;
    case "wall": {
      const [nx, nz] = FACE_N[p.face ?? "s"];
      lens = new THREE.Mesh(new THREE.BoxGeometry(nx === 0 ? 0.28 : 0.08, 0.13, nx === 0 ? 0.08 : 0.28), lensMat);
      lens.position.set(x, y, z);
      c.box("metalDark", x - 0.17 - Math.abs(nx) * -0.1, y + 0.07, z - 0.17 + Math.abs(nz) * 0.1, x + 0.17 - Math.abs(nx) * 0.1, y + 0.13, z + 0.17 - Math.abs(nz) * 0.1);
      break;
    }
    case "flasher":
      lens = new THREE.Mesh(new THREE.SphereGeometry(0.095, 12, 8), lensMat);
      lens.position.set(x, y, z);
      c.box("metalPaint", x - 0.08, y - 0.26, z - 0.06, x + 0.08, y - 0.08, z + 0.06, 0xc9a012);
      break;
    case "beacon":
      lens = new THREE.Mesh(new THREE.CylinderGeometry(0.085, 0.1, 0.15, 12), lensMat);
      lens.position.set(x, y, z);
      break;
    case "bare":
      lens = new THREE.Mesh(new THREE.SphereGeometry(0.045, 8, 6), lensMat);
      lens.position.set(x, y, z);
      c.box("metalDark", x - 0.12, 0.02, z - 0.035, x, 0.09, z + 0.035);
      break;
    default:
      break;
  }
  if (lens) c.dyn.add(lens);
  c.h.fixtures.push({ light: p.light, lens });
}

function buildRail(c: Ctx, p: Extract<Prop, { k: "rail" }>): void {
  const alongX = p.x1 - p.x0 > p.z1 - p.z0;
  const len = alongX ? p.x1 - p.x0 : p.z1 - p.z0;
  const mx = (p.x0 + p.x1) / 2;
  const mz = (p.z0 + p.z1) / 2;
  const at = (t: number): [number, number] => (alongX ? [p.x0 + t, mz] : [mx, p.z0 + t]);
  const bar = (mat: string, y0: number, y1: number, half: number, col = 0xffffff): void => {
    if (alongX) c.box(mat, p.x0, y0, mz - half, p.x1, y1, mz + half, col);
    else c.box(mat, mx - half, y0, p.z0, mx + half, y1, p.z1, col);
  };
  if (p.style === "hedge") {
    c.box("hedge", p.x0, 0, p.z0, p.x1, p.h, p.z1);
    return;
  }
  if (p.style === "barricade") {
    const n = Math.max(1, Math.round(len / 1.6));
    for (let i = 0; i <= n; i++) {
      const [x, z] = at((len * i) / n);
      c.box("metalDark", x - 0.03, 0, z - 0.2, x + 0.03, p.h, z + 0.2);
    }
    bar("metalPaint", p.h - 0.34, p.h - 0.1, 0.02, 0xd0a814);
    bar("metalPaint", p.h - 0.72, p.h - 0.56, 0.02, 0x1c1c1e);
    return;
  }
  const n = Math.max(1, Math.round(len / (p.style === "chain" ? 2.2 : 1.6)));
  for (let i = 0; i <= n; i++) {
    const [x, z] = at((len * i) / n);
    c.box("metalDark", x - 0.03, 0, z - 0.03, x + 0.03, p.h + 0.02, z + 0.03);
  }
  bar("metalDark", p.h - 0.05, p.h, 0.03);
  if (p.style === "rail") {
    bar("metalDark", p.h * 0.5 - 0.02, p.h * 0.5 + 0.02, 0.02);
    bar("metalDark", 0.1, 0.14, 0.02);
  } else {
    bar("metalDark", 0.04, 0.08, 0.02);
    const mat = c.mats["chain"] as THREE.Material;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(len, p.h - 0.1), mat);
    const uv = mesh.geometry.getAttribute("uv");
    for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * len * 2.5, uv.getY(i) * p.h * 2.5);
    mesh.position.set(mx, p.h / 2, mz);
    mesh.rotation.y = alongX ? 0 : Math.PI / 2;
    c.dyn.add(mesh);
  }
}

function buildPole(c: Ctx, p: Extract<Prop, { k: "pole" }>): void {
  const b = c.batch;
  const cyl = new THREE.CylinderGeometry(1, 1, 1, 10);
  const post = (r: number, h: number, col = 0x8a9096): void => {
    const m = trs(p.x, h / 2, p.z);
    m.scale(new THREE.Vector3(r, h, r));
    b.add("metalPaint", cyl, m, col);
  };
  switch (p.kind) {
    case "lamp":
      post(0.075, p.h, 0x4a5258);
      b.obox("metalDark", 0.14, 0.1, 0.9, trs(p.x, p.h - 0.1, p.z + 0.35));
      b.obox("metalDark", 0.3, 0.1, 0.5, trs(p.x, p.h - 0.2, p.z + 0.62));
      break;
    case "clock": {
      post(0.09, p.h, 0x2f4a58);
      b.obox("metalPaint", 0.95, 0.95, 0.26, trs(p.x, p.h - 0.45, p.z), 0x2f4a58);
      const mat = new THREE.MeshStandardMaterial({ map: clockTexture(), roughness: 0.4, transparent: true });
      for (const s of [1, -1]) {
        const face = plane(0.82, 0.82, mat, p.x, p.h - 0.45, p.z + s * 0.135, s > 0 ? 0 : Math.PI);
        c.dyn.add(face);
      }
      break;
    }
    case "flag": {
      post(0.05, p.h, 0xb9bcc0);
      const mat = new THREE.MeshStandardMaterial({ color: 0x1b2a4a, roughness: 0.9, side: THREE.DoubleSide });
      const flag = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 1.5, 2, 6), mat);
      const pos = flag.geometry.getAttribute("position");
      for (let i = 0; i < pos.count; i++) pos.setZ(i, Math.sin(pos.getY(i) * 4 + p.x) * 0.06 * (pos.getX(i) + 0.25));
      flag.geometry.computeVertexNormals();
      flag.position.set(p.x + 0.3, p.h - 1.0, p.z);
      flag.userData["flag"] = true;
      c.dyn.add(flag);
      break;
    }
    case "speaker": {
      post(0.1, p.h, 0x8c9296);
      const horn = new THREE.CylinderGeometry(0.1, 0.34, 0.5, 12, 1, true);
      for (let i = 0; i < 4; i++) {
        const a = (i / 4) * Math.PI * 2 + 0.4;
        const m = trs(p.x + Math.sin(a) * 0.38, p.h - 0.35, p.z + Math.cos(a) * 0.38, a, Math.PI / 2);
        b.add("metalPaint", horn, m, 0xa4a8aa);
      }
      horn.dispose();
      b.obox("metalDark", 0.4, 0.5, 0.3, trs(p.x, 2.2, p.z + 0.2));
      break;
    }
    default:
      post(0.055, p.h, 0x7b8388);
  }
  cyl.dispose();
}

function buildBridge(c: Ctx, p: Extract<Prop, { k: "bridge" }>): void {
  const w = p.x1 - p.x0;
  const len = p.z1 - p.z0;
  const xc = (p.x0 + p.x1) / 2;
  const pivot = new THREE.Group();
  pivot.position.set(xc, -0.05, p.z1);
  const grate = c.mats["grate"] as THREE.Material;
  const dark = c.mats["metalDark"] as THREE.Material;
  const deckGeo = new THREE.BoxGeometry(w, 0.18, len);
  const uv = deckGeo.getAttribute("uv");
  const nor = deckGeo.getAttribute("normal");
  for (let i = 0; i < uv.count; i++) {
    if (Math.abs(nor.getY(i)) > 0.5) uv.setXY(i, uv.getX(i) * w, uv.getY(i) * len);
  }
  const deck = new THREE.Mesh(deckGeo, grate);
  deck.position.set(0, 0, -len / 2);
  deck.castShadow = true;
  deck.receiveShadow = true;
  pivot.add(deck);
  for (const sx of [-1, 1]) {
    const girder = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.5, len), dark);
    girder.position.set(sx * (w / 2 - 0.08), -0.3, -len / 2);
    pivot.add(girder);
    const top = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.06, len), dark);
    top.position.set(sx * (w / 2 + 0.06), 1.18, -len / 2);
    pivot.add(top);
    const mid = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.04, len), dark);
    mid.position.set(sx * (w / 2 + 0.06), 0.66, -len / 2);
    pivot.add(mid);
    for (let z = 0; z <= len + 0.01; z += len / 9) {
      const post = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.1, 0.06), dark);
      post.position.set(sx * (w / 2 + 0.06), 0.62, -z);
      pivot.add(post);
    }
  }
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.055, 10, 8), new THREE.MeshBasicMaterial({ color: 0xd81f12 }));
  lamp.position.set(w / 2 + 0.06, 1.34, -len + 0.3);
  lamp.name = "tipLamp";
  pivot.add(lamp);
  c.dyn.add(pivot);
  c.h.bridge = { pivot, tip: new THREE.Vector3(w / 2 + 0.06, 1.34, -len + 0.3) };
  // hinge frame and the cables that run back to the winch house
  const col = 0x7d8388;
  for (const x of [p.x0 - 0.3, p.x1 + 0.3]) c.box("metalPaint", x - 0.14, 0, p.z1 + 0.25, x + 0.14, 4.4, p.z1 + 0.53, col);
  c.box("metalPaint", p.x0 - 0.44, 4.1, p.z1 + 0.25, p.x1 + 0.44, 4.4, p.z1 + 0.53, col);
  c.beam("metalDark", new THREE.Vector3(20, 4.7, -121.4), new THREE.Vector3(p.x0 - 0.2, 4.3, p.z1 + 0.4), 0.05);
  c.beam("metalDark", new THREE.Vector3(20, 4.7, -120.6), new THREE.Vector3(p.x1 + 0.2, 4.3, p.z1 + 0.4), 0.05);
  c.box("concrete", p.x0 - 0.6, -3.2, p.z0 - 0.7, p.x1 + 0.6, 0.02, p.z0);
}

function buildItem(c: Ctx, p: Extract<Prop, { k: "item" }>): void {
  const g = new THREE.Group();
  g.position.set(p.x, p.y, p.z);
  if (p.kind === "gun") {
    const steel = new THREE.MeshStandardMaterial({ color: 0x23262b, roughness: 0.35, metalness: 0.85 });
    const wood = new THREE.MeshStandardMaterial({ color: 0x4a2f1c, roughness: 0.6 });
    g.add(makeRevolver(steel, wood));
    g.rotation.set(0, 0.7, Math.PI / 2);
  } else {
    const [sx, sy, sz] = p.kind === "medkit" ? [0.32, 0.13, 0.22] : [0.12, 0.05, 0.08];
    const mat = new THREE.MeshStandardMaterial({ map: itemTexture(p.kind), roughness: 0.6 });
    const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), mat);
    m.position.y = sy / 2;
    m.castShadow = true;
    g.add(m);
    g.rotation.y = 0.4;
  }
  c.dyn.add(g);
  c.h.items[p.id] = g;
}

export function makeRevolver(steel: THREE.Material, wood: THREE.Material): THREE.Group {
  const g = new THREE.Group();
  const add = (mat: THREE.Material, sx: number, sy: number, sz: number, x: number, y: number, z: number, rx = 0): void => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(sx, sy, sz), mat);
    m.position.set(x, y, z);
    m.rotation.x = rx;
    g.add(m);
  };
  add(steel, 0.026, 0.03, 0.1, 0, 0.035, -0.09); // barrel
  add(steel, 0.036, 0.05, 0.075, 0, 0.022, -0.005); // frame
  add(steel, 0.046, 0.046, 0.05, 0, 0.022, -0.02); // cylinder
  add(wood, 0.03, 0.095, 0.042, 0, -0.04, 0.035, -0.35); // grip
  add(steel, 0.008, 0.02, 0.012, 0, 0.056, -0.132); // front sight
  return g;
}

function buildMisc(c: Ctx, p: Prop): void {
  const b = c.batch;
  switch (p.k) {
    case "bench": {
      const col = 0x2f6470;
      c.box("metalPaint", p.x0, 0.36, p.z0, p.x1, 0.44, p.z1, col);
      const zb = p.back === "s" ? p.z1 : p.z0;
      const dz = p.back === "s" ? -0.07 : 0.07;
      c.box("metalPaint", p.x0, 0.44, zb, p.x1, 0.9, zb + dz, col);
      for (const x of [p.x0 + 0.25, (p.x0 + p.x1) / 2, p.x1 - 0.25]) {
        c.box("metalDark", x - 0.03, 0, p.z0 + 0.06, x + 0.03, 0.36, p.z1 - 0.06);
      }
      break;
    }
    case "ceiling": {
      c.box("termCeil", p.x0, p.y, p.z0, p.x1, p.y + 0.3, p.z1);
      // dead fluorescent fittings
      for (let x = p.x0 + 2; x < p.x1 - 1; x += 4) {
        for (let z = p.z0 + 2.2; z < p.z1 - 1; z += 3.6) c.box("metalPaint", x - 0.6, p.y - 0.06, z - 0.09, x + 0.6, p.y, z + 0.09, 0x9a9c98);
      }
      break;
    }
    case "panel": {
      const col = 0x6f807a;
      c.box("metalPaint", p.x - 0.4, 0, p.z - 0.28, p.x + 0.4, 1.22, p.z + 0.28, col);
      b.obox("metalPaint", 0.84, 0.1, 0.62, trs(p.x, 1.3, p.z + 0.02, 0, -0.35), 0x55625e);
      b.obox("metalDark", 0.5, 0.02, 0.3, trs(p.x, 1.37, p.z + 0.04, 0, -0.35));
      b.obox("metalPaint", 0.84, 0.5, 0.05, trs(p.x, 1.62, p.z - 0.26), col);
      const lever = new THREE.Group();
      lever.position.set(p.x + 0.18, 1.36, p.z + 0.08);
      const stick = new THREE.Mesh(new THREE.BoxGeometry(0.035, 0.2, 0.035), new THREE.MeshStandardMaterial({ color: 0xa41c12, roughness: 0.5 }));
      stick.position.y = 0.1;
      lever.add(stick);
      lever.rotation.x = -0.75;
      c.dyn.add(lever);
      c.h.lever = lever;
      break;
    }
    case "sluice": {
      const { x, z } = p;
      for (const sx of [-1, 1]) c.box("concreteDark", x + sx * 6 - 1.3, -3.2, z - 4, x + sx * 6 + 1.3, 11, z + 3.2);
      c.box("metalDark", x - 4.7, -3.2, z - 0.4, x + 4.7, 6.5, z);
      c.box("concrete", x - 7.6, 11, z - 4.2, x + 7.6, 13.9, z + 3.4);
      c.box("roof", x - 7.9, 13.9, z - 4.5, x + 7.9, 14.15, z + 3.7);
      for (const dx of [-4.2, -1.4, 1.4, 4.2]) c.box("glassDark", x + dx - 0.7, 11.8, z + 3.4, x + dx + 0.7, 13.1, z + 3.45);
      for (const dx of [-2.6, 2.6]) c.box("metalDark", x + dx - 0.12, 6.5, z - 0.3, x + dx + 0.12, 11, z - 0.06);
      break;
    }
    case "monument": {
      c.box("stone", p.x0, 0, p.z0, p.x1, 0.5, p.z1);
      c.box("hedge", p.x0 + 0.35, 0.5, p.z0 + 0.35, p.x1 - 0.35, 1.85, p.z1 - 0.35);
      const xc = (p.x0 + p.x1) / 2;
      c.box("stone", xc - 1.5, 0.5, p.z1 - 0.34, xc + 1.5, 2.3, p.z1 - 0.02, 0x8e9096);
      const mat = new THREE.MeshStandardMaterial({
        map: signTexture({ k: "sign", x: 0, y: 0, z: 0, face: "s", w: 2.6, h: 0.7, lines: ["汐凪警察署"], style: "station", lit: false }),
        roughness: 0.5,
      });
      c.dyn.add(plane(2.6, 0.7, mat, xc, 1.45, p.z1 + 0.0, 0));
      break;
    }
    case "canopy": {
      c.box("stationTrim", p.x0, p.y, p.z0, p.x1, p.y + 0.42, p.z1);
      c.box("stationTrim", p.x0 + 0.15, 0, p.z1 - 0.8, p.x0 + 0.75, p.y, p.z1 - 0.2);
      c.box("stationTrim", p.x1 - 0.75, 0, p.z1 - 0.8, p.x1 - 0.15, p.y, p.z1 - 0.2);
      // entrance surround and the crest above it
      const xc = (p.x0 + p.x1) / 2;
      c.box("stationTrim", xc - 1.75, 0, p.z0 - 0.02, xc - 1.5, 2.6, p.z0 + 0.12);
      c.box("stationTrim", xc + 1.5, 0, p.z0 - 0.02, xc + 1.75, 2.6, p.z0 + 0.12);
      c.box("stationTrim", xc - 1.75, 2.4, p.z0 - 0.02, xc + 1.75, 3.1, p.z0 + 0.12);
      c.box("void", xc - 1.5, 0, p.z0 - 0.03, xc + 1.5, 2.4, p.z0 + 0.0);
      const crest = new THREE.MeshStandardMaterial({ map: crestTexture(), transparent: true, roughness: 0.4, metalness: 0.6 });
      c.dyn.add(plane(1.8, 1.8, crest, xc, 6.4, p.z0 + 0.05, 0));
      break;
    }
    case "arch": {
      c.box("metalPaint", p.x0 - 0.22, 0, p.z - 0.2, p.x0 + 0.22, 5.6, p.z + 0.2, 0x2a4558);
      c.box("metalPaint", p.x1 - 0.22, 0, p.z - 0.2, p.x1 + 0.22, 5.6, p.z + 0.2, 0x2a4558);
      c.box("metalPaint", p.x0 - 0.3, 4.55, p.z - 0.16, p.x1 + 0.3, 5.5, p.z + 0.16, 0x2a4558);
      const mat = new THREE.MeshStandardMaterial({ map: archTexture("なぎさ通り商店街"), roughness: 0.5 });
      const w = p.x1 - p.x0 - 0.8;
      c.dyn.add(plane(w, 0.8, mat, (p.x0 + p.x1) / 2, 5.02, p.z + 0.17, 0));
      c.dyn.add(plane(w, 0.8, mat, (p.x0 + p.x1) / 2, 5.02, p.z - 0.17, Math.PI));
      break;
    }
    case "bike": {
      const M = trs(p.x, p.fallen ? 0.08 : 0.34, p.z, p.rot, 0, p.fallen ? 1.45 : 0.12);
      const wheel = new THREE.TorusGeometry(0.31, 0.022, 6, 16);
      b.add("tire", wheel, mul(M, trs(0, 0, -0.52, Math.PI / 2)));
      b.add("tire", wheel, mul(M, trs(0, 0, 0.52, Math.PI / 2)));
      wheel.dispose();
      b.obox("metalPaint", 0.03, 0.03, 0.75, mul(M, trs(0, 0.3, 0, 0, 0.5)), 0x5d7a86);
      b.obox("metalPaint", 0.03, 0.45, 0.03, mul(M, trs(0, 0.32, 0.2, 0, -0.25)), 0x5d7a86);
      b.obox("metalPaint", 0.03, 0.55, 0.03, mul(M, trs(0, 0.28, -0.45, 0, 0.3)), 0x5d7a86);
      b.obox("metalDark", 0.42, 0.03, 0.03, mul(M, trs(0, 0.6, -0.38)));
      b.obox("metalDark", 0.1, 0.04, 0.22, mul(M, trs(0, 0.56, 0.26)));
      break;
    }
    case "aframe": {
      for (const s of [-1, 1]) {
        b.obox("metalPaint", 0.55, 0.9, 0.03, mul(trs(p.x, 0.44, p.z, p.rot), trs(0, 0, s * 0.14, 0, s * 0.3)), 0xd9d2bc);
      }
      break;
    }
    case "heap": {
      const rnd = prng(Math.round(p.x0 * 31 + p.z0 * 7));
      const w = p.x1 - p.x0;
      const d = p.z1 - p.z0;
      c.box("sandbag", p.x0, 0, p.z0, p.x1, 0.55, p.z1);
      for (let i = 0; i < 9; i++) {
        const x = p.x0 + 0.3 + rnd() * (w - 0.6);
        const z = p.z0 + 0.3 + rnd() * (d - 0.6);
        b.obox("wood", 0.12, 0.12, 1.4 + rnd() * 1.2, trs(x, 0.7 + rnd() * 0.9, z, rnd() * 3, (rnd() - 0.5) * 1.2), 0x8a7458);
      }
      b.obox("tarp", w * 0.95, 0.06, d * 1.25, trs((p.x0 + p.x1) / 2, p.h - 0.45, (p.z0 + p.z1) / 2, 0, 0.5, 0.12), 0x7a3b2a);
      b.obox("tarp", w * 0.6, 0.06, d * 1.1, trs(p.x0 + w * 0.35, p.h - 0.15, (p.z0 + p.z1) / 2, 0.2, -0.35, -0.2), 0x7a3b2a);
      break;
    }
    case "washout": {
      const xc = (p.x0 + p.x1) / 2;
      const w = p.x1 - p.x0 - 0.6;
      // what is left of the road bridge slopes into the canal
      b.obox("concreteDark", w, 0.5, 7, trs(xc, -1.55, p.z0 - 3.2, 0, -0.42, 0.04));
      b.obox("concreteDark", w * 0.7, 0.5, 3.4, trs(xc + 1.2, -2.4, p.z0 - 10.5, 0.3, 0.3, -0.1));
      for (const [dx, dz, s] of [
        [-2.8, 4.2, 0.7],
        [1.4, 2.6, 0.5],
        [3.2, 5.4, 0.9],
        [-0.6, 6.5, 0.6],
      ] as [number, number, number][]) {
        b.obox("concreteDark", s, s * 0.6, s * 1.3, trs(xc + dx, s * 0.25, p.z0 + dz, dx, 0.2, 0.3));
      }
      break;
    }
    default:
      break;
  }
}

export function buildTown(level: Level, mats: Mats): TownHandles {
  const c = new Ctx(mats, level.lights);

  // the ground: one sheet of wet asphalt either side of the canal
  c.box("asphalt", -70, -0.4, -132, 90, 0, 0.6, 0xffffff, "y");
  c.box("asphalt", -70, -0.4, -210, 90, 0, -146, 0xffffff, "y");
  c.box("concreteDark", -70, -3.4, -132.02, 90, -0.4, -132, 0xffffff);
  c.box("concreteDark", -70, -3.4, -146, 90, -0.4, -145.98, 0xffffff);

  for (const p of level.props) {
    switch (p.k) {
      case "box":
        if (p.mat === "vending") {
          // the machine front is a picture: fit it to the box instead of tiling it
          c.batch.obox("vending", p.x1 - p.x0, p.y1 - p.y0, p.z1 - p.z0, trs((p.x0 + p.x1) / 2, (p.y0 + p.y1) / 2, (p.z0 + p.z1) / 2));
        } else {
          c.box(p.mat, p.x0, p.y0, p.z0, p.x1, p.y1, p.z1, 0xffffff, p.y0 === 0 ? "y" : "");
        }
        break;
      case "building":
        c.box(`facade${p.tone % 8}`, p.x0, 0, p.z0, p.x1, p.h, p.z1, 0xffffff, "yY");
        c.box("roof", p.x0, p.h, p.z0, p.x1, p.h + 0.3, p.z1);
        break;
      case "shop":
        buildShop(c, p);
        break;
      case "car":
        buildCar(c, p);
        break;
      case "glassWall":
        buildGlassWall(c, p);
        break;
      case "door":
        buildDoor(c, p);
        break;
      case "sign":
        buildSign(c, p);
        break;
      case "lamp":
        buildLamp(c, p);
        break;
      case "rail":
        buildRail(c, p);
        break;
      case "pole":
        buildPole(c, p);
        break;
      case "ground": {
        const mat = p.mat === "concrete" ? "concreteFloor" : p.mat;
        c.box(mat, p.x0, p.y - 0.05, p.z0, p.x1, p.y, p.z1, 0xffffff, "yxXzZ");
        break;
      }
      case "water":
        c.h.waters.push({ x0: p.x0, z0: p.z0, x1: p.x1, z1: p.z1, y: p.y, kind: p.kind });
        break;
      case "bridge":
        buildBridge(c, p);
        break;
      case "item":
        buildItem(c, p);
        break;
      default:
        buildMisc(c, p);
    }
  }

  // terminal: a wall clock stopped at two
  const clock = new THREE.MeshStandardMaterial({ map: clockTexture(), roughness: 0.4, transparent: true });
  c.dyn.add(plane(1.1, 1.1, clock, -10.2, 3.35, -0.03, Math.PI));

  const statics = c.batch.build(mats);
  c.h.group.add(statics);
  c.h.group.add(c.dyn);
  return c.h;
}
