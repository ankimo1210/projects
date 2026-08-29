import { describe, expect, it } from "vitest";
import { createRun } from "../src/engine/dungeon";
import { CARD_EFFECT } from "../src/engine/cards";
import { CASINO, CLASSES, COLD, DOUBLE_UP, YUKAI, payoutFor } from "../src/engine/dungeon-def";
import { step } from "../src/engine/turn";
import { generateFloor, restingCells } from "../src/engine/mapgen";
import { idx, type ClassId } from "../src/engine/types";
import { makeState } from "./helpers";

describe("classes", () => {
  it("createRun uses the class stats", () => {
    for (const cls of Object.keys(CLASSES) as ClassId[]) {
      const s = createRun(4, YUKAI, [], cls);
      const c = CLASSES[cls];
      expect(s.player.cls).toBe(cls);
      expect(s.player.maxHp).toBe(c.hp);
      expect(s.player.atk).toBe(c.atk);
      expect(s.player.def).toBe(c.def);
      expect(s.player.maxMp).toBe(c.maxMp);
    }
  });

  it("mage: attack cards +50%, potions +25%", () => {
    const base = { pos: { x: 1, y: 3 }, enemies: [{ kind: "dragon" as const, pos: { x: 3, y: 3 } }], hand: ["fire" as const], mp: 50 };
    const warrior = step(makeState(base), { type: "useCard", index: 0, dir: 2 }).state;
    const mage = step(makeState({ ...base, cls: "mage" }), { type: "useCard", index: 0, dir: 2 }).state;
    expect(warrior.enemies[0]!.hp).toBe(67 - CARD_EFFECT.fireDamage);
    expect(mage.enemies[0]!.hp).toBe(67 - Math.round(CARD_EFFECT.fireDamage * 1.5));

    const heal = { hand: ["potion20" as const], hp: 1, maxHp: 99, mp: 50 };
    expect(step(makeState(heal), { type: "useCard", index: 0 }).state.player.hp).toBe(21);
    expect(step(makeState({ ...heal, cls: "mage" }), { type: "useCard", index: 0 }).state.player.hp).toBe(26);
  });

  it("mage sees further in corridors", () => {
    const at = { pos: { x: 7, y: 3 } };
    const warrior = step(makeState(at), { type: "wait" }).state;
    const mage = step(makeState({ ...at, cls: "mage" }), { type: "wait" }).state;
    expect(warrior.explored[idx(warrior.map, { x: 9, y: 3 })]).toBe(false);
    expect(mage.explored[idx(mage.map, { x: 9, y: 3 })]).toBe(true);
  });

  it("gambler: luckier casino odds and richer rare drops", () => {
    let lucky = 0;
    let plain = 0;
    for (const cls of ["gambler", "warrior"] as ClassId[]) {
      let s = makeState({ cls, winCollected: 10_000, tiles: [{ x: 3, y: 3, kind: "casino" }], pos: { x: 3, y: 3 }, seed: 9 });
      for (let i = 0; i < 400; i++) {
        s = { ...step(s, { type: "spin" }).state, casinoSpins: 0 };
      }
      if (cls === "gambler") lucky = s.winCollected;
      else plain = s.winCollected;
    }
    expect(lucky).toBeGreaterThan(plain);
  });
});

describe("summons", () => {
  const summon = { hand: ["summonGoblin" as const], mp: 50, pos: { x: 2, y: 2 } };

  it("appears next to the player and is capped", () => {
    const { state, events } = step(makeState(summon), { type: "useCard", index: 0 });
    expect(state.allies.length).toBe(1);
    expect(Math.max(Math.abs(state.allies[0]!.pos.x - 2), Math.abs(state.allies[0]!.pos.y - 2))).toBe(1);
    expect(events.some((e) => e.t === "summoned")).toBe(true);
    const full = makeState({ ...summon, allies: [{ kind: "goblin", pos: { x: 1, y: 1 } }, { kind: "goblin", pos: { x: 3, y: 3 } }] });
    const capped = step(full, { type: "useCard", index: 0 });
    expect(capped.state).toBe(full);
  });

  it("attacks adjacent enemies without giving the player XP", () => {
    const s0 = makeState({ pos: { x: 1, y: 1 }, allies: [{ kind: "dragon", pos: { x: 4, y: 4 } }], enemies: [{ kind: "puunya_g", pos: { x: 5, y: 4 }, hp: 3 }] });
    const { state, events } = step(s0, { type: "wait" });
    expect(events.some((e) => e.t === "allyHit")).toBe(true);
    expect(state.enemies.length).toBe(0);
    expect(state.player.level).toBe(1); // no XP from an ally kill
  });

  it("follows the player and swaps places when walked into", () => {
    let s = makeState({ pos: { x: 2, y: 2 }, allies: [{ kind: "goblin", pos: { x: 5, y: 5 } }] });
    s = step(s, { type: "wait" }).state;
    expect(s.allies[0]!.pos).toEqual({ x: 4, y: 4 });
    const ally = { ...s.allies[0]!, pos: { x: 3, y: 2 } };
    const adjacent = { ...s, allies: [ally] };
    const swapped = step(adjacent, { type: "move", dir: 2 }).state;
    expect(swapped.player.pos).toEqual({ x: 3, y: 2 });
    expect(swapped.allies[0]!.pos).toEqual({ x: 2, y: 2 });
  });

  it("soaks hits: an enemy next to the summon but not the player attacks it", () => {
    const s0 = makeState({ pos: { x: 1, y: 1 }, allies: [{ kind: "goblin", pos: { x: 4, y: 4 } }], enemies: [{ kind: "goblin", pos: { x: 5, y: 4 } }] });
    const { state, events } = step(s0, { type: "wait" });
    expect(events.some((e) => e.t === "allyHurt")).toBe(true);
    expect(state.player.hp).toBe(30);
  });

  it("is left behind on the stairs", () => {
    const s0 = makeState({ pos: { x: 9, y: 4 }, allies: [{ kind: "goblin", pos: { x: 9, y: 3 } }] });
    const onStairs = step(s0, { type: "move", dir: 2 }).state;
    const next = step(onStairs, { type: "descend" }).state;
    expect(next.allies).toEqual([]);
  });
});

describe("ice", () => {
  const ice = [
    { x: 2, y: 2, kind: "ice" as const },
    { x: 3, y: 2, kind: "ice" as const },
    { x: 4, y: 2, kind: "ice" as const },
  ];

  it("slides until leaving the ice", () => {
    const { state, events } = step(makeState({ pos: { x: 1, y: 2 }, tiles: ice }), { type: "move", dir: 2 });
    expect(state.player.pos).toEqual({ x: 5, y: 2 });
    expect(events.some((e) => e.t === "slide")).toBe(true);
  });

  it("stops in front of an enemy and only the player slides", () => {
    const blocked = step(makeState({ pos: { x: 1, y: 2 }, tiles: ice, enemies: [{ kind: "puunya_g", pos: { x: 4, y: 2 } }] }), { type: "move", dir: 2 });
    expect(blocked.state.player.pos).toEqual({ x: 3, y: 2 });
    const enemyOnIce = step(makeState({ pos: { x: 1, y: 5 }, tiles: ice, enemies: [{ kind: "puunya_g", pos: { x: 4, y: 2 } }] }), { type: "wait" });
    const moved = enemyOnIce.state.enemies[0]!.pos;
    expect(Math.max(Math.abs(moved.x - 4), Math.abs(moved.y - 2))).toBe(1);
  });

  it("picks up whatever is at the landing tile", () => {
    const s0 = makeState({ pos: { x: 1, y: 2 }, tiles: ice, items: [{ id: 1, pos: { x: 5, y: 2 }, type: "card", card: "fire" }] });
    const { state } = step(s0, { type: "move", dir: 2 });
    expect(state.player.hand).toEqual(["fire"]);
  });

  it("COLD generates ice, and every floor's goal and items stay reachable despite sliding", () => {
    expect(createRun(6, COLD, []).map.tiles.some((t) => t.kind === "ice")).toBe(true);
    for (let seed = 1; seed <= 60; seed++) {
      for (const fdef of COLD.floors) {
        const { map } = generateFloor(seed * 977 + COLD.floors.indexOf(fdef), fdef.map);
        const rest = restingCells(map, map.entrance);
        const goal = map.stairs ?? map.altar!;
        expect(rest[idx(map, goal)], `seed ${seed} goal`).toBe(true);
        if (map.shop) expect(rest[idx(map, map.shop)]).toBe(true);
        if (map.casino) expect(rest[idx(map, map.casino)]).toBe(true);
      }
      const run = createRun(seed, COLD, []);
      const rest = restingCells(run.map, run.map.entrance);
      for (const it of run.items) expect(rest[idx(run.map, it.pos)], `seed ${seed} item`).toBe(true);
    }
  });
});

describe("shop and casino", () => {
  const offers = [
    { card: "potion80" as const, price: 16, sold: false },
    { card: "fire" as const, price: 6, sold: false },
    { card: "meteor" as const, price: 20, sold: false },
  ];
  const shopState = (extra = {}) =>
    makeState({ pos: { x: 3, y: 3 }, tiles: [{ x: 3, y: 3, kind: "shop" }], offers: offers.map((o) => ({ ...o })), winCollected: 20, ...extra });

  it("buying spends collected WIN, fills the hand and costs no turn", () => {
    const { state, events } = step(shopState(), { type: "buy", index: 1 });
    expect(state.player.hand).toEqual(["fire"]);
    expect(state.winCollected).toBe(14);
    expect(state.offers[1]!.sold).toBe(true);
    expect(state.turn).toBe(0);
    expect(events.some((e) => e.t === "bought")).toBe(true);
  });

  it("refuses when poor, sold out, hand-full or off the tile", () => {
    const poor = step(shopState({ winCollected: 2 }), { type: "buy", index: 1 });
    expect(poor.events[0]).toEqual({ t: "blocked", reason: "not enough win" });
    const once = step(shopState(), { type: "buy", index: 1 }).state;
    expect(step(once, { type: "buy", index: 1 }).events[0]).toEqual({ t: "blocked", reason: "sold out" });
    const full = shopState({ hand: Array(10).fill("potion20") });
    expect(step(full, { type: "buy", index: 1 }).events[0]).toEqual({ t: "blocked", reason: "hand full" });
    const away = step(shopState({ pos: { x: 2, y: 2 } }), { type: "buy", index: 1 });
    expect(away.events[0]).toEqual({ t: "blocked", reason: "not in a shop" });
  });

  it("the casino takes the bet, pays multiples and runs out", () => {
    let s = makeState({ pos: { x: 3, y: 3 }, tiles: [{ x: 3, y: 3, kind: "casino" }], winCollected: 100, seed: 5 });
    let spins = 0;
    for (let i = 0; i < CASINO.maxSpins; i++) {
      const r = step(s, { type: "spin" });
      const ev = r.events.find((e) => e.t === "spun");
      expect(ev).toBeTruthy();
      if (ev?.t === "spun") expect([0, 10, 20, 50]).toContain(ev.payout);
      spins++;
      s = r.state;
    }
    expect(s.casinoSpins).toBe(spins);
    expect(step(s, { type: "spin" }).events[0]).toEqual({ t: "blocked", reason: "out of order" });
  });
});

describe("double up", () => {
  it("doubles the clear payout, and only on a clear", () => {
    const s0 = makeState({ pos: { x: 1, y: 1 }, items: [{ id: 1, pos: { x: 2, y: 1 }, type: "doubleUp" }] });
    const picked = step(s0, { type: "move", dir: 2 });
    expect(picked.state.winMultiplier).toBe(DOUBLE_UP.factor);
    expect(picked.events.some((e) => e.t === "doubleUp")).toBe(true);

    const clear = makeState({ pos: { x: 10, y: 4 }, final: true, winMultiplier: 2, winCollected: 10 });
    const done = step(clear, { type: "takeAltar" });
    expect(done.events.find((e) => e.t === "cleared")).toEqual({ t: "cleared", win: (YUKAI.win + 10) * 2 });

    expect(payoutFor(YUKAI, { result: "escaped", winCollected: 10, multiplier: 4 })).toBe(10);
    expect(payoutFor(YUKAI, { result: "dead", winCollected: 10, multiplier: 4 })).toBe(50);
  });

  it("stacks multiplicatively", () => {
    let s = makeState({
      pos: { x: 1, y: 1 },
      items: [
        { id: 1, pos: { x: 2, y: 1 }, type: "doubleUp" },
        { id: 2, pos: { x: 3, y: 1 }, type: "doubleUp" },
      ],
    });
    s = step(s, { type: "move", dir: 2 }).state;
    s = step(s, { type: "move", dir: 2 }).state;
    expect(s.winMultiplier).toBe(4);
  });
});
