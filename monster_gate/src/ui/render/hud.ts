// Dungeon HUD: top status bar, log, hand, shop/casino panels, help, minimap.

import { CARDS } from "../../engine/cards";
import { CASINO, CLASSES, ENEMY, type DungeonDef, type DungeonRules } from "../../engine/dungeon-def";
import { knownTiles } from "../../engine/turn";
import type { CardId, DungeonState } from "../../engine/types";
import type { ArtBank } from "./art";
import { drawCard, drawCardBack } from "./card-face";
import { CARDBAR_H, H, LOG_H, MAP_H, MAP_Y, TOP_H, W } from "./layout";
import { bar, text } from "./text";

export function drawTopBar(c: CanvasRenderingContext2D, s: DungeonState, def: DungeonDef): void {
  const p = s.player;
  c.fillStyle = "#16161e";
  c.fillRect(0, 0, W, TOP_H);
  c.fillStyle = "#2c2c3a";
  c.fillRect(0, TOP_H - 2, W, 2);

  text(c, def.name, 12, 8, "#ffd85a", 17);
  text(c, `${s.floorNo}/${def.floors.length}F`, 12, 34, "#fff", 20);

  text(c, "HP", 150, 12, "#f88", 13);
  text(c, `${p.hp}`, 178, 4, p.hp < p.maxHp * 0.3 ? "#f55" : "#fff", 24);
  text(c, `/${p.maxHp}`, 178 + String(p.hp).length * 14, 12, "#aaa", 14);
  bar(c, 150, 40, 190, 10, p.hp / p.maxHp, "#2ecc40");

  text(c, "MP", 370, 12, "#8cf", 13);
  text(c, `${p.mp}`, 398, 4, "#fff", 24);
  text(c, `/${p.maxMp}`, 398 + String(p.mp).length * 14, 12, "#aaa", 14);
  bar(c, 370, 40, 190, 10, p.mp / p.maxMp, "#3b7ddd");

  const atk = p.atk + p.equipment.weaponBonus;
  const dfn = p.def + p.equipment.shieldBonus;
  text(c, `Lv${p.level}`, 600, 8, "#fff", 15);
  text(c, CLASSES[p.cls].name, 680, 8, "#8cf", 14);
  text(c, `ATK ${atk}${p.equipment.weaponBonus ? "*" : ""}`, 600, 36, "#ddd", 14);
  text(c, `DEF ${dfn}${p.equipment.shieldBonus ? "*" : ""}`, 700, 36, "#ddd", 14);

  // WIN box, arcade style
  const bx = W - 250;
  c.strokeStyle = "#c33";
  c.lineWidth = 2;
  c.strokeRect(bx, 8, 170, 30);
  c.lineWidth = 1;
  text(c, "WIN", bx + 8, 14, "#f88", 15);
  text(c, `${s.winCollected}`, bx + 160, 11, "#fff", 20, "right");
  if (s.winMultiplier > 1) text(c, `×${s.winMultiplier}`, bx + 178, 14, "#fa4", 16);
  text(c, `T${s.turn}`, bx + 8, 44, "#777", 12);
  text(c, "? ヘルプ", W - 12, 44, "#777", 12, "right");

  const st: string[] = [...ruleTags(def.rules)];
  if (p.status.haste) st.push(`ヘイスト${p.status.haste}`);
  if (p.status.regen) st.push(`リジェネ${p.status.regen}`);
  if (p.bright) st.push("ブライト");
  if (p.searched) st.push("サーチ");
  if (p.equipment.revive) st.push("リバイブ");
  for (const a of s.allies) st.push(`${ENEMY[a.kind].name}(${a.hp})`);
  if (st.length) {
    // clipped so a long list never runs into the WIN box
    c.save();
    c.beginPath();
    c.rect(790, 0, bx - 800, TOP_H);
    c.clip();
    text(c, st.join(" "), 790, 36, "#8cf", 12);
    c.restore();
  }
}

export function drawLog(c: CanvasRenderingContext2D, log: string[]): void {
  const y = MAP_Y + MAP_H;
  c.fillStyle = "#0d0d12";
  c.fillRect(0, y, W, LOG_H);
  const shown = log.slice(-2);
  shown.forEach((line, i) => text(c, line, 12, y + 5 + i * 17, i === shown.length - 1 ? "#fff" : "#8a8a95", 13));
}

export function drawCardBar(c: CanvasRenderingContext2D, bank: ArtBank, s: DungeonState, pendingCard: number | null, discardMode: boolean): void {
  const y = H - CARDBAR_H;
  c.fillStyle = "#16161e";
  c.fillRect(0, y, W, CARDBAR_H);
  c.fillStyle = "#2c2c3a";
  c.fillRect(0, y, W, 2);
  const p = s.player;
  const slots = Math.max(10, p.handSize);
  const cw = 48;
  const gap = 8;
  const x0 = 14;
  for (let i = 0; i < slots; i++) {
    const x = x0 + i * (cw + gap);
    const cy = y + 8;
    const card = p.hand[i];
    const usable = i < p.handSize;
    if (!card) {
      drawCardBack(c, x, cy, cw, usable ? `${(i + 1) % 10}` : "×");
      continue;
    }
    drawCard(c, bank, card, x, cy, cw, {
      dim: p.mp < CARDS[card].mp,
      selected: pendingCard === i,
      danger: discardMode,
      badge: `${(i + 1) % 10}`,
    });
  }
  const hintX = x0 + slots * (cw + gap) + 16;
  const hint = discardMode
    ? "捨てるカードの番号を押す（MPが戻る）  Esc: 取消"
    : pendingCard !== null
      ? "方向キーで発動  Esc: 取消"
      : "1-0 使用   d 捨てる   Enter 階段/祭壇   ? ヘルプ";
  text(c, hint, hintX, y + CARDBAR_H / 2 - 8, discardMode ? "#ff9c9c" : pendingCard !== null ? "#ffd85a" : "#8a8a95", 14);
}

/** The card being aimed, blown up over the map so its effect is readable. */
export function drawPendingCard(c: CanvasRenderingContext2D, bank: ArtBank, card: CardId): void {
  const w = 168;
  const x = 24;
  const y = MAP_Y + MAP_H - Math.round(w * 1.5) - 20;
  c.save();
  c.shadowColor = "rgba(0,0,0,0.6)";
  c.shadowBlur = 18;
  drawCard(c, bank, card, x, y, w, { desc: true, selected: true });
  c.restore();
}

export function drawOverlay(c: CanvasRenderingContext2D, bank: ArtBank, s: DungeonState, kind: "shop" | "casino"): void {
  const w = 560;
  const h = 300;
  const x = (W - w) / 2;
  const y = MAP_Y + (MAP_H - h) / 2;
  c.fillStyle = "rgba(4,6,10,0.94)";
  c.fillRect(x, y, w, h);
  c.strokeStyle = "#6f6";
  c.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  if (kind === "shop") {
    text(c, "ショップ（拾ったWINで買える）", x + 18, y + 16, "#6f6", 18);
    const cw = 116;
    const gap = 24;
    const total = s.offers.length * cw + (s.offers.length - 1) * gap;
    s.offers.forEach((o, i) => {
      const afford = !o.sold && s.winCollected >= o.price;
      drawCard(c, bank, o.card, x + (w - total) / 2 + i * (cw + gap), y + 52, cw, {
        dim: !afford,
        badge: `${i + 1}`,
        footer: o.sold ? "売切" : `${o.price} WIN`,
      });
    });
    text(c, `所持 WIN ${s.winCollected}   1-3: 購入   Esc: 閉じる`, x + 18, y + h - 30, "#999", 14);
  } else {
    const left = CASINO.maxSpins - s.casinoSpins;
    const canSpin = left > 0 && s.winCollected >= CASINO.bet;
    text(c, "カジノ（スロット）", x + 18, y + 16, "#6f6", 18);
    text(c, `BET ${CASINO.bet} WIN  →  2倍 / 4倍 / 10倍`, x + 22, y + 62, "#ddd", 16);
    text(c, `残り ${left} 回`, x + 22, y + 98, left > 0 ? "#ddd" : "#a66", 16);
    text(c, `所持 WIN ${s.winCollected}`, x + 160, y + 98, s.winCollected >= CASINO.bet ? "#ddd" : "#a66", 16);
    if (CLASSES[s.player.cls].luckyCasino) text(c, "ギャンブラー: 当たりやすい", x + 22, y + 132, "#fa4", 14);
    text(c, canSpin ? "Space: 回す   Esc: 閉じる" : "Esc: 閉じる", x + 18, y + h - 30, "#999", 14);
  }
}

/** Castle name card, shown for a moment on entering a floor 1. */
export function drawCastleCard(c: CanvasRenderingContext2D, def: DungeonDef, alpha: number): void {
  const w = 460;
  const h = 132;
  const x = (W - w) / 2;
  const y = MAP_Y + MAP_H * 0.3;
  c.save();
  c.globalAlpha = alpha;
  c.fillStyle = "rgba(4,6,10,0.86)";
  c.fillRect(x, y, w, h);
  c.strokeStyle = "#fc6";
  c.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  text(c, def.name, W / 2, y + 22, "#fff", 34, "center");
  text(c, "★".repeat(def.stars), W / 2, y + 66, "#fc6", 20, "center");
  const tags = ruleTags(def.rules);
  text(c, tags.length ? tags.join("  ") : `${def.floors.length}F  BET ${def.bet}`, W / 2, y + 98, "#8cf", 15, "center");
  c.restore();
}

export function drawHelp(c: CanvasRenderingContext2D): void {
  const w = 760;
  const h = 330;
  const x = (W - w) / 2;
  const y = MAP_Y + (MAP_H - h) / 2;
  c.fillStyle = "rgba(4,6,10,0.94)";
  c.fillRect(x, y, w, h);
  c.strokeStyle = "#ffd85a";
  c.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
  text(c, "操作", x + 20, y + 16, "#ffd85a", 20);
  const lines = [
    "移動・攻撃   矢印 / q e z c（斜め） / テンキー",
    "待機         .  または Space",
    "カード使用   1 - 0 （方向が要るカードは続けて方向キー）",
    "カードを捨てる  d → 番号   （MPが戻る）",
    "階段・祭壇   Enter （▼ の上で降りる / 👑 でクリア）",
    "ショップ 🏪  1-3 で購入      カジノ 🎰  Space で回す",
    "取消・閉じる Esc            ヘルプ  ?",
    "",
    "足元の輪  緑=自分  水色=召喚モンスター  金=ボス（動かない・レアカードを落とす）",
    "🃏=カード  💎=ダブルアップ  🪙=WIN  ▼=階段  👑=祭壇  🏪=ショップ  🎰=カジノ",
  ];
  lines.forEach((l, i) => text(c, l, x + 22, y + 54 + i * 25, i >= 8 ? "#8cf" : "#ddd", 15));
}

export function drawMinimap(c: CanvasRenderingContext2D, s: DungeonState, x: number, y: number): void {
  const { map } = s;
  const size = 4;
  const known = knownTiles(s);
  c.fillStyle = "rgba(6,10,18,0.72)";
  c.fillRect(x - 3, y - 3, map.width * size + 6, map.height * size + 6);
  for (let my = 0; my < map.height; my++) {
    for (let mx = 0; mx < map.width; mx++) {
      const i = my * map.width + mx;
      if (!known[i]) continue;
      const t = map.tiles[i]!;
      if (t.kind === "wall") continue;
      c.fillStyle = t.roomId >= 0 ? "#6a6a78" : "#45454f";
      if (t.kind === "stairsDown" || t.kind === "altar") c.fillStyle = "#ffd85a";
      if (t.kind === "shop" || t.kind === "casino") c.fillStyle = "#6f6";
      if (t.kind === "ice") c.fillStyle = "#7ab";
      c.fillRect(x + mx * size, y + my * size, size, size);
    }
  }
  if (CLASSES[s.player.cls].treasureSight) {
    const goal = map.stairs ?? map.altar;
    c.fillStyle = "#ffd85a";
    if (goal) c.fillRect(x + goal.x * size, y + goal.y * size, size, size);
    for (const it of s.items) {
      if (it.type === "card") continue;
      c.fillStyle = it.type === "doubleUp" ? "#fa4" : "#fd4";
      c.fillRect(x + it.pos.x * size, y + it.pos.y * size, size, size);
    }
  }
  if (s.player.searched) {
    c.fillStyle = "#e44";
    for (const e of s.enemies) c.fillRect(x + e.pos.x * size, y + e.pos.y * size, size, size);
  }
  c.fillStyle = "#4cf";
  for (const a of s.allies) c.fillRect(x + a.pos.x * size, y + a.pos.y * size, size, size);
  c.fillStyle = "#8f8";
  c.fillRect(x + s.player.pos.x * size - 1, y + s.player.pos.y * size - 1, size + 2, size + 2);
}

/** Fit a card name into a hand slot. */
export function cardShort(name: string): string {
  const cut = name.replace("モンスター:", "召喚");
  return cut.length > 8 ? cut.slice(0, 8) : cut;
}

export function ruleTags(r: DungeonRules): string[] {
  const t: string[] = [];
  if (r.litCorridors) t.push("[通路が明るい]");
  if (r.dormantEnemies) t.push("[敵は眠っている]");
  if (r.acidFloor) t.push("[通路は酸の床]");
  if (r.enemyCrit) t.push("[敵も会心]");
  if (r.playerCrit) t.push("[会心率UP]");
  if (r.dark) t.push("[マップ記憶なし]");
  if (r.handSize !== undefined) t.push(`[手札${r.handSize}枚]`);
  return t;
}
