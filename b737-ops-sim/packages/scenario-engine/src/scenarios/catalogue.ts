import type { ScenarioDefinition } from '../types.js';
import { MVP_CIRCUIT_SCENARIO } from './mvpCircuit.js';
import { GATE_TO_GATE_SCENARIO } from './gateToGate.js';
import { APPROACH_DRILL_SCENARIO } from './approachDrill.js';
import { COLD_AND_DARK_SCENARIO } from './coldAndDark.js';
import {
  CROSSWIND_LANDING_SCENARIO,
  ENGINE_FAILURE_V1_SCENARIO,
  ROUTE_SID_STAR_SCENARIO,
} from './advanced.js';

/**
 * Scenario catalogue (spec §22 Phase 3 "multiple scenarios"). The UI picks
 * from this list; every entry is a plain data definition, so adding one needs
 * no engine changes (SCENARIO_AUTHORING.md).
 */
export const SCENARIOS: ScenarioDefinition[] = [
  MVP_CIRCUIT_SCENARIO,
  GATE_TO_GATE_SCENARIO,
  APPROACH_DRILL_SCENARIO,
  COLD_AND_DARK_SCENARIO,
  ENGINE_FAILURE_V1_SCENARIO,
  CROSSWIND_LANDING_SCENARIO,
  ROUTE_SID_STAR_SCENARIO,
];

export const DEFAULT_SCENARIO_ID = MVP_CIRCUIT_SCENARIO.id;

export function getScenario(id: string): ScenarioDefinition | undefined {
  return SCENARIOS.find((s) => s.id === id);
}
