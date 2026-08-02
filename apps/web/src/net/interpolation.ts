import { angleDiffDeg, lerp, normalizeDeg360, type AircraftState } from '@b737/shared';

/**
 * State sample buffer with render-time interpolation (spec §6): rendering
 * runs at display refresh while state arrives at 20–60 Hz; we render the
 * aircraft a fixed delay behind the newest sample and interpolate between
 * the two samples that straddle the render time.
 */
export class StateInterpolator {
  private buffer: AircraftState[] = [];
  /** Render this far behind the freshest sample. */
  readonly delayMs: number;

  constructor(delayMs = 120) {
    this.delayMs = delayMs;
  }

  push(state: AircraftState): void {
    this.buffer.push(state);
    // keep ~2 s of history
    const cutoff = state.timestampMs - 2000;
    while (this.buffer.length > 2 && this.buffer[0]!.timestampMs < cutoff) {
      this.buffer.shift();
    }
  }

  get latest(): AircraftState | null {
    return this.buffer[this.buffer.length - 1] ?? null;
  }

  /** Age of the newest sample relative to `nowMs` (stale detection). */
  staleness(nowMs: number): number | null {
    const latest = this.latest;
    return latest ? nowMs - latest.timestampMs : null;
  }

  /** Interpolated view at wall-clock `nowMs`. Returns latest when starved. */
  sample(nowMs: number): AircraftState | null {
    const n = this.buffer.length;
    if (n === 0) return null;
    if (n === 1) return this.buffer[0]!;
    const target = nowMs - this.delayMs;
    // find the straddling pair
    let after = this.buffer[n - 1]!;
    let before = this.buffer[n - 2]!;
    for (let i = n - 1; i >= 1; i--) {
      if (this.buffer[i - 1]!.timestampMs <= target) {
        before = this.buffer[i - 1]!;
        after = this.buffer[i]!;
        if (after.timestampMs >= target) break;
      }
    }
    if (target >= after.timestampMs) return after; // starved: hold latest
    const span = after.timestampMs - before.timestampMs;
    if (span <= 0) return after;
    const t = Math.min(1, Math.max(0, (target - before.timestampMs) / span));
    return interpolateStates(before, after, t);
  }
}

/** Linear interpolation of continuous fields; discrete fields snap to `b`. */
export function interpolateStates(a: AircraftState, b: AircraftState, t: number): AircraftState {
  const angle = (x: number, y: number): number => normalizeDeg360(x + angleDiffDeg(x, y) * t);
  return {
    ...b,
    timestampMs: lerp(a.timestampMs, b.timestampMs, t),
    simTimeSec: lerp(a.simTimeSec, b.simTimeSec, t),
    position: {
      latDeg: lerp(a.position.latDeg, b.position.latDeg, t),
      lonDeg: lerp(a.position.lonDeg, b.position.lonDeg, t),
      altitudeFtMsl: lerp(a.position.altitudeFtMsl, b.position.altitudeFtMsl, t),
      radioAltitudeFt: lerp(a.position.radioAltitudeFt, b.position.radioAltitudeFt, t),
    },
    attitude: {
      pitchDeg: lerp(a.attitude.pitchDeg, b.attitude.pitchDeg, t),
      rollDeg: lerp(a.attitude.rollDeg, b.attitude.rollDeg, t),
      headingDegMag: angle(a.attitude.headingDegMag, b.attitude.headingDegMag),
      groundTrackDegMag: angle(a.attitude.groundTrackDegMag, b.attitude.groundTrackDegMag),
      aoaDeg:
        a.attitude.aoaDeg !== null && b.attitude.aoaDeg !== null
          ? lerp(a.attitude.aoaDeg, b.attitude.aoaDeg, t)
          : b.attitude.aoaDeg,
    },
    speeds: {
      iasKt: lerp(a.speeds.iasKt, b.speeds.iasKt, t),
      gsKt: lerp(a.speeds.gsKt, b.speeds.gsKt, t),
      verticalSpeedFpm: lerp(a.speeds.verticalSpeedFpm, b.speeds.verticalSpeedFpm, t),
    },
    engines: {
      left: {
        ...b.engines.left,
        n1Pct: lerp(a.engines.left.n1Pct, b.engines.left.n1Pct, t),
      },
      right: {
        ...b.engines.right,
        n1Pct: lerp(a.engines.right.n1Pct, b.engines.right.n1Pct, t),
      },
    },
    controls: {
      ...b.controls,
      flapsActualNorm: lerp(a.controls.flapsActualNorm, b.controls.flapsActualNorm, t),
      gearPositionNorm: lerp(a.controls.gearPositionNorm, b.controls.gearPositionNorm, t),
      spoilersDeployedNorm: lerp(a.controls.spoilersDeployedNorm, b.controls.spoilersDeployedNorm, t),
    },
  };
}
