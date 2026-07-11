import type { Task, Filter, Stats } from './types';

let nextId = 0;

/** Create a new task. IDs are process-unique, not globally unique (learning app). */
export function createTask(title: string, createdAt: number = Date.now()): Task {
  return { id: `t${nextId++}`, title, done: false, createdAt };
}

/** Pure: returns a new array with the task appended. */
export function addTask(tasks: readonly Task[], task: Task): Task[] {
  return [...tasks, task];
}

/** Pure: returns a new array with the given task's `done` flipped. */
export function toggleTask(tasks: readonly Task[], id: string): Task[] {
  return tasks.map((t) => (t.id === id ? { ...t, done: !t.done } : t));
}

/** Pure: returns a new array without the given task. */
export function deleteTask(tasks: readonly Task[], id: string): Task[] {
  return tasks.filter((t) => t.id !== id);
}

/** Pure: applies the visibility filter. */
export function filterTasks(tasks: readonly Task[], filter: Filter): Task[] {
  switch (filter) {
    case 'all':
      return [...tasks];
    case 'active':
      return tasks.filter((t) => !t.done);
    case 'done':
      return tasks.filter((t) => t.done);
  }
}

/** Pure: aggregate counts. */
export function computeStats(tasks: readonly Task[]): Stats {
  const done = tasks.filter((t) => t.done).length;
  return { total: tasks.length, active: tasks.length - done, done };
}
