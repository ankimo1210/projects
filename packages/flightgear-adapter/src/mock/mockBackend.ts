import type {
  AircraftCommand,
  AircraftState,
  BackendStatus,
  CommandResult,
  ScenarioInitialState,
} from '@b737/shared';
import type { FlightBackend } from '../backend.js';
import { DEFAULT_SCENARIO_INIT } from '../backend.js';
import { MockFlightModel } from './flightModel.js';

export interface MockBackendOptions {
  /** State publish rate. Physics substeps at a fixed 60 Hz regardless. */
  stateRateHz?: number;
  initialScenario?: ScenarioInitialState;
}

/**
 * FlightBackend that runs {@link MockFlightModel} on a local timer.
 * Physics advances a fixed simulated interval per tick, so trajectories are
 * reproducible for a given seed + command sequence even under timer jitter
 * (spec §5 mock mode determinism; spec §6 physics decoupled from rendering).
 */
export class MockBackend implements FlightBackend {
  private model: MockFlightModel;
  private listeners = new Set<(state: AircraftState) => void>();
  private timer: ReturnType<typeof setInterval> | null = null;
  private readonly stateRateHz: number;
  private lastStateAtMs: number | null = null;
  private connected = false;

  private paused = false;

  constructor(options: MockBackendOptions = {}) {
    this.stateRateHz = options.stateRateHz ?? 30;
    this.model = new MockFlightModel(options.initialScenario ?? DEFAULT_SCENARIO_INIT);
  }

  connect(): Promise<void> {
    if (this.timer) return Promise.resolve();
    this.connected = true;
    const periodMs = 1000 / this.stateRateHz;
    this.timer = setInterval(() => {
      if (!this.paused) this.model.step(periodMs / 1000);
      const state = this.model.snapshot(Date.now());
      this.lastStateAtMs = state.timestampMs;
      for (const l of this.listeners) l(state);
    }, periodMs);
    return Promise.resolve();
  }

  setPaused(paused: boolean): Promise<import('@b737/shared').CommandResult> {
    this.paused = paused;
    return Promise.resolve({ ok: true });
  }

  disconnect(): Promise<void> {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
    this.connected = false;
    return Promise.resolve();
  }

  getStatus(): BackendStatus {
    return {
      mode: 'mock',
      connected: this.connected,
      detail: this.connected ? 'mock model running' : 'mock model stopped',
      lastStateAgeMs: this.lastStateAtMs === null ? null : Date.now() - this.lastStateAtMs,
      stateRateHz: this.stateRateHz,
    };
  }

  subscribe(listener: (state: AircraftState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  sendCommand(command: AircraftCommand): Promise<CommandResult> {
    return Promise.resolve(this.model.applyCommand(command));
  }

  resetScenario(config: ScenarioInitialState): Promise<void> {
    this.model.reset(config);
    return Promise.resolve();
  }
}
