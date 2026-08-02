import { beforeEach, describe, expect, it } from 'vitest';
import { makeTestAircraftState } from '@b737/shared/testing';
import type { AircraftState } from '@b737/shared';
import { FirstOfficer } from '../src/firstOfficer.js';
import { resetTranscriptIds } from '../src/transcript.js';

function st(simTimeSec: number, mutate: (s: AircraftState) => void): AircraftState {
  const s = makeTestAircraftState();
  s.simTimeSec = simTimeSec;
  mutate(s);
  return s;
}

describe('FirstOfficer takeoff callouts', () => {
  beforeEach(() => resetTranscriptIds());

  it('calls 80 knots, V1, Rotate in order, exactly once', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 }); // V1≈143, VR≈146
    const messages: string[] = [];
    for (let ias = 0, t = 0; ias <= 160; ias += 5, t += 0.5) {
      const lines = fo.update(
        st(t, (s) => {
          s.speeds.iasKt = ias;
          s.weightOnWheels = true;
        }),
        'takeoff_roll',
      );
      messages.push(...lines.map((l) => l.message));
      // repeat the same speed — must not repeat the callout
      messages.push(
        ...fo
          .update(
            st(t + 0.1, (s) => {
              s.speeds.iasKt = ias;
              s.weightOnWheels = true;
            }),
            'takeoff_roll',
          )
          .map((l) => l.message),
      );
    }
    expect(messages).toEqual(['Eighty knots.', 'V1.', 'Rotate.']);
  });

  it('does not call takeoff speeds outside takeoff phases', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    const lines = fo.update(
      st(1, (s) => {
        s.speeds.iasKt = 120;
        s.weightOnWheels = true;
      }),
      'before_takeoff',
    );
    expect(lines).toHaveLength(0);
  });

  it('calls positive rate and expects "Gear up", acknowledging a correct response', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    fo.update(
      st(10, (s) => {
        s.weightOnWheels = false;
        s.speeds.verticalSpeedFpm = 600;
        s.position.radioAltitudeFt = 15;
      }),
      'initial_climb',
    );
    const lines = fo.update(
      st(11, (s) => {
        s.weightOnWheels = false;
        s.speeds.verticalSpeedFpm = 800;
        s.position.radioAltitudeFt = 40;
      }),
      'initial_climb',
    );
    const positiveRate = lines.find((l) => l.message === 'Positive rate.');
    expect(positiveRate).toBeDefined();
    expect(positiveRate!.expectedResponse!.options.some((o) => o.correct)).toBe(true);

    const state = st(12, (s) => {
      s.weightOnWheels = false;
    });
    const { correct, followUps } = fo.respond(positiveRate!, 'gear_up', state);
    expect(correct).toBe(true);
    expect(followUps.map((f) => f.message)).toContain('Gear up.');
  });

  it('reminds about the gear if it stays down well after positive rate', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    fo.update(
      st(10, (s) => {
        s.weightOnWheels = false;
        s.speeds.verticalSpeedFpm = 700;
        s.position.radioAltitudeFt = 15;
      }),
      'initial_climb',
    );
    const prLines = fo.update(
      st(11, (s) => {
        s.weightOnWheels = false;
        s.speeds.verticalSpeedFpm = 800;
        s.position.radioAltitudeFt = 40;
      }),
      'initial_climb',
    );
    const pr = prLines.find((l) => l.message === 'Positive rate.')!;
    fo.respond(pr, 'roger', st(12, () => undefined)); // wrong response; gear stays down
    const reminder = fo.update(
      st(40, (s) => {
        s.weightOnWheels = false;
        s.position.radioAltitudeFt = 600;
        s.controls.gearLeverDown = true;
      }),
      'initial_climb',
    );
    expect(reminder.map((l) => l.message)).toContain('Gear is still down.');
  });

  it('makes descending approach altitude callouts once each', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    const messages: string[] = [];
    for (let ra = 1200; ra >= 0; ra -= 7) {
      const lines = fo.update(
        st((1200 - ra) / 10, (s) => {
          s.weightOnWheels = ra <= 0;
          s.position.radioAltitudeFt = Math.max(0, ra);
          s.speeds.verticalSpeedFpm = -700;
          s.speeds.iasKt = 145;
          s.controls.flapHandleDetent = 30;
          s.controls.gearLeverDown = true;
        }),
        'final_approach',
      );
      messages.push(...lines.map((l) => l.message));
    }
    expect(messages).toEqual(['1000.', '500.', '100', '50', '40', '30', '20', '10']);
  });

  it('calls go-around advice for a sustained unstable approach', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 }); // vapp ≈ 149
    const messages: string[] = [];
    for (let t = 0; t < 8; t += 0.5) {
      const lines = fo.update(
        st(t, (s) => {
          s.weightOnWheels = false;
          s.position.radioAltitudeFt = 800;
          s.speeds.verticalSpeedFpm = -700;
          s.speeds.iasKt = 190; // way too fast
          s.controls.flapHandleDetent = 30;
          s.controls.gearLeverDown = true;
        }),
        'final_approach',
      );
      messages.push(...lines.map((l) => l.message));
    }
    expect(messages.some((m) => m.includes('Go around'))).toBe(true);
    // fires once only
    expect(messages.filter((m) => m.includes('Go around'))).toHaveLength(1);
  });
});
