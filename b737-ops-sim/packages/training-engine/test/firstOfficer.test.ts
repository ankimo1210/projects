import { beforeEach, describe, expect, it } from 'vitest';
import { makeTestAircraftState } from '@b737/shared/testing';
import type { AircraftState, FlapDetent } from '@b737/shared';
import { FirstOfficer } from '../src/firstOfficer.js';
import type { TranscriptEntry } from '../src/transcript.js';
import { resetTranscriptIds } from '../src/transcript.js';

/** Landing configuration as the aircraft actually reports it (R-18/R-19). */
function configureForLanding(s: AircraftState): void {
  s.controls.flapHandleDetent = 30;
  s.controls.flapsActualNorm = 0.875; // flaps 30 fully travelled
  s.controls.gearLeverDown = true;
  s.controls.gearPositionNorm = 1;
  s.nav.ilsTuned = true;
  s.nav.locDeviationDots = 0;
  s.nav.gsDeviationDots = 0;
}

/** Fly a stabilised 700 fpm descent from 1200 ft to touchdown. */
function flyDescent(
  fo: FirstOfficer,
  mutate: (s: AircraftState) => void = () => undefined,
): TranscriptEntry[] {
  const lines: TranscriptEntry[] = [];
  for (let ra = 1200; ra >= 0; ra -= 7) {
    lines.push(
      ...fo.update(
        st((1200 - ra) / 10, (s) => {
          s.weightOnWheels = ra <= 0;
          s.position.radioAltitudeFt = Math.max(0, ra);
          s.speeds.verticalSpeedFpm = -700;
          s.speeds.iasKt = 145;
          configureForLanding(s);
          mutate(s);
        }),
        'final_approach',
      ),
    );
  }
  return lines;
}

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
    const lines = [
      ...fo.update(
        st(11, (s) => {
          s.weightOnWheels = false;
          s.speeds.verticalSpeedFpm = 800;
          s.position.radioAltitudeFt = 40;
        }),
        'initial_climb',
      ),
      ...fo.update(
        st(11.5, (s) => {
          s.weightOnWheels = false;
          s.speeds.verticalSpeedFpm = 900;
          s.position.radioAltitudeFt = 55;
        }),
        'initial_climb',
      ),
    ];
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
    const prLines = [
      ...fo.update(
        st(11, (s) => {
          s.weightOnWheels = false;
          s.speeds.verticalSpeedFpm = 800;
          s.position.radioAltitudeFt = 40;
        }),
        'initial_climb',
      ),
      ...fo.update(
        st(11.5, (s) => {
          s.weightOnWheels = false;
          s.speeds.verticalSpeedFpm = 800;
          s.position.radioAltitudeFt = 55;
        }),
        'initial_climb',
      ),
    ];
    const pr = prLines.find((l) => l.message === 'Positive rate.')!;
    fo.respond(
      pr,
      'roger',
      st(12, () => undefined),
    ); // wrong response; gear stays down
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

  // R-12: the callout must not depend on how often state samples arrive.
  it.each([5, 30, 60])('calls positive rate at %i Hz on a 900 fpm climb', (rateHz) => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    const dt = 1 / rateHz;
    const messages: string[] = [];
    let ra = 0;
    for (let t = 0; t < 6; t += dt) {
      ra += (900 / 60) * dt; // 900 fpm
      messages.push(
        ...fo
          .update(
            st(t, (s) => {
              s.weightOnWheels = false;
              s.speeds.verticalSpeedFpm = 900;
              s.position.radioAltitudeFt = ra;
            }),
            'initial_climb',
          )
          .map((l) => l.message),
      );
    }
    expect(messages.filter((m) => m === 'Positive rate.')).toHaveLength(1);
  });

  it('makes descending approach altitude callouts once each', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    const lines = flyDescent(fo);
    const altitudeCalls = lines
      .filter((l) => l.relatedEventId?.startsWith('callout:ra_'))
      .map((l) => l.message);
    expect(altitudeCalls).toEqual(['1000.', '500.', '100', '50', '40', '30', '20', '10']);
  });

  // M3 T5: gates, minimums and configuration read-backs.
  it('calls the 1000 and 500 gates and minimums on a stable approach', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    const messages = flyDescent(fo).map((l) => l.message);
    expect(messages).toContain('1000, stable.');
    expect(messages).toContain('500, stable.');
    expect(messages).toContain('Minimums, runway in sight.');
    expect(messages).toContain('Gear down, three green.');
  });

  it('calls the gates as not stable when the approach is not', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    const messages = flyDescent(fo, (s) => {
      s.speeds.iasKt = 195; // well above vapp
    }).map((l) => l.message);
    expect(messages.find((m) => m.startsWith('1000,'))).toContain('not stable');
    expect(messages.find((m) => m.startsWith('Minimums'))).toContain('go around');
  });

  it('reads back flap and gear selections', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    const at = (t: number, detent: FlapDetent, gearDown: boolean) =>
      fo.update(
        st(t, (s) => {
          s.weightOnWheels = false;
          s.position.radioAltitudeFt = 2500;
          s.controls.flapHandleDetent = detent;
          s.controls.gearLeverDown = gearDown;
        }),
        'approach_setup',
      );
    at(0, 5, false); // first sample only records the baseline
    const flaps = at(1, 15, false).map((l) => l.message);
    const gear = at(2, 15, true).map((l) => l.message);
    expect(flaps).toContain('Flaps 15.');
    expect(gear).toContain('Gear down.');
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
          configureForLanding(s);
        }),
        'final_approach',
      );
      messages.push(...lines.map((l) => l.message));
    }
    expect(messages.some((m) => m.includes('Go around'))).toBe(true);
    expect(messages.find((m) => m.includes('Go around'))).toContain('speed');
    // fires once only
    expect(messages.filter((m) => m.includes('Go around'))).toHaveLength(1);
  });

  // R-18: the surfaces decide, not the handles.
  it('treats a landing flap handle with the surface still in transit as unstable', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    const messages: string[] = [];
    for (let t = 0; t < 8; t += 0.5) {
      messages.push(
        ...fo
          .update(
            st(t, (s) => {
              s.weightOnWheels = false;
              s.position.radioAltitudeFt = 800;
              s.speeds.verticalSpeedFpm = -700;
              s.speeds.iasKt = 149;
              configureForLanding(s);
              s.controls.flapHandleDetent = 30; // selected…
              s.controls.flapsActualNorm = 0.5; // …but still travelling
            }),
            'final_approach',
          )
          .map((l) => l.message),
      );
    }
    expect(messages.find((m) => m.includes('Go around'))).toContain('configuration');
  });

  // R-19: on an ILS approach, missing guidance is not a stable flight path.
  it('treats a tuned ILS with no deviation data as unstable', () => {
    const fo = new FirstOfficer({ grossWeightLb: 145000 });
    const messages: string[] = [];
    for (let t = 0; t < 8; t += 0.5) {
      messages.push(
        ...fo
          .update(
            st(t, (s) => {
              s.weightOnWheels = false;
              s.position.radioAltitudeFt = 800;
              s.speeds.verticalSpeedFpm = -700;
              s.speeds.iasKt = 149;
              configureForLanding(s);
              s.nav.locDeviationDots = null;
              s.nav.gsDeviationDots = null;
            }),
            'final_approach',
          )
          .map((l) => l.message),
      );
    }
    expect(messages.find((m) => m.includes('Go around'))).toContain('flight path');
  });
});
