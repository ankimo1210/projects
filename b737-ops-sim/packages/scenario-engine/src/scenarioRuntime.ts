import type { AircraftState } from '@b737/shared';
import { ConditionEvaluator, type EvaluationContext } from './conditions.js';
import { ChecklistRun } from './checklist.js';
import type { HistorySample, ScenarioDefinition, ScenarioEvent, ScenarioPhase } from './types.js';

export type ScenarioEventListener = (event: ScenarioEvent) => void;

/**
 * Deterministic scenario phase machine (spec §11). Consumes the live state
 * stream, advances phases from real aircraft state, fires monitor rules, and
 * accumulates the event log + downsampled history used by the debrief.
 */
export class ScenarioRuntime {
  readonly evaluator = new ConditionEvaluator();
  private currentPhase: ScenarioPhase;
  private flags: Record<string, boolean | number | string> = {};
  private firedRuleIds = new Set<string>();
  readonly events: ScenarioEvent[] = [];
  readonly history: HistorySample[] = [];
  private listeners = new Set<ScenarioEventListener>();
  private lastHistoryAtSec = -Infinity;
  private lastState: AircraftState | null = null;
  readonly checklistRuns = new Map<string, ChecklistRun>();

  constructor(readonly definition: ScenarioDefinition) {
    const initial = definition.phases.find((p) => p.id === definition.initialPhaseId);
    if (!initial) throw new Error(`initial phase '${definition.initialPhaseId}' not found`);
    this.currentPhase = initial;
    for (const checklist of definition.checklists) {
      this.checklistRuns.set(checklist.id, new ChecklistRun(checklist, this.evaluator));
    }
  }

  get phaseId(): string {
    return this.currentPhase.id;
  }

  get complete(): boolean {
    return this.currentPhase.id === this.definition.completionPhaseId;
  }

  get state(): AircraftState | null {
    return this.lastState;
  }

  onEvent(listener: ScenarioEventListener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  getFlag(name: string): boolean | number | string | undefined {
    return this.flags[name];
  }

  setFlag(name: string, value: boolean | number | string): void {
    if (this.flags[name] === value) return;
    this.flags[name] = value;
    this.emit({
      kind: 'flag_changed',
      simTimeSec: this.lastState?.simTimeSec ?? 0,
      id: `flag:${name}`,
      message: `${name} = ${String(value)}`,
      severity: 'info',
      data: { name, value },
    });
  }

  context(state: AircraftState): EvaluationContext {
    return { state, flags: this.flags, derived: this.evaluator.derived(state) };
  }

  /** Feed one state sample. Returns events emitted during this update. */
  update(state: AircraftState): ScenarioEvent[] {
    const before = this.events.length;
    this.lastState = state;
    this.evaluator.observe(state);
    const ctx = this.context(state);

    for (const run of this.checklistRuns.values()) run.observe(ctx);

    // Monitor rules active in the current phase.
    for (const rule of this.definition.rules) {
      if (rule.phases && !rule.phases.includes(this.currentPhase.id)) continue;
      if (rule.once !== false && this.firedRuleIds.has(rule.id)) continue;
      if (this.evaluator.evaluate(rule.when, ctx)) {
        this.firedRuleIds.add(rule.id);
        this.emit({
          kind: 'rule_fired',
          simTimeSec: state.simTimeSec,
          id: rule.id,
          message: rule.message,
          severity: rule.severity,
        });
      }
    }

    // Phase transitions: first matching wins; allow chained transitions in
    // one tick only via successive updates (keeps behavior observable).
    for (const transition of this.currentPhase.transitions) {
      if (this.evaluator.evaluate(transition.when, ctx)) {
        const next = this.definition.phases.find((p) => p.id === transition.to);
        if (!next) throw new Error(`transition to unknown phase '${transition.to}'`);
        const from = this.currentPhase.id;
        this.currentPhase = next;
        this.emit({
          kind: 'phase_transition',
          simTimeSec: state.simTimeSec,
          id: transition.eventId ?? `phase:${next.id}`,
          message: `${from} → ${next.id}`,
          severity: 'info',
          data: { from, to: next.id },
        });
        break;
      }
    }

    // Downsampled history at 2 Hz for the debrief.
    if (state.simTimeSec - this.lastHistoryAtSec >= 0.5) {
      this.lastHistoryAtSec = state.simTimeSec;
      this.history.push({
        simTimeSec: state.simTimeSec,
        iasKt: state.speeds.iasKt,
        altitudeFtMsl: state.position.altitudeFtMsl,
        radioAltitudeFt: state.position.radioAltitudeFt,
        verticalSpeedFpm: state.speeds.verticalSpeedFpm,
        headingDegMag: state.attitude.headingDegMag,
        pitchDeg: state.attitude.pitchDeg,
        rollDeg: state.attitude.rollDeg,
        locDeviationDots: state.nav.locDeviationDots,
        gsDeviationDots: state.nav.gsDeviationDots,
        latDeg: state.position.latDeg,
        lonDeg: state.position.lonDeg,
        weightOnWheels: state.weightOnWheels,
        flapHandleDetent: state.controls.flapHandleDetent,
        gearLeverDown: state.controls.gearLeverDown,
        n1AvgPct: (state.engines.left.n1Pct + state.engines.right.n1Pct) / 2,
        phaseId: this.currentPhase.id,
      });
    }

    return this.events.slice(before);
  }

  /** Is this checklist actionable in the phase the flight is actually in? */
  isChecklistAvailable(checklistId: string): boolean {
    const run = this.checklistRuns.get(checklistId);
    if (!run) return false;
    const allowed = run.definition.allowedPhaseIds;
    return allowed === undefined || allowed.includes(this.currentPhase.id);
  }

  /** Crew answers the active item of a checklist against live state. */
  answerChecklistItem(checklistId: string): ScenarioEvent | null {
    const run = this.checklistRuns.get(checklistId);
    const state = this.lastState;
    if (!run || !state) return null;
    if (!this.isChecklistAvailable(checklistId)) {
      const event: ScenarioEvent = {
        kind: 'checklist_item_failed',
        simTimeSec: state.simTimeSec,
        id: `${checklistId}.out_of_phase`,
        message: `${run.definition.title} is not run during ${this.currentPhase.title.toLowerCase()}`,
        severity: 'deviation',
      };
      this.emit(event);
      return event;
    }
    const result = run.answerActiveItem(this.context(state));
    if (!result) return null;
    const { item, ok } = result;
    const event: ScenarioEvent = ok
      ? {
          kind: 'checklist_item_completed',
          simTimeSec: state.simTimeSec,
          id: `${checklistId}.${item.definition.id}`,
          message: `${item.definition.challenge} — ${
            item.dynamicResponseValue ?? item.definition.response ?? 'confirmed'
          }`,
          severity: 'info',
        }
      : {
          kind: 'checklist_item_failed',
          simTimeSec: state.simTimeSec,
          id: `${checklistId}.${item.definition.id}`,
          message: item.failureMessage ?? 'checklist item not satisfied',
          severity: 'deviation',
        };
    this.emit(event);
    if (ok && run.complete) {
      this.emit({
        kind: 'checklist_completed',
        simTimeSec: state.simTimeSec,
        id: checklistId,
        message: `${run.definition.title} complete`,
        severity: 'info',
      });
    }
    if (!ok) run.retryActiveItem();
    return event;
  }

  private emit(event: ScenarioEvent): void {
    this.events.push(event);
    for (const l of this.listeners) l(event);
  }
}
