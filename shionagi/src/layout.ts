export type Point = { x: number; z: number };
export type Point3D = Point & { y: number };
export type Rect = { x1: number; x2: number; z1: number; z2: number };
export type Solid = Rect & { id: string; height: number };

const rect = (x1: number, x2: number, z1: number, z2: number): Rect => ({ x1, x2, z1, z2 });
const solid = (id: string, x1: number, x2: number, z1: number, z2: number, height: number): Solid =>
  ({ id, x1, x2, z1, z2, height });

export const PLAYER_START: Point = { x: -2, z: 5.8 };
export const RADIO: Point = { x: 5, z: -1 };
export const DOOR: Point = { x: 4, z: -31 };
export const PISTOL: Point = { x: 6, z: -54 };
export const PANEL: Point = { x: 39, z: -229 };
export const STATION: Point = { x: 28, z: -297 };

export const BRIDGE = rect(33, 39, -250, -234);
export const REAR_DOOR = solid('rear-door', 2, 6, -31.3, -30.7, 3.2);
// Static paving. The movable deck joins these surfaces only at the end of its travel.
export const WALKABLE: Rect[] = [
  rect(-9, 8, -31, 10),
  rect(2, 6, -43, -30.5),
  rect(-10, 9, -164, -42),
  rect(22, 28, -164, -42),
  rect(8, 23, -58, -50),
  rect(8, 23, -107, -100),
  rect(8, 23, -157, -149),
  rect(-8, 10, -176, -156),
  rect(3, 42, -181, -168),
  rect(30, 43, -234, -174),
  rect(26, 46, -259, -249),
  rect(10, 51, -301, -250),
];

export const SOLIDS: Solid[] = [
  solid('terminal-bench-a', -6.5, -3.4, 0.9, 1.9, 0.9),
  solid('terminal-bench-b', -6.5, -3.4, -6.7, -5.7, 0.9),
  solid('terminal-pier-a', .42, .98, -8.83, -8.27, 4.6),
  solid('terminal-pier-b', .42, .98, -24.08, -23.52, 4.6),
  solid('station-vestibule', 24.5, 31.5, -301, -297.65, 3.55),
  solid('station-facade', 10, 51, -301, -299.98, 8),
  solid('terminal-counter', -8.5, -5.8, -22, -13, 1.65),
  solid('radio-cabinet', 5.2, 7.6, -2.2, -0.3, 1.05),
  solid('pistol-crate', 6.4, 8.2, -55, -53, 0.85),
  solid('street-van', -6.8, -4.3, -79, -74, 2.15),
  solid('street-stall', 2.8, 6.4, -99, -95.4, 2.35),
  solid('alley-crates', 25, 27.4, -86, -82, 1.8),
  solid('street-kiosk', -9, -6.5, -122, -119, 2.15),
  solid('street-pallet', -3, 0.2, -137, -133, 1.85),
  solid('quay-east-container', 37.2, 41.4, -202, -193, 2.75),
  solid('quay-west-container', 32, 35.8, -216, -205, 2.75),
  solid('quay-pump', 32, 35.8, -232, -225.3, 2.25),
  solid('panel-cabinet', 40, 42.4, -230, -228, 1.5),
  solid('court-booth', 17, 21.5, -281, -273, 2.45),
  solid('court-van', 34, 38.7, -289, -283.5, 1.7),
];

function contains(r: Rect, x: number, z: number, margin = 0): boolean {
  return x >= r.x1 + margin && x <= r.x2 - margin && z >= r.z1 + margin && z <= r.z2 - margin;
}

function intersects(r: Rect, x: number, z: number, radius: number): boolean {
  const dx = Math.max(r.x1 - x, 0, x - r.x2);
  const dz = Math.max(r.z1 - z, 0, z - r.z2);
  return dx * dx + dz * dz <= radius * radius;
}

const diagonal = Math.SQRT1_2;
const circle = [[1, 0], [-1, 0], [0, 1], [0, -1], [diagonal, diagonal], [diagonal, -diagonal],
  [-diagonal, diagonal], [-diagonal, -diagonal]];

function onFloor(x: number, z: number, bridgeOpen: boolean, radius: number): boolean {
  const hasSurface = (px: number, pz: number, margin: number) =>
    (bridgeOpen && contains(BRIDGE, px, pz, margin)) || WALKABLE.some(r => contains(r, px, pz, margin));
  if (hasSurface(x, z, radius)) return true;
  if (!radius || !hasSurface(x, z, 0)) return false;
  // A footprint may straddle the seam between two adjoining pieces of pavement.
  return circle.every(([dx, dz]) => hasSurface(x + dx * radius, z + dz * radius, 0));
}

export function isWall(x: number, z: number, height = 1.55, bridgeOpen = false, doorOpen = false, radius = 0): boolean {
  if (!onFloor(x, z, bridgeOpen, radius)) return true;
  if (!doorOpen && height <= REAR_DOOR.height && intersects(REAR_DOOR, x, z, radius)) return true;
  return SOLIDS.some(obstacle => height <= obstacle.height && intersects(obstacle, x, z, radius));
}

export function canStand(x: number, z: number, bridgeOpen = false, doorOpen = false, radius = 0.34): boolean {
  return !isWall(x, z, 0.3, bridgeOpen, doorOpen, radius);
}

function clearSegment(a: Point, b: Point, height: number, bridgeOpen: boolean, doorOpen: boolean,
  radius: number, endHeight = height): boolean {
  const dx = b.x - a.x, dz = b.z - a.z;
  const dh = endHeight - height;
  const count = Math.max(1, Math.ceil(Math.max(Math.hypot(dx, dz), Math.abs(dh)) / 0.36));
  for (let i = 1; i <= count; i++) {
    const t = i / count;
    if (isWall(a.x + dx * t, a.z + dz * t, height + dh * t, bridgeOpen, doorOpen, radius)) return false;
  }
  return true;
}

export function hasSightLine(a: Point, b: Point, bridgeOpen: boolean, doorOpen: boolean): boolean {
  return clearSegment(a, b, 1.45, bridgeOpen, doorOpen, 0);
}

export function hasShotLine(a: Point3D, b: Point3D, bridgeOpen: boolean, doorOpen: boolean): boolean {
  return clearSegment(a, b, a.y, bridgeOpen, doorOpen, 0, b.y);
}

const gridLeft = -10, gridRight = 51, gridNorth = -301, gridSouth = 10;
const gridWidth = gridRight - gridLeft + 1, gridSize = gridWidth * (gridSouth - gridNorth + 1);
const navRadius = 0.42;
const neighborSteps = [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, 1], [1, -1], [-1, -1]];
const grids: Int8Array[] = [];

function gridId(x: number, z: number): number {
  return (z - gridNorth) * gridWidth + x - gridLeft;
}

function gridPoint(id: number): Point {
  return { x: gridLeft + id % gridWidth, z: gridNorth + Math.floor(id / gridWidth) };
}

// Most navigation is a straight walk. Search the collision grid only when cover interrupts it.
export function findRoute(start: Point, end: Point, bridgeOpen: boolean, doorOpen: boolean): Point[] {
  const visiblePath = (a: Point, b: Point) => clearSegment(a, b, 0.3, bridgeOpen, doorOpen, navRadius);
  if (visiblePath(start, end)) return [{ x: end.x, z: end.z }];
  const variant = Number(bridgeOpen) * 2 + Number(doorOpen);
  const grid = grids[variant] ??= new Int8Array(gridSize);
  const passable = (x: number, z: number): boolean => {
    if (x < gridLeft || x > gridRight || z < gridNorth || z > gridSouth) return false;
    const id = gridId(x, z);
    if (!grid[id]) grid[id] = canStand(x, z, bridgeOpen, doorOpen, navRadius) ? 1 : -1;
    return grid[id] === 1;
  };
  const nearest = (p: Point): number => {
    let best = -1, bestDistance = Infinity;
    for (let x = Math.round(p.x) - 2; x <= Math.round(p.x) + 2; x++) {
      for (let z = Math.round(p.z) - 2; z <= Math.round(p.z) + 2; z++) {
        const distance = (x - p.x) ** 2 + (z - p.z) ** 2;
        if (distance < bestDistance && passable(x, z) && visiblePath(p, { x, z })) {
          best = gridId(x, z);
          bestDistance = distance;
        }
      }
    }
    return best;
  };
  const first = nearest(start), last = nearest(end);
  if (first < 0 || last < 0) return [];
  const parents = new Int32Array(gridSize).fill(-1);
  const queue = [first];
  parents[first] = first;
  for (let head = 0; head < queue.length && parents[last] < 0; head++) {
    const id = queue[head];
    const p = gridPoint(id);
    for (const [dx, dz] of neighborSteps) {
      const x = p.x + dx, z = p.z + dz;
      if (!passable(x, z)) continue;
      const next = gridId(x, z);
      if (parents[next] >= 0) continue;
      if (dx && dz && (!passable(x, p.z) || !passable(p.x, z))) continue;
      parents[next] = id;
      queue.push(next);
    }
  }
  if (parents[last] < 0) return [];
  const path: Point[] = [{ x: end.x, z: end.z }];
  for (let id = last; id !== first; id = parents[id]) path.push(gridPoint(id));
  path.push(gridPoint(first));
  path.reverse();
  const corners: Point[] = [];
  let anchor = start;
  for (let i = 1; i < path.length; i++) {
    if (!visiblePath(anchor, path[i])) {
      anchor = path[i - 1];
      corners.push(anchor);
    }
  }
  corners.push(path[path.length - 1]);
  return corners;
}
