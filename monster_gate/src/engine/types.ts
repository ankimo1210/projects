import type { RngState } from "./rng";

export type Vec = { x: number; y: number };

/** 0=N 1=NE 2=E 3=SE 4=S 5=SW 6=W 7=NW */
export type Dir = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7;
export const DIRS: readonly Vec[] = [
  { x: 0, y: -1 },
  { x: 1, y: -1 },
  { x: 1, y: 0 },
  { x: 1, y: 1 },
  { x: 0, y: 1 },
  { x: -1, y: 1 },
  { x: -1, y: 0 },
  { x: -1, y: -1 },
];

export type TileKind = "wall" | "floor" | "door" | "stairsDown" | "altar" | "ice" | "shop" | "casino";
export type Tile = { kind: TileKind; roomId: number; lit: boolean };

/** Interior floor area of a room (walls are outside x..x+w-1, y..y+h-1). */
export type Room = { id: number; x: number; y: number; w: number; h: number };

export type FloorMap = {
  width: number;
  height: number;
  tiles: Tile[]; // row-major, index = y*width + x
  rooms: Room[];
  entrance: Vec;
  stairs: Vec | null; // null on the final floor (altar instead)
  altar: Vec | null;
  shop: Vec | null;
  casino: Vec | null;
};

export type EnemyKind =
  | "puunya_g"
  | "puunya_y"
  | "killerbee"
  | "skeleton"
  | "kemunpa"
  | "goblin"
  | "mage"
  | "dragon";

export type ClassId = "warrior" | "mage" | "gambler";

export type CardId =
  | "potion20"
  | "potion40"
  | "potion80"
  | "fire"
  | "multiFire"
  | "thunder"
  | "sleep"
  | "haste"
  | "bright"
  | "warp"
  | "escape"
  | "bronzeSword"
  | "multiThunder"
  | "meteor"
  | "panic"
  | "multiPanic"
  | "search"
  | "map"
  | "regen"
  | "longSword"
  | "powerShield"
  | "pocket2"
  | "reviveRing"
  | "powerUp"
  | "summonGoblin"
  | "summonDragon";

export type StatusEffects = { haste: number; regen: number };

export type Player = {
  cls: ClassId;
  pos: Vec;
  level: number;
  xp: number;
  hp: number;
  maxHp: number;
  mp: number;
  maxMp: number;
  atk: number;
  def: number;
  hand: CardId[];
  handSize: number;
  status: StatusEffects;
  equipment: { weaponBonus: number; shieldBonus: number; pocket: boolean; revive: boolean };
  visitedRooms: number[];
  bright: boolean;
  searched: boolean; // enemies on this floor are shown on the map
  mapped: boolean; // items on this floor are shown on the map
};

export type Enemy = {
  id: number;
  kind: EnemyKind;
  pos: Vec;
  hp: number;
  maxHp: number;
  atk: number;
  def: number;
  awake: boolean;
  dormant: boolean; // does not wake on sight, only when hit or when the player is adjacent
  lastSeen: Vec | null;
  sleep: number;
  confused: number;
  ranged: boolean;
  boss: boolean; // guards the stairs: never moves, attacks half the time, drops a rare card
};

/** A summoned monster fighting on the player's side. */
export type Ally = {
  id: number;
  kind: EnemyKind;
  pos: Vec;
  hp: number;
  maxHp: number;
  atk: number;
  def: number;
};

export type FloorItem =
  | { id: number; pos: Vec; type: "card"; card: CardId }
  | { id: number; pos: Vec; type: "win"; amount: number }
  | { id: number; pos: Vec; type: "doubleUp" };

export type ShopOffer = { card: CardId; price: number; sold: boolean };

export type DungeonResult = null | "clear" | "dead" | "escaped";

export type DungeonState = {
  seed: number;
  rng: RngState;
  dungeonId: string;
  floorNo: number;
  map: FloorMap;
  explored: boolean[]; // per tile, same indexing as map.tiles
  player: Player;
  enemies: Enemy[];
  allies: Ally[];
  items: FloorItem[];
  offers: ShopOffer[];
  casinoSpins: number;
  nextId: number;
  turn: number;
  turnsOnFloor: number;
  spawnedOnFloor: number;
  winCollected: number;
  winMultiplier: number;
  result: DungeonResult;
};

export type Action =
  | { type: "move"; dir: Dir }
  | { type: "attack"; dir: Dir }
  | { type: "wait" }
  | { type: "useCard"; index: number; dir?: Dir }
  | { type: "discardCard"; index: number }
  | { type: "descend" }
  | { type: "takeAltar" }
  | { type: "buy"; index: number }
  | { type: "spin" };

export type Event =
  | { t: "moved"; from: Vec; to: Vec }
  | { t: "blocked"; reason: string }
  | { t: "attack"; by: "player" | number; target: "player" | number; dmg: number; crit: boolean; ranged: boolean }
  | { t: "died"; enemyId: number; kind: EnemyKind }
  | { t: "grow"; level: number; atk: number; def: number; hp: number }
  | { t: "pickup"; card: CardId }
  | { t: "pickupWin"; amount: number }
  | { t: "handFull"; card: CardId }
  | { t: "cardUsed"; card: CardId; mpCost: number }
  | { t: "notEnoughMp"; card: CardId; need: number }
  | { t: "discarded"; card: CardId; mpBack: number }
  | { t: "roomEntered"; roomId: number; hpGain: number; mpGain: number }
  | { t: "floorChanged"; floorNo: number }
  | { t: "spawn"; kind: EnemyKind }
  | { t: "slide"; to: Vec }
  | { t: "summoned"; kind: EnemyKind }
  | { t: "allyHit"; allyId: number; target: number; dmg: number }
  | { t: "allyHurt"; allyId: number; dmg: number }
  | { t: "allyDied"; kind: EnemyKind }
  | { t: "doubleUp"; multiplier: number }
  | { t: "bought"; card: CardId; price: number }
  | { t: "spun"; bet: number; payout: number }
  | { t: "enemySlept"; enemyId: number }
  | { t: "enemyConfused"; enemyId: number }
  | { t: "bossDrop"; card: CardId }
  | { t: "revived"; hp: number }
  | { t: "acid"; dmg: number }
  | { t: "playerDied" }
  | { t: "cleared"; win: number }
  | { t: "escaped"; win: number }
  | { t: "log"; msg: string };

export function idx(map: { width: number }, p: Vec): number {
  return p.y * map.width + p.x;
}

export function inBounds(map: { width: number; height: number }, p: Vec): boolean {
  return p.x >= 0 && p.y >= 0 && p.x < map.width && p.y < map.height;
}

export function tileAt(map: FloorMap, p: Vec): Tile {
  const t = map.tiles[idx(map, p)];
  if (!t) throw new Error(`tile out of bounds: ${p.x},${p.y}`);
  return t;
}

export function isWalkable(kind: TileKind): boolean {
  return kind !== "wall";
}

export function vecEq(a: Vec, b: Vec): boolean {
  return a.x === b.x && a.y === b.y;
}

export function add(a: Vec, b: Vec): Vec {
  return { x: a.x + b.x, y: a.y + b.y };
}

/** Chebyshev distance — one diagonal step counts as 1. */
export function dist(a: Vec, b: Vec): number {
  return Math.max(Math.abs(a.x - b.x), Math.abs(a.y - b.y));
}
