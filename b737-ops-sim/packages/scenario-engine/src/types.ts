import type { ScenarioInitialState } from '@b737/shared';
import type { Condition } from './conditions.js';

/** Data-driven scenario definition (spec §11). Authoring: SCENARIO_AUTHORING.md. */

export interface ScenarioPhase {
  id: string;
  title: string;
  /** Ordered; the first transition whose condition holds wins. */
  transitions: { to: string; when: Condition; eventId?: string }[];
  /** Rules that may fire (once) while this phase is active. */
  ruleIds?: string[];
}

/**
 * A monitor rule: when `when` holds while the rule is armed, an event fires.
 * Used for violations, warnings and milestone detection. `once` rules disarm
 * after firing.
 */
export interface ScenarioRule {
  id: string;
  when: Condition;
  /** Restrict to specific phases; omit = active in every phase. */
  phases?: string[];
  once?: boolean;
  severity: 'info' | 'advisory' | 'deviation' | 'safety_critical';
  message: string;
}

export type ChecklistCrew = 'captain' | 'first_officer';

export interface ChecklistItemDefinition {
  id: string;
  challenge: string;
  /** Static expected response, e.g. "Checked". */
  response?: string;
  /** Dynamic response read from state, e.g. flap detent. */
  dynamicResponseProp?: string;
  /**
   * Item is complete only when this holds (spec §14). Omit for items that
   * cannot be validated from state — they complete on crew confirmation and
   * MUST carry `manualReason` documenting why.
   */
  validation?: Condition;
  manualReason?: string;
  responsibleCrew: ChecklistCrew;
  /** May the user delegate the action to the first officer? */
  delegable?: boolean;
  trainingHint?: string;
  failureMessage?: string;
  sourceReference: string;
}

export interface ChecklistDefinition {
  id: string;
  title: string;
  items: ChecklistItemDefinition[];
  /**
   * Phases in which this checklist may be actioned. Omit = any phase.
   * Without it the crew could complete the Landing and After Landing
   * checklists while still holding short (R-10).
   */
  allowedPhaseIds?: string[];
}

export interface ScenarioDefinition {
  id: string;
  title: string;
  aircraft: string;
  description: string;
  initialState: ScenarioInitialState;
  phases: ScenarioPhase[];
  initialPhaseId: string;
  rules: ScenarioRule[];
  checklists: ChecklistDefinition[];
  /** Phase id that marks scenario completion. */
  completionPhaseId: string;
}

// ------------------------------------------------------------------ run events

export type ScenarioEventKind =
  | 'phase_transition'
  | 'rule_fired'
  | 'checklist_item_completed'
  | 'checklist_item_failed'
  | 'checklist_completed'
  | 'flag_changed'
  | 'milestone';

export interface ScenarioEvent {
  kind: ScenarioEventKind;
  simTimeSec: number;
  id: string;
  message: string;
  severity: 'info' | 'advisory' | 'deviation' | 'safety_critical';
  data?: Record<string, unknown>;
}

/** Downsampled state history entry kept for the debrief (spec §16). */
export interface HistorySample {
  simTimeSec: number;
  iasKt: number;
  altitudeFtMsl: number;
  radioAltitudeFt: number;
  verticalSpeedFpm: number;
  headingDegMag: number;
  pitchDeg: number;
  rollDeg: number;
  locDeviationDots: number | null;
  gsDeviationDots: number | null;
  latDeg: number;
  lonDeg: number;
  weightOnWheels: boolean;
  flapHandleDetent: number;
  gearLeverDown: boolean;
  /** Actual surface/gear positions — the debrief scores these, not the levers (R-18). */
  flapsActualNorm: number;
  gearPositionNorm: number;
  spoilersDeployedNorm: number;
  n1AvgPct: number;
  phaseId: string;
}
