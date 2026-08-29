import { describe, expect, it } from "vitest";
import { visibleSet } from "../src/engine/fov";
import { generateFloor, YUKAI_MAP } from "../src/engine/mapgen";
import { idx, tileAt } from "../src/engine/types";

describe("fov", () => {
  const { map } = generateFloor(11, YUKAI_MAP);

  it("sees the whole room from inside it", () => {
    const room = map.rooms[tileAt(map, map.entrance).roomId]!;
    const vis = visibleSet(map, map.entrance, false);
    for (let y = room.y; y < room.y + room.h; y++) {
      for (let x = room.x; x < room.x + room.w; x++) expect(vis[idx(map, { x, y })]).toBe(true);
    }
  });

  it("sees only the 8 neighbours in a corridor", () => {
    let corridor = null;
    for (let y = 0; y < map.height && !corridor; y++) {
      for (let x = 0; x < map.width; x++) {
        const t = tileAt(map, { x, y });
        if (t.kind === "floor" && t.roomId < 0) {
          corridor = { x, y };
          break;
        }
      }
    }
    expect(corridor).not.toBeNull();
    const vis = visibleSet(map, corridor!, false);
    const count = vis.filter(Boolean).length;
    expect(count).toBeLessThanOrEqual(9);
    expect(vis[idx(map, corridor!)]).toBe(true);
  });

  it("sees everything when bright", () => {
    const vis = visibleSet(map, map.entrance, true);
    expect(vis.every(Boolean)).toBe(true);
  });
});
