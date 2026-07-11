// Shared tick engine + perf meter for the live-board comparison.
// Framework-agnostic and DOM-free: every board (React/Vue/Angular/Solid)
// receives the exact same update stream; only the reactive wiring differs.

/** One instrument on the board. */
export interface Quote {
  symbol: string;
  last: number;
  bid: number;
  ask: number;
  changePct: number; // vs session open
  dir: 1 | -1 | 0; // direction of the most recent change
}

/** One field-level update emitted by the engine. */
export interface QuoteUpdate {
  index: number;
  last: number;
  bid: number;
  ask: number;
  changePct: number;
  dir: 1 | -1;
}

/** Deterministic PRNG (mulberry32) so every framework sees the same stream. */
export function createRng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const round2 = (x: number) => Math.round(x * 100) / 100;

/** AAAA, AAAB, ... base-26 ticker names. */
function symbolFor(i: number): string {
  let s = '';
  let n = i;
  for (let k = 0; k < 4; k++) {
    s = String.fromCharCode(65 + (n % 26)) + s;
    n = Math.floor(n / 26);
  }
  return s;
}

/** Generate n quotes with seeded pseudo-random opening prices. */
export function createBook(n: number, seed = 7): Quote[] {
  const rng = createRng(seed);
  const book: Quote[] = [];
  for (let i = 0; i < n; i++) {
    const last = round2(10 + rng() * 490);
    const spread = Math.max(0.01, round2(last * 0.0004));
    book.push({
      symbol: symbolFor(i),
      last,
      bid: round2(last - spread),
      ask: round2(last + spread),
      changePct: 0,
      dir: 0,
    });
  }
  return book;
}

export interface TickEngineOptions {
  symbols: number;
  /** ticks per second */
  rate: number;
  /** fraction (0..1) of symbols touched per tick */
  fraction: number;
  seed?: number;
  onTick: (updates: QuoteUpdate[]) => void;
}

/**
 * Emits batches of random-walk quote updates at a fixed rate. Owns the
 * master book (plain objects); each framework mirrors it into its own
 * reactive representation. Under main-thread jam, setInterval coalesces,
 * so applied updates/sec dropping is the honest throughput signal.
 */
export class TickEngine {
  readonly book: Quote[];
  private readonly open: number[];
  private readonly rng: () => number;
  private timer: ReturnType<typeof setInterval> | null = null;
  ticks = 0;
  updatesEmitted = 0;

  constructor(private readonly opts: TickEngineOptions) {
    const seed = opts.seed ?? 7;
    this.rng = createRng(seed * 31 + 1);
    this.book = createBook(opts.symbols, seed);
    this.open = this.book.map((q) => q.last);
  }

  get running(): boolean {
    return this.timer !== null;
  }

  start(): void {
    if (this.timer) return;
    this.timer = setInterval(() => this.tickOnce(), 1000 / this.opts.rate);
  }

  stop(): void {
    if (!this.timer) return;
    clearInterval(this.timer);
    this.timer = null;
  }

  /** Apply one tick synchronously (also used directly by tests). */
  tickOnce(): QuoteUpdate[] {
    const { symbols, fraction } = this.opts;
    const count = Math.max(1, Math.round(symbols * fraction));
    const updates: QuoteUpdate[] = [];
    for (let k = 0; k < count; k++) {
      const i = Math.floor(this.rng() * symbols);
      const q = this.book[i];
      const drift = (this.rng() - 0.5) * 0.004; // ±0.2 %
      const last = Math.max(0.01, round2(q.last * (1 + drift)));
      if (last === q.last) continue; // rounding ate the move
      const dir: 1 | -1 = last > q.last ? 1 : -1;
      const spread = Math.max(0.01, round2(last * 0.0004));
      const u: QuoteUpdate = {
        index: i,
        last,
        bid: round2(last - spread),
        ask: round2(last + spread),
        changePct: round2(((last - this.open[i]) / this.open[i]) * 100),
        dir,
      };
      q.last = u.last;
      q.bid = u.bid;
      q.ask = u.ask;
      q.changePct = u.changePct;
      q.dir = u.dir;
      updates.push(u);
    }
    this.ticks++;
    this.updatesEmitted += updates.length;
    this.opts.onTick(updates);
    return updates;
  }
}

/** One rolling-window sample of board performance. */
export interface PerfSample {
  /** frames rendered per second (requestAnimationFrame) */
  fps: number;
  /** frames longer than 32 ms in this window (= visible jank) */
  longFrames: number;
  /** long frames since start() */
  longTotal: number;
  /** quote updates applied per second */
  updatesPerSec: number;
  /** framework-specific work units per second (row renders / CD checks / cell effects) */
  workPerSec: number;
}

type RafFn = (cb: (time: number) => void) => number;
const raf = (globalThis as { requestAnimationFrame?: RafFn }).requestAnimationFrame;
const caf = (globalThis as { cancelAnimationFrame?: (id: number) => void })
  .cancelAnimationFrame;

/**
 * Frame/throughput meter. Counts rAF frames, long frames (>32 ms),
 * applied updates and framework "work" units, and emits a sample roughly
 * once per second. `frame()` is public so tests can drive it manually.
 */
export class PerfMeter {
  onSample?: (s: PerfSample) => void;
  private frames = 0;
  private longWindow = 0;
  private longTotal = 0;
  private updates = 0;
  private work = 0;
  private lastFrame = -1;
  private windowStart = 0;
  private rafId = 0;
  private running = false;
  private readonly windowMs: number;

  constructor(windowMs = 1000) {
    this.windowMs = windowMs;
  }

  countUpdates(n: number): void {
    this.updates += n;
  }

  countWork(n = 1): void {
    this.work += n;
  }

  start(): void {
    this.frames = this.longWindow = this.longTotal = this.updates = this.work = 0;
    this.lastFrame = -1;
    this.windowStart = performance.now();
    this.running = true;
    if (raf) {
      const loop = (now: number) => {
        if (!this.running) return;
        this.frame(now);
        this.rafId = raf(loop);
      };
      this.rafId = raf(loop);
    }
  }

  stop(): void {
    this.running = false;
    if (raf && caf) caf(this.rafId);
  }

  /** Record one frame at timestamp `now` (ms). Exposed for tests. */
  frame(now: number): void {
    if (this.lastFrame >= 0) {
      this.frames++;
      if (now - this.lastFrame > 32) {
        this.longWindow++;
        this.longTotal++;
      }
    }
    this.lastFrame = now;
    if (now - this.windowStart >= this.windowMs) {
      const secs = (now - this.windowStart) / 1000;
      this.onSample?.({
        fps: Math.round(this.frames / secs),
        longFrames: this.longWindow,
        longTotal: this.longTotal,
        updatesPerSec: Math.round(this.updates / secs),
        workPerSec: Math.round(this.work / secs),
      });
      this.frames = this.longWindow = this.updates = this.work = 0;
      this.windowStart = now;
    }
  }
}
