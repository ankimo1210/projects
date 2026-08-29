import { UI_FONT } from "./layout";

export function text(
  c: CanvasRenderingContext2D,
  s: string,
  x: number,
  y: number,
  color = "#ddd",
  size = 14,
  align: CanvasTextAlign = "left",
): void {
  c.fillStyle = color;
  c.font = `${size}px ${UI_FONT}`;
  c.textAlign = align;
  c.textBaseline = "top";
  c.fillText(s, x, y);
  c.textAlign = "left";
}

export function bar(c: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, ratio: number, color: string, label?: string): void {
  c.fillStyle = "#0c0c10";
  c.fillRect(x, y, w, h);
  c.fillStyle = color;
  c.fillRect(x + 1, y + 1, Math.round((w - 2) * clamp(ratio, 0, 1)), h - 2);
  c.strokeStyle = "#4a4a58";
  c.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  if (label) text(c, label, x + 4, y - 1, "#fff", 11);
}

export function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}
