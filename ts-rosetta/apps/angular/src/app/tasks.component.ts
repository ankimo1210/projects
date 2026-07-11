import { Component, inject, signal } from '@angular/core';
import {
  type Task,
  type Filter,
  type BenchResult,
  generateTasks,
  benchmark,
  nextPaint,
  createTasksApi,
} from '@rosetta/core';
import { TasksService } from './tasks.service';

type Mode = 'local' | 'api';

interface BenchReport {
  n: number;
  render: BenchResult;
  update: BenchResult;
}

@Component({
  selector: 'app-tasks',
  // Angular: HTML lives in a template with its own control-flow syntax
  // (@for/@if), separate from the TypeScript class below.
  template: `
    <main class="app">
      <h1>
        Tasks <span class="badge">Angular 20</span>
        <a class="badge" href="#board">board →</a>
      </h1>

      <section class="row">
        <label>
          <input type="radio" [checked]="mode() === 'local'" (change)="switchMode('local')" />
          local state
        </label>
        <label>
          <input type="radio" [checked]="mode() === 'api'" (change)="switchMode('api')" />
          REST API
        </label>
        @if (mode() === 'api') {
          <input class="url" [value]="apiUrl()" (input)="apiUrl.set($any($event.target).value)" />
        }
      </section>
      @if (error()) {
        <p class="error">{{ error() }}</p>
      }

      <form class="row" (submit)="handleAdd($event)">
        <input
          type="text"
          [value]="title()"
          (input)="title.set($any($event.target).value)"
          placeholder="New task..."
        />
        <button type="submit">Add</button>
      </form>

      <section class="row filters">
        @for (f of FILTERS; track f) {
          <button [class.active]="store.filter() === f" (click)="store.filter.set(f)">
            {{ f }}
          </button>
        }
        <span class="stats">
          total {{ store.stats().total }} / active {{ store.stats().active }} / done
          {{ store.stats().done }}
        </span>
      </section>

      <ul class="tasks">
        @for (t of store.visible(); track t.id) {
          <li>
            <label>
              <input type="checkbox" [checked]="t.done" (change)="handleToggle(t)" />
              <span [class.done]="t.done">{{ t.title }}</span>
            </label>
            <button (click)="handleRemove(t.id)">✕</button>
          </li>
        }
      </ul>

      <section class="bench">
        <button (click)="runBench(1000)">Bench 1,000</button>
        <button (click)="runBench(10000)">Bench 10,000</button>
        <button (click)="store.replaceAll([])">Clear</button>
        @if (report(); as r) {
          <p>
            N={{ r.n.toLocaleString() }}: render {{ r.render.ms }}ms / update-all
            {{ r.update.ms }}ms
            @if (r.update.fps !== null) {
              ({{ r.update.fps }} fps)
            }
          </p>
        }
      </section>
    </main>
  `,
})
export class TasksComponent {
  // Angular: dependencies arrive via DI, not imports of instances.
  readonly store = inject(TasksService);

  readonly FILTERS: Filter[] = ['all', 'active', 'done'];
  readonly title = signal('');
  readonly mode = signal<Mode>('local');
  readonly apiUrl = signal('http://localhost:4000');
  readonly report = signal<BenchReport | null>(null);
  readonly error = signal<string | null>(null);

  private async withApi(fn: () => Promise<void>): Promise<void> {
    try {
      this.error.set(null);
      await fn();
    } catch (e) {
      this.error.set(String(e));
    }
  }

  async handleAdd(e: Event): Promise<void> {
    e.preventDefault();
    const t = this.title().trim();
    if (!t) return;
    if (this.mode() === 'local') {
      this.store.add(t);
    } else {
      await this.withApi(async () => {
        const created = await createTasksApi(this.apiUrl()).add(t);
        this.store.replaceAll([...this.store.tasks(), created]);
      });
    }
    this.title.set('');
  }

  async handleToggle(task: Task): Promise<void> {
    if (this.mode() === 'local') {
      this.store.toggle(task.id);
    } else {
      await this.withApi(async () => {
        await createTasksApi(this.apiUrl()).setDone(task.id, !task.done);
        this.store.toggle(task.id);
      });
    }
  }

  async handleRemove(id: string): Promise<void> {
    if (this.mode() === 'local') {
      this.store.remove(id);
    } else {
      await this.withApi(async () => {
        await createTasksApi(this.apiUrl()).remove(id);
        this.store.remove(id);
      });
    }
  }

  async switchMode(next: Mode): Promise<void> {
    this.mode.set(next);
    this.error.set(null);
    if (next === 'api') {
      await this.withApi(async () => {
        this.store.replaceAll(await createTasksApi(this.apiUrl()).list());
      });
    } else {
      this.store.replaceAll([]);
    }
  }

  async runBench(n: number): Promise<void> {
    this.report.set(null);
    const generated = generateTasks(n);
    // Signals mark the view dirty; zone.js schedules change detection.
    // nextPaint resolves after the browser has painted the committed DOM.
    const render = await benchmark(async () => {
      this.store.replaceAll(generated);
      await nextPaint();
    });
    const update = await benchmark(async () => {
      this.store.toggleAll();
      await nextPaint();
    });
    this.report.set({ n, render, update });
  }
}
