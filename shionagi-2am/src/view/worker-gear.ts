// Equipment belonging to the ferry terminal's night-shift maintenance worker.
// Every part lives on the joint that carries it. Local +Z is the wearer's back.
import * as THREE from "three";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";
import type { Rig } from "./actors";
import { Batch, mul, trs } from "./batch";
import { jacketTexture } from "./textures";

type Ring = readonly [y: number, halfWidth: number, halfDepth: number, zOffset?: number];
type Point = [number, number, number];
type Surface = "jacket" | "cloth" | "coated" | "metal" | "lens";
type GearMaterials = Record<Surface, THREE.MeshStandardMaterial>;
const PI = Math.PI;
const ID = new THREE.Matrix4();

/** Sewn and moulded shells, with a continuous back UV and the UV seam at the front. */
function shell(
  rings: readonly Ring[],
  sides = 28,
  shape?: (point: THREE.Vector3, angle: number) => void,
  from = -PI,
  to = PI,
): THREE.BufferGeometry {
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];
  const p = new THREE.Vector3();
  const bottom = rings[0]![0];
  const height = rings[rings.length - 1]![0] - bottom;
  for (const [row, [y, rx, rz, z = 0]] of rings.entries()) {
    for (let i = 0; i <= sides; i++) {
      const u = i / sides;
      const a = from + (to - from) * u;
      p.set(rx * Math.sin(a), y, z + rz * Math.cos(a));
      shape?.(p, a);
      positions.push(p.x, p.y, p.z);
      uvs.push(u, (y - bottom) / height);
      if (row > 0 && i < sides) {
        const b = (row - 1) * (sides + 1) + i;
        indices.push(b, b + 1, b + sides + 1, b + 1, b + sides + 2, b + sides + 1);
      }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
  g.setIndex(indices);
  g.computeVertexNormals();
  if (to - from === 2 * PI) {
    const n = g.getAttribute("normal");
    const end = new THREE.Vector3();
    for (let row = 0; row < rings.length; row++) {
      const i = row * (sides + 1);
      p.fromBufferAttribute(n, i).add(end.fromBufferAttribute(n, i + sides)).normalize();
      n.setXYZ(i, p.x, p.y, p.z);
      n.setXYZ(i + sides, p.x, p.y, p.z);
    }
  }
  return g;
}

function add(batch: Batch, surface: Surface, color: number, g: THREE.BufferGeometry, matrix = ID): void {
  batch.add(surface, g, matrix, color);
  g.dispose();
}

function block(batch: Batch, surface: Surface, color: number, size: Point, radius: number, matrix: THREE.Matrix4): void {
  const g = radius < 0.003 ? new THREE.BoxGeometry(...size) : new RoundedBoxGeometry(...size, 1, radius);
  add(batch, surface, color, g, matrix);
}

function oval(batch: Batch, color: number, radii: Point, matrix: THREE.Matrix4): void {
  add(batch, "cloth", color, new THREE.SphereGeometry(1, 12, 8).scale(...radii), matrix);
}

function wire(batch: Batch, color: number, points: Point[], radius: number, divisions = 14, matrix = ID): void {
  const curve = new THREE.CatmullRomCurve3(points.map(([x, y, z]) => new THREE.Vector3(x, y, z)));
  add(batch, "coated", color, new THREE.TubeGeometry(curve, divisions, radius, 6, false), matrix);
}

function fastener(batch: Batch, color: number, radius: number, depth: number, matrix: THREE.Matrix4): void {
  const disc = new THREE.CylinderGeometry(radius, radius, depth, 14).rotateX(PI / 2);
  add(batch, "metal", color, disc, matrix);
}

function attach(joint: THREE.Group, batch: Batch, mats: GearMaterials, name: string): void {
  const group = batch.build(mats);
  group.name = name;
  joint.add(group);
}

const coatRings: Ring[] = [
  [-0.03, 0.174, 0.123], [-0.023, 0.193, 0.143], [0.006, 0.198, 0.149],
  [0.037, 0.203, 0.146], [0.073, 0.195, 0.14], [0.109, 0.199, 0.146],
  [0.151, 0.205, 0.149], [0.186, 0.199, 0.145], [0.222, 0.21, 0.153],
  [0.272, 0.213, 0.155], [0.338, 0.222, 0.157], [0.397, 0.23, 0.156],
  [0.448, 0.244, 0.153], [0.491, 0.26, 0.142], [0.532, 0.268, 0.13],
  [0.563, 0.253, 0.118], [0.581, 0.216, 0.106], [0.602, 0.151, 0.09],
  [0.615, 0.091, 0.071],
];

function jacketDrape(p: THREE.Vector3, angle: number): void {
  // Fabric gathers just above the belt; shallower folds continue up the back.
  const gathers = 0.019 * Math.exp(-((p.y - 0.16) ** 2) / 0.012) + 0.003;
  const fold = gathers * (0.5 * Math.sin(6 * angle + p.y * 13) + 0.5 * Math.sin(9 * angle - p.y * 8));
  p.x += fold * Math.sin(angle);
  p.z += fold * Math.cos(angle);
  const pleat = Math.abs(angle) - (0.58 + p.y * 0.48);
  p.z -= 0.013 * Math.exp(-(pleat ** 2) / 0.009 - ((p.y - 0.255) ** 2) / 0.009);
  p.y += Math.max(0, 1 - p.y / 0.36) * 0.009 * Math.sin(3 * angle + p.y * 17);
}

function jacket(batch: Batch): void {
  add(batch, "jacket", 0xffffff, shell(coatRings, 48, jacketDrape));
  const openCollar = (p: THREE.Vector3, a: number): void => {
    const front = (1 - Math.cos(a)) * 0.5;
    p.y -= 0.067 * front ** 2 + 0.007 * Math.sin(2 * a + 0.35);
    p.z -= 0.035 * front ** 2;
  };
  add(batch, "coated", 0x2b4153, shell([
    [0.579, 0.165, 0.111], [0.597, 0.152, 0.107], [0.621, 0.125, 0.098],
    [0.649, 0.106, 0.087], [0.666, 0.101, 0.088], [0.67, 0.09, 0.077],
  ], 28, openCollar, -PI + 0.11, PI - 0.11));
  add(batch, "coated", 0x526872, shell([
    [0.659, 0.104, 0.09], [0.663, 0.104, 0.091], [0.666, 0.102, 0.089],
  ], 28, openCollar, -PI + 0.11, PI - 0.11));

  // The web belt compresses the shell at its waist. Small cloth keepers bridge the belt.
  add(batch, "cloth", 0x555343, shell([
    [0.054, 0.201, 0.147], [0.059, 0.205, 0.151],
    [0.091, 0.205, 0.151], [0.095, 0.2, 0.146],
  ], 40, jacketDrape));
  for (const a of [-2.35, -1.55, -0.76, 0, 0.69, 1.54, 2.38]) {
    const anchor = new THREE.Vector3(0.205 * Math.sin(a), 0.075, 0.151 * Math.cos(a));
    jacketDrape(anchor, a);
    block(batch, "cloth", 0x314556, [0.024, 0.064, 0.014], 0.004, trs(anchor.x, anchor.y, anchor.z, a));
  }
  block(batch, "metal", 0x8c8978, [0.064, 0.044, 0.018], 0.006, trs(0, 0.074, -0.154));
  block(batch, "cloth", 0x4c5147, [0.046, 0.026, 0.013], 0.003, trs(0, 0.074, -0.164));

  // A small inspection lamp on a spring clip at the left breast.
  const lamp = trs(-0.098, 0.439, -0.139, PI + 0.45, -0.08);
  block(batch, "coated", 0x303b3e, [0.061, 0.074, 0.035], 0.009, lamp);
  fastener(batch, 0x9c9b85, 0.026, 0.02, mul(lamp, trs(0, 0.006, 0.024)));
  const lens = new THREE.SphereGeometry(1, 14, 8).scale(0.019, 0.019, 0.006);
  add(batch, "lens", 0xffe5ad, lens, mul(lamp, trs(0, 0.006, 0.035)));
}

function beltTools(batch: Batch): void {
  // Waxed canvas tool pocket, box-pleated at the bottom and hung from two short loops.
  const pocket = trs(-0.136, 0.017, 0.119, -0.58, -0.045, -0.055);
  for (const x of [-0.036, 0.035]) {
    block(batch, "cloth", 0x71654c, [0.025, 0.067, 0.024], 0.004, mul(pocket, trs(x, 0.046, 0.002)));
  }
  add(batch, "cloth", 0x807152, shell([
    [-0.091, 0.034, 0.016, 0.019], [-0.082, 0.055, 0.029, 0.02],
    [-0.055, 0.063, 0.037, 0.021], [-0.018, 0.061, 0.036, 0.021],
    [0.022, 0.056, 0.035, 0.019], [0.045, 0.055, 0.028, 0.018],
  ], 18), pocket);
  add(batch, "cloth", 0x978466, shell([
    [-0.014, 0.062, 0.038, 0.023], [-0.006, 0.065, 0.042, 0.021],
    [0.029, 0.058, 0.037, 0.022], [0.046, 0.055, 0.03, 0.019],
  ], 13, (p, a) => { p.y += 0.009 * (1 - Math.cos(a)); }, -1.45, 1.45), pocket);
  block(batch, "coated", 0x5d4c38, [0.019, 0.05, 0.009], 0.004, mul(pocket, trs(0, -0.014, 0.064)));
  fastener(batch, 0xb0a384, 0.0065, 0.005, mul(pocket, trs(0, -0.017, 0.069)));
  // The jaws sit inside the pocket; only the bent, dipped handles of the pliers show.
  for (const s of [-1, 1]) {
    wire(batch, 0xb96949, [
      [s * 0.009, 0.026, 0.021], [s * 0.017, 0.058, 0.02],
      [s * 0.025, 0.092, 0.014], [s * 0.03, 0.104, 0.011],
    ], 0.008, 9, pocket);
  }

  // An old marine radio, with a grille, a rotary knob and a rubber aerial.
  const radio = trs(0.157, 0.081, 0.112, 0.66, -0.06, 0.04);
  block(batch, "coated", 0x303c3f, [0.084, 0.142, 0.057], 0.012, radio);
  block(batch, "coated", 0x556263, [0.064, 0.092, 0.012], 0.006, mul(radio, trs(0, -0.012, 0.029)));
  for (let i = 0; i < 5; i++) {
    block(batch, "coated", 0x263234, [0.047, 0.0055, 0.005], 0.002, mul(radio, trs(0, 0.002 - i * 0.011, 0.036)));
  }
  block(batch, "coated", 0xb7975f, [0.049, 0.011, 0.006], 0.002, mul(radio, trs(0, 0.044, 0.028)));
  add(batch, "coated", 0x29373b, new THREE.CylinderGeometry(0.01, 0.011, 0.02, 10), mul(radio, trs(-0.021, 0.076, 0)));
  wire(batch, 0x333c3e, [[0.023, 0.059, 0], [0.024, 0.096, -0.001], [0.035, 0.151, -0.008]], 0.0055, 9, radio);

  // The handset clips to the right shoulder seam. Its cord stays outside the lettering.
  const handset = trs(0.206, 0.478, 0.088, 0.92, -0.32, -0.16);
  block(batch, "metal", 0x87887a, [0.027, 0.065, 0.024], 0.005, handset);
  block(batch, "coated", 0x38484c, [0.051, 0.063, 0.033], 0.009, mul(handset, trs(0, -0.016, 0.013)));
  for (let i = 0; i < 3; i++) {
    block(batch, "coated", 0x657173, [0.034, 0.0035, 0.003], 0.001, mul(handset, trs(0, -0.01 - i * 0.008, 0.031)));
  }
  const cord: Point[] = [[0.209, 0.443, 0.103], [0.211, 0.407, 0.094]];
  for (let i = 0; i <= 36; i++) {
    const t = i / 36;
    const turn = t * PI * 12;
    cord.push([0.203 - t * 0.012 + Math.cos(turn) * 0.006, 0.382 - t * 0.125, 0.098 + Math.sin(turn) * 0.007]);
  }
  cord.push([0.181, 0.207, 0.111], [0.166, 0.145, 0.124]);
  wire(batch, 0x28363b, cord, 0.0035, 65);
}

function sleeves(upper: THREE.Group, forearm: THREE.Group, mats: GearMaterials, side: number): void {
  const upperBatch = new Batch();
  const sleeveFold = (p: THREE.Vector3, a: number): void => {
    const width = THREE.MathUtils.smoothstep(Math.hypot(p.x, p.z), 0.008, 0.065);
    p.y += width * 0.009 * Math.cos(a + side * 0.55 + p.y * 6);
    p.y -= (0.012 + side * p.x * 0.24) * THREE.MathUtils.smoothstep(p.y, -0.06, 0.065);
    p.x += side * 0.005 * Math.sin(16 * p.y);
  };
  add(upperBatch, "cloth", 0x3d5267, shell([
    [-0.351, 0.037, 0.039], [-0.332, 0.059, 0.062], [-0.31, 0.068, 0.071],
    [-0.279, 0.073, 0.076], [-0.25, 0.072, 0.074], [-0.226, 0.078, 0.081], [-0.201, 0.079, 0.083],
    [-0.161, 0.08, 0.083], [-0.104, 0.086, 0.09], [-0.077, 0.09, 0.093],
  ], 20, sleeveFold));
  add(upperBatch, "cloth", 0x506978, shell([
    [-0.077, 0.09, 0.093], [-0.041, 0.094, 0.098], [0.007, 0.096, 0.099],
    [0.038, 0.089, 0.092], [0.064, 0.073, 0.074], [0.082, 0.044, 0.049], [0.088, 0.001, 0.001],
  ], 20, sleeveFold));
  add(upperBatch, "cloth", 0x948563, shell([[-0.207, 0.082, 0.086], [-0.174, 0.083, 0.086]], 20, sleeveFold));
  add(upperBatch, "coated", 0xc0c9c3, shell([[-0.201, 0.083, 0.087], [-0.18, 0.084, 0.087]], 20, sleeveFold));
  attach(upper, upperBatch, mats, "Work jacket sleeve");

  const lower = new Batch();
  add(lower, "cloth", 0x3b5063, shell([
    [-0.289, 0.043, 0.044], [-0.266, 0.051, 0.054], [-0.244, 0.056, 0.056],
    [-0.222, 0.053, 0.054], [-0.2, 0.06, 0.062], [-0.142, 0.067, 0.068],
    [-0.103, 0.069, 0.073], [-0.078, 0.067, 0.07], [-0.048, 0.071, 0.072],
    [-0.016, 0.069, 0.07], [0.009, 0.065, 0.066], [0.03, 0.052, 0.054], [0.046, 0.03, 0.031],
  ], 20, sleeveFold));
  add(lower, "coated", 0x2a4050, shell([[-0.286, 0.047, 0.049], [-0.28, 0.051, 0.052], [-0.26, 0.054, 0.056]], 20, sleeveFold));
  // Relaxed fingers and thumb on the cupped palm. The fingers follow the wrist during aiming.
  for (let i = 0; i < 4; i++) {
    const length = [0.029, 0.031, 0.028, 0.023][i]!;
    oval(lower, 0xc39778, [0.014, length, 0.012], trs(-side * 0.006, -0.34, -0.03 + i * 0.019, 0, 0.08, -side * 0.17));
  }
  oval(lower, 0xc79a7a, [0.016, 0.029, 0.014], trs(-side * 0.029, -0.321, -0.031, 0, 0.49, -side * 0.33));
  attach(forearm, lower, mats, "Work jacket cuff");
}

function trousersAndBoots(rig: Rig, mats: GearMaterials): void {
  const twill = 0x434d54;
  const seat = new Batch();
  add(seat, "cloth", twill, shell([
    [-0.153, 0.044, 0.049], [-0.137, 0.13, 0.086], [-0.119, 0.163, 0.114],
    [-0.071, 0.188, 0.139], [-0.01, 0.195, 0.145], [0.064, 0.19, 0.139], [0.093, 0.179, 0.128],
  ]));
  for (const side of [-1, 1]) {
    const a = side * 0.64;
    const pocket = (p: THREE.Vector3, angle: number): void => {
      p.y += 0.02 * Math.abs(angle - a);
    };
    add(seat, "cloth", 0x4b565d, shell([
      [-0.112, 0.172, 0.123], [-0.075, 0.193, 0.144], [-0.018, 0.199, 0.15],
    ], 12, pocket, a - 0.36, a + 0.36));
  }
  attach(rig.body, seat, mats, "Work trouser pockets");

  for (const [side, thigh, shin] of [[-1, rig.legL, rig.shinL], [1, rig.legR, rig.shinR]] as const) {
    const crease = (p: THREE.Vector3, a: number): void => {
      p.y += 0.011 * Math.cos(a * 2 + p.y * 14 + side * 0.32);
      p.x += 0.003 * Math.sin(a * 3 + p.y * 11);
    };
    const upper = new Batch();
    add(upper, "cloth", twill, shell([
      [-0.495, 0.053, 0.059], [-0.476, 0.074, 0.081], [-0.45, 0.086, 0.092, -0.004],
      [-0.421, 0.087, 0.096, -0.005], [-0.397, 0.083, 0.089], [-0.375, 0.091, 0.097],
      [-0.347, 0.087, 0.095], [-0.287, 0.093, 0.102], [-0.19, 0.101, 0.111],
      [-0.095, 0.107, 0.116], [-0.012, 0.103, 0.115], [0.045, 0.084, 0.092],
    ], 20, crease));
    attach(thigh, upper, mats, "Work trouser leg");

    const lower = new Batch();
    add(lower, "cloth", twill, shell([
      [-0.272, 0.069, 0.071], [-0.248, 0.075, 0.075], [-0.23, 0.083, 0.083],
      [-0.209, 0.086, 0.086], [-0.186, 0.078, 0.077], [-0.157, 0.085, 0.086],
      [-0.119, 0.079, 0.084], [-0.079, 0.082, 0.087], [-0.04, 0.084, 0.089],
      [0.004, 0.082, 0.088], [0.032, 0.067, 0.074], [0.051, 0.045, 0.05],
    ], 20, crease));
    // Rolled tops, a salt-scuffed welt and a raised toe distinguish the dock boots.
    add(lower, "coated", 0x374540, shell([
      [-0.413, 0.068, 0.082, -0.012], [-0.378, 0.076, 0.085, -0.01], [-0.347, 0.07, 0.076],
      [-0.314, 0.072, 0.077, 0.003], [-0.273, 0.077, 0.08, 0.004], [-0.242, 0.083, 0.084, 0.002],
    ], 20));
    add(lower, "coated", 0x5c6354, shell([
      [-0.255, 0.083, 0.085, 0.002], [-0.249, 0.086, 0.088, 0.002],
      [-0.238, 0.086, 0.089, 0.002], [-0.233, 0.079, 0.081, 0.002],
    ], 20));
    block(lower, "cloth", 0x9c825b, [0.019, 0.048, 0.012], 0.003, trs(0, -0.249, 0.088, 0, -0.11));
    const foot = (p: THREE.Vector3, a: number): void => {
      const toe = (1 - Math.cos(a)) * 0.5;
      const roll = THREE.MathUtils.smoothstep(-p.z, 0.097, 0.195);
      p.x = p.x * (0.84 + 0.29 * toe) + side * 0.009 * roll;
      p.y += 0.014 * roll ** 2;
    };
    add(lower, "coated", 0x3e4b45, shell([
      [-0.447, 0.084, 0.14, -0.056], [-0.425, 0.086, 0.143, -0.056],
      [-0.408, 0.085, 0.141, -0.054], [-0.394, 0.081, 0.132, -0.048],
      [-0.379, 0.079, 0.112, -0.036], [-0.358, 0.073, 0.089, -0.019], [-0.34, 0.069, 0.074, -0.007],
    ], 24, foot));
    add(lower, "coated", 0x333a35, shell([
      [-0.468, 0.001, 0.001, -0.055], [-0.468, 0.077, 0.137, -0.055], [-0.463, 0.085, 0.145, -0.056],
      [-0.448, 0.088, 0.147, -0.056], [-0.443, 0.086, 0.144, -0.056],
    ], 24, foot));
    attach(shin, lower, mats, "Dock boot and tucked trouser cuff");
  }
}

/** Raised ribs pressed into the dome. The feathered edges meet the helmet surface. */
function crownRib(x: number): THREE.BufferGeometry {
  const positions: number[] = [];
  const indices: number[] = [];
  const center = x === 0;
  for (let i = 0; i <= 20; i++) {
    const t = i / 20;
    const a = (t * 2 - 1) * (center ? 1.22 : 1.04);
    const taper = Math.sin(PI * t);
    for (let j = 0; j <= 6; j++) {
      const across = j / 3 - 1;
      const px = x + across * (center ? 0.014 : 0.009) * (0.3 + 0.7 * taper);
      const slice = Math.sqrt(1 - (px / 0.135) ** 2);
      const rise = (center ? 0.008 : 0.005) * taper * (0.5 + 0.5 * Math.cos(PI * across)) - 0.0015;
      positions.push(px, 0.212 + (0.129 * slice + rise) * Math.cos(a), (0.144 * slice + rise) * Math.sin(a));
      if (i < 20 && j < 6) {
        const b = i * 7 + j;
        indices.push(b, b + 7, b + 1, b + 1, b + 7, b + 8);
      }
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  g.setIndex(indices);
  g.computeVertexNormals();
  return g;
}

function face(batch: Batch): void {
  // Set the lids and brows against the rig's existing face, just under the helmet brim.
  const skinZ = (x: number, y: number): number => -0.048 - 0.08 * Math.sqrt(1 - (x / 0.086) ** 2 - ((y - 0.155) / 0.108) ** 2);
  for (const s of [-1, 1]) {
    const x = s * 0.035;
    oval(batch, 0x926d5a, [0.017, 0.0045, 0.0035], trs(x, 0.165, skinZ(x, 0.165), -s * 0.38));
    oval(batch, 0xc0ad93, [0.013, 0.0027, 0.0027], trs(x, 0.165, skinZ(x, 0.165) - 0.0025, -s * 0.38));
    oval(batch, 0x403b35, [0.0037, 0.0033, 0.002], trs(x, 0.165, skinZ(x, 0.165) - 0.0045, -s * 0.38));
    oval(batch, 0x514237, [0.018, 0.0034, 0.003], trs(x, 0.179, skinZ(x, 0.179) - 0.001, -s * 0.4, 0, s * 0.08));
  }
  add(batch, "cloth", 0xc89a7c, shell([
    [0.119, 0.006, 0.004, -0.123], [0.127, 0.014, 0.008, -0.129],
    [0.135, 0.012, 0.011, -0.134], [0.147, 0.009, 0.009, -0.129],
    [0.163, 0.007, 0.005, -0.126], [0.173, 0.004, 0.003, -0.123],
  ], 16));
  oval(batch, 0x987161, [0.019, 0.0022, 0.002], trs(0, 0.105, skinZ(0, 0.105) - 0.001));
}

function helmet(batch: Batch): void {
  const dome: Ring[] = [
    [0.195, 0.112, 0.129], [0.196, 0.149, 0.163, -0.011],
    [0.2, 0.154, 0.17, -0.011], [0.205, 0.152, 0.168, -0.011], [0.209, 0.136, 0.148, -0.002],
  ];
  for (let i = 0; i <= 10; i++) {
    const a = i * PI / 20;
    dome.push([0.212 + 0.129 * Math.sin(a), 0.135 * Math.cos(a), 0.144 * Math.cos(a)]);
  }
  add(batch, "coated", 0xe2b334, shell(dome, 36));
  for (const x of [-0.049, 0, 0.049]) {
    add(batch, "coated", 0xe1b137, crownRib(x));
  }
  add(batch, "coated", 0xb39237, shell([[0.214, 0.137, 0.146], [0.218, 0.136, 0.145]], 36));
  for (const a of [-0.66, 0.66]) {
    add(batch, "coated", 0xcad0be, shell([[0.225, 0.136, 0.145], [0.242, 0.133, 0.142]], 9, undefined, a - 0.37, a + 0.37));
  }
  // Rear adjustment cradle and wheel are tucked under the rim, against the nape.
  add(batch, "coated", 0x394345, shell([[0.168, 0.112, 0.122], [0.187, 0.117, 0.129]], 24, undefined, -1.75, 1.75));
  block(batch, "coated", 0x59605a, [0.067, 0.027, 0.017], 0.006, trs(0, 0.179, 0.127));
  fastener(batch, 0x74776a, 0.013, 0.009, trs(0, 0.18, 0.14));
  // Close-cut hair exposes the nape below the cradle and both ears outside the straps.
  add(batch, "cloth", 0xbb9176, shell([
    [0.012, 0.052, 0.054], [0.046, 0.059, 0.067, 0.003], [0.076, 0.07, 0.084, 0.012],
    [0.103, 0.084, 0.093, 0.016], [0.12, 0.09, 0.097, 0.013], [0.138, 0.088, 0.098, 0.003],
  ], 24, undefined, -1.9, 1.9));
  for (const s of [-1, 1]) {
    oval(batch, 0xc49779, [0.015, 0.031, 0.02], trs(s * 0.104, 0.145, -0.012, 0, -0.2, s * 0.11));
    oval(batch, 0x9f7660, [0.0035, 0.013, 0.009], trs(s * 0.117, 0.146, -0.012, 0, -0.2));
    wire(batch, 0x494f49, [
      [s * 0.126, 0.2, -0.036], [s * 0.107, 0.147, -0.04],
      [s * 0.088, 0.112, -0.067], [s * 0.05, 0.08, -0.08], [0, 0.069, -0.079],
    ], 0.005, 16);
  }
}

export function dressWorker(rig: Rig): void {
  const mats: GearMaterials = {
    jacket: new THREE.MeshStandardMaterial({ map: jacketTexture(), roughness: 0.64, emissive: 0x0b1118 }),
    cloth: new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.73, emissive: 0x0b1015 }),
    coated: new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.36, metalness: 0.06, emissive: 0x0a0d0e }),
    metal: new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.37, metalness: 0.46 }),
    lens: new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.18, emissive: 0xf7da9d, emissiveIntensity: 0.6 }),
  };
  // The garment shells enclose the rig's original clothing primitives.
  const joints = [rig.torso, rig.armL, rig.armR, rig.foreL, rig.foreR, rig.body, rig.legL, rig.legR, rig.shinL, rig.shinR];
  const originalClothes = rig.mats.slice(1, 4);
  for (const joint of joints) {
    for (const child of joint.children) {
      if (child instanceof THREE.Mesh && originalClothes.includes(child.material)) child.visible = false;
      if ((joint === rig.foreL || joint === rig.foreR) && child instanceof THREE.Mesh && child.material === rig.mats[0]) {
        child.scale.set(0.67, 0.86, 0.83);
      }
    }
  }
  const torso = new Batch();
  jacket(torso);
  beltTools(torso);
  attach(rig.torso, torso, mats, "Ferry terminal jacket and tool belt");
  sleeves(rig.armL, rig.foreL, mats, -1);
  sleeves(rig.armR, rig.foreR, mats, 1);
  trousersAndBoots(rig, mats);
  const hardhat = new Batch();
  face(hardhat);
  helmet(hardhat);
  attach(rig.head, hardhat, mats, "Maintenance hard hat");
  rig.mats.push(...Object.values(mats));
}
