import type { ScenarioDefinition } from '../types.js';

const SOURCE =
  'NON_CERTIFIED_APPROXIMATION — replace from legally obtained references (SOURCE_REQUIRED)';

/**
 * MVP scenario (spec §20): engines running near KSFO 28R, takeoff, right
 * pattern via ATC vectors, ILS 28R, landing, rollout, runway exit, debrief.
 * All checklist content is a training approximation, marked per item.
 */
export const MVP_CIRCUIT_SCENARIO: ScenarioDefinition = {
  id: 'circuit_takeoff_ils_landing_01',
  title: 'Takeoff and ILS Landing — KSFO 28R',
  aircraft: 'b737-800',
  description:
    'Complete the Before Takeoff checklist, obtain clearance, take off from ' +
    'KSFO 28R, fly ATC vectors around a right-hand pattern, capture the ILS, ' +
    'land, roll out, exit the runway and complete the After Landing checklist.',
  initialState: {
    seed: 737800,
    airportIcao: 'KSFO',
    runwayId: '28R',
    startAt: 'holding_point',
    flapDetent: 5,
    parkingBrakeSet: true,
    grossWeightLb: 145000,
    windDirDeg: 290,
    windSpeedKt: 6,
  },
  initialPhaseId: 'before_takeoff',
  completionPhaseId: 'debrief',
  phases: [
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
    {
      id: 'line_up',
      title: 'Line up',
      transitions: [{ to: 'takeoff_roll', when: { prop: 'speeds.gsKt', op: 'gt', value: 40 } }],
    },
    {
      id: 'takeoff_roll',
      title: 'Takeoff roll',
      transitions: [
        {
          to: 'rotation',
          when: {
            all: [
              { prop: 'attitude.pitchDeg', op: 'gt', value: 2.5 },
              { prop: 'speeds.iasKt', op: 'gt', value: 100 },
            ],
          },
        },
      ],
    },
    {
      id: 'rotation',
      title: 'Rotation',
      transitions: [
        {
          to: 'initial_climb',
          when: {
            all: [
              { prop: 'weightOnWheels', op: 'eq', value: false },
              { prop: 'speeds.verticalSpeedFpm', op: 'gt', value: 300 },
              { prop: 'derived.radioAltitudeTrend', op: 'eq', value: 'increasing' },
            ],
          },
          eventId: 'positive_rate',
        },
      ],
    },
    {
      id: 'initial_climb',
      title: 'Initial climb / pattern',
      transitions: [
        {
          to: 'approach_setup',
          when: { prop: 'flags.approachClearanceReceived', op: 'eq', value: true },
        },
      ],
    },
    {
      id: 'approach_setup',
      title: 'Approach setup',
      setFlagsOnEnter: { goAroundAnnounced: false },
      transitions: [
        {
          to: 'final_approach',
          when: {
            all: [
              { prop: 'nav.locDeviationDots', op: 'between', min: -1, max: 1 },
              { prop: 'position.radioAltitudeFt', op: 'lt', value: 2500 },
              {
                prop: 'attitude.headingDegMag',
                op: 'withinDegOf',
                target: 284.4,
                toleranceDeg: 30,
              },
            ],
          },
          eventId: 'established_on_approach',
        },
      ],
    },
    {
      id: 'final_approach',
      title: 'Final approach',
      transitions: [
        // The crew's go-around call wins over continuing the approach.
        { to: 'go_around', when: { prop: 'flags.goAroundAnnounced', op: 'eq', value: true } },
        {
          to: 'landing',
          when: { prop: 'position.radioAltitudeFt', op: 'lt', value: 60 },
        },
      ],
    },
    {
      id: 'go_around',
      title: 'Go around',
      // The approach is flown again from scratch once re-established.
      resetChecklistIds: ['landing'],
      transitions: [
        {
          to: 'approach_setup',
          when: {
            all: [
              { prop: 'weightOnWheels', op: 'eq', value: false },
              { prop: 'position.radioAltitudeFt', op: 'gt', value: 1500 },
            ],
          },
          eventId: 'go_around_established',
        },
      ],
      setFlagsOnEnter: { goAroundFlown: true },
    },
    {
      id: 'landing',
      title: 'Landing',
      transitions: [
        {
          to: 'go_around',
          when: {
            all: [
              { prop: 'flags.goAroundAnnounced', op: 'eq', value: true },
              { prop: 'weightOnWheels', op: 'eq', value: false },
            ],
          },
        },
        {
          // Decelerated to taxi speed — still ON the runway.
          to: 'rollout',
          when: {
            all: [
              { prop: 'weightOnWheels', op: 'eq', value: true },
              { prop: 'speeds.gsKt', op: 'lt', value: 30 },
            ],
          },
          eventId: 'rollout_complete',
        },
      ],
    },
    {
      id: 'rollout',
      title: 'Rollout / vacate',
      transitions: [
        {
          // Geometrically clear of the paved surface, not merely slow (R-08).
          to: 'runway_exit',
          when: {
            all: [
              { prop: 'weightOnWheels', op: 'eq', value: true },
              { prop: 'derived.onRunwaySurface', op: 'eq', value: false },
              { prop: 'speeds.gsKt', op: 'lt', value: 30 },
            ],
            sustainedSec: 1,
          },
          eventId: 'runway_exited',
        },
      ],
    },
    {
      id: 'runway_exit',
      title: 'Clear of the runway',
      transitions: [
        {
          to: 'debrief',
          when: {
            all: [
              { prop: 'flags.afterLandingChecklistComplete', op: 'eq', value: true },
              { prop: 'speeds.gsKt', op: 'lt', value: 20 },
            ],
          },
        },
      ],
    },
    { id: 'debrief', title: 'Debrief', transitions: [] },
  ],
  rules: [
    {
      id: 'runway_incursion',
      // Being on the paved surface without a clearance is the violation —
      // ground speed is not a proxy for position (R-08).
      when: {
        all: [
          { prop: 'flags.takeoffClearanceReceived', op: 'neq', value: true },
          { prop: 'derived.enteredRunwaySurface', op: 'eq', value: true },
        ],
      },
      phases: ['before_takeoff'],
      severity: 'safety_critical',
      message: 'Entered the runway without takeoff clearance',
    },
    {
      id: 'landed_without_clearance',
      when: {
        all: [
          { prop: 'weightOnWheels', op: 'eq', value: true },
          { prop: 'flags.landingClearanceReceived', op: 'neq', value: true },
        ],
      },
      phases: ['final_approach', 'landing'],
      severity: 'safety_critical',
      message: 'Landed without landing clearance',
    },
    {
      id: 'reverse_deployed',
      when: { prop: 'engines.left.reverserNorm', op: 'gt', value: 0.3 },
      phases: ['landing', 'rollout', 'runway_exit'],
      severity: 'info',
      message: 'Reverse thrust deployed',
    },
    {
      id: 'overspeed_250_below_10k',
      when: { prop: 'speeds.iasKt', op: 'gt', value: 255, sustainedSec: 2 },
      phases: ['initial_climb', 'approach_setup'],
      severity: 'deviation',
      message: 'Exceeded 250 kt below 10,000 ft',
    },
    {
      id: 'unstable_approach',
      when: {
        all: [
          { prop: 'position.radioAltitudeFt', op: 'lt', value: 1000 },
          { prop: 'position.radioAltitudeFt', op: 'gt', value: 100 },
          {
            any: [
              { prop: 'controls.flapHandleDetent', op: 'lt', value: 30 },
              { prop: 'controls.gearLeverDown', op: 'eq', value: false },
              { prop: 'speeds.verticalSpeedFpm', op: 'lt', value: -1100 },
            ],
          },
        ],
        sustainedSec: 3,
      },
      phases: ['final_approach'],
      severity: 'deviation',
      message: 'Unstable approach below 1,000 ft (configuration or sink rate)',
    },
  ],
  checklists: [
    {
      id: 'before_takeoff',
      title: 'Before Takeoff',
      allowedPhaseIds: ['before_takeoff'],
      items: [
        {
          id: 'flight_controls',
          challenge: 'Flight controls',
          response: 'Checked',
          validation: { prop: 'flags.flightControlCheckDone', op: 'eq', value: true },
          responsibleCrew: 'captain',
          trainingHint:
            'Move the yoke to full deflection in roll and pitch, and the rudder left/right, before answering.',
          failureMessage: 'Flight-control check has not been performed',
          sourceReference: SOURCE,
        },
        {
          id: 'flaps',
          challenge: 'Flaps',
          dynamicResponseProp: 'controls.flapHandleDetent',
          validation: {
            all: [
              { prop: 'controls.flapHandleDetent', op: 'eq', value: 5 },
              { prop: 'controls.flapsActualNorm', op: 'between', min: 0.36, max: 0.39 },
            ],
          },
          responsibleCrew: 'first_officer',
          trainingHint:
            'Takeoff flaps for this scenario are flaps 5; verify the surfaces reached the setting.',
          failureMessage: 'Flaps are not set to 5 (green band)',
          sourceReference: SOURCE,
        },
        {
          id: 'stabilizer_trim',
          challenge: 'Stabilizer trim',
          response: '__ units, set',
          manualReason:
            'PLACEHOLDER_VALUE — stabilizer trim is not modeled in Milestone 1; no state to validate against.',
          responsibleCrew: 'first_officer',
          sourceReference: SOURCE,
        },
        {
          id: 'autobrake',
          challenge: 'Autobrake',
          response: 'RTO',
          validation: { prop: 'controls.autobrake', op: 'eq', value: 'RTO' },
          responsibleCrew: 'first_officer',
          trainingHint: 'Select RTO so a rejected takeoff brakes automatically.',
          failureMessage: 'Autobrake is not in RTO',
          sourceReference: SOURCE,
        },
        {
          id: 'speedbrake',
          challenge: 'Speed brake',
          response: 'Down detent',
          validation: { prop: 'controls.speedbrakeLeverNorm', op: 'lt', value: 0.05 },
          responsibleCrew: 'first_officer',
          failureMessage: 'Speed-brake lever is not in the down detent',
          sourceReference: SOURCE,
        },
        {
          id: 'exterior_lights',
          challenge: 'Landing & strobe lights',
          response: 'On',
          validation: {
            all: [
              { prop: 'lights.landing', op: 'eq', value: true },
              { prop: 'lights.strobe', op: 'eq', value: true },
            ],
          },
          responsibleCrew: 'captain',
          delegable: true,
          trainingHint: 'Landing and strobe lights come on when entering the runway.',
          failureMessage: 'Landing and/or strobe lights are off',
          sourceReference: SOURCE,
        },
      ],
    },
    {
      id: 'landing',
      title: 'Landing',
      allowedPhaseIds: ['approach_setup', 'final_approach', 'landing'],
      items: [
        {
          id: 'speedbrake_armed',
          challenge: 'Speed brake',
          response: 'Armed',
          validation: { prop: 'controls.speedbrakeArmed', op: 'eq', value: true },
          responsibleCrew: 'first_officer',
          failureMessage: 'Speed brake is not armed',
          sourceReference: SOURCE,
        },
        {
          id: 'gear',
          challenge: 'Landing gear',
          response: 'Down',
          validation: {
            all: [
              { prop: 'controls.gearLeverDown', op: 'eq', value: true },
              { prop: 'controls.gearPositionNorm', op: 'gt', value: 0.99 },
            ],
          },
          responsibleCrew: 'first_officer',
          failureMessage: 'Gear is not down and locked',
          sourceReference: SOURCE,
        },
        {
          id: 'flaps',
          challenge: 'Flaps',
          dynamicResponseProp: 'controls.flapHandleDetent',
          // The surfaces must have travelled, not just the handle (R-18).
          validation: {
            all: [
              { prop: 'controls.flapHandleDetent', op: 'gte', value: 30 },
              { prop: 'controls.flapsActualNorm', op: 'gte', value: 0.855 },
            ],
          },
          responsibleCrew: 'first_officer',
          failureMessage: 'Landing flaps (30) are not set',
          sourceReference: SOURCE,
        },
        {
          id: 'autobrake',
          challenge: 'Autobrake',
          response: '2 or 3',
          validation: {
            any: [
              { prop: 'controls.autobrake', op: 'eq', value: '2' },
              { prop: 'controls.autobrake', op: 'eq', value: '3' },
            ],
          },
          responsibleCrew: 'first_officer',
          failureMessage: 'Autobrake is not set for landing',
          sourceReference: SOURCE,
        },
      ],
    },
    {
      id: 'after_landing',
      title: 'After Landing',
      // Run only once the aircraft is clear of the runway.
      allowedPhaseIds: ['runway_exit'],
      items: [
        {
          id: 'speedbrake_down',
          challenge: 'Speed brake',
          response: 'Down detent',
          // Lever AND the spoiler panels themselves must be stowed (R-18).
          validation: {
            all: [
              { prop: 'controls.speedbrakeLeverNorm', op: 'lt', value: 0.05 },
              { prop: 'controls.spoilersDeployedNorm', op: 'lt', value: 0.05 },
            ],
          },
          responsibleCrew: 'first_officer',
          failureMessage: 'Speed-brake lever is still up',
          sourceReference: SOURCE,
        },
        {
          id: 'flaps_up',
          challenge: 'Flaps',
          response: 'Up',
          // Not complete while the flaps are still travelling up (R-18).
          validation: {
            all: [
              { prop: 'controls.flapHandleDetent', op: 'eq', value: 0 },
              { prop: 'controls.flapsActualNorm', op: 'lt', value: 0.02 },
            ],
          },
          responsibleCrew: 'first_officer',
          failureMessage: 'Flaps are not up',
          sourceReference: SOURCE,
        },
        {
          id: 'autobrake_off',
          challenge: 'Autobrake',
          response: 'Off',
          validation: { prop: 'controls.autobrake', op: 'eq', value: 'OFF' },
          responsibleCrew: 'first_officer',
          failureMessage: 'Autobrake is still selected',
          sourceReference: SOURCE,
        },
        {
          id: 'lights_after_landing',
          challenge: 'Strobe & landing lights',
          response: 'Off, taxi light on',
          validation: {
            all: [
              { prop: 'lights.strobe', op: 'eq', value: false },
              { prop: 'lights.landing', op: 'eq', value: false },
              { prop: 'lights.taxi', op: 'eq', value: true },
            ],
          },
          responsibleCrew: 'captain',
          delegable: true,
          failureMessage: 'Exterior lights are not in the after-landing configuration',
          sourceReference: SOURCE,
        },
      ],
    },
  ],
};
