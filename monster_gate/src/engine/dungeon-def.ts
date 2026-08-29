// Data tables: enemies, the "yukai" dungeon, starting stats. Numbers marked
// (src) come from the original game; everything else is a tunable guess.

import type { MapGenParams } from "./mapgen";
import { YUKAI_MAP } from "./mapgen";
import type { CardId, ClassId, DungeonResult, EnemyKind } from "./types";

export type EnemyDef = {
  name: string;
  hp: number; // (src)
  atk: number;
  def: number;
  ranged: boolean;
  xp: number;
  /** kills give no XP once the player's level is above this (the "trivial" rule) */
  trivialAt: number;
};

export const ENEMY: Record<EnemyKind, EnemyDef> = {
  puunya_g: { name: "プーニャ(緑)", hp: 9, atk: 5, def: 0, ranged: false, xp: 3, trivialAt: 8 },
  puunya_y: { name: "プーニャ(黄)", hp: 10, atk: 6, def: 0, ranged: false, xp: 3, trivialAt: 10 },
  killerbee: { name: "キラービー", hp: 11, atk: 7, def: 1, ranged: false, xp: 4, trivialAt: 12 },
  skeleton: { name: "スケルトン", hp: 14, atk: 9, def: 2, ranged: false, xp: 5, trivialAt: 15 },
  kemunpa: { name: "ケムンパ", hp: 17, atk: 10, def: 2, ranged: true, xp: 6, trivialAt: 18 },
  goblin: { name: "ゴブリン", hp: 21, atk: 13, def: 3, ranged: false, xp: 7, trivialAt: 22 },
  mage: { name: "魔道士", hp: 26, atk: 15, def: 2, ranged: true, xp: 9, trivialAt: 26 },
  dragon: { name: "ドラゴン", hp: 67, atk: 18, def: 8, ranged: true, xp: 23, trivialAt: 40 },
};

/** Hidden level curve. Level 1 at run start; every run starts over. */
export const LEVELING = {
  xpToNext: (level: number): number => 3 + Math.floor(level / 2),
  hpPerLevel: 3,
  atkEvery: 2, // +1 ATK on levels divisible by this
  defEvery: 5, // +1 DEF on levels divisible by this
  maxLevel: 99,
};

export type FloorDef = {
  enemies: Partial<Record<EnemyKind, number>>;
  cards: number;
  wins: number;
  map: MapGenParams;
  boss?: EnemyKind; // a boss of this kind guards the stairs
};

/** Castle-specific rules. Everything optional; absent = normal. */
export type DungeonRules = {
  playerCrit?: number; // default RULES.playerCrit
  enemyCrit?: number; // default 0
  acidFloor?: boolean; // every step in a corridor costs 1 HP
  litCorridors?: boolean; // see 3 cells around you in corridors
  dormantEnemies?: boolean; // enemies stay asleep until hit or adjacent
  dark?: boolean; // the screen shows only what you see right now (no map memory / minimap)
  handSize?: number; // default 10; also the bring-in limit
};

export type DungeonDef = {
  id: string;
  name: string;
  stars: number;
  desc: string;
  bet: number;
  win: number; // (src)
  handSize: number;
  rules: DungeonRules;
  floors: FloorDef[];
  cardWeights: { item: CardId; weight: number }[];
  winDrop: { min: number; max: number };
};

const COMMON_WEIGHTS: { item: CardId; weight: number }[] = [
  { item: "potion20", weight: 30 },
  { item: "potion40", weight: 15 },
  { item: "potion80", weight: 5 },
  { item: "fire", weight: 20 },
  { item: "multiFire", weight: 8 },
  { item: "thunder", weight: 8 },
  { item: "multiThunder", weight: 2 },
  { item: "meteor", weight: 1 },
  { item: "sleep", weight: 6 },
  { item: "panic", weight: 5 },
  { item: "multiPanic", weight: 2 },
  { item: "haste", weight: 4 },
  { item: "bright", weight: 4 },
  { item: "search", weight: 3 },
  { item: "map", weight: 3 },
  { item: "regen", weight: 3 },
  { item: "warp", weight: 4 },
  { item: "escape", weight: 2 },
  { item: "bronzeSword", weight: 2 },
  { item: "longSword", weight: 1 },
  { item: "powerShield", weight: 1 },
  { item: "pocket2", weight: 1 },
  { item: "reviveRing", weight: 1 },
  { item: "powerUp", weight: 1 },
  { item: "summonGoblin", weight: 3 },
  { item: "summonDragon", weight: 1 },
];

const WIN_DROP = { min: 3, max: 8 };
const FINAL = { ...YUKAI_MAP, final: true };
const SHOP = { ...YUKAI_MAP, shop: true };
const CASINO_MAP = { ...YUKAI_MAP, casino: true };

export const YUKAI: DungeonDef = {
  id: "yukai",
  name: "ゆかい",
  stars: 3,
  desc: "腕試しの標準ダンジョン。4F にボス。",
  bet: 10,
  win: 90,
  handSize: 10,
  rules: {},
  floors: [
    { enemies: { puunya_g: 3, puunya_y: 3 }, cards: 3, wins: 1, map: YUKAI_MAP },
    { enemies: { puunya_y: 3, killerbee: 3 }, cards: 3, wins: 1, map: YUKAI_MAP },
    { enemies: { killerbee: 3, skeleton: 3 }, cards: 3, wins: 2, map: SHOP },
    { enemies: { skeleton: 3, kemunpa: 3 }, cards: 4, wins: 2, map: YUKAI_MAP, boss: "goblin" },
    { enemies: { kemunpa: 3, goblin: 3 }, cards: 4, wins: 2, map: SHOP },
    { enemies: { goblin: 3, mage: 3 }, cards: 4, wins: 3, map: CASINO_MAP },
    { enemies: { mage: 3, goblin: 2, dragon: 1 }, cards: 4, wins: 3, map: FINAL },
  ],
  cardWeights: COMMON_WEIGHTS,
  winDrop: WIN_DROP,
};

export const LIGHT: DungeonDef = {
  id: "light",
  name: "LIGHT城",
  stars: 2,
  desc: "通路が明るい。飛び道具に注意。",
  bet: 10,
  win: 20,
  handSize: 10,
  rules: { litCorridors: true },
  floors: [
    { enemies: { puunya_g: 3, puunya_y: 2, kemunpa: 1 }, cards: 3, wins: 1, map: YUKAI_MAP },
    { enemies: { puunya_y: 3, killerbee: 2, kemunpa: 1 }, cards: 3, wins: 1, map: SHOP },
    { enemies: { killerbee: 3, kemunpa: 2 }, cards: 3, wins: 2, map: YUKAI_MAP, boss: "skeleton" },
    { enemies: { skeleton: 2, kemunpa: 3 }, cards: 3, wins: 2, map: FINAL },
  ],
  cardWeights: COMMON_WEIGHTS,
  winDrop: WIN_DROP,
};

export const VAGUE: DungeonDef = {
  id: "vague",
  name: "VAGUE城",
  stars: 3,
  desc: "敵は眠っている。数は多い。起こさなければ素通りできる。",
  bet: 10,
  win: 100,
  handSize: 10,
  rules: { dormantEnemies: true },
  floors: [
    { enemies: { killerbee: 5, skeleton: 4 }, cards: 3, wins: 2, map: YUKAI_MAP },
    { enemies: { skeleton: 5, kemunpa: 4 }, cards: 3, wins: 2, map: YUKAI_MAP },
    { enemies: { kemunpa: 4, goblin: 3 }, cards: 4, wins: 2, map: { ...YUKAI_MAP, shop: true }, boss: "goblin" },
    { enemies: { goblin: 5, mage: 4 }, cards: 4, wins: 3, map: YUKAI_MAP },
    { enemies: { mage: 5, goblin: 3, dragon: 1 }, cards: 4, wins: 3, map: FINAL },
  ],
  cardWeights: COMMON_WEIGHTS,
  winDrop: WIN_DROP,
};

export const CRUEL: DungeonDef = {
  id: "cruel",
  name: "CRUEL城",
  stars: 4,
  desc: "通路は酸の床: 一歩ごとに HP-1。敵も会心を出す。回復を厚く。",
  bet: 10,
  win: 160,
  handSize: 10,
  rules: { acidFloor: true, enemyCrit: 0.1 },
  floors: [
    { enemies: { killerbee: 3, skeleton: 3 }, cards: 4, wins: 2, map: YUKAI_MAP },
    { enemies: { skeleton: 3, kemunpa: 3 }, cards: 4, wins: 2, map: YUKAI_MAP },
    { enemies: { kemunpa: 3, goblin: 3 }, cards: 4, wins: 3, map: { ...YUKAI_MAP, shop: true }, boss: "mage" },
    { enemies: { goblin: 3, mage: 3 }, cards: 4, wins: 3, map: YUKAI_MAP },
    { enemies: { mage: 4, dragon: 1 }, cards: 4, wins: 4, map: FINAL },
  ],
  cardWeights: COMMON_WEIGHTS,
  winDrop: WIN_DROP,
};

export const TIGHT: DungeonDef = {
  id: "tight",
  name: "TIGHT城",
  stars: 5,
  desc: "手札は 6 枚まで。マップは記憶できない。ドラゴンが出る。",
  bet: 10,
  win: 240,
  handSize: 6,
  rules: { handSize: 6, dark: true },
  floors: [
    { enemies: { killerbee: 3, skeleton: 3 }, cards: 3, wins: 2, map: YUKAI_MAP },
    { enemies: { skeleton: 3, kemunpa: 3 }, cards: 3, wins: 2, map: YUKAI_MAP },
    { enemies: { kemunpa: 3, goblin: 3 }, cards: 4, wins: 3, map: YUKAI_MAP, boss: "goblin" },
    { enemies: { goblin: 3, mage: 3, dragon: 1 }, cards: 4, wins: 3, map: YUKAI_MAP },
    { enemies: { mage: 3, dragon: 2 }, cards: 4, wins: 4, map: FINAL, boss: "dragon" },
  ],
  cardWeights: COMMON_WEIGHTS,
  winDrop: WIN_DROP,
};

export const COLD: DungeonDef = {
  id: "cold",
  name: "COLD城",
  stars: 4,
  desc: "床が凍っている。滑り出すと止まれない。ショップとカジノあり。",
  bet: 10,
  win: 140,
  handSize: 10,
  rules: {},
  floors: [
    { enemies: { killerbee: 3, skeleton: 3 }, cards: 3, wins: 2, map: { ...YUKAI_MAP, ice: 2 } },
    { enemies: { skeleton: 3, kemunpa: 3 }, cards: 4, wins: 2, map: { ...YUKAI_MAP, ice: 2, shop: true } },
    { enemies: { kemunpa: 3, goblin: 3 }, cards: 4, wins: 3, map: { ...YUKAI_MAP, ice: 3 }, boss: "goblin" },
    { enemies: { goblin: 3, mage: 3 }, cards: 4, wins: 3, map: { ...YUKAI_MAP, ice: 3, casino: true } },
    { enemies: { mage: 3, goblin: 2, dragon: 1 }, cards: 4, wins: 4, map: { ...FINAL, ice: 3 } },
  ],
  cardWeights: COMMON_WEIGHTS,
  winDrop: WIN_DROP,
};

export const DUNGEON_LIST: DungeonDef[] = [LIGHT, YUKAI, VAGUE, COLD, CRUEL, TIGHT];
export const DUNGEONS: Record<string, DungeonDef> = Object.fromEntries(DUNGEON_LIST.map((d) => [d.id, d]));

export type ClassDef = {
  name: string;
  desc: string;
  hp: number;
  mp: number;
  maxMp: number;
  atk: number;
  def: number;
  crit: number;
  /** vision radius in corridors (the mage sees further) */
  corridorVision: number;
  /** multiplier on attack-card damage */
  magicMul: number;
  /** multiplier on potion healing */
  potionMul: number;
  /** weight multiplier for rare floor cards, and doubled ダブルアップ spawns */
  cardLuck: number;
  /** sees WIN / ダブルアップ / the goal on the minimap */
  treasureSight: boolean;
  /** better casino odds */
  luckyCasino: boolean;
};

export const CLASSES: Record<ClassId, ClassDef> = {
  warrior: {
    name: "戦士",
    desc: "攻守のバランスがよく基礎能力が高い。初心者向け。",
    hp: 30, mp: 30, maxMp: 100, atk: 8, def: 1, crit: 0.05,
    corridorVision: 1, magicMul: 1, potionMul: 1, cardLuck: 1, treasureSight: false, luckyCasino: false,
  },
  mage: {
    name: "魔法使い",
    desc: "攻撃力は低いが攻撃カード5割増し・ポーション25%増し。通路の視界が広い。",
    hp: 24, mp: 40, maxMp: 120, atk: 6, def: 1, crit: 0.05,
    corridorVision: 2, magicMul: 1.5, potionMul: 1.25, cardLuck: 1, treasureSight: false, luckyCasino: false,
  },
  gambler: {
    name: "ギャンブラー",
    desc: "打たれ弱いが高配当。宝とダブルアップの位置が見え、レアカードとカジノに恵まれる。",
    hp: 24, mp: 30, maxMp: 100, atk: 7, def: 0, crit: 0.08,
    corridorVision: 1, magicMul: 1, potionMul: 1, cardLuck: 3, treasureSight: true, luckyCasino: true,
  },
};

/** Kept for tests and defaults. */
export const WARRIOR = CLASSES.warrior;

export const CASINO = {
  bet: 5,
  maxSpins: 5,
  /** [payout multiple on the bet, weight] — the rest is a loss */
  table: [
    { mul: 2, weight: 20 },
    { mul: 4, weight: 7 },
    { mul: 10, weight: 3 },
    { mul: 0, weight: 70 },
  ],
  luckyTable: [
    { mul: 2, weight: 25 },
    { mul: 4, weight: 10 },
    { mul: 10, weight: 5 },
    { mul: 0, weight: 60 },
  ],
};

export const DOUBLE_UP = { chancePerFloor: 0.35, factor: 2 };

/** WIN paid out for a finished run. ダブルアップ only counts if you reach the altar. */
export function payoutFor(def: DungeonDef, o: { result: Exclude<DungeonResult, null>; winCollected: number; multiplier: number }): number {
  switch (o.result) {
    case "clear":
      return Math.round((def.win + o.winCollected) * o.multiplier);
    case "escaped":
      return o.winCollected;
    case "dead":
      return Math.floor((def.win + o.winCollected) * RULES.deathRefund);
  }
}

export const RULES = {
  playerCrit: 0.05,
  bossHpMul: 2.5,
  bossAtkMul: 1.3,
  bossAttackChance: 0.5,
  reviveRatio: 0.5,
  litCorridorRadius: 3,
  roomHpGain: 5,
  roomMpGain: 10,
  spawnAfterTurns: 40,
  spawnEvery: 15,
  spawnCap: 6,
  rangedRange: 6,
  cardRange: 5,
  deathRefund: 0.5,
};
