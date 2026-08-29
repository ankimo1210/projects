// Room-grid generator: cols×rows cells, each holding a room (or a 1×1
// junction), joined by a random spanning tree plus a few extra links.
// Corridors are L-shaped and unlit; rooms are lit.

import { canStep, slideFrom } from "./geometry";
import { Rng, type RngState } from "./rng";
import { add, DIRS, idx, inBounds, isWalkable, tileAt, vecEq, type Dir, type FloorMap, type Room, type Tile, type Vec } from "./types";

export type MapGenParams = {
  cols: number;
  rows: number;
  cellW: number;
  cellH: number;
  roomMinW: number;
  roomMaxW: number;
  roomMinH: number;
  roomMaxH: number;
  roomChance: number;
  extraLinks: number;
  final: boolean; // altar instead of stairs
  ice?: number; // number of ice patches
  shop?: boolean;
  casino?: boolean;
};

export const YUKAI_MAP: MapGenParams = {
  cols: 3,
  rows: 3,
  cellW: 14,
  cellH: 10,
  roomMinW: 4,
  roomMaxW: 9,
  roomMinH: 3,
  roomMaxH: 6,
  roomChance: 0.85,
  extraLinks: 2,
  final: false,
};

type Cell = { cx: number; cy: number; room: Room; isJunction: boolean };
type Edge = [Cell, Cell]; // always left→right or top→bottom

const MAX_ATTEMPTS = 20;

export function generateFloor(seed: number, params: MapGenParams): { map: FloorMap; rng: RngState } {
  for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
    const rng = new Rng((seed + attempt) >>> 0);
    const map = tryGenerate(rng, params);
    if (map && validate(map)) return { map, rng: rng.state };
  }
  throw new Error(`mapgen: no valid map for seed ${seed} after ${MAX_ATTEMPTS} attempts`);
}

function tryGenerate(rng: Rng, p: MapGenParams): FloorMap | null {
  const width = p.cols * p.cellW + 1;
  const height = p.rows * p.cellH + 1;
  const tiles: Tile[] = Array.from({ length: width * height }, () => ({ kind: "wall", roomId: -1, lit: false }));
  const map: FloorMap = { width, height, tiles, rooms: [], entrance: { x: 0, y: 0 }, stairs: null, altar: null, shop: null, casino: null };

  // 1. place rooms / junctions
  const cells: Cell[] = [];
  let roomId = 0;
  for (let cy = 0; cy < p.rows; cy++) {
    for (let cx = 0; cx < p.cols; cx++) {
      const isJunction = !rng.chance(p.roomChance);
      const w = isJunction ? 1 : rng.int(p.roomMinW, Math.min(p.roomMaxW, p.cellW - 4));
      const h = isJunction ? 1 : rng.int(p.roomMinH, Math.min(p.roomMaxH, p.cellH - 4));
      // 1 wall cell on the top/left, 2 on the bottom/right: corridors between
      // neighbouring cells always have a free column/row to turn in.
      const x0 = cx * p.cellW + 1 + rng.int(0, p.cellW - 3 - w);
      const y0 = cy * p.cellH + 1 + rng.int(0, p.cellH - 3 - h);
      const room: Room = { id: isJunction ? -1 : roomId, x: x0, y: y0, w, h };
      if (!isJunction) {
        roomId++;
        map.rooms.push(room);
      }
      cells.push({ cx, cy, room, isJunction });
      for (let y = y0; y < y0 + h; y++) {
        for (let x = x0; x < x0 + w; x++) {
          tiles[y * width + x] = { kind: "floor", roomId: room.id, lit: !isJunction };
        }
      }
    }
  }
  if (map.rooms.length < 2) return null;

  // 2. spanning tree over the grid (random Kruskal) + extra links
  const cellAt = (cx: number, cy: number) => cells[cy * p.cols + cx]!;
  const edges: Edge[] = [];
  for (const c of cells) {
    if (c.cx + 1 < p.cols) edges.push([c, cellAt(c.cx + 1, c.cy)]);
    if (c.cy + 1 < p.rows) edges.push([c, cellAt(c.cx, c.cy + 1)]);
  }
  rng.shuffle(edges);
  const parent = new Map<Cell, Cell>();
  const find = (c: Cell): Cell => {
    let r = c;
    while (parent.get(r) && parent.get(r) !== r) r = parent.get(r)!;
    return r;
  };
  for (const c of cells) parent.set(c, c);
  const chosen: Edge[] = [];
  const rest: Edge[] = [];
  for (const e of edges) {
    const a = find(e[0]);
    const b = find(e[1]);
    if (a !== b) {
      parent.set(a, b);
      chosen.push(e);
    } else rest.push(e);
  }
  for (let i = 0; i < p.extraLinks && rest.length > 0; i++) chosen.push(rest.pop()!);

  // 3. dig door-to-door corridors through the gap between the two cells
  for (const [a, b] of chosen) digCorridor(map, a, b, rng);

  // 4. entrance and stairs/altar in different rooms
  const rooms = rng.shuffle([...map.rooms]);
  const entranceRoom = rooms[0]!;
  const goalRoom = rooms[1]!;
  map.entrance = randomInRoom(rng, entranceRoom);
  const goal = randomInRoom(rng, goalRoom);
  tiles[idx(map, goal)] = { kind: p.final ? "altar" : "stairsDown", roomId: goalRoom.id, lit: true };
  if (p.final) map.altar = goal;
  else map.stairs = goal;

  // 5. features. Order matters: ice must not bury the goal, shop or casino.
  const avoid: Vec[] = [map.entrance, goal];
  if (p.shop) {
    map.shop = placeFeature(map, rng, "shop", avoid);
    if (map.shop) avoid.push(map.shop);
  }
  if (p.casino) {
    map.casino = placeFeature(map, rng, "casino", avoid);
    if (map.casino) avoid.push(map.casino);
  }
  if (p.ice) placeIce(map, rng, p.ice, avoid);
  return map;
}

function placeFeature(map: FloorMap, rng: Rng, kind: "shop" | "casino", avoid: readonly Vec[]): Vec | null {
  const cells = floorCells(map, (t, v) => t.kind === "floor" && t.roomId >= 0 && !avoid.some((a) => vecEq(a, v)));
  if (cells.length === 0) return null;
  const v = rng.pick(cells);
  map.tiles[idx(map, v)] = { kind, roomId: tileAt(map, v).roomId, lit: true };
  return v;
}

/**
 * Rectangular ice patches inside rooms. Only the player slides on them.
 * A patch never fills its room: one column and one row stay solid so there is
 * always somewhere to come to rest, and each room gets at most one patch.
 */
function placeIce(map: FloorMap, rng: Rng, patches: number, avoid: readonly Vec[]): void {
  const rooms = rng.shuffle([...map.rooms]);
  for (let i = 0; i < patches && i < rooms.length; i++) {
    const room = rooms[i]!;
    const w = Math.min(room.w - 1, rng.int(2, 4));
    const h = Math.min(room.h - 1, rng.int(2, 3));
    if (w < 2 || h < 2) continue;
    const x0 = rng.int(room.x, room.x + room.w - w);
    const y0 = rng.int(room.y, room.y + room.h - h);
    for (let y = y0; y < y0 + h; y++) {
      for (let x = x0; x < x0 + w; x++) {
        const v = { x, y };
        if (avoid.some((a) => vecEq(a, v))) continue;
        const t = map.tiles[idx(map, v)]!;
        if (t.kind !== "floor") continue;
        map.tiles[idx(map, v)] = { ...t, kind: "ice" };
      }
    }
  }
}

function randomInRoom(rng: Rng, r: Room): Vec {
  return { x: rng.int(r.x, r.x + r.w - 1), y: rng.int(r.y, r.y + r.h - 1) };
}

/**
 * Connect two horizontally or vertically adjacent cells. Each end is a door on
 * the facing wall (or the junction tile itself); the corridor runs straight
 * out, turns once in the gap between the rooms, and runs straight in.
 */
function digCorridor(map: FloorMap, a: Cell, b: Cell, rng: Rng): void {
  const horizontal = a.cy === b.cy;
  const ra = a.room;
  const rb = b.room;
  let doorA: Vec;
  let doorB: Vec;
  if (horizontal) {
    doorA = a.isJunction ? { x: ra.x, y: ra.y } : { x: ra.x + ra.w, y: rng.int(ra.y, ra.y + ra.h - 1) };
    doorB = b.isJunction ? { x: rb.x, y: rb.y } : { x: rb.x - 1, y: rng.int(rb.y, rb.y + rb.h - 1) };
  } else {
    doorA = a.isJunction ? { x: ra.x, y: ra.y } : { x: rng.int(ra.x, ra.x + ra.w - 1), y: ra.y + ra.h };
    doorB = b.isJunction ? { x: rb.x, y: rb.y } : { x: rng.int(rb.x, rb.x + rb.w - 1), y: rb.y - 1 };
  }
  const path: Vec[] = [];
  if (horizontal) {
    const xm = rng.int(doorA.x + 1, doorB.x - 1);
    for (let x = doorA.x + 1; x <= xm; x++) path.push({ x, y: doorA.y });
    const sy = Math.sign(doorB.y - doorA.y);
    for (let y = doorA.y; y !== doorB.y; y += sy) path.push({ x: xm, y: y + sy });
    for (let x = xm; x < doorB.x; x++) path.push({ x: x + 1, y: doorB.y });
  } else {
    const ym = rng.int(doorA.y + 1, doorB.y - 1);
    for (let y = doorA.y + 1; y <= ym; y++) path.push({ x: doorA.x, y });
    const sx = Math.sign(doorB.x - doorA.x);
    for (let x = doorA.x; x !== doorB.x; x += sx) path.push({ x: x + sx, y: ym });
    for (let y = ym; y < doorB.y; y++) path.push({ x: doorB.x, y: y + 1 });
  }
  const dig = (v: Vec, kind: "door" | "floor") => {
    const i = idx(map, v);
    if (map.tiles[i]!.kind === "wall") map.tiles[i] = { kind, roomId: -1, lit: false };
  };
  dig(doorA, a.isJunction ? "floor" : "door");
  dig(doorB, b.isJunction ? "floor" : "door");
  for (const v of path) dig(v, "floor");
}

/** Every walkable tile reachable from the entrance, and goal exists. */
export function validate(map: FloorMap): boolean {
  const goal = map.stairs ?? map.altar;
  if (!goal) return false;
  const reach = reachable(map, map.entrance);
  for (let i = 0; i < map.tiles.length; i++) {
    if (isWalkable(map.tiles[i]!.kind) && !reach[i]) return false;
  }
  return true;
}

export function reachable(map: FloorMap, from: Vec): boolean[] {
  const seen = new Array<boolean>(map.tiles.length).fill(false);
  const q: Vec[] = [from];
  seen[idx(map, from)] = true;
  while (q.length) {
    const v = q.shift()!;
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue;
        const n = { x: v.x + dx, y: v.y + dy };
        if (!inBounds(map, n)) continue;
        const i = idx(map, n);
        if (seen[i] || !isWalkable(map.tiles[i]!.kind)) continue;
        // no corner cutting, same rule as movement
        if (dx && dy) {
          const a = map.tiles[idx(map, { x: v.x + dx, y: v.y })]!;
          const b = map.tiles[idx(map, { x: v.x, y: v.y + dy })]!;
          if (!isWalkable(a.kind) || !isWalkable(b.kind)) continue;
        }
        seen[i] = true;
        q.push(n);
      }
    }
  }
  return seen;
}

/**
 * Cells you can actually come to rest on, honouring ice slides. Ice can leave a
 * few cells you only ever skate over; nothing important may be placed there.
 */
export function restingCells(map: FloorMap, from: Vec): boolean[] {
  const out = new Array<boolean>(map.tiles.length).fill(false);
  out[idx(map, from)] = true;
  const q: Vec[] = [from];
  while (q.length) {
    const v = q.shift()!;
    for (let d = 0; d < 8; d++) {
      const dir = d as Dir;
      if (!canStep(map, v, dir)) continue;
      const end = slideFrom(map, () => false, add(v, DIRS[dir]!), dir);
      const i = idx(map, end);
      if (out[i]) continue;
      out[i] = true;
      q.push(end);
    }
  }
  return out;
}

/** Walkable tiles not in any room (corridor cells), for warp/spawn helpers. */
export function floorCells(map: FloorMap, filter?: (t: Tile, v: Vec) => boolean): Vec[] {
  const out: Vec[] = [];
  for (let y = 0; y < map.height; y++) {
    for (let x = 0; x < map.width; x++) {
      const t = map.tiles[y * map.width + x]!;
      if (!isWalkable(t.kind)) continue;
      const v = { x, y };
      if (!filter || filter(t, v)) out.push(v);
    }
  }
  return out;
}
