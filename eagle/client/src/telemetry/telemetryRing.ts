import type { PhaseChange, TelemetryFrame } from "./types";

/** 5 minutes at 10 Hz. */
export const RING_CAPACITY = 3000;

/**
 * Fixed-capacity telemetry ring. Holds up to {@link RING_CAPACITY} frames,
 * dropping the oldest, and derives the major-mode phase timeline on push.
 * `version` bumps on every push so React consumers can re-render cheaply.
 */
export class TelemetryRing {
  private buf: TelemetryFrame[] = [];
  latest: TelemetryFrame | null = null;
  phases: PhaseChange[] = [];
  version = 0;
  private lastMm = "";

  push(f: TelemetryFrame): void {
    this.buf.push(f);
    if (this.buf.length > RING_CAPACITY) this.buf.shift();
    this.latest = f;
    if (f.mm !== "" && f.mm !== this.lastMm) {
      this.phases.push({ t_s: f.t_s, mm: f.mm });
      this.lastMm = f.mm;
    }
    this.version++;
  }

  frames(): TelemetryFrame[] {
    return this.buf;
  }
}
