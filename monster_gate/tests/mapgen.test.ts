import { describe, expect, it } from "vitest";
import { generateFloor, reachable, YUKAI_MAP } from "../src/engine/mapgen";
import { idx, isWalkable, tileAt } from "../src/engine/types";

describe("mapgen", () => {
  it("produces connected maps with entrance and goal in different rooms for 1000 seeds", () => {
    for (let seed = 1; seed <= 1000; seed++) {
      const { map } = generateFloor(seed, YUKAI_MAP);
      const goal = map.stairs!;
      const reach = reachable(map, map.entrance);
      expect(reach[idx(map, goal)]).toBe(true);
      for (let i = 0; i < map.tiles.length; i++) {
        if (isWalkable(map.tiles[i]!.kind)) expect(reach[i]).toBe(true);
      }
      expect(tileAt(map, map.entrance).roomId).toBeGreaterThanOrEqual(0);
      expect(tileAt(map, goal).roomId).toBeGreaterThanOrEqual(0);
      expect(tileAt(map, map.entrance).roomId).not.toBe(tileAt(map, goal).roomId);
      expect(map.rooms.length).toBeGreaterThanOrEqual(2);
    }
  });

  it("rooms do not overlap and keep a wall ring inside their cell", () => {
    const { map } = generateFloor(42, YUKAI_MAP);
    for (const a of map.rooms) {
      for (const b of map.rooms) {
        if (a === b) continue;
        const overlap = a.x < b.x + b.w + 1 && b.x < a.x + a.w + 1 && a.y < b.y + b.h + 1 && b.y < a.y + a.h + 1;
        expect(overlap).toBe(false);
      }
    }
    // border is all wall
    for (let x = 0; x < map.width; x++) {
      expect(tileAt(map, { x, y: 0 }).kind).toBe("wall");
      expect(tileAt(map, { x, y: map.height - 1 }).kind).toBe("wall");
    }
  });

  it("is deterministic for a given seed", () => {
    const a = generateFloor(7, YUKAI_MAP);
    const b = generateFloor(7, YUKAI_MAP);
    expect(a.map).toEqual(b.map);
    expect(a.rng).toBe(b.rng);
  });

  it("places an altar instead of stairs on the final floor", () => {
    const { map } = generateFloor(3, { ...YUKAI_MAP, final: true });
    expect(map.stairs).toBeNull();
    expect(map.altar).not.toBeNull();
    expect(tileAt(map, map.altar!).kind).toBe("altar");
  });
});
