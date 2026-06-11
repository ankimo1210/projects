import { describe, expect, it } from 'vitest'
import {
  attemptFlee,
  attemptFriendLink,
  computeDamage,
  createBattle,
  elementMultiplier,
  fleeChance,
  friendLinkChance,
  makeBattleCreature,
  playerAttack,
  type BattleState,
} from './battle'
import { getSpecies, MOVES } from './data/creatures'

/** rng that returns queued values, then 0.5 forever */
function seqRng(values: number[]): () => number {
  let i = 0
  return () => (i < values.length ? values[i++] : 0.5)
}

describe('elementMultiplier', () => {
  it('applies the leaf > tide > ember > leaf cycle', () => {
    expect(elementMultiplier('leaf', 'tide')).toBe(1.5)
    expect(elementMultiplier('tide', 'ember')).toBe(1.5)
    expect(elementMultiplier('ember', 'leaf')).toBe(1.5)
    expect(elementMultiplier('tide', 'leaf')).toBe(0.75)
  })

  it('applies the spark > breeze > stone > spark cycle', () => {
    expect(elementMultiplier('spark', 'breeze')).toBe(1.5)
    expect(elementMultiplier('breeze', 'stone')).toBe(1.5)
    expect(elementMultiplier('stone', 'spark')).toBe(1.5)
  })

  it('is neutral across cycles and for neutral moves', () => {
    expect(elementMultiplier('leaf', 'spark')).toBe(1)
    expect(elementMultiplier('neutral', 'leaf')).toBe(1)
  })
})

describe('computeDamage', () => {
  it('matches the hand-computed formula', () => {
    const attacker = makeBattleCreature(getSpecies('nikokka'), 1) // atk 12, leaf
    const defender = makeBattleCreature(getSpecies('shellbrook'), 1) // def 16, tide
    // leaf_lash power 11, leaf vs tide = 1.5, rng 0 -> variance 0.85
    // 11 * (12/16) * 1.5 * 0.85 = 10.51875 -> round 11
    const dmg = computeDamage(attacker, defender, MOVES.leaf_lash, seqRng([0]))
    expect(dmg).toBe(11)
  })

  it('never deals less than 1', () => {
    const weak = makeBattleCreature(getSpecies('shellbrook'), 1) // atk 9
    const tank = { ...makeBattleCreature(getSpecies('wombolt'), 1), defense: 1000 }
    const dmg = computeDamage(weak, tank, MOVES.nuzzle, seqRng([0]))
    expect(dmg).toBe(1)
  })
})

describe('playerAttack', () => {
  it('damages the wild creature and triggers a counterattack', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    // rng: player hit roll (<=acc), player variance, wild move pick, wild hit roll, wild variance
    const next = playerAttack(state, 'leaf_lash', seqRng([0, 0.5, 0, 0, 0.5]))
    expect(next.wild.hp).toBeLessThan(next.wild.maxHp)
    expect(next.player.hp).toBeLessThan(next.player.maxHp)
    expect(next.outcome).toBe('ongoing')
  })

  it('wins when the wild creature faints, skipping the counterattack', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    state.wild.hp = 1
    const next = playerAttack(state, 'leaf_lash', seqRng([0, 0.5]))
    expect(next.outcome).toBe('win')
    expect(next.player.hp).toBe(next.player.maxHp)
    expect(next.log.at(-1)).toContain('fainted')
  })

  it('loses when the counterattack drops the player to 0', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    state.player.hp = 1
    const next = playerAttack(state, 'nuzzle', seqRng([0, 0.5, 0, 0, 0.5]))
    expect(next.outcome).toBe('lose')
  })

  it('a missed move deals no damage', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    // leaf_lash accuracy 0.95 -> roll 0.99 misses; then wild turn rolls
    const next = playerAttack(state, 'leaf_lash', seqRng([0.99, 0, 0, 0.5]))
    expect(next.wild.hp).toBe(next.wild.maxHp)
    expect(next.log.join(' ')).toContain('missed')
  })

  it('rejects moves the player does not know', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    expect(() => playerAttack(state, 'boulder_roll', seqRng([0]))).toThrow()
  })

  it('is a no-op once the battle has ended', () => {
    const state: BattleState = { ...createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 }), outcome: 'win' }
    expect(playerAttack(state, 'leaf_lash', seqRng([0]))).toBe(state)
  })
})

describe('friend link', () => {
  it('chance rises as the wild creature weakens', () => {
    const full = makeBattleCreature(getSpecies('wombolt'), 1)
    const hurt = { ...full, hp: Math.floor(full.maxHp / 4) }
    expect(friendLinkChance(hurt)).toBeGreaterThan(friendLinkChance(full))
  })

  it('chance is clamped to [0.05, 0.95]', () => {
    const shy = { ...makeBattleCreature(getSpecies('gnashling'), 1), friendliness: 0.01 }
    expect(friendLinkChance(shy)).toBe(0.05)
    const eager = { ...makeBattleCreature(getSpecies('nikokka'), 1), hp: 1 }
    expect(friendLinkChance(eager)).toBeLessThanOrEqual(0.95)
  })

  it('success recruits the wild creature', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'gumdrowse', level: 1 })
    const next = attemptFriendLink(state, seqRng([0]))
    expect(next.outcome).toBe('recruited')
  })

  it('failure costs a turn (wild counterattacks)', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'gumdrowse', level: 1 })
    const next = attemptFriendLink(state, seqRng([0.999, 0, 0, 0.5]))
    expect(next.outcome).toBe('ongoing')
    expect(next.player.hp).toBeLessThan(next.player.maxHp)
  })
})

describe('battle events', () => {
  it('a plain exchange emits hit events for both sides, matching new log lines', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    const before = state.log.length
    const next = playerAttack(state, 'leaf_lash', seqRng([0, 0.5, 0, 0, 0.5]))
    expect(next.events.map((e) => e.kind)).toEqual(['hit', 'hit'])
    expect(next.events[0]).toMatchObject({ kind: 'hit', target: 'wild', hp: next.wild.hp })
    expect(next.events[1]).toMatchObject({ kind: 'hit', target: 'player', hp: next.player.hp })
    // one log line per event
    expect(next.log.length - before).toBe(next.events.length)
  })

  it('a knockout emits hit then faint and stops there', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    state.wild.hp = 1
    const next = playerAttack(state, 'leaf_lash', seqRng([0, 0.5]))
    expect(next.events.map((e) => e.kind)).toEqual(['hit', 'faint'])
    expect(next.events[1]).toMatchObject({ target: 'wild' })
  })

  it('a miss emits a miss event with the right attacker', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    const next = playerAttack(state, 'leaf_lash', seqRng([0.99, 0, 0, 0.5]))
    expect(next.events[0]).toMatchObject({ kind: 'miss', attacker: 'player' })
  })

  it('events reset between actions', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    const first = playerAttack(state, 'leaf_lash', seqRng([0, 0.5, 0, 0, 0.5]))
    const second = attemptFlee(first, seqRng([0]))
    expect(second.events).toEqual([{ kind: 'flee', success: true }])
  })

  it('marks strong hits as effective', () => {
    // leaf vs tide is strong
    const state = createBattle({ speciesId: 'nikokka', level: 5 }, { speciesId: 'shellbrook', level: 1 })
    const next = playerAttack(state, 'leaf_lash', seqRng([0, 0.5, 0, 0, 0.5]))
    expect(next.events[0]).toMatchObject({ kind: 'hit', effective: 'strong' })
  })
})

describe('flee', () => {
  it('chance favors faster players and is clamped', () => {
    const fast = makeBattleCreature(getSpecies('glidewisp'), 1) // speed 15
    const slow = makeBattleCreature(getSpecies('shellbrook'), 1) // speed 4
    expect(fleeChance(fast, slow)).toBeGreaterThan(fleeChance(slow, fast))
    expect(fleeChance(slow, fast)).toBeGreaterThanOrEqual(0.25)
    expect(fleeChance(fast, slow)).toBeLessThanOrEqual(0.95)
  })

  it('success ends the battle as fled', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    const next = attemptFlee(state, seqRng([0]))
    expect(next.outcome).toBe('fled')
  })

  it('failure costs a turn', () => {
    const state = createBattle({ speciesId: 'nikokka', level: 1 }, { speciesId: 'wombolt', level: 1 })
    const next = attemptFlee(state, seqRng([0.999, 0, 0, 0.5]))
    expect(next.outcome).toBe('ongoing')
    expect(next.player.hp).toBeLessThan(next.player.maxHp)
  })
})
