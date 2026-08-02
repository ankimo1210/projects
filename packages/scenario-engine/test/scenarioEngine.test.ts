import { describe, expect, it } from 'vitest';
import { makeTestAircraftState } from '@b737/shared/testing';
import type { AircraftState } from '@b737/shared';
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
