// Title, base (storage / shop / dungeon picker) and result screens.

import { CLASSES, DUNGEON_LIST, type DungeonDef } from "../../engine/dungeon-def";
import { shopList, STORAGE_CAP, type SaveV1 } from "../../game/meta";
import type { ArtBank } from "./art";
import { drawCard, drawCardBack, type CardOpts } from "./card-face";
import { ruleTags } from "./hud";
import { H, W } from "./layout";
import { text } from "./text";

export type BaseUi = { pane: "storage" | "shop"; cursor: number; shopCursor: number; picks: number[]; msg: string; dungeonIdx: number };

/** Storage grid geometry, shared by the drawing and the cursor scrolling. */
export const GRID = { x: 16, y: 132, cols: 8, rows: 3, cw: 62, gapX: 12, gapY: 30 };
const CELL_W = GRID.cw + GRID.gapX;
const CELL_H = Math.round(GRID.cw * 1.5) + GRID.gapY;

/** First index shown, so the cursor stays on screen. */
export function gridScroll(cursor: number, count: number): number {
  const page = GRID.cols * GRID.rows;
  if (count <= page) return 0;
  const row = Math.floor(cursor / GRID.cols);
  const maxRow = Math.ceil(count / GRID.cols) - GRID.rows;
  return Math.min(Math.max(0, maxRow), Math.max(0, row - GRID.rows + 1)) * GRID.cols;
}

export function drawTitle(c: CanvasRenderingContext2D): void {
  text(c, "MONSTER GATE", W / 2, 240, "#fc6", 48, "center");
  text(c, "使い切りカード10枚とMPで潜るローグライク", W / 2, 318, "#aaa", 16, "center");
  text(c, "Enter でスタート", W / 2, 400, "#fff", 18, "center");
  text(c, "ダンジョン中は ? でいつでも操作説明", W / 2, 440, "#777", 14, "center");
}

export function drawBase(c: CanvasRenderingContext2D, bank: ArtBank, s: SaveV1, b: BaseUi, def: DungeonDef): void {
  text(c, `拠点   WIN ${s.win}   倉庫 ${s.storage.length}/${STORAGE_CAP}   runs ${s.stats.runs} clear ${s.stats.clears} dead ${s.stats.deaths}`, 16, 14, "#fc6", 18);
  text(c, "Tab: 倉庫/ショップ   ↑↓←→: 選択   c: 職業   Space: 持ち込み   s: 売る   Enter: 出発 / 買う   [ ]: ダンジョン", 16, 42, "#888", 13);
  const cd = CLASSES[s.cls];
  text(c, `職業: ${cd.name}  HP${cd.hp} MP${cd.mp}/${cd.maxMp} ATK${cd.atk} DEF${cd.def}`, 16, 66, "#8cf", 14);
  text(c, cd.desc, 340, 66, "#678", 13);

  // ---- storage grid
  const storageActive = b.pane === "storage";
  text(c, storageActive ? "▶ 倉庫（Space で持ち込み）" : "  倉庫", GRID.x, GRID.y - 26, storageActive ? "#fff" : "#888", 16);
  const start = gridScroll(b.cursor, s.storage.length);
  for (let i = 0; i < GRID.cols * GRID.rows; i++) {
    const j = start + i;
    const x = GRID.x + (i % GRID.cols) * CELL_W;
    const y = GRID.y + Math.floor(i / GRID.cols) * CELL_H;
    const card = s.storage[j];
    if (card === undefined) {
      drawCardBack(c, x, y, GRID.cw);
      continue;
    }
    const pick = b.picks.indexOf(j);
    const opts: CardOpts = { selected: storageActive && j === b.cursor, dim: pick >= 0 };
    if (pick >= 0) opts.badge = `${(pick + 1) % 10}`;
    drawCard(c, bank, card, x, y, GRID.cw, opts);
  }
  if (s.storage.length > GRID.cols * GRID.rows) {
    text(c, `${start + 1}-${Math.min(s.storage.length, start + GRID.cols * GRID.rows)} / ${s.storage.length}`, GRID.x, GRID.y + GRID.rows * CELL_H - 16, "#666", 12);
  }
  if (s.storage.length === 0) text(c, "（空）カードはダンジョンで拾うかショップで買う", GRID.x, GRID.y + 8, "#666", 15);

  // ---- the card under the cursor, full size
  const px = 660;
  const focus = b.pane === "shop" ? shopList()[b.shopCursor]?.card : s.storage[b.cursor];
  if (focus) drawCard(c, bank, focus, px, GRID.y, 150, { desc: true });
  else drawCardBack(c, px, GRID.y, 150, "―");

  // ---- carried hand
  const hx = px + 190;
  text(c, `持ち込み ${b.picks.length}/${def.handSize}`, hx, GRID.y - 26, "#fff", 16);
  for (let i = 0; i < def.handSize; i++) {
    const x = hx + (i % 5) * 52;
    const y = GRID.y + Math.floor(i / 5) * 84;
    const j = b.picks[i];
    if (j === undefined) drawCardBack(c, x, y, 44);
    else drawCard(c, bank, s.storage[j]!, x, y, 44);
  }

  // ---- dungeon picker
  const dy = GRID.y + 180;
  text(c, `[ ${def.name} ${"★".repeat(def.stars)} ]`, hx, dy, "#fc6", 20);
  text(c, `BET ${def.bet} / WIN ${def.win} / ${def.floors.length}F / 手札 ${def.handSize}`, hx, dy + 30, "#ddd", 15);
  text(c, def.desc, hx, dy + 52, "#aaa", 13);
  const tags = ruleTags(def.rules);
  if (tags.length) text(c, tags.join("  "), hx, dy + 72, "#8cf", 13);
  DUNGEON_LIST.forEach((d, i) => text(c, `${i === b.dungeonIdx ? "●" : "○"}${d.name}`, hx + (i % 3) * 130, dy + 98 + Math.floor(i / 3) * 20, i === b.dungeonIdx ? "#fff" : "#666", 13));

  // ---- shop, under the grid; the whole row plus its price footers must fit in H
  const sy = GRID.y + GRID.rows * CELL_H + 22;
  const shopActive = b.pane === "shop";
  text(c, shopActive ? "▶ ショップ（←→ で選び Enter で買う）" : "  ショップ（Tab で切替）", GRID.x, sy, shopActive ? "#fff" : "#888", 16);
  shopList().forEach((it, i) => {
    drawCard(c, bank, it.card, GRID.x + i * 66, sy + 26, 56, {
      selected: shopActive && i === b.shopCursor,
      dim: s.win < it.price,
      footer: `${it.price} WIN`,
    });
  });
  if (b.msg) text(c, b.msg, px, H - 44, "#f88", 16);
  else text(c, "Enter で出発", px, H - 44, "#8f8", 16);
}

export function drawResult(c: CanvasRenderingContext2D, lines: string[]): void {
  lines.forEach((line, i) => text(c, line, W / 2, 220 + i * 36, i === 0 ? "#fc6" : "#ddd", i === 0 ? 34 : 18, "center"));
}
