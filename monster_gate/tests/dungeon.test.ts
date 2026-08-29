import { describe, expect, it } from "vitest";
import { createRun } from "../src/engine/dungeon";
import { YUKAI } from "../src/engine/dungeon-def";
import { step } from "../src/engine/turn";
import { tileAt, type Dir, type DungeonState } from "../src/engine/types";
import { reachable } from "../src/engine/mapgen";

function walkTo(s: DungeonState, target: { x: number; y: number }): DungeonState {
  // BFS path over walkable tiles, then step it; kill anything in the way by bumping.
  const { map } = s;
  const prev = new Map<number, number>();
  const start = s.player.pos.y * map.width + s.player.pos.x;
  const goal = target.y * map.width + target.x;
  const q = [start];
  prev.set(start, -1);
  while (q.length) {
    const cur = q.shift()!;
    if (cur === goal) break;
    const cx = cur % map.width;
    const cy = Math.floor(cur / map.width);
    for (let d = 0; d < 8; d++) {
      const dx = [0, 1, 1, 1, 0, -1, -1, -1][d]!;
      const dy = [-1, -1, 0, 1, 1, 1, 0, -1][d]!;
      const nx = cx + dx;
      const ny = cy + dy;
      if (nx < 0 || ny < 0 || nx >= map.width || ny >= map.height) continue;
      if (tileAt(map, { x: nx, y: ny }).kind === "wall") continue;
      if (dx && dy && (tileAt(map, { x: nx, y: cy }).kind === "wall" || tileAt(map, { x: cx, y: ny }).kind === "wall")) continue;
      const n = ny * map.width + nx;
      if (prev.has(n)) continue;
      prev.set(n, cur);
      q.push(n);
    }
  }
  const path: number[] = [];
  for (let c = goal; c !== -1 && c !== undefined; c = prev.get(c)!) path.push(c);
  path.reverse();
  let state = s;
  for (let i = 1; i < path.length && !state.result; i++) {
    const from = path[i - 1]!;
    const to = path[i]!;
    const dx = (to % map.width) - (from % map.width);
    const dy = Math.floor(to / map.width) - Math.floor(from / map.width);
    const dir = [0, 1, 1, 1, 0, -1, -1, -1].findIndex((x, k) => x === dx && [-1, -1, 0, 1, 1, 1, 0, -1][k] === dy) as Dir;
    let guard = 0;
    // bump until we actually stand on `to`
    while (!(state.player.pos.y * map.width + state.player.pos.x === to) && !state.result && guard++ < 50) {
      state = step(state, { type: "move", dir }).state;
    }
  }
  return state;
}

describe("dungeon run", () => {
  it("createRun populates floor 1 with the defined enemies and items", () => {
    const s = createRun(5, YUKAI, ["potion20", "fire"]);
    expect(s.floorNo).toBe(1);
    const f1 = YUKAI.floors[0]!;
    expect(s.enemies.length).toBe(Object.values(f1.enemies).reduce((a, b) => a + b, 0));
    expect(s.items.filter((i) => i.type === "card").length).toBe(f1.cards);
    expect(s.items.filter((i) => i.type === "win").length).toBe(f1.wins);
    expect(s.player.hand).toEqual(["potion20", "fire"]);
    const entranceRoom = tileAt(s.map, s.map.entrance).roomId;
    for (const e of s.enemies) expect(tileAt(s.map, e.pos).roomId).not.toBe(entranceRoom);
  });

  it("is deterministic per seed", () => {
    const a = createRun(9, YUKAI, []);
    const b = createRun(9, YUKAI, []);
    expect(a).toEqual(b);
  });

  it("every floor is reachable and the last has an altar", () => {
    let s = createRun(3, YUKAI, []);
    // teleport-cheat: strip enemies so a walk cannot die; we only test floor plumbing
    for (let f = 1; f <= 7; f++) {
      s = { ...s, enemies: [], player: { ...s.player, hp: 999, maxHp: 999 } };
      const goal = s.map.stairs ?? s.map.altar!;
      expect(reachable(s.map, s.player.pos)[goal.y * s.map.width + goal.x]).toBe(true);
      s = walkTo(s, goal);
      expect(s.player.pos).toEqual(goal);
      if (f < 7) {
        s = step(s, { type: "descend" }).state;
        expect(s.floorNo).toBe(f + 1);
      } else {
        expect(s.map.altar).not.toBeNull();
        const r = step(s, { type: "takeAltar" });
        expect(r.state.result).toBe("clear");
        expect(r.events.find((e) => e.t === "cleared")).toMatchObject({ win: 90 + s.winCollected });
      }
    }
  });
});
