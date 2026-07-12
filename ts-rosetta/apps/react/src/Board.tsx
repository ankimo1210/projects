import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import {
  TickEngine,
  PerfMeter,
  type Quote,
  type PerfSample,
} from '@rosetta/core';
import { BoardStore, FRACTION } from './boardStore';

type BoardMode = 'naive' | 'optimized';
const SYMBOL_CHOICES = [50, 200, 1000, 5000];
const RATE_CHOICES = [10, 40, 60];

/* ---------- shared row view (dumb, identical in both modes) ---------- */

function RowView({ q }: { q: Quote }) {
  return (
    <tr>
      <td className="sym">{q.symbol}</td>
      <td className={q.dir === 1 ? 'up' : q.dir === -1 ? 'down' : ''}>
        {q.dir === 1 ? '▲ ' : q.dir === -1 ? '▼ ' : ''}
        {q.last.toFixed(2)}
      </td>
      <td>{q.bid.toFixed(2)}</td>
      <td>{q.ask.toFixed(2)}</td>
      <td className={q.changePct >= 0 ? 'up' : 'down'}>
        {q.changePct >= 0 ? '+' : ''}
        {q.changePct.toFixed(2)}%
      </td>
    </tr>
  );
}

function GridHead() {
  return (
    <thead>
      <tr>
        <th>Symbol</th>
        <th>Last</th>
        <th>Bid</th>
        <th>Ask</th>
        <th>Chg%</th>
      </tr>
    </thead>
  );
}

/* ---------- naive: one useState array, parent re-renders per tick ---------- */

function NaiveRow({ q, perf }: { q: Quote; perf: PerfMeter }) {
  // Runs for EVERY row on EVERY tick — the parent's setState re-renders
  // the whole list. This is the trap being measured.
  perf.countWork(1);
  return <RowView q={q} />;
}

function NaiveBoard({ symbols, rate, perf }: BoardProps) {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  useEffect(() => {
    const engine = new TickEngine({
      symbols,
      rate,
      fraction: FRACTION,
      onTick: (updates) => {
        perf.countUpdates(updates.length);
        setQuotes((prev) => {
          const next = prev.slice();
          for (const u of updates) {
            next[u.index] = {
              ...next[u.index],
              last: u.last,
              bid: u.bid,
              ask: u.ask,
              changePct: u.changePct,
              dir: u.dir,
            };
          }
          return next;
        });
      },
    });
    setQuotes(engine.book.map((q) => ({ ...q })));
    engine.start();
    return () => engine.stop();
  }, [symbols, rate, perf]);

  return (
    <div className="board-wrap">
      <table className="board-grid">
        <GridHead />
        <tbody>
          {quotes.map((q) => (
            <NaiveRow key={q.symbol} q={q} perf={perf} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- optimized: external store + per-row subscription ---------- */

function OptRow({ store, i, perf }: { store: BoardStore; i: number; perf: PerfMeter }) {
  // Re-renders ONLY when this row's slot in the store changes.
  const q = useSyncExternalStore(store.subscribes[i], store.snapshots[i]);
  perf.countWork(1);
  return <RowView q={q} />;
}

function OptBoard({ symbols, rate, perf }: BoardProps) {
  const [store] = useState(() => new BoardStore(symbols, rate, perf));
  useEffect(() => {
    store.engine.start();
    return () => store.engine.stop();
  }, [store]);

  return (
    <div className="board-wrap">
      <table className="board-grid">
        <GridHead />
        <tbody>
          {store.quotes.map((_, i) => (
            <OptRow key={store.quotes[i].symbol} store={store} i={i} perf={perf} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ---------- stats bar: isolates the 1/sec sample re-render ---------- */

function StatsBar({ perf }: { perf: PerfMeter }) {
  const [s, setS] = useState<PerfSample | null>(null);
  useEffect(() => {
    perf.onSample = setS;
    return () => {
      perf.onSample = undefined;
    };
  }, [perf]);
  return (
    <p className="board-stats">
      <span>
        <span data-stat="fps">{s?.fps ?? '–'}</span> fps
      </span>
      <span>
        <span data-stat="long">{s?.longTotal ?? 0}</span> long
      </span>
      <span>
        <span data-stat="upd">{s?.updatesPerSec ?? 0}</span> upd/s
      </span>
      <span>
        <span data-stat="work">{s?.workPerSec ?? 0}</span> work/s
      </span>
    </p>
  );
}

/* ---------- board shell ---------- */

interface BoardProps {
  symbols: number;
  rate: number;
  perf: PerfMeter;
}

export default function Board() {
  const [mode, setMode] = useState<BoardMode>('naive');
  const [symbols, setSymbols] = useState(200);
  const [rate, setRate] = useState(40);
  const [running, setRunning] = useState(false);
  const perfRef = useRef<PerfMeter | null>(null);
  perfRef.current ??= new PerfMeter();
  const perf = perfRef.current;

  useEffect(() => {
    if (!running) return;
    perf.start();
    return () => perf.stop();
    // restart the meter whenever the run config changes
  }, [running, mode, symbols, rate, perf]);

  const cfgKey = `${mode}-${symbols}-${rate}`;

  return (
    <main className="app board">
      <h1>
        Live Board <span className="badge">React 19 — {mode}</span>
        <a className="badge" href="#">
          ← tasks
        </a>
      </h1>

      <section className="row board-controls">
        {(['naive', 'optimized'] as const).map((m) => (
          <button
            key={m}
            data-mode={m}
            className={mode === m ? 'on' : ''}
            onClick={() => setMode(m)}
          >
            {m}
          </button>
        ))}
        <span className="stats">work = row renders</span>
      </section>

      <section className="row board-controls">
        {SYMBOL_CHOICES.map((n) => (
          <button
            key={n}
            data-symbols={n}
            className={symbols === n ? 'on' : ''}
            onClick={() => setSymbols(n)}
          >
            {n}
          </button>
        ))}
        <span>symbols</span>
        {RATE_CHOICES.map((r) => (
          <button
            key={r}
            data-rate={r}
            className={rate === r ? 'on' : ''}
            onClick={() => setRate(r)}
          >
            {r}/s
          </button>
        ))}
        <button data-action="toggle" onClick={() => setRunning(!running)}>
          {running ? 'Stop' : 'Start'}
        </button>
      </section>

      <StatsBar perf={perf} />

      {running ? (
        mode === 'naive' ? (
          <NaiveBoard key={cfgKey} symbols={symbols} rate={rate} perf={perf} />
        ) : (
          <OptBoard key={cfgKey} symbols={symbols} rate={rate} perf={perf} />
        )
      ) : (
        <p className="board-idle">Press Start — {symbols} symbols, {rate} ticks/s</p>
      )}
    </main>
  );
}
