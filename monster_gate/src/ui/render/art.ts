// Raster art registry. Sprites are listed in public/art/manifest.json and loaded
// lazily on first use; anything missing falls back to an emoji billboard, so the
// game (and every test) runs with no assets at all.
//
// Anchor convention: (ax, ay) is the point in the source image that lands on the
// draw position — the foot point for characters and items, the ground centre of
// the diamond for tiles. `scale` normalises source images of any size.

import type { ClassId, EnemyKind } from "../../engine/types";

export type SpriteDef = { src: string; ax: number; ay: number; scale?: number };
export type Manifest = { version: 1; sprites: Record<string, SpriteDef> };
export type ArtStatus = "idle" | "loading" | "ready" | "missing";

export class ArtBank {
  status: ArtStatus = "idle";
  private defs: Record<string, SpriteDef> = {};
  private images = new Map<string, HTMLImageElement>();
  private dimmed = new Map<string, HTMLCanvasElement>();

  constructor(private base = "art/") {}

  async load(): Promise<void> {
    this.status = "loading";
    try {
      const res = await fetch(`${this.base}manifest.json`, { cache: "no-cache" });
      const type = res.headers.get("content-type") ?? "";
      // the vite dev server answers unknown paths with index.html, status 200
      if (!res.ok || !type.includes("json")) {
        this.status = "missing";
        return;
      }
      const m = (await res.json()) as Manifest;
      this.defs = m.sprites ?? {};
      this.status = "ready";
    } catch {
      this.status = "missing";
    }
  }

  /** Number of sprites the manifest declares (0 while missing). */
  get size(): number {
    return Object.keys(this.defs).length;
  }

  /** A decoded sprite, or null: unknown id, still loading, or failed. Starts the load on first ask. */
  get(id: string): { img: CanvasImageSource; def: SpriteDef } | null {
    const def = this.defs[id];
    if (!def) return null;
    const img = this.images.get(id);
    if (img) return img.complete && img.naturalWidth > 0 ? { img, def } : null;
    const el = new Image();
    el.src = this.base + def.src;
    this.images.set(id, el);
    return null;
  }

  /**
   * The same sprite baked dark, for tiles the player only remembers. Fading with
   * globalAlpha instead would show the black background through and look ghostly.
   */
  dim(id: string): { img: CanvasImageSource; def: SpriteDef } | null {
    const cached = this.dimmed.get(id);
    if (cached) return { img: cached, def: this.defs[id]! };
    const hit = this.get(id);
    if (!hit) return null;
    const { img, def } = hit;
    const w = (img as HTMLImageElement).naturalWidth;
    const h = (img as HTMLImageElement).naturalHeight;
    const off = document.createElement("canvas");
    off.width = w;
    off.height = h;
    const c = off.getContext("2d");
    if (!c) return hit;
    c.drawImage(img, 0, 0);
    c.globalCompositeOperation = "source-atop"; // tints only the sprite's own pixels
    c.fillStyle = "rgba(8,10,26,0.66)";
    c.fillRect(0, 0, w, h);
    this.dimmed.set(id, off);
    return { img: off, def };
  }

  /** Register an already-decoded image (tests and the browser console). */
  put(id: string, img: HTMLImageElement, def: SpriteDef): void {
    this.defs[id] = def;
    this.images.set(id, img);
  }
}

export type DrawOpts = { scale?: number; alpha?: number; flip?: boolean; dim?: boolean };

/** Draw sprite `id` with its anchor at (x, y). False means the caller must fall back. */
export function drawSprite(c: CanvasRenderingContext2D, bank: ArtBank, id: string, x: number, y: number, o: DrawOpts = {}): boolean {
  const hit = o.dim ? bank.dim(id) : bank.get(id);
  if (!hit) return false;
  const { img, def } = hit;
  const k = (def.scale ?? 1) * (o.scale ?? 1);
  c.save();
  if (o.alpha !== undefined) c.globalAlpha *= o.alpha;
  c.translate(x, y);
  if (o.flip) c.scale(-1, 1);
  c.scale(k, k);
  c.drawImage(img, -def.ax, -def.ay);
  c.restore();
  return true;
}

export const classSprite = (cls: ClassId): string => `class.${cls}`;
export const enemySprite = (kind: EnemyKind): string => `enemy.${kind}`;

/** Fallback billboards, keyed by sprite id. */
export const EMOJI: Record<string, string> = {
  "class.warrior": "🦸",
  "class.mage": "🧙",
  "class.gambler": "🎲",
  "enemy.puunya_g": "🟢",
  "enemy.puunya_y": "🟡",
  "enemy.killerbee": "🐝",
  "enemy.skeleton": "💀",
  "enemy.kemunpa": "🐛",
  "enemy.goblin": "👺",
  "enemy.mage": "🔮",
  "enemy.dragon": "🐉",
  "item.card": "🃏",
  "item.doubleUp": "💎",
  "item.win": "🪙",
  "tile.altar": "👑",
  "tile.shop": "🏪",
  "tile.casino": "🎰",
};
