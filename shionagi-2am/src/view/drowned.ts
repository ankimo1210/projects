import * as THREE from "three";
import { TUNE } from "../sim/sim";
import type { EnemyState } from "../sim/types";
import type { Rig } from "./actors";
import { Batch, trs } from "./batch";

type Point = [x: number, y: number, z: number];
type Profile = [height: number, halfWidth: number, frontDepth: number, backDepth: number];
type Mark = [x: number, y: number, relief?: number];
type Surface = (x: number, y: number, relief?: number) => Point;

const TAU = Math.PI * 2;
const SIDES = 14;
const uv: [number, number][] = [[0, 0], [1, 0], [1, 1], [0, 1]];
const orb = new THREE.SphereGeometry(1, 8, 6);
const dye = new THREE.Color();
const tint = new THREE.Color();
const edge = new THREE.Vector3();
const normal = new THREE.Vector3();
const scale = new THREE.Vector3();
const { lerp, smoothstep, clamp } = THREE.MathUtils;

function mix(a: number, b: number, t: number): number {
  return dye.setHex(a).lerp(tint.setHex(b), t).getHex();
}

function panel(batch: Batch, color: number, a: Point, b: Point, c: Point, d = c): void {
  edge.set(c[0] - a[0], c[1] - a[1], c[2] - a[2]);
  normal.set(b[0] - a[0], b[1] - a[1], b[2] - a[2]).cross(edge).normalize();
  batch.quad("surface", [a, b, c, d], uv, [normal.x, normal.y, normal.z], color);
}

function oval(batch: Batch, color: number, center: Point, radius: Point, tilt = 0): void {
  const matrix = trs(...center, 0, 0, tilt).scale(scale.set(...radius));
  batch.add("surface", orb, matrix, color);
}

function ringPoint([y, rx, front, back]: Profile, angle: number): Point {
  return [rx * Math.sin(angle), y, (back - front - (back + front) * Math.cos(angle)) / 2];
}

// Follow the convex surface between profile rings. Relief is measured out from the face of the mesh.
function frontSurface(rows: Profile[]): Surface {
  return (x, y, relief = 0.003) => {
    let i = 0;
    while (i + 2 < rows.length && y > rows[i + 1]![0]) i++;
    const [ay, aw, af, ab] = rows[i]!;
    const [by, bw, bf, bb] = rows[i + 1]!;
    const t = clamp((y - ay) / (by - ay), 0, 1);
    const rx = lerp(aw, bw, t);
    const front = lerp(af, bf, t);
    const back = lerp(ab, bb, t);
    const cosine = Math.sqrt(Math.max(0, 1 - (x / rx) ** 2));
    return [x, y, (back - front - (back + front) * cosine) / 2 - relief];
  };
}

function mark(batch: Batch, surface: Surface, color: number, a: Mark, b: Mark, c: Mark, d = c): void {
  panel(batch, color, surface(...a), surface(...b), surface(...c), surface(...d));
}

const headRows: Profile[] = [
  [0.025, 0.044, 0.080, 0.024], [0.049, 0.080, 0.113, 0.049],
  [0.092, 0.094, 0.121, 0.077], [0.137, 0.111, 0.132, 0.100],
  [0.172, 0.109, 0.118, 0.109], [0.205, 0.111, 0.138, 0.111],
  [0.240, 0.105, 0.123, 0.110], [0.277, 0.079, 0.074, 0.086],
  [0.296, 0.023, 0.012, 0.036],
];
const face = frontSurface(headRows);

function sculptHead(batch: Batch, skin: number, hair: number, look: number): void {
  const shadow = mix(skin, 0x515e64, 0.58);
  const bone = mix(skin, 0xbab4a1, 0.35);
  const lip = mix(skin, 0x635662, 0.75);
  oval(batch, shadow, [0, 0.010, 0.005], [0.056, 0.088, 0.053]);
  for (let j = 0; j < headRows.length - 1; j++) {
    const lower = headRows[j]!;
    const upper = headRows[j + 1]!;
    for (let i = 0; i < SIDES; i++) {
      const a = (i / SIDES) * TAU;
      const b = ((i + 1) / SIDES) * TAU;
      const forward = Math.cos((a + b) / 2);
      const hairline = 0.126 + (0.092 + (look % 3) * 0.012) * forward + 0.011 * Math.sin(2 * a + look);
      const scalp = (lower[0] + upper[0]) / 2 > hairline;
      const color = scalp ? mix(hair, 0x55574f, 0.11 + 0.08 * Math.cos(a + look)) :
        mix(skin, shadow, j < 2 ? 0.42 : 0.09 + 0.10 * Math.sin(i * 2 + j * 0.9 + look));
      panel(batch, color, ringPoint(upper, a), ringPoint(upper, b), ringPoint(lower, b), ringPoint(lower, a));
      if (j === headRows.length - 2) {
        panel(batch, hair, [0, 0.297, 0.012], ringPoint(upper, b), ringPoint(upper, a));
      }
    }
  }
  for (const side of [-1, 1]) {
    oval(batch, shadow, [side * 0.105, 0.143, 0.003], [0.018, 0.033, 0.018], side * 0.12);
    const eyeY = 0.173 + side * (look % 2 ? -0.004 : 0.004);
    const eye: Surface = (x, y, relief) => face(side * (0.047 + x), eyeY + y, relief);
    // The chalky sliver sits at the floor of a blue-grey socket, beneath a heavy brow ridge.
    const rim: Mark[] = [[-0.032, 0.002], [-0.021, 0.020], [0.004, 0.025], [0.033, 0.014],
      [0.036, -0.007], [0.014, -0.023], [-0.012, -0.017]];
    const slit: Mark[] = [[-0.022, 0.001], [-0.012, 0.008], [0.005, 0.009], [0.023, 0.003],
      [0.018, -0.005], [0.004, -0.008], [-0.012, -0.005]];
    for (let i = 0; i < rim.length; i++) {
      const next = (i + 1) % rim.length;
      const [rx, ry] = rim[i]!;
      const [sx, sy] = slit[i]!;
      const [nx, ny] = rim[next]!;
      const [tx, ty] = slit[next]!;
      const depth = ry > 0.010 ? 0.015 : 0.005;
      const nextDepth = ny > 0.010 ? 0.015 : 0.005;
      mark(batch, eye, i < 3 ? 0x445055 : 0x556369,
        [rx, ry, depth], [nx, ny, nextDepth], [tx, ty, 0.007], [sx, sy, 0.007]);
      mark(batch, eye, i < 3 ? 0xb7bcb4 : 0x9aa7a6,
        [sx, sy, 0.007], [tx, ty, 0.007], [0.002, 0, 0.012]);
    }
    mark(batch, eye, bone, [-0.029, 0.018, 0.011], [-0.005, 0.034, 0.010],
      [0.036, 0.020, 0.006], [0.005, 0.023, 0.019]);
    // Sunken cheeks meet a high, broad cheekbone beside the nose.
    const cheek: Surface = (x, y, relief) => face(side * x, y, relief);
    mark(batch, cheek, bone, [0.032, 0.139], [0.077, 0.155], [0.093, 0.134], [0.054, 0.125, 0.010]);
    mark(batch, cheek, shadow, [0.054, 0.125, 0.010], [0.093, 0.134], [0.065, 0.091], [0.050, 0.110]);
    mark(batch, cheek, shadow, [0.008, 0.183, 0.008], [0.020, 0.127, 0.012],
      [0.015, 0.124, 0.020], [0.006, 0.135, 0.035]);
    mark(batch, cheek, bone, [0, 0.190], [0.008, 0.183, 0.008], [0.006, 0.135, 0.035], [0, 0.131, 0.037]);
    mark(batch, cheek, 0x586265, [0, 0.131, 0.037], [0.015, 0.124, 0.020], [0.007, 0.121, 0.008]);
  }
  // One corner hangs lower. A narrow strip of enamel is caught behind the upper lip.
  const sag = look % 2 ? -0.006 : 0.003;
  mark(batch, face, lip, [-0.047, 0.092], [-0.011, 0.106], [0.018, 0.104], [0.041, 0.092 + sag]);
  mark(batch, face, 0x302d37, [-0.044, 0.091, 0.006], [-0.012, 0.099, 0.009],
    [0.039, 0.091 + sag, 0.006], [0.014, 0.069, 0.009]);
  mark(batch, face, 0x403943, [-0.044, 0.091, 0.006], [0.014, 0.069, 0.009], [-0.016, 0.071, 0.008]);
  mark(batch, face, 0xa4a394, [-0.022, 0.096, 0.010], [0.012, 0.096, 0.011],
    [0.008, 0.092, 0.012], [-0.019, 0.093, 0.011]);
  mark(batch, face, lip, [-0.040, 0.085], [-0.016, 0.071, 0.008], [0.018, 0.068, 0.010], [0.010, 0.060, 0.005]);
  // Plastered locks taper around the temple, leaving both eyes exposed.
  const part = look % 2 ? 1 : -1;
  const temple: Surface = (x, y, relief) => face(part * x, y, relief);
  mark(batch, temple, hair, [0.012, 0.249], [0.075, 0.241], [0.084, 0.189], [0.052, 0.222]);
  mark(batch, temple, mix(hair, 0x444b49, 0.24), [0.066, 0.241], [0.089, 0.226],
    [0.097, 0.156 + 0.008 * (look % 3)], [0.081, 0.205]);
}

function sewCoat(batch: Batch, top: number, look: number, bulk: number): void {
  const hem = [-0.045, 0.025, -0.080, 0.005, -0.012, -0.038][look]!;
  const rows: Profile[] = [
    [hem, 0.193 * bulk, 0.129, 0.137], [0.137, 0.178 * bulk, 0.133, 0.141],
    [0.252, 0.186 * bulk, 0.144, 0.135], [0.373, 0.210 * bulk, 0.159, 0.143],
    [0.463, 0.253 * bulk, 0.147, 0.137], [0.503, 0.259 * bulk, 0.111, 0.112],
    [0.555, 0.072, 0.072, 0.068],
  ];
  const shell = frontSurface(rows);
  const light = mix(top, 0x969886, 0.20);
  const salt = mix(top, 0xbbb3a0, 0.32);
  const soaked = mix(top, 0x1d292b, 0.52);
  const point = (row: number, i: number): Point => {
    const a = (i / SIDES) * TAU;
    const p = ringPoint(rows[row]!, a);
    if (row === 0) {
      const notch = (i + look * 3) % SIDES;
      p[1] += notch === 2 ? 0.115 : 0.035 * Math.sin(5 * a + look) - 0.016 * Math.cos(3 * a);
    }
    if (row === 1) p[1] += 0.031 * Math.sin(3 * a + look) + 0.018 * Math.cos(5 * a);
    return p;
  };
  for (let j = 0; j < rows.length - 1; j++) {
    for (let i = 0; i < SIDES; i++) {
      const a = point(j + 1, i);
      const b = point(j + 1, i + 1);
      const c = point(j, i + 1);
      const d = point(j, i);
      const dye = mix(j === 0 ? soaked : top, light, 0.12 + 0.10 * Math.cos(i * 2 + j * 0.7 + look));
      panel(batch, dye, a, b, c, d);
      // Interrupted deposits along the high-water mark, including the back of the coat.
      if (j === 0 && (i + 2 * look) % 5 < 3) {
        const raised = (p: Point, drop: number): Point => [p[0] * 1.009, p[1] - drop, p[2] * 1.014];
        panel(batch, salt, raised(a, 0), raised(b, 0), raised(b, 0.005), raised(a, 0.012));
      }
    }
  }
  const collar = (spread: number, length: number, color: number): void => {
    for (const side of [-1, 1]) {
      const flap: Surface = (x, y, relief) => shell(x * side, y, relief);
      mark(batch, flap, color, [0.034, 0.543], [spread, 0.509], [spread * 0.64, length], [0.012, 0.488, 0.009]);
    }
  };
  const seam = (color: number, x: number, bottom: number): void => {
    for (const [hi, lo] of [[0.476, 0.375], [0.375, 0.25], [0.25, bottom]] as const) {
      mark(batch, shell, color, [x - 0.004, hi], [x + 0.004, hi], [x + 0.005, lo], [x - 0.003, lo]);
    }
  };
  switch (look) {
    case 0: // Oilskin: storm yoke, stand collar and a corroded zip.
    case 2: { // Longer orange raincoat, crossing storm flap and a belted waist.
      collar(look === 0 ? 0.080 : 0.135, look === 0 ? 0.467 : 0.390, light);
      for (const side of [-1, 1]) {
        const yoke: Surface = (x, y, relief) => shell(x * side, y, relief);
        mark(batch, yoke, light, [0.032, 0.504], [0.187, 0.480], [0.193, 0.443], [0.055, 0.407]);
      }
      seam(look === 0 ? salt : soaked, look === 0 ? 0.013 : -0.022, 0.10);
      if (look === 2) mark(batch, shell, soaked, [-0.134, 0.231], [0.138, 0.214], [0.143, 0.188], [-0.137, 0.210]);
      break;
    }
    case 1: // Office shirt: loose collar, a crooked tie and a missing tail.
    case 5: { // Suit: a pale shirt shows between two long, notched lapels.
      const shirt = look === 1 ? mix(top, 0xa5aba0, 0.40) : 0x858b80;
      mark(batch, shell, shirt, [-0.063, 0.530], [0.064, 0.521], [0.028, 0.404], [0.006, 0.354]);
      collar(look === 1 ? 0.101 : 0.144, look === 1 ? 0.454 : 0.372, look === 1 ? shirt : light);
      mark(batch, shell, 0x414c49, [-0.022, 0.494, 0.013], [0.006, 0.489, 0.013],
        [0.019, 0.416, 0.017], [-0.003, 0.420, 0.016]);
      mark(batch, shell, 0x414c49, [-0.003, 0.420, 0.016], [0.019, 0.416, 0.017],
        [0.043, look === 1 ? 0.265 : 0.341, 0.020], [0.020, look === 1 ? 0.276 : 0.348, 0.019]);
      break;
    }
    case 3: { // Indigo work shirt with one sagging flap pocket.
      collar(0.081, 0.454, light);
      seam(light, -0.006, 0.12);
      mark(batch, shell, light, [0.058, 0.406], [0.149, 0.391], [0.138, 0.317], [0.061, 0.324]);
      mark(batch, shell, salt, [0.056, 0.409, 0.008], [0.151, 0.395, 0.008],
        [0.114, 0.375, 0.008], [0.054, 0.392, 0.008]);
      break;
    }
    case 4: { // Knitted cardigan, stretched open over a grey undershirt.
      mark(batch, shell, 0x75817b, [-0.058, 0.529], [0.066, 0.529], [0.012, 0.363]);
      for (const side of [-1, 1]) {
        const knit: Surface = (x, y, relief) => shell(side * x, y, relief);
        mark(batch, knit, light, [0.064, 0.529, 0.008], [0.085, 0.514, 0.009], [0.010, 0.350, 0.008], [0, 0.368, 0.006]);
      }
      seam(light, 0.008, 0.100);
      break;
    }
  }
}

function sewWaist(batch: Batch, pants: number): void {
  const rows: Profile[] = [[-0.110, 0.169, 0.107, 0.125], [-0.006, 0.186, 0.123, 0.148],
    [0.075, 0.165, 0.118, 0.136], [0.110, 0.158, 0.114, 0.126]];
  for (let i = 0; i < SIDES; i++) {
    const corner = (row: number, offset: number): Point => {
      const a = (i + offset) * TAU / SIDES;
      const p = ringPoint(rows[row]!, a);
      if (row === 0) p[1] += Math.abs(Math.sin(a)) * 0.071;
      return p;
    };
    for (let j = 0; j < rows.length - 1; j++) {
      const color = j === 2 ? mix(pants, 0x4a514c, 0.13) : pants;
      panel(batch, color, corner(j + 1, 0), corner(j + 1, 1), corner(j, 1), corner(j, 0));
    }
  }
}

// The rings overlap at the articulated elbow and knee. A tensed fold breaks the outline
// on one side and runs diagonally into the cloth, as a sleeve or trouser leg does when bent.
const clothCuts: Record<"sleeve" | "cuff" | "thigh" | "shin", Profile[]> = {
  sleeve: [[0.040, 0.047, 0.037, 0.052], [0.010, 0.081, 0.068, 0.082],
    [-0.071, 0.081, 0.071, 0.079], [-0.173, 0.065, 0.062, 0.071],
    [-0.236, 0.066, 0.062, 0.070], [-0.265, 0.073, 0.068, 0.071],
    [-0.283, 0.059, 0.057, 0.063], [-0.315, 0.052, 0.052, 0.057]],
  cuff: [[0.025, 0.051, 0.047, 0.053], [-0.002, 0.064, 0.061, 0.068],
    [-0.053, 0.067, 0.064, 0.064], [-0.119, 0.061, 0.058, 0.062],
    [-0.191, 0.052, 0.048, 0.055], [-0.211, 0.058, 0.054, 0.059],
    [-0.229, 0.051, 0.048, 0.053], [-0.271, 0.046, 0.045, 0.050]],
  thigh: [[0.031, 0.083, 0.081, 0.102], [-0.050, 0.106, 0.102, 0.117],
    [-0.142, 0.110, 0.106, 0.110], [-0.272, 0.089, 0.090, 0.091],
    [-0.343, 0.083, 0.088, 0.082], [-0.379, 0.091, 0.102, 0.084],
    [-0.407, 0.079, 0.089, 0.073], [-0.465, 0.074, 0.077, 0.072]],
  shin: [[0.030, 0.071, 0.070, 0.077], [-0.003, 0.087, 0.090, 0.082],
    [-0.062, 0.084, 0.083, 0.087], [-0.145, 0.077, 0.072, 0.087],
    [-0.262, 0.064, 0.058, 0.071], [-0.314, 0.074, 0.066, 0.075],
    [-0.339, 0.062, 0.060, 0.063], [-0.390, 0.067, 0.066, 0.067]],
};

function sewLimb(batch: Batch, cut: keyof typeof clothCuts, color: number, look: number, side: number): void {
  const rows = clothCuts[cut];
  const width = look === 5 || look === 1 ? 0.95 : 1.03;
  const highlight = mix(color, 0x8b8e83, 0.20);
  const sides = 9;
  const point = (j: number, i: number): Point => {
    const a = (i / sides) * TAU;
    const p = ringPoint(rows[j]!, a);
    const fold = Math.sin(a * 2 + side * 0.7 + look * 0.63);
    p[0] *= width;
    // A diagonal ridge, followed by a pinched recess. Ends stay inside the neighbouring cuff.
    if (j === 4 || j === 5 || j === 6) p[1] += fold * (j === 5 ? 0.026 : 0.019);
    if (j === 5) p[2] += fold * 0.009;
    if (j === 7) p[1] += Math.sin(a + side) * 0.009;
    return p;
  };
  for (let j = 0; j < rows.length - 1; j++) {
    for (let i = 0; i < sides; i++) {
      const a = i * TAU / sides;
      const exposed = Math.max(0, Math.cos(a - side * 0.64));
      const shade = mix(color, highlight, j === 5 ? 0.17 + 0.35 * exposed : 0.05 + 0.08 * exposed);
      panel(batch, shade, point(j, i), point(j, i + 1), point(j + 1, i + 1), point(j + 1, i));
      if (j === 0) panel(batch, color, [0, rows[0]![0], 0], point(j, i + 1), point(j, i));
    }
  }
}

const finger = new THREE.CylinderGeometry(0.68, 1, 1, 5, 1);
const axis = new THREE.Vector3(0, 1, 0);
const rotation = new THREE.Quaternion();
const middle = new THREE.Vector3();
const transform = new THREE.Matrix4();

function fingerJoint(batch: Batch, color: number, from: Point, to: Point, width: number): void {
  edge.set(to[0] - from[0], to[1] - from[1], to[2] - from[2]);
  const length = edge.length();
  rotation.setFromUnitVectors(axis, edge.normalize());
  middle.set((from[0] + to[0]) / 2, (from[1] + to[1]) / 2, (from[2] + to[2]) / 2);
  batch.add("surface", finger, transform.compose(middle, rotation, scale.set(width, length, width * 0.80)), color);
}

function hand(batch: Batch, skin: number, top: number, side: number): void {
  const hem: Surface = (x, y, relief = 0) => [side * x, y, -0.046 + 0.31 * Math.abs(x) - relief];
  mark(batch, hem, mix(top, 0xa4a393, 0.22), [-0.027, -0.250], [0.021, -0.254],
    [0.034, -0.277], [-0.018, -0.265]);
  oval(batch, skin, [0.003 * side, -0.305, -0.005], [0.044, 0.062, 0.026], side * 0.10);
  const tips = mix(skin, 0x5c626c, 0.52);
  for (let i = 0; i < 4; i++) {
    const x = (i - 1.5) * 0.017 * side;
    const length = [0.056, 0.065, 0.061, 0.047][i]!;
    const knuckle: Point = [x, -0.341, -0.003];
    const bend: Point = [x * 1.19, -0.341 - length * 0.59, -0.005];
    fingerJoint(batch, skin, knuckle, bend, 0.011);
    fingerJoint(batch, tips, bend, [x * 1.24, -0.341 - length, -0.020 - i * 0.002], 0.008);
  }
  fingerJoint(batch, skin, [-side * 0.028, -0.296, -0.003], [-side * 0.060, -0.340, -0.014], 0.014);
}

function shapeBoot(batch: Batch, shoe: number): void {
  const rows: Profile[] = [
    [-0.062, 0.065, 0.164, 0.074], [-0.042, 0.080, 0.178, 0.081],
    [-0.009, 0.082, 0.166, 0.078], [0.028, 0.067, 0.087, 0.073], [0.090, 0.063, 0.061, 0.066],
  ];
  for (let j = 0; j < rows.length - 1; j++) {
    for (let i = 0; i < 10; i++) {
      const a = (i / 10) * TAU;
      const b = ((i + 1) / 10) * TAU;
      const bottom = rows[j]!;
      const top = rows[j + 1]!;
      const leather = mix(shoe, 0x6c6e61, j === 1 && Math.cos((a + b) / 2) > 0.4 ? 0.19 : 0.05);
      panel(batch, leather, ringPoint(top, a), ringPoint(top, b), ringPoint(bottom, b), ringPoint(bottom, a));
      if (j === 0) panel(batch, shoe, [0, bottom[0], 0], ringPoint(bottom, a), ringPoint(bottom, b));
    }
  }
}

const joints = ["body", "torso", "head", "armL", "armR", "foreL", "foreR", "legL", "legR", "shinL", "shinR"] as const;
type Joint = (typeof joints)[number];
type Pieces = Partial<Record<Joint | "boot", THREE.BufferGeometry>>;
const wardrobe = new Map<number, Pieces>();
const painted = (roughness: number) => new THREE.MeshStandardMaterial({
  vertexColors: true, roughness, side: THREE.DoubleSide,
});
const wetSkin = painted(0.43);
const clothes = painted(0.70);
const cuffs = painted(0.53);
const leather = painted(0.52);

interface Dressed {
  bootL: THREE.Mesh;
  bootR: THREE.Mesh;
  motion: number;
}
const dressed = new WeakMap<Rig, Dressed>();

function geometry(batch: Batch, material: THREE.Material): THREE.BufferGeometry {
  return (batch.build({ surface: material }).children[0] as THREE.Mesh).geometry;
}

function meshFor(part: THREE.BufferGeometry, material: THREE.Material): THREE.Mesh {
  const mesh = new THREE.Mesh(part, material);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
}

export function dressDrowned(rig: Rig, look: number): void {
  const style = look % 6;
  const skin = mix(rig.mats[0]!.color.getHex(), 0xb2b0a2, 0.46);
  const top = rig.mats[1]!.color.getHex();
  const pants = rig.mats[2]!.color.getHex();
  const shoe = rig.mats[3]!.color.getHex();
  let pieces = wardrobe.get(style);
  if (!pieces) {
    pieces = {};
    wardrobe.set(style, pieces);
  }
  // One coloured mesh per articulating joint. All wearers of the same outfit reuse its buffers.
  for (const name of joints) {
    const joint = rig[name];
    const old = joint.children.filter((child): child is THREE.Mesh => child instanceof THREE.Mesh);
    const forearm = name === "foreL" || name === "foreR";
    const material = name === "head" ? wetSkin : forearm ? cuffs : clothes;
    let part = pieces[name];
    if (!part) {
      const batch = new Batch();
      if (name === "head") {
        sculptHead(batch, skin, rig.mats[4]!.color.getHex(), style);
      } else if (name === "torso") {
        sewCoat(batch, top, style, Math.abs(rig.armL.position.x) / 0.25);
      } else if (name === "body") {
        sewWaist(batch, pants);
      } else {
        const side = name.endsWith("L") ? -1 : 1;
        const arm = name === "armL" || name === "armR";
        const thigh = name === "legL" || name === "legR";
        const cut = arm ? "sleeve" : forearm ? "cuff" : thigh ? "thigh" : "shin";
        sewLimb(batch, cut, (arm || forearm) ? top : pants, style, side);
        if (forearm) hand(batch, skin, top, side);
      }
      part = geometry(batch, material);
      pieces[name] = part;
    }
    joint.remove(...old);
    joint.add(meshFor(part, material));
  }
  if (!pieces.boot) {
    const batch = new Batch();
    shapeBoot(batch, shoe);
    pieces.boot = geometry(batch, leather);
  }
  // The ankle pivots allow a planted sole and a nearly flat, scraping toe on the trailing foot.
  const bootL = meshFor(pieces.boot, leather);
  const bootR = meshFor(pieces.boot, leather);
  bootL.position.y = bootR.position.y = -0.44;
  rig.shinL.add(bootL);
  rig.shinR.add(bootR);
  rig.mats.splice(0, rig.mats.length, wetSkin, clothes, cuffs, leather);
  rig.torso.position.set(0, 0.062, 0.033);
  rig.head.position.set(0, 0.538, -0.005);
  dressed.set(rig, { bootL, bootR, motion: 0 });
}

// Positive local Z is the heel trailing behind the hip. Only the sound foot clears the pavement.
function placeLeg(leg: THREE.Group, shin: THREE.Group, boot: THREE.Mesh, cycle: number, motion: number,
  drag: boolean, side: number, hipHeight: number, fall: number): void {
  const stance = drag ? 0.62 : 0.53;
  const front = drag ? -0.14 : -0.30;
  const back = drag ? 0.274 : 0.34;
  const swing = clamp((cycle - stance) / (1 - stance), 0, 1);
  const z = cycle < stance ? lerp(front, back, cycle / stance) : lerp(back, front, smoothstep(swing, 0, 1));
  const lift = Math.sin(Math.PI * swing) * (drag ? 0.019 : 0.135);
  const rest = lerp(drag ? 0.090 : -0.055, drag ? 0.025 : -0.018, fall);
  const footZ = lerp(rest, z, motion);
  const height = hipHeight - (0.064 + lift * motion);
  const reach = clamp(Math.hypot(height, footZ), 0.04, 0.8898);
  const thigh = 0.45;
  const calf = 0.44;
  const knee = -Math.acos(clamp((reach * reach - thigh * thigh - calf * calf) / (2 * thigh * calf), -1, 1));
  leg.rotation.x = Math.atan2(-footZ, height) + Math.acos(clamp(
    (thigh * thigh + reach * reach - calf * calf) / (2 * thigh * reach), -1, 1));
  leg.rotation.z = side * (drag ? 0.056 + 0.035 * Math.sin(swing * Math.PI) * motion : 0.025);
  shin.rotation.x = knee;
  const toes = drag ? -0.018 - 0.035 * Math.sin(Math.PI * swing) : -0.18 * Math.sin(TAU * swing);
  boot.rotation.x = toes * motion - leg.rotation.x - knee;
  boot.rotation.y = -side * (drag ? 0.20 : 0.045);
}

export function poseDrowned(rig: Rig, enemy: EnemyState, time: number, dt: number, seed: number): void {
  const state = dressed.get(rig);
  if (!state) return;
  const mode = enemy.mode;
  const dead = mode === "dead";
  const side = Math.cos(seed * 1.31) >= 0 ? -1 : 1;
  const weakArm = side < 0 ? rig.armL : rig.armR;
  const strongArm = side < 0 ? rig.armR : rig.armL;
  const weakFore = side < 0 ? rig.foreL : rig.foreR;
  const strongFore = side < 0 ? rig.foreR : rig.foreL;
  const settle = -Math.expm1(-dt * 13);
  const k = mode === "windup" || mode === "recover" || mode === "stagger" ? -Math.expm1(-dt * 32) : settle;
  const neckK = -Math.expm1(-dt * 9);
  state.motion = lerp(state.motion, smoothstep(enemy.speed, 0, 0.49), settle);
  const motion = state.motion;
  const phase = enemy.gait;
  const cycle = (phase / TAU) % 1;
  const shift = Math.sin(phase - 0.28) * motion;
  const armsLag = Math.sin(phase - 0.88) * motion;
  const headLag = Math.sin(phase - 1.27) * motion;
  const idle = dead ? 0 : Math.sin(time * 1.15 + seed);
  let neck = -0.09 + 0.10 * headLag;
  let gaze = side * (0.08 + 0.11 * headLag);
  let lean = -0.24 - 0.042 * shift;
  let slump = 0.135 + 0.08 * shift;
  let twist = side * (0.09 - 0.13 * shift);
  let hang = -0.13 - 0.24 * armsLag;
  let reach = 0.38 + 0.34 * armsLag;
  let hangElbow = 0.095 + 0.065 * headLag;
  let reachElbow = 0.36 - 0.13 * headLag;
  let sweep = 0.07;
  let hips = 0.881 - motion * (0.013 + 0.014 * Math.cos(phase - 0.82));
  let fall = 0;

  switch (mode) {
    case "dormant":
      lean = -0.25;
      neck = -0.37;
      slump = 0.16;
      reach = 0.06;
      hips = 0.881;
      break;
    case "suspicious":
    case "investigate":
    case "search":
      gaze += 0.32 * Math.sin(time * 1.08 + seed);
      neck += 0.13;
      break;
    case "chase":
      lean -= 0.029;
      reach = 0.93 + 0.31 * armsLag;
      hang = 0.19 - 0.29 * armsLag;
      reachElbow = 0.23 + 0.10 * headLag;
      neck += 0.23;
      break;
    case "windup": {
      const strike = smoothstep(enemy.modeT / TUNE.windup, 0.58, 1);
      lean = lerp(0.025, -0.30, strike);
      twist = side * lerp(-0.46, 0.34, strike);
      slump = lerp(0.01, 0.14, strike);
      hang = lerp(0.12, 0.51, strike);
      reach = lerp(2.21, 1.48, strike);
      reachElbow = lerp(0.81, 0.07, strike);
      sweep = lerp(0.47, -0.12, strike);
      neck = 0.18;
      break;
    }
    case "recover": {
      const settleArm = smoothstep(enemy.modeT / TUNE.recover, 0.05, 0.80);
      lean = lerp(-0.30, -0.24, settleArm);
      twist = side * lerp(0.34, 0.09, settleArm);
      reach = lerp(1.48, 0.30, settleArm);
      reachElbow = lerp(0.07, 0.33, settleArm);
      sweep = lerp(-0.12, 0.07, settleArm);
      neck = lerp(0.18, -0.13, settleArm);
      break;
    }
    case "stagger": {
      const recoil = 1 - smoothstep(enemy.modeT / TUNE.stagger, 0.22, 1);
      lean += 0.40 * recoil;
      twist += side * 0.33 * recoil;
      neck += 0.41 * recoil;
      reach -= 0.81 * recoil;
      hang -= 0.55 * recoil;
      sweep += 0.37 * recoil;
      hips -= 0.046 * recoil;
      break;
    }
    case "dead":
      fall = smoothstep(enemy.modeT, 0, 0.76);
      lean = -0.045;
      slump = 0.05;
      twist = side * 0.09;
      neck = 0.04;
      gaze = side * 0.35;
      reach = 0.17;
      hang = 0.11;
      hangElbow = 0.12;
      reachElbow = 0.24;
      sweep = 0.30;
      hips = 0.851;
      break;
  }
  rig.body.position.y = lerp(rig.body.position.y, hips, settle);
  rig.torso.rotation.x = lerp(rig.torso.rotation.x, lean, k);
  rig.torso.rotation.y = lerp(rig.torso.rotation.y, twist, k);
  rig.torso.rotation.z = lerp(rig.torso.rotation.z, -side * (slump + idle * 0.012), k);
  // Counterbalance the dropped shoulder and the bent spine over the feet. The skull stays
  // within the sim's head sphere even while the chin hangs well forward of the ribcage.
  rig.body.position.x = -side * (0.022 + 0.022 * shift) * (1 - fall);
  const heels = 0.11 * Math.max(0, -rig.head.rotation.x - 0.12);
  rig.body.position.z = (0.065 + heels - 0.40 * Math.sin(rig.torso.rotation.x)) * (1 - fall);
  rig.torso.position.x = 0.13 * Math.sin(rig.torso.rotation.z);
  rig.head.position.x = -side * 0.014;
  placeLeg(rig.legL, rig.shinL, state.bootL, side < 0 ? (cycle + 0.5) % 1 : cycle, motion, side < 0, -1, rig.body.position.y, fall);
  placeLeg(rig.legR, rig.shinR, state.bootR, side > 0 ? (cycle + 0.5) % 1 : cycle, motion, side > 0, 1, rig.body.position.y, fall);
  rig.head.rotation.x = lerp(rig.head.rotation.x, neck, neckK);
  rig.head.rotation.y = lerp(rig.head.rotation.y, gaze, neckK);
  rig.head.rotation.z = lerp(rig.head.rotation.z, -side * (0.21 + 0.10 * headLag + idle * 0.025), neckK);
  weakArm.rotation.x = lerp(weakArm.rotation.x, hang, k);
  strongArm.rotation.x = lerp(strongArm.rotation.x, reach, k);
  weakArm.rotation.z = lerp(weakArm.rotation.z, side * (0.15 + 0.065 * armsLag), k);
  strongArm.rotation.z = lerp(strongArm.rotation.z, -side * sweep, k);
  strongArm.rotation.y = lerp(strongArm.rotation.y, side * (0.09 - sweep * 0.72), k);
  weakFore.rotation.x = lerp(weakFore.rotation.x, hangElbow, neckK);
  strongFore.rotation.x = lerp(strongFore.rotation.x, reachElbow, k);
  weakFore.rotation.z = side * (0.07 + 0.045 * headLag);
  rig.root.rotation.x = fall * 1.54;
  rig.root.rotation.z = side * fall * 0.052;
  // Roll off the heels on the way down, then let the back of the coat meet the ground.
  rig.root.position.y = 0.150 * Math.sin(fall * 1.54) + 0.045 * Math.sin(fall * Math.PI);
  if (rig.glimmer) {
    const charged = mode === "windup" || mode === "chase" ? 1 : 0.68;
    const fading = dead ? 1 - smoothstep(enemy.modeT, 0, 3.5) : 1;
    (rig.glimmer.material as THREE.PointsMaterial).opacity =
      fading * charged * (0.35 + 0.10 * Math.sin(time * 2.1 + seed) + 0.07 * Math.sin(time * 5.3 + seed * 2));
  }
}
