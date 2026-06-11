/**
 * Pure turn-based battle logic. No React, no globals — rng is injected so
 * every branch is testable. State updates are immutable.
 *
 * Turn order is simplified for the MVP: the player always acts first;
 * speed only influences flee chance.
 */
import {
  getSpecies,
  MOVES,
  type CreatureSpecies,
  type ElementType,
  type MoveDef,
} from './data/creatures'
import { statsAtLevel } from './progression'

export type Rng = () => number

export interface BattleCreature {
  speciesId: string
  name: string
  element: ElementType
  level: number
  maxHp: number
  hp: number
  attack: number
  defense: number
  speed: number
  moveIds: string[]
  friendliness: number
}

/** One combatant entering battle: species, level, optional current hp. */
export interface BattleSide {
  speciesId: string
  level: number
  hp?: number
}

export type BattleOutcome = 'ongoing' | 'win' | 'lose' | 'recruited' | 'fled'

export type BattleSideId = 'player' | 'wild'

/**
 * What happened during the last battle action, in order. The UI replays
 * these as animations / sounds; each event matches exactly one log line
 * appended by that action.
 */
export type BattleEvent =
  | {
      kind: 'hit'
      target: BattleSideId
      damage: number
      /** target hp after the hit */
      hp: number
      effective: 'strong' | 'weak' | 'normal'
    }
  | { kind: 'miss'; attacker: BattleSideId }
  | { kind: 'faint'; target: BattleSideId }
  | { kind: 'link'; success: boolean }
  | { kind: 'flee'; success: boolean }
  | { kind: 'xp' }
  | { kind: 'levelup' }

export interface BattleState {
  player: BattleCreature
  wild: BattleCreature
  log: string[]
  outcome: BattleOutcome
  /** events of the most recent action only (cleared at each player action) */
  events: BattleEvent[]
}

/** strong-against cycle: leaf > tide > ember > leaf, spark > breeze > stone > spark */
const STRONG_AGAINST: Partial<Record<ElementType, ElementType>> = {
  leaf: 'tide',
  tide: 'ember',
  ember: 'leaf',
  spark: 'breeze',
  breeze: 'stone',
  stone: 'spark',
}

export function elementMultiplier(attacker: ElementType, defender: ElementType): number {
  if (STRONG_AGAINST[attacker] === defender) return 1.5
  if (STRONG_AGAINST[defender] === attacker) return 0.75
  return 1
}

export function makeBattleCreature(
  species: CreatureSpecies,
  level: number,
  hp?: number,
): BattleCreature {
  const stats = statsAtLevel(species.baseStats, level)
  return {
    speciesId: species.id,
    name: species.name,
    element: species.element,
    level,
    maxHp: stats.hp,
    hp: Math.max(0, Math.min(hp ?? stats.hp, stats.hp)),
    attack: stats.attack,
    defense: stats.defense,
    speed: stats.speed,
    moveIds: [...species.moveIds],
    friendliness: species.friendliness,
  }
}

export function createBattle(playerSide: BattleSide, wildSide: BattleSide): BattleState {
  const player = makeBattleCreature(getSpecies(playerSide.speciesId), playerSide.level, playerSide.hp)
  const wild = makeBattleCreature(getSpecies(wildSide.speciesId), wildSide.level, wildSide.hp)
  return {
    player,
    wild,
    log: [`A wild ${wild.name} (Lv.${wild.level}) appeared!`],
    outcome: 'ongoing',
    events: [],
  }
}

/** Damage for a landed hit. Always at least 1. */
export function computeDamage(
  attacker: BattleCreature,
  defender: BattleCreature,
  move: MoveDef,
  rng: Rng,
): number {
  const mult = elementMultiplier(move.element, defender.element)
  const variance = 0.85 + rng() * 0.3
  const raw = move.power * (attacker.attack / defender.defense) * mult * variance
  return Math.max(1, Math.round(raw))
}

/** Recruit chance rises as the wild creature weakens. */
export function friendLinkChance(wild: BattleCreature): number {
  const hpRatio = wild.hp / wild.maxHp
  const chance = wild.friendliness * (1.5 - 1.1 * hpRatio)
  return Math.min(0.95, Math.max(0.05, chance))
}

/** Flee chance favors faster players. */
export function fleeChance(player: BattleCreature, wild: BattleCreature): number {
  const chance = 0.55 + (player.speed - wild.speed) * 0.03
  return Math.min(0.95, Math.max(0.25, chance))
}

interface AttackResult {
  defender: BattleCreature
  logLine: string
  event: BattleEvent
}

function resolveAttack(
  attacker: BattleCreature,
  defender: BattleCreature,
  defenderSide: BattleSideId,
  move: MoveDef,
  rng: Rng,
): AttackResult {
  if (rng() > move.accuracy) {
    return {
      defender,
      logLine: `${attacker.name}'s ${move.name} missed!`,
      event: { kind: 'miss', attacker: defenderSide === 'wild' ? 'player' : 'wild' },
    }
  }
  const damage = computeDamage(attacker, defender, move, rng)
  const mult = elementMultiplier(move.element, defender.element)
  const note = mult > 1 ? ' It hits hard!' : mult < 1 ? ' It barely lands.' : ''
  const hp = Math.max(0, defender.hp - damage)
  return {
    defender: { ...defender, hp },
    logLine: `${attacker.name} used ${move.name} — ${damage} damage.${note}`,
    event: {
      kind: 'hit',
      target: defenderSide,
      damage,
      hp,
      effective: mult > 1 ? 'strong' : mult < 1 ? 'weak' : 'normal',
    },
  }
}

function wildTurn(state: BattleState, rng: Rng): BattleState {
  if (state.wild.hp <= 0) return state
  const moveId = state.wild.moveIds[Math.floor(rng() * state.wild.moveIds.length)]
  const move = MOVES[moveId]
  const { defender: player, logLine, event } = resolveAttack(
    state.wild,
    state.player,
    'player',
    move,
    rng,
  )
  const lost = player.hp <= 0
  return {
    ...state,
    player,
    log: [...state.log, logLine, ...(lost ? [`${player.name} is exhausted...`] : [])],
    events: [...state.events, event, ...(lost ? [{ kind: 'faint', target: 'player' } as const] : [])],
    outcome: lost ? 'lose' : state.outcome,
  }
}

/** Player picks a move; wild counterattacks if it survives. */
export function playerAttack(state: BattleState, moveId: string, rng: Rng): BattleState {
  if (state.outcome !== 'ongoing') return state
  const move = MOVES[moveId]
  if (!move || !state.player.moveIds.includes(moveId)) {
    throw new Error(`Invalid move for player: ${moveId}`)
  }
  const { defender: wild, logLine, event } = resolveAttack(
    state.player,
    state.wild,
    'wild',
    move,
    rng,
  )
  const won = wild.hp <= 0
  const next: BattleState = {
    ...state,
    wild,
    log: [...state.log, logLine, ...(won ? [`The wild ${wild.name} fainted!`] : [])],
    events: [event, ...(won ? [{ kind: 'faint', target: 'wild' } as const] : [])],
    outcome: won ? 'win' : 'ongoing',
  }
  return won ? next : wildTurn(next, rng)
}

/** Friend Link: try to befriend the wild creature. Failure costs a turn. */
export function attemptFriendLink(state: BattleState, rng: Rng): BattleState {
  if (state.outcome !== 'ongoing') return state
  const chance = friendLinkChance(state.wild)
  if (rng() < chance) {
    return {
      ...state,
      log: [...state.log, `Friend Link formed! ${state.wild.name} joins you!`],
      events: [{ kind: 'link', success: true }],
      outcome: 'recruited',
    }
  }
  const next: BattleState = {
    ...state,
    log: [...state.log, `${state.wild.name} shies away from the Friend Link...`],
    events: [{ kind: 'link', success: false }],
  }
  return wildTurn(next, rng)
}

/** Run from battle. Failure costs a turn. */
export function attemptFlee(state: BattleState, rng: Rng): BattleState {
  if (state.outcome !== 'ongoing') return state
  const chance = fleeChance(state.player, state.wild)
  if (rng() < chance) {
    return {
      ...state,
      log: [...state.log, 'You slipped away safely.'],
      events: [{ kind: 'flee', success: true }],
      outcome: 'fled',
    }
  }
  const next: BattleState = {
    ...state,
    log: [...state.log, "Couldn't get away!"],
    events: [{ kind: 'flee', success: false }],
  }
  return wildTurn(next, rng)
}
