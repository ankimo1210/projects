import * as THREE from 'three';

type Kind = 'worker' | 'wanderer';
type Point = [number, number, number];
type Section = [y: number, width: number, depth: number, z?: number, x?: number];
type Binding = number | [first: number, second: number, secondWeight: number];
type BindAt = Binding | ((p: Point, angle: number) => Binding);

const plates = {
  plain: [9, 991, 4, 4],
  cloth: [4, 4, 500, 500],
  knit: [516, 4, 504, 500],
  badge: [5, 517, 502, 179],
  label: [5, 705, 229, 86],
  tag: [244, 705, 262, 86],
  rubber: [5, 802, 502, 172],
  face: [517, 517, 503, 242],
  sick: [517, 771, 503, 245],
} as const;
type Plate = keyof typeof plates;
const tau = Math.PI * 2;
const clamp = THREE.MathUtils.clamp;
const mix = THREE.MathUtils.lerp;

function seeded(seed: number) {
  return () => {
    seed = (Math.imul(1664525, seed) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}

// The same textile, embroidery, face paint and rubber atlas serves the whole cast.
function makeAtlas(): THREE.Texture {
  if (typeof document === 'undefined') {
    const t = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
    t.needsUpdate = true;
    return t;
  }
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1024;
  const ctx = canvas.getContext('2d')!;
  const random = seeded(70231);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, 1024, 1024);
  const inPlate = (plate: Plate, draw: (w: number, h: number) => void) => {
    const [x, y, w, h] = plates[plate];
    ctx.save();
    ctx.translate(x, y);
    ctx.beginPath();
    ctx.rect(0, 0, w, h);
    ctx.clip();
    draw(w, h);
    ctx.restore();
  };
  for (const plate of ['cloth', 'knit', 'rubber'] as const) {
    inPlate(plate, (w, h) => {
      ctx.fillStyle = plate === 'knit' ? '#dbdbd6' : '#ecebe5';
      ctx.fillRect(0, 0, w, h);
      for (let i = 0; i < 11500; i++) {
        const alpha = random() * (plate === 'rubber' ? 0.12 : 0.19);
        ctx.fillStyle = random() > 0.46 ? `rgba(255,255,245,${alpha})` : `rgba(47,48,42,${alpha})`;
        ctx.fillRect(random() * w, random() * h, 0.6 + random() * 4, 0.7 + random() * 2.3);
      }
      if (plate === 'knit') {
        for (let x = -3; x < w + 2; x += 7) {
          ctx.strokeStyle = 'rgba(69,72,66,.30)';
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          for (let y = 0; y <= h; y += 4) {
            const dx = x + (y % 8 ? 1.6 : -1.6);
            if (y === 0) ctx.moveTo(dx, y);
            else ctx.lineTo(dx, y);
          }
          ctx.stroke();
        }
      } else {
        for (let i = 0; i < 190; i++) {
          const x = random() * w, y = random() * h, len = 2 + random() ** 3 * 65;
          ctx.strokeStyle = random() < 0.40 ? 'rgba(244,248,240,.33)' : 'rgba(70,68,54,.13)';
          ctx.lineWidth = random() * 1.4 + 0.4;
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.quadraticCurveTo(x + 1, y + len * 0.7, x - 1.2, y + len);
          ctx.stroke();
        }
      }
    });
  }
  inPlate('badge', (w, h) => {
    ctx.fillStyle = '#33382e';
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = '#9c9669'; ctx.lineWidth = 4;
    ctx.strokeRect(6, 6, w - 12, h - 12);
    ctx.lineWidth = 1.9; ctx.setLineDash([5, 5]);
    ctx.strokeRect(12, 12, w - 24, h - 24); ctx.setLineDash([]);
    ctx.strokeStyle = '#e0d6a1'; ctx.lineWidth = 6;
    ctx.beginPath(); ctx.arc(74, 84, 40, 0, tau); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(51, 92); ctx.lineTo(74, 67); ctx.lineTo(96, 92);
    ctx.moveTo(50, 99); ctx.quadraticCurveTo(62, 90, 74, 97); ctx.quadraticCurveTo(85, 103, 98, 95);
    ctx.moveTo(74, 53); ctx.lineTo(74, 83);
    ctx.stroke();
    // Three stencilled kanji remain legible on machines without Japanese canvas fonts.
    const water = 'M3 4l7 5M1 16l7 5M2 39l8-12';
    const kanji = [water + 'M29 3l-5 9-10 10M24 11h17l-4 10-10 12-12 8M21 19l9 6',
      'M3 41l3-10 1-27h27v25l2 10 4 1 2-7M20 11v22M21 19h8M12 19v14M10 33h19',
      water + 'M16 10h25M22 3v14M34 3v14M14 18h29M23 20l-9 7M33 20l10 7M21 26h15v6H21M21 26v12l3 2h13l4-4'];
    ctx.strokeStyle = '#ebe4bf'; ctx.lineWidth = 3.25; ctx.lineCap = 'square'; ctx.lineJoin = 'round';
    kanji.forEach((path, i) => {
      ctx.save(); ctx.translate(144 + i * 97, 31); ctx.scale(1.44, 1.44);
      ctx.stroke(new Path2D(path)); ctx.restore();
    });
    ctx.fillStyle = '#ebe4bf';
    ctx.font = 'bold 24px Arial,sans-serif';
    ctx.fillText('PORT MAINTENANCE', 139, 129, w - 158);
    for (let i = 0; i < 2200; i++) {
      ctx.fillStyle = random() < .5 ? 'rgba(16,19,15,.19)' : 'rgba(223,216,181,.13)';
      ctx.fillRect(random() * w, random() * h, 1 + random() * 3, 1);
    }
  });
  for (const plate of ['label', 'tag'] as const) {
    inPlate(plate, (w, h) => {
      ctx.fillStyle = plate === 'label' ? '#bdb9a1' : '#4b5145';
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = plate === 'label' ? '#484a40' : '#aba78a'; ctx.lineWidth = 3; ctx.setLineDash([4, 3]);
      ctx.strokeRect(5, 5, w - 10, h - 10); ctx.setLineDash([]);
      ctx.fillStyle = plate === 'label' ? '#363b35' : '#dbd6b5';
      ctx.font = 'bold 46px monospace';
      ctx.fillText(plate === 'label' ? 'S.N. / 07' : 'PORT  07', 12, 58, w - 24);
    });
  }
  for (const plate of ['face', 'sick'] as const) {
    inPlate(plate, (w, h) => {
      const sick = plate === 'sick';
      ctx.scale(w, h);
      ctx.fillStyle = sick ? '#dddcc5' : '#f1e2d3'; ctx.fillRect(0, 0, 1, 1);
      const shade = (x: number, y: number, width: number, height: number, color: string) => {
        ctx.save(); ctx.translate(x, y); ctx.scale(width, height);
        const wash = ctx.createRadialGradient(0, 0, 0, 0, 0, 1);
        wash.addColorStop(0, color); wash.addColorStop(1, 'rgba(125,112,92,0)');
        ctx.fillStyle = wash; ctx.fillRect(-1, -1, 2, 2); ctx.restore();
      };
      for (const side of [-1, 1]) {
        shade(.50 + side * .065, .444, .060, .095, sick ? '#77776d' : '#aba095');
        shade(.50 + side * .091, .564, .047, .082, sick ? '#939486' : '#d8b7a7');
        shade(.50 + side * .093, .672, .043, .147, sick ? '#8f9382' : '#cdbbb0');
        shade(.50 + side * .023, .557, .013, .106, '#beafa0');
        shade(.50 + side * .013, .607, .008, .022, '#8a7d70');
        shade(.50 + side * .233, .520, .033, .128, '#c7a796');
      }
      shade(.50, .687, .049, .026, sick ? '#8f8276' : '#bb9988');
      shade(.50, .795, .071, .077, '#b9aea2');
      for (let i = 0; i < (sick ? 1250 : 630); i++) {
        const x = .5 + (random() - .5) * .32, y = .37 + random() * .50;
        ctx.fillStyle = y > .66 ? 'rgba(71,68,61,.20)' : 'rgba(111,104,80,.12)';
        ctx.fillRect(x, y, .0015 + random() * .0024, .002 + random() * .0047);
      }
    });
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = 4;
  texture.name = '汐凪織地・刺繍・顔料';
  return texture;
}

// Geometry is authored in binding-pose metres. Each character renders in one draw.
const jointPoints: Point[] = [
  [0, .936, .017], [0, 1.079, .007], [0, 1.511, -.018],
];
const parents = [-1, 0, 1];
const sides = [-1, 1] as const;
const limbs = sides.map((sign) => {
  const first = jointPoints.length;
  jointPoints.push([sign * .223, 1.406, -.002], [sign * .273, 1.11, -.004], [sign * .293, .862, -.022],
    [sign * .096, .924, .019], [sign * .106, .514, -.018], [sign * .112, .103, .018]);
  parents.push(1, first, first + 1, 0, first + 3, first + 4);
  return { sign, arm: first, fore: first + 1, hand: first + 2, leg: first + 3, shin: first + 4, foot: first + 5 };
});
type Limb = (typeof limbs)[number];

const colorCache = new Map<number, THREE.Color>();
class Surface {
  positions: number[] = [];
  colors: number[] = [];
  uvs: number[] = [];
  indices: number[] = [];
  joints: number[] = [];
  weights: number[] = [];
  seams: [number, number][] = [];

  vertex(p: Point, paint: number, binding: Binding, plate: Plate = 'plain', u = .5, v = .5, light = 1) {
    const index = this.positions.length / 3;
    this.positions.push(...p);
    let color = colorCache.get(paint);
    if (!color) { color = new THREE.Color(paint); colorCache.set(paint, color); }
    this.colors.push(color.r * light, color.g * light, color.b * light);
    const [x, y, w, h] = plates[plate];
    this.uvs.push((x + 1 + u * (w - 2)) / 1024, 1 - (y + 1 + (1 - v) * (h - 2)) / 1024);
    if (typeof binding === 'number') {
      this.joints.push(binding, 0, 0, 0); this.weights.push(1, 0, 0, 0);
    } else {
      this.joints.push(binding[0], binding[1], 0, 0); this.weights.push(1 - binding[2], binding[2], 0, 0);
    }
    return index;
  }
  face(a: number, b: number, c: number, d: number) { this.indices.push(a, b, c, a, c, d); }
  finish(skinned = true) {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(this.positions, 3));
    g.setAttribute('color', new THREE.Float32BufferAttribute(this.colors, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(this.uvs, 2));
    if (skinned) {
      g.setAttribute('skinIndex', new THREE.Uint16BufferAttribute(this.joints, 4));
      g.setAttribute('skinWeight', new THREE.Float32BufferAttribute(this.weights, 4));
    }
    g.setIndex(this.indices);
    g.computeVertexNormals();
    const normals = g.getAttribute('normal');
    const v = new THREE.Vector3(), other = new THREE.Vector3();
    for (const [a, b] of this.seams) {
      v.fromBufferAttribute(normals, a).add(other.fromBufferAttribute(normals, b)).normalize();
      normals.setXYZ(a, v.x, v.y, v.z); normals.setXYZ(b, v.x, v.y, v.z);
    }
    g.computeBoundingSphere();
    return g;
  }
}

interface LoftOptions {
  count?: number;
  plate?: Plate;
  power?: number;
  arc?: [number, number];
  deform?: (p: Point, angle: number, row: number) => void;
  tint?: (p: Point, angle: number, row: number) => number;
}
function loft(g: Surface, rows: Section[], paint: number, bind: BindAt, opt: LoftOptions = {}) {
  const count = opt.count ?? 20, [a0, a1] = opt.arc ?? [0, tau], power = opt.power ?? 1;
  const start = g.positions.length / 3;
  for (let r = 0; r < rows.length; r++) {
    const [y, w, d, z = 0, x = 0] = rows[r];
    for (let j = 0; j <= count; j++) {
      const angle = a0 + (a1 - a0) * j / count;
      const sin = Math.sin(angle), cos = Math.cos(angle);
      const p: Point = [x + Math.sign(sin) * Math.abs(sin) ** power * w, y, z + Math.sign(cos) * Math.abs(cos) ** power * d];
      opt.deform?.(p, angle, r);
      const v = (y - rows[0][0]) / (rows[rows.length - 1][0] - rows[0][0] || 1);
      g.vertex(p, paint, typeof bind === 'function' ? bind(p, angle) : bind, opt.plate ?? 'cloth', j / count, v, opt.tint?.(p, angle, r) ?? 1);
      if (r && j) {
        const top = start + r * (count + 1) + j;
        g.face(top - count - 2, top - count - 1, top, top - 1);
      }
    }
    if (a1 - a0 > tau - .001) g.seams.push([start + r * (count + 1), start + r * (count + 1) + count]);
  }
}

function wire(g: Surface, points: Point[], radius: number, paint: number, bind: Binding, sides = 6) {
  const start = g.positions.length / 3;
  const tangent = new THREE.Vector3(), a = new THREE.Vector3(), b = new THREE.Vector3();
  const previous = new THREE.Vector3(), next = new THREE.Vector3();
  for (let i = 0; i < points.length; i++) {
    tangent.copy(next.fromArray(points[Math.min(points.length - 1, i + 1)]))
      .sub(previous.fromArray(points[Math.max(0, i - 1)])).normalize();
    a.set(0, 0, 1);
    if (Math.abs(tangent.z) > .91) a.set(0, 1, 0);
    a.cross(tangent).normalize(); b.crossVectors(tangent, a);
    for (let j = 0; j < sides; j++) {
      const c = Math.cos(tau * j / sides) * radius, s = Math.sin(tau * j / sides) * radius, p = points[i];
      g.vertex([p[0] + a.x * c + b.x * s, p[1] + a.y * c + b.y * s, p[2] + a.z * c + b.z * s], paint, bind);
      if (i) {
        const lo = start + (i - 1) * sides, hi = lo + sides, k = (j + 1) % sides;
        g.face(lo + j, lo + k, hi + k, hi + j);
      }
    }
  }
}

// Rounded equipment housings have a bevel on all twelve edges.
function block(g: Surface, center: Point, size: Point, color: number, bind: Binding, bevel = .003, tilt = 0) {
  const [w, h, d] = size.map(n => n / 2);
  const edge = Math.min(w * .46, h * .46, d * .46, bevel);
  const first = g.positions.length / 3;
  const c = Math.cos(tilt), s = Math.sin(tilt);
  for (const [y, trim] of [[-h, edge * .68], [-h + edge, 0], [h - edge, 0], [h, edge * .68]]) {
    const u = w - trim, v = d - trim, corner = edge * .9;
    const outline = [[-u + corner, v], [u - corner, v], [u, v - corner], [u, -v + corner],
      [u - corner, -v], [-u + corner, -v], [-u, -v + corner], [-u, v - corner]];
    for (const [px, pz] of outline)
      g.vertex([center[0] + px * c - y * s, center[1] + px * s + y * c, center[2] + pz], color, bind);
  }
  for (let k = 0; k < 3; k++) for (let j = 0; j < 8; j++) {
    const a = first + k * 8, n = (j + 1) % 8;
    g.face(a + j, a + n, a + n + 8, a + j + 8);
  }
  for (let j = 1; j < 7; j++) {
    g.indices.push(first, first + j + 1, first + j, first + 24, first + 24 + j, first + 24 + j + 1);
  }
}

function crossSection(rows: Section[], y: number): [number, number, number] {
  let hi = 1;
  while (hi < rows.length - 1 && rows[hi][0] < y) hi++;
  const a = rows[hi - 1], b = rows[hi], t = clamp((y - a[0]) / (b[0] - a[0]), 0, 1);
  return [mix(a[1], b[1], t), mix(a[2], b[2], t), mix(a[3] ?? 0, b[3] ?? 0, t)];
}
const zOn = (rows: Section[], x: number, y: number, sign: number, lift = 0) => {
  const [w, d, center] = crossSection(rows, y);
  return center + sign * (d * Math.sqrt(Math.max(.013, 1 - (x / w) ** 2)) + lift);
};

// Curved panels follow the body, including patch corners and harness edges.
function panel(g: Surface, rows: Section[], sign: number, y0: number, y1: number,
  left: [number, number], right: [number, number], color: number, bind: BindAt, plate: Plate = 'cloth', lift = .006) {
  const start = g.positions.length / 3, cols = 12, n = 5;
  for (let iy = 0; iy <= n; iy++) {
    const v = iy / n, y = mix(y0, y1, v);
    for (let ix = 0; ix <= cols; ix++) {
      const u = ix / cols, x = mix(mix(left[0], left[1], v), mix(right[0], right[1], v), u);
      const point: Point = [x, y, zOn(rows, x, y, sign, lift)];
      g.vertex(point, color, typeof bind === 'function' ? bind(point, 0) : bind, plate, sign > 0 ? u : 1 - u, v);
      if (iy && ix) {
        const j = start + iy * (cols + 1) + ix;
        if (sign > 0) g.face(j - cols - 2, j - cols - 1, j, j - 1);
        else g.face(j - 1, j, j - cols - 1, j - cols - 2);
      }
    }
  }
}

const workerBody: Section[] = [
  [.865, .198, .152, .004], [.879, .212, .158, .006], [.894, .215, .156, .007],
  [.917, .212, .151, .008], [.953, .208, .146, .012], [.996, .189, .132, .010],
  [1.025, .184, .134, .008], [1.058, .194, .142, .006], [1.088, .190, .137, .006],
  [1.154, .202, .145, .004], [1.236, .215, .150, .004], [1.306, .229, .154, .002],
  [1.366, .245, .150, .006], [1.397, .245, .139, .008], [1.423, .219, .128, .009],
  [1.449, .162, .109, .004], [1.468, .105, .086, -.001],
];
const cape: Section[] = [
  [1.227, .221, .157, .005], [1.233, .223, .159, .005], [1.243, .222, .157, .005],
  [1.308, .236, .160, .004], [1.366, .249, .156, .006], [1.400, .250, .147, .009],
  [1.429, .216, .132, .011], [1.453, .156, .111, .004], [1.472, .098, .086, -.001],
];
const npcBody: Section[] = [
  [.708, .247, .182, .009], [.736, .248, .183, .009], [.805, .240, .179, .009],
  [.904, .225, .166, .010], [.981, .196, .145, .011], [1.051, .187, .136, .012],
  [1.142, .189, .141, .014], [1.225, .201, .151, .015], [1.301, .222, .151, .018],
  [1.369, .236, .143, .021], [1.412, .212, .130, .020], [1.454, .153, .105, .006], [1.473, .085, .087, -.005],
];
const trunkWeight = (p: Point): Binding => [0, 1, clamp((p[1] - .987) / .201, 0, 1)];
const crease = (_: Point, a: number, i: number) => .95 + .056 * Math.cos(a * 5 + i * .51) + .028 * Math.sin(a * 11 - i * .64);

function stripe(g: Surface, rows: Section[], y0: number, y1: number, paint: number, bind: BindAt, lift: number) {
  const records: Section[] = [y0, y1].map(y => {
    const [w, d, z] = crossSection(rows, y);
    return [y, w + lift, d + lift, z];
  });
  loft(g, records, paint, bind, { count: 40, tint: crease });
}

function shoulderStrap(g: Surface, side: number) {
  const first = g.positions.length / 3;
  for (let j = 0; j <= 14; j++) for (let i = 0; i <= 6; i++) {
    const x = side * .156 + (i / 6 - .5) * .035;
    const yEnd = 1.420;
    const z = mix(zOn(cape, x, yEnd, 1, .002), zOn(cape, x, yEnd, -1, .002), j / 14);
    let lo = yEnd - .005, hi = 1.468;
    for (let k = 0; k < 13; k++) {
      const y = (lo + hi) / 2, [w, d, center] = crossSection(cape, y);
      if ((x / w) ** 2 + ((z - center) / d) ** 2 <= 1) lo = y;
      else hi = y;
    }
    g.vertex([x, lo + .004, z], i === 1 || i === 5 ? 0x686a56 : 0x4b5041, 1, 'knit', i / 6, j / 14);
    if (i && j) { const a = first + j * 7 + i; g.face(a - 8, a - 7, a, a - 1); }
  }
}

function clothFold(g: Surface, rows: Section[], path: [number, number][], width: number, depth: number, paint: number, bind: Binding) {
  const curve = new THREE.CatmullRomCurve3(path.map(([x, y]) => new THREE.Vector3(x, y, 0)));
  const first = g.positions.length / 3;
  for (let i = 0; i <= 12; i++) {
    const t = i / 12, center = curve.getPoint(t), tangent = curve.getTangent(t);
    const bulge = Math.max(.025, Math.sin(t * Math.PI)) ** .63;
    for (let j = 0; j < 3; j++) {
      const dx = (j - 1) * width * bulge;
      const x = center.x - tangent.y * dx, y = center.y + tangent.x * dx;
      g.vertex([x, y, zOn(rows, x, y, 1, .0003 + (j === 1 ? depth * bulge : 0))],
        paint, bind, 'cloth', t, j / 2, j === 0 ? .86 : j === 1 ? 1.04 : .92);
      if (i && j) { const a = first + i * 3 + j; g.face(a - 4, a - 1, a, a - 3); }
    }
  }
}

function workerTorso(g: Surface) {
  loft(g, workerBody, 0xba8235, trunkWeight, { count: 40, tint: crease, deform: (p, a, r) => {
    if (r > 1 && r < 11) {
      p[1] += .006 * Math.sin(2 * a + .40 * r) + .003 * Math.cos(5 * a - .28 * r);
      const fold = -.0028 * (1 + Math.cos(a * 7 + r * .8));
      p[0] += Math.sin(a) * fold; p[2] += Math.cos(a) * fold;
    }
  } });
  loft(g, cape, 0xd09a4a, 1, { count: 40, tint: crease });
  stripe(g, workerBody, .882, .892, 0x755a34, 0, .0017);
  stripe(g, workerBody, 1.011, 1.040, 0x514c37, trunkWeight, .003);
  stripe(g, workerBody, 1.015, 1.035, 0xa7a994, trunkWeight, .005);
  stripe(g, cape, 1.238, 1.265, 0x706d4b, 1, .002);
  stripe(g, cape, 1.243, 1.261, 0xcbcbb1, 1, .0036);
  panel(g, cape, 1, 1.278, 1.372, [-.126, -.126], [.126, .126], 0xffffff, 1, 'badge', .005);
  for (const s of sides) {
    panel(g, cape, 1, 1.242, 1.427, [s * .175 - .014, s * .155 - .018], [s * .175 + .014, s * .155 + .018], 0x4e5343, 1, 'knit', .006);
    panel(g, workerBody, 1, 1.033, 1.245, [s * .131 - .014, s * .172 - .014], [s * .131 + .014, s * .172 + .014], 0x4c4e3d, trunkWeight, 'knit', .010);
    panel(g, workerBody, -1, 1.031, 1.42, [s * .13 - .012, s * .155 - .017], [s * .13 + .012, s * .155 + .017], 0x414638, trunkWeight, 'knit', .011);
    shoulderStrap(g, s);
    panel(g, workerBody, -1, .942, 1.048, [s * .117 - .043, s * .124 - .044], [s * .117 + .043, s * .124 + .044], 0x9b712f, 0, 'cloth', .009);
    panel(g, workerBody, -1, 1.032, 1.058, [s * .122 - .046, s * .123 - .049], [s * .122 + .044, s * .123 + .047], 0xcb9345, 0, 'cloth', .012);
    clothFold(g, workerBody, [[s * .042, 1.206], [s * .094, 1.171], [s * .153, 1.147], [s * .181, 1.114]], .009, .006, 0xba843a, 1);
    clothFold(g, workerBody, [[s * .097, 1.067], [s * .144, 1.087], [s * .187, 1.095]], .007, .005, 0xaf7e37, 1);
    clothFold(g, workerBody, [[s * .015, .918], [s * .062, .939], [s * .106, .948]], .006, .0034, 0xb98339, 0);
    const yokeEdges = [[[s * .054, 1.448], [s * .107, 1.429], [s * .140, 1.416]],
      [[s * .182, 1.395], [s * .198, 1.383], [s * .214, 1.370]]];
    for (const offset of [0, .0047]) {
      for (const edge of yokeEdges) {
        const seam: Point[] = edge.map(([x, y]) => [x, y - offset, zOn(cape, x, y - offset, 1, .002)]);
        wire(g, seam, .00145, offset ? 0xd8a459 : 0x957038, 1, 5);
      }
    }
    const strapEdge: Point[] = [];
    for (let i = 0; i <= 8; i++) {
      const t = i / 8, y = mix(1.249, 1.420, t), x = mix(s * .175, s * .155, t) + s * .010;
      strapEdge.push([x, y, zOn(cape, x, y, 1, .007)]);
    }
    wire(g, strapEdge, .0009, 0x80816b, 1, 5);
  }
  const bx = .171, by = 1.272;
  for (const dy of [-.010, .010]) {
    const rail: Point[] = [-.018, 0, .018].map(dx => [bx + dx, by + dy, zOn(cape, bx + dx, by + dy, 1, .012)]);
    wire(g, rail, .0022, 0x9a9a83, 1, 5);
  }
  for (const dx of [-.018, .018]) wire(g, [[bx + dx, by - .010, zOn(cape, bx + dx, by - .010, 1, .012)],
    [bx + dx, by + .010, zOn(cape, bx + dx, by + .010, 1, .012)]], .0022, 0x9a9a83, 1, 5);
  panel(g, workerBody, -1, .913, 1.454, [-.012, -.014], [.011, .014], 0x9a7134, trunkWeight, 'cloth', .013);
  panel(g, workerBody, -1, 1.207, 1.251, [.033, .034], [.130, .132], 0xf6f0d5, 1, 'label', .011);
  for (const y of [1.104, 1.182, 1.270, 1.349, 1.426])
    block(g, [.001, y, zOn(workerBody, 0, y, -1, .018)], [.009, .009, .005], 0x73715b, 1);
  // Turned, double-walled storm collar and the ochre cord at its hem.
  const collar: Section[] = [[1.435, .119, .104, .006], [1.453, .136, .119, .009],
    [1.478, .126, .108, .006], [1.505, .108, .098, .001], [1.523, .102, .094, -.001],
    [1.527, .093, .087, -.001], [1.510, .088, .081, -.001]];
  const drop = (p: Point, a: number) => { p[1] -= .028 * Math.max(0, -Math.cos(a)); };
  loft(g, collar.slice(0, 6), 0xad803d, 1, { deform: drop, count: 32, tint: crease });
  loft(g, [[1.499, .091, .082], [1.525, .097, .091]], 0x494d3b, 1, { deform: drop, count: 32 });
  const folded: Point[] = [];
  for (let i = 0; i <= 18; i++) {
    const a = -1.35 + i / 18 * 2.7;
    folded.push([Math.sin(a) * .124, 1.466 + .014 * Math.cos(a * 2), .011 + .113 * Math.cos(a)]);
  }
  wire(g, folded, .007, 0xc49a58, 1, 8);
  // Radio clipped high on the left strap. Its moulded grille is silhouette geometry.
  const x = -.174;
  block(g, [x, 1.331, .145], [.073, .120, .037], 0x363b35, 1, .007, -.095);
  block(g, [x, 1.325, .165], [.063, .097, .012], 0x51554a, 1, .004, -.095);
  block(g, [x + .001, 1.354, .172], [.042, .016, .005], 0x939c7e, 1, .001);
  for (let i = 0; i < 6; i++) block(g, [x, 1.338 - i * .0064, .173], [.045 - Math.abs(i - 2) * .002, .0028, .003], 0x323831, 1, .0008);
  block(g, [x - .020, 1.399, .145], [.015, .018, .016], 0x272e2a, 1);
  wire(g, [[x - .02, 1.402, .145], [x - .026, 1.451, .147], [x - .045, 1.583, .156]], .0035, 0x363d3b, 1, 8);
  block(g, [x - .045, 1.583, .156], [.007, .007, .007], 0x676956, 1, .001);
  const cord: Point[] = [];
  for (let i = 0; i <= 38; i++) {
    const t = i / 38;
    cord.push([x + .016 + .062 * t + .0034 * Math.cos(t * tau * 8), 1.384 + .102 * t + .0029 * Math.sin(t * tau * 8), .145 - .077 * t]);
  }
  wire(g, cord, .0024, 0x373e35, 1, 5);
  block(g, [.137, 1.027, .116], [.084, .103, .045], 0x545443, 0, .009, -.10);
  block(g, [.137, 1.053, .143], [.088, .037, .009], 0x75735a, 0, .004, -.10);
  block(g, [.139, 1.029, .145], [.014, .019, .008], 0xa7a488, 0);
}

const npcPalettes = [
  { coat: 0x758074, shoulder: 0x92978a, cloth: 0x494d42, trouser: 0x545a54, hair: 0x423e35 },
  { coat: 0x637780, shoulder: 0x809196, cloth: 0x414e51, trouser: 0x525559, hair: 0x3b3934 },
  { coat: 0x877c68, shoulder: 0x9c917d, cloth: 0x5b5347, trouser: 0x515747, hair: 0x646052 },
];
function wandererTorso(g: Surface, variant: number) {
  const palette = npcPalettes[variant];
  const lining: Section[] = [[.893, .172, .119, .007], [1.01, .159, .124, .013],
    [1.17, .170, .130, .011], [1.32, .199, .134, .010], [1.419, .177, .115, .004], [1.462, .085, .078, -.003]];
  loft(g, lining, 0x919083, trunkWeight, { count: 24, plate: 'knit', tint: crease });
  const clothWeight = (p: Point): Binding => p[1] < .964
    ? [0, p[0] < 0 ? limbs[0].leg : limbs[1].leg, clamp((.964 - p[1]) * 3.65, 0, .86)]
    : trunkWeight(p);
  const hang = (p: Point, a: number, row: number) => {
    if (row < 3) {
      const strength = (3 - row) / 3;
      p[1] += strength * (.055 * Math.sin(a + variant) - .023 * Math.cos(a * 7 + .4) + .021 * Math.sin(a * 11));
      p[2] += strength * (.013 * Math.cos(a * 7) + .008 * Math.cos(2 * a));
    }
    p[1] += .016 * Math.sin(a) * clamp((p[1] - 1.21) * 5, 0, 1);
  };
  loft(g, npcBody, palette.coat, clothWeight, { count: 34, arc: [Math.PI + .32, Math.PI * 3 - .27], deform: hang, tint: crease });
  const inside = npcBody.slice(0, 6).map(([y, w, d, z]): Section => [y + .001, w - .005, d - .005, z]);
  loft(g, inside, palette.cloth, clothWeight, { count: 34, arc: [Math.PI * 3 - .27, Math.PI + .32], deform: hang, tint: crease });
  const yoke = npcBody.slice(7).map(([y, w, d, z]): Section => [y, w + .004, d + .005, z]);
  loft(g, yoke, palette.shoulder, 1, { count: 28, arc: [Math.PI + .45, Math.PI * 3 - .39],
    deform: (p, a, row) => hang(p, a, row + 7), tint: crease });
  for (const s of sides) {
    panel(g, npcBody, -1, 1.075, 1.423, [s * .082 - .018, s * .081 - .034], [s * .082 + .018, s * .081 + .034],
      palette.shoulder, 1, 'cloth', .009);
    const edge: Point[] = [[s * .071, 1.418, -.10], [s * .077, 1.348, -.132], [s * .072, 1.255, -.138],
      [s * .064, 1.131, -.130], [s * .058, 1.064, -.121]];
    wire(g, edge, .003, palette.cloth, 1);
    panel(g, npcBody, -1, .967, 1.013, [s * .123 - .041, s * .123 - .044], [s * .123 + .037, s * .123 + .040],
      palette.cloth, 0, 'cloth', .013);
  }
  const stitch: Point[] = [];
  for (let i = 0; i <= 12; i++) {
    const x = -.170 + i * .028, y = 1.252 - (1 - Math.abs(x) / .170) * .022;
    stitch.push([x, y, zOn(npcBody, x, y, 1, .009)]);
  }
  wire(g, stitch, .0023, palette.cloth, 1);
  for (const y of [1.08, 1.19, 1.28])
    block(g, [-.081, y, zOn(npcBody, -.081, y, -1, .013)], [.012, .011, .006], 0x8b8a74, 1);
  loft(g, [[1.433, .121, .109, .011], [1.458, .123, .104, .012], [1.505, .093, .094, .007]],
    palette.cloth, 1, { count: 21, arc: [Math.PI + .33, Math.PI * 3 - .52],
      deform: (p, a) => { p[1] += (Math.sin(a) * .023 + .009 * Math.cos(a * 3)) * Math.max(0, (p[1] - 1.433) * 12); } });
  // A salt-streaked repair on one shoulder catches harbour lights at a distance.
  panel(g, npcBody, 1, 1.305, 1.337, [-.179, -.171], [-.086, -.081], 0xb3b3a0, 1, 'cloth', .014);
}

function head(g: Surface, kind: Kind, variant: number) {
  const worker = kind === 'worker', skin = worker ? 0xba9580 : [0xb9b6a3, 0xc4bca5, 0xb6b29b][variant];
  const hair = worker ? 0x413c32 : npcPalettes[variant].hair;
  const cap = worker || variant === 1;
  loft(g, [[1.432, .059, .058, .001], [1.508, .067, .067, -.009], [1.574, .056, .061, -.023]],
    skin, [1, 2, .43], { count: 16, plate: 'cloth' });
  const skull: Section[] = [[1.510, .034, .047, -.049], [1.530, .057, .075, -.042],
    [1.551, .074, .087, -.040], [1.583, .086, .100, -.032], [1.615, .095, .107, -.027],
    [1.643, .099, .110, -.022], [1.674, .098, .113, -.019], [1.710, .092, .107, -.013],
    [1.739, .076, .092, -.010], [1.756, .046, .063, -.009], [1.764, .003, .008, -.006]];
  loft(g, skull, skin, 2, { count: 38, plate: worker ? 'face' : 'sick',
    deform: (p, a, r) => {
      if (r < 4) p[1] += Math.max(0, Math.cos(a)) * .036 * (1 - r / 5);
      if (r === 5) p[2] += .004 * Math.max(0, -Math.cos(a)) * Math.abs(Math.sin(a * 2));
    } });
  for (const s of sides) {
    loft(g, [[1.577, .004, .009, -.001, s * .093], [1.591, .012, .017, -.003, s * .097],
      [1.614, .014, .020, -.007, s * .098], [1.630, .009, .014, -.006, s * .096],
      [1.634, .004, .007, -.006, s * .095]], worker ? 0xb1917b : 0xb0a68f, 2, { count: 12, plate: 'rubber' });
    wire(g, [[s * .108, 1.598, -.010], [s * .110, 1.613, -.013], [s * .107, 1.621, -.007],
      [s * .106, 1.619, .003]], .003, worker ? 0x8c7769 : 0x898772, 2);
    const f = (x: number, y: number, offset: number): Point => [s * x, y, zOn(skull, x, y, -1, offset)];
    const brow = [[.015, 1.647, .0023], [.024, 1.650, .0057], [.039, 1.653, .0053], [.053, 1.652, .0035], [.065, 1.648, .0006]];
    let prev = -1;
    for (const [x, y, h] of brow) {
      const a = g.vertex(f(x, y - h * .48, .0019), hair, 2);
      const b = g.vertex(f(x, y + h * .50, .0024), hair, 2);
      if (prev >= 0) {
        if (s > 0) g.face(prev + 1, b, a, prev);
        else g.face(prev, a, b, prev + 1);
      }
      prev = a;
    }
    const upperLid: Point[] = [], lowerLid: Point[] = [];
    const eyeWidth = .029, eyeMiddle = .038;
    prev = -1;
    for (let i = 0; i <= 8; i++) {
      const t = i / 8, x = eyeMiddle + (t - .5) * eyeWidth, arch = Math.sin(Math.PI * t);
      const center = 1.6347 + .0015 * t;
      const low = f(x, center - arch * .0026, .002),
        high = f(x, center + arch * .0030, .0024);
      upperLid.push(high); lowerLid.push(low);
      const a = g.vertex(low, worker ? 0xaa9e89 : 0xc0bda9, 2);
      const b = g.vertex(high, worker ? 0xb8ad97 : 0xb5b3a2, 2);
      if (prev >= 0) {
        if (s > 0) g.face(prev + 1, b, a, prev);
        else g.face(prev, a, b, prev + 1);
      }
      prev = a;
    }
    wire(g, upperLid, .0012, worker ? 0x746457 : 0x79766a, 2, 5);
    wire(g, lowerLid.slice(1, -1), .0008, worker ? 0xac927c : 0xa29e8b, 2, 5);
    const iris: number[] = [];
    for (let k = 0; k < 12; k++) {
      const a = k * tau / 12;
      iris.push(g.vertex(f(eyeMiddle + .0036 * Math.cos(a), 1.6354 + .00275 * Math.sin(a), .0033),
        worker ? 0x4c493b : 0x66685b, 2));
    }
    const pupil = g.vertex(f(eyeMiddle, 1.6354, .0041), 0x393b32, 2);
    for (let k = 0; k < 12; k++) {
      const next = (k + 1) % 12;
      g.indices.push(pupil, iris[s > 0 ? next : k], iris[s > 0 ? k : next]);
    }
  }
  const nose: Point[] = [[0, 1.650, -.132], [-.011, 1.621, -.139], [-.017, 1.600, -.142],
    [-.009, 1.597, -.146], [0, 1.602, -.157], [.009, 1.597, -.146], [.017, 1.600, -.142], [.011, 1.621, -.139]];
  const ni = nose.map(p => g.vertex(p, skin, 2));
  for (const [a, b, c] of [[0, 4, 1], [1, 4, 2], [2, 4, 3], [0, 7, 4], [7, 6, 4], [6, 5, 4], [3, 4, 5]])
    g.indices.push(ni[a], ni[b], ni[c]);
  const mouth: Point[] = [[-.028, 1.574, -.126], [-.014, 1.575, -.131], [0, 1.574, -.133],
    [.015, 1.575, -.131], [.027, 1.573, -.126]];
  wire(g, mouth, .002, worker ? 0x947b6a : 0x898578, 2);
  const hairline = (p: Point, a: number, row: number) => {
    if (row === 0) p[1] += .060 * (1 - Math.cos(a)) / 2 + .006 * Math.cos(a * 7 + .7);
    if (!cap && row >= 2) {
      p[0] += .005 * Math.sin(a * 3 + row * .72); p[1] += Math.cos(a * 5 - row * .49) * .004;
    }
  };
  loft(g, [[1.591, .089, .102, -.012], [1.664, .100, .115, -.015], [1.712, .094, .111, -.013],
    [1.744, .077, .095, -.010], [1.761, .049, .068, -.01], [1.770, .002, .006, -.011]],
    hair, 2, { count: 34, plate: 'knit', deform: hairline, tint: crease });
  if (!cap) {
    const random = seeded(24 + variant);
    for (let i = 0; i < 32; i++) {
      const a = i / 32 * tau, dx = Math.sin(a), dz = Math.cos(a), front = (1 - dz) / 2;
      const y = 1.602 + front * .064 + random() * .010;
      const root: Point = [dx * .095, y + .024, -.015 + dz * .110];
      const a0 = g.vertex([root[0] - .009 * dz, root[1], root[2] + .009 * dx], hair, 2);
      const b0 = g.vertex([root[0] + .009 * dz, root[1], root[2] - .009 * dx], hair, 2);
      const c0 = g.vertex([dx * .094 + .009 * dz, y - random() * .026, -.012 + dz * .110], hair, 2);
      g.indices.push(b0, a0, c0);
    }
    for (let k = 0; k < 6; k++) {
      const a = 2.68 + k * .119 + .035 * Math.sin(k * 9);
      const left = a - .058, right = a + .072;
      const rootY = 1.686 + .012 * Math.cos(k * .8);
      const tipAngle = a + .10, tipY = rootY - .027 - .019 * Math.sin(k * 2.24) ** 2;
      const leftId = g.vertex([Math.sin(left) * .099, rootY, -.018 + Math.cos(left) * .115], hair, 2);
      const rightId = g.vertex([Math.sin(right) * .099, rootY, -.018 + Math.cos(right) * .115], hair, 2);
      const tipId = g.vertex([Math.sin(tipAngle) * .099, tipY, -.021 + Math.cos(tipAngle) * .116], hair, 2);
      g.indices.push(rightId, leftId, tipId);
    }
    return;
  }
  const capTone = worker ? 0x485250 : 0x5d655e;
  const capTilt = (p: Point, a: number, row: number) => { p[1] -= (.014 * Math.cos(a) - .004 * Math.sin(a)) * Math.max(0, 1 - row / 7); };
  const hat: Section[] = [[1.639, .095, .105, -.009], [1.646, .103, .114, -.009], [1.665, .108, .120, -.008],
    [1.692, .107, .118, -.007], [1.721, .099, .115, -.003], [1.749, .090, .103, .002],
    [1.769, .070, .083, .007], [1.786, .036, .047, .013], [1.790, .005, .008, .014]];
  loft(g, hat, capTone, 2, { count: 40, plate: 'knit', deform: capTilt, tint: crease });
  loft(g, [[1.635, .097, .108, -.009], [1.641, .105, .115, -.009], [1.648, .110, .120, -.008],
    [1.674, .111, .123, -.008], [1.681, .108, .120, -.008]],
    worker ? 0x565d55 : 0x626353, 2, { count: 48, plate: 'knit', deform: capTilt, tint: crease });
  for (const a of [-1.77, -.28, 1.21, 2.68]) {
    const points = hat.slice(3, -1).map(([y, w, d, z], i): Point => {
      const t = a + i * .092;
      return [Math.sin(t) * (w + .001), y - .005 * Math.cos(t), (z ?? 0) + Math.cos(t) * (d + .001)];
    });
    wire(g, points, .00155, worker ? 0x67706a : 0x737669, 2);
  }
  if (worker) {
    block(g, [.048, 1.649, .103], [.023, .023, .004], 0xa3956f, 2, .001, -.13);
    block(g, [.048, 1.651, .106], [.012, .003, .002], 0x524f40, 2, .0004);
  }
}

function leg(g: Surface, limb: Limb, kind: Kind, variant: number) {
  const worker = kind === 'worker', s = limb.sign;
  const rows: Section[] = [[.137, .053, .057, .018, s * .112], [.179, .061, .064, .018, s * .112],
    [.204, .066, .070, .016, s * .111], [.226, .063, .062, .011, s * .111],
    [.254, .073, .071, .008, s * .110], [.289, .068, .069, .002, s * .110],
    [.376, .076, .080, .002, s * .109], [.451, .073, .077, -.007, s * .107],
    [.481, .076, .078, -.014, s * .106], [.508, .080, .084, -.018, s * .106],
    [.534, .078, .080, -.018, s * .106], [.562, .085, .085, -.015, s * .105],
    [.641, .092, .103, -.006, s * .103], [.730, .099, .114, .002, s * .101],
    [.816, .104, .122, .008, s * .099], [.898, .103, .124, .014, s * .096], [.954, .088, .105, .018, s * .096]];
  const bind = (p: Point): Binding => [limb.shin, limb.leg, clamp((p[1] - .474) / .091, 0, 1)];
  const trouser = worker ? 0x4c5650 : npcPalettes[variant].trouser;
  loft(g, rows, trouser, bind, { count: 20, tint: crease, deform: (p, a, i) => {
    const fold = (i > 1 && i < 6) || (i > 7 && i < 12);
    if (fold) p[1] += .009 * Math.cos(a + i * .59);
  } });
  for (const [first, last, joint] of [[2, 8, limb.shin], [11, 15, limb.leg]]) {
    const seam = rows.slice(first, last + 1).map(([y, w, , z, x]): Point => [(x ?? 0) + s * (w - .001), y, (z ?? 0) + .004]);
    wire(g, seam, .0018, worker ? 0x73786a : 0x73766a, joint, 5);
  }
  const bx = s * .112;
  const boot = (y: number, w: number, d: number, z: number): Section => [y, w, d, z, bx];
  const bootColor = worker ? 0x3d423a : 0x464940;
  loft(g, [boot(.012, .066, .130, -.033), boot(.021, .072, .143, -.038), boot(.042, .072, .143, -.038),
    boot(.052, .068, .139, -.036)], 0x323932, limb.foot, { count: 20, power: .71, plate: 'rubber' });
  const center = g.vertex([bx, .0121, -.033], 0x353930, limb.foot);
  const perimeter: number[] = [];
  for (let i = 0; i < 20; i++) {
    const sn = Math.sin(i * tau / 20), cs = Math.cos(i * tau / 20);
    perimeter.push(g.vertex([bx + Math.sign(sn) * Math.abs(sn) ** .71 * .066, .012, -.033 + Math.sign(cs) * Math.abs(cs) ** .71 * .130],
      0x353930, limb.foot));
  }
  for (let i = 0; i < 20; i++) g.indices.push(center, perimeter[(i + 1) % 20], perimeter[i]);
  loft(g, [boot(.047, .069, .140, -.037), boot(.058, .071, .141, -.037), boot(.067, .068, .137, -.034)],
    worker ? 0x555a50 : 0x585a4f, limb.foot, { count: 20, power: .71, plate: 'rubber' });
  loft(g, [boot(.061, .069, .138, -.035), boot(.079, .067, .126, -.029), boot(.097, .064, .112, -.018),
    boot(.120, .059, .090, -.004), boot(.148, .053, .069, .013), boot(.183, .054, .064, .020),
    boot(.216, .061, .068, .019), boot(.228, .060, .066, .018)],
    bootColor, limb.foot, { count: 20, power: .82, plate: 'rubber', tint: crease });
  loft(g, [boot(.210, .061, .067, .019), boot(.216, .064, .072, .019), boot(.226, .064, .071, .019),
    boot(.231, .059, .065, .019)], 0x565b50, limb.foot, { count: 16, plate: 'rubber' });
  wire(g, [[bx - .054, .077, -.101], [bx - .030, .091, -.113], [bx, .096, -.117],
    [bx + .030, .091, -.113], [bx + .054, .077, -.101]], .0022, 0x626357, limb.foot, 5);
  if (worker) {
    for (let i = 0; i < 4; i++) {
      const z = -.077 + i * .012, y = .108 + i * .011;
      wire(g, [[bx - .024, y, z], [bx, y + .006, z + .001], [bx + .024, y + .001, z + .003]], .0028, 0x333a33, limb.foot, 5);
    }
  }
}

function arm(g: Surface, l: Limb, kind: Kind, variant: number) {
  const worker = kind === 'worker', s = l.sign, short = !worker && s === (variant === 1 ? 1 : -1);
  const skin = worker ? 0x484d41 : [0xa7a394, 0xb2a994, 0xaaa394][variant];
  const bind = (p: Point): Binding => [l.fore, l.arm, clamp((p[1] - 1.071) / .079, 0, 1)];
  const sleeve = (y: number, w: number, d: number, z: number, x: number): Section => [y, w, d, z, s * x];
  const rows: Section[] = [
    sleeve(.867, .049, .048, -.021, .293), sleeve(.880, .058, .055, -.019, .291), sleeve(.899, .063, .062, -.016, .290),
    sleeve(.920, .060, .058, -.015, .290), sleeve(.954, .068, .067, -.014, .288), sleeve(1.020, .072, .071, -.010, .282),
    sleeve(1.066, .073, .074, -.008, .278), sleeve(1.091, .069, .070, -.006, .276), sleeve(1.112, .079, .077, -.004, .273),
    sleeve(1.139, .074, .073, -.004, .269), sleeve(1.174, .081, .081, -.003, .265), sleeve(1.251, .084, .088, -.002, .254),
    sleeve(1.330, .091, .092, -.001, .242), sleeve(1.377, .092, .091, .000, .231), sleeve(1.413, .073, .076, .001, .222),
    sleeve(1.440, .042, .044, .002, .213), sleeve(1.446, .010, .014, .004, .209),
  ];
  if (short) {
    loft(g, [sleeve(.852, .030, .033, -.019, .292), sleeve(.905, .036, .043, -.015, .290),
      sleeve(.984, .047, .049, -.013, .285), sleeve(1.045, .054, .052, -.008, .280),
      sleeve(1.119, .046, .044, -.005, .272)], skin, bind, { count: 16, plate: 'rubber', tint: crease });
  }
  loft(g, short ? rows.slice(6) : rows, worker ? 0xc18a3c : npcPalettes[variant].coat, bind, { count: 22, tint: crease,
    deform: (p, a, r) => { p[1] += (short && r < 2 ? .016 : .0045) * Math.cos(a * (short && r === 0 ? 5 : 2) + r * .72); } });
  if (worker) {
    const shoulderBand = (lo: number, hi: number, color: number, scale: number) =>
      loft(g, [sleeve(lo, .084 * scale, .087 * scale, -.002, .256), sleeve(hi, .085 * scale, .089 * scale, -.002, .253)],
        color, l.arm, { count: 22, tint: crease });
    shoulderBand(1.229, 1.264, 0x756d47, 1.038);
    shoulderBand(1.235, 1.258, 0xc6c9ad, 1.054);
    const shoulderRows = rows.slice(12);
    loft(g, shoulderRows.map(([y, w, d, z, x]): Section => [y, w + .0015, d + .002, z, x]),
      0xb78036, l.arm, { count: 20, arc: [s * 1.42 - .87, s * 1.42 + .87], tint: crease });
    const first = g.positions.length / 3, cols = 10;
    for (let row = 0; row <= 4; row++) {
      const v = row / 4, y = 1.281 + v * .041;
      const x = s * mix(.254, .242, (y - 1.251) / .079);
      const [w, d, z] = crossSection(rows, y);
      for (let j = 0; j <= cols; j++) {
        const a = s * 1.23 + (j / cols - .5) * 1.06;
        g.vertex([x + (w + .0034) * Math.sin(a), y, z + (d + .0034) * Math.cos(a)],
          0xf9f6e9, l.arm, 'tag', j / cols, v);
        if (row && j) { const n = first + row * (cols + 1) + j; g.face(n - cols - 2, n - cols - 1, n, n - 1); }
      }
    }
    loft(g, [sleeve(.852, .043, .043, -.021, .293), sleeve(.865, .053, .051, -.021, .293),
      sleeve(.882, .054, .054, -.019, .291)], 0x545642, l.fore, { count: 18, plate: 'knit' });
    const seam: Point[] = [[s * .305, 1.373, .048], [s * .323, 1.315, .048], [s * .331, 1.253, .040], [s * .340, 1.177, .025]];
    wire(g, seam, .0022, 0xd9a75c, l.arm);
    wire(g, [[s * .339, 1.075, .03], [s * .348, 1.012, .021], [s * .346, .942, .014], [s * .342, .890, .012]],
      .0021, 0x9d773b, l.fore);
  }
  const hx = s * .294;
  const palm = (y: number, w: number, d: number, z: number, dx = 0): Section => [y, w, d, z, hx + s * dx];
  // The narrow palm is side-on in the resting pose. Four separately shaped fingers curl inwards.
  loft(g, [palm(.748, .018, .026, -.023), palm(.763, .024, .039, -.027),
    palm(.791, .029, .046, -.027), palm(.817, .027, .039, -.025), palm(.843, .023, .029, -.022),
    palm(.873, .028, .031, -.020)], skin, l.hand, { count: 16, plate: worker ? 'rubber' : 'cloth', tint: crease });
  for (let j = 0; j < 4; j++) {
    const z = -.054 + j * .0195, end = .731 + Math.abs(j - 1) * .006;
    loft(g, [palm(end, .003, .004, z + .004, -.015), palm(end + .007, .009, .008, z + .002, -.016),
      palm(.748 + Math.abs(j - 1) * .003, .010, .009, z, -.008), palm(.771, .011, .010, z)],
      worker ? 0x444a40 : skin, l.hand, { count: 8, plate: 'rubber' });
  }
  wire(g, [[hx - s * .005, .815, -.053], [hx - s * .014, .799, -.067], [hx - s * .023, .779, -.067],
    [hx - s * .027, .770, -.059]], worker ? .0115 : .0105, skin, l.hand, 9);
  if (worker) {
    for (let i = 0; i < 3; i++) {
      const z = -.046 + .017 * i;
      wire(g, [[hx + s * .024, .770, z], [hx + s * .029, .795, z], [hx + s * .022, .821, z + .004]],
        .0014, 0x66695b, l.hand, 5);
    }
  }
}

let sharedMaterial: THREE.MeshStandardMaterial | undefined;
const bodies = new Map<string, THREE.BufferGeometry>();
let propGeometry: THREE.BufferGeometry | undefined;
function bodyGeometry(kind: Kind, variant: number) {
  const key = `${kind}-${variant}`;
  const existing = bodies.get(key);
  if (existing) return existing;
  const g = new Surface();
  if (kind === 'worker') workerTorso(g);
  else wandererTorso(g, variant);
  head(g, kind, variant);
  for (const limb of limbs) { leg(g, limb, kind, variant); arm(g, limb, kind, variant); }
  const geometry = g.finish();
  geometry.name = key;
  bodies.set(key, geometry);
  return geometry;
}

function sidearm(material: THREE.Material) {
  if (!propGeometry) {
    const g = new Surface();
    block(g, [0, .002, .010], [.027, .064, .032], 0x44483f, 0, .006);
    block(g, [0, .028, -.038], [.032, .027, .137], 0x606761, 0, .004);
    block(g, [0, .013, -.021], [.029, .020, .095], 0x454b44, 0, .004);
    block(g, [0, .029, -.107], [.027, .020, .004], 0x363d38, 0, .002);
    propGeometry = g.finish(false);
  }
  const prop = new THREE.Mesh(propGeometry, material);
  prop.name = 'held-sidearm';
  prop.position.set(-.012, -.068, -.026);
  prop.rotation.x = -Math.PI / 2;
  prop.castShadow = true;
  const tip = new THREE.Object3D();
  tip.name = 'sidearm-muzzle'; tip.position.set(0, .028, -.111); prop.add(tip);
  return prop;
}

function skeleton() {
  const bones = jointPoints.map(() => new THREE.Bone());
  const jointNames = ['hips', 'chest', 'head', ...['left', 'right'].flatMap(s =>
    ['shoulder', 'elbow', 'wrist', 'hip', 'knee', 'ankle'].map(j => `${s}-${j}`))];
  bones.forEach((bone, i) => {
    bone.name = jointNames[i];
    bone.position.fromArray(jointPoints[i]);
    const parent = parents[i];
    if (parent >= 0) {
      const [x, y, z] = jointPoints[parent];
      bone.position.x -= x; bone.position.y -= y; bone.position.z -= z;
      bones[parent].add(bone);
    }
  });
  return bones;
}

// Inverse kinematics is evaluated once in the bind-pose chest frame. The hands converge
// on the same point so the support hand stays at the grip throughout the aim transition.
function aimTargets(l: Limb, bones: THREE.Bone[]) {
  const s = l.sign;
  const upperBind = bones[l.fore].position.clone(), lowerBind = bones[l.hand].position.clone();
  const upperLength = upperBind.length(), lowerLength = lowerBind.length();
  const target = s > 0 ? new THREE.Vector3(-.120, -.043, -.478) : new THREE.Vector3(.263, -.097, -.440);
  const direction = target.clone().normalize(), distance = target.length();
  const pole = new THREE.Vector3(s * .13, -.32, -.12);
  pole.addScaledVector(direction, -pole.dot(direction)).normalize();
  const along = (upperLength ** 2 - lowerLength ** 2 + distance ** 2) / (2 * distance);
  const elbow = direction.multiplyScalar(along).addScaledVector(pole, Math.sqrt(Math.max(0, upperLength ** 2 - along ** 2)));
  const upper = new THREE.Quaternion().setFromUnitVectors(upperBind.normalize(), elbow.clone().normalize());
  const fore = new THREE.Quaternion().setFromUnitVectors(lowerBind.normalize(),
    target.sub(elbow).normalize().applyQuaternion(upper.clone().invert()));
  const grip = s > 0 ? new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2) :
    new THREE.Quaternion().setFromEuler(new THREE.Euler(1.28, -.51, -.28, 'YXZ'));
  const hand = upper.clone().multiply(fore).invert().multiply(grip);
  return { upper, fore, hand };
}

export function createCharacter(kind: Kind, variant = 0) {
  const worker = kind === 'worker';
  const v = worker ? 0 : ((Math.trunc(variant) % 3) + 3) % 3;
  if (!sharedMaterial) {
    const atlas = makeAtlas();
    sharedMaterial = new THREE.MeshStandardMaterial({ map: atlas, bumpMap: atlas, bumpScale: .00065,
      vertexColors: true, roughness: .72, metalness: .055, emissive: 0x060807 });
    sharedMaterial.name = '濡れた油布と港の道具';
  }
  const root = new THREE.Group(), rig = new THREE.Group(), bones = skeleton();
  root.name = worker ? '港務作業員・七番' : `濡れた人影・${v + 1}`;
  root.add(rig);
  const skin = new THREE.SkinnedMesh(bodyGeometry(kind, v), sharedMaterial);
  skin.name = worker ? 'oilskin-worker' : 'dock-wanderer';
  skin.add(bones[0]); rig.add(skin);
  skin.bind(new THREE.Skeleton(bones));
  skin.castShadow = true; skin.receiveShadow = true;
  skin.boundingSphere = new THREE.Sphere(new THREE.Vector3(0, .90, -.10), 1.18);
  rig.scale.set(worker ? .90 : [.87, .92, .88][v], worker ? 1 : [1.00, .975, 1.035][v], 1);
  const prop = worker ? sidearm(sharedMaterial) : null;
  if (prop) { prop.visible = false; bones[limbs[1].hand].add(prop); }
  const targetAngles = worker ? limbs.map(l => aimTargets(l, bones)) : [];
  let stride = worker ? 0 : variant * 1.73, movement = 0, sight = 0;
  const staggerSide = v === 1 ? -1 : 1;

  function pose(dt: number, speed: number, aim: boolean, armed: boolean, fallen: number, time: number) {
    const step = clamp(dt, 0, .10), down = clamp(fallen, 0, 1), live = 1 - down;
    const pace = clamp(Math.abs(speed), 0, 3.5);
    movement = THREE.MathUtils.damp(movement, Math.min(1, pace * 1.45), 12, step);
    sight = THREE.MathUtils.damp(sight, worker && aim && armed ? 1 : 0, 13, step);
    const gait = movement * live;
    stride += step * gait * (worker ? 5.6 + pace * 1.17 : 4.9 + pace * 1.16);
    const swing = Math.sin(stride), double = Math.cos(2 * stride);
    const breath = Math.sin(time * (worker ? 1.71 : 2.05) + v * 2.4) * live;
    const easeFall = down * down * (3 - 2 * down);
    const lean = worker ? -.033 - .034 * gait : -.197 - .029 * v - .035 * gait;
    const fallSide = worker ? -1 : staggerSide;
    rig.rotation.set(easeFall * 1.55, fallSide * easeFall * .26, fallSide * easeFall * .12);
    rig.position.set(fallSide * .11 * down, .211 * easeFall - .015 * Math.sin(Math.PI * down), -.15 * easeFall);
    const hips = bones[0], chest = bones[1], skull = bones[2];
    hips.position.y = jointPoints[0][1] + (.022 * double - .024) * gait + .0021 * breath;
    hips.rotation.set((worker ? -.015 : -.045) * (1 - sight), -.060 * swing * gait * (1 - sight),
      ((worker ? .020 : .039) * swing * gait + (worker ? 0 : staggerSide * .019)) * (1 - sight));
    chest.rotation.set((lean - .006 * breath) * (1 - sight) * live - .20 * Math.sin(Math.PI * down),
      .074 * swing * gait * (1 - sight), ((worker ? -.008 : -.065 * staggerSide) + .015 * swing * gait) * (1 - sight) * live);
    skull.rotation.set((worker ? .025 : -.133) + .011 * breath - .016 * double * gait,
      (worker ? .032 : .085) * Math.sin(time * .62 + v) * (1 - sight) * live,
      (worker ? .008 : .125 * staggerSide) + (worker ? .007 : .035) * Math.sin(time * .91 + v) * live - .09 * down);
    const strideSize = worker ? .31 + pace * .077 : .29 + pace * .063;
    limbs.forEach((l, i) => {
      const s = l.sign, wave = swing * s, phase = stride + (s < 0 ? Math.PI : 0);
      const drag = worker ? 1 : s === staggerSide ? .66 : 1.13;
      const thigh = bones[l.leg], shin = bones[l.shin], foot = bones[l.foot];
      const upper = bones[l.arm], fore = bones[l.fore], hand = bones[l.hand];
      thigh.rotation.set(mix((worker ? .025 : .115) + wave * strideSize * gait * drag, i ? .34 : .14, down),
        s * (worker ? .018 : .048), s * (.015 + down * (i ? .18 : .07)));
      shin.rotation.x = mix((worker ? -.050 : -.145) - .64 * Math.max(0, -Math.cos(phase)) * gait * drag, i ? -.55 : -.25, down);
      foot.rotation.set(-.30 * thigh.rotation.x - .47 * shin.rotation.x - .032, -s * (worker ? .055 : .10), 0);
      if (worker) {
        upper.rotation.set(.064 - wave * (.255 + .034 * pace) * gait, -s * .052, s * (.023 + .014 * breath));
        fore.rotation.set(.192 + .12 * gait + .086 * Math.max(0, wave) * gait, s * .032, -s * .04);
        hand.rotation.set(.032, -s * .110, s * .052);
        if (s > 0 && armed) { upper.rotation.x += .11; fore.rotation.x += .17; }
        if (sight > .0001) {
          upper.quaternion.slerp(targetAngles[i].upper, sight * live);
          fore.quaternion.slerp(targetAngles[i].fore, sight * live);
          hand.quaternion.slerp(targetAngles[i].hand, sight * live);
        }
      } else {
        upper.rotation.set((s === staggerSide ? .37 : -.045) - wave * .23 * gait + .03 * breath,
          s * -.102, s * (.058 + .035 * Math.sin(time * .8 + i)));
        fore.rotation.set((s === staggerSide ? .28 : .121) + .091 * Math.max(0, wave) * gait, s * .055, -s * .042);
        hand.rotation.set(-.076 + .025 * breath, -s * .16, s * .102);
      }
      if (down > 0) {
        upper.rotation.x = mix(upper.rotation.x, i ? .14 : .23, down);
        upper.rotation.z = mix(upper.rotation.z, s * (i ? .35 : .56), down);
        fore.rotation.x = mix(fore.rotation.x, i ? .20 : .34, down);
      }
    });
    if (prop) prop.visible = armed;
  }
  pose(0, 0, false, false, 0, 0);
  return { root, pose };
}
