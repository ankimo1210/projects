import { clamp, type AircraftState } from '@b737/shared';

/**
 * Shared target values for the continuous cockpit controls (R-13).
 *
 * Keyboard, gamepad, the DOM panel and 3D lever drags all move the SAME
 * target. Previously the input manager kept private throttle/reverser values
 * starting at 0, so nudging the throttle key after a 3D drag to 50 % snapped
 * the lever back to ~4 %.
 *
 * When nobody has touched a target recently it follows backend state, which
 * also re-syncs it after a scenario reset or a reconnect.
 */

export type ControlTargetKey = 'throttle' | 'reverser';

/** How long a local intent wins over incoming backend state. */
const HOLD_LOCAL_MS = 500;

class ControlTargets {
  private values: Record<ControlTargetKey, number> = { throttle: 0, reverser: 0 };
  private touchedAtMs: Record<ControlTargetKey, number> = {
    throttle: -Infinity,
    reverser: -Infinity,
  };

  /** Feed every state sample: idle targets adopt what the aircraft is doing. */
  observe(state: AircraftState): void {
    const now = Date.now();
    if (now - this.touchedAtMs.throttle > HOLD_LOCAL_MS) {
      this.values.throttle = state.engines.left.throttleLeverNorm;
    }
    if (now - this.touchedAtMs.reverser > HOLD_LOCAL_MS) {
      this.values.reverser = state.engines.left.reverserNorm;
    }
  }

  get(key: ControlTargetKey): number {
    return this.values[key];
  }

  /** Set an explicit target (slider, 3D drag); returns the clamped value. */
  set(key: ControlTargetKey, value: number): number {
    this.values[key] = clamp(value, 0, 1);
    this.touchedAtMs[key] = Date.now();
    return this.values[key];
  }

  /** Relative change (keyboard/gamepad step) from the current target. */
  nudge(key: ControlTargetKey, delta: number): number {
    return this.set(key, this.values[key] + delta);
  }

  /** Forget local intent — used on scenario reset. */
  reset(): void {
    this.values = { throttle: 0, reverser: 0 };
    this.touchedAtMs = { throttle: -Infinity, reverser: -Infinity };
  }
}

export const controlTargets = new ControlTargets();
