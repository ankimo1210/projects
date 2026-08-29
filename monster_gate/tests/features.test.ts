import { describe, expect, it } from "vitest";
import { meleeDamage } from "../src/engine/combat";
import { createRun } from "../src/engine/dungeon";
import { CRUEL, LEVELING, LIGHT, RULES, TIGHT, VAGUE, YUKAI } from "../src/engine/dungeon-def";
import { Rng } from "../src/engine/rng";
import { knownTiles, step } from "../src/engine/turn";
import { dist, idx, tileAt } from "../src/engine/types";
import { makeState } from "./helpers";

describe("boss", () => {
  it("is placed next to the stairs on boss floors, tripled HP, stationary", () => {
    let s = createRun(11, YUKAI, []);
    for (let f = 1; f < 4; f++) {
      s = { ...s, player: { ...s.player, pos: { ...s.map.stairs! } } };
      s = step(s, { type: "descend" }).state;
    }
    expect(s.floorNo).toBe(4);
    const boss = s.enemies.find((e) => e.boss)!;
    expect(boss).toBeTruthy();
    expect(boss.kind).toBe("goblin");
    expect(boss.maxHp).toBe(Math.round(21 * RULES.bossHpMul));
    expect(dist(boss.pos, s.map.stairs!)).toBe(1);
    const before = boss.pos;
    s = step(s, { type: "wait" }).state;
    expect(s.enemies.find((e) => e.boss)!.pos).toEqual(before);
  });

  it("attacks only about half the time and drops a rare card on death", () => {
    const s0 = makeState({ pos: { x: 2, y: 2 }, hp: 9999, maxHp: 9999, enemies: [{ kind: "goblin", pos: { x: 3, y: 2 }, boss: true }] });
    let s = s0;
    let attacks = 0;
    for (let i = 0; i < 200; i++) {
      const r = step(s, { type: "wait" });
      attacks += r.events.filter((e) => e.t === "attack" && e.by === 100).length;
      s = r.state;
    }
    expect(attacks).toBeGreaterThan(60);
    expect(attacks).toBeLessThan(140);
    const weak = { ...s0, enemies: [{ ...s0.enemies[0]!, hp: 1 }] };
    const { state, events } = step(weak, { type: "attack", dir: 2 });
    expect(events.some((e) => e.t === "bossDrop")).toBe(true);
    expect(state.items.some((it) => it.type === "card" && it.pos.x === 3 && it.pos.y === 2)).toBe(true);
  });
});

describe("castle rules", () => {
  it("dormant enemies ignore room entry and wake when adjacent", () => {
    const s0 = makeState({ dungeonId: VAGUE.id, pos: { x: 8, y: 3 }, enemies: [{ kind: "goblin", pos: { x: 10, y: 3 }, awake: false, dormant: true }] });
    const a = step(s0, { type: "move", dir: 2 }); // enter room 1 at (9,3), adjacent to goblin
    // entering the room does not wake it, but adjacency does on its own turn
    expect(a.state.enemies[0]!.awake).toBe(true);
    const far = makeState({ dungeonId: VAGUE.id, pos: { x: 8, y: 3 }, enemies: [{ kind: "goblin", pos: { x: 10, y: 2 }, awake: false, dormant: true }] });
    const b = step(far, { type: "move", dir: 2 }); // (9,3): dist 1 diagonal -> wakes
    expect(b.state.enemies[0]!.awake).toBe(true);
    const farther = makeState({ dungeonId: VAGUE.id, pos: { x: 1, y: 1 }, enemies: [{ kind: "goblin", pos: { x: 5, y: 5 }, awake: false, dormant: true }] });
    const c = step(farther, { type: "wait" });
    expect(c.state.enemies[0]!.awake).toBe(false);
    expect(createRun(3, VAGUE, []).enemies.every((e) => e.dormant)).toBe(true);
  });

  it("acid floor costs 1 HP per step in corridors, none in rooms", () => {
    const inRoom = step(makeState({ dungeonId: CRUEL.id, pos: { x: 2, y: 2 } }), { type: "move", dir: 2 });
    expect(inRoom.state.player.hp).toBe(30);
    const s0 = makeState({ dungeonId: CRUEL.id, pos: { x: 6, y: 3 } });
    const { state, events } = step(s0, { type: "move", dir: 2 }); // onto corridor (7,3)
    expect(state.player.hp).toBe(29);
    expect(events.some((e) => e.t === "acid")).toBe(true);
  });

  it("enemy crit rule doubles damage sometimes", () => {
    const rng = new Rng(3);
    expect(meleeDamage(rng, 10, 0, 1).crit).toBe(true);
    expect(meleeDamage(rng, 10, 0, 0).crit).toBe(false);
  });

  it("dark: the screen shows only the current view until a map card; memory itself is kept", () => {
    const s0 = makeState({ dungeonId: TIGHT.id, pos: { x: 1, y: 1 }, hand: ["map"] });
    const a = step(s0, { type: "wait" }).state;
    const inCorridor = { ...a, player: { ...a.player, pos: { x: 7, y: 3 } } };
    const c = step(inCorridor, { type: "wait" }).state;
    expect(c.explored[idx(c.map, { x: 1, y: 1 })]).toBe(true); // engine remembers
    expect(knownTiles(c)[idx(c.map, { x: 1, y: 1 })]).toBe(false); // screen does not
    const d = step(c, { type: "useCard", index: 0 }).state;
    expect(d.player.mapped).toBe(true);
    expect(knownTiles(d).every(Boolean)).toBe(true);
    const plain = step(makeState({ pos: { x: 7, y: 3 } }), { type: "wait" }).state;
    expect(knownTiles(plain)).toBe(plain.explored);
  });

  it("lit corridors: radius 3 in corridors", () => {
    const s0 = makeState({ dungeonId: LIGHT.id, pos: { x: 8, y: 3 } });
    const a = step(s0, { type: "wait" }).state;
    expect(a.explored[idx(a.map, { x: 10, y: 4 })]).toBe(true); // 2 away inside room 1
    const plain = step(makeState({ pos: { x: 8, y: 3 } }), { type: "wait" }).state;
    expect(plain.explored[idx(plain.map, { x: 10, y: 4 })]).toBe(false);
  });

  it("hand size rule limits the hand", () => {
    expect(TIGHT.handSize).toBe(6);
    const s = createRun(1, TIGHT, ["fire", "fire", "fire", "fire", "fire", "fire"]);
    expect(s.player.handSize).toBe(6);
    expect(() => createRun(1, TIGHT, Array(7).fill("fire"))).toThrow();
  });
});

describe("new cards", () => {
  it("meteor 60 / multiThunder 30 to all visible", () => {
    const s0 = makeState({ pos: { x: 1, y: 3 }, enemies: [{ kind: "dragon", pos: { x: 3, y: 3 } }, { kind: "goblin", pos: { x: 5, y: 5 } }], hand: ["meteor", "multiThunder"], mp: 100 });
    const a = step(s0, { type: "useCard", index: 0, dir: 2 }).state;
    expect(a.enemies.find((e) => e.kind === "dragon")!.hp).toBe(7);
    const b = step(a, { type: "useCard", index: 0 }).state;
    expect(b.enemies.find((e) => e.kind === "dragon")).toBeUndefined();
    expect(b.enemies.find((e) => e.kind === "goblin")).toBeUndefined();
  });

  it("panic: a confused enemy staggers instead of attacking", () => {
    const s0 = makeState({ pos: { x: 3, y: 3 }, enemies: [{ kind: "goblin", pos: { x: 4, y: 3 } }], hand: ["panic"] });
    let s = step(s0, { type: "useCard", index: 0, dir: 2 }).state;
    expect(s.enemies[0]!.confused).toBe(5);
    for (let i = 0; i < 5; i++) {
      const r = step(s, { type: "wait" });
      expect(r.events.some((e) => e.t === "attack")).toBe(false);
      s = r.state;
    }
    expect(s.enemies[0]!.confused).toBe(0);
  });

  it("multiPanic confuses every visible enemy", () => {
    const s0 = makeState({ pos: { x: 3, y: 3 }, enemies: [{ kind: "goblin", pos: { x: 1, y: 1 } }, { kind: "goblin", pos: { x: 5, y: 5 } }, { kind: "goblin", pos: { x: 10, y: 2 } }], hand: ["multiPanic"] });
    const { state } = step(s0, { type: "useCard", index: 0 });
    expect(state.enemies.map((e) => e.confused > 0)).toEqual([true, true, false]);
  });

  it("search / regen / longSword / powerShield / pocket2 / reviveRing", () => {
    let s = makeState({ hand: ["search", "regen", "longSword", "powerShield", "pocket2", "pocket2", "reviveRing"], mp: 100, hp: 10 });
    s = step(s, { type: "useCard", index: 0 }).state;
    expect(s.player.searched).toBe(true);
    s = step(s, { type: "useCard", index: 0 }).state;
    expect(s.player.status.regen).toBe(99);
    expect(s.player.hp).toBe(11);
    s = step(s, { type: "useCard", index: 0 }).state;
    expect(s.player.equipment.weaponBonus).toBe(8);
    s = step(s, { type: "useCard", index: 0 }).state;
    expect(s.player.equipment.shieldBonus).toBe(4);
    s = step(s, { type: "useCard", index: 0 }).state;
    expect(s.player.handSize).toBe(12);
    const again = step(s, { type: "useCard", index: 0 });
    expect(again.state.player.handSize).toBe(12);
    expect(again.events[0]).toEqual({ t: "blocked", reason: "already used" });
    s = step(s, { type: "discardCard", index: 0 }).state;
    s = step(s, { type: "useCard", index: 0 }).state;
    expect(s.player.equipment.revive).toBe(true);
    // lethal hit -> revive at half HP once
    const lethal = { ...s, player: { ...s.player, hp: 1 }, enemies: [{ ...makeState({ enemies: [{ kind: "dragon", pos: { x: 2, y: 1 } }] }).enemies[0]! }] };
    const r = step(lethal, { type: "wait" });
    expect(r.events.some((e) => e.t === "revived")).toBe(true);
    expect(r.state.result).toBeNull();
    expect(r.state.player.hp).toBe(Math.floor(r.state.player.maxHp / 2));
    expect(r.state.player.equipment.revive).toBe(false);
  });

  it("powerUp: +10 levels with the same gains as natural levelling, plus HP+10", () => {
    const s0 = makeState({ hand: ["powerUp"], mp: 100, hp: 30 });
    const { state, events } = step(s0, { type: "useCard", index: 0 });
    expect(state.player.level).toBe(11);
    expect(state.player.maxHp).toBe(30 + 10 * LEVELING.hpPerLevel);
    expect(state.player.atk).toBe(8 + 5); // levels 2,4,6,8,10
    expect(state.player.def).toBe(1 + 2); // levels 5,10
    expect(state.player.hp).toBe(Math.min(state.player.maxHp, 30 + 10 * LEVELING.hpPerLevel + 10));
    expect(events.some((e) => e.t === "grow" && e.level === 10)).toBe(true);
  });

  it("shield bonus reduces enemy melee damage", () => {
    const base = makeState({ pos: { x: 2, y: 2 }, enemies: [{ kind: "goblin", pos: { x: 3, y: 2 } }], hp: 999, maxHp: 999 });
    const shielded = { ...base, player: { ...base.player, equipment: { ...base.player.equipment, shieldBonus: 4 } } };
    const a = step(base, { type: "wait" }).events.find((e) => e.t === "attack")!;
    const b = step(shielded, { type: "wait" }).events.find((e) => e.t === "attack")!;
    if (a.t === "attack" && b.t === "attack") expect(a.dmg - b.dmg).toBe(4);
  });

  it("bronze sword does not downgrade a long sword", () => {
    let s = makeState({ hand: ["longSword", "bronzeSword"], mp: 100 });
    s = step(s, { type: "useCard", index: 0 }).state;
    s = step(s, { type: "useCard", index: 0 }).state;
    expect(s.player.equipment.weaponBonus).toBe(8);
  });

  it("sanity: every dungeon has a reachable final altar", () => {
    for (const def of [LIGHT, YUKAI, VAGUE, CRUEL, TIGHT]) {
      const last = def.floors[def.floors.length - 1]!;
      expect(last.map.final).toBe(true);
      const s = createRun(2, def, []);
      expect(tileAt(s.map, s.map.entrance).kind).toBe("floor");
    }
  });
});
