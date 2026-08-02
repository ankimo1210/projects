import type { ScenarioDefinition } from '../types.js';
import { MVP_CIRCUIT_SCENARIO } from './mvpCircuit.js';
import { APPROACH_DRILL_SCENARIO } from './approachDrill.js';

/**
 * Advanced training scenarios (spec §22 Phase 5): an engine failure after V1,
 * a crosswind landing, and a departure/arrival flown on the route with LNAV.
 *
 * All three reuse the circuit's phases, rules and checklists — what differs is
 * the weather, the failures and what the crew is asked to do.
 */

/**
 * Engine failure just after V1. The failure is injected by a rule when the
 * aeroplane actually reaches V1 on the runway, so it cannot be anticipated by
 * watching a clock.
 */
export const ENGINE_FAILURE_V1_SCENARIO: ScenarioDefinition = {
  ...MVP_CIRCUIT_SCENARIO,
  id: 'engine_failure_v1_ksfo_01',
  title: 'Engine Failure after V1 — KSFO 28R',
  description:
    'Engine 1 fails just after V1. Continue the takeoff, fly the single-engine ' +
    'climb-out, then return for the ILS 28R.',
  initialState: {
    ...MVP_CIRCUIT_SCENARIO.initialState,
    startAt: 'threshold',
  },
  rules: [
    ...MVP_CIRCUIT_SCENARIO.rules,
    {
      id: 'v1_cut',
      when: {
        all: [
          { prop: 'weightOnWheels', op: 'eq', value: true },
          { prop: 'speeds.iasKt', op: 'gte', value: 145 },
        ],
      },
      phases: ['takeoff_roll'],
      severity: 'safety_critical',
      message: 'Engine 1 failure after V1',
      injectFailure: 'engine_1_flameout',
    },
    {
      id: 'rejected_after_v1',
      when: {
        all: [
          { prop: 'weightOnWheels', op: 'eq', value: true },
          { prop: 'speeds.iasKt', op: 'gte', value: 145 },
          { prop: 'engines.left.throttleLeverNorm', op: 'lt', value: 0.2 },
        ],
        sustainedSec: 1,
      },
      phases: ['takeoff_roll'],
      severity: 'safety_critical',
      message: 'Takeoff rejected after V1',
    },
    {
      id: 'asymmetric_heading',
      when: {
        all: [
          { prop: 'weightOnWheels', op: 'eq', value: false },
          { prop: 'position.radioAltitudeFt', op: 'lt', value: 1000 },
          {
            prop: 'attitude.headingDegMag',
            op: 'withinDegOf',
            target: 284.4,
            toleranceDeg: 15,
          },
        ],
      },
      phases: ['initial_climb'],
      severity: 'info',
      message: 'Runway track maintained on one engine',
    },
  ],
};

/** Landing with a strong crosswind — drift, crab and centreline discipline. */
export const CROSSWIND_LANDING_SCENARIO: ScenarioDefinition = {
  ...APPROACH_DRILL_SCENARIO,
  id: 'crosswind_landing_ksfo_01',
  title: 'Crosswind Landing — ILS 28R',
  description:
    'Established on the ILS 28R with a strong, gusty crosswind from the ' +
    'south-west. Fly the approach, keep the centreline and land.',
  initialState: {
    ...APPROACH_DRILL_SCENARIO.initialState,
    // Surface wind ~40° off the runway course, gusting.
    windDirDeg: 245,
    windSpeedKt: 22,
    weather: {
      windAloftDirDeg: 235,
      windAloftSpeedKt: 38,
      gustKt: 12,
      visibilityM: 9000,
      turbulence: 0.35,
    },
  },
};

/**
 * Departure and arrival on the route: load the SID, follow it with LNAV, join
 * the arrival and hand over to the ILS.
 */
export const ROUTE_SID_STAR_SCENARIO: ScenarioDefinition = {
  ...MVP_CIRCUIT_SCENARIO,
  id: 'route_sid_star_ksfo_01',
  title: 'SID and Arrival — KSFO 28R',
  description:
    'Load the SFOUT1 departure and the BAYIN1 arrival, fly them with LNAV, ' +
    'then join the ILS 28R.',
  checklists: [
    ...MVP_CIRCUIT_SCENARIO.checklists.map((c) =>
      c.id === 'before_takeoff'
        ? {
            ...c,
            items: [
              {
                id: 'route',
                challenge: 'Route',
                response: 'Loaded',
                validation: { prop: 'fms.routeId', op: 'neq' as const, value: null },
                responsibleCrew: 'first_officer' as const,
                trainingHint: 'Load SFOUT1 / BAYIN1 in the FMS panel before departure.',
                failureMessage: 'No route is loaded',
                sourceReference: 'NON_CERTIFIED_APPROXIMATION',
              },
              ...c.items,
            ],
          }
        : c,
    ),
  ],
  rules: [
    ...MVP_CIRCUIT_SCENARIO.rules,
    {
      id: 'lnav_not_engaged',
      when: {
        all: [
          { prop: 'position.radioAltitudeFt', op: 'gt', value: 1000 },
          { prop: 'mcp.rollMode', op: 'neq', value: 'LNAV' },
        ],
        sustainedSec: 20,
      },
      phases: ['initial_climb'],
      severity: 'deviation',
      message: 'Departure flown without LNAV',
    },
    {
      id: 'route_deviation',
      // Cross-track is signed (+ = right); the DSL has no abs, so both sides
      // are spelled out (F-04: the first version only caught right deviations).
      when: {
        all: [
          { prop: 'mcp.rollMode', op: 'eq', value: 'LNAV' },
          {
            any: [
              { prop: 'fms.crossTrackNm', op: 'gt', value: 2 },
              { prop: 'fms.crossTrackNm', op: 'lt', value: -2 },
            ],
          },
        ],
        sustainedSec: 10,
      },
      phases: ['initial_climb', 'approach_setup'],
      severity: 'deviation',
      message: 'More than 2 NM off the route',
    },
  ],
};
