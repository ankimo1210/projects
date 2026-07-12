import type { Task } from './types';
import { createTask } from './store';

// Resolved via globalThis so this file type-checks without the DOM lib
// (server-express / server-nest re-check core's source with lib: ES2022).
type RafFn = (cb: (time: number) => void) => number;
const raf = (globalThis as { requestAnimationFrame?: RafFn }).requestAnimationFrame;
const caf = (globalThis as { cancelAnimationFrame?: (id: number) => void })
  .cancelAnimationFrame;

export interface BenchResult {
  /** Total wall-clock time of the measured operation, in ms. */
  ms: number;
  /** Frames observed during the operation window (requestAnimationFrame). */
  fps: number | null;
}

/** Generate n tasks; every 3rd one is done, so filters/stats have work to do. */
export function generateTasks(n: number): Task[] {
  const tasks: Task[] = [];
  for (let i = 0; i < n; i++) {
    const t = createTask(`Task #${i}`, i);
    if (i % 3 === 0) t.done = true;
    tasks.push(t);
  }
  return tasks;
}

/**
 * Resolve after the browser has painted (double requestAnimationFrame).
 * Every UI implementation awaits this after a state change so that bench
 * numbers include actual rendering, not just the framework's JS work.
 */
export function nextPaint(): Promise<void> {
  return new Promise((resolve) => {
    if (!raf) return resolve();
    raf(() => raf(() => resolve()));
  });
}

/**
 * Measure one async operation. `fn` should resolve when the UI has committed
 * (e.g. after awaiting the framework's next-tick / effect flush).
 * FPS is sampled with requestAnimationFrame when available (browser only).
 */
export async function benchmark(fn: () => Promise<void> | void): Promise<BenchResult> {
  let frames = 0;
  let rafId = 0;
  let running = true;
  if (raf) {
    const tick = () => {
      frames++;
      if (running) rafId = raf(tick);
    };
    rafId = raf(tick);
  }

  const start = performance.now();
  await fn();
  const ms = performance.now() - start;

  running = false;
  if (raf && caf) caf(rafId);

  const fps = raf && ms > 0 ? Math.round((frames / ms) * 1000) : null;
  return { ms: Math.round(ms * 100) / 100, fps };
}
