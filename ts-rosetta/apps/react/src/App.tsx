import { useState, type FormEvent } from 'react';
import { flushSync } from 'react-dom';
import {
  type Task,
  type Filter,
  type BenchResult,
  createTask,
  addTask,
  toggleTask,
  deleteTask,
  filterTasks,
  computeStats,
  generateTasks,
  benchmark,
  nextPaint,
  createTasksApi,
} from '@rosetta/core';

type Mode = 'local' | 'api';

interface BenchReport {
  n: number;
  render: BenchResult;
  update: BenchResult;
}

const FILTERS: Filter[] = ['all', 'active', 'done'];

export default function App() {
  // React: each piece of state is an explicit useState hook.
  // Derived values are recomputed on every render (no memo needed at this size).
  const [tasks, setTasks] = useState<Task[]>([]);
  const [filter, setFilter] = useState<Filter>('all');
  const [title, setTitle] = useState('');
  const [mode, setMode] = useState<Mode>('local');
  const [apiUrl, setApiUrl] = useState('http://localhost:4000');
  const [report, setReport] = useState<BenchReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const visible = filterTasks(tasks, filter);
  const stats = computeStats(tasks);

  async function withApi(fn: () => Promise<void>) {
    try {
      setError(null);
      await fn();
    } catch (e) {
      setError(String(e));
    }
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    const t = title.trim();
    if (!t) return;
    if (mode === 'local') {
      setTasks(addTask(tasks, createTask(t)));
    } else {
      await withApi(async () => {
        const created = await createTasksApi(apiUrl).add(t);
        setTasks((ts) => addTask(ts, created));
      });
    }
    setTitle('');
  }

  async function handleToggle(task: Task) {
    if (mode === 'local') {
      setTasks(toggleTask(tasks, task.id));
    } else {
      await withApi(async () => {
        await createTasksApi(apiUrl).setDone(task.id, !task.done);
        setTasks((ts) => toggleTask(ts, task.id));
      });
    }
  }

  async function handleRemove(id: string) {
    if (mode === 'local') {
      setTasks(deleteTask(tasks, id));
    } else {
      await withApi(async () => {
        await createTasksApi(apiUrl).remove(id);
        setTasks((ts) => deleteTask(ts, id));
      });
    }
  }

  async function switchMode(next: Mode) {
    setMode(next);
    setError(null);
    if (next === 'api') {
      await withApi(async () => setTasks(await createTasksApi(apiUrl).list()));
    } else {
      setTasks([]);
    }
  }

  async function runBench(n: number) {
    setReport(null);
    const generated = generateTasks(n);
    // flushSync forces React to commit synchronously inside the measured window;
    // nextPaint waits until the browser has actually painted the result.
    const render = await benchmark(async () => {
      flushSync(() => setTasks(generated));
      await nextPaint();
    });
    const update = await benchmark(async () => {
      flushSync(() => setTasks((ts) => ts.map((t) => ({ ...t, done: !t.done }))));
      await nextPaint();
    });
    setReport({ n, render, update });
  }

  return (
    <main className="app">
      <h1>
        Tasks <span className="badge">React 19 + Vite</span>
        <a className="badge" href="#board">
          board →
        </a>
      </h1>

      <section className="row">
        <label>
          <input type="radio" checked={mode === 'local'} onChange={() => switchMode('local')} />{' '}
          local state
        </label>
        <label>
          <input type="radio" checked={mode === 'api'} onChange={() => switchMode('api')} /> REST
          API
        </label>
        {mode === 'api' && (
          <input className="url" value={apiUrl} onChange={(e) => setApiUrl(e.target.value)} />
        )}
      </section>
      {error && <p className="error">{error}</p>}

      <form className="row" onSubmit={handleAdd}>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="New task..."
        />
        <button type="submit">Add</button>
      </form>

      <section className="row filters">
        {FILTERS.map((f) => (
          <button key={f} className={filter === f ? 'active' : ''} onClick={() => setFilter(f)}>
            {f}
          </button>
        ))}
        <span className="stats">
          total {stats.total} / active {stats.active} / done {stats.done}
        </span>
      </section>

      <ul className="tasks">
        {visible.map((t) => (
          <li key={t.id}>
            <label>
              <input type="checkbox" checked={t.done} onChange={() => handleToggle(t)} />
              <span className={t.done ? 'done' : ''}>{t.title}</span>
            </label>
            <button onClick={() => handleRemove(t.id)}>✕</button>
          </li>
        ))}
      </ul>

      <section className="bench">
        <button onClick={() => runBench(1_000)}>Bench 1,000</button>
        <button onClick={() => runBench(10_000)}>Bench 10,000</button>
        <button onClick={() => setTasks([])}>Clear</button>
        {report && (
          <p>
            N={report.n.toLocaleString()}: render {report.render.ms}ms / update-all{' '}
            {report.update.ms}ms
            {report.update.fps !== null && ` (${report.update.fps} fps)`}
          </p>
        )}
      </section>
    </main>
  );
}
