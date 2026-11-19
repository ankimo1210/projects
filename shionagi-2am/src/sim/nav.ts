// Grid navigation: colliders are rasterised (grown by the agent radius) onto a
// 0.25 m grid; A* runs on it with 8 neighbours and no corner cutting, and the
// result is string-pulled into a short list of waypoints.

import type { Box, Rect } from "./geom";

export interface Pt {
  x: number;
  z: number;
}

const SQRT2 = Math.SQRT2;

export class NavGrid {
  readonly cell: number;
  readonly w: number;
  readonly h: number;
  readonly ox: number;
  readonly oz: number;
  blocked: Uint8Array;

  private g: Float32Array;
  private f: Float32Array;
  private from: Int32Array;
  private seen: Uint32Array;
  private done: Uint32Array;
  private gen = 0;
  private heap: number[] = [];

  constructor(bounds: Rect, cell = 0.25) {
    this.cell = cell;
    this.ox = bounds.x0;
    this.oz = bounds.z0;
    this.w = Math.ceil((bounds.x1 - bounds.x0) / cell);
    this.h = Math.ceil((bounds.z1 - bounds.z0) / cell);
    const n = this.w * this.h;
    this.blocked = new Uint8Array(n);
    this.g = new Float32Array(n);
    this.f = new Float32Array(n);
    this.from = new Int32Array(n);
    this.seen = new Uint32Array(n);
    this.done = new Uint32Array(n);
  }

  rebuild(boxes: readonly Box[], radius: number): void {
    const { w, h, cell, ox, oz, blocked } = this;
    blocked.fill(0);
    for (const b of boxes) {
      if (!b.on || !b.solid) continue;
      // cells whose centre lies inside the grown rectangle
      const i0 = Math.max(0, Math.ceil((b.x0 - radius - ox) / cell - 0.5));
      const i1 = Math.min(w - 1, Math.floor((b.x1 + radius - ox) / cell - 0.5));
      const j0 = Math.max(0, Math.ceil((b.z0 - radius - oz) / cell - 0.5));
      const j1 = Math.min(h - 1, Math.floor((b.z1 + radius - oz) / cell - 0.5));
      for (let j = j0; j <= j1; j++) {
        const row = j * w;
        for (let i = i0; i <= i1; i++) blocked[row + i] = 1;
      }
    }
    // closed border so a leak can never run off the grid
    for (let i = 0; i < w; i++) {
      blocked[i] = 1;
      blocked[(h - 1) * w + i] = 1;
    }
    for (let j = 0; j < h; j++) {
      blocked[j * w] = 1;
      blocked[j * w + w - 1] = 1;
    }
  }

  index(x: number, z: number): number {
    const i = Math.floor((x - this.ox) / this.cell);
    const j = Math.floor((z - this.oz) / this.cell);
    if (i < 0 || j < 0 || i >= this.w || j >= this.h) return -1;
    return j * this.w + i;
  }

  cx(idx: number): number {
    return this.ox + ((idx % this.w) + 0.5) * this.cell;
  }

  cz(idx: number): number {
    return this.oz + (Math.floor(idx / this.w) + 0.5) * this.cell;
  }

  isFree(x: number, z: number): boolean {
    const i = this.index(x, z);
    return i >= 0 && this.blocked[i] === 0;
  }

  /** Nearest free cell to a point (spiral search), or -1. */
  nearestFree(x: number, z: number, maxCells = 12): number {
    const i0 = Math.floor((x - this.ox) / this.cell);
    const j0 = Math.floor((z - this.oz) / this.cell);
    let best = -1;
    let bestD = Infinity;
    for (let r = 0; r <= maxCells; r++) {
      for (let dj = -r; dj <= r; dj++) {
        for (let di = -r; di <= r; di++) {
          if (Math.max(Math.abs(di), Math.abs(dj)) !== r) continue;
          const i = i0 + di;
          const j = j0 + dj;
          if (i < 0 || j < 0 || i >= this.w || j >= this.h) continue;
          const idx = j * this.w + i;
          if (this.blocked[idx]) continue;
          const dx = this.cx(idx) - x;
          const dz = this.cz(idx) - z;
          const d = dx * dx + dz * dz;
          if (d < bestD) {
            bestD = d;
            best = idx;
          }
        }
      }
      if (best >= 0) return best;
    }
    return best;
  }

  /** True when the straight segment stays on free cells (and under `limit` extra cost). */
  lineFree(ax: number, az: number, bx: number, bz: number, extra?: Float32Array | null, limit = 0): boolean {
    const dx = bx - ax;
    const dz = bz - az;
    const len = Math.hypot(dx, dz);
    const n = Math.max(1, Math.ceil(len / (this.cell * 0.5)));
    for (let k = 0; k <= n; k++) {
      const t = k / n;
      const idx = this.index(ax + dx * t, az + dz * t);
      if (idx < 0 || this.blocked[idx]) return false;
      if (extra && (extra[idx] as number) > limit) return false;
    }
    return true;
  }

  private push(idx: number): void {
    const heap = this.heap;
    const f = this.f;
    let i = heap.length;
    heap.push(idx);
    while (i > 0) {
      const parent = (i - 1) >> 1;
      const pv = heap[parent] as number;
      if ((f[pv] as number) <= (f[idx] as number)) break;
      heap[i] = pv;
      i = parent;
    }
    heap[i] = idx;
  }

  private pop(): number {
    const heap = this.heap;
    const f = this.f;
    const top = heap[0] as number;
    const last = heap.pop() as number;
    const n = heap.length;
    if (n > 0) {
      let i = 0;
      for (;;) {
        let c = i * 2 + 1;
        if (c >= n) break;
        if (c + 1 < n && (f[heap[c + 1] as number] as number) < (f[heap[c] as number] as number)) c++;
        const cv = heap[c] as number;
        if ((f[cv] as number) >= (f[last] as number)) break;
        heap[i] = cv;
        i = c;
      }
      heap[i] = last;
    }
    return top;
  }

  /**
   * A* from (sx, sz) to (gx, gz). `extra` adds a per-cell cost (multiplied by
   * the step length) so callers can steer paths away from danger.
   * Returns waypoints excluding the start, or null when there is no route.
   */
  findPath(
    sx: number,
    sz: number,
    gx: number,
    gz: number,
    extra: Float32Array | null = null,
    maxExpand = 80000,
  ): Pt[] | null {
    const { w, blocked, g, f, from, seen, done } = this;
    let start = this.index(sx, sz);
    if (start < 0 || blocked[start]) start = this.nearestFree(sx, sz);
    let goal = this.index(gx, gz);
    let goalMoved = false;
    if (goal < 0 || blocked[goal]) {
      goal = this.nearestFree(gx, gz);
      goalMoved = true;
    }
    if (start < 0 || goal < 0) return null;
    const gen = ++this.gen;
    const gi = goal % w;
    const gj = Math.floor(goal / w);
    const heur = (idx: number): number => {
      const di = Math.abs((idx % w) - gi);
      const dj = Math.abs(Math.floor(idx / w) - gj);
      return (Math.max(di, dj) + (SQRT2 - 1) * Math.min(di, dj)) * 1.001;
    };
    this.heap.length = 0;
    g[start] = 0;
    f[start] = heur(start);
    from[start] = -1;
    seen[start] = gen;
    this.push(start);
    let expanded = 0;
    let found = false;
    while (this.heap.length > 0) {
      const cur = this.pop();
      if (done[cur] === gen) continue;
      done[cur] = gen;
      if (cur === goal) {
        found = true;
        break;
      }
      if (++expanded > maxExpand) break;
      const gc = g[cur] as number;
      for (let dj = -1; dj <= 1; dj++) {
        for (let di = -1; di <= 1; di++) {
          if (di === 0 && dj === 0) continue;
          const nb = cur + di + dj * w;
          if (blocked[nb] || done[nb] === gen) continue;
          let cost = 1;
          if (di !== 0 && dj !== 0) {
            if (blocked[cur + di] || blocked[cur + dj * w]) continue;
            cost = SQRT2;
          }
          if (extra) cost *= 1 + (extra[nb] as number);
          const ng = gc + cost;
          if (seen[nb] !== gen || ng < (g[nb] as number)) {
            seen[nb] = gen;
            g[nb] = ng;
            f[nb] = ng + heur(nb);
            from[nb] = cur;
            this.push(nb);
          }
        }
      }
    }
    if (!found) return null;
    // reconstruct (goal -> start), then reverse
    const cells: number[] = [];
    for (let c = goal; c !== -1; c = from[c] as number) cells.push(c);
    cells.reverse();
    const pts: Pt[] = cells.map((c) => ({ x: this.cx(c), z: this.cz(c) }));
    (pts[0] as Pt).x = sx;
    (pts[0] as Pt).z = sz;
    if (!goalMoved) {
      const lastPt = pts[pts.length - 1] as Pt;
      lastPt.x = gx;
      lastPt.z = gz;
    }
    // string pulling
    const out: Pt[] = [];
    let i = 0;
    const n = pts.length;
    const window = extra ? 10 : 80;
    while (i < n - 1) {
      let j = Math.min(n - 1, i + window);
      const a = pts[i] as Pt;
      while (j > i + 1) {
        const b = pts[j] as Pt;
        if (this.lineFree(a.x, a.z, b.x, b.z, extra, 0.35)) break;
        j--;
      }
      out.push(pts[j] as Pt);
      i = j;
    }
    if (out.length === 0) out.push(pts[n - 1] as Pt);
    return out;
  }

  /** Flood fill from a point; returns a mask of reachable cells. */
  flood(sx: number, sz: number): Uint8Array {
    const { w, blocked } = this;
    const mask = new Uint8Array(blocked.length);
    let start = this.index(sx, sz);
    if (start < 0 || blocked[start]) start = this.nearestFree(sx, sz);
    if (start < 0) return mask;
    const stack = [start];
    mask[start] = 1;
    while (stack.length > 0) {
      const cur = stack.pop() as number;
      for (let dj = -1; dj <= 1; dj++) {
        for (let di = -1; di <= 1; di++) {
          if (di === 0 && dj === 0) continue;
          const nb = cur + di + dj * w;
          if (blocked[nb] || mask[nb]) continue;
          if (di !== 0 && dj !== 0 && (blocked[cur + di] || blocked[cur + dj * w])) continue;
          mask[nb] = 1;
          stack.push(nb);
        }
      }
    }
    return mask;
  }
}
