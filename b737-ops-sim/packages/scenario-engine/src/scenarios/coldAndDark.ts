import type { ChecklistDefinition, ScenarioDefinition, ScenarioPhase } from '../types.js';
import { GATE_TO_GATE_SCENARIO } from './gateToGate.js';

const SOURCE =
  'NON_CERTIFIED_APPROXIMATION — replace from legally obtained references (SOURCE_REQUIRED)';

/**
 * Cold-and-dark scenario (spec §22 Phase 4).
 *
 * Find the aeroplane with everything off and bring it to life: battery, APU,
 * generator, IRS alignment, fuel pumps, both engines on APU bleed, then hand
 * over to the gate-to-gate flow for the taxi out.
 *
 * Every phase transition is a systems fact (`systems.*` in the state), not a
 * button press, so the crew can only advance by actually configuring the
 * aeroplane.
 */

/** Everything from the taxi out onwards is reused from gate-to-gate. */
const REUSED_PHASE_IDS = GATE_TO_GATE_SCENARIO.phases
  .map((p) => p.id)
  .filter((id) => id !== 'preflight');

const reusedPhases: ScenarioPhase[] = GATE_TO_GATE_SCENARIO.phases.filter((p) =>
  REUSED_PHASE_IDS.includes(p.id),
);

const PREFLIGHT: ChecklistDefinition = {
  id: 'preflight',
  title: 'Preflight',
  allowedPhaseIds: ['cold_and_dark', 'power_on'],
  items: [
    {
      id: 'battery',
      challenge: 'Battery',
      response: 'On',
      validation: { prop: 'systems.electrical.batterySwitchOn', op: 'eq', value: true },
      responsibleCrew: 'captain',
      trainingHint: 'Battery switch on the overhead panel brings up the DC bus.',
      failureMessage: 'Battery switch is off',
      sourceReference: SOURCE,
    },
    {
      id: 'standby_power',
      challenge: 'Standby power',
      response: 'On',
      validation: { prop: 'systems.electrical.standbyPowerOn', op: 'eq', value: true },
      responsibleCrew: 'first_officer',
      failureMessage: 'Standby power is off',
      sourceReference: SOURCE,
    },
    {
      id: 'irs',
      challenge: 'IRS',
      response: 'Aligning or aligned',
      validation: {
        all: [
          { prop: 'systems.irs.leftState', op: 'neq', value: 'off' },
          { prop: 'systems.irs.rightState', op: 'neq', value: 'off' },
        ],
      },
      responsibleCrew: 'first_officer',
      trainingHint: 'Both IRS units to NAV — alignment takes time, start it early.',
      failureMessage: 'An IRS unit is still off',
      sourceReference: SOURCE,
    },
  ],
};

const BEFORE_START: ChecklistDefinition = {
  id: 'before_start_systems',
  title: 'Before Start (systems)',
  allowedPhaseIds: ['apu_available'],
  items: [
    {
      id: 'apu_generator',
      challenge: 'APU generator',
      response: 'On bus',
      validation: { prop: 'systems.electrical.acBus1Powered', op: 'eq', value: true },
      responsibleCrew: 'first_officer',
      failureMessage: 'The AC buses are not powered',
      sourceReference: SOURCE,
    },
    {
      id: 'fuel_pumps',
      challenge: 'Fuel pumps',
      response: 'On, pressurised',
      validation: { prop: 'systems.fuel.pressurised', op: 'eq', value: true },
      responsibleCrew: 'first_officer',
      trainingHint: 'Main tank pumps on; they need AC power to build pressure.',
      failureMessage: 'No fuel pressure',
      sourceReference: SOURCE,
    },
    {
      id: 'packs_off',
      challenge: 'Packs',
      response: 'Off for start',
      validation: {
        all: [
          { prop: 'systems.pneumatic.packLeftOn', op: 'eq', value: false },
          { prop: 'systems.pneumatic.packRightOn', op: 'eq', value: false },
        ],
      },
      responsibleCrew: 'first_officer',
      trainingHint: 'The packs take air the starter needs — off for an APU-bleed start.',
      failureMessage: 'A pack is still on: the duct pressure will not support a start',
      sourceReference: SOURCE,
    },
    {
      id: 'apu_bleed',
      challenge: 'APU bleed',
      response: 'On, duct pressure',
      validation: { prop: 'systems.pneumatic.ductPressurePsi', op: 'gte', value: 25 },
      responsibleCrew: 'first_officer',
      failureMessage: 'Not enough duct pressure to motor a starter',
      sourceReference: SOURCE,
    },
  ],
};

const AFTER_START: ChecklistDefinition = {
  id: 'after_start',
  title: 'After Start',
  allowedPhaseIds: ['after_start', 'ready_to_taxi'],
  items: [
    {
      id: 'generators',
      challenge: 'Generators',
      response: 'Both on',
      validation: {
        all: [
          { prop: 'systems.electrical.gen1On', op: 'eq', value: true },
          { prop: 'systems.electrical.gen2On', op: 'eq', value: true },
        ],
      },
      responsibleCrew: 'first_officer',
      failureMessage: 'An engine generator is not on the bus',
      sourceReference: SOURCE,
    },
    {
      id: 'apu_bleed_off',
      challenge: 'APU bleed',
      response: 'Off',
      validation: { prop: 'systems.apu.bleedOn', op: 'eq', value: false },
      responsibleCrew: 'first_officer',
      failureMessage: 'APU bleed is still on',
      sourceReference: SOURCE,
    },
    {
      id: 'packs_on',
      challenge: 'Packs',
      response: 'On',
      validation: {
        all: [
          { prop: 'systems.pneumatic.packLeftOn', op: 'eq', value: true },
          { prop: 'systems.pneumatic.packRightOn', op: 'eq', value: true },
        ],
      },
      responsibleCrew: 'first_officer',
      failureMessage: 'A pack is off',
      sourceReference: SOURCE,
    },
    {
      id: 'hydraulics',
      challenge: 'Hydraulics',
      response: 'Pressurised',
      validation: {
        all: [
          { prop: 'systems.hydraulic.systemAPressurePsi', op: 'gte', value: 2500 },
          { prop: 'systems.hydraulic.systemBPressurePsi', op: 'gte', value: 2500 },
        ],
      },
      responsibleCrew: 'first_officer',
      trainingHint: 'Engine-driven pumps on both systems, electric pumps as required.',
      failureMessage: 'A hydraulic system is not pressurised',
      sourceReference: SOURCE,
    },
  ],
};

export const COLD_AND_DARK_SCENARIO: ScenarioDefinition = {
  id: 'cold_and_dark_ksfo_01',
  title: 'Cold and Dark — KSFO',
  aircraft: 'b737-800',
  description:
    'The aeroplane is at the stand with everything off. Power it up, start the ' +
    'APU, align the IRS, start both engines on APU bleed and configure the ' +
    'systems for taxi.',
  initialState: {
    ...GATE_TO_GATE_SCENARIO.initialState,
    coldAndDark: true,
  },
  initialPhaseId: 'cold_and_dark',
  completionPhaseId: 'debrief',
  phases: [
    {
      id: 'cold_and_dark',
      title: 'Cold and dark',
      transitions: [
        {
          to: 'power_on',
          when: { prop: 'systems.electrical.dcBusPowered', op: 'eq', value: true },
          eventId: 'dc_power_on',
        },
      ],
    },
    {
      id: 'power_on',
      title: 'Powered up',
      transitions: [
        {
          to: 'apu_available',
          when: { prop: 'systems.apu.state', op: 'eq', value: 'running' },
          eventId: 'apu_running',
        },
      ],
    },
    {
      id: 'apu_available',
      title: 'APU available',
      transitions: [
        {
          // The Before Start checklist is what clears the crew to start.
          to: 'engine_start',
          when: { prop: 'flags.beforeStartSystemsChecklistComplete', op: 'eq', value: true },
          eventId: 'cleared_to_start',
        },
      ],
    },
    {
      id: 'engine_start',
      title: 'Engine start',
      transitions: [
        {
          to: 'after_start',
          when: {
            all: [
              { prop: 'systems.engines.left.running', op: 'eq', value: true },
              { prop: 'systems.engines.right.running', op: 'eq', value: true },
            ],
          },
          eventId: 'both_engines_running',
        },
      ],
    },
    {
      id: 'after_start',
      title: 'After start',
      transitions: [
        {
          to: 'ready_to_taxi',
          when: { prop: 'flags.afterStartChecklistComplete', op: 'eq', value: true },
          eventId: 'ready_to_taxi',
        },
      ],
    },
    {
      id: 'ready_to_taxi',
      title: 'Ready to taxi',
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
    ...reusedPhases,
  ],
  rules: [
    ...GATE_TO_GATE_SCENARIO.rules.filter((r) => r.id !== 'taxi_without_clearance'),
    {
      id: 'engine_start_without_duct_pressure',
      when: {
        all: [
          { prop: 'systems.engines.left.startValveOpen', op: 'eq', value: true },
          { prop: 'systems.pneumatic.ductPressurePsi', op: 'lt', value: 25 },
        ],
      },
      phases: ['engine_start'],
      severity: 'deviation',
      message: 'Starter motored without adequate duct pressure',
    },
    {
      id: 'taxi_without_hydraulics',
      when: {
        all: [
          { prop: 'speeds.gsKt', op: 'gt', value: 5 },
          { prop: 'systems.hydraulic.systemAPressurePsi', op: 'lt', value: 1500 },
          { prop: 'systems.hydraulic.systemBPressurePsi', op: 'lt', value: 1500 },
        ],
      },
      phases: ['taxi_out'],
      severity: 'safety_critical',
      message: 'Taxied with no hydraulic system pressurised',
    },
    {
      id: 'master_warning_active',
      when: { prop: 'systems.masterWarning', op: 'eq', value: true, sustainedSec: 3 },
      severity: 'deviation',
      message: 'Master warning left unaddressed',
      once: false,
    },
  ],
  checklists: [PREFLIGHT, BEFORE_START, AFTER_START, ...GATE_TO_GATE_SCENARIO.checklists],
};
