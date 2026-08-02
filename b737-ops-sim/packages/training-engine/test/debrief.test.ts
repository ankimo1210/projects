import { describe, expect, it } from 'vitest';
import { KSFO_28R, destinationPoint } from '@b737/shared';
import type { HistorySample, ScenarioEvent } from '@b737/scenario-engine';
import { generateDebrief, type DebriefInput } from '../src/debrief.js';

/** Build a plausible history: roll → liftoff → climb → approach → touchdown. */
function makeHistory(opts: {
  touchdownVsFpm?: number;
  touchdownDistM?: number;
  gearUpDelaySec?: number;
  offCenterM?: number;
}): HistorySample[] {
  const { touchdownVsFpm = -200, touchdownDistM = 450, gearUpDelaySec = 6, offCenterM = 1 } = opts;
  const samples: HistorySample[] = [];
  const push = (
    t: number,
    partial: Partial<HistorySample> & { alongM?: number; crossM?: number },
  ) => {
    const alongM = partial.alongM ?? 0;
    const crossM = partial.crossM ?? 0;
    const east =
      Math.sin((KSFO_28R.headingDegTrue * Math.PI) / 180) * alongM +
      Math.cos((KSFO_28R.headingDegTrue * Math.PI) / 180) * crossM;
    const north =
      Math.cos((KSFO_28R.headingDegTrue * Math.PI) / 180) * alongM -
      Math.sin((KSFO_28R.headingDegTrue * Math.PI) / 180) * crossM;
    const pos = destinationPoint(
      KSFO_28R.thresholdLatDeg,
      KSFO_28R.thresholdLonDeg,
      (Math.atan2(east, north) * 180) / Math.PI,
      Math.hypot(east, north),
    );
    samples.push({
      simTimeSec: t,
      iasKt: 0,
      altitudeFtMsl: 13,
      radioAltitudeFt: 0,
      verticalSpeedFpm: 0,
      headingDegMag: KSFO_28R.headingDegMag,
      pitchDeg: 0,
      rollDeg: 0,
      locDeviationDots: 0,
      gsDeviationDots: 0,
      latDeg: pos.latDeg,
      lonDeg: pos.lonDeg,
      weightOnWheels: true,
      flapHandleDetent: 5,
      gearLeverDown: true,
      n1AvgPct: 90,
      phaseId: 'takeoff_roll',
      ...partial,
    });
  };

  // takeoff roll 0..30 s, liftoff at ~146 kt
  for (let t = 0; t <= 30; t += 0.5) {
    push(t, { iasKt: t * 5, alongM: t * t * 2.2, weightOnWheels: true });
  }
  // climb 30..60 s
  for (let t = 30.5; t <= 60; t += 0.5) {
    push(t, {
      iasKt: 160,
      weightOnWheels: false,
      radioAltitudeFt: (t - 30) * 40,
      altitudeFtMsl: 13 + (t - 30) * 40,
      verticalSpeedFpm: 2000,
      pitchDeg: 15,
      gearLeverDown: t - 30 < gearUpDelaySec,
      alongM: 2000 + (t - 30) * 80,
      phaseId: 'initial_climb',
    });
  }
  // final approach 300..360 s, descending to threshold
  for (let t = 300; t <= 360; t += 0.5) {
    const raFt = Math.max(5, 1200 - (t - 300) * 20);
    push(t, {
      iasKt: 150,
      weightOnWheels: false,
      radioAltitudeFt: raFt,
      altitudeFtMsl: 13 + raFt,
      verticalSpeedFpm: -650,
      pitchDeg: 2,
      flapHandleDetent: 30,
      gearLeverDown: true,
      alongM: -((raFt / Math.tan((3 * Math.PI) / 180)) * 0.3048),
      crossM: offCenterM,
      phaseId: 'final_approach',
    });
  }
  // touchdown + rollout
  push(360.5, {
    iasKt: 140,
    weightOnWheels: false,
    radioAltitudeFt: 10,
    verticalSpeedFpm: touchdownVsFpm,
    flapHandleDetent: 30,
    alongM: touchdownDistM - 20,
    crossM: offCenterM,
    phaseId: 'landing',
  });
  for (let t = 361; t <= 375; t += 0.5) {
    push(t, {
      iasKt: Math.max(20, 140 - (t - 361) * 12),
      weightOnWheels: true,
      flapHandleDetent: 30,
      alongM: touchdownDistM + (t - 361) * 55,
      crossM: offCenterM,
      phaseId: 'rollout',
    });
  }
  return samples;
}

function baseInput(history: HistorySample[], events: ScenarioEvent[] = []): DebriefInput {
  return {
    events: [
      {
        kind: 'checklist_completed',
        simTimeSec: 5,
        id: 'before_takeoff',
        message: '',
        severity: 'info',
      },
      {
        kind: 'checklist_completed',
        simTimeSec: 340,
        id: 'landing',
        message: '',
        severity: 'info',
      },
      { kind: 'milestone', simTimeSec: 362, id: 'reverse_deployed', message: '', severity: 'info' },
      ...events,
    ],
    history,
    transcript: [],
    atcStats: { readbacksTotal: 5, readbacksCorrect: 5 },
    grossWeightLb: 145000,
    runway: KSFO_28R,
    expectedChecklistIds: ['before_takeoff', 'landing'],
  };
}

describe('generateDebrief', () => {
  it('scores a clean flight as PASS with full categories', () => {
    const report = generateDebrief(baseInput(makeHistory({})));
    expect(report.overall).toBe('PASS');
    for (const category of report.categories) {
      expect(category.score).toBe(100);
    }
    expect(report.metrics['Touchdown sink rate']).toBeDefined();
  });

  it('flags a hard landing with an explicit finding', () => {
    const report = generateDebrief(baseInput(makeHistory({ touchdownVsFpm: -800 })));
    const landing = report.categories.find((c) => c.id === 'landing')!;
    expect(landing.score).toBeLessThan(100);
    expect(landing.findings.some((f) => f.label === 'Hard landing')).toBe(true);
    expect(report.overall).toBe('PASS_WITH_DEVIATIONS');
  });

  it('deducts for late gear retraction', () => {
    const report = generateDebrief(baseInput(makeHistory({ gearUpDelaySec: 29.5 })));
    const takeoff = report.categories.find((c) => c.id === 'takeoff_procedure')!;
    expect(takeoff.findings.some((f) => f.label === 'Late gear retraction')).toBe(true);
  });

  it('fails the flight on a runway incursion', () => {
    const report = generateDebrief(
      baseInput(makeHistory({}), [
        {
          kind: 'rule_fired',
          simTimeSec: 2,
          id: 'runway_incursion',
          message: 'entered runway without clearance',
          severity: 'safety_critical',
        },
      ]),
    );
    const takeoff = report.categories.find((c) => c.id === 'takeoff_procedure')!;
    expect(takeoff.score).toBeLessThanOrEqual(60);
    expect(report.overall).toBe('FAIL');
  });

  it('penalizes incorrect readbacks and missing checklists', () => {
    const input = baseInput(makeHistory({}));
    input.atcStats = { readbacksTotal: 6, readbacksCorrect: 4 };
    input.expectedChecklistIds = ['before_takeoff', 'landing', 'after_landing'];
    const report = generateDebrief(input);
    expect(report.categories.find((c) => c.id === 'atc_compliance')!.findings[0]!.detail).toContain(
      '2 incorrect',
    );
    expect(
      report.categories
        .find((c) => c.id === 'checklist_discipline')!
        .findings.some((f) => f.detail.includes('after_landing')),
    ).toBe(true);
  });

  it('reports touchdown metrics with explicit values', () => {
    const report = generateDebrief(baseInput(makeHistory({ touchdownDistM: 500, offCenterM: 3 })));
    expect(report.metrics['Touchdown point']).toMatch(/\d+ m past the threshold/);
    expect(report.metrics['Centerline offset at touchdown']).toMatch(/m$/);
  });
});
