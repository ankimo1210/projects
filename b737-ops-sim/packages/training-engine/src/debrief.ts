import {
  FT_TO_M,
  angleDiffDeg,
  degToRad,
  flapDetentToNorm,
  toLocalEnuM,
  vSpeedsForWeight,
  type RunwayData,
} from '@b737/shared';
import type { HistorySample, ScenarioEvent } from '@b737/scenario-engine';
import type { AtcStats } from './atc.js';
import type { TranscriptEntry } from './transcript.js';

/**
 * Post-flight debrief with transparent, rule-based scoring (spec §16):
 * every deduction is an explicit finding — no opaque aggregate.
 * Thresholds are NON_CERTIFIED_APPROXIMATION training heuristics.
 */

/** Actual flap travel that counts as landing flaps (handle 30, small margin). */
const LANDING_FLAP_NORM = flapDetentToNorm(30) - 0.02;

export interface DebriefFinding {
  label: string;
  detail: string;
  pointsDelta: number; // negative = deduction
}

export interface DebriefCategory {
  id: string;
  label: string;
  score: number; // 0..100
  findings: DebriefFinding[];
}

export type DebriefOverall = 'PASS' | 'PASS_WITH_DEVIATIONS' | 'FAIL';

export interface DebriefReport {
  overall: DebriefOverall;
  categories: DebriefCategory[];
  timeline: ScenarioEvent[];
  metrics: Record<string, string>;
}

export interface DebriefInput {
  events: ScenarioEvent[];
  history: HistorySample[];
  transcript: TranscriptEntry[];
  atcStats: AtcStats;
  grossWeightLb: number;
  runway: RunwayData;
  expectedChecklistIds: string[];
}

export function generateDebrief(input: DebriefInput): DebriefReport {
  const { history, events, runway } = input;
  const vs = vSpeedsForWeight(input.grossWeightLb);
  const metrics: Record<string, string> = {};

  const frame = (s: HistorySample): { alongM: number; crossM: number } => {
    const { eastM, northM } = toLocalEnuM(
      runway.thresholdLatDeg,
      runway.thresholdLonDeg,
      s.latDeg,
      s.lonDeg,
    );
    const c = degToRad(runway.headingDegTrue);
    return {
      alongM: eastM * Math.sin(c) + northM * Math.cos(c),
      crossM: eastM * Math.cos(c) - northM * Math.sin(c),
    };
  };

  // ---- key moments -------------------------------------------------------
  const liftoffIdx = history.findIndex(
    (s, i) => i > 0 && !s.weightOnWheels && history[i - 1]!.weightOnWheels,
  );
  const liftoff = liftoffIdx > 0 ? history[liftoffIdx]! : null;
  let touchdownIdx = -1;
  for (let i = history.length - 1; i > 0; i--) {
    if (history[i]!.weightOnWheels && !history[i - 1]!.weightOnWheels) {
      touchdownIdx = i;
      break;
    }
  }
  const touchdown = touchdownIdx > 0 ? history[touchdownIdx]! : null;

  // ---- category: takeoff procedure --------------------------------------
  const takeoff: DebriefFinding[] = [];
  if (events.some((e) => e.id === 'runway_incursion')) {
    takeoff.push({
      label: 'Takeoff clearance',
      detail: 'Entered the runway or began the takeoff roll without clearance',
      pointsDelta: -40,
    });
  }
  if (liftoff) {
    // Rotation = first pitch-up on the ground before liftoff (not liftoff speed).
    const rotationSample =
      history
        .slice(0, liftoffIdx)
        .find((s) => s.weightOnWheels && s.pitchDeg > 2 && s.iasKt > 80) ??
      history[liftoffIdx - 1]!;
    const iasAtRotation = rotationSample.iasKt;
    metrics['Rotation speed'] = `${iasAtRotation.toFixed(0)} kt (Vr ${vs.vrKt} kt)`;
    const rotDelta = iasAtRotation - vs.vrKt;
    if (rotDelta < -8) {
      takeoff.push({
        label: 'Early rotation',
        detail: `Rotated ~${Math.abs(rotDelta).toFixed(0)} kt below Vr`,
        pointsDelta: -15,
      });
    } else if (rotDelta > 15) {
      takeoff.push({
        label: 'Late rotation',
        detail: `Rotated ~${rotDelta.toFixed(0)} kt above Vr`,
        pointsDelta: -10,
      });
    }
    const after = history.slice(liftoffIdx, liftoffIdx + 40);
    const maxPitch = Math.max(...after.map((s) => s.pitchDeg));
    metrics['Max pitch after liftoff'] = `${maxPitch.toFixed(1)}°`;
    if (maxPitch > 22) {
      takeoff.push({
        label: 'Over-rotation',
        detail: `Pitch reached ${maxPitch.toFixed(1)}° (tail-strike risk region)`,
        pointsDelta: -15,
      });
    }
    // retraction timing measures the crew action, so the lever is correct here
    const gearUpSample = history.slice(liftoffIdx).find((s) => !s.gearLeverDown);
    if (!gearUpSample) {
      takeoff.push({
        label: 'Gear retraction',
        detail: 'Gear was never retracted',
        pointsDelta: -20,
      });
    } else {
      const delay = gearUpSample.simTimeSec - liftoff.simTimeSec;
      metrics['Gear retraction after liftoff'] = `${delay.toFixed(0)} s`;
      if (delay > 20) {
        takeoff.push({
          label: 'Late gear retraction',
          detail: `Gear up ${delay.toFixed(0)} s after liftoff (expected shortly after positive rate)`,
          pointsDelta: -10,
        });
      }
    }
    // Centerline during the roll
    const rollSamples = history
      .slice(0, liftoffIdx)
      .filter((s) => s.weightOnWheels && s.iasKt > 40);
    if (rollSamples.length > 0) {
      const maxOff = Math.max(...rollSamples.map((s) => Math.abs(frame(s).crossM)));
      metrics['Max centerline offset (takeoff roll)'] = `${maxOff.toFixed(1)} m`;
      if (maxOff > 12) {
        takeoff.push({
          label: 'Centerline tracking',
          detail: `Deviated up to ${maxOff.toFixed(0)} m from the centerline during the roll`,
          pointsDelta: -10,
        });
      }
    }
  } else {
    takeoff.push({
      label: 'Takeoff',
      detail: 'No liftoff detected in this session',
      pointsDelta: -50,
    });
  }

  // ---- category: flight path control -------------------------------------
  const flightPath: DebriefFinding[] = [];
  // Heading assignments end once established on the approach (the pilot then
  // flies the localizer, not the last vector).
  const establishedAtSec =
    events.find((e) => e.id === 'established_on_approach')?.simTimeSec ?? Infinity;
  const headingTargets = flagSegments(events, 'atcTargetHeadingDeg');
  let worstHdgErr = 0;
  for (const seg of headingTargets) {
    const segSamples = history.filter(
      (s) =>
        s.simTimeSec >= seg.fromSec + 45 &&
        s.simTimeSec < Math.min(seg.toSec, establishedAtSec) &&
        !s.weightOnWheels,
    );
    for (const s of segSamples) {
      worstHdgErr = Math.max(
        worstHdgErr,
        Math.abs(angleDiffDeg(s.headingDegMag, Number(seg.value))),
      );
    }
  }
  if (headingTargets.length > 0) {
    metrics['Worst heading deviation (established)'] = `${worstHdgErr.toFixed(0)}°`;
    if (worstHdgErr > 20) {
      flightPath.push({
        label: 'Heading compliance',
        detail: `Assigned heading missed by up to ${worstHdgErr.toFixed(0)}° after capture window`,
        pointsDelta: -15,
      });
    } else if (worstHdgErr > 10) {
      flightPath.push({
        label: 'Heading compliance',
        detail: `Heading wandered up to ${worstHdgErr.toFixed(0)}° from assignment`,
        pointsDelta: -7,
      });
    }
  }
  const altTargets = flagSegments(events, 'atcTargetAltitudeFt');
  let worstAltBust = 0;
  for (const seg of altTargets) {
    const segSamples = history.filter(
      (s) =>
        s.simTimeSec >= seg.fromSec &&
        s.simTimeSec < Math.min(seg.toSec, establishedAtSec) &&
        !s.weightOnWheels,
    );
    // A bust only counts after the aircraft first reaches the assigned level
    // (climbing/descending toward a new assignment is not a violation).
    const capturedIdx = segSamples.findIndex(
      (s) => Math.abs(s.altitudeFtMsl - Number(seg.value)) < 150,
    );
    if (capturedIdx < 0) continue;
    for (const s of segSamples.slice(capturedIdx)) {
      const over = Math.abs(s.altitudeFtMsl - Number(seg.value));
      if (over > worstAltBust) worstAltBust = over;
    }
  }
  if (altTargets.length > 0 && worstAltBust > 300) {
    metrics['Worst altitude overshoot'] = `${worstAltBust.toFixed(0)} ft`;
    flightPath.push({
      label: 'Altitude compliance',
      detail: `Climbed ${worstAltBust.toFixed(0)} ft above the assigned altitude`,
      pointsDelta: worstAltBust > 600 ? -20 : -10,
    });
  }
  const climbOverspeed = history.filter((s) => !s.weightOnWheels && s.iasKt > 260).length;
  if (climbOverspeed > 2) {
    flightPath.push({
      label: 'Speed discipline',
      detail: 'Exceeded 250 kt below 10,000 ft',
      pointsDelta: -10,
    });
  }

  // ---- category: ATC compliance ------------------------------------------
  const atcFindings: DebriefFinding[] = [];
  const { readbacksTotal, readbacksCorrect } = input.atcStats;
  metrics['ATC readbacks'] = `${readbacksCorrect}/${readbacksTotal} correct`;
  if (readbacksTotal > 0 && readbacksCorrect < readbacksTotal) {
    atcFindings.push({
      label: 'Readback accuracy',
      detail: `${readbacksTotal - readbacksCorrect} incorrect readback(s)`,
      pointsDelta: -8 * (readbacksTotal - readbacksCorrect),
    });
  }
  if (events.some((e) => e.id === 'landed_without_clearance')) {
    atcFindings.push({
      label: 'Landing clearance',
      detail: 'Landed without landing clearance',
      pointsDelta: -50,
    });
  }

  // ---- category: approach stability --------------------------------------
  const approach: DebriefFinding[] = [];
  const gate = touchdown
    ? [...history]
        .slice(0, touchdownIdx)
        .reverse()
        .find((s) => !s.weightOnWheels && s.radioAltitudeFt >= 450 && s.radioAltitudeFt <= 700)
    : null;
  if (gate) {
    metrics['500 ft gate'] =
      `${gate.iasKt.toFixed(0)} kt / ${gate.verticalSpeedFpm.toFixed(0)} fpm / flaps ${gate.flapHandleDetent}`;
    // Down-and-locked / surfaces travelled, not lever positions (R-18).
    if (gate.gearPositionNorm <= 0.99)
      approach.push({
        label: 'Configuration',
        detail: gate.gearLeverDown
          ? 'Gear still in transit at the 500 ft gate'
          : 'Gear not down at the 500 ft gate',
        pointsDelta: -25,
      });
    if (gate.flapsActualNorm < LANDING_FLAP_NORM)
      approach.push({
        label: 'Configuration',
        detail:
          gate.flapHandleDetent >= 30
            ? `Flap handle 30 but the surfaces were only ${(gate.flapsActualNorm * 100).toFixed(0)}% at the 500 ft gate`
            : `Flaps ${gate.flapHandleDetent} at the 500 ft gate (landing flaps expected)`,
        pointsDelta: -15,
      });
    if (gate.iasKt > vs.vappKt + 20 || gate.iasKt < vs.vappKt - 5)
      approach.push({
        label: 'Approach speed',
        detail: `${gate.iasKt.toFixed(0)} kt at 500 ft (target ${vs.vappKt} kt)`,
        pointsDelta: -12,
      });
    if (gate.verticalSpeedFpm < -1100)
      approach.push({
        label: 'Sink rate',
        detail: `${Math.abs(gate.verticalSpeedFpm).toFixed(0)} fpm descent at 500 ft`,
        pointsDelta: -12,
      });
    if (gate.locDeviationDots !== null && Math.abs(gate.locDeviationDots) > 1)
      approach.push({
        label: 'Localizer',
        detail: `${Math.abs(gate.locDeviationDots).toFixed(1)} dots off the localizer at 500 ft`,
        pointsDelta: -10,
      });
    if (gate.gsDeviationDots !== null && Math.abs(gate.gsDeviationDots) > 1)
      approach.push({
        label: 'Glideslope',
        detail: `${Math.abs(gate.gsDeviationDots).toFixed(1)} dots off the glideslope at 500 ft`,
        pointsDelta: -10,
      });
  } else if (touchdown) {
    approach.push({
      label: 'Approach data',
      detail: 'No stable sample captured at the 500 ft gate',
      pointsDelta: -5,
    });
  }
  if (events.some((e) => e.id === 'fo:unstable_approach' || e.id === 'unstable_approach')) {
    approach.push({
      label: 'Stability',
      detail: 'First officer called an unstable approach',
      pointsDelta: -15,
    });
  }
  for (const gate of [1000, 500] as const) {
    if (events.some((e) => e.id === `fo:gate_${gate}_unstable`)) {
      approach.push({
        label: `${gate} ft gate`,
        detail: `Not stable at the ${gate} ft gate`,
        pointsDelta: gate === 500 ? -15 : -10,
      });
    }
  }
  if (events.some((e) => e.id === 'fo:minimums_go_around')) {
    approach.push({
      label: 'Minimums',
      detail: 'Not stable at minimums — a go-around was called for',
      pointsDelta: -10,
    });
  }

  // ---- category: landing --------------------------------------------------
  const landing: DebriefFinding[] = [];
  if (touchdown) {
    const before = history[touchdownIdx - 1]!;
    const tdVs = Math.min(before.verticalSpeedFpm, 0);
    metrics['Touchdown sink rate'] = `${Math.abs(tdVs).toFixed(0)} fpm`;
    if (tdVs < -600) {
      landing.push({
        label: 'Hard landing',
        detail: `~${Math.abs(tdVs).toFixed(0)} fpm at touchdown`,
        pointsDelta: -30,
      });
    } else if (tdVs < -450) {
      landing.push({
        label: 'Firm landing',
        detail: `~${Math.abs(tdVs).toFixed(0)} fpm at touchdown`,
        pointsDelta: -10,
      });
    }
    const tdFrame = frame(touchdown);
    const tdDistM = tdFrame.alongM;
    metrics['Touchdown point'] = `${tdDistM.toFixed(0)} m past the threshold`;
    if (tdDistM < 75) {
      landing.push({
        label: 'Short touchdown',
        detail: `Touched down ${tdDistM.toFixed(0)} m past the threshold`,
        pointsDelta: -20,
      });
    } else if (tdDistM > 1200) {
      landing.push({
        label: 'Long landing',
        detail: `Touched down ${tdDistM.toFixed(0)} m past the threshold (${(
          tdDistM /
          (runway.lengthFt * FT_TO_M)
        ).toLocaleString(undefined, { style: 'percent' })} of the runway)`,
        pointsDelta: -15,
      });
    }
    metrics['Centerline offset at touchdown'] = `${Math.abs(tdFrame.crossM).toFixed(1)} m`;
    if (Math.abs(tdFrame.crossM) > 10) {
      landing.push({
        label: 'Centerline',
        detail: `Touched down ${Math.abs(tdFrame.crossM).toFixed(0)} m off the centerline`,
        pointsDelta: -12,
      });
    }
    const rollout = history.slice(touchdownIdx, touchdownIdx + 50); // ~25 s
    const usedReverse = events.some((e) => e.id === 'reverse_deployed');
    if (!usedReverse) {
      landing.push({
        label: 'Reverse thrust',
        detail: 'Reverse thrust was not used',
        pointsDelta: -8,
      });
    }
    const slowed = rollout.some((s) => s.iasKt < 45);
    if (!slowed && rollout.length >= 50) {
      landing.push({
        label: 'Deceleration',
        detail: 'Aircraft had not reached taxi speed 25 s after touchdown',
        pointsDelta: -8,
      });
    }
  } else {
    landing.push({
      label: 'Landing',
      detail: 'No touchdown recorded in this session',
      pointsDelta: -60,
    });
  }

  // ---- category: checklist discipline ------------------------------------
  const checklist: DebriefFinding[] = [];
  for (const id of input.expectedChecklistIds) {
    if (!events.some((e) => e.kind === 'checklist_completed' && e.id === id)) {
      checklist.push({
        label: 'Incomplete checklist',
        detail: `Checklist '${id}' was not completed`,
        pointsDelta: -20,
      });
    }
  }
  const failedItems = events.filter((e) => e.kind === 'checklist_item_failed').length;
  if (failedItems > 0) {
    checklist.push({
      label: 'Checklist answers',
      detail: `${failedItems} checklist challenge(s) answered with the aircraft in the wrong state`,
      pointsDelta: Math.max(-15, -3 * failedItems),
    });
  }

  const categories: DebriefCategory[] = [
    cat('takeoff_procedure', 'Takeoff procedure', takeoff),
    cat('flight_path', 'Flight-path control', flightPath),
    cat('atc_compliance', 'ATC compliance', atcFindings),
    cat('approach_stability', 'Approach stability', approach),
    cat('landing', 'Landing accuracy', landing),
    cat('checklist_discipline', 'Checklist discipline', checklist),
  ];

  const safetyCritical = events.filter((e) => e.severity === 'safety_critical');
  const minScore = Math.min(...categories.map((c) => c.score));
  // A single safety-critical event fails the flight. SCENARIO_AUTHORING.md
  // defines that severity as flight-failing, and a runway incursion scoring
  // "pass with deviations" contradicted it (R-09).
  const overall: DebriefOverall =
    minScore < 50 || safetyCritical.length > 0
      ? 'FAIL'
      : minScore < 85 || categories.some((c) => c.findings.length > 0)
        ? 'PASS_WITH_DEVIATIONS'
        : 'PASS';

  return {
    overall,
    categories,
    timeline: events.filter((e) => e.kind !== 'flag_changed'),
    metrics,
  };
}

function cat(id: string, label: string, findings: DebriefFinding[]): DebriefCategory {
  const score = Math.max(0, 100 + findings.reduce((acc, f) => acc + f.pointsDelta, 0));
  return { id, label, score, findings };
}

/** Time segments during which a numeric flag held each value. */
function flagSegments(
  events: ScenarioEvent[],
  flagName: string,
): { value: number | string | boolean; fromSec: number; toSec: number }[] {
  const changes = events
    .filter((e) => e.kind === 'flag_changed' && (e.data as { name?: string })?.name === flagName)
    .map((e) => ({ atSec: e.simTimeSec, value: (e.data as { value: number }).value }));
  const segments: { value: number; fromSec: number; toSec: number }[] = [];
  for (let i = 0; i < changes.length; i++) {
    segments.push({
      value: changes[i]!.value,
      fromSec: changes[i]!.atSec,
      toSec: changes[i + 1]?.atSec ?? Infinity,
    });
  }
  return segments;
}
