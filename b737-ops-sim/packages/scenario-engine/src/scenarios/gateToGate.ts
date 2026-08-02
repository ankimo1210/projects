import type { ChecklistDefinition, ScenarioDefinition, ScenarioPhase } from '../types.js';
import { MVP_CIRCUIT_SCENARIO } from './mvpCircuit.js';

const SOURCE =
  'NON_CERTIFIED_APPROXIMATION — replace from legally obtained references (SOURCE_REQUIRED)';

/**
 * Gate-to-gate scenario (spec §22 Phase 3 taxi operations).
 *
 * Start parked at the stand, obtain a taxi clearance, taxi to the holding
 * position without crossing it uncleared, fly the same circuit as
 * {@link MVP_CIRCUIT_SCENARIO}, then vacate, taxi in and park.
 *
 * The airborne phases, rules and checklists are reused from the circuit
 * scenario so there is one definition of "how the pattern is flown"; only the
 * ground phases and their rules are new.
 */

/** Airborne part reused verbatim from the circuit scenario. */
const REUSED_PHASE_IDS = [
  'line_up',
  'takeoff_roll',
  'rotation',
  'initial_climb',
  'approach_setup',
  'final_approach',
  'go_around',
  'landing',
  'rollout',
];

const reusedPhases: ScenarioPhase[] = MVP_CIRCUIT_SCENARIO.phases.filter((p) =>
  REUSED_PHASE_IDS.includes(p.id),
);

/** Checklists reused from the circuit, with the ground phases folded in. */
const reusedChecklists: ChecklistDefinition[] = MVP_CIRCUIT_SCENARIO.checklists.map((c) =>
  c.id === 'before_takeoff'
    ? { ...c, allowedPhaseIds: ['hold_short', 'before_takeoff'] }
    : c.id === 'after_landing'
      ? { ...c, allowedPhaseIds: ['runway_exit', 'taxi_in'] }
      : c,
);

const BEFORE_START: ChecklistDefinition = {
  id: 'before_start',
  title: 'Before Start',
  allowedPhaseIds: ['preflight'],
  items: [
    {
      id: 'parking_brake',
      challenge: 'Parking brake',
      response: 'Set',
      validation: { prop: 'controls.parkingBrakeSet', op: 'eq', value: true },
      responsibleCrew: 'captain',
      failureMessage: 'Parking brake is not set',
      sourceReference: SOURCE,
    },
    {
      id: 'flaps_up',
      challenge: 'Flaps',
      response: 'Up',
      validation: { prop: 'controls.flapHandleDetent', op: 'eq', value: 0 },
      responsibleCrew: 'first_officer',
      failureMessage: 'Flaps are not up for start',
      sourceReference: SOURCE,
    },
    {
      id: 'beacon',
      challenge: 'Beacon',
      response: 'On',
      validation: { prop: 'lights.beacon', op: 'eq', value: true },
      responsibleCrew: 'first_officer',
      failureMessage: 'Beacon is off',
      sourceReference: SOURCE,
    },
  ],
};

const BEFORE_TAXI: ChecklistDefinition = {
  id: 'before_taxi',
  title: 'Before Taxi',
  allowedPhaseIds: ['preflight', 'taxi_out'],
  items: [
    {
      id: 'taxi_clearance',
      challenge: 'Taxi clearance',
      response: 'Received',
      validation: { prop: 'flags.taxiClearanceReceived', op: 'eq', value: true },
      responsibleCrew: 'captain',
      failureMessage: 'No taxi clearance yet',
      sourceReference: SOURCE,
    },
    {
      id: 'taxi_light',
      challenge: 'Taxi light',
      response: 'On',
      validation: { prop: 'lights.taxi', op: 'eq', value: true },
      responsibleCrew: 'first_officer',
      failureMessage: 'Taxi light is off',
      sourceReference: SOURCE,
    },
    {
      id: 'flaps_takeoff',
      challenge: 'Flaps',
      response: 'Set for takeoff',
      dynamicResponseProp: 'controls.flapHandleDetent',
      validation: {
        all: [
          { prop: 'controls.flapHandleDetent', op: 'eq', value: 5 },
          { prop: 'controls.flapsActualNorm', op: 'between', min: 0.36, max: 0.39 },
        ],
      },
      responsibleCrew: 'first_officer',
      failureMessage: 'Takeoff flaps are not set',
      sourceReference: SOURCE,
    },
    {
      id: 'parking_brake_released',
      challenge: 'Parking brake',
      response: 'Released',
      validation: { prop: 'controls.parkingBrakeSet', op: 'eq', value: false },
      responsibleCrew: 'captain',
      failureMessage: 'Parking brake is still set',
      sourceReference: SOURCE,
    },
  ],
};

const SHUTDOWN: ChecklistDefinition = {
  id: 'shutdown',
  title: 'Shutdown',
  allowedPhaseIds: ['parked'],
  items: [
    {
      id: 'parking_brake_set',
      challenge: 'Parking brake',
      response: 'Set',
      validation: { prop: 'controls.parkingBrakeSet', op: 'eq', value: true },
      responsibleCrew: 'captain',
      failureMessage: 'Parking brake is not set at the stand',
      sourceReference: SOURCE,
    },
    {
      id: 'thrust_idle',
      challenge: 'Thrust levers',
      response: 'Idle',
      validation: { prop: 'engines.left.throttleLeverNorm', op: 'lt', value: 0.05 },
      responsibleCrew: 'captain',
      failureMessage: 'Thrust levers are not closed',
      sourceReference: SOURCE,
    },
    {
      id: 'exterior_lights_off',
      challenge: 'Exterior lights',
      response: 'Off',
      validation: {
        all: [
          { prop: 'lights.taxi', op: 'eq', value: false },
          { prop: 'lights.landing', op: 'eq', value: false },
          { prop: 'lights.strobe', op: 'eq', value: false },
        ],
      },
      responsibleCrew: 'first_officer',
      failureMessage: 'Exterior lights are still on',
      sourceReference: SOURCE,
    },
  ],
};

export const GATE_TO_GATE_SCENARIO: ScenarioDefinition = {
  id: 'gate_to_gate_ksfo_01',
  title: 'Gate to Gate — KSFO 28R',
  aircraft: 'b737-800',
  description:
    'Start at the stand, obtain a taxi clearance, taxi to runway 28R holding ' +
    'short, fly the ILS circuit, vacate the runway, taxi back to the stand ' +
    'and complete the Shutdown checklist.',
  initialState: {
    ...MVP_CIRCUIT_SCENARIO.initialState,
    startAt: 'stand',
    flapDetent: 0,
    parkingBrakeSet: true,
  },
  initialPhaseId: 'preflight',
  completionPhaseId: 'debrief',
  phases: [
    {
      id: 'preflight',
      title: 'At the stand',
      transitions: [
        {
          to: 'taxi_out',
          when: {
            all: [
              { prop: 'flags.taxiClearanceReceived', op: 'eq', value: true },
              { prop: 'speeds.gsKt', op: 'gt', value: 2 },
            ],
          },
          eventId: 'taxi_started',
        },
      ],
    },
    {
      id: 'taxi_out',
      title: 'Taxi out',
      transitions: [
        {
          // Stopped at the holding position — geometry, not a button (D6).
          to: 'hold_short',
          when: {
            all: [
              { prop: 'derived.distanceToHoldShortM', op: 'lt', value: 60 },
              { prop: 'derived.pastHoldShort', op: 'eq', value: false },
              { prop: 'speeds.gsKt', op: 'lt', value: 5 },
            ],
            sustainedSec: 1,
          },
          eventId: 'holding_short',
        },
      ],
    },
    {
      id: 'hold_short',
      title: 'Holding short',
      transitions: [
        {
          to: 'before_takeoff',
          when: { prop: 'flags.takeoffClearanceReceived', op: 'eq', value: true },
        },
      ],
    },
    {
      id: 'before_takeoff',
      title: 'Before takeoff',
      transitions: [
        {
          to: 'line_up',
          when: {
            all: [
              { prop: 'flags.takeoffClearanceReceived', op: 'eq', value: true },
              { prop: 'speeds.gsKt', op: 'gt', value: 3 },
            ],
          },
        },
      ],
    },
    ...reusedPhases,
    {
      id: 'runway_exit',
      title: 'Clear of the runway',
      transitions: [
        {
          to: 'taxi_in',
          when: {
            all: [
              { prop: 'flags.afterLandingChecklistComplete', op: 'eq', value: true },
              { prop: 'derived.onRunwaySurface', op: 'eq', value: false },
            ],
          },
          eventId: 'taxi_in_started',
        },
      ],
    },
    {
      id: 'taxi_in',
      title: 'Taxi in',
      transitions: [
        {
          to: 'parked',
          when: {
            all: [
              { prop: 'derived.distanceToStandM', op: 'lt', value: 30 },
              { prop: 'speeds.gsKt', op: 'lt', value: 1 },
            ],
            sustainedSec: 1,
          },
          eventId: 'parked_at_stand',
        },
      ],
    },
    {
      id: 'parked',
      title: 'Parked',
      transitions: [
        {
          to: 'debrief',
          when: { prop: 'flags.shutdownChecklistComplete', op: 'eq', value: true },
        },
      ],
    },
    { id: 'debrief', title: 'Debrief', transitions: [] },
  ],
  rules: [
    ...MVP_CIRCUIT_SCENARIO.rules.filter((r) => r.id !== 'runway_incursion'),
    {
      id: 'runway_incursion',
      when: {
        all: [
          { prop: 'flags.takeoffClearanceReceived', op: 'neq', value: true },
          { prop: 'derived.pastHoldShort', op: 'eq', value: true },
          { prop: 'weightOnWheels', op: 'eq', value: true },
        ],
      },
      phases: ['preflight', 'taxi_out', 'hold_short'],
      severity: 'safety_critical',
      message: 'Crossed the runway holding position without a takeoff clearance',
    },
    {
      id: 'taxi_without_clearance',
      when: {
        all: [
          { prop: 'flags.taxiClearanceReceived', op: 'neq', value: true },
          { prop: 'speeds.gsKt', op: 'gt', value: 5 },
        ],
      },
      phases: ['preflight'],
      severity: 'deviation',
      message: 'Started taxiing before the taxi clearance',
    },
    {
      id: 'taxi_overspeed',
      when: { prop: 'speeds.gsKt', op: 'gt', value: 25, sustainedSec: 3 },
      phases: ['taxi_out', 'taxi_in'],
      severity: 'deviation',
      message: 'Taxi speed above 25 kt',
      once: false,
    },
    {
      id: 'taxi_off_surface',
      when: {
        all: [
          { prop: 'weightOnWheels', op: 'eq', value: true },
          { prop: 'derived.onTaxiSurface', op: 'eq', value: false },
          { prop: 'derived.onRunwaySurface', op: 'eq', value: false },
          { prop: 'speeds.gsKt', op: 'gt', value: 3 },
        ],
        sustainedSec: 3,
      },
      phases: ['taxi_out', 'taxi_in'],
      severity: 'deviation',
      message: 'Taxied off the paved surface',
    },
  ],
  checklists: [BEFORE_START, BEFORE_TAXI, ...reusedChecklists, SHUTDOWN],
};
