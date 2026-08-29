// step(state, action) — the only state transition. Never mutates its input.

import { enemyAct } from "./ai";
import { allyAct, allyAt, damageAlly, freeCellNear, makeAlly } from "./ally";
import { BOSS_DROPS, CARD_EFFECT, CARDS, dungeonPrice } from "./cards";
import { gainXp, levelUp, meleeDamage, playerAtk } from "./combat";
import { CASINO, CLASSES, DOUBLE_UP, DUNGEONS, ENEMY, RULES, payoutFor, type DungeonRules } from "./dungeon-def";
import { enterFloor, makeEnemy } from "./dungeon";
import { visibleSet } from "./fov";
import { canStep, enemyAt, firstEnemyInDir, slideFrom } from "./geometry";
import { floorCells } from "./mapgen";
import { Rng } from "./rng";
import { add, DIRS, idx, tileAt, vecEq, type Action, type Dir, type DungeonState, type Enemy, type EnemyKind, type Event, type Vec } from "./types";

export type StepResult = { state: DungeonState; events: Event[] };

export function step(input: DungeonState, action: Action): StepResult {
  if (input.result) return { state: input, events: [{ t: "blocked", reason: "run is over" }] };
  const events: Event[] = [];
  const r = playerPhase(input, action, events);
  let state = r.state;
  if (!r.consumedTurn) return { state, events };
  if (r.skipEnemies) return finish(state, events);

  // haste: enemies act only on every second player action
  const p = state.player;
  if (p.status.haste > 0) {
    const haste = p.status.haste - 1;
    state = { ...state, player: { ...p, status: { ...p.status, haste } } };
    if (haste % 2 === 1) return finish(state, events);
  }

  for (const a of state.allies.slice()) {
    const res = allyAct(state, a.id);
    state = res.state;
    events.push(...res.events);
    if (res.attack) state = damageEnemy(state, res.attack.enemyId, res.attack.dmg, events, false);
  }
  for (const e of state.enemies.slice()) {
    if (state.player.hp <= 0) break;
    const res = enemyAct(state, e.id);
    state = res.state;
    events.push(...res.events);
  }
  return finish(endOfTurn(state, events), events);
}

function rulesOf(state: DungeonState): DungeonRules {
  return DUNGEONS[state.dungeonId]?.rules ?? {};
}

function corridorRadius(state: DungeonState): number {
  const byRule = rulesOf(state).litCorridors ? RULES.litCorridorRadius : 1;
  return Math.max(byRule, CLASSES[state.player.cls].corridorVision);
}

/** Visible tiles under this dungeon's rules. */
export function visibleNow(state: DungeonState): boolean[] {
  return visibleSet(state.map, state.player.pos, state.player.bright, corridorRadius(state));
}

function finish(state: DungeonState, events: Event[]): StepResult {
  let s = { ...state, turn: state.turn + 1 };
  if (s.player.hp <= 0 && !s.result) {
    if (s.player.equipment.revive) {
      const hp = Math.max(1, Math.floor(s.player.maxHp * RULES.reviveRatio));
      s = { ...s, player: { ...s.player, hp, equipment: { ...s.player.equipment, revive: false } } };
      events.push({ t: "revived", hp });
    } else {
      s = { ...s, player: { ...s.player, hp: 0 }, result: "dead" };
      events.push({ t: "playerDied" });
    }
  }
  return { state: reveal(s), events };
}

/** Tiles the player is allowed to *see on screen*: in a dark castle only the current view (until mapped). */
export function knownTiles(state: DungeonState): boolean[] {
  if (rulesOf(state).dark && !state.player.mapped) return visibleNow(state);
  return state.explored;
}

function reveal(state: DungeonState): DungeonState {
  const vis = visibleNow(state);
  const explored = state.explored.slice();
  for (let i = 0; i < vis.length; i++) if (vis[i]) explored[i] = true;
  return { ...state, explored };
}

type PhaseResult = { state: DungeonState; consumedTurn: boolean; skipEnemies?: boolean };

function playerPhase(state: DungeonState, action: Action, events: Event[]): PhaseResult {
  switch (action.type) {
    case "wait":
      return { state, consumedTurn: true };
    case "move":
      return doMove(state, action.dir, events);
    case "attack": {
      const target = add(state.player.pos, DIRS[action.dir]!);
      const e = enemyAt(state.enemies, target);
      if (!e) return { state, consumedTurn: true }; // swing at air
      return { state: playerMelee(state, e, events), consumedTurn: true };
    }
    case "useCard":
      return useCard(state, action.index, action.dir, events);
    case "discardCard":
      return { state: discardCard(state, action.index, events), consumedTurn: false };
    case "descend": {
      if (!state.map.stairs || !vecEq(state.player.pos, state.map.stairs)) {
        events.push({ t: "blocked", reason: "not on stairs" });
        return { state, consumedTurn: false };
      }
      const def = DUNGEONS[state.dungeonId]!;
      const next = enterFloor(state, def, state.floorNo + 1);
      events.push({ t: "floorChanged", floorNo: next.floorNo });
      for (const a of state.allies) events.push({ t: "log", msg: `${ENEMY[a.kind].name}とはぐれた` });
      return { state: next, consumedTurn: true, skipEnemies: true };
    }
    case "takeAltar": {
      if (!state.map.altar || !vecEq(state.player.pos, state.map.altar)) {
        events.push({ t: "blocked", reason: "not on altar" });
        return { state, consumedTurn: false };
      }
      const def = DUNGEONS[state.dungeonId]!;
      const win = payoutFor(def, { result: "clear", winCollected: state.winCollected, multiplier: state.winMultiplier });
      events.push({ t: "cleared", win });
      return { state: { ...state, result: "clear" }, consumedTurn: true, skipEnemies: true };
    }
    case "buy":
      return { state: buy(state, action.index, events), consumedTurn: false };
    case "spin":
      return { state: spin(state, events), consumedTurn: false };
  }
}

/** Shops and casinos are free actions: the room is safe while you deal. */
function buy(state: DungeonState, index: number, events: Event[]): DungeonState {
  if (tileAt(state.map, state.player.pos).kind !== "shop") {
    events.push({ t: "blocked", reason: "not in a shop" });
    return state;
  }
  const offer = state.offers[index];
  if (!offer || offer.sold) {
    events.push({ t: "blocked", reason: "sold out" });
    return state;
  }
  const p = state.player;
  if (state.winCollected < offer.price) {
    events.push({ t: "blocked", reason: "not enough win" });
    return state;
  }
  if (p.hand.length >= p.handSize) {
    events.push({ t: "blocked", reason: "hand full" });
    return state;
  }
  events.push({ t: "bought", card: offer.card, price: offer.price });
  return {
    ...state,
    winCollected: state.winCollected - offer.price,
    offers: state.offers.map((o, i) => (i === index ? { ...o, sold: true } : o)),
    player: { ...p, hand: [...p.hand, offer.card] },
  };
}

function spin(state: DungeonState, events: Event[]): DungeonState {
  if (tileAt(state.map, state.player.pos).kind !== "casino") {
    events.push({ t: "blocked", reason: "not in a casino" });
    return state;
  }
  if (state.casinoSpins >= CASINO.maxSpins) {
    events.push({ t: "blocked", reason: "out of order" });
    return state;
  }
  if (state.winCollected < CASINO.bet) {
    events.push({ t: "blocked", reason: "not enough win" });
    return state;
  }
  const rng = new Rng(state.rng);
  const table = CLASSES[state.player.cls].luckyCasino ? CASINO.luckyTable : CASINO.table;
  const mul = rng.weighted(table.map((e) => ({ item: e.mul, weight: e.weight })));
  const payout = CASINO.bet * mul;
  events.push({ t: "spun", bet: CASINO.bet, payout });
  return { ...state, rng: rng.state, casinoSpins: state.casinoSpins + 1, winCollected: state.winCollected - CASINO.bet + payout };
}

function doMove(state: DungeonState, dir: Dir, events: Event[]): PhaseResult {
  const from = state.player.pos;
  const to = add(from, DIRS[dir]!);
  if (!canStep(state.map, from, dir)) {
    events.push({ t: "blocked", reason: "wall" });
    return { state, consumedTurn: false };
  }
  const e = enemyAt(state.enemies, to);
  if (e) return { state: playerMelee(state, e, events), consumedTurn: true };

  const ally = allyAt(state.allies, to);
  let s: DungeonState = ally
    ? { ...state, player: { ...state.player, pos: to }, allies: state.allies.map((a) => (a.id === ally.id ? { ...a, pos: from } : a)) }
    : { ...state, player: { ...state.player, pos: to } };
  events.push({ t: "moved", from, to });
  if (!ally) s = slide(s, dir, events);
  const landed = s.player.pos;
  if (rulesOf(s).acidFloor && tileAt(s.map, landed).roomId < 0) {
    s = { ...s, player: { ...s.player, hp: s.player.hp - 1 } };
    events.push({ t: "acid", dmg: 1 });
  }
  s = pickup(s, events);
  s = onEnterTile(s, events);
  return { state: s, consumedTurn: true };
}

/** Ice: keep going in the same direction until leaving the ice or hitting something. Only the player slides. */
function slide(state: DungeonState, dir: Dir, events: Event[]): DungeonState {
  const blocked = (v: Vec) => !!enemyAt(state.enemies, v) || !!allyAt(state.allies, v);
  const pos = slideFrom(state.map, blocked, state.player.pos, dir);
  if (vecEq(pos, state.player.pos)) return state;
  events.push({ t: "slide", to: pos });
  return { ...state, player: { ...state.player, pos } };
}

function onEnterTile(state: DungeonState, events: Event[]): DungeonState {
  const t = tileAt(state.map, state.player.pos);
  if (t.roomId < 0) return state;
  // wake everything in the room (dormant enemies only wake when hit or adjacent)
  const enemies = state.enemies.map((e) => (!e.dormant && tileAt(state.map, e.pos).roomId === t.roomId ? { ...e, awake: true } : e));
  let player = state.player;
  if (!player.visitedRooms.includes(t.roomId)) {
    const hp = Math.min(player.maxHp, player.hp + RULES.roomHpGain);
    const mp = Math.min(player.maxMp, player.mp + RULES.roomMpGain);
    events.push({ t: "roomEntered", roomId: t.roomId, hpGain: hp - player.hp, mpGain: mp - player.mp });
    player = { ...player, hp, mp, visitedRooms: [...player.visitedRooms, t.roomId] };
  }
  return { ...state, enemies, player };
}

function pickup(state: DungeonState, events: Event[]): DungeonState {
  const here = state.player.pos;
  const item = state.items.find((it) => vecEq(it.pos, here));
  if (!item) return state;
  if (item.type === "win") {
    events.push({ t: "pickupWin", amount: item.amount });
    return { ...state, items: state.items.filter((it) => it !== item), winCollected: state.winCollected + item.amount };
  }
  if (item.type === "doubleUp") {
    const multiplier = state.winMultiplier * DOUBLE_UP.factor;
    events.push({ t: "doubleUp", multiplier });
    return { ...state, items: state.items.filter((it) => it !== item), winMultiplier: multiplier };
  }
  if (state.player.hand.length >= state.player.handSize) {
    events.push({ t: "handFull", card: item.card });
    return state;
  }
  events.push({ t: "pickup", card: item.card });
  return {
    ...state,
    items: state.items.filter((it) => it !== item),
    player: { ...state.player, hand: [...state.player.hand, item.card] },
  };
}

function playerMelee(state: DungeonState, target: Enemy, events: Event[]): DungeonState {
  const rng = new Rng(state.rng);
  const critChance = rulesOf(state).playerCrit ?? CLASSES[state.player.cls].crit;
  const { dmg, crit } = meleeDamage(rng, playerAtk(state.player), target.def, critChance);
  events.push({ t: "attack", by: "player", target: target.id, dmg, crit, ranged: false });
  return damageEnemy({ ...state, rng: rng.state }, target.id, dmg, events);
}

/** Apply damage; on kill remove the enemy and grow the player. */
function damageEnemy(state: DungeonState, enemyId: number, dmg: number, events: Event[], grantXp = true): DungeonState {
  const e = state.enemies.find((x) => x.id === enemyId);
  if (!e) return state;
  const hp = e.hp - dmg;
  if (hp > 0) {
    return { ...state, enemies: state.enemies.map((x) => (x.id === enemyId ? { ...x, hp, awake: true } : x)) };
  }
  events.push({ t: "died", enemyId, kind: e.kind });
  const { player, gains } = grantXp ? gainXp(state.player, e.kind) : { player: state.player, gains: { level: 0, hp: 0, atk: 0, def: 0 } };
  if (gains.level > 0) events.push({ t: "grow", ...gains });
  let s: DungeonState = { ...state, enemies: state.enemies.filter((x) => x.id !== enemyId), player };
  if (e.boss) {
    const rng = new Rng(s.rng);
    const card = rng.weighted(BOSS_DROPS);
    events.push({ t: "bossDrop", card });
    s = { ...s, rng: rng.state, items: [...s.items, { id: s.nextId, pos: { ...e.pos }, type: "card", card }], nextId: s.nextId + 1 };
  }
  return s;
}

function useCard(state: DungeonState, index: number, dir: Dir | undefined, events: Event[]): PhaseResult {
  const card = state.player.hand[index];
  if (card === undefined) {
    events.push({ t: "blocked", reason: "no such card" });
    return { state, consumedTurn: false };
  }
  const def = CARDS[card];
  if (state.player.mp < def.mp) {
    events.push({ t: "notEnoughMp", card, need: def.mp });
    return { state, consumedTurn: false };
  }
  if (def.target === "dir" && dir === undefined) {
    events.push({ t: "blocked", reason: "direction required" });
    return { state, consumedTurn: false };
  }

  const p = state.player;
  const cls = CLASSES[p.cls];
  const magic = (n: number): number => Math.round(n * cls.magicMul);
  const spend = (s: DungeonState): DungeonState => ({
    ...s,
    player: { ...s.player, mp: s.player.mp - def.mp, hand: s.player.hand.filter((_, i) => i !== index) },
  });
  const done = (s: DungeonState, skipEnemies = false): PhaseResult => {
    events.push({ t: "cardUsed", card, mpCost: def.mp });
    return { state: spend(s), consumedTurn: true, skipEnemies };
  };
  const noTarget = (): PhaseResult => {
    events.push({ t: "blocked", reason: "no target" });
    return { state, consumedTurn: false };
  };

  switch (card) {
    case "potion20":
    case "potion40":
    case "potion80": {
      const amount = Math.round(CARD_EFFECT[card] * cls.potionMul);
      return done({ ...state, player: { ...p, hp: Math.min(p.maxHp, p.hp + amount) } });
    }
    case "fire":
    case "thunder":
    case "meteor": {
      const e = firstEnemyInDir(state.map, state.enemies, p.pos, dir!, RULES.cardRange);
      if (!e) return noTarget();
      const dmg = magic(card === "fire" ? CARD_EFFECT.fireDamage : card === "thunder" ? CARD_EFFECT.thunderDamage : CARD_EFFECT.meteorDamage);
      events.push({ t: "attack", by: "player", target: e.id, dmg, crit: false, ranged: true });
      return done(damageEnemy(state, e.id, dmg, events));
    }
    case "multiFire":
    case "multiThunder": {
      const vis = visibleNow(state);
      const targets = state.enemies.filter((e) => vis[idx(state.map, e.pos)]);
      if (targets.length === 0) return noTarget();
      const dmg = magic(card === "multiFire" ? CARD_EFFECT.fireDamage : CARD_EFFECT.thunderDamage);
      let s = state;
      for (const e of targets) {
        events.push({ t: "attack", by: "player", target: e.id, dmg, crit: false, ranged: true });
        s = damageEnemy(s, e.id, dmg, events);
      }
      return done(s);
    }
    case "sleep": {
      const e = firstEnemyInDir(state.map, state.enemies, p.pos, dir!, RULES.cardRange);
      if (!e) return noTarget();
      events.push({ t: "enemySlept", enemyId: e.id });
      return done({ ...state, enemies: state.enemies.map((x) => (x.id === e.id ? { ...x, sleep: CARD_EFFECT.sleepTurns, awake: true } : x)) });
    }
    case "panic": {
      const e = firstEnemyInDir(state.map, state.enemies, p.pos, dir!, RULES.cardRange);
      if (!e) return noTarget();
      events.push({ t: "enemyConfused", enemyId: e.id });
      return done({ ...state, enemies: state.enemies.map((x) => (x.id === e.id ? { ...x, confused: CARD_EFFECT.panicTurns, awake: true } : x)) });
    }
    case "multiPanic": {
      const vis = visibleNow(state);
      const ids = new Set(state.enemies.filter((e) => vis[idx(state.map, e.pos)]).map((e) => e.id));
      if (ids.size === 0) return noTarget();
      for (const id of ids) events.push({ t: "enemyConfused", enemyId: id });
      return done({ ...state, enemies: state.enemies.map((x) => (ids.has(x.id) ? { ...x, confused: CARD_EFFECT.panicTurns, awake: true } : x)) });
    }
    case "search":
      return done({ ...state, player: { ...p, searched: true } });
    case "map":
      return done({ ...state, explored: state.explored.map(() => true), player: { ...p, mapped: true } });
    case "regen":
      return done({ ...state, player: { ...p, status: { ...p.status, regen: CARD_EFFECT.regenTurns } } });
    case "longSword":
      return done({ ...state, player: { ...p, equipment: { ...p.equipment, weaponBonus: CARD_EFFECT.longSwordBonus } } });
    case "powerShield":
      return done({ ...state, player: { ...p, equipment: { ...p.equipment, shieldBonus: CARD_EFFECT.powerShieldBonus } } });
    case "pocket2": {
      if (p.equipment.pocket) {
        events.push({ t: "blocked", reason: "already used" });
        return { state, consumedTurn: false };
      }
      return done({ ...state, player: { ...p, handSize: p.handSize + CARD_EFFECT.pocketBonus, equipment: { ...p.equipment, pocket: true } } });
    }
    case "reviveRing":
      return done({ ...state, player: { ...p, equipment: { ...p.equipment, revive: true } } });
    case "summonGoblin":
    case "summonDragon": {
      if (state.allies.length >= CARD_EFFECT.allyCap) {
        events.push({ t: "blocked", reason: "too many summons" });
        return { state, consumedTurn: false };
      }
      const cell = freeCellNear(state, p.pos);
      if (!cell) return noTarget();
      const kind: EnemyKind = card === "summonGoblin" ? "goblin" : "dragon";
      events.push({ t: "summoned", kind });
      return done({ ...state, allies: [...state.allies, makeAlly(state.nextId, kind, cell)], nextId: state.nextId + 1 });
    }
    case "powerUp": {
      const { player, gains } = levelUp(p, CARD_EFFECT.powerUpLevels);
      events.push({ t: "grow", ...gains });
      return done({ ...state, player: { ...player, hp: Math.min(player.maxHp, player.hp + CARD_EFFECT.powerUpHeal) } });
    }
    case "haste":
      return done({ ...state, player: { ...p, status: { ...p.status, haste: CARD_EFFECT.hasteTurns } } });
    case "bright":
      return done({ ...state, player: { ...p, bright: true } });
    case "warp": {
      const rng = new Rng(state.rng);
      const cells = floorCells(state.map, (_, v) => !vecEq(v, p.pos) && !enemyAt(state.enemies, v));
      const to = rng.pick(cells);
      events.push({ t: "moved", from: p.pos, to });
      let s: DungeonState = { ...state, rng: rng.state, player: { ...p, pos: to } };
      s = spend(s);
      s = pickup(s, events);
      s = onEnterTile(s, events);
      events.push({ t: "cardUsed", card, mpCost: def.mp });
      return { state: s, consumedTurn: true };
    }
    case "escape": {
      events.push({ t: "escaped", win: state.winCollected });
      return done({ ...state, result: "escaped" }, true);
    }
    case "bronzeSword":
      return done({ ...state, player: { ...p, equipment: { ...p.equipment, weaponBonus: Math.max(p.equipment.weaponBonus, CARD_EFFECT.bronzeSwordBonus) } } });
  }
}

function discardCard(state: DungeonState, index: number, events: Event[]): DungeonState {
  const card = state.player.hand[index];
  if (card === undefined) {
    events.push({ t: "blocked", reason: "no such card" });
    return state;
  }
  const p = state.player;
  const mp = Math.min(p.maxMp, p.mp + CARDS[card].mp);
  events.push({ t: "discarded", card, mpBack: mp - p.mp });
  return { ...state, player: { ...p, mp, hand: p.hand.filter((_, i) => i !== index) } };
}

function endOfTurn(state: DungeonState, events: Event[]): DungeonState {
  let s = state;
  const p = s.player;
  if (p.status.regen > 0) {
    s = { ...s, player: { ...p, hp: Math.min(p.maxHp, p.hp + 1), status: { ...p.status, regen: p.status.regen - 1 } } };
  }
  const turnsOnFloor = s.turnsOnFloor + 1;
  s = { ...s, turnsOnFloor };
  const over = turnsOnFloor - RULES.spawnAfterTurns;
  if (over > 0 && over % RULES.spawnEvery === 0 && s.spawnedOnFloor < RULES.spawnCap) {
    s = spawnEnemy(s, events);
  }
  return s;
}

function spawnEnemy(state: DungeonState, events: Event[]): DungeonState {
  const def = DUNGEONS[state.dungeonId]!;
  const fdef = def.floors[state.floorNo - 1]!;
  const kinds = Object.keys(fdef.enemies) as EnemyKind[];
  const rng = new Rng(state.rng);
  const vis = visibleNow(state);
  const cells = floorCells(state.map, (t, v) => t.kind === "floor" && t.roomId >= 0 && !vis[idx(state.map, v)] && !enemyAt(state.enemies, v) && !allyAt(state.allies, v));
  if (cells.length === 0) return { ...state, rng: rng.state };
  const kind = rng.pick(kinds);
  const pos: Vec = rng.pick(cells);
  const e = { ...makeEnemy(state.nextId, kind, pos), awake: true, dormant: false };
  events.push({ t: "spawn", kind });
  return { ...state, rng: rng.state, enemies: [...state.enemies, e], nextId: state.nextId + 1, spawnedOnFloor: state.spawnedOnFloor + 1 };
}

export { ENEMY, dungeonPrice };
export { damageAlly };
