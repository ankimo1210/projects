import { getRunway, type AircraftState } from '@b737/shared';
import {
  ScenarioRuntime,
  type ScenarioDefinition,
  type ScenarioEvent,
} from '@b737/scenario-engine';
import { AtcController, type AtcInstruction } from './atc.js';
import { generateDebrief, type DebriefReport } from './debrief.js';
import { FirstOfficer } from './firstOfficer.js';
import type { TranscriptEntry } from './transcript.js';

export type TrainingMode = 'guided' | 'assisted' | 'evaluation';

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

  constructor(
    readonly scenario: ScenarioDefinition,
    options: { mode?: TrainingMode } = {},
  ) {
    this.mode = options.mode ?? 'guided';
    this.runtime = new ScenarioRuntime(scenario);
    this.fo = new FirstOfficer({
      grossWeightLb: scenario.initialState.grossWeightLb,
      takeoffPhaseIds: ['takeoff_roll', 'rotation'],
      approachPhaseIds: ['final_approach', 'landing'],
    });
    const runway = getRunway(scenario.initialState.airportIcao, scenario.initialState.runwayId);
    if (!runway) throw new Error('scenario runway not found');
    this.atc = new AtcController(runway, {
      dirDeg: scenario.initialState.windDirDeg,
      speedKt: scenario.initialState.windSpeedKt,
    });
    this.runtime.onEvent((event) => this.onScenarioEvent(event));
  }

  get state(): AircraftState | null {
    return this.lastState;
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
      const { followUps, flags } = this.atc.handleReadback(instruction, optionId, state);
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
    if (this.runtime.phaseId !== 'before_takeoff') return;
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
    const e = this.axisExtremes;
    const full = (min: number, max: number): boolean => min < -0.85 && max > 0.85;
    if (full(e.rollMin, e.rollMax) && full(e.pitchMin, e.pitchMax) && full(e.yawMin, e.yawMax)) {
      this.runtime.setFlag('flightControlCheckDone', true);
    }
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
    if (event.kind === 'checklist_completed' && event.id === 'after_landing') {
      this.runtime.setFlag('afterLandingChecklistComplete', true);
    }
    for (const line of this.fo.onScenarioEvent(event)) this.push(line);
    this.version += 1;
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
