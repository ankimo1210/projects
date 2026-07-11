import { describe, it, expect } from 'vitest';
import {
  createTask,
  addTask,
  toggleTask,
  deleteTask,
  filterTasks,
  computeStats,
} from './store';
import { generateTasks, benchmark } from './bench';
import type { Task } from './types';

describe('store', () => {
  it('createTask produces unique ids and sane defaults', () => {
    const a = createTask('buy milk', 123);
    const b = createTask('walk dog', 456);
    expect(a.id).not.toBe(b.id);
    expect(a).toMatchObject({ title: 'buy milk', done: false, createdAt: 123 });
  });

  it('addTask appends without mutating the original', () => {
    const t = createTask('x');
    const before: Task[] = [];
    const after = addTask(before, t);
    expect(after).toHaveLength(1);
    expect(before).toHaveLength(0);
  });

  it('toggleTask flips only the target task', () => {
    const [a, b] = [createTask('a'), createTask('b')];
    const tasks = [a, b];
    const toggled = toggleTask(tasks, a.id);
    expect(toggled.find((t) => t.id === a.id)?.done).toBe(true);
    expect(toggled.find((t) => t.id === b.id)?.done).toBe(false);
    expect(tasks.find((t) => t.id === a.id)?.done).toBe(false); // no mutation
  });

  it('deleteTask removes only the target task', () => {
    const [a, b] = [createTask('a'), createTask('b')];
    const rest = deleteTask([a, b], a.id);
    expect(rest.map((t) => t.id)).toEqual([b.id]);
  });

  it('filterTasks handles all three filters', () => {
    const a = createTask('a');
    const b = { ...createTask('b'), done: true };
    const tasks = [a, b];
    expect(filterTasks(tasks, 'all')).toHaveLength(2);
    expect(filterTasks(tasks, 'active').map((t) => t.id)).toEqual([a.id]);
    expect(filterTasks(tasks, 'done').map((t) => t.id)).toEqual([b.id]);
  });

  it('computeStats counts total/active/done', () => {
    const tasks = generateTasks(9); // every 3rd is done -> 3 done
    expect(computeStats(tasks)).toEqual({ total: 9, active: 6, done: 3 });
  });
});

describe('bench', () => {
  it('generateTasks produces n tasks with every 3rd done', () => {
    const tasks = generateTasks(6);
    expect(tasks).toHaveLength(6);
    expect(tasks.filter((t) => t.done)).toHaveLength(2); // indices 0, 3
  });

  it('benchmark measures elapsed time (fps null outside browser)', async () => {
    const result = await benchmark(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });
    expect(result.ms).toBeGreaterThanOrEqual(15);
    expect(result.fps).toBeNull(); // no requestAnimationFrame in Node
  });
});
