'use client';
// Client Component: same React syntax as apps/react, but it starts from
// server-rendered props (hydration) and talks to Route Handlers under
// /api that live in the SAME project — no separate server needed.
import { useState, type FormEvent } from 'react';
import {
  type Task,
  type Filter,
  toggleTask,
  deleteTask,
  filterTasks,
  computeStats,
} from '@rosetta/core';

const FILTERS: Filter[] = ['all', 'active', 'done'];

export default function TaskApp({ initialTasks }: { initialTasks: Task[] }) {
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [filter, setFilter] = useState<Filter>('all');
  const [title, setTitle] = useState('');

  const visible = filterTasks(tasks, filter);
  const stats = computeStats(tasks);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    const t = title.trim();
    if (!t) return;
    const res = await fetch('/api/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: t }),
    });
    const created: Task = await res.json();
    setTasks((ts) => [...ts, created]);
    setTitle('');
  }

  async function handleToggle(task: Task) {
    await fetch(`/api/tasks/${task.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ done: !task.done }),
    });
    setTasks((ts) => toggleTask(ts, task.id));
  }

  async function handleRemove(id: string) {
    await fetch(`/api/tasks/${id}`, { method: 'DELETE' });
    setTasks((ts) => deleteTask(ts, id));
  }

  return (
    <main className="app">
      <h1>
        Tasks <span className="badge">Next.js 15 (SSR)</span>
      </h1>

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

      <p className="stats">
        Initial list above was rendered on the server — view page source to see it as HTML.
      </p>
    </main>
  );
}
