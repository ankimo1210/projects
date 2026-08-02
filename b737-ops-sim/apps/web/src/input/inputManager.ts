import { FLAP_DETENTS, clamp, type FlapDetent } from '@b737/shared';
import { sendCommand, sendCommandWithSound } from '../state/connection.js';
import { useSimStore } from '../state/stores.js';
import { controlTargets } from './controlTargets.js';

/**
 * Input abstraction layer (spec §18): keyboard + mouse + standard gamepad in
 * M1, with per-axis deadzone / sensitivity / inversion persisted locally.
 * Axis commands are coalesced and rate-limited to ~20 Hz (spec §6).
 */

export interface AxisSettings {
  deadzone: number;
  sensitivity: number; // exponent-style curve, 1 = linear
  inverted: boolean;
}

export interface InputBindings {
  gamepadAxes: { roll: number; pitch: number; yaw: number; throttle: number };
  axisSettings: { roll: AxisSettings; pitch: AxisSettings; yaw: AxisSettings };
}

const DEFAULT_BINDINGS: InputBindings = {
  gamepadAxes: { roll: 0, pitch: 1, yaw: 2, throttle: 3 },
  axisSettings: {
    roll: { deadzone: 0.08, sensitivity: 1.4, inverted: false },
    pitch: { deadzone: 0.08, sensitivity: 1.4, inverted: false },
    yaw: { deadzone: 0.1, sensitivity: 1.2, inverted: false },
  },
};

const STORAGE_KEY = 'b737.bindings.v1';

export function loadBindings(): InputBindings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULT_BINDINGS, ...(JSON.parse(raw) as Partial<InputBindings>) };
  } catch {
    /* corrupted storage — fall back to defaults */
  }
  return DEFAULT_BINDINGS;
}

export function saveBindings(bindings: InputBindings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(bindings));
}

function shapeAxis(raw: number, s: AxisSettings): number {
  const v = s.inverted ? -raw : raw;
  const abs = Math.abs(v);
  if (abs < s.deadzone) return 0;
  const scaled = (abs - s.deadzone) / (1 - s.deadzone);
  return Math.sign(v) * Math.pow(scaled, s.sensitivity);
}

export class InputManager {
  bindings = loadBindings();
  private keys = new Set<string>();
  /** Last shaped axis values (read by the 3D yoke display). */
  readonly axes = { pitch: 0, roll: 0, yaw: 0 };
  private brake = 0;
  private lastSent = { pitch: NaN, roll: NaN, yaw: NaN, throttle: NaN, brake: NaN };
  private timer: number | null = null;
  private gamepadIndex: number | null = null;

  start(): void {
    window.addEventListener('keydown', this.onKeyDown);
    window.addEventListener('keyup', this.onKeyUp);
    window.addEventListener('gamepadconnected', (e) => {
      this.gamepadIndex = (e as GamepadEvent).gamepad.index;
    });
    window.addEventListener('gamepaddisconnected', () => {
      this.gamepadIndex = null;
    });
    this.timer = window.setInterval(() => this.tick(), 50); // 20 Hz
  }

  stop(): void {
    window.removeEventListener('keydown', this.onKeyDown);
    window.removeEventListener('keyup', this.onKeyUp);
    if (this.timer !== null) window.clearInterval(this.timer);
  }

  /** Current throttle target (UI slider sync) — shared with 3D/DOM input. */
  get throttleNorm(): number {
    return controlTargets.get('throttle');
  }

  setThrottle(v: number): void {
    controlTargets.set('throttle', v);
  }

  setReverser(v: number): void {
    sendCommandWithSound(
      { type: 'set_reverse_thrust', leverNorm: controlTargets.set('reverser', v) },
      'lever',
    );
  }

  private onKeyDown = (e: KeyboardEvent): void => {
    if (e.repeat) return;
    if (isTypingTarget(e.target)) return;
    this.keys.add(e.code);
    this.handleDiscreteKey(e.code);
  };

  private onKeyUp = (e: KeyboardEvent): void => {
    this.keys.delete(e.code);
  };

  private handleDiscreteKey(code: string): void {
    const state = useSimStore.getState().latest;
    switch (code) {
      case 'KeyG': {
        const down = state?.controls.gearLeverDown ?? true;
        sendCommandWithSound({ type: 'set_gear', down: !down }, 'gear_lever');
        break;
      }
      case 'BracketRight': {
        this.stepFlaps(1);
        break;
      }
      case 'BracketLeft': {
        this.stepFlaps(-1);
        break;
      }
      case 'KeyP': {
        const set = state?.controls.parkingBrakeSet ?? false;
        sendCommandWithSound({ type: 'set_parking_brake', engaged: !set }, 'click');
        break;
      }
      case 'KeyB': {
        const lever = state?.controls.speedbrakeLeverNorm ?? 0;
        sendCommandWithSound({ type: 'set_speedbrake', leverNorm: lever > 0.5 ? 0 : 1 }, 'lever');
        break;
      }
      case 'KeyR': {
        this.setReverser(controlTargets.get('reverser') > 0.5 ? 0 : 1);
        break;
      }
      case 'KeyA': {
        const engaged = state?.mcp.autopilotEngaged ?? false;
        sendCommandWithSound({ type: 'set_autopilot', engaged: !engaged }, 'click');
        break;
      }
      default:
        break;
    }
  }

  private stepFlaps(direction: 1 | -1): void {
    const state = useSimStore.getState().latest;
    const current = (state?.controls.flapHandleDetent ?? 0) as FlapDetent;
    const idx = FLAP_DETENTS.indexOf(current);
    const next = FLAP_DETENTS[clamp(idx + direction, 0, FLAP_DETENTS.length - 1)]!;
    if (next !== current) {
      sendCommandWithSound({ type: 'set_flaps', detent: next }, 'flap_lever');
    }
  }

  private tick(): void {
    // ---- keyboard axes (hold to deflect, release to center) ----
    let kbPitch = 0;
    let kbRoll = 0;
    let kbYaw = 0;
    if (this.keys.has('ArrowUp')) kbPitch -= 1; // stick forward = nose down
    if (this.keys.has('ArrowDown')) kbPitch += 1;
    if (this.keys.has('ArrowLeft')) kbRoll -= 1;
    if (this.keys.has('ArrowRight')) kbRoll += 1;
    if (this.keys.has('Comma')) kbYaw -= 1;
    if (this.keys.has('Period')) kbYaw += 1;
    // Keyboard steps move the SHARED target, so they continue from wherever
    // the lever actually is (3D drag, DOM slider, backend) — R-13.
    if (this.keys.has('Equal') || this.keys.has('PageUp')) {
      controlTargets.nudge('throttle', 0.02);
    }
    if (this.keys.has('Minus') || this.keys.has('PageDown')) {
      controlTargets.nudge('throttle', -0.02);
    }
    this.brake = this.keys.has('Space') ? 1 : 0;

    // ---- gamepad ----
    let gp: Gamepad | null = null;
    if (this.gamepadIndex !== null) {
      gp = navigator.getGamepads()[this.gamepadIndex] ?? null;
    }
    if (gp) {
      const a = this.bindings.gamepadAxes;
      const s = this.bindings.axisSettings;
      kbRoll = kbRoll || shapeAxis(gp.axes[a.roll] ?? 0, s.roll);
      kbPitch = kbPitch || shapeAxis(gp.axes[a.pitch] ?? 0, s.pitch);
      kbYaw = kbYaw || shapeAxis(gp.axes[a.yaw] ?? 0, s.yaw);
      const rawThr = gp.axes[a.throttle];
      if (rawThr !== undefined && Math.abs(rawThr) > 0.02) {
        controlTargets.set('throttle', (1 - rawThr) / 2); // typical inverted slider
      }
    }

    // schema: pitch +1 = nose up; ArrowDown (pull) maps to +1 already
    this.axes.pitch = clamp(kbPitch, -1, 1);
    this.axes.roll = clamp(kbRoll, -1, 1);
    this.axes.yaw = clamp(kbYaw, -1, 1);

    this.sendIfChanged('pitch', this.axes.pitch);
    this.sendIfChanged('roll', this.axes.roll);
    this.sendIfChanged('yaw', this.axes.yaw);
    const throttle = controlTargets.get('throttle');
    if (this.lastSent.throttle !== throttle) {
      this.lastSent.throttle = throttle;
      sendCommand({ type: 'set_throttle', valueNorm: throttle });
    }
    if (this.lastSent.brake !== this.brake) {
      this.lastSent.brake = this.brake;
      sendCommand({ type: 'set_brakes', valueNorm: this.brake });
    }
  }

  private sendIfChanged(axis: 'pitch' | 'roll' | 'yaw', value: number): void {
    if (this.lastSent[axis] === value) return;
    this.lastSent[axis] = value;
    sendCommand({ type: 'set_control_axis', axis, valueNorm: value });
  }
}

function isTypingTarget(target: EventTarget | null): boolean {
  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    (target instanceof HTMLElement && target.isContentEditable)
  );
}

export const inputManager = new InputManager();
