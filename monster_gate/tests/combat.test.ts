import { describe, expect, it } from "vitest";
import { gainXp, meleeDamage, rangedDamage } from "../src/engine/combat";
import { ENEMY, LEVELING, WARRIOR } from "../src/engine/dungeon-def";
import { Rng } from "../src/engine/rng";
import { step } from "../src/engine/turn";
import { makeState } from "./helpers";

describe("combat", () => {
  it("melee damage is at least 1", () => {
    const rng = new Rng(1);
    for (let i = 0; i < 200; i++) expect(meleeDamage(rng, 1, 50, 0).dmg).toBe(1);
  });

  it("crit doubles", () => {
    const rng = new Rng(1);
    let seenCrit = false;
    for (let i = 0; i < 500; i++) {
      const r = meleeDamage(rng, 10, 0, 0.5);
      if (r.crit) {
        seenCrit = true;
        expect(r.dmg).toBeGreaterThanOrEqual(18);
      }
    }
    expect(seenCrit).toBe(true);
  });

  it("ranged damage falls off with distance", () => {
    expect(rangedDamage(20, 2, 1)).toBe(18);
    expect(rangedDamage(20, 2, 3)).toBe(6);
    expect(rangedDamage(4, 3, 6)).toBe(1);
  });

  it("trivial kills give no XP; otherwise XP accrues and levels apply stat gains", () => {
    const high = makeState({ level: ENEMY.puunya_g.trivialAt + 1 });
    expect(gainXp(high.player, "puunya_g").gains).toEqual({ level: 0, hp: 0, atk: 0, def: 0 });
    let p = makeState().player;
    // level 1 needs xpToNext(1) = 3; one green puunya (3 xp) levels up to 2 (+hp, +atk on even level)
    const r = gainXp(p, "puunya_g");
    expect(r.player.level).toBe(2);
    expect(r.player.xp).toBe(0);
    expect(r.gains).toEqual({ level: 1, hp: LEVELING.hpPerLevel, atk: 1, def: 0 });
    p = r.player;
    // reaching level 5 grants DEF
    let defGain = 0;
    while (p.level < 5) {
      const g = gainXp(p, "dragon");
      defGain += g.gains.def;
      p = g.player;
    }
    expect(defGain).toBe(1);
  });

  it("killing an enemy that levels the player emits a grow event", () => {
    const s0 = makeState({ pos: { x: 2, y: 2 }, enemies: [{ kind: "puunya_g", pos: { x: 3, y: 2 }, hp: 1 }] });
    const { state, events } = step(s0, { type: "attack", dir: 2 });
    expect(state.enemies.length).toBe(0);
    expect(events.some((e) => e.t === "died")).toBe(true);
    expect(state.player.level).toBe(2);
    expect(state.player.maxHp).toBe(WARRIOR.hp + LEVELING.hpPerLevel);
    expect(events.some((e) => e.t === "grow")).toBe(true);
  });

  it("weapon bonus is applied to melee", () => {
    const base = makeState({ pos: { x: 2, y: 2 }, enemies: [{ kind: "dragon", pos: { x: 3, y: 2 } }] });
    const armed = { ...base, player: { ...base.player, equipment: { ...base.player.equipment, weaponBonus: 4 } } };
    const a = step(base, { type: "attack", dir: 2 });
    const b = step(armed, { type: "attack", dir: 2 });
    const dmgA = a.events.find((e) => e.t === "attack" && e.by === "player")!;
    const dmgB = b.events.find((e) => e.t === "attack" && e.by === "player")!;
    if (dmgA.t === "attack" && dmgB.t === "attack" && !dmgA.crit && !dmgB.crit) {
      expect(dmgB.dmg - dmgA.dmg).toBe(4);
    }
  });

  it("player dies at 0 HP", () => {
    const s0 = makeState({ pos: { x: 2, y: 2 }, hp: 1, enemies: [{ kind: "goblin", pos: { x: 3, y: 2 } }] });
    const { state, events } = step(s0, { type: "wait" });
    expect(state.result).toBe("dead");
    expect(state.player.hp).toBe(0);
    expect(events.some((e) => e.t === "playerDied")).toBe(true);
  });
});
