import { afterEach, describe, expect, it, vi } from 'vitest'
import { maxHpOf, useGameStore, type PartyMember } from './gameStore'
import { createBattle } from '../battle'
import { STARTER_SPECIES_ID } from '../data/creatures'
import { ZONE_LEVEL_RANGES } from '../data/world'

const STARTER_UID = 'starter-test'

function testStarter(): PartyMember {
  return {
    uid: STARTER_UID,
    speciesId: STARTER_SPECIES_ID,
    level: 5,
    xp: 0,
    hp: maxHpOf({ speciesId: STARTER_SPECIES_ID, level: 5 }),
  }
}

function resetStore() {
  useGameStore.setState({
    mode: 'explore',
    battle: null,
    battleSpawnKey: null,
    battleMemberUid: null,
    collection: { [STARTER_SPECIES_ID]: { seen: true, recruited: true } },
    party: [testStarter()],
    activeUid: STARTER_UID,
    encounterCooldownUntil: 0,
    notice: null,
  })
}

afterEach(() => {
  vi.restoreAllMocks()
  resetStore()
})

describe('gameStore party & spawns', () => {
  it('starts with the starter in the party and leveled spawns in every zone', () => {
    const state = useGameStore.getState()
    expect(state.wildSpawns.length).toBeGreaterThanOrEqual(5)
    const zones = new Set(state.wildSpawns.map((s) => s.zoneId))
    expect(zones.size).toBe(3)
    for (const spawn of state.wildSpawns) {
      const [min, max] = ZONE_LEVEL_RANGES[spawn.zoneId]
      expect(spawn.level).toBeGreaterThanOrEqual(min)
      expect(spawn.level).toBeLessThanOrEqual(max)
    }
  })

  it('rests the whole party at the well', () => {
    resetStore()
    useGameStore.setState({
      party: [{ ...testStarter(), hp: 3 }],
    })
    useGameStore.getState().restParty()
    const member = useGameStore.getState().party[0]
    expect(member.hp).toBe(maxHpOf(member))
    expect(useGameStore.getState().notice).toContain('rested')
  })

  it('refuses to make a fainted member active', () => {
    resetStore()
    const fainted: PartyMember = { ...testStarter(), uid: 'fainted', hp: 0 }
    useGameStore.setState({ party: [testStarter(), fainted] })
    useGameStore.getState().setActive('fainted')
    expect(useGameStore.getState().activeUid).toBe(STARTER_UID)
  })
})

describe('gameStore battle flow', () => {
  it('startEncounter builds a leveled battle from the active member', () => {
    resetStore()
    const spawn = useGameStore.getState().wildSpawns[0]
    useGameStore.getState().startEncounter(spawn.key)
    const state = useGameStore.getState()
    expect(state.mode).toBe('battle')
    expect(state.battle?.player.level).toBe(5)
    expect(state.battle?.wild.level).toBe(spawn.level)
    expect(state.battleMemberUid).toBe(STARTER_UID)
    expect(state.collection[spawn.speciesId]?.seen).toBe(true)
  })

  it('does not start an encounter outside explore mode', () => {
    resetStore()
    const spawn = useGameStore.getState().wildSpawns[0]
    useGameStore.setState({ mode: 'collection' })
    useGameStore.getState().startEncounter(spawn.key)
    expect(useGameStore.getState().battle).toBeNull()
  })

  it('winning grants XP to the fighter', () => {
    resetStore()
    const spawn = useGameStore.getState().wildSpawns[0]
    useGameStore.getState().startEncounter(spawn.key)
    const battle = createBattle(
      { speciesId: STARTER_SPECIES_ID, level: 5 },
      { speciesId: spawn.speciesId, level: spawn.level },
    )
    battle.wild.hp = 1
    useGameStore.setState({ battle })
    vi.spyOn(Math, 'random').mockReturnValue(0.5)
    useGameStore.getState().battleAction({ type: 'move', moveId: battle.player.moveIds[0] })

    const state = useGameStore.getState()
    expect(state.battle?.outcome).toBe('win')
    const fighter = state.party[0]
    expect(fighter.level > 5 || fighter.xp > 0).toBe(true)
    expect(state.battle?.log.join(' ')).toContain('XP')

    useGameStore.getState().closeBattle()
    expect(useGameStore.getState().wildSpawns.find((s) => s.key === spawn.key)).toBeUndefined()
  })

  it('a recruited creature joins the party at its wild level', () => {
    resetStore()
    const spawn = useGameStore.getState().wildSpawns[0]
    useGameStore.getState().startEncounter(spawn.key)
    vi.spyOn(Math, 'random').mockReturnValue(0) // Friend Link succeeds
    useGameStore.getState().battleAction({ type: 'link' })
    expect(useGameStore.getState().battle?.outcome).toBe('recruited')

    useGameStore.getState().closeBattle()
    const state = useGameStore.getState()
    expect(state.mode).toBe('explore')
    expect(state.party).toHaveLength(2)
    expect(state.party[1].speciesId).toBe(spawn.speciesId)
    expect(state.party[1].level).toBe(spawn.level)
    expect(state.collection[spawn.speciesId]?.recruited).toBe(true)
  })

  it('a total wipe rescues the party back to full hp', () => {
    resetStore()
    const spawn = useGameStore.getState().wildSpawns[0]
    useGameStore.getState().startEncounter(spawn.key)
    const battle = createBattle(
      { speciesId: STARTER_SPECIES_ID, level: 5, hp: 1 },
      { speciesId: 'wombolt', level: 3 },
    )
    useGameStore.setState({ battle })
    vi.spyOn(Math, 'random').mockReturnValue(0.5)
    useGameStore.getState().battleAction({ type: 'move', moveId: battle.player.moveIds[1] })
    expect(useGameStore.getState().battle?.outcome).toBe('lose')
    expect(useGameStore.getState().party[0].hp).toBe(0)

    useGameStore.getState().closeBattle()
    const state = useGameStore.getState()
    expect(state.mode).toBe('explore')
    expect(state.party[0].hp).toBe(maxHpOf(state.party[0]))
    expect(state.notice).toContain('carried back')
  })

  it('fleeing keeps the same species and level in the zone and sets a cooldown', () => {
    resetStore()
    const spawn = useGameStore.getState().wildSpawns[0]
    useGameStore.getState().startEncounter(spawn.key)
    vi.spyOn(Math, 'random').mockReturnValue(0) // flee succeeds
    useGameStore.getState().battleAction({ type: 'flee' })
    expect(useGameStore.getState().battle?.outcome).toBe('fled')

    useGameStore.getState().closeBattle()
    const state = useGameStore.getState()
    const relocated = state.wildSpawns.find(
      (s) =>
        s.zoneId === spawn.zoneId && s.speciesId === spawn.speciesId && s.level === spawn.level,
    )
    expect(relocated).toBeDefined()
    expect(state.encounterCooldownUntil).toBeGreaterThan(Date.now() - 100)
  })
})

describe('gameStore dialog flow', () => {
  it('walks through NPC lines and returns to explore', () => {
    resetStore()
    useGameStore.getState().startDialog('maro')
    expect(useGameStore.getState().mode).toBe('dialog')
    // Elder Maro has 4 lines
    for (let i = 0; i < 4; i++) useGameStore.getState().advanceDialog()
    const state = useGameStore.getState()
    expect(state.mode).toBe('explore')
    expect(state.dialogNpcId).toBeNull()
  })
})
