import { describe, it, expect, vi } from 'vitest';
import {
  createRng,
  createBook,
  TickEngine,
  PerfMeter,
  type QuoteUpdate,
  type PerfSample,
} from './market';

describe('createRng / createBook', () => {
  it('rng is deterministic for a given seed', () => {
    const a = createRng(7);
    const b = createRng(7);
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
  });

  it('createBook makes n quotes with unique symbols and coherent bid/ask', () => {
    const book = createBook(100);
    expect(book).toHaveLength(100);
    expect(new Set(book.map((q) => q.symbol)).size).toBe(100);
    for (const q of book) {
      expect(q.bid).toBeLessThan(q.ask);
      expect(q.last).toBeGreaterThan(0);
      expect(q.dir).toBe(0);
    }
  });
});

describe('TickEngine', () => {
  const opts = (onTick: (u: QuoteUpdate[]) => void) => ({
    symbols: 50,
    rate: 40,
    fraction: 0.3,
    onTick,
  });

  it('two engines with the same seed emit identical update streams', () => {
    const got: QuoteUpdate[][] = [[], []];
    const e1 = new TickEngine({ ...opts((u) => got[0].push(...u)) });
    const e2 = new TickEngine({ ...opts((u) => got[1].push(...u)) });
    e1.tickOnce();
    e2.tickOnce();
    expect(got[0]).toEqual(got[1]);
    expect(got[0].length).toBeGreaterThan(0);
  });

  it('tickOnce touches about fraction*symbols and mutates the book to match', () => {
    let updates: QuoteUpdate[] = [];
    const e = new TickEngine(opts((u) => (updates = u)));
    e.tickOnce();
    expect(updates.length).toBeLessThanOrEqual(15); // 50 * 0.3
    expect(updates.length).toBeGreaterThan(0);
    // The same index may be touched twice in one tick; the book reflects
    // the LAST update per index (later wins).
    const lastPerIndex = new Map(updates.map((u) => [u.index, u]));
    for (const u of lastPerIndex.values()) {
      const q = e.book[u.index];
      expect(q.last).toBe(u.last);
      expect(q.dir).toBe(u.dir);
      expect(u.bid).toBeLessThan(u.ask);
    }
    expect(e.updatesEmitted).toBe(updates.length);
  });

  it('start/stop drives ticks via setInterval', () => {
    vi.useFakeTimers();
    const onTick = vi.fn();
    const e = new TickEngine(opts(onTick));
    e.start();
    expect(e.running).toBe(true);
    vi.advanceTimersByTime(1000); // 40 ticks/s -> ~40 calls
    e.stop();
    expect(e.running).toBe(false);
    expect(onTick.mock.calls.length).toBe(40);
    vi.advanceTimersByTime(500);
    expect(onTick.mock.calls.length).toBe(40); // stopped
    vi.useRealTimers();
  });
});

describe('PerfMeter', () => {
  it('computes fps, long frames, and rates from manual frames', () => {
    const meter = new PerfMeter(1000);
    const samples: PerfSample[] = [];
    meter.onSample = (s) => samples.push(s);
    meter.start();
    meter.stop(); // stop the raf loop; drive frames manually
    const t0 = performance.now();
    meter.countUpdates(240);
    meter.countWork(1200);
    // 10 frames at ~16ms, then one 100ms stall, then cross the window
    for (let i = 1; i <= 10; i++) meter.frame(t0 + i * 16);
    meter.frame(t0 + 260); // 100ms gap -> long frame
    meter.frame(t0 + 1001); // crosses window -> sample emitted
    expect(samples).toHaveLength(1);
    const s = samples[0]!;
    expect(s.longFrames).toBeGreaterThanOrEqual(2);
    expect(s.longTotal).toBe(s.longFrames);
    expect(s.updatesPerSec).toBeGreaterThan(200);
    expect(s.workPerSec).toBeGreaterThan(1000);
    expect(s.fps).toBeGreaterThan(0);
  });
});
