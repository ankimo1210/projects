// Code-drawn ground, used wherever the art bank has no sprite for a tile.
// Top-down: a tile is a square. Walls get a lighter top lip and a dark base so a
// wall still reads as solid mass rather than as a differently coloured floor.

import { TS } from "./grid";
import { EMOJI_FONT, UI_FONT } from "./layout";
import { clamp } from "./text";

/**
 * `tint` shades the whole tile, `edge` the grout line (< 1 darker, > 1 lighter).
 * Everything goes through `shade`, which only understands #rrggbb — never hand
 * it a colour this function has already converted.
 */
export function square(c: CanvasRenderingContext2D, X: number, Y: number, top: string, tint = 1, edge = 0.72): void {
  const h = TS / 2;
  c.fillStyle = shade(top, tint);
  c.fillRect(X - h, Y - h, TS, TS);
  c.strokeStyle = shade(top, tint * edge);
  c.lineWidth = 1;
  c.strokeRect(X - h + 0.5, Y - h + 0.5, TS - 1, TS - 1);
}

/** A wall cell: solid block with a lit top edge and a shaded bottom. */
export function wallBlock(c: CanvasRenderingContext2D, X: number, Y: number, top: string, tint = 1): void {
  const h = TS / 2;
  c.fillStyle = shade(top, tint);
  c.fillRect(X - h, Y - h, TS, TS);
  c.fillStyle = shade(top, tint * 1.35);
  c.fillRect(X - h, Y - h, TS, 3);
  c.fillStyle = shade(top, tint * 0.55);
  c.fillRect(X - h, Y + h - 4, TS, 4);
}

/** Smaller square sunk into a tile, for doors, stairs and altars. */
export function inset(c: CanvasRenderingContext2D, X: number, Y: number, color: string): void {
  const h = TS / 2 - 6;
  c.fillStyle = color;
  c.fillRect(X - h, Y - h, h * 2, h * 2);
}

/** Glyph lying flat on a tile. */
export function flat(c: CanvasRenderingContext2D, X: number, Y: number, glyph: string, size: number, color: string): void {
  c.save();
  c.textAlign = "center";
  c.textBaseline = "middle";
  c.font = `${size}px ${UI_FONT}`;
  c.fillStyle = color;
  c.fillText(glyph, X, Y);
  c.restore();
}

/** Emoji standing upright with a dark rim so a pale glyph reads on a pale floor. */
export function emojiBillboard(c: CanvasRenderingContext2D, glyph: string, X: number, baseY: number, size: number, rim = true): void {
  c.save();
  c.textAlign = "center";
  c.textBaseline = "alphabetic";
  c.font = `${Math.round(size)}px ${EMOJI_FONT}`;
  if (rim) {
    c.lineWidth = 3;
    c.strokeStyle = "rgba(0,0,0,0.6)";
    c.strokeText(glyph, X, baseY);
  }
  c.fillText(glyph, X, baseY);
  c.restore();
}

export function tileColor(kind: string, lit: boolean, seen: boolean): string {
  if (kind === "wall") return seen ? "#3a3a44" : "#1e1e26";
  if (kind === "ice") return seen ? "#8fc4d8" : "#41616e";
  if (seen) return lit ? "#8a8a80" : "#5c5c58";
  return lit ? "#3c3c3a" : "#2a2a28";
}

/** Multiply a #rrggbb colour, for the darker faces of a block. #rrggbb only. */
export function shade(hex: string, f: number): string {
  const n = Number.parseInt(hex.slice(1), 16);
  const ch = (sh: number) => clamp(Math.round(((n >> sh) & 255) * f), 0, 255);
  return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
}
