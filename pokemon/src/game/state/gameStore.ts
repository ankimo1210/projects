import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  attemptFlee,
  attemptFriendLink,
  createBattle,
  playerAttack,
  type BattleEvent,
  type BattleState,
} from '../battle'
import { CREATURES, getSpecies, STARTER_SPECIES_ID } from '../data/creatures'
import { GRASS_ZONES, ZONE_LEVEL_RANGES } from '../data/world'
import { NPC_BY_ID } from '../data/npcs'
import { pointInCircle } from '../utils/random'
import { applyXp, statsAtLevel, xpGainForDefeating } from '../progression'

export type GameMode = 'explore' | 'dialog' | 'battle' | 'collection'

export interface CollectionEntry {
  seen: boolean
  recruited: boolean
}

/** One creature in the player's party. HP persists between battles. */
export interface PartyMember {
  uid: string
  speciesId: string
  level: number
  /** progress toward the next level */
  xp: number
  hp: number
}

export interface WildSpawn {
  key: number
  speciesId: string
  level: number
  x: number
  z: number
  zoneId: string
}

export type BattleAction =
  | { type: 'move'; moveId: string }
  | { type: 'link' }
  | { type: 'flee' }

export const MAX_PARTY = 6
const SPAWNS_PER_ZONE = 3
const STARTER_LEVEL = 5

let nextSpawnKey = 1

export function maxHpOf(member: Pick<PartyMember, 'speciesId' | 'level'>): number {
  return statsAtLevel(getSpecies(member.speciesId).baseStats, member.level).hp
}

function newMember(speciesId: string, level: number, hp?: number): PartyMember {
  const max = statsAtLevel(getSpecies(speciesId).baseStats, level).hp
  return {
    uid: crypto.randomUUID(),
    speciesId,
    level,
    xp: 0,
    hp: Math.max(1, Math.min(hp ?? max, max)),
  }
}

function zoneSpecies(zoneId: string): string[] {
  return CREATURES.filter(
    (c) => c.id !== STARTER_SPECIES_ID && (c.habitat === zoneId || c.habitat === 'anywhere'),
  ).map((c) => c.id)
}

function makeSpawn(zoneId: string): WildSpawn {
  const zone = GRASS_ZONES.find((z) => z.id === zoneId)
  if (!zone) throw new Error(`Unknown grass zone: ${zoneId}`)
  const candidates = zoneSpecies(zoneId)
  const speciesId = candidates[Math.floor(Math.random() * candidates.length)]
  const [minL, maxL] = ZONE_LEVEL_RANGES[zoneId] ?? [2, 4]
  const level = minL + Math.floor(Math.random() * (maxL - minL + 1))
  const [x, z] = pointInCircle(Math.random, zone.x, zone.z, zone.radius - 1)
  return { key: nextSpawnKey++, speciesId, level, x, z, zoneId }
}

function initialSpawns(): WildSpawn[] {
  return GRASS_ZONES.flatMap((zone) =>
    Array.from({ length: SPAWNS_PER_ZONE }, () => makeSpawn(zone.id)),
  )
}

function starterCollection(): Record<string, CollectionEntry> {
  return { [STARTER_SPECIES_ID]: { seen: true, recruited: true } }
}

function starterParty(): PartyMember[] {
  return [newMember(STARTER_SPECIES_ID, STARTER_LEVEL)]
}

interface GameState {
  mode: GameMode
  collection: Record<string, CollectionEntry>
  party: PartyMember[]
  /** uid of the member who fights and walks beside the player */
  activeUid: string
  battle: BattleState | null
  battleSpawnKey: number | null
  /** uid of the member currently in battle */
  battleMemberUid: string | null
  wildSpawns: WildSpawn[]
  /** wall-clock ms; encounters are suppressed until this passes */
  encounterCooldownUntil: number
  dialogNpcId: string | null
  dialogLineIndex: number
  /** NPC currently in talking range (explore mode) */
  nearbyNpcId: string | null
  /** true while the player stands next to the village well */
  nearWell: boolean
  /** transient HUD toast */
  notice: string | null

  startEncounter: (spawnKey: number) => void
  battleAction: (action: BattleAction) => void
  closeBattle: () => void
  toggleCollection: () => void
  startDialog: (npcId: string) => void
  advanceDialog: () => void
  setNearbyNpc: (npcId: string | null) => void
  setNearWell: (near: boolean) => void
  setActive: (uid: string) => void
  restParty: () => void
  showNotice: (text: string) => void
}

let noticeSeq = 0

export const useGameStore = create<GameState>()(
  persist(
    (set, get) => ({
      mode: 'explore',
      collection: starterCollection(),
      party: starterParty(),
      activeUid: '',
      battle: null,
      battleSpawnKey: null,
      battleMemberUid: null,
      wildSpawns: initialSpawns(),
      encounterCooldownUntil: 0,
      dialogNpcId: null,
      dialogLineIndex: 0,
      nearbyNpcId: null,
      nearWell: false,
      notice: null,

      showNotice: (text) => {
        const id = ++noticeSeq
        set({ notice: text })
        setTimeout(() => {
          if (noticeSeq === id) set({ notice: null })
        }, 2600)
      },

      setNearbyNpc: (npcId) => {
        if (get().nearbyNpcId !== npcId) set({ nearbyNpcId: npcId })
      },

      setNearWell: (near) => {
        if (get().nearWell !== near) set({ nearWell: near })
      },

      setActive: (uid) => {
        const { mode, party } = get()
        if (mode !== 'explore') return
        const member = party.find((m) => m.uid === uid)
        if (!member) return
        if (member.hp <= 0) {
          get().showNotice(`${getSpecies(member.speciesId).name} needs rest first!`)
          return
        }
        set({ activeUid: uid })
      },

      restParty: () => {
        const { party } = get()
        set({ party: party.map((m) => ({ ...m, hp: maxHpOf(m) })) })
        get().showNotice('Your party rested by the well — everyone is fully healed!')
      },

      startEncounter: (spawnKey) => {
        const state = get()
        if (state.mode !== 'explore') return
        const spawn = state.wildSpawns.find((s) => s.key === spawnKey)
        if (!spawn) return
        // the active member fights; fall back to the first healthy one
        const fighter =
          state.party.find((m) => m.uid === state.activeUid && m.hp > 0) ??
          state.party.find((m) => m.hp > 0)
        if (!fighter) return
        set({
          mode: 'battle',
          battle: createBattle(
            { speciesId: fighter.speciesId, level: fighter.level, hp: fighter.hp },
            { speciesId: spawn.speciesId, level: spawn.level },
          ),
          battleSpawnKey: spawnKey,
          battleMemberUid: fighter.uid,
          activeUid: fighter.uid,
          collection: {
            ...state.collection,
            [spawn.speciesId]: {
              seen: true,
              recruited: state.collection[spawn.speciesId]?.recruited ?? false,
            },
          },
        })
      },

      battleAction: (action) => {
        const state = get()
        const { battle, battleMemberUid } = state
        if (!battle || battle.outcome !== 'ongoing') return
        const rng = Math.random
        let next =
          action.type === 'move'
            ? playerAttack(battle, action.moveId, rng)
            : action.type === 'link'
              ? attemptFriendLink(battle, rng)
              : attemptFlee(battle, rng)

        // when the battle just ended, settle xp / hp on the fighting member
        let party = state.party
        if (next.outcome !== 'ongoing' && battleMemberUid) {
          party = party.map((m) => {
            if (m.uid !== battleMemberUid) return m
            if (next.outcome === 'lose') return { ...m, hp: 0 }

            let updated = { ...m, hp: next.player.hp }
            if (next.outcome === 'win' || next.outcome === 'recruited') {
              const gain = xpGainForDefeating(next.wild.level)
              const oldMax = maxHpOf(updated)
              const result = applyXp(updated.level, updated.xp, gain)
              const lines = [`${next.player.name} gained ${gain} XP!`]
              const events: BattleEvent[] = [...next.events, { kind: 'xp' }]
              if (result.levelsGained > 0) {
                const newMax = maxHpOf({ ...updated, level: result.level })
                lines.push(`${next.player.name} grew to Lv.${result.level}!`)
                events.push({ kind: 'levelup' })
                // level-ups heal by the max-hp increase
                updated = {
                  ...updated,
                  level: result.level,
                  xp: result.xp,
                  hp: Math.min(updated.hp + (newMax - oldMax), newMax),
                }
              } else {
                updated = { ...updated, xp: result.xp }
              }
              next = { ...next, log: [...next.log, ...lines], events }
            }
            return updated
          })
        }
        set({ battle: next, party })
      },

      closeBattle: () => {
        const state = get()
        const { battle, battleSpawnKey } = state
        if (!battle) return

        let wildSpawns = state.wildSpawns
        if (battleSpawnKey !== null) {
          const spawn = wildSpawns.find((s) => s.key === battleSpawnKey)
          if (spawn) {
            if (battle.outcome === 'win' || battle.outcome === 'recruited') {
              // gone for good; a fresh creature wanders in
              wildSpawns = wildSpawns
                .filter((s) => s.key !== battleSpawnKey)
                .concat(makeSpawn(spawn.zoneId))
            } else {
              // fled / lost: the creature relocates within its zone
              wildSpawns = wildSpawns
                .filter((s) => s.key !== battleSpawnKey)
                .concat({
                  ...makeSpawn(spawn.zoneId),
                  speciesId: spawn.speciesId,
                  level: spawn.level,
                })
            }
          }
        }

        let collection = state.collection
        let party = state.party
        let activeUid = state.activeUid

        if (battle.outcome === 'recruited') {
          collection = {
            ...collection,
            [battle.wild.speciesId]: { seen: true, recruited: true },
          }
          if (party.length < MAX_PARTY) {
            party = [...party, newMember(battle.wild.speciesId, battle.wild.level, battle.wild.hp)]
            get().showNotice(`${battle.wild.name} (Lv.${battle.wild.level}) joined your party!`)
          } else {
            get().showNotice(`${battle.wild.name} now lives near the village (party is full).`)
          }
        }

        if (battle.outcome === 'lose') {
          const healthy = party.find((m) => m.hp > 0)
          if (healthy) {
            activeUid = healthy.uid
            get().showNotice(`${getSpecies(healthy.speciesId).name} took the lead!`)
          } else {
            // total wipe: villagers carry the party back and nurse them
            party = party.map((m) => ({ ...m, hp: maxHpOf(m) }))
            get().showNotice('You were carried back to the village. Everyone is rested.')
          }
        }

        set({
          mode: 'explore',
          battle: null,
          battleSpawnKey: null,
          battleMemberUid: null,
          wildSpawns,
          collection,
          party,
          activeUid,
          encounterCooldownUntil: Date.now() + 2000,
        })
      },

      toggleCollection: () => {
        const { mode } = get()
        if (mode === 'collection') set({ mode: 'explore' })
        else if (mode === 'explore') set({ mode: 'collection' })
      },

      startDialog: (npcId) => {
        if (get().mode !== 'explore') return
        if (!NPC_BY_ID[npcId]) return
        set({ mode: 'dialog', dialogNpcId: npcId, dialogLineIndex: 0 })
      },

      advanceDialog: () => {
        const { mode, dialogNpcId, dialogLineIndex } = get()
        if (mode !== 'dialog' || !dialogNpcId) return
        const npc = NPC_BY_ID[dialogNpcId]
        if (dialogLineIndex + 1 < npc.lines.length) {
          set({ dialogLineIndex: dialogLineIndex + 1 })
        } else {
          set({ mode: 'explore', dialogNpcId: null, dialogLineIndex: 0 })
        }
      },
    }),
    {
      name: 'quokka-wilds-save',
      version: 2,
      partialize: (state) => ({
        collection: state.collection,
        party: state.party,
        activeUid: state.activeUid,
      }),
      merge: (persisted, current) => {
        const saved = persisted as Partial<GameState> | undefined
        const party =
          Array.isArray(saved?.party) && saved.party.length > 0 ? saved.party : starterParty()
        const activeUid = party.some((m) => m.uid === saved?.activeUid)
          ? (saved?.activeUid as string)
          : party[0].uid
        return {
          ...current,
          collection: { ...starterCollection(), ...(saved?.collection ?? {}) },
          party,
          activeUid,
        }
      },
    },
  ),
)

// ensure activeUid points at a real member on a fresh (non-persisted) start
const fresh = useGameStore.getState()
if (!fresh.party.some((m) => m.uid === fresh.activeUid)) {
  useGameStore.setState({ activeUid: fresh.party[0].uid })
}
