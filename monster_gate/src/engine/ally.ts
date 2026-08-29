// Summoned monsters. They trace the player, attack what they see, and can be
// swapped with by walking into them. Kills by an ally give the player no XP.

import { meleeDamage } from "./combat";
import { ENEMY } from "./dungeon-def";
import { canSee } from "./fov";
import { canStep, dirTo, enemyAt } from "./geometry";
import { Rng } from "./rng";
import { add, DIRS, dist, vecEq, type Ally, type Dir, type DungeonState, type EnemyKind, type Event, type Vec } from "./types";

export function makeAlly(id: number, kind: EnemyKind, pos: Vec): Ally {
  const d = ENEMY[kind];
  return { id, kind, pos: { ...pos }, hp: d.hp, maxHp: d.hp, atk: d.atk, def: d.def };
}

export function allyAt(allies: readonly Ally[], p: Vec): Ally | undefined {
  return allies.find((a) => vecEq(a.pos, p));
}

/** A free cell next to `from`, for placing a summon. */
export function freeCellNear(state: DungeonState, from: Vec): Vec | null {
  for (let d = 0; d < 8; d++) {
    const dir = d as Dir;
    if (!canStep(state.map, from, dir)) continue;
    const to = add(from, DIRS[dir]!);
    if (enemyAt(state.enemies, to) || allyAt(state.allies, to)) continue;
    return to;
  }
  return null;
}

export type AllyTurn = { state: DungeonState; events: Event[]; attack: { enemyId: number; dmg: number } | null };

/** One ally's turn: fight what is adjacent, chase what it sees, else follow the player. */
export function allyAct(state: DungeonState, allyId: number): AllyTurn {
  const events: Event[] = [];
  const i = state.allies.findIndex((a) => a.id === allyId);
  if (i < 0) return { state, events, attack: null };
  const a = { ...state.allies[i]! };
  const allies = state.allies.slice();
  allies[i] = a;
  const rng = new Rng(state.rng);

  const target = state.enemies.filter((e) => dist(e.pos, a.pos) === 1).sort((x, y) => x.hp - y.hp)[0];
  if (target) {
    const { dmg } = meleeDamage(rng, a.atk, target.def, 0);
    events.push({ t: "allyHit", allyId: a.id, target: target.id, dmg });
    return { state: { ...state, allies, rng: rng.state }, events, attack: { enemyId: target.id, dmg } };
  }

  const seen = state.enemies
    .filter((e) => e.awake && canSee(state.map, a.pos, e.pos, false) && dist(e.pos, a.pos) <= 8)
    .sort((x, y) => dist(x.pos, a.pos) - dist(y.pos, a.pos))[0];
  if (!seen && dist(a.pos, state.player.pos) <= 1) return { state: { ...state, allies }, events, attack: null };
  const to = stepToward(state, allies, a, seen ? seen.pos : state.player.pos);
  if (to) a.pos = to;
  return { state: { ...state, allies, rng: rng.state }, events, attack: null };
}

function stepToward(state: DungeonState, allies: readonly Ally[], a: Ally, target: Vec): Vec | null {
  const cur = dist(a.pos, target);
  const preferred = dirTo(a.pos, target);
  if (preferred === null) return null;
  const order: Dir[] = [preferred];
  for (let k = 1; k <= 3; k++) order.push(((preferred + k) % 8) as Dir, ((preferred - k + 8) % 8) as Dir);
  for (const dir of order) {
    const to = add(a.pos, DIRS[dir]!);
    if (dist(to, target) >= cur) continue;
    if (!canStep(state.map, a.pos, dir)) continue;
    if (vecEq(to, state.player.pos)) continue;
    if (enemyAt(state.enemies, to) || allyAt(allies, to)) continue;
    return to;
  }
  return null;
}

/** Apply damage to an ally, dropping it when it dies. */
export function damageAlly(allies: readonly Ally[], allyId: number, dmg: number, events: Event[]): Ally[] {
  const a = allies.find((x) => x.id === allyId);
  if (!a) return [...allies];
  events.push({ t: "allyHurt", allyId, dmg });
  const hp = a.hp - dmg;
  if (hp > 0) return allies.map((x) => (x.id === allyId ? { ...x, hp } : x));
  events.push({ t: "allyDied", kind: a.kind });
  return allies.filter((x) => x.id !== allyId);
}
