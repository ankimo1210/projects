import { describe, expect, it } from "vitest";
import { ENEMY, RULES, WARRIOR } from "../src/engine/dungeon-def";
import { step } from "../src/engine/turn";
import { makeState } from "./helpers";

describe("ai", () => {
  it("approaches when it sees the player and attacks when adjacent", () => {
    let s = makeState({ pos: { x: 1, y: 1 }, enemies: [{ kind: "puunya_g", pos: { x: 5, y: 5 } }] });
    s = step(s, { type: "wait" }).state;
    expect(s.enemies[0]!.pos).toEqual({ x: 4, y: 4 });
    s = step(s, { type: "wait" }).state;
    s = step(s, { type: "wait" }).state;
    expect(s.enemies[0]!.pos).toEqual({ x: 2, y: 2 });
    const r = step(s, { type: "wait" });
    expect(r.events.some((e) => e.t === "attack" && e.by === 100)).toBe(true);
    expect(r.state.player.hp).toBeLessThan(30);
  });

  it("sleeping enemies (not awake) do nothing until the player enters the room", () => {
    const s0 = makeState({ pos: { x: 7, y: 3 }, enemies: [{ kind: "puunya_g", pos: { x: 10, y: 2 }, awake: false }] });
    const a = step(s0, { type: "wait" });
    expect(a.state.enemies[0]!.pos).toEqual({ x: 10, y: 2 });
    expect(a.state.enemies[0]!.awake).toBe(false);
    const b = step(a.state, { type: "move", dir: 2 }); // (8,3) still corridor
    const c = step(b.state, { type: "move", dir: 2 }); // (9,3) room 1
    expect(c.state.enemies[0]!.awake).toBe(true);
  });

  it("ranged enemies shoot along a clear line and damage falls with distance", () => {
    const s0 = makeState({ pos: { x: 1, y: 3 }, enemies: [{ kind: "kemunpa", pos: { x: 5, y: 3 } }] });
    const { events } = step(s0, { type: "wait" });
    const shot = events.find((e) => e.t === "attack" && e.by === 100);
    expect(shot).toBeTruthy();
    if (shot?.t === "attack") {
      expect(shot.ranged).toBe(true);
      expect(shot.dmg).toBe(Math.max(1, Math.floor((ENEMY.kemunpa.atk - WARRIOR.def) / 4)));
    }
  });

  it("does not shoot when another enemy blocks the line", () => {
    const s0 = makeState({
      pos: { x: 1, y: 3 },
      enemies: [
        { kind: "kemunpa", pos: { x: 5, y: 3 } },
        { kind: "puunya_g", pos: { x: 3, y: 3 } },
      ],
    });
    const { events } = step(s0, { type: "wait" });
    expect(events.some((e) => e.t === "attack" && e.by === 100 && e.ranged)).toBe(false);
  });

  it("walks to the last seen position after losing sight, then forgets", () => {
    // player (5,3) in room 0, enemy (1,3). Player walks out through the door into room 1.
    let s = makeState({ pos: { x: 5, y: 3 }, enemies: [{ kind: "puunya_g", pos: { x: 1, y: 3 } }] });
    s = step(s, { type: "wait" }).state; // enemy sees (5,3), moves to (2,3)
    expect(s.enemies[0]!.lastSeen).toEqual({ x: 5, y: 3 });
    s = step(s, { type: "move", dir: 2 }).state; // player on door (6,3): still visible from the room
    expect(s.enemies[0]!.lastSeen).toEqual({ x: 6, y: 3 });
    s = step(s, { type: "move", dir: 2 }).state; // (7,3) corridor: out of sight
    expect(s.enemies[0]!.lastSeen).toEqual({ x: 6, y: 3 });
    expect(s.enemies[0]!.pos).toEqual({ x: 4, y: 3 });
    s = step(s, { type: "move", dir: 2 }).state; // (8,3)
    s = step(s, { type: "move", dir: 2 }).state; // (9,3) room 1; enemy reaches (6,3) and forgets
    expect(s.enemies[0]!.pos).toEqual({ x: 6, y: 3 });
    expect(s.enemies[0]!.lastSeen).toBeNull();
  });

  it("a slept enemy does not act while the counter runs", () => {
    const s0 = makeState({ pos: { x: 2, y: 2 }, enemies: [{ kind: "puunya_g", pos: { x: 3, y: 2 } }], hand: ["sleep"] });
    let s = step(s0, { type: "useCard", index: 0, dir: 2 }).state;
    expect(s.enemies[0]!.sleep).toBe(7); // 8, then one enemy phase already elapsed
    for (let i = 0; i < 6; i++) {
      const r = step(s, { type: "wait" });
      expect(r.events.some((e) => e.t === "attack")).toBe(false);
      s = r.state;
    }
  });

  it("spawns extra enemies after lingering on a floor, out of sight, up to the cap", () => {
    let s = makeState({ pos: { x: 1, y: 1 }, hp: 9999, maxHp: 9999 });
    let spawns = 0;
    for (let i = 0; i < 200; i++) {
      const r = step(s, { type: "wait" });
      spawns += r.events.filter((e) => e.t === "spawn").length;
      s = r.state;
    }
    expect(spawns).toBe(RULES.spawnCap);
    expect(s.spawnedOnFloor).toBe(RULES.spawnCap);
  });
});
