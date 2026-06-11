import { describe, expect, it } from 'vitest'
import { CREATURES, MOVES, SPECIES_BY_ID, STARTER_SPECIES_ID } from './creatures'

describe('creature data integrity', () => {
  it('has exactly 20 species', () => {
    expect(CREATURES).toHaveLength(20)
  })

  it('has unique ids, dex numbers and names', () => {
    const ids = new Set(CREATURES.map((c) => c.id))
    const dexNos = new Set(CREATURES.map((c) => c.dexNo))
    const names = new Set(CREATURES.map((c) => c.name))
    expect(ids.size).toBe(20)
    expect(dexNos.size).toBe(20)
    expect(names.size).toBe(20)
  })

  it('numbers dex entries 1..20', () => {
    const sorted = [...CREATURES].map((c) => c.dexNo).sort((a, b) => a - b)
    expect(sorted).toEqual(Array.from({ length: 20 }, (_, i) => i + 1))
  })

  it('references only existing moves', () => {
    for (const c of CREATURES) {
      for (const moveId of c.moveIds) {
        expect(MOVES[moveId], `${c.id} -> ${moveId}`).toBeDefined()
      }
    }
  })

  it('has positive stats and sane ranges', () => {
    for (const c of CREATURES) {
      expect(c.baseStats.hp).toBeGreaterThan(0)
      expect(c.baseStats.attack).toBeGreaterThan(0)
      expect(c.baseStats.defense).toBeGreaterThan(0)
      expect(c.baseStats.speed).toBeGreaterThan(0)
      expect(c.friendliness).toBeGreaterThan(0)
      expect(c.friendliness).toBeLessThanOrEqual(1)
      expect(c.size).toBeGreaterThan(0)
    }
  })

  it('uses valid hex palettes', () => {
    const hex = /^#[0-9a-f]{6}$/i
    for (const c of CREATURES) {
      expect(c.palette.primary).toMatch(hex)
      expect(c.palette.secondary).toMatch(hex)
      expect(c.palette.accent).toMatch(hex)
    }
  })

  it('includes the starter Nikokka', () => {
    expect(SPECIES_BY_ID[STARTER_SPECIES_ID]?.name).toBe('Nikokka')
    expect(SPECIES_BY_ID[STARTER_SPECIES_ID]?.inspiration).toBe('quokka')
  })

  it('move accuracies are within (0, 1]', () => {
    for (const move of Object.values(MOVES)) {
      expect(move.accuracy).toBeGreaterThan(0)
      expect(move.accuracy).toBeLessThanOrEqual(1)
      expect(move.power).toBeGreaterThan(0)
    }
  })
})
