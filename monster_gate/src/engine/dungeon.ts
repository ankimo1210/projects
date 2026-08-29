// Run creation and floor population.

import { dungeonPrice } from "./cards";
import { CLASSES, DOUBLE_UP, ENEMY, RULES, type DungeonDef } from "./dungeon-def";
import { visibleSet } from "./fov";
import { floorCells, generateFloor, restingCells } from "./mapgen";
import { Rng, seedRng } from "./rng";
import { idx, tileAt, type CardId, type ClassId, type DungeonState, type Enemy, type EnemyKind, type FloorItem, type Player, type ShopOffer, type Vec } from "./types";

export function createRun(seed: number, def: DungeonDef, hand: CardId[], cls: ClassId = "warrior"): DungeonState {
  if (hand.length > def.handSize) throw new Error("hand too large");
  const c = CLASSES[cls];
  const player: Player = {
    cls,
    pos: { x: 0, y: 0 },
    level: 1,
    xp: 0,
    hp: c.hp,
    maxHp: c.hp,
    mp: c.mp,
    maxMp: c.maxMp,
    atk: c.atk,
    def: c.def,
    hand: [...hand],
    handSize: def.handSize,
    status: { haste: 0, regen: 0 },
    equipment: { weaponBonus: 0, shieldBonus: 0, pocket: false, revive: false },
    visitedRooms: [],
    bright: false,
    searched: false,
    mapped: false,
  };
  const base: DungeonState = {
    seed,
    rng: seedRng(seed),
    dungeonId: def.id,
    floorNo: 0,
    map: { width: 0, height: 0, tiles: [], rooms: [], entrance: { x: 0, y: 0 }, stairs: null, altar: null, shop: null, casino: null },
    explored: [],
    player,
    enemies: [],
    allies: [],
    items: [],
    offers: [],
    casinoSpins: 0,
    nextId: 1,
    turn: 0,
    turnsOnFloor: 0,
    spawnedOnFloor: 0,
    winCollected: 0,
    winMultiplier: 1,
    result: null,
  };
  return enterFloor(base, def, 1);
}

export function enterFloor(state: DungeonState, def: DungeonDef, floorNo: number): DungeonState {
  const fdef = def.floors[floorNo - 1];
  if (!fdef) throw new Error(`no floor ${floorNo}`);
  const { map } = generateFloor(state.seed * 1000 + floorNo, fdef.map);
  const rng = new Rng((state.rng ^ (floorNo * 0x9e3779b9)) >>> 0);
  let nextId = state.nextId;
  const entranceRoom = tileAt(map, map.entrance).roomId;

  const enemies: Enemy[] = [];
  const taken = new Set<number>([idx(map, map.entrance)]);
  const enemyCells = floorCells(map, (t) => t.roomId >= 0 && t.roomId !== entranceRoom && t.kind === "floor");
  const dormant = def.rules.dormantEnemies === true;
  for (const [kind, n] of Object.entries(fdef.enemies) as [EnemyKind, number][]) {
    for (let i = 0; i < n; i++) {
      const cell = pickFree(rng, enemyCells, taken);
      if (!cell) break;
      enemies.push({ ...makeEnemy(nextId++, kind, cell), dormant });
    }
  }
  if (fdef.boss) {
    const goal = map.stairs ?? map.altar!;
    const goalRoom = tileAt(map, goal).roomId;
    const near = enemyCells.filter((c) => tileAt(map, c).roomId === goalRoom && Math.max(Math.abs(c.x - goal.x), Math.abs(c.y - goal.y)) === 1);
    const cell = pickFree(rng, near.length ? near : enemyCells, taken);
    if (cell) enemies.push(makeBoss(nextId++, fdef.boss, cell));
  }

  const items: FloorItem[] = [];
  // only where the player can stop: on ice you skate over some cells
  const canRest = restingCells(map, map.entrance);
  const itemCells = floorCells(map, (t, v) => t.kind === "floor" && canRest[idx(map, v)] === true);
  const luck = CLASSES[state.player.cls].cardLuck;
  const weights = luck === 1 ? def.cardWeights : def.cardWeights.map((w) => (w.weight <= 3 ? { ...w, weight: w.weight * luck } : w));
  for (let i = 0; i < fdef.cards; i++) {
    const cell = pickFree(rng, itemCells, taken);
    if (!cell) break;
    items.push({ id: nextId++, pos: cell, type: "card", card: rng.weighted(weights) });
  }
  for (let i = 0; i < fdef.wins; i++) {
    const cell = pickFree(rng, itemCells, taken);
    if (!cell) break;
    items.push({ id: nextId++, pos: cell, type: "win", amount: rng.int(def.winDrop.min, def.winDrop.max) });
  }
  const doubleChance = DOUBLE_UP.chancePerFloor * (CLASSES[state.player.cls].treasureSight ? 2 : 1);
  if (rng.chance(doubleChance)) {
    const cell = pickFree(rng, itemCells, taken);
    if (cell) items.push({ id: nextId++, pos: cell, type: "doubleUp" });
  }

  const offers: ShopOffer[] = [];
  if (map.shop) {
    for (let i = 0; i < 3; i++) {
      const card = rng.weighted(weights);
      offers.push({ card, price: dungeonPrice(card), sold: false });
    }
  }

  const player: Player = {
    ...state.player,
    pos: { ...map.entrance },
    visitedRooms: [entranceRoom],
    bright: false,
    searched: false,
    mapped: false,
  };
  const explored = visibleSet(map, player.pos, false, def.rules.litCorridors ? RULES.litCorridorRadius : 1);
  return {
    ...state,
    rng: rng.state,
    floorNo,
    map,
    explored,
    player,
    enemies,
    allies: [],
    items,
    offers,
    casinoSpins: 0,
    nextId,
    turnsOnFloor: 0,
    spawnedOnFloor: 0,
  };
}

export function makeEnemy(id: number, kind: EnemyKind, pos: Vec): Enemy {
  const d = ENEMY[kind];
  return { id, kind, pos: { ...pos }, hp: d.hp, maxHp: d.hp, atk: d.atk, def: d.def, awake: false, dormant: false, lastSeen: null, sleep: 0, confused: 0, ranged: d.ranged, boss: false };
}

export function makeBoss(id: number, kind: EnemyKind, pos: Vec): Enemy {
  const e = makeEnemy(id, kind, pos);
  const hp = Math.round(e.hp * RULES.bossHpMul);
  return { ...e, hp, maxHp: hp, atk: Math.round(e.atk * RULES.bossAtkMul), awake: true, ranged: false, boss: true };
}

function pickFree(rng: Rng, cells: readonly Vec[], taken: Set<number>): Vec | null {
  const free = cells.filter((c) => !taken.has(c.y * 100000 + c.x));
  if (free.length === 0) return null;
  const c = rng.pick(free);
  taken.add(c.y * 100000 + c.x);
  return c;
}
