// Server-side in-memory store. This code runs in Node.js on the server —
// the browser never sees it. The `globalThis` stash survives dev-mode
// hot reloads, which would otherwise reset a plain module variable.
import { type Task, createTask, addTask, deleteTask } from '@rosetta/core';

interface ServerStore {
  tasks: Task[];
}

const g = globalThis as typeof globalThis & { __rosettaStore?: ServerStore };

function seed(): Task[] {
  return ['Learn Next.js', 'Compare with plain React', 'View page source'].map((t) =>
    createTask(t),
  );
}

const store: ServerStore = (g.__rosettaStore ??= { tasks: seed() });

export function listTasks(): Task[] {
  return store.tasks;
}

export function createOne(title: string): Task {
  const task = createTask(title);
  store.tasks = addTask(store.tasks, task);
  return task;
}

export function setDone(id: string, done: boolean): Task | undefined {
  const task = store.tasks.find((t) => t.id === id);
  if (task) task.done = done;
  return task;
}

export function removeOne(id: string): boolean {
  const before = store.tasks.length;
  store.tasks = deleteTask(store.tasks, id);
  return store.tasks.length < before;
}
