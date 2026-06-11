import { describe, expect, it } from 'vitest'
import { applyXp, MAX_LEVEL, statsAtLevel, xpGainForDefeating, xpToNext } from './progression'
import { getSpecies } from './data/creatures'

describe('statsAtLevel', () => {
  it('returns base stats at level 1', () => {
    const base = getSpecies('nikokka').baseStats
    expect(statsAtLevel(base, 1)).toEqual(base)
  })

  it('matches hand-computed scaling at level 5', () => {
    const base = getSpecies('nikokka').baseStats // hp44 atk12 def10 spd12
    const at5 = statsAtLevel(base, 5)
    expect(at5.hp).toBe(62) // 44 * 1.4 = 61.6 -> 62
    expect(at5.attack).toBe(15) // 12 * 1.24 = 14.88 -> 15
    expect(at5.defense).toBe(12) // 10 * 1.24 = 12.4 -> 12
    expect(at5.speed).toBe(15)
  })

  it('clamps levels beyond MAX_LEVEL', () => {
    const base = getSpecies('wombolt').baseStats
    expect(statsAtLevel(base, MAX_LEVEL + 10)).toEqual(statsAtLevel(base, MAX_LEVEL))
  })
})

describe('xp curve', () => {
  it('grows with level', () => {
    expect(xpToNext(1)).toBe(25)
    expect(xpToNext(5)).toBe(65)
    expect(xpToNext(10)).toBeGreaterThan(xpToNext(5))
  })

  it('rewards more for higher-level wilds', () => {
    expect(xpGainForDefeating(3)).toBe(42)
    expect(xpGainForDefeating(9)).toBeGreaterThan(xpGainForDefeating(3))
  })
})

describe('applyXp', () => {
  it('accumulates without leveling below the threshold', () => {
    expect(applyXp(5, 0, 30)).toEqual({ level: 5, xp: 30, levelsGained: 0 })
  })

  it('levels up and carries the overflow', () => {
    // level 5 needs 65: 50 + 42 = 92 -> level 6 with 27 left
    expect(applyXp(5, 50, 42)).toEqual({ level: 6, xp: 27, levelsGained: 1 })
  })

  it('can gain multiple levels at once', () => {
    // level 1 needs 25, level 2 needs 35: 100 -> level 3 with 40 left
    expect(applyXp(1, 0, 100)).toEqual({ level: 3, xp: 40, levelsGained: 2 })
  })

  it('stops at MAX_LEVEL', () => {
    const result = applyXp(MAX_LEVEL, 0, 10_000)
    expect(result.level).toBe(MAX_LEVEL)
    expect(result.levelsGained).toBe(0)
  })
})
