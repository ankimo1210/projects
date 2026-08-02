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
  private axisExtremes = { rollMin: 0, rollMax: 0, pitchMin: 0, pitchMax: 0 };
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
    this.atc = new AtcController(runway);
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
    for (const line of this.fo.update(state, this.runtime.phaseId)) this.push(line);
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
      for (const f of followUps) this.push(f);
      this.pendingInstructions.delete(entryId);
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
    }
    const e = this.axisExtremes;
    if (e.rollMin < -0.85 && e.rollMax > 0.85 && e.pitchMin < -0.85 && e.pitchMax > 0.85) {
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

  private push(entry: TranscriptEntry): void {
    this.transcript.push(entry);
    this.version += 1;
  }
}
