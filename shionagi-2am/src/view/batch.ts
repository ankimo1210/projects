// Static geometry batcher: the town is a few thousand boxes, far too many to
// draw one by one. Everything that never moves is appended into one buffer per
// material and ends up as a handful of draw calls.

import * as THREE from "three";

interface Bin {
  pos: number[];
  nor: number[];
  uv: number[];
  col: number[];
  idx: number[];
}

const _c = new THREE.Color();
const _v = new THREE.Vector3();
const _n = new THREE.Vector3();
const _nm = new THREE.Matrix3();

export interface BoxOpts {
  /** texture repeats per metre, horizontally */
  su?: number;
  /** texture repeats per metre, vertically */
  sv?: number;
  color?: number;
  /** faces to leave out: any of "x" (-x), "X" (+x), "y", "Y", "z", "Z" */
  skip?: string;
}

export class Batch {
  private bins = new Map<string, Bin>();

  private bin(name: string): Bin {
    let b = this.bins.get(name);
    if (!b) {
      b = { pos: [], nor: [], uv: [], col: [], idx: [] };
      this.bins.set(name, b);
    }
    return b;
  }

  /** Quad from four corners in counter-clockwise order (seen from the front). */
  quad(
    mat: string,
    p: [number, number, number][],
    uv: [number, number][],
    normal: [number, number, number],
    color = 0xffffff,
  ): void {
    const b = this.bin(mat);
    const base = b.pos.length / 3;
    _c.set(color);
    for (let i = 0; i < 4; i++) {
      const pt = p[i] as [number, number, number];
      const t = uv[i] as [number, number];
      b.pos.push(pt[0], pt[1], pt[2]);
      b.nor.push(normal[0], normal[1], normal[2]);
      b.uv.push(t[0], t[1]);
      b.col.push(_c.r, _c.g, _c.b);
    }
    b.idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
  }

  /** Axis-aligned box with world-space UVs so neighbouring boxes tile seamlessly. */
  box(mat: string, x0: number, y0: number, z0: number, x1: number, y1: number, z1: number, o: BoxOpts = {}): void {
    const su = o.su ?? 0.5;
    const sv = o.sv ?? su;
    const col = o.color ?? 0xffffff;
    const skip = o.skip ?? "";
    if (!skip.includes("X")) {
      this.quad(
        mat,
        [
          [x1, y0, z1],
          [x1, y0, z0],
          [x1, y1, z0],
          [x1, y1, z1],
        ],
        [
          [-z1 * su, y0 * sv],
          [-z0 * su, y0 * sv],
          [-z0 * su, y1 * sv],
          [-z1 * su, y1 * sv],
        ],
        [1, 0, 0],
        col,
      );
    }
    if (!skip.includes("x")) {
      this.quad(
        mat,
        [
          [x0, y0, z0],
          [x0, y0, z1],
          [x0, y1, z1],
          [x0, y1, z0],
        ],
        [
          [z0 * su, y0 * sv],
          [z1 * su, y0 * sv],
          [z1 * su, y1 * sv],
          [z0 * su, y1 * sv],
        ],
        [-1, 0, 0],
        col,
      );
    }
    if (!skip.includes("Z")) {
      this.quad(
        mat,
        [
          [x0, y0, z1],
          [x1, y0, z1],
          [x1, y1, z1],
          [x0, y1, z1],
        ],
        [
          [x0 * su, y0 * sv],
          [x1 * su, y0 * sv],
          [x1 * su, y1 * sv],
          [x0 * su, y1 * sv],
        ],
        [0, 0, 1],
        col,
      );
    }
    if (!skip.includes("z")) {
      this.quad(
        mat,
        [
          [x1, y0, z0],
          [x0, y0, z0],
          [x0, y1, z0],
          [x1, y1, z0],
        ],
        [
          [-x1 * su, y0 * sv],
          [-x0 * su, y0 * sv],
          [-x0 * su, y1 * sv],
          [-x1 * su, y1 * sv],
        ],
        [0, 0, -1],
        col,
      );
    }
    if (!skip.includes("Y")) {
      this.quad(
        mat,
        [
          [x0, y1, z1],
          [x1, y1, z1],
          [x1, y1, z0],
          [x0, y1, z0],
        ],
        [
          [x0 * su, -z1 * su],
          [x1 * su, -z1 * su],
          [x1 * su, -z0 * su],
          [x0 * su, -z0 * su],
        ],
        [0, 1, 0],
        col,
      );
    }
    if (!skip.includes("y")) {
      this.quad(
        mat,
        [
          [x0, y0, z0],
          [x1, y0, z0],
          [x1, y0, z1],
          [x0, y0, z1],
        ],
        [
          [x0 * su, z0 * su],
          [x1 * su, z0 * su],
          [x1 * su, z1 * su],
          [x0 * su, z1 * su],
        ],
        [0, -1, 0],
        col,
      );
    }
  }

  /** Any indexed geometry with normals and UVs, placed by a matrix. */
  add(mat: string, geo: THREE.BufferGeometry, m: THREE.Matrix4, color = 0xffffff): void {
    const b = this.bin(mat);
    const base = b.pos.length / 3;
    const pos = geo.getAttribute("position");
    const nor = geo.getAttribute("normal");
    const uv = geo.getAttribute("uv");
    _nm.getNormalMatrix(m);
    _c.set(color);
    for (let i = 0; i < pos.count; i++) {
      _v.fromBufferAttribute(pos, i).applyMatrix4(m);
      _n.fromBufferAttribute(nor, i).applyMatrix3(_nm).normalize();
      b.pos.push(_v.x, _v.y, _v.z);
      b.nor.push(_n.x, _n.y, _n.z);
      b.uv.push(uv ? uv.getX(i) : 0, uv ? uv.getY(i) : 0);
      b.col.push(_c.r, _c.g, _c.b);
    }
    const index = geo.getIndex();
    if (index) {
      for (let i = 0; i < index.count; i++) b.idx.push(base + index.getX(i));
    } else {
      for (let i = 0; i < pos.count; i++) b.idx.push(base + i);
    }
  }

  /** Oriented box (UVs 0..1 on each face). */
  obox(mat: string, sx: number, sy: number, sz: number, m: THREE.Matrix4, color = 0xffffff): void {
    const g = new THREE.BoxGeometry(sx, sy, sz);
    this.add(mat, g, m, color);
    g.dispose();
  }

  build(mats: Record<string, THREE.Material>, shadows = true): THREE.Group {
    const group = new THREE.Group();
    for (const [name, b] of this.bins) {
      const mat = mats[name];
      if (!mat) throw new Error(`unknown material "${name}"`);
      const geo = new THREE.BufferGeometry();
      geo.setAttribute("position", new THREE.Float32BufferAttribute(b.pos, 3));
      geo.setAttribute("normal", new THREE.Float32BufferAttribute(b.nor, 3));
      geo.setAttribute("uv", new THREE.Float32BufferAttribute(b.uv, 2));
      geo.setAttribute("color", new THREE.Float32BufferAttribute(b.col, 3));
      geo.setIndex(b.idx);
      geo.computeBoundingSphere();
      const mesh = new THREE.Mesh(geo, mat);
      mesh.name = `static:${name}`;
      mesh.castShadow = shadows && !mat.transparent;
      mesh.receiveShadow = shadows;
      mesh.matrixAutoUpdate = false;
      group.add(mesh);
    }
    return group;
  }
}

const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _e = new THREE.Euler();
const _p = new THREE.Vector3();
const _s = new THREE.Vector3(1, 1, 1);

/** Matrix from a position and Euler angles (YXZ order). */
export function trs(x: number, y: number, z: number, ry = 0, rx = 0, rz = 0): THREE.Matrix4 {
  _e.set(rx, ry, rz, "YXZ");
  _q.setFromEuler(_e);
  _p.set(x, y, z);
  return new THREE.Matrix4().compose(_p, _q, _s);
}

/** `parent * local` as a new matrix. */
export function mul(parent: THREE.Matrix4, local: THREE.Matrix4): THREE.Matrix4 {
  return _m.multiplyMatrices(parent, local).clone();
}
