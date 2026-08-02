/** Simple token bucket for per-connection input rate limiting (spec §6). */
export class TokenBucket {
  private tokens: number;
  private lastRefillMs: number;

  constructor(
    private readonly capacity: number,
    private readonly refillPerSec: number,
    nowMs: number,
  ) {
    this.tokens = capacity;
    this.lastRefillMs = nowMs;
  }

  tryTake(nowMs: number): boolean {
    const elapsed = Math.max(0, nowMs - this.lastRefillMs) / 1000;
    this.tokens = Math.min(this.capacity, this.tokens + elapsed * this.refillPerSec);
    this.lastRefillMs = nowMs;
    if (this.tokens >= 1) {
      this.tokens -= 1;
      return true;
    }
    return false;
  }
}

/**
 * Axis-style commands stream continuously; discrete commands do not.
 * Speed brake and reverse levers are dragged like the throttle, so they belong
 * in the continuous bucket — in the discrete one a normal drag was mostly
 * rejected and the lever stopped short of where it was released (R-14).
 */
export const AXIS_COMMAND_TYPES = new Set([
  'set_control_axis',
  'set_throttle',
  'set_brakes',
  'set_speedbrake',
  'set_reverse_thrust',
]);
