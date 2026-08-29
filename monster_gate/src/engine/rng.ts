// mulberry32 — small, fast, deterministic. State is a single uint32 so it can
// live inside DungeonState and be replayed.

export type RngState = number;

export function seedRng(seed: number): RngState {
  return seed >>> 0;
}

/** Advance the state and return [next state, float in [0,1)]. */
export function nextFloat(s: RngState): [RngState, number] {
  let t = (s + 0x6d2b79f5) >>> 0;
  const state = t;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return [state, ((t ^ (t >>> 14)) >>> 0) / 4294967296];
}

/** Mutable cursor over an RngState for code that draws many values in a row. */
export class Rng {
  constructor(public state: RngState) {}

  float(): number {
    const [s, v] = nextFloat(this.state);
    this.state = s;
    return v;
  }

  /** Integer in [lo, hi], both inclusive. */
  int(lo: number, hi: number): number {
    return lo + Math.floor(this.float() * (hi - lo + 1));
  }

  chance(p: number): boolean {
    return this.float() < p;
  }

  pick<T>(arr: readonly T[]): T {
    if (arr.length === 0) throw new Error("pick from empty array");
    return arr[this.int(0, arr.length - 1)]!;
  }

  /** Weighted pick; weights need not sum to 1. */
  weighted<T>(entries: readonly { item: T; weight: number }[]): T {
    const total = entries.reduce((a, e) => a + e.weight, 0);
    let r = this.float() * total;
    for (const e of entries) {
      r -= e.weight;
      if (r < 0) return e.item;
    }
    return entries[entries.length - 1]!.item;
  }

  shuffle<T>(arr: T[]): T[] {
    for (let i = arr.length - 1; i > 0; i--) {
      const j = this.int(0, i);
      [arr[i], arr[j]] = [arr[j]!, arr[i]!];
    }
    return arr;
  }
}
