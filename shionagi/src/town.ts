import * as T from 'three';
import {
  Builder,
  direction,
  lettering,
  nameplate,
  paint as p,
  plain,
  random,
  signTexture,
  surface,
} from './materials';
import {
  beacon,
  contact,
  container,
  emitter,
  ring,
  streetLamp,
  tubeLamp,
  van,
  vent,
  wetPatch,
  type SetKit,
} from './fixtures';
import { SOLIDS } from './layout';

const pi = Math.PI;
const shopNames = [
  ['潮見鮮魚', 'SHIOMI FISH'],
  ['朝霧電器', 'ASAGIRI ELECTRIC'],
  ['喫茶 波音', 'NAMINE COFFEE'],
  ['灯屋雑貨', 'TOMOYA SUPPLIES'],
  ['港南理髪室', 'KONAN BARBER'],
  ['汐路薬舗', 'SHIOJI PHARMACY'],
  ['千帆食堂', 'CHIHO DINER'],
  ['船具 水庭', 'MIZUNIWA MARINE'],
  ['海灯写真館', 'KAITO PHOTO'],
  ['青波書店', 'AONAMI BOOKS'],
];
const facings = ['#7d8174', '#768782', '#576f70', '#777a6e', '#687c78'];
const awnings = ['#30534e', '#73594f', '#7f7151', '#536775', '#7d6353'];
const shopSigns = ['#56665e', '#604f45', '#a7ac93', '#405957', '#847053'];
const windowMat = plain('#253c42'),
  glassLight = plain('#76988c');
const paintLine = surface('#aea78b', 'metal');
function facade(k: SetKit, side: number, z: number, w: number, x: number, index: number) {
  const { b } = k,
    r = random(index * 125 + 0.5),
    dep = side > 0 ? 12 : 6.7 + r() * 3,
    tall = 5.5 + r() * 5.7;
  const wall = surface(facings[index % facings.length]),
    trim = surface(awnings[index % 5], 'metal'),
    face = (-side * pi) / 2;
  b.box(x + side * dep * 0.5, tall * 0.5, z, dep, tall, w - 0.05, wall);
  b.box(x + side * dep * 0.5, tall + 0.11, z, dep + 0.22, 0.22, w + 0.12, p.metal);
  b.box(x - side * 0.03, 1.99, z, 0.08, 3.92, w - 0.08, p.dark);
  const shutter = surface(index % 3 === 1 ? '#708078' : '#637370', 'shutter');
  const awningH = 3.22;
  b.box(x - side * 0.13, 1.47, z, 0.16, 2.83, w * 0.72, shutter);
  for (const s of [-1, 1]) b.box(x - side * 0.235, 1.43, z + s * (w * 0.37), 0.23, 2.87, 0.12, p.metal);
  b.box(x - side * 0.16, 0.14, z, 0.33, 0.24, w * 0.74, p.structure);
  b.box(x - side * 0.56, awningH, z, 1.15, 0.15, w * 0.88, trim);
  b.box(x - side * 1.1, awningH - 0.19, z, 0.1, 0.37, w * 0.88, trim);
  for (let n = 0; n < Math.floor(w * 0.7); n++)
    b.box(x - side * 1.155, awningH - 0.18, z - w * 0.37 + n * 1.03, 0.015, 0.32, 0.065, p.cream);
  const [jp, en] = shopNames[index % shopNames.length],
    signBg = shopSigns[index % 5];
  b.box(x - side * 0.16, 3.78, z, 0.28, 0.84, w * 0.78, p.metal);
  b.board(
    x - side * 0.31,
    3.78,
    z,
    w * 0.76,
    0.78,
    nameplate(jp, en, signBg, index % 5 === 2 ? '#263e3e' : '#dad9be'),
    face,
  );
  const levels = Math.floor((tall - 4.4) / 2.2);
  for (let level = 0; level <= levels; level++) {
    const yy = 4.82 + level * 2.03;
    if (yy + 0.61 > tall) break;
    for (let j = 0; j < 3; j++) {
      const zz = z + (j - 1) * w * 0.27;
      b.box(x - side * 0.05, yy, zz, 0.08, 1.14, w * 0.2, p.metal);
      b.box(
        x - side * 0.1,
        yy,
        zz,
        0.035,
        0.93,
        w * 0.175,
        (index + j + level) % 13 === 0 ? glassLight : windowMat,
      );
      b.box(x - side * 0.135, yy, zz, 0.024, 0.97, 0.047, p.metal);
      b.box(x - side * 0.17, yy - 0.6, zz, 0.23, 0.08, w * 0.23, p.structure);
    }
  }
  b.tube([x - side * 0.23, 0.18, z + w * 0.47], [x - side * 0.23, tall - 0.1, z + w * 0.47], 0.089, p.metal);
  for (let h = 0.8; h < tall; h += 2.1) b.box(x - side * 0.22, h, z + w * 0.47, 0.23, 0.08, 0.22, p.dark);
  if (index % 2 === 0) {
    b.box(x - side * 0.25, 4.47, z + w * 0.33, 0.44, 0.67, 1.06, p.cream);
    vent(b, x - side * 0.486, 4.47, z + w * 0.33, face);
  }
  if (index % 3 === 0) {
    b.box(x - side * 0.76, 4.5, z - w * 0.29, 1.34, 0.074, 0.12, p.metal);
    const blade = nameplate(jp.slice(0, 3), en, '#8a7956', '#e9dbb9');
    b.box(x - side * 0.96, 4.0, z - w * 0.29, 0.98, 0.83, 0.14, p.metal);
    b.board(x - side * 0.96, 4.0, z - w * 0.29 + 0.079, 0.92, 0.77, blade);
  }
  if (index % 4 === 0) {
    emitter(k, x - side * 0.7, 2.94, z, '#c1cbb0', 19, 11, 1.1);
    b.box(x - side * 0.8, 3.08, z, 0.05, 0.055, 1.64, p.aqua);
  }
  if (side > 0) {
    for (const ofz of [-0.34, 0.34]) b.box(x + dep + 0.045, 2.43, z + w * ofz, 0.13, 0.95, 0.76, p.dark);
  }
}
function guide(b: Builder, x: number, z: number, label: string, en: string, arrow: string, face = 0) {
  b.box(x, 1.13, z, 0.11, 2.24, 0.12, p.metal);
  b.box(x, 2.05, z, 2.8, 0.69, 0.13, p.metal, face);
  b.board(
    x + Math.sin(face) * 0.076,
    2.05,
    z + Math.cos(face) * 0.076,
    2.72,
    0.61,
    direction(label, en, '↥', arrow),
    face,
  );
}
function wires(b: Builder, x1: number, z1: number, x2: number, z2: number, y: number, sag: number) {
  for (const off of [-0.23, 0, 0.23]) {
    let last = [x1 + off, y, z1];
    for (let i = 1; i <= 6; i++) {
      const t = i / 6,
        point = [x1 + (x2 - x1) * t + off, y - Math.sin(t * pi) * sag, z1 + (z2 - z1) * t];
      b.tube(last, point, 0.014, p.rubber, 4);
      last = point;
    }
  }
}
function streetArch(k: SetKit) {
  const { b } = k;
  for (const x of [-9.45, 8.42]) {
    b.box(x, 2.89, -44.3, 0.22, 5.8, 0.26, p.blue);
    b.box(x, 0.39, -44.3, 0.46, 0.78, 0.46, p.structure);
  }
  b.box(-0.5, 5.7, -44.3, 18.12, 0.13, 0.26, p.blue);
  b.box(-0.5, 5.5, -44.3, 7.3, 1.08, 0.26, p.metal);
  b.board(-0.5, 5.5, -44.15, 7.15, 0.94, nameplate('潮 見 商 店 街', 'SHIOMI SHOPPING STREET', '#395953'));
  beacon(k, 7.8, 2.72, -44.1);
  guide(b, 7.3, -50.1, '保守路・裏路地', 'MAINTENANCE LANE', '→');
}
function laneBoundaries(b: Builder) {
  for (const z of [-62, -79, -95, -112, -130, -146]) {
    b.box(30.9, 3.5, z, 5.6, 7.0, 15.95, surface(z % 2 ? '#526361' : '#596b68'));
    b.box(28.05, 2.04, z, 0.1, 2.57, 2.85, surface('#485b59', 'shutter'));
    b.box(27.91, 3.6, z, 0.32, 0.12, 3.01, p.metal);
    vent(b, 28.04, 4.3, z + 2.45, -pi / 2);
    b.tube([27.91, 0.2, z + 5.35], [27.91, 6.87, z + 5.35], 0.067, p.metal);
  }
  for (let z = -43; z > -163; z -= 9.6) {
    for (const x of [-9.65, 8.69]) b.box(x, 0.099, z, 0.42, 0.192, 9.46, p.structure);
    b.box(-0.46, 0.026, z, 0.1, 0.017, 3.2, paintLine);
  }
  for (let x = -7.8; x < 8; x += 1.45) b.box(x, 0.026, -61.76, 0.66, 0.015, 3.26, paintLine);
}
function service(k: SetKit) {
  const { b } = k,
    slatted = surface('#526762', 'shutter');
  for (const [x, z, w, d] of [
    [-3, -184.1, 25, 6],
    [15.6, -164, 11.0, 7],
    [25, -207, 9.5, 48],
    [48, -205, 9, 61],
  ]) {
    b.box(x, 2.6, z, w, 5.2, d, p.structure);
    b.box(x, 5.34, z, w + 0.4, 0.31, d + 0.4, p.dark);
    b.box(x, 1.5, z + d * 0.504, w * 0.53, 2.98, 0.1, slatted);
  }
  guide(b, 1.2, -174.8, '水門保守通路', 'FLOODGATE  ACCESS', '→');
  b.board(
    7.5,
    3.43,
    -179.93,
    5.25,
    0.98,
    nameplate('汐 凪 第 二 水 門', 'SHIONAGI FLOOD CONTROL  02', '#3a514e'),
  );
  guide(b, 40.7, -179.9, '水門操作盤', 'BRIDGE CONTROL', '↑');
  for (let z = -180; z > -234; z -= 5.8) {
    for (const x of [30.02, 42.97]) {
      b.box(x, 0.4, z, 0.11, 0.8, 0.12, p.yellow);
      b.box(x, 0.61, z, 0.116, 0.18, 0.125, p.rubber);
    }
    b.box(30.14, 0.032, z, 0.16, 0.029, 3.84, p.yellow);
  }
  for (const z of [-186, -211, -231]) streetLamp(k, 42.72, z, -1, 4.4);
  for (const x of [29.8, 43.2]) {
    b.tube([x, 0.91, -233.6], [x, 0.91, -181], 0.039, p.metal);
    b.tube([x, 0.48, -233.6], [x, 0.48, -181], 0.034, p.metal);
  }
  // Canal walls, lifting machinery and the strip of open water below the span.
  for (const z of [-234.28, -249.76]) {
    for (const [x, w] of [
      [12, 41.5],
      [63, 48.5],
    ]) {
      b.box(x, -0.28, z, w, 0.95, 0.62, p.structure);
      b.box(x, 0.203, z, w, 0.13, 0.68, p.metal);
    }
  }
  for (const x of [32.53, 39.52]) {
    b.box(x, 2.28, -234.28, 0.42, 4.56, 0.55, p.metal);
    b.box(x, 4.35, -234.28, 0.61, 0.36, 0.76, p.yellow);
    b.add(new T.CylinderGeometry(0.28, 0.28, 0.41, 12), p.dark, x, 4.13, -234.22, new T.Euler(0, 0, pi / 2));
    b.tube([x, 0.55, -234.3], [x, 3.48, -234.3], 0.089, p.metal);
    b.box(x, 0.35, -234.26, 0.84, 0.7, 1.12, p.structure);
    beacon(k, x, 4.62, -234.25);
  }
  b.box(35.95, 4.35, -234.28, 7.05, 0.21, 0.33, p.metal);
  b.board(
    36,
    3.97,
    -234.04,
    3.76,
    0.62,
    nameplate('水 門 歩 道 橋', 'SHIONAGI LOCK  02', '#9c8559', '#202c2d'),
  );
  guide(b, 39.66, -252.8, '汐凪警察署', 'POLICE STATION', '↑');
}
function police(k: SetKit) {
  const { b } = k,
    cement = surface('#65746f'),
    wall = surface('#465953', 'tile');
  for (const [x, z, w, d, h] of [
    [27.9, -306.7, 15.9, 13.3, 7.5],
    [15.8, -308, 12.6, 12.8, 10.4],
    [42.9, -307.8, 15.0, 13.6, 5.32],
  ]) {
    b.box(x, h / 2, z, w, h, d, cement);
    for (let y = 1.6; y < h - 0.8; y += 2.5) {
      b.box(x, y + 0.5, z + d * 0.503, w * 0.9, 1.4, 0.15, windowMat);
      for (let xx = x - w * 0.44; xx < x + w * 0.46; xx += 1.32)
        b.box(xx, y + 0.5, z + d * 0.514, 0.07, 1.4, 0.16, p.metal);
      b.box(x, y - 0.27, z + d * 0.52, w * 0.97, 0.17, 0.35, wall);
    }
    b.box(x, h + 0.09, z, w + 0.32, 0.22, d + 0.4, p.structure);
  }
  b.box(28, 1.7, -298.82, 7.0, 3.4, 2.34, wall);
  for (const x of [27.1, 28.9]) {
    b.box(x, 1.31, -297.59, 1.74, 2.61, 0.1, p.metal);
    b.box(x, 1.52, -297.52, 1.52, 1.83, 0.045, windowMat);
    b.box(x + (x < 28 ? 0.6 : -0.6), 1.18, -297.43, 0.046, 0.55, 0.11, p.cream);
  }
  b.box(28, 3.52, -297.64, 8.7, 0.29, 4.8, p.structure);
  b.board(
    28,
    3.94,
    -299.59,
    5.3,
    0.84,
    nameplate('汐 凪 警 察 署', 'SHIONAGI POLICE STATION', '#485953', '#d6ddc8'),
  );
  b.board(28, 2.88, -297.61, 2.19, 0.4, direction('避難入口', 'SHELTER', '↥', '↑', '#356048', '#ddf5d2'));
  tubeLamp(k, 28, 3.31, -296.15, 2.26);
  emitter(k, 28, 2.86, -297.13, '#baf0c6', 35, 14, 2.0);
  b.box(12.2, 1.56, -286.4, 0.81, 3.13, 1.32, cement);
  b.board(
    12.2,
    1.77,
    -285.71,
    0.72,
    2.45,
    signTexture('police-stone', 160, 500, (c) => {
      c.fillStyle = '#777d71';
      c.fillRect(0, 0, 160, 500);
      c.textAlign = 'center';
      for (const [i, ch] of [...'汐凪警察署'].entries()) lettering(c, ch, 80, 60 + i * 91, 65, '#273735');
    }),
  );
  for (const s of [-1, 1])
    for (let z = -258; z > -299; z -= 3.6) {
      const x = s < 0 ? 10.2 : 50.6;
      b.box(x, 0.79, z, 0.13, 1.6, 0.13, p.metal);
      b.box(x, 1.41, z - 1.75, 0.08, 0.08, 3.61, p.metal);
      b.box(x, 0.54, z - 1.75, 0.08, 0.07, 3.61, p.metal);
    }
  for (let x = 12; x < 50; x += 2.68) b.box(x, 0.027, -289.1, 0.066, 0.015, 4.8, paintLine);
  b.tube([17, 10.4, -309], [17, 17.8, -309], 0.08, p.metal);
  b.tube([15.9, 16.51, -309], [18.1, 16.51, -309], 0.039, p.metal);
}
function solidProps(k: SetKit) {
  const { b } = k;
  for (const s of SOLIDS) {
    const x = (s.x1 + s.x2) / 2,
      z = (s.z1 + s.z2) / 2,
      w = s.x2 - s.x1,
      d = s.z2 - s.z1,
      h = s.height;
    if (s.id.startsWith('terminal') || s.id === 'radio-cabinet' || s.id.startsWith('station-')) continue;
    if (s.id.includes('van')) {
      van(b, x, z, w, d);
      continue;
    }
    if (s.id.includes('container')) {
      container(b, x, z, w, d, h);
      continue;
    }
    if (s.id === 'pistol-crate') {
      b.box(x, h * 0.49, z, w, h * 0.98, d, surface('#63716b', 'metal'));
      b.box(x, h, z, w + 0.05, 0.052, d + 0.05, p.yellow);
      for (const xx of [x - w * 0.35, x + w * 0.35])
        b.box(xx, h * 0.46, z + d * 0.51, 0.074, h * 0.84, 0.035, p.metal);
      b.board(x, h * 0.55, z + d * 0.53, w * 0.73, 0.28, nameplate('緊急装備', 'EMERGENCY', '#536557'));
      beacon(k, x + 0.66, h + 0.16, z - 0.72);
    } else if (s.id === 'panel-cabinet') {
      b.box(x, h * 0.5, z, w, h, d, p.blue);
      b.box(x - w * 0.505, 1.17, z, 0.09, 0.86, d * 0.81, p.metal);
      b.board(
        x - w * 0.535,
        1.19,
        z,
        d * 0.73,
        0.75,
        nameplate('降 橋', 'LOWER BRIDGE', '#b7aa7f', '#304746'),
        -pi / 2,
      );
      b.box(x - w * 0.55, 0.88, z, 0.07, 0.13, 0.17, p.amber);
      beacon(k, x, yTop(h), z);
    } else if (s.id.includes('stall') || s.id.includes('kiosk') || s.id === 'court-booth') {
      b.box(x, 0.56, z, w, 1.1, d, p.tile);
      for (const xx of [-1, 1])
        for (const zz of [-1, 1])
          b.box(x + xx * (w * 0.48), (h + 1) * 0.5, z + zz * (d * 0.48), 0.105, h - 1, 0.1, p.metal);
      b.box(x, h - 0.12, z, w + 0.17, 0.24, d + 0.16, p.metal);
      b.box(x, (h + 1.13) * 0.5, z - d * 0.47, w * 0.96, h - 1.17, 0.1, windowMat);
      b.board(
        x,
        0.69,
        z + d * 0.511,
        w * 0.69,
        0.32,
        nameplate(
          s.id === 'court-booth' ? '守衛室' : '港の売店',
          s.id === 'court-booth' ? 'GATEHOUSE' : 'SHIONAGI PORT',
          '#47615b',
        ),
      );
    } else {
      b.box(x, h * 0.5, z, w, h, d, s.id.includes('pump') ? p.metal : surface('#756d59', 'wood'));
      for (const xx of [x - w * 0.35, x + w * 0.35]) b.box(xx, h + 0.018, z, 0.085, 0.04, d + 0.035, p.dark);
      if (s.id.includes('pump')) {
        vent(b, x, h * 0.6, z + d * 0.504);
        ring(b, x - 0.64, h * 0.72, z + d * 0.517, 0.25, 0);
      }
    }
    contact(b, x, z, w * 1.3, d * 1.2);
  }
}
function yTop(h: number) {
  return h + 0.21;
}
export function buildTown(k: SetKit) {
  const { b } = k;
  // The back passage opens into the shopping street.
  for (const x of [1.86, 6.13]) b.box(x, 1.77, -36.81, 0.25, 3.56, 11.5, p.structure);
  b.box(4, 3.62, -36.75, 4.6, 0.24, 11.42, p.metal);
  tubeLamp(k, 4, 3.45, -38.1, 1.55, true);
  streetArch(k);
  laneBoundaries(b);
  let index = 0;
  for (let z = -47.4; z > -162; z -= 9.7) facade(k, -1, z, 9.7, -10.18, index++);
  for (const [lo, hi] of [
    [-50, -42],
    [-100, -58],
    [-149, -107],
    [-166, -157],
  ]) {
    const count = Math.max(1, Math.round((hi - lo) / 10.2)),
      w = (hi - lo) / count;
    for (let n = 0; n < count; n++) facade(k, 1, lo + (n + 0.5) * w, w, 9.11, index++);
  }
  for (let n = 0; n < 6; n++) {
    const z = -49 - n * 20;
    streetLamp(k, n % 2 === 0 ? -9.37 : 8.39, z, n % 2 === 0 ? 1 : -1);
    const x = -9.45;
    b.tube([x, 0, z], [x, 7.85, z], 0.13, p.dark);
    b.box(x, 7.35, z, 2.04, 0.1, 0.12, p.metal);
    if (n < 5) wires(b, x, z, x, z - 20, 7.55, 1.32);
    if (n % 2 === 0) wires(b, x, z, 8.8, z - 8, 7.3, 1.35);
  }
  for (const z of [-67, -117, -145]) {
    b.box(28.02, 2.64, z, 0.3, 0.33, 0.28, p.dark);
    emitter(k, 27.88, 2.55, z, '#afcbb5', 14, 9, 1.05);
    wetPatch(b, 26.48, z, '#abcdbb', 1, 3);
  }
  guide(b, 25.5, -153, '水門通路', 'FLOODGATE', '←');
  streetLamp(k, 8.85, -164, -1, 4.5);
  // Low utility yards close the ends of the streets and frame the turn to the lock.
  b.box(-11.87, 2.4, -169, 7.4, 4.8, 15.0, p.structure);
  b.box(-3, 2.62, -178.56, 11.8, 5.23, 5.0, p.structure);
  service(k);
  police(k);
  solidProps(k);
}

export function bridgeObject(root: T.Object3D) {
  const g = new T.Group(),
    b = new Builder(g);
  g.position.set(36, 0.008, -234);
  root.add(g);
  b.box(0, -0.12, -8.02, 5.95, 0.24, 16.04, surface('#555f5b', 'metal'));
  for (let z = -0.12; z > -16; z -= 0.42) b.box(0, 0.016, z, 5.9, 0.025, 0.045, p.dark);
  for (const x of [-2.92, 2.92]) {
    b.box(x, 0.053, -8, 0.13, 0.089, 15.97, p.yellow);
    for (let z = -0.2; z > -16.1; z -= 1.96) b.box(x, 0.53, z, 0.09, 1.06, 0.095, p.metal);
    b.tube([x, 1.07, 0], [x, 1.07, -16], 0.044, p.cream);
    b.tube([x, 0.51, 0], [x, 0.51, -16], 0.029, p.metal);
  }
  b.finish();
  return g;
}

export function pickupObject(root: T.Object3D) {
  const g = new T.Group(),
    b = new Builder(g);
  g.position.set(7.08, 0.98, -54.14);
  root.add(g);
  b.box(0, 0.014, 0, 0.63, 0.028, 0.47, p.dark);
  b.box(0, 0.037, 0, 0.57, 0.021, 0.41, surface('#9e967b', 'wood'));
  b.box(-0.053, 0.09, 0.012, 0.31, 0.068, 0.085, p.rubber);
  b.box(-0.16, 0.09, 0.084, 0.092, 0.071, 0.15, p.dark);
  for (let i = 0; i < 5; i++) b.box(0.147, 0.083, -0.115 + i * 0.053, 0.087, 0.04, 0.027, p.yellow);
  b.finish();
  return g;
}
