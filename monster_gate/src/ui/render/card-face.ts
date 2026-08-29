// A card face: family-coloured frame, rarity trim, illustration, cost and range.
// One function draws every size — hand slot, storage grid, and the big preview —
// so a card looks the same wherever it appears.

import { CARDS, type CardFamily, type CardRarity, type CardTarget } from "../../engine/cards";
import type { CardId } from "../../engine/types";
import { drawSprite, type ArtBank } from "./art";
import { UI_FONT } from "./layout";

const FAMILY: Record<CardFamily, { frame: string; panel: string }> = {
  heal: { frame: "#3fae5a", panel: "#1e5636" },
  fire: { frame: "#d8433a", panel: "#5f2222" },
  bolt: { frame: "#e0b13a", panel: "#5f4c1c" },
  status: { frame: "#8a5bd0", panel: "#3a2661" },
  scout: { frame: "#3b7ddd", panel: "#1c3a6b" },
  buff: { frame: "#e08a34", panel: "#5e3a16" },
  special: { frame: "#b9c0cf", panel: "#3f4452" },
  summon: { frame: "#3a3550", panel: "#191626" },
};

/** Rare gets a bright inner line, epic a gold border and corner marks. */
const RARITY_TRIM: Record<CardRarity, string | null> = { common: null, rare: "#dfe7ff", epic: "#ffd85a" };

/** Range is drawn as a shape, not a glyph: a kanji is unreadable at 8px. */
function rangeMark(c: CanvasRenderingContext2D, cx: number, cy: number, r: number, t: CardTarget): void {
  c.beginPath();
  c.arc(cx, cy, r, 0, Math.PI * 2);
  c.fillStyle = "rgba(10,10,18,0.72)";
  c.fill();
  c.fillStyle = "#fff";
  c.strokeStyle = "#fff";
  c.lineWidth = Math.max(1, r * 0.24);
  c.beginPath();
  if (t === "self") {
    c.arc(cx, cy, r * 0.42, 0, Math.PI * 2);
    c.fill();
  } else if (t === "dir") {
    c.moveTo(cx - r * 0.42, cy - r * 0.55);
    c.lineTo(cx + r * 0.55, cy);
    c.lineTo(cx - r * 0.42, cy + r * 0.55);
    c.closePath();
    c.fill();
  } else {
    c.arc(cx, cy, r * 0.52, 0, Math.PI * 2);
    c.stroke();
  }
}

export type CardOpts = {
  /** Greys the card out — not enough MP, sold, or otherwise unusable. */
  dim?: boolean;
  /** Gold selection ring. */
  selected?: boolean;
  /** Red ring, for the discard prompt. */
  danger?: boolean;
  /** Show the effect text; only fits from about 150px wide. */
  desc?: boolean;
  /** Drawn top-left over the frame (hand slot number, shop index). */
  badge?: string;
  /** Drawn under the card (price, count). */
  footer?: string;
};

export const CARD_RATIO = 1.5;

export function drawCard(c: CanvasRenderingContext2D, bank: ArtBank, card: CardId, x: number, y: number, w: number, o: CardOpts = {}): void {
  const def = CARDS[card];
  const h = Math.round(w * CARD_RATIO);
  const fam = FAMILY[def.family];
  const pad = Math.max(3, Math.round(w * 0.055));

  c.save();
  roundRect(c, x, y, w, h, w * 0.1);
  c.fillStyle = "#14121c";
  c.fill();
  roundRect(c, x + pad, y + pad, w - pad * 2, h - pad * 2, w * 0.07);
  c.fillStyle = fam.frame;
  c.fill();

  // illustration panel
  const ax = x + pad * 1.6;
  const ay = y + h * 0.155;
  const aw = w - pad * 3.2;
  const ah = h * 0.42;
  roundRect(c, ax, ay, aw, ah, w * 0.05);
  c.fillStyle = fam.panel;
  c.fill();
  c.save();
  c.clip();
  const art = Math.min(aw, ah) * 0.92;
  if (!drawSprite(c, bank, `card.${card}`, ax + aw / 2, ay + ah / 2, { scale: art / 256 })) {
    text(c, "?", ax + aw / 2, ay + ah / 2 - art * 0.3, "#fff", art * 0.6, "center");
  }
  c.restore();

  // name, then effect text when there is room
  const nameSize = Math.max(8, Math.round(w * 0.115));
  const inner = w - pad * 3;
  c.font = `${nameSize}px ${UI_FONT}`;
  text(c, fit(c, def.name, inner), x + w / 2, ay + ah + h * 0.035, "#fff", nameSize, "center");
  if (o.desc) {
    const ds = Math.max(9, Math.round(w * 0.075));
    c.font = `${ds}px ${UI_FONT}`;
    const lines = wrap(c, def.desc, inner);
    lines.slice(0, 4).forEach((line, i) => text(c, line, x + w / 2, ay + ah + h * 0.035 + nameSize * 1.5 + i * ds * 1.35, "#f2eeff", ds, "center"));
  }

  // cost badge and range mark
  const br = Math.max(7, w * 0.14);
  c.beginPath();
  c.arc(x + pad + br * 0.9, y + pad + br * 0.9, br, 0, Math.PI * 2);
  c.fillStyle = "#14121c";
  c.fill();
  text(c, `${def.mp}`, x + pad + br * 0.9, y + pad + br * 0.9 - br * 0.62, "#9cc4ff", br * 1.25, "center");
  rangeMark(c, x + w - pad - br * 0.75, y + pad + br * 0.75, br * 0.75, def.target);

  const trim = RARITY_TRIM[def.rarity];
  if (trim) {
    c.strokeStyle = trim;
    c.lineWidth = def.rarity === "epic" ? 2 : 1;
    roundRect(c, x + pad * 1.7, y + pad * 1.7, w - pad * 3.4, h - pad * 3.4, w * 0.05);
    c.stroke();
    if (def.rarity === "epic") {
      c.fillStyle = trim;
      const t = w * 0.14;
      for (const [cx, cy, sx, sy] of [
        [x + pad, y + pad, 1, 1],
        [x + w - pad, y + pad, -1, 1],
        [x + pad, y + h - pad, 1, -1],
        [x + w - pad, y + h - pad, -1, -1],
      ] as const) {
        c.beginPath();
        c.moveTo(cx, cy);
        c.lineTo(cx + t * sx, cy);
        c.lineTo(cx, cy + t * sy);
        c.closePath();
        c.fill();
      }
    }
  }

  if (o.dim) {
    roundRect(c, x, y, w, h, w * 0.1);
    c.fillStyle = "rgba(8,8,14,0.62)";
    c.fill();
  }
  if (o.badge) {
    c.fillStyle = "rgba(10,10,18,0.8)";
    const bw = Math.max(12, w * 0.26);
    roundRect(c, x + w - bw - 1, y + h - bw * 0.8 - 1, bw, bw * 0.8, 3);
    c.fill();
    text(c, o.badge, x + w - bw / 2 - 1, y + h - bw * 0.78, "#fff", Math.max(9, w * 0.16), "center");
  }
  if (o.selected || o.danger) {
    c.strokeStyle = o.danger ? "#ff6b6b" : "#ffd85a";
    c.lineWidth = 3;
    roundRect(c, x - 2, y - 2, w + 4, h + 4, w * 0.11);
    c.stroke();
  }
  if (o.footer) text(c, o.footer, x + w / 2, y + h + 3, "#cfd4de", Math.max(10, w * 0.14), "center");
  c.restore();
}

/** The face-down back, for empty hand slots. */
export function drawCardBack(c: CanvasRenderingContext2D, x: number, y: number, w: number, label?: string): void {
  const h = Math.round(w * CARD_RATIO);
  c.save();
  roundRect(c, x, y, w, h, w * 0.1);
  c.fillStyle = "#14121c";
  c.fill();
  const pad = Math.max(3, Math.round(w * 0.055));
  roundRect(c, x + pad, y + pad, w - pad * 2, h - pad * 2, w * 0.07);
  c.fillStyle = "#1e1c2c";
  c.fill();
  c.strokeStyle = "#2e2b42";
  c.lineWidth = 1;
  roundRect(c, x + pad * 2, y + pad * 2, w - pad * 4, h - pad * 4, w * 0.05);
  c.stroke();
  if (label) text(c, label, x + w / 2, y + h / 2 - w * 0.1, "#4a4760", Math.max(9, w * 0.2), "center");
  c.restore();
}

function roundRect(c: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  c.beginPath();
  c.roundRect(x, y, w, h, r);
}

function text(c: CanvasRenderingContext2D, s: string, x: number, y: number, color: string, size: number, align: CanvasTextAlign = "left"): void {
  c.fillStyle = color;
  c.font = `${Math.round(size)}px ${UI_FONT}`;
  c.textAlign = align;
  c.textBaseline = "top";
  c.fillText(s, x, y);
  c.textAlign = "left";
}

/** Japanese wraps anywhere, but the widths are mixed, so measure. Set c.font first. */
function wrap(c: CanvasRenderingContext2D, s: string, maxW: number): string[] {
  const out: string[] = [];
  let line = "";
  for (const ch of s) {
    if (line && c.measureText(line + ch).width > maxW) {
      out.push(line);
      line = "";
    }
    line += ch;
  }
  if (line) out.push(line);
  return out;
}

/** Trim to the frame width with an ellipsis. Set c.font first. */
function fit(c: CanvasRenderingContext2D, s: string, maxW: number): string {
  const cut = s.replace("モンスター:", "召喚");
  if (c.measureText(cut).width <= maxW) return cut;
  let out = cut;
  while (out.length > 1 && c.measureText(out + "…").width > maxW) out = out.slice(0, -1);
  return out + "…";
}
