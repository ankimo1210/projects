import type { CardId } from "./types";

export type CardTarget = "self" | "dir" | "none";

/** Presentation only: groups cards by what they do, which drives the frame colour. */
export type CardFamily = "heal" | "fire" | "bolt" | "status" | "scout" | "buff" | "special" | "summon";
export type CardRarity = "common" | "rare" | "epic";

export type CardDef = {
  name: string;
  mp: number;
  target: CardTarget;
  desc: string;
  /** shop price in WIN, undefined = not for sale */
  price?: number;
  family: CardFamily;
  rarity: CardRarity;
};

export const CARDS: Record<CardId, CardDef> = {
  potion20: { name: "ポーション20", mp: 2, target: "self", desc: "HP +20", price: 5, family: "heal", rarity: "common" },
  potion40: { name: "ポーション40", mp: 4, target: "self", desc: "HP +40", price: 9, family: "heal", rarity: "common" },
  potion80: { name: "ポーション80", mp: 8, target: "self", desc: "HP +80", family: "heal", rarity: "rare" },
  fire: { name: "ファイア", mp: 3, target: "dir", desc: "直線5マスの敵に15", price: 6, family: "fire", rarity: "common" },
  multiFire: { name: "マルチファイア", mp: 6, target: "none", desc: "見える敵全てに15", price: 12, family: "fire", rarity: "rare" },
  thunder: { name: "サンダー", mp: 6, target: "dir", desc: "直線5マスの敵に30", price: 12, family: "bolt", rarity: "rare" },
  sleep: { name: "スリープ", mp: 3, target: "dir", desc: "直線5マスの敵を8T睡眠", family: "status", rarity: "common" },
  haste: { name: "ヘイスト", mp: 4, target: "self", desc: "4行動の間、敵は2回に1回だけ動く", family: "buff", rarity: "common" },
  bright: { name: "ブライト", mp: 3, target: "self", desc: "このフロアが全て見える", family: "scout", rarity: "common" },
  warp: { name: "ワープ", mp: 2, target: "self", desc: "ランダムな場所へ移動", family: "scout", rarity: "common" },
  escape: { name: "エスケープ", mp: 5, target: "self", desc: "手札とWINを持って脱出", family: "scout", rarity: "rare" },
  bronzeSword: { name: "ブロンズソード", mp: 5, target: "self", desc: "このダンジョン中 攻撃+4", family: "buff", rarity: "common" },
  multiThunder: { name: "マルチサンダー", mp: 12, target: "none", desc: "見える敵全てに30", family: "bolt", rarity: "epic" },
  meteor: { name: "メテオ", mp: 10, target: "dir", desc: "直線5マスの敵に60", family: "fire", rarity: "epic" },
  panic: { name: "パニック", mp: 3, target: "dir", desc: "直線5マスの敵を6T混乱", family: "status", rarity: "rare" },
  multiPanic: { name: "マルチパニック", mp: 6, target: "none", desc: "見える敵全てを6T混乱", family: "status", rarity: "epic" },
  search: { name: "サーチ", mp: 3, target: "self", desc: "このフロアの敵の位置が分かる", family: "scout", rarity: "common" },
  map: { name: "マップ", mp: 3, target: "self", desc: "このフロアの地形とカードが分かる", family: "scout", rarity: "common" },
  regen: { name: "リジェネ", mp: 3, target: "self", desc: "100T の間 毎ターン HP+1", family: "heal", rarity: "rare" },
  longSword: { name: "ロングソード", mp: 8, target: "self", desc: "このダンジョン中 攻撃+8", family: "buff", rarity: "epic" },
  powerShield: { name: "パワーシールド", mp: 6, target: "self", desc: "このダンジョン中 防御+4", family: "buff", rarity: "rare" },
  pocket2: { name: "ポケット+2", mp: 4, target: "self", desc: "手札の上限+2（1回まで）", family: "special", rarity: "rare" },
  reviveRing: { name: "リバイブリング", mp: 6, target: "self", desc: "倒れたとき1度だけ HP半分で復活", family: "special", rarity: "epic" },
  powerUp: { name: "パワーアップ", mp: 12, target: "self", desc: "レベル+10、HP+10", family: "buff", rarity: "epic" },
  summonGoblin: { name: "モンスター:ゴブリン", mp: 6, target: "self", desc: "ゴブリンを召喚して連れ歩く", family: "summon", rarity: "rare" },
  summonDragon: { name: "モンスター:ドラゴン", mp: 14, target: "self", desc: "ドラゴンを召喚して連れ歩く", family: "summon", rarity: "epic" },
};

/** What a card costs at a shop found inside a dungeon (paid with collected WIN). */
export function dungeonPrice(card: CardId): number {
  return Math.max(4, CARDS[card].mp * 2);
}

export const CARD_EFFECT = {
  potion20: 20,
  potion40: 40,
  potion80: 80,
  fireDamage: 15,
  thunderDamage: 30,
  meteorDamage: 60,
  sleepTurns: 8,
  panicTurns: 6,
  hasteTurns: 4,
  regenTurns: 100,
  bronzeSwordBonus: 4,
  longSwordBonus: 8,
  powerShieldBonus: 4,
  pocketBonus: 2,
  powerUpLevels: 10,
  powerUpHeal: 10,
  allyCap: 2,
} as const;

/** Guaranteed drop from a boss. */
export const BOSS_DROPS: { item: CardId; weight: number }[] = [
  { item: "meteor", weight: 3 },
  { item: "multiThunder", weight: 3 },
  { item: "multiPanic", weight: 3 },
  { item: "longSword", weight: 2 },
  { item: "powerShield", weight: 2 },
  { item: "reviveRing", weight: 2 },
  { item: "pocket2", weight: 2 },
  { item: "potion80", weight: 3 },
  { item: "regen", weight: 2 },
  { item: "powerUp", weight: 2 },
  { item: "summonDragon", weight: 2 },
];

export const CARD_IDS = Object.keys(CARDS) as CardId[];
