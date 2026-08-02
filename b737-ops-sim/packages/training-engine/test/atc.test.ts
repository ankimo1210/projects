import { beforeEach, describe, expect, it } from 'vitest';
import { KSFO_28R, type AircraftState } from '@b737/shared';
import { makeTestAircraftState } from '@b737/shared/testing';
import { AtcController, type AtcInstruction } from '../src/atc.js';
import { resetTranscriptIds } from '../src/transcript.js';

function st(
  simTimeSec: number,
  mutate: (s: AircraftState) => void = () => undefined,
): AircraftState {
  const s = makeTestAircraftState();
  s.simTimeSec = simTimeSec;
  mutate(s);
  return s;
}

describe('AtcController', () => {
  beforeEach(() => resetTranscriptIds());

  it('issues takeoff clearance on request with a correct readback option', () => {
    const atc = new AtcController(KSFO_28R);
    const result = atc.requestTakeoffClearance(st(1));
    expect('flagsOnAccept' in result).toBe(true);
    const instruction = result as AtcInstruction;
    expect(instruction.transcriptEntry.message).toContain('cleared for takeoff');
    expect(instruction.flagsOnAccept.takeoffClearanceReceived).toBe(true);
    const correctOptions = instruction.transcriptEntry.expectedResponse!.options.filter(
      (o) => o.correct,
    );
    expect(correctOptions).toHaveLength(1);
  });

  it('tracks readback stats and repeats the instruction on a wrong readback', () => {
    const atc = new AtcController(KSFO_28R);
    const instruction = atc.requestTakeoffClearance(st(1)) as AtcInstruction;
    const wrong = atc.handleReadback(instruction, 'roger', st(2));
    expect(wrong.correct).toBe(false);
    expect(wrong.followUps[0]!.message).toContain('negative');
    expect(atc.stats).toEqual({ readbacksTotal: 1, readbacksCorrect: 0 });
    const right = atc.handleReadback(instruction, 'correct', st(3));
    expect(right.correct).toBe(true);
    expect(atc.stats).toEqual({ readbacksTotal: 2, readbacksCorrect: 1 });
  });

  it('walks the departure → vectors → approach → landing sequence from state', () => {
    const atc = new AtcController(KSFO_28R);
    atc.requestTakeoffClearance(st(1));
    // climb out
    let out = atc.update(
      st(60, (s) => {
        s.weightOnWheels = false;
        s.position.radioAltitudeFt = 400;
      }),
      'initial_climb',
    );
    expect(out[0]!.transcriptEntry.message).toContain('runway heading');
    expect(out[0]!.targetAltitudeFt).toBe(3000);

    // through 1500 AGL → first vector
    out = atc.update(
      st(120, (s) => {
        s.weightOnWheels = false;
        s.position.radioAltitudeFt = 1600;
      }),
      'initial_climb',
    );
    expect(out[0]!.targetHeadingDeg).toBeDefined();
    const crosswindHdg = out[0]!.targetHeadingDeg!;

    // fly the crosswind leg long enough with heading captured → downwind vector
    out = atc.update(
      st(180, (s) => {
        s.weightOnWheels = false;
        s.position.radioAltitudeFt = 2500;
        s.attitude.headingDegMag = crosswindHdg;
      }),
      'pattern',
    );
    expect(out).toHaveLength(1);
    const downwindHdg = out[0]!.targetHeadingDeg!;
    expect(downwindHdg).not.toBe(crosswindHdg);

    // downwind → base (with descent)
    out = atc.update(
      st(330, (s) => {
        s.weightOnWheels = false;
        s.position.radioAltitudeFt = 2800;
        s.attitude.headingDegMag = downwindHdg;
      }),
      'pattern',
    );
    expect(out[0]!.targetAltitudeFt).toBe(1800);
    const baseHdg = out[0]!.targetHeadingDeg!;

    // base → intercept + approach clearance
    out = atc.update(
      st(420, (s) => {
        s.weightOnWheels = false;
        s.position.radioAltitudeFt = 1800;
        s.attitude.headingDegMag = baseHdg;
      }),
      'pattern',
    );
    expect(out[0]!.transcriptEntry.message).toContain('cleared ILS');
    expect(out[0]!.flagsOnAccept.approachClearanceReceived).toBe(true);

    // established inbound → landing clearance
    out = atc.update(
      st(420, (s) => {
        s.weightOnWheels = false;
        s.position.radioAltitudeFt = 1500;
        s.attitude.headingDegMag = KSFO_28R.headingDegMag;
        s.nav.locDeviationDots = 0.2;
      }),
      'final_approach',
    );
    expect(out[0]!.transcriptEntry.message).toContain('cleared to land');

    // after rollout → exit instruction
    out = atc.update(
      st(560, (s) => {
        s.weightOnWheels = true;
        s.speeds.gsKt = 30;
      }),
      'rollout',
    );
    expect(out[0]!.transcriptEntry.message).toContain('exit the runway');
  });

  it('does not issue landing clearance when not established', () => {
    const atc = new AtcController(KSFO_28R);
    atc.requestTakeoffClearance(st(1));
    atc.update(
      st(60, (s) => ((s.weightOnWheels = false), (s.position.radioAltitudeFt = 400))),
      'x',
    );
    atc.update(
      st(120, (s) => ((s.weightOnWheels = false), (s.position.radioAltitudeFt = 1600))),
      'x',
    );
    // skip ahead: pretend we're on final but 2 dots off
    const out = atc.update(
      st(400, (s) => {
        s.weightOnWheels = false;
        s.position.radioAltitudeFt = 1500;
        s.attitude.headingDegMag = KSFO_28R.headingDegMag;
        s.nav.locDeviationDots = 2.2;
      }),
      'final_approach',
    );
    expect(out.every((i) => !i.transcriptEntry.message.includes('cleared to land'))).toBe(true);
  });
});
