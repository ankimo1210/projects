import {
  ChangeDetectionStrategy,
  Component,
  input,
  signal,
  OnInit,
  OnDestroy,
} from '@angular/core';
import type { PerfMeter, PerfSample } from '@rosetta/core';

/** Isolates the once-per-second sample updates from the board component. */
@Component({
  selector: 'app-stats-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <p class="board-stats">
      <span><span data-stat="fps">{{ s()?.fps ?? '–' }}</span> fps</span>
      <span><span data-stat="long">{{ s()?.longTotal ?? 0 }}</span> long</span>
      <span><span data-stat="upd">{{ s()?.updatesPerSec ?? 0 }}</span> upd/s</span>
      <span><span data-stat="work">{{ s()?.workPerSec ?? 0 }}</span> work/s</span>
    </p>
  `,
})
export class StatsBarComponent implements OnInit, OnDestroy {
  readonly perf = input.required<PerfMeter>();
  readonly s = signal<PerfSample | null>(null);

  ngOnInit(): void {
    this.perf().onSample = (sample) => this.s.set(sample);
  }

  ngOnDestroy(): void {
    this.perf().onSample = undefined;
  }
}
