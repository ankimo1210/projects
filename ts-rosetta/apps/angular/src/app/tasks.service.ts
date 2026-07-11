import { Injectable, signal, computed } from '@angular/core';
import {
  type Task,
  type Filter,
  createTask,
  addTask,
  toggleTask,
  deleteTask,
  filterTasks,
  computeStats,
} from '@rosetta/core';

/**
 * Angular: state lives in an injectable service, not in the component.
 * Signals (`signal`/`computed`) are Angular's fine-grained reactivity —
 * the same role as Vue's ref/computed, but injected via DI.
 */
@Injectable({ providedIn: 'root' })
export class TasksService {
  readonly tasks = signal<Task[]>([]);
  readonly filter = signal<Filter>('all');

  readonly visible = computed(() => filterTasks(this.tasks(), this.filter()));
  readonly stats = computed(() => computeStats(this.tasks()));

  add(title: string): void {
    this.tasks.update((ts) => addTask(ts, createTask(title)));
  }

  toggle(id: string): void {
    this.tasks.update((ts) => toggleTask(ts, id));
  }

  remove(id: string): void {
    this.tasks.update((ts) => deleteTask(ts, id));
  }

  replaceAll(tasks: Task[]): void {
    this.tasks.set(tasks);
  }

  toggleAll(): void {
    this.tasks.update((ts) => ts.map((t) => ({ ...t, done: !t.done })));
  }
}
