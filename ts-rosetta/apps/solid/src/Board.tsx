// Solid board: JSX like React, but there is NO re-render. Components run
// ONCE; each {expression} compiles to a fine-grained effect that patches
// its own DOM node. A store path update touches exactly the cells that
// read the changed fields — the "optimized React" architecture is simply
// how Solid works by default.
import { For, Show, batch, createSignal, onCleanup } from 'solid-js';
import { createStore } from 'solid-js/store';
import {
  TickEngine,
  PerfMeter,
  type Quote,
  type PerfSample,
} from '@rosetta/core';

const SYMBOL_CHOICES = [50, 200, 1000, 5000];
const RATE_CHOICES = [10, 40, 60];
const FRACTION = 0.1;

export default function Board() {
  const [symbols, setSymbols] = createSignal(200);
  const [rate, setRate] = createSignal(40);
  const [running, setRunning] = createSignal(false);
  const [sample, setSample] = createSignal<PerfSample | null>(null);
  const [rows, setRows] = createStore<Quote[]>([]);
  const perf = new PerfMeter();
  perf.onSample = setSample;
  let engine: TickEngine | null = null;

  function stop() {
    engine?.stop();
    engine = null;
    perf.stop();
    setRunning(false);
  }

  function start() {
    stop();
    const e = new TickEngine({
      symbols: symbols(),
      rate: rate(),
      fraction: FRACTION,
      onTick: (updates) => {
        perf.countUpdates(updates.length);
        batch(() => {
          for (const u of updates) {
            // Path update: merges into the row proxy → cell-level effects.
            setRows(u.index, {
              last: u.last,
              bid: u.bid,
              ask: u.ask,
              changePct: u.changePct,
              dir: u.dir,
            });
          }
        });
      },
    });
    setRows(e.book.map((q) => ({ ...q })));
    engine = e;
    e.start();
    perf.start();
    setRunning(true);
  }

  function toggle() {
    if (running()) stop();
    else start();
  }

  function pickSymbols(n: number) {
    setSymbols(n);
    if (running()) start();
  }

  function pickRate(r: number) {
    setRate(r);
    if (running()) start();
  }

  onCleanup(stop);

  return (
    <main class="app board">
      <h1>
        Live Board <span class="badge">Solid 1.9</span>
        <a class="badge" href="http://localhost:8080">dashboard</a>
      </h1>

      <section class="row board-controls">
        <span class="stats">work = last-cell effect runs</span>
      </section>

      <section class="row board-controls">
        <For each={SYMBOL_CHOICES}>
          {(n) => (
            <button
              data-symbols={n}
              classList={{ on: symbols() === n }}
              onClick={() => pickSymbols(n)}
            >
              {n}
            </button>
          )}
        </For>
        <span>symbols</span>
        <For each={RATE_CHOICES}>
          {(r) => (
            <button data-rate={r} classList={{ on: rate() === r }} onClick={() => pickRate(r)}>
              {r}/s
            </button>
          )}
        </For>
        <button data-action="toggle" onClick={toggle}>
          {running() ? 'Stop' : 'Start'}
        </button>
      </section>

      <p class="board-stats">
        <span>
          <span data-stat="fps">{sample()?.fps ?? '–'}</span> fps
        </span>
        <span>
          <span data-stat="long">{sample()?.longTotal ?? 0}</span> long
        </span>
        <span>
          <span data-stat="upd">{sample()?.updatesPerSec ?? 0}</span> upd/s
        </span>
        <span>
          <span data-stat="work">{sample()?.workPerSec ?? 0}</span> work/s
        </span>
      </p>

      <Show
        when={running()}
        fallback={
          <p class="board-idle">
            Press Start — {symbols()} symbols, {rate()} ticks/s
          </p>
        }
      >
        <div class="board-wrap">
          <table class="board-grid">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Last</th>
                <th>Bid</th>
                <th>Ask</th>
                <th>Chg%</th>
              </tr>
            </thead>
            <tbody>
              <For each={rows}>
                {(q) => (
                  <tr>
                    <td class="sym">{q.symbol}</td>
                    <td class={q.dir === 1 ? 'up' : q.dir === -1 ? 'down' : ''}>
                      {q.dir === 1 ? '▲ ' : q.dir === -1 ? '▼ ' : ''}
                      {/* comma expression: counting rides on the effect that
                          re-runs whenever this row's `last` changes */}
                      {(perf.countWork(1), q.last.toFixed(2))}
                    </td>
                    <td>{q.bid.toFixed(2)}</td>
                    <td>{q.ask.toFixed(2)}</td>
                    <td class={q.changePct >= 0 ? 'up' : 'down'}>
                      {q.changePct >= 0 ? '+' : ''}
                      {q.changePct.toFixed(2)}%
                    </td>
                  </tr>
                )}
              </For>
            </tbody>
          </table>
        </div>
      </Show>
    </main>
  );
}
