// One environmental particle layer per castle: dust, fog, snow, acid, embers.
// Positions are a pure function of the clock and the particle index, so there
// is no state to reset and a dropped frame never shows as a jump.

import { MAP_H, MAP_W, MAP_X, MAP_Y } from "./layout";

type Spec = {
  count: number;
  /** rgb, so the soft ones can build their own gradient stops */
  color: [number, number, number];
  /** radius range in logical px */
  r: [number, number];
  /** drift in px per second; negative vy rises */
  vx: number;
  vy: number;
  /** horizontal sway amplitude */
  sway: number;
  alpha: number;
  /** additive, for anything that glows */
  glow?: boolean;
  /** a radial falloff instead of a disc; anything bigger than a mote needs it */
  soft?: boolean;
};

const WEATHER: Record<string, Spec> = {
  // 松明の火の粉
  yukai: { count: 24, color: [255, 178, 87], r: [0.7, 1.9], vx: 5, vy: -15, sway: 11, alpha: 0.5, glow: true },
  // 窓から差す光の中の埃
  light: { count: 34, color: [255, 244, 214], r: [0.8, 2.1], vx: 6, vy: 8, sway: 15, alpha: 0.3 },
  // 低く漂う霧
  vague: { count: 13, color: [185, 201, 178], r: [18, 42], vx: 8, vy: -2, sway: 7, alpha: 0.12, soft: true },
  // 雪
  cold: { count: 42, color: [234, 247, 255], r: [0.9, 2.5], vx: -7, vy: 25, sway: 17, alpha: 0.55 },
  // 酸の泡
  cruel: { count: 20, color: [166, 216, 74], r: [1.3, 3.2], vx: 2, vy: -17, sway: 13, alpha: 0.38, glow: true },
  // 溶岩の火の粉
  tight: { count: 30, color: [255, 106, 42], r: [0.8, 2.3], vx: 4, vy: -27, sway: 9, alpha: 0.6, glow: true },
};

/** Irrational strides scatter the pool evenly without an RNG. */
function frac(x: number): number {
  return x - Math.floor(x);
}

export function drawWeather(c: CanvasRenderingContext2D, theme: string, t: number): void {
  const s = WEATHER[theme];
  if (!s) return;
  const sec = t / 1000;
  c.save();
  c.beginPath();
  c.rect(MAP_X, MAP_Y, MAP_W, MAP_H);
  c.clip();
  if (s.glow) c.globalCompositeOperation = "lighter";
  const [cr, cg, cb] = s.color;
  c.fillStyle = `rgb(${cr},${cg},${cb})`;
  for (let i = 0; i < s.count; i++) {
    const a = frac((i + 1) * 0.6180339887);
    const b = frac((i + 1) * 0.7548776662);
    const d = frac((i + 1) * 0.4142135624);
    const span = MAP_H + s.r[1] * 2;
    const yp = frac(b + (sec * s.vy) / span);
    const x = MAP_X + frac(a + (sec * s.vx) / MAP_W) * MAP_W + Math.sin(sec * (0.5 + d) + a * 6.283) * s.sway;
    const y = MAP_Y - s.r[1] + yp * span;
    // fade at both ends of the run so wrapping never pops
    c.globalAlpha = s.alpha * Math.sin(Math.PI * yp) * (0.5 + d * 0.5);
    const rad = s.r[0] + d * (s.r[1] - s.r[0]);
    if (s.soft) {
      const g = c.createRadialGradient(x, y, 0, x, y, rad);
      g.addColorStop(0, `rgba(${cr},${cg},${cb},1)`);
      g.addColorStop(1, `rgba(${cr},${cg},${cb},0)`);
      c.fillStyle = g;
    }
    c.beginPath();
    c.arc(x, y, rad, 0, Math.PI * 2);
    c.fill();
  }
  c.restore();
}
