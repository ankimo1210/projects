import { ENEMY, LEVELING } from "./dungeon-def";
import type { Rng } from "./rng";
import type { EnemyKind, Player } from "./types";

export function meleeDamage(rng: Rng, atk: number, def: number, critChance: number): { dmg: number; crit: boolean } {
  const base = atk - def + rng.int(-1, 1);
  const crit = rng.chance(critChance);
  const dmg = Math.max(1, base) * (crit ? 2 : 1);
  return { dmg, crit };
}

/** Ranged hits are divided by distance (d >= 1). */
export function rangedDamage(atk: number, def: number, d: number): number {
  return Math.max(1, Math.floor((atk - def) / Math.max(1, d)));
}

export function playerAtk(p: Player): number {
  return p.atk + p.equipment.weaponBonus;
}

export function playerDef(p: Player): number {
  return p.def + p.equipment.shieldBonus;
}

export type Gains = { level: number; hp: number; atk: number; def: number };

/** Award XP for a kill and apply any level-ups. Trivial kills give nothing. */
export function gainXp(p: Player, kind: EnemyKind): { player: Player; gains: Gains } {
  const e = ENEMY[kind];
  const gains: Gains = { level: 0, hp: 0, atk: 0, def: 0 };
  if (p.level > e.trivialAt || p.level >= LEVELING.maxLevel) return { player: p, gains };
  let { level, xp } = p;
  xp += e.xp;
  while (level < LEVELING.maxLevel && xp >= LEVELING.xpToNext(level)) {
    xp -= LEVELING.xpToNext(level);
    level++;
    addLevelGains(gains, level);
  }
  return { player: applyGains({ ...p, level, xp }, gains), gains };
}

/** Raise the level by `n` outright (パワーアップ). */
export function levelUp(p: Player, n: number): { player: Player; gains: Gains } {
  const gains: Gains = { level: 0, hp: 0, atk: 0, def: 0 };
  let level = p.level;
  for (let i = 0; i < n && level < LEVELING.maxLevel; i++) {
    level++;
    addLevelGains(gains, level);
  }
  return { player: applyGains({ ...p, level }, gains), gains };
}

function addLevelGains(g: Gains, newLevel: number): void {
  g.level++;
  g.hp += LEVELING.hpPerLevel;
  if (newLevel % LEVELING.atkEvery === 0) g.atk++;
  if (newLevel % LEVELING.defEvery === 0) g.def++;
}

function applyGains(p: Player, g: Gains): Player {
  return { ...p, maxHp: p.maxHp + g.hp, hp: p.hp + g.hp, atk: p.atk + g.atk, def: p.def + g.def };
}
