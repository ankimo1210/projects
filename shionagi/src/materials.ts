import * as T from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

export function random(seed: number) {
  let n = seed >>> 0;
  return () => {
    n = (Math.imul(n, 1664525) + 1013904223) >>> 0;
    return n / 4294967296;
  };
}

export function canvasTexture(w: number, h: number, paint: (ctx: CanvasRenderingContext2D) => void) {
  const canvas = document.createElement('canvas');
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext('2d')!;
  paint(ctx);
  const tex = new T.CanvasTexture(canvas);
  tex.colorSpace = T.SRGBColorSpace;
  tex.anisotropy = 4;
  return tex;
}

type Finish = 'concrete' | 'metal' | 'shutter' | 'tile' | 'wood';
const masonry = new Image();
masonry.src = import.meta.env.BASE_URL + 'art/port-concrete.webp';
function weatherConcrete(tex: T.CanvasTexture) {
  const apply = () => {
    const canvas = tex.image as HTMLCanvasElement,
      c = canvas.getContext('2d')!;
    c.save();
    c.globalCompositeOperation = 'soft-light';
    c.globalAlpha = 0.95;
    c.drawImage(masonry, 0, 0, canvas.width, canvas.height);
    c.restore();
    tex.needsUpdate = true;
  };
  if (masonry.complete && masonry.naturalWidth) apply();
  else masonry.addEventListener('load', apply, { once: true });
}
const surfaces = new Map<string, T.MeshStandardMaterial>();
export function surface(color: string, kind: Finish = 'concrete') {
  const key = kind + color;
  if (surfaces.has(key)) return surfaces.get(key)!;
  const seed = parseInt(color.replace('#', ''), 16);
  const rand = random(seed);
  const tex = canvasTexture(256, 256, (ctx) => {
    ctx.fillStyle = color;
    ctx.fillRect(0, 0, 256, 256);
    const img = ctx.getImageData(0, 0, 256, 256);
    const stripes = Array.from({ length: 256 }, () => rand() * 3);
    for (let y = 0; y < 256; y++)
      for (let x = 0; x < 256; x++) {
        const i = (x + y * 256) * 4;
        const noise = (rand() - 0.5) * (kind === 'concrete' ? 36 : 18) + stripes[x];
        for (let c = 0; c < 3; c++) img.data[i + c] += noise;
      }
    ctx.putImageData(img, 0, 0);
    for (let i = 0; i < 170; i++) {
      const x = rand() * 256,
        y = rand() * 256,
        h = 5 + rand() ** 2 * 128;
      const grad = ctx.createLinearGradient(0, y, 0, y + h);
      grad.addColorStop(0, i % 5 ? 'rgba(9,19,17,.19)' : 'rgba(201,177,126,.2)');
      grad.addColorStop(1, 'rgba(60,57,45,0)');
      ctx.fillStyle = grad;
      ctx.fillRect(x, y, rand() ** 2 * 11 + 0.4, h);
    }
    if (kind === 'shutter' || kind === 'wood') {
      const step = kind === 'shutter' ? 11 : 44;
      for (let y = 0; y < 256; y += step) {
        ctx.fillStyle = 'rgba(0,6,7,.55)';
        ctx.fillRect(0, y, 256, 2);
        ctx.fillStyle = 'rgba(198,211,197,.30)';
        ctx.fillRect(0, y + 2, 256, 1.4);
      }
    }
    if (kind === 'tile') {
      for (let i = 0; i < 256; i += 64) {
        ctx.fillStyle = '#293c3b';
        ctx.fillRect(i, 0, 2, 256);
        ctx.fillRect(0, i, 256, 2);
        ctx.fillStyle = '#98ada0';
        ctx.fillRect(i + 2, 0, 1, 256);
      }
    }
    if (kind === 'concrete') {
      for (let j = 0; j < 8; j++) {
        let x = rand() * 256,
          y = rand() * 256;
        ctx.beginPath();
        ctx.moveTo(x, y);
        for (let i = 0; i < 4; i++) {
          x += (rand() - 0.47) * 23;
          y += rand() * 13;
          ctx.lineTo(x, y);
        }
        ctx.strokeStyle = 'rgba(19,32,32,.21)';
        ctx.lineWidth = 0.7;
        ctx.stroke();
      }
    }
  });
  if (kind === 'concrete') weatherConcrete(tex);
  tex.wrapS = tex.wrapT = T.RepeatWrapping;
  const material = new T.MeshStandardMaterial({
    map: tex,
    bumpMap: tex,
    bumpScale: kind === 'concrete' ? 0.055 : 0.025,
    metalness: kind === 'metal' || kind === 'shutter' ? 0.38 : 0.09,
    roughness: kind === 'tile' ? 0.42 : kind === 'metal' ? 0.47 : 0.76,
  });
  material.userData.tile = kind === 'tile' ? 1.45 : 2.6;
  surfaces.set(key, material);
  return material;
}

const plainMats = new Map<string, T.Material>();
export function plain(color: string, glow = false) {
  const key = color + glow;
  if (!plainMats.has(key))
    plainMats.set(
      key,
      glow
        ? new T.MeshBasicMaterial({ color, toneMapped: false })
        : new T.MeshStandardMaterial({ color, roughness: 0.54, metalness: 0.24 }),
    );
  return plainMats.get(key)!;
}

const up = new T.Vector3(0, 1, 0);
export class Builder {
  private batches = new Map<string, { mat: T.Material; items: T.BufferGeometry[] }>();
  constructor(readonly root: T.Group) {}
  add(geom: T.BufferGeometry, mat: T.Material, x: number, y: number, z: number, rot = new T.Euler()) {
    geom.applyMatrix4(
      new T.Matrix4().compose(
        new T.Vector3(x, y, z),
        new T.Quaternion().setFromEuler(rot),
        new T.Vector3(1, 1, 1),
      ),
    );
    const key = mat.uuid + '_' + Math.floor(z / 26);
    let batch = this.batches.get(key);
    if (!batch) {
      batch = { mat, items: [] };
      this.batches.set(key, batch);
    }
    const item = geom.index ? geom.toNonIndexed() : geom;
    if (item !== geom) geom.dispose();
    batch.items.push(item);
  }
  box(x: number, y: number, z: number, w: number, h: number, d: number, mat: T.Material, ry = 0) {
    const g = new T.BoxGeometry(w, h, d);
    if (mat.userData.tile) {
      const uv = g.attributes.uv,
        tile = mat.userData.tile as number;
      for (let i = 0; i < 24; i++) {
        const face = Math.floor(i / 4);
        uv.setXY(
          i,
          (uv.getX(i) * (face < 2 ? d : w)) / tile,
          (uv.getY(i) * (face < 2 || face > 3 ? h : d)) / tile,
        );
      }
    }
    this.add(g, mat, x, y, z, new T.Euler(0, ry, 0));
  }
  tube(a: number[], b: number[], r: number, mat: T.Material, n = 8) {
    const start = new T.Vector3(a[0], a[1], a[2]),
      delta = new T.Vector3(b[0], b[1], b[2]).sub(start);
    if (delta.lengthSq() < 0.00001) return;
    const mid = start.addScaledVector(delta, 0.5);
    const g = new T.CylinderGeometry(r, r, delta.length(), n);
    this.add(
      g,
      mat,
      mid.x,
      mid.y,
      mid.z,
      new T.Euler().setFromQuaternion(new T.Quaternion().setFromUnitVectors(up, delta.normalize())),
    );
  }
  board(x: number, y: number, z: number, w: number, h: number, mat: T.Material, ry = 0) {
    this.add(new T.PlaneGeometry(w, h), mat, x, y, z, new T.Euler(0, ry, 0));
  }
  finish() {
    for (const { mat, items } of this.batches.values()) {
      const g = mergeGeometries(items);
      if (g) {
        g.computeBoundingSphere();
        this.root.add(new T.Mesh(g, mat));
      }
      for (const item of items) item.dispose();
    }
    this.batches.clear();
  }
}

export const paint = {
  structure: surface('#64706c'),
  soffit: surface('#4e5653'),
  metal: surface('#536363', 'metal'),
  dark: surface('#2c383a', 'metal'),
  cream: surface('#bec0a6', 'metal'),
  blue: surface('#386464', 'metal'),
  yellow: surface('#b18b47', 'metal'),
  rust: surface('#815744', 'metal'),
  tile: surface('#66847f', 'tile'),
  rubber: plain('#1a2427'),
  warm: plain('#ffe3a2', true),
  amber: plain('#ffab4d', true),
  aqua: plain('#c2f3de', true),
};

const signs = new Map<string, T.Material>();
export function signTexture(
  key: string,
  w: number,
  h: number,
  draw: (c: CanvasRenderingContext2D) => void,
  lit = 0.25,
) {
  if (signs.has(key)) return signs.get(key)!;
  const tex = canvasTexture(w, h, (c) => {
    draw(c);
    const rng = random([...key].reduce((a, b) => a + b.charCodeAt(0), 610));
    for (let n = 0; n < Math.floor((w * h) / 76); n++) {
      c.fillStyle = rng() > 0.58 ? 'rgba(223,217,177,.11)' : 'rgba(16,28,30,.15)';
      c.fillRect(rng() * w, rng() * h, 0.5 + rng() * 2, 0.5 + rng() * 3);
    }
  });
  const mat = new T.MeshStandardMaterial({
    map: tex,
    emissive: 0xffffff,
    emissiveMap: tex,
    emissiveIntensity: lit,
    side: T.DoubleSide,
    roughness: 0.58,
    metalness: 0.12,
  });
  signs.set(key, mat);
  return mat;
}

export function lettering(
  c: CanvasRenderingContext2D,
  label: string,
  x: number,
  y: number,
  size: number,
  ink: string,
  weight = 700,
  mono = false,
) {
  c.fillStyle = ink;
  c.textBaseline = 'middle';
  c.font =
    weight +
    ' ' +
    size +
    'px ' +
    (mono ? '"Arial", sans-serif' : '"Yu Gothic","Meiryo","Droid Sans Fallback",sans-serif');
  c.fillText(label, x, y);
}

export function direction(
  label: string,
  en: string,
  code: string,
  arrow: string,
  bg = '#183b3a',
  ink = '#e4e9ce',
) {
  return signTexture(
    [label, en, code, arrow, bg].join('|'),
    800,
    190,
    (c) => {
      c.fillStyle = bg;
      c.fillRect(0, 0, 800, 190);
      c.fillStyle = '#132626';
      c.fillRect(0, 0, 800, 7);
      c.fillRect(0, 181, 800, 9);
      c.fillStyle = ink;
      c.fillRect(14, 16, 4, 155);
      lettering(c, code, 34, 91, 84, ink, 700, true);
      c.globalAlpha = 0.55;
      c.fillRect(172, 28, 2, 135);
      c.globalAlpha = 1;
      lettering(c, label, 198, 74, 57, ink);
      lettering(c, en, 201, 139, 24, ink, 600, true);
      lettering(c, arrow, 684, 95, 82, ink, 600);
      for (const x of [13, 784])
        for (const y of [13, 177]) {
          c.fillStyle = '#89978b';
          c.fillRect(x, y, 3, 3);
        }
    },
    0.57,
  );
}

export function nameplate(jp: string, en: string, bg = '#3a5050', fg = '#dfdec4') {
  return signTexture(
    jp + en + bg,
    600,
    160,
    (c) => {
      c.fillStyle = bg;
      c.fillRect(0, 0, 600, 160);
      c.strokeStyle = fg;
      c.lineWidth = 2;
      c.strokeRect(9, 9, 582, 142);
      c.textAlign = 'center';
      lettering(c, jp, 300, 65, Math.min(64, 505 / jp.length), fg);
      lettering(c, en, 300, 121, 21, fg, 500, true);
      c.textAlign = 'left';
    },
    0.26,
  );
}

const haloMap = canvasTexture(96, 96, (c) => {
  const g = c.createRadialGradient(48, 48, 1, 48, 48, 47);
  g.addColorStop(0, 'rgba(255,255,255,.95)');
  g.addColorStop(0.1, 'rgba(255,255,255,.53)');
  g.addColorStop(0.32, 'rgba(255,255,255,.18)');
  g.addColorStop(0.67, 'rgba(255,255,255,.045)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  c.fillStyle = g;
  c.fillRect(0, 0, 96, 96);
});
const haloMats = new Map<string, T.SpriteMaterial>();
export function halo(parent: T.Object3D, x: number, y: number, z: number, color: string, size: number) {
  let mat = haloMats.get(color);
  if (!mat) {
    mat = new T.SpriteMaterial({
      map: haloMap,
      color,
      transparent: true,
      opacity: 0.62,
      depthWrite: false,
      blending: T.AdditiveBlending,
      toneMapped: false,
    });
    haloMats.set(color, mat);
  }
  const s = new T.Sprite(mat);
  s.position.set(x, y, z);
  s.scale.setScalar(size);
  parent.add(s);
  return s;
}

export function softMap() {
  return haloMap;
}
