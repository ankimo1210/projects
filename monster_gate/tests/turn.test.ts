import { describe, expect, it } from "vitest";
import { step } from "../src/engine/turn";
import { makeState } from "./helpers";

describe("turn: movement", () => {
  it("moving into a wall does not consume a turn", () => {
    const s0 = makeState({ pos: { x: 1, y: 1 } });
    const { state, events } = step(s0, { type: "move", dir: 0 });
    expect(state.turn).toBe(0);
    expect(state.player.pos).toEqual({ x: 1, y: 1 });
    expect(events.some((e) => e.t === "blocked")).toBe(true);
  });

  it("moving onto an enemy becomes an attack", () => {
    const s0 = makeState({ pos: { x: 2, y: 2 }, enemies: [{ kind: "puunya_g", pos: { x: 3, y: 2 } }] });
    const { state, events } = step(s0, { type: "move", dir: 2 });
    expect(state.player.pos).toEqual({ x: 2, y: 2 });
    expect(events.find((e) => e.t === "attack" && e.by === "player")).toBeTruthy();
    expect(state.turn).toBe(1);
  });

  it("forbids corner cutting", () => {
    // from the corridor (7,3) moving NE to (8,2) is wall anyway; test door diagonal:
    // (5,2) -> SE (6,3) door: orthogonal (6,2) is wall => blocked
    const s0 = makeState({ pos: { x: 5, y: 2 } });
    const { state } = step(s0, { type: "move", dir: 3 });
    expect(state.player.pos).toEqual({ x: 5, y: 2 });
  });

  it("wait consumes a turn and lets enemies act", () => {
    const s0 = makeState({ pos: { x: 2, y: 2 }, enemies: [{ kind: "puunya_g", pos: { x: 4, y: 2 } }] });
    const { state } = step(s0, { type: "wait" });
    expect(state.turn).toBe(1);
    expect(state.enemies[0]!.pos).toEqual({ x: 3, y: 2 });
  });

  it("entering a new room heals HP+5 and MP+10 once", () => {
    const s0 = makeState({ pos: { x: 8, y: 3 }, hp: 10, mp: 10 });
    const a = step(s0, { type: "move", dir: 2 }); // into room 1 at (9,3)
    expect(a.state.player.hp).toBe(15);
    expect(a.state.player.mp).toBe(20);
    const b = step(a.state, { type: "move", dir: 6 }); // back to corridor
    const c = step(b.state, { type: "move", dir: 2 }); // re-enter
    expect(c.state.player.hp).toBe(15);
    expect(c.state.player.mp).toBe(20);
  });

  it("picks up cards and WIN; hand full leaves the card", () => {
    const full = Array(10).fill("potion20") as "potion20"[];
    const s0 = makeState({
      pos: { x: 1, y: 1 },
      hand: full,
      items: [
        { id: 1, pos: { x: 2, y: 1 }, type: "card", card: "fire" },
        { id: 2, pos: { x: 3, y: 1 }, type: "win", amount: 5 },
      ],
    });
    const a = step(s0, { type: "move", dir: 2 });
    expect(a.events.some((e) => e.t === "handFull")).toBe(true);
    expect(a.state.items.length).toBe(2);
    const b = step(a.state, { type: "move", dir: 2 });
    expect(b.state.winCollected).toBe(5);
    expect(b.state.items.length).toBe(1);
    const c = step(b.state, { type: "discardCard", index: 0 });
    expect(c.state.turn).toBe(b.state.turn); // no turn
    const d = step(c.state, { type: "move", dir: 6 }); // back onto fire
    expect(d.state.player.hand).toContain("fire");
  });

  it("does not step the run once it is over", () => {
    const s0 = { ...makeState(), result: "dead" as const };
    const { state, events } = step(s0, { type: "wait" });
    expect(state).toBe(s0);
    expect(events[0]?.t).toBe("blocked");
  });

  it("never mutates the input state", () => {
    const s0 = makeState({ pos: { x: 2, y: 2 }, enemies: [{ kind: "puunya_g", pos: { x: 4, y: 2 } }], hand: ["potion20"] });
    const snapshot = JSON.stringify(s0);
    step(s0, { type: "wait" });
    step(s0, { type: "move", dir: 2 });
    step(s0, { type: "useCard", index: 0 });
    expect(JSON.stringify(s0)).toBe(snapshot);
  });
});

describe("turn: stairs and altar", () => {
  it("descend only works on the stairs and moves to the next floor", () => {
    const s0 = makeState({ pos: { x: 9, y: 4 } });
    const bad = step(s0, { type: "descend" });
    expect(bad.state.floorNo).toBe(1);
    const onStairs = step(s0, { type: "move", dir: 2 }).state;
    const ok = step(onStairs, { type: "descend" });
    expect(ok.state.floorNo).toBe(2);
    expect(ok.state.turnsOnFloor).toBe(0);
    expect(ok.state.player.bright).toBe(false);
    expect(ok.state.enemies.length).toBeGreaterThan(0);
  });

  it("taking the altar clears the run with base WIN + collected", () => {
    const s0 = { ...makeState({ pos: { x: 10, y: 4 }, final: true, floorNo: 7 }), winCollected: 12 };
    const { state, events } = step(s0, { type: "takeAltar" });
    expect(state.result).toBe("clear");
    expect(events.find((e) => e.t === "cleared")).toEqual({ t: "cleared", win: 102 });
  });
});
