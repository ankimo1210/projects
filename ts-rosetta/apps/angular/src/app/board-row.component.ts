import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import type { WritableSignal } from '@angular/core';
import type { Quote, PerfMeter } from '@rosetta/core';

export interface RowSig {
  symbol: string;
  q: WritableSignal<Quote>;
}

/**
 * OnPush row. Reading `row().q()` in the template subscribes this view to
 * that ONE signal: a q.set() marks only this row dirty, and Angular's
 * scheduler refreshes just the dirty views — no zone, no full-tree check.
 */
@Component({
  // Attribute selector keeps valid <table> markup.
  // eslint-disable-next-line @angular-eslint/component-selector
  selector: 'tr[app-board-row]',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <td class="sym">{{ track() }}{{ row().symbol }}</td>
    <td [class]="row().q().dir === 1 ? 'up' : row().q().dir === -1 ? 'down' : ''">
      {{ row().q().dir === 1 ? '▲ ' : row().q().dir === -1 ? '▼ ' : '' }}{{ row().q().last.toFixed(2) }}
    </td>
    <td>{{ row().q().bid.toFixed(2) }}</td>
    <td>{{ row().q().ask.toFixed(2) }}</td>
    <td [class]="row().q().changePct >= 0 ? 'up' : 'down'">
      {{ row().q().changePct >= 0 ? '+' : '' }}{{ row().q().changePct.toFixed(2) }}%
    </td>
  `,
})
export class BoardRowComponent {
  readonly row = input.required<RowSig>();
  readonly perf = input.required<PerfMeter>();

  /** Deliberately impure: counts how often this row's view is checked. */
  track(): string {
    this.perf().countWork(1); // work = row CD checks
    return '';
  }
}
