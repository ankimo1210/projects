// External store for the OPTIMIZED React board. React itself has no
// fine-grained reactivity, so we build the granularity by hand: each row
// subscribes to its own slot and re-renders only when that slot changes.
import { TickEngine, PerfMeter, type Quote } from '@rosetta/core';

export const FRACTION = 0.1;

export class BoardStore {
  quotes: Quote[];
  readonly engine: TickEngine;
  // Pre-built stable (subscribe, getSnapshot) pairs — useSyncExternalStore
  // resubscribes if these identities change between renders.
  readonly subscribes: Array<(cb: () => void) => () => void>;
  readonly snapshots: Array<() => Quote>;
  private readonly rowSubs: Array<Set<() => void>>;

  constructor(symbols: number, rate: number, perf: PerfMeter) {
    this.engine = new TickEngine({
      symbols,
      rate,
      fraction: FRACTION,
      onTick: (updates) => {
        perf.countUpdates(updates.length);
        const touched = new Set<number>();
        for (const u of updates) {
          const q = this.quotes[u.index];
          // Replace the object: snapshot identity must change for React.
          this.quotes[u.index] = {
            ...q,
            last: u.last,
            bid: u.bid,
            ask: u.ask,
            changePct: u.changePct,
            dir: u.dir,
          };
          touched.add(u.index);
        }
        for (const i of touched) {
          for (const cb of this.rowSubs[i]) cb();
        }
      },
    });
    this.quotes = this.engine.book.map((q) => ({ ...q }));
    this.rowSubs = this.quotes.map(() => new Set());
    this.subscribes = this.quotes.map((_, i) => (cb: () => void) => {
      this.rowSubs[i].add(cb);
      return () => this.rowSubs[i].delete(cb);
    });
    this.snapshots = this.quotes.map((_, i) => () => this.quotes[i]);
  }
}
