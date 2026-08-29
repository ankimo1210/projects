import { add, DIRS, dist, idx, inBounds, isWalkable, tileAt, type Dir, type Enemy, type FloorMap, type Vec } from "./types";

/** Can a unit step from `from` one cell in `dir`? Walls block; no corner cutting. */
export function canStep(map: FloorMap, from: Vec, dir: Dir): boolean {
  const d = DIRS[dir]!;
  const to = add(from, d);
  if (!inBounds(map, to) || !isWalkable(tileAt(map, to).kind)) return false;
  if (d.x !== 0 && d.y !== 0) {
    const a = { x: from.x + d.x, y: from.y };
    const b = { x: from.x, y: from.y + d.y };
    if (!isWalkable(tileAt(map, a).kind) || !isWalkable(tileAt(map, b).kind)) return false;
  }
  return true;
}

export function dirTo(from: Vec, to: Vec): Dir | null {
  const dx = Math.sign(to.x - from.x);
  const dy = Math.sign(to.y - from.y);
  const i = DIRS.findIndex((d) => d.x === dx && d.y === dy);
  return i < 0 ? null : (i as Dir);
}

/** Cells strictly between from and to along an 8-direction line, or null if not aligned. */
export function lineBetween(from: Vec, to: Vec): Vec[] | null {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  if (!(dx === 0 || dy === 0 || Math.abs(dx) === Math.abs(dy))) return null;
  const n = dist(from, to);
  const sx = Math.sign(dx);
  const sy = Math.sign(dy);
  const out: Vec[] = [];
  for (let i = 1; i < n; i++) out.push({ x: from.x + sx * i, y: from.y + sy * i });
  return out;
}

export function enemyAt(enemies: readonly Enemy[], p: Vec): Enemy | undefined {
  return enemies.find((e) => e.pos.x === p.x && e.pos.y === p.y);
}

/** First enemy along `dir` within `range`, stopping at walls. */
export function firstEnemyInDir(map: FloorMap, enemies: readonly Enemy[], from: Vec, dir: Dir, range: number): Enemy | null {
  let cur = from;
  for (let i = 0; i < range; i++) {
    cur = add(cur, DIRS[dir]!);
    if (!inBounds(map, cur) || !isWalkable(tileAt(map, cur).kind)) return null;
    const e = enemyAt(enemies, cur);
    if (e) return e;
  }
  return null;
}

/** True if `to` is on a clear 8-direction line from `from` within `range`. */
export function hasLineOfFire(map: FloorMap, enemies: readonly Enemy[], from: Vec, to: Vec, range: number): boolean {
  const d = dist(from, to);
  if (d < 1 || d > range) return false;
  const between = lineBetween(from, to);
  if (!between) return false;
  for (const c of between) {
    if (!isWalkable(tileAt(map, c).kind)) return false;
    if (enemyAt(enemies, c)) return false;
  }
  return true;
}

export function tileIndex(map: FloorMap, p: Vec): number {
  return idx(map, p);
}

/** Where you end up after entering `start` heading `dir`: keep going while standing on ice. */
export function slideFrom(map: FloorMap, blocked: (v: Vec) => boolean, start: Vec, dir: Dir): Vec {
  let pos = start;
  for (let guard = 0; guard < 40; guard++) {
    if (tileAt(map, pos).kind !== "ice") break;
    if (!canStep(map, pos, dir)) break;
    const next = add(pos, DIRS[dir]!);
    if (blocked(next)) break;
    pos = next;
  }
  return pos;
}
