/**
 * Leveling and XP rules. Pure functions, no state.
 *
 * - Stats scale linearly from base stats (level 1 = base).
 * - XP-to-next grows linearly; overflow carries into the next level.
 */
import type { BaseStats } from './data/creatures'

export const MAX_LEVEL = 30

/** XP required to advance from `level` to `level + 1`. */
export function xpToNext(level: number): number {
  return 15 + level * 10
}

/** Stats at a given level; level 1 equals the species base stats. */
export function statsAtLevel(base: BaseStats, level: number): BaseStats {
  const l = Math.max(1, Math.min(MAX_LEVEL, level))
  return {
    hp: Math.round(base.hp * (1 + 0.1 * (l - 1))),
    attack: Math.round(base.attack * (1 + 0.06 * (l - 1))),
    defense: Math.round(base.defense * (1 + 0.06 * (l - 1))),
    speed: Math.round(base.speed * (1 + 0.06 * (l - 1))),
  }
}

/** XP awarded for defeating (or befriending) a wild creature of this level. */
export function xpGainForDefeating(wildLevel: number): number {
  return 18 + wildLevel * 8
}

export interface LevelUpResult {
  level: number
  xp: number
  levelsGained: number
}

/** Add XP, consuming level-ups as thresholds are crossed. */
export function applyXp(level: number, xp: number, gain: number): LevelUpResult {
  let l = level
  let x = xp + gain
  let levelsGained = 0
  while (l < MAX_LEVEL && x >= xpToNext(l)) {
    x -= xpToNext(l)
    l += 1
    levelsGained += 1
  }
  if (l >= MAX_LEVEL) x = 0
  return { level: l, xp: x, levelsGained }
}
