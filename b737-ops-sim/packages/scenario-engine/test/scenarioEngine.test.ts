import { describe, expect, it } from 'vitest';
import { makeTestAircraftState } from '@b737/shared/testing';
import {
  destinationPoint,
  KSFO_28R,
  runwayPointToLatLon,
  type AircraftState,
} from '@b737/shared';
import { ScenarioRuntime } from '../src/scenarioRuntime.js';
import type { ScenarioDefinition } from '../src/types.js';

/** Minimal two-checklist scenario exercising spec §11 example rules. */
function makeScenario(): ScenarioDefinition {
  return {
    id: 'test_scenario',
    title: 'Test',
    aircraft: 'b737-800',
    description: 'test',
    initialState: {
      seed: 1,
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
            to: 'takeoff_roll',
            when: {
              all: [
                { prop: 'flags.takeoffClearanceReceived', op: 'eq', value: true },
                { prop: 'speeds.gsKt', op: 'gt', value: 40 },
              ],
            },
          },
        ],
      },
      {
        id: 'takeoff_roll',
        title: 'Takeoff roll',
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
      { id: 'initial_climb', title: 'Initial climb', transitions: [] },
      { id: 'debrief', title: 'Debrief', transitions: [] },
    ],
    rules: [
      {
        id: 'runway_incursion',
        when: {
          all: [
            { prop: 'flags.takeoffClearanceReceived', op: 'neq', value: true },
            { prop: 'speeds.gsKt', op: 'gt', value: 15 },
          ],
        },
        phases: ['before_takeoff'],
        severity: 'safety_critical',
        message: 'Entered the runway without takeoff clearance',
      },
      {
        id: 'sustained_overspeed',
        when: { prop: 'speeds.iasKt', op: 'gt', value: 250, sustainedSec: 2 },
        severity: 'deviation',
        message: 'Overspeed below 10,000 ft',
      },
    ],
    checklists: [
      {
        id: 'before_takeoff',
        title: 'Before Takeoff',
        items: [
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
            failureMessage: 'Flaps are not set to 5',
            sourceReference: 'NON_CERTIFIED_APPROXIMATION',
          },
          {
            id: 'flight_controls',
            challenge: 'Flight controls',
            response: 'Checked',
            validation: { prop: 'flags.flightControlCheckDone', op: 'eq', value: true },
            responsibleCrew: 'captain',
            sourceReference: 'NON_CERTIFIED_APPROXIMATION',
          },
        ],
      },
    ],
  };
}

/** Same base, but the incursion rule is geometric (R-08). */
function makeIncursionScenario(): ScenarioDefinition {
  const scenario = makeScenario();
  const rule = scenario.rules.find((r) => r.id === 'runway_incursion')!;
  rule.when = {
    all: [
      { prop: 'flags.takeoffClearanceReceived', op: 'neq', value: true },
      { prop: 'derived.enteredRunwaySurface', op: 'eq', value: true },
    ],
  };
  return scenario;
}

/** Landing → rollout → clear of the runway, gated on geometry. */
function makeExitScenario(): ScenarioDefinition {
  const scenario = makeScenario();
  scenario.initialPhaseId = 'rollout';
  scenario.phases = [
    ...scenario.phases,
    {
      id: 'rollout',
      title: 'Rollout',
      transitions: [
        {
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
    { id: 'runway_exit', title: 'Clear of the runway', transitions: [] },
  ];
  return scenario;
}

/** Adds an After Landing checklist that may only run after vacating. */
function makePhaseGatedScenario(): ScenarioDefinition {
  const scenario = makeScenario();
  scenario.checklists = [
    { ...scenario.checklists[0]!, allowedPhaseIds: ['before_takeoff'] },
    {
      id: 'after_landing',
      title: 'After Landing',
      allowedPhaseIds: ['runway_exit'],
      items: [
        {
          id: 'flaps_up',
          challenge: 'Flaps',
          response: 'Up',
          validation: { prop: 'controls.flapHandleDetent', op: 'eq', value: 0 },
          responsibleCrew: 'first_officer',
          sourceReference: 'NON_CERTIFIED_APPROXIMATION',
        },
      ],
    },
  ];
  return scenario;
}

function state(simTimeSec: number, overrides: (s: AircraftState) => void): AircraftState {
  const s = makeTestAircraftState();
  s.simTimeSec = simTimeSec;
  overrides(s);
  return s;
}

describe('phase machine', () => {
  it('does not advance without the clearance flag, then advances with it', () => {
    const rt = new ScenarioRuntime(makeScenario());
    rt.update(
      state(1, (s) => {
        s.speeds.gsKt = 60;
      }),
    );
    expect(rt.phaseId).toBe('before_takeoff');
    rt.setFlag('takeoffClearanceReceived', true);
    rt.update(
      state(2, (s) => {
        s.speeds.gsKt = 60;
      }),
    );
    expect(rt.phaseId).toBe('takeoff_roll');
  });

  it('detects positive rate only with vs>300, no WOW, and increasing RA', () => {
    const rt = new ScenarioRuntime(makeScenario());
    rt.setFlag('takeoffClearanceReceived', true);
    rt.update(state(0, (s) => (s.speeds.gsKt = 60)));
    expect(rt.phaseId).toBe('takeoff_roll');

    // airborne but RA flat (not yet increasing over the window)
    for (let t = 0; t < 3; t += 0.25) {
      rt.update(
        state(1 + t, (s) => {
          s.weightOnWheels = false;
          s.speeds.verticalSpeedFpm = 800;
          s.position.radioAltitudeFt = 0; // RA not yet rising
        }),
      );
    }
    expect(rt.phaseId).toBe('takeoff_roll');

    // now RA climbs
    for (let t = 0; t < 3; t += 0.25) {
      rt.update(
        state(5 + t, (s) => {
          s.weightOnWheels = false;
          s.speeds.verticalSpeedFpm = 900;
          s.position.radioAltitudeFt = 20 + t * 40;
        }),
      );
    }
    expect(rt.phaseId).toBe('initial_climb');
    expect(rt.events.some((e) => e.id === 'positive_rate')).toBe(true);
  });
});

describe('monitor rules', () => {
  it('fires a safety-critical event for rolling without clearance, once', () => {
    const rt = new ScenarioRuntime(makeScenario());
    rt.update(state(1, (s) => (s.speeds.gsKt = 20)));
    rt.update(state(2, (s) => (s.speeds.gsKt = 25)));
    const fired = rt.events.filter((e) => e.id === 'runway_incursion');
    expect(fired).toHaveLength(1);
    expect(fired[0]!.severity).toBe('safety_critical');
  });

  it('requires sustained duration before firing sustained rules', () => {
    const rt = new ScenarioRuntime(makeScenario());
    rt.setFlag('takeoffClearanceReceived', true);
    rt.update(state(0, (s) => (s.speeds.iasKt = 260)));
    rt.update(state(1, (s) => (s.speeds.iasKt = 260)));
    expect(rt.events.some((e) => e.id === 'sustained_overspeed')).toBe(false);
    rt.update(state(2.5, (s) => (s.speeds.iasKt = 260)));
    expect(rt.events.some((e) => e.id === 'sustained_overspeed')).toBe(true);
  });
});

describe('checklist runtime', () => {
  it('completes a state-validated item only when state matches', () => {
    const rt = new ScenarioRuntime(makeScenario());
    // flaps at 10, not 5 → item must fail
    rt.update(
      state(1, (s) => {
        s.controls.flapHandleDetent = 10;
      }),
    );
    const fail = rt.answerChecklistItem('before_takeoff');
    expect(fail?.kind).toBe('checklist_item_failed');

    // correct the configuration → item passes
    rt.update(
      state(2, (s) => {
        s.controls.flapHandleDetent = 5;
        s.controls.flapsActualNorm = 0.375;
      }),
    );
    const ok = rt.answerChecklistItem('before_takeoff');
    expect(ok?.kind).toBe('checklist_item_completed');
  });

  it('flag-gated item + checklist completion event', () => {
    const rt = new ScenarioRuntime(makeScenario());
    rt.update(
      state(1, (s) => {
        s.controls.flapHandleDetent = 5;
        s.controls.flapsActualNorm = 0.375;
      }),
    );
    expect(rt.answerChecklistItem('before_takeoff')?.kind).toBe('checklist_item_completed');
    // flight-control check not performed yet
    expect(rt.answerChecklistItem('before_takeoff')?.kind).toBe('checklist_item_failed');
    rt.setFlag('flightControlCheckDone', true);
    rt.update(state(2, () => undefined));
    expect(rt.answerChecklistItem('before_takeoff')?.kind).toBe('checklist_item_completed');
    expect(rt.events.some((e) => e.kind === 'checklist_completed')).toBe(true);
    expect(rt.checklistRuns.get('before_takeoff')!.complete).toBe(true);
  });
});

// --------------------------------------------------------------- R-08 / R-10

describe('runway geometry drives entry, occupancy and exit', () => {
  const rwy = KSFO_28R;
  const at =
    (alongM: number, crossM: number, mutate: (s: AircraftState) => void = () => undefined) =>
    (t: number): AircraftState => {
      const centerline = destinationPoint(
        rwy.thresholdLatDeg,
        rwy.thresholdLonDeg,
        rwy.headingDegTrue,
        alongM,
      );
      const p = destinationPoint(
        centerline.latDeg,
        centerline.lonDeg,
        rwy.headingDegTrue + 90,
        crossM,
      );
      return state(t, (s) => {
        s.position.latDeg = p.latDeg;
        s.position.lonDeg = p.lonDeg;
        s.weightOnWheels = true;
        mutate(s);
      });
    };

  it('reports occupancy from position, not ground speed', () => {
    const rt = new ScenarioRuntime(makeScenario());
    rt.update(at(800, 0)(0));
    expect(rt.context(rt.state!).derived.onRunwaySurface).toBe(true);
    expect(rt.context(rt.state!).derived.runwayAlongM).toBeCloseTo(800, 0);

    rt.update(at(800, 76)(1)); // the offset that used to trigger an incursion
    expect(rt.context(rt.state!).derived.onRunwaySurface).toBe(false);
  });

  it('flags an incursion when the aircraft crosses onto the runway uncleared', () => {
    const rt = new ScenarioRuntime(makeIncursionScenario());
    rt.update(at(40, 90)(0)); // holding point, clear of the runway
    rt.update(at(40, 60)(1)); // still clear
    expect(rt.events.some((e) => e.id === 'runway_incursion')).toBe(false);
    rt.update(at(40, 5)(2)); // crossed the edge without a clearance
    expect(rt.events.some((e) => e.id === 'runway_incursion')).toBe(true);
  });

  it('does not flag an aircraft that starts lined up on the runway', () => {
    const rt = new ScenarioRuntime(makeIncursionScenario());
    rt.update(at(30, 0)(0));
    rt.update(at(30, 0)(1));
    expect(rt.events.some((e) => e.id === 'runway_incursion')).toBe(false);
  });

  it('slowing down on the centerline is not "clear of the runway"', () => {
    const rt = new ScenarioRuntime(makeExitScenario());
    for (let t = 0; t < 5; t += 0.5) rt.update(at(2000, 0, (s) => (s.speeds.gsKt = 8))(t));
    expect(rt.phaseId).toBe('rollout');
    for (let t = 5; t < 10; t += 0.5) rt.update(at(2000, 45, (s) => (s.speeds.gsKt = 8))(t));
    expect(rt.phaseId).toBe('runway_exit');
  });
});

// ------------------------------------------------------------------ M3 taxi

describe('taxi geometry', () => {
  const onGroundAt = (latDeg: number, lonDeg: number, gsKt = 10) =>
    state(0, (s) => {
      s.position.latDeg = latDeg;
      s.position.lonDeg = lonDeg;
      s.weightOnWheels = true;
      s.speeds.gsKt = gsKt;
    });

  it('reports the taxiway the aircraft is on', () => {
    const rt = new ScenarioRuntime(makeScenario());
    const p = runwayPointToLatLon(KSFO_28R, 700, 90);
    rt.update(onGroundAt(p.latDeg, p.lonDeg));
    const d = rt.context(rt.state!).derived;
    expect(d.onTaxiSurface).toBe(true);
    expect(d.taxiwayLabel).toBe('A');
    expect(d.pastHoldShort).toBe(false);
    expect(d.distanceToHoldShortM).toBeCloseTo(45, 0);
  });

  it('reports crossing the holding position before reaching the runway', () => {
    const rt = new ScenarioRuntime(makeScenario());
    const p = runwayPointToLatLon(KSFO_28R, 40, 40);
    rt.update(onGroundAt(p.latDeg, p.lonDeg));
    const d = rt.context(rt.state!).derived;
    expect(d.pastHoldShort).toBe(true);
    expect(d.onRunwaySurface).toBe(false); // not on the pavement yet
  });

  it('measures the distance to the stand', () => {
    const rt = new ScenarioRuntime(makeScenario());
    const p = runwayPointToLatLon(KSFO_28R, 350, 205);
    rt.update(onGroundAt(p.latDeg, p.lonDeg, 0));
    expect(rt.context(rt.state!).derived.distanceToStandM!).toBeLessThan(6);
  });

  it('is not "on a taxiway" while airborne over one', () => {
    const rt = new ScenarioRuntime(makeScenario());
    const p = runwayPointToLatLon(KSFO_28R, 700, 90);
    rt.update(
      state(0, (s) => {
        s.position.latDeg = p.latDeg;
        s.position.lonDeg = p.lonDeg;
        s.weightOnWheels = false;
        s.position.radioAltitudeFt = 600;
      }),
    );
    expect(rt.context(rt.state!).derived.onTaxiSurface).toBe(false);
  });
});

describe('phases can re-arm a checklist', () => {
  it('resets the checklists a phase declares on entry (go-around)', () => {
    const scenario = makeScenario();
    scenario.phases = [
      {
        id: 'before_takeoff',
        title: 'Before takeoff',
        transitions: [{ to: 'go_around', when: { prop: 'speeds.gsKt', op: 'gt', value: 50 } }],
      },
      {
        id: 'go_around',
        title: 'Go around',
        transitions: [],
        resetChecklistIds: ['before_takeoff'],
      },
      ...scenario.phases.filter((p) => p.id !== 'before_takeoff'),
    ];
    const rt = new ScenarioRuntime(scenario);
    rt.update(state(0, (s) => (s.controls.flapsActualNorm = 0.375)));
    rt.setFlag('flightControlCheckDone', true);
    rt.update(state(1, (s) => (s.controls.flapsActualNorm = 0.375)));
    expect(rt.answerChecklistItem('before_takeoff')?.kind).toBe('checklist_item_completed');
    expect(rt.checklistRuns.get('before_takeoff')!.items[0]!.status).toBe('completed');

    rt.update(state(2, (s) => (s.speeds.gsKt = 60)));
    expect(rt.phaseId).toBe('go_around');
    expect(rt.checklistRuns.get('before_takeoff')!.items[0]!.status).toBe('active');
    expect(rt.checklistRuns.get('before_takeoff')!.complete).toBe(false);
  });
});

describe('checklists are gated on the flight phase', () => {
  it('refuses a checklist that does not belong to the current phase', () => {
    const rt = new ScenarioRuntime(makePhaseGatedScenario());
    rt.update(state(0, () => undefined));
    const event = rt.answerChecklistItem('after_landing');
    expect(event?.kind).toBe('checklist_item_failed');
    expect(event?.id).toContain('out_of_phase');
    expect(rt.checklistRuns.get('after_landing')!.complete).toBe(false);
    expect(rt.isChecklistAvailable('after_landing')).toBe(false);
    expect(rt.isChecklistAvailable('before_takeoff')).toBe(true);
  });
});

describe('history', () => {
  it('keeps a downsampled history for the debrief', () => {
    const rt = new ScenarioRuntime(makeScenario());
    for (let t = 0; t < 10; t += 0.1) {
      rt.update(state(t, (s) => (s.speeds.iasKt = t * 10)));
    }
    expect(rt.history.length).toBeGreaterThan(15);
    expect(rt.history.length).toBeLessThan(30);
    expect(rt.history.at(-1)!.phaseId).toBe('before_takeoff');
  });
});
