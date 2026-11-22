import * as T from 'three';
import {
  Builder,
  direction,
  lettering,
  nameplate,
  paint as p,
  plain,
  signTexture,
  surface,
} from './materials';
import { beacon, bench, contact, emitter, ring, tubeLamp, vent, type SetKit } from './fixtures';
import { installHallFixtures } from './terminal-fittings';
import { glassMaterial } from './weather';

const pi = Math.PI;
const quayLogo = nameplate('汐 凪 港', 'SHIONAGI MUNICIPAL PORT', '#ced2b9', '#244344');
function weatherBoard() {
  return signTexture(
    'terminal-departures',
    640,
    380,
    (c) => {
      c.fillStyle = '#203334';
      c.fillRect(0, 0, 640, 380);
      c.fillStyle = '#91a89b';
      c.fillRect(0, 0, 640, 60);
      lettering(c, '渡 船 時 刻 表', 20, 31, 31, '#203536');
      lettering(c, 'DEPARTURES', 422, 32, 20, '#203536', 600, true);
      const rows = [
        ['22:10', '沖灯島', '欠航'],
        ['23:25', '北防波堤', '欠航'],
        ['00:40', '沖灯島', '欠航'],
        ['02:15', '北防波堤', '欠航'],
      ];
      for (const [i, row] of rows.entries()) {
        const y = 102 + i * 66;
        c.fillStyle = '#53635c';
        c.fillRect(20, y + 30, 600, 1);
        lettering(c, row[0], 26, y, 31, '#d6ceb2', 600, true);
        lettering(c, row[1], 226, y, 27, '#bbc9b9');
        lettering(c, row[2], 498, y, 24, '#d2956c');
      }
    },
    0.36,
  );
}
function platformSign() {
  return signTexture(
    'berth-three',
    900,
    215,
    (c) => {
      c.fillStyle = '#162a2b';
      c.fillRect(0, 0, 900, 215);
      c.fillStyle = '#d7ad68';
      c.fillRect(12, 12, 193, 190);
      lettering(c, '03', 29, 111, 113, '#1d302f', 700, true);
      lettering(c, '市営渡船 のりば', 232, 76, 53, '#e5e2c9');
      lettering(c, 'SHIONAGI  FERRY  TERMINAL', 235, 148, 22, '#b8c8bd', 600, true);
      c.strokeStyle = '#d9dcc5';
      c.lineWidth = 9;
      c.lineJoin = 'miter';
      c.beginPath();
      c.moveTo(766, 112);
      c.lineTo(837, 112);
      c.moveTo(804, 80);
      c.lineTo(838, 112);
      c.lineTo(804, 144);
      c.stroke();
      c.strokeStyle = '#88988d';
      c.lineWidth = 2;
      c.strokeRect(3, 3, 894, 209);
    },
    0.65,
  );
}
function suspension(
  b: Builder,
  x: number,
  z: number,
  w: number,
  y: number,
  mat: T.Material,
  height = 0.94,
  ry = 0,
) {
  for (const dx of [-w * 0.38, w * 0.38]) {
    const sx = x + dx * Math.cos(ry),
      sz = z - dx * Math.sin(ry);
    b.tube([sx, y + height * 0.45, sz], [sx, 4.54, sz], 0.025, p.metal);
  }
  b.box(x, y, z, w + 0.12, height + 0.1, 0.14, p.dark, ry);
  b.board(x + Math.sin(ry) * 0.076, y, z + Math.cos(ry) * 0.076, w, height, mat, ry);
}
function railing(b: Builder, x: number, z1: number, z2: number, y = 0.99) {
  for (let z = z1; z <= z2; z += 2.5) {
    b.box(x, y / 2, z, 0.095, y, 0.1, p.metal);
    b.box(x, 0.065, z, 0.25, 0.13, 0.24, p.dark);
  }
  b.tube([x, y, z1], [x, y, z2], 0.052, p.cream);
  b.tube([x, y * 0.47, z1], [x, y * 0.47, z2], 0.03, p.metal);
}
export function buildTerminal(k: SetKit) {
  const { b } = k,
    glass = glassMaterial();
  const flaking = surface('#829087', 'metal'),
    lower = surface('#516561'),
    roof = surface('#545c56', 'metal');
  // Wide bays leave sight lines out over the water from the waiting hall.
  b.box(-0.5, 4.84, -10.5, 18.0, 0.36, 42.6, roof);
  b.box(8.24, 2.34, -10.5, 0.5, 4.67, 41.7, p.structure);
  b.box(7.965, 0.79, -10.4, 0.04, 1.56, 41.4, p.tile);
  b.box(7.9, 1.65, -10.5, 0.075, 0.105, 41.6, p.blue);
  b.box(-9.07, 0.35, -10.45, 0.24, 0.7, 41.4, lower);
  b.box(-9.09, 0.735, -10.45, 0.38, 0.105, 41.4, p.metal);
  for (let z = 9.7; z > -32; z -= 5.8) {
    b.box(-9.02, 2.47, z, 0.3, 4.78, 0.3, p.structure);
    b.box(-9.01, 0.35, z, 0.39, 0.7, 0.42, p.blue);
    for (const x of [-8.6, 7.64]) b.box(x, 4.24, z, 0.74, 0.55, 0.33, lower);
    b.box(-0.5, 4.49, z, 17.3, 0.29, 0.16, flaking);
    if (z - 5.8 >= -31.2) {
      b.board(-9.015, 2.32, z - 2.88, 5.53, 3.2, glass, pi / 2);
      b.box(-9.02, 1.48, z - 2.9, 0.072, 0.044, 5.53, p.metal);
    }
  }
  for (const x of [-8.75, -8.4, 7.1, 7.36]) {
    b.tube([x, 4.32, 10], [x, 4.32, -31], x > 0 ? 0.054 : 0.076, p.metal);
  }
  for (const z of [-2, -17, -27]) {
    for (const x of [1.35, 3.9]) b.tube([x, 4.63, z], [x, 4.22, z], 0.019, p.metal);
    tubeLamp(k, 2.65, 4.15, z, 2.74, z === -17);
  }
  // Rear wall with the evacuation door; clerestory glazing shows movement outside.
  b.box(-3.54, 0.46, -31.07, 10.95, 0.9, 0.22, lower);
  b.box(-3.56, 4.29, -31.07, 10.95, 1.06, 0.23, p.structure);
  for (let x = -8.95; x < 2; x += 2.74) {
    b.box(x, 2.38, -31.07, 0.11, 3.0, 0.18, p.metal);
    b.board(x + 1.36, 2.35, -31.04, 2.61, 2.83, glass);
  }
  b.box(6.97, 2.33, -31.1, 2.09, 4.66, 0.3, p.structure);
  b.box(4, 3.79, -31.11, 4, 1.66, 0.3, lower);
  b.box(4, 3.18, -30.9, 2.42, 0.5, 0.13, p.dark);
  b.board(4, 3.18, -30.821, 2.35, 0.44, direction('非常口', 'EMERGENCY EXIT', '↥', '↑', '#275748'));
  emitter(k, 4, 3.16, -30.65, '#a5e7bd', 22, 9, 1.5);
  beacon(k, 6.1, 2.89, -30.73);
  b.box(-0.5, 2.33, 10.3, 17.52, 4.65, 0.32, p.structure);
  b.board(-0.3, 2.55, 10.1, 4, 1.1, quayLogo, pi);
  // Salt-stained painted guidance and raised ribs remain visible in the reflection.
  const tactile = surface('#967c43', 'metal');
  b.box(2.1, 0.023, -9.35, 0.53, 0.019, 37.8, tactile);
  for (let i = 0; i < 4; i++) b.box(1.91 + i * 0.122, 0.039, -9.25, 0.025, 0.016, 37.45, p.yellow);
  b.box(3.02, 0.029, -28.13, 2.37, 0.032, 0.54, tactile);
  b.box(4, 0.029, -29.58, 0.53, 0.032, 3.16, tactile);
  for (let z = -28.2; z < 9; z += 1.16) b.box(2.1, 0.043, z, 0.53, 0.007, 0.021, p.dark);
  // Port authority fit-out, local printed art and back-lit public information.
  suspension(b, -3.05, -3.7, 4.1, 3.26, platformSign(), 0.99, -0.14);
  suspension(
    b,
    2.25,
    -19.0,
    3.65,
    3.23,
    direction('裏口・避難通路', 'REAR EXIT  /  EVACUATION', '↥', '↑'),
    0.85,
  );
  for (const z of [5.5, -12.5, -22.5]) {
    b.box(7.86, 3.24, z, 0.29, 0.18, 0.32, p.dark);
    beacon(k, 7.71, 3.29, z);
    vent(b, 7.91, 3.91, z + 0.65, -pi / 2);
  }
  const poster = new T.TextureLoader().load(import.meta.env.BASE_URL + 'art/island-poster.webp');
  poster.colorSpace = T.SRGBColorSpace;
  const posterMat = new T.MeshStandardMaterial({
    map: poster,
    emissiveMap: poster,
    emissive: 0xffffff,
    emissiveIntensity: 0.13,
    roughness: 0.78,
  });
  for (const z of [2.6, -16.9]) {
    b.box(7.88, 2.36, z, 0.12, 1.67, 1.18, p.dark);
    b.board(7.8, 2.36, z, 1.08, 1.56, posterMat, -pi / 2);
  }
  b.box(7.82, 2.78, -4.55, 0.22, 1.65, 2.78, p.metal);
  b.board(7.69, 2.78, -4.55, 2.58, 1.49, weatherBoard(), -pi / 2);
  b.board(7.88, 2.61, 6.3, 2.3, 0.71, quayLogo, -pi / 2);
  // Benches and cabinet positions mirror the collision plan.
  bench(b, -4.95, 1.4, 3.1);
  bench(b, -4.95, -6.2, 3.1);
  b.box(-7.15, 0.78, -17.5, 2.64, 1.53, 8.83, p.tile);
  b.box(-7.15, 1.6, -17.5, 2.74, 0.13, 8.96, p.metal);
  b.box(6.4, 0.51, -1.25, 2.32, 1.02, 1.83, p.blue);
  b.box(6.4, 1.055, -1.25, 2.42, 0.07, 1.93, p.metal);
  b.box(5.89, 1.25, -0.95, 0.57, 0.35, 0.29, p.dark);
  b.board(5.89, 1.25, -0.791, 0.52, 0.27, nameplate('防災無線', 'CITY RADIO', '#756d4e'));
  b.tube([6.12, 1.43, -0.99], [6.31, 1.97, -0.99], 0.012, p.metal);
  b.box(5.74, 1.32, -0.795, 0.04, 0.027, 0.009, p.amber);
  b.board(6.31, 0.71, -0.309, 1.63, 0.42, nameplate('設備管理', 'PORT MAINTENANCE', '#314747'));
  ring(b, -8.83, 1.32, -10.69, 0.36, pi / 2);
  // Under the eaves: signal boxes, the quay edge and an original moored launch.
  b.box(-12.2, -0.17, -9.2, 6.3, 0.3, 52, p.structure);
  railing(b, -14.85, -32.5, 15.5);
  for (const z of [-29, -19, -9, 1, 11]) {
    b.box(-14.75, 0.025, z, 0.31, 0.045, 2.1, p.yellow);
    b.add(new T.CylinderGeometry(0.14, 0.21, 0.35, 10), p.dark, -13.72, 0.18, z);
    b.tube([-13.98, 0.35, z], [-13.45, 0.35, z], 0.085, p.dark);
  }
  buildBoat(b, -23, -6);
  installHallFixtures(k);
  for (const [x, z, s] of [
    [-36, -29, 0.86],
    [-51, 14, 0.65],
  ])
    dockCrane(b, x, z, s);
  contact(b, 6.5, -1.25, 3.5, 2.8);
}
function buildBoat(b: Builder, x: number, z: number) {
  const hull = surface('#3c5659', 'metal'),
    cabin = surface('#9ba89d', 'metal'),
    window = plain('#243f45');
  const shape = new T.Shape();
  shape.moveTo(-2.7, 6);
  shape.lineTo(-2.6, -6);
  shape.quadraticCurveTo(-2.3, -8.2, 0, -10);
  shape.quadraticCurveTo(2.3, -8.2, 2.6, -6);
  shape.lineTo(2.7, 6);
  shape.quadraticCurveTo(0, 6.45, -2.7, 6);
  const geo = new T.ExtrudeGeometry(shape, {
    depth: 1.4,
    bevelEnabled: true,
    bevelSize: 0.13,
    bevelThickness: 0.12,
    bevelSegments: 1,
  });
  geo.rotateX(pi / 2);
  b.add(geo, hull, x, 0.84, z);
  b.box(x, 1.6, z + 0.3, 4.3, 1.6, 9.2, cabin);
  b.box(x, 2.57, z + 0.3, 4.75, 0.23, 9.75, p.metal);
  b.box(x, 2.94, z - 2.25, 3.13, 0.6, 3.6, cabin);
  b.box(x, 3.3, z - 2.21, 3.5, 0.13, 4.03, p.metal);
  for (let i = 0; i < 7; i++)
    for (const s of [-1, 1]) b.box(x + s * 2.155, 1.82, z - 3.56 + i * 1.18, 0.035, 0.68, 0.86, window);
  for (const s of [-1, 1])
    for (let i = 0; i < 3; i++) b.box(x + s * 1.58, 2.97, z - 3.55 + i, 0.035, 0.36, 0.75, window);
  b.board(
    x + 2.19,
    1.11,
    z + 1,
    3.1,
    0.43,
    nameplate('汐凪丸', 'SHIONAGI MARU', '#9aaba1', '#233d3e'),
    pi / 2,
  );
  b.tube([x, 3.34, z - 2.3], [x, 5.69, z - 2.3], 0.038, p.metal);
  b.tube([x - 1.05, 4.61, z - 2.3], [x + 1.05, 4.61, z - 2.3], 0.031, p.metal);
  b.box(x, 5.7, z - 2.3, 0.11, 0.11, 0.11, p.amber);
  for (const s of [-1, 1])
    for (let i = 0; i < 7; i++)
      b.tube([x + s * 2.5, 0.85, z - 6.5 + i * 1.7], [x + s * 2.5, 1.29, z - 6.5 + i * 1.7], 0.02, p.cream);
  for (const s of [-1, 1]) b.tube([x + s * 2.5, 1.29, z - 6.5], [x + s * 2.5, 1.29, z + 3.7], 0.022, p.cream);
}
function dockCrane(b: Builder, x: number, z: number, s: number) {
  const steel = surface('#485858', 'metal');
  function rod(a: number[], c: number[], r: number) {
    b.tube([x + a[0] * s, a[1] * s, z + a[2] * s], [x + c[0] * s, c[1] * s, z + c[2] * s], r * s, steel);
  }
  for (const dx of [-1, 1]) for (const dz of [-1, 1]) rod([dx, 0.1, dz], [dx * 0.58, 14, dz * 0.58], 0.12);
  for (let j = 0; j < 7; j++)
    for (const side of [-1, 1]) {
      rod([-0.86, j * 2, side * 0.8], [0.86, j * 2 + 2, side * 0.8], 0.06);
      rod([side * 0.8, j * 2, -0.86], [side * 0.8, j * 2 + 2, 0.86], 0.06);
    }
  b.box(x, 14.2 * s, z, 3.3 * s, 1.3 * s, 2.25 * s, steel);
  for (const side of [-1, 1]) {
    rod([0, 14.6, side * 0.9], [9, 19.2, side * 0.3], 0.13);
    rod([0, 15.9, side * 0.9], [9, 19.2, side * 0.3], 0.09);
    for (let j = 0; j < 5; j++)
      rod([j * 1.8, 14.6 + j * 0.92, side * 0.66], [(j + 1) * 1.8, 16.1 + j * 0.71, side * 0.6], 0.045);
  }
  rod([9, 19.2, 0], [9, 8.2, 0], 0.02);
  b.box(x + 9 * s, 19.2 * s, z, 0.13, 0.15, 0.13, plain('#db7459', true));
}

export function terminalDoor(root: T.Object3D) {
  const g = new T.Group();
  root.add(g);
  g.position.set(2, 0, -31);
  const b = new Builder(g);
  b.box(2, 1.5, 0, 3.96, 3.0, 0.16, p.blue);
  for (const x of [1, 3]) {
    b.box(x, 1.88, 0.089, 1.51, 0.88, 0.04, p.dark);
    b.box(x, 1.88, 0.115, 1.36, 0.74, 0.03, plain('#385458'));
    b.box(x, 1.06, 0.135, 1.61, 0.082, 0.1, p.cream);
    b.board(x, 2.66, 0.086, 0.83, 0.18, nameplate('非常口', 'EXIT', '#396256'));
  }
  b.box(2, 1.5, 0.095, 0.035, 3, 0.04, p.dark);
  b.finish();
  return g;
}
