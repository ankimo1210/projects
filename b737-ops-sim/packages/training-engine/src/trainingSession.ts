import {
  getRunway,
  type AircraftCommand,
  type AircraftState,
  type CommandResult,
  type FailureKind,
  type ScenarioInitialState,
} from '@b737/shared';
import {
  ScenarioRuntime,
  type ScenarioDefinition,
  type ScenarioEvent,
} from '@b737/scenario-engine';
import { AtcController, type AtcInstruction, type AtcPhase } from './atc.js';
import { generateDebrief, type DebriefReport } from './debrief.js';
import { FirstOfficer } from './firstOfficer.js';
import type { TranscriptEntry } from './transcript.js';

export type TrainingMode = 'guided' | 'assisted' | 'evaluation';

export interface FlightControlCheckProgress {
  rollLeft: boolean;
  rollRight: boolean;
  pitchForward: boolean;
  pitchBack: boolean;
  rudderLeft: boolean;
  rudderRight: boolean;
}

/** Where the flight joins the ATC sequence, from the scenario's start point. */
function atcEntryPhase(startAt: ScenarioInitialState['startAt']): AtcPhase {
  if (startAt === 'stand') return 'awaiting_taxi_request';
  if (startAt === 'final_approach') return 'cleared_approach';
  return 'awaiting_takeoff_request';
}

/** FO callouts the debrief must see as events (R-19). */
const FO_SAFETY_EVENTS: Record<string, { severity: ScenarioEvent['severity']; message: string }> = {
  'fo:unstable_approach': {
    severity: 'deviation',
    message: 'First officer called an unstable approach',
  },
  'fo:gear_reminder': {
    severity: 'deviation',
    message: 'First officer had to prompt for the landing gear',
  },
  // Stabilisation gates (M3 D4): the call is data the debrief scores, not just
  // a line of transcript.
  'fo:gate_1000_unstable': {
    severity: 'deviation',
    message: 'Not stable at the 1,000 ft gate',
  },
  'fo:gate_500_unstable': {
    severity: 'deviation',
    message: 'Not stable at the 500 ft gate',
  },
  'fo:minimums_go_around': {
    severity: 'deviation',
    message: 'Not stable at minimums — a go-around was called for',
  },
};

/**
 * Orchestrates one training run: scenario phase machine + first officer +
 * ATC + transcript (spec §11–§16). Pure and deterministic — the browser (or a
 * test) feeds state samples in and reads transcript/checklists/debrief out.
 * The selected mode changes assistance only, never flight behavior (spec §15).
 */
export class TrainingSession {
  readonly runtime: ScenarioRuntime;
  readonly fo: FirstOfficer;
  readonly atc: AtcController;
  readonly transcript: TranscriptEntry[] = [];
  mode: TrainingMode;
  /** Monotonic counter UIs can watch to re-render cheaply. */
  version = 0;

  private pendingInstructions = new Map<string, AtcInstruction>();
  private axisExtremes = {
    rollMin: 0,
    rollMax: 0,
    pitchMin: 0,
    pitchMax: 0,
    yawMin: 0,
    yawMax: 0,
  };
  private lastState: AircraftState | null = null;
  private readonly sendCommand: (
    command: AircraftCommand,
  ) => void | CommandResult | Promise<CommandResult>;

  constructor(
    readonly scenario: ScenarioDefinition,
    options: {
      mode?: TrainingMode;
      /**
       * How the session asks the aircraft to do something the scenario
       * requires — currently only failure injection (spec §22 Phase 5). The
       * host wires this to the same command path the crew uses.
       */
      sendCommand?: (command: AircraftCommand) => void | CommandResult | Promise<CommandResult>;
    } = {},
  ) {
    this.mode = options.mode ?? 'guided';
    this.sendCommand = options.sendCommand ?? (() => undefined);
    this.runtime = new ScenarioRuntime(scenario);
    this.fo = new FirstOfficer({
      grossWeightLb: scenario.initialState.grossWeightLb,
      takeoffPhaseIds: ['takeoff_roll', 'rotation'],
      approachPhaseIds: ['final_approach', 'landing'],
    });
    const runway = getRunway(scenario.initialState.airportIcao, scenario.initialState.runwayId);
    if (!runway) throw new Error('scenario runway not found');
    this.atc = new AtcController(
      runway,
      {
        dirDeg: scenario.initialState.windDirDeg,
        speedKt: scenario.initialState.windSpeedKt,
      },
      atcEntryPhase(scenario.initialState.startAt),
    );
    this.runtime.onEvent((event) => this.onScenarioEvent(event));
  }

  get state(): AircraftState | null {
    return this.lastState;
  }

  get flightControlCheckProgress(): FlightControlCheckProgress {
    const e = this.axisExtremes;
    return {
      rollLeft: e.rollMin < -0.85,
      rollRight: e.rollMax > 0.85,
      pitchForward: e.pitchMin < -0.85,
      pitchBack: e.pitchMax > 0.85,
      rudderLeft: e.yawMin < -0.85,
      rudderRight: e.yawMax > 0.85,
    };
  }

  get phaseId(): string {
    return this.runtime.phaseId;
  }

  get complete(): boolean {
    return this.runtime.complete;
  }

  /** Checklist relevant to the current phase (UI focus). */
  get activeChecklistId(): string | null {
    const phase = this.runtime.phaseId;
    if (['cold_and_dark', 'power_on'].includes(phase)) return 'preflight';
    if (phase === 'apu_available') return 'before_start_systems';
    if (phase === 'after_start') return 'after_start';
    if (phase === 'ready_to_taxi') return 'before_taxi';
    if (['before_takeoff', 'line_up'].includes(phase)) return 'before_takeoff';
    if (['approach_setup', 'final_approach'].includes(phase)) return 'landing';
    // After Landing is run once clear of the runway, not during the rollout.
    if (['runway_exit'].includes(phase)) return 'after_landing';
    return null;
  }

  /** Feed one live state sample. */
  update(state: AircraftState): void {
    this.lastState = state;
    this.runtime.update(state); // events flow via onScenarioEvent
    for (const line of this.fo.update(state, this.runtime.phaseId)) {
      this.push(line);
      this.recordFoSafetyEvent(line, state);
    }
    for (const instruction of this.atc.update(state, this.runtime.phaseId)) {
      this.registerInstruction(instruction);
    }
  }

  /** User keys the mic for a taxi clearance (ground control). */
  requestTaxiClearance(): void {
    if (!this.lastState) return;
    this.push({
      id: `user_req_${this.transcript.length}`,
      simTimeSec: this.lastState.simTimeSec,
      speaker: 'captain',
      message: `Ground, Boeing 737 at the stand, request taxi.`,
    });
    const result = this.atc.requestTaxiClearance(this.lastState);
    if ('flagsOnAccept' in result) this.registerInstruction(result);
    else this.push(result);
  }

  /**
   * The crew goes around. This is the crew's call — the FO may advise it, but
   * pressing TO/GA is what starts the missed approach (spec §22 Phase 3).
   */
  announceGoAround(): void {
    if (!this.lastState) return;
    this.push({
      id: `user_ga_${this.transcript.length}`,
      simTimeSec: this.lastState.simTimeSec,
      speaker: 'captain',
      message: 'Going around.',
    });
    this.runtime.setFlag('goAroundAnnounced', true);
    this.registerInstruction(this.atc.announceGoAround(this.lastState));
  }

  /** User keys the mic for takeoff clearance. */
  requestTakeoffClearance(): void {
    if (!this.lastState) return;
    this.push({
      id: `user_req_${this.transcript.length}`,
      simTimeSec: this.lastState.simTimeSec,
      speaker: 'captain',
      message: 'Tower, Boeing 737 holding short runway 28R, ready for departure.',
    });
    const result = this.atc.requestTakeoffClearance(this.lastState);
    if ('flagsOnAccept' in result) this.registerInstruction(result);
    else this.push(result);
  }

  /** User answers a transcript line that expects a response. */
  respond(entryId: string, optionId: string): void {
    const state = this.lastState;
    const entry = this.transcript.find((e) => e.id === entryId);
    if (!entry || !state || entry.responseResult) return;
    const option = entry.expectedResponse?.options.find((o) => o.id === optionId);
    // Echo the user's spoken line into the transcript.
    if (option) {
      this.push({
        id: `user_${entryId}`,
        simTimeSec: state.simTimeSec,
        speaker: 'captain',
        message: option.text,
        relatedEventId: entryId,
      });
    }
    const instruction = this.pendingInstructions.get(entryId);
    if (instruction) {
      const { correct, followUps, flags } = this.atc.handleReadback(instruction, optionId, state);
      // Grade the transcript line the crew actually answered. A correction is
      // a separate entry from the original instruction; marking only the
      // original leaves that correction pending in the UI forever (V-07).
      entry.responseResult = correct ? 'correct' : 'incorrect';
      for (const [name, value] of Object.entries(flags)) this.runtime.setFlag(name, value);
      this.pendingInstructions.delete(entryId);
      for (const f of followUps) {
        this.push(f);
        // A "negative — read back" follow-up routes back to the same
        // instruction so the crew can correct themselves (R-20).
        if (f.expectedResponse) this.pendingInstructions.set(f.id, instruction);
      }
    } else {
      const { followUps } = this.fo.respond(entry, optionId, state);
      for (const f of followUps) this.push(f);
    }
    this.version += 1;
  }

  /** Crew answers the active item of a checklist (validated against state). */
  answerChecklistItem(checklistId: string): void {
    this.runtime.answerChecklistItem(checklistId);
    this.version += 1;
  }

  /**
   * Track raw axis inputs during before-takeoff so the "flight controls —
   * checked" item can be validated from real control movement.
   */
  notifyAxisInput(axis: 'pitch' | 'roll' | 'yaw', valueNorm: number): void {
    // Valid wherever the Before Takeoff checklist may be run — in a gate-to-gate
    // scenario the crew checks the controls while holding short, not in a phase
    // that happens to be called 'before_takeoff'.
    if (!this.runtime.isChecklistAvailable('before_takeoff')) return;
    const before = this.flightControlProgressMask();
    if (axis === 'roll') {
      this.axisExtremes.rollMin = Math.min(this.axisExtremes.rollMin, valueNorm);
      this.axisExtremes.rollMax = Math.max(this.axisExtremes.rollMax, valueNorm);
    } else if (axis === 'pitch') {
      this.axisExtremes.pitchMin = Math.min(this.axisExtremes.pitchMin, valueNorm);
      this.axisExtremes.pitchMax = Math.max(this.axisExtremes.pitchMax, valueNorm);
    } else {
      this.axisExtremes.yawMin = Math.min(this.axisExtremes.yawMin, valueNorm);
      this.axisExtremes.yawMax = Math.max(this.axisExtremes.yawMax, valueNorm);
    }
    // The hint asks for rudder too, so the check must require it (R-18).
    const progress = this.flightControlCheckProgress;
    if (Object.values(progress).every(Boolean)) {
      this.runtime.setFlag('flightControlCheckDone', true);
    }
    if (this.flightControlProgressMask() !== before) this.version += 1;
  }

  private flightControlProgressMask(): number {
    return Object.values(this.flightControlCheckProgress).reduce(
      (mask, complete, index) => mask | (complete ? 1 << index : 0),
      0,
    );
  }

  /** Structured report; meaningful once the scenario is complete (spec §16). */
  debrief(): DebriefReport {
    return generateDebrief({
      events: this.runtime.events,
      history: this.runtime.history,
      transcript: this.transcript,
      atcStats: this.atc.stats,
      grossWeightLb: this.scenario.initialState.grossWeightLb,
      runway: this.atcRunway(),
      expectedChecklistIds: this.scenario.checklists.map((c) => c.id),
      // Scenarios that begin established on final have no takeoff to score.
      expectTakeoff: this.scenario.initialState.startAt !== 'final_approach',
    });
  }

  private atcRunway() {
    const runway = getRunway(
      this.scenario.initialState.airportIcao,
      this.scenario.initialState.runwayId,
    );
    if (!runway) throw new Error('scenario runway not found');
    return runway;
  }

  private onScenarioEvent(event: ScenarioEvent): void {
    // A rule may demand a failure; the aircraft applies it, not the engine.
    const failure = event.data?.['injectFailure'];
    if (typeof failure === 'string') {
      this.injectScenarioFailure(failure as FailureKind, event);
    }
    if (event.kind === 'checklist_completed') {
      // `after_landing` → `afterLandingChecklistComplete`, so scenarios can
      // gate a phase on any checklist without engine changes.
      const camel = event.id.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
      this.runtime.setFlag(`${camel}ChecklistComplete`, true);
    }
    for (const line of this.fo.onScenarioEvent(event)) this.push(line);
    this.version += 1;
  }

  private injectScenarioFailure(failure: FailureKind, source: ScenarioEvent): void {
    let result: void | CommandResult | Promise<CommandResult>;
    try {
      result = this.sendCommand({ type: 'inject_failure', failure });
    } catch (error) {
      this.recordFailureInjectionFailure(failure, source, String(error));
      return;
    }
    if (result === undefined) return;
    void Promise.resolve(result)
      .then((ack) => {
        if (!ack.ok) this.recordFailureInjectionFailure(failure, source, ack.error);
      })
      .catch((error: unknown) =>
        this.recordFailureInjectionFailure(failure, source, String(error)),
      );
  }

  private recordFailureInjectionFailure(
    failure: FailureKind,
    source: ScenarioEvent,
    error: string,
  ): void {
    this.runtime.recordEvent({
      kind: 'milestone',
      simTimeSec: this.lastState?.simTimeSec ?? source.simTimeSec,
      id: `failure_injection_failed:${source.id}`,
      message: `Aircraft rejected ${failure}: ${error}`,
      severity: 'safety_critical',
      data: { failure, sourceEventId: source.id },
    });
  }

  private registerInstruction(instruction: AtcInstruction): void {
    this.pendingInstructions.set(instruction.id, instruction);
    this.push(instruction.transcriptEntry);
  }

  /**
   * FO callouts that represent a real deviation become scenario events, so the
   * debrief scores them instead of leaving them buried in the transcript.
   */
  private recordFoSafetyEvent(line: TranscriptEntry, state: AircraftState): void {
    const safety = line.relatedEventId ? FO_SAFETY_EVENTS[line.relatedEventId] : undefined;
    if (!safety || !line.relatedEventId) return;
    this.runtime.recordEvent({
      kind: 'rule_fired',
      simTimeSec: state.simTimeSec,
      id: line.relatedEventId,
      message: safety.message,
      severity: safety.severity,
    });
  }

  private push(entry: TranscriptEntry): void {
    this.transcript.push(entry);
    this.version += 1;
  }
}
