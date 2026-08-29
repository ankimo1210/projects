// One enemy's turn. Pure: returns a new state + events.

import { allyAt, damageAlly } from "./ally";
import { playerDef, rangedDamage } from "./combat";
import { DUNGEONS, RULES } from "./dungeon-def";
import { canSee } from "./fov";
import { canStep, dirTo, enemyAt, hasLineOfFire } from "./geometry";
import { Rng } from "./rng";
import { add, DIRS, dist, tileAt, vecEq, type Ally, type Dir, type DungeonState, type Enemy, type Event, type Vec } from "./types";
import { meleeDamage } from "./combat";

export function enemyAct(state: DungeonState, enemyId: number): { state: DungeonState; events: Event[] } {
  const events: Event[] = [];
  const i = state.enemies.findIndex((e) => e.id === enemyId);
  if (i < 0) return { state, events };
  const e = { ...state.enemies[i]! };
  const enemies = state.enemies.slice();
  enemies[i] = e;
  let player = state.player;
  let allies = state.allies;
  const rng = new Rng(state.rng);
  /** melee an adjacent summon when the player is out of reach */
  const hitAlly = (): boolean => {
    const a = allies.filter((x) => dist(x.pos, e.pos) === 1).sort((x, y) => x.hp - y.hp)[0];
    if (!a) return false;
    const { dmg } = meleeDamage(rng, e.atk, a.def, rules.enemyCrit ?? 0);
    allies = damageAlly(allies, a.id, dmg, events);
    return true;
  };

  const rules = DUNGEONS[state.dungeonId]?.rules ?? {};
  const pdef = playerDef(player);

  if (e.sleep > 0) {
    e.sleep--;
    return { state: { ...state, enemies, rng: rng.state }, events };
  }

  const corridorRadius = rules.litCorridors ? RULES.litCorridorRadius : 1;
  const sees = canSee(state.map, e.pos, player.pos, false, corridorRadius);
  const d = dist(e.pos, player.pos);
  if (!e.awake) {
    if (e.dormant ? d === 1 : sees) e.awake = true;
    else return { state: { ...state, enemies }, events };
  }

  if (e.confused > 0) {
    e.confused--;
    const to = wander(state, enemies, e, rng, true);
    if (to) e.pos = to;
    return { state: { ...state, enemies, rng: rng.state }, events };
  }

  if (e.boss) {
    if (rng.chance(RULES.bossAttackChance)) {
      if (d === 1) {
        const { dmg, crit } = meleeDamage(rng, e.atk, pdef, rules.enemyCrit ?? 0);
        player = { ...player, hp: player.hp - dmg };
        events.push({ t: "attack", by: e.id, target: "player", dmg, crit, ranged: false });
      } else hitAlly();
    }
    return { state: { ...state, enemies, allies, player, rng: rng.state }, events };
  }

  if (sees) {
    e.lastSeen = { ...player.pos };
    if (e.ranged && d > 1 && hasLineOfFire(state.map, enemies, e.pos, player.pos, RULES.rangedRange)) {
      const dmg = rangedDamage(e.atk, pdef, d);
      player = { ...player, hp: player.hp - dmg };
      events.push({ t: "attack", by: e.id, target: "player", dmg, crit: false, ranged: true });
    } else if (d === 1) {
      const { dmg, crit } = meleeDamage(rng, e.atk, pdef, rules.enemyCrit ?? 0);
      player = { ...player, hp: player.hp - dmg };
      events.push({ t: "attack", by: e.id, target: "player", dmg, crit, ranged: false });
    } else if (!hitAlly()) {
      const to = stepToward(state, enemies, e, player.pos, allies);
      if (to) e.pos = to;
    }
  } else if (hitAlly()) {
    // busy with the summon
  } else if (e.lastSeen) {
    const to = stepToward(state, enemies, e, e.lastSeen, allies);
    if (to) e.pos = to;
    if (vecEq(e.pos, e.lastSeen) || !to) e.lastSeen = null;
  } else {
    const to = wander(state, enemies, e, rng);
    if (to) e.pos = to;
  }

  return { state: { ...state, enemies, allies, player, rng: rng.state }, events };
}

/** Best neighbouring cell that strictly reduces Chebyshev distance; null if none. */
export function stepToward(state: DungeonState, enemies: readonly Enemy[], e: Enemy, target: Vec, allies: readonly Ally[] = []): Vec | null {
  const cur = dist(e.pos, target);
  const preferred = dirTo(e.pos, target);
  const order: Dir[] = [];
  if (preferred !== null) order.push(preferred);
  for (let k = 1; k <= 7; k++) {
    if (preferred === null) break;
    order.push(((preferred + k) % 8) as Dir, ((preferred - k + 8) % 8) as Dir);
  }
  for (const dir of order) {
    const to = add(e.pos, DIRS[dir]!);
    if (dist(to, target) >= cur) continue;
    if (!canStep(state.map, e.pos, dir)) continue;
    if (vecEq(to, state.player.pos)) continue;
    if (enemyAt(enemies, to) || allyAt(allies, to)) continue;
    return to;
  }
  return null;
}

/** Random step. Confused enemies stagger anywhere (and never stop); idle ones prefer their room. */
function wander(state: DungeonState, enemies: readonly Enemy[], e: Enemy, rng: Rng, confused = false): Vec | null {
  const here = tileAt(state.map, e.pos);
  const options: Vec[] = [];
  for (let d = 0; d < 8; d++) {
    const dir = d as Dir;
    if (!canStep(state.map, e.pos, dir)) continue;
    const to = add(e.pos, DIRS[dir]!);
    if (vecEq(to, state.player.pos) || enemyAt(enemies, to) || allyAt(state.allies, to)) continue;
    // inside a room stay in the room 80% of the time
    const t = tileAt(state.map, to);
    if (!confused && here.roomId >= 0 && t.roomId !== here.roomId && rng.chance(0.8)) continue;
    options.push(to);
  }
  if (options.length === 0 || (!confused && rng.chance(0.3))) return null;
  return rng.pick(options);
}
