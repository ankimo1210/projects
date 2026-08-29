// Hand-built 2-room map for deterministic engine tests.
//
//   x: 0 1 2 3 4 5 6 7 8 9 10 11
// y0   # # # # # # # # # #  #  #
// y1   # . . . . . # # # #  #  #   room 0 = x1..5, y1..5
// y2   # . . . . . # # # .  .  #   room 1 = x9..10, y2..4
// y3   # . . . . . D . . .  .  #   door at (6,3), corridor (7,3),(8,3)
// y4   # . . . . . # # # .  >  #   stairs at (10,4)
// y5   # . . . . . # # # #  #  #
// y6   # # # # # # # # # #  #  #

import { YUKAI } from "../src/engine/dungeon-def";
import { makeAlly } from "../src/engine/ally";
import { makeEnemy } from "../src/engine/dungeon";
import { seedRng } from "../src/engine/rng";
import { WARRIOR } from "../src/engine/dungeon-def";
import type { CardId, ClassId, DungeonState, EnemyKind, FloorItem, FloorMap, ShopOffer, Tile, TileKind, Vec } from "../src/engine/types";

export function testMap(final = false, patch: { x: number; y: number; kind: TileKind }[] = []): FloorMap {
  const width = 12;
  const height = 7;
  const tiles: Tile[] = Array.from({ length: width * height }, () => ({ kind: "wall", roomId: -1, lit: false }));
  const set = (x: number, y: number, t: Tile) => (tiles[y * width + x] = t);
  for (let y = 1; y <= 5; y++) for (let x = 1; x <= 5; x++) set(x, y, { kind: "floor", roomId: 0, lit: true });
  for (let y = 2; y <= 4; y++) for (let x = 9; x <= 10; x++) set(x, y, { kind: "floor", roomId: 1, lit: true });
  set(6, 3, { kind: "door", roomId: -1, lit: false });
  set(7, 3, { kind: "floor", roomId: -1, lit: false });
  set(8, 3, { kind: "floor", roomId: -1, lit: false });
  set(10, 4, { kind: final ? "altar" : "stairsDown", roomId: 1, lit: true });
  for (const t of patch) set(t.x, t.y, { kind: t.kind, roomId: tiles[t.y * width + t.x]!.roomId, lit: tiles[t.y * width + t.x]!.lit });
  const shop = patch.find((t) => t.kind === "shop");
  const casino = patch.find((t) => t.kind === "casino");
  return {
    width,
    height,
    tiles,
    rooms: [
      { id: 0, x: 1, y: 1, w: 5, h: 5 },
      { id: 1, x: 9, y: 2, w: 2, h: 3 },
    ],
    entrance: { x: 1, y: 1 },
    stairs: final ? null : { x: 10, y: 4 },
    altar: final ? { x: 10, y: 4 } : null,
    shop: shop ? { x: shop.x, y: shop.y } : null,
    casino: casino ? { x: casino.x, y: casino.y } : null,
  };
}

export type Opts = {
  pos?: Vec;
  enemies?: { kind: EnemyKind; pos: Vec; awake?: boolean; hp?: number; dormant?: boolean; boss?: boolean }[];
  items?: FloorItem[];
  hand?: CardId[];
  hp?: number;
  mp?: number;
  maxHp?: number;
  level?: number;
  seed?: number;
  final?: boolean;
  floorNo?: number;
  dungeonId?: string;
  cls?: ClassId;
  allies?: { kind: EnemyKind; pos: Vec; hp?: number }[];
  winMultiplier?: number;
  winCollected?: number;
  offers?: ShopOffer[];
  tiles?: { x: number; y: number; kind: TileKind }[];
  casinoSpins?: number;
};

export function makeState(o: Opts = {}): DungeonState {
  const map = testMap(o.final ?? false, o.tiles ?? []);
  const pos = o.pos ?? { x: 1, y: 1 };
  const enemies = (o.enemies ?? []).map((e, i) => ({ ...makeEnemy(100 + i, e.kind, e.pos), awake: e.awake ?? true, dormant: e.dormant ?? false, boss: e.boss ?? false, ...(e.hp !== undefined ? { hp: e.hp } : {}) }));
  return {
    seed: o.seed ?? 1,
    rng: seedRng(o.seed ?? 1),
    dungeonId: o.dungeonId ?? YUKAI.id,
    floorNo: o.floorNo ?? 1,
    map,
    explored: new Array(map.tiles.length).fill(false),
    player: {
      cls: o.cls ?? "warrior",
      pos,
      level: o.level ?? 1,
      xp: 0,
      hp: o.hp ?? WARRIOR.hp,
      maxHp: o.maxHp ?? WARRIOR.hp,
      mp: o.mp ?? WARRIOR.mp,
      maxMp: WARRIOR.maxMp,
      atk: WARRIOR.atk,
      def: WARRIOR.def,
      hand: o.hand ?? [],
      handSize: YUKAI.handSize,
      status: { haste: 0, regen: 0 },
      equipment: { weaponBonus: 0, shieldBonus: 0, pocket: false, revive: false },
      visitedRooms: [0],
      bright: false,
      searched: false,
      mapped: false,
    },
    enemies,
    allies: (o.allies ?? []).map((a, i) => ({ ...makeAlly(200 + i, a.kind, a.pos), ...(a.hp !== undefined ? { hp: a.hp } : {}) })),
    items: o.items ?? [],
    offers: o.offers ?? [],
    casinoSpins: o.casinoSpins ?? 0,
    nextId: 1000,
    turn: 0,
    turnsOnFloor: 0,
    spawnedOnFloor: 0,
    winCollected: o.winCollected ?? 0,
    winMultiplier: o.winMultiplier ?? 1,
    result: null,
  };
}
