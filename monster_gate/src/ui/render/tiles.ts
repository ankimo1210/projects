// Code-drawn ground: a tile is a box with two side faces for height and a lit top
// face. Used wherever the art bank has no sprite for the tile.

import { TH, TW } from "./iso";
import { clamp } from "./text";
import { EMOJI_FONT, UI_FONT } from "./layout";

/**
 * `tint` shades the whole block, `edge` the outline (< 1 draws grout, > 1 a
 * highlight). Everything goes through `shade`, which only understands #rrggbb —
 * never hand it a colour this function has already converted.
 */
export function block(c: CanvasRenderingContext2D, X: number, Y: number, h: number, top: string, tint = 1, edge = 1.22): void {
  const hw = TW / 2;
  const hh = TH / 2;
  const ty = Y - h;
  c.fillStyle = shade(top, tint * 0.48);
  c.beginPath();
  c.moveTo(X - hw, Y);
  c.lineTo(X, Y + hh);
  c.lineTo(X, ty + hh);
  c.lineTo(X - hw, ty);
  c.closePath();
  c.fill();
  c.fillStyle = shade(top, tint * 0.7);
  c.beginPath();
  c.moveTo(X, Y + hh);
  c.lineTo(X + hw, Y);
  c.lineTo(X + hw, ty);
  c.lineTo(X, ty + hh);
  c.closePath();
  c.fill();
  c.fillStyle = shade(top, tint);
  c.beginPath();
  c.moveTo(X, ty - hh);
  c.lineTo(X + hw, ty);
  c.lineTo(X, ty + hh);
  c.lineTo(X - hw, ty);
  c.closePath();
  c.fill();
  c.strokeStyle = shade(top, tint * edge);
  c.lineWidth = 1;
  c.stroke();
}

/** Smaller diamond sunk into a tile's top face. */
export function inset(c: CanvasRenderingContext2D, X: number, topY: number, color: string): void {
  const hw = TW / 2 - 7;
  const hh = TH / 2 - 3.5;
  c.fillStyle = color;
  c.beginPath();
  c.moveTo(X, topY - hh);
  c.lineTo(X + hw, topY);
  c.lineTo(X, topY + hh);
  c.lineTo(X - hw, topY);
  c.closePath();
  c.fill();
}

/** Glyph lying flat on a tile. */
export function flat(c: CanvasRenderingContext2D, X: number, topY: number, glyph: string, size: number, color: string): void {
  c.save();
  c.textAlign = "center";
  c.textBaseline = "middle";
  c.font = `${size}px ${UI_FONT}`;
  c.fillStyle = color;
  c.fillText(glyph, X, topY);
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

/** Multiply a #rrggbb colour, for the darker side faces of a block. #rrggbb only. */
export function shade(hex: string, f: number): string {
  const n = Number.parseInt(hex.slice(1), 16);
  const ch = (sh: number) => clamp(Math.round(((n >> sh) & 255) * f), 0, 255);
  return `rgb(${ch(16)},${ch(8)},${ch(0)})`;
}
