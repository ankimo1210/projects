import type {
  AircraftCommand,
  AircraftState,
  BackendStatus,
  CommandResult,
  ScenarioInitialState,
} from '@b737/shared';

/**
 * Abstraction over the simulation of record (spec §5).
 * Everything above this interface is backend-agnostic; FlightGear protocol
 * details never leak past the adapter package.
 */
export interface FlightBackend {
  connect(): Promise<void>;
  disconnect(): Promise<void>;
  getStatus(): BackendStatus;
  /** Register a state listener; returns an unsubscribe function. */
  subscribe(listener: (state: AircraftState) => void): () => void;
  sendCommand(command: AircraftCommand): Promise<CommandResult>;
  resetScenario(config: ScenarioInitialState): Promise<void>;
  /** Freeze/unfreeze the simulation (training aid). Optional per backend. */
  setPaused?(paused: boolean): Promise<CommandResult>;
}

/** Default MVP scenario initial conditions (spec §20). */
export const DEFAULT_SCENARIO_INIT: ScenarioInitialState = {
  seed: 737800,
  airportIcao: 'KSFO',
  runwayId: '28R',
  startAt: 'holding_point',
  flapDetent: 5,
  parkingBrakeSet: true,
  // NON_CERTIFIED_APPROXIMATION: moderate weight MVP default.
  grossWeightLb: 145000,
  windDirDeg: 290,
  windSpeedKt: 6,
};
