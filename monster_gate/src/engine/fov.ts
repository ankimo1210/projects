// Visibility: inside a lit room you see the whole room plus its doors; in a
// corridor only the 8 neighbours; `bright` reveals the whole floor.

import { idx, inBounds, tileAt, type FloorMap, type Vec } from "./types";

export function visibleSet(map: FloorMap, from: Vec, bright: boolean, corridorRadius = 1): boolean[] {
  const vis = new Array<boolean>(map.tiles.length).fill(false);
  if (bright) {
    vis.fill(true);
    return vis;
  }
  const here = tileAt(map, from);
  const r = here.roomId >= 0 ? 1 : corridorRadius;
  if (here.roomId >= 0) {
    const room = map.rooms[here.roomId]!;
    for (let y = room.y - 1; y <= room.y + room.h; y++) {
      for (let x = room.x - 1; x <= room.x + room.w; x++) {
        const v = { x, y };
        if (!inBounds(map, v)) continue;
        const t = tileAt(map, v);
        const inside = x >= room.x && x < room.x + room.w && y >= room.y && y < room.y + room.h;
        if (inside || t.kind === "door") vis[idx(map, v)] = true;
      }
    }
  }
  for (let dy = -r; dy <= r; dy++) {
    for (let dx = -r; dx <= r; dx++) {
      const v = { x: from.x + dx, y: from.y + dy };
      if (inBounds(map, v)) vis[idx(map, v)] = true;
    }
  }
  return vis;
}

export function canSee(map: FloorMap, from: Vec, target: Vec, bright: boolean, corridorRadius = 1): boolean {
  return visibleSet(map, from, bright, corridorRadius)[idx(map, target)] === true;
}
