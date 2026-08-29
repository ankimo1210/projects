import { describe, expect, it } from "vitest";
import { CARDS } from "../src/engine/cards";
import { step } from "../src/engine/turn";
import { makeState } from "./helpers";

describe("cards", () => {
  it("potions heal and are capped at maxHp", () => {
    const s0 = makeState({ hp: 20, hand: ["potion20", "potion40"] });
    const a = step(s0, { type: "useCard", index: 0 });
    expect(a.state.player.hp).toBe(30);
    expect(a.state.player.mp).toBe(28);
    expect(a.state.player.hand).toEqual(["potion40"]);
    expect(a.state.turn).toBe(1);
  });

  it("not enough MP: no effect, no turn", () => {
    const s0 = makeState({ hp: 10, mp: 1, hand: ["potion20"] });
    const { state, events } = step(s0, { type: "useCard", index: 0 });
    expect(state).toBe(s0);
    expect(events[0]).toEqual({ t: "notEnoughMp", card: "potion20", need: 2 });
  });

  it("discarding refunds the MP cost, capped at maxMp, no turn", () => {
    const s0 = makeState({ mp: 98, hand: ["thunder"] });
    const { state, events } = step(s0, { type: "discardCard", index: 0 });
    expect(state.player.mp).toBe(100);
    expect(state.player.hand).toEqual([]);
    expect(state.turn).toBe(0);
    expect(events[0]).toEqual({ t: "discarded", card: "thunder", mpBack: 2 });
  });

  it("fire hits the first enemy in a line within 5 and ignores defense", () => {
    const s0 = makeState({
      pos: { x: 1, y: 3 },
      enemies: [
        { kind: "dragon", pos: { x: 3, y: 3 } },
        { kind: "puunya_g", pos: { x: 5, y: 3 } },
      ],
      hand: ["fire"],
    });
    const { state } = step(s0, { type: "useCard", index: 0, dir: 2 });
    expect(state.enemies.find((e) => e.kind === "dragon")!.hp).toBe(67 - 15);
    expect(state.enemies.find((e) => e.kind === "puunya_g")!.hp).toBe(9);
  });

  it("fire without a target is refused without cost", () => {
    const s0 = makeState({ pos: { x: 1, y: 3 }, hand: ["fire"] });
    const { state, events } = step(s0, { type: "useCard", index: 0, dir: 2 });
    expect(state).toBe(s0);
    expect(events[0]).toEqual({ t: "blocked", reason: "no target" });
    const noDir = step(s0, { type: "useCard", index: 0 });
    expect(noDir.state).toBe(s0);
  });

  it("thunder does 30 and kills weak enemies, awarding XP", () => {
    const s0 = makeState({ pos: { x: 1, y: 3 }, enemies: [{ kind: "goblin", pos: { x: 4, y: 3 } }], hand: ["thunder"] });
    const { state, events } = step(s0, { type: "useCard", index: 0, dir: 2 });
    expect(state.enemies.length).toBe(0);
    expect(events.some((e) => e.t === "died")).toBe(true);
    expect(state.player.level).toBeGreaterThan(1);
  });

  it("multiFire hits every visible enemy and nothing in another room", () => {
    const s0 = makeState({
      pos: { x: 3, y: 3 },
      enemies: [
        { kind: "goblin", pos: { x: 1, y: 1 } },
        { kind: "goblin", pos: { x: 5, y: 5 } },
        { kind: "goblin", pos: { x: 10, y: 2 } },
      ],
      hand: ["multiFire"],
    });
    const { state } = step(s0, { type: "useCard", index: 0 });
    const hps = state.enemies.map((e) => e.hp).sort((a, b) => a - b);
    expect(hps).toEqual([6, 6, 21]);
  });

  it("haste gives 4 actions during which enemies move only twice", () => {
    const s0 = makeState({ pos: { x: 1, y: 1 }, enemies: [{ kind: "puunya_g", pos: { x: 5, y: 5 } }], hand: ["haste"] });
    let s = step(s0, { type: "useCard", index: 0 }).state; // action 1 (haste 4->3, enemies skip)
    expect(s.enemies[0]!.pos).toEqual({ x: 5, y: 5 });
    s = step(s, { type: "wait" }).state; // 3->2, enemies act
    expect(s.enemies[0]!.pos).toEqual({ x: 4, y: 4 });
    s = step(s, { type: "wait" }).state; // 2->1 skip
    expect(s.enemies[0]!.pos).toEqual({ x: 4, y: 4 });
    s = step(s, { type: "wait" }).state; // 1->0 act
    expect(s.enemies[0]!.pos).toEqual({ x: 3, y: 3 });
    s = step(s, { type: "wait" }).state; // normal
    expect(s.enemies[0]!.pos).toEqual({ x: 2, y: 2 });
  });

  it("bright reveals the whole floor and resets on descend", () => {
    const s0 = makeState({ pos: { x: 9, y: 4 }, hand: ["bright"] });
    const a = step(s0, { type: "useCard", index: 0 });
    expect(a.state.player.bright).toBe(true);
    expect(a.state.explored.every(Boolean)).toBe(true);
    const b = step(step(a.state, { type: "move", dir: 2 }).state, { type: "descend" });
    expect(b.state.player.bright).toBe(false);
  });

  it("warp moves to a free walkable cell and is deterministic", () => {
    const s0 = makeState({ pos: { x: 1, y: 1 }, hand: ["warp"] });
    const a = step(s0, { type: "useCard", index: 0 });
    const b = step(s0, { type: "useCard", index: 0 });
    expect(a.state.player.pos).toEqual(b.state.player.pos);
    expect(a.state.player.pos).not.toEqual({ x: 1, y: 1 });
    expect(a.state.map.tiles[a.state.player.pos.y * 12 + a.state.player.pos.x]!.kind).not.toBe("wall");
  });

  it("escape ends the run keeping hand and collected WIN", () => {
    const s0 = { ...makeState({ hand: ["escape", "fire"] }), winCollected: 7 };
    const { state, events } = step(s0, { type: "useCard", index: 0 });
    expect(state.result).toBe("escaped");
    expect(state.player.hand).toEqual(["fire"]);
    expect(events).toContainEqual({ t: "escaped", win: 7 });
  });

  it("bronze sword sets the weapon bonus", () => {
    const s0 = makeState({ hand: ["bronzeSword"] });
    const { state } = step(s0, { type: "useCard", index: 0 });
    expect(state.player.equipment.weaponBonus).toBe(4);
  });

  it("every card has a positive MP cost and a name", () => {
    for (const [id, c] of Object.entries(CARDS)) {
      expect(c.mp, id).toBeGreaterThan(0);
      expect(c.name.length).toBeGreaterThan(0);
    }
  });
});
