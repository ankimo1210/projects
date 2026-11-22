// Every texture in the game is drawn here at start-up on 2D canvases: no image
// files, so all of the town's surfaces and signage are original to this project.

import * as THREE from "three";
import type { Prop } from "../sim/types";

export const FONT =
  '"Hiragino Sans", "Hiragino Kaku Gothic ProN", "Yu Gothic", "Noto Sans JP", "Noto Sans CJK JP", "Meiryo", sans-serif';

type Ctx = CanvasRenderingContext2D;

function makeCanvas(w: number, h: number): [HTMLCanvasElement, Ctx] {
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d");
  if (!ctx) throw new Error("2d canvas unavailable");
  return [c, ctx];
}

function toTexture(c: HTMLCanvasElement, o: { srgb?: boolean; repeat?: boolean } = {}): THREE.CanvasTexture {
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = o.srgb === false ? THREE.NoColorSpace : THREE.SRGBColorSpace;
  if (o.repeat) {
    t.wrapS = THREE.RepeatWrapping;
    t.wrapT = THREE.RepeatWrapping;
  }
  t.anisotropy = 8;
  t.needsUpdate = true;
  return t;
}

export function prng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), s | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Tileable value noise in [0, 1]. */
function valueNoise(size: number, cells: number, seed: number): Float32Array {
  const rnd = prng(seed);
  const grid = new Float32Array(cells * cells);
  for (let i = 0; i < grid.length; i++) grid[i] = rnd();
  const out = new Float32Array(size * size);
  const g = (i: number, j: number): number => grid[(((j % cells) + cells) % cells) * cells + (((i % cells) + cells) % cells)] as number;
  for (let y = 0; y < size; y++) {
    const fy = (y / size) * cells;
    const j = Math.floor(fy);
    let ty = fy - j;
    ty = ty * ty * (3 - 2 * ty);
    for (let x = 0; x < size; x++) {
      const fx = (x / size) * cells;
      const i = Math.floor(fx);
      let tx = fx - i;
      tx = tx * tx * (3 - 2 * tx);
      const a = g(i, j) * (1 - tx) + g(i + 1, j) * tx;
      const b = g(i, j + 1) * (1 - tx) + g(i + 1, j + 1) * tx;
      out[y * size + x] = a * (1 - ty) + b * ty;
    }
  }
  return out;
}

function fbm(size: number, seed: number, octaves: number, base: number): Float32Array {
  const out = new Float32Array(size * size);
  let amp = 0.5;
  let norm = 0;
  for (let o = 0; o < octaves; o++) {
    const n = valueNoise(size, base << o, seed + o * 101);
    for (let i = 0; i < out.length; i++) out[i] = (out[i] as number) + (n[i] as number) * amp;
    norm += amp;
    amp *= 0.5;
  }
  for (let i = 0; i < out.length; i++) out[i] = (out[i] as number) / norm;
  return out;
}

function normalFromHeight(h: Float32Array, size: number, strength: number): THREE.CanvasTexture {
  const [c, ctx] = makeCanvas(size, size);
  const img = ctx.createImageData(size, size);
  const at = (x: number, y: number): number => h[((y + size) % size) * size + ((x + size) % size)] as number;
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const dx = (at(x + 1, y) - at(x - 1, y)) * strength;
      const dy = (at(x, y + 1) - at(x, y - 1)) * strength;
      const inv = 1 / Math.hypot(dx, dy, 1);
      const o = (y * size + x) * 4;
      img.data[o] = (-dx * inv * 0.5 + 0.5) * 255;
      img.data[o + 1] = (dy * inv * 0.5 + 0.5) * 255;
      img.data[o + 2] = inv * 255;
      img.data[o + 3] = 255;
    }
  }
  ctx.putImageData(img, 0, 0);
  return toTexture(c, { srgb: false, repeat: true });
}

function grayTexture(data: Float32Array, size: number, map: (v: number) => number): THREE.CanvasTexture {
  const [c, ctx] = makeCanvas(size, size);
  const img = ctx.createImageData(size, size);
  for (let i = 0; i < size * size; i++) {
    const v = clamp01(map(data[i] as number)) * 255;
    img.data[i * 4] = v;
    img.data[i * 4 + 1] = v;
    img.data[i * 4 + 2] = v;
    img.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  return toTexture(c, { srgb: false, repeat: true });
}

const clamp01 = (v: number): number => (v < 0 ? 0 : v > 1 ? 1 : v);

function speckle(ctx: Ctx, w: number, h: number, n: number, seed: number, alpha: number, light = true): void {
  const rnd = prng(seed);
  for (let i = 0; i < n; i++) {
    const v = light ? 150 + rnd() * 100 : rnd() * 40;
    ctx.fillStyle = `rgba(${v},${v},${v},${alpha * rnd()})`;
    const s = 1 + rnd() * 1.6;
    ctx.fillRect(rnd() * w, rnd() * h, s, s);
  }
}

export interface SurfaceSet {
  map: THREE.Texture;
  normalMap?: THREE.Texture;
  roughnessMap?: THREE.Texture;
}

/** Wet asphalt: dark aggregate, with standing water where the roughness drops out. */
export function asphaltSet(): SurfaceSet {
  const size = 512;
  const [c, ctx] = makeCanvas(size, size);
  ctx.fillStyle = "#3b3e44";
  ctx.fillRect(0, 0, size, size);
  speckle(ctx, size, size, 9000, 11, 0.16);
  speckle(ctx, size, size, 5000, 12, 0.5, false);
  // patched repairs and cracks
  const rnd = prng(5);
  ctx.strokeStyle = "rgba(8,9,10,0.7)";
  ctx.lineWidth = 1.2;
  for (let i = 0; i < 9; i++) {
    ctx.beginPath();
    let x = rnd() * size;
    let y = rnd() * size;
    ctx.moveTo(x, y);
    for (let k = 0; k < 7; k++) {
      x += (rnd() - 0.5) * 70;
      y += (rnd() - 0.5) * 70;
      ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
  const puddle = fbm(size, 31, 4, 3);
  const grain = fbm(size, 77, 3, 48);
  const rough = grayTexture(puddle, size, (v) => {
    // below the threshold water has pooled: mirror-smooth
    const wet = clamp01((v - 0.47) * 9);
    return 0.07 + wet * 0.42;
  });
  const height = new Float32Array(size * size);
  for (let i = 0; i < height.length; i++) {
    const wet = clamp01(((puddle[i] as number) - 0.47) * 9);
    height[i] = (grain[i] as number) * wet;
  }
  return {
    map: toTexture(c, { repeat: true }),
    normalMap: normalFromHeight(height, size, 2.2),
    roughnessMap: rough,
  };
}

export function pavingSet(): SurfaceSet {
  const size = 512;
  const [c, ctx] = makeCanvas(size, size);
  ctx.fillStyle = "#3e4045";
  ctx.fillRect(0, 0, size, size);
  const rnd = prng(8);
  const n = 8;
  const s = size / n;
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const v = 62 + rnd() * 18;
      ctx.fillStyle = `rgb(${v},${v + 1},${v + 4})`;
      ctx.fillRect(i * s + 1.5, j * s + 1.5, s - 3, s - 3);
    }
  }
  speckle(ctx, size, size, 5000, 21, 0.14);
  const puddle = fbm(size, 131, 4, 3);
  const height = new Float32Array(size * size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const gx = Math.min(x % s, s - (x % s));
      const gy = Math.min(y % s, s - (y % s));
      height[y * size + x] = Math.min(1, Math.min(gx, gy) / 3);
    }
  }
  return {
    map: toTexture(c, { repeat: true }),
    normalMap: normalFromHeight(height, size, 1.4),
    roughnessMap: grayTexture(puddle, size, (v) => 0.1 + clamp01((v - 0.45) * 7) * 0.4),
  };
}

export function concreteSet(tone: string, seed: number): SurfaceSet {
  const size = 256;
  const [c, ctx] = makeCanvas(size, size);
  ctx.fillStyle = tone;
  ctx.fillRect(0, 0, size, size);
  speckle(ctx, size, size, 3500, seed, 0.12);
  speckle(ctx, size, size, 2500, seed + 1, 0.35, false);
  // rain streaks running down
  const rnd = prng(seed + 2);
  for (let i = 0; i < 26; i++) {
    const x = rnd() * size;
    const g = ctx.createLinearGradient(0, 0, 0, size);
    g.addColorStop(0, `rgba(0,0,0,${0.1 + rnd() * 0.22})`);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x, 0, 2 + rnd() * 7, size * (0.4 + rnd() * 0.6));
  }
  const grain = fbm(size, seed + 9, 3, 24);
  return { map: toTexture(c, { repeat: true }), normalMap: normalFromHeight(grain, size, 1.2) };
}

export function tileSet(): SurfaceSet {
  const size = 256;
  const [c, ctx] = makeCanvas(size, size);
  ctx.fillStyle = "#3d3f3c";
  ctx.fillRect(0, 0, size, size);
  const n = 4;
  const s = size / n;
  const rnd = prng(3);
  for (let j = 0; j < n; j++) {
    for (let i = 0; i < n; i++) {
      const v = (i + j) % 2 === 0 ? 148 : 126;
      const k = v + rnd() * 10;
      ctx.fillStyle = `rgb(${k},${k - 3},${k - 12})`;
      ctx.fillRect(i * s + 1, j * s + 1, s - 2, s - 2);
    }
  }
  speckle(ctx, size, size, 1600, 4, 0.18, false);
  return { map: toTexture(c, { repeat: true }) };
}

export function linoSet(): SurfaceSet {
  const size = 256;
  const [c, ctx] = makeCanvas(size, size);
  ctx.fillStyle = "#4a5750";
  ctx.fillRect(0, 0, size, size);
  speckle(ctx, size, size, 5000, 14, 0.2);
  speckle(ctx, size, size, 3000, 15, 0.3, false);
  return { map: toTexture(c, { repeat: true }) };
}

/** Roller shutter: slats every 8 cm with rust weeping from the guides. */
export function shutterSet(): SurfaceSet {
  const w = 256;
  const h = 256;
  const [c, ctx] = makeCanvas(w, h);
  const slats = 16;
  const sh = h / slats;
  const rnd = prng(6);
  for (let i = 0; i < slats; i++) {
    const v = 104 + rnd() * 14;
    const g = ctx.createLinearGradient(0, i * sh, 0, (i + 1) * sh);
    g.addColorStop(0, `rgb(${v + 22},${v + 24},${v + 26})`);
    g.addColorStop(0.55, `rgb(${v},${v + 2},${v + 5})`);
    g.addColorStop(1, `rgb(${v - 42},${v - 40},${v - 38})`);
    ctx.fillStyle = g;
    ctx.fillRect(0, i * sh, w, sh);
  }
  for (let i = 0; i < 16; i++) {
    const x = rnd() * w;
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, "rgba(90,48,20,0)");
    g.addColorStop(0.3, `rgba(96,50,22,${0.12 + rnd() * 0.25})`);
    g.addColorStop(1, "rgba(60,30,14,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x, 0, 3 + rnd() * 9, h);
  }
  const height = new Float32Array(w * h);
  for (let y = 0; y < h; y++) {
    const t = (y % sh) / sh;
    const v = Math.sin(t * Math.PI);
    for (let x = 0; x < w; x++) height[y * w + x] = v;
  }
  return { map: toTexture(c, { repeat: true }), normalMap: normalFromHeight(height, w, 3.5) };
}

const FACADE_TONES: [string, string][] = [
  ["#6f6a60", "#4b473f"],
  ["#5d6468", "#3e4447"],
  ["#73685a", "#51483d"],
  ["#5a5f57", "#3c403a"],
  ["#6b6260", "#473f3e"],
  ["#59595f", "#3b3b41"],
  ["#70705f", "#4c4c3f"],
  ["#5f5750", "#403a35"],
];

/** Mortar wall with rows of dark windows; one tile is 6 m wide and 3.2 m (one storey) tall. */
export function facadeSet(tone: number): SurfaceSet {
  const w = 512;
  const h = 256;
  const [c, ctx] = makeCanvas(w, h);
  const [base, dark] = FACADE_TONES[tone % FACADE_TONES.length] as [string, string];
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, w, h);
  speckle(ctx, w, h, 5000, tone + 40, 0.1);
  speckle(ctx, w, h, 4000, tone + 41, 0.3, false);
  const rnd = prng(tone * 13 + 3);
  // storey band
  ctx.fillStyle = dark;
  ctx.fillRect(0, h - 14, w, 14);
  // windows: three per tile
  for (let i = 0; i < 3; i++) {
    const x = 28 + i * (w / 3);
    const ww = w / 3 - 62;
    const y = 52;
    const wh = 118;
    ctx.fillStyle = "#15171a";
    ctx.fillRect(x - 5, y - 5, ww + 10, wh + 10);
    const g = ctx.createLinearGradient(0, y, 0, y + wh);
    g.addColorStop(0, "#0b1016");
    g.addColorStop(1, "#05070a");
    ctx.fillStyle = g;
    ctx.fillRect(x, y, ww, wh);
    ctx.strokeStyle = "#2a2d31";
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, ww, wh);
    ctx.beginPath();
    ctx.moveTo(x + ww / 2, y);
    ctx.lineTo(x + ww / 2, y + wh);
    ctx.stroke();
    if (rnd() < 0.4) {
      // drawn curtain
      ctx.fillStyle = "rgba(60,58,52,0.55)";
      ctx.fillRect(x + 2, y + 2, ww * (0.3 + rnd() * 0.5), wh - 4);
    }
    // sill streak
    const sg = ctx.createLinearGradient(0, y + wh, 0, h);
    sg.addColorStop(0, "rgba(0,0,0,0.32)");
    sg.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = sg;
    ctx.fillRect(x, y + wh + 5, ww, h - y - wh);
  }
  for (let i = 0; i < 14; i++) {
    const x = rnd() * w;
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, `rgba(0,0,0,${0.08 + rnd() * 0.16})`);
    g.addColorStop(1, "rgba(0,0,0,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x, 0, 2 + rnd() * 6, h);
  }
  return { map: toTexture(c, { repeat: true }) };
}

export function grateSet(): SurfaceSet {
  const size = 128;
  const [c, ctx] = makeCanvas(size, size);
  ctx.fillStyle = "#101214";
  ctx.fillRect(0, 0, size, size);
  ctx.strokeStyle = "#5b6064";
  ctx.lineWidth = 3;
  for (let i = 0; i <= 8; i++) {
    ctx.beginPath();
    ctx.moveTo((i * size) / 8, 0);
    ctx.lineTo((i * size) / 8, size);
    ctx.stroke();
  }
  ctx.lineWidth = 6;
  for (let j = 0; j <= 2; j++) {
    ctx.beginPath();
    ctx.moveTo(0, (j * size) / 2);
    ctx.lineTo(size, (j * size) / 2);
    ctx.stroke();
  }
  const height = new Float32Array(size * size);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const gx = Math.min(x % 16, 16 - (x % 16));
      const gy = Math.min(y % 64, 64 - (y % 64));
      height[y * size + x] = gx < 2 || gy < 3 ? 1 : 0;
    }
  }
  return { map: toTexture(c, { repeat: true }), normalMap: normalFromHeight(height, size, 2) };
}

export function rippleNormal(): THREE.Texture {
  const size = 256;
  return normalFromHeight(fbm(size, 9, 4, 6), size, 5.5);
}

export function glowTexture(): THREE.Texture {
  const size = 128;
  const [c, ctx] = makeCanvas(size, size);
  const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  g.addColorStop(0, "rgba(255,255,255,1)");
  g.addColorStop(0.12, "rgba(255,255,255,0.72)");
  g.addColorStop(0.35, "rgba(255,255,255,0.2)");
  g.addColorStop(0.7, "rgba(255,255,255,0.045)");
  g.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
  return toTexture(c);
}

/** Long soft smear used for light reflections on the wet road. */
export function streakTexture(): THREE.Texture {
  const w = 64;
  const h = 256;
  const [c, ctx] = makeCanvas(w, h);
  const img = ctx.createImageData(w, h);
  const rnd = prng(17);
  const jitter = new Float32Array(h);
  for (let y = 0; y < h; y++) jitter[y] = 0.75 + rnd() * 0.25;
  for (let y = 0; y < h; y++) {
    const t = y / (h - 1);
    // bright near the light (t = 0), fading towards the viewer
    const along = Math.pow(1 - t, 1.6) * Math.min(1, t * 14);
    for (let x = 0; x < w; x++) {
      const u = (x / (w - 1)) * 2 - 1;
      const across = Math.exp(-u * u * 5.5);
      const v = along * across * (jitter[y] as number) * 255;
      const o = (y * w + x) * 4;
      img.data[o] = 255;
      img.data[o + 1] = 255;
      img.data[o + 2] = 255;
      img.data[o + 3] = v;
    }
  }
  ctx.putImageData(img, 0, 0);
  return toTexture(c);
}

function fitText(ctx: Ctx, text: string, maxW: number, size: number, weight = 800): number {
  let s = size;
  for (;;) {
    ctx.font = `${weight} ${s}px ${FONT}`;
    if (ctx.measureText(text).width <= maxW || s <= 8) return s;
    s -= 2;
  }
}

function arrow(ctx: Ctx, cx: number, cy: number, size: number, dir: "l" | "r" | "u", color: string): void {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(dir === "r" ? 0 : dir === "l" ? Math.PI : -Math.PI / 2);
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.moveTo(size * 0.5, 0);
  ctx.lineTo(0, -size * 0.42);
  ctx.lineTo(0, -size * 0.16);
  ctx.lineTo(-size * 0.5, -size * 0.16);
  ctx.lineTo(-size * 0.5, size * 0.16);
  ctx.lineTo(0, size * 0.16);
  ctx.lineTo(0, size * 0.42);
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

/** A walking figure heading for a doorway: the game's own evacuation mark. */
function evacMark(ctx: Ctx, cx: number, cy: number, s: number, color: string): void {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  // doorway
  ctx.lineWidth = s * 0.09;
  ctx.strokeRect(s * 0.12, -s * 0.46, s * 0.36, s * 0.92);
  // figure
  ctx.beginPath();
  ctx.arc(-s * 0.2, -s * 0.34, s * 0.085, 0, Math.PI * 2);
  ctx.fill();
  ctx.lineWidth = s * 0.1;
  ctx.beginPath();
  ctx.moveTo(-s * 0.2, -s * 0.2);
  ctx.lineTo(-s * 0.14, s * 0.06);
  ctx.lineTo(-s * 0.3, s * 0.4);
  ctx.moveTo(-s * 0.14, s * 0.06);
  ctx.lineTo(s * 0.04, s * 0.38);
  ctx.moveTo(-s * 0.4, -s * 0.02);
  ctx.lineTo(-s * 0.19, -s * 0.14);
  ctx.lineTo(s * 0.04, -s * 0.06);
  ctx.stroke();
  ctx.restore();
}

export function signTexture(p: Extract<Prop, { k: "sign" }>): THREE.Texture {
  const ppm = p.w > 4 ? 96 : 220; // pixels per metre
  const w = Math.max(64, Math.min(1024, Math.round(p.w * ppm)));
  const h = Math.max(48, Math.min(512, Math.round(p.h * ppm)));
  const [c, ctx] = makeCanvas(w, h);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const lines = p.lines;
  switch (p.style) {
    case "exit": {
      ctx.fillStyle = "#0f9a50";
      ctx.fillRect(0, 0, w, h);
      ctx.fillStyle = "#f4fff8";
      const markW = h * 1.0;
      evacMark(ctx, markW * 0.55, h / 2, h * 0.78, "#f4fff8");
      const arrowW = p.arrow ? h * 0.9 : 0;
      const textW = w - markW - arrowW - 10;
      const size = fitText(ctx, lines[0] ?? "", textW, h * 0.56);
      ctx.font = `800 ${size}px ${FONT}`;
      ctx.fillText(lines[0] ?? "", markW + textW / 2, h / 2 + 1);
      if (p.arrow) arrow(ctx, w - arrowW * 0.55, h / 2, h * 0.62, p.arrow, "#f4fff8");
      break;
    }
    case "evac": {
      ctx.fillStyle = "#0b5a36";
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = "#e8f5ec";
      ctx.lineWidth = Math.max(3, w * 0.018);
      ctx.strokeRect(ctx.lineWidth, ctx.lineWidth, w - ctx.lineWidth * 2, h - ctx.lineWidth * 2);
      const top = h * 0.36;
      evacMark(ctx, w * 0.26, top * 0.56, top * 0.86, "#e8f5ec");
      if (p.arrow) arrow(ctx, w * 0.68, top * 0.56, top * 0.74, p.arrow, "#ffe066");
      const rowH = (h - top - 8) / lines.length;
      lines.forEach((ln, i) => {
        const size = fitText(ctx, ln, w * 0.86, rowH * (i === 1 ? 0.86 : 0.7));
        ctx.font = `800 ${size}px ${FONT}`;
        ctx.fillStyle = i === 1 ? "#ffffff" : "#d6eadc";
        ctx.fillText(ln, w / 2, top + rowH * (i + 0.5));
      });
      break;
    }
    case "warn": {
      ctx.fillStyle = "#e0b414";
      ctx.fillRect(0, 0, w, h);
      // hazard stripes along the top and bottom edges
      const sw = h * 0.16;
      ctx.fillStyle = "#17171a";
      for (let x = -h; x < w + h; x += sw * 2) {
        for (const y of [0, h - sw * 0.9]) {
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(x + sw, y);
          ctx.lineTo(x + sw * 1.9, y + sw * 0.9);
          ctx.lineTo(x + sw * 0.9, y + sw * 0.9);
          ctx.closePath();
          ctx.fill();
        }
      }
      const rowH = (h - sw * 2) / lines.length;
      lines.forEach((ln, i) => {
        const size = fitText(ctx, ln, w * 0.9, rowH * (i === 0 ? 0.82 : 0.6), 900);
        ctx.font = `900 ${size}px ${FONT}`;
        ctx.fillStyle = i === 0 ? "#b0160f" : "#17171a";
        ctx.fillText(ln, w / 2, sw + rowH * (i + 0.5));
      });
      break;
    }
    case "station": {
      ctx.fillStyle = "#1c1e22";
      ctx.fillRect(0, 0, w, h);
      speckle(ctx, w, h, 1500, 51, 0.12);
      const size = fitText(ctx, lines[0] ?? "", w * 0.8, h * 0.66, 700);
      ctx.font = `700 ${size}px ${FONT}`;
      ctx.fillStyle = "#b9a56a";
      ctx.fillText(lines[0] ?? "", w / 2, h / 2 + 2);
      break;
    }
    case "notice": {
      ctx.fillStyle = "#d8d4c6";
      ctx.fillRect(0, 0, w, h);
      speckle(ctx, w, h, 900, 61, 0.18, false);
      const padX = p.arrow ? h * 0.9 : 0;
      const rowH = (h - 12) / lines.length;
      lines.forEach((ln, i) => {
        const size = fitText(ctx, ln, (w - padX) * 0.9, rowH * (i === 0 ? 0.72 : 0.5), 700);
        ctx.font = `700 ${size}px ${FONT}`;
        ctx.fillStyle = i === 0 ? "#14161a" : "#3a3d42";
        ctx.fillText(ln, padX + (w - padX) / 2, 6 + rowH * (i + 0.5));
      });
      if (p.arrow) arrow(ctx, padX * 0.52, h / 2, h * 0.56, p.arrow, "#a41c12");
      break;
    }
    default: {
      // plate
      ctx.fillStyle = "#e4e1d6";
      ctx.fillRect(0, 0, w, h);
      ctx.strokeStyle = "#2b2e33";
      ctx.lineWidth = Math.max(2, h * 0.05);
      ctx.strokeRect(ctx.lineWidth / 2, ctx.lineWidth / 2, w - ctx.lineWidth, h - ctx.lineWidth);
      const rowH = (h - 8) / lines.length;
      lines.forEach((ln, i) => {
        const size = fitText(ctx, ln, w * 0.88, rowH * 0.7, 800);
        ctx.font = `800 ${size}px ${FONT}`;
        ctx.fillStyle = "#1a1c20";
        ctx.fillText(ln, w / 2, 4 + rowH * (i + 0.5));
      });
      speckle(ctx, w, h, 500, 71, 0.25, false);
    }
  }
  return toTexture(c);
}

const SHOP_COLORS: [string, string][] = [
  ["#7a2a1e", "#f3e6c8"],
  ["#1f4a6e", "#eef3f7"],
  ["#e8dfc6", "#5a1b12"],
  ["#2f5b3a", "#f1ead2"],
  ["#d9c9a0", "#1d2a44"],
  ["#3a3a3f", "#e9c75a"],
  ["#8a5a22", "#fff3d6"],
  ["#c9d6d2", "#243a36"],
  ["#5a2440", "#f2dfe6"],
  ["#e6e2d8", "#1f1f22"],
  ["#274a4e", "#e3efe9"],
  ["#b9422a", "#fff0d8"],
];

/** Fascia board above a shop front. */
export function shopSignTexture(name: string, sub: string, tone: number): THREE.Texture {
  const w = 768;
  const h = 144;
  const [c, ctx] = makeCanvas(w, h);
  const [bg, fg] = SHOP_COLORS[tone % SHOP_COLORS.length] as [string, string];
  ctx.fillStyle = bg;
  ctx.fillRect(0, 0, w, h);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const size = fitText(ctx, name, w * 0.86, h * 0.56, 900);
  ctx.font = `900 ${size}px ${FONT}`;
  ctx.fillStyle = fg;
  ctx.fillText(name, w / 2, h * 0.42);
  const s2 = fitText(ctx, sub, w * 0.8, h * 0.2, 600);
  ctx.font = `600 ${s2}px ${FONT}`;
  ctx.globalAlpha = 0.85;
  ctx.fillText(sub, w / 2, h * 0.82);
  ctx.globalAlpha = 1;
  // weathering
  const rnd = prng(tone * 7 + 1);
  for (let i = 0; i < 22; i++) {
    const x = rnd() * w;
    const g = ctx.createLinearGradient(0, 0, 0, h);
    g.addColorStop(0, `rgba(20,14,8,${0.1 + rnd() * 0.25})`);
    g.addColorStop(1, "rgba(20,14,8,0)");
    ctx.fillStyle = g;
    ctx.fillRect(x, 0, 2 + rnd() * 8, h);
  }
  speckle(ctx, w, h, 1500, tone + 90, 0.22, false);
  return toTexture(c);
}

export function archTexture(text: string): THREE.Texture {
  const w = 1024;
  const h = 128;
  const [c, ctx] = makeCanvas(w, h);
  ctx.fillStyle = "#1f3d52";
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = "#c9a23a";
  ctx.fillRect(0, 0, w, 8);
  ctx.fillRect(0, h - 8, w, 8);
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  const size = fitText(ctx, text, w * 0.8, h * 0.62, 900);
  ctx.font = `900 ${size}px ${FONT}`;
  ctx.fillStyle = "#f2ead4";
  ctx.fillText(text, w / 2, h / 2 + 2);
  speckle(ctx, w, h, 1600, 33, 0.3, false);
  return toTexture(c);
}

/** Station-clock face stopped at two o'clock. */
export function clockTexture(): THREE.Texture {
  const s = 256;
  const [c, ctx] = makeCanvas(s, s);
  ctx.fillStyle = "#d9d6cb";
  ctx.beginPath();
  ctx.arc(s / 2, s / 2, s / 2 - 4, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#1b1d21";
  ctx.lineWidth = 8;
  ctx.stroke();
  ctx.lineCap = "round";
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2;
    ctx.lineWidth = i % 3 === 0 ? 9 : 4;
    ctx.beginPath();
    ctx.moveTo(s / 2 + Math.sin(a) * 96, s / 2 - Math.cos(a) * 96);
    ctx.lineTo(s / 2 + Math.sin(a) * 112, s / 2 - Math.cos(a) * 112);
    ctx.stroke();
  }
  const hand = (a: number, len: number, wid: number): void => {
    ctx.lineWidth = wid;
    ctx.beginPath();
    ctx.moveTo(s / 2, s / 2);
    ctx.lineTo(s / 2 + Math.sin(a) * len, s / 2 - Math.cos(a) * len);
    ctx.stroke();
  };
  hand((2 / 12) * Math.PI * 2, 62, 11);
  hand(0, 96, 7);
  return toTexture(c);
}

/** The town police crest: three wave lines under a pine sprig, in a ring. */
export function crestTexture(): THREE.Texture {
  const s = 256;
  const [c, ctx] = makeCanvas(s, s);
  ctx.clearRect(0, 0, s, s);
  ctx.strokeStyle = "#b9a56a";
  ctx.fillStyle = "#b9a56a";
  ctx.lineWidth = 10;
  ctx.beginPath();
  ctx.arc(s / 2, s / 2, 108, 0, Math.PI * 2);
  ctx.stroke();
  ctx.lineWidth = 9;
  ctx.lineCap = "round";
  for (let k = 0; k < 3; k++) {
    ctx.beginPath();
    for (let x = -70; x <= 70; x += 4) {
      const y = 36 + k * 22 + Math.sin((x / 70) * Math.PI * 2 + k) * 8;
      if (x === -70) ctx.moveTo(s / 2 + x, s / 2 + y);
      else ctx.lineTo(s / 2 + x, s / 2 + y);
    }
    ctx.stroke();
  }
  for (let k = -2; k <= 2; k++) {
    ctx.beginPath();
    ctx.moveTo(s / 2, s / 2 + 14);
    ctx.lineTo(s / 2 + k * 26, s / 2 - 62 + Math.abs(k) * 14);
    ctx.stroke();
  }
  return toTexture(c);
}

/** Lettering for the back of the protagonist's work jacket. */
export function jacketTexture(): THREE.Texture {
  // One wrap around the garment. The front zip meets at the two edges and
  // the silkscreen follows the folds across the middle of the back.
  const w = 1024;
  const h = 512;
  const [c, ctx] = makeCanvas(w, h);
  const fabric = ctx.createLinearGradient(0, 0, 0, h);
  fabric.addColorStop(0, "#40566a");
  fabric.addColorStop(0.46, "#354c62");
  fabric.addColorStop(0.8, "#3e5262");
  fabric.addColorStop(1, "#293c4c");
  ctx.fillStyle = fabric;
  ctx.fillRect(0, 0, w, h);
  const edge = (x: number): number => 194 - 22 * Math.cos(4 * Math.PI * x / w) + 17 * Math.cos(2 * Math.PI * (x / w - 0.5));
  const traceYoke = (offset: number): void => {
    ctx.beginPath();
    for (let x = 0; x <= w; x += 4) {
      if (x === 0) ctx.moveTo(x, edge(x) + offset);
      else ctx.lineTo(x, edge(x) + offset);
    }
  };
  traceYoke(0);
  ctx.lineTo(w, 0);
  ctx.lineTo(0, 0);
  ctx.closePath();
  const yoke = ctx.createLinearGradient(0, 0, 0, 220);
  yoke.addColorStop(0, "#536d7c");
  yoke.addColorStop(0.58, "#455e71");
  yoke.addColorStop(1, "#40576c");
  ctx.fillStyle = yoke;
  ctx.fill();
  for (const [offset, width, color] of [
    [5, 22, "#283a49"], [0, 19, "#8d8362"], [0, 12, "#c1cac4"], [13, 2, "#627681"],
  ] as const) {
    traceYoke(offset);
    ctx.lineWidth = width;
    ctx.strokeStyle = color;
    ctx.stroke();
  }

  // The sleeve-side seams and the front placket are sewn into the same cloth.
  for (const x of [w * 0.25, w * 0.75]) {
    ctx.lineWidth = 3;
    ctx.strokeStyle = "#344552";
    ctx.beginPath();
    ctx.moveTo(x, edge(x) + 13);
    ctx.bezierCurveTo(x + 14, 285, x - 12, 390, x, h);
    ctx.stroke();
  }
  // Action pleats under the back yoke, and stitched raglan seams up to the collar.
  for (const side of [-1, 1]) {
    const start = w / 2 + side * 117;
    const foot = w / 2 + side * 97;
    const top = edge(start) + 13;
    ctx.beginPath();
    ctx.moveTo(start, top);
    ctx.bezierCurveTo(start - side * 3, 257, foot + side * 11, 322, foot, 405);
    ctx.bezierCurveTo(foot + side * 19, 334, start + side * 18, 254, start + side * 11, top);
    ctx.closePath();
    const pleat = ctx.createLinearGradient(foot, 0, start + side * 15, 0);
    pleat.addColorStop(0, "rgba(19,35,49,.04)");
    pleat.addColorStop(0.53, "rgba(18,34,46,.38)");
    pleat.addColorStop(1, "rgba(155,178,185,.14)");
    ctx.fillStyle = pleat;
    ctx.fill();
    ctx.lineWidth = 2;
    ctx.strokeStyle = "rgba(158,177,181,.32)";
    ctx.beginPath();
    ctx.moveTo(w / 2 + side * 119, 2);
    ctx.bezierCurveTo(w / 2 + side * 157, 45, w / 2 + side * 181, 102, w / 2 + side * 221, 159);
    ctx.stroke();
  }
  for (const x of [0, w]) {
    ctx.fillStyle = "#283a49";
    ctx.fillRect(x - 8, 0, 16, h);
    ctx.fillStyle = "#65747a";
    ctx.fillRect(x - 1, 0, 2, h);
  }
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.font = `800 60px ${FONT}`;
  ctx.fillStyle = "#e3e2cc";
  ctx.fillText("汐凪渡船", w / 2, 103, 245);
  ctx.font = `700 24px ${FONT}`;
  ctx.fillStyle = "#c7cfbe";
  ctx.fillText("設備課", w / 2, 154);
  ctx.fillRect(w / 2 - 81, 153, 30, 2);
  ctx.fillRect(w / 2 + 51, 153, 30, 2);

  const rnd = prng(57);
  for (let i = 0; i < 85; i++) {
    const x = rnd() * w;
    const y = rnd() * h;
    const length = 6 + rnd() * 34;
    ctx.strokeStyle = i % 4 === 0 ? "rgba(186,205,207,.18)" : "rgba(24,43,56,.12)";
    ctx.lineWidth = 1 + rnd() * 2;
    ctx.beginPath();
    ctx.moveTo(x, y);
    ctx.quadraticCurveTo(x - 1, y + length * 0.6, x + 2, y + length);
    ctx.stroke();
  }
  ctx.lineWidth = 1;
  ctx.strokeStyle = "rgba(185,203,206,.065)";
  ctx.beginPath();
  for (let x = -h; x < w; x += 4) {
    ctx.moveTo(x, 0);
    ctx.lineTo(x + h, h);
  }
  ctx.stroke();
  speckle(ctx, w, h, 6800, 71, 0.16, false);
  return toTexture(c);
}

export function vendingTexture(): THREE.Texture {
  const w = 128;
  const h = 256;
  const [c, ctx] = makeCanvas(w, h);
  ctx.fillStyle = "#8f3528";
  ctx.fillRect(0, 0, w, h);
  ctx.fillStyle = "#0a0c0f";
  ctx.fillRect(10, 14, w - 20, 124);
  const rnd = prng(44);
  for (let r = 0; r < 3; r++) {
    for (let k = 0; k < 6; k++) {
      ctx.fillStyle = `hsl(${Math.floor(rnd() * 360)},35%,${18 + rnd() * 14}%)`;
      ctx.fillRect(16 + k * 16.5, 22 + r * 38, 11, 26);
    }
  }
  ctx.fillStyle = "#1c1e22";
  ctx.fillRect(10, 150, w - 20, 22);
  ctx.fillRect(22, 196, w - 44, 36);
  return toTexture(c);
}

/** A first-aid box lid and a cartridge box label. */
export function itemTexture(kind: "medkit" | "ammo"): THREE.Texture {
  const s = 128;
  const [c, ctx] = makeCanvas(s, s);
  if (kind === "medkit") {
    ctx.fillStyle = "#e9ece6";
    ctx.fillRect(0, 0, s, s);
    ctx.fillStyle = "#1a8f4a";
    ctx.fillRect(s * 0.4, s * 0.2, s * 0.2, s * 0.6);
    ctx.fillRect(s * 0.2, s * 0.4, s * 0.6, s * 0.2);
  } else {
    ctx.fillStyle = "#3b4a2c";
    ctx.fillRect(0, 0, s, s);
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = "#e8dfb8";
    ctx.font = `800 30px ${FONT}`;
    ctx.fillText(".38", s / 2, s * 0.4);
    ctx.font = `700 16px ${FONT}`;
    ctx.fillText("執行実包", s / 2, s * 0.72);
  }
  return toTexture(c);
}
