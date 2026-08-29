// A simple scripted player for balance measurement. It only uses information
// a human would have: explored tiles, visible enemies/items, its own hand.

import { CARDS } from "./cards";
import { CASINO, CLASSES, RULES } from "./dungeon-def";
import { allyAt } from "./ally";
import { canStep, dirTo, enemyAt, firstEnemyInDir, slideFrom } from "./geometry";
import { visibleNow } from "./turn";
import { add, DIRS, dist, idx, isWalkable, tileAt, vecEq, type Action, type CardId, type Dir, type DungeonState, type Vec } from "./types";

export type BotConfig = { healBelow: number; nukeIfEnemyAtkOver: number };
export const DEFAULT_BOT: BotConfig = { healBelow: 0.5, nukeIfEnemyAtkOver: 0.25 };

/** What the bot remembers across turns (items it has seen on this floor). */
export type BotMemory = { floorNo: number; seenItems: Set<number>; targetItem: number | null; frontier: Vec | null; shopDone: boolean; lastPos: Vec | null };
export function newMemory(): BotMemory {
  return { floorNo: 0, seenItems: new Set(), targetItem: null, frontier: null, shopDone: false, lastPos: null };
}

export function botAction(s: DungeonState, cfg: BotConfig = DEFAULT_BOT, mem: BotMemory = newMemory()): Action {
  const p = s.player;
  const previous = mem.lastPos;
  mem.lastPos = { ...p.pos };
  const vis = visibleNow(s);
  if (mem.floorNo !== s.floorNo) {
    mem.floorNo = s.floorNo;
    mem.seenItems.clear();
    mem.targetItem = null;
    mem.frontier = null;
    mem.shopDone = false;
  }
  for (const it of s.items) if (vis[idx(s.map, it.pos)]) mem.seenItems.add(it.id);
  const visible = s.enemies.filter((e) => vis[idx(s.map, e.pos)]);
  const adjacent = visible.filter((e) => dist(e.pos, p.pos) === 1).sort((a, b) => a.hp - b.hp);

  // 0a. standing in a shop or casino: deal before moving on
  const here = tileAt(s.map, p.pos).kind;
  if (here === "shop") {
    const i = s.offers.findIndex((o) => !o.sold && o.price <= s.winCollected);
    if (i >= 0 && p.hand.length < p.handSize) return { type: "buy", index: i };
    mem.shopDone = true;
  }
  if (here === "casino" && CLASSES[p.cls].luckyCasino && s.casinoSpins < CASINO.maxSpins && s.winCollected >= CASINO.bet) {
    return { type: "spin" };
  }

  // 0b. equipment-style cards: play as soon as affordable (they only help)
  const passive: CardId[] = ["powerUp", "longSword", "bronzeSword", "powerShield", "pocket2", "reviveRing"];
  for (const card of passive) {
    const i = p.hand.indexOf(card);
    if (i < 0 || p.mp < CARDS[card].mp) continue;
    if (card === "bronzeSword" && p.equipment.weaponBonus >= 4) continue;
    if (card === "longSword" && p.equipment.weaponBonus >= 8) continue;
    if (card === "powerShield" && p.equipment.shieldBonus > 0) continue;
    if (card === "pocket2" && p.equipment.pocket) continue;
    if (card === "reviveRing" && p.equipment.revive) continue;
    return { type: "useCard", index: i };
  }

  // 1. heal when low
  if (p.hp < p.maxHp * cfg.healBelow) {
    const i = bestPotion(p.hand, p.maxHp - p.hp);
    if (i >= 0 && p.mp >= CARDS[p.hand[i]!].mp) return { type: "useCard", index: i };
    const r = p.hand.indexOf("regen");
    if (r >= 0 && p.status.regen === 0 && p.mp >= CARDS.regen.mp) return { type: "useCard", index: r };
  }

  // 1b. summon when outnumbered
  if (s.allies.length < 2 && (visible.length >= 2 || visible.some((e) => e.boss))) {
    for (const card of ["summonDragon", "summonGoblin"] as const) {
      const i = p.hand.indexOf(card);
      if (i >= 0 && p.mp >= CARDS[card].mp) return { type: "useCard", index: i };
    }
  }

  // 2. nuke a dangerous enemy in line
  const dangerous = visible.filter((e) => e.atk >= p.hp * cfg.nukeIfEnemyAtkOver || e.hp > (p.atk + p.equipment.weaponBonus - e.def) * 3);
  for (const card of ["meteor", "thunder", "fire"] as const) {
    const i = p.hand.indexOf(card);
    if (i < 0 || p.mp < CARDS[card].mp) continue;
    for (const e of dangerous) {
      const dir = dirTo(p.pos, e.pos);
      if (dir === null) continue;
      const hit = firstEnemyInDir(s.map, s.enemies, p.pos, dir, RULES.cardRange);
      if (hit && hit.id === e.id) return { type: "useCard", index: i, dir };
    }
  }
  if (visible.length >= 3) {
    for (const card of ["multiThunder", "multiFire", "multiPanic"] as const) {
      const i = p.hand.indexOf(card);
      if (i >= 0 && p.mp >= CARDS[card].mp) return { type: "useCard", index: i };
    }
  }

  // 3. melee — but walk past a boss we cannot bring down in a few hits
  const hit = Math.max(1, p.atk + p.equipment.weaponBonus - 0);
  const target = adjacent.find((e) => !e.boss || e.hp <= hit * 5 || p.hp > e.atk * 6);
  if (target) return { type: "attack", dir: dirTo(p.pos, target.pos)! };

  // 4. stairs / altar
  const goal = s.map.stairs ?? s.map.altar!;
  if (vecEq(p.pos, goal)) return s.map.altar ? { type: "takeAltar" } : { type: "descend" };

  // 5. an item we have seen: pick the nearest within 10 and stick to it until
  //    picked up (a distance threshold alone makes the bot oscillate on its edge)
  // a human walks around sleeping enemies; prefer paths that never touch a visible dormant one
  const sleepers = visible.filter((e) => e.dormant && !e.awake);
  const safe = (v: Vec) => !sleepers.some((e) => dist(e.pos, v) <= 1);
  const explored = (v: Vec) => s.explored[idx(s.map, v)] === true;
  const known = (v: Vec) => explored(v) && safe(v);
  /** step towards a cell: safe route first, any explored route second */
  const goTo = (target: Vec): Dir | null => moveToward(s, target, known) ?? moveToward(s, target, explored);
  const wantable = (it: { type: string }) => it.type === "win" || p.hand.length < p.handSize;
  let item = s.items.find((it) => it.id === mem.targetItem);
  if (!item || !wantable(item)) {
    mem.targetItem = null;
    item = s.items.filter((it) => mem.seenItems.has(it.id) && wantable(it) && dist(it.pos, p.pos) <= 10).sort((a, b) => dist(a.pos, p.pos) - dist(b.pos, p.pos))[0];
  }
  if (item) {
    const d = goTo(item.pos);
    if (d !== null) {
      mem.targetItem = item.id;
      return { type: "move", dir: d };
    }
    mem.targetItem = null;
  }

  // 5b. a shop worth visiting on the way
  if (!mem.shopDone && s.map.shop && explored(s.map.shop) && p.hand.length < p.handSize && s.offers.some((o) => !o.sold && o.price <= s.winCollected)) {
    const d = goTo(s.map.shop);
    if (d !== null) return { type: "move", dir: d };
  }

  // 6. known stairs, else the remembered frontier (re-chosen only when it stops being one)
  if (explored(goal)) {
    const d = goTo(goal);
    if (d !== null) return { type: "move", dir: d };
  }
  // Head for a spot that would actually show us something new. (Anything visible
  // from where we stand is already explored, so this never picks the current cell.)
  const reveals = revealSet(s);
  if (mem.frontier && reveals[idx(s.map, mem.frontier)]) {
    const d = goTo(mem.frontier);
    if (d !== null) return { type: "move", dir: d };
  }
  const wanted = (v: Vec) => reveals[idx(s.map, v)] === true;
  const toFrontier = planMove(s, wanted, known) ?? planMove(s, wanted, explored);
  if (toFrontier) {
    mem.frontier = toFrontier.cell;
    return { type: "move", dir: toFrontier.dir };
  }
  mem.frontier = null;

  // 7. cornered: something is standing in the only way (a boss never steps aside).
  //    Break through rather than stand still.
  const blocker = adjacent[0] ?? visible.filter((e) => dist(e.pos, p.pos) === 1)[0];
  if (blocker) return { type: "attack", dir: dirTo(p.pos, blocker.pos)! };
  const slideBlocked = (v: Vec) => !!enemyAt(s.enemies, v) || !!allyAt(s.allies, v);
  let fallback: Dir | null = null;
  for (let d = 0; d < 8; d++) {
    const dir = d as Dir;
    if (!canStep(s.map, p.pos, dir)) continue;
    const first = add(p.pos, DIRS[dir]!);
    if (enemyAt(s.enemies, first)) continue;
    if (fallback === null) fallback = dir;
    // do not bounce straight back to where we just came from
    const end = allyAt(s.allies, first) ? first : slideFrom(s.map, slideBlocked, first, dir);
    if (previous && vecEq(end, previous)) continue;
    return { type: "move", dir };
  }
  return fallback === null ? { type: "wait" } : { type: "move", dir: fallback };
}

function bestPotion(hand: readonly string[], missing: number): number {
  const order = ["potion20", "potion40", "potion80"];
  let best = -1;
  let bestWaste = Infinity;
  hand.forEach((c, i) => {
    const k = order.indexOf(c);
    if (k < 0) return;
    const amount = [20, 40, 80][k]!;
    const waste = Math.max(0, amount - missing);
    if (waste < bestWaste) {
      bestWaste = waste;
      best = i;
    }
  });
  return best;
}

/**
 * Shortest path measured in *actions*, not cells: one action is a step plus any
 * ice slide it triggers, so the bot plans around ice instead of skating past its
 * target. Walking into a summon swaps places and cancels the slide.
 */
function moveToward(s: DungeonState, goal: Vec, allow: (v: Vec) => boolean): Dir | null {
  return planMove(s, (v) => vecEq(v, goal), allow)?.dir ?? null;
}

/** As above, but for any cell matching `isGoal` — used to head for the nearest frontier. */
function planMove(s: DungeonState, isGoal: (v: Vec) => boolean, allow: (v: Vec) => boolean): { dir: Dir; cell: Vec } | null {
  const { map } = s;
  const start = s.player.pos;
  const slideBlocked = (v: Vec) => !!enemyAt(s.enemies, v) || !!allyAt(s.allies, v);
  const firstDir = new Map<number, Dir>();
  const seen = new Set<number>([idx(map, start)]);
  const q: Vec[] = [start];
  while (q.length) {
    const v = q.shift()!;
    for (let d = 0; d < 8; d++) {
      const dir = d as Dir;
      if (!canStep(map, v, dir)) continue;
      const first = add(v, DIRS[dir]!);
      if (!allow(first)) continue;
      // Only the step we are about to take must be clear: monsters further along
      // the path will have moved by the time we get there.
      const atStart = vecEq(v, start);
      if (atStart && enemyAt(s.enemies, first)) continue;
      const end = atStart && allyAt(s.allies, first) ? first : slideFrom(map, slideBlocked, first, dir);
      if (!allow(end)) continue;
      const i = idx(map, end);
      if (seen.has(i)) continue;
      seen.add(i);
      const step0 = vecEq(v, start) ? dir : firstDir.get(idx(map, v))!;
      firstDir.set(i, step0);
      if (isGoal(end)) return { dir: step0, cell: end };
      q.push(end);
    }
  }
  return null;
}

/**
 * Cells worth walking to: standing there would bring an unexplored walkable cell
 * into view — the whole room you are in, or a neighbour in a corridor.
 */
function revealSet(s: DungeonState): boolean[] {
  const { map } = s;
  const out = new Array<boolean>(map.tiles.length).fill(false);
  const roomsWanted = new Set<number>();
  for (let y = 0; y < map.height; y++) {
    for (let x = 0; x < map.width; x++) {
      const i = y * map.width + x;
      const t = map.tiles[i]!;
      if (s.explored[i] || !isWalkable(t.kind)) continue;
      if (t.roomId >= 0) roomsWanted.add(t.roomId);
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const v = { x: x + dx, y: y + dy };
          if (v.x < 0 || v.y < 0 || v.x >= map.width || v.y >= map.height) continue;
          const j = idx(map, v);
          if (s.explored[j] && isWalkable(map.tiles[j]!.kind)) out[j] = true;
        }
      }
    }
  }
  if (roomsWanted.size > 0) {
    for (let i = 0; i < map.tiles.length; i++) {
      const t = map.tiles[i]!;
      if (s.explored[i] && isWalkable(t.kind) && t.roomId >= 0 && roomsWanted.has(t.roomId)) out[i] = true;
    }
  }
  return out;
}
