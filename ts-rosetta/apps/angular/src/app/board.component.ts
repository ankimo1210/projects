import {
  ChangeDetectionStrategy,
  Component,
  NgZone,
  OnDestroy,
  inject,
  signal,
} from '@angular/core';
import { TickEngine, PerfMeter } from '@rosetta/core';
import { BoardRowComponent, type RowSig } from './board-row.component';
import { StatsBarComponent } from './stats-bar.component';

const SYMBOL_CHOICES = [50, 200, 1000, 5000];
const RATE_CHOICES = [10, 40, 60];
const FRACTION = 0.1;

/**
 * Angular board: one WritableSignal<Quote> per row. The engine and the
 * perf meter run OUTSIDE the Angular zone — otherwise every setInterval
 * tick and every rAF frame would trigger app-wide change detection.
 * Signal writes alone schedule targeted refresh of the dirty rows.
 */
@Component({
  selector: 'app-board',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BoardRowComponent, StatsBarComponent],
  template: `
    <main class="app board">
      <h1>
        Live Board <span class="badge">Angular 20</span>
        <a class="badge" href="#">← tasks</a>
      </h1>

      <section class="row board-controls">
        <span class="stats">work = row CD checks</span>
      </section>

      <section class="row board-controls">
        @for (n of SYMBOL_CHOICES; track n) {
          <button [attr.data-symbols]="n" [class.on]="symbols() === n" (click)="setSymbols(n)">
            {{ n }}
          </button>
        }
        <span>symbols</span>
        @for (r of RATE_CHOICES; track r) {
          <button [attr.data-rate]="r" [class.on]="rate() === r" (click)="setRate(r)">
            {{ r }}/s
          </button>
        }
        <button data-action="toggle" (click)="toggle()">{{ running() ? 'Stop' : 'Start' }}</button>
      </section>

      <app-stats-bar [perf]="perf" />

      @if (running()) {
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
              @for (r of rows(); track r.symbol) {
                <tr app-board-row [row]="r" [perf]="perf"></tr>
              }
            </tbody>
          </table>
        </div>
      } @else {
        <p class="board-idle">Press Start — {{ symbols() }} symbols, {{ rate() }} ticks/s</p>
      }
    </main>
  `,
})
export class BoardComponent implements OnDestroy {
  private readonly zone = inject(NgZone);

  readonly SYMBOL_CHOICES = SYMBOL_CHOICES;
  readonly RATE_CHOICES = RATE_CHOICES;
  readonly symbols = signal(200);
  readonly rate = signal(40);
  readonly running = signal(false);
  readonly rows = signal<RowSig[]>([]);
  readonly perf = new PerfMeter();

  private engine: TickEngine | null = null;

  toggle(): void {
    if (this.running()) this.stop();
    else this.start();
  }

  setSymbols(n: number): void {
    this.symbols.set(n);
    if (this.running()) this.start();
  }

  setRate(r: number): void {
    this.rate.set(r);
    if (this.running()) this.start();
  }

  start(): void {
    this.stop();
    const engine = new TickEngine({
      symbols: this.symbols(),
      rate: this.rate(),
      fraction: FRACTION,
      onTick: (updates) => {
        this.perf.countUpdates(updates.length);
        const rows = this.rows();
        for (const u of updates) {
          const row = rows[u.index];
          // signal.set from outside the zone still marks the row's view
          // dirty and schedules a targeted refresh (Angular 18+ scheduler).
          row.q.set({
            ...row.q(),
            last: u.last,
            bid: u.bid,
            ask: u.ask,
            changePct: u.changePct,
            dir: u.dir,
          });
        }
      },
    });
    this.rows.set(engine.book.map((q) => ({ symbol: q.symbol, q: signal({ ...q }) })));
    this.engine = engine;
    this.zone.runOutsideAngular(() => {
      engine.start();
      this.perf.start();
    });
    this.running.set(true);
  }

  stop(): void {
    this.engine?.stop();
    this.engine = null;
    this.perf.stop();
    this.running.set(false);
  }

  ngOnDestroy(): void {
    this.stop();
  }
}
