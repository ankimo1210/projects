import type { ScenarioDefinition, ScenarioPhase } from '../types.js';
import { MVP_CIRCUIT_SCENARIO } from './mvpCircuit.js';

/**
 * Short approach drill (spec §22 Phase 3 "multiple scenarios").
 *
 * Starts established on the ILS at about 5 NM: one approach, the
 * stabilisation gates, the landing and the runway exit. Intended for
 * practising the approach itself — including going around — without flying
 * the whole pattern first.
 */

const REUSED_PHASE_IDS = ['final_approach', 'go_around', 'landing', 'rollout', 'runway_exit'];

const reusedPhases: ScenarioPhase[] = MVP_CIRCUIT_SCENARIO.phases
  .filter((p) => REUSED_PHASE_IDS.includes(p.id))
  .map((p) =>
    p.id === 'go_around'
      ? // No pattern to rejoin here: the drill ends after a go-around is
        // established, which is the point of the exercise.
        {
          ...p,
          transitions: [
            {
              to: 'debrief',
              when: {
                all: [
                  { prop: 'weightOnWheels' as const, op: 'eq' as const, value: false },
                  { prop: 'position.radioAltitudeFt' as const, op: 'gt' as const, value: 1500 },
                ],
              },
              eventId: 'go_around_established',
            },
          ],
        }
      : p,
  );

export const APPROACH_DRILL_SCENARIO: ScenarioDefinition = {
  id: 'approach_drill_ksfo_28r_01',
  title: 'Approach Drill — ILS 28R',
  aircraft: 'b737-800',
  description:
    'Established on the ILS for KSFO 28R at about 5 NM: configure, fly the ' +
    'stabilisation gates, land and vacate — or go around.',
  initialState: {
    ...MVP_CIRCUIT_SCENARIO.initialState,
    startAt: 'final_approach',
    flapDetent: 15,
    parkingBrakeSet: false,
  },
  initialPhaseId: 'final_approach',
  completionPhaseId: 'debrief',
  phases: [...reusedPhases, { id: 'debrief', title: 'Debrief', transitions: [] }],
  rules: MVP_CIRCUIT_SCENARIO.rules.filter(
    (r) => r.id !== 'runway_incursion' && r.id !== 'overspeed_250_below_10k',
  ),
  checklists: MVP_CIRCUIT_SCENARIO.checklists.filter((c) => c.id !== 'before_takeoff'),
};
